"""
forecast_kit.py — reusable forecasting functions for the Ajman Business Hackathon.

Everything here works on a monthly DataFrame indexed by pandas Period('M') with:
  - a target column (e.g. 'total' new licences), NaN for months with no data
  - calendar / shock columns: ramadan_share, eid_fitr, eid_adha, covid, disruption, source flag

Models: seasonal naive, SARIMAX (statsmodels), Prophet (optional), XGBoost (lag features).
Extras: back-testing, shock-effect estimate, scenario forecasts, stock-flow projection.
"""
from __future__ import annotations

import warnings
import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

EXOG_DEFAULT = ["ramadan_share", "eid_fitr", "eid_adha", "covid", "disruption", "issuance_source"]


# ----------------------------------------------------------------------------- data
def load_monthly(path="data/ajman_monthly.csv"):
    df = pd.read_csv(path)
    df["month"] = pd.PeriodIndex(df["month"], freq="M")
    df = df.set_index("month")
    if "source" in df:
        df["issuance_source"] = (df["source"] == "issuance_records").astype(int)
    return df


def extend_index(df, end):
    """Add future months (up to `end`) with calendar features filled in; target stays NaN."""
    from hijridate import Gregorian
    idx = pd.period_range(df.index[0], end, freq="M")
    out = df.reindex(idx)
    new = out.index[out.index > df.index[-1]]
    for p in new:
        days = pd.date_range(p.start_time, p.end_time, freq="D")
        hij = [Gregorian(d.year, d.month, d.day).to_hijri() for d in days]
        out.loc[p, "ramadan_share"] = np.mean([h.month == 9 for h in hij])
        out.loc[p, "eid_fitr"] = int(any(h.month == 10 and h.day <= 3 for h in hij))
        out.loc[p, "eid_adha"] = int(any(h.month == 12 and 9 <= h.day <= 12 for h in hij))
        out.loc[p, "covid"] = 0
        out.loc[p, "issuance_source"] = 1
        out.loc[p, "month_num"] = p.month
    out.index.name = df.index.name
    return out


# ----------------------------------------------------------------------------- metrics
def metrics(actual, pred):
    a, p = pd.Series(actual), pd.Series(pred)
    m = a.notna() & p.notna()
    a, p = a[m], p[m]
    return {
        "MAE": float(np.mean(np.abs(a - p))),
        "MAPE_%": float(np.mean(np.abs((a - p) / a)) * 100),
        "Bias_%": float((p.sum() / a.sum() - 1) * 100),
        "n": int(m.sum()),
    }


# ----------------------------------------------------------------------------- models
def seasonal_naive(y_train: pd.Series, horizon_index):
    """Same month last year; if that month is missing, the average of that calendar month in the last 3 years."""
    hist = y_train.copy()
    preds = {}
    for p in horizon_index:
        lag = p - 12
        while lag > hist.index[-1]:
            lag -= 12
        v = hist.get(lag, np.nan)
        if pd.isna(v):
            same = hist[(hist.index.month == p.month)].dropna().tail(3)
            v = same.mean()
        preds[p] = v
    return pd.Series(preds)


def fit_sarimax(y: pd.Series, exog: pd.DataFrame | None, order=(1, 0, 0), seasonal_order=(0, 1, 1, 12)):
    from statsmodels.tsa.statespace.sarimax import SARIMAX
    mod = SARIMAX(np.log(y), exog=exog, order=order, seasonal_order=seasonal_order, trend="c",
                  enforce_stationarity=False, enforce_invertibility=False)
    return mod.fit(disp=False, maxiter=200)


def predict_sarimax(res, exog_future: pd.DataFrame | None, horizon_index, alpha=0.2):
    fc = res.get_forecast(steps=len(horizon_index), exog=exog_future)
    mean = np.exp(fc.predicted_mean.values)
    ci = np.exp(fc.conf_int(alpha=alpha).values)
    return pd.DataFrame({"mean": mean, "lo": ci[:, 0], "hi": ci[:, 1]}, index=horizon_index)


