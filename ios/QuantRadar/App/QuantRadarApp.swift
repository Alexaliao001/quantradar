import SwiftUI

@main
struct QuantRadarApp: App {
    @StateObject private var radar = RadarService()
    @StateObject private var watchlist = WatchlistStore()
    @StateObject private var purchases = PurchaseStore()
    @AppStorage("hasSeenOnboarding") private var hasSeenOnboarding = false

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
            .preferredColorScheme(.dark)
            .onAppear { ReviewPrompt.recordLaunch() }
        }
    }
}
