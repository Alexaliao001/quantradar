# GO LIVE status

Checked **2026-08-28 14:42 +08**: App Store version 1.0 was **REJECTED** under **Guideline 4.3(a) — Design: Spam**, then **resubmitted** with build 7.

Apple said the binary, metadata, and/or concept appeared similar to apps from other developers. Build 7 is the substantive response: original **Chase Check → mechanical radar → private Decision Journal** workflow, stable Plan tab, updated screenshots, and review notes that explain source ownership and distinct functionality.

- App ID `6800090745` · Bundle `one.quantradar.app`
- Listing price **Free** · IAP Unlock `$9.99` (`one.quantradar.app.unlock`) submitted with the version
- Rejected binary: **1.2.0 (6)** on version string **1.0**
- Replacement in local validation: **1.2.0 (7)**
- Markets: IAP `availableInNewTerritories=true`, **175 territories** including USA, HKG, SGP, TWN, GBR, JPN, AUS, CAN, DEU, CHN
- Privacy URL on the listing: `https://quantradar.one/privacy-ios` (**200** on the Nube VPS that serves the apex)
- Terms: `https://quantradar.one/terms-ios` (**200**)
- Public iTunes lookup remains empty (`resultCount: 0`) until Apple approves and releases
- zh-Hans / zh-Hant store copy is prepared but **locked until review ends** — run `ios/scripts/ship_locales_after_approval.py`

- Resubmitted **2026-08-28 14:40 +08**: review submission `WAITING_FOR_REVIEW`
- Attached binary **1.2.0 (7)** `d8f8434d-2b7b-44d4-bbfc-59886fd00543` (`VALID`)
- Listing copy now leads with Chase Check + Decision Journal; keywords no longer “stock scanner”
- iPhone 6.5" (5) and iPad 12.9" (5) screenshots are current build 7 product shots: Chase Check, SPY three-gate Today, Plan journal, Unlock sheet, onboarding

Do not resubmit build 6. Do not replace build 7 while Apple is reviewing.

Operator command after Apple unlocks the version:

```bash
/tmp/asc-jwt2/bin/python ios/scripts/go_live.py
```

That ships zh-Hans / zh-Hant store + IAP copy and checks the public iTunes listing. `releaseType` is `AFTER_APPROVAL`, so the app should go live when Apple approves — no second click.

Web and iOS remain independent cash registers. Website Pro (Stripe) does not unlock iOS. iOS Unlock does not sign into the website.

