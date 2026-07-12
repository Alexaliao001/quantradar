"""P0 trust gates: no fake buys, symbol aliases, volume/options honesty."""

from __future__ import annotations

import copy
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
from app.quality import (  # noqa: E402
    assess_charts_payload,
    canonicalize_ticker,
    fail_response,
)


class SymbolTests(unittest.TestCase):
    def test_brk_alias(self) -> None:
        self.assertEqual(canonicalize_ticker("brk.b"), "BRK-B")
        req = normalize_request("BRK.B")
        self.assertEqual(req["ticker"], "BRK-B")

    def test_blocks_placeholder(self) -> None:
        with self.assertRaises(ValueError):
            normalize_request("XXXX")
        with self.assertRaises(ValueError):
            normalize_request("asdf")


class NoFakeBuyTests(unittest.TestCase):
    def test_unknown_ticker_fails_closed(self) -> None:
        # Must match ticker regex but have no charts artifact
        result = analyze("NOREALTK", mode="artifact")
        self.assertFalse(result.get("ok"), result)
        self.assertEqual(result.get("error"), "artifact_not_found")
        self.assertTrue((result.get("score") or {}).get("withheld"))
        self.assertIsNone((result.get("score") or {}).get("final"))
        self.assertEqual((result.get("gate") or {}).get("signal"), "NO")
        self.assertEqual((result.get("primary") or {}).get("action"), "NO")
        self.assertEqual(validate_response(result), [])

    def test_empty_payload_not_usable(self) -> None:
        q = assess_charts_payload({}, "INTC")
        self.assertFalse(q["usable"])
        self.assertEqual(q["error"], "no_data")

    def test_missing_mechanical_scores(self) -> None:
        q = assess_charts_payload({"ticker": "INTC", "data_quality": {}}, "INTC")
        self.assertFalse(q["usable"])

    def test_volume_zero_blocks_narrative(self) -> None:
        path = find_analysis_artifact("INTC")
        self.assertIsNotNone(path)
        assert path is not None
        payload = load_charts_json(path)
        payload = copy.deepcopy(payload)
        payload["volumeAnalysis"] = {
            "avgVolume20": 0,
            "currentVolume": 0,
            "validation": {"isValid": True, "volumeScore": 100, "reason": "fake"},
        }
        mapped = map_charts_payload(payload, mode="artifact")
        self.assertTrue(mapped["ok"])
        self.assertFalse(mapped["data_quality"]["volume_narrative_allowed"])
        self.assertTrue(mapped["degraded"])
        self.assertTrue(any("volume" in w.lower() for w in mapped["warnings"]))

    def test_simulated_options_flag(self) -> None:
        path = find_analysis_artifact("INTC")
        assert path is not None
        payload = copy.deepcopy(load_charts_json(path))
        payload["optionChainDataSource"] = "simulated"
        payload["data_quality"] = dict(payload.get("data_quality") or {})
        payload["data_quality"]["option_chain_ok"] = False
        mapped = map_charts_payload(payload, mode="artifact")
        self.assertFalse(mapped["data_quality"]["options_actionable"])
        self.assertTrue(any("option" in w.lower() for w in mapped["warnings"]))

    def test_fail_response_contract(self) -> None:
        body = fail_response(
            ticker="XXXX",
            contract_version="1.0.0",
            error="invalid_ticker",
            error_detail="blocked",
            mode="artifact",
        )
        self.assertEqual(validate_response(body), [])
        self.assertFalse(body["ok"])


class IntcStillWorks(unittest.TestCase):
    def test_intc_ok(self) -> None:
        result = analyze("INTC", mode="artifact")
        self.assertTrue(result.get("ok"), result)
        self.assertEqual(validate_response(result), [])
        self.assertIsNotNone(result["score"]["final"])
        self.assertIn(result["primary"]["action"], {"FULL", "BUILD", "PROBE", "WAIT", "NO", "PUT"})
        # single primary equals gate signal
        self.assertEqual(result["primary"]["action"], result["gate"]["signal"])


class HttpP0Tests(unittest.TestCase):
    def test_http_xxxx_and_intc(self) -> None:
        import threading
        import urllib.error
        import urllib.request
        from http.server import ThreadingHTTPServer

        from app.server import Handler, health_payload

        h = health_payload()
        self.assertTrue(h.get("p0_gates"))
        self.assertIs(h.get("manus_login"), False)

        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        port = server.server_address[1]
        t = threading.Thread(target=server.serve_forever, daemon=True)
        t.start()
        try:
            try:
                urllib.request.urlopen(
                    f"http://127.0.0.1:{port}/api/analyze?ticker=XXXX", timeout=5
                )
                self.fail("expected HTTP error for XXXX")
            except urllib.error.HTTPError as e:
                self.assertEqual(e.code, 400)
                body = json.loads(e.read().decode())
                self.assertEqual(body.get("error"), "invalid_ticker")
                self.assertTrue(
                    body.get("score", {}).get("withheld")
                    or body.get("score", {}).get("final") in (None, 0)
                )

            with urllib.request.urlopen(
                f"http://127.0.0.1:{port}/api/analyze?ticker=INTC", timeout=5
            ) as resp:
                body = json.loads(resp.read().decode())
            self.assertTrue(body.get("ok"), body)
            self.assertIsNotNone(body["score"]["final"])

            try:
                urllib.request.urlopen(
                    f"http://127.0.0.1:{port}/api/oauth/callback", timeout=5
                )
                self.fail("oauth should 410")
            except urllib.error.HTTPError as e:
                self.assertEqual(e.code, 410)
        finally:
            server.shutdown()
            server.server_close()


if __name__ == "__main__":
    unittest.main()
