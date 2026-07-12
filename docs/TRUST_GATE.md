# Trust Gate — 上线 / 收款前验收

> 产品哲学：可信雷达，不是又一个指标仪表盘。  
> 来源：2026-07-12 外部产品评审 + LIVE_BUGS P0 + path-C 契约。

## 铁律（违反 = 禁止推付费 / 禁止 cutover 完成）

| ID | 规则 |
|----|------|
| TG-1 | 页面上 **最多 1 个** 主分数，字段名 `primary_score`（= charts `score.final`）。禁止同时展示多个 “Composite”。 |
| TG-2 | `primary.action` 与 summary / CTA 文案 **一致**。不允许 buy 与 Wait & Watch 并存。 |
| TG-3 | **禁止** 无出处 testimonials；禁止硬编码 `1247/896` 类社交证明。早期用 “Beta · sample analyses”。 |
| TG-4 | 定价文案全站一致（形态数量、期权是否含、年付整数价）。禁止换算残留 `$266.58`。 |
| TG-5 | **Demo ticker**（chip / sample）走预缓存 artifact，**不扣额度、不打 live API**。 |
| TG-6 | 无数据 / 假 ticker **fail-closed**（P0）：不 buy、不编量价叙事。 |
| TG-7 | 模拟期权必须 `options_actionable=false` + 明示 simulated。 |
| TG-8 | og:image / 品牌图 **自托管** 于本域 `static/`，禁止 `files.manuscdn.com`。 |
| TG-9 | Stripe 收款前：Terms / Privacy / Refund 三页可访问。 |
| TG-10 | 产品登录不得 `manus.im/app-auth`；`/health.manus_login=false`。 |

## 产品结构（推荐）

| 档 | 定位 |
|----|------|
| Guest / Free | Demo artifact + 有限 guest analyze；**无期权 actionable** |
| Pro | 登录 + live + 更高限流（Stripe） |
| Elite | **默认不上架**；无公开 track record 前不卖 institutional 叙事 |

Wait & Watch 后默认 CTA：**Setup 改善时提醒我**（邮件捕获），而非挡结果的 Sign Up 浮层。

## 战略

- 对外卖 **可审计姿态分 + 单一主结论 + methodology 页**。  
- 私有壁垒（market_context / Wave / exit）经校准后进 methodology，不进假评价。

## 验收命令

```bash
python3 -m unittest discover -s tests -v
python3 scripts/p0_smoke.py --base http://127.0.0.1:8765
curl -sS http://127.0.0.1:8765/methodology | head
curl -sS http://127.0.0.1:8765/terms | head
curl -sS http://127.0.0.1:8765/api/sample | python3 -c "import sys,json; d=json.load(sys.stdin); assert d.get('sample') is True; assert 'primary_score' in d or d.get('score')"
# 禁止
curl -sS http://127.0.0.1:8765/ | grep -E '1247|896|M\. Chen|manuscdn' && exit 1 || true
```

## Cutover 完成定义

`https://quantradar.one/health` → `service=quantradar-shell` + 本文件 TG-1…TG-10 本地与线上均 PASS。
