#!/usr/bin/env python3
"""Poll until quantradar.one serves path-C shell; re-verify Render custom domains."""
from __future__ import annotations
import json, re, time, urllib.request
from pathlib import Path

token = re.search(r"key:\s*(rnd_\S+)", Path.home().joinpath(".render/cli.yaml").read_text()).group(1)
SID = "srv-d99nc357vvec73frpus0"
DOMAINS = [
    ("cdm-d99ptt8k1i2s73eip0e0", "quantradar.one"),
    ("cdm-d99ptt8k1i2s73eip0gg", "www.quantradar.one"),
]

def api(method, path, body=None):
    url = "https://api.render.com/v1" + path
    data = None if body is None else json.dumps(body).encode()
    req = urllib.request.Request(url, data=data, method=method, headers={
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
        "Content-Type": "application/json",
    })
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            raw = r.read().decode()
            return r.status, json.loads(raw) if raw else None
    except Exception as e:
        return getattr(e, "code", 0), str(e)

def health(host: str):
    try:
        with urllib.request.urlopen(host + "/health", timeout=20) as r:
            return json.loads(r.read().decode())
    except Exception as e:
        return {"error": str(e)}

def main():
    for i in range(60):
        for did, _ in DOMAINS:
            api("POST", f"/services/{SID}/custom-domains/{did}/verify", {})
        h = health("https://quantradar.one")
        print(f"[{i}] quantradar.one", h.get("service") or h.get("error") or h)
        if h.get("service") == "quantradar-shell":
            print("CUTOVER OK")
            print(json.dumps(h, indent=2)[:600])
            return 0
        time.sleep(30)
    return 1

if __name__ == "__main__":
    raise SystemExit(main())
