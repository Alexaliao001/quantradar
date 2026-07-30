"""Operator-published track notes — never invent win rates or social proof."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_PATH = REPO_ROOT / "fixtures" / "track_record.json"


def track_path() -> Path:
    env = os.environ.get("QUANTRADAR_TRACK_FILE", "").strip()
    if env:
        return Path(env).expanduser()
    return DEFAULT_PATH


def load_track_record() -> dict[str, Any]:
    path = track_path()
    if not path.is_file():
        return {
            "ok": True,
            "label": "Operator track notes",
            "disclaimer": (
                "No published track entries yet. We do not invent win rates or user counts. "
                "Educational only — not investment advice."
            ),
            "entries": [],
            "stats": None,
            "source": "empty",
        }
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {
            "ok": False,
            "error": "track_unreadable",
            "label": "Operator track notes",
            "disclaimer": "Track file present but unreadable.",
            "entries": [],
            "stats": None,
            "source": str(path.name),
        }
    if not isinstance(raw, dict):
        return {
            "ok": False,
            "error": "track_invalid",
            "entries": [],
            "stats": None,
        }
    entries = raw.get("entries") if isinstance(raw.get("entries"), list) else []
    clean: list[dict[str, Any]] = []
    for e in entries[:100]:
        if not isinstance(e, dict):
            continue
        clean.append(
            {
                "as_of": str(e.get("as_of") or "")[:32],
                "ticker": str(e.get("ticker") or "")[:12].upper(),
                "primary_at_publish": str(e.get("primary_at_publish") or "")[:24],
                "score_at_publish": e.get("score_at_publish"),
                "note": str(e.get("note") or "")[:400],
                "outcome": e.get("outcome"),
                "outcome_note": str(e.get("outcome_note") or "")[:400],
            }
        )
    return {
        "ok": True,
        "label": str(raw.get("label") or "Operator track notes")[:80],
        "disclaimer": str(
            raw.get("disclaimer")
            or (
                "Operator-published snapshots only. Not audited returns. "
                "Educational only — not investment advice."
            )
        )[:600],
        "entries": clean,
        "stats": None,  # TG-3: never invent aggregate win-rate stats
        "updated": raw.get("updated"),
        "source": path.name,
    }
