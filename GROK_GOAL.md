# GROK /goal — QuantRadar 产品优化（免费数据 + 仓库恢复 + 去 Manus 锁）

> **用途**：优化 **QuantRadar 产品线**（线上 `https://quantradar.one` + GitHub `Alexaliao001/quantradar` + 本地引擎 `~/charts`）时，本文件是 Grok Build `/goal` 的**唯一主任务源**。  
> **不是** `stock-skills` 的 `GROK_GOAL_FREE_DATA_STACK.md`（那是 `/stock-agent` 管线省钱）；二者可复用 Provider 思路，**代码仓库与交付物不同**。  
> **证据**：2026-07-10 — `quantradar` / `quantradarold` GitHub **size=0 空仓**；`quantradar.one` HTTP 200（Cloudflare）；描述称 Yahoo+Polygon 双源 + Manus；本地完整分析引擎在 `~/charts`（`stock-charts` remote）；公开营销站 `quantradar-site`；选型报告 `~/charts/research/data_provider_comparison.md`（2026-06-10）。  
> **编排**：每轮 1 项、单写者；大改先 explore；密钥不进日志/commit。  
> **停止**：用户 pause / 说停；或 §八 S1–S10 全 ✅ 且用户认可 → `update_goal(completed=true)`。

---

## 粘贴版（复制到 Grok Build 开跑）

### 精简版（推荐）

```
/goal 优化 QuantRadar 产品。主任务源：~/charts/GROK_GOAL_QUANTRADAR.md

北极星：
  1) 恢复可编辑源码 SSOT（GitHub quantradar 不再空）
  2) 数据层 $0/hybrid：Yahoo + Alpha Vantage BYO + agent-reach 社交/新闻；
     Massive/Polygon 只保期权 Greeks（或自用引擎）
  3) 去 Manus 登录墙（产品可独立鉴权/访客读）
  4) 门控 Market→Sector→Stock + 评分/期权策略效果不崩

强制 Phase 0：
  - 确认 quantradar.one / manus.space 可达
  - 盘点 ~/charts · quantradar-site · Manus 项目
  - 选定 QR0 恢复路径（A 拉 Manus 代码 / B charts 产品化 / C 混合）
  - 本轮只做 1 个 QR-ID

每轮：最小 diff；禁止打印 API key；PROGRESS 写 ~/charts/PROGRESS_QUANTRADAR.md
commit 前确认仓库：产品代码 → quantradar；引擎工具 → stock-charts(charts)。
```

### 完整版

```
/goal QuantRadar 产品优化（仓库恢复 + 免费数据栈 + 去 Manus + 效果）。

任务源：~/charts/GROK_GOAL_QUANTRADAR.md
相关：
  ~/charts/research/data_provider_comparison.md
  ~/charts/site/*（域名/部署/Manus 笔记）
  ~/.codex/skills/quantradar-manus-ops/SKILL.md
  agent-reach skill（社交/调研免费抓取）
  stock-skills GROK_GOAL_FREE_DATA_STACK.md（仅作 Provider 思路参考，勿改错仓）

════════════════════════════════════
北极星
════════════════════════════════════
A. GitHub Alexaliao001/quantradar 有可 build 源码（非 empty）
B. 访客/登录用户能用核心分析，不强制 Manus 账号
C. 数据成本：产品层默认 free/BYO；自用完整期权可保留 Massive
D. 产品叙事兑现：门控 + 形态 + 量价 + 期权策略 + 1–100 分
E. 合规：个人档行情不转售；产品只分发分析结论或 BYO-key

Phase 0（强制）→ 然后按 §六 QR0→QR1→QR2… 每轮 1 项
```

---

## 一、使命（一句话）

把 **QuantRadar** 从「Manus 托管 + 空 GitHub + Polygon 账单焦虑」变成 **自有仓库可迭代、数据分层省钱、无 Manus 登录也能交付分析价值** 的产品。

### 1.1 用户体感

