# Product Selection Logged-in Fixture Workflow

Goal: capture real Taobao / Goofish search-result pages as reusable fixtures for adapter regression tests.

This is the production path we want:

1. export a logged-in cookie JSON
2. capture a rendered DOM snapshot
3. save the fixture under `app/backend/tests/fixtures/product_selection/`
4. assert that public shell fixtures still fall back, while logged-in fixtures produce stronger extracted evidence

There are now two practical capture paths:

1. attach to an existing logged-in Chrome session through a CDP endpoint
2. export cookies and replay them into HTTP or headless-browser capture

## Recommended order

1. existing logged-in Chrome via CDP
2. manual DevTools cookie export
3. rendered DOM capture
4. optional automatic Chromium cookie export after the browser is closed

Why this order:

- public HTML is often only a CSR shell
- rendered DOM is closer to what the adapter actually needs
- Chrome often locks the `Cookies` SQLite while the browser is running

## Option A: attach to your existing logged-in Chrome

This is the preferred path when you already have Taobao or Goofish open in Chrome and do not want to keep saving HTML manually.

Start Chrome once with remote debugging enabled:

```text
"C:\Program Files\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222
```

The repo now includes a helper for this:

```bash
python app/backend/scripts/launch_chromium_debug.py ^
  --browser chrome ^
  --profile Default ^
  --port 9222 ^
  --url "https://www.goofish.com/search?keyword=Mate%20X6"
```

It will:

- detect whether `http://127.0.0.1:9222` is already live
- launch Chrome or Edge only when needed
- open an optional URL in the debug-enabled browser session

Then capture directly from the live logged-in browser session:

```bash
python app/backend/scripts/product_selection_capture_fixture.py ^
  --url "https://www.goofish.com/search?keyword=Mate%20X6" ^
  --rendered-via-browser ^
  --cdp-endpoint http://127.0.0.1:9222 ^
  --wait-ms 5000 ^
  --output app/backend/tests/fixtures/product_selection/goofish_logged_in_browser_rendered_search.html ^
  --meta-output app/backend/tests/fixtures/product_selection/goofish_logged_in_browser_rendered_search.meta.json ^
  --label goofish_logged_in_browser_rendered_search
```

What this does:

- attaches Playwright to the existing Chrome session
- reuses the logged-in browser context instead of replaying cookies into a fresh browser
- saves the rendered DOM that the adapter actually sees

Important:

- if your current Chrome was not started with a remote debugging port, the helper can start one for you
- if another non-debug Chrome instance is already holding the same profile, you may need to close it first so the debug-enabled launch can take over that logged-in profile cleanly

If you also want detail pages from the same logged-in session, add:

```bash
  --capture-detail-pages-from-snapshot ^
  --platform xianyu ^
  --query-text "Mate X6" ^
  --detail-limit 5 ^
  --detail-output-dir app/backend/tests/fixtures/product_selection/goofish_detail_pages
```

## Option B: manual cookie JSON export

Use this first to get the pipeline moving.

1. Open the logged-in search page in Chrome or Edge
2. Open DevTools
3. Go to `Application` -> `Storage` -> `Cookies`
4. Select the target domain, for example:
   - `https://s.taobao.com`
   - `https://2.taobao.com`
   - `https://www.goofish.com`
5. Export cookies to JSON, for example:

```text
C:\temp\taobao-cookies.json
```

Accepted JSON shapes:

- `{"cookies": [{"name": "...", "value": "...", "domain": "..."}]}`
- `[{"name": "...", "value": "...", "domain": "..."}]`
- `{"cookie_name": "cookie_value"}`

## Option C: save a rendered DOM snapshot

This is the more valuable fixture form because the adapter already accepts `rendered_snapshot_html`.

Prefer the rendered DOM, not `View Source`.

Ways to capture it:

1. In DevTools Elements, copy `document.documentElement.outerHTML`
2. In the console:

```js
copy(document.documentElement.outerHTML)
```

3. Save it as:

```text
C:\temp\taobao-rendered-search.html
```

If the page uses lazy loading, scroll the result area first, then export the DOM.

## Use the repo script to generate fixtures

### 1. From a saved rendered snapshot

```bash
python app/backend/scripts/product_selection_capture_fixture.py ^
  --snapshot-file C:\temp\taobao-rendered-search.html ^
  --output app/backend/tests/fixtures/product_selection/taobao_logged_in_rendered_search.html ^
  --meta-output app/backend/tests/fixtures/product_selection/taobao_logged_in_rendered_search.meta.json ^
  --label taobao_logged_in_rendered_search
```

### 2. From live HTTP fetch plus cookie JSON

```bash
python app/backend/scripts/product_selection_capture_fixture.py ^
  --url "https://s.taobao.com/search?q=%E5%AE%A0%E7%89%A9%E9%A5%AE%E6%B0%B4%E6%9C%BA" ^
  --cookie-file C:\temp\taobao-cookies.json ^
  --output app/backend/tests/fixtures/product_selection/taobao_logged_in_http_search.html ^
  --meta-output app/backend/tests/fixtures/product_selection/taobao_logged_in_http_search.meta.json ^
  --label taobao_logged_in_http_search
```

### 3. From a rendered browser session plus cookie JSON

This is the best path for CSR-heavy marketplace pages.

```bash
python app/backend/scripts/product_selection_capture_fixture.py ^
  --url "https://s.taobao.com/search?q=%E5%AE%A0%E7%89%A9%E9%A5%AE%E6%B0%B4%E6%9C%BA" ^
  --cookie-file C:\temp\taobao-cookies.json ^
  --rendered-via-browser ^
  --wait-ms 5000 ^
  --output app/backend/tests/fixtures/product_selection/taobao_logged_in_rendered_search.html ^
  --meta-output app/backend/tests/fixtures/product_selection/taobao_logged_in_rendered_search.meta.json ^
  --label taobao_logged_in_rendered_search
```

