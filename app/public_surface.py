"""Public response surface — keep Trust Gate honesty, shrink cloneable internals.

Guest / Free / artifact responses stay decision-useful (primary, score, gates,
coarse breakdown, freeze). They must not ship analysis file paths, host paths,
or verbose volume/options internals that only help reverse-engineering.

Pro + live keeps fuller data_quality detail for paying operators.
"""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any


def _basename(path: Any) -> str | None:
    if path is None:
        return None
    s = str(path).strip()
    if not s:
        return None
    return Path(s).name


def _slim_sources(sources: Any) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    if not isinstance(sources, list):
        return out
    for s in sources:
        if not isinstance(s, dict):
            continue
        out.append(
            {
                "name": str(s.get("name") or "charts")[:64],
                "role": str(s.get("role") or "engine")[:32],
                "status": str(s.get("status") or "ok")[:32],
            }
        )
    return out


def is_pro_live_audience(user: dict[str, Any] | None, result: dict[str, Any]) -> bool:
    if not user:
        return False
    plan = str(user.get("plan") or "").strip().lower()
    if plan != "pro":
        return False
    meta = result.get("meta") if isinstance(result.get("meta"), dict) else {}
    return str(meta.get("mode") or "").strip().lower() == "live"


def harden_public_analyze(
    result: dict[str, Any],
    *,
    user: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Return a copy safe to send on public HTTP (does not mutate input)."""
    out = deepcopy(result)
    pro_live = is_pro_live_audience(user, out)

    arts = out.get("artifacts") if isinstance(out.get("artifacts"), dict) else {}
    charts_in = arts.get("charts") if isinstance(arts.get("charts"), dict) else {}
    charts_out: dict[str, str | None] = {}
    for key in ("daily_price", "daily_indicators", "weekly_price", "weekly_indicators"):
        charts_out[key] = _basename(charts_in.get(key))
    out["artifacts"] = {
        "charts": charts_out,
        "analysis_json": None,
        "report_html": None,
    }

    out["sources"] = _slim_sources(out.get("sources"))

    meta = out.get("meta") if isinstance(out.get("meta"), dict) else {}
    meta = dict(meta)
    meta.pop("user_email", None)
    meta["public_surface"] = "pro_live" if pro_live else "desk"
    out["meta"] = meta

    if pro_live:
        return out

    # Desk surface (guest, free session, or artifact) — honesty without internals
    dq = out.get("data_quality") if isinstance(out.get("data_quality"), dict) else {}
    vol = dq.get("volume") if isinstance(dq.get("volume"), dict) else {}
    opt = dq.get("options") if isinstance(dq.get("options"), dict) else {}
    out["data_quality"] = {
        "usable": dq.get("usable"),
        "reliability": dq.get("reliability"),
        "volume_narrative_allowed": dq.get("volume_narrative_allowed"),
        "options_actionable": bool(dq.get("options_actionable")),
        "volume": {
            "volume_ratio": vol.get("volume_ratio"),
            "volume_unavailable": vol.get("volume_unavailable"),
            "volume_zero_flag": vol.get("volume_zero_flag"),
        },
        "options": {
            "options_actionable": bool(
                opt.get("options_actionable")
                if "options_actionable" in opt
                else dq.get("options_actionable")
            ),
            "option_data_source": opt.get("option_data_source"),
            "options_simulated": opt.get("options_simulated"),
            "options_from_artifact": opt.get("options_from_artifact"),
        },
    }

    score = out.get("score") if isinstance(out.get("score"), dict) else {}
    breakdown_in = score.get("breakdown") if isinstance(score.get("breakdown"), list) else []
    breakdown_out: list[dict[str, Any]] = []
    for row in breakdown_in:
        if not isinstance(row, dict):
            continue
        breakdown_out.append(
            {
                "name": str(row.get("name") or "")[:48],
                "value": row.get("value"),
                "max": row.get("max"),
            }
        )
    out["score"] = {
        "final": score.get("final"),
        "base_total": score.get("base_total"),
        "scale": score.get("scale", 100),
        "withheld": score.get("withheld"),
        "breakdown": breakdown_out,
    }

    return out
