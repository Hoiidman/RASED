"""Government portal pages (owner: Agent B)."""
from __future__ import annotations

import json

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


def _plot(fig, key=None):
    st.plotly_chart(fig, width="stretch", config=PC, key=key)


# ------------------------------------------------------------------ Overview
def overview(lang):
    _title("overview")
    k = be.get_kpis()
    cols = st.columns(5)
    with cols[0]:
        ui.kpi("Active licences", f"{k['active_licences']['value']:,}", k["active_licences"].get("change_pct"),
               f"{k['active_licences']['period']} · DED")
    with cols[1]:
        ui.kpi("Renewal rate", f"{k['renewal_rate']['value']}%", k["renewal_rate"].get("change_pct"),
               "2025 · +1 pt ≈ +370 businesses", delta_suffix=" pts")
    with cols[2]:
        nb = k["new_businesses"]
        ui.kpi("New businesses 2025", f"{int(nb['value']):,}", nb.get("change_pct"),
               f"Mainland + Free Zone · FZ {nb.get('fz_share_pct', 59):.0f}%")
    with cols[3]:
        ui.kpi("Activity signal", f"+{k['activity_signal']['value']}%", None, "Licence-implied · a signal, not GDP")
    with cols[4]:
        oa = k["open_alerts"]
        sev = oa.get("by_severity", {})
        ui.kpi("Open early warnings", f"{oa['value']}", None,
               f"{sev.get('high', 0)} high · {sev.get('medium', 0)} medium · {sev.get('low', 0)} low")
    st.write("")
    left, right = st.columns([2, 1], gap="large")
    with left:
        df = be.get_series(["new_reg_total"], group_type="zone", start="2024-01")
        _plot(ch.registrations_chart(
            df, "Free Zone keeps growing while mainland registrations dropped",
            "New registrations per month. Mainland data runs to Jun 2026; Free Zone to Oct 2026 "
            "(Nov is partial and not shown)", height=430))
    with right:
        ui.section("Early warnings")
        for a in sorted(be.get_alerts(), key=lambda a: not a.get("new", False))[:5]:
            ui.alert_card(a)
        st.caption("Factors and suggested actions are in the Early warnings tab.")


def _vo_share():
    vo = be.get_series(["virtual_office_share"])
    vo = vo[~vo["is_partial"]].sort_values("period")
    return round(float(vo["value"].iloc[-1]), 1) if not vo.empty else None


# ------------------------------------------------------------------ Alerts
def _alert_fig(a):
    """Best-effort mini chart for an alert; None if the series isn't available."""
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
    ui.section("Latest data updates")
    rows = []
    for c in changes:
        n = c.get("new_alerts", 0)
        rows.append(f"<b>{ui.ago(c['time'])}</b>: {c['dataset']} added {c['rows_added']:,} rows "
                    f"({', '.join(c.get('indicators', []))})"
                    + (f". <b style='color:{ch.RED_TXT}'>{n} new alert{'s' if n != 1 else ''}</b>" if n else
                       ". No new alerts."))
    st.markdown("<div class='r-meta'>" + "<br>".join(rows) + "</div>", unsafe_allow_html=True)


