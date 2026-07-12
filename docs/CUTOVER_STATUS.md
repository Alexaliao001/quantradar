# Cutover status

权威操作法见 **[CORRECT_OPS.md](./CORRECT_OPS.md)**（已锁定）。

| 表面 | 状态 |
|------|------|
| GitHub main | ✅ v0.6.0 `d8132cc` path-C + 密码登录 + Trust Gate |
| 本地 `python -m app` | 开发验收用 |
| `quantradar.one` | ❌ 仍是 Manus 旧 SPA，**不是**仓库最新版 |

**下一步（唯一推荐）**：Render（或等价 Python 主机）从 GitHub 部署 → GlobalDomain 改 DNS → 停 Manus 旧发布。  
**不推荐**：继续用 Manus Max/Lite 当运行时或 Worker 反代硬扛。
