import SwiftUI

enum QRTheme {
    static let bg = Color(red: 0.043, green: 0.059, blue: 0.055)
    static let panel = Color(red: 0.07, green: 0.10, blue: 0.09)
    static let radar = Color(red: 0.18, green: 0.80, blue: 0.44)
    static let radarDim = Color(red: 0.18, green: 0.80, blue: 0.44).opacity(0.18)
    static let text = Color(red: 0.92, green: 0.95, blue: 0.93)
    static let muted = Color(red: 0.55, green: 0.62, blue: 0.58)
    static let danger = Color(red: 0.95, green: 0.35, blue: 0.32)
    static let warn = Color(red: 0.95, green: 0.72, blue: 0.25)
}

struct RootTabView: View {
    @EnvironmentObject private var purchases: PurchaseStore

    var body: some View {
        TabView {
            TodayView()
                .tabItem { Label("Today", systemImage: "dot.radiowaves.left.and.right") }
            SearchView()
                .tabItem { Label("Scan", systemImage: "magnifyingglass") }
            if purchases.effectiveUnlocked {
                WatchlistView()
                    .tabItem { Label("Watch", systemImage: "eye") }
            }
            SettingsView()
                .tabItem { Label("Settings", systemImage: "gearshape") }
        }
        .tint(QRTheme.radar)
    }
}
