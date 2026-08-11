import SwiftUI

struct SearchView: View {
    @EnvironmentObject private var radar: RadarService
    @EnvironmentObject private var watchlist: WatchlistStore
    @EnvironmentObject private var purchases: PurchaseStore
    @State private var ticker = ""
    @State private var showPaywall = false
    @State private var gateMessage: String?
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
                        ForEach(["INTC", "AAPL", "NVDA", "SPY"], id: \.self) { chip in
                            Button(chip) {
                                ticker = chip
                                Task { await runScan(forceDemo: chip == AppAccess.freeDemoTicker) }
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
                        Text("Free preview: INTC demo only. Unlock for any ticker.")
                            .font(.caption)
                            .foregroundStyle(QRTheme.warn)
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
                        VerdictCardView(verdict: v)
                        Text("Educational only — not investment advice. Not a broker.")
                            .font(.caption2)
                            .foregroundStyle(QRTheme.muted)
                        if let src = radar.lastSource {
                            Text("Source: \(src)")
                                .font(.caption2)
                                .foregroundStyle(QRTheme.muted)
                        }
                        Button {
                            addToWatch(v.ticker)
                        } label: {
                            Label("Add to Watch", systemImage: "eye")
                        }
                        .buttonStyle(.bordered)
                    }
                }
                .padding(20)
            }
            .background(QRTheme.bg.ignoresSafeArea())
            .navigationTitle("Scan")
            .sheet(isPresented: $showPaywall) {
                PaywallView()
                    .environmentObject(purchases)
            }
        }
    }

    private func runScan(forceDemo: Bool = false) async {
        focused = false
        gateMessage = nil
        let symbol = AppAccess.normalizeTicker(ticker)
        if forceDemo && symbol == AppAccess.freeDemoTicker {
            _ = await radar.analyze(ticker: symbol, forceDemo: true)
            return
        }
        guard AppAccess.canScan(ticker: symbol, unlocked: purchases.effectiveUnlocked) else {
            gateMessage = "Unlock required to scan \(symbol). INTC demo stays free."
            showPaywall = true
            return
        }
        _ = await radar.analyze(ticker: symbol, forceDemo: false)
    }

    private func addToWatch(_ ticker: String) {
        guard purchases.effectiveUnlocked else {
            gateMessage = "Unlock to use Watch."
            showPaywall = true
            return
        }
        if !watchlist.add(ticker: ticker, limit: purchases.watchlistLimit) {
            gateMessage = "Watchlist full (\(purchases.watchlistLimit)). Live+ raises the limit."
        }
    }
}
