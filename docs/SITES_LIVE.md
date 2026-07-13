# SITES_LIVE — 生产域实测矩阵

> 任务源：`GROK_GOAL_SITES_EXTREME.md` · SX0  
> 验收脚本：`python3 scripts/sites_extreme_verify.py`  
> 本表更新：**2026-07-13T06:58Z**（与同日 `sites_extreme_verify` **RESULT: PASS** 对齐）

## 总览

| 站 | 生产 URL | 托管 | 形态 | HTTP | Cert CN | 备注 |
|----|----------|------|------|------|---------|------|
| QuantRadar | https://quantradar.one | Render Free `quantradar-shell` | path-C 壳 | 200 | `quantradar.one` | `/health` 绿；`manus_login:false` |
| Fortune | https://fortunesite.one | Render + 自定义域 | 静态 SPA | 200 | `fortunesite.one` | Hobby 自定义域组之一 |
| Fortune www | https://www.fortunesite.one | 同上 | 301→apex | 301→200 | `www.fortunesite.one` | 跳转到 apex |
| MoYu | https://chillworks.ai | GitHub Pages | 静态 SPA | 200 | `chillworks.ai` | 无 Render 自定义域占用 |
| Portfolio | https://rj.fortunesite.one | GitHub Pages | 静态 SPA | 200 | `rj.fortunesite.one` | 子域 GH Pages |
| Drama | https://shorts.fortunesite.one | GitHub Pages | 静态 SPA | 200 | `shorts.fortunesite.one` | bundle 无 `undefined/app-auth` |

### onrender 备用（optional · 脚本 soft）

| URL | 角色 |
|-----|------|
| https://quantradar-shell.onrender.com | QR 直连（与自定义域同 app） |
| https://fortune-insight.onrender.com | Fortune 直连 |
| https://moyu-fortune.onrender.com | MoYu 备用（生产主路径为 chillworks GH） |
| https://rongjian-portfolio.onrender.com | Portfolio 备用 |
| https://ai-drama-studio.onrender.com | Drama 备用 |

## QuantRadar health（实测）

```json
{
  "ok": true,
  "service": "quantradar-shell",
  "version": "0.6.0",
  "contract_version": "1.0.0",
  "git_sha": "78e40e3",
  "charts_reachable": false,
  "mode_default": "artifact",
  "manus_login": false,
  "guest_access": true,
  "login_path": "/login",
  "p0_gates": true
}
```

- `charts_reachable=false` 在 **artifact 模式**下为预期（fixtures），非宕机。
- Free 空闲约 15 分钟休眠；冷启动约 1 分钟。

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
