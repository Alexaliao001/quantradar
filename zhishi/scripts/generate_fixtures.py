#!/usr/bin/env python3
"""Generate 20 teaching OHLCV fixtures + case metadata."""
from __future__ import annotations

import json
import math
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OHLCV = ROOT / "fixtures" / "ohlcv"
CASES = ROOT / "content" / "cases"
OHLCV.mkdir(parents=True, exist_ok=True)
CASES.mkdir(parents=True, exist_ok=True)

# symbol, name, seed, base, is_st, star/chinext, story tag
UNIVERSE = [
    ("600519", "贵州茅台", 1, 1600, False, False, "白酒龙头·常态波动"),
    ("000001", "平安银行", 2, 11.5, False, False, "银行股·低波动"),
    ("300750", "宁德时代", 3, 180, False, True, "创业板·弹性"),
    ("688981", "中芯国际", 4, 45, False, True, "科创板·制度差异"),
    ("600036", "招商银行", 5, 32, False, False, "银行·趋势教学"),
    ("601318", "中国平安", 6, 42, False, False, "保险·均值回归"),
    ("000858", "五粮液", 7, 140, False, False, "白酒·回调复盘"),
    ("002594", "比亚迪", 8, 220, False, False, "新能源·放量讨论"),
    ("601012", "隆基绿能", 9, 18, False, False, "光伏·弱势结构"),
    ("600276", "恒瑞医药", 10, 38, False, False, "医药·中性观察"),
    ("000568", "泸州老窖", 11, 160, False, False, "白酒·教学案例"),
    ("002415", "海康威视", 12, 30, False, False, "制造·量能常态"),
    ("600900", "长江电力", 13, 25, False, False, "公用事业·低波动"),
    ("601888", "中国中免", 14, 70, False, False, "消费·趋势破裂"),
    ("300059", "东方财富", 15, 14, False, True, "券商互联·弹性"),
    ("600030", "中信证券", 16, 20, False, False, "券商·周期教学"),
    ("000725", "京东方Ａ", 17, 3.8, False, False, "制造·贴近跌停带演示"),
    ("601398", "工商银行", 18, 5.2, False, False, "大行·复盘四问"),
    ("600000", "浦发银行", 19, 7.5, False, False, "银行·T+1持有期"),
    ("000002", "万科Ａ", 20, 8.0, False, False, "地产·制度风险讨论"),
]


def gen_bars(seed: int, base: float, n: int = 80, near_limit: bool = False) -> list[dict]:
    rng = random.Random(seed)
    price = base
    bars = []
    # simple random walk with mild drift
    for i in range(n):
        year = 2024
        month = 1 + (i // 20)
        day = 1 + (i % 20)
        date = f"{year}{month:02d}{day:02d}"
        shock = rng.uniform(-0.02, 0.025)
        if near_limit and i == n - 1:
            shock = -0.092  # approach -10% band for teaching
        open_p = price
        close_p = max(0.5, price * (1 + shock))
        high_p = max(open_p, close_p) * (1 + rng.uniform(0, 0.01))
        low_p = min(open_p, close_p) * (1 - rng.uniform(0, 0.01))
        vol = rng.uniform(8e5, 3e6) * (3.0 if near_limit and i == n - 1 else 1.0)
        bars.append(
            {
                "date": date,
                "open": round(open_p, 2),
                "high": round(high_p, 2),
                "low": round(low_p, 2),
                "close": round(close_p, 2),
                "volume": round(vol, 2),
            }
        )
        price = close_p
    return bars


def main() -> None:
    cases_index = []
    for idx, (symbol, name, seed, base, is_st, star, tag) in enumerate(UNIVERSE):
        near = symbol == "000725"
        bars = gen_bars(seed, base, near_limit=near)
        payload = {
            "symbol": symbol,
            "name": name,
            "market": "A",
            "is_st": is_st,
            "is_star_or_chinext": star,
            "bars": bars,
            "source": "fixture",
            "sample": idx < 3,
            "teaching_tag": tag,
        }
        (OHLCV / f"{symbol}.json").write_text(
            json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        case = {
            "id": f"case-{symbol}",
            "symbol": symbol,
            "name": name,
            "title": f"{name}（{symbol}）· {tag}",
            "as_of": bars[-1]["date"],
            "free_demo": idx < 3,
            "summary": f"历史日线教学样本，用于练习框架自检与复盘四问。标签：{tag}。",
            "learning_goal": "写出假设与失效条件，而不是预测涨跌。",
        }
        (CASES / f"{symbol}.json").write_text(
            json.dumps(case, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        cases_index.append(case)
    (CASES / "index.json").write_text(
        json.dumps(cases_index, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"wrote {len(UNIVERSE)} fixtures + cases")


if __name__ == "__main__":
    main()
