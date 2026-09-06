#if DEBUG
import Foundation

/// Debug-only launch arguments so App Store screenshots can be captured
/// from the simulator framebuffer without clicking a visible window.
enum ScreenshotLaunch {
    static var isEnabled: Bool {
        ProcessInfo.processInfo.arguments.contains("-ui-screenshot")
    }

    static var screen: String {
        let args = ProcessInfo.processInfo.arguments
        guard let idx = args.firstIndex(of: "-qr-screen"), idx + 1 < args.count else {
            return ""
        }
        return args[idx + 1]
    }

    static var tabIndex: Int? {
        switch screen {
        case "scan", "decision", "paywall": return 1
        case "plan": return 2
        case "today": return 0
        case "settings": return 3
        default: return nil
        }
    }

    static var showOnboarding: Bool {
        isEnabled && screen == "onboarding"
    }

    @MainActor
    static func seedJournalIfNeeded(_ journal: DecisionJournal) {
        guard isEnabled, screen == "plan" else { return }
        journal.replaceForScreenshot(
            [
                DecisionEntry(
                    id: UUID(),
                    ticker: "AAPL",
                    radarAction: "WAIT",
                    decision: "WAIT",
                    score: 66,
                    processClear: true,
                    createdAt: Date()
                )
            ]
        )
        AppAccess.storage.set("AAPL", forKey: AppAccess.previewTickerKey)
    }
}
#endif
