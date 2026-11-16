"""External context for early warnings: news, events and the wider economy.

CONTRACT: get_context(period, sector=None) -> {"news": [...], "macro": [...], "events": [...], ...}
Written by Agent B with the user's go-ahead while Agent A was offline; Agent A may take it over.

Sources, tried in order, each with a short timeout:
  news   Google News RSS search (keyless)  ->  GDELT DOC 2.0 (keyless, 1 request / 5 s)
         -> last good cached copy  ->  labelled sample headlines
  macro  World Bank API (UAE GDP growth, inflation) -> cached copy -> labelled sample values
  events config/events.yaml if Agent A adds it, otherwise the built-in calendar

Everything fetched is cached in data/cache/context/ so the demo still works offline.
Headlines are context for an analyst, never treated as causes, and never fed into models.
"""
from __future__ import annotations

import hashlib
import json
import re
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / "data" / "cache" / "context"
UA = {"User-Agent": "Mozilla/5.0 (compatible; RASED-hackathon-prototype/0.1)"}
TIMEOUT = 5
NEWS_TTL = 3 * 3600      # refetch headlines after 3 hours
MACRO_TTL = 7 * 24 * 3600

# Keep alerts about business. Political / conflict headlines are dropped (BUILD_PLAN: neutral language).
_BLOCK = re.compile(r"\b(war|attack|missile|strike[sd]?|killed|military|army|troops|drone|bomb|"
                    r"iran|israel|houthi|gaza|hamas|hezbollah|sanction|protest|election)\b", re.I)

# Sector -> search words. Keys match RASED activity / group names; unknown sectors use "business".
_SECTOR_WORDS = {
    "Retail shops": "retail OR mall OR shops",
    "Restaurants & cafes": "restaurants OR cafes OR food",
    "Construction & contracting": "construction OR contractors OR projects",
    "IT & e-commerce": "e-commerce OR ecommerce OR online OR startups",
    "Real estate": "property OR \"real estate\"",
    "General trading": "trade OR trading OR exports",
    "Logistics & transport": "logistics OR shipping OR port",
    "Manufacturing": "manufacturing OR factory OR industrial",
    "Professional services": "services OR consultancy",
    "Beauty & personal care": "salon OR beauty",
    "Free Zone": "\"free zone\"",
    "Mainland": "licences OR SMEs OR business",
    "Virtual-office firms": "SMEs OR \"small businesses\" OR \"virtual office\"",
}

_EVENTS = [
    {"name": "Ramadan", "start": "2025-03-01", "end": "2025-03-30", "kind": "season"},
    {"name": "Eid al-Fitr", "start": "2025-03-30", "end": "2025-04-02", "kind": "season"},
    {"name": "Corporate tax first filing deadline for many firms", "start": "2025-09-30", "end": "2025-09-30", "kind": "policy"},
    {"name": "Ramadan", "start": "2026-02-18", "end": "2026-03-19", "kind": "season"},
    {"name": "Eid al-Fitr", "start": "2026-03-20", "end": "2026-03-22", "kind": "season"},
    {"name": "Regional disruption begins", "start": "2026-03-01", "end": None, "kind": "shock"},
    {"name": "DED fee and fine waivers", "start": "2026-03-15", "end": "2026-06-30", "kind": "policy"},
    {"name": "Eid al-Adha", "start": "2026-05-26", "end": "2026-05-29", "kind": "season"},
    {"name": "Summer slowdown", "start": "2026-07-01", "end": "2026-08-31", "kind": "season"},
]

_SAMPLE_MACRO = [
    {"indicator": "UAE real GDP growth", "value": 4.0, "unit": "%", "period": "2025", "source": "World Bank (sample value)"},
    {"indicator": "UAE consumer price inflation", "value": 2.1, "unit": "%", "period": "2025", "source": "World Bank (sample value)"},
]


# ------------------------------------------------------------------ cache
def _cache_path(key: str) -> Path:
    return CACHE / (hashlib.sha1(key.encode("utf-8")).hexdigest()[:16] + ".json")


def _cache_get(key: str, ttl: float | None):
    p = _cache_path(key)
    try:
        d = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if ttl is not None and time.time() - d.get("t", 0) > ttl:
        return None
    return d


def _cache_put(key: str, data) -> None:
    try:
        CACHE.mkdir(parents=True, exist_ok=True)
        _cache_path(key).write_text(json.dumps({"t": time.time(), "data": data}, ensure_ascii=False), encoding="utf-8")
    except OSError:
        pass


def _get(url: str) -> bytes:
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        return r.read()


# ------------------------------------------------------------------ news
def _clean_title(title: str, source: str) -> str:
    title = (title or "").strip()
    for sep in (" - ", " | "):
        if source and title.endswith(sep + source):
            title = title[: -len(sep + source)]
    return title


