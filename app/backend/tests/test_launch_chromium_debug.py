from __future__ import annotations

from pathlib import Path
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts import launch_chromium_debug  # noqa: E402


def test_build_launch_command_includes_debugging_profile_and_url():
    command = launch_chromium_debug.build_launch_command(
        browser_path=Path("C:/Program Files/Google/Chrome/Application/chrome.exe"),
        user_data_dir=Path("C:/Users/test/AppData/Local/Google/Chrome/User Data"),
        profile="Profile 1",
        port=9333,
        urls=["https://www.goofish.com/search?keyword=Mate%20X6"],
    )

    assert command[1:] == [
        "--remote-debugging-port=9333",
        "--user-data-dir=C:\\Users\\test\\AppData\\Local\\Google\\Chrome\\User Data",
        "--profile-directory=Profile 1",
        "https://www.goofish.com/search?keyword=Mate%20X6",
    ]
    assert command[0].endswith("Chrome\\Application\\chrome.exe")


def test_launch_debug_browser_is_noop_when_endpoint_ready(monkeypatch):
    monkeypatch.setattr(launch_chromium_debug, "is_debug_endpoint_ready", lambda port: True)

    launched, command = launch_chromium_debug.launch_debug_browser(
        browser="chrome",
        profile="Default",
        port=9222,
        urls=[],
    )

    assert launched is False
    assert command == []


def test_launch_debug_browser_spawns_process_when_endpoint_missing(monkeypatch, tmp_path):
    fake_browser = tmp_path / "chrome.exe"
    fake_browser.write_text("", encoding="utf-8")
    recorded: dict[str, object] = {}

    monkeypatch.setattr(launch_chromium_debug, "is_debug_endpoint_ready", lambda port: False)
    monkeypatch.setattr(launch_chromium_debug, "resolve_browser_path", lambda browser, explicit_path=None: fake_browser)

    class FakeSubprocess:
        DETACHED_PROCESS = 0x8
        CREATE_NEW_PROCESS_GROUP = 0x200

        @staticmethod
        def Popen(command, creationflags=0):
            recorded["command"] = command
            recorded["creationflags"] = creationflags
            return None

    monkeypatch.setattr(launch_chromium_debug, "subprocess", FakeSubprocess)

    launched, command = launch_chromium_debug.launch_debug_browser(
        browser="chrome",
        profile="Default",
        port=9222,
        urls=["https://s.taobao.com/search?q=test"],
        user_data_dir="C:/Users/test/AppData/Local/Google/Chrome/User Data",
    )

    assert launched is True
    assert command == recorded["command"]
    assert "--remote-debugging-port=9222" in command
    assert "--profile-directory=Default" in command
    assert "https://s.taobao.com/search?q=test" in command
    assert recorded["creationflags"] == FakeSubprocess.DETACHED_PROCESS | FakeSubprocess.CREATE_NEW_PROCESS_GROUP


def test_resolve_browser_path_raises_for_missing_explicit_path():
    with pytest.raises(FileNotFoundError):
        launch_chromium_debug.resolve_browser_path("chrome", "C:/missing/chrome.exe")
