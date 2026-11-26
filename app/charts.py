"""Plotly chart helpers — every chart in RASED goes through here (UAE Design System palette)."""
from __future__ import annotations

import textwrap

import pandas as pd
import plotly.graph_objects as go

from i18n import MONTHS_AR, is_ar, name, rtl, sig, tr

# UAE Design System colour tokens (designsystem.gov.ae/guidelines/colour-system)
GOLD, GOLD_DARK, GOLD_LIGHT, GOLD_BG = "#B68A35", "#92722A", "#F2ECCF", "#F9F7ED"  # AEGold 500/600/100/50
BLACK, MUTED, GREY = "#232528", "#5F646D", "#C3C6CB"                               # AEBlack 800/500/200
PAGE_BG = "#FCFCFC"
# Status: DS 500 shades for chart marks (3:1 graphics contrast); darker tones for text (4.5:1 AA)
GREEN, RED = "#4A9D5C", "#EA4F49"            # AEGreen 500, AERed 500 (graphics)
GREEN_TXT, RED_TXT = "#2F6B3B", "#B42318"    # darker text tones for AA contrast on white
SERIES = [GOLD, BLACK, GREEN, GOLD_DARK, GREY, "#CBA344", "#4B4F58", "#3E8E6E"]
SCEN_COL = {"A": RED, "B": GOLD, "C": GREEN, "custom": BLACK}
SCEN_NAME = {"A": "A · slow recovery", "B": "B · central", "C": "C · fast recovery", "custom": "Your scenario"}
SCEN_NAME_AR = {"A": "أ · تعافٍ بطيء", "B": "ب · المسار الأوسط", "C": "ج · تعافٍ سريع", "custom": "سيناريوك"}


def scen_name(s: str) -> str:
    return (SCEN_NAME_AR if is_ar() else SCEN_NAME)[s]
FONT = "Roboto, 'Noto Kufi Arabic', 'Segoe UI', Arial, sans-serif"  # DS body fonts
HEAD_FONT = "Inter, Alexandria, 'Segoe UI', Arial, sans-serif"      # DS heading fonts
SHOCK_START = "2026-03"


def dt(periods) -> pd.Series:
    """'YYYY-MM' or 'YYYY' strings -> timestamps (first day)."""
    s = pd.Series(periods).astype(str)
    return pd.to_datetime(s.where(s.str.len() > 4, s + "-01") + "-01")


def is_mobile() -> bool:
    """Phone browser? Read from this visitor's User-Agent, so each visitor gets charts sized for their screen."""
    try:
        import streamlit as st
        ua = st.context.headers.get("User-Agent") or ""
    except Exception:  # noqa: BLE001 - no browser session (tests, API): desktop layout
        return False
    return "Mobi" in ua or "iPhone" in ua


# Plotly's own date formatting in Arabic: month names on date axes and in hover headers.
# Digits stay Western (as on UAE government sites) and time still runs left to right.
AR_LOCALE = {"ar-ae-rased": {"dictionary": {}, "format": {
    "days": ["الأحد", "الاثنين", "الثلاثاء", "الأربعاء", "الخميس", "الجمعة", "السبت"],
    "shortDays": ["أحد", "اثنين", "ثلاثاء", "أربعاء", "خميس", "جمعة", "سبت"],
    "months": MONTHS_AR, "shortMonths": MONTHS_AR, "date": "%d/%m/%Y",
    "decimal": ".", "thousands": ",", "grouping": [3], "currency": ["", " د.إ"]}}}


def chart_config() -> dict:
    """Plotly toolbar on desktop; none on phones, where it covers the chart title. Arabic month names in Arabic."""
    cfg = {**CHART_CONFIG, "displayModeBar": False} if is_mobile() else dict(CHART_CONFIG)
    if is_ar():
        cfg.update(locale="ar-ae-rased", locales=AR_LOCALE)
    return cfg


