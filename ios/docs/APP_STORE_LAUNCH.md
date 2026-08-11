# QuantRadar iOS — App Store Launch Checklist

## Product decisions (locked)

- **Paid download $9.99** (App Store app price — not StoreKit)
- **No free tier / no trial freemium** inside the binary
- Full core radar unlocked after purchase
- **No required IAP in v1** (optional Live+ later — see PRODUCT.md)
- Separate from web Stripe

## Prerequisites (you)

1. Apple Developer Program + banking/tax/paid-apps agreements
2. App Store Connect app: bundle `one.quantradar.app`, SKU `quantradar-ios`
3. **Pricing → $9.99** (or local equivalents)
4. Set `DEVELOPMENT_TEAM` in Xcode

## Local build

```bash
cd ~/quantradar/ios
xcodegen generate
open QuantRadar.xcodeproj
```

Paid price cannot be simulated as App Store charge in Simulator; treat Xcode installs as “already purchased.”

## App Store Connect

1. Create iOS app · category **Finance**
2. Price: **$9.99**
3. Privacy policy: `https://quantradar.one/privacy`
4. Terms + Apple Standard EULA
5. Review note: “Paid educational mechanical posture radar. Not a broker. INTC demo works offline. No account required for core use.”

### Listing copy (EN — draft)

**Subtitle:** Mechanical stock posture radar

**Promotional text:** One score. One action. Built for traders tired of tipster noise.

**Description:**
QuantRadar is a paid educational radar for US tickers. It shows a single mechanical posture score and a clear action: act, wait, or avoid — with market / sector / stock gates.

This is not a broker, not investment advice, and not a tipster feed. Most days the honest answer is don’t trade.

Independent App Store product — website subscriptions do not apply.

**Keywords:** stock radar,trading journal,stock scanner,options setup,swing trade,market posture,ticker analysis

## Screenshots

1. Today verdict card  
2. Scan + gates  
3. Watchlist reminders  
4. Onboarding value prop  
5. Settings / disclaimer  

## Ads → cash register

- Use **Custom Product Page** per creative angle if useful
- Send paid traffic **straight to the paid App Store listing**
- Optimize CPA vs **~$7–8.50** net per install after Apple cut — kill campaigns above payback

## Review risks

| Risk | Mitigation |
|------|------------|
| Investment advice | Disclaimers on onboarding / Today / Settings |
| Thin wrapper | Native SwiftUI + offline demo |
| Misleading | Fail-closed; no fake returns |

## You still must do

Create ASC record · set $9.99 · screenshots · Archive with your Team ID · Submit.
