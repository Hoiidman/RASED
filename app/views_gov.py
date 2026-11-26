"""Government portal pages (owner: Agent B).

Text is bilingual through i18n.tr(en, ar); data names (areas, activities, zones) keep their English values
for lookups and are translated only for display, through i18n.name().
"""
from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import backend as be
import charts as ch
import ui
from core import ai
from i18n import is_ar, sig, lang as cur_lang, month, name, tr
from labels import TITLES, TITLES_AR

PC = ch.CHART_CONFIG
SEV_AR = {"All": "الكل", "high": "مرتفع", "medium": "متوسط", "low": "منخفض"}


def _title(page):
    t, q = (TITLES_AR if is_ar() else TITLES)[page]
    ui.page_title(t, q)


def _plot(fig, key=None):
    st.plotly_chart(fig, width="stretch", config=ch.chart_config(), key=key)


# ------------------------------------------------------------------ Overview
def overview(lang):
    _title("overview")
    k = be.get_kpis()
    cols = st.columns(5)
    with cols[0]:
        ui.kpi(tr("Active licences", "الرخص السارية"), f"{k['active_licences']['value']:,}",
               k["active_licences"].get("change_pct"),
               f"{k['active_licences']['period']} · " + tr("DED", "دائرة التنمية الاقتصادية"))
    with cols[1]:
        ui.kpi(tr("Renewal rate", "معدل التجديد"), f"{k['renewal_rate']['value']}%", k["renewal_rate"].get("change_pct"),
               tr("2025 · +1 pt ≈ +370 businesses", "2025 · كل نقطة إضافية ≈ 370 منشأة"),
               delta_suffix=tr(" pts", " نقطة"))
    with cols[2]:
        nb = k["new_businesses"]
        fz = nb.get("fz_share_pct", 59)
        ui.kpi(tr("New businesses 2025", "المنشآت الجديدة 2025"), f"{int(nb['value']):,}", nb.get("change_pct"),
               tr(f"Mainland + Free Zone · FZ {fz:.0f}%", f"البر الرئيسي والمنطقة الحرة · الحرة {fz:.0f}%"))
    with cols[3]:
        ui.kpi(tr("Activity signal", "مؤشر النشاط"), f"+{k['activity_signal']['value']}%", None,
               tr("Licence-implied · a signal, not GDP", "مستمد من الرخص · مؤشر وليس الناتج المحلي"))
    with cols[4]:
        oa = k["open_alerts"]
        sev = oa.get("by_severity", {})
        h, m, lo = sev.get("high", 0), sev.get("medium", 0), sev.get("low", 0)
        ui.kpi(tr("Open early warnings", "الإنذارات المفتوحة"), f"{oa['value']}", None,
               tr(f"{h} high · {m} medium · {lo} low", f"{h} مرتفع · {m} متوسط · {lo} منخفض"))
    st.write("")
    left, right = st.columns([2, 1], gap="large")
    with left:
        df = be.get_series(["new_reg_total"], group_type="zone", start="2024-01")
        _plot(ch.registrations_chart(
            df, tr("Free Zone keeps growing while mainland registrations dropped",
                   "المنطقة الحرة تواصل النمو بينما تراجعت تسجيلات البر الرئيسي"),
            tr("New registrations per month. Mainland data runs to Jun 2026; Free Zone to Oct 2026 "
               "(Nov is partial and not shown)",
               "التسجيلات الجديدة شهرياً. بيانات البر الرئيسي حتى يونيو 2026 والمنطقة الحرة حتى أكتوبر 2026 "
               "(نوفمبر غير مكتمل ولا يُعرض)"), height=430))
    with right:
        ui.section(tr("Early warnings", "الإنذارات المبكرة"))
        for a in sorted(be.get_alerts(), key=lambda a: not a.get("new", False))[:5]:
            ui.alert_card(a)
        st.caption(tr("Factors and suggested actions are in the Early warnings tab.",
                      "العوامل والإجراءات المقترحة في تبويب الإنذارات المبكرة."))


def _vo_share():
    vo = be.get_series(["virtual_office_share"])
    vo = vo[~vo["is_partial"]].sort_values("period")
    return round(float(vo["value"].iloc[-1]), 1) if not vo.empty else None


# ------------------------------------------------------------------ Alerts
def _alert_fig(a):
    """Best-effort mini chart for an alert; None if the series isn't available. Cached per data version,
    device and language, so the 25 alert charts are built once, not on every click on the page."""
    return _alert_fig_cached(be.data_version(), a["indicator"], a["group"], a.get("group_type"), a["period"],
                             a["severity"], ch.is_mobile(), cur_lang())


@st.cache_data(ttl=24 * 3600, show_spinner=False)
def _alert_fig_cached(v, indicator, group, group_type, period, severity, mobile=False, lang="en"):
    a = {"indicator": indicator, "group": group, "group_type": group_type, "period": period, "severity": severity}
    try:
        ind, grp = a["indicator"], a["group"]
        start = None if ind == "renewal_rate" else "2025-01"
        s = None
        # find the alert's own group in whichever breakdown holds it (activity, area, licence type, ...)
        for gt in ([a["group_type"]] if a.get("group_type") else []) + [
                "activity", "area", "licence_type", "legal_form", "facility", "zone"]:
            cand = be.get_series([ind], group_type=gt, start=start)
            cand = cand[cand["group"] == grp]
            if not cand.empty:
                s = cand
                break
        if s is None:  # totals only when the alert really is about the total
            tot = be.get_series([ind], start=start)
            if not tot.empty and grp in set(tot["group"]) | {"Ajman", "Total"}:
                s = tot
        if s is None or s.empty:
            return None
        col = ui.SEV.get(a["severity"], (ch.MUTED, ""))[0]
        return ch.alert_chart(s, a["period"], col, "%" if ind in ("virtual_office_share", "renewal_rate") else "")
    except Exception:  # noqa: BLE001 - a missing chart must never break the alert list
        return None


