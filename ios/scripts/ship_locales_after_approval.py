#!/usr/bin/env python3
"""Add zh-Hans / zh-Hant listings when the App Store version is editable.

Apple rejects localization creates while WAITING_FOR_REVIEW.
Run after approval or rejection, before the next review submission.

  /tmp/asc-jwt/bin/python ios/scripts/ship_locales_after_approval.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from ship_asc import api, find_app, load_token  # noqa: E402

APP_ID = "6800090745"
PRIVACY = "https://quantradar.one/privacy-ios"
SUPPORT = "https://quantradar.one"

LOCALES = {
    "zh-Hant": {
        "subtitle": "交易前先別追高",
        "promotionalText": "追價前先檢查流程：三個問題、一個機械姿態、一本只存在裝置上的決策日誌。",
        "whatsNew": "新增追價檢查與私人決策日誌。免費 SPY 加一支個人標的；一次解鎖完整雷達。",
        "keywords": "交易日誌,追高,美股,波段,股票分析,自選股,市場,紀律",
        "description": (
            "QuantRadar 是給美股波段交易者的交易前紀律工具。\n\n"
            "先做「追價檢查」：確認進場位是在行情啟動前訂好、能說出失效條件，並把決定與社群熱度分開。"
            "再讀市場、產業與標的三道門控形成的一個機械姿態分數。\n\n"
            "在結果揭曉前保存暫停、等待、放棄或複核決定。私人決策日誌只存在這台裝置。"
            "免費安裝可看 SPY 並掃描一支個人標的；一次解鎖（$9.99）開放完整雷達、自選與 90 天紀錄。\n\n"
            "這不是券商、不執行交易、不是投資建議，也不是喊單。多數日子最誠實的答案是等待。\n\n"
            "獨立 App Store 產品。網站訂閱不能解鎖本 App。"
        ),
        "iap_name": "QuantRadar 解鎖",
        "iap_desc": "一次解鎖任意美股掃描與自選清單。非訂閱。",
    },
    "zh-Hans": {
        "subtitle": "交易前先别追高",
        "promotionalText": "追价前先检查流程：三个问题、一个机械姿态、一本只存在设备上的决策日志。",
        "whatsNew": "新增追价检查与私人决策日志。免费 SPY 加一支个人标的；一次解锁完整雷达。",
        "keywords": "交易日志,追高,美股,波段,股票分析,自选股,市场,纪律",
        "description": (
            "QuantRadar 是给美股波段交易者的交易前纪律工具。\n\n"
            "先做“追价检查”：确认入场位是在行情启动前定好、能说出失效条件，并把决定与社交热度分开。"
            "再读市场、行业与标的三道门控形成的一个机械姿态分数。\n\n"
            "在结果揭晓前保存暂停、等待、放弃或复核决定。私人决策日志只存在这台设备。"
            "免费安装可看 SPY 并扫描一支个人标的；一次解锁（$9.99）开放完整雷达、自选与 90 天记录。\n\n"
            "这不是券商、不执行交易、不是投资建议，也不是喊单。多数日子最诚实的答案是等待。\n\n"
            "独立 App Store 产品。网站订阅不能解锁本 App。"
        ),
        "iap_name": "QuantRadar 解锁",
        "iap_desc": "一次解锁任意美股扫描与自选清单。非订阅。",
    },
}


def latest_ios_version(token: str) -> dict:
    st, vers = api(token, "GET", f"/v1/apps/{APP_ID}/appStoreVersions?limit=10")
    if st != 200:
        raise SystemExit(f"versions {st} {vers}")
    return (vers.get("data") or [])[0]


def upsert_version_loc(token: str, version_id: str, locale: str, copy: dict) -> None:
    st, locs = api(token, "GET", f"/v1/appStoreVersions/{version_id}/appStoreVersionLocalizations")
    loc_id = None
    if st == 200:
        for loc in locs.get("data") or []:
            if loc["attributes"].get("locale") == locale:
                loc_id = loc["id"]
    attrs = {
        "description": copy["description"],
        "keywords": copy["keywords"],
        "marketingUrl": SUPPORT,
        "supportUrl": SUPPORT,
        "promotionalText": copy["promotionalText"],
        "whatsNew": copy["whatsNew"],
    }
    if loc_id:
        s, b = api(
            token,
            "PATCH",
            f"/v1/appStoreVersionLocalizations/{loc_id}",
            {"data": {"type": "appStoreVersionLocalizations", "id": loc_id, "attributes": attrs}},
        )
        print(locale, "version loc patch", s)
        if s >= 400:
            print(b if isinstance(b, str) else json.dumps(b)[:500])
        return
    s, b = api(
        token,
        "POST",
        "/v1/appStoreVersionLocalizations",
        {
            "data": {
                "type": "appStoreVersionLocalizations",
                "attributes": {"locale": locale, **attrs},
                "relationships": {
                    "appStoreVersion": {"data": {"type": "appStoreVersions", "id": version_id}}
                },
            }
        },
    )
    print(locale, "version loc post", s)
    if s >= 400:
        print(b if isinstance(b, str) else json.dumps(b)[:500])


def upsert_info_loc(token: str, locale: str, copy: dict) -> None:
    st, infos = api(token, "GET", f"/v1/apps/{APP_ID}/appInfos")
    if st != 200 or not infos.get("data"):
        print("appInfos", st)
        return
    info_id = infos["data"][0]["id"]
    st, ilocs = api(token, "GET", f"/v1/appInfos/{info_id}/appInfoLocalizations")
    loc_id = None
    if st == 200:
        for loc in ilocs.get("data") or []:
            if loc["attributes"].get("locale") == locale:
                loc_id = loc["id"]
    attrs = {
        "name": "QuantRadar",
        "subtitle": copy["subtitle"],
        "privacyPolicyUrl": PRIVACY,
    }
    if loc_id:
        s, b = api(
            token,
            "PATCH",
            f"/v1/appInfoLocalizations/{loc_id}",
            {"data": {"type": "appInfoLocalizations", "id": loc_id, "attributes": attrs}},
        )
        print(locale, "info loc patch", s)
        if s >= 400:
            print(b if isinstance(b, str) else json.dumps(b)[:500])
        return
    s, b = api(
        token,
        "POST",
        "/v1/appInfoLocalizations",
        {
            "data": {
                "type": "appInfoLocalizations",
                "attributes": {"locale": locale, **attrs},
                "relationships": {"appInfo": {"data": {"type": "appInfos", "id": info_id}}},
            }
        },
    )
    print(locale, "info loc post", s)
    if s >= 400:
        print(b if isinstance(b, str) else json.dumps(b)[:500])


def upsert_iap_loc(token: str, locale: str, copy: dict) -> None:
    st, iap = api(token, "GET", f"/v1/apps/{APP_ID}/inAppPurchasesV2?limit=10")
    unlock = None
    if st == 200:
        for p in iap.get("data") or []:
            if p["attributes"].get("productId") == "one.quantradar.app.unlock":
                unlock = p["id"]
    if not unlock:
        print("unlock IAP missing")
        return
    st, locs = api(token, "GET", f"/v2/inAppPurchases/{unlock}/inAppPurchaseLocalizations")
    loc_id = None
    if st == 200:
        for loc in locs.get("data") or []:
            if loc["attributes"].get("locale") == locale:
                loc_id = loc["id"]
    if loc_id:
        s, b = api(
            token,
            "PATCH",
            f"/v1/inAppPurchaseLocalizations/{loc_id}",
            {
                "data": {
                    "type": "inAppPurchaseLocalizations",
                    "id": loc_id,
                    "attributes": {"name": copy["iap_name"], "description": copy["iap_desc"]},
                }
            },
        )
        print(locale, "iap loc patch", s)
        if s >= 400:
            print(b if isinstance(b, str) else json.dumps(b)[:400])
        return
    s, b = api(
        token,
        "POST",
        "/v1/inAppPurchaseLocalizations",
        {
            "data": {
                "type": "inAppPurchaseLocalizations",
                "attributes": {
                    "name": copy["iap_name"],
                    "locale": locale,
                    "description": copy["iap_desc"],
                },
                "relationships": {
                    "inAppPurchaseV2": {"data": {"type": "inAppPurchases", "id": unlock}}
                },
            }
        },
    )
    print(locale, "iap loc post", s)
    if s >= 400:
        print(b if isinstance(b, str) else json.dumps(b)[:400])


def main() -> int:
    token = load_token()
    app = find_app(token)
    if not app:
        raise SystemExit("app missing")
    version = latest_ios_version(token)
    state = version["attributes"].get("appVersionState") or version["attributes"].get("appStoreState")
    print("version", version["id"], version["attributes"].get("versionString"), state)
    if state in {"WAITING_FOR_REVIEW", "IN_REVIEW"}:
        print("Apple still has this version locked. Re-run after approval or reject.")
        return 2
    vid = version["id"]
    for locale, copy in LOCALES.items():
        upsert_info_loc(token, locale, copy)
        upsert_version_loc(token, vid, locale, copy)
        upsert_iap_loc(token, locale, copy)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
