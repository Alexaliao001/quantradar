# QuantRadar iOS — App Store Launch Checklist

## Product decisions (locked for next ship)

- **Free App Store download**
- **$9.99 Non-Consumable unlock** (`one.quantradar.app.unlock`)
- Free preview: Today SPY + **one lifetime personal ticker** — no daily quotas
- Live+ **not listed in 1.1** (keep StoreKit products for later)
- Separate from web Stripe / Massive
- User-facing copy: posture only (no COGS / Massive / yahoo_q1)

## Do not touch ASC 1.0 while Waiting for Review

Current 1.0 paid-download submission stays as-is. After it is **Approved / Rejected / Removed**:

### Post-1.0 ASC cutover checklist

1. Set App price to **Free**
2. Create IAP: Non-Consumable **QuantRadar Unlock** $9.99 · id `one.quantradar.app.unlock`
3. Skip Live+ subscription group for 1.1 listing (products may exist in StoreKit config only)
4. Paid Apps / IAP agreements + tax/banking current
5. New version **1.1** binary (build 5+) with StoreKit gates
6. Screenshots: live SPY Today · personal Scan · SETUP/WAIT card · Unlock sheet · Settings restore. No “paid download” / COGS / Massive captions
7. Privacy URL: `https://quantradar.one/privacy-ios` · Terms: `https://quantradar.one/terms-ios`
8. Review note: free SPY + one personal ticker; unlock once; no account; educational; not a broker; SETUP ≠ buy order
9. Submit 1.1 — do not mutate the closed 1.0 review thread casually

## Local build

```bash
cd ios
xcodegen generate
open QuantRadar.xcodeproj
```

Scheme uses `QuantRadar/Resources/Products.storekit`.  
DEBUG Settings toggles: Force unlocked / Force Live+.

## Listing copy (EN — 1.1)

**Subtitle:** Stock scanner: wait or act

**Promotional text:** One score for a US ticker. Most days the honest answer is wait — not a tipster feed.

**Description:**
QuantRadar is an educational radar for US tickers. Free to install: see today’s SPY posture and scan one ticker of yours. Unlock once ($9.99) for every ticker and a watchlist.

One mechanical posture score and a clear action — setup zone, wait, or avoid. This is not a broker, not investment advice, and not a tipster feed. Most days the honest answer is don’t trade.

Independent App Store product. Website subscriptions do not unlock this app.

**Keywords:** stock scanner,stock tracker,watchlist,swing trade,stock analysis,market,ticker,stocks,trading,setup

## Ads → cash register

- Send traffic to **free** listing (lower friction)
- Optimize toward **unlock CPA** vs ~$7 net, not install vanity
- Use Offer Codes for creative tests
- Kill campaigns that only buy installs without unlocks

## Review risks

| Risk | Mitigation |
|------|------------|
| Investment advice | SETUP not BUY; disclaimers onboarding / Today / Scan / Paywall / Settings |
| Thin wrapper | Native SwiftUI + live SPY + one real personal scan |
| Misleading IAP | Unlock only in 1.1; no fake server push |
| Privacy mismatch | iOS-specific policy: no account, no tracking |
