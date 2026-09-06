"""Free multi-source OHLCV acquisition layer — stdlib only.

Sources (all free, no API keys):
  1. Yahoo Finance chart API — query1 host
  2. Yahoo Finance chart API — query2 host (independent edge)
  3. Nasdaq.com chart API (US-listed equities)
  4. Stooq daily CSV (US + international coverage)

Every source runs in parallel with per-source timeout and retry. Results are
raw (date, close, volume) series; aggregation/voting happens in free_aggregate.

A small disk cache (TTL minutes) absorbs upstream rate-limit bursts — the
quantradar facade may invoke this subprocess on every live analyze.
"""

from __future__ import annotations

import gzip
import io
import json
import os
import ssl
import threading
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

# Stooq is opt-out: it now serves a JS-challenge page to non-browser agents,
# so it cannot be a reliable free source. fetch_stooq stays for a future
# proxy; it is not in the default rotation.
SOURCE_NAMES = ("yahoo_q1", "yahoo_q2", "nasdaq")

_UA_YAHOO = (
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) QuantRadar/1.0"
)
_UA_NASDAQ = (
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
    "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15"
)
_UA_PLAIN = "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) QuantRadar/1.0"

_SSL_CTX = ssl.create_default_context()
_LOCK = threading.Lock()


class SourceError(RuntimeError):
    """One source failed; message carries the reason."""


def _http_get(url: str, headers: dict[str, str], timeout: float = 8.0) -> bytes:
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=_SSL_CTX) as resp:
            raw = resp.read()
    except urllib.error.HTTPError as exc:
        raise SourceError(f"http {exc.code}") from exc
    except Exception as exc:  # timeout / DNS / reset / ssl
        raise SourceError(f"net {type(exc).__name__}") from exc
    if raw[:2] == b"\x1f\x8b":
        try:
            raw = gzip.GzipFile(fileobj=io.BytesIO(raw)).read()
        except OSError:
            pass
    return raw


def _to_float(val: Any) -> float | None:
    if val is None:
        return None
    if isinstance(val, bool):
        return None
    if isinstance(val, (int, float)):
        return float(val)
    if isinstance(val, str):
        cleaned = val.replace(",", "").replace("$", "").strip()
        if not cleaned or cleaned in {"null", "N/A", "None"}:
            return None
        try:
            return float(cleaned)
        except ValueError:
            return None
    return None


def yahoo_range(days: int) -> str:
    if days <= 30:
        return "1mo"
    if days <= 100:
        return "3mo"
    if days <= 200:
        return "6mo"
    return "1y"


# ---------------------------------------------------------------------------
# Yahoo chart API
# ---------------------------------------------------------------------------


def _parse_yahoo(raw: bytes, source: str) -> list[tuple[str, float, float]]:
    try:
        root = json.loads(raw.decode("utf-8", errors="replace"))
    except json.JSONDecodeError as exc:
        raise SourceError(f"{source}: bad json") from exc
    chart = root.get("chart") if isinstance(root, dict) else None
    if not isinstance(chart, dict):
        raise SourceError(f"{source}: no chart node")
    if chart.get("error"):
        err = chart["error"]
        desc = err.get("description") if isinstance(err, dict) else str(err)
        raise SourceError(f"{source}: api error {str(desc)[:120]}")
    results = chart.get("result")
    if not isinstance(results, list) or not results:
        raise SourceError(f"{source}: empty result")
    result = results[0]
    timestamps = result.get("timestamp")
    indicators = result.get("indicators") or {}
    quotes = indicators.get("quote") if isinstance(indicators, dict) else None
    if not isinstance(timestamps, list) or not isinstance(quotes, list) or not quotes:
        raise SourceError(f"{source}: malformed payload")
    quote = quotes[0]
    closes = quote.get("close") if isinstance(quote, dict) else None
    volumes = quote.get("volume") if isinstance(quote, dict) else None
    if not isinstance(closes, list) or not isinstance(volumes, list):
        raise SourceError(f"{source}: missing close/volume")
    bars: list[tuple[str, float, float]] = []
    for i, ts in enumerate(timestamps):
        c = _to_float(closes[i]) if i < len(closes) else None
        v = _to_float(volumes[i]) if i < len(volumes) else 0.0
        if c is None or c <= 0:
            continue
        day = datetime.fromtimestamp(float(ts), tz=timezone.utc).strftime("%Y-%m-%d")
        bars.append((day, c, max(0.0, v or 0.0)))
    return bars


