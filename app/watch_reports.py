"""Account-owned daily watchlist snapshots, with recoverable per-ticker work."""

from __future__ import annotations

import csv
import io
import json
import time
import uuid

from app import engagement, paid_delivery, users
from free_engine.market_calendar import completed_session


def request_report(owner: str) -> str:
    owner = users.normalize_email(owner)
    plan = users.resolve_plan(owner)
    if not users.is_paid_plan(plan):
        raise ValueError("Pro is required to create daily watchlist reports")
    cutoff = completed_session()
    if cutoff is None:
        raise ValueError("Market calendar coverage is unavailable")
    roster = engagement.get_watchlist(owner)[:engagement.WATCH_LIMITS[plan]]
    if not roster:
        raise ValueError("Add a ticker to your watchlist first")
    with paid_delivery.database() as db:
        db.execute("""INSERT OR IGNORE INTO watch_reports
            (id,owner,as_of,roster,created_at,csv_enabled) VALUES(?,?,?,?,?,?)""",
            (uuid.uuid4().hex, owner, cutoff, json.dumps(roster), time.time(), int(plan == "portfolio_pro")))
        return db.execute("SELECT id FROM watch_reports WHERE owner=? AND as_of=?", (owner, cutoff)).fetchone()[0]


def schedule_optins():
    for account in engagement.digest_optins():
        if users.is_paid_plan(users.resolve_plan(account["email"])):
            try:
                request_report(account["email"])
            except ValueError:
                pass


def _public(row) -> dict:
    results = json.loads(row["results"])
    roster = json.loads(row["roster"])
    return {
        "id": row["id"], "as_of": row["as_of"], "created_at": row["created_at"],
        "state": row["state"], "tickers": roster, "total": len(roster),
        "processed": len(results), "ready": sum(r["status"] == "ready" for r in results.values()),
        "csv_enabled": bool(row["csv_enabled"]),
        "rows": [{k: v for k, v in results[ticker].items() if k != "attempts"}
                 for ticker in roster if ticker in results],
        "note": "A daily watchlist snapshot, not portfolio returns or trade recommendations. Changes compare prior saved snapshots. Missing data remains UNKNOWN.",
    }


def list_reports(owner: str) -> list[dict]:
    with paid_delivery.database() as db:
        return [_public(row) for row in db.execute("SELECT * FROM watch_reports WHERE owner=? ORDER BY as_of DESC LIMIT 30", (users.normalize_email(owner),))]


def get_report(owner: str, report_id: str) -> dict | None:
    with paid_delivery.database() as db:
        row = db.execute("SELECT * FROM watch_reports WHERE owner=? AND id=?", (users.normalize_email(owner), report_id)).fetchone()
        return _public(row) if row else None


def csv_export(report: dict) -> str:
    output = io.StringIO(newline="")
    fields = ("ticker", "as_of", "status", "close", "score", "action", "market_gate", "previous_action", "changed", "reliability", "note")
    writer = csv.DictWriter(output, fieldnames=fields, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(report["rows"])
    return output.getvalue()


def process_next(*, now: float | None = None) -> bool:
    from app.charts_facade import run_fetch_all
    from app.quality import assess_charts_payload

    now = time.time() if now is None else now
    with paid_delivery.database() as db:
        db.execute("BEGIN IMMEDIATE")
        job = db.execute("""SELECT * FROM watch_reports WHERE state IN ('queued','building','retrying')
            AND retry_at<=? AND lease_until<=? ORDER BY created_at LIMIT 1""", (now, now)).fetchone()
        if job is None:
            return False
        roster, results = json.loads(job["roster"]), json.loads(job["results"])
        candidates = [t for t in roster if t not in results] or [t for t in roster if results[t]["status"] != "ready" and results[t]["attempts"] < 3]
        if not candidates:
            state = "ready" if all(r["status"] == "ready" for r in results.values()) else "partial"
            db.execute("UPDATE watch_reports SET state=?,lease_until=0,lease_token=NULL WHERE id=?", (state, job["id"]))
            return True
        ticker = candidates[0]
        attempt = results.get(ticker, {}).get("attempts", 0) + 1
        results[ticker] = {**results.get(ticker, {}), "ticker": ticker, "as_of": job["as_of"],
                          "status": "unavailable", "action": "UNKNOWN", "score": None,
                          "note": "Data fetch is pending or interrupted.", "attempts": attempt}
        lease_token = uuid.uuid4().hex
        db.execute("UPDATE watch_reports SET state='building',lease_until=?,lease_token=?,results=? WHERE id=?",
                   (now + 120, lease_token, json.dumps(results), job["id"]))
        previous = db.execute("SELECT results FROM watch_reports WHERE owner=? AND as_of<? AND state IN ('ready','partial') ORDER BY as_of DESC LIMIT 1", (job["owner"], job["as_of"])).fetchone()
    prior = json.loads(previous[0]).get(ticker, {}) if previous else {}
    result = {"ticker": ticker, "as_of": job["as_of"], "status": "unavailable", "close": None,
              "score": None, "action": "UNKNOWN", "market_gate": "UNKNOWN", "previous_action": None,
              "changed": None, "reliability": "unknown", "note": "Completed-session data is unavailable.",
              "attempts": attempt, "reconstructed": False}
    try:
        payload = run_fetch_all(ticker)
        quality = assess_charts_payload(payload, ticker)
        if (payload.get("data_quality") or {}).get("market_as_of") != job["as_of"]:
            from free_engine.replay import build_replay
            historical = build_replay(payload, sessions=1, cutoff=job["as_of"])[0]
            if historical["score"] is None:
                raise ValueError("Historical coverage is unavailable")
            result.update(close=historical["close"], score=historical["score"], market_gate=historical["market_gate"],
                          reconstructed=True, sector_gate="UNKNOWN", earnings_gate="UNKNOWN",
                          note="Recovered mechanical reconstruction; historical earnings and sector gates unavailable.")
            action = historical["action"]
        else:
            if not quality["usable"]:
                raise ValueError("Snapshot data is unavailable")
            result.update(close=payload["daily_bars"][-1][1], score=payload["mechanical_scores"]["final_score"],
                          market_gate=payload["data_quality"].get("market_gate", "UNKNOWN"), note="Educational daily-close snapshot.")
            action = payload["mechanical_scores"]["signal_mechanical"]
        action = "PROBE" if action == "SETUP" else action
        previous_action = prior.get("action") if prior.get("status") == "ready" else None
        previous_action = "PROBE" if previous_action == "SETUP" else previous_action
        result.update(status="ready", action=action,
                      previous_action=previous_action, changed=action != previous_action if previous_action else None,
                      reliability=quality.get("reliability", "unknown"))
    except Exception:
        pass
    results[ticker] = result
    missing = any(t not in results for t in roster)
    retry = any(r["status"] != "ready" and r["attempts"] < 3 for r in results.values())
    state = "building" if missing else "retrying" if retry else "ready" if all(r["status"] == "ready" for r in results.values()) else "partial"
    with paid_delivery.database() as db:
        db.execute("UPDATE watch_reports SET results=?,state=?,retry_at=?,lease_until=0,lease_token=NULL WHERE id=? AND lease_token=?",
                   (json.dumps(results, allow_nan=False), state, now + 60 if state == "retrying" else 0, job["id"], lease_token))
    return True
