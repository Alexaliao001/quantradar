# QuantRadar 本次验收记录

日期：2026-09-06。状态：修复、本地验收及真实 Stripe 测试环境验收完成，商业全量发布尚未完成。此记录将源码、测试、正式账户和商店状态分开。

## 改动与用途

- Web / iOS / Widget 只使用完成的交易日；纽约节假日与提前收市共用 2026–2028 日历，缺数据为 UNKNOWN，SPY/个股日期对齐。Yahoo 两个入口只算一个来源；跨收市缓存不能掩盖旧数据。
- Web 并发取数限制为 2 个进程，相同请求合并与短时缓存。账号隔离的扫描记录保存实际收盘日期及价格，不用“扫描后收益”包装日线差值。
- 单股报告在结账前验证 90 日重建所需覆盖并冻结输入；SQLite 记录订单、付款、退款和事件。异步生成 JSON/图表/CSV，重试及 worker lease 避免迟到结果覆盖交付。
- 每个账号只有一个可恢复的订阅结账尝试，网络失败/多次点击/更换套餐不会盲目新建第二个可付 Session；旧订阅先与 Stripe 对账。
- 真实退款测试发现旧优惠结账链接会阻塞再次订阅：现在返回链接前重新核对价格和当前抵扣资格；退款 worker 确认未完成的优惠 Checkout 已失效后才完成撤销，网络失败可重试。
- Pro 10 / Portfolio 50 股票每日快照、姿态比较、JSON 和 Portfolio CSV；保存后降级仍可访问。自动生成需主动启用，邮件不在当前交付范围。
- 价格页、登录回流、报告与观察列表可使用；年费、一次性报告、可选加购和 Web/iOS 独立权益明确。

## 本地验证

| 检查 | 结果 | 范围 |
|---|---|---|
| `python3 scripts/test_isolated.py` | 244 项通过，19.413 秒 | 临时目录；不载入真实账户或支付密钥；含 6 项退款结账回归 |
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
- 原默认 Portal 允许期末取消，但 `subscription_update.enabled=false`，不能承载新套餐切换。
- 测试验收后已创建并 GET 展开核对独立正式 Portal `bpc_1UCTPA7uBhbslGrGuE1dZAda`：允许 Pro 月/年与 Portfolio 月套餐切换、即时结算差额、期末取消、付款方式和发票管理。它不是默认配置，尚未接入生产环境；旧默认 Portal 未修改。
- Webhook 需补全订阅、发票、异步支付、Session 到期、退款事件；尚未更新正式配置。
- Stripe 插件认证仍过期，但已通过用户登录的 Chrome JJ 工作账号取得测试访问，完整测试流程已完成，见下节。

## 真实 Stripe 测试环境验收

账号 `acct_1SwTY37uBhbslGrG`；所有付款对象 `livemode=false`。隔离的 Nube Python 3.12 应用经 SSH 隧道供浏览器访问；仅载入测试密钥与 Stripe CLI 的签名 secret，未启用 webhook 绕过。行情采用合成 TESTCO 数据，不代表真实市场表现。脱敏回执：[stripe-sandbox.json](stripe-sandbox.json)。

| 流程 | 实际结果 |
|---|---|
| 六种 Checkout 金额 | $9 报告、$14 含 CSV、$29 月、$249 年、报告抵扣后 $20 月、$99 Portfolio 均正确；金额检查 Session 已关闭 |
| 美元报告购买 | 浏览器用官方测试卡付 $14；签名回调后 ready；JSON 含 90 个交易日，CSV 12,217 字节、ZIP 10,421 字节；其他账号下载返回 404 |
| 英镑自适应定价 | 浏览器付 £10.77；Session 集成金额仍为 USD 1,400 分，`presentment_details` 为 GBP 1,077；2026-01-28.clover 事件处理后报告 ready |
| 报告退款 | 两笔测试报告均全额退款成功，账号不再可下载；第二笔验证后台自动关闭 $20 优惠 Checkout 并将 credit 标记 revoked，再次结账为新 $29 Session |
| 月订阅与升级 | 浏览器付 $29 后 app=pro；Portal 升级 Portfolio，显示并支付 $70 差额，下期 $99；签名回调后 app=portfolio_pro |
| Portal 取消 | UI 确认 2026-10-06 终止，当前权益仍为 portfolio_pro。实际对象以 `cancel_at` 等于 item 的 period end 表示期末取消，`cancel_at_period_end` 为 false，不能仅凭这个布尔值判断失败 |
| Test Clock 续费与到期 | 首付及下一周期发票各 $29 paid；期末取消后 Stripe=canceled、app=free |
| 扣款失败与补缴 | 官方失败测试支付方式使下一周期 past_due、app=free；换回成功方式并补缴后 active、app=pro |
| 回调与独立复核 | 39 次签名事件转发返回 200、0 次非 2xx；只读复核另做 10 项定向验证，未发现本次 diff 的剩余可复现 P1/P2 |