def fetch_yahoo(symbol: str, host: str, days: int = 200) -> list[tuple[str, float, float]]:
    source = "yahoo_q1" if "query1" in host else "yahoo_q2"
    encoded = urllib.parse.quote(symbol, safe="")
    url = (
        f"https://{host}/v8/finance/chart/{encoded}"
        f"?range={yahoo_range(days)}&interval=1d&includePrePost=false"
    )
    headers = {"User-Agent": _UA_YAHOO, "Accept": "application/json"}
    data = _http_get(url, headers)
    return _parse_yahoo(data, source)


# ---------------------------------------------------------------------------
# Nasdaq.com chart API
# ---------------------------------------------------------------------------


def _parse_nasdaq(raw: bytes) -> list[tuple[str, float, float]]:
    try:
        root = json.loads(raw.decode("utf-8", errors="replace"))
    except json.JSONDecodeError as exc:
        raise SourceError("nasdaq: bad json") from exc
    data = root.get("data") if isinstance(root, dict) else None
    chart = data.get("chart") if isinstance(data, dict) else None
    if not isinstance(chart, list):
        raise SourceError("nasdaq: no chart array")
    bars: list[tuple[str, float, float]] = []
    for point in chart:
        if not isinstance(point, dict):
            continue
        y = _to_float(point.get("y"))
        x = _to_float(point.get("x"))
        if y is None or y <= 0 or x is None:
            continue
        z = point.get("z")
        volume = _to_float(z.get("volume")) if isinstance(z, dict) else None
        day = datetime.fromtimestamp(x / 1000.0, tz=timezone.utc).strftime("%Y-%m-%d")
        bars.append((day, y, max(0.0, volume or 0.0)))
    bars.sort(key=lambda b: b[0])
    return bars


def fetch_nasdaq(symbol: str, days: int = 200) -> list[tuple[str, float, float]]:
    # Nasdaq chart API uses dot class shares; skip symbols it cannot serve.
    if "=" in symbol or "." in symbol:
        raise SourceError("nasdaq: unsupported symbol form")
    nasdaq_symbol = symbol.replace("-", ".")
    end = datetime.now(tz=timezone.utc)
    start = end - timedelta(days=max(60, days))
    fmt = "%Y-%m-%d"
    url = (
        "https://api.nasdaq.com/api/quote/"
        f"{urllib.parse.quote(nasdaq_symbol, safe='')}/chart"
        f"?assetclass=stocks&fromdate={start.strftime(fmt)}&todate={end.strftime(fmt)}"
    )
    headers = {
        "User-Agent": _UA_NASDAQ,
        "Accept": "application/json, text/plain, */*",
        "Origin": "https://www.nasdaq.com",
        "Referer": "https://www.nasdaq.com/",
    }
    data = _http_get(url, headers)
    return _parse_nasdaq(data)


# ---------------------------------------------------------------------------
# Stooq daily CSV (US symbols need .US suffix)
# ---------------------------------------------------------------------------


