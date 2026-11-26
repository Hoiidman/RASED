"""Investor portal pages (owner: Agent B). Warmer layout, more text, fewer controls.

Text is bilingual through i18n.tr(en, ar); data names keep their English values for lookups and are
translated only for display, through i18n.name().
"""
from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import backend as be
import charts as ch
import ui
from core import ai
from i18n import MONTHS_AR, MONTHS_EN, is_ar, lang as cur_lang, month, name, name_ar, sig, tr
from labels import TITLES, TITLES_AR

PC = ch.CHART_CONFIG
LEVEL_AR = {"high": "مرتفع", "moderate": "متوسط", "low": "منخفض"}       # خطر (risk), masculine
COMP_AR = {"high": "مرتفعة", "moderate": "متوسطة", "low": "منخفضة"}       # منافسة (competition), feminine
ZONES = {"Mainland": "البر الرئيسي", "Free Zone": "المنطقة الحرة"}
SIZES = {"Micro (1–5)": "متناهية الصغر (1–5)", "Small (6–20)": "صغيرة (6–20)", "Medium (21–100)": "متوسطة (21–100)"}


def _title(page):
    t, q = (TITLES_AR if is_ar() else TITLES)[page]
    ui.page_title(t, q)


def _plot(fig):
    st.plotly_chart(fig, width="stretch", config=ch.chart_config())


def _level(lvl: str) -> str:
    return LEVEL_AR.get(lvl, lvl) if is_ar() else lvl


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
    st.caption(tr("Based on public licence data from Ajman DED and Ajman Free Zone, updated automatically.",
                  "مبني على بيانات الرخص العامة من دائرة التنمية الاقتصادية والمنطقة الحرة في عجمان، ويُحدّث تلقائياً."))
    act = be.group_differences("activity")["table"]
    mon = _activity_monthly()
    top = act.head(4)
    if _shrinking(act):
        fell = int((act["change_pct"] < 0).sum())
        ui.section(tr(f"Most resilient sectors, H1 2026 vs H1 2025 ({fell} of {len(act)} sectors fell)",
                      f"القطاعات الأكثر صموداً، النصف الأول 2026 مقارنة بـ 2025 (تراجع {fell} من {len(act)} قطاعات)"))
    else:
        ui.section(tr("Fastest-growing sectors, H1 2026 vs H1 2025",
                      "القطاعات الأسرع نمواً، النصف الأول 2026 مقارنة بـ 2025"))
    cols = st.columns(4, gap="large")
    for col, (_, r) in zip(cols, top.iterrows()):
        s = mon[mon["group"] == r["group"]].sort_values("period")
        last12 = int(s["value"].tail(12).sum())
        lvl = _competition(last12)
        with col:
            ui.kpi(name(r["group"]), f"{r['change_pct']:+.0f}%", None,
                   tr(f"Competition {lvl}: {last12:,} new licences in 12 months",
                      f"المنافسة {COMP_AR.get(lvl, lvl)}: {last12:,} رخصة جديدة خلال 12 شهراً"))
            st.plotly_chart(ch.sparkline(s["value"].tail(18)), width="stretch", config={"displayModeBar": False})

    c1, c2 = st.columns(2, gap="large")
    with c1:
        area = be.group_differences("area")
        at = area["table"]
        overall = (at["H1 2026"].sum() / at["H1 2025"].sum() - 1) * 100
        if is_ar():
            where = "أين يصمد الطلب أكثر" if _shrinking(at) else "أين ينمو الطلب"
            title = f"{where} (عجمان إجمالاً {sig(f'{overall:+.0f}%')})"
        else:
            where = "Where demand is holding up best" if _shrinking(at) else "Where demand is growing"
            title = f"{where} (Ajman overall {overall:+.0f}%)"
        fig = ch.bar_change(at, title, ui.group_finding(area), height=430)
        fig.add_vline(x=overall, line=dict(color=ch.MUTED, dash="dot", width=1.5))
        fig.add_annotation(x=overall, y=1.0, yref="paper", text=tr("Ajman overall", "عجمان إجمالاً"), showarrow=False,
                           yanchor="bottom", font=dict(size=11, color=ch.MUTED))
        _plot(fig)
    with c2:
        vo = be.get_series(["virtual_office_share"], start="2024-01")
        vo = vo[~vo["is_partial"]]
        fig = go.Figure(go.Scatter(x=ch.dt(vo["period"]), y=vo["value"], mode="lines", fill="tozeroy",
                                   line=dict(color=ch.GOLD, width=3, shape="spline"),
                                   fillcolor="rgba(182,138,53,0.15)", hovertemplate="%{y:.0f}%"))
        ch.style(fig, tr("Most new Free Zone firms now start with a virtual office",
                         "معظم الشركات الجديدة في المنطقة الحرة تبدأ الآن بمكتب افتراضي"),
                 tr("Share of new Free Zone registrations using a virtual office",
                    "نسبة التسجيلات الجديدة في المنطقة الحرة التي تستخدم مكتباً افتراضياً"), 430, legend=False)
        fig.update_yaxes(ticksuffix="%", range=[0, 70])
        _plot(fig)
    zone = be.get_series(["new_reg_total"], group_type="zone", start="2024-01")
    _plot(ch.registrations_chart(zone, tr("Mainland or Free Zone? Free Zone is growing faster in 2026",
                                          "البر الرئيسي أم المنطقة الحرة؟ المنطقة الحرة تنمو أسرع في 2026"),
                                 tr("New business registrations per month", "تسجيلات الأعمال الجديدة شهرياً"),
                                 height=380))


