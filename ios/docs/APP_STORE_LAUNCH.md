# QuantRadar iOS — App Store Launch Checklist

## Product decisions (locked for this ship)

- **Free App Store download**
- **$9.99 Non-Consumable unlock** (`one.quantradar.app.unlock`) — founder price, first 1,000
- Free preview: Today SPY + **one lifetime personal ticker** — no daily quotas
- Second ticker: live score, **blurred** card, anxiety paywall
- Live+ **not listed** (keep StoreKit products for later)
- Separate from web Stripe / Massive
- User-facing copy: posture only (no COGS / Massive / yahoo_q1)
- Binary: **1.2.0 / build 6**

## Listing strategy

Paid-download 1.0 is the wrong cash register. The public product is **free + Unlock**.

If 1.0 is still Waiting for Review: **cancel that thread**, set price Free, create Unlock IAP, submit **1.2**. Do not launch $9.99-to-download then convert later.

### Cutover / first public listing

1. Cancel any in-flight paid 1.0 review submission
2. Set App price to **Free**
3. Create IAP: Non-Consumable **QuantRadar Unlock** $9.99 · id `one.quantradar.app.unlock`
4. Skip Live+ subscription group on the listing (products may exist in StoreKit config only)
5. Paid Apps / IAP agreements + tax/banking current
6. Version **1.2** binary (build 6+) with StoreKit gates + depth features
7. Screenshots: live SPY Today · personal Scan · SETUP/WAIT card · blurred 2nd-ticker paywall · Unlock sheet. No “paid download” / COGS / Massive captions
8. Privacy URL: `https://quantradar.one/privacy-ios` · Terms: `https://quantradar.one/terms-ios`
9. Review note: free SPY + one personal ticker; second ticker scores but stays locked; unlock once; no account; educational; not a broker; SETUP ≠ buy order; weekday briefing is a local reminder, not a signal
10. Submit 1.2 — After Approval

## Local build

```bash
cd ios
xcodegen generate
open QuantRadar.xcodeproj
```

Scheme uses `QuantRadar/Resources/Products.storekit`.  
DEBUG Settings toggles: Force unlocked / Force Live+.

## Listing copy (EN — 1.2)

**Subtitle:** Stock scanner: wait or act

**Promotional text:** One score for a US ticker. Most days the honest answer is wait — not a tipster feed.

**Description:**
QuantRadar is an educational radar for US tickers. Free to install: see today’s SPY posture and scan one ticker of yours. Unlock once ($9.99) for every ticker, a watchlist, and a 90-day posture history.

One mechanical posture score and a clear action — setup zone, wait, or avoid. Earnings windows stay on wait. This is not a broker, not investment advice, and not a tipster feed. Most days the honest answer is don’t trade.

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
| Thin wrapper | Native SwiftUI + live SPY + one real personal scan + 90-day strip |
| Misleading IAP | Unlock only in 1.2; no fake server push; no fake countdown |
| Privacy mismatch | iOS-specific policy: no account, no tracking |
| Earnings / FOMO | Real market events only; briefing copy is static |
