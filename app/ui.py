"""Shared UI pieces: CSS, header, KPI tiles, alert cards, data-health strip."""
from __future__ import annotations

from datetime import datetime
from html import escape

import streamlit as st

from charts import BLACK, GOLD, GOLD_BG, GOLD_DARK, GREEN, MUTED, RED

SEV = {"high": (RED, "High"), "medium": (GOLD, "Medium"), "low": (GREEN, "Low")}

CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Noto+Sans+Arabic:wght@400;600&display=swap');
html, body, [class*="css"], .stMarkdown, .stText {{ font-family: Inter, 'Noto Sans Arabic', 'Segoe UI', sans-serif; }}
.block-container {{ padding-top: 1.2rem; padding-bottom: 3rem; max-width: 1400px; }}
header[data-testid="stHeader"] {{ background: transparent; }}
section[data-testid="stSidebar"] {{ background: {BLACK}; }}
section[data-testid="stSidebar"] * {{ color: #EDEDED; }}
section[data-testid="stSidebar"] .stRadio label p {{ font-size: 15px; }}
section[data-testid="stSidebar"] hr {{ border-color: #3A3D42; }}
section[data-testid="stSidebar"] input {{ color: {BLACK} !important; }}
section[data-testid="stSidebar"] button p {{ color: {BLACK} !important; }}
.rased-header {{ background: {BLACK}; border-radius: 14px; padding: 18px 26px; display:flex;
  align-items:center; justify-content:space-between; margin-bottom: 10px; border-bottom: 4px solid {GOLD}; }}
.rased-title {{ color: {GOLD}; font-size: 30px; font-weight: 700; letter-spacing: .5px; margin:0; line-height:1.1 }}
.rased-sub {{ color: #CFCFCF; font-size: 14px; margin-top: 4px; }}
.rased-portal {{ color: {BLACK}; background: {GOLD}; padding: 6px 14px; border-radius: 20px; font-weight: 600; font-size: 13px; }}
.health {{ display:flex; gap:8px; flex-wrap:wrap; margin: 4px 0 14px 0; font-size: 12.5px; }}
.chip {{ border:1px solid #E4E4E4; border-radius: 16px; padding: 3px 10px; background:#fff; color:{MUTED}; }}
.dot {{ display:inline-block; width:8px; height:8px; border-radius:50%; margin-right:6px; }}
.kpi {{ background: #fff; border: 1px solid #ECE6D3; border-top: 4px solid {GOLD}; border-radius: 12px;
  padding: 14px 16px; height: 100%; box-shadow: 0 1px 3px rgba(0,0,0,.04); }}
.kpi-label {{ color: {MUTED}; font-size: 13px; font-weight: 500; }}
.kpi-value {{ color: {BLACK}; font-size: 30px; font-weight: 700; margin: 2px 0; }}
.kpi-delta {{ font-size: 13px; font-weight: 600; }}
.kpi-note {{ color: {MUTED}; font-size: 11.5px; margin-top: 2px; }}
.alert {{ background:#fff; border:1px solid #EEE; border-left: 6px solid var(--c); border-radius: 10px;
  padding: 10px 14px; margin-bottom: 10px; }}
.alert-top {{ display:flex; justify-content:space-between; align-items:center; gap: 8px; }}
.alert-title {{ font-weight: 600; font-size: 14.5px; color:{BLACK}; }}
.badge {{ color:#fff; background: var(--c); border-radius: 10px; padding: 1px 9px; font-size: 11.5px; font-weight:600; white-space:nowrap; }}
.alert-body {{ color:{MUTED}; font-size: 13px; margin-top: 4px; }}
.banner {{ background: {GOLD_BG}; border: 1px solid {GOLD}; border-radius: 10px; padding: 8px 14px;
  color: {GOLD_DARK}; font-weight: 600; font-size: 14px; margin-bottom: 12px; }}
.card {{ background:#fff; border:1px solid #ECE6D3; border-radius: 12px; padding: 14px 16px; margin-bottom: 12px; }}
.card h4 {{ margin: 0 0 4px 0; font-size: 16px; color: {BLACK}; }}
.muted {{ color: {MUTED}; font-size: 13px; }}
.pill {{ display:inline-block; border-radius: 10px; padding: 1px 9px; font-size: 11.5px; font-weight: 600; color:#fff; }}
.page-title {{ font-size: 26px; font-weight: 700; color: {BLACK}; margin: 6px 0 0 0; }}
.page-q {{ color: {GOLD_DARK}; font-size: 15px; font-weight: 500; margin-bottom: 10px; }}
div[data-testid="stMetricValue"] {{ color: {BLACK}; }}
</style>
"""


def inject_css():
    st.markdown(CSS, unsafe_allow_html=True)


def header(portal_label: str, tagline: str):
    st.markdown(
        f"""<div class="rased-header"><div><div class="rased-title">RASED | راصد</div>
        <div class="rased-sub">{escape(tagline)}</div></div>
        <div class="rased-portal">{escape(portal_label)}</div></div>""",
        unsafe_allow_html=True)


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


def health_strip(status: list[dict]):
    col = {"ok": GREEN, "stale": GOLD, "error": RED}
    chips = "".join(
        f'<span class="chip"><span class="dot" style="background:{col.get(s["status"], MUTED)}"></span>'
        f'{escape(s["source"])} · {escape(s["status"])} · changed {_ago(s["last_changed"])}</span>'
        for s in status)
    st.markdown(f'<div class="health"><span class="chip"><b>Data health</b></span>{chips}</div>',
                unsafe_allow_html=True)


def page_title(title: str, question: str = ""):
    st.markdown(f'<div class="page-title">{escape(title)}</div>'
                + (f'<div class="page-q">{escape(question)}</div>' if question else ""), unsafe_allow_html=True)


def kpi(label: str, value: str, delta: float | None = None, note: str = "", delta_suffix: str = "%"):
    d = ""
    if delta is not None:
        c = GREEN if delta >= 0 else RED
        arrow = "▲" if delta >= 0 else "▼"
        d = f'<div class="kpi-delta" style="color:{c}">{arrow} {delta:+.1f}{delta_suffix}</div>'
    st.markdown(f'<div class="kpi"><div class="kpi-label">{escape(label)}</div><div class="kpi-value">{value}</div>'
                f'{d}<div class="kpi-note">{escape(note)}</div></div>', unsafe_allow_html=True)


def alert_card(a: dict, compact: bool = True):
    c, lab = SEV.get(a["severity"], (MUTED, a["severity"]))
    status = " · acknowledged" if a.get("status") == "acknowledged" else ""
    body = f'{escape(a["what_happened"])}'
    if not compact:
        body += f'<br><b>Expected:</b> {escape(a["expected"])} &nbsp; <b>Actual:</b> {escape(a["actual"])}'
    st.markdown(
        f'<div class="alert" style="--c:{c}"><div class="alert-top"><span class="alert-title">'
        f'{escape(a["group"])} · {escape(a["period"])}</span><span class="badge">{lab} severity{status}</span></div>'
        f'<div class="alert-body">{body}</div></div>', unsafe_allow_html=True)


def banner(text: str):
    st.markdown(f'<div class="banner">🔔 {escape(text)}</div>', unsafe_allow_html=True)


def ago(ts: str) -> str:
    return _ago(ts)
