"""Completed NYSE sessions shared with the on-device radar calendar."""

import json
import math
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

CALENDAR = json.loads(Path(__file__).with_name("nyse_calendar.json").read_text())


def session_window(end: str, count: int) -> list[str] | None:
    day = date.fromisoformat(end)
    days = []
    while len(days) < count:
        if not CALENDAR["first_year"] <= day.year <= CALENDAR["last_year"]:
            return None
        if day.weekday() < 5 and day.isoformat() not in CALENDAR["holidays"]:
            days.append(day.isoformat())
        day -= timedelta(days=1)
    return list(reversed(days))


def session_close(day: str) -> datetime:
    hour = 13 if day in CALENDAR["early_closes"] else 16
    return datetime.fromisoformat(day).replace(hour=hour, tzinfo=ZoneInfo("America/New_York"))


def completed_session(now: datetime | None = None) -> str | None:
    local = (now or datetime.now(timezone.utc)).astimezone(ZoneInfo("America/New_York"))
    if not CALENDAR["first_year"] <= local.year <= CALENDAR["last_year"]:
        return None
    day = local.date()
    for _ in range(10):
        key = day.isoformat()
        close_hour = 13 if key in CALENDAR["early_closes"] else 16
        if (day.weekday() < 5 and key not in CALENDAR["holidays"]
                and (day < local.date() or local.hour >= close_hour)):
            return key
        day -= timedelta(days=1)
    return None


def completed_bars(bars, *, now: datetime | None = None, minimum: int = 50):
    """Reject stale/invalid history and exclude the still-open daily candle."""
    expected = completed_session(now)
    if expected is None:
        raise ValueError("NYSE calendar coverage unavailable")
    selected = [row for row in bars if row[0] <= expected]
    if len(selected) < minimum or selected[-1][0] != expected:
        raise ValueError(f"daily data does not cover completed session {expected}")
    if any(not math.isfinite(row[1]) or row[1] <= 0
           or not math.isfinite(row[2]) or row[2] < 0 for row in selected):
        raise ValueError("invalid daily prices or volumes")
    if any(a[0] >= b[0] for a, b in zip(selected, selected[1:])):
        raise ValueError("daily bars must have unique ascending dates")
    return selected
