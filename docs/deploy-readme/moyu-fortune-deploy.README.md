# moyu-fortune-deploy

Public mirror for **https://chillworks.ai** (GH Pages) + Render Free **moyu-light** API.

| Branch | Role |
|--------|------|
| `gh-pages` | Production frontend (`CNAME=chillworks.ai`) — keep CNAME |
| `main` | Render Free `moyu-fortune` → `dist/light.js` API only |

Topology: frontend GH Pages; API `https://moyu-fortune.onrender.com` (no Hobby custom domain).

Layout note: Fortune Insight has deploy-only (`~/fortune-insight-deploy`), no local SSOT source repo.

## Rebuild / push

```bash
# Frontend (gh-pages) — set API base for Path B
cd ~/moyu-fortune
VITE_STATIC_MODE=true VITE_MOYU_API_BASE=https://moyu-fortune.onrender.com pnpm build
# then sync dist/public → moyu-fortune-deploy gh-pages ONLY
# (do NOT run rebuild_static.sh moyu — it overwrites main light API with static host)

# Light API (main)
cd ~/moyu-fortune && pnpm run build:light
cp dist/light.js ~/moyu-fortune-deploy/dist/light.js
# package.json start must be: node dist/light.js
# optional Render env: LIBSQL_URL + LIBSQL_AUTH_TOKEN
```

Source: `~/moyu-fortune` (private). Path B2 = draw/history/leaderboard/feedback/invite/profile.

## Verify

```bash
curl -sS https://moyu-fortune.onrender.com/health   # service=moyu-light
curl -sS -X POST https://moyu-fortune.onrender.com/api/light/feedback \
  -H 'content-type: application/json' \
  -d '{"type":"suggestion","content":"ping","deviceId":"verify"}'
curl -sS 'https://moyu-fortune.onrender.com/api/light/invite?deviceId=verify'
curl -sS https://chillworks.ai/version.json
python3 ~/quantradar/scripts/sites_extreme_verify.py
```
