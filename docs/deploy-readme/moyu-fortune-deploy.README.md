# moyu-fortune-deploy

Public mirror for **https://chillworks.ai** (GH Pages) + Render Free **moyu-light** API.

| Branch | Role |
|--------|------|
| `gh-pages` | Production frontend (`CNAME=chillworks.ai`) — keep CNAME |
| `main` | Render Free `moyu-fortune` → `dist/light.js` API only |

Topology: frontend GH Pages; API `https://moyu-fortune.onrender.com` (no Hobby custom domain).

## Rebuild / push

```bash
# Frontend (gh-pages) — set API base for Path B
cd ~/moyu-fortune
VITE_STATIC_MODE=true VITE_MOYU_API_BASE=https://moyu-fortune.onrender.com pnpm build
# then sync dist/public → moyu-fortune-deploy gh-pages (see rebuild_static.sh; do not wipe main light API)

# Light API (main)
cd ~/moyu-fortune && pnpm run build:light
cp dist/light.js ~/moyu-fortune-deploy/dist/light.js
# package.json start must be: node dist/light.js
```

Source: `~/moyu-fortune` (private). Path A = static; Path B = light REST (SX2-2).

## Verify

```bash
curl -sS https://moyu-fortune.onrender.com/health   # service=moyu-light
curl -sS https://chillworks.ai/version.json
python3 ~/quantradar/scripts/sites_extreme_verify.py
```
