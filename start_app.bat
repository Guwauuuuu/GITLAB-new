@echo off
setlocal
cd /d "%~dp0"

set OPEN_BROWSER=1

python -c "import flask" >nul 2>&1
if errorlevel 1 python -m pip install -r requirements.txt

echo.
echo Starting the BJT bias app... the browser will open automatically.
echo If it does not, open http://127.0.0.1:5000/ in your browser.
echo Keep this window open while using the app. Press Ctrl+C to stop.
echo.

python app.py

if errorlevel 1 (
  echo.
  echo The server stopped with an error. Screenshot the messages above and send them.
  pause
)