def _context_block(a):
    """News, events and wider-economy figures around the alert month. Context, not causes."""
    sector = a.get("sector") or a["group"].split(" · ")[0]
    try:
        ctx = be.get_context(a["period"], sector)
    except Exception:  # noqa: BLE001 - context is optional
        return
    st.markdown(f"**What was happening around {pd.Period(a['period'], 'M').strftime('%B %Y')}**  \n"
                "<span class='muted'>News, events and the wider economy at the time. These are possible "
                "influences for an analyst to check, not proven causes.</span>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1.4, 1, 0.8], gap="large")
    with c1:
        ui.section("In the news")
        news = ctx.get("news") or []
        for n in news:
            title = f"[{n['title']}]({n['url']})" if n.get("url") else n["title"]
            st.markdown(f"{title}  \n<span class='muted'>{n.get('source', '')}, {n.get('date', '')}</span>",
                        unsafe_allow_html=True)
        if not news:
            st.caption("No related headlines found for this period.")
        if ctx.get("news_live") and news:
            st.caption(f"Live headlines via {ctx.get('news_source') or 'news search'}, filtered to business news.")
        elif news:
            st.caption("Sample headlines: the live news search could not be reached.")
    with c2:
        ui.section("Events")
        for e in ctx.get("events") or []:
            end = e.get("end")
            when = e["start"] if end == e["start"] else e["start"] + (f" to {end}" if end else " onwards")
            st.markdown(f"{e['name']}  \n<span class='muted'>{when}</span>", unsafe_allow_html=True)
    with c3:
        ui.section("Wider economy")
        for m in ctx.get("macro") or []:
            st.markdown(f"{m['indicator']}: **{m['value']}{m.get('unit', '')}**  \n"
                        f"<span class='muted'>{m.get('period', '')}, {m.get('source', '')}</span>",
                        unsafe_allow_html=True)


def alerts(lang):
    _title("alerts")
    _updates_feed()
    sev = st.segmented_control("Severity", ["All", "high", "medium", "low"], default="All")
    items = be.get_alerts(None if sev in (None, "All") else sev)
    items = sorted(items, key=lambda a: not a.get("new", False))  # alerts from the latest sync first
    be.prefetch_context([(a["period"], a.get("sector") or a["group"].split(" · ")[0]) for a in items])
    if not items:
        st.success("No alerts at this severity.")
    for a in items:
        ui.alert_card(a, compact=False)
        with st.expander(f"Details: {a['group']}", expanded=a["id"] == items[0]["id"]):
            fig = _alert_fig(a)
            if fig is not None:
                _plot(fig, key=f"alert_chart_{a['id']}")
            _context_block(a)
            c1, c2 = st.columns(2, gap="large")
            with c1:
                st.markdown("**Possible contributing factors**  \n<span class='muted'>Context only. An analyst should "
                            "confirm before acting.</span>", unsafe_allow_html=True)
                for f in a["possible_factors"]:
                    st.markdown(f"- {f['text']}  \n  <span class='muted'>{f['source']} · {f['date']}</span>",
                                unsafe_allow_html=True)
            with c2:
                st.markdown("**Suggested DED actions**")
                for i, act in enumerate(a["actions"], 1):
                    st.markdown(f"{i}. {act}")
            if a.get("status") != "acknowledged":
                if st.button("Acknowledge and assign", key=f"ack_{a['id']}"):
                    be.acknowledge(a["id"], "gov_user")
                    st.toast(f"{a['id']} acknowledged and logged to the audit trail")
                    st.rerun()
            st.caption(f"Rule: {a['rule'].replace('_', ' ')} · indicator: {a['indicator']} · id {a['id']}")


# ------------------------------------------------------------------ Outlook
def outlook(lang):
    _title("outlook")
    c0, c1, c2, c3 = st.columns([1.3, 1, 1, 1])
    ind = c0.selectbox("Indicator", ["new_reg_mainland", "new_reg_fz", "new_reg_total"],
                       format_func={"new_reg_mainland": "Mainland registrations", "new_reg_fz": "Free Zone registrations",
                                    "new_reg_total": "All new registrations"}.get)
    rs = c1.slider("Recovery starts in (months)", 0, 12, 6)
    rl = c2.slider("Recovery takes (months)", 1, 18, 6)
    dp = c3.slider("Shock depth (% of current)", 0, 150, 100, step=10)
    fc_all = be.get_forecast(ind, rs, rl, dp)
    hist_all = be.get_series([ind])
    full_all = hist_all[~hist_all["is_partial"]]

    # Date window: any range from the first month of history to the end of the forecast
    months = sorted(set(full_all["period"]) | set(fc_all["period"]))
    default_start = "2024-01" if "2024-01" in months else months[0]
    w0, w1 = st.select_slider("Dates shown", options=months, value=(default_start, months[-1]),
                              format_func=lambda p: pd.Period(p, "M").strftime("%b %Y"), key="outlook_window")
    full = full_all[full_all["period"].between(w0, w1)]
    fc = fc_all[fc_all["period"].between(w0, w1)]

    fig = go.Figure()
    if not full.empty:
        fig.add_trace(go.Scatter(x=ch.dt(full["period"]), y=full["value"], name="Actual", mode="lines",
                                 line=dict(color=ch.BLACK, width=3, shape="spline", smoothing=0.5),
                                 hovertemplate="%{y:,.0f}"))
    cust = fc[fc["scenario"] == "custom"]
    if not cust.empty:
        x = ch.dt(cust["period"])
        fig.add_trace(go.Scatter(x=pd.concat([x, x[::-1]]), y=pd.concat([cust["hi"], cust["lo"][::-1]]),
                                 fill="toself", fillcolor="rgba(35,37,40,0.08)", line=dict(width=0),
                                 name="80% band (your scenario)", hoverinfo="skip"))
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
            x=xs, y=ys, name=ch.SCEN_NAME[s], mode="lines",
            line=dict(color=ch.SCEN_COL[s], width=3.5 if s == "custom" else 2, dash="solid" if s == "custom" else "dash",
                      shape="spline", smoothing=0.5),
            hovertemplate="%{y:,.0f}"))
    if not full.empty and full["period"].max() >= ch.SHOCK_START:
        ch.add_shock(fig, end=full["period"].max())
    label = lambda p: pd.Period(p, "M").strftime("%b %Y")  # noqa: E731
    ch.style(fig, "Three recovery paths, plus the one set by your sliders",
             f"Monthly registrations, {label(w0)} to {label(w1)}", 460)
    fig.update_yaxes(tickformat=",")
    _plot(fig)

    full, fc = full_all, fc_all  # the yearly totals below always use the full series

    actual_26 = full[full["period"].str.startswith("2026")]["value"].sum()
    rows = []
    for s in ["A", "B", "C", "custom"]:
        d = fc[fc["scenario"] == s]
        in_win = d[d["period"].between(w0, w1)]
        rows.append({"Scenario": ch.SCEN_NAME[s],
                     f"2026 total (actual to {label(full['period'].max())} + forecast)": int(actual_26 + d[d["period"].str.startswith("2026")]["mean"].sum()),
                     "2027 total": int(d[d["period"].str.startswith("2027")]["mean"].sum()),
                     f"Forecast, {label(w0)} to {label(w1)}": int(in_win["mean"].sum())})
    c1, c2 = st.columns([1.4, 1], gap="large")
    with c1:
        st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch",
                     column_config={k: st.column_config.NumberColumn(format="localized") for k in rows[0] if k != "Scenario"})
    with c2:
        ui.section("Assumptions")
        st.markdown(
            "- Model: SARIMAX on logs, with Ramadan/Eid effects and a disruption dial\n"
            "- Back-test error about 10% a year for mainland in normal years. Free Zone is shown as scenarios only.\n"
            "- Partial months are left out of the models\n"
            "- A: recovery starts after 9 months and takes 12. B: 5 and 6. C: 2 and 3.")


