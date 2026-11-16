"""
app.py — interactive scenario dashboard.  Run:  streamlit run app.py
Works offline. Move the sliders to change when the recovery starts, how long it takes and how deep the shock is.
"""
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import forecast_kit as fk

st.set_page_config(page_title="Ajman licence forecast", layout="wide")
NAVY, PURPLE, RED = "#2B1B5C", "#5B3FB5", "#C8423B"


@st.cache_data
def load():
    return fk.load_monthly("data/ajman_monthly.csv")


@st.cache_resource
def fit(target, train_start):
    df = load()
    d = df.loc[train_start:]
    d = d.loc[: d[target].last_valid_index()]
    return fk.fit_sarimax(d[target], d[fk.EXOG_DEFAULT])


df = load()
st.title("Ajman new economic licences: scenario forecast")
st.caption("Practice run on Ajman DED open data (Jan 2010 – Jun 2026). Model: SARIMAX on log scale with Ramadan, Eid, COVID and regional-disruption effects.")

with st.sidebar:
    target = st.selectbox("Indicator", ["total", "professional", "commercial", "industrial", "permits"])
    train_start = st.selectbox("Train from", ["2018-01", "2016-01", "2020-01", "2023-01"], index=0)
    horizon_end = st.selectbox("Forecast to", ["2027-06", "2027-12", "2028-06"], index=1)
    st.markdown("**Scenario dial**")
    rec_start = st.slider("Recovery starts (months after Jun 2026)", 0, 18, 6)
    rec_len = st.slider("Recovery takes (months)", 1, 18, 6)
    depth = st.slider("Shock depth vs Mar–Jun 2026 (%)", 0, 150, 100, step=10)

res = fit(target, train_start)
last = df[target].last_valid_index()
fut = fk.extend_index(df.loc[:last], horizon_end)
h = fut.index[fut.index > last]
k = np.arange(1, len(h) + 1)
dial = np.clip(1 - (k - rec_start) / rec_len, 0, 1) * depth / 100
ex = fut.loc[h, fk.EXOG_DEFAULT].astype(float).copy()
ex["disruption"] = dial
fc = fk.predict_sarimax(res, ex, h)

b = res.params["disruption"]
c1, c2, c3 = st.columns(3)
c1.metric("Estimated shock effect (Mar–Jun 2026)", f"{(np.exp(b) - 1) * 100:.0f}%")
c2.metric(f"Forecast, next 12 months ({target})", f"{fc['mean'].iloc[:12].sum():,.0f}")
prev = df.loc["2025-07":"2026-06", target].sum()
c3.metric("vs last 12 months actual", f"{prev:,.0f}", f"{(fc['mean'].iloc[:12].sum() / prev - 1) * 100:+.0f}%")

hist = df.loc["2023-01":, target]
fig = go.Figure()
fig.add_trace(go.Scatter(x=hist.index.to_timestamp(), y=hist.values, name="Actual", line=dict(color="black", width=2)))
x = h.to_timestamp()
fig.add_trace(go.Scatter(x=list(x) + list(x[::-1]), y=list(fc["hi"]) + list(fc["lo"][::-1]), fill="toself",
                         fillcolor="rgba(91,63,181,0.15)", line=dict(width=0), name="80% range"))
fig.add_trace(go.Scatter(x=x, y=fc["mean"].round(), name="Forecast", line=dict(color=PURPLE, width=3)))
fig.add_vrect(x0="2026-03-01", x1="2026-06-30", fillcolor=RED, opacity=0.08, line_width=0, annotation_text="regional disruption")
fig.update_layout(template="plotly_white", height=480, legend=dict(orientation="h", y=1.1), margin=dict(t=40))
st.plotly_chart(fig, width="stretch")

st.subheader("Forecast table")
st.dataframe(fc.round(0).rename(index=str), width="stretch")
st.download_button("Download forecast (CSV)", fc.round(0).rename(index=str).to_csv().encode(), "forecast.csv")
