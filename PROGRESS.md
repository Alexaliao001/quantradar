2026-09-06 | **STRIPE-SANDBOX** | JJ 账号真实 test mode 完成美元/英镑报告支付、签名回调、90 日交付/隔离、退款撤券、Pro→Portfolio、期末取消、时钟续费/失败/补缴；修复退款后旧优惠 Checkout 卡住，244 测试与独立复核通过；正式独立 Portal 已准备；Marketstack 询问已发送，工单 307916 | 待数据书面授权后配套切换 Nube/正式计费，Apple 仍 build 7 排队；无全量上线或盈利结论

2026-09-06 | **BUILD8-UPLOAD** | App Store Connect build 8（1.2.0）上传成功且 VALID；原 build 7 审核仍 WAITING_FOR_REVIEW；已备份审核/IAP资料并准备双项目替换和地区价格文案；补充 Marketstack $9.99 商用候选及未发送询问 | 仍待数据授权、Stripe test 重认证/真实购买验收；未全量上线

2026-09-06 | **LAUNCH-HARDENING** | 完成交易日/独立数据源、持久化单股付费交付/退款/防重复订阅、每日观察列表与真实下载；Python 238 通过，iOS 46（4 外部接口检查跳过）通过，375/1440 截图；build 8 本地归档；两条遗留 Stripe 付款链接已停用；生产热备份及异机校验完成 | 尚未全量上线：待数据授权、Stripe sandbox 生命周期、正式 Portal/配置和 Apple 审核；见 docs/audit/2026-09-06/README.md

# PROGRESS — QuantRadar

2026-08-02 | **AUDIT-FIX** | 安全/诚实审计落地：bootstrap 默认关+公网禁 demo；SESSION_SECRET 公网失败关闭；plan 仅 users store；缺/非法分数 withheld；market/sector 不再假 pass；magic 不落盘/日志脱敏；login+magic 限流；Stripe customer_id 降级回退；health storage_note；72+ 回归测 | push 后需手动 Trigger Render
2026-08-02 | **QD2-4a** | 移动端横向溢出：`.hero-copy` 补 `min-width:0`（grid item 默认 auto 被不可断行字标撑宽）+ hero/share 字标 clamp 下限降到能进 320px；320–430 全宽度 0 溢出，1440 像素级不变；截图 `docs/audit/2026-08-02/` | push 后需手动触发 Render
2026-08-02 | **HEAD-FIX** | `do_HEAD` 复用 GET 路由、只发头不发体（Content-Length 一致）；一次性/会话变更的 auth 路由回 405 + `Allow: GET`（防探针烧掉 magic link）；HEAD 不写 funnel 事件；`tests/test_head_method.py` 6 例；72 测绿 | push 后 Render 自动部署
2026-07-27 | **GRAPH-P0** | 导览 SSOT：产品顶栏 Meth·Track·Pricing·Sign in；法律回流；share footer；robots Disallow /btn-demos；Remind 诚实未发信 | 补边完成 · 邮件/Portal/三长文另刀
2026-07-26 | **SELF** | 弃 Manus 自部署文档 + QD2-0 真图（fixtures assets + /api/charts + desk）；LOCAL_POLISH/SELF_DEPLOY；local_polish_check | 本机打磨 → push → Render
2026-07-26 | **FULL_FUNNEL** | `docs/FULL_FUNNEL_DESIGN.md` SSOT（含研究 D-P0）；ready→verdict 滚动；375 sticky 防挡 Next；methodology Trust 文案；`/r/{ticker}` 分享摘要+OG；tokens/focus；unittest | 未 commit · 下一 Manus pull / QD1-1 / QD2-0
2026-07-26 | **P0+SEC** | stock-agent MAP + `gate.entry_timing` + desk 姿态文案；funnel/sample/notify/register 限流 + funnel 体积帽；Gate UI 禁 spy 启发式；unittest 全绿 | 未 commit · 下一 QD2-0 / charts PNG
2026-07-26 | **QD2-3** | 统一 motion（CSS vars/keyframes）+ 封面雷达 hero + desk loading/ready wow + pricing 轻对齐；`prefers-reduced-motion`；`docs/ENGAGEMENT.md` 动效节 | 可演示 · 未 commit · 下一 QD2-0 / QD1-1
2026-07-17 | **ENGAGE** | 商业闭环参与度：funnel JSONL + report；desk score dial/gates/breakdown/avoided+freeze；Next 回流钩；pricing FAQ；`docs/ENGAGEMENT.md`；unittest | 可 Manus pull 发布 · 下一 QD2-0 / QD1-1
2026-07-16 | **QD1-0** | Pro 价值裁决 B：Render Free 不能 live → 支持者价 + mounted 自动解锁；`docs/PRO_VALUE.md` + health `pro_value`；文案对齐；47 测绿 | 可 Manus pull 发布 · 下一 QD2-0
2026-07-16 | **QD0-0** | desk-v1 + billing 闭环落库：Verdict Desk 四态、月/年 checkout、webhook plan SSOT、cancel→free metadata、live Pro 门控诚实文案；unittest 46 绿 | 可 Manus pull 发布 · 下一 QD1-0
2026-07-13 | **SX1 v0.7.0** | 数据层诚实：health charts_status/data_path/product_note；artifact options=snapshot；路径脱敏；UI 展示；SITES EXTREME SX1 | push 后 Render 自动部署
2026-07-13 | **cutover 完成** | quantradar.one → Render Free 壳 `quantradar-shell`；apex verified；cutover_verify PASS；无 Manus auth | 主站已是新壳