def fit_predict_prophet(y: pd.Series, exog: pd.DataFrame, exog_future: pd.DataFrame, horizon_index):
    """Optional — returns None if prophet isn't installed."""
    try:
        from prophet import Prophet
    except Exception:
        return None
    import logging
    logging.getLogger("cmdstanpy").setLevel(logging.ERROR)
    train = pd.DataFrame({"ds": y.index.to_timestamp(), "y": np.log(y.values)})
    train = pd.concat([train, exog.reset_index(drop=True)], axis=1).dropna(subset=["y"])
    m = Prophet(yearly_seasonality=True, weekly_seasonality=False, daily_seasonality=False,
                changepoint_prior_scale=0.1, interval_width=0.8)
    for c in exog.columns:
        m.add_regressor(c)
    m.fit(train)
    fut = pd.DataFrame({"ds": horizon_index.to_timestamp()})
    fut = pd.concat([fut, exog_future.reset_index(drop=True)], axis=1)
    f = m.predict(fut)
    return pd.DataFrame({"mean": np.exp(f["yhat"].values), "lo": np.exp(f["yhat_lower"].values),
                         "hi": np.exp(f["yhat_upper"].values)}, index=horizon_index)


def _xgb_features(df: pd.DataFrame, ylog: pd.Series, exog_cols):
    X = pd.DataFrame(index=df.index)
    X["t"] = np.arange(len(df))
    X["month_num"] = df.index.month
    for c in exog_cols:
        X[c] = df[c].values
    X["lag12"] = ylog.shift(12)
    X["lag12_roll3"] = ylog.shift(12).rolling(3, min_periods=1).mean()
    X["lag24"] = ylog.shift(24)
    return X


def fit_predict_xgb(df: pd.DataFrame, target: str, train_end, horizon_index, exog_cols, seed=0):
    """Gradient boosting on log target with seasonal-lag features; recursive for horizons > 12."""
    from xgboost import XGBRegressor
    full = df.copy()
    ylog = np.log(full[target]).where(full.index <= train_end)
    X = _xgb_features(full, ylog, exog_cols)
    tr = X.index[(X.index <= train_end) & ylog.notna()]
    model = XGBRegressor(n_estimators=400, max_depth=3, learning_rate=0.03, subsample=0.9,
                         colsample_bytree=0.9, random_state=seed)
    model.fit(X.loc[tr], ylog.loc[tr])
    preds = {}
    for p in horizon_index:
        X = _xgb_features(full, ylog, exog_cols)
        v = float(model.predict(X.loc[[p]])[0])
        preds[p] = np.exp(v)
        ylog.loc[p] = v  # feed prediction forward for later lags
    return pd.Series(preds), model


# ----------------------------------------------------------------------------- back-test
def backtest(df, target, train_start, train_end, test_end, exog_cols=EXOG_DEFAULT, use_prophet=True):
    """Train on [train_start, train_end], forecast (train_end, test_end]; return metrics + predictions."""
    d = df.loc[train_start:test_end]
    train_end = pd.Period(train_end, "M")
    y_train = d.loc[:train_end, target]
    h_idx = d.index[d.index > train_end]
    actual = d.loc[h_idx, target]
    ex_tr, ex_fu = d.loc[:train_end, exog_cols], d.loc[h_idx, exog_cols]
    # drop exog columns that are constant in training (e.g. disruption before 2026) — can't be estimated
    keep = [c for c in exog_cols if ex_tr[c].nunique() > 1]
    preds = {}
    preds["Seasonal naive"] = seasonal_naive(y_train, h_idx)
    res = fit_sarimax(y_train, ex_tr[keep])
    preds["SARIMAX"] = predict_sarimax(res, ex_fu[keep], h_idx)["mean"]
    if use_prophet:
        pr = fit_predict_prophet(y_train, ex_tr[keep], ex_fu[keep], h_idx)
        if pr is not None:
            preds["Prophet"] = pr["mean"]
    preds["XGBoost"], _ = fit_predict_xgb(d, target, train_end, h_idx, keep)
    # simple ensemble of the model-based forecasts
    model_cols = [k for k in preds if k != "Seasonal naive"]
    preds["Ensemble (avg)"] = pd.concat([preds[k] for k in model_cols], axis=1).mean(axis=1)
    table = pd.DataFrame({k: metrics(actual, v) for k, v in preds.items()}).T
    out = pd.DataFrame(preds)
    out.insert(0, "actual", actual)
    return table, out


