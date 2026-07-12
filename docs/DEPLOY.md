# Deploy QuantRadar shell (path C) to production

## What is ready in-repo

| Piece | File |
|-------|------|
| App | `python -m app` |
| Docker | `Dockerfile` |
| Render Blueprint | `render.yaml` |
| Fly.io | `fly.toml` |
| Env bootstrap | `scripts/bootstrap_env.py` |
| Auth | Google OAuth **and/or** email magic link |
| Billing | Stripe Checkout when `QUANTRADAR_STRIPE_SECRET_KEY` set |

## Local production-like

```bash
cd ~/quantradar
python3 scripts/bootstrap_env.py
# optional: edit .env — add GOOGLE_* / SMTP_* / PUBLIC_BASE_URL
python3 -m app
python3 scripts/p0_smoke.py --base http://127.0.0.1:8765
```

Magic link without SMTP: submit email on `/login` → link printed in server log and `data/last_magic_link.txt`.

## Render (recommended; matches charts history)

1. https://dashboard.render.com → New → Blueprint  
2. Connect `Alexaliao001/quantradar`  
3. Set secrets: `SESSION_SECRET` (auto), `GOOGLE_*` (optional), `QUANTRADAR_STRIPE_SECRET_KEY`, `PUBLIC_BASE_URL=https://quantradar.one`  
4. Deploy → note `*.onrender.com` URL  
5. Custom domain: add `quantradar.one` + `www`  
6. DNS (Cloudflare / Manus domain panel): CNAME or A as Render shows  
7. Google Console redirect: `https://quantradar.one/api/auth/google/callback`

## Fly.io

```bash
brew install flyctl
flyctl auth login
cd ~/quantradar
flyctl launch --config fly.toml --no-deploy
flyctl secrets set SESSION_SECRET=... PUBLIC_BASE_URL=https://quantradar.one \
  QUANTRADAR_STRIPE_SECRET_KEY=... 
# optional GOOGLE_CLIENT_ID / GOOGLE_CLIENT_SECRET / SMTP_*
flyctl deploy
flyctl certs add quantradar.one
```

## Cutover checklist

- [ ] `/health` → `service=quantradar-shell`, `manus_login=false`
- [ ] `/login` works (Google and/or magic)
- [ ] `/api/analyze?ticker=XXXX` not a fake buy
- [ ] `/api/oauth/callback` → 410
- [ ] No `manus.im/app-auth` in browser Network
- [ ] `python3 scripts/p0_smoke.py --live` PASS

## Blocked without your click

These cannot be completed by an agent alone:

1. **Google Cloud** OAuth client creation (browser consent)  
2. **Fly/Render** account login  
3. **DNS** at Cloudflare/Manus for `quantradar.one`  
4. **Manus** platform disable App Auth / rebind domain  

In-repo code + env + deploy manifests are complete; domain cutover is the remaining human step.
