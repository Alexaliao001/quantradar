"""Engagement layer: scan ledger, avoidance moments, watchlist, daily digest.

Everything here is real-data only. Avoidance moments compare the close at scan
time with a later close from the free engine — never invented. When no SMTP
keys are configured the digest is archived to disk and the UI says so honestly
(same stance as the waitlist archive).
"""

from __future__ import annotations

import json
import os
import threading
import time
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parent.parent
DATA_DIR = REPO / "data"
LEDGER_PATH = DATA_DIR / "ledger.json"
PRICE_CACHE_PATH = DATA_DIR / "price_cache.json"
DIGEST_DIR = DATA_DIR / "digest"

_LOCK = threading.Lock()
_LEDGER_CAP = 2000
_PRICE_TTL_SEC = 6 * 3600
AVOID_DROP_PCT = 5.0
WATCH_LIMITS = {"free": 1, "pro": 10, "portfolio_pro": 50}


def _load_json(path: Path, default: Any) -> Any:
    try:
        if path.is_file():
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        pass
    return default


def _save_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, ensure_ascii=False, indent=1), encoding="utf-8")
    tmp.replace(path)


# ---------------------------------------------------------------- scan ledger

def record_scan(ticker: str, result: dict[str, Any], email: str | None) -> None:
    """Save the authenticated scan's own completed-session close, without another fetch."""
    import math
    from free_engine.market_calendar import completed_session

    meta = result.get("meta") or {}
    close = meta.get("market_close")
    if (not email or not result.get("ok") or meta.get("mode") != "live"
            or meta.get("market_as_of") != completed_session()
            or not isinstance(close, (int, float)) or not math.isfinite(close) or close <= 0):
        return
    entry = {"ticker": ticker.upper(), "ts": time.time(), "as_of": meta["market_as_of"],
             "action": str((result.get("primary") or {}).get("action") or ""),
             "score": (result.get("score") or {}).get("final"), "email": email, "close": close}
    with _LOCK:
        store = _load_json(LEDGER_PATH, {"version": 2, "entries": []})
        entries = store.get("entries") or []
        entries.append(entry)
        store["entries"] = entries[-_LEDGER_CAP:]
        _save_json(LEDGER_PATH, store)
        cache = _load_json(PRICE_CACHE_PATH, {})
        cache[ticker.upper()] = {"close": close, "ts": entry["ts"], "as_of": entry["as_of"]}
        _save_json(PRICE_CACHE_PATH, cache)


def _engine_dir() -> Path:
    charts_dir = Path(os.environ.get("CHARTS_DIR", "")).expanduser()
    return charts_dir if (charts_dir / "free_sources.py").is_file() else REPO / "free_engine"


def avoidance_events(email: str | None, limit: int = 5) -> list[dict[str, Any]]:
    """Real avoidance moments: scans we called NO/PUT whose cached close later fell >=5%.

    Cache-only by design: the response path never makes network calls. Fresh
    closes are refreshed by record_scan (background) and the daily digest.
    """
    from free_engine.market_calendar import completed_session
    if not email:
        return []
    cutoff = completed_session()
    store = _load_json(LEDGER_PATH, {"entries": []})
    cache = _load_json(PRICE_CACHE_PATH, {})
    now = time.time()
    out: list[dict[str, Any]] = []
    for e in reversed(store.get("entries") or []):
        if (e.get("email") or None) != email:
            continue
        if str(e.get("action") or "").upper() not in {"NO", "PUT"}:
            continue
        then = float(e.get("close") or 0)
        if then <= 0:
            continue
        hit = cache.get(str(e.get("ticker")))
        if not isinstance(hit, dict) or now - float(hit.get("ts") or 0) > _PRICE_TTL_SEC:
            continue
        if hit.get("as_of") != cutoff or not e.get("as_of") or hit["as_of"] <= e["as_of"]:
            continue
        try:
            cur = float(hit.get("close"))
        except Exception:
            continue
        drop = (then - cur) / then * 100.0
        if drop >= AVOID_DROP_PCT:
            out.append(
                {
                    "ticker": e.get("ticker"),
                    "then_ts": e.get("ts"),
                    "then_as_of": e["as_of"],
                    "now_as_of": hit["as_of"],
                    "then_close": then,
                    "now_close": cur,
                    "drop_pct": round(drop, 1),
                    "action_then": e.get("action"),
                }
            )
        if len(out) >= limit:
            break
    return out


