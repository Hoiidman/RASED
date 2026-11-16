"""Submits the investor advisor form on the real engine and checks advice appears. Run: python app/advisor_test.py"""
import sys

from streamlit.testing.v1 import AppTest

at = AppTest.from_file("main.py", default_timeout=180)
at.session_state["portal"] = "inv"
at.run()
btn = next(b for b in at.button if "Get my outlook" in str(b.label))
btn.click().run()
ex = [e.value for e in at.exception]
text = " ".join(str(m.value) for m in at.markdown)
ok = not ex and "Not financial advice" in text
print("advisor:", "OK" if ok else f"FAIL {ex[:1]}", "| engine caption:",
      next((c.value for c in at.caption if "Engine:" in str(c.value)), "none")[:120])
sys.exit(0 if ok else 1)
