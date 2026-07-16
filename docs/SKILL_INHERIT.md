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

*后续轮次追加在上方分隔线之下。*
