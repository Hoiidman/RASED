"""Shared UI pieces: CSS, header, KPI figures, alert rows, data-health line.

Plain editorial layout: no boxed cards, no emoji, hairline rules for structure.
"""
from __future__ import annotations

import re
from datetime import datetime
from html import escape

import streamlit as st

from charts import BLACK, GOLD, GOLD_DARK, GREEN_TXT, MUTED, RED_TXT
from i18n import is_ar, sig, lang as cur_lang, month, name, tr

SEV = {"high": (RED_TXT, "High"), "medium": (GOLD_DARK, "Medium"), "low": (GREEN_TXT, "Low")}
SEV_AR = {"high": "مرتفع", "medium": "متوسط", "low": "منخفض"}
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
/* top-bar buttons are narrow columns: less padding, or "EN" and the icons are clipped */
.st-key-topbar .stButton button, .st-key-topbar div[data-testid="stPopover"] button {{ padding: 0 8px; min-width: 0; }}
header[data-testid="stHeader"] {{ background: transparent; }}
/* no sidebar: language, portal, sync and sign-out live in the top bar */
section[data-testid="stSidebar"], div[data-testid="stSidebarCollapsedControl"],
button[data-testid="stExpandSidebarButton"], div[data-testid="stSidebarCollapseButton"] {{ display: none !important; }}
.r-head.r-head-bare {{ border-bottom: none; padding-bottom: 0; margin-bottom: 0; }}
.r-ds-row {{ display:flex; justify-content:space-between; gap:16px; padding:6px 0; border-top:1px solid {RULE};
  font-size:14px; line-height:20px; }}
