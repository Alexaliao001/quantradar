import Foundation

struct DecisionEntry: Codable, Identifiable, Hashable {
    let id: UUID
    let ticker: String
    let radarAction: String
    let decision: String
    let score: Double?
    let processClear: Bool
    let createdAt: Date
}

/// Private, on-device record of decisions made before a trade.
@MainActor
final class DecisionJournal: ObservableObject {
    @Published private(set) var entries: [DecisionEntry] = []

    static let storageKey = "qr.decision.journal"
    private static let maxEntries = 100

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
        let action = verdict.actionCode
        let decision: String
        if !chaseCheck.isClear {
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
            score: verdict.primaryScore?.value,
            processClear: chaseCheck.isClear,
            createdAt: now
        )

        if let first = entries.first,
           first.ticker == entry.ticker,
           Calendar.current.isDate(first.createdAt, inSameDayAs: now) {
            entries[0] = entry
        } else {
            entries.insert(entry, at: 0)
        }
        if entries.count > Self.maxEntries {
            entries.removeLast(entries.count - Self.maxEntries)
        }
        persist()
        return entry
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
