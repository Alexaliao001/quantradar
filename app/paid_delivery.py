"""Durable report ownership, recoverable delivery, and subscription state."""

from __future__ import annotations

import json
import os
import re
import sqlite3
import threading
import time
import uuid
from contextlib import contextmanager
from pathlib import Path

from app import users
from app.contract import normalize_request
from free_engine.replay import build_replay, build_report_bundle


_schema_lock = threading.Lock()
_initialized_databases: set[tuple[str, int]] = set()


@contextmanager
def database():
    path = Path(os.environ.get("QUANTRADAR_BILLING_DB", str(users.USERS_PATH.with_name("billing.sqlite3"))))
    path.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(path, timeout=35)
    db.row_factory = sqlite3.Row
    try:
        identity = (str(path.resolve()), path.stat().st_ino)
        with _schema_lock:
            if identity not in _initialized_databases:
                os.chmod(path, 0o600)
                db.execute("PRAGMA journal_mode=WAL")
                db.executescript("""
                    CREATE TABLE IF NOT EXISTS report_orders (
                        id TEXT PRIMARY KEY, owner TEXT NOT NULL, request_key TEXT NOT NULL,
                        ticker TEXT NOT NULL, sector TEXT, bump INTEGER NOT NULL,
                        amount INTEGER NOT NULL, currency TEXT NOT NULL DEFAULT 'usd',
                        created_at REAL NOT NULL, as_of TEXT NOT NULL, inputs TEXT NOT NULL,
                        checkout_id TEXT UNIQUE, checkout_url TEXT, payment_intent TEXT UNIQUE,
                        payment_state TEXT NOT NULL DEFAULT 'unpaid', paid_at REAL,
                        delivery_state TEXT NOT NULL DEFAULT 'pending', bundle TEXT,
                        attempts INTEGER NOT NULL DEFAULT 0, retry_at REAL NOT NULL DEFAULT 0,
                        lease_until REAL NOT NULL DEFAULT 0, lease_token TEXT, error TEXT,
                        legacy INTEGER NOT NULL DEFAULT 0, credit_code TEXT,
                        credit_state TEXT NOT NULL DEFAULT 'pending',
                        UNIQUE(owner, request_key)
                    );
                    CREATE TABLE IF NOT EXISTS billing_events (
                        id TEXT PRIMARY KEY, type TEXT NOT NULL, processed_at REAL NOT NULL, result TEXT NOT NULL
                    );
                    CREATE TABLE IF NOT EXISTS payment_refunds (
                        payment_intent TEXT PRIMARY KEY, fully_refunded INTEGER NOT NULL
                    );
                    CREATE TABLE IF NOT EXISTS subscriptions (
                        id TEXT PRIMARY KEY, owner TEXT NOT NULL, customer_id TEXT NOT NULL,
                        plan TEXT NOT NULL, price_id TEXT NOT NULL, status TEXT NOT NULL,
                        paid_through REAL NOT NULL, updated_at REAL NOT NULL
                    );
                    CREATE TABLE IF NOT EXISTS stripe_customers (
                        owner TEXT PRIMARY KEY, request_id TEXT NOT NULL, customer_id TEXT
                    );
                    CREATE TABLE IF NOT EXISTS subscription_checkouts (
                        owner TEXT PRIMARY KEY, id TEXT UNIQUE NOT NULL,
                        plan TEXT NOT NULL, interval TEXT NOT NULL, price_id TEXT NOT NULL,
                        coupon_id TEXT, customer_id TEXT NOT NULL,
                        checkout_id TEXT, checkout_url TEXT,
                        state TEXT NOT NULL DEFAULT 'creating', created_at REAL NOT NULL
                    );
                    CREATE INDEX IF NOT EXISTS subscriptions_owner ON subscriptions(owner);
                    CREATE INDEX IF NOT EXISTS reports_owner ON report_orders(owner, created_at);
                    CREATE TABLE IF NOT EXISTS watch_reports (
                        id TEXT PRIMARY KEY, owner TEXT NOT NULL, as_of TEXT NOT NULL,
                        roster TEXT NOT NULL, results TEXT NOT NULL DEFAULT '{}',
                        created_at REAL NOT NULL, state TEXT NOT NULL DEFAULT 'queued',
                        csv_enabled INTEGER NOT NULL, retry_at REAL NOT NULL DEFAULT 0,
                        lease_until REAL NOT NULL DEFAULT 0, lease_token TEXT, UNIQUE(owner,as_of)
                    );
                """)
                for table in ("watch_reports", "report_orders"):
                    if "lease_token" not in {row[1] for row in db.execute(f"PRAGMA table_info({table})")}:
                        db.execute(f"ALTER TABLE {table} ADD COLUMN lease_token TEXT")
                _initialized_databases.add(identity)
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def event_once(event_id: str, event_type: str, apply):
    if not event_id or not event_id.startswith("evt_"):
        raise ValueError("verified event ID required")
    with database() as db:
        db.execute("BEGIN IMMEDIATE")
        prior = db.execute("SELECT result FROM billing_events WHERE id=?", (event_id,)).fetchone()
        if prior:
            return {**json.loads(prior[0]), "duplicate": True}
        result = apply(db)
        if result.get("ok"):
            db.execute("INSERT INTO billing_events VALUES(?,?,?,?)",
                       (event_id, event_type, time.time(), json.dumps(result)))
        else:
            db.rollback()
        return result


