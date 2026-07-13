# SITES_COST — Free 栈成本与 suspend 策略

> 任务源：`GROK_GOAL_SITES_EXTREME.md` · SX6-1  
> 更新：2026-07-13

## 原则

- **默认零算力账单**：GH Pages 静态 + Render Free。
- **Hobby 自定义域 ≤2 组**（当前：`quantradar.one` + `fortunesite.one` 系）。新域优先 GH Pages / 子域，不新开 Hobby。
- **零 Manus agent 积分**修站；DNS 可点 UI。
- 付费 API（LLM / Kling / Stripe 超量）**仅当轮书面授权**。

## 服务矩阵

| 服务 | 计划 | 生产角色 | 空闲/限额风险 | Suspend 策略 |
|------|------|----------|---------------|--------------|
| Render `quantradar-shell` | Free | QR 生产（含自定义域） | ~15min 休眠；冷启动 ~1min | **永不 suspend**；域名占用 Hobby 名额 |
| Render `fortune-insight` | Free | Fortune 生产 + SX3 API | 同上；Web 进程内存 | **永不 suspend**；第二组 Hobby 域 |
| Render `moyu-fortune` | Free | MoYu **备用** | 休眠；生产走 GH | 可 suspend；主路径 `chillworks.ai` GH |
| Render `rongjian-portfolio` | Free | Portfolio **备用** | 休眠；生产走 GH | 可 suspend；主路径 `rj.fortunesite.one` GH |
| Render `ai-drama-studio` | Free | Drama **备用** | 休眠；生产走 GH | 可 suspend；主路径 `shorts.fortunesite.one` GH |
| GH Pages（MoYu / Portfolio / Drama） | 免费 | 生产静态 | 软配额；无算力费 | 无需 suspend |
| GH Pages / Render 镜像仓 | 免费 | 公共 `*-deploy` | — | 私有源码在 private 仓 |

## 成本面板（当前月预期）

| 项 | 预期 USD |
|----|----------|
| Render Free 五服务 | $0（超限才账单） |
| GitHub Pages | $0 |
| Manus agent | **$0 目标**（禁止开 agent 修站） |
| LLM / 视频 API | $0 除非授权 |
| 域名续费（quantradar / fortunesite / chillworks） | 按注册商（非 Render） |

## Free 踩坑清单

1. **冷启动**：QR / Fortune 首请求可能 >30s；UI 需「服务唤醒中」文案（SX0-5）。
2. **Hobby 域名槽**：已满；不要给备用服务绑新自定义域。
3. **静态 deploy 的 `dist/index.js`**：必须是**零依赖** `node:http` 静态服（见 `scripts/static_host_index.js`）。勿用源仓 express `esbuild` 产物覆盖，否则 Render `update_failed`。
4. **`.gitignore` 的 `dist/`**：deploy 仓若 ignore `dist/`，新资产需 `git add -f` 或取消 ignore（portfolio 已改）。
5. **证书**：Let's Encrypt 经 Cloudflare/GH；错配 `*.github.io` 时先查 CNAME。

## 应急

| 症状 | 动作 |
|------|------|
| 自定义域 5xx + onrender 绿 | 查 DNS / 证书；勿烧 Manus |
| Render update_failed | 查 `dist/index.js` 是否缺依赖；`render deploys list <srv>` |
| GH 仍旧包 | 等 CDN；`?v=` 或查 `version.json` |
| 全站红 | `python3 ~/quantradar/scripts/sites_extreme_verify.py` |

## 相关

- 活表：`docs/SITES_LIVE.md`
- 一键重建：`scripts/rebuild_static.sh`
- 日检：`docs/SITES_MONITOR.md`
