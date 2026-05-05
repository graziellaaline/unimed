@echo off
cd /d "%~dp0"
call venv\Scripts\activate
start "" http://localhost:8055
streamlit run main.py --server.port 8055 --server.address localhost --server.headless true