| ID | 体感 | 坏样子 | 好样子 |
|----|------|--------|--------|
| U1 | 代码在自己手里 | GitHub empty；改不动 | `quantradar` clone 可 dev/build |
| U2 | 不用 Manus 账号也能看 | 登录跳 manus.im | 自有 auth 或访客 demo 报告 |
| U3 | 账单可控 | 全站依赖付费 Polygon | hybrid：OHLCV/新闻免费；期权分档 |
| U4 | 分析可信 | 假 Greeks / 空链 | source 标注 + 降级诚实 |
| U5 | 域名产品一体 | 营销站与 app 分裂 | quantradar.one 清晰入口 |

### 1.2 资产地图（勿搞混）

| 资产 | 路径 / URL | 角色 | 2026-07-10 状态 |
|------|------------|------|-----------------|
| **产品 GitHub** | `github.com/Alexaliao001/quantradar` | 应用 SSOT（目标） | **empty size=0** |
| **旧备份名** | `quantradarold` | 历史 | empty |
| **公开营销站** | `quantradar-site` | 落地页 | 有静态资源 |
| **本地分析引擎** | `~/charts` → `stock-charts` | fetch/图表/扫描/报告 | **有完整 Python 栈** |
| **线上产品** | `https://quantradar.one` | 用户入口 | HTTP 200 |
| **Manus space** | `quantradar-*.manus.space` | 历史宿主 | 仍可达 |
| **选型报告** | `charts/research/data_provider_comparison.md` | 数据决策 SSOT | 2026-06-10 |
| **Manus ops** | `quantradar-manus-ops` skill | 发布/域名 | 有 |
| **stock-skills** | 另一产品 | `/stock-agent` 确定性管线 | 勿当 QR 源码 |

---

## 二、架构目标

```text
                    quantradar.one
                           │
          ┌────────────────┼────────────────┐
          ▼                ▼                ▼
     Marketing        App (SSR/SPA)     Auth (非 Manus)
   quantradar-site    quantradar repo    自有 session
          │                │
          │         ┌──────┴──────┐
          │         ▼             ▼
          │   Analysis API    Data Provider
          │   (可复用 charts)  free | hybrid | pro
          │         │             │
          │         └──────┬──────┘
          │                ▼
          │         结论/评分/图表（可分发）
          │         禁止转发 OPRA 原始行情（个人档）
```

### 2.1 数据三档（产品）

| 模式 | 行情 OHLCV | 期权 | 新闻/社交 | 适用 |
|------|------------|------|-----------|------|
| **free** | Yahoo / yfinance / AKShare 兜底 | Alpha Vantage HISTORICAL_OPTIONS（BYO，有限额）或 degraded 无 Greeks | agent-reach + RSS | 访客/试用 |
| **hybrid** | free 优先 | **Massive options** 仅服务端自有 key 算结论 | free + 可选 | **推荐产品默认** |
| **pro** | Massive 全量 | Massive snapshot | + 付费 news 可选 | 你自用 desk / 高价 SKU |

**已裁决（继承 data_provider_comparison，勿每轮重辩）**：

1. **自用引擎（~/charts）**：留 Massive 做期权；跨境不稳 → HK VPS 中转，不是换供应商。  
2. **产品层**：**禁止**把个人 Massive key 当「用户转发行情」；只分发分析结论，或 **BYO Alpha Vantage**。  
3. **Benzinga 扩展包**默认不买；earnings 用 web / agent-reach。  
4. **券商大陆 API 产品化路线**（富途/老虎/长桥）→ **拒绝**。  
5. **伪造 Greeks** → **拒绝**。

### 2.2 可继承的免费/本地能力

| 能力 | 来源 | 接到 QuantRadar 哪 |
|------|------|-------------------|
| 多平台抓取 | **agent-reach**（X/Reddit/雪球/Exa/Jina） | 情绪/调研柱，非 L1 硬价 |
| Yahoo 报价/VIX 范式 | `stock-skills/stockapp/vix.py`、charts 内 Yahoo 用法 | free quote |
| 双源叙事 | 产品描述已写 Yahoo+Polygon | 实现真正 fallback，非文案 |
| 图表/评分引擎 | `~/charts` fetch_all / generate_charts / scanner | 后端分析核 |
| 营销站 | `quantradar-site` / `charts/site-public` | 落地与定价 CTA |
| 选型矩阵 | `research/data_provider_comparison.md` | FD 决策 |

