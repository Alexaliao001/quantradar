# Skill 继承账本（QuantRadar）

> 每轮 `/goal` 必须追加。模板见 `GROK_GOAL.md` §4.6。  
> 水源：L1 本机 / L2 仓库 / L3 X。采用档：直接 | 技术 | 思想 | 观望 | 拒绝。  
> **路径 C 已锁定**（2026-07-10）。

---

### 2026-07-10 · 决策 · 路径 C

- 水源：用户确认  
- 层：Ops/Architecture  
- 提炼：引擎 charts + 产品壳 quantradar；Manus 只发布  
- 采用档：**直接**（架构裁决）  
- 落地：GROK_GOAL v3；QR0-1 ✅；拒绝「等 Manus 全量才开工」

---

### 2026-07-10 · 建账 · 基线盘点（本地 skill）

| 来源 | 层 | 提炼 | 判定 | 落地 |
|------|----|------|------|------|
| agent-reach | Data/Research | 15 平台免费抓取；X 搜 skill 也走此通道 | **采用** | QR2-4；每轮 §四 |
| design-taste-frontend | FE | 反 AI 模板站、方向推断 | **采用** | QR4-1/4-2 |
| emil-design-eng | FE | 克制动效与组件细节 | **采用** | QR4-4 |
| web-design-guidelines | FE | a11y/表单/对比度清单 | **采用** | QR4-1 |
| research-brief | Process | 有出处调研 | **采用** | QR0-0、QR7-2 |
| ship-code | Process | 读仓小步交付 | **采用** | 每轮 SOP |
| quantradar-manus-ops | Ops | Manus/域名路径 | **采用** | QR0-3、QR6-3 |
| stock-agent 思想 | Analysis | 确定性层、degraded、契约字段 | **采用（思想）** | QR3；禁止整仓嵌入 |
| find-skills | Meta | 发现可装 skill | **采用** | QR-SK / QR7 |
| gzh-pipeline Hot | Research | agent-reach 优先调研节奏 | **观望** | 可借鉴 Scout 顺序 |
| seedance / 恋爱类 skill | — | 与量化产品无关 | **拒绝** | — |

### 2026-07-10 · 建账 · X 采样（待实现验证）

| 来源 | 层 | 提炼 | 判定 | 落地 |
|------|----|------|------|------|
| X: Trading Floor 多 agent + FastAPI SSE + Next.js | BE/FE | 分角色分析 + 流式「董事会」UI | **观望** | 仅当门控 L1 稳后 QR3-6 |
| X: Stock-Agent-Ops 生产栈 | BE/Ops | Redis 缓存限流、critic、监控、Docker | **采用（裁剪）** | QR2-5、QR5-2/3、QR5-4 |
| X: virattt Data→Signal→Risk→Decision | Analysis | 流水线与现有门控同构 | **采用（对齐）** | QR3-1 契约命名可对齐 |
| X: Meng To 设计 skill 库 | FE | 批量 UI skill、反 slop | **观望** | QR4；保持 trading desk 气质 |
| X: RayFernando skills 结构 | Meta | 高质量 skill 目录设计 | **观望** | QR-SK3 学结构 |
| X: yfinance 封装 | Data | free OHLCV 工具 | **采用** | QR2-1 |
| X: 全自动永不停交易 agent | — | 实盘 trope | **拒绝** | 非产品范围 |
| charts/research/data_provider_comparison | Data | Massive 自用、产品 BYO/结论分发、拒券商 API | **采用** | QR2-0 铁律 |

---

### 2026-07-10 · 禁止 Manus 登录（用户要求）

- 水源：L2 线上探针 + `charts/site/LIVE_ENDPOINTS_2026-03-21.md`（历史误把 CTA 指到 manus app-auth）
- 比对：Manus 平台托管 SPA（强制 OAuth）vs GitHub 访客壳 — **选访客壳**
- 层：Ops / Auth / UX
- 提炼：线上 quantradar.one 仍是 Manus SPA；SSOT 壳必须 410 掉 oauth 路径且 UI 无登录按钮；发布时关 App Auth
- 采用档：**直接**（产品铁律）
- 落地：`docs/AUTH.md`、MANUS_SYNC 更新、server 410、tests

### 2026-07-10 · QR0-0 / QR0-4 / QR0-2 · 路径 C 最小壳落地

- 水源：**L1** ship-code / research-brief；**L2** `~/charts/fetch_all.py`、`quantradar_site_api.py`（workbench subprocess 模式）、`reports/sample-site-current/*_analysis.json`、`commands/*.md` 入口表
- 比对：charts site API 厚壳 vs 本仓 stdlib 薄壳 — 选薄壳 + ENGINE_CONTRACT，避免把 `quantradar_site_api.py` 整文件当 SSOT 迁入
- 层：Architecture / BE / Analysis 边界
- 提炼：
  1. 分析真源 = charts JSON（`mechanical_scores` / `chart_files` / `data_quality.warnings`）
  2. 壳只 normalize + map + HTTP，不算分
  3. 默认 `artifact` 模式可无 key 验收；`live` = subprocess `fetch_all.py`
- 采用档：**技术**（subprocess/读 artifact facade）+ **思想**（stock-agent degraded/sources/warnings）
- 深度分析：§4.2 — 解 U1/U2；可迁移物=契约+facade；不与路径 C 冲突；成本=零新依赖；最小 diff=PHASE0+CONTRACT+`python -m app`；charts 厚站 vs 薄壳 → 薄壳胜（Manus 可 pull）
- 落地：QR0-0 `docs/PHASE0.md`；QR0-4 `docs/ENGINE_CONTRACT.md`；QR0-2 `app/` + `static/` + fixture

