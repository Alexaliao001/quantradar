# Live now (2026-07-13 cutover complete)

## Production

| URL | Service |
|-----|---------|
| **https://quantradar.one** | path-C shell on Render Free |
| **https://www.quantradar.one** | same (verified) |
| https://quantradar-shell.onrender.com | same app (direct) |

```bash
curl -s https://quantradar.one/health
# "service":"quantradar-shell", "manus_login":false, "p0_gates":true

bash scripts/cutover_verify.sh https://quantradar.one
```

## Stack

| 层 | 实现 |
|----|------|
| 代码 | GitHub `Alexaliao001/quantradar` main |
| 托管 | Render Free `quantradar-shell` (`srv-d99nc357vvec73frpus0`) |
| DNS | CNAME `@` + `www` → `quantradar-shell.onrender.com` |
| Auth | 无 Manus App Auth；`/api/oauth/*` → 410；可选自有 `/login` |

## Manus

- 自定义域名已从 Manus 项目解绑
- 旧 SPA 不再服务 quantradar.one
- 域名注册仍可能在 Manus/GDG 账单下（与站点运行分离）

## Notes

- Free 空闲 ~15 分钟休眠，冷启动约 1 分钟
- `charts_reachable=false` 在 artifact 模式正常（用 fixtures）

## 多站点迁出 Manus

另三站（MoYu / Fortune / Portfolio）预览已在 Render Free 就绪。  
完整清单与 **DNS / Manus 解绑步骤** 见 **[MULTI_SITE_MIGRATION.md](./MULTI_SITE_MIGRATION.md)**。

```bash
python3 scripts/multi_site_verify.py
```
