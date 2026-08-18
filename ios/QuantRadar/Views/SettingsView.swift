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
                    Text("One-time unlock for any ticker and watchlist.")
                        .font(.caption)
                        .foregroundStyle(.secondary)

                    if !purchases.effectiveUnlocked {
                        Button("Unlock full radar") { showPaywall = true }
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

                Section("Legal") {
                    Text("Educational radar only. Not investment advice. Not a broker. No guarantee of outcomes.")
                    Link("Privacy Policy (iOS)", destination: URL(string: AppAccess.privacyURL)!)
                    Link("Terms of Use (iOS)", destination: URL(string: AppAccess.termsURL)!)
                    Link(
                        "EULA (Apple standard)",
                        destination: URL(string: "https://www.apple.com/legal/internet-services/itunes/dev/stdeula/")!
                    )
                }

                Section("About") {
                    LabeledContent(
                        "Version",
                        value: Bundle.main.infoDictionary?["CFBundleShortVersionString"] as? String ?? "1.1"
                    )
                    Text("Independent App Store product. Website subscriptions do not unlock this app.")
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
