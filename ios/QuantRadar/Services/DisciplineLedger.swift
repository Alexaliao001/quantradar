import Foundation

/// Streak + wait counts. Injectable storage for tests.
enum DisciplineLedger {
    static let streakKey = "qr.discipline.streak"
    static let lastDayKey = "qr.discipline.last_day"
    static let waitCountKey = "qr.discipline.wait_count"
    static let checkCountKey = "qr.discipline.check_count"
    static let avoidedPctKey = "qr.discipline.avoided_pct"
    static let lastClosePrefix = "qr.discipline.last_close."

    static var storage: UserDefaults = .standard

    static func reset() {
        for k in [streakKey, lastDayKey, waitCountKey, checkCountKey, avoidedPctKey] {
            storage.removeObject(forKey: k)
        }
    }

    static var streak: Int { storage.integer(forKey: streakKey) }
    static var waitCount: Int { storage.integer(forKey: waitCountKey) }
    static var checkCount: Int { storage.integer(forKey: checkCountKey) }
    static var avoidedPct: Double { storage.double(forKey: avoidedPctKey) }

    static func dayStamp(_ date: Date = Date()) -> String {
        let fmt = DateFormatter()
        fmt.calendar = PostureDepth.nyCalendar()
        fmt.locale = Locale(identifier: "en_US_POSIX")
        fmt.timeZone = PostureDepth.nyCalendar().timeZone
        fmt.dateFormat = "yyyy-MM-dd"
        return fmt.string(from: date)
    }

    static func record(action: String, ticker: String, close: Double?, date: Date = Date()) {
        let today = dayStamp(date)
        let last = storage.string(forKey: lastDayKey)
        if last != today {
            if last == previousNYDay(from: date) {
                storage.set(streak + 1, forKey: streakKey)
            } else {
                storage.set(1, forKey: streakKey)
            }
            storage.set(today, forKey: lastDayKey)
        }
        storage.set(checkCount + 1, forKey: checkCountKey)
        let code = action.uppercased()
        if code == "WAIT" || code == "NO" || code == "AVOID" {
            storage.set(waitCount + 1, forKey: waitCountKey)
        }

        let closeKey = lastClosePrefix + FreeMarketDataClient.normalize(ticker)
        if let close, close > 0 {
            let prevClose = storage.double(forKey: closeKey)
            let prevAction = storage.string(forKey: closeKey + ".action") ?? ""
            if prevClose > 0, ["WAIT", "NO", "AVOID"].contains(prevAction.uppercased()), close < prevClose {
                let dd = (prevClose - close) / prevClose * 100
                storage.set(avoidedPct + dd, forKey: avoidedPctKey)
            }
            storage.set(close, forKey: closeKey)
            storage.set(code, forKey: closeKey + ".action")
        }
    }

    private static func previousNYDay(from date: Date) -> String {
        let cal = PostureDepth.nyCalendar()
        let prev = cal.date(byAdding: .day, value: -1, to: date) ?? date
        return dayStamp(prev)
    }

    static var summaryLine: String {
        let s = streak
        let w = waitCount
        if s <= 0 && w <= 0 { return "Check in daily. Most days: wait." }
        return "Discipline · \(s)-day streak · \(w) waits logged"
    }
}
