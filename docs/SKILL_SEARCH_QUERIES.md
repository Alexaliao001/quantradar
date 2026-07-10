# Skill / 技术 搜索查询轮换表（X + 本地）

每轮从下表取 **≥2 组** X 查询（或等价语义搜索），勿连续 3 轮完全相同。

## X / Twitter 查询

1. `"agent skill" OR SKILL.md (trading OR quant OR fintech OR "stock analysis")`
2. `(skills OR "agent skills") (dashboard OR "next.js" OR react) (github OR open-source)`
3. `multi-agent (stock OR trading) (FastAPI OR yfinance OR SSE)`
4. `"design skill" OR "web design" skill (agent OR claude OR cursor) landing OR dashboard`
5. `(quant OR "options chain") (skill OR agent) (greeks OR IV OR polygon OR yfinance)`
6. `skill (redis OR rate-limit OR observability) (trading OR fintech) agent`
7. `"SKILL.md" (finance OR markets OR portfolio)`
8. `(MengTo OR "agent skills" OR anthropicskills) (design OR UI)` — 设计向

## 本地扫描命令

```bash
ls ~/.grok/skills ~/.claude/skills ~/.agents/skills 2>/dev/null
# 主题相关再 read SKILL.md
agent-reach doctor --json   # 若走社交/X 抓取
```

## GitHub 补充（可选，每 5 轮）

- `topic:claude-skills` / `agent skills` + `trading`
- 已知高质量 skill 结构参考（写入 inherit 再决定是否 clone）

## 输出

结果写入 `docs/SKILL_INHERIT.md`，过 `GROK_GOAL.md` §4.3 三关判定。
