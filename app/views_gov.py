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
from labels import TITLES

PC = ch.CHART_CONFIG


def _title(page):
    t, q = TITLES[page]
    ui.page_title(t, q)


def _plot(fig):
    st.plotly_chart(fig, width="stretch", config=PC)


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
        ui.kpi("New businesses 2025", f"{nb['value']:,}", nb.get("change_pct"),
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
            "New business registrations per month · grey dot = partial month (excluded from models)", height=430))
    with right:
        st.markdown("**🔔 Early warnings**")
        for a in be.get_alerts()[:5]:
            ui.alert_card(a)
        st.caption("Open *Early warnings* for factors and suggested actions.")


# ------------------------------------------------------------------ Alerts
def alerts(lang):
    _title("alerts")
    sev = st.segmented_control("Severity", ["All", "high", "medium", "low"], default="All")
    items = be.get_alerts(None if sev in (None, "All") else sev)
    if not items:
        st.success("No alerts at this severity.")
    for a in items:
        ui.alert_card(a, compact=False)
        with st.expander(f"Why and what to do — {a['group']}", expanded=a["id"] == items[0]["id"]):
            c1, c2 = st.columns(2, gap="large")
            with c1:
                st.markdown("**Possible contributing factors** · *context only — analyst to confirm*")
                for f in a["possible_factors"]:
                    st.markdown(f"- {f['text']}  \n  <span class='muted'>{f['source']} · {f['date']}</span>",
                                unsafe_allow_html=True)
            with c2:
                st.markdown("**Suggested DED actions**")
                for i, act in enumerate(a["actions"], 1):
                    st.markdown(f"{i}. {act}")
            if a.get("status") != "acknowledged":
                if st.button("✓ Acknowledge & assign", key=f"ack_{a['id']}"):
                    be.acknowledge(a["id"], "gov_user")
                    st.toast(f"{a['id']} acknowledged — logged to audit trail")
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
    fc = be.get_forecast(ind, rs, rl, dp)
    hist = be.get_series([ind], start="2024-01")
    full = hist[~hist["is_partial"]]

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=ch.dt(full["period"]), y=full["value"], name="Actual", mode="lines",
                             line=dict(color=ch.BLACK, width=3, shape="spline", smoothing=0.5),
                             hovertemplate="%{y:,.0f}"))
    cust = fc[fc["scenario"] == "custom"]
    x = ch.dt(cust["period"])
    fig.add_trace(go.Scatter(x=pd.concat([x, x[::-1]]), y=pd.concat([cust["hi"], cust["lo"][::-1]]),
                             fill="toself", fillcolor="rgba(35,37,40,0.08)", line=dict(width=0),
                             name="80% band (your scenario)", hoverinfo="skip"))
    last_x, last_y = ch.dt(full["period"]).iloc[-1], full["value"].iloc[-1]
    for s in ["A", "B", "C", "custom"]:
        d = fc[fc["scenario"] == s]
        fig.add_trace(go.Scatter(
            x=pd.concat([pd.Series([last_x]), ch.dt(d["period"])]), y=pd.concat([pd.Series([last_y]), d["mean"]]),
            name=ch.SCEN_NAME[s], mode="lines",
            line=dict(color=ch.SCEN_COL[s], width=3.5 if s == "custom" else 2, dash="solid" if s == "custom" else "dash",
                      shape="spline", smoothing=0.5),
            hovertemplate="%{y:,.0f}"))
    ch.add_shock(fig, end=full["period"].max())
    ch.style(fig, "Three recovery paths — and yours", "Monthly registrations · history + scenarios to Dec 2027", 460)
    fig.update_yaxes(tickformat=",")
    _plot(fig)

    actual_26 = full[full["period"].str.startswith("2026")]["value"].sum()
    rows = []
    for s in ["A", "B", "C", "custom"]:
        d = fc[fc["scenario"] == s]
        rows.append({"Scenario": ch.SCEN_NAME[s],
                     "2026 total (actual Jan–Oct + forecast)": int(actual_26 + d[d["period"].str.startswith("2026")]["mean"].sum()),
                     "2027 total": int(d[d["period"].str.startswith("2027")]["mean"].sum())})
    c1, c2 = st.columns([1.4, 1], gap="large")
    with c1:
        st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch",
                     column_config={k: st.column_config.NumberColumn(format="localized") for k in rows[0] if k != "Scenario"})
    with c2:
        with st.expander("📋 Assumptions", expanded=True):
            st.markdown(
                "- Model: SARIMAX (log) + Ramadan/Eid effects + disruption dial\n"
                "- Back-test error: ~10% yearly (mainland, normal years); FZ shown as scenarios only\n"
                "- Partial months excluded from models\n"
                "- A = recovery after 9 months over 12 · B = 5 over 6 · C = 2 over 3")