def _updates_feed():
    """What changed in recent data syncs, and which alerts each sync raised."""
    changes = be.get_changes()[:4]
    if not changes:
        return
    ui.section(tr("Latest data updates", "آخر تحديثات البيانات"))
    rows = []
    for c in changes:
        n = c.get("new_alerts", 0)
        inds = ", ".join(c.get("indicators", []))
        ds = ui._NICE_AR.get(c["dataset"], c["dataset"]) if is_ar() else c["dataset"]
        if is_ar():
            row = (f"<b>{ui.ago(c['time'])}</b>: أضافت {ds} {c['rows_added']:,} صفاً "
                   f"({len(c.get('indicators', []))} مؤشرات)"
                   + (f". <b style='color:{ch.RED_TXT}'>{n} إنذارات جديدة</b>" if n else ". لا إنذارات جديدة."))
        else:
            row = (f"<b>{ui.ago(c['time'])}</b>: {ds} added {c['rows_added']:,} rows ({inds})"
                   + (f". <b style='color:{ch.RED_TXT}'>{n} new alert{'s' if n != 1 else ''}</b>" if n else
                      ". No new alerts."))
        rows.append(row)
    st.markdown("<div class='r-meta'>" + "<br>".join(rows) + "</div>", unsafe_allow_html=True)


CONTEXT_AR = {  # the fixed event and wider-economy labels from core/context.py
    "Ramadan": "رمضان", "Eid al-Fitr": "عيد الفطر", "Eid al-Adha": "عيد الأضحى", "Summer slowdown": "تباطؤ الصيف",
    "Corporate tax first filing deadline for many firms": "أول موعد نهائي لإقرارات ضريبة الشركات لكثير من المنشآت",
    "Regional disruption begins": "بداية الاضطراب الإقليمي",
    "DED fee and fine waivers": "إعفاءات الدائرة من الرسوم والغرامات",
    "UAE real GDP growth": "نمو الناتج المحلي الحقيقي للإمارات",
    "UAE consumer price inflation": "تضخم أسعار المستهلك في الإمارات",
    "UAE GDP growth": "نمو الناتج المحلي للإمارات", "UAE inflation": "التضخم في الإمارات",
}


def _ctx(text) -> str:
    """Event and wider-economy labels in the current language."""
    text = str(text or "")
    if not is_ar():
        return text
    return CONTEXT_AR.get(text, text).replace("World Bank", "البنك الدولي").replace("(sample value)", "(قيمة نموذجية)")


