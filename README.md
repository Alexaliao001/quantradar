# QuantRadar

专业量化交易决策平台：门控 **Market → Sector → Stock**、形态/量价、期权策略、综合评分。

| | |
|--|--|
| 线上 | https://quantradar.one |
| **工程 SSOT** | 本仓库（GitHub） |
| 本机路径 | `~/quantradar` |
| 分析引擎（可复用） | [`stock-charts`](https://github.com/Alexaliao001/stock-charts) → `~/charts` |
| **优化 /goal** | **[GROK_GOAL.md](./GROK_GOAL.md)**（**v3 · 路径 C**） |
| Skill 继承账本 | [docs/SKILL_INHERIT.md](./docs/SKILL_INHERIT.md) |
| Manus 发布 | [docs/MANUS_SYNC.md](./docs/MANUS_SYNC.md) |

## 工程闭环（强制）

```text
本机 git pull  →  优化 + 验证  →  git push
    →  你在 Manus pull/sync  →  Manus 发布 quantradar.one
```

- **源码真相**在 GitHub / 本机，不在 Manus 独有 diff。  
- 代理每轮会做 **Skill 采掘**（本地 skill + X 搜索）并写入 `docs/SKILL_INHERIT.md`。

## 路径 C（已锁定）

| 仓 | 职责 |
|----|------|
| **本仓 quantradar** | 产品 UI / API / 鉴权 / 计费 / health / 访客样例 |
| **`~/charts` (stock-charts)** | 分析核：数据、图表、扫描、指标 |
| **Manus** | 从 GitHub pull 后构建发布，非源码 SSOT |

## 状态

应用壳仍在 **QR0-2 最小可 dev** 阶段。当前仓以 goal/文档为 SSOT 引导。  
Skill：本地 → 仓库（charts/commands、stock-skills 有用部分）→ 卡住再 X 多方比对（见 `docs/SKILL_INHERIT.md`）。

## 数据策略（摘要）

- **free**：Yahoo / yfinance + agent-reach 情报  
- **hybrid**：服务端 Massive 只算**分析结论**；不向浏览器转发原始 OPRA  
- **pro / 自用 desk**：完整期权能力可留 Massive（见 `~/charts/research/data_provider_comparison.md`）

## 开跑 /goal

```
/goal QuantRadar 极致优化 v3。主任务源：~/quantradar/GROK_GOAL.md
路径 C：charts 引擎 + 本仓库壳。闭环：pull → 改 → push → Manus 发布。
Skill：L1 本机 → L2 仓库 → 卡住 L3 上 X 比对；可多 agent 勘探、单写者落地。
```

## License

Fortune Insight, LLC. 勿提交密钥。
