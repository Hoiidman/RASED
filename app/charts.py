"""Plotly chart helpers — every chart in RASED goes through here (UAE Design System palette)."""
from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go

GOLD, GOLD_DARK, GOLD_LIGHT, GOLD_BG = "#B68A35", "#92722A", "#F2ECCF", "#F9F7ED"
BLACK, MUTED, GREEN, RED, GREY = "#232528", "#5F6368", "#006B48", "#C8102E", "#B9BBBE"
SERIES = [GOLD, BLACK, GREEN, GOLD_DARK, GREY, "#C9A86A", "#4E5257", "#3E8E6E"]
SCEN_COL = {"A": RED, "B": GOLD, "C": GREEN, "custom": BLACK}
SCEN_NAME = {"A": "A · slow recovery", "B": "B · central", "C": "C · fast recovery", "custom": "Your scenario"}
FONT = "Inter, 'Segoe UI', 'Noto Sans Arabic', Arial, sans-serif"
SHOCK_START = "2026-03"


def dt(periods) -> pd.Series:
    """'YYYY-MM' or 'YYYY' strings -> timestamps (first day)."""
    s = pd.Series(periods).astype(str)
    return pd.to_datetime(s.where(s.str.len() > 4, s + "-01") + "-01")


def style(fig: go.Figure, title: str = "", subtitle: str = "", height: int = 380, legend: bool = True) -> go.Figure:
    t = f"<b>{title}</b>" + (f"<br><span style='font-size:13px;color:{MUTED}'>{subtitle}</span>" if subtitle else "")
    fig.update_layout(
        title=dict(text=t, x=0, xanchor="left", y=0.97, yanchor="top", font=dict(size=17, color=BLACK)),
        font=dict(family=FONT, size=13, color=BLACK),
        paper_bgcolor="white", plot_bgcolor="white", height=height,
        margin=dict(l=10, r=20, t=78 if subtitle else 56, b=10),
        showlegend=legend,
        legend=dict(orientation="h", yanchor="top", y=-0.12, xanchor="left", x=0, bgcolor="rgba(0,0,0,0)",
                    font=dict(size=12)),
        hoverlabel=dict(bgcolor="white", bordercolor=GOLD, font=dict(family=FONT, color=BLACK)),
        hovermode="x unified",
    )
    fig.update_xaxes(showgrid=False, showline=True, linecolor="#D9D9D9", ticks="outside", tickcolor="#D9D9D9",
                     tickfont=dict(color=MUTED))
    fig.update_yaxes(showgrid=True, gridcolor="#F0F0F0", zeroline=False, showline=False, tickfont=dict(color=MUTED))
    return fig


def add_shock(fig: go.Figure, end: str = "2027-12", label: str = "Regional disruption from Mar 2026") -> go.Figure:
    x0, x1 = dt([SHOCK_START]).iloc[0], dt([end]).iloc[0]
    fig.add_shape(type="rect", xref="x", yref="paper", x0=x0, x1=x1, y0=0, y1=1,
                  fillcolor="rgba(200,16,46,0.06)", line_width=0, layer="below")
    fig.add_shape(type="line", xref="x", yref="paper", x0=x0, x1=x0, y0=0, y1=1,
                  line=dict(color=RED, width=1, dash="dot"))
    fig.add_annotation(x=x0, y=1, xref="x", yref="paper", text=label, showarrow=False, xanchor="left",
                       yanchor="top", xshift=6, font=dict(size=11, color=RED))
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
        fig.add_trace(go.Scatter(x=x, y=full["value"], name=g, mode="lines",
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
        lab = f"<b>{g}</b>" + (f"<br><span style='color:{GREEN if chg >= 0 else RED}'>{chg:+.0f}% H1 2026</span>"
                               if chg is not None else "")
        fig.add_annotation(x=x.iloc[-1], y=v[-1], text=lab, showarrow=False, xanchor="left", xshift=10,
                           align="left", font=dict(size=13, color=c))
    add_shock(fig, end=df[~df["is_partial"]]["period"].max())
    style(fig, title, subtitle, height, legend=False)
    fig.update_layout(margin=dict(r=110))
    fig.update_yaxes(title=None, tickformat=",", rangemode="tozero")
    return fig


def bar_change(tab: pd.DataFrame, title: str, subtitle: str = "", height: int | None = None) -> go.Figure:
    t = tab.sort_values("change_pct")
    cols = [GREEN if v >= 0 else RED for v in t["change_pct"]]
    fig = go.Figure(go.Bar(x=t["change_pct"], y=t["group"], orientation="h", marker_color=cols,
                           text=[f"{v:+.0f}%" for v in t["change_pct"]], textposition="outside",
                           cliponaxis=False, hovertemplate="%{y}: %{x:+.1f}%<extra></extra>"))
    style(fig, title, subtitle, height or max(260, 46 * len(t) + 90), legend=False)
    fig.update_layout(hovermode="closest")
    fig.update_xaxes(ticksuffix="%", zeroline=True, zerolinecolor="#BDBDBD", showgrid=True, gridcolor="#F0F0F0")
    fig.update_yaxes(showgrid=False)
    return fig


def sparkline(values, color=GOLD, height=60) -> go.Figure:
    fig = go.Figure(go.Scatter(y=list(values), mode="lines", line=dict(color=color, width=2.5, shape="spline"),
                               fill="tozeroy", fillcolor="rgba(182,138,53,0.12)", hoverinfo="skip"))
    fig.update_layout(height=height, margin=dict(l=0, r=0, t=0, b=0), paper_bgcolor="rgba(0,0,0,0)",
                      plot_bgcolor="rgba(0,0,0,0)", showlegend=False)
    fig.update_xaxes(visible=False)
    fig.update_yaxes(visible=False)
    return fig


CHART_CONFIG = {"displaylogo": False, "modeBarButtonsToRemove": ["lasso2d", "select2d", "autoScale2d"]}
