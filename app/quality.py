"""P0 data-quality gates for the product shell.

Never invent scores, volume narratives, or options profits.
Charts owns formulas; this module only refuses unsafe payloads.
"""

from __future__ import annotations

from typing import Any

# Common Yahoo/Polygon aliases → charts-friendly form
_SYMBOL_ALIASES = {
    "BRK.B": "BRK-B",
    "BRK/B": "BRK-B",
    "BF.B": "BF-B",
    "BF/B": "BF-B",
}

# Hard block — never treat as analyzable equities
_BLOCKED_TICKERS = frozenset(
    {
        "XXXX",
        "XXXXX",
        "TEST",
        "NULL",
        "NONE",
        "N/A",
        "NA",
        "UNDEFINED",
        "FOOBAR",
        "ASDF",
        "QWERTY",
    }
)


def canonicalize_ticker(ticker: str) -> str:
    """Uppercase + common class-share aliases (BRK.B → BRK-B)."""
    t = str(ticker).strip().upper().replace("/", "-")
    return _SYMBOL_ALIASES.get(t, t)


def is_blocked_ticker(ticker: str) -> bool:
    return canonicalize_ticker(ticker) in _BLOCKED_TICKERS


def _nested_get(obj: Any, *path: str) -> Any:
    cur = obj
    for key in path:
        if not isinstance(cur, dict):
            return None
        cur = cur.get(key)
    return cur


def extract_volume_snapshot(payload: dict[str, Any]) -> dict[str, Any]:
    """Best-effort volume fields from charts payload (no invention)."""
    mechanical = payload.get("mechanical_scores") or {}
    base = mechanical.get("base_score") if isinstance(mechanical, dict) else {}
    vp = (base or {}).get("volume_price") if isinstance(base, dict) else {}
    volume_ratio = None
    if isinstance(vp, dict) and vp.get("volume_ratio") is not None:
        try:
            volume_ratio = float(vp["volume_ratio"])
        except (TypeError, ValueError):
            volume_ratio = None

    indicator = payload.get("indicator_data") or {}
    # charts shapes vary; probe common nests
    candidates = [
        _nested_get(indicator, "timeframes", "daily", "volume_ratio_20d"),
        _nested_get(indicator, "daily", "volume_ratio_20d"),
        _nested_get(payload, "technicalIndicators", "volume", "volume"),
        _nested_get(payload, "volumeAnalysis", "avgVolume20"),
        _nested_get(payload, "volumeAnalysis", "currentVolume"),
    ]
    raw_vols = []
    for c in candidates:
        if c is None:
            continue
        try:
            raw_vols.append(float(c))
        except (TypeError, ValueError):
            continue

    avg_vol = None
    cur_vol = None
    va = payload.get("volumeAnalysis")
    if isinstance(va, dict):
        try:
            if va.get("avgVolume20") is not None:
                avg_vol = float(va["avgVolume20"])
            if va.get("currentVolume") is not None:
                cur_vol = float(va["currentVolume"])
        except (TypeError, ValueError):
            pass

    volume_zero = False
    if avg_vol is not None and cur_vol is not None and avg_vol == 0 and cur_vol == 0:
        volume_zero = True
    elif volume_ratio is not None and volume_ratio == 0 and not raw_vols:
        volume_zero = True

    return {
        "volume_ratio": volume_ratio,
        "avg_volume_20": avg_vol,
        "current_volume": cur_vol,
        "volume_unavailable": volume_zero or (volume_ratio is None and avg_vol is None),
        "volume_zero_flag": volume_zero,
    }


def extract_options_snapshot(payload: dict[str, Any]) -> dict[str, Any]:
    dq = payload.get("data_quality") or {}
    chain_ok = dq.get("option_chain_ok")
    source = (
        payload.get("optionChainDataSource")
        or _nested_get(payload, "options", "data_source")
        or ("live" if chain_ok is True else "unknown")
    )
    simulated = str(source).lower() in {"simulated", "sim", "mock", "fake", "synthetic"}
    if chain_ok is False:
        simulated = simulated or True
        source = source if source != "unknown" else "unavailable"
    return {
        "option_chain_ok": chain_ok,
        "option_data_source": source,
        "options_simulated": simulated,
        "options_actionable": bool(chain_ok) and not simulated,
    }