def _google_news(query: str) -> list[dict]:
    url = "https://news.google.com/rss/search?" + urllib.parse.urlencode(
        {"q": query, "hl": "en-AE", "gl": "AE", "ceid": "AE:en"})
    out = []
    for it in ET.fromstring(_get(url)).findall("./channel/item"):
        src = it.findtext("source") or ""
        try:
            date = parsedate_to_datetime(it.findtext("pubDate")).astimezone(timezone.utc).strftime("%Y-%m-%d")
        except (TypeError, ValueError):
            continue
        out.append({"title": _clean_title(it.findtext("title"), src), "source": src or "Google News",
                    "date": date, "url": it.findtext("link")})
    return out


_last_gdelt = [0.0]


def _gdelt(query: str, start: str, end: str) -> list[dict]:
    wait = 5.5 - (time.time() - _last_gdelt[0])  # GDELT allows one request every 5 seconds
    if wait > 0:
        time.sleep(wait)
    _last_gdelt[0] = time.time()
    url = "https://api.gdeltproject.org/api/v2/doc/doc?" + urllib.parse.urlencode({
        "query": query.replace(" after:", " ").split(" before:")[0] + " sourcelang:english",
        "mode": "artlist", "format": "json", "maxrecords": 50, "sort": "datedesc",
        "startdatetime": start.replace("-", "") + "000000", "enddatetime": end.replace("-", "") + "235959"})
    d = json.loads(_get(url))
    return [{"title": a.get("title", ""), "source": a.get("domain", "GDELT"),
             "date": f"{a['seendate'][:4]}-{a['seendate'][4:6]}-{a['seendate'][6:8]}", "url": a.get("url")}
            for a in d.get("articles", []) if a.get("seendate")]


_BIZ = re.compile(r"\b(business|economy|economic|licen[cs]e|invest\w*|trade|trading|market|firms?|compan\w*|"
                  r"SMEs?|entrepreneur\w*|revenue|sales|profit|growth|retail|property|real estate|construction|"
                  r"free ?zone|e-?commerce|startup\w*|chamber|DED|department of economic|transactions|jobs|"
                  r"tourism|hotel|exports?|imports?|logistics|manufactur\w*|industrial)\b", re.I)


# Stricter phrases for judging relevance locally (search words above are kept broad on purpose).
_SECTOR_MATCH = {
    "Retail shops": r"retail(ers?| sales| sector| group| market| space)|shopping|malls?\b|shops?\b|stores? open|footfall",
    "Restaurants & cafes": r"restaurants?|caf[eé]s?|food (and|&) beverage|F&B|dining",
    "Construction & contracting": r"construction|contractors?|developers?|tower|projects? (launch|start|delay)",
    "IT & e-commerce": r"e-?commerce|online (shopping|sales|retail|store)|startups?|tech (firms?|companies)|digital economy|fintech",
    "Real estate": r"property|real estate|transactions|tower|homes|rents?\b",
    "General trading": r"trad(e|ing)|exports?|imports?|non-oil",
    "Logistics & transport": r"logistics|shipping|ports?\b|freight|cargo",
    "Manufacturing": r"manufactur\w*|factor(y|ies)|industrial",
    "Professional services": r"consult\w*|professional services|accounting|legal services",
    "Beauty & personal care": r"salons?|beauty|cosmetics",
    "Free Zone": r"free ?zones?",
    "Mainland": r"licen[cs]es?|SMEs?|small businesses|business set-?up|DED|Department of Economic",
    "Virtual-office firms": r"SMEs?|small businesses|virtual offices?|flexi.?desk|co-?working|renewals?",
}
_OFFTOPIC = re.compile(r"\b(study finds|bully\w*|children|crime|court|lawsuit|defamation|police|arrest\w*|"
                       r"passport|embassy|visa centres?|weather|rain|live streaming|cricket|football|match)\b", re.I)


def _sector_re(sector: str | None):
    pat = _SECTOR_MATCH.get(sector or "")
    return re.compile(r"\b(" + pat + r")", re.I) if pat else None


def _window(period: str) -> tuple[str, str]:
    p = pd.Period(period[:7], "M")
    start = (p - 3).start_time.strftime("%Y-%m-%d")
    end = min((p + 1).end_time, pd.Timestamp.now()).strftime("%Y-%m-%d")
    return start, end


