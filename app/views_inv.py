"""Investor portal pages (owner: Agent B). Warmer layout, more text, fewer controls."""
from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import backend as be
import charts as ch
import ui
from core import ai
from labels import LANG, TITLES, TITLES_AR

PC = ch.CHART_CONFIG


def _title(page):
    t, q = (TITLES_AR if LANG["v"] == "ar" else TITLES)[page]
    ui.page_title(t, q)


def _plot(fig):
    st.plotly_chart(fig, width="stretch", config=PC)


def _activity_monthly():
    df = be.get_series(["new_reg_total"], group_type="activity", start="2024-01")
    return df[~df["is_partial"]]


def _shrinking(table) -> bool:
    """True when most groups fell, so the leaders are the most resilient rather than "growing"."""
    return bool(len(table)) and int((table["change_pct"] < 0).sum()) * 2 > len(table)


def _competition(n):
    return "high" if n > 1200 else "moderate" if n > 600 else "low"


# ------------------------------------------------------------------ Opportunities
def opportunities(lang):
    _title("opportunities")
    st.caption("Based on public licence data from Ajman DED and Ajman Free Zone, updated automatically.")
    act = be.group_differences("activity")["table"]
    mon = _activity_monthly()
    top = act.head(4)
    if _shrinking(act):
        fell = int((act["change_pct"] < 0).sum())
        ui.section(f"Most resilient sectors, H1 2026 vs H1 2025 ({fell} of {len(act)} sectors fell)")
    else:
        ui.section("Fastest-growing sectors, H1 2026 vs H1 2025")
    cols = st.columns(4, gap="large")
    for col, (_, r) in zip(cols, top.iterrows()):
        s = mon[mon["group"] == r["group"]].sort_values("period")
        last12 = int(s["value"].tail(12).sum())
        with col:
            ui.kpi(r["group"], f"{r['change_pct']:+.0f}%", None,
                   f"Competition {_competition(last12)}: {last12:,} new licences in 12 months")
            st.plotly_chart(ch.sparkline(s["value"].tail(18)), width="stretch", config={"displayModeBar": False})

    c1, c2 = st.columns(2, gap="large")
    with c1:
        area = be.group_differences("area")
        at = area["table"]
        overall = (at["H1 2026"].sum() / at["H1 2025"].sum() - 1) * 100
        where = "Where demand is holding up best" if _shrinking(at) else "Where demand is growing"
        fig = ch.bar_change(at, f"{where} (Ajman overall {overall:+.0f}%)",
                            area["finding_en"], height=430)
        fig.add_vline(x=overall, line=dict(color=ch.MUTED, dash="dot", width=1.5))
        fig.add_annotation(x=overall, y=1.0, yref="paper", text="Ajman overall", showarrow=False,
                           yanchor="bottom", font=dict(size=11, color=ch.MUTED))
        _plot(fig)
    with c2:
        vo = be.get_series(["virtual_office_share"], start="2024-01")
        vo = vo[~vo["is_partial"]]
        fig = go.Figure(go.Scatter(x=ch.dt(vo["period"]), y=vo["value"], mode="lines", fill="tozeroy",
                                   line=dict(color=ch.GOLD, width=3, shape="spline"),
                                   fillcolor="rgba(182,138,53,0.15)", hovertemplate="%{y:.0f}%"))
        ch.style(fig, "Most new Free Zone firms now start with a virtual office",
                 "Share of new Free Zone registrations using a virtual office", 430, legend=False)
        fig.update_yaxes(ticksuffix="%", range=[0, 70])
        _plot(fig)
    zone = be.get_series(["new_reg_total"], group_type="zone", start="2024-01")
    _plot(ch.registrations_chart(zone, "Mainland or Free Zone? Free Zone is growing faster in 2026",
                                 "New business registrations per month", height=380))