def _context_block(a):
    """News, events and wider-economy figures around the alert month. Context, not causes."""
    sector = a.get("sector") or a["group"].split(" · ")[0]
    try:
        ctx = be.get_context(a["period"], sector)
    except Exception:  # noqa: BLE001 - context is optional
        return
    st.markdown(tr(f"**What was happening around {month(a['period'], short=False)}**",
                   f"**ما الذي كان يحدث في {month(a['period'])}**") + "  \n<span class='muted'>"
                + tr("News, events and the wider economy at the time. These are possible influences for an analyst "
                     "to check, not proven causes.",
                     "أخبار وأحداث ووضع الاقتصاد الأوسع في تلك الفترة. هذه مؤثرات محتملة يتحقق منها المحلل، "
                     "وليست أسباباً مثبتة.") + "</span>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1.4, 1, 0.8], gap="large")
    with c1:
        ui.section(tr("In the news", "في الأخبار"))
        news = ctx.get("news") or []
        for n in news:
            title = f"[{n['title']}]({n['url']})" if n.get("url") else n["title"]
            st.markdown(f"{title}  \n<span class='muted'>{n.get('source', '')}, {n.get('date', '')}</span>",
                        unsafe_allow_html=True)
        if not news:
            st.caption(tr("No related headlines found for this period.", "لا توجد عناوين ذات صلة بهذه الفترة."))
        if ctx.get("news_live") and news:
            src = ctx.get("news_source") or "news search"
            st.caption(tr(f"Live headlines via {src}, filtered to business news.",
                          f"عناوين مباشرة عبر {src}، مقتصرة على أخبار الأعمال."))
        elif news:
            st.caption(tr("Sample headlines: the live news search could not be reached.",
                          "عناوين نموذجية: تعذّر الوصول إلى البحث المباشر في الأخبار."))
    with c2:
        ui.section(tr("Events", "الأحداث"))
        for e in ctx.get("events") or []:
            end = e.get("end")
            start = sig(e["start"])  # dates stay left to right inside Arabic text
            if end == e["start"]:
                when = start
            else:
                when = start + (tr(f" to {end}", f" إلى {sig(end or '')}") if end else tr(" onwards", " وما بعده"))
            st.markdown(f"{_ctx(e['name'])}  \n<span class='muted'>{when}</span>", unsafe_allow_html=True)
    with c3:
        ui.section(tr("Wider economy", "الاقتصاد الأوسع"))
        for m in ctx.get("macro") or []:
            st.markdown(f"{_ctx(m['indicator'])}: **{m['value']}{m.get('unit', '')}**  \n"
                        f"<span class='muted'>{m.get('period', '')}{tr(', ', '، ')}{_ctx(m.get('source', ''))}</span>",
                        unsafe_allow_html=True)


@st.cache_resource
def _playbook_ar() -> dict:
    """Arabic text of the suggested actions (config/playbook_ar.yaml), by alert rule."""
    from core.settings import config
    try:
        return config("playbook_ar") or {}
    except (OSError, ValueError):
        return {}


def alerts(lang):
    _title("alerts")
    _updates_feed()
    sev = st.segmented_control(tr("Severity", "درجة الخطورة"), ["All", "high", "medium", "low"], default="All",
                               format_func=lambda x: SEV_AR[x] if is_ar() else x)
    items = be.get_alerts(None if sev in (None, "All") else sev)
    items = sorted(items, key=lambda a: not a.get("new", False))  # alerts from the latest sync first
    be.prefetch_context([(a["period"], a.get("sector") or a["group"].split(" · ")[0]) for a in items])
    if not items:
        st.success(tr("No alerts at this severity.", "لا توجد إنذارات بهذه الدرجة."))
    for a in items:
        ui.alert_card(a, compact=False)
        with st.expander(tr(f"Details: {a['group']}", f"التفاصيل: {name(a['group'])}"),
                         expanded=a["id"] == items[0]["id"]):
            fig = _alert_fig(a)
            if fig is not None:
                _plot(fig, key=f"alert_chart_{a['id']}")
            _context_block(a)
            c1, c2 = st.columns(2, gap="large")
            with c1:
                st.markdown(tr("**Possible contributing factors**", "**عوامل محتملة**") + "  \n<span class='muted'>"
                            + tr("Context only. An analyst should confirm before acting.",
                                 "للسياق فقط. ينبغي أن يتحقق محلل منها قبل اتخاذ أي إجراء.") + "</span>",
                            unsafe_allow_html=True)
                for f in a["possible_factors"]:
                    st.markdown(f"- {f['text']}  \n  <span class='muted'>{f['source']} · {f['date']}</span>",
                                unsafe_allow_html=True)
            with c2:
                st.markdown(tr("**Suggested DED actions**", "**إجراءات مقترحة للدائرة**"))
                acts = (_playbook_ar().get(a["rule"]) or a["actions"]) if is_ar() else a["actions"]
                for i, act in enumerate(acts, 1):
                    st.markdown(f"{i}. {act}")
            if a.get("status") != "acknowledged":
                if st.button(tr("Acknowledge and assign", "تأكيد الاستلام والإسناد"), key=f"ack_{a['id']}"):
                    be.acknowledge(a["id"], "gov_user")
                    st.toast(tr(f"{a['id']} acknowledged and logged to the audit trail",
                                f"تم تأكيد {a['id']} وتسجيله في سجل التدقيق"))
                    st.rerun()
            rule = a["rule"].replace("_", " ")
            st.caption(tr(f"Rule: {rule} · indicator: {a['indicator']} · id {a['id']}",
                          f"القاعدة: {rule} · المؤشر: {a['indicator']} · المعرّف {a['id']}"))


# ------------------------------------------------------------------ Outlook
PRESET_AR = {"No disruption": "بلا اضطراب", "Fast recovery": "تعافٍ سريع", "Central": "المسار الأوسط",
             "Slow recovery": "تعافٍ بطيء", "Stress test": "اختبار ضغط"}


def _outlook_presets() -> dict:
    """Slider presets: (recovery starts in, recovery takes, shock depth %, meaning in English, in Arabic).
    A, B and C come from config/assumptions.yaml, so they always match the scenario lines on the chart."""
    from core.settings import config
    try:
        sc = config("assumptions")["scenarios"]
    except Exception:  # noqa: BLE001 - mock mode or missing config: the documented defaults
        sc = {"A": [9, 12, 100], "B": [5, 6, 100], "C": [2, 3, 100]}
    return {
        "No disruption": (0, 1, 0, "the March 2026 shock removed, to see where registrations would be without it",
                          "بدون صدمة مارس 2026، لمعرفة مستوى التسجيلات لو لم تحدث"),
        "Fast recovery": (*sc["C"][:3], "scenario C: the shock fades quickly, for example after a short-lived crisis",
                          "السيناريو ج: تتلاشى الصدمة سريعاً، كما بعد أزمة قصيرة"),
        "Central": (*sc["B"][:3], "scenario B: the most likely path if conditions keep improving",
                    "السيناريو ب: المسار الأرجح إذا واصلت الأوضاع التحسن"),
        "Slow recovery": (*sc["A"][:3], "scenario A: recovery waits most of a year, for example if instability lasts",
                          "السيناريو أ: يتأخر التعافي معظم العام، كما لو استمر عدم الاستقرار"),
        "Stress test": (12, 18, 150, "a deeper and longer crisis than today, to test how bad it could get",
                        "أزمة أعمق وأطول من الحالية، لاختبار أسوأ الاحتمالات"),
    }


def _apply_preset(presets):
    pick = st.session_state.get("ol_preset")
    if pick in presets:
        st.session_state.ol_rs, st.session_state.ol_rl, st.session_state.ol_dp = presets[pick][:3]


def _clear_preset():
    st.session_state.ol_preset = None


def outlook(lang):
    _title("outlook")
    c0, c1, c2, c3 = st.columns([1.3, 1, 1, 1])
    ind_names = {"new_reg_mainland": tr("Mainland registrations", "تسجيلات البر الرئيسي"),
                 "new_reg_fz": tr("Free Zone registrations", "تسجيلات المنطقة الحرة"),
                 "new_reg_total": tr("All new registrations", "جميع التسجيلات الجديدة")}
    ind = c0.selectbox(tr("Indicator", "المؤشر"), list(ind_names), format_func=ind_names.get)
    presets = _outlook_presets()
    for k, v in zip(("ol_rs", "ol_rl", "ol_dp"), (6, 6, 100)):
        st.session_state.setdefault(k, v)
    st.segmented_control(tr("Presets", "إعدادات جاهزة"), list(presets), key="ol_preset", on_change=_apply_preset,
                         args=(presets,), format_func=lambda p: PRESET_AR[p] if is_ar() else p,
                         help=tr("Sets the three sliders. Moving a slider afterwards makes it your own scenario.",
                                 "يضبط أشرطة التحكم الثلاثة. تحريك أي شريط بعدها يجعله سيناريوك الخاص."))
    rs = c1.slider(tr("Recovery starts in (months)", "يبدأ التعافي بعد (أشهر)"), 0, 12, key="ol_rs",
                   on_change=_clear_preset)
    rl = c2.slider(tr("Recovery takes (months)", "مدة التعافي (أشهر)"), 1, 18, key="ol_rl", on_change=_clear_preset)
    dp = c3.slider(tr("Shock depth (% of current)", "عمق الصدمة (% من الحالية)"), 0, 150, step=10, key="ol_dp",
                   on_change=_clear_preset)
    chosen = st.session_state.get("ol_preset")
    if chosen:
        st.caption(f"{PRESET_AR[chosen]}: {presets[chosen][4]}" if is_ar() else f"{chosen}: {presets[chosen][3]}")
    fc_all = be.get_forecast(ind, rs, rl, dp)
    hist_all = be.get_series([ind])
    full_all = hist_all[~hist_all["is_partial"]]

    # Date window: any range from the first month of history to the end of the forecast
    months = sorted(set(full_all["period"]) | set(fc_all["period"]))
    default_start = "2024-01" if "2024-01" in months else months[0]
    w0, w1 = st.select_slider(tr("Dates shown", "الفترة المعروضة"), options=months,
                              value=(default_start, months[-1]), format_func=month, key="outlook_window")
    full = full_all[full_all["period"].between(w0, w1)]
    fc = fc_all[fc_all["period"].between(w0, w1)]

    fig = go.Figure()
    if not full.empty:
        fig.add_trace(go.Scatter(x=ch.dt(full["period"]), y=full["value"], name=tr("Actual", "الفعلي"), mode="lines",
                                 line=dict(color=ch.BLACK, width=3, shape="spline", smoothing=0.5),
                                 hovertemplate="%{y:,.0f}"))
    cust = fc[fc["scenario"] == "custom"]
    if not cust.empty:
        x = ch.dt(cust["period"])
        fig.add_trace(go.Scatter(x=pd.concat([x, x[::-1]]), y=pd.concat([cust["hi"], cust["lo"][::-1]]),
                                 fill="toself", fillcolor="rgba(35,37,40,0.08)", line=dict(width=0),
                                 name=tr("80% band (your scenario)", "نطاق 80% (سيناريوك)"), hoverinfo="skip"))
    # join each forecast line to the last actual month when both are in the window
    join = (not full.empty and not fc.empty and full["period"].max() == full_all["period"].max())
    for s in ["A", "B", "C", "custom"]:
        d = fc[fc["scenario"] == s]
        if d.empty:
            continue
        xs, ys = ch.dt(d["period"]), d["mean"]
        if join:
            xs = pd.concat([pd.Series([ch.dt(full["period"]).iloc[-1]]), xs])
            ys = pd.concat([pd.Series([full["value"].iloc[-1]]), ys])
        fig.add_trace(go.Scatter(
            x=xs, y=ys, name=ch.scen_name(s), mode="lines",
            line=dict(color=ch.SCEN_COL[s], width=3.5 if s == "custom" else 2, dash="solid" if s == "custom" else "dash",
                      shape="spline", smoothing=0.5),
            hovertemplate="%{y:,.0f}"))
    if not full.empty and full["period"].max() >= ch.SHOCK_START:
        ch.add_shock(fig, end=full["period"].max())
    ch.style(fig, tr("Three recovery paths, plus the one set by your sliders",
                     "ثلاثة مسارات للتعافي، إضافة إلى المسار الذي تحدده أشرطة التحكم"),
             tr(f"Monthly registrations, {month(w0)} to {month(w1)}",
                f"التسجيلات الشهرية، من {month(w0)} إلى {month(w1)}"), 460)
    fig.update_yaxes(tickformat=",")
    _plot(fig)

    full, fc = full_all, fc_all  # the yearly totals below always use the full series

    actual_26 = full[full["period"].str.startswith("2026")]["value"].sum()
    last = month(full["period"].max())
    col_s = tr("Scenario", "السيناريو")
    col_26 = tr(f"2026 total (actual to {last} + forecast)", f"إجمالي 2026 (فعلي حتى {last} + توقع)")
    col_27 = tr("2027 total", "إجمالي 2027")
    col_w = tr(f"Forecast, {month(w0)} to {month(w1)}", f"التوقع، من {month(w0)} إلى {month(w1)}")
    rows = []
    for s in ["A", "B", "C", "custom"]:
        d = fc[fc["scenario"] == s]
        in_win = d[d["period"].between(w0, w1)]
        rows.append({col_s: ch.scen_name(s),
                     col_26: int(actual_26 + d[d["period"].str.startswith("2026")]["mean"].sum()),
                     col_27: int(d[d["period"].str.startswith("2027")]["mean"].sum()),
                     col_w: int(in_win["mean"].sum())})
    c1, c2 = st.columns([1.4, 1], gap="large")
    with c1:
        st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch",
                     column_config={k: st.column_config.NumberColumn(format="localized") for k in rows[0] if k != col_s})
    with c2:
        ui.section(tr("Assumptions", "الافتراضات"))
        st.markdown(tr(
            "- Model: SARIMAX on logs, with Ramadan/Eid effects and a disruption dial\n"
            "- Back-test error about 10% a year for mainland in normal years. Free Zone is shown as scenarios only.\n"
            "- Partial months are left out of the models\n"
            "- A: recovery starts after 9 months and takes 12. B: 5 and 6. C: 2 and 3.",
            "- النموذج: SARIMAX على اللوغاريتمات، مع أثر رمضان والعيدين ومؤشر للاضطراب\n"
            "- خطأ الاختبار الرجعي نحو 10% سنوياً للبر الرئيسي في السنوات العادية. تُعرض المنطقة الحرة "
            "كسيناريوهات فقط.\n"
            "- تُستبعد الأشهر غير المكتملة من النماذج\n"
            "- أ: يبدأ التعافي بعد 9 أشهر ويستغرق 12. ب: 5 و6. ج: 2 و3."))


