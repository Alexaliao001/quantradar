# STOCK_AGENT_MAP — stock-agent 思想 → QuantRadar 壳（路径 C）

> 版本：2026-07-26 · P0  
> SSOT 思想：`~/stock-skills`（`~/.claude/skills/stock-agent` → symlink）  
> 产品引擎：`~/charts`（`fetch_all` → `*_analysis.json`）  
> 产品壳：`~/quantradar` — **normalize + map + desk**；**不算分**

---

## 1. Purpose & 路径 C 边界

QuantRadar 公网站只消费 **charts 机械姿态**，不挂载 stock-agent DAG / LLM K3 / Firstrade。  
从 stock-agent **只借思想**：姿态≠方向、证据覆盖、降级、单一主结论、NO≠SELL、缺数据写 unknown。

| 层 | 职责 | 不算 / 不做 |
|----|------|-------------|
| `~/charts` | 机械分、门控状态、entry_timing、量能/期权诚实字段 | 壳不重算 |
| `~/quantradar` | HTTP、契约 map、Trust Gate、desk、funnel | 不嵌入 stock-skills |
| `~/stock-skills` | 个人研究 agent（四支柱 / Wave / cross） | **禁止**整仓进站 |

---

## 2. Source lock

| 角色 | 路径 | 备注 |
|------|------|------|
| 思想 SSOT | `~/stock-skills` | 勿用陈旧 `~/claude-stock` |
| Skill 入口 | `~/.claude/skills/stock-agent` | symlink → stock-skills |
| 引擎 | `~/charts` | 与 stock-skills **分叉并存** |
| 壳 | `~/quantradar` | `docs/ENGINE_CONTRACT.md` |

---

## 3. Signal vocabulary bridge（文档对照，非自动换算）

| charts `gate.signal` / `primary.action` | stock-agent 近似姿态 | 产品文案 |
|-----------------------------------------|----------------------|----------|
| FULL / BUILD / PROBE | BUY 区（强度递减） | 可参与 / 建仓 / 试探 |
| WAIT | WAIT | 观望 |
| NO | NO | 回避 / stand aside |
| PUT* | NO 区 + hedge 标签 | **Put / hedge bias — not a sell order** |

\* charts `PUT` ≠ stock-skills Put 研究层。上站文案必须标明 **PUT ≠ 卖出指令**。

**姿态 ≠ 方向**：`primary.action` 是机械姿态门控，不是「该做多/做空」的 direction 指令。  
stock-agent 的 `forward_call` / `direction_gate` **未**进 P0 契约（需 charts 先产出真实 JSON）。

---

## 4. Field map v1（P0）

| 来源（charts） | ENGINE 字段 | 状态 |
|----------------|-------------|------|
| `mechanical_scores.final_score` | `score.final` / `primary_score.value` | ✅ |
| `signal_timing_gated` \| `signal_mechanical` | `gate.signal` / `primary.action` | ✅ |
| `mechanical_scores.state` | `gate.state_*` | ✅ |
| `base_score.{volume_price,momentum,trend,risk}` | `score.breakdown[]` | ✅ |
| `mechanical_scores.entry_timing` | `gate.entry_timing` `{grade,total,max}` | ✅ P0（有则 map，无则省略） |
| `market_env` | `gate.market_gate` / `gate.sector_gate` / `market` | ✅ |
| `data_quality` + options snapshot | `data_quality.*` | ✅ |
| — | `forward.*` / `pillars.*` / `direction_gate` | ❌ 缺引擎 → 不编 |
| Wave5 / Firstrade / cross×K | — | 🚫 禁止公网 |

缺字段时：**省略或 `unknown`**，禁止用客户端启发式填 `pass`。

---

## 5. Desk 文案铁律（P0）

1. 单一 `primary_score`（mechanical posture）— 禁止第二 Composite。  
2. 标签：**Mechanical posture**；姿态 ≠ 方向。  
3. `PUT` → hedge bias，**不是卖出**。  
4. Gate 灯色只跟服务端 `gate.*.status` 与 `primary`（见 Trust / security）。  
5. artifact 模式 `options_actionable=false`。

---

## 6. Slice

| 切片 | 内容 | 谁做 |
|------|------|------|
| **P0** | 本文档；`gate.entry_timing` map；desk 姿态文案；Trust | 壳 |
| **P1** | `forward` / options evidence coverage / 真 PNG serve | `~/charts` 再 map |
| **P2** | 四支柱卡片、hierarchy、put research（`decision_authority=false`） | 引擎有字段才上 |

---

## 7. Forbidden

1. 整仓复制 / 嵌入 `stock-skills` 进 Manus 或 Render 镜像。  
2. 壳内重算机械分或混用 ss `final_score` 与 charts `final` 当双 Composite。  
3. 静默把 ss `BUY` 与 charts `FULL` 互换而不 bump 契约/文档。  
4. `NO`/`PUT` 文案写成「卖出 / 做空指令」。  
5. 假 Greeks / 假 live / 假社交证明 / mtime 冒充 freshness。  
6. 公网跑 Firstrade、下单、或同步 LLM K3/cross 作为 `/api/analyze`。

---

## 8. 验收

```bash
python3 -m unittest discover -s tests -v
curl -sS 'http://127.0.0.1:8765/api/sample?ticker=INTC' | python3 -c \
  "import sys,json;d=json.load(sys.stdin);assert d.get('primary_score');assert 'entry_timing' in (d.get('gate') or {})"
```

---

## 9. Changelog

| 日期 | 变更 |
|------|------|
| 2026-07-26 | P0：文档 + `gate.entry_timing` + desk 姿态文案 |
