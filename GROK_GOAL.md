# GROK /goal — QuantRadar 极致产品优化 v2

> **唯一主任务源**（产品仓 SSOT）：本文件 `Alexaliao001/quantradar/GROK_GOAL.md`  
> **镜像**：`~/charts/GROK_GOAL_QUANTRADAR.md`（与引擎文档同仓，便于对照 `~/charts`）  
> **产品**：https://quantradar.one · 发布宿主：**Manus**（用户从 GitHub 拉到 Manus 再发布）  
> **工程闭环（强制）**：
>
> ```text
> git pull (GitHub quantradar)  →  本机优化 + 验证  →  git push
>         →  你在 Manus 里 pull / sync  →  Manus 发布 quantradar.one
> ```
>
> **禁止**：在 Manus 里大改又不 push 回 GitHub（分叉地狱）；禁止未 push 就让用户发布。  
> **不是** `stock-skills` 的 FREE_DATA / stock-agent goal（可借思想，不改错仓）。

---

## 粘贴版（复制到 Grok Build 直接开跑）

### 精简版（日常续跑 · 推荐）

```
/goal QuantRadar 极致优化 v2。主任务源：~/quantradar/GROK_GOAL.md
（镜像 ~/charts/GROK_GOAL_QUANTRADAR.md）

工程闭环：本机 pull → 改 quantradar(+必要 charts) → 验证 → push GitHub
→ 用户 Manus pull → Manus 发布。禁止只改 Manus 不回写 GitHub。

北极星：每个关键环节都「专业级」——数据/分析/门控/期权/前端/后端/鉴权/计费/可观测/合规。

每轮强制：
  1) cd ~/quantradar && git pull --rebase
  2) §四 Skill 采掘（本地 skill + X 搜 skill）→ 本轮 ≥1 条可落地 inherit 写入 SKILL_INHERIT.md
  3) 只做 1 个 QR-ID；最小 diff；密钥不进 git
  4) 验收本项 + 不破坏访客样例
  5) commit + push origin main
  6) PROGRESS_QUANTRADAR.md 一行 + 提醒用户「可 Manus pull 发布」

首轮：QR0-0 盘点 → QR0-1 路径确认 → QR0-2 源码进仓（若仍空）→ QR-SK1 首轮 skill 采掘
```

### 完整版（新会话 / 过夜长跑）

```
/goal 把 QuantRadar 做到「每个环节与关键技术都非常好」。

仓库 SSOT：github.com/Alexaliao001/quantradar → 本机 ~/quantradar
任务源：GROK_GOAL.md（本文件）
发布：用户 Manus 从 GitHub 同步后发布 quantradar.one（代理不替用户点 Manus 发布，除非授权）

════════════════════════════════════
北极星（产品，可验收）
════════════════════════════════════
P1  源码在 GitHub 可 dev / 可 Manus sync（非空仓）
P2  数据 free|hybrid|pro 分层；账单可控；不伪造 Greeks
P3  门控 Market→Sector→Stock + 评分 + 形态/量价 + 期权策略 叙事兑现
P4  前端：专业 trading desk 质感（非模板 AI 站）；可访问 a11y 基线
P5  后端：缓存、限流、健康检查、错误契约、source 可审计
P6  鉴权：不强制 Manus 账号做核心读路径；访客样例可用
P7  可观测：关键路径有 log/metrics；发布可回滚
P8  合规：个人档行情不转售；只分发结论或 BYO-key

════════════════════════════════════
每轮铁律：Skill 采掘环（§四）
════════════════════════════════════
代理必须主动：
  A. 本地 skill 扫描（agent-reach / design-taste / emil-design / web-design-guidelines /
     research-brief / ship-code / quantradar-manus-ops / stock 相关 / find-skills）
  B. X 搜索相关 skill / 开源 skill 库 / 量化 agent 架构帖（twitter-cli 或 agent-reach）
  C. 提取「对本项目真实有用」的技术 → 写入 docs/SKILL_INHERIT.md
     格式：来源 | 适用层(FE/BE/Data/UX/Ops) | 可落地动作 | 本轮是否采用
  D. 拒绝清单：看起来酷但与门控量化产品无关的 hype

════════════════════════════════════
SOP
════════════════════════════════════
0  git -C ~/quantradar pull --rebase
1  读 GROK_GOAL + PROGRESS + SKILL_INHERIT 最近 20 行
2  Skill 采掘（§四）≥1 条新 inherit 或明确「本轮无新货+理由」
3  取 §六 最高 ROI 未完成 QR-ID（1 项）
4  实现于 ~/quantradar（引擎复用可改 ~/charts 再文档引用）
5  验证 §七
6  commit + push quantradar（及 charts 若改）
7  进度一行；提示用户 Manus pull → 发布
禁止 completed=true 除非 S1–S12 全满且用户认可
```

