import SwiftUI

struct WatchlistView: View {
    @EnvironmentObject private var watchlist: WatchlistStore
    @EnvironmentObject private var radar: RadarService
    @EnvironmentObject private var purchases: PurchaseStore

    var body: some View {
        NavigationStack {
            Group {
                if watchlist.items.isEmpty {
                    ContentUnavailableView(
                        "No watches yet",
                        systemImage: "eye.slash",
                        description: Text("Scan a ticker and tap Add to Watch.")
                    )
                } else {
                    List {
                        ForEach(watchlist.items) { item in
                            VStack(alignment: .leading, spacing: 8) {
                                HStack {
                                    Text(item.ticker)
                                        .font(.headline)
                                        .foregroundStyle(QRTheme.text)
                                    Spacer()
                                    if let score = item.lastScore {
                                        Text(String(format: "%.0f", score))
                                            .font(.caption.monospacedDigit().weight(.semibold))
                                            .foregroundStyle(QRTheme.muted)
                                    }
                                    if let a = item.lastAction {
                                        Text(a)
                                            .font(.caption.weight(.bold))
                                            .foregroundStyle(QRTheme.warn)
                                    }
                                }
                                Toggle(
                                    "Remind if posture changes",
                                    isOn: Binding(
                                        get: { item.remindOnImprove },
                                        set: {
                                            watchlist.setRemind(
                                                item.ticker,
                                                enabled: $0,
                                                livePlus: purchases.effectiveLivePlus
                                            )
                                        }
                                    )
                                )
                                .tint(QRTheme.radar)
                                .font(.subheadline)
                            }
                            .listRowBackground(QRTheme.panel)
                        }
                        .onDelete { idx in
                            idx.map { watchlist.items[$0].ticker }.forEach(watchlist.remove)
                        }
                    }
                    .scrollContentBackground(.hidden)
                    .overlay(alignment: .top) {
                        if watchlist.isRefreshing {
                            ProgressView()
                                .tint(QRTheme.radar)
                                .padding(8)
                        }
                    }
                }
            }
            .background(QRTheme.bg.ignoresSafeArea())
            .navigationTitle("Watch")
            .toolbar {
                ToolbarItem(placement: .topBarTrailing) {
                    Button {
                        Task { await watchlist.refreshScores(using: radar) }
                    } label: {
                        Image(systemName: "arrow.clockwise")
                    }
                    .disabled(watchlist.items.isEmpty || watchlist.isRefreshing)
                }
            }
            .task {
                guard !watchlist.items.isEmpty else { return }
                await watchlist.refreshScores(using: radar)
            }
        }
    }
}
