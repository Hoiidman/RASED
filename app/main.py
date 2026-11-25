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

st.set_page_config(page_title="RASED | راصد", layout="wide", initial_sidebar_state="collapsed")

import backend as be  # noqa: E402
import ui  # noqa: E402
import views_gov  # noqa: E402
import views_inv  # noqa: E402
from labels import LANG, L  # noqa: E402

ui.inject_css()
be.ensure_data()  # first start on a fresh copy builds the data snapshot; no-op afterwards

GOV_PAGES = ["overview", "alerts", "outlook", "actions", "sectors", "drivers", "impact", "export"]
INV_PAGES = ["opportunities", "watchouts", "advisor"]

# --- state: language and portal are toggled by buttons in the top bar (no sidebar) ---
st.session_state.setdefault("lang", "EN")      # "EN" or "ع"
st.session_state.setdefault("portal", "gov")   # "gov" or "inv"


def _toggle_lang():
    st.session_state.lang = "ع" if st.session_state.lang == "EN" else "EN"


def _toggle_portal():
    st.session_state.portal = "inv" if st.session_state.portal == "gov" else "gov"


def _sign_out():
    st.session_state.gov_ok = False


lang = "ar" if st.session_state.lang == "ع" else "en"
portal = st.session_state.portal
t = L[lang]
LANG["v"] = lang
if lang == "ar":  # right-to-left text in the main area; charts keep left-to-right axes
    st.markdown("<style>.block-container{direction:rtl;text-align:right}"
                ".block-container .js-plotly-plot,.block-container .stPlotlyChart{direction:ltr}"
                # each text block takes its direction from its own first letter, so English
                # sentences and numbers like +7.1% keep their punctuation in place inside RTL
                ".block-container p,.block-container li,.r-k-value,.r-k-delta,.r-k-note,.r-k-label,"
                ".r-alert-title,.r-alert-body,.r-meta,.page-q{unicode-bidi:plaintext}"
                ".r-fresh{unicode-bidi:plaintext}.r-ds-dot{margin-right:0;margin-left:8px}"
                ".r-tag{margin-left:0;margin-right:14px}.r-title .r-ar{margin-left:0;margin-right:8px}</style>",
                unsafe_allow_html=True)

# --- top bar: title, then icon buttons on the right ---
signed_in = portal == "gov" and st.session_state.get("gov_ok")
cols = st.columns([8, 0.6, 0.6, 2, 0.6, 0.6] if signed_in else [8, 0.6, 0.6, 2], vertical_alignment="center")
with cols[0]:
    ui.header(t["gov"] if portal == "gov" else t["inv"], t["tagline"], rule=False)
cols[1].button("ع" if lang == "en" else "EN", key="lang_toggle", on_click=_toggle_lang,
               help="العربية" if lang == "en" else "English", width="stretch")
status_slot = cols[2].empty()  # data-status icon, filled once the sync state is known (after any Sync now)
other = "inv" if portal == "gov" else "gov"
cols[3].button(t[other], key="portal_toggle", on_click=_toggle_portal, width="stretch",
               icon=":material/storefront:" if other == "inv" else ":material/account_balance:",
               help=f"Switch to the {t[other]}")
if signed_in:
    # icon-only buttons; their names show on hover
    if cols[4].button(":material/sync:", key="sync_btn", help=t["sync_now"], width="stretch"):
        res = be.run_sync(force=True)
        st.session_state.last_sync = res
        st.toast(f"{len(res.get('changed', []))} dataset(s) changed · {res.get('new_alerts', 0)} new alert(s)")
    cols[5].button(":material/logout:", key="signout_btn", help=t["logout"], width="stretch", on_click=_sign_out)

# data status lives behind a small icon instead of two lines under the title
update = None
if signed_in:
    changes = be.get_changes()
    if changes:
        last = changes[0]
        n_al = last.get("new_alerts", 0)
        update = (f"Updated {ui.ago(last['time'])}: {ui._NICE.get(last['dataset'], last['dataset'])} "
                  f"added {last['rows_added']:,} rows"
                  + (f", {n_al} new alert{'s' if n_al != 1 else ''}" if n_al else ""))
official = None if be.use_mocks() else be.official_check()  # live check against the official portal, cached 6 h
with status_slot.container():
    with st.popover(":material/database:", help="Data status", use_container_width=True):
        ui.data_status(be.sync_status(), update, official)
ui.rule()
ui.freshness_line(official, be.get_catalog())

# --- government login -------------------------------------------------------------
if portal == "gov" and not st.session_state.get("gov_ok"):
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

# Pages as tabs across the top. Each page is a fragment: moving a slider or picking a filter reruns only
# that page, not all eight tabs. Engine reads are cached in backend.
views = views_gov if portal == "gov" else views_inv


@st.fragment
def _page(page: str):
    views.render(page, lang)


for tab, page in zip(st.tabs([t["p_" + k] for k in pages]), pages):
    with tab:
        _page(page)

st.caption(f"{be.engine_summary()}. Licence data is a signal, not GDP or FDI.")  # footer
