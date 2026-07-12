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
from app import auth as authlib
from app.charts_facade import analyze, charts_dir
from app.contract import validate_response
from app.envload import load_dotenv
from app import stripe_billing
from app.notify import save_waitlist
from app.users import (
    authenticate as password_login,
    ensure_bootstrap_admin,
    register_user,
)

# Demo tickers: free artifact sample only (TG-5) — never live, never "credits"
DEMO_TICKERS = frozenset({"INTC", "NVDA", "AAPL", "MU", "TSLA", "AMD"})

# Ensure local admin exists once at import (no-op if users already present)
try:
    ensure_bootstrap_admin()
except Exception:
    pass

# Load .env before reading any auth/stripe config in handlers
load_dotenv()

REPO_ROOT = Path(__file__).resolve().parent.parent
STATIC_DIR = REPO_ROOT / "static"

# Simple sliding-window rate limit (per remote address)
_RATE_LOCK = threading.Lock()
_RATE_HITS: dict[str, list[float]] = {}


def _rate_limit_max(authenticated: bool = False) -> int:
    try:
        guest = max(1, int(os.environ.get("QUANTRADAR_RATE_LIMIT", "30")))
        authed = max(guest, int(os.environ.get("QUANTRADAR_RATE_LIMIT_AUTH", "120")))
    except ValueError:
        guest, authed = 30, 120
    return authed if authenticated else guest


def _rate_limit_window() -> float:
    try:
        return max(1.0, float(os.environ.get("QUANTRADAR_RATE_WINDOW_SEC", "60")))
    except ValueError:
        return 60.0


def check_rate_limit(client: str, *, authenticated: bool = False) -> bool:
    """Return True if allowed, False if limited."""
    now = time.time()
    window = _rate_limit_window()
    limit = _rate_limit_max(authenticated)
    key = f"{'a' if authenticated else 'g'}:{client}"
    with _RATE_LOCK:
        hits = [t for t in _RATE_HITS.get(key, []) if now - t < window]
        if len(hits) >= limit:
            _RATE_HITS[key] = hits
            return False
        hits.append(now)
        _RATE_HITS[key] = hits
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
    a = authlib.auth_status_public()
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
        # Auth: guest + optional Google session; never Manus
        "auth": a["auth_mode"],
        "manus_login": False,
        "guest_access": True,
        "google_oauth": a["google_oauth"],
        "login_path": "/login",
        "live_requires_login": True,
        "p0_gates": True,
    }


def manus_login_disabled_payload() -> dict[str, Any]:
    """Explicit 410 body for legacy Manus OAuth routes."""
    return {
        "ok": False,
        "error": "manus_login_disabled",
        "message": (
            "QuantRadar does not use manus.im/app-auth. "
            "QuantRadar uses its own /login (email+password). Guest UI at / — no Manus."
        ),
        "auth": authlib.auth_status_public()["auth_mode"],
        "manus_login": False,
        "login": "/login",
        "docs": "docs/AUTH.md",
    }


def is_manus_auth_path(path: str) -> bool:
    """Legacy Manus platform auth paths that must never succeed.

    Own product login is /login and /api/auth/* — those are NOT Manus.
    """
    p = path.lower().rstrip("/") or "/"
    if p.startswith("/api/oauth"):
        return True
    if p in {"/app-auth", "/signin", "/sign-in"}:
        return True
    if "manus" in p and ("auth" in p or "oauth" in p or "login" in p):
        return True
    return False