def prepare_report_order(owner: str, ticker: str, *, sector=None, bump=False, request_key: str):
    if type(bump) is not bool:
        raise ValueError("bump must be true or false")
    if not isinstance(request_key, str) or not re.fullmatch(r"[A-Za-z0-9_-]{16,80}", request_key):
        raise ValueError("a unique request_key is required")
    owner = users.normalize_email(owner)
    request = normalize_request(ticker, sector=sector, mode="live")
    ticker, sector = request["ticker"], request["sector"]
    with database() as db:
        prior = db.execute("SELECT * FROM report_orders WHERE owner=? AND request_key=?", (owner, request_key)).fetchone()
        if prior:
            if (prior["ticker"], prior["sector"], bool(prior["bump"])) != (ticker, sector, bump):
                raise ValueError("request_key already belongs to another report")
            return dict(prior)
    payload = validated_report_payload(ticker, sector)
    cutoff = payload["data_quality"]["market_as_of"]
    order_id = uuid.uuid4().hex
    inputs = json.dumps(payload, separators=(",", ":"), allow_nan=False)
    with database() as db:
        db.execute("INSERT OR IGNORE INTO report_orders(id,owner,request_key,ticker,sector,bump,amount,created_at,as_of,inputs) VALUES(?,?,?,?,?,?,?,?,?,?)",
                   (order_id, owner, request_key, ticker, sector, int(bump), 900 + 500 * bump, time.time(), cutoff, inputs))
        saved = db.execute("SELECT * FROM report_orders WHERE owner=? AND request_key=?", (owner, request_key)).fetchone()
        if (saved["ticker"], saved["sector"], bool(saved["bump"])) != (ticker, sector, bump):
            raise ValueError("request_key already belongs to another report")
        return dict(saved)


def validated_report_payload(ticker: str, sector: str | None = None) -> dict:
    from app.charts_facade import run_fetch_all
    from free_engine.market_calendar import completed_session
    from app.quality import assess_charts_payload

    payload = run_fetch_all(ticker, sector)
    cutoff = (payload.get("data_quality") or {}).get("market_as_of")
    if cutoff != completed_session() or not assess_charts_payload(payload, ticker)["usable"]:
        raise ValueError("Current completed-session data is unavailable; no payment was started")
    replay = build_replay(payload)
    if len(replay) != 90 or any(row["score"] is None for row in replay):
        raise ValueError("90-session report history is unavailable; no payment was started")
    return payload


def attach_checkout(order_id: str, session: dict):
    if not session.get("id") or not session.get("url"):
        raise ValueError("Stripe did not return a checkout session")
    with database() as db:
        db.execute("UPDATE report_orders SET checkout_id=?, checkout_url=? WHERE id=? AND checkout_id IS NULL",
                   (session["id"], session["url"], order_id))


