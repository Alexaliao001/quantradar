# QuantRadar

专业量化交易决策平台：门控 **Market → Sector → Stock**、形态/量价、期权策略、综合评分。

| | |
|--|--|
| 线上 | https://quantradar.one |
| **工程 SSOT** | 本仓库（GitHub） |
| 本机路径 | `~/quantradar` |
| 分析引擎（可复用） | [`stock-charts`](https://github.com/Alexaliao001/stock-charts) → `~/charts` |
| **优化 /goal** | **[GROK_GOAL.md](./GROK_GOAL.md)**（v2） |
| Skill 继承账本 | [docs/SKILL_INHERIT.md](./docs/SKILL_INHERIT.md) |
| Manus 发布 | [docs/MANUS_SYNC.md](./docs/MANUS_SYNC.md) |

## 工程闭环（强制）

```text
本机 git pull  →  优化 + 验证  →  git push
    →  你在 Manus pull/sync  →  Manus 发布 quantradar.one
```

- **源码真相**在 GitHub / 本机，不在 Manus 独有 diff。  
- 代理每轮会做 **Skill 采掘**（本地 skill + X 搜索）并写入 `docs/SKILL_INHERIT.md`。

## 状态

应用业务源码仍在恢复中（见 goal **QR0**）。当前仓含 goal、文档与发布约定。  
**请勿**在未锁定 QR0-1 路径（A/B/C）前向生产盲推破坏性变更。

## 数据策略（摘要）

- **free**：Yahoo / yfinance + agent-reach 情报  
- **hybrid**：服务端 Massive 只算**分析结论**；不向浏览器转发原始 OPRA  
- **pro / 自用 desk**：完整期权能力可留 Massive（见 `~/charts/research/data_provider_comparison.md`）

## 开跑 /goal

```
/goal QuantRadar 极致优化 v2。主任务源：~/quantradar/GROK_GOAL.md
工程闭环：pull → 改 → push → 用户 Manus 发布。
每轮 Skill 采掘 + 1 个 QR-ID。
```

## License

Fortune Insight, LLC. 勿提交密钥。
