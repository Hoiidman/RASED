"""Optional external context; read path is offline. Refresh explicitly, with timeout/cache."""
from __future__ import annotations

import calendar
import re

import httpx

from core.settings import config, data_dir, now, read_json, write_json


def get_context(period: str, sector=None) -> dict:
    if not re.fullmatch(r"\d{4}-(0[1-9]|1[0-2])", period):
        raise ValueError("Context period must be YYYY-MM")
    cache = read_json(data_dir() / "cache/context.json", {"news": [], "macro": []})
    events = [e for e in config("events") if e["start"][:7] <= period and (not e.get("end") or e["end"][:7] >= period)]
    news = [n for n in cache["news"] if n.get("period") == period and (not sector or n.get("sector") == sector)]
    macro = [m for m in cache["macro"] if m["period"] <= period[:4]]
    return {"news": news, "macro": macro, "events": events}


def refresh_context(period: str, sector=None, include_news=False):
    get_context(period, sector)  # validate before any request
    path = data_dir() / "cache/context.json"
    cached = read_json(path, {"news": [], "macro": []})
    errors = []
    headers = {"User-Agent": "RASED/1.0 (optional economic context)"}
    for code, label in [("NY.GDP.MKTP.KD.ZG", "UAE GDP growth"), ("FP.CPI.TOTL.ZG", "UAE inflation")]:
        try:
            r = httpx.get(f"https://api.worldbank.org/v2/country/ARE/indicator/{code}",
                          params={"format": "json", "per_page": 10}, timeout=5, headers=headers)
            r.raise_for_status()
            points = r.json()[1] or []
            items = [{"indicator": label, "value": p["value"], "unit": "%", "period": p["date"],
                      "source": str(r.url), "retrieved_at": now()} for p in points if p.get("value") is not None]
            cached["macro"] = [p for p in cached["macro"] if p["indicator"] != label] + items
        except (httpx.HTTPError, ValueError, KeyError, TypeError, IndexError) as exc:
            errors.append(type(exc).__name__)
    if include_news:
        try:
            year, month = map(int, period.split("-"))
            keyword = re.sub(r"[^\w\s]", " ", sector or "")[:80]
            r = httpx.get("https://api.gdeltproject.org/api/v2/doc/doc", headers=headers, timeout=5,
                          params={"query": '(Ajman OR "UAE economy") ' + keyword, "mode": "artlist", "format": "json",
                                  "maxrecords": 5, "startdatetime": f"{year:04}{month:02}01000000",
                                  "enddatetime": f"{year:04}{month:02}{calendar.monthrange(year, month)[1]}235959"})
            r.raise_for_status()
            items = [{"title": a["title"], "source": a["url"], "date": a["seendate"], "period": period,
                      "sector": sector, "retrieved_at": now(), "note": "Context only; analyst to confirm"}
                     for a in r.json().get("articles", [])]
            cached["news"] = [n for n in cached["news"] if (n.get("period"), n.get("sector")) != (period, sector)] + items
        except (httpx.HTTPError, ValueError, KeyError, TypeError) as exc:
            errors.append(type(exc).__name__)
    write_json(path, cached)
    return {"errors": errors, **get_context(period, sector)}
