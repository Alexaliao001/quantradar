# QuantRadar 发布与运行事实

核验日期：2026-09-06。此文件取代此前的 Render / Manus 部署说明。

## 当前生产

| 项目 | 已核验值 |
|---|---|
| 代码仓库 | https://github.com/Alexaliao001/quantradar |
| 网站 | https://quantradar.one ，www 同源 |
| 主机 | Nube VPS，SSH alias `nube-sin` |
| Web 进程 | systemd `quantradar`，`www-data`，Python 3.12 `python3 -m app` |
| 工作目录 | `/opt/nube-sites/apps/quantradar` |
| 线上独立引擎目录 | `/opt/nube-sites/apps/charts-engine`，由 `CHARTS_DIR` 指定 |
| 环境 | `/opt/nube-sites/secrets/quantradar.env`；不进入 Git、日志或报告 |
| 代理 | Caddy → `127.0.0.1:8765` |
| 数据 | 工作目录的 `data/`；新版本增加 `billing.sqlite3`（WAL） |
| 目前线上 health | v0.7.0，git_sha=null，live；尚未发布本次修复 |

`git_sha=null` 无法证明线上等于某个提交。待发布包加入 `SOURCE_HEAD` 后，必须核对本机提交、包清单和线上 health 三者一致。无需变更 DNS。

## 当前发布前条件

1. 数据许可须覆盖网页、iOS、计算结果及拟出售的 JSON/CSV 下载。公开 API 可访问不等于已有商用授权；见 `DATA_LICENSING.md`。
2. Stripe 测试环境必须验证实际结账、签名 webhook、交付、退款、续费、取消、计划切换。本轮已通过真实 sandbox 验收，见 `docs/audit/2026-09-06/stripe-sandbox.json`。`scripts/audit_billing.py` 拒绝 live key，仅验证金额；生命周期另由浏览器、签名事件和 Test Clock 验证。
3. 正式账户核对遗留 Payment Links、价格、Portal 和 webhook。Portfolio Pro 价格尚未接入，禁止仅靠页面展示宣称可购买。
4. 完成 Python 隔离测试、iOS 测试、375/1440 页面验收、签名归档检查。

已准备独立正式 Portal `bpc_1UCTPA7uBhbslGrGuE1dZAda`，不是默认配置，尚未写入生产环境。允许 Pro 月/年、Portfolio 月切换，差额即时开票，期末取消。正式环境应通过 `STRIPE_PORTAL_CONFIGURATION_ID` 明确选择它。当前 webhook `we_1U6uvl7uBhbslGrG01EauQuf` 仍只有四种旧事件；须随新版一同补全事件配置，不能将已创建 Portal 当作已完成生产接线。

## 发布步骤

1. `python3 scripts/test_isolated.py`；生产或真实账户目录不要直接运行 unittest。
2. 提交并推送经复核的源码。`python3 scripts/package_release.py /absolute/private/output-directory` 只打包已提交的运行文件，拒绝脏工作区；包里不含 `.env`、`data`、缓存或 iOS 签名材料。
3. 上传至 `/opt/nube-sites/releases/quantradar-<commit>/`，先核对 SHA-256 和展开后的 `SHA256SUMS`，不可直接覆盖线上目录。
4. 短暂停止 `quantradar` 后，将当前 Web、独立引擎和环境完整备份到专属私有目录，下载一份到独立主机。确认 JSON 可读；如有 SQLite，使用 backup API 或同时保留一致的主库/WAL。热拷贝只作准备性备份，不能替代停机一致备份。
5. 仅替换 `app/`、`static/`、`free_engine/`、`schemas/`、`fixtures/`、`requirements.txt`、`SOURCE_HEAD` 和清单。同步独立引擎全部 Python 与交易日历 JSON，保持同一提交；保留 `.cache`、`data/` 与 `.env`。
6. 保持 `www-data` 可写数据和引擎缓存，秘密权限不放宽。启动服务，检查本地与公网 `/health` 均为 JSON、提交一致；检查页面、401/404 账号隔离、真实数据日期及完整下载。
7. 实际支付验收在测试环境先完成，再确认正式价格、Portal、签名 webhook 配置。真实客户付款不作为自动化测试手段。

## 回滚

回滚仅恢复前一版本的代码和引擎。不得以旧 `data/` 覆盖新订单、账号、退款或订阅状态。若需要数据迁移回滚，先备份现有数据库并单独设计迁移；不要自动恢复旧付款快照。

## iOS 独立发布

网页 Stripe 与 Apple Unlock 权限独立。build 8（App/Widget 1.2.0）已归档、签名及日历校验通过，并上传 App Store Connect，处理状态 VALID（build ID `719a2f67-d5c3-49c3-ab98-7886189b0fe2`）。App Store Connect 现有版本 1.0 / build 7 为 WAITING_FOR_REVIEW，不能描述为已上架。确认新 build 上传并 VALID 后，才替换原审核构建；新审核提交需同时保留现有 IAP 项，不能只提交 App。

## 证据

本次本地验收：`docs/audit/2026-09-06/README.md`。生产切换后追加新的发布回执，不把本地测试结论改写成生产验证。
