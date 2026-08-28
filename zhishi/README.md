# 知势 Zhishi — A股 / 港股通投教产品

独立于 QuantRadar 的大陆投教产品：**复盘教练 + 课程框架自检**，不荐股。

## 快速开始

```bash
cd zhishi
python3 scripts/generate_fixtures.py   # 生成 20 个教学案例日线
python3 -m app                         # http://0.0.0.0:8787
python3 -m unittest discover -s tests -v
```

环境变量见 [docs/DATA_SOURCES.md](docs/DATA_SOURCES.md)。默认 `ZHISHI_MODE=artifact`。

## 文档

| 文档 | 说明 |
|------|------|
| [docs/BRAND.md](docs/BRAND.md) | 品牌锁定 |
| [docs/COMPLIANCE.md](docs/COMPLIANCE.md) | 禁荐股边界 |
| [docs/TRUST_GATE.md](docs/TRUST_GATE.md) | 信任门控 |
| [docs/WIREFRAMES.md](docs/WIREFRAMES.md) | 主路径线框 |
| [docs/ENGINE_CONTRACT.md](docs/ENGINE_CONTRACT.md) | API 契约 |
| [docs/DATA_SOURCES.md](docs/DATA_SOURCES.md) | 数据源授权 |
| [docs/LICENSED_PARTNER.md](docs/LICENSED_PARTNER.md) | 持牌合作路径 |

## 功能地图

- H5：`/` 案例 → 自检 → 复盘本 → 错题本 → 港股通差异 → 会员定价  
- 小程序壳：[`miniprogram/`](miniprogram/)  
- SKU：免费 / ¥68 月 / ¥488 年 / ¥129 课包（mock 支付）  
- 法务：`/terms` `/privacy` `/disclaimer` `/methodology`

## 拆仓说明

本目录设计为**独立产品根**；可整体迁到单独 GitHub 仓库。勿与美股 QuantRadar 账号或订阅互通。
