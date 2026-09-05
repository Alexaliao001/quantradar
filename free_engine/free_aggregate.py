"""Multi-source aggregation: per-day cross-source voting → consensus series.

The product promise is "multiple free sources, aggregated into one reliable
series". Rules:

  * A trading day is kept if at least `MIN_AGREE` sources report it, OR if
    only one source is alive (single-source fallback is honest, flagged).
  * The consensus close is the MEDIAN of available closes — resistant to one
    source glitching. Volume is the median too.
  * Days where sources disagree beyond `DISAGREE_PCT` are flagged (still kept,
    using median, counted toward reliability).
"""

from __future__ import annotations

import statistics
from typing import Iterable

MIN_AGREE = 1
DISAGREE_PCT = 3.0  # >3% spread between source closes on one day = disagree


def _median(values: list[float]) -> float:
    return float(statistics.median(values))


def aggregate_bars(
    bars_by_source: dict[str, list[tuple[str, float, float]]],
) -> dict:
    """Merge raw per-source series into a consensus series + diagnostics.

    Returns dict with:
      bars: list[(date, close, volume)] sorted ascending
      per_day_sources: dict[date -> source list that reported it]
      disagree_days: list[date] where spread exceeded threshold
      source_coverage: dict[source -> days reported]
      days: total consensus days
    """
    by_day: dict[str, dict[str, tuple[float, float]]] = {}
    coverage: dict[str, int] = {}
    for source, rows in bars_by_source.items():
        coverage[source] = len(rows)
        for day, close, volume in rows:
            by_day.setdefault(day, {})[source] = (close, volume)

    bars: list[tuple[str, float, float]] = []
    per_day_sources: dict[str, list[str]] = {}
    disagree_days: list[str] = []

    for day in sorted(by_day):
        entries = by_day[day]
        if len(entries) < MIN_AGREE:
            continue
        closes = [c for c, _ in entries.values() if c > 0]
        volumes = [v for _, v in entries.values() if v > 0]
        if not closes:
            continue
        close = _median(closes)
        volume = _median(volumes) if volumes else 0.0
        if len(closes) >= 2:
            spread = (max(closes) - min(closes)) / min(closes) * 100.0
            if spread > DISAGREE_PCT:
                disagree_days.append(day)
        bars.append((day, round(close, 6), round(volume, 2)))
        per_day_sources[day] = sorted(entries.keys())

    return {
        "bars": bars,
        "per_day_sources": per_day_sources,
        "disagree_days": disagree_days,
        "source_coverage": coverage,
        "days": len(bars),
    }


def consensus_dates(bars: Iterable[tuple[str, float, float]]) -> list[str]:
    return [b[0] for b in bars]
