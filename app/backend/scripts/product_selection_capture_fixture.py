r"""
Capture marketplace HTML fixtures for product-selection adapter regression tests.

Examples:
  python app/backend/scripts/product_selection_capture_fixture.py ^
    --url "https://s.taobao.com/search?q=%E5%AE%A0%E7%89%A9%E9%A5%AE%E6%B0%B4%E6%9C%BA" ^
    --output app/backend/tests/fixtures/product_selection/taobao_logged_in_search.html ^
    --cookie-file C:\path\to\browser-cookies.json

  python app/backend/scripts/product_selection_capture_fixture.py ^
    --snapshot-file C:\path\to\saved-dom.html ^
    --output app/backend/tests/fixtures/product_selection/goofish_logged_in_snapshot.html
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any
from urllib.parse import quote
from urllib.parse import urlparse

import httpx
from playwright.sync_api import sync_playwright

SCRIPT_ROOT = Path(__file__).resolve().parent
BACKEND_ROOT = SCRIPT_ROOT.parent
for path in (SCRIPT_ROOT, BACKEND_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from export_chromium_cookies import export_cookies as export_browser_cookies
from product_selection.adapters import TaobaoAdapter, XianyuAdapter


DEFAULT_HEADERS = {
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36",
    "accept-language": "zh-CN,zh;q=0.9,en;q=0.8",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Capture logged-in marketplace fixtures.")
    parser.add_argument("--url", help="Live page URL to fetch.")
    parser.add_argument("--snapshot-file", help="Already-saved rendered DOM snapshot HTML file.")
    parser.add_argument("--cookie-file", help="JSON cookie export file from browser/devtools.")
    parser.add_argument("--browser", choices=["chrome", "edge"], help="Installed Chromium browser to read cookies from.")
    parser.add_argument("--profile", default="Default", help="Chromium profile directory name.")
    parser.add_argument(
        "--cdp-endpoint",
        help="Existing Chromium remote-debugging endpoint, for example http://127.0.0.1:9222.",
    )
    parser.add_argument(
        "--cookie-domains",
        help="Comma-separated domains for automatic browser cookie export. Defaults from target URL or platform.",
    )
    parser.add_argument(
        "--rendered-via-browser",
        action="store_true",
        help="Open the target URL in a headless browser with cookies applied, then save rendered DOM.",
    )
    parser.add_argument("--wait-ms", type=int, default=4000, help="Extra wait time for rendered-browser capture.")
    parser.add_argument("--output", required=True, help="Output HTML fixture path.")
    parser.add_argument("--meta-output", help="Optional metadata JSON path.")
    parser.add_argument("--label", default="", help="Short label to store in metadata.")
    parser.add_argument("--platform", choices=["taobao", "xianyu"], help="Marketplace platform for detail capture.")
    parser.add_argument("--query-text", help="Query text used when extracting live listings from a saved snapshot.")
    parser.add_argument(
        "--capture-detail-pages-from-snapshot",
        action="store_true",
        help="Parse listing URLs from the snapshot/output HTML and capture matching detail pages.",
    )
    parser.add_argument("--detail-output-dir", help="Directory where captured detail HTML files will be written.")
    parser.add_argument("--detail-meta-output", help="Optional manifest JSON path for captured detail pages.")
    parser.add_argument("--detail-limit", type=int, default=5, help="Maximum number of detail pages to capture.")
    return parser.parse_args()


def load_cookie_map(cookie_file: str | None) -> dict[str, str]:
    if not cookie_file:
        return {}
    path = Path(cookie_file)
    if not path.exists():
        raise FileNotFoundError(f"Cookie file not found: {cookie_file}")
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if isinstance(payload, dict) and isinstance(payload.get("cookies"), list):
        rows = payload["cookies"]
    elif isinstance(payload, list):
        rows = payload
    elif isinstance(payload, dict):
        return {str(key): str(value) for key, value in payload.items()}
    else:
        rows = []
    cookie_map: dict[str, str] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        name = str(row.get("name") or "").strip()
        value = str(row.get("value") or "").strip()
        if name and value:
            cookie_map[name] = value
    return cookie_map


def default_cookie_domains(*, url: str | None, platform: str | None) -> str:
    host = urlparse(url).hostname if url else ""
    host = host or ""
    if "goofish.com" in host or platform == "xianyu":
        return "goofish.com,2.taobao.com,taobao.com"
    if "taobao.com" in host or platform == "taobao":
        return "taobao.com,2.taobao.com,goofish.com"
    return host or "taobao.com,2.taobao.com,goofish.com"


def ensure_cookie_file(
    *,
    cookie_file: str | None,
    browser: str | None,
    profile: str,
    domains: str,
    output_path: Path,
) -> str | None:
    if cookie_file:
        return cookie_file
    if not browser:
        return None

    generated_cookie_file = output_path.with_suffix(".cookies.json")
    exported = export_browser_cookies(
        browser=browser,
        profile=profile,
        domains=domains,
        strategy="auto",
    )
    generated_cookie_file.write_text(
        json.dumps(
            {
                "browser": browser,
                "profile": profile,
                "domains": domains,
                "cookies": exported,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    return str(generated_cookie_file)


def load_cookie_rows(cookie_file: str | None) -> list[dict[str, Any]]:
    if not cookie_file:
        return []
    path = Path(cookie_file)
    if not path.exists():
        raise FileNotFoundError(f"Cookie file not found: {cookie_file}")
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if isinstance(payload, dict) and isinstance(payload.get("cookies"), list):
        rows = payload["cookies"]
    elif isinstance(payload, list):
        rows = payload
    elif isinstance(payload, dict):
        return [{"name": str(key), "value": str(value)} for key, value in payload.items()]
    else:
        rows = []

    normalized: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        name = str(row.get("name") or "").strip()
        value = str(row.get("value") or "").strip()
        if not name or not value:
            continue
        normalized.append(row)
    return normalized


def _cookie_domain_matches(cookie_domain: str, hostname: str) -> bool:
    normalized = cookie_domain.lstrip(".").lower()
    return bool(normalized) and hostname.lower().endswith(normalized)


def _to_playwright_cookies(url: str, cookie_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    parsed = urlparse(url)
    hostname = parsed.hostname or ""
    secure = parsed.scheme == "https"
    cookies: list[dict[str, Any]] = []
    for row in cookie_rows:
        domain = str(row.get("domain") or "").strip()
        if domain and not _cookie_domain_matches(domain, hostname):
            continue
        cookie: dict[str, Any] = {
            "name": str(row["name"]),
            "value": str(row["value"]),
            "httpOnly": bool(row.get("httpOnly") or row.get("httponly") or False),
            "secure": bool(row.get("secure")) if row.get("secure") is not None else secure,
            "sameSite": "Lax",
        }
        same_site = str(row.get("sameSite") or row.get("same_site") or "").strip().lower()
        if same_site in {"lax", "strict", "none"}:
            cookie["sameSite"] = same_site.capitalize()
        expires = row.get("expires") or row.get("expirationDate")
        if expires is None:
            expires = row.get("expires_utc")
        if isinstance(expires, (int, float)) and float(expires) > 0:
            cookie["expires"] = int(float(expires))
        if domain:
            cookie["domain"] = domain
            cookie["path"] = str(row.get("path") or "/")
        else:
            cookie["url"] = f"{parsed.scheme}://{hostname}"
        cookies.append(cookie)
    return cookies


def capture_rendered_html(
    url: str,
    cookie_file: str | None,
    wait_ms: int,
    *,
    cdp_endpoint: str | None = None,
) -> str:
    cookie_rows = load_cookie_rows(cookie_file)
    with sync_playwright() as playwright:
        if cdp_endpoint:
            browser = playwright.chromium.connect_over_cdp(cdp_endpoint)
            context = browser.contexts[0] if browser.contexts else browser.new_context()
            page = context.new_page()
            page.goto(url, wait_until="domcontentloaded", timeout=30000)
            page.wait_for_timeout(max(wait_ms, 0))
            html = page.content()
            page.close()
            browser.close()
            return html

        browser = playwright.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent=DEFAULT_HEADERS["user-agent"],
            locale="zh-CN",
        )
        if cookie_rows:
            context.add_cookies(_to_playwright_cookies(url, cookie_rows))
        page = context.new_page()
        page.goto(url, wait_until="domcontentloaded", timeout=30000)
        page.wait_for_timeout(max(wait_ms, 0))
        html = page.content()
        context.close()
        browser.close()
        return html


def build_adapter(platform: str):
    if platform == "taobao":
        return TaobaoAdapter(live_enabled=True)
    if platform == "xianyu":
        return XianyuAdapter(live_enabled=True)
    raise ValueError(f"Unsupported platform: {platform}")


def extract_listing_urls_from_snapshot(
    *,
    platform: str,
    query_text: str,
    html: str,
    limit: int,
) -> list[str]:
    adapter = build_adapter(platform)
    base_url = adapter.search_url_template.format(query=quote(query_text))
    listings = adapter._extract_listings(
        html,
        query_text,
        base_url=base_url,
        source="rendered_snapshot",
    )
    return [listing.url for listing in listings[: max(limit, 0)]]


def capture_detail_pages(
    *,
    urls: list[str],
    cookie_file: str | None,
    wait_ms: int,
    output_dir: str,
    cdp_endpoint: str | None = None,
) -> list[dict[str, Any]]:
    target_dir = Path(output_dir)
    target_dir.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, Any]] = []
    for index, url in enumerate(urls, start=1):
        html = capture_rendered_html(url, cookie_file, wait_ms, cdp_endpoint=cdp_endpoint)
        item_id = extract_item_id_from_url(url) or f"detail_{index}"
        output_path = target_dir / f"{item_id}.html"
        output_path.write_text(html, encoding="utf-8")
        rows.append(
            {
                "item_id": item_id,
                "url": url,
                "path": str(output_path),
            }
        )
    return rows


def extract_item_id_from_url(url: str) -> str | None:
    parsed = httpx.URL(url)
    item_id = parsed.params.get("id") or parsed.params.get("itemId")
    return str(item_id) if item_id else None


def main() -> None:
    args = parse_args()
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    meta: dict[str, Any] = {"label": args.label or output_path.stem}
    cookie_domains = args.cookie_domains or default_cookie_domains(url=args.url, platform=args.platform)
    effective_cookie_file = ensure_cookie_file(
        cookie_file=args.cookie_file,
        browser=args.browser,
        profile=args.profile,
        domains=cookie_domains,
        output_path=output_path,
    )
    if effective_cookie_file:
        meta["cookie_file"] = effective_cookie_file
    if args.browser:
        meta["browser"] = args.browser
        meta["profile"] = args.profile
        meta["cookie_domains"] = cookie_domains
    if args.cdp_endpoint:
        meta["cdp_endpoint"] = args.cdp_endpoint

    if args.snapshot_file:
        snapshot_path = Path(args.snapshot_file)
        html = snapshot_path.read_text(encoding="utf-8", errors="ignore")
        meta["capture_mode"] = "rendered_snapshot_file"
        meta["snapshot_file"] = str(snapshot_path)
    elif args.url and args.rendered_via_browser:
        html = capture_rendered_html(
            args.url,
            effective_cookie_file,
            args.wait_ms,
            cdp_endpoint=args.cdp_endpoint,
        )
        meta["capture_mode"] = "rendered_browser"
        meta["url"] = args.url
        meta["wait_ms"] = args.wait_ms
    elif args.url:
        cookies = load_cookie_map(effective_cookie_file)
        response = httpx.get(
            args.url,
            headers=DEFAULT_HEADERS,
            cookies=cookies or None,
            timeout=30,
            follow_redirects=True,
        )
        response.raise_for_status()
        html = response.text
        meta["capture_mode"] = "live_fetch"
        meta["url"] = str(response.url)
        meta["status_code"] = response.status_code
        meta["cookie_names"] = sorted(cookies.keys())
    else:
        raise ValueError("Either --url or --snapshot-file is required")

    output_path.write_text(html, encoding="utf-8")

    if args.meta_output:
        meta_path = Path(args.meta_output)
        meta_path.parent.mkdir(parents=True, exist_ok=True)
        meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

    if args.capture_detail_pages_from_snapshot:
        if not args.platform:
            raise ValueError("--platform is required when --capture-detail-pages-from-snapshot is set")
        if not args.query_text:
            raise ValueError("--query-text is required when --capture-detail-pages-from-snapshot is set")
        if not args.detail_output_dir:
            raise ValueError("--detail-output-dir is required when --capture-detail-pages-from-snapshot is set")
        detail_urls = extract_listing_urls_from_snapshot(
            platform=args.platform,
            query_text=args.query_text,
            html=html,
            limit=args.detail_limit,
        )
        detail_rows = capture_detail_pages(
            urls=detail_urls,
            cookie_file=effective_cookie_file,
            wait_ms=args.wait_ms,
            output_dir=args.detail_output_dir,
            cdp_endpoint=args.cdp_endpoint,
        )
        if args.detail_meta_output:
            detail_meta_path = Path(args.detail_meta_output)
            detail_meta_path.parent.mkdir(parents=True, exist_ok=True)
            detail_meta_path.write_text(
                json.dumps(
                    {
                        "platform": args.platform,
                        "query_text": args.query_text,
                        "detail_count": len(detail_rows),
                        "items": detail_rows,
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )

    print(f"Saved fixture: {output_path}")


if __name__ == "__main__":
    main()