# ------------------------------------------------------------------ Actions
def actions(lang):
    _title("actions")
    c1, c2 = st.columns([1, 1.3], gap="large")
    with c1:
        st.markdown("#### 🎚️ Policy simulator")
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
    st.markdown("#### 🤖 Recommended actions")
    k = be.get_kpis()
    zone = be.group_differences("zone")["table"].set_index("group")
    facts = {"renewal_rate": k["renewal_rate"]["value"], "retained_per_pt": be.simulate_renewal(1)["businesses_retained"],
             "virtual_office_share": 59, "active_licences": k["active_licences"]["value"],
             "mainland_change_pct": float(zone.loc["Mainland", "change_pct"]) if "Mainland" in zone.index else None,
             "open_alerts": k["open_alerts"]["value"]}
    if st.button("Generate recommendations", type="primary") or "gov_ai" in st.session_state:
        if "gov_ai" not in st.session_state:
            with st.spinner("Analysing facts…"):
                st.session_state.gov_ai = ai.advise("gov_actions", facts, lang=lang)
        res = st.session_state.gov_ai
        with st.container(border=True):
            st.markdown(res["text"])
        st.caption(f"Engine: {res['engine']} · grounded on: " + "; ".join(res["cited_facts"]))


# ------------------------------------------------------------------ Sectors & groups
def sectors(lang):
    _title("sectors")
    df = be.get_series(["new_reg_total"], group_type="activity", start="2024-01")
    df = df[~df["is_partial"]].copy()
    p = pd.PeriodIndex(df["period"], freq="M")
    df["q"] = p.asfreq("Q").astype(str)
    q = df.groupby(["group", "q"])["value"].sum().unstack()
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
    why = {"IT & e-commerce": "Digital economy growth — diversifies Ajman beyond trading",
           "Construction & contracting": "Watch project pipeline; affects jobs and suppliers",
           "General trading": "Largest base — small % changes = many businesses",
           "Logistics & transport": "Benefits from port & road connectivity",
           "Restaurants & cafes": "Population-driven demand; seasonal around Ramadan"}
    st.dataframe(pd.DataFrame({"Sector": yoy.index, "Latest quarter YoY %": yoy.iloc[:, -1].round(1).values,
                               "Why it matters for Ajman": [why.get(s, "Track against population & area growth") for s in yoy.index]}),
                 hide_index=True, width="stretch")

    st.markdown("#### Which groups differ")
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
    st.caption("Each driver is a hypothesis with a measurable proxy — monitored, not proven.")
    stat = {"ready": (ch.GREEN, "Data ready"), "partial": (ch.GOLD, "Partial data"),
            "data_needed": (ch.MUTED, "Monitoring — data needed")}
    ds = be.get_drivers()
    for i in range(0, len(ds), 2):
        cols = st.columns(2, gap="medium")
        for col, d in zip(cols, ds[i:i + 2]):
            c, lab = stat.get(d["status"], (ch.MUTED, d["status"]))
            with col:
                st.markdown(
                    f'<div class="card"><h4>{d["name"]} <span class="pill" style="background:{c}">{lab}</span></h4>'
                    f'<div class="muted"><b>Hypothesis:</b> {d["hypothesis"]}<br><b>Proxy:</b> {d["proxy"]}<br>'
                    f'<b>Source:</b> {d["source"]}<br><b>Test:</b> {d["test"]}</div>'
                    + (f'<div style="margin-top:6px"><b>Result:</b> {d["result"]}</div>' if d.get("result") else "")
                    + "</div>", unsafe_allow_html=True)
                if d.get("chart") is not None and len(d["chart"]):
                    cd = d["chart"]
                    f = go.Figure(go.Scatter(x=ch.dt(cd["period"]), y=cd["value"], mode="lines",
                                             line=dict(color=ch.GOLD, width=3, shape="spline")))
                    ch.style(f, "", "", 180, legend=False)
                    f.update_layout(margin=dict(l=10, r=10, t=10, b=10))
                    _plot(f)


