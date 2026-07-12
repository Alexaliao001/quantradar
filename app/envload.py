"""Load gitignored .env into process env (does not override existing)."""

from __future__ import annotations

import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def load_dotenv(path: Path | None = None) -> Path | None:
    candidates = []
    if path is not None:
        candidates.append(path)
    env_file = os.environ.get("QUANTRADAR_ENV_FILE", "").strip()
    if env_file:
        candidates.append(Path(env_file).expanduser())
    candidates.extend(
        [
            REPO_ROOT / ".env",
            REPO_ROOT / ".env.local",
            Path.home() / ".config" / "quantradar" / ".env",
        ]
    )
    for p in candidates:
        if p.is_file():
            _apply(p)
            return p
    return None


def _apply(path: Path) -> None:
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[7:].strip()
        if "=" not in line:
            continue
        key, _, val = line.partition("=")
        key = key.strip()
        val = val.strip().strip("'").strip('"')
        if key and key not in os.environ:
            os.environ[key] = val
