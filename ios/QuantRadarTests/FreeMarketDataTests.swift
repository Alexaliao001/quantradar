import XCTest
@testable import QuantRadar

final class FreeMarketDataTests: XCTestCase {
    func testYahooQ1AAPL() async throws {
        FreeMarketDataClient.sourceOrder = [.yahooQuery1]
        let result = try await FreeMarketDataClient.dailyBars(symbol: "AAPL", rangeHintDays: 90)
        XCTAssertEqual(result.source, .yahooQuery1)
        XCTAssertGreaterThanOrEqual(result.bars.count, 30)
        XCTAssertGreaterThan(result.bars.last!.close, 0)
    }

    func testYahooQ2INTC() async throws {
        FreeMarketDataClient.sourceOrder = [.yahooQuery2]
        let result = try await FreeMarketDataClient.dailyBars(symbol: "INTC", rangeHintDays: 90)
        XCTAssertEqual(result.source, .yahooQuery2)
        XCTAssertGreaterThanOrEqual(result.bars.count, 30)
    }

    func testNasdaqAAPL() async throws {
        FreeMarketDataClient.sourceOrder = [.nasdaq]
        let result = try await FreeMarketDataClient.dailyBars(symbol: "AAPL", rangeHintDays: 120)
        XCTAssertEqual(result.source, .nasdaq)
        XCTAssertGreaterThanOrEqual(result.bars.count, 30)
    }

    func testFailoverSkipsBadFirstSource() async throws {
        // Force order: nasdaq on SPY often empty → should fall to yahoo
        FreeMarketDataClient.sourceOrder = [.nasdaq, .yahooQuery1]
        let result = try await FreeMarketDataClient.dailyBars(symbol: "SPY", rangeHintDays: 90)
        XCTAssertEqual(result.source, .yahooQuery1)
        XCTAssertGreaterThanOrEqual(result.bars.count, 30)
    }

    func testScorerProducesAction() async throws {
        FreeMarketDataClient.sourceOrder = [.yahooQuery1, .yahooQuery2, .nasdaq]
        let result = try await FreeMarketDataClient.dailyBars(symbol: "AAPL")
        let spy = try await FreeMarketDataClient.dailyBars(symbol: "SPY", rangeHintDays: 90)
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
        let first = try await FreeMarketDataClient.dailyBars(symbol: "AAPL", rangeHintDays: 90)
        XCTAssertFalse(first.fromCache)
        let second = try await FreeMarketDataClient.dailyBars(symbol: "AAPL", rangeHintDays: 90)
        XCTAssertTrue(second.fromCache)
        XCTAssertEqual(second.bars.count, first.bars.count)
        await BarsCache.shared.clear()
    }

    func testBundledSampleDecodes() throws {
        let url = Bundle.main.url(forResource: "SampleVerdict", withExtension: "json")
            ?? Bundle(for: FreeMarketDataTests.self).url(forResource: "SampleVerdict", withExtension: "json")
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