---

## 三、铁律

1. **密钥**：不打印、不 commit `.env`、不把 hardcoded key 留在源码（发现即 QR0 安全项）。  
2. **空仓诚实**：在 Manus/导出恢复前，禁止「假装 quantradar 已有全栈」乱写覆盖线上。  
3. **线上不盲推**：`quantradar.one` 已是活产品；部署须有回滚与确认。  
4. **合规**：个人档 Massive/Polygon 禁止再分发原始行情；产品输出评分/图表结论或 BYO。  
5. **单写者 / 每轮 1 backlog**；改分析公式须有 fixture 或样本前后对比。  
6. **仓界**：  
   - 产品应用 UI/API → 目标仓 `quantradar`  
   - 研究/图表 CLI 引擎 → `~/charts`（stock-charts）可先改，再抽模块进产品  
   - 勿把 stock-skills 整仓当 QR 前端  

---

## 四、每轮 SOP

```
0.  读本文件 §一资产图 + §六 未完成最高 ROI
0b. 若动 charts：cd ~/charts && git status；若动 quantradar：cd ~/quantradar
1.  诊断：相关 smoke（fetch 一只票 / curl 首页 / doctor）
2.  取 1 个 QR-ID；依赖未完成先做依赖
3.  最小实现
4.  验证：本项验收行 + 不泄密
5.  写 ~/charts/PROGRESS_QUANTRADAR.md 一行
6.  commit + push 到正确 remote（quantradar 或 stock-charts）
7.  update_goal(message=…)
```

卡住 >30min：记障碍，换下一项（常见：等 Manus 导出、等用户域名权限）。

---

## 五、优先级

```
P0 源码在手 + 安全（key）+ 不弄挂线上
  > P1 去 Manus 登录 / 可本地 dev
  > P2 数据 free/hybrid 落地（省钱 + 双源）
  > P3 分析质量与门控体验
  > P4 商业化 Stripe / 营销站合一
```

---

## 六、Backlog

### QR0 — 仓库与源码恢复（阻塞一切应用层优化）

| ID | 状态 | 任务 | 验收 |
|----|------|------|------|
| QR0-0 | ⬜ | **Phase0 盘点报告**落盘 `~/charts/site/QR_PHASE0_{date}.md`：empty 确认、线上入口、Manus project id、charts 可复用模块表 | 文件存在；含「恢复路径 A/B/C 推荐」 |
| QR0-1 | ⬜ | **选定恢复路径**（用户确认一项）：**A** Manus 导出/同步全量 app 进 `quantradar`；**B** 以 `~/charts`+site-public 重建薄产品壳；**C** A+B 混合（引擎 charts，UI 重建） | PROGRESS 写死路径字母 |
| QR0-2 | ⬜ | 执行恢复：`quantradar` 非 empty；README 可本地 dev 步骤 | `gh api .../contents` 有文件；clone build 说明可跑 |
| QR0-3 | ⬜ | 清扫 **hardcoded API key**（charts 内 `POLYGON_API_KEY` 默认字面量等）→ 仅 env | `rg` 无高熵 key；rotate 旧 key（用户操作） |
| QR0-4 | ⬜ | `.env.example` + `.gitignore` 密钥规范；双仓一致 | 无 secret 进 git |
| QR0-5 | ⬜ | 与 `quantradarold`：确认废弃或 archive 说明 | README 一句 |

### QR1 — 去 Manus 登录与可独立运行

