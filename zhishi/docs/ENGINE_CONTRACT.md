# ENGINE_CONTRACT — 知势自检引擎契约

> 版本：`1.0.0`  
> 壳职责：请求规范化 + 展示；引擎产出唯一 `primary_score` 与教学 `posture`。

## 1. 请求

```json
{
  "contract_version": "1.0.0",
  "symbol": "600519",
  "market": "A",
  "context": {
    "mode": "artifact",
    "as_of": "2024-06-14",
    "request_id": "optional"
  }
}
```

| 字段 | 必需 | 说明 |
|------|------|------|
| `symbol` | 是 | A股 6 位数字；港股通阶段可为 5 位 |
| `market` | 否 | `A`（默认）\| `HKCONNECT` |
| `context.mode` | 否 | `artifact` \| `live` |
| `context.as_of` | 否 | 教学复盘锚定日 |

非法代码 → HTTP 400。

## 2. 成功响应

```json
{
  "ok": true,
  "contract_version": "1.0.0",
  "symbol": "600519",
  "name": "贵州茅台",
  "market": "A",
  "primary_score": 62,
  "posture": "中性观察态",
  "gates": [
    {
      "id": "t1_settlement",
      "title": "T+1 交收",
      "passed": true,
      "teaching": "当日买入不可卖出，教学自检需计入持有期约束。"
    }
  ],
  "checklist": [
    {
      "id": "trend_structure",
      "title": "趋势结构（教学）",
      "score": 14,
      "max": 20,
      "reason": "…"
    }
  ],
  "institutional_context": {
    "near_limit": false,
    "is_st": false,
    "is_star_or_chinext": false
  },
  "sample": false,
  "degraded": false,
  "warnings": [],
  "sources": [{"name": "fixture", "role": "ohlcv", "status": "ok"}],
  "disclaimer": "本结果为课程框架自检，不构成投资建议。"
}
```

## 3. Fail-closed

```json
{
  "ok": false,
  "error": "symbol_not_found",
  "primary_score": null,
  "posture": "数据不足",
  "disclaimer": "本结果为课程框架自检，不构成投资建议。"
}
```

无数据时 **不得** 编造分数或叙事。

## 4. posture 枚举（唯一允许）

- `偏强学习态` — score ≥ 70  
- `中性观察态` — 40 ≤ score < 70  
- `偏弱学习态` — score < 40  
- `数据不足` — fail-closed  

禁止映射为买卖词。
