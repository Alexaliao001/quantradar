# QuantRadar iOS — App Store Launch Checklist

## Product decisions (locked for next ship)

- **Free App Store download**
- **$9.99 Non-Consumable unlock** (`one.quantradar.app.unlock`)
- Free preview: Today SPY + INTC demo — **no freemium scan quotas**
- **Optional Live+** (local watch limit + denser local reminders)
- Separate from web Stripe / Massive

## Do not touch ASC 1.0 while Waiting for Review

Current 1.0 paid-download submission stays as-is. After it is **Approved / Rejected / Removed**:

### Post-1.0 ASC cutover checklist

1. Set App price to **Free**
2. Create IAP: Non-Consumable **QuantRadar Unlock** $9.99 · id `one.quantradar.app.unlock`
3. Create subscription group **Radar Live+** · monthly / yearly (ids in `Products.storekit`)
4. Paid Apps / IAP agreements + tax/banking current
5. New version **1.1** binary with StoreKit gates
6. Screenshots: Today preview · Scan paywall · Unlock sheet · Watch locked CTA · Settings restore
7. Review note: free preview INTC; unlock once; no account; educational; not a broker
8. Submit 1.1 — do not mutate the closed 1.0 review thread casually

## Local build

```bash
cd ios
xcodegen generate
open QuantRadar.xcodeproj
```

Scheme uses `QuantRadar/Resources/Products.storekit`.  
DEBUG Settings toggles: Force unlocked / Force Live+.

## Listing copy (EN — draft for 1.1)

**Subtitle:** Mechanical stock posture radar

**Promotional text:** One score. Most days: don’t act — not tipster noise.

**Description:**
QuantRadar is an educational radar for US tickers. Free to install: see today’s SPY posture and try the INTC demo. Unlock once ($9.99) for full ticker scan and watchlist.

One mechanical posture score and a clear action — act, wait, or avoid. This is not a broker, not investment advice, and not a tipster feed. Most days the honest answer is don’t trade.

Independent App Store product. Website subscriptions do not apply. Optional Live+ adds local reminder density — not a Massive data plan.

**Keywords:** stock radar,stock scanner,swing trade,trading,market posture,ticker

## Ads → cash register

- Send traffic to **free** listing (lower friction)
- Optimize toward **unlock CPA** vs ~$7 net, not install vanity
- Use Offer Codes for creative tests
- Kill campaigns that only buy installs without unlocks

## Review risks

| Risk | Mitigation |
|------|------------|
| Investment advice | Disclaimers onboarding / Today / Scan / Paywall / Settings |
| Thin wrapper | Native SwiftUI + offline INTC demo |
| Misleading IAP | Clear unlock vs Live+; no fake server claims |
