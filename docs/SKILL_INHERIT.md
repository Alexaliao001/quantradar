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

*后续轮次追加在上方分隔线之下。*
