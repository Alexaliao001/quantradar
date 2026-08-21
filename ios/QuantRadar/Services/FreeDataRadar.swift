import Foundation

struct FreeBar: Hashable, Sendable, Codable {
    let date: Date
    let close: Double
    let volume: Double
}

enum FreeDataSourceID: String, CaseIterable, Sendable {
    case yahooQuery1 = "yahoo_q1"
    case yahooQuery2 = "yahoo_q2"
    case nasdaq = "nasdaq"
}

struct FreeBarsResult: Sendable {
    let bars: [FreeBar]
    let source: FreeDataSourceID
    var fromCache: Bool = false
}

enum FreeMarketDataError: LocalizedError {
    case badSymbol
    case allSourcesFailed([String])
    case parseFailed(FreeDataSourceID)

    var errorDescription: String? {
        switch self {
        case .badSymbol: return "Invalid ticker."
        case .allSourcesFailed(let errs): return "All free sources failed: \(errs.joined(separator: " | "))"
        case .parseFailed(let s): return "Parse failed for \(s.rawValue)."
        }
    }
}

/// Zero-COGS multi-source OHLCV. Order verified 2026-08-11:
/// Yahoo q1 → Yahoo q2 → Nasdaq chart (US equities).
enum FreeMarketDataClient {
    static var sourceOrder: [FreeDataSourceID] = [.yahooQuery1, .yahooQuery2, .nasdaq]
    /// Per-source HTTP timeout (fail-fast failover).
    static var requestTimeout: TimeInterval = 8

    private static let session: URLSession = {
        let config = URLSessionConfiguration.ephemeral
        config.timeoutIntervalForRequest = 8
        config.timeoutIntervalForResource = 12
        config.waitsForConnectivity = false
        config.urlCache = nil
        return URLSession(configuration: config)
    }()

    static func dailyBars(
        symbol: String,
        rangeHintDays: Int = 180,
        bypassCache: Bool = false
    ) async throws -> FreeBarsResult {
        let sym = normalize(symbol)
        guard !sym.isEmpty else { throw FreeMarketDataError.badSymbol }

        if !bypassCache, let cached = await BarsCache.shared.get(sym) {
            return FreeBarsResult(bars: cached.bars, source: cached.source, fromCache: true)
        }

        var errors: [String] = []
        for source in sourceOrder {
            do {
                let bars = try await fetch(source: source, symbol: sym, rangeHintDays: rangeHintDays)
                guard bars.count >= 30 else {
                    errors.append("\(source.rawValue): too few bars (\(bars.count))")
                    continue
                }
                let result = FreeBarsResult(bars: bars, source: source, fromCache: false)
                await BarsCache.shared.set(sym, result: result)
                return result
            } catch {
                errors.append("\(source.rawValue): \(error.localizedDescription)")
            }
        }
        throw FreeMarketDataError.allSourcesFailed(errors)
    }

    static func normalize(_ symbol: String) -> String {
        symbol.trimmingCharacters(in: .whitespacesAndNewlines).uppercased()
    }

    // MARK: - Dispatch

    private static func fetch(source: FreeDataSourceID, symbol: String, rangeHintDays: Int) async throws -> [FreeBar] {
        switch source {
        case .yahooQuery1:
            return try await yahoo(host: "query1.finance.yahoo.com", symbol: symbol, range: yahooRange(rangeHintDays))
        case .yahooQuery2:
            return try await yahoo(host: "query2.finance.yahoo.com", symbol: symbol, range: yahooRange(rangeHintDays))
        case .nasdaq:
            return try await nasdaq(symbol: symbol, rangeHintDays: rangeHintDays)
        }
    }

    private static func yahooRange(_ days: Int) -> String {
        if days <= 30 { return "1mo" }
        if days <= 100 { return "3mo" }
        if days <= 200 { return "6mo" }
        return "1y"
    }

    // MARK: - Yahoo

    private static func yahoo(host: String, symbol: String, range: String) async throws -> [FreeBar] {
        let encoded = symbol.addingPercentEncoding(withAllowedCharacters: .urlPathAllowed) ?? symbol
        guard var components = URLComponents(string: "https://\(host)/v8/finance/chart/\(encoded)") else {
            throw URLError(.badURL)
        }
        components.queryItems = [
            URLQueryItem(name: "range", value: range),
            URLQueryItem(name: "interval", value: "1d"),
            URLQueryItem(name: "includePrePost", value: "false"),
        ]
        guard let url = components.url else { throw URLError(.badURL) }
        let data = try await get(url, headers: [
            "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) QuantRadar/1.0",
            "Accept": "application/json",
        ])
        return try parseYahoo(data)
    }

