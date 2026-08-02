"""ENGINE_CONTRACT v1 — request normalize + charts payload → shell response map.

No scoring formulas here. Scores and gates come only from charts JSON.
"""

from __future__ import annotations

import math
import re
from pathlib import Path
from typing import Any

from app.quality import (
    assess_charts_payload,
    canonicalize_ticker,
    extract_options_snapshot,
    extract_volume_snapshot,
    is_blocked_ticker,
)

CONTRACT_VERSION = "1.0.0"

_TICKER_RE = re.compile(r"^[A-Za-z][A-Za-z0-9.\-]{0,9}$")

SIGNAL_LABELS = {
    "FULL": "Full size",
    "BUILD": "Build",
    "PROBE": "Probe",
    "WAIT": "Wait",
    "NO": "No / stand aside",
    # charts PUT = hedge bias label — NOT a sell / short order (NO_IS_NOT_SELL)
    "PUT": "Put / hedge bias — not a sell order",
}


def normalize_request(
    ticker: str | None,
    sector: str | None = None,
    mode: str | None = None,
    request_id: str | None = None,
    contract_version: str | None = None,
) -> dict[str, Any]:
    """Normalize and validate an analyze request. Raises ValueError on bad ticker."""
    if ticker is None or not str(ticker).strip():
        raise ValueError("ticker is required")
    raw = canonicalize_ticker(str(ticker))
    if not _TICKER_RE.match(raw):
        raise ValueError(f"invalid ticker: {ticker!r}")
    if is_blocked_ticker(raw):
        raise ValueError(f"invalid or placeholder ticker: {raw}")
    out: dict[str, Any] = {
        "contract_version": contract_version or CONTRACT_VERSION,
        "ticker": raw,
        "sector": canonicalize_ticker(str(sector)) if sector else None,
        "context": {
            "mode": (mode or "").strip().lower() or None,
            "request_id": request_id,
        },
    }
    return out


def _public_path(path: str | None) -> str | None:
    """Never leak host paths into public API JSON — basename only."""
    if path is None:
        return None
    s = str(path).strip()
    if not s:
        return None
    return Path(s).name


def _chart_paths(indicator_data: dict[str, Any]) -> dict[str, str | None]:
    files = (indicator_data or {}).get("chart_files") or {}
    daily = files.get("daily") or {}
    weekly = files.get("weekly") or {}
    return {
        "daily_price": _public_path(daily.get("price")),
        "daily_indicators": _public_path(daily.get("indicators")),
        "weekly_price": _public_path(weekly.get("price")),
        "weekly_indicators": _public_path(weekly.get("indicators")),
    }


def _map_entry_timing(mechanical: dict[str, Any]) -> dict[str, Any] | None:
    """Map charts mechanical_scores.entry_timing — omit when absent (never invent)."""
    et = mechanical.get("entry_timing") if isinstance(mechanical, dict) else None
    if not isinstance(et, dict) or not et:
        return None
    out: dict[str, Any] = {}
    grade = et.get("grade")
    if grade is not None and str(grade).strip():
        out["grade"] = str(grade).strip().upper()[:8]
    for key in ("total", "max"):
        if et.get(key) is None:
            continue
        try:
            out[key] = float(et[key])
        except (TypeError, ValueError):
            continue
    return out or None


def _coerce_score(raw: Any) -> tuple[float | None, bool]:
    """Return (score, withheld). Never invent 0; reject bool/NaN/out-of-range."""
    if raw is None or isinstance(raw, bool):
        return None, True
    try:
        value = float(raw)
    except (TypeError, ValueError):
        return None, True
    if math.isnan(value) or math.isinf(value):
        return None, True
    if value < 0.0 or value > 100.0:
        return None, True
    return value, False


def _env_layer_status(market_env: dict[str, Any], *, layer: str) -> str:
    """Honest gate status — presence of market_env is not a pass.

    The shell does not recompute charts market/sector filters. Without an
    explicit engine status field we surface ``unknown`` / ``unavailable``
    rather than painting a green pass from field existence.
    """
    if not isinstance(market_env, dict) or not market_env:
        return "unavailable" if layer == "sector" else "unknown"
    if layer == "market":
        if market_env.get("spy_change_pct") is None and not market_env.get("market_state"):
            return "unknown"
        return "unknown"
    if layer == "sector":
        if (
            market_env.get("sector_etf") is None
            and market_env.get("sector_change_pct") is None
        ):
            return "unavailable"
        return "unknown"
    return "unknown"