# ------------------------------------------------------------------ Impact
def impact(lang):
    _title("impact")
    cols = st.columns(4)
    for col, (icon, head, txt) in zip(cols, [
        ("⏱️", "Faster decisions", "Changes flagged in weeks, not months"),
        ("🏪", "Businesses kept", "~370 businesses per +1 pt renewal"),
        ("🎯", "Targeted support", "Know which sectors, areas & setups need help"),
        ("🌍", "More investors", "Clear, public guidance for new businesses")]):
        col.markdown(f'<div class="card"><h4>{icon} {head}</h4><div class="muted">{txt}</div></div>',
                     unsafe_allow_html=True)
    st.markdown("#### KPI framework")
    st.dataframe(pd.DataFrame([
        ["Renewal rate", "94.3% (2025)", "95.3% (2027)", "DED licence data", "Monthly"],
        ["Businesses retained via renewal actions", "0", "+370 / year", "DED licence data", "Monthly"],
        ["Alert-to-action time", "Months (manual)", "< 14 days", "RASED audit log", "Monthly"],
        ["Mainland registrations vs scenario B", "−28% (H1 2026)", "Back to trend by end-2027", "DED open data", "Monthly"],
        ["Forecast error vs actuals", "~10% yearly (mainland)", "≤ 10%, tracked", "RASED back-test", "Monthly"],
        ["Decisions using RASED", "0", "≥ 50% of DED policy memos", "DED survey", "Quarterly"],
        ["Investor advisor sessions", "0", "1,000 / quarter", "RASED usage", "Quarterly"],
    ], columns=["KPI", "Baseline", "Target", "Data source", "Frequency"]), hide_index=True, width="stretch")
    st.info("Licence data is a **signal** of economic activity — not GDP, and not FDI. RASED says so on every page.")


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
    st.markdown(f"**Preview** · {len(prev):,} rows")
    st.dataframe(prev.head(200), hide_index=True, width="stretch", height=260)
    data = be.export(ids, None if gt == "total" else gt, start, end, fmt)
    if st.download_button(f"⬇️ Download {fmt.upper()}", data, file_name=f"rased_export.{fmt}",
                          mime="application/json" if fmt == "json" else "text/csv", type="primary"):
        st.toast("Export logged to audit trail")
    url = f"/v1/indicators/data?ids={','.join(ids)}" + (f"&group={gt}" if gt != "total" else "") + f"&from={start}&to={end}"
    st.markdown("**Same data via the REST API** (header `X-API-Key`):")
    st.code(f"curl -H 'X-API-Key: <your-key>' 'http://localhost:8000{url}'", language="bash")
    st.caption("Full API docs at /docs (FastAPI / OpenAPI). Aggregates only; groups < 5 records suppressed.")


PAGES = {"overview": overview, "alerts": alerts, "outlook": outlook, "actions": actions, "sectors": sectors,
         "drivers": drivers, "impact": impact, "export": export}


def render(page: str, lang: str):
    PAGES[page](lang)
