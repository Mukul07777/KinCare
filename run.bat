@echo off
REM KinCare: one-click run on Windows.
REM First run installs everything and downloads the real CDSCO data (a few minutes).
setlocal
cd /d "%~dp0"

echo.
echo  ===== KinCare =====
echo.

REM ---- API: Python venv + packages ----
if not exist "api\.venv\Scripts\python.exe" (
  echo [1/4] Creating Python environment...
  py -3.12 -m venv api\.venv 2>nul || python -m venv api\.venv
  if errorlevel 1 ( echo Python 3.12 not found. Install it from python.org & pause & exit /b 1 )
  echo [1/4] Installing API packages...
  api\.venv\Scripts\python -m pip install -q --upgrade pip
  api\.venv\Scripts\python -m pip install -q -r api\requirements.txt
  if errorlevel 1 ( echo Package install failed. & pause & exit /b 1 )
) else (
  echo [1/4] Python environment ready
)

REM ---- Data: real CDSCO alerts into data\kincare.db ----
if not exist "data\kincare.db" (
  echo [2/4] Downloading and parsing real CDSCO alerts. This takes a few minutes the first time...
  pushd api
  .venv\Scripts\python -m ingest.fetch --limit 24
  .venv\Scripts\python -m ingest.load
  .venv\Scripts\python -m ingest.portal
  REM Real ICU vitals for the live replay (numbers only; add waveforms later with: python -m ingest.bidmc)
  .venv\Scripts\python -m ingest.bidmc --waves 0
  REM 246k Indian medicine brands with MRP and salt, for "same medicine, lower price"
  .venv\Scripts\python -m ingest.medicines
  popd
) else (
  echo [2/4] Alert database ready
)

REM ---- Web: npm packages + production build ----
if not exist "web\node_modules" (
  echo [3/4] Installing web packages...
  pushd web
  call npm install
  popd
)
REM Rebuild when the code changed since the last build (after a git pull), not only on first run.
set "REV=none"
for /f %%h in ('git rev-parse HEAD 2^>nul') do set "REV=%%h"
set "BUILT=missing"
if exist "web\.next\kincare_rev.txt" set /p BUILT=<"web\.next\kincare_rev.txt"
set "NEEDBUILD=0"
if not exist "web\.next\BUILD_ID" set "NEEDBUILD=1"
if not "%REV%"=="%BUILT%" set "NEEDBUILD=1"
if "%NEEDBUILD%"=="1" (
  echo [3/4] Building the web app...
  pushd web
  call npm run build
  if not errorlevel 1 (echo %REV%> ".next\kincare_rev.txt")
  popd
) else (
  echo [3/4] Web app ready
)

REM ---- Start both servers in their own windows ----
echo [4/4] Starting servers...
REM Keys live in api\.env.bat (git-ignored). First run: copy the template so there is one place to fill in.
if not exist "api\.env.bat" if exist "api\env.example.bat" (
  copy /y "api\env.example.bat" "api\.env.bat" >nul
  echo       Created api\.env.bat - add your keys there (Telegram, WhatsApp...^), then run this again.
)
if exist "api\.env.bat" call "api\.env.bat"
REM This laptop is a demo machine: login codes show on screen (no WhatsApp needed). Never set this on a public server.
if not defined KINCARE_DEMO set "KINCARE_DEMO=1"
REM Admin always needs a token now. Make one for this laptop, once, and keep it in api\.env.bat.
set "NEWTOKEN="
if not defined ADMIN_TOKEN (
  for /f %%t in ('powershell -NoProfile -Command "[guid]::NewGuid().ToString('N')"') do set "ADMIN_TOKEN=%%t"
  set "NEWTOKEN=1"
)
REM Outside the block: inside it %ADMIN_TOKEN% would still be empty (cmd expands a block before running it).
if defined NEWTOKEN if exist "api\.env.bat" echo set "ADMIN_TOKEN=%ADMIN_TOKEN%">> "api\.env.bat"
echo       Admin token (for /admin): %ADMIN_TOKEN%
start "KinCare API (port 8000)" cmd /k "cd /d %~dp0api && .venv\Scripts\python -m uvicorn main:app --port 8000"
start "KinCare Web (port 3000)" cmd /k "cd /d %~dp0web && npx next start -p 3000"

REM Wait for the web server, then open the browser.
set /a tries=0
:wait
timeout /t 2 /nobreak >nul
set /a tries+=1
powershell -NoProfile -Command "try { Invoke-WebRequest -UseBasicParsing http://localhost:3000 -TimeoutSec 2 | Out-Null; exit 0 } catch { exit 1 }"
if errorlevel 1 if %tries% lss 30 goto wait

start "" http://localhost:3000
echo.
echo  KinCare is running:  http://localhost:3000    (live demo: http://localhost:3000/live)
echo  API docs:           http://localhost:8000/docs
echo  Close the two server windows to stop.
echo.
pause
