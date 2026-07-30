# QuantRadar 全流程整套设计（SSOT）

> **地位**：Desk → Revenue 前端 + 漏斗体验的可执行设计 SSOT。  
> **冲突裁决**：路径 C / 铁律 / Skill 环以 `GROK_GOAL.md` 为准；商业北极星与红线以 `GROK_GOAL_COMMERCIAL.md` 为准；收款前验收以 `docs/TRUST_GATE.md` 为准；Pro 价值以 `docs/PRO_VALUE.md`（裁决 **B · supporter_until_mount**）为准；思想映射以 `docs/STOCK_AGENT_MAP.md` 为准。  
> **本文件只管**：信息架构、封面/Desk/Pricing/Login/Methodology 规格、tokens、钩子地图、本周切片与验收。  
> **水源**：ICP+前端+钩子研究（会话 agent `8fc8619f`）；`ENGAGEMENT.md`；现网 `static/*`；frontend-design 技能 + 用户硬规则；前端精进调研见 **`docs/FRONTEND_CRAFT_RESEARCH.md`**（X/Exa/交易台工艺）。  
> **日期**：2026-07-26

---

## 0. 一句话目标与成功判据（N1–N5）

**一句话目标**：把「诚实的机械雷达」做成访客 30 秒信任、愿意掏钱、付费后真有货（或诚实 supporter，不卖空气）的产品。

| ID | 判据 | 设计如何服务 |
|----|------|--------------|
| **N1** | 盲测 30s 能口述「该不该上手 + 为什么」 | 首屏一问 + Desk Verdict→Why→Gates；单一 `primary_score` |
| **N2** | demo → 注册 ≥8% | 免费 artifact demo；结果后 Sign in；Remind me 不挡结果 |
| **N3** | 注册 → checkout ≥25% | Next / Pricing 情境升级；锚定 + supporter 诚实 |
| **N4** | checkout → pro_active ≥60% | Stripe 路径可用；无暗模式；webhook 写 plan |
| **N5** | Pro 7 日内 ≥1 live_run ≥50% | mount 前不催 live；mount 后 Mode→live；轻留存 |

计量：仅服务端 `data/funnel.jsonl`（`demo_run|analyze_run|signup|checkout_start|pro_active|live_run|notify_save`）。**禁止为指标造假。**

**产品硬锁（不可改叙事）**：

- 路径 C：壳 normalize + map + desk，**不算分**，不嵌整仓 stock-agent  
- Pro = `supporter_until_mount` 直至 `/health.charts_status=mounted`  
- UI 仅一个 `primary_score`（= charts `score.final`）

---

## 1. 精准客户与反客户（设计含义）

### 1.1 一句话主 ICP

**被 Discord/电报喊单与假回测烧过、仍做美股 swing/期权、宁可多数日子空仓、愿为「别骗我」的可审计雷达付 $29 的 25–45 岁散户。**

### 1.2 卡片 → 设计含义

| | 主 ICP | 次 ICP | 反 ICP |
|--|--------|--------|--------|
| 要什么 | 冷静台：单一结论、门控、诚实 freeze | 可审计：methodology、JSON、契约 | 今日必涨、胜率墙、VIP 喊单 |
| 设计含义 | 首屏不堆仪表盘；WAIT/NO 是权威不是失败 | Raw JSON 折叠；methodology 深链 | 文案主动劝退；无 Elite；无假社交证明 |
| 渠道 | X / 纪律 Reddit / SEO「how score」 | HN / 技术 Twitter | 喊单群（不投放） |
| 付费触发 | 看懂 avoided-loss + freeze vs live | 支持诚实产品 | 没有神股就不付（让其流失） |

**对谁说话（封面语气）**：  
EN — *You got burned by urgency signals. We show one mechanical posture and most days tell you to stand aside.*  
中 — *被喊单坑过的人：一个机械姿态分，多数日子让你别动手；冻结样本写清楚，绝不假装 live。*

---

## 2. 全站信息架构（每页一职 + 用户动线）

