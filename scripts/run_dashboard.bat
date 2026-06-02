@echo off
cd /d "%~dp0\.."
if exist ".venv\Scripts\activate.bat" call ".venv\Scripts\activate.bat"
streamlit run src\dashboard\app.py --server.address 0.0.0.0 --server.port 8501
