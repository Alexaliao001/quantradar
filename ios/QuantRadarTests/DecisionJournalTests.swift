import XCTest
@testable import QuantRadar

@MainActor
final class DecisionJournalTests: XCTestCase {
    private var defaults: UserDefaults!
    private var suiteName: String!

    override func setUp() {
        super.setUp()
        suiteName = "qr.journal.\(UUID().uuidString)"
        defaults = UserDefaults(suiteName: suiteName)!
        defaults.removePersistentDomain(forName: suiteName)
    }

    override func tearDown() {
        defaults.removePersistentDomain(forName: suiteName)
        defaults = nil
        suiteName = nil
        super.tearDown()
    }

    func testChaseCheckRequiresAllThreeCommitments() {
        var check = ChaseCheck()
        XCTAssertEqual(check.status, "PAUSE")
        XCTAssertEqual(check.completedCount, 0)

        check.entryWasPlanned = true
        check.invalidationIsDefined = true
        XCTAssertFalse(check.isClear)

        check.independentOfHype = true
        XCTAssertTrue(check.isClear)
        XCTAssertEqual(check.status, "PROCESS CLEAR")

        check.reset()
        XCTAssertEqual(check, ChaseCheck())
    }

    func testJournalRecordsPauseWhenProcessIncomplete() {
        let journal = DecisionJournal(storage: defaults)
        let verdict = RadarService.synthetic(for: "AAPL", reason: "test")

        let entry = journal.record(verdict: verdict, chaseCheck: ChaseCheck())

        XCTAssertEqual(entry.ticker, "AAPL")
        XCTAssertEqual(entry.decision, "PAUSE")
        XCTAssertFalse(entry.processClear)
        XCTAssertEqual(journal.entries.count, 1)
    }

    func testJournalPersistsAndReplacesSameTickerSameDay() {
        let now = Date(timeIntervalSince1970: 1_788_000_000)
        let verdict = RadarService.synthetic(for: "MSFT", reason: "test")
        var clear = ChaseCheck()
        clear.entryWasPlanned = true
        clear.invalidationIsDefined = true
        clear.independentOfHype = true

        let journal = DecisionJournal(storage: defaults)
        let first = journal.record(verdict: verdict, chaseCheck: clear, now: now)
        let second = journal.record(verdict: verdict, chaseCheck: clear, now: now.addingTimeInterval(60))

        XCTAssertEqual(first.decision, "WAIT")
        XCTAssertEqual(second.decision, "WAIT")
        XCTAssertEqual(journal.entries.count, 1)

        let restored = DecisionJournal(storage: defaults)
        XCTAssertEqual(restored.entries.count, 1)
        XCTAssertEqual(restored.entries.first?.ticker, "MSFT")
    }
}
