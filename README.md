# RASED (راصد)

*Sees the change before it happens · يرصد التغيير قبل حدوثه*

Ajman economic early-warning and decision dashboard: a **Government portal** (early warnings, outlook, policy simulator, export/API) and an **Investor portal** (opportunities, watch-outs, AI business advisor). Ajman Business Hackathon 2026.

- Product overview for slides and context: [RASED_OVERVIEW.md](RASED_OVERVIEW.md)
- Build plan, contract and agent protocol: [BUILD_PLAN.md](BUILD_PLAN.md)

## Run it

```bash
python -m pip install -r requirements.txt
python -m streamlit run app/main.py
```

Open http://localhost:8501. The app runs on deterministic mock data by default.

To use the real engine (Agent A), set `RASED_USE_MOCKS=0`. Each function falls back to the mock automatically if the real one is missing or fails, so the demo never breaks.

```bash
RASED_USE_MOCKS=0 python -m streamlit run app/main.py
```

API (Agent A): `uvicorn api.main:app`. Docs are at http://localhost:8000/docs.

## Secrets: `.env` in the project root (never committed)

```
ANTHROPIC_API_KEY=sk-ant-...   # optional: Claude advisor; without it, template text is used
GOV_PASSWORD=...               # optional: without it, the Government portal opens with one click (demo mode)
```

Claude also needs `python -m pip install anthropic`. If the key is missing or the internet is down, the AI falls back to templates built from the same facts.

## Layout

| Path | Owner | What |
|---|---|---|
| `app/main.py` | B | Streamlit shell: portal switch, login, data-health strip, sync banner |
| `app/views_gov.py`, `app/views_inv.py` | B | Government (8 pages) and Investor (3 pages) views |
| `app/charts.py` | B | All Plotly charts (UAE Design System palette) |
| `app/backend.py` | B | Data gateway: real engine per function, mock fallback |
| `core/mocks.py` | B | Mock implementations of the CONTRACT (reference shapes) |
| `core/ai.py` | B | Grounded Claude advisor + template fallback |
| `core/*.py` (others), `config/`, `api/`, `data/` | A | Data store, models, alerts, drivers, sync, API |

Licence data is a **signal** of economic activity, not GDP or FDI.
