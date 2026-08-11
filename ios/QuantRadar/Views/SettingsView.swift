import SwiftUI

struct SettingsView: View {
    @EnvironmentObject private var purchases: PurchaseStore
    @State private var showPaywall = false

    var body: some View {
        NavigationStack {
            Form {
                Section("Purchase") {
                    LabeledContent(
                        "Core",
                        value: purchases.effectiveUnlocked ? "Unlocked" : "Locked · $9.99"
                    )
                    LabeledContent(
                        "Live+",
                        value: purchases.effectiveLivePlus ? "Active" : "Off"
                    )
                    Text(AppAccess.appStorePriceNote)
                        .font(.caption)
                        .foregroundStyle(.secondary)
                    Text("Website Stripe / Massive Pro do not apply.")
                        .font(.caption)
                        .foregroundStyle(.secondary)

                    if !purchases.effectiveUnlocked {
                        Button("Unlock full radar") { showPaywall = true }
                    }

                    if purchases.effectiveUnlocked && !purchases.effectiveLivePlus {
                        Button("Live+ Monthly") {
                            Task { _ = await purchases.purchaseLivePlus(yearly: false) }
                        }
                        .disabled(purchases.isBusy)
                        Button("Live+ Yearly") {
                            Task { _ = await purchases.purchaseLivePlus(yearly: true) }
                        }
                        .disabled(purchases.isBusy)
                        Text("Live+ raises watch limit to \(AppAccess.livePlusWatchlistLimit) and uses denser on-device reminders. Not server push.")
                            .font(.caption2)
                            .foregroundStyle(.secondary)
                    }

                    Button("Restore Purchases") {
                        Task { await purchases.restore() }
                    }
                    .disabled(purchases.isBusy)

                    if let err = purchases.lastError {
                        Text(err)
                            .font(.caption)
                            .foregroundStyle(QRTheme.warn)
                    }
                }

                #if DEBUG
                Section("Debug") {
                    Toggle("Force unlocked", isOn: $purchases.debugForceUnlocked)
                    Toggle("Force Live+", isOn: $purchases.debugForceLivePlus)
                }
                #endif

                Section("Data (zero COGS)") {
                    LabeledContent("Primary", value: "Yahoo q1")
                    LabeledContent("Backup", value: "Yahoo q2 → Nasdaq")
                    Text("iOS never calls Massive/Polygon. Failover verified for US tickers. Web desk stays on Massive separately.")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }

                Section("Legal") {
                    Text("Educational radar only. Not investment advice. Not a broker. No guarantee of outcomes.")
                    Text(AppAccess.differentiationLine)
                        .font(.caption)
                        .foregroundStyle(.secondary)
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
                    Text("Independent App Store product. Free download · one-time unlock · optional Live+.")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }
            }
            .scrollContentBackground(.hidden)
            .background(QRTheme.bg.ignoresSafeArea())
            .navigationTitle("Settings")
            .sheet(isPresented: $showPaywall) {
                PaywallView()
                    .environmentObject(purchases)
            }
        }
    }
}