# ------------------------------------------------------------------ watchlist

def public_engagement(user: dict[str, Any]) -> dict[str, Any]:
    """Fields for /api/auth/status so the UI can render the desk honestly."""
    email = str(user.get("email") or "")
    if not email:
        return {}
    from app.users import get_user

    u = get_user(email)
    if not u:
        return {}
    return {
        "watchlist": [str(t).upper() for t in (u.get("watchlist") or [])],
        "watchlist_limit": watch_limit(email),
        "daily_digest": bool(u.get("daily_digest")),
        "report_granted": bool(u.get("report_granted")),
        "bump_csv_priority": bool(u.get("bump_csv_priority")),
    }


def get_watchlist(email: str) -> list[str]:
    from app import users

    u = users.get_user(email)
    if not u:
        return []
    wl = u.get("watchlist")
    return [str(t).upper() for t in wl] if isinstance(wl, list) else []


def watch_limit(email: str) -> int:
    from app import users

    plan = users.resolve_plan(email)
    return WATCH_LIMITS.get(plan, WATCH_LIMITS["free"])


def add_watch(email: str, ticker: str) -> tuple[bool, str, list[str]]:
    from app import users

    t = (ticker or "").strip().upper()
    if not t or not t.replace("-", "").replace(".", "").isalnum():
        return False, "invalid ticker", []
    limit = watch_limit(email)
    with users._LOCK:  # noqa: SLF001 - same-store transactional update
        store = users._load()  # noqa: SLF001
        u = store["users"].get(users.normalize_email(email))
        if not isinstance(u, dict):
            return False, "no account", []
        wl = [str(x).upper() for x in (u.get("watchlist") or [])]
        if t in wl:
            return True, "already watching", wl
        if len(wl) >= limit:
            return False, "limit", wl
        wl.append(t)
        u["watchlist"] = wl
        store["users"][users.normalize_email(email)] = u
        users._save(store)  # noqa: SLF001
    return True, "added", wl


def remove_watch(email: str, ticker: str) -> list[str]:
    from app import users

    t = (ticker or "").strip().upper()
    with users._LOCK:  # noqa: SLF001
        store = users._load()  # noqa: SLF001
        u = store["users"].get(users.normalize_email(email))
        if not isinstance(u, dict):
            return []
        wl = [str(x).upper() for x in (u.get("watchlist") or []) if str(x).upper() != t]
        u["watchlist"] = wl
        store["users"][users.normalize_email(email)] = u
        users._save(store)  # noqa: SLF001
    return wl


# ---------------------------------------------------------------- daily digest

def digest_optins() -> list[dict[str, Any]]:
    from app import users

    out = []
    with users._LOCK:  # noqa: SLF001
        store = users._load()  # noqa: SLF001
        for email, u in (store.get("users") or {}).items():
            if isinstance(u, dict) and u.get("daily_digest"):
                out.append({"email": email, "watchlist": u.get("watchlist") or []})
    return out


def set_digest_optin(email: str, on: bool) -> None:
    from app import users

    with users._LOCK:  # noqa: SLF001
        store = users._load()  # noqa: SLF001
        u = store["users"].get(users.normalize_email(email))
        if isinstance(u, dict):
            u["daily_digest"] = bool(on)
            store["users"][users.normalize_email(email)] = u
            users._save(store)  # noqa: SLF001


