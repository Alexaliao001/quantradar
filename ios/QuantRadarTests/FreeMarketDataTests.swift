import XCTest
@testable import QuantRadar

final class FreeMarketDataTests: XCTestCase {
    private func requireLiveData() throws {
        try XCTSkipUnless(ProcessInfo.processInfo.environment["QR_LIVE_DATA_TESTS"] == "1",
                          "Live provider check; enable QR_LIVE_DATA_TESTS separately from offline CI.")
    }

    private func currentBars() -> [FreeBar] {
        let day = MarketCalendar.completedSession()!
        let end = ISO8601DateFormatter().date(from: day + "T14:00:00Z")!
        return (0..<60).map { i in
            FreeBar(date: end.addingTimeInterval(Double(i - 59) * 86400), close: 100 + Double(i) * 0.1, volume: 1000)
        }
    }

    func testYahooQ1AAPL() async throws {
        try requireLiveData()
        await BarsCache.shared.clear()
        FreeMarketDataClient.sourceOrder = [.yahooQuery1]
        let result = try await FreeMarketDataClient.dailyBars(symbol: "AAPL", rangeHintDays: 90)
        XCTAssertEqual(result.source, .yahooQuery1)
        XCTAssertGreaterThanOrEqual(result.bars.count, 30)
        XCTAssertGreaterThan(result.bars.last!.close, 0)
    }

    func testYahooQ2INTC() async throws {
        try requireLiveData()
        await BarsCache.shared.clear()
        FreeMarketDataClient.sourceOrder = [.yahooQuery2]
        let result = try await FreeMarketDataClient.dailyBars(symbol: "INTC", rangeHintDays: 90)
        XCTAssertEqual(result.source, .yahooQuery2)
        XCTAssertGreaterThanOrEqual(result.bars.count, 30)
    }

    func testNasdaqAAPL() async throws {
        try requireLiveData()
        await BarsCache.shared.clear()
        FreeMarketDataClient.sourceOrder = [.nasdaq]
        let result = try await FreeMarketDataClient.dailyBars(symbol: "AAPL", rangeHintDays: 120)
        XCTAssertEqual(result.source, .nasdaq)
        XCTAssertGreaterThanOrEqual(result.bars.count, 30)
    }

    func testFailoverSkipsBadFirstSource() async throws {
        try requireLiveData()
        await BarsCache.shared.clear()
        // Force order: nasdaq on SPY often empty → should fall to yahoo
        FreeMarketDataClient.sourceOrder = [.nasdaq, .yahooQuery1]
        let result = try await FreeMarketDataClient.dailyBars(symbol: "SPY", rangeHintDays: 90)
        XCTAssertEqual(result.source, .yahooQuery1)
        XCTAssertGreaterThanOrEqual(result.bars.count, 30)
    }

    func testScorerProducesAction() async throws {
        let result = FreeBarsResult(bars: currentBars(), source: .yahooQuery1)
        let spy = result
        let verdict = FreeMechanicalScorer.score(
            symbol: "AAPL",
            company: "Apple",
            bars: result.bars,
            spyBars: spy.bars,
            source: result.source
        )
        XCTAssertTrue(verdict.ok)
        XCTAssertFalse(verdict.primaryScore?.withheld ?? true)
        XCTAssertNotNil(verdict.primaryScore?.value)
        let action = verdict.primary?.action ?? ""
        XCTAssertTrue(["SETUP", "WAIT", "NO"].contains(action))
        XCTAssertEqual(verdict.meta?.dataPath, result.source.rawValue)
    }

    func testDailyBarsCacheHitSetsFromCacheFlag() async throws {
        await BarsCache.shared.clear()
        FreeMarketDataClient.sourceOrder = [.yahooQuery1]
        let first = FreeBarsResult(bars: currentBars(), source: .yahooQuery1)
        await BarsCache.shared.set("AAPL", result: first)
        let second = try await FreeMarketDataClient.dailyBars(symbol: "AAPL", rangeHintDays: 90)
        XCTAssertTrue(second.fromCache)
        XCTAssertEqual(second.bars.count, first.bars.count)
        await BarsCache.shared.clear()
    }

    func testBundledSampleDecodes() throws {
        // App bundle resource may not be in test bundle — load from path relative to source
        let path = URL(fileURLWithPath: #filePath)
            .deletingLastPathComponent()
            .deletingLastPathComponent()
            .appendingPathComponent("QuantRadar/Resources/SampleVerdict.json")
        let data = try Data(contentsOf: path)
        let verdict = try JSONDecoder().decode(RadarVerdict.self, from: data)
        XCTAssertEqual(verdict.ticker, "INTC")
        XCTAssertEqual(verdict.primary?.action, "WAIT")
    }

    override func tearDown() async throws {
        FreeMarketDataClient.sourceOrder = [.yahooQuery1, .yahooQuery2, .nasdaq]
        await BarsCache.shared.clear()
        try await super.tearDown()
    }
}
