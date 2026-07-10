# GROK /goal — QuantRadar 极致产品优化 v3

> **唯一主任务源**（产品仓 SSOT）：本文件 `Alexaliao001/quantradar/GROK_GOAL.md`  
> **镜像**：`~/charts/GROK_GOAL_QUANTRADAR.md`  
> **产品**：https://quantradar.one · 发布：**Manus**（你 pull GitHub 后发布）  
> **恢复路径（已锁定 · 2026-07-10 用户确认）**：**C = 混合**  
> - **分析核 / 图表 / 扫描 / 数据抓取**：复用并演进 `~/charts`（stock-charts）  
> - **产品 UI / API / 鉴权 / 计费壳**：在本仓 `quantradar` 重建或薄封装，**不**等待 Manus 全量导出才开工  
> - Manus 仅 **sync GitHub + 构建发布**，不是源码 SSOT  
>
> **工程闭环（强制）**：
>
> ```text
> git pull (quantradar [+ charts 若改引擎])
>   → 本机优化（可多 agent 勘探，单写者落地）
>   → 验证 → git push
>   → 你 Manus pull/sync → 发布 quantradar.one
> ```
>
> **禁止**：Manus 独有大 diff 不回写 GitHub；伪造 Greeks；个人档行情转售；整仓嵌入 stock-skills。

---

## 粘贴版（复制到 Grok Build）

### 精简版（推荐）

```
/goal QuantRadar 极致优化 v3。主任务源：~/quantradar/GROK_GOAL.md

路径 C（已锁定）：引擎 ~/charts + 产品壳 quantradar；Manus 只 pull 发布。
闭环：本机 pull → 优化 → push → 你 Manus 发布。

能力栈（强制）：
  · 本地 + 仓库 skill（charts/commands、stock-skills 有用部分、~/.grok|claude|agents skills）
  · 卡住 / 方案不明：X 多方搜 skill/架构 → 深度比对 → inherit 或拒
  · 可多 agent 并行勘探；全仓单写者；L1/契约改动必验收

每轮：
  1) git -C ~/quantradar pull --rebase（改引擎则 charts 也 pull）
  2) §四 Skill 环：本地/仓内优先；不足则 X 深挖；写 SKILL_INHERIT.md
  3) 1 个 QR-ID；路径 C 边界不破
  4) 验证 → commit → push
  5) PROGRESS + 「可 Manus pull 发布」

下一优先：QR0-0 盘点(若未) → QR0-2 最小产品壳进仓 → QR0-SEC → QR2-1 free OHLCV 接 charts
```

### 完整版

```
/goal QuantRadar v3：路径 C + 全环节专业级 + Skill 深采掘 + 多 agent 加速。

SSOT：github.com/Alexaliao001/quantradar → ~/quantradar
引擎：~/charts（可改，改后 push stock-charts，产品只依赖稳定接口）
发布：用户 Manus pull → 发布（代理不默认代点）

路径 C：
  charts = 数据/图表/扫描/指标/报告构建核
  quantradar = HTTP/API/UI/auth/billing/health/访客样例
  禁止在 quantradar 复制粘贴整份 generate_charts 分叉；优先 import/subprocess/抽 package

Skill 策略（§四）：
  L1 本机 skill → L2 用户仓库 skill/commands → L3 卡住才 X 多方比对
  采用方式：直接用 skill | 摘技术点 | 只借思想
  多 agent：explore≤2 并行只读；1 写者；可选 verifier

北极星 P1–P8 同正文。每轮 1 QR-ID。S1–S12 收官。
```

---

## 一、使命

在 **路径 C** 下，把 QuantRadar 做成：**charts 引擎可靠、产品壳专业、GitHub SSOT、Manus 可一键发布**；每个关键环节通过 **本地/仓库 skill +（必要时）X 多方深挖** 持续升级到专业级。

### 1.1 路径 C 边界（实现时对照）

| 放 `~/charts` | 放 `quantradar` |
|---------------|-----------------|
| fetch_all / generate_charts / scanner / market_clock | 路由、页面、布局、desk UI |
| polygon/yahoo 原始拉取与指标计算 | API 聚合层、缓存、限流、/health |
| 研究脚本、CLI skills（commands/） | 鉴权、访客 sample、Stripe CTA |
| data_provider 研究笔记 | 产品 ENV、Manus 构建适配 |

