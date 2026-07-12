"""Own-session auth for QuantRadar shell.

- Guest analyze remains public (artifact).
- Google OAuth → HttpOnly session cookie (HMAC-signed, no DB required).
- Never uses manus.im / platform App Auth.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import secrets
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

COOKIE_NAME = "qr_session"
SESSION_TTL_SEC = 60 * 60 * 24 * 14  # 14 days
OAUTH_STATE_TTL_SEC = 600

_GOOGLE_AUTH = "https://accounts.google.com/o/oauth2/v2/auth"
_GOOGLE_TOKEN = "https://oauth2.googleapis.com/token"
_GOOGLE_USERINFO = "https://openidconnect.googleapis.com/v1/userinfo"

# Ephemeral OAuth state store (single process). Production multi-instance should use shared store.
_STATE_LOCK = __import__("threading").Lock()
_OAUTH_STATES: dict[str, float] = {}


def public_base_url() -> str:
    return os.environ.get("PUBLIC_BASE_URL", "http://127.0.0.1:8765").rstrip("/")


def session_secret() -> str:
    """HMAC secret for session cookies. Dev falls back to unstable secret if unset."""
    env = os.environ.get("SESSION_SECRET", "").strip()
    if env:
        return env
    # Stable-enough per-process fallback so local guest+dev login tests work without env.
    # Production MUST set SESSION_SECRET.
    return os.environ.get("_QUANTRADAR_DEV_SESSION_SECRET") or "dev-insecure-session-secret"


def google_client_id() -> str:
    return os.environ.get("GOOGLE_CLIENT_ID", "").strip()


def google_client_secret() -> str:
    return os.environ.get("GOOGLE_CLIENT_SECRET", "").strip()


def google_configured() -> bool:
    return bool(google_client_id() and google_client_secret())


def auth_status_public() -> dict[str, Any]:
    """Safe fields for /health and /api/auth/status."""
    return {
        "manus_login": False,
        "guest_access": True,
        "google_oauth": google_configured(),
        "providers": ["google"] if google_configured() else [],
        "login_path": "/login",
        "session_cookie": COOKIE_NAME,
        "auth_mode": "google_session" if google_configured() else "guest_only",
        "live_requires_login": True,
    }


def _b64url_encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _b64url_decode(text: str) -> bytes:
    pad = "=" * (-len(text) % 4)
    return base64.urlsafe_b64decode(text + pad)


def sign_payload(payload: dict[str, Any]) -> str:
    body = _b64url_encode(json.dumps(payload, separators=(",", ":"), sort_keys=True).encode())
    sig = hmac.new(session_secret().encode(), body.encode(), hashlib.sha256).digest()
    return f"{body}.{_b64url_encode(sig)}"


def verify_token(token: str | None) -> dict[str, Any] | None:
    if not token or "." not in token:
        return None
    body, _, sig = token.partition(".")
    if not body or not sig:
        return None
    expect = hmac.new(session_secret().encode(), body.encode(), hashlib.sha256).digest()
    try:
        got = _b64url_decode(sig)
    except Exception:
        return None
    if not hmac.compare_digest(expect, got):
        return None
    try:
        payload = json.loads(_b64url_decode(body).decode())
    except Exception:
        return None
    if not isinstance(payload, dict):
        return None
    exp = payload.get("exp")
    if not isinstance(exp, (int, float)) or time.time() > float(exp):
        return None
    return payload


def mint_session(
    *,
    sub: str,
    email: str,
    name: str | None = None,
    picture: str | None = None,
    plan: str = "free",
) -> str:
    now = int(time.time())
    payload = {
        "sub": str(sub),
        "email": str(email),
        "name": name or "",
        "picture": picture or "",
        "plan": plan or "free",
        "iat": now,
        "exp": now + SESSION_TTL_SEC,
        "v": 1,
    }
    return sign_payload(payload)


def session_user_public(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "authenticated": True,
        "email": payload.get("email"),
        "name": payload.get("name") or None,
        "picture": payload.get("picture") or None,
        "plan": payload.get("plan") or "free",
        "sub": payload.get("sub"),
        "exp": payload.get("exp"),
    }


def parse_cookie_header(header: str | None) -> dict[str, str]:
    out: dict[str, str] = {}
    if not header:
        return out
    for part in header.split(";"):
        part = part.strip()
        if not part or "=" not in part:
            continue
        k, _, v = part.partition("=")
        out[k.strip()] = urllib.parse.unquote(v.strip())
    return out


def user_from_cookie_header(cookie_header: str | None) -> dict[str, Any] | None:
    cookies = parse_cookie_header(cookie_header)
    return verify_token(cookies.get(COOKIE_NAME))


def session_cookie_header(token: str, *, clear: bool = False) -> str:
    base = public_base_url()
    secure = base.startswith("https://")
    parts = [
        f"{COOKIE_NAME}={'' if clear else token}",
        "Path=/",
        "HttpOnly",
        "SameSite=Lax",
    ]
    if clear:
        parts.append("Max-Age=0")
    else:
        parts.append(f"Max-Age={SESSION_TTL_SEC}")
    if secure:
        parts.append("Secure")
    return "; ".join(parts)


def create_oauth_state() -> str:
    state = secrets.token_urlsafe(24)
    now = time.time()
    with _STATE_LOCK:
        # prune
        dead = [k for k, exp in _OAUTH_STATES.items() if exp < now]
        for k in dead:
            _OAUTH_STATES.pop(k, None)
        _OAUTH_STATES[state] = now + OAUTH_STATE_TTL_SEC
    return state


def consume_oauth_state(state: str | None) -> bool:
    if not state:
        return False
    now = time.time()
    with _STATE_LOCK:
        exp = _OAUTH_STATES.pop(state, None)
    return exp is not None and exp >= now


def google_authorize_url(state: str) -> str:
    if not google_configured():
        raise RuntimeError("Google OAuth is not configured")
    redirect = f"{public_base_url()}/api/auth/google/callback"
    q = urllib.parse.urlencode(
        {
            "client_id": google_client_id(),
            "redirect_uri": redirect,
            "response_type": "code",
            "scope": "openid email profile",
            "state": state,
            "access_type": "online",
            "prompt": "select_account",
        }
    )
    return f"{_GOOGLE_AUTH}?{q}"


def _http_form_post(url: str, data: dict[str, str], timeout: float = 20) -> dict[str, Any]:
    body = urllib.parse.urlencode(data).encode()
    req = urllib.request.Request(
        url,
        data=body,
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json",
            "User-Agent": "QuantRadar-Auth/0.3",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read().decode()
    obj = json.loads(raw)
    if not isinstance(obj, dict):
        raise RuntimeError("token endpoint returned non-object")
    return obj


def _http_get_json(url: str, access_token: str, timeout: float = 20) -> dict[str, Any]:
    req = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json",
            "User-Agent": "QuantRadar-Auth/0.3",
        },
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read().decode()
    obj = json.loads(raw)
    if not isinstance(obj, dict):
        raise RuntimeError("userinfo returned non-object")
    return obj


def exchange_google_code(code: str) -> dict[str, Any]:
    """Exchange auth code → user profile. Raises on failure."""
    if not google_configured():
        raise RuntimeError("Google OAuth is not configured")
    redirect = f"{public_base_url()}/api/auth/google/callback"
    try:
        token_obj = _http_form_post(
            _GOOGLE_TOKEN,
            {
                "code": code,
                "client_id": google_client_id(),
                "client_secret": google_client_secret(),
                "redirect_uri": redirect,
                "grant_type": "authorization_code",
            },
        )
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode(errors="replace")[:500]
        raise RuntimeError(f"google token exchange failed: {exc.code} {detail}") from exc
    access = token_obj.get("access_token")
    if not access:
        raise RuntimeError(f"google token missing access_token: {token_obj.get('error')}")
    info = _http_get_json(_GOOGLE_USERINFO, str(access))
    email = info.get("email")
    sub = info.get("sub")
    if not email or not sub:
        raise RuntimeError("google userinfo missing email/sub")
    if info.get("email_verified") is False:
        raise RuntimeError("google email not verified")
    return {
        "sub": str(sub),
        "email": str(email),
        "name": str(info.get("name") or ""),
        "picture": str(info.get("picture") or ""),
    }


def dev_login_enabled() -> bool:
    """Local-only test login without Google (never on production public URL)."""
    if os.environ.get("QUANTRADAR_DEV_LOGIN", "").strip() not in {"1", "true", "yes"}:
        return False
    base = public_base_url()
    return "127.0.0.1" in base or "localhost" in base