---

## 一、使命

把 **QuantRadar** 建成：**GitHub 为唯一工程 SSOT、本机可极致打磨、Manus 只做同步与发布** 的专业量化决策产品——门控分析可信、数据成本可控、前端像 desk 不像 demo、每个关键技术有「采掘 → 继承 → 验收」闭环。

### 1.1 发布拓扑（用户指定 · 不可改）

```text
┌─────────────────┐     push      ┌──────────────────┐
│  本机 ~/quantradar │ ──────────► │ GitHub quantradar │
│  Grok/Cursor 优化  │ ◄────────── │   (SSOT)          │
└─────────────────┘     pull      └────────┬─────────┘
                                           │ 你 pull/sync
                                           ▼
                                  ┌──────────────────┐
                                  │ Manus 工作区      │
                                  │ 构建 + 发布       │
                                  └────────┬─────────┘
                                           ▼
                                  quantradar.one
```

| 角色 | 做什么 | 不做什么 |
|------|--------|----------|
| **代理（本机）** | pull、改代码、测、push、写 inherit | 默认不替你点 Manus 发布 |
| **你** | Manus pull、预览、发布、反馈线上问题 | 长期在 Manus 只改不回写 GitHub |
| **Manus** | 构建宿主 + 域名发布 | 不是源码 SSOT |

### 1.2 用户体感 U1–U8

| ID | 体感 | 坏 | 好 |
|----|------|----|----|
| U1 | 改得动 | 空仓 / 只在 Manus | clone → 改 → push → Manus 同步即更新 |
| U2 | 看得懂 | 分数无来源 | 门控三层 + source + warnings |
| U3 | 不烧钱 | 全站打付费 Polygon | free/hybrid；期权诚实分档 |
| U4 | 不骗 | 假 Greeks | available=false / estimated 标注 |
| U5 | 好看好用 | AI 模板站 | desk 级 UI + 关键路径 ≤3 点 |
| U6 | 稳 | 无缓存限流 | Redis/内存缓存 + rate limit + health |
| U7 | 能试 | 强制 Manus 登录 | 访客 sample 报告 |
| U8 | 专业 | 无观测 | health + 关键错误可诊断 |

---

## 二、资产地图

| 资产 | 位置 | 角色 |
|------|------|------|
| **产品 SSOT** | `~/quantradar` ← `Alexaliao001/quantradar` | 应用 + 本 goal |
| **分析引擎** | `~/charts` ← `stock-charts` | fetch/图表/扫描；可被产品 API 调用或抽库 |
| **营销站** | `quantradar-site` / `charts/site-public` | 落地页 |
| **线上** | `quantradar.one` | Manus 发布结果 |
| **数据选型** | `charts/research/data_provider_comparison.md` | 供应商裁决 |
| **Manus 运维** | `quantradar-manus-ops` skill | 域名/API 笔记 |
| **进度** | `~/charts/PROGRESS_QUANTRADAR.md` + 仓内 `PROGRESS.md` | 每轮一行 |
| **Skill 继承账本** | `quantradar/docs/SKILL_INHERIT.md` | 采掘产物（强制维护） |

**2026-07-10**：产品仓曾 empty，现有 goal/README；**应用源码仍可能不足** → QR0 优先。

---

## 三、铁律

1. **GitHub 先于 Manus**：可发布状态 = 已 push 的 commit；Manus 不持有独有关键 diff。  
2. **每轮 1 backlog**、单写者；≥3 模块先短 explore。  
3. **密钥**：不打印、不 commit；发现明文 key → 当轮优先 QR0-SEC。  
4. **不伪造市场数据**（Greeks/OI/IV/成交）。  
5. **合规**：个人 Massive/Polygon 不向终端用户转发原始行情；产品分发结论或 BYO。  
6. **Skill 采掘**：每轮必须做 §四（可很短，但不可跳）。  
7. **线上安全**：大改部署前本地 smoke；破坏性变更需用户确认后再提示 Manus 发布。  
8. **仓界**：UI/API 产品 → `quantradar`；纯研究 CLI → 可留 `charts` 并文档链接。