| ID | 状态 | 任务 | 验收 |
|----|------|------|------|
| QR1-0 | ⬜ | **explore**：当前 `quantradar.one` 鉴权流（Manus OAuth？cookie？）HAR/笔记 | 报告：必登录路径清单 |
| QR1-1 | ⬜ | 访客可读：**样例报告** `/sample` 或 `/analysis/demo` 无登录 | curl 200 + 无跳转 manus.im |
| QR1-2 | ⬜ | 自有 auth 方案选型（email magic / 简单 password / 暂无）+ 最小实现或明确「仅 demo」 | 文档 + 代码或 ADR |
| QR1-3 | ⬜ | 剥离 Manus 品牌锁：登录 CTA、页脚、强制 app-auth 链接 | 产品文案自有 |
| QR1-4 | ⬜ | 本地 `docker-compose` 或 `pnpm/npm/python` 一键起 API+UI | README 5 步内成功 |

### QR2 — 数据层 free / hybrid（省钱核心）

| ID | 状态 | 任务 | 验收 |
|----|------|------|------|
| QR2-0 | ⬜ | 对照 `data_provider_comparison.md` 写 **产品 Data ADR**（模式 free/hybrid/pro 字段与 env） | `docs/DATA_PROVIDER.md` |
| QR2-1 | ⬜ | **OHLCV Provider**：Yahoo/yfinance 主路径 + Massive 可选；统一内部 bar schema | 无 key 可出日线 |
| QR2-2 | ⬜ | **Quote/VIX**：Yahoo + FRED 锚（可移植 stock-skills vix 思路） | VIX 有 source 字段 |
| QR2-3 | ⬜ | **Options**：hybrid 服务端 Massive 只算结论；free 用 AV BYO 或 `available=false`+说明 | 不暴露原始全链给浏览器若 ToS 禁止 |
| QR2-4 | ⬜ | **News/Social**：agent-reach 封装（服务端或 worker）；失败 degraded | 无付费 NewsAPI |
| QR2-5 | ⬜ | **audit**：每请求/每标的外部 HTTP 计数与 provider 标签 | 日志或 admin 一行 |
| QR2-6 | ⬜ | 跨境：文档化 HK VPS / proxy 可选（个人 charts 与产品采集层） | docs 一节；非必须实现 |

### QR3 — 分析产品能力（门控 / 评分 / 期权策略）

| ID | 状态 | 任务 | 验收 |
|----|------|------|------|
| QR3-1 | ⬜ | 固化 **Market→Sector→Stock** 门控 API 契约与 UI 展示 | 样例 TSLA 报告含三层 |
| QR3-2 | ⬜ | 1–100 综合分：输入字段表 + 与 charts/score 对齐或诚实「产品分」 | 文档 + 可复现 |
| QR3-3 | ⬜ | 形态/量价：接 charts `generate_charts` 或预生成资产 | 图或 JSON 指标可见 |
| QR3-4 | ⬜ | 期权策略推荐：仅 hybrid/pro；free 显示升级/BYO | 文案不骗 |
| QR3-5 | ⬜ | 质量闸：空数据不编造分数；`data_warnings[]` | 故意断网/无 key 测 |

### QR4 — 线上域名 / 部署 / 商业化

| ID | 状态 | 任务 | 验收 |
|----|------|------|------|
| QR4-1 | ⬜ | 部署拓扑文档：Cloudflare + 现宿主（Manus/Render/…） | `site/DEPLOY_*.md` 更新 |
| QR4-2 | ⬜ | 营销站 `quantradar-site` 与 app 入口统一 CTA | 链到正确 URL |
| QR4-3 | ⬜ | Stripe Payment Link 接线（已有 `stripe_payment_links.py` 线索） | 测试模式 checkout |
| QR4-4 | ⬜ | 监控：首页 + `/api/health` 定时 | 脚本或 Uptime |

### QR5 — 与 stock-skills / agent-reach 协同（可选）

| ID | 状态 | 任务 | 验收 |
|----|------|------|------|
| QR5-1 | ⬜ | 文档：哪些模块可从 stock-skills **只读复用思想**（vix/provider），禁止双写 | ADR |
| QR5-2 | ⬜ | agent-reach doctor 纳入 QR 运维 checklist | checklist |
| QR5-3 | ⬜ | 明确 **不做**：把 stock-skills `/stock-agent` 原样嵌进 QR 当后端（边界） | 本文件 FD9 式拒绝 |

