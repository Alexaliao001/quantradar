# GROK /goal — QuantRadar 商业冲刺 v1（Desk → Revenue）

> **本文件**：`~/quantradar/GROK_GOAL_COMMERCIAL.md` — `GROK_GOAL.md` v3 的**商业子战役**执行层  
> **冲突裁决**：路径 C 边界 / 铁律 / Skill 环（§四）以 `GROK_GOAL.md` 为准；本文件只加执行密度，不改边界  
> **回写**：QD 任务覆盖 QR-ID 时，完成后把 `GROK_GOAL.md` 对应行标 ✅ 并注 `→QD`  
> **产品**：https://quantradar.one · Fortune Insight, LLC · 发布仍走「push → 用户 Manus pull → 发布」  
> **执行模型无关**：本文件写给任何在 Cursor 里干活的模型；能力不足的轮次按 §4.4 换任务不换规则。

---

## 〇、起点快照（2026-07-16 desk-v1 · 已实现·未 commit）

| 已落地 | 说明 |
|--------|------|
| Verdict Desk | 首页 Verdict → Why → 证据条(Market/Sector/Stock) → 新鲜度/来源 → Next，四态 UI（idle/loading/ready/blocked） |
| 品牌 v1 | 深炭底+雷达绿，`Syne` + `IBM Plex Mono`（暂 Google CDN），全站统一 header/footer |
| 付费漏斗 | 结果区 Upgrade 挂点；`/login?next=checkout|live` 回流；pricing 月 $29 / 年 $249 切换 |
| 计费后端 | checkout 支持 interval；`/api/billing/webhook` 写 `plan=pro/free`；plan SSOT=`data/users.json`；live 需登录+Pro（403 `plan_required`） |
| 测试 | `tests/test_billing.py` 新增；auth/password/contract 合计 24 绿 |

✅ QD0-0 / QD1-0 已落库。线上仍须 Manus pull 后才有新文案。  
⚠️ 本战役每轮 push 后都要提示「可 Manus pull 发布」。  
⚠️ **Pro 价值裁决 B**（`docs/PRO_VALUE.md`）：当前 host 不卖 live；支持者价至 `charts_status=mounted`。

---

## 一、使命与北极星

**使命**：把「诚实的机械雷达」做成访客 30 秒信任、愿意掏钱、付费后真有货的产品。四条腿：细部工程收口 · 商业闭环上线 · 前端高级化 · 诚实增长。

**北极星（方向重于显著性，样本小只看趋势）**

| ID | 指标 | 目标 |
|----|------|------|
| N1 | 首屏 30 秒理解 | 5 人盲测能口述「该不该上手+为什么」 |
| N2 | demo → 注册 | ≥8% |
| N3 | 注册 → 发起 checkout | ≥25% |
| N4 | checkout → pro_active | ≥60% |
| N5 | Pro 7 日内 ≥1 次 live_run | ≥50% |

计量只用 QD1-5 的服务端 JSONL（无第三方 tracker）。**禁止为指标造假。**

---

## 二、目标客户与心理杠杆（合法合规 · 零暗模式）

### 2.1 ICP

- **主**：25–45 岁美股 swing / 期权散户；被喊单群、大师课、假回测烧过；X/Reddit 活跃；要「别骗我」胜过「带我飞」。
- **次**：quant-curious 工程师；吃 auditable / 契约 / JSON / 方法论这套。
- **反 ICP**：找十倍神股的赌徒 — 文案主动劝退（降低退款与差评成本）。

### 2.2 杠杆 → 诚实落地映射

| 心理杠杆 | 诚实实现（我们怎么用） | 落地 ID |
|----------|------------------------|---------|
| 损失厌恶 | 「radar 多数时候让你别动手」＝帮你省掉坏交易；NO/WAIT 结果配一句"本次帮你避开了什么" | QD4-1 |
| 风险反转 | refund 政策前置进定价卡与 checkout 前视野 | QD4-2 |
| 锚定 | 年 $249 对月 $29 省 ~28%；对照文案「一笔 -8% 的 $3k 坏交易 ≈ 8 个月订阅」 | QD4-1 |
| 真实权威 | methodology 拆成可索引长文 + 可审计 score + 来源/新鲜度披露（基建已有） | QD3-1 |
| 承诺一致 | WAIT 票设提醒 → 邮件拉回 → Pro 的 saved tickers | QD3-3 |
| 蔡格尼克缺口 | demo 明示「冻结于 {date} 的样本」，live 新鲜度上锁 → 升级动机 | QD2-2 / QD4-1 |
| 社会证明 | 只展示真实数字，没有就不展示（`/api/public_stats` 已诚实返 null） | 恒守 |
| 稀缺 | 仅当真实（如 live 容量确实受限）才用，默认不用 | 恒守 |

