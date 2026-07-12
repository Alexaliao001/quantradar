# GROK /goal — 多站点极致收官（SITES EXTREME）

> **主任务源**：`~/quantradar/GROK_GOAL_SITES_EXTREME.md`  
> **姊妹**：单品 QuantRadar 仍用 `~/quantradar/GROK_GOAL.md`  
> **迁移事实底稿**：`docs/MULTI_SITE_MIGRATION.md` · `docs/LIVE_NOW.md`  
> **原则**：**不烧 Manus agent 积分** · **能静态的极致静态** · **该后端的极致最小可产品** · **每轮可验证**

---

## 粘贴版（复制到 Grok Build）

### 精简版（推荐）

```
/goal 多站点极致收官。主任务源：~/quantradar/GROK_GOAL_SITES_EXTREME.md

现状（2026-07-13）：五域已迁出 Manus 托管；QR 有 path-C 壳；其余多为静态。
铁律：零 Manus agent；Render Hobby ≤2 自定义域；单写者；每轮 1 个 SITE-ID。

每轮：
  1) 读本文件 §三 现状表 + PROGRESS_SITES.md
  2) 取 §六 最高 ROI 未完成项
  3) 实现 → §七 验收脚本 PASS
  4) commit/push 相关仓；更新 PROGRESS_SITES.md 一行
  5) update_goal

下一优先：SX0 全站验收绿 → SX1 QR 数据层 → SX2 MoYu 轻后端 → SX3 Fortune 最小后端 → SX4 Drama 仅演示层极致（全量生成另开授权）
```

### 完整版

```
/goal SITES EXTREME：把「能做的」全部做到极致。

能做 = 在免费/可控成本下，不依赖 Manus agent，能 GitHub SSOT + Render/GH Pages 交付的。
极致 = 可靠性 / 诚实降级 / 安全 / 性能 / 文案与设计 / 可观测 / 文档 都到可对外 demo 的专业线。

不做（除非当轮用户书面授权付费与时间）：
  · 短剧全量 Kling/视频账单拉满
  · Manus Forge 绑定
  · 同时开 Fortune + Drama 两个重后端

SSOT 仓：
  quantradar / moyu-fortune(+deploy) / fortune-insight-deploy /
  rongjian-portfolio(+deploy) / ai-drama-studio(+deploy)
```

---

## 一、使命（一句话）

把迁出 Manus 后的**全部自有表面**做成：**域名稳、页面真、该动的会动、不该装的不装**——  
在零 Manus agent、优先免费栈的约束下，把**每一站的天花板**摸到当前架构允许的极限。

### 1.1 「能做」的定义

| 类别 | 能做 | 不能做（默认） |
|------|------|----------------|
| 托管/域名 | GH Pages + Render Free 极致稳定 | 无脑上付费集群 |
| 静态产品 | UI/SEO/无障碍/错误边界/缓存 | 假装有 API |
| QR | 壳 + charts 数据契约做到可交易级诚实 | 抄整仓 stock-skills 进前端 |
| MoYu 轻后端 | 规则抽签 + 历史 + 排行（可选 LLM） | 一上来全量会员体系 |
| Fortune 最小后端 | 访客塔罗 1 路径 + 报告 JSON + 限流 | 八字/支付/管理后台一次全上 |
| Drama | 演示态极致 + 明确「静态」门闸 | 未授权烧视频 API |
| 个人站 | 设计/性能/SEO 极致 | 自建重 CMS |

### 1.2 北极星（S1–S12 收官才算「极致」）

| ID | 收官标准 |
|----|----------|
| S1 | 全部生产域 HTTPS 200 + 证书域名匹配（无 `*.github.io` 错配） |
| S2 | `scripts/sites_extreme_verify.py` 全 PASS（见 §七） |
| S3 | 任一站 API 缺失时：**不白屏**；UI 诚实降级（文案/空态/禁用） |
| S4 | QR：`/health` 真字段 + 至少 1 条 live 或 artifact 分析路径稳定 |
| S5 | MoYu：抽签闭环可重复（本地规则即可）且无 OAuth crash |
| S6 | Fortune：至少 1 条「访客可读报告」路径不依赖 Manus |
| S7 | Drama：首页/创建页不 crash；生成按钮明示「需后端」或接上最小 stub |
| S8 | 个人站 Lighthouse 移动端 Performance ≥ 90（或记清瓶颈与取舍） |
| S9 | 每仓 deploy 有 README：环境变量表 + 静态 vs 全栈 边界 |
| S10 | 密钥从不进 git；`.env.example` 齐全 |
| S11 | 成本面板：各服务 Render 小时/GH 静态零算力 写进 `docs/SITES_COST.md` |
| S12 | 用户体感 U1–U10 自评全绿（§1.3） |

