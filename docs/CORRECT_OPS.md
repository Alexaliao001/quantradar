# 最正确操作方法（锁定）

> 2026-07-12 定版。之后部署/改版只认本文件，避免 Manus / 仓库 / 线上三套混谈。

## 1. 唯一权威源（SSOT）

| 项 | 值 |
|----|-----|
| 代码 | `https://github.com/Alexaliao001/quantradar` **main** |
| 当前基线 | `d8132cc` · **v0.6.0**（path-C 壳 + 邮箱密码登录 + Trust Gate） |
| 引擎 | `~/charts`（stock-charts），壳**不算**分、不抄 generate_charts |
| **不是**权威 | Manus 任务里的旧 SPA、Manus 独有 diff、trycloudflare 临时隧道 |

```text
写代码 → 只改 GitHub/本机仓库 → commit + push
跑线上 → 从 GitHub pull 部署到「能跑 Python 的主机」
域名   → 在 DNS 注册商改指向（NS 当前在 GlobalDomain）
```

## 2. 明确：线上 ≠ 仓库

| 表面 | 是什么 | 是否最新仓库 |
|------|--------|--------------|
| GitHub main | Grok 建设的 path-C 壳 | ✅ 是 |
| `127.0.0.1:8765` | 本地 `python -m app` | ✅ 应与仓库一致 |
| `quantradar.one` | Manus 旧 SPA（tRPC / app-auth / 假统计） | ❌ **不是** |

验收是否 cutover 成功，只看：

```bash
curl -sS https://quantradar.one/health
# 必须： "service":"quantradar-shell" 且 "manus_login":false
# 且 version/git_sha 对齐 GitHub main
```

## 3. 最正确部署路径（默认走这条）

**不要用 Manus 当应用运行时。** Manus 不适合长期跑 path-C Python 壳；且烧 Lite/Max 额度、易分叉。

### 推荐顺序

```text
① GitHub main 干净可 pull
② 部署到 Render Free（或任意 Docker/Python 主机）
   start: python -m app
   env: 见下
③ 在 GlobalDomain 改 DNS → 指向该主机
④ 停掉 Manus 对 quantradar.one 的旧发布（若仍绑着）
⑤ curl 验收 + TRUST_GATE
```

### 环境变量（生产）

```bash
HOST=0.0.0.0
# PORT 由平台注入
QUANTRADAR_MODE=artifact
PUBLIC_BASE_URL=https://quantradar.one
SESSION_SECRET=<随机长串>
QUANTRADAR_BOOTSTRAP_DEMO=0   # 生产关掉 demo 管理员
QUANTRADAR_DEV_LOGIN=0
# 可选：ALLOW_REGISTER=1
# 以后再加：GOOGLE_*、STRIPE、SMTP
```

### 本机对照（开发）

```bash
cd ~/quantradar
git pull
python3 -m app
# http://127.0.0.1:8765/login  — 邮箱密码
```

### 临时公网预览（可选，非生产）

```bash
cloudflared tunnel --url http://127.0.0.1:8765
```

仅用于验收，**不要**写死进 DNS。

## 4. Manus 的正确角色（尽量少用）

| 做 | 不做 |
|----|------|
| 若域名仍挂在 Manus：在设置里**解绑/停发**旧 SPA | 不在 Manus 里当 SSOT 改业务代码 |
| 需要时 **Lite 一句**：停旧站 / 查域名绑定 | 不用 Max 长任务重构部署 |
| | 不搞 wrangler / Worker 硬扛 Python |
| | 不接 Manus app-auth |

## 5. 认证策略（产品）

1. **现在**：自建邮箱+密码（`/login`，`data/users.json`）  
2. **以后**：再加 Google OAuth（env 配齐即显示）  
3. **永远不要**：`manus.im/app-auth`

## 6. 禁止事项

- 把 Manus 任务输出当成仓库真相  
- 在 Manus 大改却不 push 回 GitHub  
- 未改 DNS 就宣称「已发布到 quantradar.one」  
- 同时维护 tRPC SPA 与 path-C 两套公式  

## 7. Cutover 完成检查单

- [ ] `git -C ~/quantradar log -1` 与 origin/main 一致  
- [ ] 托管进程 `python -m app`，health = `quantradar-shell`  
- [ ] `quantradar.one/health` 同上 + `git_sha` 对齐  
- [ ] `/login` 邮箱密码可用；`/api/oauth/*` = 410  
- [ ] 无假 1247/896；单 `primary_score`；demo 不计费  
- [ ] `docs/TRUST_GATE.md` 项通过  
