"""Headless smoke test: renders every page of both portals and reports exceptions.

Run:  python app/smoke_test.py
"""
import sys

from streamlit.testing.v1 import AppTest

GOV = ["overview", "alerts", "outlook", "actions", "sectors", "drivers", "impact", "export"]
INV = ["opportunities", "watchouts", "advisor"]

bad = 0
for portal, pages in (("gov", GOV), ("inv", INV)):
    for p in pages:
        at = AppTest.from_file("main.py", default_timeout=60)
        at.session_state["gov_ok"] = True
        at.session_state["portal"] = portal
        at.session_state[f"page_{portal}"] = p
        at.run()
        ex = [e.value for e in at.exception]
        print(f"{portal:4} {p:14} {'OK' if not ex else 'FAIL: ' + ex[0][:300]}")
        bad += bool(ex)
print("ALL OK" if not bad else f"{bad} page(s) failed")
sys.exit(1 if bad else 0)
