# Engagement & commercial closed-loop (QD1-5 · QD2 · QD4)

> **全流程设计 SSOT：** [`docs/FULL_FUNNEL_DESIGN.md`](FULL_FUNNEL_DESIGN.md)  
> Date: 2026-07-17 · Product: QuantRadar path-C shell  
> North-star: `GROK_GOAL_COMMERCIAL.md` N1–N5 · Trust Gate: `docs/TRUST_GATE.md`

## 1. Commercial closed-loop architecture

```text
Guest lands (/)
    │  ?demo=INTC auto-runs free artifact
    ▼
Demo / Analyze  ──funnel: demo_run | analyze_run──► data/funnel.jsonl
    │
    ├─ Verdict → Why → Gates → Breakdown → Freshness
    │
    ├─ WAIT / NO ──► Remind me (waitlist) ──funnel: notify_save
    │                 └── email loop later (QD3-3)
    │
    ├─ Liked read ──► Sign in / Register ──funnel: signup
    │                      │
    │                      ▼
    │                 Checkout ──funnel: checkout_start
    │                      │
    │                      ▼
    │                 Stripe webhook → plan=pro ──funnel: pro_active
    │                      │
    └──────────────────────┴──► Live (when charts mounted) ──funnel: live_run
```

| Stage | Product truth | Engagement hook |
|-------|---------------|-----------------|
| Demo | Frozen artifact, 0 credits | Score dial + gates + freeze label (Zeigarnik: not live) |
| WAIT/NO | Most days stand aside | Avoided-loss line + Remind me |
| Signup | Email/password (or magic/Google) | Login `next=checkout\|live` |
| Pro | Supporter until `charts_status=mounted` | Honest unlock copy — never sell air |
| Live | Pro + mounted engine | Re-check habit |

**Measure:** `python3 scripts/funnel_report.py` (server JSONL only; no third-party pixels; no raw emails).

## 2. Engagement techniques (honest)

| Lever | Implementation |
|-------|----------------|
| Loss aversion | `engagement.avoided_line` on WAIT/NO |
| Zeigarnik / freshness gap | `engagement.freeze_label` + live lock until mount |
| Anchoring | Pricing FAQ + yearly save ~28% + “−8% on $3k ≈ 8 mo Pro” |
| Commitment | Remind me waitlist on stand-aside results |
| Authority | Methodology link from Next; single `primary_score` |
| Loop | Next always offers re-check / another demo / upgrade |
| Posture honesty | Desk: mechanical posture ≠ direction; PUT ≠ sell (`docs/STOCK_AGENT_MAP.md`) |

**Forbidden:** fake counts, fake scarcity, cancel maze, forged freshness, selling live before mount, inventing gate `pass` from pct presence.

**Abuse caps:** `/api/sample` · `/api/notify` · `/api/auth/register` share analyze rate limits; `data/funnel.jsonl` capped via `QUANTRADAR_FUNNEL_MAX_BYTES` (default 5 MiB).

## 3. Frontend engagement plan

### Shipped this pass

- SVG score dial (one score only)
- Market → Sector → Stock gate tones
- Mechanical breakdown bars (`score.breakdown`)
- Avoided-line + freeze pill
- Next-block loop (remind / upgrade / analyze another)
- Mobile sticky Analyze controls
- Pricing FAQ + anchoring copy
- `/?demo=TICKER` deep link

### Motion system (QD2-3 · 2026-07-26)

Unified CSS motion language in `static/site.css` — deep charcoal + radar green, Syne + IBM Plex Mono. No third-party trackers; pure CSS/SVG + small desk JS.

| Token / keyframe | Role |
|------------------|------|
| `--motion-fast/base/slow/scan/stagger` | Shared timing |
| `qrSweep` + hero SVG | Cover radar sweep (ambient presence) |
| `deskIn` / `heroIn` | Panel & hero copy enter |
| `scanBeam` + `.desk-scan` | Loading presence while artifact/analyze runs |
| `gateLit` (staggered `.ev`) | Market → sector → stock light-up on ready |
| dial `stroke-dashoffset` | Score arc draw on ready |
| `bdGrow` | Breakdown bars grow from left |
| `verdictSweep` | Verdict label sweep highlight |
| `prefers-reduced-motion: reduce` | Disables ambient/looping motion; dial snaps |

**Cover `/`:** brand-level `QuantRadar` + SVG radar plane + one headline + one support + CTA (Try demo / Pricing). Demo chips stay below the first composition. Trust Gate unchanged: freeze labels, no fake social proof, supporter-until-mount.

**Pricing:** light `price-hero` brand mark + card enter / highlight sweep — same language, no new conversion tricks.

### Next (ordered)

| ID | Item | Lifts |
|----|------|-------|
| QD2-0 | Serve real chart PNGs when assets exist | N1 wow |
| QD1-1 | Stripe production prices + webhook | N3→N4 |
| QD3-3 | Email re-check sender + unsubscribe | N2 retention |
| QD2-5 | Share card `/r/{ticker}` — P0 HTML+OG base shipped; per-ticker SVG OG later | viral loop |

## 4. Ops checklist

```bash
python3 -m unittest discover -s tests -v
PORT=8765 python3 -m app   # open /?demo=INTC
python3 scripts/funnel_report.py
```

After polish: commit → push → **self-deploy Render** (`docs/SELF_DEPLOY.md`, no Manus) → watch `funnel.jsonl` rates.