**抽库原则**：产品需要的能力优先 **稳定 CLI/JSON 接口** 调用 charts，避免双份公式。

### 1.2 发布拓扑

```text
~/charts (引擎) ──push──► stock-charts
~/quantradar (壳) ──push──► quantradar ──你 pull──► Manus ──发布──► quantradar.one
```

### 1.3 用户体感 U1–U8

| ID | 好样子 |
|----|--------|
| U1 | clone 两仓可 dev；push 后 Manus 能同步 |
| U2 | 门控三层 + sources + warnings |
| U3 | free/hybrid 账单可控 |
| U4 | 不伪造 Greeks |
| U5 | desk 级 UI，非 AI 模板站 |
| U6 | 缓存/限流/health |
| U7 | 访客 sample 无强制 Manus 登录 |
| U8 | 发布可核对 git_sha |

---

## 二、资产地图

| 资产 | 位置 | 角色 |
|------|------|------|
| 产品壳 SSOT | `~/quantradar` | UI/API/本 goal |
| 引擎 | `~/charts` | 分析核 |
| 引擎 CLI skills | `~/charts/commands/*.md` | 技术分析/形态/回调/anti-noise |
| 研究与确定性参考 | `~/stock-skills`（只读借思想/可选抽模块） | stock-agent、CONTRACT 模式 |
| 本机通用 skills | `~/.grok|claude|agents/skills` | FE/调研/运维 |
| 线上 | quantradar.one | Manus 产物 |
| 继承账本 | `docs/SKILL_INHERIT.md` | 强制维护 |
| 进度 | `PROGRESS.md` + `~/charts/PROGRESS_QUANTRADAR.md` | 每轮一行 |

---

## 三、铁律

1. **路径 C 不可擅自改回纯 A/纯 B**（除非用户重确认）。  
2. **GitHub 先于 Manus**；可发布 = 已 push 的 commit。  
3. **每轮默认 1 个 QR-ID 落地**；勘探可并行，**写盘单写者**。  
4. **密钥**不进 git / 不打印。  
5. **不伪造** IV/Greeks/OI/成交；合规不转售个人档行情。  
6. **Skill 环 §四**每轮必做；卡住必须升级到 X 多方比对（不可闷头猜）。  
7. **公式不双分叉**：评分/指标以 charts（或未来抽库）为真源。  
8. **stock-skills**：可复用思想与小模块，禁止无边界巨石依赖拖垮 Manus 构建。

---

## 四、Skill 与知识采掘环（v3 强化）

### 4.1 三级水源（按顺序，省时间且更深）

```text
L1 本机已装 skill          ~/.grok/skills  ~/.claude/skills  ~/.agents/skills
L2 用户仓库内真正有用部分   charts/commands  stock-skills/skills  仓内 docs/skills
L3 卡住 / 争议 / 要顶尖对标  → X 多方搜索 skill/架构帖 → 深度比对 → 提取
```

| 情况 | 动作 |
|------|------|
| 题目明确且 L1/L2 已有解 | **直接用 skill 或摘有用段落**，记 inherit「采用-直接」 |
| L1/L2 只有思想 | **用思想改造** charts/壳，记「采用-思想」 |
| 实现卡住、方案≥2 难判、质量不够 | **强制 L3**：X ≥2 组 query + 可选 GitHub skill 库；**≥2 来源比对**后再写代码 |
| 纯 hype / 无关垂类 | **拒绝**并记 inherit |

### 4.2 深度分析清单（L3 或大项采用前）

对每个候选 skill/帖/仓，代理须简短回答：

1. **解决我们哪条 U/P/QR？**  
2. **可迁移物**：代码模式 / 架构 / 交互 / 数据契约 / 运维（选一主）  
3. **与路径 C 是否冲突？**（是否逼我们双分叉引擎）  
4. **成本**：LLM 调用、依赖体积、Manus 构建、合规  
5. **最小落地**：本轮能做的 1 个 diff 是什么？  
6. **比对结论**：A vs B 谁赢、为何（至少两源时）