| 路由 | 一职 | 主 CTA | 禁止抢戏 |
|------|------|--------|----------|
| `/` 封面带 | 品牌 + 一问 + 进 demo | Try demo | 统计条、多卡墙、假证明 |
| `/` Desk `#desk` | 跑票 → Verdict 台 | Analyze / Demo | 结果前注册墙 |
| `/pricing` | Free vs Pro 诚实对照 + checkout | Get Pro | Elite、假划线价、卖 live-now |
| `/login` | 自有账号；`next=checkout\|live` 回流 | Sign in / Register | Manus app-auth |
| `/methodology` | 可审计权威（How score / Why NO / Data honesty） | ← Back to radar / Try demo | 假 track record |
| `/r/{ticker}` | 只读分享摘要 + OG（吸引） | Open full desk `/?demo=` | 可交易 CTA、假盈亏 |
| `/terms` `/privacy` `/refund` | 合规前置（TG-9） | — | 营销话术 |
| `/track` | 稀疏 operator 笔记（无假胜率） | Try demo | 假 stats / 把 API 当主 CTA |

### 2.1 导览 SSOT（Graph P0 · 补边）

| 面 | 节点集 / 边 |
|----|-------------|
| **产品顶栏** | `Methodology · Track · Pricing · Sign in`（品牌 → `/`；首页可另显 Upgrade/Sign out） |
| **法律页回流** | 文末必有 `Home · Try demo · Methodology · Pricing`（禁止只停在法律团） |
| **`/r/{ticker}` 主出边** | CTA `Open full desk` → `/?demo={TICKER}`；顶栏含产品节点 + Open desk |
| **噪声** | `/btn-demos` `robots Disallow`；`/api/track` 仅页脚小号，不当正文主链 |
| **Remind** | `/api/notify` 只做 waitlist 落盘；UI 必须写明 **邮件尚未开通**（QD3-3 前禁止假装已发信） |

```text
动线（最小闭环）
X/SEO/分享卡 → / 或 /r/INTC → Try demo | ?demo=INTC
    → Desk ready（Verdict→Why→Gates→Breakdown→Freshness→Next）
        ├─ WAIT/NO → Remind me（notify 存档；邮件 QD3-3）
        ├─ 喜欢读 → /login?next=checkout → /pricing → Stripe → pro_active
        └─ freeze 标签 → 升级好奇（不伪造 live）
Pro + charts mounted → Mode live → live_run（N5）
```

---

## 3. 封面 / Landing 规格（元素预算、雷达视觉、CTA、禁区）

### 3.1 首屏元素预算（严格 5+1 · 研究 D2 · 服务 N1 / 信任）

| # | 元素 | 规格 | 约束 |
|---|------|------|------|
| 0 | Eyebrow | `Beta · no fake social proof` | ≤6 词；accent；uppercase |
| 1 | **品牌** | `QuantRadar`（Radar=accent） | `clamp(2.4rem,7vw,3.75rem)` Syne 800；**大于** headline |
| 2 | Headline | `Should you engage this setup?` | ≤8 词；`clamp(1.55–2.15rem)` |
| 3 | Support | one score · gates · honest freeze | 1 句；≤22 词；muted |
| 4 | CTA 组 | Primary `Try demo` · Secondary `Pricing` | 热区 ≥44px；主按钮仅 1 个 |
| 5 | **主导视觉** | 全幅/贴边雷达 SVG 平面 | 非卡片、非拼贴、无 overlay badge |

首屏**下**（`hero-samples`，不算堆料）：最多 3 demo chips + data mode 一行。Chips **不得压过**品牌。  
**品牌测试**：去掉 nav 后首屏仍一眼是 QuantRadar。

### 3.2 雷达视觉

- 色：`--accent #3dd68c` 环线 / sweep；背景深炭渐变（非平涂）  
- 动效：`qrSweep` 环境扫描；`prefers-reduced-motion: reduce` 时停  
- **禁**：紫渐变、cream 衬线报纸风、霓虹多层 glow 堆叠、hero 上浮 badge/sticker、inset 媒体卡

### 3.3 CTA 行为

| 控件 | 行为 |
|------|------|
| Try demo | `runDemo(INTC)` + 平滑滚到 `#desk` |
| Pricing | `/pricing` |
| Chip / `/?demo=TICKER` | artifact sample，0 credits（TG-5） |

