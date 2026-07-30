#!/usr/bin/env python3
"""Print honest funnel rates from data/funnel.jsonl (no PII)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from app.funnel import summarize  # noqa: E402


def main() -> int:
    s = summarize()
    print(json.dumps(s, indent=2, ensure_ascii=False))
    counts = s.get("counts") or {}
    print("\nNorth-star snapshot:")
    print(f"  demo_run={counts.get('demo_run', 0)}")
    print(f"  signup={counts.get('signup', 0)}  (N2 vs demos: {s['rates'].get('signup_per_demo')})")
    print(
        f"  checkout_start={counts.get('checkout_start', 0)}  "
        f"(N3 vs signup: {s['rates'].get('checkout_per_signup')})"
    )
    print(
        f"  pro_active={counts.get('pro_active', 0)}  "
        f"(N4 vs checkout: {s['rates'].get('pro_per_checkout')})"
    )
    print(
        f"  live_run={counts.get('live_run', 0)}  "
        f"(N5 vs pro: {s['rates'].get('live_per_pro')})"
    )
    print(f"  notify_save={counts.get('notify_save', 0)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