    private static func parseYahoo(_ data: Data) throws -> [FreeBar] {
        guard
            let root = try JSONSerialization.jsonObject(with: data) as? [String: Any],
            let chart = root["chart"] as? [String: Any],
            let results = chart["result"] as? [[String: Any]],
            let result = results.first,
            let timestamps = result["timestamp"] as? [Double],
            let indicators = result["indicators"] as? [String: Any],
            let quotes = indicators["quote"] as? [[String: Any]],
            let quote = quotes.first,
            let closes = quote["close"] as? [Any],
            let volumes = quote["volume"] as? [Any]
        else { throw FreeMarketDataError.parseFailed(.yahooQuery1) }

        var bars: [FreeBar] = []
        for i in 0..<timestamps.count {
            guard let c = asDouble(closes, i), c > 0 else { continue }
            let v = asDouble(volumes, i) ?? 0
            bars.append(FreeBar(date: Date(timeIntervalSince1970: timestamps[i]), close: c, volume: max(0, v)))
        }
        return bars
    }

    // MARK: - Nasdaq

    private static func nasdaq(symbol: String, rangeHintDays: Int) async throws -> [FreeBar] {
        // Nasdaq API uses BRK.B style; reject obvious non-equities early.
        if symbol.contains("-") || symbol.contains("=") {
            throw URLError(.unsupportedURL)
        }
        let nasdaqSymbol = symbol.replacingOccurrences(of: "-", with: ".")
        let end = Date()
        let start = Calendar.current.date(byAdding: .day, value: -max(60, rangeHintDays), to: end) ?? end
        let fmt = DateFormatter()
        fmt.calendar = Calendar(identifier: .gregorian)
        fmt.locale = Locale(identifier: "en_US_POSIX")
        fmt.timeZone = TimeZone(secondsFromGMT: 0)
        fmt.dateFormat = "yyyy-MM-dd"
        let from = fmt.string(from: start)
        let to = fmt.string(from: end)
        let urlString = "https://api.nasdaq.com/api/quote/\(nasdaqSymbol)/chart?assetclass=stocks&fromdate=\(from)&todate=\(to)"
        guard let url = URL(string: urlString) else { throw URLError(.badURL) }
        let data = try await get(url, headers: [
            "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15",
            "Accept": "application/json, text/plain, */*",
            "Origin": "https://www.nasdaq.com",
            "Referer": "https://www.nasdaq.com/",
        ])
        return try parseNasdaq(data)
    }

    private static func parseNasdaq(_ data: Data) throws -> [FreeBar] {
        guard
            let root = try JSONSerialization.jsonObject(with: data) as? [String: Any],
            let dataObj = root["data"] as? [String: Any],
            let chart = dataObj["chart"] as? [[String: Any]],
            !chart.isEmpty
        else { throw FreeMarketDataError.parseFailed(.nasdaq) }

        var bars: [FreeBar] = []
        for point in chart {
            let close: Double?
            if let y = point["y"] as? Double {
                close = y
            } else if let y = point["y"] as? NSNumber {
                close = y.doubleValue
            } else if let z = point["z"] as? [String: Any] {
                close = doubleFromAny(z["close"] ?? z["value"])
            } else {
                close = nil
            }
            guard let c = close, c > 0 else { continue }
            let ts: Date
            if let x = point["x"] as? Double {
                // Nasdaq x is ms
                ts = Date(timeIntervalSince1970: x / 1000)
            } else if let x = point["x"] as? NSNumber {
                ts = Date(timeIntervalSince1970: x.doubleValue / 1000)
            } else {
                continue
            }
            var volume = 0.0
            if let z = point["z"] as? [String: Any] {
                volume = doubleFromAny(z["volume"]) ?? 0
            }
            bars.append(FreeBar(date: ts, close: c, volume: max(0, volume)))
        }
        return bars.sorted { $0.date < $1.date }
    }

    // MARK: - HTTP

    private static func get(_ url: URL, headers: [String: String]) async throws -> Data {
        var request = URLRequest(url: url)
        request.timeoutInterval = requestTimeout
        request.cachePolicy = .reloadIgnoringLocalCacheData
        for (k, v) in headers { request.setValue(v, forHTTPHeaderField: k) }
        let (data, response) = try await session.data(for: request)
        guard let http = response as? HTTPURLResponse else { throw URLError(.badServerResponse) }
        guard (200..<300).contains(http.statusCode) else {
            throw URLError(.init(rawValue: http.statusCode))
        }
        return data
    }

    private static func asDouble(_ arr: [Any], _ i: Int) -> Double? {
        guard i < arr.count else { return nil }
        return doubleFromAny(arr[i])
    }

