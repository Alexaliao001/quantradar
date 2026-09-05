# Pro value adjudication (QD1-0)

> **Verdict: A — live is open to everyone; Pro is the supporter tier.**
> Date: 2026-09-01 · Host: `quantradar.one` (Nube.sh VPS, stdlib-only shell + free engine)

## Decision

| Question | Answer |
|----------|--------|
| Can this production host run `mode=live` today? | **Yes** — free multi-source engine (`free_engine/fetch_all.py`) mounted via `CHARTS_DIR` |
| Who may run live? | **Everyone** — guests included; per-IP guest budget (`QUANTRADAR_LIVE_GUEST_RATE`, default 6/window) protects the shared data path |
| What is Pro today? | **Supporter tier**: higher rate limits + keeps the free engine running. Not a gate on live. |
| What flipped the verdict? | Polygon replaced by a free consensus engine (Yahoo q1/q2 + Nasdaq) ported 1:1 from the iOS `FreeMechanicalScorer`; `/health.charts_status == "mounted"`; guest live smoke-verified in production |

## Production evidence (2026-09-01)

`GET https://quantradar.one/health`:

| Field | Value |
|-------|-------|
| `charts_status` | `mounted` |
| `charts_reachable` | `true` |
| `fetch_all_present` | `true` |
| `data_path` | `charts_engine` |
| `mode_default` | `live` |
| `live_requires_login` | `false` |
| `live_requires_pro` | `false` |

## Honesty constraints (unchanged)

1. **No fake scores** — live fails closed (`ok:false`) when sources disagree or the engine errors; artifact fallback is labeled `degraded` with an explicit warning.
2. **Options never sold as actionable** without a live chain (`options_actionable` honesty gate).
3. **No paid-API keys in the public path** — the free engine uses only public endpoints (Yahoo query1/query2, Nasdaq.com); no Polygon/Massive key required.
4. **Guest budget** — a single IP cannot burn host + upstream capacity; signed-in users (any plan) get the normal authenticated budget, Pro the highest.

## Product copy (locked by this verdict)

- Free = live multi-source scans for any ticker (guest limits) + frozen demo artifacts (INTC/AAPL).
- Pro = supporter tier ($29/mo · $249/yr): higher limits, keeps the desk running. Never sold as "the only way to get live".
- Server gates: none on live; rate limits only. `plan_required`/`login_required` remain for checkout and `/api/me` only.

## Related backlog

- QD5-0 / QR2-1 — free OHLCV refresh path (Yahoo) — shipped as the free engine.
- QD1-1 — Stripe production prices/webhook (money path; value stance is this doc).
