# Manus 同步与发布（用户操作）

**架构路径 C**：GitHub `quantradar` = 产品壳；分析重逻辑在 `stock-charts`/`~/charts`（若壳构建需要引擎 artifact，见 goal `QR0-3` 后续说明）。

本机代理 **push 到 GitHub 后**，由你完成：

1. 打开 Manus 中 QuantRadar 项目工作区  
2. **Pull / Sync** 自 `https://github.com/Alexaliao001/quantradar`（以 Manus UI 实际按钮为准）  
3. 确认 commit / `git_sha` 与 GitHub `main` 一致（实现 `/health` 后核对此字段）  
4. 配置/检查环境变量（见将来 `docs/ENV.md`，勿把 key 写进仓库）  
5. **Publish / Deploy** 到 `quantradar.one`  
6. 烟雾：首页 → 访客 sample（若有）→ `/health`  


## 禁止

- 在 Manus 里做大改却不 push 回 GitHub  
- 未 pull 最新 main 就发布  

## 回滚

GitHub 上 `git revert` 或回退到上一 tag → push → Manus 再 pull 发布。
