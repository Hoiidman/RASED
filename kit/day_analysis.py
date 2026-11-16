"""
day_analysis.py — analysis of the organisers' files (16 Nov 2026).
  data/organisers/ded_annual.xlsx  : DED annual 2016–2025 (GDP, licences, permits)
  data/organisers/fz_monthly.xlsx  : Ajman Free Zone company registrations, Jan 2024 – Nov 2026
Outputs: outputs/day_*.png, outputs/day_results.json, outputs/day_tables.xlsx
"""
import json, warnings, logging
import numpy as np, pandas as pd, statsmodels.api as sm
import matplotlib.pyplot as plt, matplotlib.dates as mdates
from statsmodels.tsa.statespace.sarimax import SARIMAX
from hijridate import Gregorian
warnings.filterwarnings("ignore"); logging.getLogger("cmdstanpy").setLevel(logging.ERROR)

INK, BG, VIOLET, ORANGE, TEAL, GREY = "#1E1440", "#F7F5FB", "#6A4BE0", "#D9692E", "#1F8F83", "#8C88A0"
plt.rcParams.update({"font.size": 18, "axes.spines.top": False, "axes.spines.right": False, "axes.grid": True,
                     "grid.alpha": .3, "axes.facecolor": BG, "figure.facecolor": BG, "font.family": "DejaVu Sans"})
R = {}

# ------------------------------------------------------------------ A. annual DED data
a = pd.read_excel("data/organisers/ded_annual.xlsx").replace("-", np.nan)
for c in a.columns[1:]: a[c] = pd.to_numeric(a[c])
a = a.set_index("Year")
a["Lapsed"] = a["Active Licenses"].shift(1) + a["New Licenses"] - a["Cancelled Licenses"] - a["Active Licenses"]
a["Renewal rate"] = a["Renewed Licenses"] / (a["Renewed Licenses"] + a["Lapsed"])

# GDP nowcast: log-log models on active licences and permits; leave-future-out back-test
drivers = ["Active Licenses", "Permits"]
def fit_pred(train, x, xval):
    m = sm.OLS(np.log(train.GDP), sm.add_constant(np.log(train[x]))).fit()
    return float(np.exp(m.params.iloc[0] + m.params.iloc[1] * np.log(xval))), m
bt = []
for yr in range(2021, 2025):
    tr = a.loc[2017:yr - 1].dropna(subset=["GDP"] + drivers)
    preds = [fit_pred(tr, x, a.loc[yr, x])[0] for x in drivers]
    bt.append({"year": yr, "actual": a.loc[yr, "GDP"], "nowcast": np.mean(preds)})
bt = pd.DataFrame(bt).set_index("year"); bt["error_%"] = (bt.nowcast / bt.actual - 1) * 100
tr = a.loc[2017:2024]
fits = {x: fit_pred(tr, x, a.loc[2025, x]) for x in drivers}
gdp25 = np.mean([v[0] for v in fits.values()])
mape = bt["error_%"].abs().mean()
R["gdp_2025"] = {"estimate_aed_mn": round(gdp25), "growth_%": round((gdp25 / a.loc[2024, "GDP"] - 1) * 100, 1),
                 "range_aed_mn": [round(gdp25 * (1 - mape / 100)), round(gdp25 * (1 + mape / 100))],
                 "by_driver": {x: round(v[0]) for x, v in fits.items()},
                 "elasticity": {x: round(v[1].params.iloc[1], 2) for x, v in fits.items()},
                 "r2": {x: round(v[1].rsquared, 2) for x, v in fits.items()},
                 "backtest_mape_%": round(mape, 1), "backtest": bt.round(1).reset_index().to_dict("records")}
R["renewal"] = a[["Lapsed", "Renewal rate"]].dropna().round(3).reset_index().to_dict("records")

# ------------------------------------------------------------------ B. Free Zone monthly
f = pd.read_excel("data/organisers/fz_monthly.xlsx")
f["month"] = pd.PeriodIndex(f["Month"], freq="M"); f = f.set_index("month")
PARTIAL = pd.Period("2026-11", "M")
y = f["Company records"].astype(float).copy(); y.loc[PARTIAL] = np.nan   # partial month excluded

def calendar(idx):
    rows = []
    for p in idx:
        days = pd.date_range(p.start_time, p.end_time, freq="D")
        h = [Gregorian(d.year, d.month, d.day).to_hijri() for d in days]
        rows.append({"ramadan_share": np.mean([x.month == 9 for x in h])})
    return pd.DataFrame(rows, index=idx)

