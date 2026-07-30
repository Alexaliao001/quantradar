# Clone defense（上线后 · 诚实版）

> 2026-07-26。目标：**提高复刻真实产品的成本**，不假装 UI 可保密。  
> 对齐 Trust Gate：仍诚实展示 score / freeze / gates；不藏方法论原则。

## 现实

| 几乎挡不住 | 值得守 |
|------------|--------|
| Desk HTML/CSS/动效 | `~/charts` 计分引擎（勿并入本仓公开） |
| 冻结 demo 观感 | 行情密钥 + 常驻 mount |
| 「长得像」的站 | 校准 track、信任与分发 |

## 已落地（壳）

| 项 | 做法 |
|----|------|
| 公开 analyze 表面 | `app/public_surface.py`：guest/Free/artifact 收束 volume/options 细节；`analysis_json` 恒为 null；路径 basename |
| `/health` | `charts_dir` 恒 `null`；仅 `charts_dir_configured` + status |
| robots | `Disallow: /api/`（信号，非安全边界） |
| ToS | 禁批量抓取 / 再分发 API 与 demo 资产冒充自有产品 |
| Track | `/track` + `/api/track` — 运营手写笔记，**永不编造胜率** |

Pro + `mode=live` 保留更完整的 `data_quality`（付费操作者需要审计）。

## 部署隔离（必做）

见 [`SELF_DEPLOY.md`](./SELF_DEPLOY.md)「密钥与引擎隔离」：

1. **勿**把 `~/charts` 源码推到与 quantradar 同一公开仓库  
2. Render/主机上 `CHARTS_DIR` 仅环境变量指向私有盘或私有镜像层  
3. Polygon/Massive 等密钥只在 charts 主机，永不进前端 env  
4. GitHub 若公开：接受 fixtures 可被克隆；护城河仍是 live 引擎 + 运营

## 不要做

- JS/CSS 混淆当护城河  
- 前端「加密」分数再解密  
- 为防抄而关掉 freeze / methodology（伤「别骗我」）

## 验证

```bash
python3 -m unittest tests.test_public_surface -v
curl -sS http://127.0.0.1:8765/api/sample?ticker=INTC | python3 -c "import sys,json; j=json.load(sys.stdin); assert j['artifacts']['analysis_json'] is None; assert j['meta'].get('public_surface')=='desk'"
curl -sS http://127.0.0.1:8765/health | python3 -c "import sys,json; j=json.load(sys.stdin); assert j['charts_dir'] is None"
```
