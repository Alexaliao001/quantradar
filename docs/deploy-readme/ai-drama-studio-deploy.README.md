# ai-drama-studio-deploy

Public mirror for **https://shorts.fortunesite.one** (GH Pages static demo · SX4).

| Branch | Role |
|--------|------|
| `gh-pages` | Production (`CNAME=shorts.fortunesite.one`) |
| `main` | Render `ai-drama-studio` backup |

## Rebuild / push

```bash
bash ~/quantradar/scripts/rebuild_static.sh drama
```

Full Kling/video backend is **out of scope** unless paid API authorized.

## Verify

```bash
curl -sS https://shorts.fortunesite.one/version.json
curl -sS -o /dev/null -w '%{http_code}\n' https://shorts.fortunesite.one/demo
python3 ~/quantradar/scripts/sites_extreme_verify.py
```