退款前创建的旧 $20 Session 在旧代码下仍显示 open，但浏览器显示错误；没有观察到退款后成功按优惠价扣款。修复针对已复现的重结账阻塞和撤销未完成问题，不能描述为已证实的扣款漏洞。

这些是实际 Stripe sandbox 对象及测试时钟事件，不是真实收入，也不代表生产支付已经切换。

验收后已取消两条尚在存续的测试订阅、关闭剩余可付测试链接、删除测试时钟，测试账号最终为 free。隔离服务、SSH 隧道、临时 CLI、Cookie 和测试凭据已清理；保留测试产品/价格/Portal 供后续复验。正式配置准备回执：[stripe-production-prepared.json](stripe-production-prepared.json)，尚未应用到生产运行环境。

## 生产与备份

生产 Nube 服务保持运行，Web/引擎修复尚未切换，health 仍 v0.7.0 / git_sha=null。无 DNS 变更。

已生成生产准备性热备份并下载本机，SHA-256：
`217d369cd9ee3037914e4de2c85598e74a5b0cecbee9bd850f9b6065d1ced107`

共 296 个 tar 条目，4 个账户/业务 JSON 文件可解析，包含代码、引擎、环境。私有档案不进入 Git。这个热备份不是停机一致性备份；激活新版本之前还必须按 `docs/CORRECT_OPS.md` 做短暂停机备份。回滚只恢复代码，不覆盖新付款数据。

## 剩余商业与外部闸门

1. Yahoo/Nasdaq 商用和下载再分发授权尚未提供；已核实候选方案和成本，见 [DATA_LICENSING](../../DATA_LICENSING.md)。授权范围决定付费文件交付能否发布。
2. Stripe 测试生命周期已通过，独立正式 Portal 已准备。取得数据授权后，再配套更新生产 Portal/价格/Webhook 并切换服务，完成公网验收。
3. Apple 仍是版本 1.0 / build 7 WAITING_FOR_REVIEW；新 build 8 已上传且 VALID，尚未替换审核；替换时须保留 App + IAP 两个审核项目。
4. 没有“保证赚钱”的证据。待上述条件完成，用真实客户的购买、交付、28 日回访、续订、退款与净收入判断效果，不用模拟数据或安装量冒充盈利。

## 同日上传后补充核验

- Xcode export/upload 返回 0，并输出 EXPORT SUCCEEDED。
- App Store Connect 新 build 8：`719a2f67-d5c3-49c3-ab98-7886189b0fe2`，1.2.0，processingState=VALID。
- 再次读取现有商店版本：1.0 / build 7 / WAITING_FOR_REVIEW，AFTER_APPROVAL；本次未取消或替换它。
- 现有版本、英文描述、审核资料、两个 review items、IAP version/本地化/审核图/定价计划/可用性元数据已私有备份。
- 商店当前英文描述仍写 $9.99，和已核验的美国 $9.90 不一致；已准备替换为按地区显示价格的 PATCH 草稿，待可编辑时执行，不篡改排队中的审核。
- 准备的替换请求包含新 build 8、现有 App version 和 IAP version `407ef5c5-194c-4240-832b-9213cfcdf561`；未提交。
- 更低标价候选 Marketstack Basic/Starter 为 $9.99/月，但 CSV/JSON 分发权未确认。书面授权询问现已发送，等待供应商答复；未购买。
- 当时 Stripe 插件返回 UNAUTHORIZED；之后已使用 JJ 账号完成真实测试验收，见上节。

上传时的运行代码为 `510707af7eafb31a8056efbefb42febce4efe1ec`；此后新增退款结账修复，必须使用包含该修复的新发布包，不能将旧包当作最终代码。

## 同日继续处理：授权询问已发送

- 07:15:28（Asia/Shanghai）通过 `fortuneinsight@outlook.com` 向 `support@apilayer.com` 发送 [授权询问](../../MARKETSTACK_LICENSE_INQUIRY.md)，Outlook 查询已核对主题、收件人、正文与时间。邮件不构成订单、合同接受或授权已获批。
- 07:15:41 收到 APILayer 自动回执，工单 **307916**；其说明周一办公时间处理。回执不等于商用及下载再分发授权。
- 用户在 Chrome JJ 工作账号登录后，测试认证已恢复。临时使用官方 Stripe CLI 1.50.10，下载校验通过；密钥、Cookie 和完整敏感回执不入库。
- App Store Connect 再次确认 build 8 为 VALID；当前版本仍选 build 7，WAITING_FOR_REVIEW / AFTER_APPROVAL。生产 health 仍为 v0.7.0 / git_sha=null；未切换新版。
- PR #5 新增退款结账修复及六项回归，244 项隔离测试通过；未把发送邮件、sandbox 付款或已准备 Portal 计作数据授权、生产切换或盈利。
