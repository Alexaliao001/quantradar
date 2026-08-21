import Foundation
import UserNotifications

struct WatchItem: Codable, Identifiable, Hashable {
    var id: String { ticker }
    let ticker: String
    var note: String
    var remindOnImprove: Bool
    var lastAction: String?
    var lastScore: Double?
}

@MainActor
final class WatchlistStore: ObservableObject {
    @Published private(set) var items: [WatchItem] = []
    @Published private(set) var isRefreshing = false

    private let key = "qr.watchlist"

    init() { load() }

    func load() {
        guard let data = UserDefaults.standard.data(forKey: key),
              let decoded = try? JSONDecoder().decode([WatchItem].self, from: data) else {
            items = []
            return
        }
        items = decoded
    }

    private func persist() {
        if let data = try? JSONEncoder().encode(items) {
            UserDefaults.standard.set(data, forKey: key)
        }
    }

    func canAdd(limit: Int) -> Bool {
        items.count < limit
    }

    @discardableResult
    func add(ticker: String, limit: Int) -> Bool {
        let t = ticker.uppercased()
        guard !items.contains(where: { $0.ticker == t }) else { return true }
        guard canAdd(limit: limit) else { return false }
        items.insert(WatchItem(ticker: t, note: "", remindOnImprove: true, lastAction: nil, lastScore: nil), at: 0)
        persist()
        return true
    }

    func remove(_ ticker: String) {
        items.removeAll { $0.ticker == ticker }
        persist()
    }

    func setRemind(_ ticker: String, enabled: Bool, livePlus: Bool = false) {
        guard let idx = items.firstIndex(where: { $0.ticker == ticker }) else { return }
        items[idx].remindOnImprove = enabled
        persist()
        if enabled {
            Task { _ = await AlertScheduler.requestPermission() }
        }
        _ = livePlus
    }

    func updateAction(_ ticker: String, action: String, score: Double? = nil) {
        guard let idx = items.firstIndex(where: { $0.ticker == ticker }) else { return }
        items[idx].lastAction = action
        if let score { items[idx].lastScore = score }
        persist()
    }

    /// Refresh watchlist scores with limited concurrency (max 2) so SPY cache is reused.
    func refreshScores(using radar: RadarService) async {
        guard !items.isEmpty, !isRefreshing else { return }
        isRefreshing = true
        defer { isRefreshing = false }

        let tickers = items.map(\.ticker)
        var index = 0
        let limit = 2

        await withTaskGroup(of: (String, RadarVerdict?).self) { group in
            func enqueueNext() {
                guard index < tickers.count else { return }
                let t = tickers[index]
                index += 1
                group.addTask {
                    let verdict = await radar.scoreQuietly(ticker: t)
                    return (t, verdict)
                }
            }

            for _ in 0..<min(limit, tickers.count) { enqueueNext() }

            for await (ticker, verdict) in group {
                if let verdict {
                    let previous = items.first(where: { $0.ticker == ticker })?.lastAction
                    let remind = items.first(where: { $0.ticker == ticker })?.remindOnImprove ?? false
                    let next = (verdict.primary?.action ?? "WAIT")
                    updateAction(
                        ticker,
                        action: next,
                        score: verdict.primaryScore?.value
                    )
                    if AppAccess.shouldNotifyPostureChange(previous: previous, next: next, remind: remind) {
                        await AlertScheduler.notifyPostureChange(ticker: ticker, action: next)
                    }
                }
                enqueueNext()
            }
        }
    }
}

enum AlertScheduler {
    static func requestPermission() async -> Bool {
        let center = UNUserNotificationCenter.current()
        let granted = try? await center.requestAuthorization(options: [.alert, .sound, .badge])
        return granted == true
    }

    static func notifyPostureChange(ticker: String, action: String) async {
        guard await requestPermission() else { return }
        let content = UNMutableNotificationContent()
        content.title = "\(ticker) posture changed"
        content.body = "Now \(action). Educational only — not investment advice."
        content.sound = .default
        let trigger = UNTimeIntervalNotificationTrigger(timeInterval: 1, repeats: false)
        let req = UNNotificationRequest(
            identifier: "watch-change-\(ticker)-\(Int(Date().timeIntervalSince1970))",
            content: content,
            trigger: trigger
        )
        try? await UNUserNotificationCenter.current().add(req)
    }
}
