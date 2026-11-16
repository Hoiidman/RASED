"""Headless smoke test: renders both portals (every tab) in English and Arabic and reports exceptions.

Run:  python app/smoke_test.py
      RASED_USE_MOCKS=0 python app/smoke_test.py   (real engine, mock fallback)
"""
import sys
import time

from streamlit.testing.v1 import AppTest

bad = 0
for lang in ("EN", "ع"):
    for portal in ("gov", "inv"):
        at = AppTest.from_file("main.py", default_timeout=120)
        at.session_state["lang"] = lang
        at.session_state["gov_ok"] = True
        at.session_state["portal"] = portal
        t0 = time.perf_counter()
        at.run()
        secs = time.perf_counter() - t0
        ex = [e.value for e in at.exception]
        n_tabs = len(at.tabs)
        tag = "AR" if lang != "EN" else "EN"
        print(f"{tag} {portal:4} tabs={n_tabs:2} {secs:4.1f}s  {'OK' if not ex else 'FAIL: ' + ex[0][:300]}")
        bad += bool(ex)
print("ALL OK" if not bad else f"{bad} run(s) failed")
sys.exit(1 if bad else 0)
