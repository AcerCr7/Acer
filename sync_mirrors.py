#!/usr/bin/env python3
"""Keep mirrored bot files in sync automatically.

Source of truth: repository root files.
Mirrors:
- *.clean.py backups
- fresh_showdown_bot/* copies
"""

from __future__ import annotations

from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parent
FRESH = ROOT / "fresh_showdown_bot"

MIRRORS = {
    ROOT / "bot.py": [ROOT / "bot.clean.py", FRESH / "bot.py", FRESH / "bot.clean.py"],
    ROOT / "run_bot.py": [ROOT / "run_bot.clean.py", FRESH / "run_bot.py", FRESH / "run_bot.clean.py"],
    ROOT / "start_bot.bat": [ROOT / "start_bot.clean.bat", FRESH / "start_bot.bat", FRESH / "start_bot.clean.bat"],
    ROOT / "run_bot.bat": [ROOT / "run_bot.clean.bat", FRESH / "run_bot.bat", FRESH / "run_bot.clean.bat"],
    ROOT / "requirements.txt": [FRESH / "requirements.txt"],
    ROOT / "recover_and_run.py": [FRESH / "recover_and_run.py"],
}


def main() -> int:
    for src, targets in MIRRORS.items():
        if not src.exists():
            raise FileNotFoundError(f"Missing source file: {src}")
        for dst in targets:
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(src, dst)
    print("Mirror files synced.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
