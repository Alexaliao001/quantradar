# moyu-fortune-deploy

Public mirror for **https://chillworks.ai** (GH Pages) + Render Free backup.

| Branch | Role |
|--------|------|
| `gh-pages` | Production (`CNAME=chillworks.ai`) — keep CNAME |
| `main` | Render `moyu-fortune` static host |

## Rebuild / push

```bash
bash ~/quantradar/scripts/rebuild_static.sh moyu
```

Source: `~/moyu-fortune` (private). Path A = static frontend only (SX2).

## Verify

```bash
curl -sS https://chillworks.ai/ | head
python3 ~/quantradar/scripts/sites_extreme_verify.py
```