# ----------------------------------------------------------------------------- shock & scenarios
def shock_effect(df, target, train_start, exog_cols=EXOG_DEFAULT):
    """Estimate the disruption effect on the log scale, controlling for seasonality, Ramadan, Eid, COVID."""
    d = df.loc[train_start:]
    d = d.loc[: d[target].last_valid_index()]
    res = fit_sarimax(d[target], d[exog_cols])
    b = res.params["disruption"]
    lo, hi = res.conf_int(alpha=0.1).loc["disruption"]
    return {"coef": b, "effect_%": (np.exp(b) - 1) * 100,
            "effect_lo_%": (np.exp(lo) - 1) * 100, "effect_hi_%": (np.exp(hi) - 1) * 100,
            "result": res}


def scenario_paths(horizon_index):
    """Disruption intensity (1 = full effect seen in Mar–Jun 2026, 0 = back to normal)."""
    h = pd.Series(horizon_index.to_timestamp(), index=horizon_index)

    def ramp(start, end):
        s, e = pd.Timestamp(start), pd.Timestamp(end)
        frac = ((h - s).dt.days / (e - s).days).clip(0, 1)
        return 1 - frac

    return {
        "A. Disruption persists through 2027": pd.Series(1.0, index=horizon_index),
        "B. Normalises in H1 2027": ramp("2027-01-01", "2027-06-01"),
        "C. Quick recovery by Jan 2027": ramp("2026-09-01", "2027-01-01"),
    }


def forecast_scenarios(df, target, train_start, horizon_end, exog_cols=EXOG_DEFAULT, alpha=0.2):
    d = df.loc[train_start:]
    last = d[target].last_valid_index()
    d = d.loc[:last]
    res = fit_sarimax(d[target], d[exog_cols])
    fut = extend_index(df.loc[:last], horizon_end)
    h_idx = fut.index[fut.index > last]
    out = {}
    for name, path in scenario_paths(h_idx).items():
        ex = fut.loc[h_idx, exog_cols].copy()
        ex["disruption"] = path.values
        out[name] = predict_sarimax(res, ex.astype(float), h_idx, alpha=alpha)
    return out, res


# ----------------------------------------------------------------------------- stock & flow
def calibrate_renewal_rate(active_now, active_growth_yoy, new_last_12m, cancelled_per_month, renewals_per_month):
    """Back out the implied monthly lapse and renewal rate from DED's published figures.
    Active(t) = Active(t-12) + New(12m) - Cancelled(12m) - Lapsed(12m)."""
    active_prev = active_now / (1 + active_growth_yoy)
    lapsed_12m = active_prev + new_last_12m - 12 * cancelled_per_month - active_now
    lapsed_pm = max(lapsed_12m / 12, 0)
    r = renewals_per_month / (renewals_per_month + lapsed_pm)
    return {"active_12m_ago": active_prev, "lapsed_per_month": lapsed_pm, "renewal_rate": r}


def stock_flow(active0, new_path: pd.Series, renewals_per_month, renewal_rate, cancelled_per_month):
    """Active(t) = Active(t-1) + New(t) - Cancelled(t) - Lapsed(t),  Lapsed(t) = Due(t) * (1 - r(t)),
    Due(t) = renewals_per_month / r_base (licences reaching their renewal date each month).
    `renewal_rate` may be a float or a Series aligned to new_path."""
    r = renewal_rate if isinstance(renewal_rate, pd.Series) else pd.Series(renewal_rate, index=new_path.index)
    due = renewals_per_month / r.iloc[0]
    active, rows = active0, []
    for p in new_path.index:
        lapsed = due * (1 - r.loc[p])
        active = active + new_path.loc[p] - cancelled_per_month - lapsed
        rows.append((p, new_path.loc[p], due * r.loc[p], lapsed, active))
    return pd.DataFrame(rows, columns=["month", "new", "renewed", "lapsed", "active"]).set_index("month")


# ----------------------------------------------------------------------------- breakdowns
def change_table(frame: pd.DataFrame, before: tuple[str, str], after: tuple[str, str], min_before=20):
    a = frame.loc[before[0]:before[1]].sum()
    b = frame.loc[after[0]:after[1]].sum()
    t = pd.DataFrame({f"{before[0]}..{before[1]}": a, f"{after[0]}..{after[1]}": b})
    t["change_%"] = (b / a - 1) * 100
    t = t[a >= min_before].sort_values("change_%")
    return t.round(1)
