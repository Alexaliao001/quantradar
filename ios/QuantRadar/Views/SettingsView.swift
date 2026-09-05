import SwiftUI

struct SettingsView: View {
    @EnvironmentObject private var purchases: PurchaseStore
    @EnvironmentObject private var journal: DecisionJournal
    @State private var showPaywall = false
    @State private var showClearJournalConfirmation = false

    var body: some View {
        NavigationStack {
            Form {
                Section("Purchase") {
                    LabeledContent(
                        "Core",
                        value: purchases.effectiveUnlocked ? "Unlocked" : "Locked · \(unlockPrice)"
                    )
                    Text("One-time unlock for every supported ticker, watchlist, and 90-day evidence.")
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

                Section("Discipline") {
                    LabeledContent("Streak", value: "\(DisciplineLedger.streak) days")
                    LabeledContent("Waits logged", value: "\(DisciplineLedger.waitCount)")
                    LabeledContent("Decisions saved", value: "\(journal.entries.count)")
                    Text(DisciplineLedger.summaryLine)
                        .font(.caption)
                        .foregroundStyle(.secondary)
                    if !journal.entries.isEmpty {
                        Button("Clear decision history", role: .destructive) {
                            showClearJournalConfirmation = true
                        }
                    }
                }

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
            .frame(maxWidth: 760)
            .frame(maxWidth: .infinity)
            .background(QRTheme.bg.ignoresSafeArea())
            .navigationTitle("Settings")
            .sheet(isPresented: $showPaywall) {
                PaywallView()
                    .environmentObject(purchases)
            }
            .confirmationDialog(
                "Clear decision history?",
                isPresented: $showClearJournalConfirmation,
                titleVisibility: .visible
            ) {
                Button("Clear history", role: .destructive) {
                    journal.clear()
                }
            } message: {
                Text("This removes the private on-device journal. It cannot be undone.")
            }
        }
    }

    private var unlockPrice: String {
        purchases.unlockProduct?.displayPrice ?? "$9.99"
    }
}