# ------------------------------------------------------------------ Actions
def actions(lang):
    _title("actions")
    c1, c2 = st.columns([1, 1.3], gap="large")
    with c1:
        ui.section(tr("Policy simulator", "محاكي السياسات"))
        delta = st.slider(tr("Raise renewal rate by (points)", "رفع معدل التجديد بمقدار (نقاط)"), 0.0, 3.0, 1.0, 0.1)
        sim = be.simulate_renewal(delta)
        m1, m2, m3 = st.columns(3)
        m1.metric(tr("Businesses retained", "منشآت محتفظ بها"), f"+{sim['businesses_retained']:,}")
        m2.metric(tr("Active licences", "الرخص السارية"), f"{sim['active_licences']:,}")
        m3.metric(tr("Activity signal", "مؤشر النشاط"), f"{sim['activity_signal_pct']:+.1f}%")
        camp = st.slider(tr("New-licence campaign uplift (%)", "زيادة الرخص الجديدة بحملة ترويجية (%)"), 0, 20, 5)
        extra = round(18504 * camp / 100)
        st.metric(tr("Extra new businesses / year", "منشآت جديدة إضافية سنوياً"), f"+{extra:,}")
        with st.expander(tr("Assumptions", "الافتراضات")):
            for a in sim.get("assumptions", []):
                st.markdown(f"- {a}")
    with c2:
        base = sim["active_licences"] - sim["businesses_retained"]
        total = base + sim["businesses_retained"] + extra
        fig = go.Figure(go.Waterfall(
            orientation="v", measure=["absolute", "relative", "relative", "total"],
            x=[tr("Active licences today", "الرخص السارية اليوم"),
               tr(f"Renewal +{delta:.1f} pts", f"التجديد +{delta:.1f} نقطة"),
               tr(f"Campaign +{camp}%", f"الحملة +{camp}%"), tr("With DED actions", "مع إجراءات الدائرة")],
            y=[base, sim["businesses_retained"], extra, 0],
            text=[f"{base:,}", f"+{sim['businesses_retained']:,}", f"+{extra:,}", f"{total:,}"],
            textposition="outside", connector=dict(line=dict(color="#CCCCCC")),
            increasing=dict(marker=dict(color=ch.GREEN)), totals=dict(marker=dict(color=ch.GOLD)),
            decreasing=dict(marker=dict(color=ch.RED))))
        gain = sim["businesses_retained"] + extra
        ch.style(fig, tr(f"+{gain:,} businesses from two policy levers", f"{sig(f'+{gain:,}')} منشأة من أداتين للسياسات"),
                 tr("Active licences: today vs with renewal and campaign actions",
                    "الرخص السارية: اليوم مقارنة بما بعد إجراءات التجديد والحملة"), 420, legend=False)
        fig.update_yaxes(range=[base * 0.9, total * 1.03], tickformat=",")
        fig.update_layout(hovermode="closest")
        _plot(fig)
    ui.section(tr("Recommended actions", "الإجراءات الموصى بها"))
    k = be.get_kpis()
    zone = be.group_differences("zone")["table"].set_index("group")
    facts = {"renewal_rate": k["renewal_rate"]["value"], "retained_per_pt": be.simulate_renewal(1)["businesses_retained"],
             "virtual_office_share": _vo_share(), "active_licences": k["active_licences"]["value"],
             "mainland_change_pct": float(zone.loc["Mainland", "change_pct"]) if "Mainland" in zone.index else None,
             "open_alerts": k["open_alerts"]["value"]}
    key = f"gov_ai_{cur_lang()}"  # one answer per language, so switching language never shows the other one
    if st.button(tr("Generate recommendations", "إنشاء التوصيات"), type="primary") or key in st.session_state:
        if key not in st.session_state:
            with st.spinner(tr("Analysing facts", "جارٍ تحليل الحقائق")):
                st.session_state[key] = ai.advise("gov_actions", facts, lang=cur_lang())
        res = st.session_state[key]
        st.markdown(res["text"])
        st.caption(tr(f"Engine: {res['engine']}. Based on: ", f"المحرك: {res['engine']}. المستند إلى: ")
                   + "; ".join(res["cited_facts"]))


