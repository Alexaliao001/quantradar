import SwiftUI

/// Unlock sheet — one product, one decision.
struct PaywallView: View {
    @EnvironmentObject private var purchases: PurchaseStore
    @Environment(\.dismiss) private var dismiss
    var focusTicker: String? = nil

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: 20) {
                    Text(AppAccess.differentiationLine)
                        .font(.headline)
                        .foregroundStyle(QRTheme.radar)

                    Text("Unlock any ticker.")
                        .font(.title2.bold())
                        .foregroundStyle(QRTheme.text)

                    Text(headline)
                        .font(.body)
                        .foregroundStyle(QRTheme.muted)

                    VStack(alignment: .leading, spacing: 10) {
                        bullet("Every supported US ticker scan")
                        bullet("Watchlist refreshed when you open the app")
                        bullet("90-day posture strip and setup evidence")
                        bullet("One-time \(unlockPrice) — not a subscription")
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

                    Text(AppAccess.founderPriceLine)
                        .font(.caption)
                        .foregroundStyle(QRTheme.muted)

                    Text("Educational only — not investment advice. No guarantee of outcomes.")
                        .font(.caption2)
                        .foregroundStyle(QRTheme.muted)
                }
                .padding(20)
                .frame(maxWidth: 620)
                .frame(maxWidth: .infinity)
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

    private var headline: String {
        if let t = focusTicker, !t.isEmpty {
            return "\(AppAccess.anxietyCopy(ticker: t)) You already have today’s SPY and one personal scan. Unlock once for every supported US ticker plus a watchlist. Most days the honest answer is still wait."
        }
        return "You already have today’s SPY and one personal scan. Unlock once for every supported US ticker plus a watchlist. Most days the honest answer is still wait."
    }

    private var unlockButtonTitle: String {
        if purchases.effectiveUnlocked { return "Already unlocked" }
        if let p = purchases.unlockProduct {
            return "Unlock · \(p.displayPrice)"
        }
        return "Unlock · $9.99"
    }

    private var unlockPrice: String {
        purchases.unlockProduct?.displayPrice ?? "$9.99"
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
