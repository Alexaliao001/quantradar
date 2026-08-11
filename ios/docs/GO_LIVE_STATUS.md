# GO LIVE status

**Resubmitted 2026-08-11** with performance build — **WAITING_FOR_REVIEW**.

- App ID: `6800090745` · Bundle: `one.quantradar.app` · SKU: `quantradar-ios`
- Version **1.0** · Build **3** (`46a1633b-753a-4b33-824f-2977d24ad233`) · Price **$9.99**
- Review submission: `ce92d66d-eeaa-4566-a7b4-3d982a0c7be2`
- Release: after approval

## Simulator verification (build 3)

- Unit tests **9/9** passed
- Installed on iPhone 17 sim; Today warm-up shows live SPY via `yahoo_q1` + cached path copy
- Screenshots: `ios/docs/sim-perf-01-launch.png`, `sim-perf-02-today.png`, `sim-perf-03-today-live.png`

## Build 3 includes

- Bars memory+disk cache (SPY 30m / ticker 15m)
- HTTP timeout 8s fail-fast failover
- Today SPY warm-up + refresh
- Watchlist concurrent refresh (max 2)

## Watch

- Review contact phone is still placeholder `+14155550100` — update if Apple calls
- EU DSA non-trader status may need trader compliance for EU sales later