.r-ds-row span.when {{ color:{MUTED}; white-space:nowrap; }}
.r-fresh {{ color:{MUTED}; font-size:14px; line-height:20px; margin:4px 0 8px 0; }}
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
/* ---- phones (Streamlit stacks every column below 640px) ---- */
@media (max-width: 640px) {{
  .block-container {{ padding: 12px 16px 40px 16px; }}
  /* top bar: title on its own line, then the buttons side by side instead of five full-width rows */
  .st-key-topbar div[data-testid="stHorizontalBlock"] {{ flex-wrap: wrap !important; flex-direction: row !important; gap: 8px !important; }}
  .st-key-topbar div[data-testid="stColumn"] {{ width: auto !important; min-width: 0 !important; flex: 0 0 auto !important; }}
  .st-key-topbar div[data-testid="stColumn"]:first-child {{ flex: 1 1 100% !important; }}
  .st-key-topbar div[data-testid="stColumn"]:nth-child(4) {{ flex: 1 1 auto !important; }}
  .st-key-topbar .stButton button, .st-key-topbar div[data-testid="stPopover"] button {{ padding: 0 12px; min-height: 38px; }}
  /* Streamlit pulls markdown up by 16px; inside the wrapped top bar that hides the title under the buttons */
  .st-key-topbar div[data-testid="stColumn"]:first-child {{ padding-bottom: 18px; }}
  .r-head {{ flex-wrap: wrap; align-items: baseline; gap: 0 12px; }}
  .r-portal {{ flex-basis: 100%; }}
  .r-title {{ font-size: 22px; line-height: 28px; }}
  .r-tag {{ display: none; }}
  .r-fresh {{ font-size: 13px; line-height: 18px; }}
  .page-q {{ font-size: 20px; line-height: 28px; margin: 4px 0 12px 0; }}
  .stMarkdown p, .stMarkdown li {{ font-size: 15px; line-height: 23px; }}
  /* tabs: smaller and closer together; the row still scrolls sideways */
  div[data-baseweb="tab-list"] {{ gap: 12px; }}
  button[data-baseweb="tab"] p {{ font-size: 14px; }}
  /* headline figures two per row instead of one per screen */
  /* (only rows of figures: a layout row that holds a nested row, like the policy simulator, still stacks) */
  div[data-testid="stHorizontalBlock"]:has(> div[data-testid="stColumn"] .r-k):not(:has(div[data-testid="stHorizontalBlock"])),
  div[data-testid="stHorizontalBlock"]:has(> div[data-testid="stColumn"] div[data-testid="stMetric"]):not(:has(div[data-testid="stHorizontalBlock"])) {{
    flex-wrap: wrap !important; flex-direction: row !important; gap: 12px 16px !important; }}
  div[data-testid="stHorizontalBlock"]:has(> div[data-testid="stColumn"] .r-k):not(:has(div[data-testid="stHorizontalBlock"])) > div[data-testid="stColumn"],
  div[data-testid="stHorizontalBlock"]:has(> div[data-testid="stColumn"] div[data-testid="stMetric"]):not(:has(div[data-testid="stHorizontalBlock"])) > div[data-testid="stColumn"] {{
    flex: 1 1 calc(50% - 8px) !important; min-width: calc(50% - 8px) !important; width: calc(50% - 8px) !important; }}
  /* an odd one out (5 headline figures, 3 advisor figures) takes the full last row */
  div[data-testid="stHorizontalBlock"]:has(> div[data-testid="stColumn"] .r-k):not(:has(div[data-testid="stHorizontalBlock"])) > div[data-testid="stColumn"]:last-child:nth-child(odd),
  div[data-testid="stHorizontalBlock"]:has(> div[data-testid="stColumn"] div[data-testid="stMetric"]):not(:has(div[data-testid="stHorizontalBlock"])) > div[data-testid="stColumn"]:last-child:nth-child(odd) {{
    flex-basis: 100% !important; width: 100% !important; }}
  div[data-testid="stMetricDelta"] div, div[data-testid="stMetricLabel"] p {{ white-space: normal !important; overflow: visible !important; }}
  .r-k-value {{ font-size: 24px; line-height: 30px; }}
  div[data-testid="stMetricValue"] {{ font-size: 24px; }}
  .r-alert-title {{ font-size: 15px; line-height: 22px; }}
}}
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
        return tr("just now", "الآن")
    if m < 60:
        return tr(f"{m} min ago", f"قبل {m} دقيقة")
    if m < 60 * 48:
        return tr(f"{m // 60} h ago", f"قبل {m // 60} ساعة")
    return tr(f"{m // 1440} d ago", f"قبل {m // 1440} يوم")


def ago(ts: str) -> str:
    return _ago(ts)


_NICE = {"kit_aggregates": "DED and Free Zone data", "ajman_open_data": "Ajman Open Data portal"}
_NICE_AR = {"kit_aggregates": "بيانات الدائرة والمنطقة الحرة", "ajman_open_data": "بوابة عجمان للبيانات المفتوحة"}


_MON_EN = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
_MON_AR = ["يناير", "فبراير", "مارس", "أبريل", "مايو", "يونيو", "يوليو", "أغسطس", "سبتمبر", "أكتوبر", "نوفمبر", "ديسمبر"]


def month_label(period: str, lang: str | None = None) -> str:
    lang = lang or cur_lang()
    try:
        y, m = period[:4], int(period[5:7])
    except (TypeError, ValueError):
        return str(period)
    return f"{(_MON_AR if lang == 'ar' else _MON_EN)[m - 1]} {y}"


