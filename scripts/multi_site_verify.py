#!/usr/bin/env python3
"""Verify multi-site migration surfaces (Render Free + optional custom domains)."""
from __future__ import annotations

import json
import re
import ssl
import sys
import urllib.error
import urllib.request
from pathlib import Path

CTX = ssl.create_default_context()

SITES = [
    {
        "name": "quantradar",
        "urls": [
            "https://quantradar.one",
            "https://quantradar-shell.onrender.com",
        ],
        "title_has": ["QuantRadar", "quantradar"],
        "health": "https://quantradar.one/health",
        "health_expect": {"service": "quantradar-shell"},
    },
    {
        "name": "moyu / chillworks",
        "urls": [
            "https://moyu-fortune.onrender.com",
            "https://chillworks.ai",
        ],
        "title_has": ["摸了么", "MoYu", "摸鱼"],
    },
    {
        "name": "fortune insight",
        "urls": [
            "https://fortune-insight.onrender.com",
            "https://fortunesite.one",
        ],
        "title_has": ["Fortune Insight", "Tarot", "BaZi"],
    },
    {
        "name": "portfolio",
        "urls": [
            "https://rongjian-portfolio.onrender.com",
        ],
        "title_has": ["Rongjian", "Portfolio"],
    },
]


def fetch(url: str, timeout: float = 60.0) -> tuple[int, str, dict]:
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "multi-site-verify/1.0"},
        method="GET",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=CTX) as r:
            body = r.read().decode("utf-8", errors="replace")
            return r.status, body, dict(r.headers)
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        return e.code, body, dict(e.headers)
    except Exception as e:
        return 0, str(e), {}


def title_of(html: str) -> str:
    m = re.search(r"<title>([^<]+)", html, re.I)
    return (m.group(1).strip() if m else "")[:80]


def main() -> int:
    ok_all = True
    print("=== multi-site verify ===\n")
    for site in SITES:
        print(f"## {site['name']}")
        any_ok = False
        for url in site["urls"]:
            code, body, _ = fetch(url)
            title = title_of(body) if code == 200 else ""
            title_ok = any(t.lower() in title.lower() for t in site["title_has"]) if title else False
            # onrender preview is required; custom domain optional until cutover
            is_preview = "onrender.com" in url or "quantradar.one" in url
            if code == 200 and (title_ok or not site["title_has"]):
                status = "PASS"
                if is_preview or "quantradar.one" in url:
                    any_ok = True
            elif code == 200:
                status = "WARN title?"
                any_ok = any_ok or is_preview
            else:
                status = "FAIL" if is_preview else "PENDING(dns)"
                if is_preview:
                    ok_all = False
            print(f"  [{status:12}] {code:3}  {url}")
            if title:
                print(f"               title: {title}")
            if code == 0:
                print(f"               err: {body[:120]}")

        if site.get("health"):
            code, body, _ = fetch(site["health"])
            try:
                data = json.loads(body) if code == 200 else {}
            except json.JSONDecodeError:
                data = {}
            expect = site.get("health_expect") or {}
            health_ok = code == 200 and all(data.get(k) == v for k, v in expect.items())
            print(
                f"  [{'PASS' if health_ok else 'FAIL':12}] health {data if data else body[:80]}"
            )
            if not health_ok:
                ok_all = False

        if not any_ok:
            ok_all = False
        print()

    # Render custom domain status (optional)
    cli = Path.home() / ".render" / "cli.yaml"
    if cli.exists():
        token_m = re.search(r"key:\s*(rnd_\S+)", cli.read_text())
        if token_m:
            token = token_m.group(1)
            print("## Render custom domains")
            for sid, name in [
                ("srv-d99nc357vvec73frpus0", "quantradar-shell"),
                ("srv-d99uh33tqb8s73b79pj0", "moyu-fortune"),
                ("srv-d99uh3m7r5hc73bth4a0", "fortune-insight"),
                ("srv-d99uh4ecjfls738ue8s0", "rongjian-portfolio"),
            ]:
                req = urllib.request.Request(
                    f"https://api.render.com/v1/services/{sid}/custom-domains",
                    headers={
                        "Authorization": f"Bearer {token}",
                        "Accept": "application/json",
                    },
                )
                try:
                    with urllib.request.urlopen(req, timeout=30) as r:
                        items = json.loads(r.read().decode())
                except Exception as e:
                    print(f"  {name}: api err {e}")
                    continue
                if not items:
                    print(f"  {name}: (no custom domains)")
                    continue
                for it in items:
                    cd = it.get("customDomain") or it
                    print(
                        f"  {name}: {cd.get('name')} → {cd.get('verificationStatus')}"
                    )
            print()

    print("RESULT:", "PASS (previews live)" if ok_all else "FAIL")
    print("Custom-domain PENDING is OK until you finish DNS + Manus unbind.")
    print("See docs/MULTI_SITE_MIGRATION.md")
    return 0 if ok_all else 1


if __name__ == "__main__":
    raise SystemExit(main())