end = pd.Period("2027-12", "M")
idx = pd.period_range(y.index[0], end, freq="M")
X = calendar(idx); X["disruption"] = (X.index >= pd.Period("2026-03", "M")).astype(float)
hist = y.index[y.notna()]
res = SARIMAX(np.log(y), exog=X.loc[y.index], order=(1, 1, 0), trend="n").fit(disp=False)
R["fz_shock_effect_%"] = round((np.exp(res.params["disruption"]) - 1) * 100, 1)

h = idx[idx > y.index[-1]]
h = pd.period_range(PARTIAL, end, freq="M")
def ramp(start, stop):
    t = pd.Series(h.to_timestamp(), index=h); s, e = pd.Timestamp(start), pd.Timestamp(stop)
    return (1 - ((t - s).dt.days / (e - s).days).clip(0, 1)).values
scen = {"A. Disruption persists": np.ones(len(h)), "B. Normalises in H1 2027": ramp("2027-01-01", "2027-06-01"),
        "C. Quick recovery by Jan 2027": ramp("2026-12-01", "2027-01-01")}
fc = {}
for name, dial in scen.items():
    ex = X.loc[h].copy(); ex["disruption"] = dial
    g = res.get_forecast(steps=len(h), exog=ex)
    ci = np.exp(g.conf_int(alpha=0.2).values)
    fc[name] = pd.DataFrame({"mean": np.exp(g.predicted_mean.values), "lo": ci[:, 0], "hi": ci[:, 1]}, index=h)
R["fz_2027"] = {k: round(v.loc["2027-01":"2027-12", "mean"].sum()) for k, v in fc.items()}
R["fz_nov_2026_full_month"] = {k: round(v.loc[PARTIAL, "mean"]) for k, v in fc.items()}
R["fz_years"] = {"2024": int(f.loc["2024", "Company records"].sum()), "2025": int(f.loc["2025", "Company records"].sum()),
                 "2026_jan_oct": int(f.loc["2026-01":"2026-10", "Company records"].sum()),
                 "2025_jan_oct": int(f.loc["2025-01":"2025-10", "Company records"].sum())}
# back-test: train to Aug 2025, test Sep 2025 – Feb 2026 (pre-shock)
ytr = y.loc[:"2025-08"]
r2 = SARIMAX(np.log(ytr), exog=X.loc[ytr.index, ["ramadan_share"]], order=(1, 1, 0), trend="n").fit(disp=False)
tst = pd.period_range("2025-09", "2026-02", freq="M")
p2 = np.exp(r2.get_forecast(steps=len(tst), exog=X.loc[tst, ["ramadan_share"]]).predicted_mean.values)
R["fz_backtest_mape_%"] = round(float(np.mean(np.abs(p2 / y.loc[tst].values - 1)) * 100), 1)

# facility mix
fac = f[[c for c in f.columns if c.startswith("Facility:")]].div(f["Company records"], axis=0)
R["virtual_office_share_%"] = {str(k): round(v * 100) for k, v in fac["Facility: Virtual Office"].iloc[[0, 11, 23, 25, 29, 33]].items()}

# ------------------------------------------------------------------ C. 2026 active licences & GDP (scenarios)
mainland = pd.read_csv("outputs/forecast_scenarios.csv")   # from the kit (DED open data, monthly)
act25, canc = a.loc[2025, "Active Licenses"], a.loc[2025, "Cancelled Licenses"]
h1_2026_new = 2697                                          # Jan–Jun 2026 actual, DED open data
rr_base = a.loc[2025, "Renewal rate"]
gdp26 = {}
for name_kit, name in zip(sorted(mainland.scenario.unique()), scen):
    new26 = h1_2026_new + mainland[(mainland.scenario == name_kit) & mainland.month.between("2026-07", "2026-12")].forecast.sum()
    rr = rr_base - (0.02 if name.startswith("A") else 0.01 if name.startswith("B") else 0.005)   # assumption
    lapsed = a.loc[2025, "Renewed Licenses"] / rr_base * (1 - rr)
    act26 = act25 + new26 - canc - lapsed
    g = np.mean([np.exp(fits[x][1].params.iloc[0] + fits[x][1].params.iloc[1] * np.log(act26 if x == "Active Licenses" else a.loc[2025, "Permits"] * act26 / act25)) for x in drivers])
    gdp26[name] = {"new_licences": round(new26), "active_end_2026": round(act26), "renewal_rate": round(rr, 3),
                   "licence_implied_gdp_aed_mn": round(g), "growth_vs_2025_%": round((g / gdp25 - 1) * 100, 1)}
R["2026"] = gdp26

