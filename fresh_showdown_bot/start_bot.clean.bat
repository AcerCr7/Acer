@echo off
setlocal
cd /d %~dp0

echo [0/7] Syncing mirrored files...
py -3 sync_mirrors.py >nul 2>nul

echo [1/7] Self-healing launcher/source files if needed...
findstr /B /C:"index " run_bot.py >nul 2>nul && copy /Y run_bot.clean.py run_bot.py >nul
findstr /B /C:"diff --git" run_bot.py >nul 2>nul && copy /Y run_bot.clean.py run_bot.py >nul
findstr /B /C:"index " bot.py >nul 2>nul && copy /Y bot.clean.py bot.py >nul
findstr /B /C:"diff --git" bot.py >nul 2>nul && copy /Y bot.clean.py bot.py >nul
findstr /B /C:"+++ " run_bot.bat >nul 2>nul && copy /Y run_bot.clean.bat run_bot.bat >nul
findstr /B /C:"+++ " start_bot.bat >nul 2>nul && copy /Y start_bot.clean.bat start_bot.bat >nul

echo [2/7] Preparing Python virtual environment...
if not exist .venv\Scripts\python.exe (
  py -3.11 -m venv .venv >nul 2>nul
)
if not exist .venv\Scripts\python.exe (
  py -3 -m venv .venv >nul 2>nul
)
if not exist .venv\Scripts\python.exe (
  echo Failed to create virtual environment. Install Python 3 and retry.
  pause
  exit /b 1
)

echo [3/7] Installing/upgrading dependencies...
.venv\Scripts\python.exe -m pip install --upgrade pip >nul
.venv\Scripts\python.exe -m pip install -r requirements.txt
if errorlevel 1 (
  echo Failed to install dependencies.
  pause
  exit /b 1
)

echo [4/7] Re-syncing mirrors after any updates...
.venv\Scripts\python.exe sync_mirrors.py >nul

echo [5/7] Running Python self-heal pass...
.venv\Scripts\python.exe run_bot.py --help >nul 2>nul

echo [6/7] Starting bot...
.venv\Scripts\python.exe run_bot.py

echo [7/7] Bot exited.
pause
endlocal