def assess_charts_payload(payload: dict[str, Any] | None, ticker: str) -> dict[str, Any]:
    """Return quality assessment. `usable` False → shell must not emit a trade score."""
    t = canonicalize_ticker(ticker)
    reasons: list[str] = []
    warnings: list[str] = []

    if is_blocked_ticker(t):
        return {
            "usable": False,
            "error": "invalid_ticker",
            "error_detail": f"{t} is not a real security symbol",
            "reasons": ["blocked_placeholder_ticker"],
            "warnings": [],
            "volume": {},
            "options": {},
        }

    if not isinstance(payload, dict) or not payload:
        return {
            "usable": False,
            "error": "no_data",
            "error_detail": f"no charts payload for {t}",
            "reasons": ["empty_payload"],
            "warnings": [],
            "volume": {},
            "options": {},
        }

    payload_ticker = str(payload.get("ticker") or "").upper()
    if payload_ticker and canonicalize_ticker(payload_ticker) != t:
        # Allow if payload ticker is alias of request
        if canonicalize_ticker(payload_ticker) != canonicalize_ticker(t):
            reasons.append(
                f"payload_ticker_mismatch:{payload_ticker}!={t}"
            )

    mechanical = payload.get("mechanical_scores")
    if not isinstance(mechanical, dict) or not mechanical:
        return {
            "usable": False,
            "error": "no_data",
            "error_detail": f"charts payload for {t} lacks mechanical_scores",
            "reasons": ["missing_mechanical_scores"],
            "warnings": [],
            "volume": extract_volume_snapshot(payload),
            "options": extract_options_snapshot(payload),
        }

    # Explicit engine failure markers
    if payload.get("error") or payload.get("ok") is False:
        return {
            "usable": False,
            "error": "engine_error",
            "error_detail": str(payload.get("error") or "charts engine reported failure"),
            "reasons": ["engine_flagged_error"],
            "warnings": [],
            "volume": extract_volume_snapshot(payload),
            "options": extract_options_snapshot(payload),
        }

    final = mechanical.get("final_score")
    if final is None and mechanical.get("signal_mechanical") is None:
        reasons.append("missing_score_and_signal")

    dq = payload.get("data_quality") or {}
    reliability = str(dq.get("reliability") or "unknown")
    if reliability in {"none", "failed", "empty"}:
        reasons.append(f"reliability={reliability}")

    tf_ok = dq.get("timeframes_ok")
    if tf_ok is not None:
        try:
            if int(tf_ok) <= 0:
                reasons.append("timeframes_ok=0")
        except (TypeError, ValueError):
            pass

    volume = extract_volume_snapshot(payload)
    options = extract_options_snapshot(payload)

    if volume.get("volume_zero_flag"):
        warnings.append(
            "volume_fields_are_zero — volume-price narrative withheld; do not invent breakout volume"
        )
    if volume.get("volume_unavailable") and not volume.get("volume_zero_flag"):
        warnings.append("volume metrics unavailable from engine payload")

    if options.get("options_simulated"):
        warnings.append(
            f"options data source={options.get('option_data_source')!r} — "
            "options conclusions non-actionable (simulated/unavailable)"
        )

    for w in dq.get("warnings") or []:
        warnings.append(str(w))

    if reasons:
        return {
            "usable": False,
            "error": "no_data",
            "error_detail": f"insufficient engine data for {t}: {', '.join(reasons)}",
            "reasons": reasons,
            "warnings": warnings,
            "volume": volume,
            "options": options,
        }

    return {
        "usable": True,
        "error": None,
        "error_detail": None,
        "reasons": [],
        "warnings": warnings,
        "volume": volume,
        "options": options,
        "reliability": reliability,
    }


def fail_response(
    *,
    ticker: str,
    contract_version: str,
    error: str,
    error_detail: str,
    mode: str,
    sources: list[dict[str, str]] | None = None,
    warnings: list[str] | None = None,
    meta_extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Contract-shaped hard failure — score withheld, no buy signal."""
    t = canonicalize_ticker(ticker)
    meta = {
        "engine": "charts",
        "mode": mode,
        "score_withheld": True,
        "primary": "NO",
    }
    if meta_extra:
        meta.update(meta_extra)
    return {
        "ok": False,
        "contract_version": contract_version,
        "ticker": t,
        "error": error,
        "error_detail": error_detail,
        "gate": {
            "state_code": None,
            "state_name": None,
            "state_reason": error_detail,
            "signal": "NO",
            "signal_label": "No / stand aside",
            "primary": "NO",
        },
        "score": {
            "final": None,
            "base_total": None,
            "scale": 100,
            "withheld": True,
        },
        "primary": {
            "action": "NO",
            "label": "No / stand aside",
            "reason": error_detail,
        },
        "data_quality": {
            "usable": False,
            "volume_narrative_allowed": False,
            "options_actionable": False,
        },
        "artifacts": {"charts": {}, "analysis_json": None, "report_html": None},
        "sources": sources
        or [{"name": "charts", "role": "engine", "status": "error"}],
        "warnings": list(warnings or []),
        "degraded": True,
        "market": {},
        "meta": meta,
    }