2026-07-12 | **Render Free 上线** | `quantradar-shell` plan=free · https://quantradar-shell.onrender.com · cutover_verify PASS · srv-d99nc357vvec73frpus0 | **域名 quantradar.one 待 DNS 切**
2026-07-12 | **最终决断** | `docs/DECISION.md`：否决 Manus 修 SPA；Render 跑 path-C 壳 → GlobalDomain DNS → Manus 仅解绑；`scripts/cutover_verify.sh` | 代理侧代码/测试/文档完成；等你点 Render+DNS
2026-07-12 | **ops 锁定** | `docs/CORRECT_OPS.md`：SSOT=GitHub；线上 Manus SPA≠仓库；部署=Render/Python 主机+GlobalDomain DNS；Manus 只做解绑/停发、尽量少用 Lite | 执行时勿再混三套
2026-07-12 | **auth v0.6.0** | 自建邮箱+密码登录（`data/users.json` PBKDF2）；`/api/auth/register|login`；登录页主路径密码，magic 次要，Google 仅 env 配置时显示；bootstrap admin@local.test | 可本地立刻用
2026-07-12 | **trust v0.5.0** | TRUST_GATE.md + 单 primary_score/summary；demo chips 免费 sample；methodology/pricing/terms/privacy/refund；/api/notify waitlist；og 自托管；无假 1247 社交证明 | **可 Manus pull**；上线前按 TRUST_GATE 验收
2026-07-12 | **ship v0.4.0** | magic link + Stripe checkout + .env bootstrap + Docker/Render/Fly/CI；`docs/DEPLOY.md` | 代码可发布；域名/Render账号/Google Console 需人工
2026-07-12 | **auth v0.3.0** | 自有 `/login` + Google OAuth + `qr_session` cookie；`/api/me`；live 需登录；dev-login 仅本地；docs/AUTH.md | **可 Manus pull**；生产需 GOOGLE_* + SESSION_SECRET + PUBLIC_BASE_URL
2026-07-12 | **P0 shell v0.2.0** | quality gates：占位 ticker 拒绝、无数据 score withheld、量能0禁叙事、期权 simulated 降级、单 primary、限流、诚实 UI；`scripts/p0_smoke.py` + `docs/P0_CUTOVER.md`；unittest 全过 | **可 Manus pull 发布**；线上 cutover 前 `--live` 仍会 FAIL（旧 SPA）
2026-07-12 | **积分铁律** | 能不用就不用；能 lite 就 lite；**主要部署才用**。本机开发 → push → Manus 只 publish。误开 task 已 DELETE（404）。规则：`docs/MANUS_SYNC.md` + manus-ops skill | 默认零 agent
2026-07-12 | **live audit** | 12 项线上 bug 文档；误开 Manus agent 已停 | 后续修 bug 只走本机壳 + cutover
2026-07-10 | **auth** | 铁律：禁止 manus.im 登录；`/api/oauth/*`→410；health `manus_login:false`；docs/AUTH.md | **可 Manus pull 发布**（须关平台 App Auth）
2026-07-10 | **QR0-2** | 最小产品壳 `python -m app`：`/health` + `/api/analyze` 读 charts 工件/可选 live fetch_all；路径 C 边界无引擎分叉 | **可 Manus pull 发布**
2026-07-10 | **QR0-4** | `docs/ENGINE_CONTRACT.md` + schema + map/validate；样例由真实 fixture 生成 | 契约可测
2026-07-10 | **QR0-0** | `docs/PHASE0.md`：线上笔记、charts 入口表（≥8）、壳栈建议 stdlib HTTP | 盘点完成
2026-07-10 | goal v3 | 路径 C 锁定；Skill L1→L2→L3；多 agent 勘探+单写者 | 下一优先 QR0-SEC / QR0-3
2026-07-10 | goal v2 | 工程闭环 + Skill 采掘环建账 | 已由 v3 取代主叙事
