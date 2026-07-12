# Cutover status (2026-07-12)

## Working now

| Surface | URL | Status |
|---------|-----|--------|
| Path-C shell (public tunnel) | https://hwy-regional-registry-wings.trycloudflare.com | **LIVE** `quantradar-shell` v0.5 Trust Gate |
| Local | http://127.0.0.1:8765 | Same process |
| Production domain | https://quantradar.one | **Still old Manus SPA** |

## Blockers for quantradar.one

1. **DNS NS** = `ns1/ns2.globaldomaingroup.com` (not Cloudflare account `liaor@merrimack.edu`, which has **zero zones**).
2. Domain currently fronts Manus app via CF edge IP `104.18.26.246` — managed by Manus/host stack, not personal CF account.
3. Fly.io requires credit card for launch.
4. Render requires email verification (`liaorongjian@outlook.com` — not found in connected Outlook).
5. Manus task waiting for CF API token / Worker reverse-proxy config.

## What to do next (pick one)

### A. Fastest permanent: Render free + DNS at GlobalDomain

1. Verify Render email, Blueprint: `Alexaliao001/quantradar` (`render.yaml` native Python).
2. Get `https://quantradar-shell.onrender.com`.
3. At **globaldomaingroup** DNS for `quantradar.one`: CNAME/A per Render custom domain instructions.
4. Disable Manus publish for that hostname.

### B. Manus Worker reverse-proxy

1. Manus has origin: `https://hwy-regional-registry-wings.trycloudflare.com` (temporary).
2. Replace with Render URL when ready.
3. Point Manus custom domain routing to Worker.

### C. Move zone to personal Cloudflare

1. Add `quantradar.one` to CF account.
2. Change nameservers at GlobalDomain to CF NS.
3. Tunnel or Pages+container + custom hostname.

## Tunnel note

Quick tunnel URL changes when `cloudflared` restarts. Not for production; only for proof + Manus wiring tests.
