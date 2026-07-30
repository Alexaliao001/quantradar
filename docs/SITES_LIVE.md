# SITES_LIVE — 生产域实测矩阵

> 任务源：`GROK_GOAL_SITES_EXTREME.md` · SX0  
> 验收脚本：`python3 scripts/sites_extreme_verify.py`  
> 本表更新：**2026-07-13T06:58Z**（与同日 `sites_extreme_verify` **RESULT: PASS** 对齐）

## 总览

| 站 | 生产 URL | 托管 | 形态 | HTTP | Cert CN | 备注 |
|----|----------|------|------|------|---------|------|
| QuantRadar | https://quantradar.one | Render Free `quantradar-shell` | path-C 壳 | 200 | `quantradar.one` | `/health` 绿；`manus_login:false` |
| Fortune | https://fortunesite.one | Render Free `fortune-insight` | SPA + **SX3 最小 API** | 200 | `fortunesite.one` | `/health` · `/api/tarot/preview` · `/free-tarot` |
| Fortune www | https://www.fortunesite.one | 同上 | 301→apex | 301→200 | `www.fortunesite.one` | 跳转到 apex |
| MoYu | https://chillworks.ai | GitHub Pages | 静态 SPA · 路径 A | 200 | `chillworks.ai` | SX2：本机抽签/历史；bundle 无 `undefined/app-auth`；`version.json` mode=static |
| Portfolio | https://rj.fortunesite.one | GitHub Pages | 静态 SPA · **SX5** | 200 | `rj.fortunesite.one` | SEO/favicon/self-host fonts；`build:static`；LH mobile Perf **67**（瓶颈见 `~/rongjian-portfolio/docs/SX5_PORTFOLIO.md`） |
| Drama | https://shorts.fortunesite.one | GitHub Pages | 静态演示层 SX4 | 200 | `shorts.fortunesite.one` | `/demo` 只读分镜；生成门闸；`version.json`；无 `undefined/app-auth` |

### onrender 备用（optional · 脚本 soft）

| URL | 角色 |
|-----|------|
| https://quantradar-shell.onrender.com | QR 直连（与自定义域同 app） |
| https://fortune-insight.onrender.com | Fortune 直连 |
| https://moyu-fortune.onrender.com | MoYu 备用（生产主路径为 chillworks GH） |
| https://rongjian-portfolio.onrender.com | Portfolio 备用 |
| https://ai-drama-studio.onrender.com | Drama 备用 |

## QuantRadar health（实测）

### SX0 基线（v0.6 · 部署前）

```json
{
  "ok": true,
  "service": "quantradar-shell",
  "version": "0.6.0",
  "charts_reachable": false,
  "mode_default": "artifact",
  "manus_login": false,
  "p0_gates": true
}
```

### SX1 数据层字段（v0.7+ · 目标契约）

| 字段 | 含义 |
|------|------|
| `charts_reachable` | `CHARTS_DIR` 是否为目录 |
| `fetch_all_present` | 是否可 subprocess live |
| `charts_status` | `mounted` \| `artifact_only` \| `unavailable` |
| `data_path` | `charts_engine` \| `artifact_fixtures` \| `none` |
| `charts_dir` | 恒为 `null`（不暴露主机路径）；用 `charts_dir_configured` |
| `artifact_fixtures` | 仓内 fixture ticker 列表（如 `["INTC"]`） |
| `product_note` | 人话解释：Free 上 `charts_reachable=false` 不等于宕机 |

Render Free 预期：`charts_status=artifact_only`，`data_path=artifact_fixtures`，guest `GET /api/analyze?ticker=INTC` → `ok=true`，`meta.mode=artifact`，`options.option_data_source=artifact_snapshot`（**非 live actionable**）。

- Free 空闲约 15 分钟休眠；冷启动约 1 分钟。
- UI footer / hero 同步展示 `charts_status` + `product_note`。

### SX1-5 首屏预算（2026-07-13 抽查 · 暖机）

| 资源 | size (bytes) | total time (s) |
|------|---------------|----------------|
| `GET /` HTML | ~18 KB | ~0.6 |
| `/static/site.css` | ~2.3 KB | ~0.5 |
| `/health` | ~0.4–1 KB | ~0.9 |
| `/api/analyze?ticker=INTC` | ~3 KB | ~0.6 |

预算：**首屏关键 HTML+CSS < 30 KB**；分析 JSON 单次 < 20 KB（artifact）。冷启动不计入。

## 证书（openssl s_client · 2026-07-13）

| Host | Subject | notAfter (GMT) |
|------|---------|----------------|
| quantradar.one | `/CN=quantradar.one` | 2026-10-10 |
| fortunesite.one | `/CN=fortunesite.one` | 2026-10-10 |
| www.fortunesite.one | `/CN=www.fortunesite.one` | 2026-10-10 |
| chillworks.ai | `/CN=chillworks.ai` | 2026-10-10 |
| rj.fortunesite.one | `/CN=rj.fortunesite.one` | 2026-10-10 |
| shorts.fortunesite.one | `/CN=shorts.fortunesite.one` | 2026-10-10 |

无 `*.github.io` 错配（GH 自定义域已发对应 CN 证书）。

## Drama bundle（SX0-3）

| 项 | 值 |
|----|-----|
| HTML | https://shorts.fortunesite.one/ |
| 主 JS | `/assets/index-Bodw5v6e.js` |
| `undefined/app-auth` | **absent**（`sites_extreme_verify` → `drama.bundle` PASS） |

## Cache 抽查（SX0-4 · 平台默认）

| 站 | HTML cache 观察 |
|----|-----------------|
| Render（QR / Fortune） | `cf-cache-status: DYNAMIC`（经 Cloudflare 边缘） |
| GH Pages（MoYu / Portfolio / Drama） | `cache-control: max-age=600`（HTML）；hash assets 由 SPA 构建路径决定 |

> 更严的「html no-cache + assets long-cache」若要平台级强制，需在各 deploy 的 `_headers` / Render 静态配置补齐（SX0-4 加深可后续单轮）。

## 安全头抽查（SX0-6 · 平台能力内）

| 站 | 观察 |
|----|------|
| Render + CF | 有 CF/Render 默认栈；未见自定义 `X-Content-Type-Options` 强制（可后续补中间件/headers） |
| GH Pages | 标准 GH/Fastly；`access-control-allow-origin: *` 于静态资源 |

## DNS / Hobby 约束

| 域组 | 路径 | Hobby 自定义域 |
|------|------|----------------|
| `quantradar.one` (+ www) | CNAME → `quantradar-shell.onrender.com` | **占用 1** |
| `fortunesite.one` (+ www) | Render custom | **占用 1** |
| `chillworks.ai` / `rj.*` / `shorts.*` | GH Pages | 不占 Render Hobby 自定义域 |

铁律：Render Hobby **≤2** 自定义域组 — 当前已满；新域优先 GH Pages 或先腾位。

## 复验

```bash
python3 ~/quantradar/scripts/sites_extreme_verify.py
# 期望：RESULT: PASS
```

相关：`LIVE_NOW.md`（QR 单站）· `MULTI_SITE_MIGRATION.md`（迁出底稿）· `PROGRESS_SITES.md`（轮次日志）

## 相关

- 成本：`docs/SITES_COST.md`（SX6）
- 日检：`docs/SITES_MONITOR.md`
- 重建：`scripts/rebuild_static.sh`
