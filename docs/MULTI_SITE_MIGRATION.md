# 多站点迁出 Manus（2026-07-13）

> 原则：**零 Manus agent 积分**；前端预构建静态托管；域名 cutover 你点 DNS + Manus 解绑。

## 总览

| 站点 | 域名 | 托管（已就绪）| 域名 cutover | 说明 |
|------|------|----------------|--------------|------|
| QuantRadar | `quantradar.one` | ✅ Render Free `quantradar-shell` | ✅ **已完成** | path-C 壳 |
| 摸了么 MoYu | `chillworks.ai` | ✅ Render Free `moyu-fortune` | ⏳ 待你改 DNS + 解绑 Manus | Hobby 已挂自定义域名 |
| Fortune Insight | `fortunesite.one` | ✅ Render + ✅ GitHub Pages | ⏳ 待你改 DNS + 解绑 Manus | Render Hobby **域名名额已满**，自定义域走 GH Pages |
| 个人站 Portfolio | （无自有域） | ✅ Render Free `rongjian-portfolio` | — | 直接用 onrender URL |

**不要用** `fortuneinsight.com`（非你的域名）。

---

## 已上线 URL（可立即访问）

| 用途 | URL | HTTP | 内容 |
|------|-----|------|------|
| QuantRadar 生产 | https://quantradar.one | 200 | path-C shell |
| QuantRadar 直连 | https://quantradar-shell.onrender.com | 200 | 同上 |
| MoYu 预览 | https://moyu-fortune.onrender.com | 200 | 摸了么 SPA |
| Fortune 预览 | https://fortune-insight.onrender.com | 200 | Fortune Insight SPA |
| Fortune 静态（GH） | https://alexaliao001.github.io/fortune-insight-deploy/ | 随 CNAME 跳转 | `gh-pages` 全量静态 |
| Portfolio | https://rongjian-portfolio.onrender.com | 200 | 个人站 |

```bash
# 一键探测
for u in \
  https://quantradar.one \
  https://moyu-fortune.onrender.com \
  https://fortune-insight.onrender.com \
  https://rongjian-portfolio.onrender.com
do
  curl -sS -o /dev/null -w "%{http_code}  %{time_total}s  $u\n" --max-time 60 "$u"
done
```

---

## Render 服务清单（Free plan）

| name | service id | URL | 自定义域 |
|------|------------|-----|----------|
| quantradar-shell | `srv-d99nc357vvec73frpus0` | quantradar-shell.onrender.com | `quantradar.one` + `www` ✅ verified |
| moyu-fortune | `srv-d99uh33tqb8s73b79pj0` | moyu-fortune.onrender.com | `chillworks.ai` + `www` ⏳ unverified |
| fortune-insight | `srv-d99uh3m7r5hc73bth4a0` | fortune-insight.onrender.com | 无（Hobby 限 2 组域） |
| rongjian-portfolio | `srv-d99uh4ecjfls738ue8s0` | rongjian-portfolio.onrender.com | 无 |

**Hobby 限制**：整账户约 **2 组**自定义域名（apex+www 算一组）。  
已占用：`quantradar.one` + `chillworks.ai`。  
→ `fortunesite.one` **不能**再挂 Render，改用 **GitHub Pages 免费自定义域**。

**免费时长**：4 个 Free Web Service 空闲约 15 分钟休眠；冷启动 ~30–60s。  
若月度 750 小时紧张，可在 Render Dashboard **Suspend** 暂不用的服务（建议保留 quantradar + 正在 cutover 的那一个）。

---

## 公共 deploy 仓库（Render 可拉）

私有源码仓 Render Free 拉不到 → 用 public mirror：

| 项目 | 源（private） | deploy mirror（public） |
|------|---------------|-------------------------|
| MoYu | `Alexaliao001/moyu-fortune` | `Alexaliao001/moyu-fortune-deploy` |
| Fortune | `Alexaliao001/fortune-insight` | `Alexaliao001/fortune-insight-deploy` |
| Portfolio | `Alexaliao001/rongjian-portfolio` | `Alexaliao001/rongjian-portfolio-deploy` |
| QuantRadar | `Alexaliao001/quantradar` | （已 public） |

部署形态：`dist/` 预构建 + 零依赖 `node dist/index.js` 静态托管（无 DB/Stripe/Forge 时前端可跑）。

---

## 你需要做的 cutover（约 15 分钟，不烧 Manus 积分）

### A. chillworks.ai → Render（摸了么）

**顺序很重要**（与 quantradar 相同）：

1. **先确认预览 OK**  
   打开 https://moyu-fortune.onrender.com （首次可能冷启动 1 分钟）

