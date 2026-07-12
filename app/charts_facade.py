"""Path-C facade: invoke charts via subprocess or read real on-disk charts JSON.

Never re-implements generate_charts / mechanical scoring.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

from app.contract import CONTRACT_VERSION, map_charts_payload, normalize_request
from app.quality import assess_charts_payload, fail_response

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_FIXTURE_DIR = REPO_ROOT / "fixtures" / "charts_sample"


def charts_dir() -> Path:
    env = os.environ.get("CHARTS_DIR", "").strip()
    if env:
        return Path(env).expanduser().resolve()
    return (Path.home() / "charts").resolve()


def resolve_mode(explicit: str | None = None) -> str:
    if explicit in {"live", "artifact"}:
        return explicit
    env = os.environ.get("QUANTRADAR_MODE", "artifact").strip().lower()
    return env if env in {"live", "artifact"} else "artifact"


def find_analysis_artifact(ticker: str, root: Path | None = None) -> Path | None:
    """Locate a real charts-produced {TICKER}_analysis.json."""
    t = ticker.upper()
    candidates: list[Path] = []

    fixture = DEFAULT_FIXTURE_DIR / f"{t}_analysis.json"
    if fixture.is_file():
        candidates.append(fixture)

    cdir = root or charts_dir()
    if cdir.is_dir():
        # Prefer sample-site-current symlink (stable demo)
        sample = cdir / "reports" / "sample-site-current" / "assets" / f"{t}_analysis.json"
        if sample.is_file():
            candidates.append(sample)
        # Broader search under reports (bounded)
        reports = cdir / "reports"
        if reports.is_dir():
            for path in sorted(reports.glob(f"**/assets/{t}_analysis.json"), reverse=True):
                if path.is_file() and path not in candidates:
                    candidates.append(path)
                    if len(candidates) >= 8:
                        break

    return candidates[0] if candidates else None


def load_charts_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"charts artifact is not an object: {path}")
    return data


def run_fetch_all(ticker: str, sector: str | None = None, timeout: int = 300) -> dict[str, Any]:
    """Subprocess charts fetch_all.py; parse stdout JSON."""
    cdir = charts_dir()
    script = cdir / "fetch_all.py"
    if not script.is_file():
        raise FileNotFoundError(f"fetch_all.py not found under CHARTS_DIR={cdir}")
    cmd = [sys.executable, str(script), ticker]
    if sector:
        cmd.append(sector)
    result = subprocess.run(
        cmd,
        cwd=str(cdir),
        capture_output=True,
        text=True,
        timeout=timeout,
        env=os.environ.copy(),
    )
    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "fetch_all failed").strip()
        raise RuntimeError(detail[-4000:])
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError("fetch_all returned non-JSON stdout") from exc
    if not isinstance(payload, dict):
        raise RuntimeError("fetch_all JSON root must be object")
    return payload


def _map_or_fail(
    payload: dict[str, Any],
    *,
    ticker: str,
    mode: str,
    analysis_json_path: str | None,
    sources: list[dict[str, str]],
) -> dict[str, Any]:
    quality = assess_charts_payload(payload, ticker)
    if not quality.get("usable"):
        return fail_response(
            ticker=ticker,
            contract_version=CONTRACT_VERSION,
            error=str(quality.get("error") or "no_data"),
            error_detail=str(quality.get("error_detail") or "insufficient data"),
            mode=mode,
            sources=sources,
            warnings=list(quality.get("warnings") or []),
            meta_extra={
                "quality_reasons": quality.get("reasons") or [],
                "analysis_json": analysis_json_path,
            },
        )
    mapped = map_charts_payload(
        payload,
        mode=mode,
        analysis_json_path=analysis_json_path,
        sources=sources,
        quality=quality,
    )
    return mapped


def analyze(
    ticker: str,
    sector: str | None = None,
    mode: str | None = None,
    request_id: str | None = None,
) -> dict[str, Any]:
    """Full analyze path: normalize → charts live|artifact → quality gate → contract map."""
    req = normalize_request(ticker, sector=sector, mode=mode, request_id=request_id)
    mode_r = resolve_mode(req["context"].get("mode"))
    t = req["ticker"]
    sec = req["sector"]

    if mode_r == "live":
        try:
            payload = run_fetch_all(t, sec)
            sources = [
                {"name": "charts.fetch_all", "role": "engine", "status": "ok"},
                {"name": "live-subprocess", "role": "invoke", "status": "ok"},
            ]
            return _map_or_fail(
                payload,
                ticker=t,
                mode="live",
                analysis_json_path=None,
                sources=sources,
            )
        except Exception as exc:
            # Fall through to artifact with warning rather than invent scores
            art = find_analysis_artifact(t)
            if art is None:
                return fail_response(
                    ticker=t,
                    contract_version=req["contract_version"],
                    error="live_fetch_failed",
                    error_detail=str(exc),
                    mode="live",
                    sources=[
                        {"name": "charts.fetch_all", "role": "engine", "status": "error"},
                    ],
                    warnings=[f"live fetch failed: {exc}"],
                    meta_extra={"fallback": None},
                )
            payload = load_charts_json(art)
            sources = [
                {"name": "charts.fetch_all", "role": "engine", "status": "error"},
                {"name": "charts.artifact", "role": "engine", "status": "ok"},
            ]
            mapped = _map_or_fail(
                payload,
                ticker=t,
                mode="artifact",
                analysis_json_path=str(art),
                sources=sources,
            )
            if mapped.get("ok"):
                mapped["warnings"] = list(mapped.get("warnings") or []) + [
                    f"live fetch failed, using artifact: {exc}"
                ]
                mapped["degraded"] = True
                mapped.setdefault("meta", {})["fallback"] = "artifact"
            else:
                mapped["warnings"] = list(mapped.get("warnings") or []) + [
                    f"live fetch failed: {exc}"
                ]
            return mapped

    # artifact mode
    art = find_analysis_artifact(t)
    if art is None:
        return fail_response(
            ticker=t,
            contract_version=req["contract_version"],
            error="artifact_not_found",
            error_detail=(
                f"no charts artifact for {t}; place fixtures/charts_sample/{t}_analysis.json "
                "or set CHARTS_DIR with reports/**/assets"
            ),
            mode="artifact",
            sources=[{"name": "charts.artifact", "role": "engine", "status": "missing"}],
            warnings=[f"no charts artifact for {t}"],
        )
    payload = load_charts_json(art)
    sources = [
        {"name": "charts.artifact", "role": "engine", "status": "ok"},
        {"name": art.name, "role": "file", "status": "ok"},
    ]
    return _map_or_fail(
        payload,
        ticker=t,
        mode="artifact",
        analysis_json_path=str(art),
        sources=sources,
    )
