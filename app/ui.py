"""Shared UI pieces: CSS, header, KPI figures, alert rows, data-health line.

Plain editorial layout: no boxed cards, no emoji, hairline rules for structure.
"""
from __future__ import annotations

from datetime import datetime
from html import escape

import streamlit as st

from charts import BLACK, GOLD, GOLD_DARK, GREEN, MUTED, RED

SEV = {"high": (RED, "High"), "medium": (GOLD_DARK, "Medium"), "low": (GREEN, "Low")}
RULE = "#E6E1D3"

CSS = f"""
<style>
/* UAE Design System typography (designsystem.gov.ae/guidelines/typography):
   body = Roboto (EN) + Noto Kufi Arabic (AR); headings = Inter (EN) + Alexandria (AR).
   Latin font first in each stack, so Arabic glyphs fall through to the Arabic face. */
@import url('https://fonts.googleapis.com/css2?family=Roboto:wght@400;500;700&family=Inter:wght@500;600;700&family=Noto+Kufi+Arabic:wght@400;500;700&family=Alexandria:wght@500;600;700&display=swap');
html, body, [class*="css"], .stMarkdown, .stText, input, textarea, button, select, label {{
  font-family: Roboto, 'Noto Kufi Arabic', -apple-system, BlinkMacSystemFont, system-ui, 'Segoe UI', sans-serif; }}
.r-title, .page-q, .r-section, .r-k-value, .r-alert-title, h1, h2, h3, h4,
button[data-baseweb="tab"] p, div[data-testid="stMetricValue"] {{
  font-family: Inter, Alexandria, -apple-system, system-ui, 'Segoe UI', sans-serif !important; }}
.r-ar {{ font-family: Alexandria, 'Noto Kufi Arabic', sans-serif !important; }}
.block-container {{ padding-top: 1.4rem; padding-bottom: 3rem; max-width: 1400px; }}
header[data-testid="stHeader"] {{ background: transparent; }}
section[data-testid="stSidebar"] {{ background: {BLACK}; }}
section[data-testid="stSidebar"] * {{ color: #EDEDED; }}
section[data-testid="stSidebar"] .stRadio label p {{ font-size: 15px; }}
section[data-testid="stSidebar"] hr {{ border-color: #3A3D42; }}
section[data-testid="stSidebar"] input {{ color: {BLACK} !important; }}
section[data-testid="stSidebar"] button p {{ color: {BLACK} !important; }}
.r-head {{ display:flex; align-items:baseline; justify-content:space-between; gap: 16px;
  border-bottom: 2px solid {GOLD}; padding-bottom: 8px; margin-bottom: 6px; }}
.r-title {{ font-size: 26px; font-weight: 700; color: {BLACK}; letter-spacing: .3px; }}
.r-title .r-ar {{ color: {GOLD_DARK}; font-weight: 600; margin-left: 8px; }}
.r-tag {{ color: {MUTED}; font-size: 13.5px; margin-left: 14px; font-weight: 400; }}
.r-portal {{ color: {MUTED}; font-size: 12px; text-transform: uppercase; letter-spacing: 1.2px; white-space: nowrap; }}
.r-meta {{ color: {MUTED}; font-size: 12.5px; margin: 0 0 18px 0; line-height: 1.7; }}
.r-meta b {{ color: {BLACK}; font-weight: 600; }}
.r-k {{ padding: 2px 0 8px 0; }}
.r-k-label {{ color: {MUTED}; font-size: 13px; }}
.r-k-value {{ color: {BLACK}; font-size: 30px; font-weight: 700; line-height: 1.25; }}
.r-k-delta {{ font-size: 13px; font-weight: 600; }}
.r-k-note {{ color: {MUTED}; font-size: 12px; }}
.r-alert {{ border-top: 1px solid {RULE}; padding: 10px 0 10px 0; }}
.r-alert-sev {{ font-size: 11.5px; font-weight: 700; text-transform: uppercase; letter-spacing: .8px; }}
.r-alert-title {{ font-weight: 600; font-size: 14.5px; color: {BLACK}; margin-top: 1px; }}
.r-alert-body {{ color: {MUTED}; font-size: 13px; margin-top: 2px; }}
.r-section {{ font-size: 13px; font-weight: 600; color: {MUTED}; text-transform: uppercase; letter-spacing: 1px;
  margin: 18px 0 6px 0; }}
.muted {{ color: {MUTED}; font-size: 13px; }}
.page-title {{ font-size: 24px; font-weight: 700; color: {BLACK}; margin: 8px 0 0 0; }}
.page-q {{ color: {BLACK}; font-size: 19px; font-weight: 600; margin: 6px 0 14px 0; }}
div[data-baseweb="tab-list"] {{ gap: 22px; border-bottom: 1px solid {RULE}; }}
button[data-baseweb="tab"] p {{ font-size: 15px; font-weight: 500; }}
button[data-baseweb="tab"][aria-selected="true"] p {{ color: {BLACK}; font-weight: 700; }}
div[data-testid="stMetricValue"] {{ color: {BLACK}; }}
</style>
"""


