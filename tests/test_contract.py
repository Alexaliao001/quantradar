"""Drive real contract mapping + validation against charts fixture."""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from app.charts_facade import analyze, find_analysis_artifact, load_charts_json  # noqa: E402
from app.contract import (  # noqa: E402
    map_charts_payload,
    normalize_request,
    validate_response,
)


class ContractTests(unittest.TestCase):
    def test_normalize_ticker(self) -> None:
        req = normalize_request("intc", sector="smh")
        self.assertEqual(req["ticker"], "INTC")
        self.assertEqual(req["sector"], "SMH")

    def test_normalize_rejects_empty(self) -> None:
        with self.assertRaises(ValueError):
            normalize_request("")

    def test_map_real_fixture(self) -> None:
        path = find_analysis_artifact("INTC")
        self.assertIsNotNone(path, "INTC fixture or charts artifact required")
        assert path is not None
        payload = load_charts_json(path)
        # Must look like charts output, not a hand-made score sheet
        self.assertIn("mechanical_scores", payload)
        self.assertIn("data_quality", payload)
        mapped = map_charts_payload(payload, mode="artifact", analysis_json_path=str(path))
        errs = validate_response(mapped)
        self.assertEqual(errs, [], msg=errs)
        self.assertEqual(mapped["ticker"], "INTC")
        self.assertIsInstance(mapped["score"]["final"], (int, float))
        self.assertTrue(mapped["gate"].get("signal") or mapped["gate"].get("state_code"))
        self.assertIn("charts", mapped["artifacts"])
        self.assertIsInstance(mapped["sources"], list)
        self.assertIsInstance(mapped["warnings"], list)
        # Score must equal charts mechanical_scores.final_score (no recompute)
        self.assertEqual(
            float(mapped["score"]["final"]),
            float(payload["mechanical_scores"]["final_score"]),
        )

    def test_analyze_artifact_path(self) -> None:
        result = analyze("INTC", mode="artifact")
        self.assertTrue(result.get("ok"), result)
        self.assertEqual(validate_response(result), [])
        self.assertEqual(result["meta"]["mode"], "artifact")
        self.assertGreater(len(result["ticker"]), 0)
        self.assertIsNotNone(result["score"]["final"])


class SchemaSampleTests(unittest.TestCase):
    def test_sample_file_valid(self) -> None:
        sample = REPO / "schemas" / "samples" / "engine_response.sample.json"
        if not sample.is_file():
            # generate on the fly from fixture (same code path as script)
            result = analyze("INTC", mode="artifact")
            sample.parent.mkdir(parents=True, exist_ok=True)
            sample.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        obj = json.loads(sample.read_text(encoding="utf-8"))
        self.assertEqual(validate_response(obj), [])


class NoManusAuthTests(unittest.TestCase):
    """Product shell must never offer Manus login."""

    def test_auth_helpers(self) -> None:
        from app.server import health_payload, is_manus_auth_path, manus_login_disabled_payload

        self.assertTrue(is_manus_auth_path("/api/oauth/callback"))
        self.assertTrue(is_manus_auth_path("/login"))
        self.assertFalse(is_manus_auth_path("/api/analyze"))
        self.assertFalse(is_manus_auth_path("/health"))
        body = manus_login_disabled_payload()
        self.assertEqual(body["error"], "manus_login_disabled")
        self.assertIs(body["manus_login"], False)
        h = health_payload()
        self.assertEqual(h["auth"], "none")
        self.assertIs(h["manus_login"], False)
        self.assertIs(h["guest_access"], True)

    def test_source_has_no_manus_auth_urls(self) -> None:
        # Code/UI must not construct a Manus login URL or OAuth redirect
        forbidden = (
            "https://manus.im/app-auth",
            "manus.im/app-auth?",
            "type=signIn",
            "/api/oauth/callback?code=",
        )
        for path in list((REPO / "app").rglob("*.py")) + [REPO / "static" / "index.html"]:
            text = path.read_text(encoding="utf-8")
            for token in forbidden:
                self.assertNotIn(token, text, msg=f"{path} embeds {token!r}")
        ui = (REPO / "static" / "index.html").read_text(encoding="utf-8")
        self.assertNotIn("href=\"https://manus.im", ui)
        self.assertNotIn("app-auth", ui)
        # No login button / OAuth start
        self.assertNotIn("Sign in with Manus", ui)
        self.assertNotIn("用 Manus 登录", ui)


if __name__ == "__main__":
    unittest.main()