def _legacy_checkout_order(db, session: dict):
    """Bind paid checkouts created before ticker-specific report orders existed."""
    meta = session.get("metadata") or {}
    owner = users.normalize_email(meta.get("email") or "")
    bump = meta.get("bump") == "1"
    if (not owner or "@" not in owner or session.get("mode") != "payment"
            or session.get("payment_status") != "paid" or session.get("currency") != "usd"
            or session.get("amount_total") != 900 + 500 * bump
            or meta.get("product") != "quantradar_report"):
        raise ValueError("Legacy report payment is invalid")
    existing = db.execute("SELECT * FROM report_orders WHERE checkout_id=?", (session["id"],)).fetchone()
    if existing:
        return existing
    account = users.get_user(owner) or {}
    old_coupon = account.get("report_coupon")
    if old_coupon and db.execute("SELECT 1 FROM report_orders WHERE credit_code=? AND checkout_id IS NOT NULL", (old_coupon,)).fetchone():
        old_coupon = None
    claim = db.execute("SELECT id FROM report_orders WHERE owner=? AND legacy=1 AND checkout_id IS NULL LIMIT 1", (owner,)).fetchone()
    if claim:
        db.execute("UPDATE report_orders SET checkout_id=?,amount=?,payment_state='unpaid',bump=?,credit_code=?,credit_state=? WHERE id=?",
                   (session["id"], session["amount_total"], int(bump), old_coupon, "ready" if old_coupon else "pending", claim["id"]))
    else:
        db.execute("""INSERT INTO report_orders
            (id,owner,request_key,ticker,bump,amount,created_at,as_of,inputs,checkout_id,delivery_state,legacy,credit_code,credit_state)
            VALUES(?,?,?,'',?,?,?,'','{}',?,'awaiting_ticker',1,?,?)""",
            (uuid.uuid4().hex, owner, "legacy-" + session["id"], int(bump), session["amount_total"], time.time(), session["id"], old_coupon, "ready" if old_coupon else "pending"))
    return db.execute("SELECT * FROM report_orders WHERE checkout_id=?", (session["id"],)).fetchone()


def mark_report_paid(db, session: dict, *, paid_at: float | None = None) -> dict:
    meta = session.get("metadata") or {}
    order_id = meta.get("order_id")
    row = db.execute("SELECT * FROM report_orders WHERE id=? AND checkout_id=?", (order_id, session.get("id"))).fetchone()
    if not order_id:
        row = _legacy_checkout_order(db, session)
        order_id = row["id"]
    if not row:
        raise ValueError("No bound report order for this checkout")
    if (session.get("mode") != "payment" or session.get("payment_status") != "paid"
            or session.get("amount_total") != row["amount"] or session.get("currency") != row["currency"]
            or meta.get("product") != "quantradar_report" or meta.get("email") != row["owner"]):
        raise ValueError("Report payment does not match the saved order")
    intent = session.get("payment_intent")
    if not isinstance(intent, str) or not intent.startswith("pi_"):
        raise ValueError("Report payment intent missing")
    if row["payment_intent"] and row["payment_intent"] != intent:
        raise ValueError("This order is already bound to another payment")
    newly_paid = row["payment_intent"] is None
    if newly_paid:
        refund = db.execute("SELECT fully_refunded FROM payment_refunds WHERE payment_intent=?", (intent,)).fetchone()
        state = "refunded" if refund and refund[0] else "partially_refunded" if refund else "paid"
        delivery = "ready" if row["bundle"] else "queued" if row["ticker"] else "awaiting_ticker"
        db.execute("UPDATE report_orders SET payment_state=?, paid_at=?, payment_intent=?, delivery_state=?,credit_state=? WHERE id=?",
                   (state, paid_at if paid_at is not None else time.time(), intent, delivery,
                    ("revoking" if row["credit_code"] else "revoked") if refund else row["credit_state"], order_id))
    return {"ok": True, "action": "report_paid", "order_id": order_id, "email": row["owner"],
            "duplicate_payment": not newly_paid}


def record_refund(db, charge: dict) -> dict:
    intent = charge.get("payment_intent")
    if not isinstance(intent, str) or not intent.startswith("pi_"):
        return {"ok": True, "action": "ignored"}
    # Successful charge refunds are cumulative. Persist even when checkout has not arrived.
    db.execute("""INSERT INTO payment_refunds VALUES(?,?) ON CONFLICT(payment_intent) DO UPDATE
        SET fully_refunded=MAX(payment_refunds.fully_refunded,excluded.fully_refunded)""",
        (intent, int(bool(charge.get("refunded")))))
    full = db.execute("SELECT fully_refunded FROM payment_refunds WHERE payment_intent=?", (intent,)).fetchone()[0]
    db.execute("""UPDATE report_orders SET payment_state=?,credit_state=CASE WHEN credit_code IS NULL
        THEN 'revoked' ELSE 'revoking' END,retry_at=0 WHERE payment_intent=?""",
        ("refunded" if full else "partially_refunded", intent))
    return {"ok": True, "action": "refund_recorded"}


def report_summary(row) -> dict:
    return {key: row[key] for key in ("id", "ticker", "as_of", "bump", "amount", "currency", "created_at", "payment_state", "delivery_state", "error", "legacy", "credit_state", "paid_at")}