### 1.3 用户体感 U1–U10

| ID | 好样子 |
|----|--------|
| U1 | 书签打开任意生产域 <3s 有内容（冷启动除外并有提示） |
| U2 | 强制刷新后无旧 bundle 白屏（cache 策略正确） |
| U3 | 点登录/生成：**永不** `new URL("undefined/…")` |
| U4 | 网络失败有中文/英文可理解提示 |
| U5 | QR 假 ticker 不给 buy；disclaimer 可见 |
| U6 | MoYu 抽一次有结果可分享（即使文案是本地） |
| U7 | Fortune 至少能完成一次「免费预览」级体验 |
| U8 | Drama 不假装正在渲染长视频 |
| U9 | 个人站作品链接全可点、无 404 |
| U10 | 你愿意把链接发到朋友圈/简历而不心虚 |

---

## 二、边界（铁律，违反 = 本轮作废）

1. **零 Manus agent 积分**：DNS/设置可点 UI；禁止开 agent 修站。  
2. **GitHub SSOT**：私有源码 + public `*-deploy` 镜像；禁止只在 Manus 改。  
3. **Render Hobby 自定义域 ≤2 组**（当前：`quantradar.one` + `fortunesite.one` 系）。新增域先腾位或走 GH Pages。  
4. **单写者**：每轮 1 个 SITE-ID / 1 个主仓；禁止并行改多仓无 worktree。  
5. **诚实产品**：静态站禁止伪造「已生成成功」；缺后端必须可见降级。  
6. **密钥**：不提交 `.env`；支付/AI key 只走宿主环境变量。  
7. **成本默认免费**：付费 API/视频模型 **当轮用户明文授权** 才接。  
8. **QuantRadar 公式**：charts/L1 语义变更走 `GROK_GOAL.md` 铁律 + 回归。  

---

## 三、现状底表（每轮开工先核对，过时则改表）

> 更新于 **2026-07-13** 会话后。验收以 `sites_extreme_verify.py` 为准。

| 站 | 生产 URL | 托管 | 形态 | 后端 |
|----|----------|------|------|------|
| QuantRadar | https://quantradar.one | Render `quantradar-shell` | path-C 壳 | ✅ 有（artifact 为主） |
| Fortune | https://fortunesite.one | Render + 域 | SPA | ❌ 静态 |
| MoYu | https://chillworks.ai | GH Pages | SPA | ❌ 静态 |
| Portfolio | https://rj.fortunesite.one | GH Pages | SPA | ❌ 不需要 |
| Drama | https://shorts.fortunesite.one | GH Pages | SPA | ❌ 静态（已修 OAuth URL crash） |
| 备用 | `*-onrender.com` | Render Free | 静态 host 或 QR 壳 | 见上 |

**Deploy 仓**

| 产品 | 源 | deploy |
|------|-----|--------|
| QR | `Alexaliao001/quantradar` | 同仓 public |
| MoYu | `moyu-fortune` | `moyu-fortune-deploy` |
| Fortune | private / deploy | `fortune-insight-deploy` |
| Portfolio | `rongjian-portfolio` | `rongjian-portfolio-deploy` |
| Drama | `ai-drama-studio` | `ai-drama-studio-deploy` |

---

## 四、能力栈（强制）

1. 本地：Shell · gh · Render API（`~/.render/cli.yaml`）· Manus DNS API（仅记录，零 agent）  
2. 仓库 skill：`web-design-guidelines` · `design-taste-frontend` · `check-work`  
3. QR 专用：`~/quantradar/GROK_GOAL.md` + charts 契约  
4. 卡住：先读 MULTI_SITE / LIVE_NOW；再搜本机历史会话；最后才 web  

---

## 五、每轮 SOP

