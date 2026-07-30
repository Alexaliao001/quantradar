"""Honest funnel / engagement event log (append-only JSONL, no third-party trackers).

Events (N1–N5 north-star):
  demo_run | analyze_run | signup | checkout_start | pro_active | live_run | notify_save

Never store raw emails or passwords. Optional email_hash is truncated SHA-256.
"""

from __future__ import annotations

import hashlib
import json
import os
import threading
import time
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parent.parent
DATA = REPO / "data"
FUNNEL_PATH = DATA / "funnel.jsonl"

_LOCK = threading.Lock()

# Cap append-only log growth (funnel poisoning / disk fill). Override via env.
DEFAULT_FUNNEL_MAX_BYTES = 5 * 1024 * 1024  # 5 MiB

ALLOWED_EVENTS = frozenset(
    {
        "demo_run",
        "analyze_run",
        "signup",
        "checkout_start",
        "pro_active",
        "live_run",
        "notify_save",
    }
)


def funnel_max_bytes() -> int:
    raw = os.environ.get("QUANTRADAR_FUNNEL_MAX_BYTES", "").strip()
    if not raw:
        return DEFAULT_FUNNEL_MAX_BYTES
    try:
        return max(1024, int(raw))
    except ValueError:
        return DEFAULT_FUNNEL_MAX_BYTES


def email_hash(email: str | None) -> str | None:
    if not email:
        return None
    raw = email.strip().lower().encode("utf-8")
    if not raw:
        return None
    return hashlib.sha256(raw).hexdigest()[:16]


def track(
    event: str,
    *,
    ticker: str | None = None,
    mode: str | None = None,
    primary: str | None = None,
    plan: str | None = None,
    interval: str | None = None,
    ok: bool | None = None,
    demo: bool | None = None,
    kind: str | None = None,
    email: str | None = None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    """Append one funnel event. Returns the record, or None if event name invalid."""
    name = (event or "").strip().lower()
    if name not in ALLOWED_EVENTS:
        return None
    rec: dict[str, Any] = {
        "ts": time.time(),
        "event": name,
    }
    if ticker:
        rec["ticker"] = str(ticker).strip().upper()[:12]
    if mode:
        rec["mode"] = str(mode).strip().lower()[:24]
    if primary:
        rec["primary"] = str(primary).strip().upper()[:24]
    if plan:
        rec["plan"] = str(plan).strip().lower()[:16]
    if interval:
        rec["interval"] = str(interval).strip().lower()[:16]
    if ok is not None:
        rec["ok"] = bool(ok)
    if demo is not None:
        rec["demo"] = bool(demo)
    if kind:
        rec["kind"] = str(kind).strip()[:32]
    eh = email_hash(email)
    if eh:
        rec["email_hash"] = eh
    if extra:
        for k, v in extra.items():
            if k in rec or k in {"email", "password", "token"}:
                continue
            if isinstance(v, (str, int, float, bool)) or v is None:
                rec[k] = v
    DATA.mkdir(parents=True, exist_ok=True)
    line = json.dumps(rec, ensure_ascii=False) + "\n"
    max_bytes = funnel_max_bytes()
    with _LOCK:
        try:
            size = FUNNEL_PATH.stat().st_size if FUNNEL_PATH.is_file() else 0
        except OSError:
            size = 0
        if size + len(line.encode("utf-8")) > max_bytes:
            # Refuse write — do not truncate (preserve audit trail integrity)
            return None
        with FUNNEL_PATH.open("a", encoding="utf-8") as f:
            f.write(line)
    return rec


def read_events(*, limit: int | None = None) -> list[dict[str, Any]]:
    if not FUNNEL_PATH.is_file():
        return []
    out: list[dict[str, Any]] = []
    with FUNNEL_PATH.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(obj, dict):
                out.append(obj)
    if limit is not None and limit >= 0:
        return out[-limit:]
    return out


def summarize(events: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    rows = events if events is not None else read_events()
    counts: dict[str, int] = {e: 0 for e in sorted(ALLOWED_EVENTS)}
    for r in rows:
        ev = str(r.get("event") or "")
        if ev in counts:
            counts[ev] += 1

    def rate(a: str, b: str) -> float | None:
        denom = counts.get(b) or 0
        num = counts.get(a) or 0
        if denom <= 0:
            return None
        return round(num / denom, 4)

    path_out = str(FUNNEL_PATH)
    try:
        path_out = str(FUNNEL_PATH.relative_to(REPO))
    except ValueError:
        path_out = str(FUNNEL_PATH)
    return {
        "ok": True,
        "events": len(rows),
        "counts": counts,
        "rates": {
            "signup_per_demo": rate("signup", "demo_run"),
            "checkout_per_signup": rate("checkout_start", "signup"),
            "pro_per_checkout": rate("pro_active", "checkout_start"),
            "live_per_pro": rate("live_run", "pro_active"),
            "notify_per_demo": rate("notify_save", "demo_run"),
        },
        "path": path_out if FUNNEL_PATH.is_file() else path_out,
    }
