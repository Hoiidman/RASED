"""Edge cases for the Outlook date window. Run: python app/window_test.py"""
import os
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
# Sync now -> a new alert appears, with news/events context, and nothing breaks
at = AppTest.from_file("main.py", default_timeout=120)
at.session_state["gov_ok"] = True
at.session_state["portal"] = "gov"
at.run()
at.button(key="sync_btn").click().run()
ex = [e.value for e in at.exception]
text = " ".join(str(m.value) for m in at.markdown)
mock_mode = os.environ.get("RASED_USE_MOCKS", "0") == "1"
# Mocks raise a demo alert on sync. The real engine only raises one when the data actually changed.
after_alert = ("Retail shops, 2026-10" in text) if mock_mode else ("Latest data updates" in text.upper()
                                                                   or "LATEST DATA UPDATES" in text.upper())
news = any("headlines" in str(c.value).lower() for c in at.caption)  # live or sample news shown
ok = not ex and after_alert and news
print(f"sync ({'mock' if mock_mode else 'real'}) -> update feed/alert={after_alert}, news shown={news}  "
      f"{'OK' if ok else 'FAIL ' + str(ex[:1])}")
bad += not ok
sys.exit(1 if bad else 0)
