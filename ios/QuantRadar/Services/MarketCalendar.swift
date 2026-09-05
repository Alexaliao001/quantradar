import Foundation

enum MarketCalendar {
    private struct Schedule: Decodable {
        let first_year: Int
        let last_year: Int
        let holidays: Set<String>
        let early_closes: Set<String>
    }

    private static let schedule: Schedule? = {
        guard let url = Bundle.main.url(forResource: "nyse_calendar", withExtension: "json"),
              let data = try? Data(contentsOf: url) else { return nil }
        return try? JSONDecoder().decode(Schedule.self, from: data)
    }()

    private static let barFormatter: DateFormatter = {
        let formatter = DateFormatter()
        formatter.calendar = Calendar(identifier: .gregorian)
        formatter.locale = Locale(identifier: "en_US_POSIX")
        formatter.timeZone = TimeZone(secondsFromGMT: 0)
        formatter.dateFormat = "yyyy-MM-dd"
        return formatter
    }()

    static func barDay(_ date: Date) -> String {
        barFormatter.string(from: date)
    }

    static func completedSession(now: Date = Date()) -> String? {
        guard let schedule else { return nil }
        var calendar = Calendar(identifier: .gregorian)
        calendar.timeZone = TimeZone(identifier: "America/New_York")!
        let year = calendar.component(.year, from: now)
        guard (schedule.first_year...schedule.last_year).contains(year) else { return nil }
        let formatter = DateFormatter()
        formatter.calendar = calendar
        formatter.locale = Locale(identifier: "en_US_POSIX")
        formatter.timeZone = calendar.timeZone
        formatter.dateFormat = "yyyy-MM-dd"
        let today = calendar.startOfDay(for: now)
        var day = today
        for _ in 0..<10 {
            let key = formatter.string(from: day)
            let weekday = calendar.component(.weekday, from: day)
            let closeHour = schedule.early_closes.contains(key) ? 13 : 16
            if weekday != 1 && weekday != 7 && !schedule.holidays.contains(key),
               day < today || calendar.component(.hour, from: now) >= closeHour {
                return key
            }
            guard let previous = calendar.date(byAdding: .day, value: -1, to: day) else { return nil }
            day = previous
        }
        return nil
    }

    static func sessionClose(_ day: String) -> Date? {
        guard let schedule else { return nil }
        let formatter = DateFormatter()
        formatter.locale = Locale(identifier: "en_US_POSIX")
        formatter.timeZone = TimeZone(identifier: "America/New_York")
        formatter.dateFormat = "yyyy-MM-dd HH:mm"
        return formatter.date(from: day + (schedule.early_closes.contains(day) ? " 13:00" : " 16:00"))
    }

    static func completedBars(_ bars: [FreeBar], now: Date = Date(), minimum: Int = 50, fetchedAt: Date? = nil) -> [FreeBar]? {
        guard let expected = completedSession(now: now) else { return nil }
        if let fetchedAt, let close = sessionClose(expected), fetchedAt < close { return nil }
        let selected = bars.filter { barDay($0.date) <= expected }
        guard selected.count >= minimum, let last = selected.last, barDay(last.date) == expected,
              selected.allSatisfy({ $0.close.isFinite && $0.close > 0 && $0.volume.isFinite && $0.volume >= 0 }),
              zip(selected, selected.dropFirst()).allSatisfy({ barDay($0.date) < barDay($1.date) })
        else { return nil }
        return selected
    }
}
