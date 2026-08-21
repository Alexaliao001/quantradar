import XCTest
@testable import QuantRadar

final class AppAccessTests: XCTestCase {
    override func setUp() {
        super.setUp()
        AppAccess.storage = UserDefaults(suiteName: "qr.tests.\(UUID().uuidString)")!
        AppAccess.resetPreviewTicker()
        ReviewPrompt.storage = UserDefaults(suiteName: "qr.review.\(UUID().uuidString)")!
    }

    override func tearDown() {
        AppAccess.storage = .standard
        ReviewPrompt.storage = .standard
        super.tearDown()
    }

    func testSPYAlwaysFree() {
        XCTAssertTrue(AppAccess.canScan(ticker: "SPY", unlocked: false))
        XCTAssertTrue(AppAccess.canScan(ticker: " spy ", unlocked: false))
    }

    func testFirstPersonalTickerThenLock() {
        XCTAssertTrue(AppAccess.canScan(ticker: "AAPL", unlocked: false))
        XCTAssertTrue(AppAccess.claimPreviewTickerIfNeeded("AAPL", withheld: false))
        XCTAssertEqual(AppAccess.claimedPreviewTicker, "AAPL")
        XCTAssertTrue(AppAccess.canScan(ticker: "AAPL", unlocked: false))
        XCTAssertFalse(AppAccess.canScan(ticker: "NVDA", unlocked: false))
        XCTAssertTrue(AppAccess.canScan(ticker: "SPY", unlocked: false))
    }

    func testWithheldDoesNotClaimPreview() {
        XCTAssertTrue(AppAccess.claimPreviewTickerIfNeeded("MSFT", withheld: true))
        XCTAssertNil(AppAccess.claimedPreviewTicker)
        XCTAssertTrue(AppAccess.canScan(ticker: "NVDA", unlocked: false))
    }

    func testSPYDoesNotConsumePreview() {
        XCTAssertTrue(AppAccess.claimPreviewTickerIfNeeded("SPY", withheld: false))
        XCTAssertNil(AppAccess.claimedPreviewTicker)
        XCTAssertTrue(AppAccess.canScan(ticker: "AAPL", unlocked: false))
    }

    func testUnlockedScansAny() {
        _ = AppAccess.claimPreviewTickerIfNeeded("AAPL", withheld: false)
        XCTAssertTrue(AppAccess.canScan(ticker: "NVDA", unlocked: true))
        XCTAssertTrue(AppAccess.canScan(ticker: "AAPL", unlocked: true))
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

    func testPostureChangeNotify() {
        XCTAssertFalse(AppAccess.shouldNotifyPostureChange(previous: nil, next: "SETUP", remind: true))
        XCTAssertFalse(AppAccess.shouldNotifyPostureChange(previous: "WAIT", next: "WAIT", remind: true))
        XCTAssertFalse(AppAccess.shouldNotifyPostureChange(previous: "WAIT", next: "SETUP", remind: false))
        XCTAssertTrue(AppAccess.shouldNotifyPostureChange(previous: "WAIT", next: "SETUP", remind: true))
    }

    func testReviewPromptNeedsSecondLaunchAndWait() {
        XCTAssertFalse(ReviewPrompt.shouldRequestReview())
        ReviewPrompt.recordLaunch()
        XCTAssertFalse(ReviewPrompt.shouldRequestReview())
        ReviewPrompt.recordLaunch()
        XCTAssertFalse(ReviewPrompt.shouldRequestReview())
        ReviewPrompt.storage.set(true, forKey: ReviewPrompt.waitKey)
        XCTAssertTrue(ReviewPrompt.shouldRequestReview())
    }
}
