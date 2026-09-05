# QuantRadar iOS — App Store Launch Checklist

## Product decisions (locked for this ship)

- **Free App Store download**
- **Non-Consumable unlock** (`one.quantradar.app.unlock`) — regional price displayed by StoreKit
- Free preview: Today SPY + **one lifetime personal ticker** — no daily quotas
- Second ticker: live score, **blurred** card, one-time Unlock offer
- Distinct core: **Chase Check → mechanical radar → private Decision Journal**
- Live+ **not listed** (keep StoreKit products for later)
- Separate from web Stripe / Massive
- User-facing copy: posture only (no COGS / Massive / yahoo_q1)
- Binary: **1.2.0 / build 8**

## 已核验审核状态（2026-09-06）

App Store Connect 的公开版本 1.0 当前为 **WAITING_FOR_REVIEW**，关联 build 7；安装价已为 Free，Unlock IAP 已存在并包含在审核中。美国 Unlock 当前配置 $9.90，其他地区由 Apple 定价。不能从本地 StoreKit 测试价格推断所有地区售价。

### 替换构建

1. 先完成数据授权与实际 StoreKit 验收；核对 App 协议、税务、银行及销售地区。
2. build 8（1.2.0）本地测试和归档后上传，等待 Apple 处理为 VALID。上传成功不等于已审核或上架。
3. 备份现有版本、构建关系、审核项目和 IAP 配置。新构建可用之前保留当前审核。
4. 如确需替换，取消现有审核并等待可编辑，再关联已验证可用于该版本的新构建。
5. 新 review submission 必须同时包含 App version 和现有 Unlock IAP version，核对后提交；保持 AFTER_APPROVAL。
6. Live+ 不上架、不另建订阅。网页 Stripe 权限不进入 iOS。
7. 截图和说明使用真实界面；无虚构前 1,000 名、倒计时或收益。
8. 隐私：`https://quantradar.one/privacy-ios`；条款：`https://quantradar.one/terms-ios`。

2026-09-06：build 8 已上传并处理为 VALID（ID `719a2f67-d5c3-49c3-ab98-7886189b0fe2`）。尚未取消旧审核、替换选定构建或提交新审核。已准备私有 `ios/build/launch-build-8-final-20260906/review-replacement-plan.json`，包含 build 8、App + IAP 项及移除商店描述中固定 $9.99 的更新，未执行。实际发布时间由数据授权、购买验收、Apple 审核与商店状态决定。

## Local build

```bash
cd ios
xcodegen generate
open QuantRadar.xcodeproj
```

Scheme uses `QuantRadar/Resources/Products.storekit`.  
DEBUG Settings toggles: Force unlocked / Force Live+.

## Listing copy (EN — 1.2)

**Subtitle:** Stop chasing stock setups

**Promotional text:** Before you chase, check your process. Three questions, one mechanical posture, and a private decision journal.

**Description:**
QuantRadar is a pre-trade discipline tool for US-stock swing traders.

Start with Chase Check: confirm that your entry existed before the move, define what invalidates the setup, and separate your decision from social hype. Then read one mechanical posture score through market, sector, and stock gates.

Save the decision before you know the outcome. The private on-device journal records whether you chose to pause, wait, pass, or review — so discipline becomes a process, not a victory-lap screenshot.

Free to install: see today’s SPY posture and scan one ticker of yours. Unlock once (your regional price is shown before purchase) for every supported ticker, Watch, and 90-day posture history.

This is not a broker, does not place trades, and is not investment advice or a tipster feed. Most days the honest answer is wait.

Independent App Store product. Website subscriptions do not unlock this app.

**Keywords:** trading journal,fomo,swing trade,stock analysis,watchlist,market,ticker,discipline,setup

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
| 4.3(a) / template spam | Original Chase Check + private Decision Journal + Plan workflow; review notes explain the distinct process |
| Thin wrapper | Native SwiftUI + SPY + one real personal scan + 90-day strip + widget + journal |
| Misleading IAP | Unlock only in 1.2; no fake server push; no fake countdown |
| Privacy mismatch | iOS-specific policy: no account, no tracking |
| Earnings / FOMO | Real market events only; briefing copy is static |
