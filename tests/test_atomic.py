"""Atomic unit tests for the engagement / users / billing layer.

Each test verifies exactly one behavior with hand-computed expectations —
no HTTP, no network, no engine subprocess. Pure functions and the users store
are isolated in temp dirs.
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

import app.users as users_mod  # noqa: E402
from app import engagement  # noqa: E402
from app import stripe_billing  # noqa: E402


class EngagementStoreFixture(unittest.TestCase):
    """Temp-dir isolation for engagement JSON stores."""

    def setUp(self) -> None:
        self._td = tempfile.TemporaryDirectory()
        d = Path(self._td.name)
        self._orig = (engagement.LEDGER_PATH, engagement.PRICE_CACHE_PATH, engagement.DIGEST_DIR, engagement.TODAY_CACHE_PATH)
        engagement.LEDGER_PATH = d / "ledger.json"
        engagement.PRICE_CACHE_PATH = d / "price_cache.json"
        engagement.DIGEST_DIR = d / "digest"
        engagement.TODAY_CACHE_PATH = d / "today_cache.json"

    def tearDown(self) -> None:
        (engagement.LEDGER_PATH, engagement.PRICE_CACHE_PATH, engagement.DIGEST_DIR, engagement.TODAY_CACHE_PATH) = self._orig
        self._td.cleanup()

    def _seed(self, entries, cache) -> None:
        engagement.LEDGER_PATH.write_text(json.dumps({"version": 1, "entries": entries}), encoding="utf-8")
        engagement.PRICE_CACHE_PATH.write_text(json.dumps(cache), encoding="utf-8")


class AvoidanceAtoms(EngagementStoreFixture):
    def test_exact_threshold_5pct_counts(self) -> None:
        # drop of exactly 5.0 is >= threshold → counts
        self._seed(
            [{"ticker": "T", "ts": time.time() - 10, "action": "NO", "close": 100.0, "email": None}],
            {"T": {"ts": time.time(), "close": 95.0}},
        )
        ev = engagement.avoidance_events(None)
        self.assertEqual(len(ev), 1)
        self.assertEqual(ev[0]["drop_pct"], 5.0)

    def test_drop_4_9pct_excluded(self) -> None:
        self._seed(
            [{"ticker": "T", "ts": time.time() - 10, "action": "NO", "close": 100.0, "email": None}],
            {"T": {"ts": time.time(), "close": 95.1}},
        )
        self.assertEqual(engagement.avoidance_events(None), [])

    def test_price_rise_never_counts(self) -> None:
        self._seed(
            [{"ticker": "T", "ts": time.time() - 10, "action": "NO", "close": 100.0, "email": None}],
            {"T": {"ts": time.time(), "close": 130.0}},
        )
        self.assertEqual(engagement.avoidance_events(None), [])

    def test_wait_action_never_counts(self) -> None:
        self._seed(
            [{"ticker": "T", "ts": time.time() - 10, "action": "WAIT", "close": 100.0, "email": None}],
            {"T": {"ts": time.time(), "close": 50.0}},
        )
        self.assertEqual(engagement.avoidance_events(None), [])

    def test_zero_then_close_skipped(self) -> None:
        self._seed(
            [{"ticker": "T", "ts": time.time() - 10, "action": "NO", "close": 0.0, "email": None}],
            {"T": {"ts": time.time(), "close": 1.0}},
        )
        self.assertEqual(engagement.avoidance_events(None), [])

    def test_missing_cache_entry_skipped(self) -> None:
        self._seed(
            [{"ticker": "T", "ts": time.time() - 10, "action": "NO", "close": 100.0, "email": None}],
            {},
        )
        self.assertEqual(engagement.avoidance_events(None), [])

    def test_cache_older_than_ttl_excluded(self) -> None:
        stale_ts = time.time() - engagement._PRICE_TTL_SEC - 10
        self._seed(
            [{"ticker": "T", "ts": time.time() - 10, "action": "NO", "close": 100.0, "email": None}],
            {"T": {"ts": stale_ts, "close": 90.0}},
        )
        self.assertEqual(engagement.avoidance_events(None), [])

    def test_limit_parameter(self) -> None:
        entries = [
            {"ticker": f"T{i}", "ts": time.time() - 10, "action": "NO", "close": 100.0, "email": None}
            for i in range(8)
        ]
        cache = {f"T{i}": {"ts": time.time(), "close": 90.0} for i in range(8)}
        self._seed(entries, cache)
        self.assertEqual(len(engagement.avoidance_events(None, limit=3)), 3)
        self.assertEqual(len(engagement.avoidance_events(None, limit=100)), 8)

    def test_most_recent_scans_first(self) -> None:
        self._seed(
            [
                {"ticker": "OLD", "ts": time.time() - 5000, "action": "NO", "close": 100.0, "email": None},
                {"ticker": "NEW", "ts": time.time() - 10, "action": "NO", "close": 100.0, "email": None},
            ],
            {"OLD": {"ts": time.time(), "close": 90.0}, "NEW": {"ts": time.time(), "close": 90.0}},
        )
        ev = engagement.avoidance_events(None)
        self.assertEqual(ev[0]["ticker"], "NEW")

    def test_corrupt_cache_file_yields_empty(self) -> None:
        engagement.LEDGER_PATH.write_text("{not json", encoding="utf-8")
        engagement.PRICE_CACHE_PATH.write_text("{not json", encoding="utf-8")
        self.assertEqual(engagement.avoidance_events(None), [])

    def test_drop_pct_rounded_to_one_decimal(self) -> None:
        self._seed(
            [{"ticker": "T", "ts": time.time() - 10, "action": "NO", "close": 100.0, "email": None}],
            {"T": {"ts": time.time(), "close": 93.3333}},
        )
        ev = engagement.avoidance_events(None)
        self.assertEqual(ev[0]["drop_pct"], 6.7)


class RecordScanAtoms(EngagementStoreFixture):
    def test_failed_result_not_recorded(self) -> None:
        engagement.record_scan("T", {"ok": False}, None)
        time.sleep(0.15)
        self.assertFalse(engagement.LEDGER_PATH.is_file())

    def test_demo_result_not_recorded_by_caller_convention(self) -> None:
        # The server skips demos before calling; record_scan itself only
        # checks ok — verify it writes when called directly with ok=True.
        with mock.patch.object(engagement, "_current_close", return_value=10.0):
            engagement.record_scan("T", {"ok": True, "primary": {"action": "SETUP"}, "score": {"final": 70}}, None)
            deadline = time.time() + 5
            while time.time() < deadline and not engagement.LEDGER_PATH.is_file():
                time.sleep(0.05)
        data = json.loads(engagement.LEDGER_PATH.read_text(encoding="utf-8"))
        self.assertEqual(data["entries"][0]["action"], "SETUP")
        self.assertEqual(data["entries"][0]["close"], 10.0)
        self.assertIsNone(data["entries"][0]["email"])

    def test_close_fetch_failure_skips_entry(self) -> None:
        with mock.patch.object(engagement, "_current_close", return_value=None):
            engagement.record_scan("T", {"ok": True, "primary": {"action": "NO"}}, None)
            time.sleep(0.4)
        self.assertFalse(engagement.LEDGER_PATH.is_file())

    def test_ledger_capped_at_2000(self) -> None:
        big = [
            {"ticker": f"T{i}", "ts": time.time(), "action": "NO", "close": 1.0, "email": None}
            for i in range(2050)
        ]
        engagement.LEDGER_PATH.write_text(json.dumps({"version": 1, "entries": big}), encoding="utf-8")
        with mock.patch.object(engagement, "_current_close", return_value=2.0):
            engagement.record_scan("CAP", {"ok": True, "primary": {"action": "NO"}}, None)
            deadline = time.time() + 5
            while time.time() < deadline:
                if engagement.LEDGER_PATH.is_file():
                    data = json.loads(engagement.LEDGER_PATH.read_text(encoding="utf-8"))
                    if len(data["entries"]) <= engagement._LEDGER_CAP:
                        break
                time.sleep(0.05)
        data = json.loads(engagement.LEDGER_PATH.read_text(encoding="utf-8"))
        self.assertEqual(len(data["entries"]), 2000)
        self.assertEqual(data["entries"][-1]["ticker"], "CAP")


class RecentClosesAtoms(EngagementStoreFixture):
    def _write_cache(self, src: str, ticker: str, rows: list) -> None:
        engine_dir = engagement._engine_dir()
        cache_dir = engine_dir / ".cache"
        cache_dir.mkdir(parents=True, exist_ok=True)
        safe = "".join(ch if ch.isalnum() else "_" for ch in f"{src}:{ticker}")
        (cache_dir / f"{safe}.json").write_text(
            json.dumps({"t": time.time(), "v": rows}), encoding="utf-8"
        )

    def test_cold_cache_returns_empty(self) -> None:
        self.assertEqual(engagement.recent_closes("NOSUCH"), [])

    def test_warm_cache_returns_last_n(self) -> None:
        rows = [["2026-08-0%d" % (i + 1), 100.0 + i, 1000.0] for i in range(10)]
        self._write_cache("yahoo_q1", "WARM", rows)
        got = engagement.recent_closes("WARM", n=5)
        self.assertEqual(got, [105.0, 106.0, 107.0, 108.0, 109.0])

    def test_shorter_cache_than_n_returns_empty(self) -> None:
        rows = [["2026-08-0%d" % (i + 1), 100.0 + i, 1000.0] for i in range(3)]
        self._write_cache("yahoo_q1", "SHORT", rows)
        self.assertEqual(engagement.recent_closes("SHORT", n=5), [])


class WatchlistAtoms(unittest.TestCase):
    def setUp(self) -> None:
        self._td = tempfile.TemporaryDirectory()
        self._orig = users_mod.USERS_PATH
        users_mod.USERS_PATH = Path(self._td.name) / "users.json"
        os.environ["ALLOW_REGISTER"] = "1"
        users_mod.register_user("w@test.local", "hunter2secret")

    def tearDown(self) -> None:
        users_mod.USERS_PATH = self._orig
        self._td.cleanup()

    def test_invalid_tickers_rejected(self) -> None:
        for bad in ("", "   ", "A B", "T;DROP", "!!!!"):
            ok, why, _ = engagement.add_watch("w@test.local", bad)
            self.assertFalse(ok, f"should reject {bad!r}")
            self.assertEqual(why, "invalid ticker")

    def test_lowercase_normalized_to_upper(self) -> None:
        ok, why, wl = engagement.add_watch("w@test.local", "nvda")
        self.assertTrue(ok)
        self.assertEqual(wl, ["NVDA"])

    def test_duplicate_add_idempotent(self) -> None:
        engagement.add_watch("w@test.local", "NVDA")
        ok, why, wl = engagement.add_watch("w@test.local", "NVDA")
        self.assertTrue(ok)
        self.assertEqual(why, "already watching")
        self.assertEqual(wl, ["NVDA"])

    def test_free_limit_is_one(self) -> None:
        self.assertEqual(engagement.watch_limit("w@test.local"), 1)
        engagement.add_watch("w@test.local", "NVDA")
        ok, why, wl = engagement.add_watch("w@test.local", "AMD")
        self.assertFalse(ok)
        self.assertEqual(why, "limit")
        self.assertEqual(wl, ["NVDA"])

    def test_pro_limit_is_ten(self) -> None:
        users_mod.set_plan("w@test.local", "pro")
        self.assertEqual(engagement.watch_limit("w@test.local"), 10)
        tickers = ["A1", "B2", "C3", "D4", "E5", "F6", "G7", "H8", "I9", "J0"]
        for t in tickers:
            ok, why, _ = engagement.add_watch("w@test.local", t)
            self.assertTrue(ok, (t, why))
        # 10 full — the 11th must hit the cap
        ok, why, wl = engagement.add_watch("w@test.local", "K1")
        self.assertFalse(ok)
        self.assertEqual(why, "limit")
        self.assertEqual(len(wl), 10)

    def test_remove_missing_ticker_no_error(self) -> None:
        wl = engagement.remove_watch("w@test.local", "NOPE")
        self.assertEqual(wl, [])

    def test_remove_then_readd_slot_freed(self) -> None:
        engagement.add_watch("w@test.local", "NVDA")
        engagement.remove_watch("w@test.local", "NVDA")
        ok, why, wl = engagement.add_watch("w@test.local", "AMD")
        self.assertTrue(ok)
        self.assertEqual(wl, ["AMD"])

    def test_unknown_account_returns_error(self) -> None:
        ok, why, wl = engagement.add_watch("ghost@test.local", "NVDA")
        self.assertFalse(ok)
        self.assertEqual(why, "no account")
        self.assertEqual(wl, [])
        self.assertEqual(engagement.get_watchlist("ghost@test.local"), [])


class DigestAtoms(unittest.TestCase):
    def setUp(self) -> None:
        self._td = tempfile.TemporaryDirectory()
        self._orig = users_mod.USERS_PATH
        users_mod.USERS_PATH = Path(self._td.name) / "users.json"
        os.environ["ALLOW_REGISTER"] = "1"
        self._orig_smtp = {k: os.environ.get(k) for k in ("SMTP_HOST", "SMTP_USER")}
        os.environ.pop("SMTP_HOST", None)
        os.environ.pop("SMTP_USER", None)

    def tearDown(self) -> None:
        users_mod.USERS_PATH = self._orig
        for k, v in self._orig_smtp.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        self._td.cleanup()

    def test_optin_defaults_false(self) -> None:
        users_mod.register_user("d@test.local", "hunter2secret")
        self.assertFalse(users_mod.get_user("d@test.local").get("daily_digest"))

    def test_optin_roundtrip(self) -> None:
        users_mod.register_user("d@test.local", "hunter2secret")
        engagement.set_digest_optin("d@test.local", True)
        self.assertTrue(users_mod.get_user("d@test.local").get("daily_digest"))
        engagement.set_digest_optin("d@test.local", False)
        self.assertFalse(users_mod.get_user("d@test.local").get("daily_digest"))

    def test_optins_only_returns_subscribed(self) -> None:
        users_mod.register_user("a@test.local", "hunter2secret")
        users_mod.register_user("b@test.local", "hunter2secret")
        engagement.set_digest_optin("a@test.local", True)
        rows = engagement.digest_optins()
        self.assertEqual([r["email"] for r in rows], ["a@test.local"])

    def test_smtp_configured_false_without_keys(self) -> None:
        self.assertFalse(engagement.smtp_configured())

    def test_smtp_configured_true_with_keys(self) -> None:
        os.environ["SMTP_HOST"] = "smtp.example.com"
        os.environ["SMTP_USER"] = "u"
        self.assertTrue(engagement.smtp_configured())


class UsersEntitlementAtoms(unittest.TestCase):
    def setUp(self) -> None:
        self._td = tempfile.TemporaryDirectory()
        self._orig = users_mod.USERS_PATH
        users_mod.USERS_PATH = Path(self._td.name) / "users.json"
        os.environ["ALLOW_REGISTER"] = "1"
        users_mod.register_user("e@test.local", "hunter2secret")

    def tearDown(self) -> None:
        users_mod.USERS_PATH = self._orig
        self._td.cleanup()

    def test_public_user_entitlement_defaults(self) -> None:
        u = users_mod.public_user(users_mod.get_user("e@test.local"))
        self.assertEqual(u["watchlist"], [])
        self.assertFalse(u["report_granted"])
        self.assertFalse(u["bump_csv_priority"])
        self.assertFalse(u["daily_digest"])
        self.assertIsNone(u["report_coupon"])

    def test_grant_report_sets_flags(self) -> None:
        users_mod.grant_report("e@test.local")
        u = users_mod.get_user("e@test.local")
        self.assertTrue(u["report_granted"])
        self.assertIn("report_granted_at", u)
        self.assertFalse(u.get("bump_csv_priority", False))

    def test_grant_report_with_bump(self) -> None:
        users_mod.grant_report("e@test.local", bump=True)
        u = users_mod.get_user("e@test.local")
        self.assertTrue(u["report_granted"])
        self.assertTrue(u["bump_csv_priority"])

    def test_grant_report_unknown_account_raises(self) -> None:
        with self.assertRaises(ValueError):
            users_mod.grant_report("ghost@test.local")

    def test_set_report_coupon_stored(self) -> None:
        users_mod.set_report_coupon("e@test.local", "coupon_abc")
        u = users_mod.get_user("e@test.local")
        self.assertEqual(u["report_coupon"], "coupon_abc")

    def test_set_report_coupon_clears(self) -> None:
        users_mod.set_report_coupon("e@test.local", "coupon_abc")
        users_mod.set_report_coupon("e@test.local", None)
        u = users_mod.get_user("e@test.local")
        self.assertIsNone(u["report_coupon"])

    def test_grant_report_does_not_clobber_plan(self) -> None:
        users_mod.set_plan("e@test.local", "pro")
        users_mod.grant_report("e@test.local")
        u = users_mod.get_user("e@test.local")
        self.assertEqual(u["plan"], "pro")

    def test_public_engagement_shape(self) -> None:
        pub = engagement.public_engagement({"email": "e@test.local"})
        self.assertEqual(pub["watchlist"], [])
        self.assertEqual(pub["watchlist_limit"], 1)
        self.assertFalse(pub["report_granted"])

    def test_public_engagement_unknown_email_empty(self) -> None:
        self.assertEqual(engagement.public_engagement({"email": "ghost@test.local"}), {})
        self.assertEqual(engagement.public_engagement({}), {})


class StripeReportAtoms(unittest.TestCase):
    """Unit-level atoms for the $9 report checkout path (no network)."""

    def setUp(self) -> None:
        self._env_orig = {
            k: os.environ.get(k)
            for k in (
                "STRIPE_PRICE_ID_REPORT",
                "QUANTRADAR_STRIPE_PRICE_ID_REPORT",
                "STRIPE_PRICE_ID_BUMP",
                "QUANTRADAR_STRIPE_PRICE_ID_BUMP",
                "QUANTRADAR_STRIPE_SECRET_KEY",
            )
        }
        for k in self._env_orig:
            os.environ.pop(k, None)

    def tearDown(self) -> None:
        for k, v in self._env_orig.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v

    def test_price_id_report_env_resolution(self) -> None:
        self.assertEqual(stripe_billing.price_id_report(), "")
        os.environ["STRIPE_PRICE_ID_REPORT"] = "price_r1"
        self.assertEqual(stripe_billing.price_id_report(), "price_r1")
        os.environ.pop("STRIPE_PRICE_ID_REPORT")
        os.environ["QUANTRADAR_STRIPE_PRICE_ID_REPORT"] = "price_r2"
        self.assertEqual(stripe_billing.price_id_report(), "price_r2")

    def test_price_id_bump_env_resolution(self) -> None:
        self.assertEqual(stripe_billing.price_id_bump(), "")
        os.environ["STRIPE_PRICE_ID_BUMP"] = "price_b1"
        self.assertEqual(stripe_billing.price_id_bump(), "price_b1")

    def test_report_checkout_requires_stripe(self) -> None:
        with self.assertRaises(RuntimeError):
            stripe_billing.create_report_checkout(customer_email="x@y.com")

    def test_report_checkout_requires_report_price(self) -> None:
        os.environ["QUANTRADAR_STRIPE_SECRET_KEY"] = "sk_test_fake"
        with self.assertRaises(RuntimeError) as ctx:
            stripe_billing.create_report_checkout(customer_email="x@y.com")
        self.assertIn("STRIPE_PRICE_ID_REPORT", str(ctx.exception))

    def test_credit_coupon_without_key_returns_none(self) -> None:
        self.assertIsNone(stripe_billing.create_credit_coupon("x@y.com"))

    def test_pro_checkout_with_credit_requires_stripe(self) -> None:
        with self.assertRaises(RuntimeError):
            stripe_billing.pro_checkout_with_credit(
                customer_email="x@y.com", interval="monthly", coupon_id=None
            )

    def test_webhook_report_branch_grants_and_mints(self) -> None:
        """checkout.session.completed with metadata.product=quantradar_report
        must grant the report (never elevate plan) and mint the $9 credit."""
        users_td = tempfile.TemporaryDirectory()
        orig = users_mod.USERS_PATH
        users_mod.USERS_PATH = Path(users_td.name) / "users.json"
        os.environ["ALLOW_REGISTER"] = "1"
        try:
            users_mod.register_user("buyer@test.local", "hunter2secret")
            event = {
                "type": "checkout.session.completed",
                "data": {
                    "object": {
                        "customer_email": "buyer@test.local",
                        "payment_status": "paid",
                        "metadata": {"product": "quantradar_report", "bump": "1", "email": "buyer@test.local"},
                    }
                },
            }
            with mock.patch.object(stripe_billing, "create_credit_coupon", return_value="cpn_test") as mint:
                res = stripe_billing.apply_webhook_event(event)
            self.assertTrue(res["ok"], res)
            self.assertEqual(res["action"], "report_granted")
            mint.assert_called_once_with("buyer@test.local")
            u = users_mod.get_user("buyer@test.local")
            self.assertTrue(u["report_granted"])
            self.assertTrue(u["bump_csv_priority"])
            self.assertEqual(u["report_coupon"], "cpn_test")
            # CRITICAL: buying the $9 report must NOT grant Pro
            self.assertEqual(u["plan"], "free")
        finally:
            users_mod.USERS_PATH = orig
            users_td.cleanup()

    def test_webhook_pro_branch_still_sets_pro(self) -> None:
        """Regression: pro checkout still elevates plan (metadata.product=pro)."""
        users_td = tempfile.TemporaryDirectory()
        orig = users_mod.USERS_PATH
        users_mod.USERS_PATH = Path(users_td.name) / "users.json"
        os.environ["ALLOW_REGISTER"] = "1"
        try:
            event = {
                "type": "checkout.session.completed",
                "data": {
                    "object": {
                        "customer_email": "sub@test.local",
                        "payment_status": "paid",
                        "metadata": {"product": "quantradar_pro", "email": "sub@test.local"},
                    }
                },
            }
            res = stripe_billing.apply_webhook_event(event)
            self.assertTrue(res["ok"], res)
            self.assertEqual(res["action"], "plan_pro")
            self.assertEqual(users_mod.resolve_plan("sub@test.local"), "pro")
        finally:
            users_mod.USERS_PATH = orig
            users_td.cleanup()

    def test_webhook_unpaid_report_not_granted(self) -> None:
        users_td = tempfile.TemporaryDirectory()
        orig = users_mod.USERS_PATH
        users_mod.USERS_PATH = Path(users_td.name) / "users.json"
        os.environ["ALLOW_REGISTER"] = "1"
        try:
            users_mod.register_user("np@test.local", "hunter2secret")
            event = {
                "type": "checkout.session.completed",
                "data": {
                    "object": {
                        "customer_email": "np@test.local",
                        "payment_status": "unpaid",
                        "metadata": {"product": "quantradar_report"},
                    }
                },
            }
            res = stripe_billing.apply_webhook_event(event)
            self.assertFalse(res["ok"])
            self.assertEqual(res["error"], "not_paid")
            self.assertFalse(users_mod.get_user("np@test.local").get("report_granted"))
        finally:
            users_mod.USERS_PATH = orig
            users_td.cleanup()


class _FakeResp:
    def __init__(self, obj: dict) -> None:
        self._obj = obj

    def read(self) -> bytes:
        return json.dumps(self._obj).encode()

    def __enter__(self) -> "_FakeResp":
        return self

    def __exit__(self, *args: object) -> bool:
        return False


class CouponDegradeAtoms(unittest.TestCase):
    """The $9->Pro credit coupon can die (expire/redeemed/deleted) between mint
    and checkout. pro_checkout_with_credit must degrade to allow_promotion_codes
    instead of crashing the checkout session creation."""

    def setUp(self) -> None:
        self._env_orig = {
            k: os.environ.get(k)
            for k in (
                "QUANTRADAR_STRIPE_SECRET_KEY",
                "STRIPE_SECRET_KEY",
                "STRIPE_PRICE_ID_MONTHLY",
                "QUANTRADAR_STRIPE_PRICE_ID_MONTHLY",
                "STRIPE_PRICE_ID_YEARLY",
                "STRIPE_PRICE_ID",
                "PUBLIC_BASE_URL",
            )
        }
        for k in self._env_orig:
            os.environ.pop(k, None)
        os.environ["QUANTRADAR_STRIPE_SECRET_KEY"] = "sk_test_fake"
        os.environ["STRIPE_PRICE_ID_MONTHLY"] = "price_m1"
        os.environ["PUBLIC_BASE_URL"] = "http://127.0.0.1:8765"

    def tearDown(self) -> None:
        for k, v in self._env_orig.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v

    def _patch_urlopen(self, coupon_obj: dict | Exception | None):
        captured: list = []

        def fake(req, timeout=None):  # noqa: ANN001
            captured.append(req)
            url = req.full_url
            if "/checkout/sessions" in url:
                return _FakeResp({"id": "cs_test_1", "url": "https://checkout.stripe.com/x"})
            if "/v1/coupons/" in url:
                if isinstance(coupon_obj, Exception):
                    raise coupon_obj
                return _FakeResp(coupon_obj or {})
            raise AssertionError("unexpected url: " + url)

        return mock.patch.object(stripe_billing.urllib.request, "urlopen", side_effect=fake), captured

    def _post_body(self, captured: list) -> dict:
        req = [r for r in captured if "/checkout/sessions" in r.full_url][-1]
        from urllib.parse import parse_qs

        return {k: v[0] for k, v in parse_qs(req.data.decode()).items()}

    def test_coupon_redeemable_no_secret_false(self) -> None:
        os.environ.pop("QUANTRADAR_STRIPE_SECRET_KEY")
        os.environ.pop("STRIPE_SECRET_KEY", None)
        self.assertFalse(stripe_billing.coupon_redeemable("cpn_x"))

    def test_coupon_redeemable_no_id_false(self) -> None:
        self.assertFalse(stripe_billing.coupon_redeemable(None))
        self.assertFalse(stripe_billing.coupon_redeemable("   "))

    def test_coupon_redeemable_expired_false(self) -> None:
        patcher, _ = self._patch_urlopen(
            {"id": "cpn_x", "valid": True, "redeem_by": int(time.time()) - 10, "max_redemptions": 1, "times_redeemed": 0}
        )
        with patcher:
            self.assertFalse(stripe_billing.coupon_redeemable("cpn_x"))

    def test_coupon_redeemable_invalid_flag_false(self) -> None:
        patcher, _ = self._patch_urlopen({"id": "cpn_x", "valid": False})
        with patcher:
            self.assertFalse(stripe_billing.coupon_redeemable("cpn_x"))

    def test_coupon_redeemable_exhausted_false(self) -> None:
        patcher, _ = self._patch_urlopen(
            {"id": "cpn_x", "valid": True, "redeem_by": int(time.time()) + 3600, "max_redemptions": 1, "times_redeemed": 1}
        )
        with patcher:
            self.assertFalse(stripe_billing.coupon_redeemable("cpn_x"))

    def test_coupon_redeemable_network_error_false(self) -> None:
        patcher, _ = self._patch_urlopen(RuntimeError("boom"))
        with patcher:
            self.assertFalse(stripe_billing.coupon_redeemable("cpn_x"))

    def test_coupon_redeemable_healthy_true(self) -> None:
        patcher, _ = self._patch_urlopen(
            {"id": "cpn_x", "valid": True, "redeem_by": int(time.time()) + 3600, "max_redemptions": 1, "times_redeemed": 0}
        )
        with patcher:
            self.assertTrue(stripe_billing.coupon_redeemable("cpn_x"))

    def test_pro_checkout_applies_valid_coupon(self) -> None:
        with mock.patch.object(stripe_billing, "coupon_redeemable", return_value=True):
            patcher, captured = self._patch_urlopen(None)
            with patcher:
                res = stripe_billing.pro_checkout_with_credit(
                    customer_email="b@t.com", interval="monthly", coupon_id="cpn_live"
                )
        body = self._post_body(captured)
        self.assertEqual(res["id"], "cs_test_1")
        self.assertEqual(body["discounts[0][coupon]"], "cpn_live")
        self.assertNotIn("allow_promotion_codes", body)
        self.assertEqual(body["metadata[product]"], "quantradar_pro")

    def test_pro_checkout_degrades_on_dead_coupon(self) -> None:
        with mock.patch.object(stripe_billing, "coupon_redeemable", return_value=False):
            patcher, captured = self._patch_urlopen(None)
            with patcher:
                res = stripe_billing.pro_checkout_with_credit(
                    customer_email="b@t.com", interval="monthly", coupon_id="cpn_dead"
                )
        body = self._post_body(captured)
        self.assertEqual(res["id"], "cs_test_1")
        self.assertNotIn("discounts[0][coupon]", body)
        self.assertEqual(body["allow_promotion_codes"], "true")

    def test_pro_checkout_none_coupon_allows_promo(self) -> None:
        patcher, captured = self._patch_urlopen(None)
        with patcher:
            stripe_billing.pro_checkout_with_credit(
                customer_email="b@t.com", interval="monthly", coupon_id=None
            )
        body = self._post_body(captured)
        self.assertEqual(body["allow_promotion_codes"], "true")
        self.assertNotIn("discounts[0][coupon]", body)

    def test_pro_checkout_yearly_interval_metadata(self) -> None:
        os.environ["STRIPE_PRICE_ID_YEARLY"] = "price_y1"
        patcher, captured = self._patch_urlopen(None)
        with patcher:
            res = stripe_billing.pro_checkout_with_credit(
                customer_email="b@t.com", interval="yearly", coupon_id=None
            )
        body = self._post_body(captured)
        self.assertEqual(res["interval"], "yearly")
        self.assertEqual(body["metadata[interval]"], "yearly")
        self.assertEqual(body["line_items[0][price]"], "price_y1")


if __name__ == "__main__":
    unittest.main()
