"""
Export selected Chromium cookies into a JSON file usable by product-selection capture tools.

Windows only. Supports Chrome/Edge profiles whose cookies are encrypted with the current
user's DPAPI-protected master key.
"""

from __future__ import annotations

import argparse
import base64
from http.cookiejar import CookieJar
import json
import sqlite3
import tempfile
from pathlib import Path
import sys
from typing import Iterable

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
import win32crypt
import win32file
import win32con

try:
    import browser_cookie3
except ImportError:  # pragma: no cover
    browser_cookie3 = None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Export Chromium cookies for selected domains.")
    parser.add_argument("--browser", choices=["chrome", "edge"], default="chrome")
    parser.add_argument("--profile", default="Default")
    parser.add_argument("--domains", required=True, help="Comma-separated domains, e.g. taobao.com,goofish.com")
    parser.add_argument("--output", required=True)
    return parser.parse_args()


def browser_root(browser: str) -> Path:
    local = Path.home() / "AppData" / "Local"
    if browser == "chrome":
        return local / "Google" / "Chrome" / "User Data"
    return local / "Microsoft" / "Edge" / "User Data"


def browser_cookie_path(browser: str, profile: str) -> Path:
    return browser_root(browser) / profile / "Network" / "Cookies"


def load_master_key(root: Path) -> bytes:
    local_state = json.loads((root / "Local State").read_text(encoding="utf-8"))
    encrypted_key = base64.b64decode(local_state["os_crypt"]["encrypted_key"])
    encrypted_key = encrypted_key[5:]
    return win32crypt.CryptUnprotectData(encrypted_key, None, None, None, 0)[1]


def decrypt_cookie(encrypted_value: bytes, master_key: bytes) -> str:
    if not encrypted_value:
        return ""
    if encrypted_value[:3] in {b"v10", b"v11", b"v20"}:
        nonce = encrypted_value[3:15]
        ciphertext = encrypted_value[15:-16]
        tag = encrypted_value[-16:]
        aesgcm = AESGCM(master_key)
        decrypted = aesgcm.decrypt(nonce, ciphertext + tag, None)
        return decrypted.decode("utf-8", errors="ignore")
    try:
        return win32crypt.CryptUnprotectData(encrypted_value, None, None, None, 0)[1].decode("utf-8", errors="ignore")
    except Exception:
        return ""


def _normalize_domains(domains: str | Iterable[str]) -> list[str]:
    if isinstance(domains, str):
        values = domains.split(",")
    else:
        values = list(domains)
    return [item.strip().lower() for item in values if str(item).strip()]


def _cookie_row(
    *,
    domain: str,
    name: str,
    value: str,
    path: str = "/",
    expires_utc: int | float | None = None,
    secure: bool = False,
    http_only: bool = False,
) -> dict[str, object]:
    return {
        "domain": domain,
        "name": name,
        "value": value,
        "path": path,
        "expires_utc": expires_utc or 0,
        "secure": secure,
        "httpOnly": http_only,
    }


