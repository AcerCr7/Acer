#!/usr/bin/env python3
"""Simple launcher for the all-in-one Pokemon Showdown bot.

This launcher can auto-install required dependencies if missing.
If SHOWDOWN_USERNAME is not set, it prompts for it interactively.
"""

import asyncio
import os
from pathlib import Path
import shutil
import subprocess
import sys

REQUIRED_PACKAGES = ("aiohttp", "websockets")
DEFAULT_SHOWDOWN_USERNAME = "YoisAcer"
DEFAULT_SHOWDOWN_PASSWORD = "Kingdaman"


def _clean_credential(value: str) -> str:
    value = value.strip()
    while len(value) >= 2 and ((value[0] == '"' and value[-1] == '"') or (value[0] == "'" and value[-1] == "'")):
        value = value[1:-1].strip()
    return value


def _looks_like_diff_corruption(path: Path) -> bool:
    if not path.exists():
        return False
    head = path.read_text(errors="ignore").splitlines()[:8]
    markers = ("diff --git", "index ", "--- ", "+++ ", "@@ ")
    return any(line.strip().startswith(markers) for line in head)


def _self_heal_python_sources() -> None:
    root = Path(__file__).resolve().parent
    repairs = [
        (root / "bot.py", root / "bot.clean.py"),
    ]
    for live, clean in repairs:
        if _looks_like_diff_corruption(live) and clean.exists():
            shutil.copyfile(clean, live)
            print(f"Auto-repaired corrupted file: {live.name}")


def _ensure_dependencies() -> None:
    missing = []
    for pkg in REQUIRED_PACKAGES:
        try:
            __import__(pkg)
        except ModuleNotFoundError:
            missing.append(pkg)

    if not missing:
        return

    print(f"Missing packages detected: {', '.join(missing)}")
    print("Installing with pip...")
    cmd = [sys.executable, "-m", "pip", "install", *missing]
    subprocess.check_call(cmd)


def _ensure_username() -> None:
    username = os.getenv("SHOWDOWN_USERNAME", "")
    if not username:
        username = DEFAULT_SHOWDOWN_USERNAME
        print(f"SHOWDOWN_USERNAME not set. Using default: {DEFAULT_SHOWDOWN_USERNAME}")
    username = _clean_credential(username)
    if not username:
        raise RuntimeError("SHOWDOWN_USERNAME is empty after removing quotes.")
    os.environ["SHOWDOWN_USERNAME"] = username

    password = os.getenv("SHOWDOWN_PASSWORD", "")
    if not password:
        password = DEFAULT_SHOWDOWN_PASSWORD
        print("SHOWDOWN_PASSWORD not set. Using configured default password.")
    os.environ["SHOWDOWN_PASSWORD"] = _clean_credential(password)


def main() -> int:
    _self_heal_python_sources()
    _ensure_dependencies()
    _ensure_username()
    from bot import main as bot_main

    asyncio.run(bot_main())
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        pass