### 2.3 红线（任何轮次不可越）

假用户数/假见证/假倒计时/假库存 · cancel 迷宫或隐藏退订 · 默认勾选加购 · 伪造 Greeks/新鲜度 · QD1-0 裁决前把 live 吹成已可用 · 第三方跟踪像素 · 密钥入库或打印。

---

## 三、Backlog（QD 轨道）

> 状态：⬜ 未做 · 🔶 部分 · ✅ 完成。每轮默认取 1 个 ⬜（按 §五推荐序）。

### QD0 — 收口与守门（本轮遗产落库）

| ID | 状态 | 任务 | 验收 |
|----|------|------|------|
| QD0-0 | ✅ | 审查未提交 diff（desk+billing+tests）→ 全测 → commit → push | git clean；unittest 全绿；PROGRESS 一行；提示 Manus 发布 |
| QD0-1 | ⬜ | 浏览器走查 375/768/1440：首屏 30s、四态、对比度 AA、键盘可达 → `docs/UI_AUDIT.md`（覆盖 QR4-1） | 截图入 `docs/audit/{date}/`；问题列 P0/P1/P2 |
| QD0-2 | ⬜ | OG/favicon 品牌套件重制（雷达绿），X/iMessage 分享预览不糊 | og:image 1200×630；逐页 meta 核对 |
| QD0-3 | ⬜ | 字体自托管：Syne + Plex Mono woff2 进 `static/fonts/`，去 Google CDN | 断网仍正常渲染；无明显 CLS |

### QD1 — 商业闭环上线（真钱路径）

| ID | 状态 | 任务 | 验收 |
|----|------|------|------|
| QD1-0 | ✅ | **裁决 Pro 价值真实性**：host 能否 mount charts 跑 live？能→写部署路径并实施；不能→Pro 文案降级为「支持者价，live 上线自动解锁」 | `docs/PRO_VALUE.md`；线上文案一致；不卖空气 |
| QD1-1 | ⬜ | Stripe 生产配置：用 `quantradar-stripe-ops` skill + `~/charts/stripe_payment_links.py` 建 product/price(月$29/年$249)；host 注入 env；注册 webhook + `STRIPE_WEBHOOK_SECRET` | test mode 端到端一单；webhook 写 plan=pro 留脱敏证据 |
| QD1-2 | ⬜ | Customer Portal：`POST /api/billing/portal` + 「Manage billing」入口；退订→webhook 降 free | 退订路径演练通过；无 cancel 迷宫 |
| QD1-3 | ⬜ | webhook 幂等 + 欠费态：event id 去重；`invoice.payment_failed` → 标 `billing_state=past_due` + UI 提示 | 单测覆盖重放与欠费 |
| QD1-4 | ⬜ | Pro 限流差异化：`QUANTRADAR_RATE_LIMIT_PRO`；`/api/billing/status` 暴露限额 | 单测 |
| QD1-5 | ⬜ | 漏斗诚实计数：服务端 JSONL（demo_run/signup/checkout_start/pro_active/live_run）+ `scripts/funnel_report.py` | 本地演练出报表；无 PII 泄漏 |

### QD2 — 前端高级化（desk → Bloomberg-lite）

| ID | 状态 | 任务 | 验收 |
|----|------|------|------|
| QD2-0 | ⬜ | **结果区渲染真实图表**：`artifacts.charts` 的 daily_price / daily_indicators 出图（artifact 模式静态路由），点击放大 — 最大 wow 缺口 | INTC demo 显示两图；404 时优雅降级 |
| QD2-1 | ⬜ | 单分仪表：score dial（纯 SVG 无依赖），withheld 态禁用样式 | 四态截图 |
| QD2-2 | ⬜ | 三重门可视化：Market→Sector→Stock 关卡条（pass/unknown/fail 三色 + reason），stock-agent 门控思想产品化 | 与 contract 字段一一对应 |
| QD2-3 | ⬜ | 品牌签名动效：雷达扫描线一次扫过 verdict（≤700ms；respect prefers-reduced-motion） | 不挡操作；可关 |
| QD2-4 | ⬜ | 移动端专项：376px 修复、触控热区 ≥44px、粘性 Analyze 按钮 | 375 截图过 UI_AUDIT P0 |
| QD2-5 | ⬜ | 分享卡：`/r/{ticker}` 只读 demo 永链 + 服务端逐票 OG 卡（SVG 模板）+ X 分享按钮 | 卡片含 verdict/score/免责；预览美观 |

