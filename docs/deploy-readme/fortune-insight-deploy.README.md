# fortune-insight-deploy

Public mirror / Render source for **https://fortunesite.one**.

| Surface | Host |
|---------|------|
| Production app + SX3 `POST /api/tarot/preview` | Render Free `fortune-insight` (**Hobby domain**) |
| Optional static GH | `gh-pages` (historical / fallback) |

This is **not** a pure static site: main has Node server + tarot preview.

## Rebuild / push (app)

```bash
# From private source (if present) or this mirror when it IS the build tree:
cd ~/fortune-insight-deploy   # or private fortune-insight
pnpm install
pnpm build
git add -A && git commit -m "deploy: fortune …" && git push origin main
# Render auto-deploys from main
```

Env: see `~/quantradar/docs/env/fortune-insight.env.example` and local `.env.example`.

## Static-only note

Do not use `rebuild_static.sh` for Fortune production — that helper is for MoYu / Portfolio / Drama GH statics.

## Verify

```bash
curl -sS https://fortunesite.one/health
curl -sS -X POST https://fortunesite.one/api/tarot/preview -H 'content-type: application/json' -d '{}'
python3 ~/quantradar/scripts/sites_extreme_verify.py
```