# ------------------------------------------------------------------ Watch-outs
def watchouts(lang):
    _title("watchouts")
    act = be.group_differences("activity")["table"]
    c1, c2 = st.columns(2, gap="large")
    with c1:
        cool = act.tail(4)
        sub = (tr("Biggest falls", "أكبر التراجعات") if _shrinking(act) else tr("Lowest growth", "أدنى نمو"))
        _plot(ch.bar_change(cool, tr("Sectors that are cooling", "قطاعات تتباطأ"),
                            sub + tr(", H1 2026 vs H1 2025", "، النصف الأول 2026 مقارنة بـ 2025"), height=330))
    with c2:
        tot = be.get_series(["new_reg_total"], start="2023-01", end="2025-12")
        tot = tot.assign(m=tot["period"].str[5:7].astype(int))
        idx = tot.groupby("m")["value"].mean()
        idx = (idx / idx.mean() * 100).round(0)
        months = MONTHS_AR if is_ar() else MONTHS_EN
        cols = [ch.RED if v < 92 else ch.GOLD for v in idx.values]
        fig = go.Figure(go.Bar(x=months, y=idx.values, marker_color=cols, text=[f"{v:.0f}" for v in idx.values],
                               textposition="outside", cliponaxis=False, hovertemplate="%{x}: %{y:.0f}<extra></extra>"))
        fig.add_hline(y=100, line=dict(color=ch.MUTED, dash="dot", width=1))
        ch.style(fig, tr("Seasonality: slower months for new businesses", "الموسمية: الأشهر الأبطأ للأعمال الجديدة"),
                 tr("Average registrations by month (100 = an average month)",
                    "متوسط التسجيلات حسب الشهر (100 = شهر عادي)"), 330, legend=False)
        fig.update_layout(hovermode="closest")
        _plot(fig)
    ui.section(tr("What to keep in mind", "ما ينبغي مراعاته"))
    a, b, c = st.columns(3, gap="large")
    a.markdown(tr("**Current outlook.** Mainland activity slowed after the regional disruption that began in March 2026. "
                  "The central scenario expects a gradual recovery over the next 6 to 12 months. The Free Zone has held up.",
                  "**الوضع الحالي.** تباطأ نشاط البر الرئيسي بعد الاضطراب الإقليمي الذي بدأ في مارس 2026. "
                  "ويتوقع السيناريو الأوسط تعافياً تدريجياً خلال 6 إلى 12 شهراً. وحافظت المنطقة الحرة على أدائها."))
    b.markdown(tr("**Timing.** Ramadan, Eid, July and August are the slowest months. Plan launch dates and cash flow "
                  "around them.",
                  "**التوقيت.** رمضان والعيد ويوليو وأغسطس هي الأشهر الأبطأ. خطّط لموعد الافتتاح والسيولة على هذا الأساس."))
    c.markdown(tr("**Costs and renewals.** Virtual offices keep fixed costs low. Budget for the annual licence renewal; "
                  "DED sends reminders and sometimes offers instalments.",
                  "**التكاليف والتجديد.** المكاتب الافتراضية تُبقي التكاليف الثابتة منخفضة. خصّص ميزانية للتجديد السنوي "
                  "للرخصة؛ ترسل الدائرة رسائل تذكير وتتيح التقسيط أحياناً."))
    st.caption(tr("Indicative, based on public data. Not financial advice.",
                  "استرشادي، مبني على بيانات عامة. ليس نصيحة مالية."))


