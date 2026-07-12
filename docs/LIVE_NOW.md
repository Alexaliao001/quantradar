# Live now

## Render Free (已完成 · $0)

| | |
|--|--|
| App | https://quantradar-shell.onrender.com |
| Plan | **free** |
| Service | `srv-d99nc357vvec73frpus0` |
| Custom domains on Render | `quantradar.one` + `www.quantradar.one` (**已添加**，等 DNS 验证) |
| Verify app | `bash scripts/cutover_verify.sh https://quantradar-shell.onrender.com` → **PASS** |

## DNS（最后一步 · 代理无法代改 GlobalDomain/Manus）

当前权威 DNS（NS = globaldomaingroup.com）仍指向 **Manus**：

```
quantradar.one  →  cname.manus.space / CF 104.18.x
```

请在 **GlobalDomain DNS** 或 **Manus 已购域名管理** 改成：

### 推荐（子域最稳）

| Type | Name | Target |
|------|------|--------|
| **CNAME** | `www` | `quantradar-shell.onrender.com` |
| **CNAME** 或 **ALIAS/ANAME** | `@`（根） | `quantradar-shell.onrender.com` |

若注册商 **根域名不支持 CNAME**，用 Render 面板 Custom Domains 里显示的 **A 记录**（以面板为准，常见为 Render 负载 IP）。

改完后执行：

```bash
python3 scripts/dns_cutover_wait.py
# 或
bash scripts/cutover_verify.sh https://quantradar.one
```

成功标准：`curl -s https://quantradar.one/health` 含 `"service":"quantradar-shell"`。

## Manus

域名切走后，在 Manus 停止该域名的旧 SPA 发布（不解绑也可，只是 DNS 不再指向它）。**不要开 agent 烧积分。**
