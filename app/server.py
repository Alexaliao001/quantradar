"""Minimal stdlib HTTP shell for QuantRadar (path C).

Start:
  PORT=8765 python -m app
  # or
  python -m app.server
"""

from __future__ import annotations

import json
import os
import subprocess
import threading
import time
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from app import CONTRACT_VERSION, __version__
from app.charts_facade import analyze, charts_dir
from app.contract import validate_response

REPO_ROOT = Path(__file__).resolve().parent.parent
STATIC_DIR = REPO_ROOT / "static"

# Simple sliding-window rate limit (per remote address)
_RATE_LOCK = threading.Lock()
_RATE_HITS: dict[str, list[float]] = {}


def _rate_limit_max() -> int:
    try:
        return max(1, int(os.environ.get("QUANTRADAR_RATE_LIMIT", "30")))
    except ValueError:
        return 30


def _rate_limit_window() -> float:
    try:
        return max(1.0, float(os.environ.get("QUANTRADAR_RATE_WINDOW_SEC", "60")))
    except ValueError:
        return 60.0


def check_rate_limit(client: str) -> bool:
    """Return True if allowed, False if limited."""
    now = time.time()
    window = _rate_limit_window()
    limit = _rate_limit_max()
    with _RATE_LOCK:
        hits = [t for t in _RATE_HITS.get(client, []) if now - t < window]
        if len(hits) >= limit:
            _RATE_HITS[client] = hits
            return False
        hits.append(now)
        _RATE_HITS[client] = hits
        return True


def git_sha() -> str | None:
    try:
        out = subprocess.check_output(
            ["git", "-C", str(REPO_ROOT), "rev-parse", "--short", "HEAD"],
            text=True,
            stderr=subprocess.DEVNULL,
        )
        return out.strip() or None
    except Exception:
        return None


def health_payload() -> dict[str, Any]:
    cdir = charts_dir()
    fetch_all = cdir / "fetch_all.py"
    return {
        "ok": True,
        "service": "quantradar-shell",
        "version": __version__,
        "contract_version": CONTRACT_VERSION,
        "git_sha": git_sha(),
        "charts_dir": str(cdir),
        "charts_reachable": cdir.is_dir(),
        "fetch_all_present": fetch_all.is_file(),
        "mode_default": os.environ.get("QUANTRADAR_MODE", "artifact"),
        # Auth iron rule: guest analysis, never Manus app-auth
        "auth": "none",
        "manus_login": False,
        "guest_access": True,
        "p0_gates": True,
    }


def manus_login_disabled_payload() -> dict[str, Any]:
    """Explicit 410 body for legacy Manus OAuth routes."""
    return {
        "ok": False,
        "error": "manus_login_disabled",
        "message": (
            "QuantRadar does not use manus.im/app-auth. "
            "Use / for guest UI or GET /api/analyze?ticker=INTC — no login."
        ),
        "auth": "none",
        "manus_login": False,
        "docs": "docs/AUTH.md",
    }


def is_manus_auth_path(path: str) -> bool:
    """Legacy Manus platform auth paths that must never succeed."""
    p = path.lower()
    if p.startswith("/api/oauth"):
        return True
    if p in {"/login", "/signin", "/sign-in", "/auth", "/app-auth"}:
        return True
    if "manus" in p and ("auth" in p or "oauth" in p or "login" in p):
        return True
    return False


def http_code_for_result(result: dict[str, Any]) -> int:
    if result.get("ok"):
        return 200
    err = str(result.get("error") or "")
    if err in {"invalid_ticker", "artifact_not_found", "no_data"}:
        return 404
    if "invalid" in err:
        return 400
    return 502


