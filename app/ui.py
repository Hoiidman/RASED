"""Shared UI pieces: CSS, header, KPI figures, alert rows, data-health line.

Plain editorial layout: no boxed cards, no emoji, hairline rules for structure.
"""
from __future__ import annotations

from datetime import datetime
from html import escape

import streamlit as st

from charts import BLACK, GOLD, GOLD_DARK, GREEN_TXT, MUTED, RED_TXT

SEV = {"high": (RED_TXT, "High"), "medium": (GOLD_DARK, "Medium"), "low": (GREEN_TXT, "Low")}
RULE = "#E1E3E5"  # AEBlack 100

CSS = f"""
<style>
/* UAE Design System typography (designsystem.gov.ae/guidelines/typography):
   body = Roboto (EN) + Noto Kufi Arabic (AR); headings = Inter (EN) + Alexandria (AR).
   Latin font first in each stack, so Arabic glyphs fall through to the Arabic face. */
@import url('https://fonts.googleapis.com/css2?family=Roboto:wght@400;500;700&family=Inter:wght@500;600;700;800&family=Noto+Kufi+Arabic:wght@400;500;700&family=Alexandria:wght@500;600;700;800&display=swap');
html, body, [class*="css"], .stMarkdown, .stText, input, textarea, button, select, label {{
  font-family: Roboto, 'Noto Kufi Arabic', -apple-system, BlinkMacSystemFont, system-ui, 'Segoe UI', sans-serif; }}
.stMarkdown p, .stMarkdown li {{ font-size: 16px; line-height: 24px; }}  /* DS base 16/24, line-height >= 1.5 */
.r-title, .page-q, .r-section, .r-k-value, .r-alert-title, h1, h2, h3, h4,
button[data-baseweb="tab"] p, div[data-testid="stMetricValue"] {{
  font-family: Inter, Alexandria, -apple-system, system-ui, 'Segoe UI', sans-serif !important; }}
.r-ar {{ font-family: Alexandria, 'Noto Kufi Arabic', sans-serif !important; }}
/* DS layout: container 980px @lg, 1240px @xl, 1480px @2xl with 22/20/28px side margins; 24px gaps */
.block-container {{ padding: 24px 22px 48px 22px; max-width: 980px; }}
@media (min-width: 1280px) {{ .block-container {{ max-width: 1240px; padding-left: 20px; padding-right: 20px; }} }}
@media (min-width: 1536px) {{ .block-container {{ max-width: 1480px; padding-left: 28px; padding-right: 28px; }} }}
/* DS buttons: sm size 40px high, 20px horizontal padding; one solid (primary) per group */
.stButton button, .stDownloadButton button, .stFormSubmitButton button {{
  min-height: 40px; padding: 0 20px; font-weight: 500; }}
header[data-testid="stHeader"] {{ background: transparent; }}
/* no sidebar: language, portal, sync and sign-out live in the top bar */
section[data-testid="stSidebar"], div[data-testid="stSidebarCollapsedControl"],
button[data-testid="stExpandSidebarButton"], div[data-testid="stSidebarCollapseButton"] {{ display: none !important; }}
.r-head.r-head-bare {{ border-bottom: none; padding-bottom: 0; margin-bottom: 0; }}
.r-ds-row {{ display:flex; justify-content:space-between; gap:16px; padding:6px 0; border-top:1px solid {RULE};
  font-size:14px; line-height:20px; }}
.r-ds-row span.when {{ color:{MUTED}; white-space:nowrap; }}
.r-ds-dot {{ display:inline-block; width:8px; height:8px; border-radius:50%; margin-right:8px; }}
section[data-testid="stSidebar"] {{ background: {BLACK}; }}
section[data-testid="stSidebar"] * {{ color: #EDEDED; }}
section[data-testid="stSidebar"] .stRadio label p {{ font-size: 15px; }}
section[data-testid="stSidebar"] hr {{ border-color: #3A3D42; }}
section[data-testid="stSidebar"] input {{ color: {BLACK} !important; }}
section[data-testid="stSidebar"] button p {{ color: {BLACK} !important; }}
.r-head {{ display:flex; align-items:baseline; justify-content:space-between; gap: 16px;
  border-bottom: 2px solid {GOLD}; padding-bottom: 8px; margin-bottom: 6px; }}
/* DS type scale (size/line-height): 3xl 30/36, 2xl 24/32, xl 20/28, lg 18/28, base 16/24, sm 14/20, xs 12/16 */
.r-title {{ font-size: 26px; line-height: 32px; font-weight: 800; color: {BLACK}; }}
.r-title .r-ar {{ color: {GOLD_DARK}; font-weight: 700; margin-left: 8px; }}
.r-tag {{ color: {MUTED}; font-size: 14px; line-height: 20px; margin-left: 16px; font-weight: 400; }}
.r-portal {{ color: {MUTED}; font-size: 12px; line-height: 16px; text-transform: uppercase; letter-spacing: 1.2px; white-space: nowrap; }}
.r-meta {{ color: {MUTED}; font-size: 14px; line-height: 20px; margin: 0 0 24px 0; }}
.r-meta b {{ color: {BLACK}; font-weight: 500; }}
.r-k {{ padding: 4px 0 8px 0; }}
.r-k-label {{ color: {MUTED}; font-size: 14px; line-height: 20px; }}
.r-k-value {{ color: {BLACK}; font-size: 30px; line-height: 36px; font-weight: 800; }}
.r-k-delta {{ font-size: 14px; line-height: 20px; font-weight: 500; }}
.r-k-note {{ color: {MUTED}; font-size: 12px; line-height: 16px; }}
.r-alert {{ border-top: 1px solid {RULE}; padding: 12px 0; }}
.r-alert-sev {{ font-size: 12px; line-height: 16px; font-weight: 700; text-transform: uppercase; letter-spacing: .8px; }}
.r-alert-title {{ font-weight: 700; font-size: 16px; line-height: 24px; color: {BLACK}; }}
.r-alert-body {{ color: {MUTED}; font-size: 14px; line-height: 20px; }}
.r-section {{ font-size: 12px; line-height: 16px; font-weight: 700; color: {MUTED}; text-transform: uppercase;
  letter-spacing: 1px; margin: 24px 0 8px 0; }}
.muted {{ color: {MUTED}; font-size: 14px; line-height: 20px; }}
.page-q {{ color: {BLACK}; font-size: 24px; line-height: 32px; font-weight: 800; margin: 8px 0 16px 0; }}
/* DS tabs: gap 16 / 24 (md) / 28 (lg) / 32 (xl) */
div[data-baseweb="tab-list"] {{ gap: 16px; border-bottom: 1px solid {RULE}; }}
@media (min-width: 768px) {{ div[data-baseweb="tab-list"] {{ gap: 24px; }} }}
@media (min-width: 1024px) {{ div[data-baseweb="tab-list"] {{ gap: 28px; }} }}
@media (min-width: 1280px) {{ div[data-baseweb="tab-list"] {{ gap: 32px; }} }}
button[data-baseweb="tab"] p {{ font-size: 16px; line-height: 24px; font-weight: 500; color: {MUTED}; }}
button[data-baseweb="tab"][aria-selected="true"] p {{ color: {BLACK}; font-weight: 700; }}
div[data-baseweb="tab-highlight"] {{ background-color: {GOLD_DARK}; }}
div[data-testid="stMetricValue"] {{ color: {BLACK}; }}
</style>
"""


