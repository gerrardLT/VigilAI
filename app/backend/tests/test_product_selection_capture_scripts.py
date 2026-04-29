from __future__ import annotations

import json
import os
from pathlib import Path
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts import product_selection_capture_fixture as capture_fixture  # noqa: E402
from scripts import export_chromium_cookies  # noqa: E402


def test_load_cookie_rows_accepts_plain_cookie_map(tmp_path):
    cookie_file = tmp_path / "cookies.json"
    cookie_file.write_text(
        json.dumps({"sessionid": "abc123", "sid": "xyz"}),
        encoding="utf-8",
    )

    rows = capture_fixture.load_cookie_rows(str(cookie_file))

    assert rows == [
        {"name": "sessionid", "value": "abc123"},
        {"name": "sid", "value": "xyz"},
    ]


def test_default_cookie_domains_prefers_platform_and_url():
    assert capture_fixture.default_cookie_domains(
        url="https://www.goofish.com/search?q=huawei",
        platform=None,
    ) == "goofish.com,2.taobao.com,taobao.com"
    assert capture_fixture.default_cookie_domains(
        url="https://s.taobao.com/search?q=test",
        platform=None,
    ) == "taobao.com,2.taobao.com,goofish.com"
    assert capture_fixture.default_cookie_domains(
        url=None,
        platform="xianyu",
    ) == "goofish.com,2.taobao.com,taobao.com"


def test_ensure_cookie_file_exports_from_browser_profile(tmp_path, monkeypatch):
    output_path = tmp_path / "fixture.html"

    monkeypatch.setattr(
        capture_fixture,
        "export_browser_cookies",
        lambda **kwargs: [
            {
                "domain": ".taobao.com",
                "name": "sessionid",
                "value": "abc123",
                "path": "/",
                "expires_utc": 0,
                "secure": True,
                "httpOnly": False,
            }
        ],
    )

    cookie_file = capture_fixture.ensure_cookie_file(
        cookie_file=None,
        browser="chrome",
        profile="Default",
        domains="taobao.com,2.taobao.com",
        output_path=output_path,
    )

    assert cookie_file is not None
    payload = json.loads(Path(cookie_file).read_text(encoding="utf-8"))
    assert payload["browser"] == "chrome"
    assert payload["profile"] == "Default"
    assert payload["domains"] == "taobao.com,2.taobao.com"
    assert payload["cookies"][0]["name"] == "sessionid"


def test_export_cookies_prefers_dpapi_then_browser_cookie3(monkeypatch):
    monkeypatch.setattr(
        export_chromium_cookies,
        "export_cookies_via_dpapi",
        lambda **kwargs: [],
    )
    monkeypatch.setattr(
        export_chromium_cookies,
        "export_cookies_via_browser_cookie3",
        lambda **kwargs: [{"name": "sid", "value": "x", "domain": ".taobao.com", "path": "/"}],
    )

    rows = export_chromium_cookies.export_cookies(
        browser="chrome",
        profile="Default",
        domains="taobao.com",
        strategy="browser_cookie3",
    )

    assert rows == [{"name": "sid", "value": "x", "domain": ".taobao.com", "path": "/"}]


def test_to_playwright_cookies_filters_non_matching_domains():
    cookies = capture_fixture._to_playwright_cookies(
        "https://s.taobao.com/search?q=test",
        [
            {"name": "sessionid", "value": "abc123", "domain": ".taobao.com", "path": "/"},
            {"name": "ignored", "value": "zzz", "domain": ".example.com", "path": "/"},
            {"name": "local", "value": "vvv"},
        ],
    )

    assert cookies == [
        {
            "name": "sessionid",
            "value": "abc123",
            "path": "/",
            "httpOnly": False,
            "secure": True,
            "sameSite": "Lax",
            "domain": ".taobao.com",
        },
        {
            "name": "local",
            "value": "vvv",
            "httpOnly": False,
            "secure": True,
            "sameSite": "Lax",
            "url": "https://s.taobao.com",
        },
    ]


def test_capture_rendered_html_uses_playwright_context_and_cookies(tmp_path, monkeypatch):
    cookie_file = tmp_path / "cookies.json"
    cookie_file.write_text(
        json.dumps(
            {
                "cookies": [
                    {"name": "sessionid", "value": "abc123", "domain": ".taobao.com", "path": "/"}
                ]
            }
        ),
        encoding="utf-8",
    )

    recorded: dict[str, object] = {}

    class FakePage:
        def goto(self, url: str, wait_until: str, timeout: int) -> None:
            recorded["goto"] = {"url": url, "wait_until": wait_until, "timeout": timeout}

        def wait_for_timeout(self, wait_ms: int) -> None:
            recorded["wait_ms"] = wait_ms

        def content(self) -> str:
            return "<html><body>rendered</body></html>"

    class FakeContext:
        def add_cookies(self, cookies: list[dict[str, object]]) -> None:
            recorded["cookies"] = cookies

        def new_page(self) -> FakePage:
            return FakePage()

        def close(self) -> None:
            recorded["context_closed"] = True

    class FakeBrowser:
        def new_context(self, **kwargs) -> FakeContext:
            recorded["context_options"] = kwargs
            return FakeContext()

        def close(self) -> None:
            recorded["browser_closed"] = True

    class FakeChromium:
        def launch(self, headless: bool) -> FakeBrowser:
            recorded["headless"] = headless
            return FakeBrowser()

    class FakePlaywright:
        chromium = FakeChromium()

    class FakeManager:
        def __enter__(self) -> FakePlaywright:
            return FakePlaywright()

        def __exit__(self, exc_type, exc, tb) -> None:
            return None

    monkeypatch.setattr(capture_fixture, "sync_playwright", lambda: FakeManager())

    html = capture_fixture.capture_rendered_html(
        "https://s.taobao.com/search?q=test",
        str(cookie_file),
        5000,
    )

    assert html == "<html><body>rendered</body></html>"
    assert recorded["headless"] is True
    assert recorded["context_options"] == {
        "user_agent": capture_fixture.DEFAULT_HEADERS["user-agent"],
        "locale": "zh-CN",
    }
    assert recorded["goto"] == {
        "url": "https://s.taobao.com/search?q=test",
        "wait_until": "domcontentloaded",
        "timeout": 30000,
    }
    assert recorded["wait_ms"] == 5000
    assert recorded["cookies"] == [
        {
            "name": "sessionid",
            "value": "abc123",
            "path": "/",
            "httpOnly": False,
            "secure": True,
            "sameSite": "Lax",
            "domain": ".taobao.com",
        }
    ]
    assert recorded["context_closed"] is True
    assert recorded["browser_closed"] is True


