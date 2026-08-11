import XCTest
@testable import QuantRadar

final class AppAccessTests: XCTestCase {
    func testFreePreviewOnlyINTC() {
        XCTAssertTrue(AppAccess.canScan(ticker: "INTC", unlocked: false))
        XCTAssertTrue(AppAccess.canScan(ticker: " intc ", unlocked: false))
        XCTAssertFalse(AppAccess.canScan(ticker: "AAPL", unlocked: false))
        XCTAssertFalse(AppAccess.canScan(ticker: "SPY", unlocked: false))
    }

    func testUnlockedScansAny() {
        XCTAssertTrue(AppAccess.canScan(ticker: "AAPL", unlocked: true))
        XCTAssertTrue(AppAccess.canScan(ticker: "NVDA", unlocked: true))
    }

    func testWatchlistLimits() {
        XCTAssertEqual(AppAccess.watchlistLimit(livePlus: false), 20)
        XCTAssertEqual(AppAccess.watchlistLimit(livePlus: true), 50)
    }

    func testReminderIntervals() {
        XCTAssertEqual(AppAccess.reminderIntervalSeconds(livePlus: false), 60 * 60 * 24)
        XCTAssertEqual(AppAccess.reminderIntervalSeconds(livePlus: true), 60 * 60 * 6)
    }

    func testProductIDsStable() {
        XCTAssertEqual(AppAccess.unlockProductID, "one.quantradar.app.unlock")
        XCTAssertEqual(AppAccess.liveMonthlyProductID, "one.quantradar.app.live.monthly")
        XCTAssertEqual(AppAccess.liveYearlyProductID, "one.quantradar.app.live.yearly")
    }
}
