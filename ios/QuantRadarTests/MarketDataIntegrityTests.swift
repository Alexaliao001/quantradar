import XCTest
@testable import QuantRadar

final class MarketDataIntegrityTests: XCTestCase {
    private func date(_ value: String) -> Date { ISO8601DateFormatter().date(from: value)! }
    private var now: Date { date("2026-09-04T21:00:00Z") }

    private func setupBars() -> [FreeBar] {
        var closes = (0..<45).map { 100 + Double($0) * 0.3 }
        for delta in Array(repeating: 0.9, count: 8) + Array(repeating: -0.7, count: 6) {
            closes.append(closes.last! + delta)
        }
        let end = date("2026-09-04T14:00:00Z")
        return closes.enumerated().map { i, close in
            FreeBar(date: end.addingTimeInterval(Double(i - 58) * 86400), close: close,
                    volume: i == 58 ? 1_500_000 : 1_000_000)
        }
    }

    func testMissingAndInvalidMarketNeverPass() {
        let bars = setupBars()
        for spy: [FreeBar]? in [nil, [], Array(bars.prefix(4)), bars.map { FreeBar(date: $0.date, close: 0, volume: 0) }] {
            let result = FreeMechanicalScorer.core(bars: bars, spyBars: spy)
            XCTAssertEqual(result.score, 88)
            XCTAssertEqual(result.marketGate, "UNKNOWN")
            XCTAssertEqual(result.action, "WAIT")
            XCTAssertNil(result.spyPct)
        }
    }

    func testHolidayDSTAndEarlyCloseBoundaries() {
        let cases = [
            ("2026-09-08T19:59:59Z", "2026-09-04"),
            ("2026-09-08T20:00:00Z", "2026-09-08"),
            ("2026-09-07T23:00:00Z", "2026-09-04"),
            ("2026-11-27T17:59:59Z", "2026-11-25"),
            ("2026-11-27T18:00:00Z", "2026-11-27"),
            ("2026-03-06T20:30:00Z", "2026-03-05"),
            ("2026-03-09T20:30:00Z", "2026-03-09"),
            ("2026-01-01T22:00:00Z", "2025-12-31")
        ]
        for (instant, expected) in cases {
            XCTAssertEqual(MarketCalendar.completedSession(now: date(instant)), expected, instant)
        }
        XCTAssertNil(MarketCalendar.completedSession(now: date("2029-01-02T22:00:00Z")))
    }

    func testStaleBarsWithheldAndCacheTimestampPreserved() {
        let bars = setupBars()
        let stale = FreeMechanicalScorer.score(symbol: "TEST", company: nil, bars: Array(bars.dropLast()),
            spyBars: bars, source: .yahooQuery1, now: now)
        XCTAssertEqual(stale.dataQuality?.usable, false)
        XCTAssertEqual(stale.primaryScore?.withheld, true)
        XCTAssertNil(stale.primaryScore?.value)
        XCTAssertEqual(stale.primary?.action, "WAIT")
        let fetched = now.addingTimeInterval(-120)
        let fresh = FreeMechanicalScorer.score(symbol: "TEST", company: nil, bars: bars,
            spyBars: bars, source: .yahooQuery1, fetchedAt: fetched, fromCache: true, now: now)
        XCTAssertEqual(fresh.dataQuality?.usable, true)
        XCTAssertEqual(fresh.meta?.marketAsOf, "2026-09-04")
        XCTAssertEqual(fresh.meta?.fetchTime, ISO8601DateFormatter().string(from: fetched))
        XCTAssertEqual(fresh.meta?.fromCache, true)
        let partial = FreeBar(date: date("2026-09-08T14:00:00Z"), close: 999, volume: 1000)
        XCTAssertEqual(MarketCalendar.completedBars(bars + [partial], now: date("2026-09-08T18:00:00Z")), bars)
        XCTAssertNil(MarketCalendar.completedBars(bars, now: now, fetchedAt: date("2026-09-04T19:59:00Z")))
        XCTAssertNotNil(MarketCalendar.completedBars(bars, now: now, fetchedAt: date("2026-09-04T20:01:00Z")))
        XCTAssertEqual(MarketCalendar.sessionClose("2026-11-27"), date("2026-11-27T18:00:00Z"))
    }

    func testReplayAlignsDatesAndNeverReadsFutureMarketBars() {
        let bars = setupBars()
        let spy = (0..<70).map { i in
            let day = bars[0].date.addingTimeInterval(Double(i + 5) * 86400)
            return FreeBar(date: day, close: i <= 53 ? 100 : 100 - Double(i - 53) * 3, volume: 1000)
        }
        let replay = PostureDepth.replayActions(bars: bars, spyBars: spy)
        XCTAssertEqual(replay.last, "SETUP")
        let missingDay = spy.filter { MarketCalendar.barDay($0.date) != "2026-09-04" }
        XCTAssertEqual(PostureDepth.replayActions(bars: bars, spyBars: missingDay).last, "WAIT")
    }

    func testEarningsGateSuppressesAnActualSetup() {
        let bars = setupBars()
        let spy = bars.map { FreeBar(date: $0.date, close: 100, volume: 1000) }
        let open = FreeMechanicalScorer.score(symbol: "TEST", company: nil, bars: bars,
            spyBars: spy, source: .yahooQuery1, now: now)
        XCTAssertEqual(open.primary?.action, "SETUP")
        let guarded = FreeMechanicalScorer.score(symbol: "TEST", company: nil, bars: bars,
            spyBars: spy, source: .yahooQuery1, earningsDate: now.addingTimeInterval(86400), now: now)
        XCTAssertEqual(guarded.primary?.action, "WAIT")
        XCTAssertEqual(guarded.depth?.earningsForcedWait, true)
    }
}
