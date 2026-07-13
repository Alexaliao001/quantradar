# PROGRESS_SITES — 多站点极致 goal 日志

> 任务源：`GROK_GOAL_SITES_EXTREME.md`  
> 规则：每轮 **≤3 非空行** 摘要；细节可链到 commit。

| 日期 | SITE-ID | 结果 | 遗留 |
|------|---------|------|------|
| 2026-07-13 | SX5 | 个人站极致：favicon/OG/sitemap；外链 noopener；IBM Plex+JetBrains 自托管；`build:static` 去 Manus runtime；LH mobile Perf 67（瓶颈记清）；源 `a3b1789` · gh-pages `dd12706` · deploy-main `0616120`；sites PASS | onrender 备用可能滞后于 GH；≥90 需更深 SPA 拆包；下一 SX6 |
| 2026-07-13 | SX4 | Drama 演示层：生成门闸 modal；`/demo` 只读分镜；无 `undefined/app-auth`；`version.json` SX4；gh-pages+onrender 对齐；sites PASS | 全量生成（SX4-4）默认不做；GH `/demo` 可能 404 状态但 SPA shell；下一 SX5/SX6 |
| 2026-07-13 | SX3 | Fortune 访客塔罗 MVP：`POST /api/tarot/preview` rules+限流；`/health`；`/free-tarot`；deploy `2a1a331` fortunesite 绿 | SPA 整站 trpc 仍静态；LLM/Stripe 需授权 |
| 2026-07-13 | SX2 | MoYu 路径 A：`MOYU_BACKEND_DECISION`；本地抽签/金句/历史；禁死 OAuth；gh-pages+CNAME 上线 `index-0EAWDXlc` 无 `undefined/app-auth`；sites_extreme PASS | SX2-2 轻后端默认不做 |
| 2026-07-13 | SX1 | QR v0.7 数据层诚实：health `charts_status`/`data_path`/`product_note`；artifact options 非 actionable；路径脱敏；UI 数据路径条；SITES_LIVE 预算；unittest + cutover 绿 | 已上线 v0.7 |
| 2026-07-13 | SX0 | 全站 `sites_extreme_verify` PASS；`docs/SITES_LIVE.md`；drama bundle 无 `undefined/app-auth`；verify retry/TLS flake 硬化 + unit tests | SX0-4/6 更深 headers 可后续 |
| 2026-07-13 | — | goal 文件创建；五域已迁出 Manus；QR 有壳其余静态 | （已由 SX0 行承接） |