```
0.  读本文件 §三 + PROGRESS_SITES.md（无则创建）
0b. git pull 将要改的仓
1.  python3 ~/quantradar/scripts/sites_extreme_verify.py  （基线）
2.  取 §六 一项 SITE-ID
3.  实现（单仓单写者）
4.  验证：§七 相关行 + 站点 curl/title/cert
5.  commit + push；deploy 镜像同步（若改 private 源）
6.  PROGRESS_SITES.md 一行
7.  update_goal(message=…)
```

卡住 >45 分钟：PROGRESS 记障碍，换下一项；禁止烧 Manus agent 硬闯。

---

## 六、Backlog（按 ROI · 做到极致）

### SX0 — 全站可靠性极致（先做）

| ID | 项 | 验收 |
|----|----|------|
| SX0-1 | `sites_extreme_verify.py` 覆盖全部生产域 + onrender 备用 | 脚本 PASS |
| SX0-2 | 证书/域名矩阵写入 `docs/SITES_LIVE.md` | 表与实测一致 |
| SX0-3 | 各静态站：无 `undefined/app-auth`、无 analytics 占位 404 | bundle grep + 控制台无红 |
| SX0-4 | Cache：html no-cache，带 hash 的 assets long-cache | 响应头抽查 |
| SX0-5 | Render 冷启动：关键页首屏 skeleton/文案「服务唤醒中」 | 文案或 loading 存在 |
| SX0-6 | 安全头：至少 nosniff + 合理 referrer（GH/Render 能力内） | 抽查 |

### SX1 — QuantRadar 极致（有后端 · 补强）

| ID | 项 | 验收 |
|----|----|------|
| SX1-1 | 与 `GROK_GOAL.md` 对齐：本周最高 ROI 的 1 个 QR-ID | 该 QR 验收 |
| SX1-2 | health 字段与 LIVE 文档一致 | curl 对照 |
| SX1-3 | 假 ticker / oauth 410 / disclaimer 持续绿 | cutover_verify 或等价 |
| SX1-4 | charts 可达性或诚实 `charts_reachable` 产品解释 | UI/API 一致 |
| SX1-5 | 性能：首屏关键 CSS/JS 预算文档化 | 数字写入 SITES_LIVE |

### SX2 — MoYu 轻后端极致（可选产品）

| ID | 项 | 验收 |
|----|----|------|
| SX2-0 | 决策记录：静态极致 vs 轻后端（写 `docs/MOYU_BACKEND_DECISION.md`） | 文件存在 |
| SX2-1 | **路径 A 静态极致**：本地抽签 + fallback 金句全前端；禁用/隐藏死登录 | 无 crash；可抽签 |
| SX2-2 | **路径 B 轻后端**：Node/Python + SQLite/Turso 存 history；排行榜只读 | 抽签 API 200 |
| SX2-3 | Stripe/会员：仅授权后做 | — |
| SX2-4 | AI 金句：有 key 才调；失败 fallback | source 字段 |

**默认推荐**：先 **SX2-1 做到极致**，再决定是否 SX2-2。

### SX3 — Fortune 最小可产品后端

| ID | 项 | 验收 |
|----|----|------|
| SX3-0 | 产品切片：只做「访客免费塔罗 1 牌阵」MVP | 文档 1 页 |
| SX3-1 | API：`POST /api/tarot/preview` → 结构化 JSON + 免责声明 | curl 契约 |
| SX3-2 | 限流 + 无 key 时规则牌义（不装 AI） | 429 / fallback |
| SX3-3 | 前端接真 API；失败空态 | 无白屏 |
| SX3-4 | 部署：Render Web + env；域已在 fortunesite | health 200 |
| SX3-5 | （授权后）LLM 润色牌义 | A/B 开关 |
| SX3-6 | （授权后）Stripe 会员 | webhook 测试 |

### SX4 — Drama 演示极致 / 全量隔离

| ID | 项 | 验收 |
|----|----|------|
| SX4-1 | 静态门闸：生成按钮 → modal「需后端/积分」；禁止假进度条跑满 | UI 审查 |
| SX4-2 | 已修 OAuth URL 回归：bundle 无 `undefined/app-auth` | grep |
| SX4-3 | 演示数据：1 个假项目只读展示分镜（fixture） | 可点开 |
| SX4-4 | **全量生成后端**（Kling/积分/Stripe）→ 独立子 goal，需付费授权 | 默认不做 |
| SX4-5 | onrender 与 GH Pages 双端版本号一致 | version.json 或 commit sha |

