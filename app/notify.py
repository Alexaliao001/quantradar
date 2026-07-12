"""Waitlist / setup-alert capture (append-only JSONL, no third-party)."""

from __future__ import annotations

import json
import re
import time
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parent.parent
DATA = REPO / "data"
WAITLIST = DATA / "waitlist.jsonl"

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def save_waitlist(
    *,
    email: str,
    ticker: str | None = None,
    kind: str = "setup_alert",
    source: str = "web",
) -> dict[str, Any]:
    email_n = email.strip().lower()
    if not _EMAIL_RE.match(email_n):
        raise ValueError("invalid email")
    DATA.mkdir(parents=True, exist_ok=True)
    rec = {
        "ts": time.time(),
        "email": email_n,
        "ticker": (ticker or "").strip().upper() or None,
        "kind": kind,
        "source": source,
    }
    with WAITLIST.open("a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    return {"ok": True, "email": email_n, "ticker": rec["ticker"], "kind": kind}