def export_cookies_via_dpapi(*, browser: str, profile: str, domains: str | Iterable[str]) -> list[dict[str, object]]:
    root = browser_root(browser)
    cookie_db = browser_cookie_path(browser, profile)
    if not cookie_db.exists():
        raise FileNotFoundError(f"Cookie DB not found: {cookie_db}")

    master_key = load_master_key(root)
    normalized_domains = _normalize_domains(domains)

    with tempfile.TemporaryDirectory() as tmpdir:
        temp_db = Path(tmpdir) / "Cookies"
        try:
            handle = win32file.CreateFile(
                str(cookie_db),
                win32con.GENERIC_READ,
                win32con.FILE_SHARE_READ | win32con.FILE_SHARE_WRITE | win32con.FILE_SHARE_DELETE,
                None,
                win32con.OPEN_EXISTING,
                win32con.FILE_ATTRIBUTE_NORMAL,
                None,
            )
        except Exception as exc:
            raise RuntimeError(
                "Failed to open Chromium cookie DB. Close the browser first, run elevated so browser_cookie3 can "
                "use shadow copy, or export cookies manually."
            ) from exc
        try:
            chunks: list[bytes] = []
            while True:
                _, data = win32file.ReadFile(handle, 1024 * 1024)
                if not data:
                    break
                chunks.append(data)
                if len(data) < 1024 * 1024:
                    break
        finally:
            handle.Close()
        temp_db.write_bytes(b"".join(chunks))
        conn = sqlite3.connect(temp_db)
        try:
            rows = conn.execute(
                """
                SELECT host_key, name, path, expires_utc, is_secure, is_httponly, encrypted_value
                FROM cookies
                """
            ).fetchall()
        finally:
            conn.close()

    exported: list[dict[str, object]] = []
    for host_key, name, path, expires_utc, is_secure, is_httponly, encrypted_value in rows:
        host = str(host_key or "").lstrip(".").lower()
        if not any(host.endswith(domain) for domain in normalized_domains):
            continue
        value = decrypt_cookie(encrypted_value, master_key)
        if not value:
            continue
        exported.append(
            _cookie_row(
                domain=host_key,
                name=name,
                value=value,
                path=path,
                expires_utc=expires_utc,
                secure=bool(is_secure),
                http_only=bool(is_httponly),
            )
        )
    return exported


def _iter_cookiejar_rows(cookie_jar: CookieJar) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for cookie in cookie_jar:
        rows.append(
            _cookie_row(
                domain=cookie.domain,
                name=cookie.name,
                value=cookie.value,
                path=cookie.path or "/",
                expires_utc=cookie.expires or 0,
                secure=bool(cookie.secure),
                http_only=bool("HttpOnly" in (cookie._rest or {})),
            )
        )
    return rows


def export_cookies_via_browser_cookie3(
    *,
    browser: str,
    profile: str,
    domains: str | Iterable[str],
) -> list[dict[str, object]]:
    if browser_cookie3 is None:
        raise RuntimeError("browser_cookie3 is not installed")

    normalized_domains = _normalize_domains(domains)
    root = browser_root(browser)
    cookie_file = browser_cookie_path(browser, profile)
    key_file = root / "Local State"

    rows: list[dict[str, object]] = []
    loader = browser_cookie3.chrome if browser == "chrome" else browser_cookie3.edge
    for domain in normalized_domains:
        jar = loader(cookie_file=str(cookie_file), domain_name=domain, key_file=str(key_file))
        rows.extend(_iter_cookiejar_rows(jar))

    deduped: dict[tuple[str, str, str], dict[str, object]] = {}
    for row in rows:
        deduped[(str(row["domain"]), str(row["name"]), str(row["path"]))] = row
    return list(deduped.values())


def export_cookies(
    *,
    browser: str,
    profile: str,
    domains: str | Iterable[str],
    strategy: str = "auto",
) -> list[dict[str, object]]:
    normalized_domains = _normalize_domains(domains)
    strategies = [strategy] if strategy != "auto" else ["dpapi", "browser_cookie3"]
    errors: list[str] = []
    for candidate in strategies:
        try:
            if candidate == "dpapi":
                return export_cookies_via_dpapi(browser=browser, profile=profile, domains=normalized_domains)
            if candidate == "browser_cookie3":
                return export_cookies_via_browser_cookie3(browser=browser, profile=profile, domains=normalized_domains)
            raise ValueError(f"Unsupported cookie export strategy: {candidate}")
        except Exception as exc:
            errors.append(f"{candidate}: {exc}")
    raise RuntimeError(" ; ".join(errors))


def main() -> None:
    args = parse_args()
    exported = export_cookies(
        browser=args.browser,
        profile=args.profile,
        domains=args.domains,
        strategy="auto",
    )

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps({"browser": args.browser, "profile": args.profile, "cookies": exported}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Exported {len(exported)} cookies to {output}")
    if not exported:
        print(
            "No matching cookies were exported. Confirm the profile is logged in, the target domain matches, "
            "and consider manual DevTools export if the browser session is using another profile.",
            file=sys.stderr,
        )


if __name__ == "__main__":
    main()