---

## 四、Skill 采掘环（每轮强制 · 本 goal 核心增量）

### 4.1 目的

从 **本地 skill + X 上公开 skill/架构帖** 持续提取对 QuantRadar **真实有用** 的前端/后端/数据/UX/运维技术，避免闭门造车，也避免追 hype。

### 4.2 每轮最少动作

```bash
# 1) 本地（必做）
ls ~/.grok/skills ~/.claude/skills ~/.agents/skills 2>/dev/null
# 按本轮 QR 主题 read 1–3 个相关 SKILL.md

# 2) X 搜索（必做，用 agent-reach / twitter-cli / 内置 X 工具）
# 示例 query（按主题轮换，勿每次完全相同）：
#   "agent skill" OR SKILL.md (trading OR quant OR dashboard OR fintech)
#   (skills OR "agent skills") (react OR "next.js" OR design) (github.com)
#   multi-agent (stock OR trading) (FastAPI OR yfinance)

# 3) 写入 docs/SKILL_INHERIT.md（追加，不要只口头）
```

### 4.3 继承判定（必须过 3 关才「采用」）

| # | 问题 | 否 → |
|---|------|------|
| 1 | 是否直接改善 U1–U8 或 P1–P8？ | 记「观望」 |
| 2 | 能否在 1 轮 backlog 内落地或拆成明确子项？ | 记「搁置+条件」 |
| 3 | 是否与铁律冲突（造假数据、转售行情、密钥）？ | **拒绝** |

### 4.4 基线技能包（已盘点 · 默认优先读）

#### A. 本机已安装 — 建议映射

| Skill | 层 | 对 QuantRadar 的真实用处 |
|-------|----|--------------------------|
| **agent-reach** | Data / Research | X/Reddit/雪球/Exa/Jina 免费情报；**Skill 采掘也用它搜 X** |
| **design-taste-frontend** | FE | 反模板落地页与 desk UI 方向 |
| **emil-design-eng** | FE | 动效、组件 polish、细节质感 |
| **web-design-guidelines** | FE | a11y / 表单 / 焦点 / 对比度审计 |
| **research-brief** | Process | 有出处的调研简报（供应商/竞品） |
| **ship-code** | Process | 读仓→小步改→验证→交付 |
| **check-work** / code-review | QA | push 前自检 |
| **quantradar-manus-ops** | Ops | Manus/域名/发布路径笔记 |
| **stock-agent**（思想） | Analysis | 确定性 L1、降级、契约字段 — **勿整仓嵌入** |
| **find-skills** | Meta | 发现可安装 skill |
| **gzh-pipeline** Hot 路径 | Research | agent-reach 优先的调研节奏 |
| **self-learning** | Meta | 本轮踩坑固化为 skill 片段 |

#### B. X 公开线索（2026-07 采样 · 待验证后采用）

> 下列来自 X 公开讨论，**不是**立刻全抄；须经 4.3 判定后写入 SKILL_INHERIT 再实现。

| 线索 | 可提炼技术 | 可能映射 QR 层 | 风险 |
|------|------------|----------------|------|
| Multi-agent “Trading Floor”（Quant/Sentiment/Macro/Risk/Chief + FastAPI SSE + Next.js） | 分角色分析 + **流式展示辩论** | BE 编排、FE 实时面板 | LLM 成本；需确定性门控压阵 |
| Stock-Agent-Ops 类生产栈 | Redis 缓存/限流、报告 critic、监控面板、Docker | BE/Ops | 过重则砍到最小 |
| virattt 式 agent 分工图 | Data→Signal→Risk→Decision 流水线 | 与现有门控对齐 | 避免纯 LLM 无数据 |
| Meng To / 设计 skill 库 | landing/UI skill 批量、反 slop | 营销站 + app shell | 别做成通用 landing 丢掉 trading 专业感 |
| RayFernando skills 仓库 | 高质量 skill 结构设计参考 | 仓内 `skills/` 可选 | 仅学结构 |
| yfinance 工具封装 | free OHLCV | Data free 档 | 无可靠 Greeks |
| loop engineering / 自跑 quant desk 12 步 | intent→data→signal→verify→refine | 分析闭环 | 与 Manus 发布环分开 |

#### C. 明确拒绝（采掘时直接丢掉）

- 无验证的「AI 自动下单赚翻」叙事 skill  
- 大陆券商 API 产品化  
- 把个人 Polygon key 塞进浏览器  
- 仅加密货币 meme 与本产品无关的 agent token 项目  

