"""A股制度门控 + 课程框架自检分（唯一 primary_score）。"""
from __future__ import annotations

from typing import Any

from app.config import CONTRACT_VERSION, DISCLAIMER

POSTURE_STRONG = "偏强学习态"
POSTURE_NEUTRAL = "中性观察态"
POSTURE_WEAK = "偏弱学习态"
POSTURE_NODATA = "数据不足"


def posture_for(score: int | None) -> str:
    if score is None:
        return POSTURE_NODATA
    if score >= 70:
        return POSTURE_STRONG
    if score >= 40:
        return POSTURE_NEUTRAL
    return POSTURE_WEAK


def fail_closed(symbol: str, error: str = "symbol_not_found") -> dict[str, Any]:
    return {
        "ok": False,
        "contract_version": CONTRACT_VERSION,
        "symbol": symbol,
        "error": error,
        "primary_score": None,
        "posture": POSTURE_NODATA,
        "gates": [],
        "checklist": [],
        "sample": False,
        "degraded": False,
        "warnings": [],
        "disclaimer": DISCLAIMER,
    }


def analyze(payload: dict[str, Any]) -> dict[str, Any]:
    """对已加载的 fixture/live payload 计算自检分。"""
    bars = payload.get("bars") or []
    if len(bars) < 20:
        return fail_closed(str(payload.get("symbol", "")), "insufficient_bars")

    closes = [float(b["close"]) for b in bars]
    volumes = [float(b.get("volume") or 0) for b in bars]
    highs = [float(b["high"]) for b in bars]
    lows = [float(b["low"]) for b in bars]

    last = closes[-1]
    prev = closes[-2]
    ma5 = sum(closes[-5:]) / 5
    ma20 = sum(closes[-20:]) / 20
    vol20 = sum(volumes[-20:]) / 20 or 1.0
    vol_ratio = volumes[-1] / vol20

    # 涨跌停近似：主板 10%，双创/科创 20%
    limit_pct = 0.20 if payload.get("is_star_or_chinext") else 0.10
    day_ret = (last - prev) / prev if prev else 0.0
    near_limit = abs(day_ret) >= (limit_pct * 0.85)

    is_st = bool(payload.get("is_st"))
    market = payload.get("market") or "A"

    gates = _build_gates(market=market, near_limit=near_limit, is_st=is_st, limit_pct=limit_pct)

    checklist: list[dict[str, Any]] = []
    # 1) 趋势结构 0-25
    trend_score = 0
    if last > ma20 > sum(closes[-60:]) / min(60, len(closes)) if len(closes) >= 60 else ma20:
        trend_score = 22
        reason = "收盘位于均线上方，教学上视为偏多结构（仅供框架练习）。"
    elif last > ma20:
        trend_score = 16
        reason = "短中期均线偏多，但更长周期未确认。"
    elif last > ma5:
        trend_score = 10
        reason = "仅短均线支撑，结构偏弱，适合作为观察教学案例。"
    else:
        trend_score = 4
        reason = "价格位于主要均线下方，教学上归入偏弱结构。"
    checklist.append(
        {"id": "trend_structure", "title": "趋势结构（教学）", "score": trend_score, "max": 25, "reason": reason}
    )

    # 2) 量能配合 0-20
    if 0.8 <= vol_ratio <= 1.8:
        vol_score = 16
        vol_reason = "量能处于常态区间，利于讨论「不追极端放量」。"
    elif vol_ratio > 2.5:
        vol_score = 6
        vol_reason = "放量显著，教学重点：区分突破与接力风险。"
    else:
        vol_score = 10
        vol_reason = "量能偏淡，强调流动性与滑点认知。"
    checklist.append(
        {"id": "volume_quality", "title": "量能质量（教学）", "score": vol_score, "max": 20, "reason": vol_reason}
    )

    # 3) 波动与涨跌停邻近 0-20
    if near_limit:
        lim_score = 4
        lim_reason = f"接近约 {int(limit_pct*100)}% 涨跌停带，流动性与次日缺口是复盘重点。"
    else:
        range20 = (max(highs[-20:]) - min(lows[-20:])) / ma20 if ma20 else 0
        lim_score = 16 if range20 < 0.25 else 10
        lim_reason = "未贴涨跌停，可练习常规波动下的假设书写。"
    checklist.append(
        {
            "id": "limit_proximity",
            "title": "涨跌停邻近度（教学）",
            "score": lim_score,
            "max": 20,
            "reason": lim_reason,
        }
    )

    # 4) 制度风险项 0-20（ST / 次新简化）
    if is_st:
        inst_score = 2
        inst_reason = "ST/*ST 标的：规则与退市风险教育优先于形态讨论。"
    else:
        inst_score = 16
        inst_reason = "非 ST，制度风险项按常规教学权重计分。"
    checklist.append(
        {
            "id": "institutional_risk",
            "title": "制度风险（教学）",
            "score": inst_score,
            "max": 20,
            "reason": inst_reason,
        }
    )

    # 5) 复盘完备度占位 0-15（引擎侧给基准，用户写入假设后由复盘本加分在产品层）
    review_score = 12
    checklist.append(
        {
            "id": "review_ready",
            "title": "复盘完备度（基准）",
            "score": review_score,
            "max": 15,
            "reason": "写入「假设/失效条件」后，复盘本才算完成一次学习闭环。",
        }
    )

    raw = sum(i["score"] for i in checklist)
    primary = int(round(raw / sum(i["max"] for i in checklist) * 100))
    # 门控惩罚：近涨跌停或 ST 额外下调，避免「高分+危险制度」
    if near_limit:
        primary = max(0, primary - 8)
    if is_st:
        primary = max(0, primary - 15)

    return {
        "ok": True,
        "contract_version": CONTRACT_VERSION,
        "symbol": payload.get("symbol"),
        "name": payload.get("name") or payload.get("symbol"),
        "market": market,
        "primary_score": primary,
        "posture": posture_for(primary),
        "gates": gates,
        "checklist": checklist,
        "institutional_context": {
            "near_limit": near_limit,
            "is_st": is_st,
            "is_star_or_chinext": bool(payload.get("is_star_or_chinext")),
            "day_return_pct": round(day_ret * 100, 2),
            "limit_band_pct": int(limit_pct * 100),
        },
        "sample": bool(payload.get("sample")),
        "degraded": False,
        "warnings": list(payload.get("warnings") or []),
        "sources": [
            {
                "name": payload.get("source") or "fixture",
                "role": "ohlcv",
                "status": "ok",
            }
        ],
        "as_of": bars[-1].get("date"),
        "disclaimer": DISCLAIMER,
    }


