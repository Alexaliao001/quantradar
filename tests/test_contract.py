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


if __name__ == "__main__":
    unittest.main()