def fetch_stooq(symbol: str, days: int = 200) -> list[tuple[str, float, float]]:
    if symbol.startswith("^") or "." in symbol or "=" in symbol:
        raise SourceError("stooq: unsupported symbol form")
    stooq_symbol = symbol.lower().replace("-", ".")
    if stooq_symbol not in {"spy", "qqq", "dia", "iwm"}:
        stooq_symbol = f"{stooq_symbol}.us"
    end = datetime.now(tz=timezone.utc)
    start = end - timedelta(days=max(60, days))
    url = (
        "https://stooq.com/q/d/l/"
        f"?s={urllib.parse.quote(stooq_symbol, safe='')}"
        f"&d1={start.strftime('%Y%m%d')}&d2={end.strftime('%Y%m%d')}&i=d"
    )
    data = _http_get(url, {"User-Agent": _UA_PLAIN, "Accept": "text/csv"})
    text = data.decode("utf-8", errors="replace")
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    if len(lines) < 2 or not lines[0].lower().startswith("date"):
        raise SourceError("stooq: no csv data")
    header = [h.strip().lower() for h in lines[0].split(",")]
    try:
        di, ci, vi = header.index("date"), header.index("close"), header.index("volume")
    except ValueError as exc:
        raise SourceError("stooq: unexpected header") from exc
    bars: list[tuple[str, float, float]] = []
    for line in lines[1:]:
        parts = line.split(",")
        if len(parts) <= max(di, ci, vi):
            continue
        c = _to_float(parts[ci])
        v = _to_float(parts[vi])
        if c is None or c <= 0:
            continue
        bars.append((parts[di], c, max(0.0, v or 0.0)))
    bars.sort(key=lambda b: b[0])
    return bars


# ---------------------------------------------------------------------------
# Fundamentals (fail-open): company name, sector, earnings date
# ---------------------------------------------------------------------------


def _parse_yahoo_fundamentals(raw: bytes) -> dict[str, Any]:
    root = json.loads(raw.decode("utf-8", errors="replace"))
    qs = root.get("quoteSummary") if isinstance(root, dict) else None
    results = qs.get("result") if isinstance(qs, dict) else None
    if not isinstance(results, list) or not results:
        return {}
    result = results[0]
    out: dict[str, Any] = {}
    profile = result.get("assetProfile")
    if isinstance(profile, dict):
        sector = profile.get("sector")
        name = profile.get("longBusinessSummary") and None  # never fabricate
        if isinstance(sector, str) and sector.strip():
            out["sector"] = sector.strip()
        _ = name
    cal = result.get("calendarEvents")
    if isinstance(cal, dict):
        earn = cal.get("earnings")
        if isinstance(earn, dict):
            ed = earn.get("earningsDate")
            if isinstance(ed, list) and ed:
                first = ed[0]
                raw_ts = first.get("raw") if isinstance(first, dict) else None
                if isinstance(raw_ts, (int, float)) and raw_ts > 0:
                    out["earnings_date"] = datetime.fromtimestamp(
                        float(raw_ts), tz=timezone.utc
                    ).strftime("%Y-%m-%d")
    return out


def fetch_yahoo_fundamentals(symbol: str) -> dict[str, Any]:
    encoded = urllib.parse.quote(symbol, safe="")
    url = (
        "https://query1.finance.yahoo.com/v10/finance/quoteSummary/"
        f"{encoded}?modules=assetProfile,calendarEvents"
    )
    try:
        data = _http_get(url, {"User-Agent": _UA_YAHOO, "Accept": "application/json"}, timeout=6.0)
        return _parse_yahoo_fundamentals(data)
    except Exception:
        return {}


def fetch_yahoo_chart_meta(symbol: str) -> dict[str, Any]:
    """Cheap free metadata from the chart endpoint (name, exchange)."""
    encoded = urllib.parse.quote(symbol, safe="")
    url = (
        f"https://query1.finance.yahoo.com/v8/finance/chart/{encoded}"
        "?range=5d&interval=1d"
    )
    try:
        data = _http_get(url, {"User-Agent": _UA_YAHOO, "Accept": "application/json"}, timeout=6.0)
        root = json.loads(data.decode("utf-8", errors="replace"))
        results = ((root.get("chart") or {}).get("result")) or []
        meta = results[0].get("meta") if results else None
        if not isinstance(meta, dict):
            return {}
        out: dict[str, Any] = {}
        name = meta.get("longName") or meta.get("shortName")
        if isinstance(name, str) and name.strip():
            out["company_name"] = name.strip()
        return out
    except Exception:
        return {}