def build_digest(email: str | None = None) -> dict[str, Any]:
    """Build one account's digest, or archive the opt-in batch for a worker."""
    import sys
    from app.users import normalize_email

    charts_dir = Path(os.environ.get("CHARTS_DIR", "")).expanduser()
    engine_dir = charts_dir if (charts_dir / "fetch_all.py").is_file() else REPO / "free_engine"
    if str(engine_dir) not in sys.path:
        sys.path.insert(0, str(engine_dir))
    import free_sources as fs  # type: ignore

    from free_aggregate import aggregate_bars
    from market_calendar import completed_bars, completed_session
    from datetime import datetime, timezone
    batch_now = datetime.now(timezone.utc)
    from free_mechanical import core

    def bars_for(symbol: str) -> list:
        try:
            sources, _ = fs.fetch_all_sources(symbol, days=365, cache_dir=engine_dir / ".cache", as_of=batch_now)
            agg = aggregate_bars(sources)
            bars = completed_bars(agg["bars"], now=batch_now)
            if set(agg["disagree_days"]) & {row[0] for row in bars[-50:]}:
                return []
            return bars
        except Exception:
            return []

    spy_bars = bars_for("SPY")
    market_core = core(spy_bars, spy_bars or None)
    spy_pct = market_core["spy_pct"]
    market_open = None if market_core["market_gate"] == "UNKNOWN" else market_core["market_gate"] == "PASS"

    users_rows = []
    recipients = (
        [{"email": normalize_email(email), "watchlist": get_watchlist(email)}]
        if email is not None else digest_optins()
    )
    for row in recipients:
        items = []
        for t in row["watchlist"]:
            bars = bars_for(t)
            closes = [row[1] for row in bars]
            if not closes:
                items.append({"ticker": t, "state": "no data"})
                continue
            sma20 = sum(closes[-20:]) / min(20, len(closes))
            last = closes[-1]
            items.append(
                {
                    "ticker": t,
                    "close": last,
                    "above_sma20": last >= sma20,
                    "as_of": bars[-1][0],
                    "action": core(bars, spy_bars or None)["action"],
                }
            )
        users_rows.append({"email": row["email"], "items": items})

    digest = {
        "date": completed_session(batch_now),
        "market": {"spy_pct_5d": spy_pct, "gate_open": market_open},
        "users": users_rows,
        "sent": False,  # SMTP not configured yet — archived honestly
    }
    if email is None:
        DIGEST_DIR.mkdir(parents=True, exist_ok=True)
        with _LOCK:
            _save_json(DIGEST_DIR / f"{digest['date']}.json", digest)
    return digest


def smtp_configured() -> bool:
    return bool(os.environ.get("SMTP_HOST", "").strip() and os.environ.get("SMTP_USER", "").strip())


# ------------------------------------------------------------------ /today

def recent_closes(ticker: str, n: int = 5) -> list[float]:
    """Last n closes for the replay teaser, read from the warm engine cache.

    Zero network: if the cache is cold we return [] and the UI hides the block.
    """
    engine_dir = _engine_dir()
    cache_dir = engine_dir / ".cache"
    t = (ticker or "").upper()
    for src in ("yahoo_q1", "yahoo_q2", "nasdaq"):
        safe = "".join(ch if ch.isalnum() else "_" for ch in f"{src}:{t}")
        p = cache_dir / f"{safe}.json"
        try:
            obj = json.loads(p.read_text(encoding="utf-8"))
            rows = obj.get("v") if isinstance(obj, dict) else None
            if isinstance(rows, list) and len(rows) >= n:
                return [float(r[1]) for r in rows[-n:]]
        except Exception:
            continue
    return []


TODAY_CACHE_PATH = DATA_DIR / "today_cache.json"
TODAY_TTL_SEC = 3600
TODAY_UNIVERSE = (
    "SPY QQQ AAPL MSFT NVDA AMD INTC TSLA META AMZN GOOGL AVGO NFLX "
    "JPM BAC XLF V VISA MA KO PEP XLP JNJ LLY UNH XLV XOM CVX XLE "
    "CAT BA XLI PLTR SMCI HOOD SOFI BABA JD NIO MU"
).split()

_today_lock = threading.Lock()
_today_building = False