    private static func doubleFromAny(_ any: Any?) -> Double? {
        guard let any, !(any is NSNull) else { return nil }
        if let d = any as? Double { return d }
        if let n = any as? NSNumber { return n.doubleValue }
        if let s = any as? String {
            let cleaned = s.replacingOccurrences(of: ",", with: "")
            return Double(cleaned)
        }
        return nil
    }
}

enum QuoteFundamentals: Sendable {
    case missing
    case loaded(sector: String?, earningsDate: Date?)

    var sector: String? {
        if case .loaded(let s, _) = self { return s }
        return nil
    }

    var earningsDate: Date? {
        if case .loaded(_, let d) = self { return d }
        return nil
    }
}

extension FreeMarketDataClient {
    /// Yahoo quoteSummary — fail-open. Never blocks a scan.
    static func fundamentals(symbol: String) async -> QuoteFundamentals {
        let sym = normalize(symbol)
        guard !sym.isEmpty else { return .missing }
        let encoded = sym.addingPercentEncoding(withAllowedCharacters: .urlPathAllowed) ?? sym
        guard var components = URLComponents(string: "https://query1.finance.yahoo.com/v10/finance/quoteSummary/\(encoded)") else {
            return .missing
        }
        components.queryItems = [
            URLQueryItem(name: "modules", value: "assetProfile,calendarEvents"),
        ]
        guard let url = components.url else { return .missing }
        do {
            let data = try await get(url, headers: [
                "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) QuantRadar/1.2",
                "Accept": "application/json",
            ])
            return parseFundamentals(data)
        } catch {
            return .missing
        }
    }

    static func parseFundamentals(_ data: Data) -> QuoteFundamentals {
        guard
            let root = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
            let qs = root["quoteSummary"] as? [String: Any],
            let results = qs["result"] as? [[String: Any]],
            let result = results.first
        else { return .missing }

        var sector: String?
        if let profile = result["assetProfile"] as? [String: Any] {
            sector = profile["sector"] as? String
        }
        var earnings: Date?
        if
            let cal = result["calendarEvents"] as? [String: Any],
            let earn = cal["earnings"] as? [String: Any],
            let dates = earn["earningsDate"] as? [[String: Any]],
            let first = dates.first
        {
            if let raw = first["raw"] as? Double {
                earnings = Date(timeIntervalSince1970: raw)
            } else if let raw = first["raw"] as? NSNumber {
                earnings = Date(timeIntervalSince1970: raw.doubleValue)
            }
        }
        if sector == nil && earnings == nil { return .missing }
        return .loaded(sector: sector, earningsDate: earnings)
    }
}

enum FreeMechanicalScorer {
    struct Core: Equatable {
        var score: Double
        var action: String
        var label: String
        var reason: String
        var summary: String
        var marketGate: String
        var stockGate: String
        var spyPct: Double?
        var avoided: String?
        var pullback: Double
        var rsi: Double?
    }

    static func core(bars: [FreeBar], spyBars: [FreeBar]?) -> Core {
        let closes = bars.map(\.close)
        let volumes = bars.map(\.volume)
        let last = closes.last ?? 0
        let sma20 = sma(closes, 20)
        let sma50 = sma(closes, 50)
        let rsi = rsi14(closes)
        let volSma = sma(volumes, 20)
        let volRatio = (volSma > 0) ? (volumes.last ?? 0) / volSma : 1
        let pullback = sma20 > 0 ? (sma20 - last) / sma20 * 100 : 0

        var score = 50.0
        if sma20 > 0, sma50 > 0 {
            if last > sma20 && sma20 > sma50 { score += 18 }
            else if last > sma20 { score += 8 }
            else if last < sma50 { score -= 18 }
            else { score -= 8 }
        }
        if let r = rsi {
            if r >= 45 && r <= 65 { score += 12 }
            else if r > 70 { score -= 10 }
            else if r < 30 { score += 4 }
            else { score += 2 }
        }
        if volRatio >= 1.2 { score += 8 }
        else if volRatio < 0.7 { score -= 4 }

        var marketGate = "PASS"
        var spyPct: Double?
        if let spy = spyBars, spy.count >= 5 {
            let a = spy[spy.count - 5].close
            let b = spy.last!.close
            spyPct = (b - a) / a * 100
            if let p = spyPct, p < -3 { marketGate = "WATCH"; score -= 10 }
            if let p = spyPct, p < -6 { marketGate = "NO"; score -= 15 }
        }

        score = min(95, max(5, score.rounded()))

        let action: String
        let label: String
        let reason: String
        if marketGate == "NO" || score < 38 {
            action = "NO"
            label = "Avoid"
            reason = "Posture is weak or the market gate is blocked — do not force a trade."
        } else if score >= 68 && pullback >= -2 && pullback <= 8 && (rsi ?? 50) < 68 {
            action = "SETUP"
            label = "Setup zone"
            reason = String(format: "Trend supportive, RSI %.0f, pullback %.1f%% from SMA20.", rsi ?? 0, max(0, pullback))
        } else {
            action = "WAIT"
            label = "Wait & Watch"
            reason = String(format: "Score %.0f — timing not fully aligned (RSI %.0f).", score, rsi ?? 0)
        }

        let stockGate = action == "SETUP" ? "PASS" : (action == "NO" ? "NO" : "WATCH")
        let summary: String
        if action == "SETUP" {
            summary = "Timing is in a setup zone. Educational radar only — not a buy order."
        } else if action == "NO" {
            summary = "Posture says stay out. Skipping a forced trade is the point of the radar."
        } else {
            summary = "Posture is cautious. Wait until timing lines up."
        }
        return Core(
            score: score,
            action: action,
            label: label,
            reason: reason,
            summary: summary,
            marketGate: marketGate,
            stockGate: stockGate,
            spyPct: spyPct,
            avoided: action == "SETUP" ? nil : "Skipping a forced entry preserves optionality.",
            pullback: pullback,
            rsi: rsi
        )
    }