---

### 2026-07-16 · QD1-0 · Pro 价值裁决 B（supporter_until_mount）

- 水源：**L1** quantradar-manus-ops / ship-code；**L2** `docs/SITES_LIVE.md`、`render.yaml`、`charts/fetch_all.py`、`research/data_provider_comparison.md`；explore×2 + 线上 `/health` 探针
- 比对：A 挂载 charts 卖 live vs B 支持者价 — **选 B**（Free 无 charts 树、无 Polygon、冷启动不适配）
- 层：Commercial / Ops / FE copy
- 提炼：`pro_value=supporter_until_mount|live_ready` 进 `/health` 与 billing status；Pro 门控保留，文案不卖空气
- 采用档：**直接**（裁决）+ **技术**（health 字段）
- 落地：`docs/PRO_VALUE.md`；pricing/desk 文案；QR6-2 ✅

### 2026-07-16 · QD0-0 · desk-v1 + billing 闭环落库

- 水源：**L1** ship-code / quantradar-stripe-ops（思想）+ Stripe plugin best-practices；**L2** 仓内 `app/stripe_billing.py` 既有 Checkout；explore×2 审查；bugbot verifier
- 比对：session metadata vs `subscription_data.metadata`（cancel→free）— 采用后者写入；one-time `payment` 回退 vs 强制 Price ID — 强制 Price ID（不卖永久 Pro）
- 层：Billing / Auth / FE desk
- 提炼：
  1. Stripe 不把 session metadata 复制到 subscription → cancel webhook 必须写 `subscription_data[metadata][email]`
  2. webhook apply `ok:false` 须 4xx 让 Stripe 重试
  3. `auth=stripe` stub 可被 password register claim 并保留 plan
  4. live 文案在 QD1-0 前只写「when mounted」
- 采用档：**技术**（subscription metadata / paid gate）+ **直接**（desk+billing 落库）
- 落地：`qr(QD0-0)` commit；`tests/test_billing.py`；GROK_GOAL QR4-2/4-3 ✅、QR6-1 🔶

---

### 2026-07-17 · ENGAGE · 商业闭环参与度

- 水源：**L1** ship-code / decision-lab；**L2** `GROK_GOAL_COMMERCIAL.md` §2 心理杠杆 + Trust Gate；explore 盘点 desk/billing 缺口
- 比对：第三方 tracker vs 服务端 JSONL — **选 JSONL**（N1–N5 诚实、无 PII）；假社交证明 — **拒绝**
- 层：Commercial / FE / Analytics
- 提炼：
  1. 参与回路 = Verdict → Why → Gates → Breakdown → Next（remind/upgrade/re-check）
  2. WAIT/NO 用 avoided_line（损失厌恶）而非挡结果注册墙
  3. freeze_label 制造诚实新鲜度缺口，不伪造 live
- 采用档：**直接**（funnel+desk+FAQ）+ **技术**（score.breakdown / engagement 契约字段）
- 落地：`app/funnel.py`、`docs/ENGAGEMENT.md`、QD1-5/2-1/2-2/4-1/4-2 ✅

---

### 2026-07-26 · QD2-3 · 统一动效 + 封面升级

- 水源：**L1** frontend-design / ship-code；**L2** `docs/ENGAGEMENT.md`、`static/site.css`、Trust Gate / PRO_VALUE
- 比对：第三方 motion/lib vs CSS vars+SVG — **选 stdlib 壳内纯 CSS/SVG**；假社交/live 卖点 — **拒绝**；首屏堆 stats/cards — **拒绝**（品牌雷达 composition）
- 层：FE / Commercial presence
- 提炼：
  1. Motion SSOT = `--motion-*` + 命名 keyframes；desk `data-state` 驱动 loading scan / ready 点亮
  2. Dial 用固定半圆 + `stroke-dashoffset`，比重写 path `d` 更稳
  3. `prefers-reduced-motion` 必须关掉循环扫描与 stagger，保留瞬时可读态
- 采用档：**直接**（hero+desk+pricing 对齐）+ **技术**（CSS motion system）
- 落地：`static/site.css`、`static/index.html`、`static/pricing.html`、`docs/ENGAGEMENT.md` · QD2-3 ✅

### 2026-07-26 · P0 · stock-agent 映射 + 安全收口

- 水源：**L1** stock-agent（思想）/ ship-code；**L2** `~/stock-skills` 调研 8300f684、`~/charts` entry_timing；Security Review 959d7ee6 Medium×2
- 比对：整仓嵌 ss vs 路径 C 只 map charts — **选只 map**；Gate UI 用 spy 启发式 vs 服务端 status — **选服务端**
- 层：Analysis 边界 / FE / Security
- 提炼：
  1. `gate.entry_timing` 有则 map、无则省略；姿态≠方向；PUT≠卖出
  2. sample/notify/register 与 analyze 同级限流；funnel JSONL 体积帽
  3. 禁止双轨公式与假 pass
- 采用档：**思想**（stock-agent）+ **技术**（限流/体积帽）+ **直接**（MAP 文档）
- 落地：`docs/STOCK_AGENT_MAP.md`、`app/contract.py`、`app/funnel.py`、`app/server.py`、desk 文案

---

*后续轮次追加在上方分隔线之下。*