# ------------------------------------------------------------------ Sectors & groups
WHY_AR = {"Digital economy growth that diversifies Ajman beyond trading": "نمو الاقتصاد الرقمي ينوّع اقتصاد عجمان بعيداً عن التجارة",
          "Watch the project pipeline; affects jobs and suppliers": "راقب المشاريع المقبلة؛ تؤثر في الوظائف والموردين",
          "Largest base, so small % changes mean many businesses": "القاعدة الأكبر، فالتغير الصغير يعني منشآت كثيرة",
          "Benefits from port & road connectivity": "يستفيد من الربط بالموانئ والطرق",
          "Population-driven demand; seasonal around Ramadan": "طلب مرتبط بالسكان؛ موسمي حول رمضان",
          "Track against population & area growth": "تابعه مقابل نمو السكان والمناطق"}


def _quarter(q: str) -> str:
    """'2025 Q4' -> '2025 Q4' / 'الربع 4 2025'."""
    y, n = q.split(" Q")
    return f"الربع {n} {y}" if is_ar() else q


def sectors(lang):
    _title("sectors")
    df = be.get_series(["new_reg_total"], group_type="activity", start="2024-01")
    df = df[~df["is_partial"]].copy()
    p = pd.PeriodIndex(df["period"], freq="M")
    df["q"] = p.asfreq("Q").astype(str)
    full_q = df.groupby("q")["period"].nunique()
    df = df[df["q"].isin(full_q[full_q == 3].index)]  # complete quarters only
    q = df.groupby(["group", "q"])["value"].sum().unstack()
    q.columns = [c.replace("Q", " Q") for c in q.columns]
    yoy = ((q / q.shift(4, axis=1) - 1) * 100).iloc[:, 4:].dropna(axis=1, how="all")
    yoy = yoy.loc[yoy.iloc[:, -1].sort_values(ascending=False).index]
    mobile, ar = ch.is_mobile(), is_ar()
    if mobile:  # a phone fits about three quarters next to the sector names
        yoy = yoy.iloc[:, -3:]
    names = [name(n) for n in yoy.index]
    fig = go.Figure(go.Heatmap(
        z=yoy.values, x=list(yoy.columns), y=list(yoy.index), zmid=0, zmin=-40, zmax=40,
        colorscale=[[0, ch.RED], [0.5, "#FFFFFF"], [1, ch.GREEN]],
        text=[["" if pd.isna(v) else f"{v:+.0f}%" for v in row] for row in yoy.values], texttemplate="%{text}",
        customdata=[[n] * yoy.shape[1] for n in names],
        textfont=dict(size=11 if mobile else 12),
        hovertemplate="%{customdata} · %{x}: %{z:+.1f}%" + tr(" YoY", " سنوياً") + "<extra></extra>",
        showscale=not mobile, colorbar=dict(title=tr("YoY", "سنوي"), ticksuffix="%", thickness=12,
                                            x=-0.02 if ar else 1.02, xanchor="right" if ar else "left")))
    ch.style(fig, tr("Which sectors are heating up or cooling down", "أي القطاعات تنشط وأيها تتباطأ"),
             tr("New registrations, % change vs same quarter last year",
                "التسجيلات الجديدة، نسبة التغير مقارنة بالربع نفسه من العام الماضي"),
             max(300, 30 * len(yoy) + 60) if mobile else 440, legend=False)
    fig.update_layout(hovermode="closest")
    fig.update_xaxes(showline=False, ticks="", side="top" if mobile else "bottom",
                     tickvals=list(yoy.columns), ticktext=[_quarter(c) for c in yoy.columns])
    # some official Arabic activity names are long ("... (العباءات النسائية)"), so they are capped on desktop too
    cut = (16 if ar else 18) if mobile else (34 if ar else 60)
    labels = [n if len(n) <= cut else n[:cut - 1].rstrip() + "…" for n in names]
    # short names on phones (full name in the tooltip); Arabic names sit on the right
    fig.update_yaxes(tickvals=list(yoy.index), ticktext=labels, side="right" if ar else "left")
    _plot(fig)
    why = {"IT & e-commerce": "Digital economy growth that diversifies Ajman beyond trading",
           "Construction & contracting": "Watch the project pipeline; affects jobs and suppliers",
           "General trading": "Largest base, so small % changes mean many businesses",
           "Logistics & transport": "Benefits from port & road connectivity",
           "Restaurants & cafes": "Population-driven demand; seasonal around Ramadan"}
    reasons = [why.get(s, "Track against population & area growth") for s in yoy.index]
    st.dataframe(pd.DataFrame({tr("Sector", "القطاع"): names,
                               tr("Latest quarter YoY %", "آخر ربع، التغير السنوي %"): yoy.iloc[:, -1].round(1).values,
                               tr("Why it matters for Ajman", "لماذا يهم عجمان"):
                                   [WHY_AR.get(r, r) if ar else r for r in reasons]}),
                 hide_index=True, width="stretch")

    ui.section(tr("Which groups differ", "أي الفئات تختلف"))
    dims = {"zone": tr("Mainland vs FZ", "البر الرئيسي مقابل الحرة"), "licence_type": tr("Licence type", "نوع الرخصة"),
            "legal_form": tr("Legal form", "الشكل القانوني"),
            "facility": tr("Facility (virtual office)", "المقر (مكتب افتراضي)"), "area": tr("Area", "المنطقة"),
            "activity": tr("Activity", "النشاط")}
    tabs = st.tabs(list(dims.values()))
    for tab, dim in zip(tabs, dims):
        with tab:
            gd = be.group_differences(dim)
            st.markdown(f"**{ui.group_finding(gd)}**")
            if dim == "facility":
                vo = be.get_series(["virtual_office_share"], start="2024-01")
                vo = vo[~vo["is_partial"]]
                fig = go.Figure(go.Scatter(x=ch.dt(vo["period"]), y=vo["value"], mode="lines", fill="tozeroy",
                                           line=dict(color=ch.GOLD, width=3, shape="spline"),
                                           fillcolor="rgba(182,138,53,0.15)", hovertemplate="%{y:.0f}%"))
                ch.add_shock(fig, end=vo["period"].max())
                ch.style(fig, tr("Virtual offices now dominate Free Zone setups",
                                 "المكاتب الافتراضية تتصدر الآن تأسيس الشركات في المنطقة الحرة"),
                         tr("Share of new Free Zone registrations using a virtual office",
                            "نسبة التسجيلات الجديدة في المنطقة الحرة التي تستخدم مكتباً افتراضياً"), 340, legend=False)
                fig.update_yaxes(ticksuffix="%", range=[0, 70])
                _plot(fig)
            _plot(ch.bar_change(gd["table"], tr("Change H1 2026 vs H1 2025",
                                                "التغير: النصف الأول 2026 مقارنة بالنصف الأول 2025"),
                                tr("Groups with < 5 records are suppressed", "تُحجب الفئات التي تقل سجلاتها عن 5")))


