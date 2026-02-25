#!/usr/bin/env python3
"""Emergency recovery launcher.

Use this if run_bot.py or bot.py were overwritten with pasted git diff text.
It restores files from clean backups, then runs run_bot.py.
"""

from __future__ import annotations

from pathlib import Path
import shutil
import subprocess
import sys


def _looks_like_diff(path: Path) -> bool:
    if not path.exists():
        return False
    head = path.read_text(errors="ignore").splitlines()[:12]
    markers = ("diff --git", "index ", "--- ", "+++ ", "@@ ")
    return any(line.strip().startswith(markers) for line in head)


def _repair(root: Path) -> None:
    pairs = [
        (root / "run_bot.py", root / "run_bot.clean.py"),
        (root / "bot.py", root / "bot.clean.py"),
    ]
    for live, clean in pairs:
        if _looks_like_diff(live):
            if not clean.exists():
                raise FileNotFoundError(f"Missing clean backup for repair: {clean}")
            shutil.copyfile(clean, live)
            print(f"Repaired: {live.name} (from {clean.name})")


def main() -> int:
    root = Path(__file__).resolve().parent
    _repair(root)
    cmd = [sys.executable, str(root / "run_bot.py")]
    return subprocess.call(cmd)


if __name__ == "__main__":
    raise SystemExit(main())
