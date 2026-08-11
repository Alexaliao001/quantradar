import Foundation

/// Product IDs and free-preview gates for the free-download + unlock model.
/// Not freemium quotas — preview Today/INTC, then one-time unlock.
enum AppAccess {
    static let unlockProductID = "one.quantradar.app.unlock"
    static let liveMonthlyProductID = "one.quantradar.app.live.monthly"
    static let liveYearlyProductID = "one.quantradar.app.live.yearly"

    static let freeDemoTicker = "INTC"
    static let freeWatchlistLimit = 20
    static let livePlusWatchlistLimit = 50

    static let appStorePriceNote = "Free to try · $9.99 unlock · optional Live+"
    static let differentiationLine = "One score. Most days: don’t act — not tipster noise."

    static func normalizeTicker(_ ticker: String) -> String {
        ticker.trimmingCharacters(in: .whitespacesAndNewlines).uppercased()
    }

    /// Free preview may only force-demo INTC (or unlocked full scan).
    static func canScan(ticker: String, unlocked: Bool) -> Bool {
        unlocked || normalizeTicker(ticker) == freeDemoTicker
    }

    static func watchlistLimit(livePlus: Bool) -> Int {
        livePlus ? livePlusWatchlistLimit : freeWatchlistLimit
    }

    /// Local reminder cadence — Live+ is more frequent; still on-device only.
    static func reminderIntervalSeconds(livePlus: Bool) -> TimeInterval {
        livePlus ? 60 * 60 * 6 : 60 * 60 * 24
    }
}
