# 本机打磨清单（部署前）

目标：在 `127.0.0.1:8765` 把产品磨到「可对外」再 `git push` → 自部署（见 [`SELF_DEPLOY.md`](./SELF_DEPLOY.md)）。**不用 Manus。**

## 一键检查

```bash
cd ~/quantradar
PORT=8765 python3 -m app   # 若尚未启动
python3 scripts/local_polish_check.py
```

## 人工走查（建议顺序）

| # | 动作 | 通过标准 |
|---|------|----------|
| 1 | 打开 `/` | 品牌 > 问句；雷达平面；Try demo + Pricing；无假用户数 |
| 2 | `/?demo=INTC` | ≤30s 能口述该不该上手 + 为什么；见 freeze；见日线图（若 fixture 有） |
| 3 | WAIT/NO 结果 | avoided 句 + Remind me；**无**注册挡墙 |
| 4 | `/pricing` | Free/Pro 两卡；supporter / 锚 / FAQ；无 Elite |
| 5 | `/r/INTC` | 无 JS 也能看到 ticker + primary + score |
| 6 | 375 宽 | sticky Analyze；Verdict 可读；Next 不被挡 |
| 7 | `mode=live` 未登录 | 引导登录；不假 BUY |
| 8 | `/methodology` | posture≠direction、PUT≠sell、Educational |

## 工程绿线

- [ ] `python3 -m unittest discover -s tests -v` 全绿  
- [ ] `python3 scripts/p0_smoke.py --base http://127.0.0.1:8765` PASS  
- [ ] `GET /api/charts/INTC_daily_price_2026-03-21_01-43-21.png` → 200 PNG  
- [ ] 源码无 `manus.im`；`/health.manus_login=false`  

## 部署前仍可诚实留下

| 项 | 说明 |
|----|------|
| Stripe 生产价 | 本机可无 test key；上线前配 QD1-1 |
| Remind 邮件实发 | waitlist 已存；SMTP 后做 QD3-3 |
| 全量 ticker live | 生产 Free 无 charts 树属预期 |

打磨满意 → commit → push → 按 `SELF_DEPLOY.md` 上 Render。