### 3.4 禁区（赶走主 ICP / 吸引赌徒）

假用户数 · 胜率环 · 「今日 5 只必涨」 · 倒计时稀缺 · 结果前强制注册 · 把 artifact 写成 live · Elite 无 track record · URGENT/FOMO · 多 Composite 分数。

---

## 4. Desk 结果台规格（四态、层级、文案、动效剂量）

### 4.1 四态 `data-state`

| 态 | UI | 动效剂量 |
|----|-----|----------|
| `idle` | 控件可见；verdict 隐藏；status 引导 demo | 无扫描 |
| `loading` | 控件降噪；`.desk-scan` 光束 | `scanBeam` ≤ loading 时长；可关 |
| `ready` | 完整结果层级 | dial 描弧、gate `gateLit` stagger、breakdown `bdGrow`、可选 `verdictSweep` ≤700ms |
| `blocked` | 错误/无数据 fail-closed；Next 给 demo 出路 | 无庆祝动效 |

### 4.2 结果层级（上→下，不可打乱 · 研究 D3）

1. **Verdict action** — 最大字重；tone→ok/warn/bad  
2. **Why** — 1–3 行；PUT 前缀 *hedge bias, not a sell order*；姿态≠方向  
3. **Avoided line** — WAIT/NO/PUT 时损失厌恶一句  
4. **Score dial** — 仅 `primary_score`；标签 `Mechanical posture` + `Posture ≠ direction · PUT ≠ sell`  
5. **Gates** — Market → Sector → Stock（+ Entry timing 有则显示）；灯色**只跟**服务端 status；unknown≠pass；禁 spy 启发式  
6. **Breakdown** — 同 score 分量；注明非第二 composite；头上 `freeze-pill`  
7. **Freshness** — 冻结/来源/警告必见  
8. **Next** — 唯一转化挂点（remind / upgrade / share `/r/` / another）  
9. **Raw JSON** — `<details>` 折叠，服务次 ICP  

**封面→Desk 动线（D5）**：Try demo / `?demo=` → loading→ready → **P0 必须** `scrollIntoView`/`focus` 到 `#verdictBlock`（手机不丢结果）。钱在理解之后要。  
**动效总剂量（D3）**：环境 1（雷达）+ 反馈 1（loading scan）+ 揭示 2–3（gate/dial/bars）。超过即噪音。

### 4.3 Next 文案矩阵（服务参与/付费，不挡结果）

| 条件 | Title | Copy 要点 | Actions |
|------|-------|-----------|---------|
| `plan_required` | Supporter plan for live | Pro=$29/$249；live 仅 mount 后解锁 | Upgrade · Pricing |
| `!ok` | Blocked | fail-closed；试 demo | Try INTC demo |
| WAIT/NO/PUT | Next — stay in the loop | avoided_line + Remind me（waitlist only） | Notify · Analyze another · Upgrade · Methodology |
| ok + demo + !Pro | Liked the read? | freeze + supporter 锚定 | Sign in & upgrade · Pricing · another demo |
| Pro + !mounted | Pro active — live pending | 支持者权益在；live pending | Pricing · Re-check demo |
| Pro + mounted | Pro active | 可切 live | Run live |

### 4.4 移动端（375 · P0）

- sticky `.desk-controls`；Analyze 热区 ≥44px  
- Verdict 视觉权重大于 breakdown  
- hero 雷达降 opacity，不挡文案

---

## 5. Pricing / Login / Methodology 规格

### 5.1 Pricing（付费 · N3/N4）

| 块 | 要求 |
|----|------|
| Hero | 品牌 mark +「Clear Free vs Pro」+ supporter / artifact_only 一句 |
| Toggle | Monthly $29 / Yearly $249 save ~28%（整数价，禁 $266.58） |
| Free 卡 | Demo 不扣额度；单分；无 live；options 非 actionable |
| Pro 卡 | **Supporter plan**；higher limits now；live auto-unlock when mounted；锚定「−8% on $3k ≈ 8 mo」 |
| FAQ | Why not free live · Why no Elite · Refund · vs hype · worth it before live |
| 合规链 | Refund / Terms 可见（TG-9） |
| CTA | 未登录 → `/login?next=checkout`；已登录 → checkout；Stripe 未配 → 诚实提示，不硬编密钥 |

