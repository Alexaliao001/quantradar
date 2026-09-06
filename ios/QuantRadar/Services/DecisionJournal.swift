import Foundation

struct DecisionPlan: Codable, Hashable {
    let reason: String
    let trigger: String
    let invalidation: String
    let reviewOn: Date
}

struct DecisionReview: Codable, Hashable {
    enum Outcome: String, Codable, CaseIterable {
        case followed = "Followed my plan"
        case changed = "Changed my plan"
        case didNotAct = "Did not act"
    }
    let outcome: Outcome
    let lesson: String
    let reviewedAt: Date
}

struct DecisionEntry: Codable, Identifiable, Hashable {
    let id: UUID
    let ticker: String
    let radarAction: String
    let decision: String
    let score: Double?
    let processClear: Bool
    let createdAt: Date
    var plan: DecisionPlan? = nil
    var review: DecisionReview? = nil
    var marketAsOf: String? = nil

    var exportText: String {
        var lines = ["QuantRadar · Decision record", ticker + " · " + decision,
                     "Recorded: " + createdAt.formatted(date: .abbreviated, time: .shortened)]
        if let plan {
            lines += ["Original reason: " + plan.reason, "Condition to observe: " + plan.trigger,
                      "What invalidates it: " + plan.invalidation,
                      "Review date: " + plan.reviewOn.formatted(date: .abbreviated, time: .omitted)]
        }
        if radarAction != "NOT SCANNED" {
            lines += ["Radar at recording: " + radarAction, "Market session: " + (marketAsOf ?? "Not recorded")]
        }
        if let review {
            lines += ["Self-review: " + review.outcome.rawValue, "Lesson: " + review.lesson,
                      "Reviewed: " + review.reviewedAt.formatted(date: .abbreviated, time: .shortened)]
        }
        lines.append("Personal process journal. No trades or investment returns are verified.")
        return lines.joined(separator: "\n\n")
    }
}

/// Private, on-device record of decisions made before a trade.
@MainActor
final class DecisionJournal: ObservableObject {
    @Published private(set) var entries: [DecisionEntry] = []

    static let storageKey = "qr.decision.journal"

    var storage: UserDefaults

    init(storage: UserDefaults = .standard) {
        self.storage = storage
        load()
    }

    var summaryLine: String {
        switch entries.count {
        case 0:
            return "No decisions logged yet."
        case 1:
            return "1 process-first decision saved on this device."
        default:
            return "\(entries.count) process-first decisions saved on this device."
        }
    }

    @discardableResult
    func record(verdict: RadarVerdict, chaseCheck: ChaseCheck, now: Date = Date()) -> DecisionEntry {
        let action = verdict.isWithheld ? "UNKNOWN" : verdict.actionCode
        let decision: String
        if !chaseCheck.isClear || verdict.isWithheld {
            decision = "PAUSE"
        } else if ["NO", "AVOID"].contains(action) {
            decision = "PASS"
        } else if action == "WAIT" {
            decision = "WAIT"
        } else {
            decision = "REVIEW"
        }

        let entry = DecisionEntry(
            id: UUID(),
            ticker: AppAccess.normalizeTicker(verdict.ticker),
            radarAction: action,
            decision: decision,
            score: verdict.isWithheld ? nil : verdict.primaryScore?.value,
            processClear: chaseCheck.isClear,
            createdAt: now,
            marketAsOf: verdict.meta?.marketAsOf
        )

        entries.insert(entry, at: 0)
        persist()
        return entry
    }

    enum JournalError: LocalizedError {
        case invalidPlan, invalidReview
        var errorDescription: String? {
            switch self {
            case .invalidPlan: return "Enter a valid ticker, all three plan details (up to 1,000 characters each), and a review date from today onward."
            case .invalidReview: return "Add a lesson (up to 2,000 characters). A saved review cannot replace an earlier review."
            }
        }
    }

    @discardableResult
    func commitPlan(ticker: String, reason: String, trigger: String, invalidation: String,
                    reviewOn: Date, decision: String, verdict: RadarVerdict? = nil,
                    now: Date = Date()) throws -> DecisionEntry {
        let symbol = AppAccess.normalizeTicker(ticker)
        let details = [reason, trigger, invalidation].map { $0.trimmingCharacters(in: .whitespacesAndNewlines) }
        guard symbol.range(of: "^[A-Z][A-Z0-9.\\-^]{0,11}$", options: .regularExpression) != nil,
              details.allSatisfy({ !$0.isEmpty && $0.count <= 1_000 }),
              ["PAUSE", "WAIT", "PASS", "REVIEW"].contains(decision),
              Calendar.current.startOfDay(for: reviewOn) >= Calendar.current.startOfDay(for: now),
              verdict == nil || AppAccess.normalizeTicker(verdict!.ticker) == symbol else {
            throw JournalError.invalidPlan
        }
        let entry = DecisionEntry(id: UUID(), ticker: symbol, radarAction: verdict.map { $0.isWithheld ? "UNKNOWN" : $0.actionCode } ?? "NOT SCANNED",
                                  decision: decision, score: verdict?.isWithheld == false ? verdict?.primaryScore?.value : nil,
                                  processClear: false, createdAt: now,
                                  plan: DecisionPlan(reason: details[0], trigger: details[1], invalidation: details[2], reviewOn: reviewOn),
                                  marketAsOf: verdict?.meta?.marketAsOf)
        entries.insert(entry, at: 0)
        persist()
        return entry
    }

    func completeReview(id: UUID, outcome: DecisionReview.Outcome, lesson: String, now: Date = Date()) throws {
        let text = lesson.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !text.isEmpty, text.count <= 2_000,
              let index = entries.firstIndex(where: { $0.id == id }),
              entries[index].review == nil, now >= entries[index].createdAt else {
            throw JournalError.invalidReview
        }
        entries[index].review = DecisionReview(outcome: outcome, lesson: text, reviewedAt: now)
        persist()
    }

    func dueCount(now: Date = Date()) -> Int {
        entries.filter {
            guard $0.review == nil, let plan = $0.plan else { return false }
            return Calendar.current.startOfDay(for: plan.reviewOn) <= Calendar.current.startOfDay(for: now)
        }.count
    }

    func clear() {
        entries = []
        storage.removeObject(forKey: Self.storageKey)
    }

    #if DEBUG
    func replaceForScreenshot(_ seeded: [DecisionEntry]) {
        entries = seeded
    }
    #endif

    private func load() {
        guard
            let data = storage.data(forKey: Self.storageKey),
            let saved = try? JSONDecoder().decode([DecisionEntry].self, from: data)
        else {
            entries = []
            return
        }
        entries = saved
    }

    private func persist() {
        guard let data = try? JSONEncoder().encode(entries) else { return }
        storage.set(data, forKey: Self.storageKey)
    }
}
