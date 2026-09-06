import XCTest
@testable import QuantRadar

@MainActor
final class DepthEngineTests: XCTestCase {
    override func setUp() {
        super.setUp()
        DisciplineLedger.storage = UserDefaults(suiteName: "qr.disc.\(UUID().uuidString)")!
        DisciplineLedger.reset()
        AppAccess.storage = UserDefaults(suiteName: "qr.acc.\(UUID().uuidString)")!
        AppAccess.resetPreviewTicker()
    }

    override func tearDown() {
        DisciplineLedger.storage = .standard
        AppAccess.storage = .standard
        super.tearDown()
    }

    func testSectorETFMap() {
        XCTAssertEqual(PostureDepth.etf(forSector: "Technology"), "XLK")
        XCTAssertEqual(PostureDepth.etf(forSector: "Financial Services"), "XLF")
        XCTAssertEqual(PostureDepth.etf(forSector: "XLK"), "XLK")
        XCTAssertNil(PostureDepth.etf(forSector: nil))
    }

    func testEarningsWindow() {
        let now = Date(timeIntervalSince1970: 1_787_184_000) // 2026-08-20 approx
        let soon = now.addingTimeInterval(2 * 86_400)
        let far = now.addingTimeInterval(20 * 86_400)
        XCTAssertTrue(PostureDepth.isNearEarnings(soon, now: now))
        XCTAssertFalse(PostureDepth.isNearEarnings(far, now: now))
        XCTAssertEqual(PostureDepth.daysUntilEarnings(soon, now: now), 2)
    }

    func testMedian() {
        XCTAssertEqual(PostureDepth.median([1, 3, 2]), 2)
        XCTAssertEqual(PostureDepth.median([1, 2, 3, 4]), 2.5)
        XCTAssertNil(PostureDepth.median([]))
    }

    func testEarningsForcesSETUPToWAIT() {
        let bars = Self.grind(start: 100, end: 112, count: 80, lastVolume: 2_400_000)
        let spy = Self.grind(start: 400, end: 408, count: 80, lastVolume: 1_000_000)
        let now = Date(timeIntervalSince1970: 1_787_184_000)
        let earnings = now.addingTimeInterval(86_400)
        let open = FreeMechanicalScorer.score(
            symbol: "AAPL",
            company: "Apple",
            bars: bars,
            spyBars: spy,
            source: .yahooQuery1,
            now: now
        )
        let guarded = FreeMechanicalScorer.score(
            symbol: "AAPL",
            company: "Apple",
            bars: bars,
            spyBars: spy,
            source: .yahooQuery1,
            earningsDate: earnings,
            now: now
        )
        XCTAssertNotEqual(open.primary?.action, "BUY")
        XCTAssertNotEqual(guarded.primary?.action, "BUY")
        XCTAssertNotEqual(guarded.primary?.action, "SETUP")
        if open.primary?.action == "SETUP" {
            XCTAssertEqual(guarded.primary?.action, "WAIT")
            XCTAssertEqual(guarded.depth?.earningsForcedWait, true)
        }
    }

    func testReplayHistoryBounded() {
        let bars = Self.grind(start: 80, end: 120, count: 120, lastVolume: 2_000_000)
        let hist = PostureDepth.replayActions(bars: bars, spyBars: bars)
        XCTAssertFalse(hist.isEmpty)
        XCTAssertLessThanOrEqual(hist.count, PostureDepth.historyDays)
        XCTAssertTrue(hist.allSatisfy { ["SETUP", "WAIT", "NO"].contains($0) })
    }

    func testForwardEvidenceFromUptrend() {
        let bars = Self.grind(start: 80, end: 140, count: 120, lastVolume: 2_000_000)
        let depth = PostureDepth.build(
            bars: bars,
            spyBars: bars,
            earningsDate: nil,
            earningsForcedWait: false,
            sectorEtf: "XLK"
        )
        XCTAssertEqual(depth.sectorEtf, "XLK")
        XCTAssertFalse(depth.history.isEmpty)
    }

    func testParseFundamentals() throws {
        let json = """
        {"quoteSummary":{"result":[{"assetProfile":{"sector":"Technology"},"calendarEvents":{"earnings":{"earningsDate":[{"raw":1787280000}]}}}]}}
        """.data(using: .utf8)!
        let f = FreeMarketDataClient.parseFundamentals(json)
        XCTAssertEqual(f.sector, "Technology")
        XCTAssertNotNil(f.earningsDate)
    }

