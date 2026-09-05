# QuantRadar 本次验收记录

日期：2026-09-06。状态：修复及本地验收完成，商业全量发布尚未完成。此记录将源码、测试、正式账户和商店状态分开。

## 改动与用途

- Web / iOS / Widget 只使用完成的交易日；纽约节假日与提前收市共用 2026–2028 日历，缺数据为 UNKNOWN，SPY/个股日期对齐。Yahoo 两个入口只算一个来源；跨收市缓存不能掩盖旧数据。
- Web 并发取数限制为 2 个进程，相同请求合并与短时缓存。账号隔离的扫描记录保存实际收盘日期及价格，不用“扫描后收益”包装日线差值。
- 单股报告在结账前验证 90 日重建所需覆盖并冻结输入；SQLite 记录订单、付款、退款和事件。异步生成 JSON/图表/CSV，重试及 worker lease 避免迟到结果覆盖交付。
- 每个账号只有一个可恢复的订阅结账尝试，网络失败/多次点击/更换套餐不会盲目新建第二个可付 Session；旧订阅先与 Stripe 对账。
- Pro 10 / Portfolio 50 股票每日快照、姿态比较、JSON 和 Portfolio CSV；保存后降级仍可访问。自动生成需主动启用，邮件不在当前交付范围。
- 价格页、登录回流、报告与观察列表可使用；年费、一次性报告、可选加购和 Web/iOS 独立权益明确。

## 本地验证

| 检查 | 结果 | 范围 |
|---|---|---|
| `python3 scripts/test_isolated.py` | 238 项通过，19.385 秒 | 临时目录；不载入真实账户或支付密钥 |
| iOS XCTest | 46 项，4 跳过，0 失败 | 4 项真实外部服务检查为显式 opt-in，未运行 |
| iOS offline commercial gates | 通过 | 源码及配置静态检查，不能代替真实购买 |
| `p0_smoke --base http://127.0.0.1:8769` | 通过 | 本地 fixture / HTTP，包括无效股票、契约、OAuth 410 |
| contract sample validator | 通过 | INTC fixture，验证生成物未纳入本次修改 |
| 独立只读复核 | 通过本次修复范围 | 支付/退款/旧 worker/账号隔离/日期与历史重建 |
| 页面 375 / 1440 | 无页面横向溢出 | Pricing、Reports、Watchlist；截图见本目录 |
| 本地 CSV HTTP 下载 | 200，183 字节，1 行，Content-Length 一致 | 合成 TESTCO 预览账号；浏览器下载按钮触发正常，不代表真实付款 |
| iOS 模拟器首页 | 可启动并显示日终日期 | 现有本地模拟器数据，不是收益验证 |
| build 8 Release 归档 | ARCHIVE SUCCEEDED，签名检查通过 | App/Widget 1.2.0 (8)，日历字节与源码一致；现已上传并处理为 VALID |

Python 测试仍有三个既有测试 HTTP socket ResourceWarning，没有功能测试失败。

截图：
- [Pricing 桌面](pricing-1440.png)、[手机](pricing-375.png)
- [Reports 桌面](reports-1440.png)、[手机](reports-375.png)
- [Watchlist 桌面](watchlist-1440.png)、[手机结果](watchlist-results-375.png)
- [iOS 模拟器](ios-simulator-home.png)

本机最终归档：`ios/build/launch-build-8-final-20260906/QuantRadar.xcarchive`（gitignored）。

## 正式 Stripe 核查与已执行修复

实际账户已核对为 Fortune Insight LLC。完整分页检查含产品 6、价格 8、Payment Links 5、Checkout 199（2 页）、独立 Checkout 行项目 204（199 次）、订阅 1；各列表最终 has_more=false。

扩展到 QuantRadar 价格、域名及产品后的关联范围：31 个 Checkout，已付 1、开放 0；1 个订阅已取消。历史订单原价 $99、折扣 $98.01，实付 $0.99。不能用这个范围代表整个账户收入。

