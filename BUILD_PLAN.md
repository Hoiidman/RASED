# RASED (راصد) — Build Plan (for Claude Code)

*RASED — sees the change before it happens · يرصد التغيير قبل حدوثه*

**Hackathon:** Ajman Business Hackathon 2026 · **Today:** 16 Nov 2026 · **Demo:** 12:30
**Build window:** 10:55 → 12:20 (≈85 min, after a 10-min GitHub setup buffer), two agents in parallel. Everything not built by 12:15 is shown as "roadmap" in slides.

> **⚡ PRIORITY NOTE — speed over completeness:** Focus on speed. Build the **skeleton first** (every page exists, navigable, showing real or mock numbers and charts), **then** add features. Most judges are not technical — what matters is that we can **always show something on screen**. A clickable app with charts beats a perfect engine nobody can see. When in doubt: make it visible, make it run, polish later.
>
> **📊 Graphs must look good.** Charts are what judges remember. Use Plotly with the UAE palette (§6), clean white backgrounds, no gridline clutter, clear titles that state the finding (e.g. "Free Zone up 7% while mainland fell 28%"), readable labels, annotations on key events (Mar 2026 shock), and hover tooltips. Agent A: return tidy DataFrames ready to plot (clean period strings, sensible units, no NaN gaps). Agent B: invest polish time in charts before anything else.

> **Instruction to Claude Code:** Two agents build in parallel (§9, §12–§14). Build in the phase order below. After each phase the app must run end-to-end (`streamlit run app/main.py` and `uvicorn api.main:app`). Commit (or copy the folder) after every phase. **Never break a working demo to add a feature.** If a phase overruns its timebox, cut to its "minimum" line and move on.

---

## 0. Critique of the brief (read first)

| Idea | Verdict | Change |
|---|---|---|
| Two dashboards (government + investor) | ✅ Strong — maps to Impact + Innovation | One Streamlit app, two portals (sidebar switch). Not two apps. |
| Live Ajman Open Data API | ✅ Required, but **risky live on hotel wifi**; portal may block scripts | Connector with **cache + "last synced" badge + offline snapshot fallback**. Never call the network during the demo render path. |
| AI suggestions + investor advisor | ✅ Wow factor, ⚠️ hallucination & needs internet + API key | **Grounded AI only**: the LLM receives *computed facts JSON* and must cite them; never invents numbers. **Template fallback** when no key/offline so the demo never fails. |
| News-linked early warning | ⚠️ Live news is slow, noisy, and **politically sensitive** in UAE | Anomaly detection (built) + **curated event calendar** (built) + news connector (GDELT, optional, behind a toggle). Wording: "possible contributing factors — needs analyst review". Neutral language ("regional disruption"). |
| "Licence data can't measure GDP/FDI" | ✅ Correct and important | Rename GDP output to **"Licence-implied activity signal"**; show permits/active licences as *indicators*, not GDP. **No FDI number.** Show "foreign-owner share" only where data exists, labelled "proxy, incomplete". |
| Security | ✅ Must be visible | API keys, role-based portals, aggregate-only data (no trade names), small-group suppression, audit log of exports, secrets in `.env`. Compliance items as roadmap (see §8). |
| Population & tourism | ⚠️ Only if the open-data portal has those datasets | Sector cards are **generic**: any dataset the connector loads becomes a card. Don't hard-code tourism. |
| Per-business forecasting for investors | ⚠️ We cannot forecast *their* business | Forecast **their sector + area** (demand, competition, growth), and say so. Add "not financial advice". |
| Export JSON with metric selector | ✅ Easy, high value for "integration" | Gov Export page: multiselect metrics + date range + format (JSON/CSV) + matching API URL shown. |

**What I added:** data-freshness badge, partial-month flag, assumptions panel, small-group suppression, Arabic/English toggle (labels file), audit log, 60-second demo video as fallback, judging-criteria map, demo script.

---

## 1. Architecture

