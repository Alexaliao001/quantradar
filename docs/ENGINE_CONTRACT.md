# ENGINE_CONTRACT — charts → quantradar 壳（QR0-4）

> 版本：`1.0.0`  
> 真源：charts 产出的 JSON（`fetch_all` stdout 或 `*_analysis.json`）  
> 壳职责：**请求规范化 + 字段映射 + 展示**；**不算** volume/momentum/trend 等机械分。

---

## 1. 请求（shell → facade）

### 1.1 形状（versioned）

```json
{
  "contract_version": "1.0.0",
  "ticker": "INTC",
  "sector": "SMH",
  "context": {
    "mode": "artifact",
    "request_id": "optional-client-id"
  }
}
```

| 字段 | 类型 | 必需 | 说明 |
|------|------|------|------|
| `contract_version` | string | 否 | 默认 `1.0.0`；壳可填 |
| `ticker` | string | **是** | 1–10 字符，字母数字 `.` `-`；规范化为大写 |
| `sector` | string | 否 | 行业 ETF（如 `SMH`/`XLK`），传给 `fetch_all` 第二参 |
| `context.mode` | `"live"` \| `"artifact"` | 否 | 默认看环境 `QUANTRADAR_MODE` |
| `context.request_id` | string | 否 | 链路追踪 |

### 1.2 HTTP 绑定（QR0-2）

- `GET /api/analyze?ticker=INTC&sector=SMH`  
- `POST /api/analyze` body = 上表 JSON  

非法 ticker → HTTP 400 + `{ "ok": false, "error": "..." }`。

---

## 2. 响应（facade → shell / UI）

### 2.1 成功形状

```json
{
  "ok": true,
  "contract_version": "1.0.0",
  "ticker": "INTC",
  "company_name": "Intel Corporation",
  "sector": "Technology",
  "gate": {
    "state_code": "B",
    "state_name": "uptrend_pullback",
    "state_reason": "Weekly MA bullish, pullback 7.1%",
    "signal": "NO",
    "signal_label": "No / stand aside"
  },
  "score": {
    "final": 39,
    "base_total": 53,
    "scale": 100
  },
  "artifacts": {
    "charts": {
      "daily_price": "/path/or/null",
      "daily_indicators": "/path/or/null"
    },
    "analysis_json": "optional path to source artifact",
    "report_html": null
  },
  "sources": [
    {"name": "charts.fetch_all", "role": "engine", "status": "ok"},
    {"name": "polygon", "role": "ohlcv", "status": "degraded"}
  ],
  "warnings": [],
  "degraded": false,
  "market": {
    "market_state": "closed",
    "spy_change_pct": -0.12,
    "sector_etf": "SMH",
    "vix_current": 18.2
  },
  "meta": {
    "engine": "charts",
    "mode": "artifact",
    "fetch_time": "2026-03-21T01:43:25.276639",
    "generated_at": "…"
  }
}
```

### 2.2 必需字段（校验用）

| 字段 | 规则 |
|------|------|
| `ok` | boolean |
| `contract_version` | non-empty string |
| `ticker` | non-empty string |
| `gate` | object；至少含 `signal` **或** `state_code` |
| `score` | object；含 `final`（number）与 `scale` |
| `artifacts` | object；含 `charts`（object，可空路径） |
| `sources` | array（可空，但键必须存在） |
| `warnings` | array（可空） |

降级：引擎不可用时 `ok=false` **或** `ok=true` + `degraded=true` + `warnings` 说明原因；**禁止**编造 `score.final` / Greeks。

### 2.3 从 charts 原始 JSON 的映射

| 契约字段 | charts 来源 |
|----------|-------------|
| `ticker` | `payload.ticker` |
| `gate.state_*` | `mechanical_scores.state.{code,name,reason}` |
| `gate.signal` | `signal_timing_gated` 否则 `signal_mechanical` |
| `score.final` | `mechanical_scores.final_score` |
| `score.base_total` | `mechanical_scores.base_score.total` |
| `artifacts.charts.*` | `indicator_data.chart_files.{tf}.{price\|indicators}` |
| `warnings` | `data_quality.warnings` (+ 可选 trend degradation) |
| `sources` | 由 facade 根据 mode / data_quality 生成，不由壳瞎编行情源细节 |
| `market.*` | `market_env.*` |
| `company_name` / `sector` | `fundamentals.*` |

完整 JSON Schema：[`schemas/engine_response.schema.json`](../schemas/engine_response.schema.json)。

---

## 3. 调用模式

| mode | 行为 |
|------|------|
| `live` | `subprocess`: `python {CHARTS_DIR}/fetch_all.py TICKER [SECTOR]`，解析 stdout JSON |
| `artifact` | 读 `{CHARTS_DIR}/reports/**/assets/{TICKER}_analysis.json` 或仓内 `fixtures/charts_sample/{TICKER}_analysis.json`（**真实 charts 产出副本**） |

环境变量：

| 变量 | 默认 | 含义 |
|------|------|------|
| `CHARTS_DIR` | `~/charts` | 引擎根目录 |
| `QUANTRADAR_MODE` | `artifact` | `live` 需网络 + Polygon/Yahoo |
| `PORT` | `8765` | 壳监听端口 |

---

## 4. 非目标（契约边界）

- 壳内重新实现 `generate_charts` / RSI / MACD / 机械分  
- 输出伪造 IV / Greeks / OI  
- 强制 Manus 登录字段  

---

## 5. 样例与校验

```bash
# 单元：映射 + schema
python -m unittest discover -s tests -v

# 对照样例
python scripts/validate_contract_sample.py
```

样例对象：`schemas/samples/engine_response.sample.json`（由真实 fixture map 生成，可再校验）。

---

*QR0-4 ✅ — 壳只消费本契约，评分真源在 charts。*
