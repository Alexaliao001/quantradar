import SwiftUI

struct SearchView: View {
    @EnvironmentObject private var radar: RadarService
    @EnvironmentObject private var watchlist: WatchlistStore
    @State private var ticker = ""
    @FocusState private var focused: Bool

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: 16) {
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
                                Task { await runScan(forceDemo: chip == "INTC") }
                            }
                            .font(.caption.weight(.semibold))
                            .padding(.horizontal, 10)
                            .padding(.vertical, 6)
                            .background(QRTheme.radarDim)
                            .foregroundStyle(QRTheme.radar)
                            .clipShape(Capsule())
                        }
                    }

                    if radar.isLoading {
                        ProgressView("Running mechanical scan…")
                            .tint(QRTheme.radar)
                            .foregroundStyle(QRTheme.muted)
                    }

                    if let err = radar.errorMessage {
                        Text(err)
                            .font(.footnote)
                            .foregroundStyle(QRTheme.warn)
                    }

                    if let v = radar.latest {
                        VerdictCardView(verdict: v)
                        if let src = radar.lastSource {
                            Text("Source: \(src)")
                                .font(.caption2)
                                .foregroundStyle(QRTheme.muted)
                        }
                        Button {
                            _ = watchlist.add(ticker: v.ticker)
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
        }
    }

    private func runScan(forceDemo: Bool = false) async {
        focused = false
        _ = await radar.analyze(ticker: ticker, forceDemo: forceDemo)
    }
}