    static func score(
        symbol: String,
        company: String?,
        bars: [FreeBar],
        spyBars: [FreeBar]?,
        source: FreeDataSourceID,
        earningsDate: Date? = nil,
        sectorName: String? = nil,
        sectorAction: String? = nil,
        now: Date = Date()
    ) -> RadarVerdict {
        var c = core(bars: bars, spyBars: spyBars)
        var earningsForced = false
        if let earningsDate, PostureDepth.isNearEarnings(earningsDate, now: now), c.action == "SETUP" {
            c.action = "WAIT"
            c.label = "Wait & Watch"
            c.reason = "Earnings within 3 days — radar stays on wait."
            c.summary = "Earnings window: posture stays on wait. Educational only — not a buy order."
            c.stockGate = "WATCH"
            earningsForced = true
        }
        var sectorGate = "N/A"
        if let sectorAction {
            sectorGate = sectorAction == "NO" ? "NO" : (sectorAction == "SETUP" ? "PASS" : "WATCH")
            if sectorAction == "NO" && c.action == "SETUP" {
                c.action = "WAIT"
                c.label = "Wait & Watch"
                c.reason = "Sector posture is blocked — wait even if the stock looks ready."
                c.summary = "Sector gate is closed. Wait until the group improves."
                c.stockGate = "WATCH"
            }
        }
        let etf = PostureDepth.etf(forSector: sectorName)
        let depth = PostureDepth.build(
            bars: bars,
            spyBars: spyBars,
            earningsDate: earningsDate,
            now: now,
            earningsForcedWait: earningsForced,
            sectorEtf: etf
        )
        return RadarVerdict(
            ok: true,
            ticker: symbol,
            companyName: company ?? symbol,
            sector: sectorName ?? etf,
            primaryScore: .init(
                value: c.score,
                scale: 100,
                label: "Mechanical posture score",
                withheld: false,
                note: nil
            ),
            primary: .init(action: c.action, label: c.label, reason: c.reason),
            summary: c.summary,
            engagement: .init(
                avoidedLine: c.avoided,
                freezeLabel: "on-device",
                postureNote: "Mechanical posture ≠ trade direction."
            ),
            dataQuality: .init(usable: true, reliability: "medium", optionsActionable: false),
            market: .init(
                marketState: c.marketGate == "PASS" ? "risk_on_cautious" : "risk_off",
                spyChangePct: c.spyPct,
                sectorEtf: etf,
                sectorChangePct: nil,
                vixCurrent: nil,
                vixTrend: nil
            ),
            meta: .init(
                mode: "free_multi_source",
                fetchTime: ISO8601DateFormatter().string(from: Date()),
                disclaimer: "Educational radar only — not investment advice.",
                dataPath: source.rawValue
            ),
            gate: .init(market: c.marketGate, sector: sectorGate, stock: c.stockGate),
            warnings: ["Options data is not part of this radar."],
            depth: depth
        )
    }

    private static func sma(_ xs: [Double], _ n: Int) -> Double {
        guard xs.count >= n else { return 0 }
        return xs.suffix(n).reduce(0, +) / Double(n)
    }

    private static func rsi14(_ closes: [Double]) -> Double? {
        guard closes.count > 15 else { return nil }
        var gains = 0.0
        var losses = 0.0
        let slice = Array(closes.suffix(15))
        for i in 1..<slice.count {
            let d = slice[i] - slice[i - 1]
            if d >= 0 { gains += d } else { losses -= d }
        }
        let ag = gains / 14
        let al = losses / 14
        if al == 0 { return 100 }
        let rs = ag / al
        return 100 - (100 / (1 + rs))
    }
}