### QD3 — 获客增长（诚实增长循环）

| ID | 状态 | 任务 | 验收 |
|----|------|------|------|
| QD3-0 | ⬜ | SEO 基建：sitemap.xml、逐页 title/desc/canonical、JSON-LD（Organization/Product/FAQ） | 校验器通过；robots 正确 |
| QD3-1 | ⬜ | 内容枢纽：methodology 拆「How the score works / Why we say NO / Data honesty」三篇长文 + 内链 | 每篇 ≥800 词、可索引、口径与产品一致 |
| QD3-2 | ⬜ | demo 永链 SEO 页（6 只 demo 票）：预渲染 verdict 摘要 + CTA | `curl` 可见静态内容（不依赖 JS） |
| QD3-3 | ⬜ | 邮件回路：waitlist → re-check 提醒发送脚本（复用 SMTP env）+ 双确认 + 一键退订 | 本地演练信件落地；合规文案 |
| QD3-4 | ⬜ | 分发 SOP：每周 X 帖模板（真实 verdict 卡 + 免责）→ `docs/DISTRIBUTION.md` | 模板 3 套；禁止买粉/互赞 |

### QD4 — 客户心理与文案系统

| ID | 状态 | 任务 | 验收 |
|----|------|------|------|
| QD4-0 | ⬜ | `docs/ICP.md`：ICP 卡片 + 反 ICP + 每页文案对照 ICP 语言 | 文件 + 首页/定价对照表 |
| QD4-1 | ⬜ | §2.2 杠杆逐条落地：NO/WAIT 的「帮你避开」句式、锚定对照、demo 冻结时间戳 vs live 锁 | 逐页 copy diff + before/after 截图 |
| QD4-2 | ⬜ | 定价页异议处理：FAQ（为何不免费/为何无 Elite/退款怎么算/与 hype 工具差异）+ refund 前置 | FAQ JSON-LD 同步 QD3-0 |
| QD4-3 | ⬜ | `docs/VOICE.md`（一页反 hype 语气规范）；全站 status/banner 文案过一遍 | 抽查 10 处一致 |

### QD5 — live 价值与数据（付费墙后的真货）

| ID | 状态 | 任务 | 验收 |
|----|------|------|------|
| QD5-0 | ⬜ | = QR2-1：free OHLCV 路径产品化（host 可刷新 artifact） | 无付费 key 也有新鲜样本 |
| QD5-1 | ⬜ | = QR3-1：门控 API+UI 全字段接 ENGINE_CONTRACT（含 sector reason） | 样例票全字段渲染 |
| QD5-2 | ⬜ | live 冒烟：Pro 测试号跑 live INTC，图表新鲜度断言 | 冒烟脚本 + 记录 |

---

## 四、编排 SOP（Cursor 执行规则 · 给任何模型）

### 4.1 每轮固定流程

```text
1) git -C ~/quantradar pull --rebase（改引擎则 ~/charts 也 pull）
2) 读本文件 → 按 §五取 1 个 ⬜ QD-ID（或用户指定）→ TodoWrite 建轮内清单
3) 勘探：explore 子代理 ≤2 个并行【只读】；需要视觉证据用 browser 子代理
4) 实现：主 agent 是唯一写者；涉及契约/计费改动 → 完成后跑 bugbot/verifier 审一遍
5) 验证闸门（§4.2）全过 → SKILL_INHERIT.md 追加本轮水源记录
6) commit `qr(QD1-1): ...` → push → PROGRESS.md 一行 → 结束语含「可 Manus pull 发布」
7) 本文件对应行改状态（⬜→✅），覆盖 QR-ID 时回写 GROK_GOAL.md
```

### 4.2 验证闸门（分级）

| 改动类型 | 必过 |
|----------|------|
| 任何改动 | `python3 -m unittest discover tests` 全绿；无密钥入库/打印 |
| UI | 本地起服（`PORT=8765 python3 -m app`）+ 375/1440 截图存 `docs/audit/{date}/`；四态走查 |
| 计费 | `tests.test_billing` 全绿；真实 Stripe 一律先 test mode；证据脱敏 |
| 文案 | 对照 `docs/VOICE.md` + §2.3 红线 |
| SEO/分享 | `curl` 验证无 JS 也可见关键内容；OG 卡预览截图 |

### 4.3 子代理边界（硬约束）

