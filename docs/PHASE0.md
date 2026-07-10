# PHASE0 — QuantRadar 盘点（QR0-0）

> 路径 C：`~/charts` = 分析核；本仓 = 产品壳。本文件让实现者无需重新摸索 charts 即可开工。  
> 日期：2026-07-10

---

## 1. 线上 / 产品行为笔记

| 项 | 现状 |
|----|------|
| 域名 | https://quantradar.one |
| 历史实现位置 | 引擎侧曾有完整 site：`~/charts/quantradar_site_api.py` + `~/charts/site/` + `site-public/` |
| 产品 SSOT | 本仓库 `Alexaliao001/quantradar`（GitHub）；Manus 只 pull 发布 |
| 当前本仓 | goal/文档为主；**最小壳自 QR0-2 起**（`python -m app`） |
| 访客 sample | charts 有 `reports/sample-site-current` 与 site API `/api/sample-report` |
| 计费 | charts site API 含 Stripe webhook / checkout（壳层后续 QR6 再接，不在 PHASE0） |
| 分析真源 | `fetch_all.py` → `mechanical_scores` / `indicator_data.chart_files`；禁止在壳内重写评分公式 |

### 用户体感对齐（U1–U8 摘录）

- **U1**：clone 两仓可 dev；本轮交付最小壳 + charts 调用约定  
- **U2**：门控/分/sources/warnings 经 ENGINE_CONTRACT 出壳  
- **U4**：不伪造 Greeks（contract 不输出虚构 IV/OI）  
- **U8**：`/health` 预留 `git_sha`（QR1-4 完善 charts 可达性）

---

## 2. charts 可调用入口表

| # | 入口 | 调用方式 | 产出 | 壳如何用 |
|---|------|----------|------|----------|
| 1 | `~/charts/fetch_all.py TICKER [SECTOR_ETF]` | CLI / subprocess；stdout = JSON | `ticker`, `mechanical_scores`, `indicator_data`（含 `chart_files`）, `data_quality.warnings`, `market_env`, `fundamentals` | **主分析路径**；壳 facade 调此脚本并 map 到 ENGINE_CONTRACT |
| 2 | `~/charts/generate_charts.py TICKER INPUT.json` | CLI；stdin 文件 | 4 TF PNG + JSON summary stdout | 由 `fetch_all` 内部调用；**壳不直接分叉** |
| 3 | `~/charts/report_builder.py TICKER…` | CLI | `reports/<run>/report.html` + `report_data.json` + `assets/*_analysis.json` | 长报告 / 分享页；API 可 subprocess，超时更长 |
| 4 | `~/charts/analyze_and_report.py` | CLI 薄包装 → report_builder | 同上 | 一键报告别名 |
| 5 | `~/charts/scanner.py [--json] [--tickers …]` | CLI | `scanner_reports/*.json` 或 stdout | 扫描盘，非单票首屏 |
| 6 | `~/charts/quantradar_site_api.py` | FastAPI 进程 | `/api/trading-workbench`, `/api/report`, `/api/health`, sample | **参考实现**（workbench 已 subprocess `fetch_all`）；产品壳应重建于本仓，勿整文件拷贝当 SSOT |
| 7 | `~/charts/market_clock.py` | import / 间接 | 会话/时区上下文 | 健康检查与 briefing 时间戳 |
| 8 | 已有 JSON 工件 | 读盘 | `reports/**/assets/{TICKER}_analysis.json`、`sample-site-current` | **离线 / 无 key 回退**：读真实 charts 产出，不手造分数 |

### 推荐最小调用链（QR0-2）

```text
shell POST /api/analyze {ticker}
  → charts_facade
       ├─ live:  python fetch_all.py TICKER  （CHARTS_DIR 指向 ~/charts）
       └─ artifact: 读 fixtures 或 CHARTS_DIR/reports/... 真实 JSON
  → map_to_engine_response()  # 仅字段映射，不算分
  → ENGINE_CONTRACT JSON
```

---

## 3. 产品壳技术选型建议

| 层 | 选型 | 理由 |
|----|------|------|
| 运行时 | **Python 3.11+ stdlib**（`http.server`）首版 | 零依赖；Manus/本机均可 `python -m app`；后续可换 FastAPI 而不改契约 |
| API | REST JSON：`/health`、`/api/analyze` | 与 charts site API 思想对齐，但契约以本仓 `ENGINE_CONTRACT` 为准 |
| UI | 单页 `static/index.html` | desk 气质后续 QR4；PHASE0 仅验证分析路径 |
| 引擎边界 | subprocess / 读 artifact / 未来 thin import | **禁止**粘贴 `generate_charts` 全量指标公式 |
| 配置 | 环境变量 `CHARTS_DIR`、`QUANTRADAR_MODE=live\|artifact`、`PORT` | 密钥只在 charts 侧（`.polygon_key` / env），不进本仓 |
| 测试 | stdlib `unittest` + 契约校验 | 驱动真实 map/facade，不用假分数 |
| 发布 | GitHub main → 用户 Manus pull | 见 `docs/MANUS_SYNC.md` |

### 明确不做（本轮）

- 鉴权 / Stripe / 多 ticker 工作台  
- 在壳内重算 mechanical_scores  
- 嵌入整个 stock-skills 或 charts 树进 Manus 构建  

---

## 4. 相关文档

| 文档 | 作用 |
|------|------|
| [ENGINE_CONTRACT.md](./ENGINE_CONTRACT.md) | charts→壳 JSON 契约（QR0-4） |
| [SKILL_INHERIT.md](./SKILL_INHERIT.md) | Skill 采掘账本 |
| [MANUS_SYNC.md](./MANUS_SYNC.md) | 用户发布步骤 |
| `~/charts/commands/*.md` | 技术分析 / 形态 / 回调 / anti-noise CLI skills |

---

*QR0-0 ✅ — 盘点完成，可进入 QR0-4 契约与 QR0-2 最小壳。*
