#!/usr/bin/env python3
"""Run Python tests without loading local secrets or writing real account data."""

from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile


def main() -> int:
    repo = Path(__file__).resolve().parents[1]
    with tempfile.TemporaryDirectory(prefix="quantradar-tests-") as directory:
        root = Path(directory)
        for name in ("app", "tests", "static", "fixtures", "schemas", "scripts", "docs", "free_engine", "ios"):
            shutil.copytree(
                repo / name, root / name,
                ignore=shutil.ignore_patterns("__pycache__", ".cache", "build", "DerivedData", "*.xcresult", "*.xcodeproj", "xcuserdata"),
            )
        for name in ("README.md", "Dockerfile", "requirements.txt"):
            shutil.copy2(repo / name, root / name)
        env = {
            k: v for k, v in os.environ.items()
            if not k.startswith(("QUANTRADAR_", "STRIPE_", "SMTP_", "GOOGLE_"))
            and k not in {"SESSION_SECRET", "PUBLIC_BASE_URL", "CHARTS_DIR"}
        }
        env.update({
            "QUANTRADAR_BOOTSTRAP_DEMO": "0",
            "PUBLIC_BASE_URL": "http://127.0.0.1",
            "SESSION_SECRET": "isolated-tests-only-not-a-live-secret",
            "CHARTS_DIR": str(root / "missing-engine"),
        })
        arguments = sys.argv[1:] or ["discover", "-s", "tests", "-q"]
        return subprocess.run([sys.executable, "-m", "unittest", *arguments], cwd=root, env=env).returncode


if __name__ == "__main__":
    raise SystemExit(main())
