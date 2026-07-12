# PROGRESS — QuantRadar

2026-07-12 | **auth v0.3.0** | 自有 `/login` + Google OAuth + `qr_session` cookie；`/api/me`；live 需登录；dev-login 仅本地；docs/AUTH.md | **可 Manus pull**；生产需 GOOGLE_* + SESSION_SECRET + PUBLIC_BASE_URL
2026-07-12 | **P0 shell v0.2.0** | quality gates：占位 ticker 拒绝、无数据 score withheld、量能0禁叙事、期权 simulated 降级、单 primary、限流、诚实 UI；`scripts/p0_smoke.py` + `docs/P0_CUTOVER.md`；unittest 全过 | **可 Manus pull 发布**；线上 cutover 前 `--live` 仍会 FAIL（旧 SPA）
2026-07-12 | **live audit** | 实测 quantradar.one：12 项 bug（P0: 假代码XXXX可买、量能为0却编叙事、期权荒谬、BRK.B 500）；文档 `docs/LIVE_BUGS_2026-07-12.md`；Manus 修复任务 `c6Xp49sUbpKBzinjeYeqAs` | 等 Manus 部署后复验
2026-07-10 | **auth** | 铁律：禁止 manus.im 登录；`/api/oauth/*`→410；health `manus_login:false`；docs/AUTH.md | **可 Manus pull 发布**（须关平台 App Auth）
2026-07-10 | **QR0-2** | 最小产品壳 `python -m app`：`/health` + `/api/analyze` 读 charts 工件/可选 live fetch_all；路径 C 边界无引擎分叉 | **可 Manus pull 发布**
2026-07-10 | **QR0-4** | `docs/ENGINE_CONTRACT.md` + schema + map/validate；样例由真实 fixture 生成 | 契约可测
2026-07-10 | **QR0-0** | `docs/PHASE0.md`：线上笔记、charts 入口表（≥8）、壳栈建议 stdlib HTTP | 盘点完成
2026-07-10 | goal v3 | 路径 C 锁定；Skill L1→L2→L3；多 agent 勘探+单写者 | 下一优先 QR0-SEC / QR0-3
2026-07-10 | goal v2 | 工程闭环 + Skill 采掘环建账 | 已由 v3 取代主叙事