If this still produces a shell page, the problem is usually one of:

- incomplete cookies
- insufficient logged-in state
- more wait time or scrolling is required
- the platform moved listing data into later API calls

### 4. From a rendered browser session attached to existing Chrome

```bash
python app/backend/scripts/product_selection_capture_fixture.py ^
  --url "https://s.taobao.com/search?q=%E5%AE%A0%E7%89%A9%E9%A5%AE%E6%B0%B4%E6%9C%BA" ^
  --rendered-via-browser ^
  --cdp-endpoint http://127.0.0.1:9222 ^
  --wait-ms 8000 ^
  --output app/backend/tests/fixtures/product_selection/taobao_logged_in_rendered_search.html ^
  --meta-output app/backend/tests/fixtures/product_selection/taobao_logged_in_rendered_search.meta.json ^
  --label taobao_logged_in_rendered_search
```

## Batch capture detail pages from a saved search snapshot

Once you already have a rendered search snapshot, you can now let the repo script extract listing URLs and batch-capture detail pages.

Example for Goofish:

```bash
python app/backend/scripts/product_selection_capture_fixture.py ^
  --snapshot-file docs/goofish-rendered-search.html ^
  --output app/backend/tests/fixtures/product_selection/goofish_logged_in_huawei_search.html ^
  --platform xianyu ^
  --query-text "huawei" ^
  --cookie-file C:\temp\goofish-cookies.json ^
  --capture-detail-pages-from-snapshot ^
  --detail-limit 5 ^
  --detail-output-dir app/backend/tests/fixtures/product_selection/goofish_detail_pages ^
  --detail-meta-output app/backend/tests/fixtures/product_selection/goofish_detail_pages.manifest.json
```

What this does:

- copies the saved rendered search snapshot into a stable fixture path
- extracts up to `--detail-limit` matching listing URLs using the live adapter
- opens each listing page in a rendered browser session
- writes one detail HTML file per item id
- writes a manifest JSON listing item id, URL, and saved file path

This is the preferred next step when moving from one-off real fixtures toward repeatable logged-in regression coverage.

## Feed a detail manifest directly into research-jobs

Once the manifest exists, you no longer need to manually collect `detail_snapshot_htmls`.

Example request body:

```json
{
  "query_type": "keyword",
  "query_text": "Mate X6",
  "platform_scope": "xianyu",
  "rendered_snapshot_path": "docs/goofish-rendered-search.html",
  "detail_snapshot_manifest_path": "app/backend/tests/fixtures/product_selection/goofish_detail_pages.manifest.json"
}
```

The backend will:

- load the rendered search snapshot from `rendered_snapshot_path`
- load each detail HTML path listed under `items[*].path`
- merge matching detail fields into the live search candidates
- score and persist the enriched opportunities as a normal research job

## Automatic Chromium cookie export

The repo already includes a helper:

```bash
python app/backend/scripts/export_chromium_cookies.py ^
  --browser chrome ^
  --profile Default ^
  --domains taobao.com,2.taobao.com ^
  --output C:\temp\taobao-cookies.json
```

On Windows, this may fail if the browser still holds an exclusive lock on the cookie database.

Current recommendation:

1. use `--cdp-endpoint` first when you want to reuse the actual logged-in Chrome session
2. use manual DevTools export when CDP is not available
3. use the automatic export only after closing Chrome

## Current real-world limits

- automatic Chromium cookie export can fail while Chrome still holds the cookie SQLite lock
- on some Windows setups, `browser_cookie3` fallback needs elevated filesystem access
- real Taobao rendered pages may return an anti-bot challenge instead of listing cards
- the backend now classifies those fixtures as `captcha_challenge`, not generic `search_shell_only`

## Backend environment variables

If you want the live adapter to read a default cookie file:

```env
PRODUCT_SELECTION_BROWSER_COOKIES_PATH=C:\temp\taobao-cookies.json
PRODUCT_SELECTION_LIVE_COOKIE_DOMAINS=taobao.com,goofish.com,2.taobao.com
```

## Fixture naming

- `taobao_search_pet_water_fountain.html`
  - public shell fixture
- `taobao_logged_in_rendered_search.html`
  - logged-in rendered DOM fixture
- `taobao_logged_in_http_search.html`
  - logged-in HTTP fetch fixture
- `goofish_logged_in_rendered_search.html`
  - Goofish logged-in rendered DOM fixture

Keep public shell fixtures separate from logged-in fixtures so regression intent stays obvious.

## Verification

Backend:

```bash
cd app/backend
pytest tests/test_product_selection_agent_tools.py tests/test_product_selection_api.py tests/test_product_selection_repository.py -q
```

Frontend:

```bash
cd app/frontend
npm test -- SelectionOpportunitiesPage.test.tsx SelectionWorkspacePage.test.tsx SelectionTrackingPage.test.tsx
```

## What the next real regression should assert

Once a true logged-in fixture exists, the next assertions should be stronger than "not a shell page".

Prefer checks like:

- at least one accepted listing
- `source_mode == "live"`
- at least part of the listings expose:
  - `price_low`
  - `sales_volume`
  - `seller_count`
  - `seller_type`

If a real Taobao rendered fixture yields `captcha_challenge`, that is still a valid regression artifact. It means the platform served an anti-bot wall instead of accessible listings, and the adapter should preserve that distinction.

If a logged-in fixture still only yields `search_shell_only`, the issue is not the test. It is the page structure, session state, or capture path.
