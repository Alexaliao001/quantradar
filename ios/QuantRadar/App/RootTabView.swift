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
    @State private var selection = 2

    var body: some View {
        TabView(selection: $selection) {
            WatchlistView()
                .tabItem { Label("Plan", systemImage: "checklist") }
                .tag(2)
            TodayView()
                .tabItem { Label("Today", systemImage: "dot.radiowaves.left.and.right") }
                .tag(0)
            SearchView()
                .tabItem { Label("Scan", systemImage: "magnifyingglass") }
                .tag(1)
            SettingsView()
                .tabItem { Label("Settings", systemImage: "gearshape") }
                .tag(3)
        }
        .tint(QRTheme.radar)
        .onAppear {
            #if DEBUG
            if let tab = ScreenshotLaunch.tabIndex {
                selection = tab
            }
            #endif
        }
    }
}