def list_reports(owner: str) -> list[dict]:
    ensure_legacy_claim(owner)
    with database() as db:
        return [report_summary(row) for row in db.execute("SELECT * FROM report_orders WHERE owner=? ORDER BY created_at DESC LIMIT 100", (users.normalize_email(owner),))]


def ensure_legacy_claim(owner: str):
    owner = users.normalize_email(owner)
    account = users.get_user(owner) or {}
    if not account.get("report_granted"):
        return
    with database() as db:
        db.execute("BEGIN IMMEDIATE")
        if db.execute("SELECT 1 FROM report_orders WHERE owner=? AND legacy=1 LIMIT 1", (owner,)).fetchone():
            return
        db.execute("""INSERT OR IGNORE INTO report_orders
            (id,owner,request_key,ticker,bump,amount,created_at,as_of,inputs,payment_state,delivery_state,legacy,credit_code,credit_state)
            VALUES(?,?,?,'',?,0,?,'','{}','paid','awaiting_ticker',1,?,?)""",
            (uuid.uuid4().hex, owner, "legacy-existing-grant", int(bool(account.get("bump_csv_priority"))), time.time(),
             account.get("report_coupon"), "ready" if account.get("report_coupon") else "legacy"))


def claim_legacy_report(owner: str, order_id: str, ticker: str) -> dict:
    owner = users.normalize_email(owner)
    request = normalize_request(ticker, mode="live")
    with database() as db:
        row = db.execute("SELECT * FROM report_orders WHERE id=? AND owner=? AND legacy=1", (order_id, owner)).fetchone()
        if not row:
            raise ValueError("Legacy report claim not found")
        if row["ticker"]:
            if row["ticker"] == request["ticker"]:
                return report_summary(row)
            raise ValueError("This legacy report has already been assigned")
        if row["payment_state"] not in {"paid", "partially_refunded"}:
            raise ValueError("This report is not paid")
    payload = validated_report_payload(request["ticker"])
    with database() as db:
        updated = db.execute("""UPDATE report_orders SET ticker=?,as_of=?,inputs=?,delivery_state='queued'
            WHERE id=? AND owner=? AND ticker='' AND payment_state IN ('paid','partially_refunded')""",
            (request["ticker"], payload["data_quality"]["market_as_of"], json.dumps(payload, allow_nan=False), order_id, owner))
        if updated.rowcount != 1:
            raise ValueError("This report has already been assigned")
        return report_summary(db.execute("SELECT * FROM report_orders WHERE id=?", (order_id,)).fetchone())


def report_credit(owner: str) -> str | None:
    from app.stripe_billing import coupon_redeemable
    with database() as db:
        rows = db.execute("""SELECT credit_code FROM report_orders WHERE owner=? AND payment_state='paid'
            AND credit_state='ready' AND (paid_at>? OR (legacy=1 AND paid_at IS NULL)) ORDER BY paid_at DESC""",
            (users.normalize_email(owner), time.time() - 7 * 86400)).fetchall()
        legacy = users.get_user(owner) or {}
        code = legacy.get("report_coupon") if legacy.get("report_granted") else None
        legacy_available = code and not db.execute("SELECT 1 FROM report_orders WHERE credit_code=?", (code,)).fetchone()
    for row in rows:
        if coupon_redeemable(row[0]):
            return row[0]
    if legacy_available and coupon_redeemable(str(code)):
        return str(code)
    return None


def get_report(owner: str, order_id: str) -> dict | None:
    with database() as db:
        row = db.execute("SELECT * FROM report_orders WHERE owner=? AND id=?", (users.normalize_email(owner), order_id)).fetchone()
        if not row:
            return None
        result = report_summary(row)
        if row["payment_state"] in {"paid", "partially_refunded"} and row["delivery_state"] == "ready":
            result["bundle"] = json.loads(row["bundle"])
        return result


