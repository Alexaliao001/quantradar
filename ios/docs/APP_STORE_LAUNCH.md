# QuantRadar iOS — App Store Launch Checklist

## Product decisions (locked for this ship)

- **Free App Store download**
- **Non-Consumable unlock** (`one.quantradar.app.unlock`) — regional price displayed by StoreKit
- Free preview: Today SPY + **one lifetime personal ticker** — no daily quotas
- Second ticker: live score, **blurred** card, one-time Unlock offer
- Free native core: **written plan → preserved original record → dated process review**; optional Chase Check and mechanical radar
- Live+ **not listed**; local StoreKit configuration contains only the currently offered Unlock
- Separate from web Stripe / Massive
- User-facing copy: posture only (no COGS / Massive / yahoo_q1)
- Binary: **1.2.0 / build 9**

## 已核验审核状态（2026-09-06 17:45 Asia/Shanghai）

App Store Connect 版本 **1.2.0 / build 9** 与 **QuantRadar Unlock IAP** 均为 **WAITING_FOR_REVIEW**，API 与 Safari 页面已交叉核对。build 9 处理状态为 VALID。新提交 ID：`07500692-0e8e-4347-b06f-395810c8d5b0`，时间 `2026-09-06T09:45:12.963Z`。

发布方式为 **MANUAL**。此次已取消旧 build 7 审核、替换构建、上传 6 张真实截图、更新文案，并重新提交 App + IAP。build 8 的早前替换计划已被本次 build 9 取代。Apple 历史 4.3(a) 反馈后的重新送审不代表已获批或公开上线。

安装价为 Free。美国 Unlock 当前配置 $9.90，其他地区由 Apple 定价；StoreKit 本地测试价格 $9.99 不代表正式地区售价。上架文案已改为购买前展示 App Store 价格。

[审核页面](https://appstoreconnect.apple.com/apps/6800090745/distribution/reviewsubmissions/details/07500692-0e8e-4347-b06f-395810c8d5b0) · [验收记录与回执](review-build9/README.md)

### 公开发布前剩余条件

1. 取得当前 Yahoo/Nasdaq 行情展示及下载分发所需商业授权；供应商询问回执不是授权。
2. 在兼容 Xcode/runtime 上通过实际 StoreKit 框架验收，并完成 TestFlight sandbox 购买、取消和重启恢复检查。当前环境配置保存 Code 3 失败，包括 Xcode 原样生成的对照配置，不能算购买通过。
3. Apple 审核通过；再次核对 App 协议、税务、银行、销售地区及 App + IAP 状态后再手动发布。保持 MANUAL，直到上述条件完成。
4. Live+ 不上架、不另建订阅。网页 Stripe 权限不进入 iOS。
5. 截图和说明使用真实界面；无虚构限量、倒计时或收益。
6. 隐私：`https://quantradar.one/privacy-ios`；条款：`https://quantradar.one/terms-ios`。

## Local build

```bash
cd ios
xcodegen generate
open QuantRadar.xcodeproj
```

Local runs use `QuantRadar/Resources/Products.storekit`; framework purchase tests use the separate `QuantRadarStoreKit` scheme. The configuration is excluded from Release.
DEBUG Settings toggles: Force unlocked / Force Live+; these are not purchase acceptance evidence.

## Listing copy (EN — 1.2.0 build 9, saved in ASC)

**Subtitle:** Plan first. Review honestly.

**Promotional text:** Write your reasons before the outcome. Keep the original plan beside your dated process review, privately on your device.

**Description:**

QuantRadar helps you write a decision before the outcome and review whether you followed your own process.

PLAN BEFORE YOU ACT
Write your reason, the condition you will wait for, and what would change your mind. Choose a review date and your own decision: pause, wait, pass, or review. Saving preserves the original plan. Separate plans stay separate, even for the same ticker on the same day.

REVIEW WHAT YOU DID
Return to your open plans and add a dated process review. Record whether you followed the plan, changed it, or did not act, along with what you learned. The review sits beside the original conditions without rewriting them. Browse open and reviewed records, or share an individual record when you choose.

FREE, PRIVATE CORE
Writing and reviewing plans require no account, purchase, or market data connection. Your journal is stored on this device. These are personal notes, not verified trades or investment returns.

OPTIONAL MARKET CONTEXT
Read mechanical market, sector, and stock context, with source-session dates and explicit unavailable-data states. Use Chase Check to reflect on your process and attach a radar snapshot to a written plan. The free app includes SPY plus one personal ticker. A one-time, non-consumable Unlock purchase adds scans for other supported tickers, Watch, and 90-session posture history. The App Store shows the price before purchase. Restore Purchases is available in Settings.

QuantRadar does not place trades, connect to a brokerage, or provide investment advice. Website subscriptions do not unlock the iOS app.

**Keywords:** trading journal,trade plan,discipline,stock research,review,watchlist,ticker,process

Review steps and exact API text: [listing.json](review-build9/listing.json).

## Listing copy (zh-Hant / zh-Hans — after approval)

Apple rejects new localizations while the version is in review. After Ready for Sale / an editable version:

```bash
/tmp/asc-jwt/bin/python ios/scripts/ship_locales_after_approval.py
```

Copy lives in that script. Unlock IAP availability was observed for 175 territories; app availability, agreements and public listing must be checked separately.

## Ads → cash register

- Send traffic to **free** listing (lower friction)
- Evaluate acquisition cost against actual net Unlock receipts after Apple fees, tax and refunds
- Use Offer Codes for creative tests
- Kill campaigns that only buy installs without unlocks

## Review risks

| Risk | Mitigation |
|------|------------|
| Investment advice | SETUP not BUY; disclaimers onboarding / Today / Scan / Paywall / Settings |
| 4.3(a) / template spam | Free written plans, preserved originals and separate dated reviews; review steps and actual screenshots document the new workflow. Approval remains Apple’s decision |
| Thin wrapper | Native SwiftUI + SPY + one real personal scan + 90-day strip + widget + journal |
| Misleading IAP | Unlock only in 1.2; no fake server push; no fake countdown |
| Privacy mismatch | iOS-specific policy: no account, no tracking |
| Earnings / FOMO | Real market events only; briefing copy is static |