# ------------------------------------------------------------------ Actions
def actions(lang):
    _title("actions")
    c1, c2 = st.columns([1, 1.3], gap="large")
    with c1:
        ui.section("Policy simulator")
        delta = st.slider("Raise renewal rate by (points)", 0.0, 3.0, 1.0, 0.1)
        sim = be.simulate_renewal(delta)
        m1, m2, m3 = st.columns(3)
        m1.metric("Businesses retained", f"+{sim['businesses_retained']:,}")
        m2.metric("Active licences", f"{sim['active_licences']:,}")
        m3.metric("Activity signal", f"{sim['activity_signal_pct']:+.1f}%")
        camp = st.slider("New-licence campaign uplift (%)", 0, 20, 5)
        extra = round(18504 * camp / 100)
        st.metric("Extra new businesses / year", f"+{extra:,}")
        with st.expander("Assumptions"):
            for a in sim.get("assumptions", []):
                st.markdown(f"- {a}")
    with c2:
        base = sim["active_licences"] - sim["businesses_retained"]
        fig = go.Figure(go.Waterfall(
            orientation="v", measure=["absolute", "relative", "relative", "total"],
            x=["Active licences today", f"Renewal +{delta:.1f} pts", f"Campaign +{camp}%", "With DED actions"],
            y=[base, sim["businesses_retained"], extra, 0],
            text=[f"{base:,}", f"+{sim['businesses_retained']:,}", f"+{extra:,}", f"{base + sim['businesses_retained'] + extra:,}"],
            textposition="outside", connector=dict(line=dict(color="#CCCCCC")),
            increasing=dict(marker=dict(color=ch.GREEN)), totals=dict(marker=dict(color=ch.GOLD)),
            decreasing=dict(marker=dict(color=ch.RED))))
        ch.style(fig, f"+{sim['businesses_retained'] + extra:,} businesses from two policy levers",
                 "Active licences: today vs with renewal and campaign actions", 420, legend=False)
        fig.update_yaxes(range=[base * 0.9, (base + sim["businesses_retained"] + extra) * 1.03], tickformat=",")
        fig.update_layout(hovermode="closest")
        _plot(fig)
    ui.section("Recommended actions")
    k = be.get_kpis()
    zone = be.group_differences("zone")["table"].set_index("group")
    facts = {"renewal_rate": k["renewal_rate"]["value"], "retained_per_pt": be.simulate_renewal(1)["businesses_retained"],
             "virtual_office_share": _vo_share(), "active_licences": k["active_licences"]["value"],
             "mainland_change_pct": float(zone.loc["Mainland", "change_pct"]) if "Mainland" in zone.index else None,
             "open_alerts": k["open_alerts"]["value"]}
    if st.button("Generate recommendations", type="primary") or "gov_ai" in st.session_state:
        if "gov_ai" not in st.session_state:
            with st.spinner("Analysing facts"):
                st.session_state.gov_ai = ai.advise("gov_actions", facts, lang=lang)
        res = st.session_state.gov_ai
        st.markdown(res["text"])
        st.caption(f"Engine: {res['engine']}. Based on: " + "; ".join(res["cited_facts"]))


