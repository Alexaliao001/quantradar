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
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from app import CONTRACT_VERSION, __version__
from app.charts_facade import analyze, charts_dir
from app.contract import validate_response

REPO_ROOT = Path(__file__).resolve().parent.parent
STATIC_DIR = REPO_ROOT / "static"


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
    }


class Handler(BaseHTTPRequestHandler):
    server_version = f"QuantRadarShell/{__version__}"

    def log_message(self, fmt: str, *args: Any) -> None:
        sys_stderr = __import__("sys").stderr
        print(f"[shell] {self.address_string()} {fmt % args}", file=sys_stderr)

    def _send(self, code: int, body: dict[str, Any] | bytes, content_type: str = "application/json") -> None:
        if isinstance(body, dict):
            raw = json.dumps(body, ensure_ascii=False, indent=2).encode("utf-8")
        else:
            raw = body
        self.send_response(code)
        self.send_header("Content-Type", f"{content_type}; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.send_header("Cache-Control", "no-store")
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

    def do_GET(self) -> None:  # noqa: N802
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path.rstrip("/") or "/"
        qs = urllib.parse.parse_qs(parsed.query)

        if path in {"/health", "/api/health"}:
            self._send(200, health_payload())
            return

        if path == "/api/analyze":
            ticker = (qs.get("ticker") or [None])[0]
            sector = (qs.get("sector") or [None])[0]
            mode = (qs.get("mode") or [None])[0]
            try:
                result = analyze(ticker or "", sector=sector, mode=mode)
            except ValueError as exc:
                self._send(400, {"ok": False, "error": str(exc), "contract_version": CONTRACT_VERSION})
                return
            code = 200 if result.get("ok") else 502
            # still 200 for degraded-but-mapped artifact success
            if result.get("ok"):
                code = 200
            errs = validate_response(result)
            if errs and result.get("ok"):
                result = {**result, "warnings": list(result.get("warnings") or []) + errs}
            self._send(code, result)
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
        if path != "/api/analyze":
            self._send(404, {"ok": False, "error": "not found"})
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
            self._send(400, {"ok": False, "error": str(exc), "contract_version": CONTRACT_VERSION})
            return
        code = 200 if result.get("ok") else 502
        self._send(code, result)


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