### 4.5 `docs/SKILL_INHERIT.md` 条目模板

```markdown
### {date} · 轮次 · 主题
- 来源：本地 skill X / X post URL / repo
- 层：FE | BE | Data | UX | Ops | Analysis
- 提炼：一句话技术点
- 判定：采用 | 观望 | 拒绝（理由）
- 落地：QR-ID 或「本轮已实现：…」
```

---

## 五、架构目标（全环节专业级）

```text
                    quantradar.one (Manus 发布)
                           │
          ┌────────────────┼────────────────┐
          ▼                ▼                ▼
     Marketing          App Shell         Auth
     (site)           (desk UI)        (非强制 Manus)
          │                │
          │         ┌──────┴──────┐
          │         ▼             ▼
          │   Analysis API    Data Providers
          │   门控+评分+图     free|hybrid|pro
          │         │             │
          │         └──────┬──────┘
          │                ▼
          │     可审计 JSON + charts + warnings
          │
          └── Observability: /health · logs · rate limit · cache
```

### 5.1 数据三档（继承选型报告）

| 模式 | OHLCV | 期权 | 新闻/社交 |
|------|-------|------|-----------|
| free | Yahoo/yfinance | BYO AV 或 degraded | agent-reach |
| hybrid | free 优先 | 服务端 Massive **只出结论** | free+ |
| pro | 可 Massive | 全能力 desk | +可选 |

### 5.2 前端专业标准（每轮 FE 相关必查）

- 信息密度适合交易者：首屏 30 秒能回答「方向 / 门控 / 风险 / 下一步」  
- 反 AI slop：读 design-taste + emil-design + web-design-guidelines  
- 状态：loading / empty / error / degraded 四态齐全  
- 移动端可读；关键数字等宽字体  

### 5.3 后端专业标准

- 统一错误 JSON：`{ code, message, data_warnings? }`  
- 缓存 ticker 分析结果（TTL）；限流防刷  
- `GET /health`：依赖探测（数据源可选 degraded）  
- 所有输出带 `as_of`、`data_mode`、`sources[]`  

### 5.4 分析专业标准

- 门控顺序不可跳：Market → Sector → Stock  
- 分数可解释（因子列表或支柱）  
- 与 LLM 文案分离：数字层确定性优先  

---

## 六、Backlog（按依赖；每轮 1 项）

### QR-SK — Skill 采掘基建（与功能并行，前 3 轮优先夹带）

| ID | 状态 | 任务 | 验收 |
|----|------|------|------|
| QR-SK0 | ⬜ | 建 `docs/SKILL_INHERIT.md` + `docs/SKILL_SEARCH_QUERIES.md`（可轮换 X 查询表） | 文件在仓 |
| QR-SK1 | ⬜ | 首轮全量：本地 skill 表 + X 搜 2 组 query → ≥5 条判定写入 inherit | 5 条含采用/拒绝 |
| QR-SK2 | ⬜ | 把「每轮 §四」写进 README 贡献者/代理说明 | README 一节 |
| QR-SK3 | ⬜ | （可选）仓内 `skills/quantradar-*` 固化本产品专用 skill | 至少 1 个 SKILL.md |

### QR0 — 仓库与安全（阻塞）

| ID | 状态 | 任务 | 验收 |
|----|------|------|------|
| QR0-0 | ⬜ | Phase0 盘点：`docs/PHASE0.md`（线上、Manus、charts 可复用模块、空仓程度） | 文件 + 恢复建议 A/B/C |
| QR0-1 | ⬜ | **用户确认**恢复路径：A Manus 全量进仓 / B charts 重建壳 / C 混合 | PROGRESS 写死字母 |
| QR0-2 | ⬜ | 执行：应用源码进入 `quantradar` 且 `git push`；README dev 5 步 | size>0；本机可起 |
| QR0-SEC | ⬜ | 清除明文 API key（含 charts 历史硬编码）；`.env.example` | rg 清洁；rotate 提示用户 |
| QR0-3 | ⬜ | `.gitignore` / 密钥规范 / Manus 同步说明（pull 后如何发布） | docs/MANUS_SYNC.md |

### QR1 — 本机 dev 与 Manus 同步友好

