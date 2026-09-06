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

    func testJournalPreservesSeparateDecisionsForSameTickerAndDay() {
        let now = Date(timeIntervalSince1970: 1_788_000_000)
        let verdict = RadarService.synthetic(for: "MSFT", reason: "test")
        var clear = ChaseCheck()
        clear.entryWasPlanned = true
        clear.invalidationIsDefined = true
        clear.independentOfHype = true

        let journal = DecisionJournal(storage: defaults)
        let first = journal.record(verdict: verdict, chaseCheck: clear, now: now)
        let second = journal.record(verdict: verdict, chaseCheck: clear, now: now.addingTimeInterval(60))

        XCTAssertEqual(first.decision, "PAUSE")
        XCTAssertEqual(first.radarAction, "UNKNOWN")
        XCTAssertEqual(second.decision, "PAUSE")
        XCTAssertNotEqual(first.id, second.id)
        XCTAssertEqual(journal.entries.count, 2)
        XCTAssertEqual(journal.entries.last, first)

        let restored = DecisionJournal(storage: defaults)
        XCTAssertEqual(restored.entries.count, 2)
        XCTAssertEqual(restored.entries.first?.ticker, "MSFT")
    }

    private func makePlan(_ journal: DecisionJournal, now: Date = Date()) throws -> DecisionEntry {
        try journal.commitPlan(ticker: " aapl ", reason: " My original reason ", trigger: "Wait for my condition",
                               invalidation: "My invalidation", reviewOn: now, decision: "WAIT", now: now)
    }

    func testPlanWorksWithoutMarketDataAndSurvivesRelaunch() throws {
        let journal = DecisionJournal(storage: defaults)
        let plan = try makePlan(journal)
        XCTAssertEqual(plan.ticker, "AAPL")
        XCTAssertEqual(plan.plan?.reason, "My original reason")
        XCTAssertEqual(plan.radarAction, "NOT SCANNED")
        XCTAssertNil(plan.score)
        XCTAssertNil(plan.review)
        XCTAssertEqual(DecisionJournal(storage: defaults).entries.first, plan)
    }

    func testReviewKeepsOriginalAndCannotOverwritePreviousReview() throws {
        let journal = DecisionJournal(storage: defaults)
        let now = Date()
        let before = try makePlan(journal, now: now)
        try journal.completeReview(id: before.id, outcome: .didNotAct, lesson: "Condition never occurred", now: now.addingTimeInterval(60))
        let after = try XCTUnwrap(DecisionJournal(storage: defaults).entries.first)
        XCTAssertEqual(after.id, before.id)
        XCTAssertEqual(after.plan, before.plan)
        XCTAssertEqual(after.createdAt, before.createdAt)
        XCTAssertEqual(after.decision, before.decision)
        XCTAssertEqual(after.review?.lesson, "Condition never occurred")
        XCTAssertTrue(after.exportText.contains("Original reason: My original reason"))
        XCTAssertTrue(after.exportText.contains("Condition never occurred"))
        XCTAssertThrowsError(try journal.completeReview(id: before.id, outcome: .followed, lesson: "Rewrite"))
        XCTAssertEqual(journal.entries.first, after)
    }

    func testIncompleteOrMismatchedPlanDoesNotPersist() {
        let journal = DecisionJournal(storage: defaults)
        let now = Date()
        for symbol in ["", "<SCRIPT>", "TOOLONGTICKERXX"] {
            XCTAssertThrowsError(try journal.commitPlan(ticker: symbol, reason: "Reason", trigger: "Trigger",
                                                       invalidation: "Invalidation", reviewOn: now, decision: "WAIT"))
        }
        for invalidReason in ["  ", String(repeating: "x", count: 1_001)] {
            XCTAssertThrowsError(try journal.commitPlan(ticker: "AAPL", reason: invalidReason, trigger: "Trigger",
                                                       invalidation: "Invalidation", reviewOn: now, decision: "WAIT"))
        }
        XCTAssertThrowsError(try journal.commitPlan(ticker: "AAPL", reason: "Reason", trigger: "Trigger", invalidation: "Invalidation",
                                                   reviewOn: now.addingTimeInterval(-172_800), decision: "WAIT", now: now))
        XCTAssertThrowsError(try journal.commitPlan(ticker: "AAPL", reason: "Reason", trigger: "Trigger", invalidation: "Invalidation",
                                                   reviewOn: now, decision: "BUY"))
        XCTAssertThrowsError(try journal.commitPlan(ticker: "AAPL", reason: "Reason", trigger: "Trigger", invalidation: "Invalidation",
                                                   reviewOn: now, decision: "WAIT", verdict: RadarService.synthetic(for: "MSFT", reason: "test")))
        XCTAssertTrue(journal.entries.isEmpty)
    }

    func testReviewQueueExcludesReviewedAndFuturePlans() throws {
        let journal = DecisionJournal(storage: defaults)
        let now = Date()
        let due = try makePlan(journal, now: now)
        _ = try journal.commitPlan(ticker: "MSFT", reason: "Reason", trigger: "Trigger", invalidation: "Invalidation",
                                   reviewOn: now.addingTimeInterval(172_800), decision: "PASS", now: now)
        XCTAssertEqual(journal.dueCount(now: now), 1)
        XCTAssertThrowsError(try journal.completeReview(id: due.id, outcome: .changed, lesson: "  "))
        XCTAssertThrowsError(try journal.completeReview(id: due.id, outcome: .changed, lesson: "Earlier", now: now.addingTimeInterval(-1)))
        try journal.completeReview(id: due.id, outcome: .changed, lesson: "I revised the condition", now: now)
        XCTAssertEqual(journal.dueCount(now: now), 0)
    }

    func testExistingJournalDecodesWithoutNewFields() throws {
        let old: [[String: Any]] = [["id": UUID().uuidString, "ticker": "MSFT", "radarAction": "WAIT",
                                     "decision": "PAUSE", "processClear": false, "createdAt": 123_456.0]]
        defaults.set(try JSONSerialization.data(withJSONObject: old), forKey: DecisionJournal.storageKey)
        let journal = DecisionJournal(storage: defaults)
        let entry = try XCTUnwrap(journal.entries.first)
        XCTAssertNil(entry.plan)
        XCTAssertNil(entry.review)
        XCTAssertEqual(entry.ticker, "MSFT")
        try journal.completeReview(id: entry.id, outcome: .didNotAct, lesson: "Legacy decision reviewed")
        XCTAssertEqual(journal.entries.first?.createdAt, entry.createdAt)
    }

    func testNewPlansDoNotSilentlyEvictOriginalRecords() throws {
        let journal = DecisionJournal(storage: defaults)
        let first = try makePlan(journal)
        for _ in 0..<100 { _ = try makePlan(journal) }
        XCTAssertEqual(journal.entries.count, 101)
        XCTAssertEqual(DecisionJournal(storage: defaults).entries.last, first)
    }
}