def test_capture_rendered_html_can_attach_to_existing_cdp_browser(monkeypatch):
    recorded: dict[str, object] = {}

    class FakePage:
        def goto(self, url: str, wait_until: str, timeout: int) -> None:
            recorded["goto"] = {"url": url, "wait_until": wait_until, "timeout": timeout}

        def wait_for_timeout(self, wait_ms: int) -> None:
            recorded["wait_ms"] = wait_ms

        def content(self) -> str:
            return "<html><body>attached</body></html>"

        def close(self) -> None:
            recorded["page_closed"] = True

    class FakeContext:
        def new_page(self) -> FakePage:
            recorded["new_page"] = True
            return FakePage()

    class FakeBrowser:
        contexts = [FakeContext()]

        def close(self) -> None:
            recorded["browser_closed"] = True

    class FakeChromium:
        def connect_over_cdp(self, endpoint: str) -> FakeBrowser:
            recorded["cdp_endpoint"] = endpoint
            return FakeBrowser()

    class FakePlaywright:
        chromium = FakeChromium()

    class FakeManager:
        def __enter__(self) -> FakePlaywright:
            return FakePlaywright()

        def __exit__(self, exc_type, exc, tb) -> None:
            return None

    monkeypatch.setattr(capture_fixture, "sync_playwright", lambda: FakeManager())

    html = capture_fixture.capture_rendered_html(
        "https://www.goofish.com/search?keyword=huawei",
        None,
        2500,
        cdp_endpoint="http://127.0.0.1:9222",
    )

    assert html == "<html><body>attached</body></html>"
    assert recorded["cdp_endpoint"] == "http://127.0.0.1:9222"
    assert recorded["goto"] == {
        "url": "https://www.goofish.com/search?keyword=huawei",
        "wait_until": "domcontentloaded",
        "timeout": 30000,
    }
    assert recorded["wait_ms"] == 2500
    assert recorded["page_closed"] is True
    assert recorded["browser_closed"] is True


def test_extract_listing_urls_from_goofish_snapshot():
    fixture = (
        Path(__file__).parent
        / "fixtures"
        / "product_selection"
        / "goofish_logged_in_huawei_search.html"
    )
    html = fixture.read_text(encoding="utf-8", errors="ignore")

    urls = capture_fixture.extract_listing_urls_from_snapshot(
        platform="xianyu",
        query_text="huawei",
        html=html,
        limit=3,
    )

    assert len(urls) == 3
    assert all(url.startswith("https://www.goofish.com/item?id=") for url in urls)


def test_capture_detail_pages_writes_html_and_manifest_rows(tmp_path, monkeypatch):
    recorded: list[tuple[str, str | None, int]] = []

    def fake_capture_rendered_html(
        url: str,
        cookie_file: str | None,
        wait_ms: int,
        *,
        cdp_endpoint: str | None = None,
    ) -> str:
        recorded.append((url, cookie_file, wait_ms))
        return f"<html><body>{url}</body></html>"

    monkeypatch.setattr(capture_fixture, "capture_rendered_html", fake_capture_rendered_html)

    rows = capture_fixture.capture_detail_pages(
        urls=[
            "https://www.goofish.com/item?id=1046552914070&categoryId=126862528",
            "https://www.goofish.com/item?id=1046559046467&categoryId=126862528",
        ],
        cookie_file="C:\\temp\\cookies.json",
        wait_ms=4500,
        output_dir=str(tmp_path / "details"),
    )

    assert [row["item_id"] for row in rows] == ["1046552914070", "1046559046467"]
    assert Path(rows[0]["path"]).read_text(encoding="utf-8") == (
        "<html><body>https://www.goofish.com/item?id=1046552914070&categoryId=126862528</body></html>"
    )
    assert recorded == [
        ("https://www.goofish.com/item?id=1046552914070&categoryId=126862528", "C:\\temp\\cookies.json", 4500),
        ("https://www.goofish.com/item?id=1046559046467&categoryId=126862528", "C:\\temp\\cookies.json", 4500),
    ]
