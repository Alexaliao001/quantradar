import SwiftUI

@main
struct QuantRadarApp: App {
    @StateObject private var radar = RadarService()
    @StateObject private var watchlist = WatchlistStore()
    @StateObject private var purchases = PurchaseStore()
    @StateObject private var journal = DecisionJournal()
    @AppStorage("hasSeenOnboarding") private var hasSeenOnboarding = false
    @Environment(\.scenePhase) private var scenePhase

    var body: some Scene {
        WindowGroup {
            Group {
                if hasSeenOnboarding {
                    RootTabView()
                } else {
                    OnboardingView(hasSeenOnboarding: $hasSeenOnboarding)
                }
            }
            .environmentObject(radar)
            .environmentObject(watchlist)
            .environmentObject(purchases)
            .environmentObject(journal)
            .preferredColorScheme(.dark)
            .onAppear {
                ReviewPrompt.recordLaunch()
                #if DEBUG
                if ScreenshotLaunch.showOnboarding {
                    hasSeenOnboarding = false
                } else if ScreenshotLaunch.isEnabled {
                    hasSeenOnboarding = true
                    ScreenshotLaunch.seedJournalIfNeeded(journal)
                }
                if ProcessInfo.processInfo.arguments.contains("-qr-force-unlock") {
                    hasSeenOnboarding = true
                    purchases.debugForceUnlocked = true
                }
                if ProcessInfo.processInfo.arguments.contains("-qr-buy-unlock") {
                    hasSeenOnboarding = true
                    Task { _ = await purchases.purchaseUnlock() }
                }
                #endif
            }
            .onChange(of: scenePhase) { _, phase in
                guard phase == .active, purchases.effectiveUnlocked, !watchlist.items.isEmpty else { return }
                Task { await watchlist.refreshScores(using: radar) }
            }
        }
    }
}