class Handler(BaseHTTPRequestHandler):
    server_version = f"QuantRadarShell/{__version__}"

    def log_message(self, fmt: str, *args: Any) -> None:
        sys_stderr = __import__("sys").stderr
        print(f"[shell] {self.address_string()} {fmt % args}", file=sys_stderr)

    def _client_id(self) -> str:
        return self.client_address[0] if self.client_address else "unknown"

    def _send(
        self,
        code: int,
        body: dict[str, Any] | bytes,
        content_type: str = "application/json",
    ) -> None:
        if isinstance(body, dict):
            raw = json.dumps(body, ensure_ascii=False, indent=2).encode("utf-8")
        else:
            raw = body
        self.send_response(code)
        self.send_header("Content-Type", f"{content_type}; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-QuantRadar-Auth", "none")
        self.end_headers()
        self.wfile.write(raw)

    def _read_json(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length") or 0)
        if length <= 0:
            return {}
        raw = self.rfile.read(length)
        if not raw:
            return {}
        data = json.loads(raw.decode("utf-8"))
        if not isinstance(data, dict):
            raise ValueError("JSON body must be an object")
        return data

    def _analyze_response(self, result: dict[str, Any]) -> None:
        errs = validate_response(result)
        if errs:
            result = {
                **result,
                "warnings": list(result.get("warnings") or [])
                + [f"contract: {e}" for e in errs],
            }
            if result.get("ok") and errs:
                # structural break on success path → refuse rather than ship bad JSON
                result = {
                    **result,
                    "ok": False,
                    "error": result.get("error") or "contract_violation",
                    "error_detail": "; ".join(errs),
                    "score": {
                        "final": None,
                        "base_total": None,
                        "scale": 100,
                        "withheld": True,
                    },
                    "gate": {
                        **(result.get("gate") or {}),
                        "signal": "NO",
                        "primary": "NO",
                    },
                    "primary": {
                        "action": "NO",
                        "label": "No / stand aside",
                        "reason": "contract validation failed",
                    },
                    "degraded": True,
                }
        self._send(http_code_for_result(result), result)

    def do_GET(self) -> None:  # noqa: N802
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path.rstrip("/") or "/"
        qs = urllib.parse.parse_qs(parsed.query)

        # Never proxy or succeed at Manus platform login
        if is_manus_auth_path(path) or is_manus_auth_path(parsed.path):
            self._send(410, manus_login_disabled_payload())
            return

        if path in {"/health", "/api/health"}:
            self._send(200, health_payload())
            return

        if path == "/api/analyze":
            if not check_rate_limit(self._client_id()):
                self._send(
                    429,
                    {
                        "ok": False,
                        "error": "rate_limited",
                        "error_detail": "too many analyze requests; try again shortly",
                        "contract_version": CONTRACT_VERSION,
                    },
                )
                return
            ticker = (qs.get("ticker") or [None])[0]
            sector = (qs.get("sector") or [None])[0]
            mode = (qs.get("mode") or [None])[0]
            try:
                result = analyze(ticker or "", sector=sector, mode=mode)
            except ValueError as exc:
                self._send(
                    400,
                    {
                        "ok": False,
                        "error": "invalid_ticker",
                        "error_detail": str(exc),
                        "contract_version": CONTRACT_VERSION,
                        "gate": {"signal": "NO"},
                        "score": {"final": None, "scale": 100, "withheld": True},
                        "artifacts": {"charts": {}},
                        "sources": [],
                        "warnings": [str(exc)],
                        "ticker": (ticker or "").upper() or "UNKNOWN",
                    },
                )
                return
            self._analyze_response(result)
            return

        # Guest sample — no login (QR1-2 direction)
        if path in {"/api/sample", "/sample"}:
            result = analyze("INTC", mode="artifact")
            result["meta"] = dict(result.get("meta") or {})
            result["meta"]["guest"] = True
            result["meta"]["auth"] = "none"
            result["sample"] = True
            self._analyze_response(result)
            return

        if path in {"/", "/index.html"}:
            index = STATIC_DIR / "index.html"
            if not index.is_file():
                self._send(404, {"ok": False, "error": "static/index.html missing"})
                return
            self._send(200, index.read_bytes(), content_type="text/html")
            return

        # static assets
        if path.startswith("/static/"):
            rel = path[len("/static/") :]
            target = (STATIC_DIR / rel).resolve()
            if not str(target).startswith(str(STATIC_DIR.resolve())) or not target.is_file():
                self._send(404, {"ok": False, "error": "not found"})
                return
            ctype = "text/plain"
            if target.suffix == ".css":
                ctype = "text/css"
            elif target.suffix == ".js":
                ctype = "application/javascript"
            elif target.suffix == ".html":
                ctype = "text/html"
            self._send(200, target.read_bytes(), content_type=ctype)
            return

        self._send(404, {"ok": False, "error": "not found", "path": path})

    def do_POST(self) -> None:  # noqa: N802
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path.rstrip("/") or "/"
        if is_manus_auth_path(path) or is_manus_auth_path(parsed.path):
            self._send(410, manus_login_disabled_payload())
            return
        if path != "/api/analyze":
            self._send(404, {"ok": False, "error": "not found"})
            return
        if not check_rate_limit(self._client_id()):
            self._send(
                429,
                {
                    "ok": False,
                    "error": "rate_limited",
                    "error_detail": "too many analyze requests; try again shortly",
                    "contract_version": CONTRACT_VERSION,
                },
            )
            return
        try:
            body = self._read_json()
        except Exception as exc:
            self._send(400, {"ok": False, "error": f"invalid JSON: {exc}"})
            return
        ticker = body.get("ticker")
        sector = body.get("sector")
        ctx = body.get("context") if isinstance(body.get("context"), dict) else {}
        mode = ctx.get("mode") or body.get("mode")
        request_id = ctx.get("request_id")
        try:
            result = analyze(
                str(ticker) if ticker is not None else "",
                sector=str(sector) if sector else None,
                mode=str(mode) if mode else None,
                request_id=str(request_id) if request_id else None,
            )
        except ValueError as exc:
            self._send(
                400,
                {
                    "ok": False,
                    "error": "invalid_ticker",
                    "error_detail": str(exc),
                    "contract_version": CONTRACT_VERSION,
                    "gate": {"signal": "NO"},
                    "score": {"final": None, "scale": 100, "withheld": True},
                    "artifacts": {"charts": {}},
                    "sources": [],
                    "warnings": [str(exc)],
                    "ticker": str(ticker or "UNKNOWN").upper(),
                },
            )
            return
        self._analyze_response(result)


def main() -> None:
    host = os.environ.get("HOST", "127.0.0.1")
    port = int(os.environ.get("PORT", "8765"))
    server = ThreadingHTTPServer((host, port), Handler)
    print(
        f"quantradar shell v{__version__} contract={CONTRACT_VERSION} "
        f"http://{host}:{port}/  (health=/health analyze=/api/analyze)",
        flush=True,
    )
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nshutting down", flush=True)
        server.shutdown()


if __name__ == "__main__":
    main()
