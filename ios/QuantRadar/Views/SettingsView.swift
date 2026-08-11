import SwiftUI

struct SettingsView: View {
    var body: some View {
        NavigationStack {
            Form {
                Section("Purchase") {
                    LabeledContent("App Store", value: "Paid · $9.99")
                    Text("You own this install. Website Stripe / Massive Pro do not apply.")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }

                Section("Data (zero COGS)") {
                    LabeledContent("Primary", value: "Yahoo q1")
                    LabeledContent("Backup", value: "Yahoo q2 → Nasdaq")
                    Text("iOS never calls Massive/Polygon. Failover verified for US tickers. Web desk stays on Massive separately.")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }

                Section("Legal") {
                    Text("Educational radar only. Not investment advice. Not a broker. No guarantee of outcomes.")
                    Link("Privacy Policy", destination: URL(string: "https://quantradar.one/privacy")!)
                    Link("Terms of Use", destination: URL(string: "https://quantradar.one/terms")!)
                    Link(
                        "EULA (Apple standard)",
                        destination: URL(string: "https://www.apple.com/legal/internet-services/itunes/dev/stdeula/")!
                    )
                }

                Section("About") {
                    LabeledContent(
                        "Version",
                        value: Bundle.main.infoDictionary?["CFBundleShortVersionString"] as? String ?? "1.0"
                    )
                    Text("Independent paid App Store product. Free-data mechanical radar.")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }
            }
            .scrollContentBackground(.hidden)
            .background(QRTheme.bg.ignoresSafeArea())
            .navigationTitle("Settings")
        }
    }
}