### 5.2 Login（回流）

- 主路径：email + password；magic 次要；Google 仅 env  
- `next=checkout` → `/pricing?authed=1`；`next=live` → `/?want=live`  
- 明示 No Manus；Continue as guest 保留 desk

### 5.3 Methodology（信任 · 次 ICP）

P0 页须锁定口径：

1. One public score = `primary_score`  
2. Mechanical posture ≠ direction；PUT ≠ sell order  
3. Gates + fail-closed  
4. Demo artifact vs live（Pro + mounted）  
5. No fake social proof  

P1（QD3-1）：拆三长文 How the score works / Why we say NO / Data honesty（≥800 词可索引）。

### 5.4 Share `/r/{ticker}`（吸引 · N1/N2）

- 只读摘要：ticker · primary · score · freeze 提示 · Educational only  
- CTA → `/?demo={ticker}` 全台  
- OG：title/description；图可用既有 `/static/og-default.svg`（逐票 SVG 模板属 P1）  
- 仅 DEMO_TICKERS；未知票回退 INTC 或 404 诚实页  
- **不**提供下单/Greeks/假盈亏

---

## 6. 设计系统 tokens（色/字/间距/motion）— 对照 site.css「现状 → 目标」

| Token | 现状 (`site.css`) | 目标 | 服务 |
|-------|-------------------|------|------|
| `--bg` | `#090b0a` | 保持深炭（产品裁决：交易台 dark 保留） | 品牌 |
| `--accent` | `#3dd68c` | 保持雷达绿；禁改紫 | 品牌 |
| `--warn` / `--bad` | `#e8b84a` / `#e86a6a` | 保持；gate 三色 | 信任 |
| `--display` / `--mono` | Syne / IBM Plex Mono（CDN） | 保持；P1 自托管 woff2（QD0-3） | 品牌 |
| `--motion-*` | 160/420/720 / scan 3.6s / stagger 110ms | 保持剂量；减动效关闭 | 参与 |
| `--space-1…6` | P0 增量 | 4/8/12/16/24/40px 命名 | 纪律 |
| `--touch-min` | P0 增量 | `44px` | 移动 |
| `--z-header` / `--z-sticky` / `--z-scan` | P0 增量 | 20 / 12 / 3 | sticky 不挡 Next |
| `--focus-ring` | P0 增量 | accent 双环 | 键盘可达 |
| `--radius` | 10px | 保持；hero **无卡**；pricing **两卡**可作交互容器 | 反模板 |
| 字号 | brand-mark > h1 | 品牌 > 问句 | N1 |
| reduced-motion | 已有块 | 停 sweep/scan/loop；dial snap | 无障碍 |

**签名动效（保留）**：封面 `qrSweep` · loading `scanBeam` · ready dial/gates/breakdown · `verdictSweep` 可选。

---

## 7. 吸引→参与→付费→轻留存 钩子地图（已有 / 缺口 / 优先级）