def fetch_nasdaq_info(symbol: str) -> dict[str, Any]:
    """Nasdaq info endpoint — companyName (free)."""
    if "=" in symbol or "." in symbol:
        return {}
    nasdaq_symbol = symbol.replace("-", ".")
    url = (
        "https://api.nasdaq.com/api/quote/"
        f"{urllib.parse.quote(nasdaq_symbol, safe='')}/info?assetclass=stocks"
    )
    headers = {
        "User-Agent": _UA_NASDAQ,
        "Accept": "application/json, text/plain, */*",
        "Origin": "https://www.nasdaq.com",
        "Referer": "https://www.nasdaq.com/",
    }
    try:
        data = _http_get(url, headers, timeout=6.0)
        root = json.loads(data.decode("utf-8", errors="replace"))
        d = root.get("data") if isinstance(root, dict) else None
        out: dict[str, Any] = {}
        name = d.get("companyName") if isinstance(d, dict) else None
        if isinstance(name, str) and name.strip():
            out["company_name"] = name.strip()
        return out
    except Exception:
        return {}


def fetch_nasdaq_summary(symbol: str) -> dict[str, Any]:
    if "=" in symbol:
        return {}
    nasdaq_symbol = symbol.replace("-", ".")
    for asset in ("stocks", "etf"):
        url = (
            "https://api.nasdaq.com/api/quote/"
            f"{urllib.parse.quote(nasdaq_symbol, safe='')}/summary?assetclass={asset}"
        )
        headers = {
            "User-Agent": _UA_NASDAQ,
            "Accept": "application/json, text/plain, */*",
            "Origin": "https://www.nasdaq.com",
            "Referer": "https://www.nasdaq.com/",
        }
        try:
            data = _http_get(url, headers, timeout=6.0)
            root = json.loads(data.decode("utf-8", errors="replace"))
            d = root.get("data") if isinstance(root, dict) else None
            summary = d.get("summaryData") if isinstance(d, dict) else None
            if not isinstance(summary, dict):
                continue
            out: dict[str, Any] = {}
            sector = summary.get("Sector")
            if isinstance(sector, dict):
                v = sector.get("value")
                if isinstance(v, str) and v.strip():
                    out["sector"] = v.strip()
            company = summary.get("Company Name")
            if isinstance(company, dict):
                v = company.get("value")
                if isinstance(v, str) and v.strip():
                    out["company_name"] = v.strip()
            if out:
                return out
        except Exception:
            continue
    return {}


# ---------------------------------------------------------------------------
# Orchestration: parallel fetch + disk cache
# ---------------------------------------------------------------------------

_CACHE_LOCK = threading.Lock()
_CACHE_TTL_SEC = 600  # 10 min — absorbs rate-limit bursts on repeated scans


def _cache_path(cache_dir: Path, key: str) -> Path:
    safe = "".join(ch if ch.isalnum() else "_" for ch in key)
    return cache_dir / f"{safe}.json"


def _cache_read(cache_dir: Path | None, key: str, *, not_before: float = 0) -> Any | None:
    if cache_dir is None:
        return None
    p = _cache_path(cache_dir, key)
    try:
        obj = json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None
    if (not isinstance(obj, dict) or time.time() - float(obj.get("t", 0)) > _CACHE_TTL_SEC
            or float(obj.get("t", 0)) < not_before):
        return None
    return obj.get("v")


def _cache_write(cache_dir: Path | None, key: str, value: Any, *, fetched_at: float | None = None) -> None:
    if cache_dir is None:
        return
    try:
        cache_dir.mkdir(parents=True, exist_ok=True)
        with _CACHE_LOCK:
            with tempfile.NamedTemporaryFile(mode="w", dir=cache_dir, prefix=".cache-", suffix=".tmp", delete=False) as temporary:
                temp_path = Path(temporary.name)
                try:
                    json.dump({"t": time.time() if fetched_at is None else fetched_at, "v": value}, temporary, allow_nan=False)
                    temporary.flush()
                    os.replace(temp_path, _cache_path(cache_dir, key))
                finally:
                    temp_path.unlink(missing_ok=True)
        _cache_prune(cache_dir)
    except OSError:
        pass


def _cache_prune(cache_dir: Path) -> None:
    try:
        files = sorted(cache_dir.glob("*.json"), key=lambda p: p.stat().st_mtime)
        for stale in files[:-800]:
            stale.unlink(missing_ok=True)
    except OSError:
        pass


