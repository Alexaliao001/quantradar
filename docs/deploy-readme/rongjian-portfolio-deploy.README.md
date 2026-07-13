# rongjian-portfolio-deploy

Public mirror for **https://rj.fortunesite.one** (GH Pages) + Render Free backup.

| Branch | Role |
|--------|------|
| `gh-pages` | Production static (`CNAME=rj.fortunesite.one`) |
| `main` | Render `rongjian-portfolio` — zero-dep `dist/index.js` + `dist/public/` |

## Rebuild / push

```bash
# Preferred (from quantradar SX6 helper)
bash ~/quantradar/scripts/rebuild_static.sh portfolio

# Manual
cd ~/rongjian-portfolio
PORTFOLIO_STATIC=1 pnpm exec vite build
# then sync dist/public → this repo main + gh-pages
# CRITICAL: dist/index.js must be scripts/static_host_index.js (no express)
```

Do **not** copy the source repo’s esbuild `dist/index.js` (express) — Render will `update_failed`.

## Verify

```bash
curl -sS https://rj.fortunesite.one/version.json
python3 ~/quantradar/scripts/sites_extreme_verify.py
```