# ------------------------------------------------------------------ Sectors & groups
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
    fig = go.Figure(go.Heatmap(
        z=yoy.values, x=list(yoy.columns), y=list(yoy.index), zmid=0, zmin=-40, zmax=40,
        colorscale=[[0, ch.RED], [0.5, "#FFFFFF"], [1, ch.GREEN]],
        text=[[f"{v:+.0f}%" for v in row] for row in yoy.values], texttemplate="%{text}",
        textfont=dict(size=12), hovertemplate="%{y} · %{x}: %{z:+.1f}% YoY<extra></extra>",
        colorbar=dict(title="YoY", ticksuffix="%", thickness=12)))
    ch.style(fig, "Which sectors are heating up or cooling down",
             "New registrations, % change vs same quarter last year", 440, legend=False)
    fig.update_layout(hovermode="closest")
    fig.update_xaxes(showline=False, ticks="")
    _plot(fig)
    why = {"IT & e-commerce": "Digital economy growth that diversifies Ajman beyond trading",
           "Construction & contracting": "Watch the project pipeline; affects jobs and suppliers",
           "General trading": "Largest base, so small % changes mean many businesses",
           "Logistics & transport": "Benefits from port & road connectivity",
           "Restaurants & cafes": "Population-driven demand; seasonal around Ramadan"}
    st.dataframe(pd.DataFrame({"Sector": yoy.index, "Latest quarter YoY %": yoy.iloc[:, -1].round(1).values,
                               "Why it matters for Ajman": [why.get(s, "Track against population & area growth") for s in yoy.index]}),
                 hide_index=True, width="stretch")

    ui.section("Which groups differ")
    dims = {"zone": "Mainland vs FZ", "licence_type": "Licence type", "legal_form": "Legal form",
            "facility": "Facility (virtual office)", "area": "Area", "activity": "Activity"}
    tabs = st.tabs(list(dims.values()))
    for tab, dim in zip(tabs, dims):
        with tab:
            gd = be.group_differences(dim)
            st.markdown(f"**{gd['finding_ar'] if lang == 'ar' else gd['finding_en']}**")
            if dim == "facility":
                vo = be.get_series(["virtual_office_share"], start="2024-01")
                vo = vo[~vo["is_partial"]]
                fig = go.Figure(go.Scatter(x=ch.dt(vo["period"]), y=vo["value"], mode="lines", fill="tozeroy",
                                           line=dict(color=ch.GOLD, width=3, shape="spline"),
                                           fillcolor="rgba(182,138,53,0.15)", hovertemplate="%{y:.0f}%"))
                ch.add_shock(fig, end=vo["period"].max())
                ch.style(fig, "Virtual offices now dominate Free Zone setups",
                         "Share of new Free Zone registrations using a virtual office", 340, legend=False)
                fig.update_yaxes(ticksuffix="%", range=[0, 70])
                _plot(fig)
            _plot(ch.bar_change(gd["table"], "Change H1 2026 vs H1 2025", "Groups with < 5 records are suppressed"))


# ------------------------------------------------------------------ Drivers
def drivers(lang):
    _title("drivers")
    st.caption("Each driver is a hypothesis with a measurable proxy. They are monitored, not proven.")
    stat = {"ready": "Data ready", "partial": "Partial data", "data_needed": "Data needed"}
    ds = be.get_drivers()
    st.dataframe(pd.DataFrame([{
        "Driver": d["name"], "Status": stat.get(d["status"], d["status"]), "Hypothesis": d["hypothesis"],
        "What we measure": d["proxy"], "Source": d["source"], "Finding so far": d.get("result") or "",
    } for d in ds]), hide_index=True, width="stretch")
    for d in ds:
        if d.get("chart") is not None and len(d["chart"]):
            cd = d["chart"]
            f = go.Figure(go.Scatter(x=ch.dt(cd["period"]), y=cd["value"], mode="lines",
                                     line=dict(color=ch.GOLD, width=3, shape="spline"), hovertemplate="%{y:.0f}%"))
            ch.style(f, f"{d['name']}: {d.get('result') or ''}", d["proxy"], 300, legend=False)
            f.update_yaxes(ticksuffix="%")
            _plot(f)