def _fetch_source(name: str, symbol: str, days: int) -> list[tuple[str, float, float]]:
    last_err = "unknown"
    for attempt in range(2):
        try:
            if name == "yahoo_q1":
                return fetch_yahoo(symbol, "query1.finance.yahoo.com", days)
            if name == "yahoo_q2":
                return fetch_yahoo(symbol, "query2.finance.yahoo.com", days)
            if name == "nasdaq":
                return fetch_nasdaq(symbol, days)
            if name == "stooq":
                return fetch_stooq(symbol, days)
            raise SourceError(f"unknown source {name}")
        except SourceError as exc:
            last_err = str(exc)
            if "http 429" in last_err or "http 403" in last_err or "net " in last_err:
                time.sleep(0.9 * (attempt + 1))
                continue
            raise
    raise SourceError(last_err)


def fetch_all_sources(
    symbol: str,
    days: int = 200,
    cache_dir: Path | None = None,
    as_of: datetime | None = None,
) -> tuple[dict[str, list[tuple[str, float, float]]], dict[str, str]]:
    """Fetch every source in parallel.

    Returns (bars_by_source, errors_by_source). Sources that produced fewer
    than 10 rows are treated as failed (too thin to be useful).
    """
    bars: dict[str, list[tuple[str, float, float]]] = {}
    errors: dict[str, str] = {}
    from market_calendar import completed_bars, completed_session, session_close
    as_of = as_of or datetime.now(timezone.utc)
    cutoff = completed_session(as_of)
    if cutoff is None:
        return {}, {name: "calendar coverage unavailable" for name in SOURCE_NAMES}
    not_before = session_close(cutoff).timestamp()

    def worker(name: str) -> tuple[str, list[tuple[str, float, float]] | None, str]:
        cached = _cache_read(cache_dir, f"{name}:{symbol}", not_before=not_before)
        if cached is not None:
            rows = [(str(r[0]), float(r[1]), float(r[2])) for r in cached]
            try:
                completed_bars(rows, now=as_of, minimum=min(139, max(5, days // 2)))
                return name, rows, ""
            except ValueError:
                pass
        try:
            started = time.time()
            rows = _fetch_source(name, symbol, days)
            if len(rows) < 10:
                return name, None, f"{name}: too few bars ({len(rows)})"
            _cache_write(cache_dir, f"{name}:{symbol}", rows, fetched_at=started)
            return name, rows, ""
        except SourceError as exc:
            return name, None, str(exc)
        except Exception as exc:  # never let one source sink the batch
            return name, None, f"{name}: {type(exc).__name__}"

    with ThreadPoolExecutor(max_workers=len(SOURCE_NAMES)) as pool:
        futures = [pool.submit(worker, n) for n in SOURCE_NAMES]
        for fut in as_completed(futures):
            name, rows, err = fut.result()
            if rows is not None:
                bars[name] = rows
            else:
                errors[name] = err
    return bars, errors


def fetch_fundamentals(symbol: str, cache_dir: Path | None = None) -> dict[str, Any]:
    """Company name / sector / earnings date. Fail-open: {} is acceptable."""
    cached = _cache_read(cache_dir, f"fund:{symbol}")
    if cached is not None:
        return cached if isinstance(cached, dict) else {}
    out: dict[str, Any] = fetch_yahoo_fundamentals(symbol)
    # Sector/name from Nasdaq summary (free) when Yahoo quoteSummary is dead
    nasdaq_sum = fetch_nasdaq_summary(symbol)
    for key, val in nasdaq_sum.items():
        out.setdefault(key, val)
    # Company name fallbacks: Yahoo chart meta → Nasdaq info
    if not out.get("company_name"):
        meta = fetch_yahoo_chart_meta(symbol)
        if meta.get("company_name"):
            out["company_name"] = meta["company_name"]
    if not out.get("company_name"):
        info = fetch_nasdaq_info(symbol)
        if info.get("company_name"):
            out["company_name"] = info["company_name"]
    _cache_write(cache_dir, f"fund:{symbol}", out)
    return out
