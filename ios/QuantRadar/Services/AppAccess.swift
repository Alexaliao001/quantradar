import Foundation

/// Product IDs and free-preview gates for the free-download + unlock model.
/// Preview is Today SPY + one lifetime personal ticker — not daily quotas.
enum AppAccess {
    static let unlockProductID = "one.quantradar.app.unlock"
    static let liveMonthlyProductID = "one.quantradar.app.live.monthly"
    static let liveYearlyProductID = "one.quantradar.app.live.yearly"

    static let freeMarketTicker = "SPY"
    static let freeWatchlistLimit = 20
    static let livePlusWatchlistLimit = 50

    static let privacyURL = "https://quantradar.one/privacy-ios"
    static let termsURL = "https://quantradar.one/terms-ios"

    static let differentiationLine = "One score. Most days: don’t act — not tipster noise."
    static let previewLine = "Free: today’s SPY plus one ticker of yours."
    static let founderPriceLine = "Launch unlock. One-time, not a subscription. Restore anytime."

    static let previewTickerKey = "qr.preview.personal_ticker"

    /// Injectable for tests. Production uses `.standard`.
    static var storage: UserDefaults = .standard

    static func normalizeTicker(_ ticker: String) -> String {
        ticker.trimmingCharacters(in: .whitespacesAndNewlines).uppercased()
    }

    static var claimedPreviewTicker: String? {
        let t = normalizeTicker(storage.string(forKey: previewTickerKey) ?? "")
        return t.isEmpty ? nil : t
    }

    static func resetPreviewTicker() {
        storage.removeObject(forKey: previewTickerKey)
    }

    /// SPY is always free (Today). One other ticker can be claimed for life.
    /// While nothing is claimed, any non-empty ticker may be scanned once.
    static func canScan(ticker: String, unlocked: Bool) -> Bool {
        let t = normalizeTicker(ticker)
        guard !t.isEmpty else { return false }
        if unlocked { return true }
        if t == freeMarketTicker { return true }
        if let claimed = claimedPreviewTicker {
            return claimed == t
        }
        return true
    }

    /// Second personal ticker (and beyond) stays locked until unlock.
    static func isPreviewLocked(ticker: String, unlocked: Bool) -> Bool {
        !canScan(ticker: ticker, unlocked: unlocked)
    }

    static func anxietyCopy(ticker: String) -> String {
        let t = normalizeTicker(ticker)
        if t.isEmpty { return "Should you chase another ticker right now?" }
        return "Should you chase \(t) right now?"
    }

    /// Persist the first successful personal preview ticker. SPY does not consume it.
    @discardableResult
    static func claimPreviewTickerIfNeeded(_ ticker: String, withheld: Bool) -> Bool {
        let t = normalizeTicker(ticker)
        if withheld || t.isEmpty || t == freeMarketTicker { return true }
        if let claimed = claimedPreviewTicker {
            return claimed == t
        }
        storage.set(t, forKey: previewTickerKey)
        return true
    }

    static func watchlistLimit(livePlus: Bool) -> Int {
        livePlus ? livePlusWatchlistLimit : freeWatchlistLimit
    }

    static func reminderIntervalSeconds(livePlus: Bool) -> TimeInterval {
        livePlus ? 60 * 60 * 6 : 60 * 60 * 24
    }

    /// Fire a local alert only when a watched ticker's action actually changes.
    static func shouldNotifyPostureChange(previous: String?, next: String, remind: Bool) -> Bool {
        guard remind else { return false }
        let prev = (previous ?? "").uppercased()
        let nxt = next.uppercased()
        guard !prev.isEmpty, prev != nxt else { return false }
        return true
    }
}