### 4.3 多 Agent 用法（鼓励 · 有边界）

用于 **快速全面**，不是热闹：

| 角色 | 何时 | 约束 |
|------|------|------|
| **explore ×1–2**（只读，可并行） | 模块边界不明、FE/BE 分头摸、L3 比对 | 不写业务代码；产出报告进 `docs/explore/` 或 inherit |
| **主写者 ×1** | 落地 QR-ID | 唯一改 quantradar（+必要时 charts）的写者 |
| **verifier / check-work** | 动 API 契约、评分接口、发布清单 | 验收后才 push |
| **背景测试** | regression/smoke 长 | 不并行第二写者 |

**禁止**：无 worktree 双写者同仓；用 stock-agent 式 5 路 cross 做工程扇出；explore 直接 push。

### 4.4 基线 skill 包（优先读）

#### 本机

| Skill | 用处 |
|-------|------|
| agent-reach | 数据/社交 + **L3 上 X** |
| design-taste-frontend / emil-design-eng / web-design-guidelines | FE 专业级 |
| research-brief / ship-code / check-work | 调研与交付 |
| quantradar-manus-ops | Manus/域名 |
| find-skills | 发现新 skill |
| stock-agent（思想） | 降级、契约、确定性层 |

#### 仓库（路径 C 核心）

| 来源 | 用处 |
|------|------|
| `charts/commands/stock-technical-analysis.md` | 分析报告结构 |
| `charts/commands/pattern-recognition.md` | 形态 |
| `charts/commands/pullback-signal.md` | 回调 |
| `charts/commands/anti-noise.md` | 决策卫生 |
| `charts/research/data_provider_comparison.md` | 数据供应商裁决 |
| `stock-skills` CONTRACT / vix / social_digest 思想 | 多源 VIX、社交降级 |
| `stock-skills/skills/agent-reach` | 与本机同源时统一路由 |

#### L3 X 查询

见 `docs/SKILL_SEARCH_QUERIES.md`；卡住时 **至少 2 组不同 query**，结果写入 inherit 并做 4.2 分析。

### 4.5 采用方式三档

| 档 | 含义 | 例 |
|----|------|-----|
| **直接使用** | 按 skill 步骤执行或安装 | agent-reach 拉 X 讨论 |
| **提取技术** | 抄模式/中间件/组件结构 | Redis 限流、SSE 面板 |
| **提取思想** | 只改我们的架构叙事 | Data→Signal→Risk→Decision ↔ 门控 |

### 4.6 `docs/SKILL_INHERIT.md` 模板

```markdown
### {date} · {QR-id或主题}
- 水源：L1 本地 / L2 仓库 / L3 X（URL）
- 比对：来源A vs 来源B（若有）
- 层：FE|BE|Data|UX|Ops|Analysis
- 提炼：…
- 采用档：直接|技术|思想|观望|拒绝
- 深度分析：§4.2 六问一句话摘要
- 落地：QR-ID 或已实现 commit
```

---

## 五、架构（路径 C）

```text
quantradar.one
    │
    ▼
quantradar App (本仓)
    ├── UI desk
    ├── API gateway (cache, rate limit, auth, health)
    └── Analysis facade
            │  CLI / JSON / 未来 package
            ▼
        ~/charts engine
            ├── providers free|hybrid|pro
            ├── charts / scanner / scores
            └── optional agent-reach side channel
```

数据三档、FE/BE/分析专业标准：同 v2（free Yahoo；hybrid 服务端 Massive 只出结论；不骗 Greeks；/health+sources）。

---

## 六、Backlog

### 已锁定

| ID | 状态 | 说明 |
|----|------|------|
| **QR0-1** | ✅ | **路径 C**（2026-07-10 用户确认） |

### QR-SK — Skill 基建