| 阶段 | 钩子 | 机制 | 落地 | 现状 | Pri |
|------|------|------|------|------|-----|
| 吸引 | Anti-hype 真相卡 | 逆 FOMO | X 帖 + `/r/{ticker}` | 分享页 P0 落地；周更属 ops | P0 |
| 吸引 | Demo 深链 | PLG 即时价值 | `/?demo=` · chips | **已有** | P0 |
| 吸引 | SEO 枢纽 | 高意图 | methodology 三长文 | 页在；长文 **缺口** QD3-1 | P1 |
| 吸引 | 诚实 null 社证 | 可信 | `/api/public_stats` | **已有** | 恒守 |
| 参与 | 30s 单一结论 | 认知流畅 | Verdict+dial | **已有** | P0 |
| 参与 | Gate M→S→S | 透明 | evidence-strip | **已有** | P0 |
| 参与 | Avoided-loss | 损失厌恶 | `engagement.avoided_line` | **已有** | P0 |
| 参与 | Freeze / Zeigarnik | 未完成感 | freeze-pill | **已有** | P0 |
| 参与 | Remind me | 承诺 | `/api/notify` | API **已有**；邮件 QD3-3 **缺口** | P0/P1 |
| 参与 | 真图表 wow | 具身证据 | artifacts PNG | **缺口** QD2-0 | P0* |
| 付费 | 避损锚定 | 锚定 | pricing + Next | **已有** | P0 |
| 付费 | 年付 ~28% | 承诺 | interval toggle | **已有** | P0 |
| 付费 | Supporter 诚实 | 风险反转 | PRO_VALUE B 文案 | **已有** | P0 |
| 付费 | Refund 前置 | 风险反转 | FAQ + `/refund` | **已有**；Portal QD1-2 **缺口** | P0 |
| 付费 | Checkout 低摩擦 | 减放弃 | login→Stripe | 代码有；**生产 Stripe QD1-1 缺口** | P0 |
| 留存 | pro_active 诚实态 | 期望管理 | Next Pro pending | **已有** | P0 |
| 留存 | 漏斗复盘 | 学习 | `funnel_report.py` | **已有** | 恒守 |
| 留存 | live_run | 价值兑现 | mount 后 | 引擎未 mount | P2 |

\* QD2-0 依赖 charts PNG 资产；本周有资产则做，无则诚实降级。

**§2.2 杠杆对照**：损失厌恶/锚定/蔡格尼克/社会证明诚实 → 已有；风险反转 Portal / 承诺邮件 / 权威长文 → 缺口。

---

## 8. Trust Gate 与诚实约束清单（设计侧检查表）

实现/文案 PR 自检（打勾再推付费叙事）：

- [ ] **TG-1** 页面最多 1 个主分数 `primary_score`  
- [ ] **TG-2** `primary.action` 与 Why / CTA 一致  
- [ ] **TG-3** 无 testimonials；无硬编码用户数；无则不展示  
- [ ] **TG-4** 价：$29 / $249 整数；全站一致  
- [ ] **TG-5** Demo = artifact，不扣额度、不打 live  
- [ ] **TG-6** 假 ticker / 无数据 fail-closed  
- [ ] **TG-7** 模拟期权 `options_actionable=false` + 明示  
- [ ] **TG-8** og/品牌图自托管 `static/`  
- [ ] **TG-9** Terms / Privacy / Refund 可访问  
- [ ] **TG-10** 无 `manus.im` 登录；`manus_login=false`  
- [ ] **PRO_VALUE B** 不写「付费即 live」；supporter_until_mount  
- [ ] **STOCK_AGENT** 姿态≠方向；PUT≠卖出；gate 不客户端编造 pass  
- [ ] **红线** 无假稀缺/cancel 迷宫/默认加购/第三方像素/密钥入库  
- [ ] **路径 C** 壳不算分、不嵌 stock-skills DAG  

---

## 9. 本周实现切片 P0→P2（工程可勾选）

### P0（本周 · D-P0 准绳 · 可本地验证）

| ID | 项 | 状态 |
|----|-----|------|
| D-P0-doc | SSOT 本文件 + `ENGAGEMENT.md` 链入 | ✅ |
| D-P0-cover | 封面 5+1 预算（品牌>问句·雷达·双 CTA） | ✅ 对齐 / 勿堆料 |
| D-P0-desk | Desk 层级 Verdict→…→Next；四态；姿态/PUT 文案 | ✅ |
| **D-P0-2** | **ready 后 scroll/focus → `#verdictBlock`** | ✅ 本轮实现 |
| D-P0-motion | 剂量：雷达+scan+gate/dial/bars；reduced-motion | ✅ 保留勿回滚 |
| D-P0-pricing | Free/Pro **两卡**；supporter/锚/FAQ/refund；无 Elite | ✅ |
| D-P0-375 | sticky Analyze ≥44px；desk 底 padding 防挡 Next/Remind | ✅ 本轮加固 |
| D-P0-trust | freeze / posture≠direction / PUT≠sell / supporter_until_mount | ✅ methodology+desk |
| D-P0-funnel | funnel 事件 + sample/notify/register 限流 + 体积帽 | ✅ 勿回滚 |
| D-P0-map | STOCK_AGENT_MAP + entry_timing；gate 跟服务端 | ✅ 勿回滚 |
| D-P0-demo | `/?demo=` 深链 | ✅ |
| D-P0-share | `/r/{ticker}` 只读摘要 + 基础 OG | ✅（逐票 SVG OG→P1） |
| D-P0-1 ops | **自部署** Render（不用 Manus）— `docs/SELF_DEPLOY.md` | ⬜ 用户侧 push+DNS |
| D-P0-3 | QD2-0 真图 PNG | ✅ fixture assets + `/api/charts/` + desk 出图 |
| QD1-1 | Stripe 生产价 + webhook | ⬜ env |

