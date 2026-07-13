# fortune-insight-deploy

Public mirror / Render source for **https://fortunesite.one**.

| Surface | Host |
|---------|------|
| Production app + SX3 `POST /api/tarot/preview` | Render Free `fortune-insight` (**Hobby domain**) |
| Optional static GH | `gh-pages` (historical / fallback) |

## Source of truth

| Role | Repo | Local |
|------|------|-------|
| **SSOT (edit here)** | private `Alexaliao001/fortune-insight` | `~/fortune-insight` |
| **Deploy (Render)** | public `Alexaliao001/fortune-insight-deploy` | `~/fortune-insight-deploy` |
| Archive (do not edit) | private `Alexaliao001/fortune-insight-` (trailing `-`) | — |

Sync:

```bash
bash ~/quantradar/scripts/sync_fortune_deploy.sh
```

This keeps deploy `package.json` / `render.yaml` as the **zero-dep host** (`server/host.mjs`), and copies SSOT product + SX3 files.

## Rebuild / push (app)

Prefer SSOT + sync script above. Manual:

```bash
cd ~/fortune-insight   # edit / build full product
bash ~/quantradar/scripts/sync_fortune_deploy.sh
# Render auto-deploys from fortune-insight-deploy main
```

Env: see `~/quantradar/docs/env/fortune-insight.env.example` and SSOT `.env.example`.

## Static-only note

Do not use `rebuild_static.sh` for Fortune production — that helper is for MoYu / Portfolio / Drama GH statics.

## Verify

```bash
curl -sS https://fortunesite.one/health
curl -sS -X POST https://fortunesite.one/api/tarot/preview -H 'content-type: application/json' -d '{}'
python3 ~/quantradar/scripts/sites_extreme_verify.py
```