def freshness_line(official: dict | None, catalog):
    """One line under the top bar: is RASED's data as new as the official sources?"""
    lang = cur_lang()
    try:
        last = catalog.set_index("id")["last_period"]
        main, fz = month_label(str(last["new_reg_mainland"]), lang), month_label(str(last["new_reg_fz"]), lang)
    except (KeyError, AttributeError):
        return
    if official and official["up_to_date"]:
        colour = GREEN_TXT
        text = (f"البيانات محدّثة: أرقام البر الرئيسي تطابق آخر شهر منشور على بوابة عجمان للبيانات المفتوحة ({main})، "
                f"وبيانات المنطقة الحرة حتى {fz}." if lang == "ar" else
                f"Up to date: mainland figures match the latest month published on the official Ajman Open Data "
                f"portal ({main}, checked {_ago(official['checked'])}). Free Zone figures run to {fz}.")
    elif official:
        colour = GOLD_DARK
        newer = month_label(official["portal_latest"], lang)
        text = (f"البوابة الرسمية لديها بيانات أحدث ({newer}) من راصد ({main}). شغّل المزامنة للتحديث." if lang == "ar" else
                f"The official portal has newer mainland data ({newer}) than RASED ({main}). Run Sync to update.")
    else:
        colour = MUTED
        text = (f"أحدث البيانات: البر الرئيسي {main}، المنطقة الحرة {fz}." if lang == "ar" else
                f"Latest data: mainland {main}, Free Zone {fz}. The official portal could not be checked just now.")
    st.markdown(f'<div class="r-fresh"><span class="r-ds-dot" style="background:{colour}"></span>{escape(text)}</div>',
                unsafe_allow_html=True)


def data_status(status: list[dict], update: str | None = None, official: dict | None = None):
    """Data-status panel (shown inside the top bar's popover): latest update, then one row per source."""
    st.markdown(tr("**Data status**", "**حالة البيانات**"))
    if update:
        st.caption(update)
    colour = {"ok": GREEN_TXT, "stale": GOLD_DARK, "error": RED_TXT}
    rows = []
    for s in status:
        state = s.get("status", "")
        src = (_NICE_AR if is_ar() else _NICE).get(s["source"], s["source"])
        changed = s.get("last_changed")
        never = changed in (None, "", "Not synced")
        when = tr("awaiting official access", "بانتظار الوصول الرسمي") if never else tr(f"changed {_ago(changed)}",
                                                                                        f"تغيّرت {_ago(changed)}")
        states = {"ok": tr("up to date", "محدّثة"), "stale": tr("stale", "قديمة"), "error": tr("error", "خطأ")}
        label = tr("not connected", "غير متصلة") if never else states.get(state, state)
        if never:
            state = "none"
        if s["source"] == "ajman_open_data":  # public API, checked live against our data (no key needed)
            if official:
                state = "ok" if official["up_to_date"] else "stale"
                label = (tr("matches ours", "مطابقة لبياناتنا") if official["up_to_date"]
                         else tr("has newer data", "لديها بيانات أحدث"))
                when = tr(f"latest {month_label(official['portal_latest'])}, checked {_ago(official['checked'])}",
                          f"الأحدث {month_label(official['portal_latest'])}، فُحصت {_ago(official['checked'])}")
            else:
                label = tr("public API", "واجهة عامة")
                when = tr("check unavailable just now", "تعذّر الفحص حالياً")
        rows.append(f'<div class="r-ds-row"><span><span class="r-ds-dot" style="background:{colour.get(state, MUTED)}">'
                    f'</span>{escape(src)}</span><span class="when">{label} · {escape(when)}</span></div>')
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
        d = f'<div class="r-k-delta" style="color:{c}"><bdi dir="ltr">{delta:+.1f}</bdi>{delta_suffix}</div>'
    st.markdown(f'<div class="r-k"><div class="r-k-label">{escape(label)}</div><div class="r-k-value">{value}</div>'
                f'{d}<div class="r-k-note">{escape(note)}</div></div>', unsafe_allow_html=True)