def _vo_share():
    """Latest full-month virtual-office share of Free Zone registrations, from the data."""
    vo = be.get_series(["virtual_office_share"])
    vo = vo[~vo["is_partial"]].sort_values("period")
    return round(float(vo["value"].iloc[-1]), 1) if not vo.empty else None


# ------------------------------------------------------------------ Advisor
def advisor(lang):
    _title("advisor")
    # dropdowns come from whatever the engine has (real activity / area names, or the mock lists)
    acts = sorted(be.group_differences("activity")["table"]["group"].tolist(), key=name)
    areas = sorted(be.group_differences("area")["table"]["group"].tolist(), key=name)
    pick = next((i for i, a in enumerate(acts) if "restaurant" in a.lower() or "trading" in a.lower()), 0)
    res_key = f"inv_res_{cur_lang()}"  # one answer per language, so switching language never shows the other one
    with st.form("advisor", border=False):
        c1, c2, c3, c4 = st.columns(4)
        activity = c1.selectbox(tr("Business activity", "النشاط التجاري"), acts, index=pick, format_func=name)
        area = c2.selectbox(tr("Area", "المنطقة"), areas, index=0, format_func=name)
        zone = c3.selectbox(tr("Setup", "مكان التأسيس"), list(ZONES), format_func=lambda z: ZONES[z] if is_ar() else z)
        size = c4.selectbox(tr("Size", "الحجم"), list(SIZES), format_func=lambda z: SIZES[z] if is_ar() else z)
        notes = st.text_area(tr("Your plans (optional)", "خططك (اختياري)"),
                             tr("Family restaurant, 40 seats, delivery focus", "مطعم عائلي، 40 مقعداً، مع تركيز على التوصيل"),
                             max_chars=400)
        go_ = st.form_submit_button(tr("Get my outlook", "اعرض توقعاتي"), type="primary")
    if not go_ and res_key not in st.session_state:
        st.caption(tr("Describe your business above, then press Get my outlook.",
                      "صف نشاطك أعلاه، ثم اضغط اعرض توقعاتي."))
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
        if is_ar():  # official Arabic names, so an Arabic answer uses the register's spelling
            profile.update(activity_ar=name_ar(activity), area_ar=name_ar(area), zone_ar=ZONES.get(zone, zone))
        with st.spinner(tr("Building your outlook", "جارٍ إعداد توقعاتك")):
            res = ai.advise("investor", facts, profile, cur_lang())
        st.session_state[res_key] = (activity, area, zone, facts, res,
                                     mon[mon["group"] == activity].sort_values("period"), comp)
    saved = st.session_state[res_key]
    activity, area, zone, facts, res, s, comp = saved if len(saved) == 7 else (*saved, None)
    a_n, r_n = name(activity), name(area)

    m1, m2, m3 = st.columns(3)
    pct = lambda v: f"{v:+.1f}%" if v is not None else tr("n/a", "غير متاح")  # noqa: E731
    m1.metric(tr(f"{activity} growth", f"نمو {a_n}"), pct(facts["sector_growth_pct"]))
    m2.metric(tr(f"{area} demand growth", f"نمو الطلب في {r_n}"), pct(facts["area_growth_pct"]))
    if comp:
        here = f"{comp['in_area']:,}" if comp["in_area"] is not None else tr("fewer than 5", "أقل من 5")
        if is_ar():
            where = f"، المرتبة {comp['rank']} من {comp['areas']} منطقة" if comp["rank"] else ""
            m3.metric(f"خطر التشبع في {r_n}", _level(comp["level"]), f"{here} رخصة {a_n} هنا{where}", delta_color="off")
        else:
            where = f", rank {comp['rank']} of {comp['areas']} areas" if comp["rank"] else ""
            m3.metric(f"Saturation risk in {area}", comp["level"].capitalize(),
                      f"{here} {activity.lower()} licences here{where}", delta_color="off")
    else:
        n12 = facts["new_businesses_all_sectors_in_area_last_12_months"]
        m3.metric(tr(f"Competition in {area}", f"المنافسة في {r_n}"),
                  COMP_AR.get(facts["competition_level"]) if is_ar() else facts["competition_level"].capitalize(),
                  tr(f"{n12:,} new businesses in the area / 12 mo", f"{n12:,} منشأة جديدة في المنطقة خلال 12 شهراً"),
                  delta_color="off")
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
                                 name=tr("Range: slow to fast recovery", "النطاق: من التعافي البطيء إلى السريع"),
                                 hoverinfo="skip"))
        fig.add_trace(go.Scatter(x=ch.dt(sm["period"]), y=sm["v"], name=tr("Actual (3-month average)",
                                                                           "الفعلي (متوسط 3 أشهر)"), mode="lines",
                                 line=dict(color=ch.BLACK, width=3, shape="spline"), hovertemplate="%{y:,.0f}"))
        fig.add_trace(go.Scatter(x=xf, y=pd.concat([pd.Series([ly]), piv["B"]], ignore_index=True),
                                 name=tr("Central outlook", "التوقع الأوسط"), mode="lines",
                                 line=dict(color=ch.GOLD, width=3, dash="dash", shape="spline"), hovertemplate="%{y:,.0f}"))
        ch.add_shock(fig, end=s["period"].max())
        ch.style(fig, tr(f"{activity}: demand outlook in Ajman", f"{a_n}: توقعات الطلب في عجمان"),
                 tr("New licences per month for the whole sector, not a forecast of your business",
                    "الرخص الجديدة شهرياً للقطاع كله، وليست توقعاً لعملك"), 400)
        fig.update_yaxes(tickformat=",")
        _plot(fig)
    with c2:
        st.markdown(res["text"])
        if comp:
            if is_ar():
                st.caption(f"يقارن التشبع عدد رخص {a_n} في كل منطقة وفق السجل العام للدائرة "
                           f"({comp['ajman']:,} في عجمان كلها). تمتد قائمة الأنشطة في السجل حتى "
                           f"{month(comp['through'])} وقد تشمل رخصاً لم تعد سارية، لذا اقرأها مقياساً لمدى ازدحام "
                           f"{r_n} مقارنة بالمناطق الأخرى، لا عدداً دقيقاً. معظم منشآت هذا النشاط تحمل "
                           f"{name(comp['licence_type'])} ({comp['licence_type_share']}%).")
            else:
                st.caption(f"Saturation compares how many {activity.lower()} licences each area holds on DED's public "
                           f"register ({comp['ajman']:,} across Ajman). The register's activity list runs to "
                           f"{ui.month_label(comp['through'])} and may include licences no longer active, so read it as "
                           f"how crowded {area} is relative to other areas, not an exact count. Most {activity.lower()} "
                           f"businesses hold a {comp['licence_type'].lower()} ({comp['licence_type_share']}%).")
        st.caption(tr("Indicative, based on public data. Not financial advice. "
                      "Forecasts cover the whole sector and area, not your business.",
                      "استرشادي، مبني على بيانات عامة. ليس نصيحة مالية. "
                      "تغطي التوقعات القطاع والمنطقة كاملين، لا عملك تحديداً."))
        st.caption(tr(f"Engine: {res['engine']}. Facts used: ", f"المحرك: {res['engine']}. الحقائق المستخدمة: ")
                   + "; ".join(res["cited_facts"]))


PAGES = {"opportunities": opportunities, "watchouts": watchouts, "advisor": advisor}


def render(page: str, lang: str):
    PAGES[page](lang)