- explore：只读勘探/竞品对照，产出进 `docs/explore/` 或 inherit，**禁止写业务代码**
- 主写者 ×1：全仓唯一写者；**禁止双写者同仓**
- verifier（bugbot / security-review）：动 API 契约、计费、auth 时必跑
- browser 子代理：视觉 QA 与截图证据；不代替单测
- 卡住升级：L1 本机 skill → L2 仓内（charts/commands、stock-skills 思想）→ L3 X 双源比对，全部记 `docs/SKILL_INHERIT.md`

### 4.4 模型分工建议（用户换模型执行时参考）

| 任务类型 | 建议 |
|----------|------|
| QD2 视觉 / QD4 文案心理 | 用最强可用模型（品味敏感） |
| QD0-3 / QD3-0 等机械落地 | 快模型即可 |
| QD1 计费 / auth | 强模型 + verifier 双保险，宁慢勿错 |
| 纯勘探/竞品 | explore 子代理挂快模型并行 |

### 4.5 commit / 进度约定

- commit：`qr(QD2-0): render daily charts in verdict desk`
- 进度：`PROGRESS.md` 每轮一行（ID · 一句话 · sha）
- 结束语固定含：已 push `sha`；请 Manus pull 后发布；下一推荐 QD-ID

---

## 五、推荐执行序（前 10 轮）

| 轮 | ID | 为何 |
|----|-----|------|
| 1 | QD0-0 | 未提交资产先落库，防丢防冲突 |
| 2 | QD1-0 | Pro 卖什么必须先裁决 — 商业诚实的地基 |
| 3 | QD2-0 | 真图表 = 最大 wow 缺口，直接抬 N2 |
| 4 | QD1-1 | Stripe 生产化，钱路真通 |
| 5 | QD0-1 + QD2-4 | 审计+移动端一起清 P0 |
| 6 | QD4-1 | 心理杠杆文案落地，抬 N3 |
| 7 | QD1-2 + QD1-3 | Portal + 幂等，售后闭环 |
| 8 | QD3-0 | SEO 基建，铺长尾 |
| 9 | QD2-5 + QD3-2 | 分享卡+永链，增长循环成型 |
| 10 | QD1-5 | 漏斗计数 → 用数据复盘再排后 10 轮 |

---

## 六、粘贴版

### 6.1 战役启动（新会话粘贴一次）

```
/goal QuantRadar 商业冲刺 v1（Desk→Revenue）。
SSOT：~/quantradar/GROK_GOAL_COMMERCIAL.md（子战役）；边界与铁律从 ~/quantradar/GROK_GOAL.md v3。

四条腿：工程收口(QD0) · 商业闭环(QD1) · 前端高级化(QD2) · 诚实增长(QD3/QD4) · live 真货(QD5)。
北极星 N1–N5（30s 理解 / demo→注册 / →checkout / →pro / →live 留存），计量只用服务端 JSONL。

编排（强制）：
· 每轮 1 个 ⬜ QD-ID，按文件 §五推荐序；explore≤2 只读并行；全仓单写者
· 验证闸门：unittest 全绿；UI 出 375/1440 截图证据；计费先 Stripe test mode；密钥零入库
· 契约/计费改动必跑 verifier；卡住走 L1→L2→L3 双源并记 SKILL_INHERIT.md
· commit `qr(QD-ID): …` → push → PROGRESS 一行 → 提示「可 Manus pull 发布」→ 回写状态

红线：假社会证明/假稀缺/cancel 迷宫/伪造 Greeks 或新鲜度/Pro 卖空气（QD1-0 裁决前不吹 live）/第三方 tracker。

本轮从 QD0-0 开始（工作区有未提交的 desk-v1 + billing 闭环，先审查落库）。
```

### 6.2 每轮 kick（重复使用）

```
/goal 继续 QuantRadar 商业冲刺。SSOT：~/quantradar/GROK_GOAL_COMMERCIAL.md
本轮：按 §五取下一个 ⬜ QD-ID（或我指定：QD__）。
守规：单写者；explore≤2 只读；UI 改动出 375/1440 截图；unittest 全绿才 commit；
commit qr(QD-ID): … → push → PROGRESS → 提示可 Manus 发布 → 回写状态与 GROK_GOAL.md。
红线照 §2.3。卡住 L1→L2→L3 双源，记 SKILL_INHERIT。
```

---

## 七、版本

| 版本 | 变更 |
|------|------|
| v1 | 商业子战役建档：QD0–QD5 轨道、ICP+心理杠杆映射、北极星 N1–N5、Cursor 编排 SOP、模型分工、粘贴版 |
