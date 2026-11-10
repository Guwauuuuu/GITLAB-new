@echo off
setlocal
cd /d "%~dp0"

python -c "import flask" >nul 2>&1
if errorlevel 1 python -m pip install -r requirements.txt

python app.py
