@echo off
setlocal
cd /d "%~dp0"

set HOST=0.0.0.0

python -c "import flask" >nul 2>&1
if errorlevel 1 python -m pip install -r requirements.txt

echo.
echo Sharing on the local network. Give your friend the "Network:" URL below.
echo Your friend must be on the same Wi-Fi / hotspot.
echo If Windows asks about firewall access for Python, click Allow.
echo.

python app.py