| ID | 状态 | 任务 | 验收 |
|----|------|------|------|
| QR-SK0 | ✅/维护 | `SKILL_INHERIT` + `SKILL_SEARCH_QUERIES` | 文件在仓 |
| QR-SK1 | ⬜ | 路径 C 专项：扫 charts/commands + stock-skills 有用段 → ≥8 条 inherit | 含采用/拒绝 |
| QR-SK2 | ⬜ | README 写明 L1→L2→L3 与多 agent 边界 | 文档 |
| QR-SK3 | ⬜ | 卡住演练：任选难题走一遍 L3 双源比对记样例 | explore 笔记 |
| QR-SK4 | ⬜ | （可选）仓内 `skills/quantradar-dev/SKILL.md` 固化路径 C 开发法 | skill 可被 agent 读 |

### QR0 — 最小可发布壳（路径 C 执行）

| ID | 状态 | 任务 | 验收 |
|----|------|------|------|
| QR0-0 | ✅ | `docs/PHASE0.md`：线上行为、charts 可调用入口表、壳技术选型建议 | 文件 |
| QR0-2 | ✅ | **最小产品壳**进 quantradar：可 dev 的 API+简单 UI 或静态+API；调用 charts 1 条路径（如 fetch 或读已有报告 JSON） | push 后本机可起；Manus 可 pull |
| QR0-SEC | ⬜ | 清 charts/历史明文 key；两仓 `.env.example` | 无明文 |
| QR0-3 | ⬜ | 完善 `MANUS_SYNC.md` + 路径 C 构建说明（是否需 charts submodule/复制 artifact） | 你能按文档同步 |
| QR0-4 | ✅ | 定义 charts→壳 的 **契约**：输入 ticker/sector，输出 JSON schema（门控/分/图路径） | `docs/ENGINE_CONTRACT.md` |

### QR1 — Dev / 访客 / 同步可验证

| ID | 状态 | 任务 | 验收 |
|----|------|------|------|
| QR1-1 | ⬜ | 一键本地起壳（+文档如何指到 charts） | README 5 步 |
| QR1-2 | ⬜ | 访客 sample 报告 | 无强制 manus.im |
| QR1-3 | ⬜ | ENV 表本机 vs Manus | docs/ENV.md |
| QR1-4 | ⬜ | `/health` 含 `git_sha` + charts 可达性 | JSON |

### QR2 — 数据

| ID | 状态 | 任务 | 验收 |
|----|------|------|------|
| QR2-0 | ⬜ | DATA_PROVIDER 产品文档 | md |
| QR2-1 | ⬜ | free OHLCV（charts 或壳 provider） | 无付费 key |
| QR2-2 | ⬜ | VIX/quote 多源 | source 字段 |
| QR2-3 | ⬜ | options hybrid 结论；free degraded | 诚实 |
| QR2-4 | ⬜ | agent-reach 新闻/社交 | degraded ok |
| QR2-5 | ⬜ | 缓存+限流+审计 | 测通 |

### QR3 — 分析 / 门控

| ID | 状态 | 任务 | 验收 |
|----|------|------|------|
| QR3-1 | ⬜ | 门控 API+UI 接 ENGINE_CONTRACT | 样例 ticker |
| QR3-2 | ⬜ | 1–100 分可解释 | JSON |
| QR3-3 | ⬜ | 形态/量价接 charts commands 思想 | 展示 |
| QR3-4 | ⬜ | 期权策略分档 | 文案 |
| QR3-5 | ⬜ | 空数据质量闸 | 测 |
| QR3-6 | ⬜ | 可选多角色流式 UI（仅 inherit 采用后） | 可关 |

### QR4 — 前端

| ID | 状态 | 任务 | 验收 |
|----|------|------|------|
| QR4-1 | ⬜ | design-taste + guidelines 审计 | UI_AUDIT.md |
| QR4-2 | ⬜ | Analysis 首屏 30 秒可读 | 验收描述 |
| QR4-3 | ⬜ | 四态 UI | checklist |
| QR4-4 | ⬜ | 克制动效 | 不挡操作 |
| QR4-5 | ⬜ | 与营销站品牌对齐 | token |

### QR5 — 后端

| ID | 状态 | 任务 | 验收 |
|----|------|------|------|
| QR5-1 | ⬜ | 错误契约 | md/OpenAPI |
| QR5-2 | ⬜ | 缓存 | 命中 |
| QR5-3 | ⬜ | 请求 id 日志 | 链路 |
| QR5-4 | ⬜ | 可重复构建 | Manus/本地 |