# ------------------------------------------------------------------ charts
# 1 GDP nowcast
fig, ax = plt.subplots(figsize=(10.4, 6.6))
ax.plot(a.index[:-1], a.GDP.iloc[:-1] / 1000, color=INK, lw=3.5, marker="o", ms=8, label="Reported GDP (AED bn)")
ax.errorbar([2025], [gdp25 / 1000], yerr=[[gdp25 / 1000 - R["gdp_2025"]["range_aed_mn"][0] / 1000], [R["gdp_2025"]["range_aed_mn"][1] / 1000 - gdp25 / 1000]],
            fmt="o", color=ORANGE, ms=14, lw=3, capsize=10, label=f"2025 estimate: {gdp25/1000:.1f}bn (+{R['gdp_2025']['growth_%']}%)")
ax.plot(bt.index, bt.nowcast / 1000, ls="--", color=VIOLET, lw=2.5, marker="s", ms=7, label=f"Back-test estimates (error {mape:.1f}%)")
ax.set_xticks(range(2016, 2026)); ax.legend(frameon=False, loc="upper left", fontsize=16); ax.set_ylim(28, 44)
plt.tight_layout(); plt.savefig("outputs/day_gdp_nowcast.png", dpi=200); plt.close()
# 2 FZ registrations + scenarios
fig, ax = plt.subplots(figsize=(10.4, 6.6))
ax.plot(y.index.to_timestamp(), y.values, color=INK, lw=3.5, label="Free Zone registrations")
ax.scatter([PARTIAL.to_timestamp()], [f.loc[PARTIAL, "Company records"]], color=GREY, s=60, zorder=5, label="Nov 2026 (partial month)")
for (n, v), c in zip(fc.items(), [ORANGE, VIOLET, TEAL]):
    ax.plot(v.index.to_timestamp(), v["mean"], color=c, lw=3, label=n)
    pass  # 80% bands omitted on the slide: too wide with 34 months of history (see day_tables.xlsx)
ax.axvspan(pd.Timestamp("2026-02-28"), pd.Timestamp("2026-06-30"), color=ORANGE, alpha=.07)
ax.xaxis.set_major_formatter(mdates.DateFormatter("%b\n%Y")); ax.legend(frameon=False, fontsize=15, loc="upper left"); ax.set_ylim(0, 1600)
plt.tight_layout(); plt.savefig("outputs/day_fz_scenarios.png", dpi=200); plt.close()
# 3 facility mix
fig, ax = plt.subplots(figsize=(10.4, 6.6))
q = fac.loc[:"2026-10"]; t = q.index.to_timestamp()
ax.plot(t, q["Facility: Virtual Office"] * 100, color=ORANGE, lw=3.5, label="Virtual office")
ax.plot(t, q["Facility: Office"] * 100, color=VIOLET, lw=3.5, label="Physical office")
ax.axvspan(pd.Timestamp("2026-02-28"), pd.Timestamp("2026-06-30"), color=ORANGE, alpha=.07)
ax.set_ylabel("% of new Free Zone companies"); ax.set_ylim(0, 100); ax.legend(frameon=False, loc="upper left")
ax.xaxis.set_major_formatter(mdates.DateFormatter("%b\n%Y"))
plt.tight_layout(); plt.savefig("outputs/day_facility_mix.png", dpi=200); plt.close()
# 4 renewal rate
fig, ax = plt.subplots(figsize=(10.4, 6.6))
rr = a["Renewal rate"].dropna() * 100
ax.plot(rr.index, rr.values, color=TEAL, lw=3.5, marker="o", ms=9)
for yr, v in rr.items(): ax.annotate(f"{v:.1f}%", (yr, v), textcoords="offset points", xytext=(0, 12), ha="center", fontsize=15)
ax.set_ylabel("Licences renewed (%)"); ax.set_ylim(80, 100); ax.set_xticks(rr.index)
plt.tight_layout(); plt.savefig("outputs/day_renewal_rate.png", dpi=200); plt.close()

with pd.ExcelWriter("outputs/day_tables.xlsx") as w:
    a.round(3).to_excel(w, sheet_name="DED annual + derived")
    bt.round(1).to_excel(w, sheet_name="GDP back-test")
    pd.DataFrame({k: v["mean"].round() for k, v in fc.items()}).rename(index=str).to_excel(w, sheet_name="FZ scenarios")
    pd.DataFrame(gdp26).T.to_excel(w, sheet_name="2026 scenarios")
    (fac * 100).round(1).rename(index=str).to_excel(w, sheet_name="FZ facility mix %")
json.dump(R, open("outputs/day_results.json", "w"), indent=2, default=float)
print(json.dumps(R, indent=1, default=float))