def _wrap(text: str, width: int) -> list[str]:
    """Wrap to at most `width` characters, with lines of similar length (no lone last word)."""
    lines = textwrap.wrap(text, width) or [""]
    if len(lines) > 1:
        even = textwrap.wrap(text, -(-len(text) // len(lines)) + 4)
        if len(even) == len(lines):
            lines = even
    return lines


def _has_dates(fig: go.Figure) -> bool:
    for t in fig.data:
        x = getattr(t, "x", None)
        if x is not None and len(x) and hasattr(x[0], "year") and hasattr(x[0], "month"):
            return True
    return False


def style(fig: go.Figure, title: str = "", subtitle: str = "", height: int = 380, legend: bool = True) -> go.Figure:
    mobile, ar = is_mobile(), is_ar()
    if mobile:  # a phone chart is ~340px wide: wrap the title and subtitle instead of letting them run off the edge
        # Arabic (Kufi) glyphs are wider, so Arabic wraps sooner
        tl = _wrap(title, 30 if ar else 34) if title else []
        sl = _wrap(subtitle, 40 if ar else 46) if subtitle else []
        t = "<br>".join(f"<b>{rtl(x)}</b>" for x in tl) + "".join(
            f"<br><span style='font-size:12px;color:{MUTED};font-family:{FONT}'>{rtl(x)}</span>" for x in sl)
        top = 16 + 21 * len(tl) + 17 * len(sl) if (tl or sl) else 10
        height = height + max(0, top - (84 if subtitle else 60))
    else:  # long subtitles wrap too (Arabic runs wider), so nothing runs past the chart's edge
        # (charts can sit in half-width columns, ~600px: an Arabic title wraps after about 46 characters)
        tl = _wrap(title, 46 if ar else 72) if title else []
        sl = _wrap(subtitle, 78 if ar else 88) if subtitle else []
        t = "<br>".join(f"<b>{rtl(x)}</b>" for x in tl) + "".join(
            f"<br><span style='font-size:14px;color:{MUTED};font-family:{FONT}'>{rtl(x)}</span>" for x in sl)
        extra = 24 * max(0, len(tl) - 1) + 19 * max(0, len(sl) - 1)
        top = (84 if subtitle else 60) + extra
        height += extra
    fig.update_layout(
        # right-to-left: title and legend start from the right edge
        title=dict(text=t, x=1 if ar else 0, xanchor="right" if ar else "left", y=1 - 12 / height, yanchor="top",
                   font=dict(family=HEAD_FONT, size=15 if mobile else 18, color=BLACK)),
        font=dict(family=FONT, size=11 if mobile else 13, color=BLACK),
        paper_bgcolor=PAGE_BG, plot_bgcolor=PAGE_BG, height=height,
        margin=dict(l=4 if mobile else 10, r=8 if mobile else 20, t=top, b=10),
        showlegend=legend,
        legend=dict(orientation="h", yanchor="top", y=-0.12, xanchor="right" if ar else "left", x=1 if ar else 0,
                    bgcolor="rgba(0,0,0,0)", font=dict(size=11 if mobile else 12)),
        hoverlabel=dict(bgcolor="white", bordercolor=GOLD, font=dict(family=FONT, color=BLACK)),
        hovermode="x unified",
    )
    fig.update_xaxes(showgrid=False, showline=True, linecolor="#E1E3E5", ticks="outside", tickcolor="#E1E3E5",
                     tickfont=dict(color=MUTED))
    fig.update_yaxes(showgrid=True, gridcolor="#EFEFEF", zeroline=False, showline=False, tickfont=dict(color=MUTED))
    if _has_dates(fig):  # month and year in the hover header (Arabic month names via chart_config)
        fig.update_xaxes(hoverformat="%b %Y")
    return fig


def add_shock(fig: go.Figure, end: str = "2027-12", label: str | None = None) -> go.Figure:
    if label is None:
        label = (tr("Disruption from Mar 2026", "اضطراب منذ مارس 2026") if is_mobile() else
                 tr("Regional disruption from Mar 2026", "اضطراب إقليمي منذ مارس 2026"))
    x0, x1 = dt([SHOCK_START]).iloc[0], dt([end]).iloc[0]
    fig.add_shape(type="rect", xref="x", yref="paper", x0=x0, x1=x1, y0=0, y1=1,
                  fillcolor="rgba(200,16,46,0.06)", line_width=0, layer="below")
    fig.add_shape(type="line", xref="x", yref="paper", x0=x0, x1=x0, y0=0, y1=1,
                  line=dict(color=RED, width=1, dash="dot"))
    fig.add_annotation(x=x0, y=1, xref="x", yref="paper", text=label, showarrow=False, xanchor="right",
                       yanchor="top", xshift=-6, font=dict(size=11, color=RED))
    return fig


def registrations_chart(df: pd.DataFrame, title: str, subtitle: str = "", height: int = 400) -> go.Figure:
    """df: rows of get_series for zone groups (group = Mainland / Free Zone)."""
    fig = go.Figure()
    colors = {"Free Zone": GOLD, "Mainland": BLACK}
    for g, d in df.groupby("group", sort=False):
        d = d.sort_values("period")
        full = d[~d["is_partial"]]  # partial month left out: it looks like a crash to non-experts
        c = colors.get(g, GREEN)
        x = dt(full["period"])
        fig.add_trace(go.Scatter(x=x, y=full["value"], name=name(g), mode="lines",
                                 line=dict(color=c, width=3.5, shape="spline", smoothing=0.6),
                                 hovertemplate="%{y:,.0f}"))
        # end-of-line label: name + H1 2026 vs H1 2025 (same comparison used across the app)
        v = full["value"].to_numpy()
        per = full["period"]
        h26 = full[per.between("2026-01", "2026-06")]["value"].sum()
        h25 = full[per.between("2025-01", "2025-06")]["value"].sum()
        chg = (h26 / h25 - 1) * 100 if h25 else None
        fig.add_trace(go.Scatter(x=[x.iloc[-1]], y=[v[-1]], mode="markers", marker=dict(color=c, size=9),
                                 showlegend=False, hoverinfo="skip"))
        if chg is None:
            h1 = ""
        elif is_ar() and is_mobile():  # narrow phone margin: the number on one line, the period on the next
            h1 = f"{sig(f'{chg:+.0f}%')}<br>{rtl('النصف الأول 2026')}"
        else:
            h1 = tr(f"{chg:+.0f}% H1 2026", rtl(f"{sig(f'{chg:+.0f}%')} النصف الأول 2026"))
        lab = f"<b>{name(g)}</b>" + (f"<br><span style='color:{GREEN_TXT if chg >= 0 else RED_TXT}'>{h1}</span>"
                                     if chg is not None else "")
        fig.add_annotation(x=x.iloc[-1], y=v[-1], text=lab, showarrow=False, xanchor="left", xshift=8,
                           align="left", font=dict(size=11 if is_mobile() else 13, color=c))
    add_shock(fig, end=df[~df["is_partial"]]["period"].max())
    style(fig, title, subtitle, height, legend=False)
    fig.update_layout(margin=dict(r=(104 if is_ar() else 84) if is_mobile() else (150 if is_ar() else 110)))
    fig.update_yaxes(title=None, tickformat=",", rangemode="tozero")
    full = df[~df["is_partial"]]
    if not full.empty:  # stop the axis at the last month instead of an empty stretch to the next tick year
        fig.update_xaxes(range=[dt([full["period"].min()]).iloc[0],
                                dt([full["period"].max()]).iloc[0] + pd.DateOffset(days=20)])
    return fig


def bar_change(tab: pd.DataFrame, title: str, subtitle: str = "", height: int | None = None) -> go.Figure:
    t = tab.sort_values("change_pct")
    cols = [GREEN if v >= 0 else RED for v in t["change_pct"]]
    fig = go.Figure(go.Bar(x=t["change_pct"], y=t["group"], orientation="h", marker_color=cols,
                           customdata=[name(g) for g in t["group"]],
                           text=[f"{v:+.0f}%" for v in t["change_pct"]],
                           textposition=["outside" if v >= 0 else "inside" for v in t["change_pct"]],
                           insidetextanchor="start", textfont=dict(color=[BLACK if v >= 0 else "white" for v in t["change_pct"]]),
                           cliponaxis=False, hovertemplate="%{customdata}: %{x:+.1f}%<extra></extra>"))
    style(fig, title, subtitle, height or max(260, 46 * len(t) + 90), legend=False)
    fig.update_layout(hovermode="closest")
    fig.update_xaxes(ticksuffix="%", zeroline=True, zerolinecolor="#BDBDBD", showgrid=True, gridcolor="#F0F0F0")
    fig.update_yaxes(showgrid=False)
    if is_ar():  # category names in Arabic, on the right-hand side
        fig.update_yaxes(side="right", tickvals=list(t["group"]), ticktext=[name(g) for g in t["group"]])
    return fig


def sparkline(values, color=GOLD, height=60) -> go.Figure:
    fig = go.Figure(go.Scatter(y=list(values), mode="lines", line=dict(color=color, width=2.5, shape="spline"),
                               fill="tozeroy", fillcolor="rgba(182,138,53,0.12)", hoverinfo="skip"))
    fig.update_layout(height=height, margin=dict(l=0, r=0, t=0, b=0), paper_bgcolor="rgba(0,0,0,0)",
                      plot_bgcolor="rgba(0,0,0,0)", showlegend=False)
    fig.update_xaxes(visible=False)
    fig.update_yaxes(visible=False)
    return fig


def alert_chart(s: pd.DataFrame, period: str, color: str, unit: str = "") -> go.Figure:
    """Small chart for an alert: series, 'typical level' line, alert point highlighted."""
    s = s[~s["is_partial"]].sort_values("period")
    x = dt(s["period"])
    typical = s["value"].iloc[: max(len(s) // 3, 3)].mean()
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=x, y=s["value"], mode="lines", line=dict(color=BLACK, width=2.5, shape="spline"),
                             name=tr("Actual", "الفعلي"), hovertemplate="%{y:,.1f}" + unit))
    fig.add_hline(y=typical, line=dict(color=MUTED, dash="dash", width=1.2),
                  annotation_text=tr("typical level", "المستوى المعتاد"),
                  annotation_position="top right" if is_ar() else "top left",
                  annotation_font=dict(size=11, color=MUTED))
    hit = s[s["period"] == period]
    if not hit.empty:
        hx = dt(hit["period"]).iloc[0]
        fig.add_trace(go.Scatter(x=[hx], y=hit["value"], mode="markers+text", text=[tr("alert", "إنذار")],
                                 textposition="top center", textfont=dict(color=color, size=12),
                                 marker=dict(color=color, size=13, line=dict(color="white", width=2)),
                                 name=tr("Alert", "إنذار"), hoverinfo="skip"))
    style(fig, "", "", 230, legend=False)
    fig.update_layout(margin=dict(l=10, r=10, t=20, b=10), hovermode="closest")
    if unit == "%":
        fig.update_yaxes(ticksuffix="%")
    return fig


CHART_CONFIG = {"displaylogo": False, "modeBarButtonsToRemove": ["lasso2d", "select2d", "autoScale2d"]}
