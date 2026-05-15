"""Runtime helpers inspired by the local agent-reach setup."""

from __future__ import annotations

import json
import re
import subprocess
from html import unescape
from typing import Any
from urllib.parse import quote_plus

import requests


_SEARCH_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
)


def exa_search_available() -> bool:
    try:
        check = subprocess.run(
            ["mcporter", "config", "list"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=8,
        )
    except (FileNotFoundError, subprocess.SubprocessError):
        return False
    return check.returncode == 0 and "exa" in (check.stdout or "")


def search_urls(query: str, *, max_results: int = 5) -> list[str]:
    query = query.strip()
    if not query:
        return []
    urls = _search_urls_via_exa(query, max_results=max_results)
    if urls:
        return urls
    return _search_urls_via_duckduckgo(query, max_results=max_results)


def _search_urls_via_exa(query: str, *, max_results: int) -> list[str]:
    if not exa_search_available():
        return []
    command = [
        "mcporter",
        "call",
        f'exa.web_search_exa(query: "{query.replace(chr(34), chr(39))}", numResults: {max_results})',
    ]
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=20,
        )
    except (FileNotFoundError, subprocess.SubprocessError):
        return []
    if result.returncode != 0 or not result.stdout.strip():
        return []
    return _extract_urls_from_text(result.stdout, max_results=max_results)


def _search_urls_via_duckduckgo(query: str, *, max_results: int) -> list[str]:
    response = requests.get(
        f"https://html.duckduckgo.com/html/?q={quote_plus(query)}",
        headers={"User-Agent": _SEARCH_USER_AGENT},
        timeout=20,
    )
    response.raise_for_status()
    matches = re.findall(r'<a[^>]+class="result__a"[^>]+href="([^"]+)"', response.text, re.IGNORECASE)
    urls: list[str] = []
    for match in matches:
        cleaned = unescape(match)
        if cleaned.startswith("http") and cleaned not in urls:
            urls.append(cleaned)
        if len(urls) >= max_results:
            break
    return urls


def _extract_urls_from_text(text: str, *, max_results: int) -> list[str]:
    urls: list[str] = []

    try:
        payload = json.loads(text)
        urls.extend(_extract_urls_from_payload(payload))
    except json.JSONDecodeError:
        pass

    if not urls:
        urls.extend(re.findall(r"https?://[^\s\"'>)]+", text))

    deduped: list[str] = []
    for url in urls:
        normalized = url.rstrip(".,)")
        if normalized not in deduped:
            deduped.append(normalized)
        if len(deduped) >= max_results:
            break
    return deduped


def _extract_urls_from_payload(payload: Any) -> list[str]:
    found: list[str] = []
    if isinstance(payload, dict):
        for key, value in payload.items():
            if key in {"url", "link", "href"} and isinstance(value, str) and value.startswith("http"):
                found.append(value)
            else:
                found.extend(_extract_urls_from_payload(value))
    elif isinstance(payload, list):
        for item in payload:
            found.extend(_extract_urls_from_payload(item))
    return found