### P1

- [ ] QD3-3 Remind 邮件 + 退订  
- [ ] QD1-2 Customer Portal  
- [ ] QD3-1 methodology 三长文  
- [ ] QD2-5 逐票 OG SVG 模板增强  
- [ ] QD0-1 UI_AUDIT 375/1440 截图档  
- [ ] QD0-3 字体自托管  

### P2

- [ ] QD3-0 SEO JSON-LD / sitemap.xml  
- [ ] live mount 后 N5 习惯回路打磨  
- [ ] QD2-3 verdict 扫描签名再收口（若需）  

---

## 10. 验收清单（盲测 30s、375/1440、漏斗事件）

### 10.1 盲测 30s（N1）

找 5 人看 `/?demo=INTC`（勿讲解）。通过标准：能说出  
1) 该不该上手（WAIT/NO/…）  
2) 至少一个为什么（gate 或 why）  
3) 知道这是 demo/冻结而非「保证赚钱」。

### 10.2 视口

| 视口 | 检查 |
|------|------|
| 375 | 品牌可读；CTA ≥44px；sticky Analyze；Verdict 不被挤没 |
| 1440 | hero 一 composition；雷达不抢 CTA；desk 层级清晰 |
| reduced-motion | 无循环扫线；结果仍可读 |

### 10.3 漏斗事件（本地）

```bash
python3 -m unittest discover -s tests -v
PORT=8765 python3 -m app
# 浏览器: /  ·  /?demo=INTC  ·  /pricing  ·  /r/INTC
python3 scripts/funnel_report.py
```

期望：demo 产生 `demo_run`；注册→`signup`；checkout 启动→`checkout_start`（Stripe 配齐时）；无原始 email 进 JSONL。

### 10.4 拟合矩阵（决策 → 目标）

| 决策 | 信任 | 参与 | 付费 | 劝退反 ICP |
|------|:----:|:----:|:----:|:----------:|
| 单一 primary_score | ✓ | ✓ | | ✓ |
| WAIT/NO + avoided_line | ✓ | ✓ | ✓ | ✓ |
| freeze / supporter 文案 | ✓ | ✓ | ✓ | |
| 无假社证 / 无 Elite | ✓ | | | ✓ |
| Remind 不挡结果 | ✓ | ✓ | | |
| 结果后 Upgrade | ✓ | | ✓ | |
| `/r/` 只读+免责 | ✓ | ✓ | | ✓ |
| 路径 C / 不算分 | ✓ | | | |

---

## 附录 A · 实现对照（2026-07-26）

| 模块 | 文件 |
|------|------|
| 封面+Desk | `static/index.html` · `static/site.css` |
| Pricing | `static/pricing.html` |
| Methodology | `static/methodology.html` |
| Share | `app/server.py` `/r/{ticker}` · `static/share.html`（若拆分） |
| Funnel | `app/funnel.py` · `scripts/funnel_report.py` |
| 契约/姿态 | `app/contract.py` · `docs/STOCK_AGENT_MAP.md` |
| Pro 价值 | `docs/PRO_VALUE.md` |
| Trust | `docs/TRUST_GATE.md` |
| 参与文档 | `docs/ENGAGEMENT.md` |

## 附录 B · 给下一实现 agent 的开工句

```
按 docs/FULL_FUNNEL_DESIGN.md §9 P0 未勾项继续。
红线：supporter_until_mount · 单一 primary_score · 路径 C · Trust Gate。
验证：unittest 全绿；PORT=8765 演示 / ?demo=INTC /pricing /r/INTC。
默认不 commit，除非用户要。
```