def http_code_for_result(result: dict[str, Any]) -> int:
    if result.get("ok"):
        return 200
    err = str(result.get("error") or "")
    if err in {"login_required"}:
        return 401
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

    def _current_user(self) -> dict[str, Any] | None:
        return authlib.user_from_cookie_header(self.headers.get("Cookie"))

    def _send(
        self,
        code: int,
        body: dict[str, Any] | bytes,
        content_type: str = "application/json",
        *,
        extra_headers: list[tuple[str, str]] | None = None,
        auth_tag: str | None = None,
    ) -> None:
        if isinstance(body, dict):
            raw = json.dumps(body, ensure_ascii=False, indent=2).encode("utf-8")
        else:
            raw = body
        self.send_response(code)
        self.send_header("Content-Type", f"{content_type}; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.send_header("Cache-Control", "no-store")
        tag = auth_tag
        if tag is None:
            tag = "session" if self._current_user() else "guest"
        self.send_header("X-QuantRadar-Auth", tag)
        if extra_headers:
            for k, v in extra_headers:
                self.send_header(k, v)
        self.end_headers()
        self.wfile.write(raw)

    def _redirect(self, location: str, *, extra_headers: list[tuple[str, str]] | None = None) -> None:
        self.send_response(302)
        self.send_header("Location", location)
        self.send_header("Cache-Control", "no-store")
        if extra_headers:
            for k, v in extra_headers:
                self.send_header(k, v)
        self.end_headers()

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

    def _analyze_response(self, result: dict[str, Any], *, user: dict[str, Any] | None) -> None:
        errs = validate_response(result)
        if errs:
            result = {
                **result,
                "warnings": list(result.get("warnings") or [])
                + [f"contract: {e}" for e in errs],
            }
            if result.get("ok") and errs:
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
        result.setdefault("meta", {})
        if isinstance(result["meta"], dict):
            result["meta"]["auth"] = "session" if user else "guest"
            if user:
                result["meta"]["user_email"] = user.get("email")
        self._send(
            http_code_for_result(result),
            result,
            auth_tag="session" if user else "guest",
        )

    def _run_analyze(
        self,
        ticker: str | None,
        sector: str | None,
        mode: str | None,
        request_id: str | None = None,
    ) -> None:
        user = self._current_user()
        if not check_rate_limit(self._client_id(), authenticated=bool(user)):
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

        mode_norm = (mode or "").strip().lower() or None
        # Live mode requires login (uses real charts fetch / keys)
        if mode_norm == "live" and not user:
            self._send(
                401,
                {
                    "ok": False,
                    "error": "login_required",
                    "error_detail": "mode=live requires sign-in. Guest may use artifact/sample.",
                    "login": "/login",
                    "contract_version": CONTRACT_VERSION,
                    "gate": {"signal": "NO"},
                    "score": {"final": None, "scale": 100, "withheld": True},
                    "artifacts": {"charts": {}},
                    "sources": [],
                    "warnings": ["live mode requires Google session"],
                    "ticker": (ticker or "").upper() or "UNKNOWN",
                },
                auth_tag="guest",
            )
            return

        try:
            result = analyze(
                ticker or "",
                sector=sector,
                mode=mode_norm,
                request_id=request_id,
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
                    "ticker": (ticker or "").upper() or "UNKNOWN",
                },
            )
            return
        self._analyze_response(result, user=user)

    def do_GET(self) -> None:  # noqa: N802
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path.rstrip("/") or "/"
        qs = urllib.parse.parse_qs(parsed.query)

        # Never succeed at Manus platform login
        if is_manus_auth_path(path) or is_manus_auth_path(parsed.path):
            self._send(410, manus_login_disabled_payload(), auth_tag="none")
            return

        if path in {"/health", "/api/health"}:
            self._send(200, health_payload(), auth_tag="none")
            return

        # --- Auth API (own session, not Manus) ---
        if path in {"/api/auth/status", "/api/me"}:
            user = self._current_user()
            body = {
                "ok": True,
                **authlib.auth_status_public(),
                "user": authlib.session_user_public(user) if user else None,
                "authenticated": bool(user),
            }
            if path == "/api/me" and not user:
                self._send(
                    401,
                    {
                        "ok": False,
                        "error": "login_required",
                        "authenticated": False,
                        "login": "/login",
                        **authlib.auth_status_public(),
                    },
                    auth_tag="guest",
                )
                return
            self._send(200, body, auth_tag="session" if user else "guest")
            return

        if path == "/api/auth/google/start":
            if not authlib.google_configured():
                self._send(
                    503,
                    {
                        "ok": False,
                        "error": "google_not_configured",
                        "error_detail": (
                            "Set GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, "
                            "SESSION_SECRET, PUBLIC_BASE_URL"
                        ),
                        "login": "/login",
                    },
                )
                return
            state = authlib.create_oauth_state()
            try:
                url = authlib.google_authorize_url(state)
            except Exception as exc:
                self._send(500, {"ok": False, "error": "oauth_start_failed", "error_detail": str(exc)})
                return
            self._redirect(url)
            return

        if path == "/api/auth/google/callback":
            if not authlib.google_configured():
                self._redirect("/login?error=google_not_configured")
                return
            err = (qs.get("error") or [None])[0]
            if err:
                self._redirect(f"/login?error={urllib.parse.quote(str(err))}")
                return
            state = (qs.get("state") or [None])[0]
            code = (qs.get("code") or [None])[0]
            if not authlib.consume_oauth_state(state):
                self._redirect("/login?error=invalid_state")
                return
            if not code:
                self._redirect("/login?error=missing_code")
                return
            try:
                profile = authlib.exchange_google_code(str(code))
                token = authlib.mint_session(
                    sub=profile["sub"],
                    email=profile["email"],
                    name=profile.get("name"),
                    picture=profile.get("picture"),
                    plan="free",
                )
            except Exception as exc:
                self._redirect(f"/login?error={urllib.parse.quote(str(exc)[:120])}")
                return
            self._redirect(
                "/?signed_in=1",
                extra_headers=[("Set-Cookie", authlib.session_cookie_header(token))],
            )
            return

        if path == "/api/auth/logout":
            # GET logout for simple <a href>
            self._redirect(
                "/",
                extra_headers=[("Set-Cookie", authlib.session_cookie_header("", clear=True))],
            )
            return

        if path == "/api/auth/dev-login":
            if not authlib.dev_login_enabled():
                self._send(404, {"ok": False, "error": "not found"})
                return
            email = (qs.get("email") or ["dev@localhost"])[0]
            token = authlib.mint_session(
                sub="dev-local",
                email=str(email),
                name="Dev User",
                plan="free",
            )
            self._redirect(
                "/?signed_in=1",
                extra_headers=[("Set-Cookie", authlib.session_cookie_header(token))],
            )
            return

        if path == "/api/auth/magic/consume":
            tok = (qs.get("token") or [None])[0]
            try:
                profile = authlib.consume_magic_token(tok)
                token = authlib.mint_session(
                    sub=profile["sub"],
                    email=profile["email"],
                    name=profile.get("name"),
                    plan="free",
                )
            except Exception as exc:
                self._redirect(f"/login?error={urllib.parse.quote(str(exc)[:120])}")
                return
            self._redirect(
                "/?signed_in=1",
                extra_headers=[("Set-Cookie", authlib.session_cookie_header(token))],
            )
            return

        if path == "/api/billing/status":
            self._send(
                200,
                {
                    "ok": True,
                    "stripe_configured": stripe_billing.stripe_configured(),
                    "checkout": "/api/billing/checkout",
                },
            )
            return

        if path == "/api/analyze":
            ticker = (qs.get("ticker") or [None])[0]
            sector = (qs.get("sector") or [None])[0]
            mode = (qs.get("mode") or [None])[0]
            self._run_analyze(ticker, sector, mode)
            return

        # Guest sample / demo chips — free, artifact only (TG-5)
        if path in {"/api/sample", "/sample"}:
            user = self._current_user()
            ticker = (qs.get("ticker") or ["INTC"])[0] or "INTC"
            t = str(ticker).strip().upper()
            if t not in DEMO_TICKERS:
                t = "INTC"
            result = analyze(t, mode="artifact")
            result["meta"] = dict(result.get("meta") or {})
            result["meta"]["guest"] = not bool(user)
            result["meta"]["auth"] = "session" if user else "guest"
            result["meta"]["demo"] = True
            result["meta"]["credits_charged"] = 0
            result["sample"] = True
            result["demo"] = True
            self._analyze_response(result, user=user)
            return

        if path == "/api/public_stats":
            # TG-3: never invent social proof counts
            self._send(
                200,
                {
                    "ok": True,
                    "label": "Beta",
                    "note": "No fabricated user counts. Early product — sample analyses available free.",
                    "totalAnalyses": None,
                    "totalUsers": None,
                },
            )
            return

        if path in {"/", "/index.html"}:
            index = STATIC_DIR / "index.html"
            if not index.is_file():
                self._send(404, {"ok": False, "error": "static/index.html missing"})
                return
            self._send(200, index.read_bytes(), content_type="text/html")
            return

        # Marketing / legal pages (TG-8/9)
        page_map = {
            "/login": "login.html",
            "/methodology": "methodology.html",
            "/pricing": "pricing.html",
            "/terms": "terms.html",
            "/privacy": "privacy.html",
            "/refund": "refund.html",
        }
        if path in page_map:
            page = STATIC_DIR / page_map[path]
            if not page.is_file():
                self._send(404, {"ok": False, "error": f"missing {page_map[path]}"})
                return
            self._send(200, page.read_bytes(), content_type="text/html")
            return

        if path == "/robots.txt":
            body = (
                "User-agent: *\n"
                "Allow: /\n"
                "Disallow: /api/auth/\n"
                "Sitemap: /sitemap.txt\n"
            ).encode()
            self._send(200, body, content_type="text/plain")
            return

        if path == "/sitemap.txt":
            body = (
                "/\n/methodology\n/pricing\n/terms\n/privacy\n/refund\n/login\n"
            ).encode()
            self._send(200, body, content_type="text/plain")
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
            self._send(410, manus_login_disabled_payload(), auth_tag="none")
            return

        if path == "/api/auth/logout":
            self._send(
                200,
                {"ok": True, "authenticated": False, "manus_login": False},
                extra_headers=[("Set-Cookie", authlib.session_cookie_header("", clear=True))],
                auth_tag="guest",
            )
            return

        if path == "/api/auth/register":
            try:
                body = self._read_json()
            except Exception as exc:
                self._send(400, {"ok": False, "error": f"invalid JSON: {exc}"})
                return
            try:
                user = register_user(
                    str(body.get("email") or ""),
                    str(body.get("password") or ""),
                    name=str(body.get("name") or "") or None,
                )
            except ValueError as exc:
                self._send(400, {"ok": False, "error": "register_failed", "error_detail": str(exc)})
                return
            except RuntimeError as exc:
                self._send(403, {"ok": False, "error": "register_disabled", "error_detail": str(exc)})
                return
            token = authlib.mint_session(
                sub=f"pw:{user['email']}",
                email=str(user["email"]),
                name=user.get("name"),
                plan=str(user.get("plan") or "free"),
            )
            self._send(
                200,
                {
                    "ok": True,
                    "authenticated": True,
                    "user": user,
                    "auth": "password",
                },
                extra_headers=[("Set-Cookie", authlib.session_cookie_header(token))],
                auth_tag="session",
            )
            return

        if path == "/api/auth/login":
            try:
                body = self._read_json()
            except Exception as exc:
                self._send(400, {"ok": False, "error": f"invalid JSON: {exc}"})
                return
            try:
                user = password_login(
                    str(body.get("email") or ""),
                    str(body.get("password") or ""),
                )
            except ValueError as exc:
                self._send(401, {"ok": False, "error": "login_failed", "error_detail": str(exc)})
                return
            except RuntimeError as exc:
                self._send(403, {"ok": False, "error": "login_disabled", "error_detail": str(exc)})
                return
            token = authlib.mint_session(
                sub=f"pw:{user['email']}",
                email=str(user["email"]),
                name=user.get("name"),
                plan=str(user.get("plan") or "free"),
            )
            self._send(
                200,
                {
                    "ok": True,
                    "authenticated": True,
                    "user": user,
                    "auth": "password",
                },
                extra_headers=[("Set-Cookie", authlib.session_cookie_header(token))],
                auth_tag="session",
            )
            return

        if path == "/api/notify":
            try:
                body = self._read_json()
            except Exception as exc:
                self._send(400, {"ok": False, "error": f"invalid JSON: {exc}"})
                return
            try:
                out = save_waitlist(
                    email=str(body.get("email") or ""),
                    ticker=str(body.get("ticker") or "") or None,
                    kind=str(body.get("kind") or "setup_alert"),
                    source=str(body.get("source") or "web"),
                )
            except ValueError as exc:
                self._send(400, {"ok": False, "error": "invalid_email", "error_detail": str(exc)})
                return
            self._send(200, out)
            return

        if path == "/api/auth/magic/start":
            try:
                body = self._read_json()
            except Exception as exc:
                self._send(400, {"ok": False, "error": f"invalid JSON: {exc}"})
                return
            email = str(body.get("email") or "").strip()
            try:
                result = authlib.issue_magic_link(email)
            except ValueError as exc:
                self._send(400, {"ok": False, "error": "invalid_email", "error_detail": str(exc)})
                return
            except Exception as exc:
                self._send(500, {"ok": False, "error": "magic_failed", "error_detail": str(exc)})
                return
            self._send(200, result)
            return

        if path == "/api/billing/checkout":
            user = self._current_user()
            if not user:
                self._send(
                    401,
                    {
                        "ok": False,
                        "error": "login_required",
                        "login": "/login",
                        "error_detail": "Sign in before checkout",
                    },
                )
                return
            if not stripe_billing.stripe_configured():
                self._send(
                    503,
                    {
                        "ok": False,
                        "error": "stripe_not_configured",
                        "error_detail": "Set QUANTRADAR_STRIPE_SECRET_KEY",
                    },
                )
                return
            try:
                body = self._read_json()
            except Exception:
                body = {}
            try:
                session = stripe_billing.create_checkout_session(
                    customer_email=str(user.get("email") or "") or None,
                    price_id=str(body.get("price_id") or "") or None,
                )
            except Exception as exc:
                self._send(
                    502,
                    {"ok": False, "error": "stripe_error", "error_detail": str(exc)[:500]},
                )
                return
            self._send(200, {"ok": True, **session})
            return

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
        self._run_analyze(
            str(ticker) if ticker is not None else "",
            str(sector) if sector else None,
            str(mode) if mode else None,
            str(request_id) if request_id else None,
        )


def main() -> None:
    load_dotenv()
    host = os.environ.get("HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", "8765"))
    server = ThreadingHTTPServer((host, port), Handler)
    a = authlib.auth_status_public()
    print(
        f"quantradar shell v{__version__} contract={CONTRACT_VERSION} "
        f"auth={a['auth_mode']} google={a['google_oauth']} magic={a['magic_link']} "
        f"stripe={a['stripe_checkout']} "
        f"http://{host}:{port}/  login=/login",
        flush=True,
    )
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nshutting down", flush=True)
        server.shutdown()


if __name__ == "__main__":
    main()
