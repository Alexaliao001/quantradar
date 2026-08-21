import Foundation

struct SectorChip: Identifiable, Hashable {
    var id: String { etf }
    let etf: String
    let label: String
    let action: String
}

@MainActor
final class RadarService: ObservableObject {
    @Published private(set) var demo: RadarVerdict?
    @Published private(set) var latest: RadarVerdict?
    @Published private(set) var todayVerdict: RadarVerdict?
    @Published private(set) var sectorHeat: [SectorChip] = []
    @Published private(set) var lastSource: String?
    @Published private(set) var isLoading = false
    @Published private(set) var isWarmingUp = false
    @Published var errorMessage: String?

    private var warmUpStarted = false

    private var debugAnalyzeOverride: URL? {
        guard let raw = UserDefaults.standard.string(forKey: "qr.debug.analyze.base"),
              let url = URL(string: raw), !raw.isEmpty,
              UserDefaults.standard.bool(forKey: "qr.debug.allow_web_analyze") else {
            return nil
        }
        return url
    }

    func loadDemo() {
        guard let url = Bundle.main.url(forResource: "SampleVerdict", withExtension: "json"),
              let data = try? Data(contentsOf: url),
              let verdict = try? JSONDecoder().decode(RadarVerdict.self, from: data) else {
            errorMessage = "Bundled demo missing."
            return
        }
        demo = verdict
        // Do not assign `latest` here — Today must not flash the INTC sample.
    }

    /// Prefetch SPY into cache, then refresh Today with live SPY posture.
    func warmUpToday() async {
        guard !warmUpStarted else { return }
        warmUpStarted = true
        isWarmingUp = true
        defer { isWarmingUp = false }
        _ = try? await FreeMarketDataClient.dailyBars(symbol: "SPY", rangeHintDays: 90)
        if await analyze(ticker: "SPY") {
            todayVerdict = latest
        }
    }

    func analyze(ticker: String, forceDemo: Bool = false, bypassCache: Bool = false) async -> Bool {
        let symbol = FreeMarketDataClient.normalize(ticker)
        guard !symbol.isEmpty else {
            errorMessage = "Enter a ticker."
            return false
        }

        if forceDemo && symbol == "INTC" {
            if demo == nil { loadDemo() }
            latest = demo
            lastSource = "bundled_sample"
            errorMessage = nil
            return true
        }

        isLoading = true
        errorMessage = nil
        defer { isLoading = false }

        if let base = debugAnalyzeOverride {
            do {
                latest = try await fetchWebAnalyze(base: base, ticker: symbol)
                lastSource = "debug_web"
                errorMessage = "Debug web analyze override active."
                return true
            } catch {
                // fall through
            }
        }

        do {
            async let primary = FreeMarketDataClient.dailyBars(
                symbol: symbol,
                bypassCache: bypassCache
            )
            async let spy = FreeMarketDataClient.dailyBars(
                symbol: "SPY",
                rangeHintDays: 90,
                bypassCache: bypassCache && symbol == "SPY"
            )
            async let fund = FreeMarketDataClient.fundamentals(symbol: symbol)
            let result = try await primary
            let spyBars = try? await spy
            let fundamentals = await fund
            var sectorAction: String?
            if let etf = PostureDepth.etf(forSector: fundamentals.sector), etf != symbol {
                if let sectorBars = try? await FreeMarketDataClient.dailyBars(symbol: etf, rangeHintDays: 90) {
                    sectorAction = FreeMechanicalScorer.core(bars: sectorBars.bars, spyBars: spyBars?.bars).action
                }
            }
            let scored = FreeMechanicalScorer.score(
                symbol: symbol,
                company: nil,
                bars: result.bars,
                spyBars: spyBars?.bars,
                source: result.source,
                earningsDate: fundamentals.earningsDate,
                sectorName: fundamentals.sector,
                sectorAction: sectorAction
            )
            latest = scored
            if symbol == "SPY" { todayVerdict = scored }
            lastSource = result.fromCache ? "\(result.source.rawValue) · cache" : result.source.rawValue
            return true
        } catch {
            if symbol == "INTC" {
                if demo == nil { loadDemo() }
                latest = demo
                lastSource = "bundled_sample"
                errorMessage = "All free sources failed — showing bundled INTC sample."
                return latest != nil
            }
            latest = Self.synthetic(for: symbol, reason: error.localizedDescription)
            lastSource = nil
            errorMessage = "Free-data radar unavailable — fail closed."
            return true
        }
    }

