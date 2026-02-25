Fresh standalone folder for the Pokemon Showdown bot.

Zero-effort run (Windows):
  1) Open this folder
  2) Double-click `start_bot.bat`

What `start_bot.bat` does automatically:
  - syncs all mirrored files (`*.clean.py`, `*.clean.bat`, and `fresh_showdown_bot/*`) from root sources
  - self-heals `run_bot.py`, `bot.py`, and launcher .bat files if they were corrupted by pasted git diff text
  - creates a local `.venv` if missing
  - installs/upgrades required dependencies from `requirements.txt`
  - starts the bot

Important:
  - Do not paste git diff output (lines like `+++`, `---`, `index`) directly into CMD.
  - If files were corrupted, just run `start_bot.bat` again and it will repair them.

Default login configured in launcher:
  SHOWDOWN_USERNAME=YoisAcer
  SHOWDOWN_PASSWORD=Kingdaman

Optional environment variables:
  SHOWDOWN_TARGET
  SHOWDOWN_FORMAT (default: gen9ou)
  SHOWDOWN_SERVER (default: sim3.psim.us)
  SHOWDOWN_TEAM

Emergency manual recovery (if run_bot.py is corrupted):
  py -3.11 recover_and_run.py