以下两条绕过账号绑定及防重流程的旧链接已经 POST 停用，并 GET 确认 active=false；操作前完整对象已保存在私有备份，未产生任何扣款：

- `plink_1TDM037uBhbslGrGHh3mTQfm`（Pro 月付）
- `plink_1TDM077uBhbslGrGP3HlYZVg`（Portfolio 月付）

待发布配置：
- Portfolio 现有价格 `price_1TDM067uBhbslGrGtxzYXEq1`，$99/月，active；尚未配置进运行环境。
- 默认 Portal 允许期末取消，但 `subscription_update.enabled=false`；尚不能通过新套餐切换验收。需要测试环境验证后配置独立 Portal，加入当前 Pro 月/年及 Portfolio 价格。
- Webhook 需补全订阅、发票、异步支付、Session 到期、退款事件；尚未更新正式配置。
- Stripe 插件认证已过期，本机无 test key；未运行真实 sandbox 付款/退款/续费/Portal 流程。已请求恢复测试环境连接。

## 生产与备份

生产 Nube 服务保持运行，Web/引擎修复尚未切换，health 仍 v0.7.0 / git_sha=null。无 DNS 变更。

已生成生产准备性热备份并下载本机，SHA-256：
`217d369cd9ee3037914e4de2c85598e74a5b0cecbee9bd850f9b6065d1ced107`

共 296 个 tar 条目，4 个账户/业务 JSON 文件可解析，包含代码、引擎、环境。私有档案不进入 Git。这个热备份不是停机一致性备份；激活新版本之前还必须按 `docs/CORRECT_OPS.md` 做短暂停机备份。回滚只恢复代码，不覆盖新付款数据。

## 剩余商业与外部闸门

1. Yahoo/Nasdaq 商用和下载再分发授权尚未提供；已核实候选方案和成本，见 [DATA_LICENSING](../../DATA_LICENSING.md)。授权范围决定付费文件交付能否发布。
2. 恢复 Stripe 测试环境，执行实际结账→签名 webhook→交付→退款/取消/续费/切换，再更新正式配置和切换服务。
3. Apple 仍是版本 1.0 / build 7 WAITING_FOR_REVIEW；新 build 8 已上传且 VALID，尚未替换审核；替换时须保留 App + IAP 两个审核项目。
4. 没有“保证赚钱”的证据。待上述条件完成，用真实客户的购买、交付、28 日回访、续订、退款与净收入判断效果，不用模拟数据或安装量冒充盈利。

## 同日上传后补充核验

- Xcode export/upload 返回 0，并输出 EXPORT SUCCEEDED。
- App Store Connect 新 build 8：`719a2f67-d5c3-49c3-ab98-7886189b0fe2`，1.2.0，processingState=VALID。
- 再次读取现有商店版本：1.0 / build 7 / WAITING_FOR_REVIEW，AFTER_APPROVAL；本次未取消或替换它。
- 现有版本、英文描述、审核资料、两个 review items、IAP version/本地化/审核图/定价计划/可用性元数据已私有备份。
- 商店当前英文描述仍写 $9.99，和已核验的美国 $9.90 不一致；已准备替换为按地区显示价格的 PATCH 草稿，待可编辑时执行，不篡改排队中的审核。
- 准备的替换请求包含新 build 8、现有 App version 和 IAP version `407ef5c5-194c-4240-832b-9213cfcdf561`；未提交。
- 更低标价候选 Marketstack Basic 为 $9.99/月，但 CSV/JSON 分发权未确认。已准备书面授权询问，等待明确的对外发送授权；未购买。
- Stripe 插件再次返回 UNAUTHORIZED / reauthentication required；真实测试环境仍未恢复。

这次新增工作是上传与核验、发布资料和授权调查；运行代码仍是已通过本地/云端测试、发布包校验及 Nube 隔离启动的 `510707af7eafb31a8056efbefb42febce4efe1ec`。
