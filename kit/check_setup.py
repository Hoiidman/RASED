"""
check_setup.py — run this on every laptop the night before.   python check_setup.py
It checks every package, runs the full pipeline once, and tells you if the laptop is ready to work offline.
"""
import importlib
import importlib.util
import sys
import time

REQUIRED = ["pandas", "numpy", "matplotlib", "statsmodels", "sklearn", "xgboost", "plotly", "streamlit",
            "hijridate", "nbformat", "nbconvert"]
OPTIONAL = ["prophet"]

ok = True
print(f"Python {sys.version.split()[0]}")
for name in REQUIRED + OPTIONAL:
    try:
        m = importlib.import_module(name)
        print(f"  OK   {name:12s} {getattr(m, '__version__', '')}")
    except Exception as e:
        flag = "MISSING (optional — set USE_PROPHET = False)" if name in OPTIONAL else "MISSING"
        print(f"  !!   {name:12s} {flag}: {e.__class__.__name__}")
        ok = ok and name in OPTIONAL

if not ok:
    sys.exit("\nNot ready: install the missing packages with  pip install -r requirements.txt")

print("\nRunning the pipeline once (data prep + back-test + scenarios)...")
t = time.time()
import prepare_data
prepare_data.main()
import forecast_kit as fk
df = fk.load_monthly("data/ajman_monthly.csv")
table, _ = fk.backtest(df, "total", "2018-01", "2024-10", "2026-02", use_prophet=importlib.util.find_spec("prophet") is not None)
print(table.round(1))
scen, _ = fk.forecast_scenarios(df, "total", "2018-01", "2027-12")
print(f"\nREADY. Pipeline ran in {time.time() - t:.0f}s. Now turn wifi OFF and run it again to prove it works offline.")