def _compute_today() -> dict[str, Any]:
    """Full synchronous compute — parallel fetches, warm engine cache."""
    import sys
    from concurrent.futures import ThreadPoolExecutor

    engine_dir = _engine_dir()
    if str(engine_dir) not in sys.path:
        sys.path.insert(0, str(engine_dir))
    import free_mechanical as fm  # type: ignore
    import free_sources as fs  # type: ignore

    cache_dir = engine_dir / ".cache"

    from free_aggregate import aggregate_bars
    from market_calendar import completed_bars, completed_session
    from datetime import datetime, timezone
    batch_now = datetime.now(timezone.utc)

    def bars_for(symbol: str) -> list:
        try:
            sources, _ = fs.fetch_all_sources(symbol, days=365, cache_dir=cache_dir, as_of=batch_now)
            agg = aggregate_bars(sources)
            bars = completed_bars(agg["bars"], now=batch_now)
            if set(agg["disagree_days"]) & {row[0] for row in bars[-50:]}:
                return []
            return bars
        except Exception:
            return []

    spy_bars = bars_for("SPY")
    market_core = fm.core(spy_bars, spy_bars or None)
    spy_pct = market_core["spy_pct"]
    market_gate = market_core["market_gate"]
    gate_state = {"PASS": "open", "WATCH": "watch", "NO": "closed"}.get(market_gate, "unknown")

    universe = [t for t in TODAY_UNIVERSE if t != "SPY"]
    results: dict[str, list] = {}
    # Low concurrency: Yahoo/Nasdaq free endpoints rate-limit bursts (403).
    with ThreadPoolExecutor(max_workers=3) as pool:
        futures = {pool.submit(bars_for, t): t for t in universe}
        for fut, t in futures.items():
            try:
                results[t] = fut.result(timeout=90)
            except Exception:
                results[t] = []

    rows = []
    for t in universe:
        bars = results.get(t) or []
        if len(bars) < 50:
            continue
        c = fm.core(bars, spy_bars or None)
        rows.append(
            {
                "ticker": t,
                "close": round(float(c["last"]), 2),
                "score": c["score"],
                "action": c["action"],
            }
        )

    passing = [r for r in rows if r["action"] == "SETUP"]
    passing.sort(key=lambda r: -r["score"])
    return {
        "ts": time.time(),
        "market_as_of": completed_session(batch_now),
        "scanned": len(rows),
        "unavailable": len(universe) - len(rows),
        "market": {
            "spy_pct_5d": round(spy_pct, 2) if spy_pct is not None else None,
            "gate_open": None if market_gate == "UNKNOWN" else market_gate == "PASS",
            "gate_state": gate_state,
            "stale": not bool(spy_bars),
            "as_of": spy_bars[-1][0] if spy_bars else None,
        },
        "passing": len(passing),
        "top": passing[:5],
        "note": "Mechanical screen only — educational, not investment advice.",
        "computing": False,
    }


def build_today(force: bool = False) -> dict[str, Any]:
    """Daily gate overview. Never blocks the request thread.

    Fresh cache (1h) → returned instantly. Otherwise a background thread
    computes it once; callers get the stale payload or a computing flag and
    the page polls. Honest counts only.
    """
    global _today_building
    now = time.time()
    cached = _load_json(TODAY_CACHE_PATH, {})
    engine_dir = _engine_dir()
    import sys
    if str(engine_dir) not in sys.path:
        sys.path.insert(0, str(engine_dir))
    from market_calendar import completed_session

    expected = completed_session()
    payload = (cached or {}).get("payload") or {}
    current = bool(expected) and payload.get("market_as_of") == expected
    if not current:
        cached = {"payload": {"market": {"gate_open": None, "gate_state": "unknown", "stale": True},
                              "top": [], "passing": 0, "scanned": 0}}
    fresh = current and now - float(cached.get("ts") or 0) < TODAY_TTL_SEC
    if fresh and not force:
        return cached.get("payload") or {}

    with _today_lock:
        global _today_building  # noqa: PLW0603
        if _today_building:
            payload = (cached or {}).get("payload") or {}
            return {**payload, "computing": True}
        _today_building = True

    def _worker() -> None:
        global _today_building  # noqa: PLW0603
        try:
            payload = _compute_today()
            with _today_lock:
                _save_json(TODAY_CACHE_PATH, {"ts": time.time(), "payload": payload})
        except Exception:
            pass
        finally:
            with _today_lock:
                _today_building = False

    threading.Thread(target=_worker, daemon=True).start()
    payload = (cached or {}).get("payload") or {}
    return {**payload, "computing": True}
