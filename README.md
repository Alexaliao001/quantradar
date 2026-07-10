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
| 盘点 | [docs/PHASE0.md](./docs/PHASE0.md) |
| 引擎契约 | [docs/ENGINE_CONTRACT.md](./docs/ENGINE_CONTRACT.md) |

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

**禁止**在本仓复制粘贴整份 `generate_charts` / 机械分公式。壳只通过 subprocess 或读取 charts 产出的 JSON，映射到 [ENGINE_CONTRACT](./docs/ENGINE_CONTRACT.md)。

## 本地最小壳（QR0-2）

零第三方依赖（Python 3.11+ stdlib）：

```bash
cd ~/quantradar
# 默认 artifact：读 fixtures/charts_sample 或 CHARTS_DIR 下真实报告 JSON
QUANTRADAR_MODE=artifact PORT=8765 python3 -m app
```

| 端点 | 说明 |
|------|------|
| `GET /` | 访客 UI（**无需登录**，无 manus.im） |
| `GET /health` | `git_sha` + `auth: none` + `manus_login: false` |
| `GET /api/analyze?ticker=INTC` | 公开分析（ENGINE_CONTRACT JSON） |
| `POST /api/analyze` | body: `{"ticker":"INTC","sector":"SMH"}` |
| `GET /api/sample` | 访客样例（INTC artifact） |
| `GET /api/oauth/*` | **410** — Manus 登录已禁用 |

**Auth**：不使用 Manus 登录。见 [docs/AUTH.md](./docs/AUTH.md)。若线上仍跳 `manus.im/app-auth`，说明域名还挂着旧 Manus 托管 App，需按 [MANUS_SYNC.md](./docs/MANUS_SYNC.md) 关平台 Auth 并发布本仓壳。

### 环境变量

| 变量 | 默认 | 含义 |
|------|------|------|
| `PORT` | `8765` | 监听端口 |
| `HOST` | `127.0.0.1` | 绑定地址 |
| `CHARTS_DIR` | `~/charts` | 引擎根目录 |
| `QUANTRADAR_MODE` | `artifact` | `artifact` 读盘；`live` 调 `fetch_all.py`（需网络/key） |

### 测试

```bash
python3 -m unittest discover -s tests -v
python3 scripts/validate_contract_sample.py
```

## 状态

| QR | 状态 |
|----|------|
| QR0-0 PHASE0 盘点 | ✅ |
| QR0-4 ENGINE_CONTRACT | ✅ |
| QR0-2 最小产品壳 | ✅ 可 `python -m app`；**可 Manus pull 发布** |
| 下一优先 | QR0-SEC / QR0-3 / QR2-1 |

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
