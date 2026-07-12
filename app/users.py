"""Local password accounts (stdlib only). Google can be layered later.

Storage: data/users.json
Password: PBKDF2-HMAC-SHA256
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import secrets
import threading
import time
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parent.parent
USERS_PATH = REPO / "data" / "users.json"
_LOCK = threading.Lock()
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_PBKDF2_ROUNDS = 200_000


def password_auth_enabled() -> bool:
    return os.environ.get("PASSWORD_AUTH_DISABLED", "").strip().lower() not in {
        "1",
        "true",
        "yes",
    }


def registration_open() -> bool:
    # Default open for beta; set ALLOW_REGISTER=0 to lock
    return os.environ.get("ALLOW_REGISTER", "1").strip().lower() not in {
        "0",
        "false",
        "no",
    }


def _empty_store() -> dict[str, Any]:
    return {"version": 1, "users": {}}


def _load() -> dict[str, Any]:
    if not USERS_PATH.is_file():
        return _empty_store()
    try:
        data = json.loads(USERS_PATH.read_text(encoding="utf-8"))
    except Exception:
        return _empty_store()
    if not isinstance(data, dict) or "users" not in data:
        return _empty_store()
    if not isinstance(data["users"], dict):
        data["users"] = {}
    return data


def _save(store: dict[str, Any]) -> None:
    USERS_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp = USERS_PATH.with_suffix(".tmp")
    tmp.write_text(json.dumps(store, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    tmp.replace(USERS_PATH)


def _hash_password(password: str, salt: bytes | None = None) -> tuple[str, str]:
    if salt is None:
        salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt, _PBKDF2_ROUNDS
    )
    return salt.hex(), digest.hex()


def _verify(password: str, salt_hex: str, hash_hex: str) -> bool:
    try:
        salt = bytes.fromhex(salt_hex)
        expect = bytes.fromhex(hash_hex)
    except ValueError:
        return False
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt, _PBKDF2_ROUNDS
    )
    return hmac_compare(digest, expect)


def hmac_compare(a: bytes, b: bytes) -> bool:
    import hmac as _hmac

    return _hmac.compare_digest(a, b)


def normalize_email(email: str) -> str:
    return email.strip().lower()


def get_user(email: str) -> dict[str, Any] | None:
    email_n = normalize_email(email)
    with _LOCK:
        store = _load()
        u = store["users"].get(email_n)
        if not isinstance(u, dict):
            return None
        return dict(u)


def public_user(u: dict[str, Any]) -> dict[str, Any]:
    return {
        "email": u.get("email"),
        "name": u.get("name") or None,
        "plan": u.get("plan") or "free",
        "created_at": u.get("created_at"),
    }


def register_user(
    email: str,
    password: str,
    *,
    name: str | None = None,
    plan: str = "free",
) -> dict[str, Any]:
    if not password_auth_enabled():
        raise RuntimeError("password auth disabled")
    if not registration_open():
        raise RuntimeError("registration closed")
    email_n = normalize_email(email)
    if not _EMAIL_RE.match(email_n):
        raise ValueError("invalid email")
    if len(password) < 8:
        raise ValueError("password must be at least 8 characters")
    salt_hex, hash_hex = _hash_password(password)
    with _LOCK:
        store = _load()
        if email_n in store["users"]:
            raise ValueError("email already registered")
        rec = {
            "email": email_n,
            "name": (name or email_n.split("@")[0]).strip()[:80],
            "plan": plan or "free",
            "salt": salt_hex,
            "password_hash": hash_hex,
            "created_at": time.time(),
            "auth": "password",
        }
        store["users"][email_n] = rec
        _save(store)
        return public_user(rec)


def authenticate(email: str, password: str) -> dict[str, Any]:
    if not password_auth_enabled():
        raise RuntimeError("password auth disabled")
    email_n = normalize_email(email)
    with _LOCK:
        store = _load()
        u = store["users"].get(email_n)
        if not isinstance(u, dict):
            raise ValueError("invalid email or password")
        if not _verify(password, str(u.get("salt") or ""), str(u.get("password_hash") or "")):
            raise ValueError("invalid email or password")
        return public_user(u)


def ensure_bootstrap_admin() -> dict[str, Any] | None:
    """Create admin from env if set and missing. Returns public user if created/exists."""
    email = os.environ.get("QUANTRADAR_ADMIN_EMAIL", "").strip()
    password = os.environ.get("QUANTRADAR_ADMIN_PASSWORD", "").strip()
    if not email or not password:
        # Local default for easy first login (only if no users yet)
        if os.environ.get("QUANTRADAR_BOOTSTRAP_DEMO", "1").strip().lower() in {
            "0",
            "false",
            "no",
        }:
            return None
        with _LOCK:
            store = _load()
            if store["users"]:
                return None
        email = "admin@local.test"
        password = "quantradar"
    try:
        existing = get_user(email)
        if existing:
            return existing
        # force create even if registration closed
        email_n = normalize_email(email)
        salt_hex, hash_hex = _hash_password(password)
        with _LOCK:
            store = _load()
            if email_n in store["users"]:
                return public_user(store["users"][email_n])
            rec = {
                "email": email_n,
                "name": "Admin",
                "plan": "free",
                "salt": salt_hex,
                "password_hash": hash_hex,
                "created_at": time.time(),
                "auth": "password",
                "bootstrap": True,
            }
            store["users"][email_n] = rec
            _save(store)
            return public_user(rec)
    except Exception:
        return None


def count_users() -> int:
    with _LOCK:
        return len(_load().get("users") or {})
