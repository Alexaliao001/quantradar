import Foundation
import UserNotifications

/// Weekday 09:25 America/New_York local notification. Copy is static on
/// purpose — we do not invent a score in the banner.
enum DailyBriefing {
    static let idPrefix = "qr.briefing.weekday."
    static let hour = 9
    static let minute = 25

    static func requestAndSchedule() async {
        let center = UNUserNotificationCenter.current()
        let granted = (try? await center.requestAuthorization(options: [.alert, .sound, .badge])) ?? false
        guard granted else { return }
        await schedule(center: center)
    }

    static func schedule(center: UNUserNotificationCenter = .current()) async {
        let existing = await center.pendingNotificationRequests()
        for req in existing where req.identifier.hasPrefix(idPrefix) {
            center.removePendingNotificationRequests(withIdentifiers: [req.identifier])
        }
        let tz = TimeZone(identifier: "America/New_York") ?? .gmt
        // Sunday=1 … Saturday=7. Weekdays 2...6.
        for weekday in 2...6 {
            var comps = DateComponents()
            comps.weekday = weekday
            comps.hour = hour
            comps.minute = minute
            comps.timeZone = tz
            let content = UNMutableNotificationContent()
            content.title = "Today's radar is ready"
            content.body = "Open QuantRadar for SPY posture. Most days the honest answer is wait."
            content.sound = .default
            let trigger = UNCalendarNotificationTrigger(dateMatching: comps, repeats: true)
            let req = UNNotificationRequest(
                identifier: "\(idPrefix)\(weekday)",
                content: content,
                trigger: trigger
            )
            try? await center.add(req)
        }
    }
}
