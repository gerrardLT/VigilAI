"""
Launch Chrome or Edge with a remote debugging port for fixture capture workflows.

Examples:
  python app/backend/scripts/launch_chromium_debug.py --browser chrome --profile Default --url https://www.goofish.com
  python app/backend/scripts/launch_chromium_debug.py --browser chrome --port 9222 --check-only
"""

from __future__ import annotations

import argparse
from pathlib import Path
import socket
import subprocess
import sys
import time


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Launch Chromium with remote debugging enabled.")
    parser.add_argument("--browser", choices=["chrome", "edge"], default="chrome")
    parser.add_argument("--profile", default="Default", help="Profile directory name, for example Default or Profile 1.")
    parser.add_argument("--port", type=int, default=9222, help="Remote debugging port.")
    parser.add_argument("--url", action="append", default=[], help="Optional URL to open. May be passed multiple times.")
    parser.add_argument("--browser-path", help="Explicit browser executable path.")
    parser.add_argument("--user-data-dir", help="Explicit Chromium user data directory.")
    parser.add_argument("--check-only", action="store_true", help="Only report whether the debugging endpoint is ready.")
    return parser.parse_args()


def default_user_data_dir(browser: str) -> Path:
    local = Path.home() / "AppData" / "Local"
    if browser == "chrome":
        return local / "Google" / "Chrome" / "User Data"
    return local / "Microsoft" / "Edge" / "User Data"


def candidate_browser_paths(browser: str) -> list[Path]:
    program_files = [
        Path("C:/Program Files"),
        Path("C:/Program Files (x86)"),
    ]
    suffixes = {
        "chrome": [Path("Google/Chrome/Application/chrome.exe")],
        "edge": [Path("Microsoft/Edge/Application/msedge.exe")],
    }[browser]
    candidates: list[Path] = []
    for root in program_files:
        for suffix in suffixes:
            candidates.append(root / suffix)
    return candidates


def resolve_browser_path(browser: str, explicit_path: str | None = None) -> Path:
    if explicit_path:
        path = Path(explicit_path)
        if not path.exists():
            raise FileNotFoundError(f"Browser executable not found: {path}")
        return path
    for candidate in candidate_browser_paths(browser):
        if candidate.exists():
            return candidate
    raise FileNotFoundError(f"Could not find {browser} executable in standard install locations.")


def is_debug_endpoint_ready(port: int, timeout_seconds: float = 0.4) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(timeout_seconds)
        try:
            sock.connect(("127.0.0.1", port))
        except OSError:
            return False
    return True


def build_launch_command(
    *,
    browser_path: Path,
    user_data_dir: Path,
    profile: str,
    port: int,
    urls: list[str],
) -> list[str]:
    command = [
        str(browser_path),
        f"--remote-debugging-port={port}",
        f"--user-data-dir={user_data_dir}",
        f"--profile-directory={profile}",
    ]
    command.extend(urls)
    return command


def launch_debug_browser(
    *,
    browser: str,
    profile: str,
    port: int,
    urls: list[str],
    browser_path: str | None = None,
    user_data_dir: str | None = None,
) -> tuple[bool, list[str]]:
    if is_debug_endpoint_ready(port):
        return False, []

    resolved_browser = resolve_browser_path(browser, browser_path)
    resolved_user_data_dir = Path(user_data_dir) if user_data_dir else default_user_data_dir(browser)
    command = build_launch_command(
        browser_path=resolved_browser,
        user_data_dir=resolved_user_data_dir,
        profile=profile,
        port=port,
        urls=urls,
    )
    creationflags = getattr(subprocess, "DETACHED_PROCESS", 0) | getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
    subprocess.Popen(command, creationflags=creationflags)
    return True, command


def main() -> None:
    args = parse_args()

    if args.check_only:
        ready = is_debug_endpoint_ready(args.port)
        print(f"ready={str(ready).lower()} endpoint=http://127.0.0.1:{args.port}")
        raise SystemExit(0 if ready else 1)

    launched, command = launch_debug_browser(
        browser=args.browser,
        profile=args.profile,
        port=args.port,
        urls=args.url,
        browser_path=args.browser_path,
        user_data_dir=args.user_data_dir,
    )

    endpoint = f"http://127.0.0.1:{args.port}"
    if launched:
        for _ in range(20):
            if is_debug_endpoint_ready(args.port):
                break
            time.sleep(0.5)
        print(f"Launched {args.browser} with remote debugging: {endpoint}")
        if command:
            print("Command:", " ".join(command))
    else:
        print(f"Remote debugging endpoint already ready: {endpoint}")


if __name__ == "__main__":
    main()
