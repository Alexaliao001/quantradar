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
WATCH_LIMITS = {"free": 1, "pro": 10}


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
    """Append a real scan event (score/action/close) for later avoidance checks.

    The fresh close fetch runs in a background thread so analyze latency is
    unaffected; the ledger entry lands a moment later.
    """
    if not result.get("ok"):
        return
    t = (ticker or "").upper()
    entry = {
        "ticker": t,
        "ts": time.time(),
        "action": str((result.get("primary") or {}).get("action") or ""),
        "score": (result.get("score") or {}).get("final"),
        "email": email,
    }

    def _finish() -> None:
        close = _current_close(t)
        if close is None:
            return
        entry["close"] = close
        with _LOCK:
            store = _load_json(LEDGER_PATH, {"version": 1, "entries": []})
            entries = store.get("entries") or []
            entries.append(entry)
            if len(entries) > _LEDGER_CAP:
                entries = entries[-_LEDGER_CAP:]
            store["entries"] = entries
            _save_json(LEDGER_PATH, store)

    threading.Thread(target=_finish, daemon=True).start()


def _current_close(ticker: str) -> float | None:
    cache = _load_json(PRICE_CACHE_PATH, {})
    now = time.time()
    hit = cache.get(ticker)
    if isinstance(hit, dict) and now - float(hit.get("ts") or 0) < _PRICE_TTL_SEC:
        try:
            return float(hit.get("close"))
        except Exception:
            return None
    close = _fresh_close(ticker)
    if close is None:
        return None
    cache[ticker] = {"ts": now, "close": close}
    with _LOCK:
        _save_json(PRICE_CACHE_PATH, cache)
    return close


def _fresh_close(ticker: str) -> float | None:
    try:
        import sys

        engine_dir = _engine_dir()
        if str(engine_dir) not in sys.path:
            sys.path.insert(0, str(engine_dir))
        import free_sources as fs  # type: ignore

        bars_by_source, _errors = fs.fetch_all_sources(ticker, days=30, cache_dir=None)
        for bars in bars_by_source.values():
            if bars:
                return float(bars[-1][1])
    except Exception:
        return None
    return None


def _engine_dir() -> Path:
    charts_dir = Path(os.environ.get("CHARTS_DIR", "")).expanduser()
    return charts_dir if (charts_dir / "free_sources.py").is_file() else REPO / "free_engine"


def avoidance_events(email: str | None, limit: int = 5) -> list[dict[str, Any]]:
    """Real avoidance moments: scans we called NO/PUT whose cached close later fell >=5%.

    Cache-only by design: the response path never makes network calls. Fresh
    closes are refreshed by record_scan (background) and the daily digest.
    """
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
    with users._LOCK:  # noqa: SLF001 - same-store transactional update
        store = users._load()  # noqa: SLF001
        u = store["users"].get(users.normalize_email(email))
        if not isinstance(u, dict):
            return False, "no account", []
        wl = [str(x).upper() for x in (u.get("watchlist") or [])]
        if t in wl:
            return True, "already watching", wl
        plan = str(u.get("plan") or "free").lower()
        if len(wl) >= WATCH_LIMITS.get(plan, 1):
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

    def closes_for(symbol: str) -> list[float]:
        bars_by_source, _ = fs.fetch_all_sources(symbol, days=60, cache_dir=None)
        for bars in bars_by_source.values():
            if bars:
                return [float(b[1]) for b in bars]
        return []

    spy_c = closes_for("SPY")
    spy_pct = (spy_c[-1] / spy_c[-6] - 1) * 100.0 if len(spy_c) >= 6 else None
    market_open = spy_pct >= 0 if spy_pct is not None else None

    users_rows = []
    recipients = (
        [{"email": normalize_email(email), "watchlist": get_watchlist(email)}]
        if email is not None else digest_optins()
    )
    for row in recipients:
        items = []
        for t in row["watchlist"]:
            closes = closes_for(t)
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
                }
            )
        users_rows.append({"email": row["email"], "items": items})

    digest = {
        "date": time.strftime("%Y-%m-%d", time.gmtime()),
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

    def _stale_cache(symbol: str) -> list:
        """Expired cache fallback: if every live source fails (rate limit),
        an expired-but-real close series beats nothing. Educational screen."""
        for src in ("yahoo_q1", "yahoo_q2", "nasdaq"):
            safe = "".join(ch if ch.isalnum() else "_" for ch in f"{src}:{symbol}")
            p = cache_dir / f"{safe}.json"
            try:
                obj = json.loads(p.read_text(encoding="utf-8"))
                rows = obj.get("v") if isinstance(obj, dict) else None
                if isinstance(rows, list) and len(rows) >= 30:
                    return [(str(r[0]), float(r[1]), float(r[2])) for r in rows]
            except Exception:
                continue
        return []

    def bars_for(symbol: str) -> tuple[list, bool]:
        try:
            bars_by_source, _ = fs.fetch_all_sources(symbol, days=90, cache_dir=cache_dir)
        except Exception:
            bars_by_source = {}
        for bars in bars_by_source.values():
            if bars:
                return list(bars), False
        stale = _stale_cache(symbol)
        return stale, bool(stale)

    spy_bars, spy_stale = bars_for("SPY")
    spy_c = [b[1] for b in spy_bars]
    spy_pct = (spy_c[-1] / spy_c[-6] - 1) * 100.0 if len(spy_c) >= 6 else None
    # Unknown (no SPY data at all) is NOT "closed" — keep the three states honest.
    gate_state = "unknown" if spy_pct is None else ("open" if spy_pct >= 0 else "closed")

    universe = [t for t in TODAY_UNIVERSE if t != "SPY"]
    results: dict[str, list] = {}
    # Low concurrency: Yahoo/Nasdaq free endpoints rate-limit bursts (403).
    with ThreadPoolExecutor(max_workers=3) as pool:
        futures = {pool.submit(bars_for, t): t for t in universe}
        for fut, t in futures.items():
            try:
                results[t] = fut.result(timeout=90)[0]
            except Exception:
                results[t] = []

    rows = []
    for t in universe:
        bars = results.get(t) or []
        if len(bars) < 30:
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
        "scanned": len(rows),
        "market": {
            "spy_pct_5d": round(spy_pct, 2) if spy_pct is not None else None,
            "gate_open": None if spy_pct is None else spy_pct >= 0,
            "gate_state": gate_state,
            "stale": spy_stale,
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
    fresh = isinstance(cached, dict) and now - float(cached.get("ts") or 0) < TODAY_TTL_SEC
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
