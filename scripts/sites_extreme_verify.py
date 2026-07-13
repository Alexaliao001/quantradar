#!/usr/bin/env python3
"""SITES EXTREME — production surface verification.

Usage:
  python3 ~/quantradar/scripts/sites_extreme_verify.py
  python3 ~/quantradar/scripts/sites_extreme_verify.py --json
"""
from __future__ import annotations

import argparse
import json
import re
import ssl
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import asdict, dataclass

CTX = ssl.create_default_context()

UA = "sites-extreme-verify/1.0"


@dataclass
class Check:
    name: str
    ok: bool
    detail: str


SITES = [
    {
        "name": "quantradar",
        "url": "https://quantradar.one",
        "title_any": ["QuantRadar"],
        "health": "https://quantradar.one/health",
        "health_expect": {"service": "quantradar-shell", "manus_login": False},
        "cert_cn_any": ["quantradar.one"],
    },
    {
        "name": "fortune",
        "url": "https://fortunesite.one",
        "title_any": ["Fortune Insight"],
        "cert_cn_any": ["fortunesite.one"],
    },
    {
        "name": "fortune-www",
        "url": "https://www.fortunesite.one",
        "title_any": ["Fortune Insight"],
        "cert_cn_any": ["fortunesite.one", "www.fortunesite.one"],
    },
    {
        "name": "moyu",
        "url": "https://chillworks.ai",
        "title_any": ["摸了么", "MoYu", "摸鱼"],
        "cert_cn_any": ["chillworks.ai"],
    },
    {
        "name": "portfolio",
        "url": "https://rj.fortunesite.one",
        "title_any": ["Rongjian", "Portfolio"],
        "cert_cn_any": ["rj.fortunesite.one"],
    },
    {
        "name": "drama",
        "url": "https://shorts.fortunesite.one",
        "title_any": ["Drama", "短剧", "AI Drama"],
        "cert_cn_any": ["shorts.fortunesite.one"],
        "bundle_forbid": ["undefined/app-auth"],
    },
    {
        "name": "qr-onrender",
        "url": "https://quantradar-shell.onrender.com",
        "title_any": ["QuantRadar"],
        "optional": True,
    },
    {
        "name": "fortune-onrender",
        "url": "https://fortune-insight.onrender.com",
        "title_any": ["Fortune Insight"],
        "optional": True,
    },
    {
        "name": "moyu-onrender",
        "url": "https://moyu-fortune.onrender.com",
        "title_any": ["摸了么", "MoYu", "摸鱼"],
        "optional": True,
    },
    {
        "name": "portfolio-onrender",
        "url": "https://rongjian-portfolio.onrender.com",
        "title_any": ["Rongjian", "Portfolio"],
        "optional": True,
    },
    {
        "name": "drama-onrender",
        "url": "https://ai-drama-studio.onrender.com",
        "title_any": ["Drama", "短剧"],
        "optional": True,
    },
]


def fetch(url: str, timeout: float = 45.0) -> tuple[int, str]:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=CTX) as r:
            return r.status, r.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        return e.code, body
    except Exception as e:
        return 0, str(e)


def is_tls_flake(code: int, body: str) -> bool:
    if code != 0:
        return False
    b = body.lower()
    return any(
        k in b
        for k in (
            "eof occurred in violation of protocol",
            "ssl",
            "certificate",
            "timed out",
            "temporary failure",
            "connection reset",
            "network is unreachable",
        )
    )


def fetch_with_retry(url: str, attempts: int = 3, timeout: float = 45.0) -> tuple[int, str]:
    last = (0, "")
    for i in range(attempts):
        last = fetch(url, timeout=timeout)
        if last[0] == 200:
            return last
        if last[0] != 0 and not is_tls_flake(last[0], last[1]):
            return last
        if i + 1 < attempts:
            import time
            time.sleep(2 + i * 2)
    return last


