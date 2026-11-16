"""Edge cases for the Outlook date window. Run: python app/window_test.py"""
import sys

from streamlit.testing.v1 import AppTest

cases = {"history only": ("2023-01", "2025-12"), "forecast only": ("2027-01", "2027-12"),
         "single month": ("2026-06", "2026-06"), "everything": ("2023-01", "2027-12")}
bad = 0
for name, win in cases.items():
    at = AppTest.from_file("main.py", default_timeout=120)
    at.session_state["gov_ok"] = True
    at.session_state["portal"] = "gov"
    at.session_state["outlook_window"] = win
    at.run()
    ex = [e.value for e in at.exception]
    print(f"{name:14} {win}  {'OK' if not ex else 'FAIL: ' + ex[0][:300]}")
    bad += bool(ex)
sys.exit(1 if bad else 0)