# ------------------------------------------------------------------ Impact
def impact(lang):
    _title("impact")
    st.markdown(
        "- **Faster decisions.** Changes are flagged within weeks instead of months.\n"
        "- **More businesses kept.** Each extra point of renewal rate keeps about 370 businesses.\n"
        "- **Better targeting.** DED can see which sectors, areas and setup types need support.\n"
        "- **More investors.** New businesses get clear, public guidance on where demand is.")
    ui.section("KPI framework")
    st.dataframe(pd.DataFrame([
        ["Renewal rate", "94.3% (2025)", "95.3% (2027)", "DED licence data", "Monthly"],
        ["Businesses retained via renewal actions", "0", "+370 / year", "DED licence data", "Monthly"],
        ["Alert-to-action time", "Months (manual)", "< 14 days", "RASED audit log", "Monthly"],
        ["Mainland registrations vs scenario B", "−28% (H1 2026)", "Back to trend by end-2027", "DED open data", "Monthly"],
        ["Forecast error vs actuals", "~10% yearly (mainland)", "≤ 10%, tracked", "RASED back-test", "Monthly"],
        ["Decisions using RASED", "0", "≥ 50% of DED policy memos", "DED survey", "Quarterly"],
        ["Investor advisor sessions", "0", "1,000 / quarter", "RASED usage", "Quarterly"],
    ], columns=["KPI", "Baseline", "Target", "Data source", "Frequency"]), hide_index=True, width="stretch")
    st.caption("Licence data is a signal of economic activity. It is not GDP and not FDI.")


# ------------------------------------------------------------------ Export
def export(lang):
    _title("export")
    cat = be.get_catalog()
    names = dict(zip(cat["id"], cat["name_en"]))
    c1, c2 = st.columns([2, 1])
    ids = c1.multiselect("Metrics", list(cat["id"]), default=["new_reg_mainland", "new_reg_fz", "virtual_office_share"],
                         format_func=lambda i: names.get(i, i))
    gt = c2.selectbox("Group", ["total", "zone", "activity", "area", "facility"])
    c3, c4, c5 = st.columns(3)
    start = c3.text_input("From (YYYY-MM)", "2025-01")
    end = c4.text_input("To (YYYY-MM)", "2026-10")
    fmt = c5.radio("Format", ["json", "csv"], horizontal=True)
    if not ids:
        st.warning("Pick at least one metric.")
        return
    prev = be.get_series(ids, None if gt == "total" else gt, start, end)
    st.markdown(f"**Preview**, {len(prev):,} rows")
    st.dataframe(prev.head(200), hide_index=True, width="stretch", height=260)
    req = (tuple(ids), gt, start, end, fmt)
    if st.button(f"Prepare {fmt.upper()} export", type="primary"):
        # export() writes an audit-log line, so it runs only when the user asks for a file
        st.session_state.export = (req, be.export(ids, None if gt == "total" else gt, start, end, fmt))
        st.toast("Export logged to the audit trail")
    ready = st.session_state.get("export")
    if ready and ready[0] == req:
        st.download_button(f"Download {fmt.upper()}", ready[1], file_name=f"rased_export.{fmt}",
                           mime="application/json" if fmt == "json" else "text/csv")
    url = f"/v1/indicators/data?ids={','.join(ids)}" + (f"&group={gt}" if gt != "total" else "") + f"&from={start}&to={end}"
    st.markdown("**Same data via the REST API** (header `X-API-Key`):")
    st.code(f"curl -H 'X-API-Key: <your-key>' 'http://localhost:8000{url}'", language="bash")
    st.caption("Full API docs at /docs. Totals and averages only; groups with fewer than 5 records are hidden.")


PAGES = {"overview": overview, "alerts": alerts, "outlook": outlook, "actions": actions, "sectors": sectors,
         "drivers": drivers, "impact": impact, "export": export}


def render(page: str, lang: str):
    PAGES[page](lang)