    /// Score a ticker without mutating `latest` (watchlist batch refresh).
    func scoreQuietly(ticker: String) async -> RadarVerdict? {
        let symbol = FreeMarketDataClient.normalize(ticker)
        guard !symbol.isEmpty else { return nil }
        do {
            async let primary = FreeMarketDataClient.dailyBars(symbol: symbol)
            async let spy = FreeMarketDataClient.dailyBars(symbol: "SPY", rangeHintDays: 90)
            async let fund = FreeMarketDataClient.fundamentals(symbol: symbol)
            let result = try await primary
            let spyBars = try? await spy
            let fundamentals = await fund
            var sectorAction: String?
            if let etf = PostureDepth.etf(forSector: fundamentals.sector), etf != symbol {
                if let sectorBars = try? await FreeMarketDataClient.dailyBars(symbol: etf, rangeHintDays: 90) {
                    sectorAction = FreeMechanicalScorer.core(bars: sectorBars.bars, spyBars: spyBars?.bars).action
                }
            }
            return FreeMechanicalScorer.score(
                symbol: symbol,
                company: nil,
                bars: result.bars,
                spyBars: spyBars?.bars,
                source: result.source,
                earningsDate: fundamentals.earningsDate,
                sectorName: fundamentals.sector,
                sectorAction: sectorAction
            )
        } catch {
            return nil
        }
    }

    /// Unlocked Today: sector ETF posture chips. Cached bars, limited concurrency.
    func refreshSectors() async {
        var rows: [SectorChip] = []
        let spy = try? await FreeMarketDataClient.dailyBars(symbol: "SPY", rangeHintDays: 90)
        let etfs = Array(PostureDepth.sectorETF.keys).sorted()
        await withTaskGroup(of: SectorChip?.self) { group in
            var i = 0
            func enqueue() {
                guard i < etfs.count else { return }
                let etf = etfs[i]
                i += 1
                group.addTask {
                    guard let bars = try? await FreeMarketDataClient.dailyBars(symbol: etf, rangeHintDays: 90) else {
                        return nil
                    }
                    let action = FreeMechanicalScorer.core(bars: bars.bars, spyBars: spy?.bars).action
                    let label = PostureDepth.sectorETF[etf] ?? etf
                    return SectorChip(etf: etf, label: label, action: action)
                }
            }
            for _ in 0..<min(3, etfs.count) { enqueue() }
            for await row in group {
                if let row { rows.append(row) }
                enqueue()
            }
        }
        sectorHeat = rows.sorted { $0.etf < $1.etf }
    }

    private func fetchWebAnalyze(base: URL, ticker: String) async throws -> RadarVerdict {
        var components = URLComponents(
            url: base.appendingPathComponent("api/analyze"),
            resolvingAgainstBaseURL: false
        )!
        components.queryItems = [URLQueryItem(name: "ticker", value: ticker)]
        guard let url = components.url else { throw URLError(.badURL) }
        var request = URLRequest(url: url)
        request.timeoutInterval = 20
        let (data, response) = try await URLSession.shared.data(for: request)
        guard let http = response as? HTTPURLResponse, (200..<300).contains(http.statusCode) else {
            throw URLError(.badServerResponse)
        }
        return try JSONDecoder().decode(RadarVerdict.self, from: data)
    }

    static func synthetic(for ticker: String, reason: String) -> RadarVerdict {
        RadarVerdict(
            ok: true,
            ticker: ticker,
            companyName: ticker,
            sector: nil,
            primaryScore: .init(value: nil, scale: 100, label: "Mechanical posture score", withheld: true, note: reason),
            primary: .init(action: "WAIT", label: "Wait & Watch", reason: "Insufficient free data — fail closed."),
            summary: "Could not load bars for this ticker. Not forcing a trade.",
            engagement: .init(
                avoidedLine: "Not forcing a trade without usable data.",
                freezeLabel: "Placeholder",
                postureNote: "Mechanical posture ≠ trade direction."
            ),
            dataQuality: .init(usable: false, reliability: "low", optionsActionable: false),
            market: nil,
            meta: .init(
                mode: "placeholder",
                fetchTime: nil,
                disclaimer: "Educational radar only — not investment advice.",
                dataPath: "synthetic"
            ),
            gate: .init(market: "UNKNOWN", sector: "N/A", stock: "NO"),
            warnings: [reason],
            depth: nil
        )
    }
}
