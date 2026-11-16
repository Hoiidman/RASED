@echo off
REM One-time setup on Windows. Needs Python 3.10-3.12 from python.org (tick "Add Python to PATH").
cd /d "%~dp0"
python -m venv .venv
call .venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
python check_setup.py
echo.
echo To open the notebook:   .venv\Scripts\activate  then  jupyter lab Ajman_Forecasting_Kit.ipynb
echo To open the dashboard:  .venv\Scripts\activate  then  streamlit run app.py
pause
