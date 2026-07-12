# Auth policy — 自有邮箱密码登录优先；禁止 Manus

> **铁律**：QuantRadar **不使用** `manus.im/app-auth`。  
> 产品登录是 **本站 `/login`**：**邮箱+密码（默认）**，可选 magic link；**Google 可选、后接**。

## 现行策略（v0.6）

| 能力 | 策略 |
|------|------|
| 访客分析 `/api/analyze`（默认 artifact） | **公开**，无登录 |
| 访客样例 `/api/sample` | **公开** |
| Health `/health` | **公开** |
| Live 分析 `mode=live` | **需登录**（session cookie） |
| 产品登录 | **`/login`** → **邮箱+密码** 注册/登录 |
| Magic link | 可选（无 SMTP 时控制台/文件交付） |
| Google OAuth | 仅当配置 `GOOGLE_CLIENT_*` 时显示 |
| Session | HttpOnly cookie `qr_session`（HMAC 签名） |
| 用户库 | `data/users.json`（PBKDF2-SHA256） |
| Manus OAuth `/api/oauth/*` | **410** |
| Stripe checkout | 登录后 `POST /api/billing/checkout` |

## 自有登录 API

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/auth/register` | `{email,password,name?}` → Set-Cookie |
| POST | `/api/auth/login` | `{email,password}` → Set-Cookie |
| POST | `/api/auth/logout` | 清 cookie |
| GET | `/api/me` | 当前用户 |

## Bootstrap

- 环境变量 `QUANTRADAR_ADMIN_EMAIL` + `QUANTRADAR_ADMIN_PASSWORD`：无用户时创建管理员  
- 或默认 demo（`QUANTRADAR_BOOTSTRAP_DEMO=1`）：`admin@local.test` / `quantradar`（仅无用户时）

## 环境变量

| 变量 | 必需 | 说明 |
|------|------|------|
| `GOOGLE_CLIENT_ID` | 生产登录 | Google Cloud OAuth 客户端 ID |
| `GOOGLE_CLIENT_SECRET` | 生产登录 | 客户端密钥 |
| `SESSION_SECRET` | 生产 | 签名 session 的随机长串（≥32 字节） |
| `PUBLIC_BASE_URL` | 生产 | 如 `https://quantradar.one`（无尾斜杠） |
| `QUANTRADAR_DEV_LOGIN` | 仅本地 | `1` 时允许 `/api/auth/dev-login`（仅 127.0.0.1/localhost） |

未配置 Google 时：访客雷达仍可用；`/login` 显示「未配置」；`/api/auth/google/start` → 503。

## Google Cloud 配置

1. [Google Cloud Console](https://console.cloud.google.com/apis/credentials) → OAuth 2.0 Client ID（Web）
2. Authorized JavaScript origins: `https://quantradar.one`
3. Authorized redirect URIs: **`https://quantradar.one/api/auth/google/callback`**
4. 本地开发可再加：`http://127.0.0.1:8765/api/auth/google/callback`
5. 把 Client ID/Secret 注入运行环境（勿提交 git）

## 路由

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/login` | 自有登录页 |
| GET | `/api/auth/status` | 是否已登录 + 是否配置 Google |
| GET | `/api/me` | 当前用户（需 cookie） |
| GET | `/api/auth/google/start` | 302 → Google |
| GET | `/api/auth/google/callback` | OAuth code 换 session |
| GET/POST | `/api/auth/logout` | 清 cookie |
| GET | `/api/auth/dev-login` | 仅本地 dev |
| GET | `/api/oauth/*` | **410 Manus 禁用** |

## 为何线上还会看到 Manus 登录

域名若仍挂 **Manus 托管旧 SPA + App Auth**，会跳 `manus.im/app-auth`。  
必须按 [MANUS_SYNC.md](./MANUS_SYNC.md) 发布本仓壳并关闭平台 Auth。

## 验收

```bash
python3 -m app
curl -sS http://127.0.0.1:8765/health | grep manus_login   # false
curl -sS -o /dev/null -w "%{http_code}\n" http://127.0.0.1:8765/api/oauth/callback  # 410
curl -sS -o /dev/null -w "%{http_code}\n" http://127.0.0.1:8765/login  # 200
curl -sS -o /dev/null -w "%{http_code}\n" "http://127.0.0.1:8765/api/analyze?ticker=INTC&mode=live"  # 401
# 页面源码无 manus.im；有 /login 与 Continue with Google
```

本地无 Google 密钥时测 session：

```bash
PUBLIC_BASE_URL=http://127.0.0.1:8765 QUANTRADAR_DEV_LOGIN=1 SESSION_SECRET=devsecret \
  python3 -m app
# 浏览器打开 http://127.0.0.1:8765/api/auth/dev-login
```