# ------------------------------------------------------------------ Drivers
def _drv(d: dict, field: str) -> str:
    """Driver text in the current language (Arabic from config/drivers.yaml where given)."""
    return (d.get(f"{field}_ar") or d.get(field) or "") if is_ar() else (d.get(field) or "")


RESULT_AR = {"Observed proxy available; hypothesis testing and verified event context pending.":
             "البيانات البديلة متاحة؛ اختبار الفرضية والتحقق من سياق الأحداث قيد الانتظار."}


def drivers(lang):
    _title("drivers")
    st.caption(tr("Each driver is a hypothesis with a measurable proxy. They are monitored, not proven.",
                  "كل محرك فرضية لها مؤشر قابل للقياس. تخضع للمتابعة، ولم تُثبت."))
    stat = {"ready": tr("Data ready", "البيانات جاهزة"), "partial": tr("Partial data", "بيانات جزئية"),
            "data_needed": tr("Data needed", "بيانات مطلوبة")}
    ds = be.get_drivers()

    def result(d):
        r = d.get("result") or ""
        return RESULT_AR.get(r, r) if is_ar() else r

    st.dataframe(pd.DataFrame([{
        tr("Driver", "المحرك"): _drv(d, "name"), tr("Status", "الحالة"): stat.get(d["status"], d["status"]),
        tr("Hypothesis", "الفرضية"): _drv(d, "hypothesis"), tr("What we measure", "ما نقيسه"): _drv(d, "proxy"),
        tr("Source", "المصدر"): _drv(d, "source"), tr("Finding so far", "النتيجة حتى الآن"): result(d),
    } for d in ds]), hide_index=True, width="stretch")
    for d in ds:
        if d.get("chart") is not None and len(d["chart"]):
            cd = d["chart"]
            f = go.Figure(go.Scatter(x=ch.dt(cd["period"]), y=cd["value"], mode="lines",
                                     line=dict(color=ch.GOLD, width=3, shape="spline"), hovertemplate="%{y:.0f}%"))
            ch.style(f, f"{_drv(d, 'name')}: {result(d)}", _drv(d, "proxy"), 300, legend=False)
            f.update_yaxes(ticksuffix="%")
            _plot(f)


