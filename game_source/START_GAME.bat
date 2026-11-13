@echo off
chcp 65001 >nul
cd /d "%~dp0"
where py >nul 2>nul
if %errorlevel%==0 (
  py -3 run_preview.py
) else (
  python run_preview.py
)
pause
