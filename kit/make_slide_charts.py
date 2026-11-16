"""Slide-sized versions of the key charts (no titles, large type, deck palette)."""
import warnings
import logging
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import forecast_kit as fk

warnings.filterwarnings("ignore")
logging.getLogger("cmdstanpy").setLevel(logging.ERROR)
INK, BG, VIOLET, ORANGE, TEAL, GREY = "#1E1440", "#F7F5FB", "#6A4BE0", "#D9692E", "#1F8F83", "#8C88A0"
plt.rcParams.update({"font.size": 19, "axes.spines.top": False, "axes.spines.right": False, "axes.grid": True,
                     "grid.alpha": 0.3, "axes.facecolor": BG, "figure.facecolor": BG, "axes.edgecolor": GREY,
                     "xtick.color": INK, "ytick.color": INK, "axes.labelcolor": INK, "font.family": "DejaVu Sans"})

df = fk.load_monthly("data/ajman_monthly.csv")

# 1) shock test
_, pred = fk.backtest(df, "total", "2018-01", "2026-02", "2026-06")
fig, ax = plt.subplots(figsize=(10.4, 6.6))
hist = df.loc["2025-01":"2026-06", "total"]
ax.plot(hist.index.to_timestamp(), hist.values, color=INK, lw=3.5, marker="o", ms=7, label="Actual new licences")
x = pred.index.to_timestamp()
ax.plot(x, pred["Ensemble (avg)"], color=ORANGE, lw=3.5, ls="--", marker="o", ms=7, label="Forecast made in Feb 2026")
ax.fill_between(x, pred[["SARIMAX", "XGBoost", "Prophet"]].min(axis=1), pred[["SARIMAX", "XGBoost", "Prophet"]].max(axis=1),
                color=ORANGE, alpha=0.15, label="Range of 3 models")
ax.axvspan(pd.Timestamp("2026-02-28"), pd.Timestamp("2026-06-30"), color=ORANGE, alpha=0.07)
ax.set_ylim(250, 850)
ax.legend(frameon=False, loc="lower left", fontsize=18)
ax.tick_params(axis="x", labelsize=17)
import matplotlib.dates as mdates
ax.xaxis.set_major_formatter(mdates.DateFormatter("%b\n%Y"))
plt.tight_layout()
plt.savefig("outputs/slide_shock.png", dpi=200)

# 2) scenarios
scen, _ = fk.forecast_scenarios(df, "total", "2018-01", "2027-12")
fig, ax = plt.subplots(figsize=(10.4, 6.6))
h = df.loc["2024-01":, "total"]
ax.plot(h.index.to_timestamp(), h.values, color=INK, lw=3.5, label="Actual")
for (name, f), c in zip(scen.items(), [ORANGE, VIOLET, TEAL]):
    xx = f.index.to_timestamp()
    ax.plot(xx, f["mean"], color=c, lw=3.5, label=name.split(". ")[0] + ". " + name.split(". ")[1].replace(" through 2027", "").replace(" by Jan 2027", ""))
    ax.fill_between(xx, f["lo"], f["hi"], color=c, alpha=0.08)
ax.axvspan(pd.Timestamp("2026-02-28"), pd.Timestamp("2026-06-30"), color=ORANGE, alpha=0.07)
ax.set_ylim(200, 1100)
ax.legend(frameon=False, loc="upper left", fontsize=17, ncol=2)
ax.xaxis.set_major_formatter(mdates.DateFormatter("%b\n%Y"))
ax.tick_params(axis="x", labelsize=17)
plt.tight_layout()
plt.savefig("outputs/slide_scenarios.png", dpi=200)
print("ok")
