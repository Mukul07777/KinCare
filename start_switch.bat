@echo off
REM KinCare on Switch: one click. Sets up KinCare (first run), starts its API, then the Recall Watcher.
REM Switch Console must be open (it runs the Switch server and the Claude Code agents).
setlocal
cd /d %~dp0

if not exist api\.venv\Scripts\python.exe (
  echo [1/3] First run: creating the Python environment...
  py -3.12 -m venv api\.venv 2>nul || python -m venv api\.venv
  if errorlevel 1 ( echo Python 3.12 not found. Install it from python.org & pause & exit /b 1 )
  api\.venv\Scripts\python -m pip install -q -r api\requirements.txt
  if errorlevel 1 ( echo Package install failed. & pause & exit /b 1 )
)
if not exist data\kincare.db (
  echo [1/3] Loading real CDSCO alerts and 246k medicine brands. A few minutes, once...
  pushd api
  .venv\Scripts\python -m ingest.fetch --limit 24
  .venv\Scripts\python -m ingest.load
  .venv\Scripts\python -m ingest.portal
  .venv\Scripts\python -m ingest.medicines
  popd
) else (
  echo [1/3] KinCare data ready
)

powershell -NoProfile -Command "try { Invoke-RestMethod http://localhost:8000/health -TimeoutSec 2 | Out-Null; exit 0 } catch { exit 1 }"
if errorlevel 1 (
  echo [2/3] Starting KinCare API on http://localhost:8000
  start "KinCare API" cmd /k "cd /d %~dp0api && .venv\Scripts\python -m uvicorn main:app --port 8000"
) else (
  echo [2/3] KinCare API already running
)

echo Waiting for the API...
:wait
powershell -NoProfile -Command "try { Invoke-RestMethod http://localhost:8000/health -TimeoutSec 2 | Out-Null; exit 0 } catch { exit 1 }"
if errorlevel 1 ( timeout /t 2 /nobreak >nul & goto wait )

if not exist switch\.env (
  copy switch\.env.example switch\.env >nul
  echo.
  echo switch\.env created. Fill SWITCH_URL and SWITCH_REGISTRATION_KEY, then run:
  echo    api\.venv\Scripts\python switch\recall_watcher.py register
  echo and add "kincare-recall-watcher" to the family room in Switch Console. Then run this file again.
  goto end
)

echo [3/3] Starting the Recall Watcher (checks the family's medicines every few minutes)
start "KinCare Recall Watcher" cmd /k "cd /d %~dp0 && api\.venv\Scripts\python switch\recall_watcher.py run"

echo.
echo KinCare is running. In Telegram, send a strip photo to the family group and @kincare-scan.
:end
endlocal
