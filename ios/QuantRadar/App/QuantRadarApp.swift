import SwiftUI

@main
struct QuantRadarApp: App {
    @StateObject private var radar = RadarService()
    @StateObject private var watchlist = WatchlistStore()
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
            .preferredColorScheme(.dark)
        }
    }
}
