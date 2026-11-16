#!/usr/bin/env bash
# One-time setup on macOS / Linux. Needs Python 3.10-3.12.   Run:  bash setup_mac_linux.sh
set -e
cd "$(dirname "$0")"
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
python check_setup.py
echo
echo "To open the notebook:   source .venv/bin/activate && jupyter lab Ajman_Forecasting_Kit.ipynb"
echo "To open the dashboard:  source .venv/bin/activate && streamlit run app.py"
