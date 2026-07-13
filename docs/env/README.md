# Env templates by product (SX6-4)
#
# Copy the matching file to the product repo as `.env` (gitignored) or paste into Render.
# Never commit real secrets.

| Product | Template | Production host |
|---------|----------|-----------------|
| QuantRadar | `quantradar.env.example` → also `~/quantradar/.env.example` | Render `quantradar-shell` |
| Fortune Insight | `fortune-insight.env.example` | Render `fortune-insight` |
| MoYu | `moyu.env.example` | GH Pages（无后端密钥） |
| Portfolio | `portfolio.env.example` | GH Pages（静态；Manus 可选） |
| Drama | `drama.env.example` | GH Pages 演示态（全量生成需授权） |