def inject_css():
    st.markdown(CSS, unsafe_allow_html=True)


def header(portal_label: str, tagline: str):
    st.markdown(
        f'<div class="r-head"><div class="r-title">RASED<span class="r-ar">راصد</span>'
        f'<span class="r-tag">{escape(tagline)}</span></div>'
        f'<div class="r-portal">{escape(portal_label)}</div></div>', unsafe_allow_html=True)


def _ago(ts: str) -> str:
    try:
        d = datetime.now() - datetime.fromisoformat(ts)
    except ValueError:
        return ts
    m = int(d.total_seconds() // 60)
    if m < 1:
        return "just now"
    if m < 60:
        return f"{m} min ago"
    if m < 60 * 48:
        return f"{m // 60} h ago"
    return f"{m // 1440} d ago"


def ago(ts: str) -> str:
    return _ago(ts)


def meta_line(status: list[dict], update: str | None = None):
    """One muted line: latest update, then each source's state. Only non-ok states get colour."""
    parts = []
    for s in status:
        st_ = s["status"]
        tag = "" if st_ == "ok" else f' <span style="color:{GOLD_DARK if st_ == "stale" else RED}">({escape(st_)})</span>'
        parts.append(f'{escape(s["source"])} {_ago(s["last_changed"])}{tag}')
    head = f"<b>{escape(update)}</b><br>" if update else ""
    st.markdown(f'<div class="r-meta">{head}Sources: ' + " · ".join(parts) + "</div>", unsafe_allow_html=True)


def page_title(title: str, question: str = ""):
    """Pages live in tabs that already show the title, so only the guiding question is drawn."""
    st.markdown(f'<div class="page-q">{escape(question or title)}</div>', unsafe_allow_html=True)


def section(text: str):
    st.markdown(f'<div class="r-section">{escape(text)}</div>', unsafe_allow_html=True)


def kpi(label: str, value: str, delta: float | None = None, note: str = "", delta_suffix: str = "%"):
    d = ""
    if delta is not None:
        c = GREEN if delta >= 0 else RED
        d = f'<div class="r-k-delta" style="color:{c}">{delta:+.1f}{delta_suffix}</div>'
    st.markdown(f'<div class="r-k"><div class="r-k-label">{escape(label)}</div><div class="r-k-value">{value}</div>'
                f'{d}<div class="r-k-note">{escape(note)}</div></div>', unsafe_allow_html=True)


def alert_card(a: dict, compact: bool = True):
    c, lab = SEV.get(a["severity"], (MUTED, a["severity"]))
    status = " · acknowledged" if a.get("status") == "acknowledged" else ""
    body = escape(a["what_happened"])
    if not compact:
        body += f'<br>Expected {escape(a["expected"])}, actual <b style="color:{BLACK}">{escape(a["actual"])}</b>'
    st.markdown(
        f'<div class="r-alert"><div class="r-alert-sev" style="color:{c}">{lab}{status}</div>'
        f'<div class="r-alert-title">{escape(a["group"])}, {escape(a["period"])}</div>'
        f'<div class="r-alert-body">{body}</div></div>', unsafe_allow_html=True)
