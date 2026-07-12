#!/usr/bin/env python3
"""Create/deploy quantradar-shell on Render Free plan only ($0 compute).

Requires:
  - `render login` done (reads ~/.render/cli.yaml)
  - Payment method on file (Render requires card even for Free; Free plan is $0)

Usage:
  python3 scripts/render_deploy_free.py
  python3 scripts/render_deploy_free.py --wait
"""

from __future__ import annotations

import argparse
import json
import re
import secrets
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

CLI_YAML = Path.home() / ".render" / "cli.yaml"
OWNER_FALLBACK = "tea-d6virqnfte5s73dte8i0"
REPO = "https://github.com/Alexaliao001/quantradar"
NAME = "quantradar-shell"


def token_from_cli() -> str:
    text = CLI_YAML.read_text()
    m = re.search(r"key:\s*(rnd_\S+)", text)
    if not m:
        raise SystemExit("No Render API key. Run: render login")
    return m.group(1)


def api(token: str, method: str, path: str, body=None):
    url = "https://api.render.com/v1" + path
    data = None if body is None else json.dumps(body).encode()
    req = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            raw = r.read().decode()
            return r.status, json.loads(raw) if raw else None
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()


def owner_id(token: str) -> str:
    st, body = api(token, "GET", "/owners?limit=20")
    if st != 200 or not isinstance(body, list) or not body:
        return OWNER_FALLBACK
    o0 = body[0]
    return (o0.get("owner") or o0).get("id") or OWNER_FALLBACK


def find_service(token: str, name: str = NAME):
    st, body = api(token, "GET", "/services?limit=50")
    if st != 200 or not isinstance(body, list):
        return None
    for item in body:
        s = item.get("service") or item
        if s.get("name") == name:
            return s
    return None


def create_free(token: str) -> dict:
    payload = {
        "type": "web_service",
        "name": NAME,
        "ownerId": owner_id(token),
        "repo": REPO,
        "branch": "main",
        "autoDeploy": "yes",
        "envVars": [
            {"key": "HOST", "value": "0.0.0.0"},
            {"key": "QUANTRADAR_MODE", "value": "artifact"},
            {"key": "PUBLIC_BASE_URL", "value": "https://quantradar.one"},
            {"key": "SESSION_SECRET", "value": secrets.token_urlsafe(48)},
            {"key": "QUANTRADAR_DEV_LOGIN", "value": "0"},
            {"key": "QUANTRADAR_BOOTSTRAP_DEMO", "value": "0"},
            {"key": "PYTHON_VERSION", "value": "3.12.8"},
        ],
        "serviceDetails": {
            "env": "python",
            "runtime": "python",
            "plan": "free",  # $0 — never starter/standard
            "region": "oregon",
            "numInstances": 1,
            "healthCheckPath": "/health",
            "envSpecificDetails": {
                "buildCommand": "python -c \"print('ok')\"",
                "startCommand": "python -m app",
            },
        },
    }
    st, body = api(token, "POST", "/services", payload)
    if st in (200, 201) and isinstance(body, dict):
        return body.get("service") or body
    msg = body if isinstance(body, str) else json.dumps(body)
    if "Payment" in msg or st == 402:
        raise SystemExit(
            "Render still requires a payment method on file (even for Free).\n"
            "Open https://dashboard.render.com/billing → Add payment method.\n"
            "Free instance is $0/month; card is for verification / overage only.\n"
            f"API: {st} {msg[:300]}"
        )
    raise SystemExit(f"Create failed: {st} {msg[:500]}")


def service_url(svc: dict) -> str | None:
    sd = svc.get("serviceDetails") or {}
    return sd.get("url") or svc.get("serviceDetails", {}).get("url")


def wait_live(url: str, timeout: int = 600) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            req = urllib.request.Request(url.rstrip("/") + "/health", method="GET")
            with urllib.request.urlopen(req, timeout=20) as r:
                j = json.loads(r.read().decode())
                if j.get("service") == "quantradar-shell":
                    print("LIVE", json.dumps(j, ensure_ascii=False)[:400])
                    return True
                print("health shape", j)
        except Exception as e:
            print("waiting…", type(e).__name__, e)
        time.sleep(15)
    return False


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--wait", action="store_true", help="poll /health until live")
    args = ap.parse_args()

    token = token_from_cli()
    svc = find_service(token)
    if svc:
        print("exists", svc.get("id"), service_url(svc), "plan=", (svc.get("serviceDetails") or {}).get("plan"))
    else:
        print("creating FREE service", NAME, "…")
        svc = create_free(token)
        print(
            "created",
            svc.get("id"),
            "plan=",
            (svc.get("serviceDetails") or {}).get("plan"),
            "url=",
            service_url(svc),
        )
        if (svc.get("serviceDetails") or {}).get("plan") not in (None, "free"):
            print("WARNING: plan is not free — check dashboard", file=sys.stderr)

    url = service_url(svc)
    sid = svc.get("id")
    print("dashboard", f"https://dashboard.render.com/web/{sid}")
    if url:
        print("url", url)
    if args.wait and url:
        ok = wait_live(url)
        sys.exit(0 if ok else 2)


if __name__ == "__main__":
    main()