### SX5 — 个人站极致

| ID | 项 | 验收 |
|----|----|------|
| SX5-1 | 全链接可点；外链 `rel` 合理 | 爬链 |
| SX5-2 | OG/SEO/favicon 齐全 | 源码检查 |
| SX5-3 | 性能：压缩字体/图片；Lighthouse 记录 | 分数入档 |
| SX5-4 | 设计：走 design-taste 一轮，去 AI 味 | 前后截图 |

### SX6 — 工程与成本极致

| ID | 项 | 验收 |
|----|----|------|
| SX6-1 | `docs/SITES_COST.md`：各 Free 服务风险与 suspend 策略 | 文件 |
| SX6-2 | 每 deploy 仓 README：如何 rebuild / 推 gh-pages | 文件 |
| SX6-3 | 统一 `scripts/rebuild_static.sh <product>` | 一键 |
| SX6-4 | 密钥清单 `.env.example` 分产品 | 文件 |
| SX6-5 | 监控：日一次 verify 可用 cron 文档（可选 launchd） | 文档 |

---

## 七、验收矩阵

### 7.1 一键脚本（必须维护）

```bash
python3 ~/quantradar/scripts/sites_extreme_verify.py
# 期望：生产域 HTTPS 200 + title 关键字 + cert CN 匹配（或 document SAN）
```

### 7.2 手工红线

| 检查 | 命令/动作 |
|------|-----------|
| 无 Manus 登录泄漏 | 页面源码无 `manus.im/app-auth`（QR 已 410） |
| 无 undefined URL | `curl -sS <js> \| grep undefined/app-auth` 为空 |
| QR health | `curl -sS https://quantradar.one/health \| jq .manus_login` → false |
| Drama 静态诚实 | 生成流程不出现「100% 完成」假状态（除非真有任务 ID） |

### 7.3 每轮最低交付

- 1 个 SITE-ID 完成 + 脚本相关断言绿  
- PROGRESS 一行  
- 可回滚的 git commit  

---

## 八、优先级规则（取 backlog 时）

1. **红灯先灭**：HTTPS/白屏/安全 > 新功能  
2. **诚实 > 华丽**：降级文案优于假成功  
3. **QR 数据 / 全站可靠** 先于 Fortune/Drama 重后端  
4. **同一时间只深做一个重后端**（Fortune 或 Drama）  
5. 用户当轮点名的站 **插队**  

默认序：

```text
SX0 → SX1(与 QR goal 协同) → SX2-1 → SX5 → SX4-1/2/3 → SX3-0… → SX6
```

---

## 九、进度文件

| 文件 | 用途 |
|------|------|
| `~/quantradar/PROGRESS_SITES.md` | 每轮一行：SITE-ID / 结果 / 遗留 |
| `~/quantradar/docs/SITES_LIVE.md` | 域名·证书·形态 活表（SX0-2 建） |
| `~/quantradar/docs/SITES_COST.md` | 成本与 Free 配额（SX6-1 建） |

---

## 十、完成定义

当 **S1–S12 全满足** 且用户未提出新站时：

```
update_goal(completed=true, message="SITES EXTREME 收官：全站可靠+诚实降级+QR/可选轻后端边界清晰")
```

未授权的付费重后端不阻塞收官；在 PROGRESS 标 `DEFERRED: Drama full / Fortune Stripe`。

---

## 十一、与单站 goal 关系

| Goal | 关系 |
|------|------|
| `GROK_GOAL.md`（QR 极致） | **并行**；QR 深度优化优先跟 QR goal，本文件只做多站协同与 SX1 对齐 |
| stock-skills 各 GROK_GOAL_* | **无关**（交易管线） |
| 本文件 | **多站产品表面** 的唯一总控 |

---

## 十二、第一轮建议（开箱即做）

1. **SX0-1** 落地/硬化 `sites_extreme_verify.py`  
2. **SX0-3** 扫描全部 GH 静态 bundle 的 OAuth/analytics 坑  
3. **SX2-1 或 SX4-1** 二选一：MoYu 纯前端可抽签 **或** Drama 诚实门闸  
4. 写 `PROGRESS_SITES.md` 起盘  

---

*End of GROK_GOAL_SITES_EXTREME.md*