### QR6 — 发布 / 商业

| ID | 状态 | 任务 | 验收 |
|----|------|------|------|
| QR6-1 | ⬜ | Stripe/mailto | 诚实可用 |
| QR6-2 | ⬜ | 定价与 free/hybrid/pro | 一致 |
| QR6-3 | ⬜ | MANUS_RELEASE_CHECKLIST | 你跑通 |
| QR6-4 | ⬜ | 发布烟雾 | checklist |

### QR7 — 持续采掘

| ID | 状态 | 任务 | 验收 |
|----|------|------|------|
| QR7-1 | ⬜ | 每 5 轮加大 L3 | +5 inherit |
| QR7-2 | ⬜ | 竞品技术短表 | md |
| QR7-3 | ⬜ | 稳定 inherit → 仓内 skill | skills/ |

### QR9 — 拒绝

| ID | 裁决 |
|----|------|
| 大陆券商 API 产品源 | 拒绝 |
| 伪造 Greeks | 拒绝 |
| 浏览器暴露个人 OPRA key | 拒绝 |
| 全自动实盘 agent 当主产品 | 搁置 |
| 重型 K8s 演示栈默认 | 搁置 |
| 路径 A 等 Manus 全量才开工 | **拒绝**（已选 C） |

---

## 七、验收矩阵

| 检查 | 通过条件 |
|------|----------|
| 路径 C | 壳不复制整引擎；有 ENGINE_CONTRACT 或明确 CLI 调用 |
| pull/push | quantradar（+charts）干净已推 |
| Skill | 本轮 inherit 有 L1/L2 记录；若卡住有 L3 双源 |
| 多 agent | 无双写者事故 |
| 本地起 | 壳 + 至少 1 条分析路径 |
| health | 实现后含 git_sha |
| sample | 无强制 Manus 登录 |
| 密钥 | 无明文 |
| 发布话术 | PROGRESS 含可 Manus pull |

---

## 八、收官 S1–S12

S1 PHASE0 · S2 最小壳可 dev 已 push · S3 无明文 key · S4 inherit≥20（含 L2）· S5 sample · S6 free OHLCV · S7 options 诚实 · S8 门控三层 · S9 FE P0 清零 · S10 health+限流 · S11 Manus checklist 你跑通 · S12 两次完整「push→Manus 发布」无事故  

---

## 九、推荐近序（路径 C）

| 序 | ID | 为何 |
|----|-----|------|
| 1 | QR0-0 | 盘点 charts 入口与壳栈 |
| 2 | QR0-4 | 引擎契约（防双分叉） |
| 3 | QR0-2 | 最小壳 push → 你可 Manus 试同步 |
| 4 | QR0-SEC / QR0-3 | 安全与发布文档 |
| 5 | QR-SK1 | L2 仓库 skill 吃干榨尽 |
| 6 | QR2-1 + QR1-4 | free 数据 + health |
| 7 | QR3-1 + QR4-2 | 门控与首屏 |
| … | 按 ROI | 卡住则 §四 L3 + 多 explore |

---

## 十、进度与 commit

| 项 | 约定 |
|----|------|
| 进度 | `quantradar/PROGRESS.md` 与 `charts/PROGRESS_QUANTRADAR.md` |
| commit | `qr(QR0-2): minimal app shell calling charts` |
| 结束语 | 已 push `sha`（quantradar [+ charts]）。请 Manus pull 后发布。 |

---

## 十一、版本

| 版本 | 变更 |
|------|------|
| v1 | 恢复/省钱/去 Manus |
| v2 | GitHub↔Manus 闭环 + Skill 采掘 + 全环节 backlog |
| **v3** | **路径 C 锁定**；**L1 本机→L2 仓库→L3 X 卡住深挖**；**直接/技术/思想三档采用**；**多 agent 勘探+单写者**；QR0 改为最小壳+ENGINE_CONTRACT |

---

*v3 = 你的三点决策已写进可执行 goal：C + 全水源 skill + 必要时 X 深比对 + 多 agent 加速。*
