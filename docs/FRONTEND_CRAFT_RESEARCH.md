# 前端精进调研（X + 交易/数据台工艺）→ QuantRadar

> Date: 2026-07-26 · 研究 → **已落地 FR-1～FR-6**（2026-07-26 polish）  

> 工具：agent-reach（twitter-cli / OpenCLI X · Exa · Jina · gh）  
> 约束：对齐 `FULL_FUNNEL_DESIGN.md` / Trust Gate / 主 ICP「别骗我」· 路径 C stdlib 壳

## 0. 调研说明

| 通道 | 结果 |
|------|------|
| `twitter search` | **失败**（HTTP 404 / ClientTransaction）— 关键词搜不可用 |
| `twitter feed` + `opencli twitter search` | 可用；命中多为 AI 设计工作流 / 图标库，**少见**深度 trading desk 工艺帖 |
| Exa + Jina 深读 | **主水源**：交易 App UX、data-dense dashboard 实战文 |
| GitHub | 大量「neon cyberpunk trading dashboard」模板 — **对主 ICP 多为反面教材** |

**结论先行**：X 上「炫酷交易 UI」噪声高；真正适合 QuantRadar 的方案，来自 **data-dense / trading journal / fintech hierarchy** 工艺文 + Linear 系 craft 动效原则，而不是 neon dashboard clone。

---

## 1. 外部工艺要点（分级）

### A. 密度与受众（Lollypop · Trading App Design, 2026-06）

来源：https://lollypop.design/blog/2026/june/trading-app-design/

| 论点 | 对 QuantRadar |
|------|----------------|
| Bloomberg = 最大密度；Robinhood = 渐进披露 | 我们是 **零售 swing + 「别骗我」** → **偏 Robinhood 清晰度 + Terminal 气质**，不是满屏 widgets |
| 差 UX 会改变金融行为；信任与界面一体 | Trust Gate / freeze / 单一 score 继续压过「热闹」 |
| 图是决策核心层；stale/闪烁 = 信任崩 | artifact 图已出；**必须**标 freeze；loading/stale 态要诚实 |
| 微动效只传达系统态（live 脉冲、确认），不娱乐 | 已有雷达/scan；**砍**任何装饰性 bounce/count-up |
| 色盲：红绿不能单独承载语义 | gate 已有 status 文案；tone 旁保留文字（pass/warn/fail） |
| AI 洞察要贴资产上下文，勿另开抢戏仪表盘 | 我们不做 AI pick 墙；Raw JSON 折叠即可 |

### B. Data-dense 八条（Pixel Show · Trading Journal, 2026-05）

来源：https://pixel-show.com/blog/designing-data-dense-dashboards

| # | 教训 | QuantRadar 映射 |
|---|------|-----------------|
| 1 | **应用区默认 dark**（长会话）；营销站可另论 | Desk 保持深炭；封面可同系，勿改奶油浅色 |
| 2 | 语义色两套刻度（深/浅底感知不同） | 维持 `--accent/--warn/--bad`；勿再叠霓虹第二套绿 |
| 3 | Dark 要 **4 级 elevation**，两级会糊成一片 | 现有 `--bg / --panel / --panel-2` 可再差一层 hover/surface |
| 4 | **双字体**：句子用 display/sans，数字用 mono | 已有 Syne + Plex Mono — **加强**：分数/门控/breakdown **强制 mono tabular** |
| 5 | Drawer > 跳详情页（保扫描上下文） | Raw JSON / 放大图用 **drawer/lightbox 同页**，勿新路由打断 desk |
| 6–7 | （文内：表密度、标签/值分离） | Evidence strip = 标签小 + 值 mono；避免句子和数字混同一字重 |
| 8 | **Motion = confidence，不是 decoration**；三时长+一曲线；交易区内禁 spring bounce；勿每行 skeleton 乱跳 | 建议把 motion token 收到 120/200/350ms 量级；封面可稍长，desk 内缩短 |

关键金句（可作评审标准）：

> Motion should *confirm* a user's action, not entertain them.  
> If a motion takes longer than the time to dismiss it, it's too long.  
> Know which side of the line：daily sustained tool vs weekly reassurance — **我们偏前者气质、后者信息量**（30s 决策，不是 14h 盯盘）。

### C. Craft 动效原则（Emil Kowalski · animations.dev / skill 摘要）

| 原则 | 落地 |
|------|------|
| 进入/退出 → ease-out | desk ready 揭示、panel 入场 |
| 屏上移动 → ease-in-out | 少用；滚动用原生 |
| hover/色 → ease | 按钮、chip |
| **一天看 100+ 次的东西不要动** | status 行、gate 文字稳定后勿循环闪 |
| CSS 优先（我们是 stdlib 壳） | 继续纯 CSS；不上 Framer/GSAP |

### D. X / 开源侧信号（慎用）

| 信号 | 判定 |
|------|------|
| 大量「Futuristic neon trading dashboard」仓库 | **拒绝** — 吸引反 ICP，伤害「别骗我」 |
| X 上「先出 3 套高保真再写码」工作流 | **可采用（流程）** — 精进前先定视觉板，再改 CSS |
| `frontend-design` 被列为企业 AI 编程 Top Skills | **已对齐** — 继续用仓内 skill + 本文件 |
| Linear / Rauno 系「界面手感」讨论（Exa） | **借思想**：克制、密度、焦点；不抄 SaaS 紫营销站 |