# ------------------------------------------------------------------ Impact
def impact(lang):
    _title("impact")
    st.markdown(tr(
        "- **Faster decisions.** Changes are flagged within weeks instead of months.\n"
        "- **More businesses kept.** Each extra point of renewal rate keeps about 370 businesses.\n"
        "- **Better targeting.** DED can see which sectors, areas and setup types need support.\n"
        "- **More investors.** New businesses get clear, public guidance on where demand is.",
        "- **قرارات أسرع.** تُرصد التغيرات خلال أسابيع بدلاً من أشهر.\n"
        "- **الحفاظ على منشآت أكثر.** كل نقطة إضافية في معدل التجديد تحافظ على نحو 370 منشأة.\n"
        "- **استهداف أدق.** ترى الدائرة القطاعات والمناطق وأنواع التأسيس التي تحتاج إلى دعم.\n"
        "- **مستثمرون أكثر.** تحصل المنشآت الجديدة على إرشاد عام وواضح حول أماكن الطلب."))
    ui.section(tr("KPI framework", "إطار مؤشرات الأداء"))
    if is_ar():
        rows = [
            ["معدل التجديد", "94.3% (2025)", "95.3% (2027)", "بيانات رخص الدائرة", "شهري"],
            ["منشآت محتفظ بها عبر إجراءات التجديد", "0", "+370 سنوياً", "بيانات رخص الدائرة", "شهري"],
            ["الوقت من الإنذار إلى الإجراء", "أشهر (يدوي)", "أقل من 14 يوماً", "سجل تدقيق راصد", "شهري"],
            ["تسجيلات البر الرئيسي مقابل السيناريو ب", "−28% (النصف الأول 2026)", "العودة إلى الاتجاه بنهاية 2027",
             "بيانات الدائرة المفتوحة", "شهري"],
            ["خطأ التوقع مقابل الفعلي", "~10% سنوياً (البر الرئيسي)", "10% أو أقل، مع المتابعة", "اختبار راصد الرجعي",
             "شهري"],
            ["قرارات تستخدم راصد", "0", "50% أو أكثر من مذكرات السياسات", "استبيان الدائرة", "ربع سنوي"],
            ["جلسات مستشار المستثمر", "0", "1,000 لكل ربع", "استخدام راصد", "ربع سنوي"],
        ]
        cols = ["المؤشر", "خط الأساس", "المستهدف", "مصدر البيانات", "التكرار"]
    else:
        rows = [
            ["Renewal rate", "94.3% (2025)", "95.3% (2027)", "DED licence data", "Monthly"],
            ["Businesses retained via renewal actions", "0", "+370 / year", "DED licence data", "Monthly"],
            ["Alert-to-action time", "Months (manual)", "< 14 days", "RASED audit log", "Monthly"],
            ["Mainland registrations vs scenario B", "−28% (H1 2026)", "Back to trend by end-2027", "DED open data", "Monthly"],
            ["Forecast error vs actuals", "~10% yearly (mainland)", "≤ 10%, tracked", "RASED back-test", "Monthly"],
            ["Decisions using RASED", "0", "≥ 50% of DED policy memos", "DED survey", "Quarterly"],
            ["Investor advisor sessions", "0", "1,000 / quarter", "RASED usage", "Quarterly"],
        ]
        cols = ["KPI", "Baseline", "Target", "Data source", "Frequency"]
    st.dataframe(pd.DataFrame(rows, columns=cols), hide_index=True, width="stretch")
    st.caption(tr("Licence data is a signal of economic activity. It is not GDP and not FDI.",
                  "بيانات الرخص مؤشر على النشاط الاقتصادي، وليست الناتج المحلي ولا الاستثمار الأجنبي المباشر."))


