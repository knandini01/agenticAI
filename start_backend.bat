@echo off
title Autonomous Desktop OS Multi-Agent Backend
cd /d "%~dp0backend"
echo =======================================================
echo Starting Autonomous OS Multi-Agent Backend on port 8000
echo =======================================================
python -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload
pause