def inject_css():
    st.markdown(CSS, unsafe_allow_html=True)


def header(portal_label: str, tagline: str, rule: bool = True):
    """Title line. With rule=False it sits in the top bar's first column and ui.rule() draws the line under the bar."""
    cls = "r-head" if rule else "r-head r-head-bare"
    st.markdown(
        f'<div class="{cls}"><div class="r-title">RASED<span class="r-ar">راصد</span>'
        f'<span class="r-tag">{escape(tagline)}</span></div>'
        f'<div class="r-portal">{escape(portal_label)}</div></div>', unsafe_allow_html=True)


def rule():
    st.markdown(f'<div style="border-bottom:2px solid {GOLD};margin:0 0 6px 0"></div>', unsafe_allow_html=True)


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


_NICE = {"kit_aggregates": "DED and Free Zone data", "ajman_open_data": "Ajman Open Data portal"}


def data_status(status: list[dict], update: str | None = None):
    """Data-status panel (shown inside the top bar's popover): latest update, then one row per source."""
    st.markdown("**Data status**")
    if update:
        st.caption(update)
    colour = {"ok": GREEN_TXT, "stale": GOLD_DARK, "error": RED_TXT}
    rows = []
    for s in status:
        state = s.get("status", "")
        name = _NICE.get(s["source"], s["source"])
        changed = s.get("last_changed")
        never = changed in (None, "", "Not synced")
        when = "awaiting official access" if never else f"changed {_ago(changed)}"
        label = "not connected" if never else {"ok": "up to date", "stale": "stale", "error": "error"}.get(state, state)
        if never:
            state = "none"
        rows.append(f'<div class="r-ds-row"><span><span class="r-ds-dot" style="background:{colour.get(state, MUTED)}">'
                    f'</span>{escape(name)}</span><span class="when">{label} · {escape(when)}</span></div>')
    st.markdown("".join(rows), unsafe_allow_html=True)


def page_title(title: str, question: str = ""):
    """Pages live in tabs that already show the title, so only the guiding question is drawn."""
    st.markdown(f'<div class="page-q">{escape(question or title)}</div>', unsafe_allow_html=True)


def section(text: str):
    st.markdown(f'<div class="r-section">{escape(text)}</div>', unsafe_allow_html=True)


def kpi(label: str, value: str, delta: float | None = None, note: str = "", delta_suffix: str = "%"):
    d = ""
    if delta is not None:
        c = GREEN_TXT if delta >= 0 else RED_TXT
        d = f'<div class="r-k-delta" style="color:{c}">{delta:+.1f}{delta_suffix}</div>'
    st.markdown(f'<div class="r-k"><div class="r-k-label">{escape(label)}</div><div class="r-k-value">{value}</div>'
                f'{d}<div class="r-k-note">{escape(note)}</div></div>', unsafe_allow_html=True)


def alert_card(a: dict, compact: bool = True):
    c, lab = SEV.get(a["severity"], (MUTED, a["severity"]))
    status = " · acknowledged" if a.get("status") == "acknowledged" else ""
    if a.get("new"):
        status += f' · <span style="color:{BLACK}">new since last sync</span>'
    body = escape(a["what_happened"])
    if not compact:
        body += f'<br>Expected {escape(a["expected"])}, actual <b style="color:{BLACK}">{escape(a["actual"])}</b>'
    st.markdown(
        f'<div class="r-alert"><div class="r-alert-sev" style="color:{c}">{lab}{status}</div>'
        f'<div class="r-alert-title">{escape(a["group"])}, {escape(a["period"])}</div>'
        f'<div class="r-alert-body">{body}</div></div>', unsafe_allow_html=True)
