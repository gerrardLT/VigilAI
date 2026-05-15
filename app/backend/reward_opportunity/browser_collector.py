"""Read-only browser collection policy and adapter."""

from __future__ import annotations

import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Callable
from urllib.parse import urlparse

from pydantic import BaseModel, Field

from .mcp_tools import tool_envelope


BROWSER_DISALLOWED_ACTIONS = {
    "submit_form",
    "register",
    "login",
    "claim_reward",
    "payment",
    "purchase",
}


class BrowserCollectConstraints(BaseModel):
    read_only: bool = True
    max_steps: int = 12
    max_seconds: int = 60
    allowed_domains: list[str] = Field(default_factory=list)
    disallowed_actions: list[str] = Field(default_factory=lambda: sorted(BROWSER_DISALLOWED_ACTIONS))


BrowserRunner = Callable[[str, str, BrowserCollectConstraints], dict[str, Any]]


def _allowed_domain(url: str, allowed_domains: list[str]) -> bool:
    if not allowed_domains:
        return True
    host = urlparse(url).netloc.lower()
    return any(host == domain.lower() or host.endswith(f".{domain.lower()}") for domain in allowed_domains)


def _default_runner(url: str, objective: str, constraints: BrowserCollectConstraints) -> dict[str, Any]:
    try:
        browser_use_result = _try_browser_use_runner(url, objective, constraints)
        if browser_use_result is not None:
            return browser_use_result
    except Exception:
        pass
    return _playwright_runner(url, objective, constraints)


def _try_browser_use_runner(url: str, objective: str, constraints: BrowserCollectConstraints) -> dict[str, Any] | None:
    if not url.lower().startswith(("http://", "https://")):
        return None

    try:
        from browser_use import Agent as BrowserUseAgent
    except Exception:
        return None

    try:
        from langchain_openai import ChatOpenAI
    except Exception as exc:
        raise RuntimeError("browser-use is installed but langchain-openai is unavailable") from exc

    from .pydantic_evaluator import build_openai_compatible_client_config

    client_config = build_openai_compatible_client_config()

    task = (
        f"Open {url} and collect evidence for: {objective}. "
        "Read-only policy: do not log in, submit forms, click claim buttons, register, pay, or modify state. "
        "Return page title, visible text excerpts, final URL, and links that look like rules, FAQ, terms, rewards, or eligibility."
    )
    llm = ChatOpenAI(
        model=str(client_config["model"]),
        api_key=str(client_config["api_key"]),
        base_url=str(client_config["base_url"]),
        temperature=0,
    )
    agent = BrowserUseAgent(task=task, llm=llm)
    result = asyncio.run(agent.run(max_steps=constraints.max_steps))
    return {
        "final_url": url,
        "text": str(result),
        "objective": objective,
        "actions": [{"action_type": "browser_use_read", "target_url": url}],
        "screenshot_path": None,
        "dom_excerpt": str(result)[:4000],
        "constraints": constraints.model_dump(),
        "engine": "browser_use",
    }


def _playwright_runner(url: str, objective: str, constraints: BrowserCollectConstraints) -> dict[str, Any]:
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return _playwright_runner_sync(url, objective, constraints)

    with ThreadPoolExecutor(max_workers=1) as executor:
        return executor.submit(_playwright_runner_sync, url, objective, constraints).result()


def _playwright_runner_sync(url: str, objective: str, constraints: BrowserCollectConstraints) -> dict[str, Any]:
    try:
        from playwright.sync_api import sync_playwright
    except Exception as exc:
        raise RuntimeError("browser-use and Playwright are unavailable for real browser collection") from exc

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        try:
            page = browser.new_page()
            page.goto(url, wait_until="domcontentloaded", timeout=constraints.max_seconds * 1000)
            page.wait_for_timeout(500)
            title = page.title()
            text = page.locator("body").inner_text(timeout=5000)[:12000]
            links = page.eval_on_selector_all(
                "a[href]",
                """els => els.slice(0, 200).map(a => ({text: (a.innerText || '').trim(), href: a.href}))""",
            )
            relevant_links = [
                link
                for link in links
                if any(token in f"{link.get('text', '')} {link.get('href', '')}".lower() for token in ("rule", "faq", "term", "reward", "eligib", "campaign", "invite"))
            ][:25]
            return {
                "final_url": page.url,
                "title": title,
                "text": text,
                "objective": objective,
                "links": relevant_links,
                "actions": [{"action_type": "open_url", "target_url": url}],
                "screenshot_path": None,
                "dom_excerpt": text[:4000],
                "constraints": constraints.model_dump(),
                "engine": "playwright",
            }
        finally:
            browser.close()


def _empty_runner(url: str, objective: str, constraints: BrowserCollectConstraints) -> dict[str, Any]:
    return {
        "final_url": url,
        "text": "",
        "objective": objective,
        "actions": [{"action_type": "open_url", "target_url": url}],
        "screenshot_path": None,
        "dom_excerpt": "",
        "constraints": constraints.model_dump(),
    }


def browser_collect(
    url: str,
    objective: str,
    *,
    constraints: BrowserCollectConstraints | dict[str, Any] | None = None,
    runner: BrowserRunner | None = None,
) -> dict[str, Any]:
    active_constraints = (
        constraints
        if isinstance(constraints, BrowserCollectConstraints)
        else BrowserCollectConstraints.model_validate(constraints or {})
    )
    if not _allowed_domain(url, active_constraints.allowed_domains):
        return tool_envelope(
            ok=False,
            source="browser_collect",
            failure_type="domain_blocked",
            error_message=f"Domain not allowed for browser collection: {url}",
        )

    try:
        result = (runner or _default_runner)(url, objective, active_constraints)
    except Exception as exc:
        return tool_envelope(ok=False, source="browser_collect", failure_type="tool_error", error_message=str(exc))

    disallowed = set(active_constraints.disallowed_actions)
    attempted = [
        str(action.get("action_type"))
        for action in list(result.get("actions") or [])
        if str(action.get("action_type")) in disallowed
    ]
    if active_constraints.read_only and attempted:
        return tool_envelope(
            ok=False,
            source="browser_collect",
            failure_type="approval_required",
            error_message=f"Read-only browser policy blocked actions: {', '.join(attempted)}",
            data={"attempted_actions": attempted, "raw_result": result},
        )

    return tool_envelope(ok=True, source="browser_collect", data=result)