---

## 2. 适合本项目的「前端配方」

一句话：

**封面用「品牌雷达构图」做信任；Desk 用「data-dense 工具台」做决策；动效只确认系统态；绝不走 neon casino。**

| 层 | 配方 | 反配方 |
|----|------|--------|
| 封面 | 5+1 预算、品牌>问句、一雷达平面、双 CTA | 统计条、多卡、假证明、紫渐变 |
| Desk | Verdict 最大 → Why → Gates → 图 → Breakdown → Freshness → Next | 指标墙、多 Composite、未标注 live |
| 字 | Syne 标题 + **Plex Mono 全数字** | 单一圆体、数字不对齐 |
| 色 | 深炭四级面 + 雷达绿/琥珀/红作语义 | 霓虹多层 glow |
| 动 | 封面 ambient 可慢；desk ≤350ms；reduced-motion | bounce、count-up、表格逐行 stagger |
| 图 | 真图 + freeze；点击同页放大 | 假实时跳动蜡烛 |

---

## 3. 精进切片

| ID | 精进项 | 状态 | Pri |
|----|--------|------|-----|
| FR-1 | Desk motion ~120/200/350；load scan 仅 loading | **done** · `--motion-*` | P0 |
| FR-2 | 四级 elevation `--bg-void / --bg / --bg-elev / --surface` | **done** | P0 |
| FR-3 | 数字 `tabular-nums` + mono（`.num` / gate / dial / bd） | **done** | P0 |
| FR-4 | Gate：**色条 + Pass/Warn/Fail/Unknown 文字** | **done** · `.gate-status` | P0 |
| FR-5 | 图表同页 lightbox（Esc / 点遮罩关闭） | **done** | P1 |
| FR-6 | 封面 `--motion-hero-scan` vs desk `--motion-load-scan` | **done** | P1 |
| FR-7 | 自托管字体（去 Google CDN） | 未做 | P1 |
| FR-8 | 拒绝 neon template 美学 | 恒守（配方 §2） | 恒守 |

---

## 4. 要不要继续精进设计/动效/沉浸？（2026-07-26 复验）

使用 agent-reach：twitter-cli（search 仍 404）· OpenCLI X · `twitter user-posts` · Exa · Jina · Reddit（噪声）· GH。

### X 复试

| 通道 | 结果 |
|------|------|
| `twitter search` | **仍失败** HTTP 404 / ClientTransaction |
| OpenCLI `twitter search` | 可用；命中多为 **SaaS 宣传片 / AI dashboard showreel**，对 desk 精进几乎无配方价值 |
| `twitter user-posts @emilkowalski` / `@raunofreiberg` | **可用**；信号是工艺克制与变体试验，不是「更沉浸」 |

### 外部共识（是否值得再砸沉浸感）

| 源 | 要点 | 对 QR |
|----|------|--------|
| Emil · [You Don't Need Animations](https://emilkowal.ski/ui/you-dont-need-animations) | 高频交互勿动；≤300ms；无目的则删；动效可伤信任 | Desk 已达配方；**再加沉浸 = 风险** |
| Motion budget / When to skip (2026) | 数据台动画抢认知；不确定就 skip；营销可炫、产品要效率 | 封面 ambient 已够；勿第三层 |
| Fintech trust patterns | 谨慎用户把重动效读成「钱花在营销站」；homepage ≤1 ambient + 1 触发 | 我们已是 1 雷达 + loading scan |
| Fintech 2026 (Masterly) | 信任 = 核心动作清晰 + 诚实数字，不是美学皮肤 | 下一刀应是部署/转化，不是 glow |

### 判决

**不必再做一轮「更精致 / 更沉浸」的设计大改。** FR-1～FR-6 已覆盖工艺配方；继续加沉浸感的边际收益低，且易伤害主 ICP「别骗我」。

| 仍值得（小） | 不值得（现刻） |
|--------------|----------------|
| FR-7 自托管字体（性能/少 CDN） | parallax / scroll-jack / 第三层 ambient |
| 人工 30s 盲测 + 截图入 audit | bounce、count-up、逐行 skeleton |
| 部署 → 真用户 → 看 funnel | neon / 「immersive trading」模板向 |

**ROI 更高**：commit → Render 自部署 → Stripe/真实转化 → charts mount；设计只在用户反馈「看不清/不信」时再动刀。

---

## 5. 下一刀（可选 · 非阻塞）

1. FR-7 自托管 Syne + IBM Plex Mono（可选）  
2. 人工 30s 盲测 + 新截图入 `docs/audit/`  
3. **优先**：commit → push → `SELF_DEPLOY.md`（仍不动 Trust Gate）

---

## 6. 水源

| 级 | 源 |
|----|-----|
| B/C | Lollypop Trading App Design (2026-06) |
| B | Pixel Show · Data-Dense Dashboards (2026-05) |
| A/B | Emil Kowalski · You Don't Need Animations / Great Animations |
| B | Motion budget / When to animate and skip (2026) |
| B | Fintech trust / calm site patterns（Exa；警惕假社证） |
| C | Exa：Linear/Rauno craft |
| D | OpenCLI X：dashboard showreel（弱相关 / 反面倾向） |
| — | twitter-cli keyword search **仍不可用**（404）；user-posts 可用 |
| 反面 | GH neon / immersive trading dashboard 模板群 |

Agent Reach：v1.5.0（已最新）。
