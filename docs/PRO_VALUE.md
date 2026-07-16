# Pro value adjudication (QD1-0)

> **Verdict: B — supporter price until charts are mounted.**  
> Date: 2026-07-16 · Host: `quantradar.one` (Render Free `quantradar-shell`)

## Decision

| Question | Answer |
|----------|--------|
| Can this production host mount `~/charts` and run `mode=live` today? | **No** |
| May we sell Pro as “live desk available now”? | **No** |
| What is Pro today? | **Supporter plan**: session + higher limits + **automatic live unlock** when `/health.charts_status == "mounted"` |
| When does verdict flip to A? | Paid/always-on host with real `CHARTS_DIR` + `fetch_all.py` + Massive/Polygon key (never in git) + smoke Pro live without artifact fallback |

## Production evidence (2026-07-16)

`GET https://quantradar.one/health`:

| Field | Value |
|-------|-------|
| `charts_status` | `artifact_only` |
| `charts_reachable` | `false` |
| `fetch_all_present` | `false` |
| `data_path` | `artifact_fixtures` |
| `mode_default` | `artifact` |

Matches `docs/SITES_LIVE.md` / `render.yaml` (`plan: free`, `QUANTRADAR_MODE=artifact`, no charts tree in Dockerfile).

## Why Free cannot run live (honest constraints)

1. **No charts tree** on the shell image — only `fixtures/charts_sample`.
2. **Charts deps** (pandas/matplotlib/requests) are outside the stdlib-only shell design.
3. **Cold start + 10–20s fetch** is a bad fit for Render Free sleep.
4. **Massive/Polygon personal keys** must not power a public raw-feed product (conclusions-only policy).

## Path to verdict A (later ops)

Document only — not implemented on Free:

1. Separate always-on host (or paid plan) with disk + charts checkout.
2. Set `CHARTS_DIR` to a directory containing `fetch_all.py`.
3. Inject `POLYGON_API_KEY` on that host only (never commit).
4. Keep default `QUANTRADAR_MODE=artifact`; allow Pro `mode=live`.
5. Accept only when `/health` shows `charts_status=mounted` **and** a Pro session live run returns non-artifact data without silent fake scores.

Until then, UI + `/health.pro_value` stay on **`supporter_until_mount`**.

## Product copy (locked by this verdict)

- Free = frozen demo artifacts. Not a live market feed.
- Pro = supporter price ($29/mo · $249/yr). Live **auto-unlocks** when engine is mounted — not sold as available on this host today.
- Server gates (login + `plan=pro` for live) remain so A can turn on without a billing rewrite.

## Related backlog

- QD5-0 / QR2-1 — free OHLCV refresh path (Yahoo) so Pro has tangible refresh value without Massive.
- QD1-1 — Stripe production prices/webhook (money path; value stance is this doc).
