# 数据授权与成本核实

核验日期：2026-09-06。以下是官方公开资料和项目内查找结果，不代表已签合同。当前未在项目文档找到 Yahoo/Nasdaq 商用及再分发授权；已向项目所有者询问是否另有授权。

Nasdaq 当前条款第 6/7 节对个人非商用、出售/分发及衍生用途有限制，不能从公开端点可访问推定可售卖数据报告：[Nasdaq Legal](https://www.nasdaq.com/legal)。Yahoo 也需确认适用授权，而非仅依赖项目代码的 MIT 许可。

## 候选方案（未购买，Marketstack 已询问）

| 方案 | 官网月付起价 | 与当前产品相关的限制 |
|---|---:|---|
| Marketstack Basic | $9.99/月 | 定价页明确列 Commercial Use；网页/iOS 展示、JSON/CSV 再分发和订阅终止后已购文件保留权仍待确认 |
| Twelve Data Venture | $499/月 | 面向客户的商业展示；JSON/CSV 再分发仍需单独书面约定 |
| Twelve Data Enterprise | $1,099/月 | 页面列外部分发能力，但具体数据、区域、下载和交易所费用仍须合同确认 |
| Massive Stocks Business | $2,499/月 | 商用/展示、FMV 盘中及 SIP 日终；下载、再分发、历史日线完整性需按实际用例确认 |

来源：[Twelve Data 商业价格](https://twelvedata.com/pricing-business)、[商业与个人用途](https://support.twelvedata.com/en/articles/5332349-commercial-and-personal-usage)、[条款](https://twelvedata.com/terms)、[Massive Stocks](https://massive.com/stocks)。官网价不是 QuantRadar 已取得的完整报价。补充来源：[Marketstack 定价](https://marketstack.com/pricing/)、[服务协议](https://marketstack.com/agreement)。Marketstack 的更低标价说明不能把 $499 当作商用数据的市场最低成本；但也不能仅凭 Commercial Use 标签宣称已取得付费 CSV/JSON 再分发权。

仅以 $29/月毛收入覆盖表中数据月费，依次至少需要 1 / 18 / 38 / 87 个订阅；以 $99/月则需 1 / 6 / 12 / 26 个。此算式未计支付手续费、退款、税、服务器、支持、获客及附加许可，不能作为净利润预测。

## 需要明确写入供应商答复的用例

- 美国股票与 ETF 完整日终 OHLCV，至少 139 个交易日，含 SPY/行业 ETF；覆盖与复权方法不能静默变更。
- 网页和 iOS 客户端展示、服务器缓存、机械评分及历史重建。
- 付费单股 JSON/CSV、4 张图、观察列表 JSON/CSV；允许范围、保留期限、终止后的已购文件访问。
- 免费来宾、注册用户、订阅用户、网站域名和 iOS 包名，是否按用户、交易所或设备另计费用。
- 历史数据及衍生结果是否可转出；第三方署名、归属、记录和删除要求。

优先确认低成本日终商用授权及下载边界。现阶段不据此购买高额订阅，也不在授权未明时扩大收费数据分发。若只有展示许可，应先调整交付承诺和价格，再上线相应版本。

补充排查：[EODHD 商用说明](https://eodhd.com/financial-apis/commercial-vs-personal-license-use)明确其一般定价页套餐仅供个人使用，商用需另行报价，不能把个人 API 套餐当作可售卖报告的授权。未购买套餐。

已于 2026-09-06 07:15（Asia/Shanghai）从公司 Outlook 邮箱向 APILayer 官方支持邮箱发送 [Marketstack 授权询问](MARKETSTACK_LICENSE_INQUIRY.md)，并核对发送记录，当前等待书面答复。最新 APILayer 套餐页将 $9.99/月方案称为 Starter，因此询问中使用 Basic/Starter，见 [官方套餐页](https://app.apilayer.com/signup/marketstack/starter)。其官网页脚另链接 [APILayer 法律条款入口](https://www.ideracorp.com/legal/APILayer)；实际许可须与订单和数据使用范围一并确认。

APILayer 已自动确认工单 **307916**，说明周一办公时间处理；尚无实质授权或报价答复。
