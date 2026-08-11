import XCTest
@testable import QuantRadar

final class BarsCacheTests: XCTestCase {
    func testMemoryAndDiskRoundTrip() async throws {
        let dir = FileManager.default.temporaryDirectory
            .appendingPathComponent("qr_cache_test_\(UUID().uuidString)", isDirectory: true)
        try FileManager.default.createDirectory(at: dir, withIntermediateDirectories: true)
        defer { try? FileManager.default.removeItem(at: dir) }

        let cache = BarsCache(diskDir: dir)
        let bars = (0..<40).map { i in
            FreeBar(
                date: Date(timeIntervalSince1970: 1_700_000_000 + Double(i) * 86_400),
                close: 100 + Double(i),
                volume: 1_000_000
            )
        }
        let result = FreeBarsResult(bars: bars, source: .yahooQuery1, fromCache: false)
        await cache.set("AAPL", result: result)

        let hit = await cache.get("AAPL", maxAge: 60)
        XCTAssertNotNil(hit)
        XCTAssertEqual(hit?.bars.count, 40)
        XCTAssertEqual(hit?.source, .yahooQuery1)

        // New actor instance sharing same disk dir should still hit.
        let cache2 = BarsCache(diskDir: dir)
        let diskHit = await cache2.get("aapl", maxAge: 60)
        XCTAssertEqual(diskHit?.bars.last?.close, bars.last?.close)
    }

    func testExpiredEntryMisses() async throws {
        let dir = FileManager.default.temporaryDirectory
            .appendingPathComponent("qr_cache_ttl_\(UUID().uuidString)", isDirectory: true)
        try FileManager.default.createDirectory(at: dir, withIntermediateDirectories: true)
        defer { try? FileManager.default.removeItem(at: dir) }

        let cache = BarsCache(diskDir: dir)
        let bars = (0..<35).map { i in
            FreeBar(date: Date().addingTimeInterval(Double(i) * -86_400), close: 50, volume: 100)
        }
        await cache.set("MSFT", result: FreeBarsResult(bars: bars, source: .nasdaq, fromCache: false))
        let miss = await cache.get("MSFT", maxAge: 0)
        XCTAssertNil(miss)
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
}
