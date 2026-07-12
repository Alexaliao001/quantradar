# Manus 同步与发布（用户操作）

**架构路径 C**：GitHub `quantradar` = 产品壳；分析核在 `~/charts`。  
**Auth 铁律**：发布后的 `quantradar.one` **不得** 再走 `manus.im/app-auth`。见 [AUTH.md](./AUTH.md)。

## 积分铁律（强制 · 2026-07-12 用户确认）

**Manus 积分必须尽量少花。能不用就不用；能用 lite 就用 lite；主要用途是部署才用。**

| 优先 | 做法 |
|------|------|
| ✅ | 本机 / GitHub 改代码 → `git push` → Manus **只 Pull/Sync + Publish**（部署通道，尽量不跑 agent） |
| ✅ | 排障用本机 curl / 本地 `python -m app` |
| ✅ | 若必须开 Manus agent：**优先 lite / 最便宜模型**，prompt 压到最短，单任务 |
| ❌ | 默认 `tasks create` 让 Manus 修 bug / 写功能 / 探索（烧积分） |
| ❌ | 重复轮询、并行 task、满血 agent 做本机可做的事 |

**默认策略**：开发与修 bug **全在本机**；Manus = **部署/发布**，不是开发环境。

## 发布步骤

1. 打开 Manus 中 QuantRadar **工作区 / 同步**（仅作 Git 同步与构建，**不是**用户登录产品）  
2. **Pull / Sync** 自 `https://github.com/Alexaliao001/quantradar`  
3. 确认 `git_sha` 与 GitHub `main` 一致（`/health` 字段）  
4. **关闭 Manus App Auth / 强制登录**（设置名因 UI 而异：App Auth、Require sign-in、Platform login 等）  
5. 若 Manus 只能以「带平台登录的托管 App」发布：改用 **静态/自托管** 跑本仓壳，或换部署目标，**不要**再绑 `appId` OAuth  
6. **Publish / Deploy** 到 `quantradar.one`  
7. 烟雾（**全部应无跳转 manus.im**）：
   - 打开 `https://quantradar.one/` → 直接见分析 UI  
   - `https://quantradar.one/health` → `"manus_login": false`  
   - `https://quantradar.one/api/analyze?ticker=INTC` → JSON 门控/分  
   - `https://quantradar.one/api/oauth/callback` → **410**（不是 Manus 登录页）  
   - 浏览器 Network 中 **无** `manus.im/app-auth`

## 禁止

- 在 Manus 里做大改却不 push 回 GitHub  
- 未 pull 最新 main 就发布  
- **把产品登录接到 `manus.im/app-auth`**  
- 营销 CTA 指向 Manus space 登录 URL（历史错误，已废止）  

## 回滚

GitHub 上 `git revert` 或回退 tag → push → 再 sync 发布。

## 本机对照（无 Manus）

```bash
cd ~/quantradar
QUANTRADAR_MODE=artifact PORT=8765 python3 -m app
# 浏览器只开 http://127.0.0.1:8765/  — 无 Manus 登录
```
