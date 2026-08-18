import SwiftUI

/// Unlock sheet — one product, one decision.
struct PaywallView: View {
    @EnvironmentObject private var purchases: PurchaseStore
    @Environment(\.dismiss) private var dismiss

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: 20) {
                    Text("Unlock any ticker.")
                        .font(.title2.bold())
                        .foregroundStyle(QRTheme.text)

                    Text("You already have today’s SPY and one personal scan. Unlock once for every US ticker plus a watchlist. Most days the honest answer is still wait.")
                        .font(.body)
                        .foregroundStyle(QRTheme.muted)

                    VStack(alignment: .leading, spacing: 10) {
                        bullet("Any US ticker scan")
                        bullet("Watchlist with posture-change alerts")
                        bullet("One-time $9.99 — not a subscription")
                    }
                    .padding(14)
                    .frame(maxWidth: .infinity, alignment: .leading)
                    .background(QRTheme.panel)
                    .clipShape(RoundedRectangle(cornerRadius: 14, style: .continuous))

                    if let err = purchases.lastError {
                        Text(err)
                            .font(.footnote)
                            .foregroundStyle(QRTheme.warn)
                    }

                    Button {
                        Task {
                            if await purchases.purchaseUnlock() {
                                dismiss()
                            }
                        }
                    } label: {
                        Text(unlockButtonTitle)
                            .font(.headline)
                            .frame(maxWidth: .infinity)
                            .padding(.vertical, 14)
                            .background(QRTheme.radar)
                            .foregroundStyle(.black)
                            .clipShape(RoundedRectangle(cornerRadius: 14, style: .continuous))
                    }
                    .disabled(purchases.isBusy || purchases.effectiveUnlocked)

                    Button("Restore Purchases") {
                        Task { await purchases.restore() }
                    }
                    .disabled(purchases.isBusy)

                    Text("Educational only — not investment advice. No guarantee of outcomes.")
                        .font(.caption2)
                        .foregroundStyle(QRTheme.muted)
                }
                .padding(20)
            }
            .background(QRTheme.bg.ignoresSafeArea())
            .navigationTitle("Unlock")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .topBarTrailing) {
                    Button("Close") { dismiss() }
                }
            }
        }
    }

    private var unlockButtonTitle: String {
        if purchases.effectiveUnlocked { return "Already unlocked" }
        if let p = purchases.unlockProduct {
            return "Unlock · \(p.displayPrice)"
        }
        return "Unlock · $9.99"
    }

    private func bullet(_ text: String) -> some View {
        HStack(alignment: .top, spacing: 8) {
            Image(systemName: "checkmark.circle.fill")
                .foregroundStyle(QRTheme.radar)
            Text(text)
                .foregroundStyle(QRTheme.text)
                .font(.subheadline)
        }
    }
}
