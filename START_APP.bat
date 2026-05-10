@echo off
title Launching Finance AI DSS
color 0A
echo ==========================================
echo   Starting Personal Finance AI System...
echo ==========================================
echo.
py -m streamlit run app.py
if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Failed to start. Checking if 'py' command works...
    py -m streamlit run app.py
)
pause