    func testDisciplineStreakAndWait() {
        let d0 = Date(timeIntervalSince1970: 1_787_184_000)
        DisciplineLedger.record(action: "WAIT", ticker: "SPY", close: 500, date: d0)
        XCTAssertEqual(DisciplineLedger.streak, 1)
        XCTAssertEqual(DisciplineLedger.waitCount, 1)
        let d1 = d0.addingTimeInterval(86_400)
        DisciplineLedger.record(action: "NO", ticker: "SPY", close: 490, date: d1)
        XCTAssertEqual(DisciplineLedger.streak, 2)
        XCTAssertGreaterThan(DisciplineLedger.avoidedPct, 0)
    }

    func testPreviewLockedSecondTicker() {
        XCTAssertFalse(AppAccess.isPreviewLocked(ticker: "AAPL", unlocked: false))
        _ = AppAccess.claimPreviewTickerIfNeeded("AAPL", withheld: false)
        XCTAssertTrue(AppAccess.isPreviewLocked(ticker: "NVDA", unlocked: false))
        XCTAssertFalse(AppAccess.isPreviewLocked(ticker: "AAPL", unlocked: false))
        XCTAssertFalse(AppAccess.isPreviewLocked(ticker: "NVDA", unlocked: true))
    }

    func testAnxietyAndFounderCopy() {
        XCTAssertTrue(AppAccess.anxietyCopy(ticker: "nvda").contains("NVDA"))
        XCTAssertTrue(AppAccess.founderPriceLine.contains("One-time"))
        XCTAssertTrue(AppAccess.founderPriceLine.contains("Restore"))
        XCTAssertFalse(AppAccess.founderPriceLine.lowercased().contains("countdown"))
    }

    func testShareReverseFlexOnWait() {
        let v = RadarService.synthetic(for: "MSFT", reason: "test")
        XCTAssertTrue(v.shareText.contains("didn't force a trade"))
        XCTAssertTrue(v.shareText.contains("not investment advice"))
    }

    func testDailyBriefingIds() {
        XCTAssertTrue(DailyBriefing.idPrefix.hasPrefix("qr.briefing"))
        XCTAssertEqual(DailyBriefing.hour, 9)
        XCTAssertEqual(DailyBriefing.minute, 25)
    }

    func testTodayPublishDoesNotClobberScan() {
        let radar = RadarService()
        radar.applyScored(RadarService.synthetic(for: "AAPL", reason: "scan"), target: .scan, sourceLabel: "scan")
        radar.applyScored(RadarService.synthetic(for: "SPY", reason: "today"), target: .today, sourceLabel: "today")
        XCTAssertEqual(radar.latest?.ticker, "AAPL")
        XCTAssertEqual(radar.todayVerdict?.ticker, "SPY")
        XCTAssertEqual(radar.lastSource, "today")
    }

    func testScanSPYAlsoUpdatesToday() {
        let radar = RadarService()
        radar.applyScored(RadarService.synthetic(for: "AAPL", reason: "a"), target: .scan, sourceLabel: "aapl")
        radar.applyScored(RadarService.synthetic(for: "SPY", reason: "s"), target: .scan, sourceLabel: "spy")
        XCTAssertEqual(radar.latest?.ticker, "SPY")
        XCTAssertEqual(radar.todayVerdict?.ticker, "SPY")
    }

    func testParseNasdaqSummarySector() {
        let json = """
        {"data":{"symbol":"AAPL","summaryData":{"Sector":{"label":"Sector","value":"Technology"}}}}
        """.data(using: .utf8)!
        let f = FreeMarketDataClient.parseNasdaqSummary(json)
        XCTAssertEqual(f.sector, "Technology")
        XCTAssertTrue(f.isUseful)
    }

    private static func grind(start: Double, end: Double, count: Int, lastVolume: Double) -> [FreeBar] {
        (0..<count).map { i in
            let t = Double(i) / Double(max(count - 1, 1))
            let close = start + (end - start) * t
            let vol = i == count - 1 ? lastVolume : 1_000_000
            return FreeBar(
                date: Date(timeIntervalSince1970: 1_700_000_000 + Double(i) * 86_400),
                close: close,
                volume: vol
            )
        }
    }
}
