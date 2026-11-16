"""RASED Streamlit app — Government portal + Investor portal (owner: Agent B).

Run:  streamlit run app/main.py        (mocks by default)
      RASED_USE_MOCKS=0 streamlit run app/main.py   (real engine, per-function mock fallback)
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
APP = Path(__file__).resolve().parent
for p in (str(ROOT), str(APP)):
    if p not in sys.path:
        sys.path.insert(0, p)


def _load_env():
    # .env.txt too: Windows Notepad often saves ".env" with a hidden .txt extension
    for env in (ROOT / ".env", ROOT / ".env.txt"):
        if not env.exists():
            continue
        for line in env.read_text(encoding="utf-8-sig").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


_load_env()

import streamlit as st  # noqa: E402

st.set_page_config(page_title="RASED | راصد", layout="wide", initial_sidebar_state="expanded")

import backend as be  # noqa: E402
import ui  # noqa: E402
import views_gov  # noqa: E402
import views_inv  # noqa: E402
from labels import LANG, L  # noqa: E402

ui.inject_css()

GOV_PAGES = ["overview", "alerts", "outlook", "actions", "sectors", "drivers", "impact", "export"]
INV_PAGES = ["opportunities", "watchouts", "advisor"]

with st.sidebar:
    lang = "ar" if st.radio("Language / اللغة", ["EN", "ع"], horizontal=True, key="lang") == "ع" else "en"
    t = L[lang]
    LANG["v"] = lang
    if lang == "ar":  # right-to-left text in the main area; charts keep left-to-right axes
        st.markdown("<style>.block-container{direction:rtl;text-align:right}"
                    ".block-container .js-plotly-plot,.block-container .stPlotlyChart{direction:ltr}"
                    ".r-tag{margin-left:0;margin-right:14px}.r-title .r-ar{margin-left:0;margin-right:8px}</style>",
                    unsafe_allow_html=True)
    portal = st.radio(t["portal"], ["gov", "inv"], format_func=lambda k: t[k], key="portal")
    st.divider()

# --- government login -------------------------------------------------------------
if portal == "gov" and not st.session_state.get("gov_ok"):
    ui.header(t["gov"], t["tagline"])
    st.markdown("### " + t["login_title"])
    pw_required = os.environ.get("GOV_PASSWORD")
    c1, _ = st.columns([1, 2])
    with c1:
        if pw_required:
            pw = st.text_input(t["password"], type="password")
            if st.button(t["login"], type="primary"):
                if pw == pw_required:
                    st.session_state.gov_ok = True
                    st.rerun()
                else:
                    st.error(t["wrong_pw"])
        else:
            st.caption(t["demo_login"])
            if st.button(t["login"], type="primary"):
                st.session_state.gov_ok = True
                st.rerun()
    st.stop()

pages = GOV_PAGES if portal == "gov" else INV_PAGES
with st.sidebar:
    page = st.radio(t["nav"], pages, format_func=lambda k: t["p_" + k], key=f"page_{portal}")
    st.divider()
    if portal == "gov":
        if st.button(t["sync_now"], width="stretch"):
            res = be.run_sync(force=True)
            st.session_state.last_sync = res
            st.toast(f"{len(res.get('changed', []))} dataset(s) changed · {res.get('new_alerts', 0)} new alert(s)")
        if st.button(t["logout"], width="stretch"):
            st.session_state.gov_ok = False
            st.rerun()
    engine_slot = st.empty()  # filled after the page renders, once we know which functions ran for real

ui.header(t["gov"] if portal == "gov" else t["inv"], t["tagline"])

update = None
if portal == "gov":
    changes = be.get_changes()
    if changes:
        last = changes[0]
        n_al = last.get("new_alerts", 0)
        update = (f"Updated {ui.ago(last['time'])}: {last['dataset']} added {last['rows_added']:,} rows"
                  + (f", {n_al} new alert{'s' if n_al != 1 else ''}" if n_al else ""))
ui.meta_line(be.sync_status(), update)

if portal == "gov":
    views_gov.render(page, lang)
else:
    views_inv.render(page, lang)

engine_slot.caption(f"{be.engine_summary()}. Licence data is a signal, not GDP or FDI.")