def _build_gates(*, market: str, near_limit: bool, is_st: bool, limit_pct: float) -> list[dict[str, Any]]:
    if market == "HKCONNECT":
        return [
            {
                "id": "hkconnect_quota",
                "title": "港股通额度与时段",
                "passed": True,
                "teaching": "港股通有交易时段与额度约束，教学自检需单独记住与 A 股差异。",
            },
            {
                "id": "hkconnect_fx",
                "title": "汇率与价差感知",
                "passed": True,
                "teaching": "报价与结算涉及汇率；复盘时记录汇率假设是否影响结论。",
            },
            {
                "id": "t_plus_hk",
                "title": "交收习惯差异",
                "passed": True,
                "teaching": "勿用 A 股 T+1 直觉硬套；以课程港股通篇为准。",
            },
        ]
    return [
        {
            "id": "t1_settlement",
            "title": "T+1 交收",
            "passed": True,
            "teaching": "当日成交的股票通常下一交易日才可了结，持有期与隔夜缺口必须进入假设。",
        },
        {
            "id": "limit_liquidity",
            "title": "涨跌停流动性",
            "passed": not near_limit,
            "teaching": f"接近约 {int(limit_pct*100)}% 涨跌停时，排队与打开风险优先于形态美丑。",
        },
        {
            "id": "st_rules",
            "title": "ST 与风险警示",
            "passed": not is_st,
            "teaching": "ST 标的以规则与退市教育为主，不作走势预测练习题。",
        },
    ]