# ------------------------------------------------------------------ Watch-outs
def watchouts(lang):
    _title("watchouts")
    act = be.group_differences("activity")["table"]
    c1, c2 = st.columns(2, gap="large")
    with c1:
        cool = act.tail(4)
        _plot(ch.bar_change(cool, "Sectors that are cooling",
                            ("Biggest falls" if _shrinking(act) else "Lowest growth") + ", H1 2026 vs H1 2025",
                            height=330))
    with c2:
        tot = be.get_series(["new_reg_total"], start="2023-01", end="2025-12")
        tot = tot.assign(m=tot["period"].str[5:7].astype(int))
        idx = tot.groupby("m")["value"].mean()
        idx = (idx / idx.mean() * 100).round(0)
        months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
        cols = [ch.RED if v < 92 else ch.GOLD for v in idx.values]
        fig = go.Figure(go.Bar(x=months, y=idx.values, marker_color=cols, text=[f"{v:.0f}" for v in idx.values],
                               textposition="outside", cliponaxis=False, hovertemplate="%{x}: %{y:.0f}<extra></extra>"))
        fig.add_hline(y=100, line=dict(color=ch.MUTED, dash="dot", width=1))
        ch.style(fig, "Seasonality: slower months for new businesses",
                 "Average registrations by month (100 = an average month)", 330, legend=False)
        fig.update_layout(hovermode="closest")
        _plot(fig)
    ui.section("What to keep in mind")
    a, b, c = st.columns(3, gap="large")
    a.markdown("**Current outlook.** Mainland activity slowed after the regional disruption that began in March 2026. "
               "The central scenario expects a gradual recovery over the next 6 to 12 months. The Free Zone has held up.")
    b.markdown("**Timing.** Ramadan, Eid, July and August are the slowest months. Plan launch dates and cash flow "
               "around them.")
    c.markdown("**Costs and renewals.** Virtual offices keep fixed costs low. Budget for the annual licence renewal; "
               "DED sends reminders and sometimes offers instalments.")
    st.caption("Indicative, based on public data. Not financial advice.")


def _vo_share():
    """Latest full-month virtual-office share of Free Zone registrations, from the data."""
    vo = be.get_series(["virtual_office_share"])
    vo = vo[~vo["is_partial"]].sort_values("period")
    return round(float(vo["value"].iloc[-1]), 1) if not vo.empty else None


