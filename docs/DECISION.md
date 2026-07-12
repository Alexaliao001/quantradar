# 最终决断（2026-07-12 · 锁定）

## 一句话

**停用 Manus 旧 SPA 作为产品运行时；以 GitHub path-C 壳为唯一真相；用 Render（或等价 Python 主机）跑线上；Manus 只负责解绑域名（能不用 agent 就不用）。**

---

## 事实盘点

| 层 | 状态 | 含义 |
|----|------|------|
| 线上 `quantradar.one` | Manus SPA + tRPC | 假 ticker 可 buy、量能映射坏、期权荒谬、BRK.B 500、manus 登录 |
| GitHub `main` | path-C 壳 **v0.6.0** | P0 闸门、Trust Gate、邮箱密码、artifact 分析、unittest **全绿** |
| DNS | NS=`globaldomaingroup.com`；A≈Cloudflare `104.18.26.246` | 域名仍挂在 Manus/Cloudflare 发布链，**不是**本壳 |
| Manus 积分 | 用户铁律：能不用就不用；能 lite 就 lite；**主要部署才用** | 禁止再开 agent 修 bug |
| 本机 | tests + `p0_smoke` PASS | 代码侧已可上线 |

## 否决的方案

| 方案 | 否决原因 |
|------|----------|
| Manus agent 修 tRPC SPA | 烧积分；双轨；与 SSOT 冲突；已误烧 ~511 分 |
| 继续把 Manus 当 Python 运行时 | 不适配 stdlib 壳；易分叉；成本高 |
| 只本机修、不切 DNS | 用户打开 quantradar.one 永远仍是旧 bug |
| 双轨维护 SPA + 壳 | 公式/门控必然漂移 |

## 选定方案（唯一）

```text
本机/GitHub 写代码 (已完成基线)
        │
        ▼
  Render Free Blueprint  ←  python -m app  (render.yaml 已就绪)
        │
        ▼
  GlobalDomain DNS → Render  (CNAME 按面板指示)
        │
        ▼
  Manus：仅解绑/停发 quantradar.one 旧 SPA  (UI 点一下，零 agent)
        │
        ▼
  验收：/health = quantradar-shell + p0_smoke --live PASS
```

### 为什么是 Render 而不是 Fly / Manus

- **Render**：仓库已有 `render.yaml` 原生 Python、Free plan、health path；与历史 charts 部署习惯一致。  
- **Fly**：本机有 `flyctl` 但 **未 login**；备选，不阻塞主路径。  
- **Manus**：只做域名解绑；**不**跑业务进程、**不**开 Max/长任务。

## 代理能做 vs 必须你点一下

| 已由代理完成 / 可完成 | 必须你（账号/DNS） |
|----------------------|-------------------|
| 壳代码 + P0 + 登录 + Trust Gate | Render 账号：New → Blueprint → 连本仓 |
| unittest / p0_smoke 本地 PASS | GlobalDomain：按 Render 改 CNAME/A |
| 文档锁定 + push main | Manus 设置：解绑 quantradar.one 旧发布 |
| 验收脚本 `scripts/cutover_verify.sh` | （可选）Google/Stripe env |

## 成功判据（唯一）

```bash
curl -sS https://quantradar.one/health
# "service":"quantradar-shell"
# "manus_login":false
# "p0_gates":true
# version / git_sha 对齐 GitHub main

python3 scripts/p0_smoke.py --live   # 全部 PASS
# XXXX 不得 buy；oauth → 410；无 manus.im/app-auth
```

在此之前，**禁止**宣称「线上 bug 已修完」——旧 SPA 仍会显示 BUG-1…12。

## 执行顺序（你 15 分钟）

见 [CORRECT_OPS.md](./CORRECT_OPS.md) §3 与 [DEPLOY.md](./DEPLOY.md)。  
最短点击路径：

1. https://dashboard.render.com → **New** → **Blueprint** → `Alexaliao001/quantradar`  
2. 确认 Free / start `python -m app` / `SESSION_SECRET` 自动生成  
3. Deploy 成功 → 记下 `https://quantradar-shell.onrender.com`（名以面板为准）  
4. Render → Custom Domain → `quantradar.one` + `www`  
5. GlobalDomain DNS：按 Render 给的 CNAME 记录改  
6. Manus 域名管理：去掉旧 SPA 绑定（避免争抢）  
7. 等 TLS 绿 → 跑 `p0_smoke.py --live`

---

*本决断取代「在 Manus 里修 SPA」与「等 Manus agent 完成」两条死路。*
