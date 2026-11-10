@echo off
setlocal
cd /d "%~dp0"

python -c "import flask" >nul 2>&1
if errorlevel 1 python -m pip install -r requirements.txt

echo.
echo Open http://127.0.0.1:5000/ in your browser.
echo Press Ctrl+C in this window to stop the server.
echo.

python app.py
