# 自部署（不用 Manus）

> 2026-07-26 锁定。QuantRadar **不再依赖 Manus** 发布或运行时。  
> 代码 SSOT = GitHub `main` · 线上 = Render（或任意 Python 主机）· 域名 = 你的 DNS。

## 原则

| 做 | 不做 |
|----|------|
| 本机打磨 → commit → `git push` → Render 自动/手动部署 | Manus pull / Manus agent / Manus 当 Python 运行时 |
| DNS 指向 Render | 域名继续挂 Manus 旧 SPA |
| `/health` 验收 `service=quantradar-shell` | 用 Manus App Auth |

## 密钥与引擎隔离（防复刻 · 运维）

| 做 | 不做 |
|----|------|
| `CHARTS_DIR` 仅在主机环境变量指向私有引擎树 | 把 `~/charts` 源码并进公开 quantradar 仓 |
| 行情 API 密钥只放 charts 主机 / Render Secret | 把密钥写进前端或公开 `.env` 提交 |
| 公开仓可含 fixtures（接受 demo 可被抄） | 指望混淆 HTML 挡住 LLM 复刻 UI |

详情：[`CLONE_DEFENSE.md`](./CLONE_DEFENSE.md)。

## 部署前：本机打磨到最佳

```bash
cd ~/quantradar
python3 scripts/local_polish_check.py
# 浏览器打开：
#   http://127.0.0.1:8765/
#   http://127.0.0.1:8765/?demo=INTC
#   http://127.0.0.1:8765/pricing
#   http://127.0.0.1:8765/r/INTC
```

验收标准见 `docs/FULL_FUNNEL_DESIGN.md` §10 + `docs/LOCAL_POLISH.md`。

## Render（推荐）

仓库已有 [`render.yaml`](../render.yaml)：

1. [Render Dashboard](https://dashboard.render.com) → **New** → **Blueprint** → 连 `Alexaliao001/quantradar`
2. 确认 Free / start `python -m app` / `SESSION_SECRET` 自动生成
3. 生产密钥（Dashboard → Environment，勿入库）：
   - `PUBLIC_BASE_URL=https://quantradar.one`
   - `SESSION_SECRET`（Blueprint `generateValue`；**禁止**缺省回退）
   - `QUANTRADAR_BOOTSTRAP_DEMO=0`（禁止默认 `admin@local.test`）
   - `QUANTRADAR_STRIPE_SECRET_KEY` + `STRIPE_PRICE_ID_MONTHLY` / `YEARLY` + `STRIPE_WEBHOOK_SECRET`（收款时）
   - 可选：`GOOGLE_*`、`SMTP_*`（magic link 在公网主机**必须**配 SMTP，否则拒发）
4. Deploy 成功 → 记下 `*.onrender.com`

### 易失磁盘（必读）

Render Free **没有持久盘**。`data/users.json`、waitlist、funnel 会在 redeploy / 休眠后清空。

| 现状 | 含义 |
|------|------|
| Plan SSOT = users 文件 | cookie 里的 `plan=pro` **不再**提权 |
| `storage_durable` in `/health` | 默认 `false`；接上持久卷/外部 DB 后设 `QUANTRADAR_STORAGE_DURABLE=1` |
| 自动部署 | GitHub→Render webhook 历史上常失效；push 后需确认 deploy 或手动 Trigger |

要收真钱 / 留真账号：加 **Render Disk** 或 Postgres，再标 `QUANTRADAR_STORAGE_DURABLE=1`。
5. **Custom Domain** → `quantradar.one` + `www`
6. **DNS**（GlobalDomain / Cloudflare）：按 Render 给的 CNAME/A 改
7. **解绑 Manus** 对 `quantradar.one` 的旧发布（若仍绑着）——只需控制台点一下，**不开 agent**

### 验收

```bash
curl -sS https://quantradar.one/health
# service=quantradar-shell · manus_login=false · git_sha 对齐 push 后的 main

python3 scripts/p0_smoke.py --live
```

## Fly.io（备选）

见 [`DEPLOY.md`](./DEPLOY.md) Fly 小节。同样：**不经 Manus**。

## 与本机差异（诚实）

| | 本机（你打磨时） | Render Free 生产 |
|--|------------------|------------------|
| `charts_status` | 常为 `mounted`（有 `~/charts`） | 多为 `artifact_only` |
| Pro 文案 | 可 `live_ready` | 通常 `supporter_until_mount` |
| Demo 图 | `fixtures/.../assets` + charts | 仅镜像内 `fixtures`（已含 INTC 日线两图） |

生产未 mount 时 **不要** 卖「付费即 live」——产品已按 `PRO_VALUE` 诚实降级。

## 相关

- 设计 SSOT：[`FULL_FUNNEL_DESIGN.md`](./FULL_FUNNEL_DESIGN.md)
- 本机清单：[`LOCAL_POLISH.md`](./LOCAL_POLISH.md)
- 旧总览：[`DEPLOY.md`](./DEPLOY.md)（Render/Fly 细节仍有效；忽略 Manus publish）