def fulfill_next(*, now: float | None = None) -> bool:
    now = time.time() if now is None else now
    with database() as db:
        db.execute("BEGIN IMMEDIATE")
        row = db.execute("""SELECT * FROM report_orders
            WHERE ((payment_state IN ('paid','partially_refunded')
            AND (delivery_state IN ('queued','retrying','building') OR (delivery_state='ready' AND credit_state='pending')))
            OR credit_state='revoking')
            AND retry_at <= ? AND lease_until <= ?
            ORDER BY paid_at - CASE WHEN bump=1 THEN 60 ELSE 0 END, id LIMIT 1""", (now, now)).fetchone()
        if row is None:
            return False
        lease_token = uuid.uuid4().hex
        db.execute("UPDATE report_orders SET lease_until=?,lease_token=?, attempts=attempts+1 WHERE id=?", (now + 120, lease_token, row["id"]))
    if row["credit_state"] == "revoking":
        from app.stripe_billing import revoke_credit_coupon
        revoked = revoke_credit_coupon(row["credit_code"])
        if revoked and row["credit_code"]:
            from app.subscription_checkout import revoke_coupon_checkouts
            try:
                revoke_coupon_checkouts(row["credit_code"])
            except Exception:
                revoked = False
        with database() as db:
            db.execute("UPDATE report_orders SET credit_state=?,lease_until=0,lease_token=NULL,retry_at=? WHERE id=? AND lease_token=?",
                       ("revoked" if revoked else "revoking", now + 60, row["id"], lease_token))
        return True
    try:
        bundle = json.loads(row["bundle"]) if row["bundle"] else build_report_bundle(json.loads(row["inputs"]), include_csv=bool(row["bump"] or row["legacy"]))
        encoded = json.dumps(bundle, separators=(",", ":"), allow_nan=False)
        with database() as db:
            updated = db.execute("UPDATE report_orders SET bundle=?, delivery_state='ready', error=NULL WHERE id=? AND lease_token=?",
                                 (encoded, row["id"], lease_token))
            if not updated.rowcount:
                return True
    except Exception:
        with database() as db:
            db.execute("UPDATE report_orders SET delivery_state='retrying', lease_until=0,lease_token=NULL, retry_at=?, error=? WHERE id=? AND lease_token=?",
                       (now + min(3600, 30 * 2 ** min(row["attempts"], 7)), "Report delivery is retrying. Your payment is recorded.", row["id"], lease_token))
        return True
    # Credit failures never take away a completed download; keep the lease through issuance.
    with database() as db:
        current = db.execute("SELECT * FROM report_orders WHERE id=?", (row["id"],)).fetchone()
    if current["lease_token"] != lease_token:
        return True
    if current["credit_state"] == "pending" and current["payment_state"] == "paid":
        from app.stripe_billing import create_credit_coupon
        expired = now >= row["paid_at"] + 7 * 86400
        try:
            coupon = None if expired else create_credit_coupon(row["owner"], order_id=row["id"], paid_at=row["paid_at"])
        except Exception:
            coupon = None
        with database() as db:
            db.execute("""UPDATE report_orders SET credit_code=?,credit_state=CASE WHEN payment_state='paid'
                THEN ? ELSE ? END,retry_at=? WHERE id=? AND lease_token=?""",
                (coupon, "ready" if coupon else "expired" if expired else "pending",
                 "revoking" if coupon else "revoked", now + 60, row["id"], lease_token))
    with database() as db:
        db.execute("UPDATE report_orders SET lease_until=0,lease_token=NULL WHERE id=? AND lease_token=?", (row["id"], lease_token))
    return True


_worker_lock = threading.Lock()
_worker_started = False


def start_worker():
    global _worker_started
    with _worker_lock:
        if _worker_started:
            return
        _worker_started = True

    def work():
        from app import watch_reports
        next_schedule = 0
        while True:
            try:
                if fulfill_next():
                    continue
                if time.monotonic() >= next_schedule:
                    watch_reports.schedule_optins()
                    next_schedule = time.monotonic() + 60
                if watch_reports.process_next():
                    continue
            except Exception:
                pass
            time.sleep(2)

    threading.Thread(target=work, name="report-delivery", daemon=True).start()


def subscription_plan(owner: str, *, now: float | None = None) -> str | None:
    with database() as db:
        rows = db.execute("SELECT * FROM subscriptions WHERE owner=?", (users.normalize_email(owner),)).fetchall()
    if not rows:
        return None  # Legacy/manual accounts remain under the existing account policy.
    now = time.time() if now is None else now
    active = {row["plan"] for row in rows if row["status"] in {"active", "trialing"} and row["paid_through"] > now}
    return "portfolio_pro" if "portfolio_pro" in active else "pro" if "pro" in active else "free"


def has_open_subscription(owner: str) -> bool:
    with database() as db:
        return db.execute("SELECT 1 FROM subscriptions WHERE owner=? AND status NOT IN ('canceled','incomplete_expired') LIMIT 1",
                          (users.normalize_email(owner),)).fetchone() is not None
