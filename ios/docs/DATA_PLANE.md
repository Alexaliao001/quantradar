# Data plane split (locked)

| Surface | Data | Cost |
|---------|------|------|
| **Web** | Massive / Polygon | Paid API |
| **iOS** | Free multi-source · on-device score | **$0 COGS** |

## iOS source chain (tested 2026-08-11)

| Order | Source | Verified |
|------|--------|----------|
| 1 | Yahoo `query1` chart API | AAPL/INTC/F/SPY/BRK-B/BTC-USD |
| 2 | Yahoo `query2` chart API | same family, independent host |
| 3 | Nasdaq quote chart API | US equities (AAPL/INTC/F); ETFs like SPY may fail → failover |

Rejected for production chain:

- Stooq — JS bot wall (HTML challenge)
- Twelve Data `demo` — AAPL only
- Alpha/Finnhub/FMP/Polygon — need keys or 401

## Rules

1. Never call Massive / `quantradar.one/api/analyze` in App Store builds.
2. Fail-closed if all free sources fail.
3. Market copy: educational free-data radar — not web Massive parity.