| ID | 状态 | 任务 | 验收 |
|----|------|------|------|
| QR1-1 | ⬜ | 一键本地：`pnpm/npm/docker` 或 python 文档化 | 冷机按 README 成功 |
| QR1-2 | ⬜ | 访客 sample 分析页无强制 Manus OAuth | curl 路径不跳 manus.im |
| QR1-3 | ⬜ | 环境变量表：本机 vs Manus 构建 | docs/ENV.md |
| QR1-4 | ⬜ | 健康检查 + 版本号 commit sha 展示（便于确认 Manus 是否拉到最新） | /health 含 git_sha |

### QR2 — 数据层卓越

| ID | 状态 | 任务 | 验收 |
|----|------|------|------|
| QR2-0 | ⬜ | `docs/DATA_PROVIDER.md`（三档 + 合规） | 文档 |
| QR2-1 | ⬜ | free OHLCV Provider + 统一 bar schema | 无付费 key 出日线 |
| QR2-2 | ⬜ | Quote/VIX 多源（Yahoo+FRED 思想） | source 字段 |
| QR2-3 | ⬜ | Options hybrid 结论 API；free degraded 诚实 | 不骗 Greeks |
| QR2-4 | ⬜ | News/Social：agent-reach 服务端封装 | 失败 degraded |
| QR2-5 | ⬜ | 缓存 + 限流 + provider 审计计数 | 压测或单测 |

### QR3 — 分析与门控卓越

| ID | 状态 | 任务 | 验收 |
|----|------|------|------|
| QR3-1 | ⬜ | 门控 API 契约 + UI 三层展示 | 样例 TSLA |
| QR3-2 | ⬜ | 1–100 分可解释 | 文档+JSON |
| QR3-3 | ⬜ | 形态/量价接 charts 或预计算 | 图或指标 |
| QR3-4 | ⬜ | 期权策略分档展示 | free 引导升级/BYO |
| QR3-5 | ⬜ | 质量闸：空数据不编分 | 断依赖测试 |
| QR3-6 | ⬜ | （可选）多角色分析流式 UI — 仅当 SKILL_INHERIT 采用 Trading Floor 类 | SSE 可关 |

### QR4 — 前端卓越

| ID | 状态 | 任务 | 验收 |
|----|------|------|------|
| QR4-1 | ⬜ | 设计审计：design-taste + web-guidelines 清单 | `docs/UI_AUDIT.md` |
| QR4-2 | ⬜ | Dashboard / Analysis 页信息架构重做 | 30 秒可读结论 |
| QR4-3 | ⬜ | 四态 UI + 骨架屏 | 截图或 checklist |
| QR4-4 | ⬜ | 动效/细节（emil-design 约束：克制） | 无炫技挡操作 |
| QR4-5 | ⬜ | 营销站与 app 视觉体系统一 | 同品牌 token |

### QR5 — 后端 / 平台卓越

| ID | 状态 | 任务 | 验收 |
|----|------|------|------|
| QR5-1 | ⬜ | 统一 API 错误与分页契约 | OpenAPI 或 md |
| QR5-2 | ⬜ | 缓存层（内存→Redis 可选） | 重复请求命中 |
| QR5-3 | ⬜ | 结构化日志 + 请求 id | 一条链路可跟 |
| QR5-4 | ⬜ | Docker 或 Manus 构建可重复 | 同 commit 同产物 |

### QR6 — 商业化与发布

| ID | 状态 | 任务 | 验收 |
|----|------|------|------|
| QR6-1 | ⬜ | Stripe / mailto 现状盘点与 Payment Link | 测试 checkout 或诚实 mailto |
| QR6-2 | ⬜ | 定价页与能力档 free/hybrid/pro 对齐 | 文案一致 |
| QR6-3 | ⬜ | `docs/MANUS_RELEASE_CHECKLIST.md`：pull→build→publish→验证 /health sha | 你可照做 |
| QR6-4 | ⬜ | 发布后烟雾：首页 + sample + health | checklist 勾选 |

### QR7 — 持续采掘与竞品

| ID | 状态 | 任务 | 验收 |
|----|------|------|------|
| QR7-1 | ⬜ | 每 5 轮强制加大 X 采掘（新 query） | inherit +5 条 |
| QR7-2 | ⬜ | 竞品/开源对照短表（仅技术可学点） | docs/COMPETITOR_TECH.md |
| QR7-3 | ⬜ | 将稳定 inherit 固化为仓内 skill | skills/ |

### QR9 — 拒绝 / 搁置

