"""知势 — 配置。默认 artifact，live 需显式开关 + token。"""
from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "fixtures"
CONTENT = ROOT / "content"

HOST = os.environ.get("HOST", "0.0.0.0")
PORT = int(os.environ.get("PORT", os.environ.get("ZHISHI_PORT", "8787")))
MODE = os.environ.get("ZHISHI_MODE", "artifact").strip().lower()
ALLOW_LIVE = os.environ.get("ZHISHI_ALLOW_LIVE", "0").strip() in {"1", "true", "yes"}
TUSHARE_TOKEN = os.environ.get("TUSHARE_TOKEN", "").strip()
SESSION_SECRET = os.environ.get("SESSION_SECRET", "zhishi-dev-secret-change-me")

DISCLAIMER = "本产品为投资教育工具，不构成任何投资建议。市场有风险，决策须自负。"
CONTRACT_VERSION = "1.0.0"

# 知识付费 SKU（微信支付商品名须与此类目一致）
SKUS = {
    "free": {"name": "免费导读", "price_fen": 0, "period": None},
    "monthly": {"name": "月度研习会员", "price_fen": 6800, "period": "month"},
    "yearly": {"name": "年度研习会员", "price_fen": 48800, "period": "year"},
    "course_traps": {"name": "课包·A股制度与行为陷阱", "price_fen": 12900, "period": None},
}


def live_eligible() -> bool:
    return ALLOW_LIVE and bool(TUSHARE_TOKEN) and MODE == "live"