```
rased/
  config/
    sources.yaml        # data registry: every dataset, URL, refresh, column map
    assumptions.yaml    # scenario dates, renewal dip, partial months, shock start
    events.yaml         # curated event calendar (Ramadan/Eid, fee waivers, regional disruption...)
    playbook.yaml       # alert type -> suggested DED actions
    labels_en.yaml / labels_ar.yaml
  core/
    connectors.py       # local_file, ajman_open_data, ded_open_data, gdelt_news (all cached)
    store.py            # standard long table in DuckDB/parquet: period, indicator, group, value, unit, source
    analytics.py        # wraps existing forecast_kit.py, day_analysis.py, backtest_history.py
    alerts.py           # anomaly detection + factor matching + actions
    ai.py               # grounded LLM (Claude API) + template fallback
    security.py         # roles, API keys, suppression, audit log
  app/main.py           # Streamlit: Government portal + Investor portal
  api/main.py           # FastAPI: same core functions, OpenAPI docs at /docs
  data/cache/ data/snapshot/   # snapshot = last good data, used offline
  .env.example          # ANTHROPIC_API_KEY, GOV_PASSWORD, API_KEYS
```

**Reuse from existing kit** (`kit/`): `forecast_kit.py` (SARIMAX/XGB/scenarios/stock-flow), `day_analysis.py` (organisers' files), `backtest_history.py`, `data/ajman_monthly.csv`, `data/by_activity.csv`, `data/by_area.csv`, `data/organisers/*.xlsx`.

**Standard format (everything converts to this):**
`period | frequency | indicator | group_type | group | value | unit | source | is_partial`
→ Every module reads only this table, so new data = new rows, no code change.

---

## 2. Data sources (`config/sources.yaml`)

| id | Source | Content | Refresh | Status |
|---|---|---|---|---|
| fz_monthly | organisers file | Free Zone registrations by licence/legal form/facility | manual | ✅ have |
| ded_annual | organisers file | GDP, inflation, new/renewed/cancelled/active licences, permits | manual | ✅ have |
| ded_licences | ajmanded.ae open data JSON | licence-level new licences by activity/area/type (Jan 2025–Jun 2026) | monthly | ✅ in kit (aggregated) |
| ajman_open_data | data.ajman.ae | **verify first** — likely Opendatasoft (`/api/explore/v2.1/catalog/datasets`). Population, tourism, real estate if present | daily/monthly | ⚠️ verify in Phase 0 (10 min max) |
| fza_open_data | fza.ae/open-data | Free Zone open data | monthly | ⚠️ verify |
| news | GDELT DOC 2.0 API (no key) filtered "Ajman OR UAE economy" | headlines for alert context | on demand | optional (toggle) |

### 2.1 External information (all keyless, each optional, each with timeout + cache)

| id | Source | Used for |
|---|---|---|
| news | GDELT DOC 2.0 API (`api.gdeltproject.org/api/v2/doc/doc`) — query "Ajman" / "UAE economy" + sector keyword | headlines shown as *possible factors* on alerts |
| macro | World Bank API (`api.worldbank.org/v2/country/ARE/indicator/...`) — UAE GDP growth, inflation | macro context next to Ajman indicators |
| fx_oil (optional) | any free keyless FX/commodity feed if available at the venue | context only; skip if no keyless source |
| events | `config/events.yaml` (curated, versioned) | Ramadan/Eid, fee waivers, policy changes, regional disruption |

External data is **context, never a model input that changes forecasts silently** — every external item shown with source + timestamp.

### 2.2 Automatic updates when Ajman Open Data changes (`core/sync.py`)

1. **Scheduler:** APScheduler background job inside the API process (`api/main.py` startup), every 30 min (configurable in `sources.yaml`; 1 min in demo mode). Streamlit reads the store; it never fetches itself.
2. **Change detection per dataset** (cheapest first): Opendatasoft catalogue metadata `modified`/`data_processed` timestamp → HTTP `ETag`/`Last-Modified` → SHA-256 of the downloaded file. Store last fingerprint in `data/cache/fingerprints.json`.
3. **On change:** download → validate (schema matches column map, row count not < 50% of previous, no future dates) → if invalid keep old snapshot + raise a *data-quality alert* → if valid: ingest to store, re-run models, regenerate alerts, write a **"What changed"** entry (dataset, rows added, indicators affected, new alerts) to `data/changelog.jsonl`.
4. **New datasets on the portal:** catalogue diff detects new dataset ids → listed in Gov "Data Health" as *"New dataset available — map columns to add"* (one-click add if its columns match an existing mapping).
5. **UI:** `st_autorefresh` (or `st.rerun` timer) every 60 s on Gov portal; banner "Updated 3 min ago · 2 datasets changed · 1 new alert"; Data Health page lists each source: status, last checked, last changed, rows.
6. **API/integration:** `GET /v1/changes?since=` returns the changelog; optional webhook URL in `.env` receives a POST on every change (partners plug this into their workflow).
7. **Resilience:** any source failing 3 times → marked "stale" (amber, with text) and the app keeps serving the last good snapshot.
8. **Permission:** the portal's robots.txt blocks automated crawling of some paths — use only the **official API endpoints**, identify the client in the User-Agent, keep to the schedule, and **confirm with the organisers that automated API access is allowed** (they asked teams to use it).

Connector rules: timeout 5 s; on failure → use `data/snapshot/`; record `last_synced`, `rows`, `status` per source; show these in a **Data Health** strip on both portals. Partial current month (e.g. Nov 2026 FZ = 379) → `is_partial=True`, excluded from models, drawn as grey dot.

---

## 3. Analytics (already proven — wrap, don't rebuild)

| Output | Method | Evidence (back-test) |
|---|---|---|
| Registrations outlook (mainland + FZ) | SARIMAX log + Ramadan/Eid + disruption dial; 3 scenarios | mainland yearly error ~10% normal years; FZ ≈ naive → show as scenarios only |
| Active licences | Stock-flow: Active = prev + New − Cancelled − Lapsed; renewal rate from DED data | 0.9% error normal years |
| Licence-implied activity signal | log-log on active licences & permits (2017–2024) | 2.3% normal years; 8.7% in 2020 → **signal, not GDP** |
| Economy ↔ business links | growth correlations, 2017–2024 (n=8, indicative) | new licences ≈ 2.4× GDP growth; renewals lag 1 yr |
| Renewal lever | +1 pt renewal ≈ +370 businesses | derived from DED 2025 figures |
| Group differences | mainland vs FZ; licence type; legal form; facility; area; activity | e.g. FZ +7% vs mainland −28% H1 2026; virtual office 35%→59% |

---

## 4. Early-warning system (`core/alerts.py`)

**Detect** (per indicator × group, monthly):
1. **Off-forecast:** actual outside the model's 80% band → severity by distance.
2. **Unusual change:** YoY change beyond the series' historical 5th/95th percentile.
3. **Mix shift:** share change > 10 pts in 6 months (e.g. virtual office share).
4. **Renewal pressure:** renewal rate below 3-yr average − 1 pt.

**Explain** (possible factors, never "causes"):
- Match alert month against `events.yaml` (Ramadan/Eid, fee waivers, policy changes, regional disruption from Mar 2026, data gaps).
- If news toggle on: top 5 GDELT headlines for that month + sector keyword. Label: *"Context only — analyst to confirm."*

**Act:** `playbook.yaml` maps alert type → 2–3 DED actions (e.g. renewal pressure → targeted renewal reminders via AI renewal service, fee instalments, outreach to virtual-office companies).

Alert card = indicator · group · what happened (number vs expected) · severity (text + colour) · possible factors · suggested actions · "Assign/Acknowledge" button (writes to audit log).

### 4.1 Drivers monitor — internal factors (`config/drivers.yaml`, Gov page "Drivers")

Each driver = **hypothesis → measurable proxy → data source → how we test it → status**. Shown as *hypotheses being monitored*, not proven causes.

| Driver | Hypothesis | Proxy we can measure | Source | Test | Status today |
|---|---|---|---|---|---|
| Government policy (fees, discounts, FZ offers) | Cheaper/promoted licences → more registrations | Dated policy events (fee waivers, FZ packages) | `events.yaml` (+ news) | **Event study**: registrations 3 months before vs after each event, vs same months last year | ✅ build (events we know: Mar 2026 fee/fine waivers; add FZ 2025 offers when dates confirmed) |
| Corporate tax | Tax level changes openings/closures | UAE CT is **fixed** (9% above AED 375k since June 2023; qualifying Free Zone income 0%) — not a moving variable | event date only | Before/after June 2023 on cancellations & legal-form mix; FZ vs mainland gap | ⚠️ treat as one-off event + FZ advantage, not a dial |
| Visa / residency rules | Easier residency → more freelancers & virtual offices | FZ "Free Lancer" licences, virtual-office share | fz_monthly (have) | Trend + event dates for visa changes | ✅ data ready (virtual office 35%→59%) |
| Rent / real estate prices | High rent → virtual offices instead of physical | Ajman rent/tenancy & real-estate indices | Ajman Open Data (if available) | Correlation & lag vs virtual-office share | ⚠️ needs dataset from portal |
| Infrastructure (roads, ports) | New infrastructure → factories & warehouses | Industrial licences, FZ "Warehouse"/"Land" facilities, industrial-area licences | have (by_area, fz facility) + project dates in events | Event study around project completion dates | 🟡 data ready, need project dates |
| Competition between emirates | Rival FZ fee cuts → Ajman loses registrations | Ajman FZ share of new registrations; rival fee changes as events | fz_monthly + news/events | Alert when Ajman share falls after a rival event | 🟡 needs rival fee events (manual entry) |
| Population growth | More people → more shops & services | Population, retail/services licences | SCC / Ajman Open Data population | Licences per 1,000 residents by activity | ⚠️ needs population dataset |

Rules: every driver card shows **data available / missing**; drivers without data appear as "monitoring — data needed" (a clear roadmap item, and proof we know what's missing). Add/change drivers by editing `drivers.yaml` only.
**Investor portal reuse:** the same drivers feed "Watch-outs" (e.g. "rent rising → consider virtual office", "rival free-zone offers").

---

## 5. AI layer (`core/ai.py`)

- Model: Claude API (`ANTHROPIC_API_KEY` in `.env`). If missing/offline → deterministic templates from the same facts.
- **Grounding contract (system prompt):** "Use only the facts in FACTS_JSON. Quote numbers exactly with their source and period. If a fact is missing, say so. Licence data is not GDP or FDI. Give suggestions as options with trade-offs, not orders. Neutral language on regional events. Answer in {lang}."
- FACTS_JSON = only aggregates (no trade names, no licence numbers).
- Uses: (a) Gov "What should DED do" narrative; (b) monthly briefing; (c) Investor business advisor; (d) themes: economic growth, investment opportunities, government planning, population & tourism (only if data loaded).

---

## 6. Dashboard design (UAE Design System)

**Colours** (UAE Design System core palette, designsystem.gov.ae):
- Primary **AE Gold** `#B68A35` (500) · dark `#92722A` (600) · light `#F2ECCF` (100) · bg tint `#F9F7ED` (50)
- Secondary **AE Black** `#232528` · text `#232528` · muted `#5F6368`
- Status (always with a text label, never colour alone): good **UAE Green** `#006B48` · alert **UAE Red** `#C8102E` · watch: AE Gold `#B68A35`
- Neutrals `#FFFFFF` / `#F2F2F2`
- Streamlit `.streamlit/config.toml`: `primaryColor="#B68A35"`, `backgroundColor="#FFFFFF"`, `secondaryBackgroundColor="#F9F7ED"`, `textColor="#232528"`.
- Charts: series order AE Gold, AE Black, UAE Green, `#92722A`, grey. Scenario A/B/C = Red / Gold / Green **with labels**.
- Header bar: AE Black with gold title "RASED | راصد", language toggle EN/ع, Data Health badge.

### 6.1 Government portal (login: password from `.env`)

Sidebar nav (6 pages):

1. **Overview — "What's changing"**
   - Row of 5 KPI tiles: Active licences (41,316, +12.5%) · Renewal rate (94.3%) · New businesses 2025 mainland+FZ (18,504; FZ 59%) · Licence-implied activity signal (+7.1%, *signal*) · Open alerts (n, by severity)
   - Left 2/3: line chart new registrations mainland vs FZ (monthly) with shaded Mar 2026+.
   - Right 1/3: **Alerts feed** (top 5 alert cards).
2. **Outlook — "What may happen next"**
   - Scenario dial (sidebar): recovery start, recovery length, shock depth. Chart: history + 3 scenarios + 80% band. Table: 2026/2027 totals per scenario. Assumptions panel (read from `assumptions.yaml`).
3. **Actions — "What DED should do"**
   - **Policy simulator:** renewal rate slider (+0–3 pts) → businesses retained → active licences → activity signal. New-licence campaign slider.
   - AI recommendations panel (grounded), each with "why" (facts cited) and "how to measure".
4. **Sectors & groups**
   - Sector growth heat table (activity × period, % change) with a "Why it matters for Ajman" column (AI/template one-liner).
   - "Which groups differ": tabs Mainland vs FZ · Licence type · Legal form · Facility (virtual office shift) · Area. Each: chart + 1-line finding.
5. **Impact & measurement**
   - How Ajman benefits + KPI framework table: KPI · baseline · target · data source · frequency (e.g. renewal rate 94.3% → 95.3%; alert-to-action time; businesses retained; % decisions using RASED; forecast error tracked monthly vs actuals).
6. **Export & API**
   - Metric **multiselect** (from indicator catalogue), group filter, date range, format JSON/CSV → preview → **Download**. Shows equivalent API call (`GET /v1/indicators?ids=...&from=...&to=...`) and a copy button. Each export written to audit log.

### 6.2 Investor portal (public, no login)

Sidebar nav (3 pages), warmer layout, more text, fewer controls:

1. **Opportunities** — cards for fastest-growing activities/areas (growth %, demand trend sparkline, competition level = new licences per area), mainland vs FZ comparison, "setup types investors choose" (virtual office trend).
2. **Watch-outs** — sectors cooling or crowded, seasonality (Ramadan/Eid months), current outlook scenario in plain language, renewal/cost considerations.
3. **My business advisor** — form: activity (dropdown from catalogue), area, mainland/FZ, size, plans (free text) → output: sector + area outlook (forecast chart), competition, risks, 3 tailored suggestions (grounded AI). Disclaimer: "Indicative, based on public data; not financial advice."

---

## 7. API (`api/main.py`, FastAPI, auth `X-API-Key`)

| Method | Endpoint | Returns |
|---|---|---|
| GET | `/v1/health` | sources, last_synced, status |
| GET | `/v1/indicators` | catalogue of metric ids |
| GET | `/v1/indicators/data?ids=&group=&from=&to=` | standard-format rows (JSON) |
| GET | `/v1/forecast/{indicator}?scenario=A|B|C` | forecast + 80% band |
| GET | `/v1/alerts?severity=` | alert cards |
| POST | `/v1/simulate/renewal` `{delta_pts}` | businesses retained, active licences, signal |
| POST | `/v1/advisor` `{activity, area, zone, notes}` | grounded advice JSON |
| POST | `/v1/sync` (admin key) | trigger connector refresh |
| GET | `/v1/changes?since=` | "what changed" log (datasets, rows, new alerts) |
| GET | `/v1/context?month=&sector=` | external context (news headlines, World Bank macro, events) |

OpenAPI docs at `/docs` = proof of integration in the demo. Rate limit (simple in-memory), CORS restricted.

---

## 8. Security & governance

**Build today:** role split (Gov password / public investor) · API keys in `.env` (never in code; `.env.example` only) · aggregate-only outputs, suppress any group with < 5 records · no trade names/licence numbers exposed · AI receives aggregates only · audit log (`data/audit.log`: who/what/when for exports, syncs, acknowledged alerts) · read-only connectors.
**Roadmap slide (say it, don't build):** UAE Pass SSO for officials · hosting on UAE-based government cloud (data residency) · HTTPS/TLS · alignment with UAE Personal Data Protection Law (Federal Decree-Law No. 45 of 2021) and UAE Information Assurance standards · role-based access per department · penetration test before go-live.

---

## 9. Phases, timeboxes & two-agent split

**Two Claude Code agents work in parallel on the same GitHub repo.**
- **Agent A — "Engine"**: data, models, alerts, drivers, sync, external context, export, API. Owns `core/` (except `core/ai.py`), `config/`, `api/`, `data/`.
- **Agent B — "Experience"**: both dashboards, UAE theme, AI layer, demo polish. Owns `app/`, `core/ai.py`, `core/mocks.py`, `.streamlit/`, `assets/`.
- **Shared, edit only by agreement:** `CONTRACT.md`, `README.md`, `requirements.txt` (append-only).
- B never waits for A: B builds against `core/mocks.py` (same shapes as the contract) and switches to real functions with env `RASED_USE_MOCKS=0`.

| Time | Phase | Agent A — Engine | Agent B — Experience | Gate (both must pass) |
|---|---|---|---|---|
| **10:45–10:55** | **Buffer (humans)** | — idle — | — idle — | Team creates GitHub repo, clones, copies `kit/`, adds `.env`, opens two Claude Code sessions. Paste kickoff prompts (§13). |
| 10:55–11:05 | **P0 Contract & skeleton** | Write `CONTRACT.md` (§12) as stubs in `core/*.py` returning correct shapes; folder + config files | Theme (`.streamlit/config.toml`), app shell with Gov/Investor switch, header, Data Health strip; `core/mocks.py` from contract | `streamlit run app/main.py` opens with mocks; `python -m core.store` runs |
| 11:05–11:35 | **P1 Core** | `store.py` (kit CSVs + organisers xlsx → standard table), `analytics.py` (KPIs, forecasts, scenarios via `forecast_kit`), `exporter.py`, `sync.py` (fingerprints + changelog, manual), open-data check (≤10 min) | Gov pages: Overview, Outlook (scenario dial), Export (metric multiselect → JSON/CSV + API URL shown) | Real data on Overview with `RASED_USE_MOCKS=0`; JSON export downloads |
| 11:35–11:55 | **P2 Intelligence** | `alerts.py` (4 rules), `drivers.py` + `drivers.yaml`, `events.yaml`, `playbook.yaml`, `simulate_renewal()`, `group_differences()` | Gov pages: Alerts cards, Actions (policy simulator), Sectors & groups, Drivers, Impact & measurement | ≥3 real alerts render; simulator moves numbers |
| 11:55–12:10 | **P3 Reach** | FastAPI (`/v1/health, indicators, indicators/data, forecast, alerts, changes, context, simulate/renewal`), APScheduler (demo: 1 min), GDELT + World Bank `context.py` | `core/ai.py` (grounded Claude + template fallback), Investor portal (Opportunities, Watch-outs, My business advisor), auto-refresh banner | `/docs` opens; advisor answers "restaurant, mainland, Al Nuaimia" |
| 12:10–12:20 | **P4 Integrate & freeze** | Run full smoke test, fix contract mismatches, final sync → snapshot | Wire banner to `sync.changes()`, polish, Arabic labels for headers | Smoke test (§14) all green → tag `demo-v1` |
| 12:20–12:30 | **P5 Demo prep** | Stand by for fixes only | Record 60-s screen video | Video saved; no more code changes |

**Cut rules if late:** P1 minimum = Overview + Export. P2 minimum = alert rules 1+3, simulator, Drivers static table. P3 minimum = template advisor + `/v1/health` + `/v1/indicators/data`. Anything cut → roadmap slide.

Not built = roadmap slide: live news on every alert, UAE Pass, webhooks, full Arabic UI & AI output.

---

## 10. Judging-criteria map

| Criterion (weight) | Where we score |
|---|---|
| Innovation & Originality (20%) | Two portals; early warning with factors + actions; renewal lever in AED; investor advisor |
| Problem Understanding (15%) | 2026 shock; FZ vs mainland divergence; virtual-office shift; licence data ≠ GDP/FDI (we say it) |
| Feasibility & Implementation (20%) | Uses DED/Ajman open data + API; runs offline; JSON export + REST API; config-driven |
| Impact & Sustainability (20%) | Measurement framework with baselines/targets; auto-updating connectors; expandable sector cards |
| Analytical Approach & Prototype (15%) | Back-tested models (errors shown), assumptions panel, scenarios, working prototype |
| Presentation (10%) | 4-min script below; Q&A answers prepared |

---

## 11. Demo script (4 min)

1. (30 s) Problem: shock in 2026, FZ vs mainland diverge, officials see data months late.
2. (60 s) **Gov → Overview → Alerts**: open the virtual-office alert → factors → actions.
3. (45 s) **Outlook**: move the dial; **Actions**: +1 pt renewal = ~370 businesses.
4. (30 s) **Export**: pick 3 metrics → JSON; show `/docs` API. **Live update moment:** click "Sync now" (or wait for the 1-min job) → banner "dataset changed · new alert" appears.
5. (45 s) **Investor → Advisor**: type a business → tailored outlook.
6. (30 s) Security + roadmap + "licence data is a signal, not GDP/FDI".

---

## 12. Interface contract (`CONTRACT.md`) — the only thing both agents must agree on

All functions return plain pandas DataFrames / dicts. Periods are strings `YYYY-MM` (monthly) or `YYYY` (annual).

```python
# core/store.py                                         (owner: A)
get_catalog() -> DataFrame[id, name_en, name_ar, unit, frequency, group_types, source, last_period]
get_series(ids: list[str], group_type: str|None=None, start: str|None=None, end: str|None=None)
    -> DataFrame[period, frequency, indicator, group_type, group, value, unit, source, is_partial]

# core/analytics.py                                     (owner: A)
get_kpis() -> dict  # {"active_licences":{"value":41316,"change_pct":12.5,"period":"2025","source":...}, ...}
get_forecast(indicator: str, recovery_start: int=6, recovery_len: int=6, depth_pct: int=100)
    -> DataFrame[period, scenario, mean, lo, hi]        # scenarios "A","B","C","custom"
simulate_renewal(delta_pts: float) -> dict  # {"businesses_retained":int,"active_licences":int,"activity_signal_pct":float,"assumptions":[...]}
group_differences(dim: str) -> {"table": DataFrame, "finding_en": str, "finding_ar": str}
    # dim in {"zone","licence_type","legal_form","facility","area","activity"}

# core/alerts.py                                        (owner: A)
get_alerts(severity: str|None=None) -> list[dict]
    # {"id","indicator","group","period","what_happened","expected","actual","severity":"high|medium|low",
    #  "rule","possible_factors":[{"text","source","date"}],"actions":[str],"status":"open|acknowledged"}
acknowledge(alert_id: str, user: str) -> None

# core/drivers.py                                       (owner: A)
get_drivers() -> list[dict]  # {"id","name","hypothesis","proxy","source","test","status":"ready|partial|data_needed","result":str|None,"chart":DataFrame|None}

# core/sync.py, core/context.py, core/exporter.py       (owner: A)
sync_status() -> list[dict]    # {"source","status":"ok|stale|error","last_checked","last_changed","rows"}
run_sync(force: bool=False) -> dict   # {"changed":[source ids],"new_alerts":int}
get_changes(since: str|None=None) -> list[dict]
get_context(period: str, sector: str|None=None) -> {"news":[...],"macro":[...],"events":[...]}
export(ids, group_type=None, start=None, end=None, fmt="json") -> bytes   # writes audit log

# core/ai.py                                            (owner: B)
advise(mode: str, facts: dict, profile: dict|None=None, lang: str="en") -> {"text": str, "cited_facts": [str], "engine": "claude|template"}
    # mode in {"gov_actions","briefing","investor","theme"}
```
Changing a signature = send a CONTRACT CHANGE message (§13) and wait for "ACK" before pushing.

---

## 13. Agent communication & relay protocol

**Channel:** the repo itself. Two files, append-only:
- `agents/to_B.md` — Agent A writes here, Agent B reads
- `agents/to_A.md` — Agent B writes here, Agent A reads

Both agents: `git pull --rebase` → read your inbox → work → commit & push **only your owned folders** + your outbox, at least at the end of every phase.

**Message format (every message, also printed in chat so a human can relay it):**
```
=== RELAY ▸ FROM: A  TO: B  #<n>  <time> ===
TYPE: STATUS | NEED | CONTRACT CHANGE | BLOCKER | ACK | DONE
SUMMARY: <one line>
DETAILS: <what changed / what is needed, file paths, function names>
ACTION FOR RECEIVER: <exact instruction the other agent should execute>
=== END RELAY ===
```

**Human relay rule (works even if git is slow):** whenever an agent prints a RELAY block, the person running it copies the whole block and pastes it into the other agent's chat with: *"Message from the other agent — read, act on ACTION FOR RECEIVER, reply with an ACK relay block."* Each agent must end every phase by printing a STATUS relay block.

**Conflict rules:** never edit the other agent's folders; if you need a change there, send NEED. Merge conflicts in shared files → Agent A resolves `CONTRACT.md`/`requirements.txt`, Agent B resolves `README.md`.

### Kickoff prompt — Agent A (paste into Claude Code session 1)
```
You are Agent A ("Engine") on the RASED hackathon project. Read BUILD_PLAN.md fully, then follow §9 for Agent A only.
You own core/ (except core/ai.py and core/mocks.py), config/, api/, data/. Never edit app/, .streamlit/, core/ai.py, core/mocks.py.
Reuse kit/forecast_kit.py, kit/day_analysis.py, kit/backtest_history.py and kit/data/. Implement CONTRACT.md (§12) exactly.
Communicate only via agents/to_B.md and by printing RELAY blocks (§13). Read agents/to_A.md at the start of each phase.
Commit and push your folders at the end of every phase. Respect the timeboxes and cut rules. Start with P0 now.
```

### Kickoff prompt — Agent B (paste into Claude Code session 2)
```
You are Agent B ("Experience") on the RASED hackathon project. Read BUILD_PLAN.md fully, then follow §9 for Agent B only.
You own app/, core/ai.py, core/mocks.py, .streamlit/, assets/. Never edit other core/ files, config/, api/, data/.
Build against core/mocks.py (same shapes as CONTRACT.md §12) until Agent A reports DONE for a function, then switch with RASED_USE_MOCKS=0.
Use the UAE Design System colours and page layouts in §6. Communicate only via agents/to_A.md and by printing RELAY blocks (§13).
Read agents/to_B.md at the start of each phase. Commit and push your folders at the end of every phase. Start with P0 now.
```

---

## 14. Smoke test (run at 12:10, both agents)

1. `RASED_USE_MOCKS=0 streamlit run app/main.py` → Gov login works; Overview KPIs show 41,316 active licences; ≥3 alerts.
2. Outlook dial changes the chart; Actions: +1 pt renewal ≈ +370 businesses.
3. Export: select 3 metrics → JSON downloads; audit log line written.
4. Investor → Advisor returns an answer (Claude or template) with cited facts.
5. `uvicorn api.main:app` → `/docs` loads; `GET /v1/indicators/data?ids=...` with `X-API-Key` returns rows; without key → 401.
6. "Sync now" → changelog entry + banner.
7. Wifi off → app still loads from snapshot.

---

## 15. Change log / open items (update as info arrives)

- [ ] data.ajman.ae API: confirm endpoint + datasets (population/tourism?)
- [ ] fza.ae open data: confirm format
- [ ] Claude API key available? (else template mode)
- [ ] Organisers' preferred output (forecast accuracy vs tool)
- [ ] Any new dataset → add to `sources.yaml`, map columns, done.
