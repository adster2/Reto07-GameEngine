@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>nul
if %errorlevel% equ 0 (
    py -3 virtual_game.py %*
) else (
    python virtual_game.py %*
)
if errorlevel 1 pause