def map_charts_payload(
    payload: dict[str, Any],
    *,
    mode: str,
    analysis_json_path: str | None = None,
    sources: list[dict[str, str]] | None = None,
    quality: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Map a real charts fetch_all / *_analysis.json object to ENGINE_CONTRACT response."""
    ticker = canonicalize_ticker(str(payload.get("ticker") or ""))
    mechanical = payload.get("mechanical_scores") or {}
    state = mechanical.get("state") or {}
    if not isinstance(state, dict):
        state = {}
    data_quality = payload.get("data_quality") or {}
    fundamentals = payload.get("fundamentals") or {}
    market_env = payload.get("market_env") or {}
    indicator_data = payload.get("indicator_data") or {}

    q = quality if quality is not None else assess_charts_payload(payload, ticker)
    vol = q.get("volume") or extract_volume_snapshot(payload)
    opt = q.get("options") or extract_options_snapshot(payload)

    signal = str(
        mechanical.get("signal_timing_gated")
        or mechanical.get("signal_mechanical")
        or "NO"
    )
    warnings = [str(w) for w in (q.get("warnings") or [])]
    # de-dupe while preserving order
    seen: set[str] = set()
    uniq_warnings: list[str] = []
    for w in warnings:
        if w not in seen:
            seen.add(w)
            uniq_warnings.append(w)
    warnings = uniq_warnings

    reliability = str(
        q.get("reliability") or data_quality.get("reliability") or "unknown"
    )
    volume_narrative_allowed = True
    if vol.get("volume_zero_flag"):
        volume_narrative_allowed = False
    elif vol.get("volume_unavailable") and vol.get("volume_ratio") is None:
        volume_narrative_allowed = False

    # Copy options snapshot so we can annotate without mutating quality cache
    opt = dict(opt) if isinstance(opt, dict) else {}
    options_actionable = bool(opt.get("options_actionable"))

    # SX1-4: artifact mode is a frozen snapshot — never claim live options actionable.
    # Do not add a warnings[] entry solely for this (would force degraded demos).
    if mode == "artifact":
        opt = {
            **opt,
            "options_actionable": False,
            "option_data_source": "artifact_snapshot",
            "options_from_artifact": True,
        }
        options_actionable = False

    degraded = reliability in {"low", "poor"} or bool(warnings)
    if not volume_narrative_allowed:
        degraded = True
    if opt.get("options_simulated"):
        degraded = True
    if mode == "artifact" and reliability == "unknown":
        reliability = "medium"

    base = mechanical.get("base_score") or {}
    base_total = base.get("total") if isinstance(base, dict) else None
    final, score_withheld = _coerce_score(mechanical.get("final_score"))
    if score_withheld:
        if "score missing or invalid from charts payload" not in warnings:
            warnings.append("score missing or invalid from charts payload")
        degraded = True

    breakdown: list[dict[str, Any]] = []
    if isinstance(base, dict) and not score_withheld:
        for key in ("volume_price", "momentum", "trend", "risk"):
            part = base.get(key)
            if not isinstance(part, dict):
                continue
            if part.get("total") is None or part.get("max") is None:
                continue
            try:
                breakdown.append(
                    {
                        "name": key,
                        "value": float(part["total"]),
                        "max": float(part["max"]),
                    }
                )
            except (TypeError, ValueError):
                continue

    default_sources = sources or [
        {
            "name": "charts",
            "role": "engine",
            "status": "ok" if not degraded else "degraded",
        },
    ]

    # Single primary conclusion — never dual buy + wait
    primary_action = signal if signal in SIGNAL_LABELS else "NO"
    primary_label = SIGNAL_LABELS.get(primary_action, primary_action)

    # Never expose on-disk analysis paths to clients (clone surface).
    _ = analysis_json_path

    fetch_time = payload.get("fetch_time")
    freeze_label = None
    if mode == "artifact" and fetch_time:
        freeze_label = f"Frozen demo snapshot · {str(fetch_time)[:10]}"
    elif mode == "artifact":
        freeze_label = "Frozen demo snapshot · not a live feed"
    elif mode == "live":
        freeze_label = "Live path · freshness follows data_quality"

    # Honest engagement copy (loss-aversion without dark patterns)
    if primary_action in {"WAIT"}:
        avoided_line = (
            "Radar says stand aside — often that avoids chasing a half-formed setup."
        )
    elif primary_action in {"NO"} or str(primary_action).startswith("PUT"):
        avoided_line = (
            "Standing aside here can spare you a bad entry. Re-check when setup improves."
        )
    elif primary_action in {"FULL", "BUILD", "PROBE"}:
        avoided_line = (
            "Gates allow engagement — still size risk yourself. Educational only."
        )
    else:
        avoided_line = "One mechanical read. Educational only — not investment advice."

    market_env = market_env if isinstance(market_env, dict) else {}
    gate_obj: dict[str, Any] = {
        "state_code": state.get("code"),
        "state_name": state.get("name"),
        "state_reason": state.get("reason"),
        "signal": signal,
        "signal_label": SIGNAL_LABELS.get(signal, signal),
        "primary": primary_action,
        "market_gate": {
            "status": _env_layer_status(market_env, layer="market"),
            "spy_change_pct": market_env.get("spy_change_pct"),
            "market_state": market_env.get("market_state"),
        },
        "sector_gate": {
            "status": _env_layer_status(market_env, layer="sector"),
            "sector_etf": market_env.get("sector_etf"),
            "sector_change_pct": market_env.get("sector_change_pct"),
        },
    }
    # P0: map charts entry_timing when present — never invent
    entry_timing = _map_entry_timing(mechanical if isinstance(mechanical, dict) else {})
    if entry_timing:
        gate_obj["entry_timing"] = entry_timing

    if score_withheld:
        score_note = "Score withheld — missing or invalid mechanical score from engine."
        summary = (
            f"{ticker} — Posture score: withheld · Primary: {primary_label}"
            + (f" · {state.get('name')}" if state.get("name") else "")
        )
        base_total_out = None
    else:
        score_note = (
            "Single authoritative posture score from charts — not a direction call "
            "and not a multi-panel composite mix."
        )
        summary = (
            f"{ticker} — Posture score: {float(final):.0f}/100 · "
            f"Primary: {primary_label}"
            + (f" · {state.get('name')}" if state.get("name") else "")
        )
        try:
            base_total_out = float(base_total) if base_total is not None else None
        except (TypeError, ValueError):
            base_total_out = None

    return {
        "ok": True,
        "contract_version": CONTRACT_VERSION,
        "ticker": ticker,
        "company_name": fundamentals.get("company_name") or ticker,
        "sector": fundamentals.get("sector") or market_env.get("sector_etf"),
        "gate": gate_obj,
        "score": {
            "final": None if score_withheld else float(final),  # type: ignore[arg-type]
            "base_total": base_total_out,
            "scale": 100,
            "withheld": score_withheld,
            "breakdown": breakdown,
        },
        # TG-1: only public-facing composite. UI must not invent sibling "Composite" scores.
        "primary_score": {
            "value": None if score_withheld else float(final),  # type: ignore[arg-type]
            "scale": 100,
            "label": "Mechanical posture score",
            "withheld": score_withheld,
            "note": score_note,
        },
        "primary": {
            "action": primary_action,
            "label": primary_label,
            "reason": state.get("reason") or primary_label,
        },
        "summary": summary,
        "engagement": {
            "avoided_line": avoided_line,
            "freeze_label": freeze_label,
            "loop": "verdict → why → gates → next (remind / upgrade / re-check)",
            "posture_note": "Mechanical posture ≠ trade direction. PUT ≠ sell order.",
        },
        "data_quality": {
            "usable": True,
            "reliability": reliability,
            "volume_narrative_allowed": volume_narrative_allowed,
            "volume": vol,
            "options_actionable": options_actionable,
            "options": opt,
        },
        "artifacts": {
            "charts": _chart_paths(indicator_data if isinstance(indicator_data, dict) else {}),
            "analysis_json": None,
            "report_html": None,
        },
        "sources": default_sources,
        "warnings": warnings,
        "degraded": degraded,
        "market": {
            "market_state": market_env.get("market_state"),
            "spy_change_pct": market_env.get("spy_change_pct"),
            "sector_etf": market_env.get("sector_etf"),
            "sector_change_pct": market_env.get("sector_change_pct"),
            "vix_current": market_env.get("vix_current"),
            "vix_trend": market_env.get("vix_trend"),
        },
        "meta": {
            "engine": "charts",
            "mode": mode,
            "fetch_time": fetch_time,
            "generated_at": (indicator_data or {}).get("generated_at")
            if isinstance(indicator_data, dict)
            else None,
            "reliability": reliability,
            "score_withheld": score_withheld,
            "primary": primary_action,
            "disclaimer": "Educational radar only — not investment advice.",
            "data_path": "artifact_fixtures" if mode == "artifact" else "charts_engine",
        },
    }


def validate_response(obj: Any) -> list[str]:
    """Return list of contract violations (empty = valid). Stdlib-only structural check."""
    errors: list[str] = []
    if not isinstance(obj, dict):
        return ["response must be an object"]
    for key in (
        "ok",
        "contract_version",
        "ticker",
        "gate",
        "score",
        "artifacts",
        "sources",
        "warnings",
    ):
        if key not in obj:
            errors.append(f"missing required field: {key}")
    if "ok" in obj and not isinstance(obj["ok"], bool):
        errors.append("ok must be boolean")
    if obj.get("contract_version") in (None, ""):
        errors.append("contract_version must be non-empty")
    if obj.get("ticker") in (None, ""):
        errors.append("ticker must be non-empty")

    ok = obj.get("ok")
    gate = obj.get("gate")
    if not isinstance(gate, dict):
        errors.append("gate must be object")
    elif not (gate.get("signal") or gate.get("state_code")):
        errors.append("gate must include signal or state_code")

    score = obj.get("score")
    if not isinstance(score, dict):
        errors.append("score must be object")
    else:
        final = score.get("final")
        withheld = bool(score.get("withheld")) or ok is False
        if final is None:
            if not withheld:
                errors.append("score.final must be a number unless withheld/ok=false")
        elif not isinstance(final, (int, float)):
            errors.append("score.final must be a number")
        if "scale" not in score or not isinstance(score["scale"], (int, float)):
            errors.append("score.scale must be a number")

    # P0: never emit actionable buy-like signals for hard failures
    if ok is False:
        if not obj.get("error"):
            errors.append("ok=false requires error")
        if looks_like_fake_buy(obj):
            errors.append("ok=false must not look like a buy recommendation with score")
        primary = (
            (obj.get("primary") or {}).get("action")
            if isinstance(obj.get("primary"), dict)
            else None
        )
        gate_sig = gate.get("signal") if isinstance(gate, dict) else None
        if primary and primary not in (None, "NO", "WAIT"):
            errors.append("ok=false primary.action must be NO or WAIT")
        if gate_sig and gate_sig not in (None, "NO", "WAIT"):
            errors.append("ok=false gate.signal must be NO or WAIT")

    artifacts = obj.get("artifacts")
    if not isinstance(artifacts, dict):
        errors.append("artifacts must be object")
    elif "charts" not in artifacts or not isinstance(artifacts["charts"], dict):
        errors.append("artifacts.charts must be object")
    if "sources" in obj and not isinstance(obj["sources"], list):
        errors.append("sources must be array")
    if "warnings" in obj and not isinstance(obj["warnings"], list):
        errors.append("warnings must be array")
    return errors


def looks_like_fake_buy(obj: dict[str, Any]) -> bool:
    """True if a failed/no-data response still looks like a buy call (P0)."""
    score = obj.get("score") if isinstance(obj.get("score"), dict) else {}
    final = score.get("final")
    if score.get("withheld") or final is None:
        return False
    try:
        score_n = float(final)
    except (TypeError, ValueError):
        return False
    if score_n < 50:
        return False
    sig = str((obj.get("gate") or {}).get("signal") or "").upper()
    primary = ""
    if isinstance(obj.get("primary"), dict):
        primary = str(obj["primary"].get("action") or "").upper()
    bullish = {"FULL", "BUILD", "PROBE", "BUY", "LONG"}
    return sig in bullish or primary in bullish