def title_of(html: str) -> str:
    m = re.search(r"<title>([^<]+)", html, re.I)
    return (m.group(1).strip() if m else "")[:100]


def cert_subject(host: str) -> str:
    try:
        out = subprocess.check_output(
            [
                "openssl",
                "s_client",
                "-servername",
                host,
                "-connect",
                f"{host}:443",
            ],
            input=b"",
            stderr=subprocess.DEVNULL,
            timeout=25,
        )
        # pipe to x509
        p = subprocess.run(
            ["openssl", "x509", "-noout", "-subject"],
            input=out,
            capture_output=True,
            timeout=10,
        )
        return p.stdout.decode(errors="replace").strip()
    except Exception as e:
        return f"ERR:{e}"


def host_of(url: str) -> str:
    return urllib.request.urlparse(url).hostname or ""


def check_site(site: dict) -> list[Check]:
    checks: list[Check] = []
    name = site["name"]
    url = site["url"]
    optional = bool(site.get("optional"))

    code, body = fetch_with_retry(url)
    title = title_of(body) if code == 200 else ""
    title_ok = any(t.lower() in title.lower() for t in site.get("title_any") or [""])
    if code == 200 and (title_ok or not site.get("title_any")):
        checks.append(Check(f"{name}.http", True, f"200 title={title!r}"))
    else:
        checks.append(
            Check(
                f"{name}.http",
                optional and code != 0,
                f"code={code} title={title!r} body={body[:80]!r}",
            )
        )
        if optional:
            # soft-fail optional
            checks[-1] = Check(f"{name}.http", True, f"optional soft code={code}")

    if site.get("health"):
        hc, hb = fetch_with_retry(site["health"])
        try:
            data = json.loads(hb) if hc == 200 else {}
        except json.JSONDecodeError:
            data = {}
        expect = site.get("health_expect") or {}
        ok = hc == 200 and all(data.get(k) == v for k, v in expect.items())
        detail = json.dumps(data, ensure_ascii=False)[:200] if data else hb[:120]
        if code != 200 and hc == 200:
            detail = f"homepage_code={code}; {detail}"
        checks.append(Check(f"{name}.health", ok, detail))

    # cert
    if site.get("cert_cn_any") and not optional:
        host = host_of(url)
        subj = cert_subject(host)
        cn_ok = any(cn.lower() in subj.lower() for cn in site["cert_cn_any"])
        # also accept if subject has the host
        cn_ok = cn_ok or host.lower() in subj.lower()
        checks.append(Check(f"{name}.cert", cn_ok, subj or "no-cert"))

    # bundle forbid
    if site.get("bundle_forbid") and code == 200:
        js_paths = re.findall(r'src="(/assets/[^"]+\.js)"', body)
        bad = []
        for jp in js_paths[:3]:
            jc, jb = fetch(urllib.parse.urljoin(url, jp))
            if jc != 200:
                continue
            for frag in site["bundle_forbid"]:
                if frag in jb:
                    bad.append(f"{jp}:{frag}")
        checks.append(
            Check(f"{name}.bundle", len(bad) == 0, "clean" if not bad else ",".join(bad))
        )

    return checks


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    all_checks: list[Check] = []
    for site in SITES:
        all_checks.extend(check_site(site))

    if args.json:
        print(json.dumps([asdict(c) for c in all_checks], ensure_ascii=False, indent=2))
    else:
        print("=== sites_extreme_verify ===\n")
        width = max(len(c.name) for c in all_checks)
        for c in all_checks:
            flag = "PASS" if c.ok else "FAIL"
            print(f"[{flag}] {c.name.ljust(width)}  {c.detail[:120]}")
        failed = [c for c in all_checks if not c.ok]
        print()
        if failed:
            print(f"RESULT: FAIL ({len(failed)} checks)")
            return 1
        print("RESULT: PASS")
        return 0

    return 0 if all(c.ok for c in all_checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
