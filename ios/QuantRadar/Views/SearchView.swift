import SwiftUI

struct SearchView: View {
    @EnvironmentObject private var radar: RadarService
    @EnvironmentObject private var watchlist: WatchlistStore
    @EnvironmentObject private var purchases: PurchaseStore
    @State private var ticker = ""
    @State private var showPaywall = false
    @State private var paywallTicker: String?
    @State private var gateMessage: String?
    @State private var lockedPreview = false
    @FocusState private var focused: Bool

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: 16) {
                    Text(AppAccess.differentiationLine)
                        .font(.footnote)
                        .foregroundStyle(QRTheme.muted)

                    HStack {
                        TextField("Ticker (e.g. AAPL)", text: $ticker)
                            .textInputAutocapitalization(.characters)
                            .autocorrectionDisabled()
                            .focused($focused)
                            .padding(14)
                            .background(QRTheme.panel)
                            .clipShape(RoundedRectangle(cornerRadius: 12, style: .continuous))
                            .foregroundStyle(QRTheme.text)

                        Button("Scan") { Task { await runScan() } }
                            .buttonStyle(.borderedProminent)
                            .tint(QRTheme.radar)
                            .foregroundStyle(.black)
                            .disabled(radar.isLoading || ticker.trimmingCharacters(in: .whitespaces).isEmpty)
                    }

                    HStack(spacing: 8) {
                        ForEach(["SPY", "AAPL", "NVDA", "MSFT"], id: \.self) { chip in
                            Button(chip) {
                                ticker = chip
                                Task { await runScan() }
                            }
                            .font(.caption.weight(.semibold))
                            .padding(.horizontal, 10)
                            .padding(.vertical, 6)
                            .background(QRTheme.radarDim)
                            .foregroundStyle(QRTheme.radar)
                            .clipShape(Capsule())
                        }
                    }

                    if !purchases.effectiveUnlocked {
                        Text(previewCaption)
                            .font(.caption)
                            .foregroundStyle(QRTheme.muted)
                    }

                    if radar.isLoading {
                        ProgressView("Running mechanical scan…")
                            .tint(QRTheme.radar)
                            .foregroundStyle(QRTheme.muted)
                    }

                    if let gateMessage {
                        Text(gateMessage)
                            .font(.footnote)
                            .foregroundStyle(QRTheme.warn)
                    }

                    if let err = radar.errorMessage {
                        Text(err)
                            .font(.footnote)
                            .foregroundStyle(QRTheme.warn)
                    }

                    if let v = radar.latest {
                        if lockedPreview {
                            LockedVerdictView(verdict: v) {
                                paywallTicker = v.ticker
                                showPaywall = true
                            }
                        } else {
                            VerdictCardView(verdict: v)
                            Text("Educational only — not investment advice. Not a broker.")
                                .font(.caption2)
                                .foregroundStyle(QRTheme.muted)
                            Button {
                                addToWatch(v.ticker)
                            } label: {
                                Label("Add to Watch", systemImage: "eye")
                            }
                            .buttonStyle(.bordered)
                        }
                    }
                }
                .padding(20)
            }
            .background(QRTheme.bg.ignoresSafeArea())
            .navigationTitle("Scan")
            .onChange(of: radar.latest?.ticker) { _, _ in
                if let v = radar.latest, !lockedPreview { ReviewPrompt.recordVerdict(v) }
            }
            .sheet(isPresented: $showPaywall) {
                PaywallView(focusTicker: paywallTicker)
                    .environmentObject(purchases)
            }
        }
    }

    private var previewCaption: String {
        if let claimed = AppAccess.claimedPreviewTicker {
            return "Free ticker: \(claimed). Unlock for any other symbol."
        }
        return AppAccess.previewLine
    }

    private func runScan() async {
        focused = false
        gateMessage = nil
        let symbol = AppAccess.normalizeTicker(ticker)
        let locked = AppAccess.isPreviewLocked(ticker: symbol, unlocked: purchases.effectiveUnlocked)
        lockedPreview = locked
        let ok = await radar.analyze(ticker: symbol)
        guard ok, let latest = radar.latest else { return }
        if locked {
            paywallTicker = symbol
            showPaywall = true
            return
        }
        if !latest.isWithheld {
            AppAccess.claimPreviewTickerIfNeeded(symbol, withheld: false)
            DisciplineLedger.record(action: latest.actionCode, ticker: symbol, close: nil)
        }
    }

    private func addToWatch(_ ticker: String) {
        guard purchases.effectiveUnlocked else {
            gateMessage = "Unlock to use Watch."
            paywallTicker = ticker
            showPaywall = true
            return
        }
        if !watchlist.add(ticker: ticker, limit: purchases.watchlistLimit) {
            gateMessage = "Watchlist full (\(purchases.watchlistLimit))."
        }
    }
}
