# Cutover status

权威：**[DECISION.md](./DECISION.md)** + **[CORRECT_OPS.md](./CORRECT_OPS.md)**。

| 表面 | 状态 |
|------|------|
| GitHub main | ✅ path-C 壳 v0.6.0+（P0 / Trust / 密码登录） |
| 本地 `python -m app` + tests | ✅ PASS |
| `quantradar.one` | ❌ 仍是 Manus 旧 SPA（`service=quantradar`） |
| Render / DNS | ⏳ 等你点 Blueprint + GlobalDomain |

**决断**：不修 Manus SPA；Render 跑壳 → 改 DNS → 解绑 Manus。

```bash
# 部署完成后验收
bash scripts/cutover_verify.sh https://quantradar.one
```
