#!/usr/bin/env python3
"""Map real charts fixture → ENGINE_CONTRACT sample and validate."""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from app.charts_facade import analyze  # noqa: E402
from app.contract import validate_response  # noqa: E402


def main() -> int:
    result = analyze("INTC", mode="artifact")
    errs = validate_response(result)
    sample_dir = REPO / "schemas" / "samples"
    sample_dir.mkdir(parents=True, exist_ok=True)
    sample_path = sample_dir / "engine_response.sample.json"
    sample_path.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print("wrote", sample_path)
    print("ok=", result.get("ok"), "ticker=", result.get("ticker"), "score=", result.get("score"))
    if errs:
        print("VALIDATION FAILED:")
        for e in errs:
            print(" -", e)
        return 1
    print("VALIDATION PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