# Alert sentences come from a few fixed templates in core/alerts.py; these are their Arabic versions.
_ALERT_AR = [
    (r"Year-on-year change of ([+-]?[\d.,]+)% is outside the historical 5th–95th percentile range\.",
     lambda m: f"التغير السنوي {sig(m[1] + '%')} خارج النطاق التاريخي المعتاد (بين المئين الخامس والخامس والتسعين)."),
    (r"Latest complete month is outside the seasonal-naive approximate 80% band\.",
     lambda m: "آخر شهر مكتمل خارج النطاق الموسمي المتوقع (نحو 80%)."),
    (r"Virtual-office share changed ([+-]?[\d.,]+) percentage points in six months\.",
     lambda m: f"تغيرت حصة المكاتب الافتراضية {sig(m[1])} نقطة مئوية خلال ستة أشهر."),
    (r"Renewal rate is ([\d.,]+) points below its previous three-year mean\.",
     lambda m: f"معدل التجديد أقل بـ {m[1]} نقطة من متوسطه في السنوات الثلاث السابقة."),
    (r"^([+-]?[\d.,]+)% to ([+-]?[\d.,]+)% YoY$", lambda m: f"{sig(m[1] + '%')} إلى {sig(m[2] + '%')} سنوياً"),
    (r"^([+-]?[\d.,]+)% YoY$", lambda m: f"{sig(m[1] + '%')} سنوياً"),
    (r"^([\d.,]+) to ([\d.,]+)$", lambda m: f"{m[1]} إلى {m[2]}"),
    (r"^([\d.,]+)% six months earlier$", lambda m: f"{m[1]}% قبل ستة أشهر"),
    (r"^3-year mean ([\d.,]+)%$", lambda m: f"متوسط 3 سنوات {m[1]}%"),
]


def alert_text(text: str) -> str:
    """Alert sentence in the current language (Arabic for the known templates, else unchanged)."""
    if not is_ar():
        return text
    for pat, fn in _ALERT_AR:
        m = re.fullmatch(pat, text.strip()) if pat.startswith("^") else re.search(pat, text)
        if m:
            return fn(m)
    return text


def alert_card(a: dict, compact: bool = True):
    c, lab = SEV.get(a["severity"], (MUTED, a["severity"]))
    if is_ar():
        lab = SEV_AR.get(a["severity"], lab)
    status = tr(" · acknowledged", " · تم الاستلام") if a.get("status") == "acknowledged" else ""
    if a.get("new"):
        status += f' · <span style="color:{BLACK}">' + tr("new since last sync", "جديد منذ آخر مزامنة") + "</span>"
    body = escape(alert_text(a["what_happened"]))
    if not compact:
        exp, act = escape(alert_text(a["expected"])), escape(alert_text(a["actual"]))
        body += (f'<br>المتوقع {exp}، والفعلي <b style="color:{BLACK}">{act}</b>' if is_ar() else
                 f'<br>Expected {exp}, actual <b style="color:{BLACK}">{act}</b>')
    title = f"{name(a['group'])}، {month(a['period'])}" if is_ar() else f"{a['group']}, {a['period']}"
    st.markdown(
        f'<div class="r-alert"><div class="r-alert-sev" style="color:{c}">{lab}{status}</div>'
        f'<div class="r-alert-title">{escape(title)}</div>'
        f'<div class="r-alert-body">{body}</div></div>', unsafe_allow_html=True)


def group_finding(gd: dict) -> str:
    """The one-line finding for a group comparison. In Arabic it is rebuilt from the same table,
    so the group's name uses the official Arabic spelling."""
    if not is_ar():
        return gd.get("finding_en", "")
    t = gd.get("table")
    if t is None or t.empty:
        return gd.get("finding_ar") or gd.get("finding_en", "")
    lead, fell, n = t.iloc[0], int((t["change_pct"] < 0).sum()), len(t)
    pct = sig(f"{lead['change_pct']:+.1f}%")
    if fell * 2 > n:  # most groups shrank: the top one is the most resilient, not "growing"
        return (f"تراجعت {fell} من أصل {n} فئات. الأكثر صموداً: {name(lead['group'])} "
                f"({pct} في النصف الأول 2026 مقارنة بالنصف الأول 2025).")
    return f"{name(lead['group'])}: {pct} في النصف الأول 2026 مقارنة بالنصف الأول 2025."