# ------------------------------------------------------------------ Advisor
def advisor(lang):
    _title("advisor")
    # dropdowns come from whatever the engine has (real activity / area names, or the mock lists)
    acts = sorted(be.group_differences("activity")["table"]["group"].tolist())
    areas = sorted(be.group_differences("area")["table"]["group"].tolist())
    pick = next((i for i, a in enumerate(acts) if "restaurant" in a.lower() or "trading" in a.lower()), 0)
    with st.form("advisor", border=False):
        c1, c2, c3, c4 = st.columns(4)
        activity = c1.selectbox("Business activity", acts, index=pick)
        area = c2.selectbox("Area", areas, index=0)
        zone = c3.selectbox("Setup", ["Mainland", "Free Zone"])
        size = c4.selectbox("Size", ["Micro (1–5)", "Small (6–20)", "Medium (21–100)"])
        notes = st.text_area("Your plans (optional)", "Family restaurant, 40 seats, delivery focus",
                             max_chars=400)
        go_ = st.form_submit_button("Get my outlook", type="primary")
    if not go_ and "inv_res" not in st.session_state:
        st.caption("Describe your business above, then press Get my outlook.")
        return
    if go_:
        act = be.group_differences("activity")["table"].set_index("group")
        ar = be.group_differences("area")["table"].set_index("group")
        zt = be.group_differences("zone")["table"].set_index("group")
        mon = _activity_monthly()
        area_df = be.get_series(["new_reg_total"], group_type="area")
        area_12 = int(area_df[(area_df["group"] == area) & ~area_df["is_partial"]].sort_values("period")["value"].tail(12).sum())
        comp = be.get_competitors(activity, area)
        new_12 = int(mon[mon["group"] == activity]["value"].tail(12).sum())
        facts = {"sector_growth_pct": float(act.loc[activity, "change_pct"]) if activity in act.index else None,
                 "area_growth_pct": float(ar.loc[area, "change_pct"]) if area in ar.index else None,
                 "new_businesses_all_sectors_in_area_last_12_months": area_12, "competition_level": _competition(area_12 * 0.6),
                 "zone_change_pct": float(zt.loc[zone, "change_pct"]) if zone in zt.index else None,
                 "virtual_office_share_fz_pct": _vo_share(),
                 "source": "Ajman DED & Free Zone data, H1 2026 vs H1 2025 (activity and area figures are mainland only)"}
        if activity in act.index:  # where this sector sits, so a fall is read against the whole market
            facts["sector_rank_by_change"] = f"{list(act.index).index(activity) + 1} of {len(act)} sectors"
            facts["sectors_that_fell_h1_2026"] = f"{int((act['change_pct'] < 0).sum())} of {len(act)}"
        if comp:  # saturation risk from DED's public register; replaces the all-sector competition guess
            facts.update({
                "competition_level": comp["level"],
                "same_activity_licences_in_area (DED register to Mar 2024, may include inactive)": comp["in_area"]
                if comp["in_area"] is not None else "fewer than 5",
                "area_rank_for_this_activity": f"{comp['rank']} of {comp['areas']} areas" if comp["rank"] else "not in the top areas",
                "same_activity_licences_in_ajman (same register)": comp["ajman"],
                "new_licences_in_this_activity_last_12_months_ajman": new_12,
                "usual_licence_type": f"{comp['licence_type']} ({comp['licence_type_share']}% of this activity)"})
        profile = {"activity": activity, "area": area, "zone": zone, "size": size, "notes": notes}
        with st.spinner("Building your outlook"):
            res = ai.advise("investor", facts, profile, lang)
        st.session_state.inv_res = (activity, area, zone, facts, res, mon[mon["group"] == activity].sort_values("period"),
                                    comp)
    saved = st.session_state.inv_res
    activity, area, zone, facts, res, s, comp = saved if len(saved) == 7 else (*saved, None)

    m1, m2, m3 = st.columns(3)
    m1.metric(f"{activity} growth", f"{facts['sector_growth_pct']:+.1f}%" if facts["sector_growth_pct"] is not None else "n/a")
    m2.metric(f"{area} demand growth", f"{facts['area_growth_pct']:+.1f}%" if facts["area_growth_pct"] is not None else "n/a")
    if comp:
        here = f"{comp['in_area']:,}" if comp["in_area"] is not None else "fewer than 5"
        where = f", rank {comp['rank']} of {comp['areas']} areas" if comp["rank"] else ""
        m3.metric(f"Saturation risk in {area}", comp["level"].capitalize(),
                  f"{here} {activity.lower()} licences here{where}", delta_color="off")
    else:
        m3.metric(f"Competition in {area}", facts["competition_level"].capitalize(),
                  f"{facts['new_businesses_all_sectors_in_area_last_12_months']:,} new businesses in the area / 12 mo", delta_color="off")
    c1, c2 = st.columns([1.2, 1], gap="large")
    with c1:
        fc = be.get_forecast("new_reg_total")
        tot = be.get_series(["new_reg_total"])
        tot = tot[~tot["is_partial"]].set_index("period")["value"]
        share = (s.set_index("period")["value"].tail(6).sum() / tot.tail(6).sum())
        sm = s.assign(v=s["value"].rolling(3, min_periods=1).mean())
        piv = fc.pivot(index="period", columns="scenario", values="mean") * share
        piv = piv.rolling(3, min_periods=1).mean()
        lo, hi = piv[["A", "B", "C"]].min(axis=1), piv[["A", "B", "C"]].max(axis=1)
        lx, ly = ch.dt(sm["period"]).iloc[-1], sm["v"].iloc[-1]
        xf = pd.concat([pd.Series([lx]), ch.dt(pd.Series(piv.index))], ignore_index=True)
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=pd.concat([xf, xf[::-1]]),
                                 y=pd.concat([pd.Series([ly]), lo, hi[::-1], pd.Series([ly])], ignore_index=True),
                                 fill="toself", fillcolor="rgba(182,138,53,0.18)", line=dict(width=0),
                                 name="Range: slow to fast recovery", hoverinfo="skip"))
        fig.add_trace(go.Scatter(x=ch.dt(sm["period"]), y=sm["v"], name="Actual (3-month average)", mode="lines",
                                 line=dict(color=ch.BLACK, width=3, shape="spline"), hovertemplate="%{y:,.0f}"))
        fig.add_trace(go.Scatter(x=xf, y=pd.concat([pd.Series([ly]), piv["B"]], ignore_index=True),
                                 name="Central outlook", mode="lines",
                                 line=dict(color=ch.GOLD, width=3, dash="dash", shape="spline"), hovertemplate="%{y:,.0f}"))
        ch.add_shock(fig, end=s["period"].max())
        ch.style(fig, f"{activity}: demand outlook in Ajman",
                 "New licences per month for the whole sector, not a forecast of your business", 400)
        fig.update_yaxes(tickformat=",")
        _plot(fig)
    with c2:
        st.markdown(res["text"])
        if comp:
            st.caption(f"Saturation compares how many {activity.lower()} licences each area holds on DED's public "
                       f"register ({comp['ajman']:,} across Ajman). The register's activity list runs to "
                       f"{ui.month_label(comp['through'])} and may include licences no longer active, so read it as "
                       f"how crowded {area} is relative to other areas, not an exact count. Most {activity.lower()} "
                       f"businesses hold a {comp['licence_type'].lower()} ({comp['licence_type_share']}%).")
        st.caption("Indicative, based on public data. Not financial advice. "
                   "Forecasts cover the whole sector and area, not your business.")
        st.caption(f"Engine: {res['engine']}. Facts used: " + "; ".join(res["cited_facts"]))


PAGES = {"opportunities": opportunities, "watchouts": watchouts, "advisor": advisor}


def render(page: str, lang: str):
    PAGES[page](lang)
