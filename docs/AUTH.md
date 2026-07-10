# Auth policy — 禁止 Manus 登录

> **铁律**：QuantRadar 产品壳 **不使用** `manus.im/app-auth`、不实现 `/api/oauth/callback` 给 Manus、不强制用户用 Manus 账号进入分析。

## 现行策略

| 能力 | 策略 |
|------|------|
| 访客分析 `/api/analyze` | **公开**，无登录 |
| 访客样例 `/api/sample` | **公开**，无登录 |
| Health `/health` | **公开** |
| Manus OAuth / `app-auth` | **禁用**（见下方 410） |
| 未来 desk 账号（若有） | 自有 session / Stripe 客户态，**不得**默认跳转 `manus.im` |

## 为何线上还会看到 Manus 登录

`https://quantradar.one` **当前仍部署着 Manus 平台托管的旧 SPA**（带 `__MANUS_*` 运行时与平台 OAuth），**不是**本仓库 `python -m app` 壳。

只要域名还挂在 **Manus App Auth 项目** 上，点「登录 / 进入应用」就会去：

```text
https://manus.im/app-auth?appId=…&redirectUri=https://quantradar.one/api/oauth/callback…
```

这与 GitHub SSOT 无关；**发布必须换成无 Manus Auth 的构建**（见 [MANUS_SYNC.md](./MANUS_SYNC.md)）。

## 本仓保证

- 源码 **零** `manus.im` / `app-auth` / OAuth client  
- `GET|POST /api/oauth/*`、`/login`（Manus 遗留路径）→ **410** + JSON 说明  
- `/health` 含 `"auth": "none"`, `"manus_login": false`  
- UI 仅访客 Analyze，无「用 Manus 登录」按钮  

## 验收

```bash
python3 -m app   # 本机
curl -sS http://127.0.0.1:8765/health | grep manus_login   # false
curl -sS -o /dev/null -w "%{http_code}" http://127.0.0.1:8765/api/oauth/callback  # 410
# 页面源码无 manus.im
```
