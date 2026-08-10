# 知势 — A股日线数据源与授权边界

> 版本：1.0.0 · 结论：MVP 默认 **fixture/artifact**；live 仅在配置授权密钥后启用。

## 选定方案

| 优先级 | 源 | 用途 | 授权边界 |
|--------|-----|------|----------|
| **默认** | 内置 `fixtures/` 日线 JSON | Demo、CI、无网教学 | 自有合成/公开教学样本，可商用展示 |
| **可选 live** | **Tushare Pro** | 日线 OHLCV、基础信息、ST 标记 | 需积分/付费权限；**仅服务端**；禁止把原始行情转售或对外宣称「交易所官方」 |
| **开发备选** | AKShare | 本地研发探测 | 聚合第三方公开接口，**生产商用风险高**；未获书面授权不得作为付费卖点数据层 |

**MVP 锁定**：`ZHISHI_MODE=artifact`（默认）。`live` 仅当 `TUSHARE_TOKEN` 存在且 `ZHISHI_ALLOW_LIVE=1`。

## 为何不用 Yahoo/Polygon 作 A股主源

- A股代码、复权、涨跌停、ST、停牌语义与美股源不匹配  
- 大陆用户与合规叙事需要可说明的境内数据路径  

## 港股通

- P2：教学案例用 fixture；规则课不依赖实时报价  
- live：Tushare 港股通成分与日线（同样需权限）  

## 禁止

- 未授权源当付费产品「实时行情」卖点  
- 浏览器直出第三方 raw feed / API key  
- 把延迟数据标成「实时 Level-2」  

## 运行时开关

```bash
ZHISHI_MODE=artifact          # artifact | live
ZHISHI_ALLOW_LIVE=0           # 显式打开才允许 live
TUSHARE_TOKEN=                # 仅服务端
```

`/health` 必须暴露：`data_path`、`mode_default`、`live_eligible`（布尔，不含 token）。
