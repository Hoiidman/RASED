# Ajman Business Hackathon 2026 — Forecasting Kit

A ready-to-run forecasting pipeline, tested on **real Ajman DED open data** (new economic licences, 2010 – Jun 2026).
On the day, swap in the organisers' dataset and re-run.

## Setup (once per laptop, needs internet)
- **Windows:** double-click `setup_windows.bat`
- **Mac / Linux:** `bash setup_mac_linux.sh`

Both create a `.venv`, install `requirements.txt`, and run `check_setup.py`, which runs the whole pipeline once.
Then **turn wifi off and run `python check_setup.py` again** to prove it works offline.
If Prophet won't install (it's the usual troublemaker on Windows), set `USE_PROPHET = False` in the notebook. Everything else still runs.

## What's inside
| File | What it does |
|---|---|
| `Ajman_Forecasting_Kit.ipynb` | The full pipeline with outputs: explore → baseline → SARIMAX / Prophet / XGBoost → back-test → shock-effect estimate → 3 scenarios → stock-flow equation → export. Runs in ~10 s. |
| `forecast_kit.py` | The reusable functions behind the notebook. |
| `prepare_data.py` | Builds `data/ajman_monthly.csv` from `data/raw/`, adds Ramadan / Eid / COVID / regional-disruption markers, and checks totals against DED's published figures. |
| `app.py` | Interactive scenario dashboard: `streamlit run app.py`. Sliders for recovery start, recovery length, shock depth. |
| `outputs/` | Charts for the slides (`fig1`–`fig6`), `dashboard.html` (works offline), `forecast_scenarios.csv`, `forecast_feed.json` (integration format), back-test tables. |
| `data/raw/` | Monthly tables extracted from DED open data (ajmanded.ae → Open Data). |

## The data (and its problems: say this in the pitch)
Source: Ajman DED open data files, licence-level records aggregated to months.
- **2010-01 → 2022-06:** "Licenses in Ajman (activities)" register snapshot, counted by licence start date. It only contains licences still on file in 2024, so older years are understated.
- **2023-01 → 2026-06:** issuance records (legal-form, areas-and-activities and regions-and-activity files).
- **Gaps:** Jul–Dec 2022 (missing from the snapshot), Nov–Dec 2024 (every Jul–Dec 2024 file was published on 20 Oct 2024), Oct 2024 (partial month). These are left as NaN, not zero.
- **Quality issues found:** DED's Jul–Dec 2024 legal-form file repeats 616 licences from May–Jun 2023; area names are spelled differently across years ("Ajman Industrial2" vs "Ajman Industrial 2"); the 2023 areas-and-activities file is missing about 30% of licences (3,923 vs 5,570).
- **Checks passed:** monthly totals match across the type / area / activity tables. Q1 2026 = 1,624 new licences (DED press release: 1,617). H1 2025 growth +25% (DED: +24%).

## Headline findings from the practice run
- New licences **fell 37.5%** in Mar–Jun 2026 vs Mar–Jun 2025 (1,489 vs 2,383). Economic permits fell only 15%: existing businesses held up better than new entry.
- After controlling for seasonality, Ramadan, Eid and COVID, the **effect of the regional disruption is about −34%** (90% range −48% to −18%).
- Hardest hit: building cleaning (−82%), delivery services (−74%), building contracting (−62%). Women's ready-made clothing rose 12%.
- **Back-test (normal times):** SARIMAX and the ensemble get ~12% average error (MAPE), versus 19% for "same month last year".
- **Shock test:** every model trained up to Feb 2026 over-predicted Mar–Jun 2026 by 60–84%. That's why scenarios matter.
- **2027 scenarios:** about 5,600 new licences if the disruption persists, 7,800 if things normalise in H1 2027, 8,600 with a quick recovery (2025 actual: 7,666).
- **Stock-flow:** DED's published numbers imply a ~97.6% renewal rate (about 71 licences lapse a month).

## On the day
1. Put the organisers' file in `data/`. Make sure there's a `month` (YYYY-MM) column.
2. Re-create the calendar columns with `prepare_data.ramadan_eid_features()` if it's a new dataset.
3. Change the **CONFIG** cell → *Run All*.
4. Use `fig4` (shock test) and `fig5` (scenarios) on the slides.