def _news(period: str, sector: str | None) -> tuple[list[dict], str]:
    """Returns (headlines, source label). Empty list + label when nothing could be fetched."""
    start, end = _window(period)
    words = _SECTOR_WORDS.get(sector or "", "business OR economy")
    queries = [f"Ajman ({words}) after:{start} before:{end}",          # Ajman + sector first
               f"UAE ({words}) after:{start} before:{end}"]            # broaden to the UAE
    found: list[dict] = []
    label = ""
    for q in queries:
        key = "news:" + q
        hit = _cache_get(key, NEWS_TTL)
        items = hit["data"] if hit else None
        if items is None:
            for name, fetch in (("Google News", lambda: _google_news(q)), ("GDELT", lambda: _gdelt(q, start, end))):
                try:
                    items = fetch()
                    label = label or name
                    _cache_put(key, items)
                    break
                except Exception:  # noqa: BLE001 - network is optional, fall through
                    continue
        if items is None:  # every source failed: use a stale copy if we have one
            stale = _cache_get(key, None)
            items = stale["data"] if stale else None
            if items is not None:
                label = label or "cached copy"
        if items is None:
            continue
        label = label or "Google News (cached)"
        seen = {n["title"].lower() for n in found}
        sec_re = _sector_re(sector)
        for n in items:
            t = n["title"]
            if (not t or t.lower() in seen or not (start <= n["date"] <= end)
                    or _BLOCK.search(t) or _OFFTOPIC.search(t)):
                continue
            on_sector = bool(sec_re and sec_re.search(t))
            if not (on_sector or _BIZ.search(t)):  # drop sport, health, consular news etc.
                continue
            found.append({**n, "on_sector": on_sector})
            seen.add(t.lower())
        if sum(n["on_sector"] for n in found) >= 3:
            break
    # sector matches first, then the newest general business headlines
    found.sort(key=lambda n: (n["on_sector"], n["date"]), reverse=True)
    return found[:5], label


# ------------------------------------------------------------------ macro + events
def _macro() -> tuple[list[dict], bool]:
    key = "macro:worldbank:ARE"
    hit = _cache_get(key, MACRO_TTL)
    if hit:
        return hit["data"], True
    out = []
    try:
        for code, name in (("NY.GDP.MKTP.KD.ZG", "UAE real GDP growth"), ("FP.CPI.TOTL.ZG", "UAE consumer price inflation")):
            rows = json.loads(_get(f"https://api.worldbank.org/v2/country/ARE/indicator/{code}?format=json&per_page=8"))[1]
            latest = next(r for r in rows if r["value"] is not None)
            out.append({"indicator": name, "value": round(latest["value"], 1), "unit": "%",
                        "period": latest["date"], "source": "World Bank"})
        _cache_put(key, out)
        return out, True
    except Exception:  # noqa: BLE001
        stale = _cache_get(key, None)
        return (stale["data"], True) if stale else (_SAMPLE_MACRO, False)


def _events(start: str, end: str) -> list[dict]:
    events = _EVENTS
    cfg = ROOT / "config" / "events.yaml"
    if cfg.exists():
        try:
            import yaml
            loaded = yaml.safe_load(cfg.read_text(encoding="utf-8"))
            items = loaded.get("events", loaded) if isinstance(loaded, dict) else loaded
            if isinstance(items, list) and items:
                events = [{"name": e.get("name"), "start": str(e.get("start")),
                           "end": str(e["end"]) if e.get("end") else None, "kind": e.get("kind", "")}
                          for e in items if e.get("name") and e.get("start")]
        except Exception:  # noqa: BLE001 - fall back to the built-in calendar
            events = _EVENTS
    return [e for e in events if e["start"][:10] <= end and (e["end"] or "9999")[:10] >= start]


# ------------------------------------------------------------------ contract
def get_context(period: str, sector: str | None = None) -> dict:
    start, end = _window(period)
    news, label = _news(period, sector)
    macro, macro_live = _macro()
    return {
        "news": news,
        "news_live": bool(news),
        "news_source": label,
        "window": [start, end],
        "macro": macro,
        "macro_live": macro_live,
        "events": _events(start, end),
        "fetched": datetime.now().isoformat(timespec="minutes"),
    }


def refresh_context(period: str, sector=None, include_news=False):
    """Agent A's explicit cache refresh (World Bank + GDELT), kept in core/context_a.py."""
    from core.context_a import refresh_context as _refresh
    return _refresh(period, sector, include_news)


if __name__ == "__main__":  # quick manual check: python -m core.context
    for per, sec in (("2026-10", "Retail shops"), ("2026-09", "IT & e-commerce"), ("2026-06", "Mainland")):
        c = get_context(per, sec)
        print(per, sec, "| news:", len(c["news"]), c["news_source"], "| macro live:", c["macro_live"],
              "| events:", len(c["events"]))
        for n in c["news"][:3]:
            print("   ", n["date"], n["source"], "|", n["title"][:90])