| ID | 裁决 | 说明 |
|----|------|------|
| QR9-1 | 拒绝 | 大陆券商 API 产品源 |
| QR9-2 | 拒绝 | 伪造 Greeks / 无源分数 |
| QR9-3 | 拒绝 | 浏览器暴露个人 OPRA key |
| QR9-4 | 搁置 | 全自动实盘交易 agent（非本产品范围） |
| QR9-5 | 搁置 | 重型 K8s/EKS 演示栈（除非要 B2B 运维戏） |

---

## 七、验收矩阵

| 检查 | 命令/方式 | 通过 |
|------|-----------|------|
| 同步 | `git -C ~/quantradar pull` | 无未解释冲突 |
| 非空 | `gh api repos/Alexaliao001/quantradar --jq .size` | >0 且有源码 |
| Push | `git -C ~/quantradar status` | clean 且已 push |
| Skill 账本 | `docs/SKILL_INHERIT.md` 本轮有追加 | 是 |
| 本地 | README 启动 | 关键页 200 |
| Health | `/health` | ok + git_sha（实现后） |
| 访客 | sample 路径 | 无强制 manus.im |
| 数据 | free 模式无付费 key | bars 或诚实错误 |
| 密钥 | 人工 rg | 无明文生产 key |
| 发布提示 | PROGRESS 含「可 Manus pull」 | 是 |

---

## 八、收官闸门 S1–S12

| ID | 闸门 |
|----|------|
| S1 | PHASE0 + 路径锁定 |
| S2 | 应用源码在 GitHub 且本机可 dev |
| S3 | 无明文 key + ENV 文档 |
| S4 | SKILL_INHERIT ≥15 条有效判定（含拒绝） |
| S5 | 访客 sample |
| S6 | free OHLCV |
| S7 | hybrid 期权结论诚实 |
| S8 | 门控三层 UI+API |
| S9 | FE 审计清单清零 P0 |
| S10 | /health + 缓存/限流基线 |
| S11 | MANUS_RELEASE_CHECKLIST 你跑通一次 |
| S12 | 连续 2 轮「pull→改→push→Manus 发布」无回滚事故 |

---

## 九、推荐执行顺序（首 10 轮）

| 轮 | 项 | 为何 |
|----|----|------|
| 1 | QR-SK0 + QR0-0 | 账本 + 盘点 |
| 2 | QR0-1（你确认 A/B/C） | 方向 |
| 3 | QR0-2 源码进仓 push | 可优化前提 |
| 4 | QR0-SEC + QR0-3 | 安全与 Manus 文档 |
| 5 | QR-SK1 深采掘 | 指导 FE/BE 选型 |
| 6 | QR1-1 本地一键 | 效率 |
| 7 | QR1-2 + QR1-4 sample+health | 可发布验证 |
| 8 | QR2-0/2-1 数据 free | 省钱 |
| 9 | QR4-1 UI 审计 → QR4-2 | 专业感 |
| 10 | QR3-1 门控契约 | 核心叙事 |

之后按 PROGRESS 最高 ROI 穿插 QR2 期权 / QR5 后端 / QR6 发布清单。

---

## 十、进度与 commit

| 项 | 约定 |
|----|------|
| 进度 | `~/quantradar/PROGRESS.md` 与 `~/charts/PROGRESS_QUANTRADAR.md` 同步一行 |
| commit | `qr(QR2-1): free OHLCV provider` |
| push | `git push origin main`（quantradar）；改 charts 另 push stock-charts |
| 回合结束话术 | 「已 push `sha`。请在 Manus 中 pull 后发布；核对 /health 的 git_sha。」 |

---

## 十一、与其它文档

| 文档 | 关系 |
|------|------|
| 本文件 | **QuantRadar 产品唯一主 goal** |
| `charts/research/data_provider_comparison.md` | 数据裁决 |
| `stock-skills/GROK_GOAL_FREE_DATA_STACK.md` | 仅 stock-agent；边界见其附录 |
| `quantradar-manus-ops` | Manus 操作细节 |

---

## 十二、版本

| 版本 | 日期 | 变更 |
|------|------|------|
| v1 | 2026-07-10 | 初版：恢复/省钱/去 Manus |
| **v2** | 2026-07-10 | **工程闭环改为 GitHub→本机→push→Manus 发布**；**强制 X+本地 Skill 采掘环**；全环节卓越 backlog QR-SK/FE/BE/Ops；收官 S1–S12 |

---

*v2 目标：goal 本身足够好，代理按环执行即可把产品每个关键技术推到专业级，并由你通过 Manus 稳定发布。*
