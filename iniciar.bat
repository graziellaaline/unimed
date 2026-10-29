@echo off
cd /d "%~dp0"
call venv\Scripts\activate
start "" http://localhost:8055
python servidor.py