2. **Manus 解绑域名（必做）**  
   - Manus 项目（摸了么 / chillworks）→ Custom domain  
   - **Remove / Disconnect** `chillworks.ai` 与 `www`  
   - **不要**开 agent 任务，点设置即可

3. **Namecheap DNS**（NS 已是 `dns1/2.registrar-servers.com`）  
   Advanced DNS，删掉指向 `cname.manus.space` / Manus 的旧记录，改为：

   | Type | Host | Value | TTL |
   |------|------|-------|-----|
   | CNAME Record | `@` | `moyu-fortune.onrender.com` | Automatic |
   | CNAME Record | `www` | `moyu-fortune.onrender.com` | Automatic |

   Namecheap 对 apex 若不允许裸 CNAME：用其 **URL Redirect** `@` → `https://www.chillworks.ai`，只把 `www` CNAME 到 Render；或按 Render 面板显示的记录填。

4. **Render 验证**  
   Dashboard → moyu-fortune → Custom Domains → 等 `chillworks.ai` 变 verified（或跑下面脚本）

5. **验收**
   ```bash
   curl -sI https://chillworks.ai | head -5
   # 应 200；页面 title 含「摸了么」；不应再跳 manus.im
   ```

### B. fortunesite.one → GitHub Pages（Fortune 静态前端）

Render 域名名额已满，生产自定义域走 **GitHub Pages**（`fortune-insight-deploy` 的 `gh-pages`，CNAME=`fortunesite.one`）。

1. **预览（Render 备用，不绑域）**  
   https://fortune-insight.onrender.com

2. **Manus 解绑** `fortunesite.one` / `www`（同样只点设置，不开 agent）

3. **DNS（NS：`ns1/ns2.globaldomaingroup.com`）**  
   删掉 Manus / 混入的 GitHub 旧 A 记录，**只保留** GH Pages 记录：

   **Apex `fortunesite.one`**（GitHub Pages 标准）：
   ```text
   A  @  185.199.108.153
   A  @  185.199.109.153
   A  @  185.199.110.153
   A  @  185.199.111.153
   ```

   **www**：
   ```text
   CNAME  www  alexaliao001.github.io
   ```

   参考：https://docs.github.com/pages/configuring-a-custom-domain-for-your-github-pages-site

4. **GitHub Pages HTTPS**  
   Repo → Settings → Pages → 勾选 Enforce HTTPS（DNS 正确后证书从 `bad_authz` 恢复为 active）

5. **验收**
   ```bash
   dig fortunesite.one A +short
   # 仅 185.199.*，无 104.18 Manus 混杂

   curl -sI https://fortunesite.one | head -10
   curl -s https://fortunesite.one | grep -oE '<title>[^<]+'
   ```

### C. Portfolio

无自有域名。分享：

**https://rongjian-portfolio.onrender.com**

若以后买域，需先腾出 Render 自定义域名名额（或改 GH Pages / 付费 Render）。

---

## 功能边界（诚实说明）

当前 Free 静态切流 **只保证前端可访问**：

| 能力 | 状态 |
|------|------|
| 落地页 / SPA 路由 / 静态资源 | ✅ |
| AI（Manus Forge LLM） | ❌ 需自备 API Key + 后端 |
| MySQL / Drizzle | ❌ 需托管 DB |
| Stripe 支付 | ❌ 需密钥 + webhook |
| 登录 / tRPC 写路径 | ⚠️ 无后端时会失败或降级 |

后续若要全功能：在 Render 加 env（`DATABASE_URL`、`STRIPE_*`、`BUILT_IN_FORGE_*` 等）并恢复完整 `npm start` 服务端——**与本次「先迁出 Manus、省积分」目标分开做**。

---

## 仓库 / 镜像同步

源码仍以 private 仓为准；改 UI 后：

```bash
# 例：更新 fortune 静态
cd /path/to/fortune-insight
pnpm build
# 同步 dist 到 fortune-insight-deploy 并 push main
# 再刷新 gh-pages（从 dist/public）
```

---

## 验收脚本

```bash
python3 ~/quantradar/scripts/multi_site_verify.py
```

---

## 完成后状态目标

- [x] 四站 onrender（或 GH Pages）有可访问副本  
- [x] quantradar.one 已切 Render  
- [ ] chillworks.ai → moyu-fortune.onrender.com  
- [ ] fortunesite.one → GitHub Pages（fortune-insight-deploy）  
- [ ] Manus 项目仅保留域名账单（可选），**App Auth / 站点托管关闭**  
- [ ] 不再为部署开 Manus agent（省积分）