### QR9 — 拒绝 / 搁置

| ID | 裁决 | 说明 |
|----|------|------|
| QR9-1 | 拒绝 | 大陆券商 API 做产品数据源 |
| QR9-2 | 拒绝 | 伪造期权 Greeks |
| QR9-3 | 拒绝 | 个人 Massive key 向终端用户转发原始 OPRA |
| QR9-4 | 搁置 | 全量替换 Massive 自用期权（除非账单不可接受） |
| QR9-5 | 搁置 | Benzinga 多 expansion 订阅 |

---

## 七、验收矩阵

| 层级 | 命令 / 检查 | 通过 |
|------|-------------|------|
| 仓非空 | `gh api repos/Alexaliao001/quantradar --jq .size` | >0 且 contents 有源码 |
| 本地 dev | 按 README 起服务 | 本机打开分析页 |
| free 数据 | 无 POLYGON/MASSIVE key 跑一只日线 | 有 bars 或诚实错误 |
| 线上 | `curl -sI https://quantradar.one` | 2xx/3xx 预期内 |
| 无 Manus 强登 | 访客样例路径 | 不强制 manus.im |
| 密钥 | `rg -n 'api[_-]?key|POLYGON|MASSIVE' --glob '!**/.env*'` 人工审 | 无明文生产 key |
| 进度 | `PROGRESS_QUANTRADAR.md` | 每轮一行 |

---

## 八、收官闸门 S1–S10

| ID | 闸门 |
|----|------|
| S1 | Phase0 报告 + 恢复路径锁定 |
| S2 | `quantradar` 非 empty + 可 clone |
| S3 | 无明文 key |
| S4 | 本地一键 dev |
| S5 | 访客样例无 Manus 登录 |
| S6 | free OHLCV 路径 |
| S7 | hybrid/pro 期权策略诚实分档 |
| S8 | agent-reach 或等价免费新闻/社交一路 |
| S9 | 门控三层在样例报告可见 |
| S10 | 部署文档 + 回滚说明 |

---

## 九、首轮推荐（现在就能做）

因 **GitHub 空仓**，**禁止**直接大改「不存在的 app 源码」。

1. **QR0-0** Phase0 盘点报告（只读 + 写 md）  
2. 用户确认 **QR0-1** 路径 A/B/C  
3. **QR0-3** 顺手清 charts 明文 key（高安全 ROI）  
4. 有源码后：QR1-1 访客样例 → QR2-0/2-1 数据层  

若 Manus 暂不能导出：默认建议路径 **C** — UI 可重建，分析核用 `~/charts`，先恢复可迭代产品，再对齐旧 Manus UI。

---

## 十、进度与 commit 约定

| 项 | 约定 |
|----|------|
| 进度文件 | `~/charts/PROGRESS_QUANTRADAR.md` |
| commit 前缀 | `qr(QR0-0): …` |
| 产品仓 remote | `Alexaliao001/quantradar` |
| 引擎仓 remote | `Alexaliao001/stock-charts`（`~/charts`） |
| 本 goal 副本 | 恢复后复制到 `quantradar/GROK_GOAL.md` 作仓内 SSOT |

---

## 十一、与其它 goal 关系

| 目标 | 文件 |
|------|------|
| **QuantRadar 产品（本文件）** | `~/charts/GROK_GOAL_QUANTRADAR.md` |
| stock-agent 省 Massive | `stock-skills/GROK_GOAL_FREE_DATA_STACK.md` |
| stock-agent 字段 ROI | `stock-skills/GROK_GOAL_DATA_AUDIT.md` |
| 个人图表/交易研究 | `~/charts` 日常 + README |

**误用纠正（2026-07-10）**：曾把「免费 API / agent-reach」goal 写进 stock-skills；若目标是 **quantradar.one / quantradar 仓**，**只用本文件**。

---

*创建：2026-07-10 — 用户纠正目标为 QuantRadar；GitHub empty + charts 引擎 + 数据选型报告对齐*
