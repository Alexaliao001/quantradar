# QuantRadar

专业量化交易决策平台（门控 Market → Sector → Stock、形态/量价、期权策略、综合评分）。

| 项 | 链接 |
|----|------|
| 线上产品 | https://quantradar.one |
| 公开营销站 | https://github.com/Alexaliao001/quantradar-site |
| 分析引擎（本地） | https://github.com/Alexaliao001/stock-charts → `~/charts` |
| **产品优化 /goal** | 见 `GROK_GOAL.md`（完整版也在 `~/charts/GROK_GOAL_QUANTRADAR.md`） |

## 状态（2026-07-10）

本仓曾被清空（size=0）。当前仅恢复 **目标与文档 SSOT**，应用源码待按 goal **QR0** 从 Manus 导出或以 `~/charts` 重建（路径 A/B/C）。

**请勿**在未锁定恢复路径前向 `quantradar.one` 盲推部署。

## 数据策略（摘要）

- **产品层**：Yahoo / yfinance / Alpha Vantage BYO + agent-reach 新闻社交；Massive 仅服务端算结论（hybrid），禁止个人档转发行情。
- **自用 desk（charts）**：期权仍以 Massive 为优；跨境用 VPS 中转。详见 `~/charts/research/data_provider_comparison.md`。

## 本地引擎（源码恢复前可先用）

```bash
# 图表/扫描/报告 CLI（stock-charts）
cd ~/charts
# export POLYGON_API_KEY=...   # 或仅用免费路径（goal QR2）
python3 fetch_all.py AAPL XLK
```

## License / 公司

Fortune Insight, LLC · 商业邮箱见运营笔记（勿在公开 issue 贴密钥）。
