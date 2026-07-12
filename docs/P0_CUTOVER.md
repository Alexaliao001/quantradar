# P0 止血 + 域名切到 Path-C 壳

> 日期：2026-07-12  
> 目标：线上不再对假 ticker 出 buy；访客无需 Manus 登录；分数来自 charts 契约。

## 已在本仓完成（v0.2.0）

| 项 | 行为 |
|----|------|
| 占位 ticker | `XXXX` / `ASDF` 等 → `ValueError` / HTTP 400，无分数 |
| 无 artifact / 无 mechanical_scores | `ok=false`，`score.withheld=true`，`primary=NO` |
| 量能全 0 | `volume_narrative_allowed=false` + warning，禁止量价故事 |
| 期权 simulated | `options_actionable=false` + warning |
| 单主结论 | `primary.action` ≡ `gate.signal` |
| Auth | `/api/oauth/*` → 410；health `manus_login:false` `p0_gates:true` |
| UI | 诚实 KPI + data quality + disclaimer，无假社交证明数字 |

```bash
cd ~/quantradar
python3 -m unittest discover -s tests -v
python3 scripts/p0_smoke.py
QUANTRADAR_MODE=artifact PORT=8765 python3 -m app
# 另一终端
python3 scripts/p0_smoke.py --base http://127.0.0.1:8765
```

## 你必须做的发布动作（域名仍在 Manus 时）

本机/GitHub **修不了 DNS 上的旧 SPA**。线上仍返回：

```json
{"ok":true,"service":"quantradar","env":"production"}
```

说明 **还没切到本壳**。

**最终决断见 [DECISION.md](./DECISION.md)**（不要再开 Manus agent 修 SPA）：

1. `git push` 本仓 main  
2. **Render** Blueprint 部署 `python -m app`（`render.yaml`）  
3. **GlobalDomain** DNS 指到 Render  
4. Manus **仅解绑**旧 SPA（不烧 agent 积分）  
5. 验收：
   ```bash
   bash scripts/cutover_verify.sh https://quantradar.one
   ```
   全部 PASS 才算 cutover 完成。

### 验收清单（线上）

- [ ] `GET /health` → `service=quantradar-shell`，`manus_login=false`，`p0_gates=true`
- [ ] `GET /api/analyze?ticker=XXXX` → 4xx，`ok=false`，无 buy
- [ ] `GET /api/analyze?ticker=INTC` → JSON，`score.final` 来自 artifact/engine
- [ ] `GET /api/oauth/callback` → **410**
- [ ] 页面无跳转 `manus.im/app-auth`
- [ ] 首页无静态 `1247/896` 社交证明

## 若短期必须留 Manus SPA

在 Manus 任务里按 `docs/LIVE_BUGS_2026-07-12.md` 修 P0，并**回写 GitHub**。  
长期仍应 cutover 到本壳，避免双轨。
