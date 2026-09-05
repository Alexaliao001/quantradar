import Foundation

/// 90-day replay, forward evidence, earnings window, sector ETF map.
/// Pure functions — no network. Replay calls `FreeMechanicalScorer.core` only
/// (never `score`) so history cannot recurse.
enum PostureDepth {
    static let historyDays = 90
    static let minBarsForDay = 50
    static let earningsWindowDays = 3

    static let sectorETF: [String: String] = [
        "XLK": "Tech",
        "XLF": "Financials",
        "XLE": "Energy",
        "XLV": "Health",
        "XLY": "Cons. disc.",
        "XLP": "Cons. staples",
        "XLI": "Industrials",
        "XLB": "Materials",
        "XLRE": "Real estate",
        "XLU": "Utilities",
        "XLC": "Comm.",
    ]

    static func etf(forSector sector: String?) -> String? {
        guard let sector, !sector.isEmpty else { return nil }
        let s = sector.lowercased()
        if s.contains("technolog") { return "XLK" }
        if s.contains("financ") { return "XLF" }
        if s.contains("energy") { return "XLE" }
        if s.contains("health") { return "XLV" }
        if s.contains("cyclical") || s.contains("discretion") { return "XLY" }
        if s.contains("defensive") || s.contains("staple") { return "XLP" }
        if s.contains("industrial") { return "XLI" }
        if s.contains("material") || s.contains("basic") { return "XLB" }
        if s.contains("real estate") { return "XLRE" }
        if s.contains("utilit") { return "XLU" }
        if s.contains("communicat") { return "XLC" }
        let upper = sector.uppercased()
        if sectorETF[upper] != nil { return upper }
        return nil
    }

    static func nyCalendar() -> Calendar {
        var cal = Calendar(identifier: .gregorian)
        cal.timeZone = TimeZone(identifier: "America/New_York") ?? .gmt
        return cal
    }

    static func daysUntilEarnings(_ earnings: Date, now: Date = Date()) -> Int {
        let cal = nyCalendar()
        let a = cal.startOfDay(for: now)
        let b = cal.startOfDay(for: earnings)
        return cal.dateComponents([.day], from: a, to: b).day ?? 0
    }

    static func isNearEarnings(_ earnings: Date, now: Date = Date()) -> Bool {
        let d = daysUntilEarnings(earnings, now: now)
        return d >= -earningsWindowDays && d <= earningsWindowDays
    }

    static func median(_ xs: [Double]) -> Double? {
        guard !xs.isEmpty else { return nil }
        let s = xs.sorted()
        let m = s.count / 2
        if s.count % 2 == 0 {
            return (s[m - 1] + s[m]) / 2
        }
        return s[m]
    }

    static func replayActions(bars: [FreeBar], spyBars: [FreeBar]?) -> [String] {
        guard bars.count >= minBarsForDay else { return [] }
        let start = max(minBarsForDay - 1, bars.count - historyDays)
        var out: [String] = []
        out.reserveCapacity(bars.count - start)
        let datedSPY = (spyBars ?? []).map { (MarketCalendar.barDay($0.date), $0) }
        for i in start..<bars.count {
            let slice = Array(bars.prefix(i + 1))
            var spySlice: [FreeBar]?
            if spyBars != nil {
                let day = MarketCalendar.barDay(bars[i].date)
                let aligned = datedSPY.filter { $0.0 <= day }.map { $0.1 }
                if let last = aligned.last, MarketCalendar.barDay(last.date) == day {
                    spySlice = aligned
                }
            }
            let core = FreeMechanicalScorer.core(
                bars: slice,
                spyBars: spySlice
            )
            out.append(core.action)
        }
        return out
    }

    static func build(
        bars: [FreeBar],
        spyBars: [FreeBar]?,
        earningsDate: Date?,
        now: Date = Date(),
        earningsForcedWait: Bool,
        sectorEtf: String?
    ) -> RadarVerdict.Depth {
        let history = replayActions(bars: bars, spyBars: spyBars)
        let start = max(minBarsForDay - 1, bars.count - historyDays)
        var fwd5: [Double] = []
        var fwd20: [Double] = []
        var lastSetupIndex: Int?
        for (j, action) in history.enumerated() where action == "SETUP" {
            let barIndex = start + j
            lastSetupIndex = barIndex
            if barIndex + 5 < bars.count {
                let a = bars[barIndex].close
                let b = bars[barIndex + 5].close
                if a > 0 { fwd5.append((b - a) / a * 100) }
            }
            if barIndex + 20 < bars.count {
                let a = bars[barIndex].close
                let b = bars[barIndex + 20].close
                if a > 0 { fwd20.append((b - a) / a * 100) }
            }
        }
        var lastAgo: Int?
        var lastFwd: Double?
        if let idx = lastSetupIndex, idx < bars.count - 1, bars[idx].close > 0 {
            lastAgo = bars.count - 1 - idx
            lastFwd = (bars[bars.count - 1].close - bars[idx].close) / bars[idx].close * 100
        }
        var earnDays: Int?
        if let earningsDate {
            earnDays = daysUntilEarnings(earningsDate, now: now)
        }
        return RadarVerdict.Depth(
            history: history,
            setupCount: history.filter { $0 == "SETUP" }.count,
            medianForward5dPct: median(fwd5),
            medianForward20dPct: median(fwd20),
            lastSetupAgoDays: lastAgo,
            lastSetupForwardPct: lastFwd,
            earningsDays: earnDays,
            earningsForcedWait: earningsForcedWait,
            sectorEtf: sectorEtf
        )
    }
}