# ------------------------------------------------------------------ Export
def export(lang):
    _title("export")
    cat = be.get_catalog()
    names = dict(zip(cat["id"], cat["name_en"]))
    if is_ar() and "name_ar" in cat:
        names.update({i: n for i, n in zip(cat["id"], cat["name_ar"]) if isinstance(n, str) and n.strip()})
    c1, c2 = st.columns([2, 1])
    ids = c1.multiselect(tr("Metrics", "المؤشرات"), list(cat["id"]),
                         default=["new_reg_mainland", "new_reg_fz", "virtual_office_share"],
                         format_func=lambda i: names.get(i, i))
    groups = {"total": tr("total", "الإجمالي"), "zone": tr("zone", "النطاق"), "activity": tr("activity", "النشاط"),
              "area": tr("area", "المنطقة"), "facility": tr("facility", "المقر")}
    gt = c2.selectbox(tr("Group", "التجميع"), list(groups), format_func=groups.get)
    c3, c4, c5 = st.columns(3)
    start = c3.text_input(tr("From (YYYY-MM)", "من (YYYY-MM)"), "2025-01")
    end = c4.text_input(tr("To (YYYY-MM)", "إلى (YYYY-MM)"), "2026-10")
    fmt = c5.radio(tr("Format", "الصيغة"), ["json", "csv"], horizontal=True)
    if not ids:
        st.warning(tr("Pick at least one metric.", "اختر مؤشراً واحداً على الأقل."))
        return
    prev = be.get_series(ids, None if gt == "total" else gt, start, end)
    st.markdown(tr(f"**Preview**, {len(prev):,} rows", f"**معاينة**، {len(prev):,} صفاً"))
    st.dataframe(prev.head(200), hide_index=True, width="stretch", height=260)
    st.caption(tr("Columns: **period** is the month or year; **value** is the count or percentage; "
                  "**is_partial** is true for a month that is still in progress, so its count is incomplete. "
                  "Charts and forecasts leave partial months out; keep that in mind when comparing them.",
                  "الأعمدة: **period** هو الشهر أو السنة؛ **value** هو العدد أو النسبة؛ "
                  "**is_partial** صحيح لشهر لم ينتهِ بعد، فعدده غير مكتمل. "
                  "تستبعد الرسوم والتوقعات الأشهر غير المكتملة، فانتبه لذلك عند المقارنة."))
    req = (tuple(ids), gt, start, end, fmt)
    if st.button(tr(f"Prepare {fmt.upper()} export", f"تجهيز ملف {fmt.upper()}"), type="primary"):
        # export() writes an audit-log line, so it runs only when the user asks for a file
        st.session_state.export = (req, be.export(ids, None if gt == "total" else gt, start, end, fmt))
        st.toast(tr("Export logged to the audit trail", "سُجّل التصدير في سجل التدقيق"))
    ready = st.session_state.get("export")
    if ready and ready[0] == req:
        st.download_button(tr(f"Download {fmt.upper()}", f"تنزيل {fmt.upper()}"), ready[1],
                           file_name=f"rased_export.{fmt}", mime="application/json" if fmt == "json" else "text/csv")
    url = f"/v1/indicators/data?ids={','.join(ids)}" + (f"&group={gt}" if gt != "total" else "") + f"&from={start}&to={end}"
    st.markdown(tr("**Same data via the REST API** (header `X-API-Key`):",
                   "**البيانات نفسها عبر واجهة REST البرمجية** (الترويسة `X-API-Key`):"))
    st.code(f"curl -H 'X-API-Key: <your-key>' 'http://localhost:8000{url}'", language="bash")
    st.caption(tr("Full API docs at /docs. Totals and averages only; groups with fewer than 5 records are hidden.",
                  "التوثيق الكامل في ‎/docs. مجاميع ومتوسطات فقط؛ تُخفى الفئات التي تقل سجلاتها عن 5."))


PAGES = {"overview": overview, "alerts": alerts, "outlook": outlook, "actions": actions, "sectors": sectors,
         "drivers": drivers, "impact": impact, "export": export}


def render(page: str, lang: str):
    PAGES[page](lang)
