# QuantRadar 商业冲刺 · 一轮执行

继续 QuantRadar 商业冲刺（Desk→Revenue）。

SSOT：先完整读 `~/quantradar/GROK_GOAL_COMMERCIAL.md`（QD 轨道 + 编排 SOP + 红线）；
边界与铁律从 `~/quantradar/GROK_GOAL.md` v3（路径 C、单写者、Skill 采掘环）。

本轮任务：
- 若本条消息末尾指定了 QD-ID，执行该任务；
- 否则按文档 §五推荐序取下一个 ⬜ QD-ID。

强制守规：
1. `git -C ~/quantradar pull --rebase` 后开工；TodoWrite 建轮内清单
2. explore 子代理 ≤2 个且只读；全仓唯一写者是主 agent
3. 验证闸门：`python3 -m unittest discover tests` 全绿；UI 改动出 375/1440 截图存 `docs/audit/{date}/`；计费一律先 Stripe test mode；密钥零入库零打印
4. 契约 / 计费 / auth 改动完成后必跑 verifier（bugbot）复审
5. 卡住走 L1 本机 skill → L2 仓内 → L3 X 双源比对，记 `docs/SKILL_INHERIT.md`
6. 收尾：commit `qr(QD-ID): …` → push → `PROGRESS.md` 一行 → 结束语含「可 Manus pull 发布」→ 回写 GROK_GOAL_COMMERCIAL.md 状态（覆盖 QR-ID 时同步 GROK_GOAL.md）

红线（违反即停）：假社会证明 / 假稀缺 / cancel 迷宫 / 伪造 Greeks 或新鲜度 / QD1-0 裁决前把 live 吹成已可用 / 第三方 tracker。
