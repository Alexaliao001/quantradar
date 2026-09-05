import SwiftUI

struct WatchlistView: View {
    @EnvironmentObject private var watchlist: WatchlistStore
    @EnvironmentObject private var radar: RadarService
    @EnvironmentObject private var purchases: PurchaseStore
    @EnvironmentObject private var journal: DecisionJournal
    @State private var showPaywall = false

    var body: some View {
        NavigationStack {
            List {
                Section {
                    if journal.entries.isEmpty {
                        VStack(alignment: .leading, spacing: 6) {
                            Text("No decisions logged yet")
                                .font(.headline)
                            Text("Run a Chase Check, read the radar, then save the decision before you know the outcome.")
                                .font(.caption)
                                .foregroundStyle(QRTheme.muted)
                        }
                        .padding(.vertical, 6)
                    } else {
                        ForEach(journal.entries.prefix(12)) { entry in
                            decisionRow(entry)
                        }
                    }
                } header: {
                    Text("Decision journal")
                } footer: {
                    Text(journal.summaryLine)
                }

                Section("Watchlist") {
                    if !purchases.effectiveUnlocked {
                        VStack(alignment: .leading, spacing: 10) {
                            Label("Unlock Watch", systemImage: "lock")
                                .font(.headline)
                            Text("Keep tickers together and refresh their mechanical posture. Unlock once — not a subscription.")
                                .font(.caption)
                                .foregroundStyle(QRTheme.muted)
                            Button("Unlock full radar") { showPaywall = true }
                                .buttonStyle(.borderedProminent)
                                .tint(QRTheme.radar)
                                .foregroundStyle(.black)
                        }
                        .padding(.vertical, 6)
                    } else if watchlist.items.isEmpty {
                        Text("Scan a ticker and tap Add to Watch.")
                            .foregroundStyle(QRTheme.muted)
                    } else {
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
                }
            }
            .scrollContentBackground(.hidden)
            .frame(maxWidth: 760)
            .frame(maxWidth: .infinity)
            .overlay(alignment: .top) {
                if watchlist.isRefreshing {
                    ProgressView()
                        .tint(QRTheme.radar)
                        .padding(8)
                }
            }
            .background(QRTheme.bg.ignoresSafeArea())
            .navigationTitle("Plan")
            .toolbar {
                ToolbarItem(placement: .topBarTrailing) {
                    Button {
                        Task { await watchlist.refreshScores(using: radar) }
                    } label: {
                        Image(systemName: "arrow.clockwise")
                    }
                    .disabled(
                        !purchases.effectiveUnlocked
                            || watchlist.items.isEmpty
                            || watchlist.isRefreshing
                    )
                }
            }
            .task {
                guard purchases.effectiveUnlocked, !watchlist.items.isEmpty else { return }
                await watchlist.refreshScores(using: radar)
            }
            .sheet(isPresented: $showPaywall) {
                PaywallView()
                    .environmentObject(purchases)
            }
        }
    }

    private func decisionRow(_ entry: DecisionEntry) -> some View {
        VStack(alignment: .leading, spacing: 6) {
            HStack {
                Text(entry.ticker)
                    .font(.headline)
                    .foregroundStyle(QRTheme.text)
                Text(entry.decision)
                    .font(.caption2.monospaced().weight(.bold))
                    .padding(.horizontal, 7)
                    .padding(.vertical, 3)
                    .background((entry.processClear ? QRTheme.radar : QRTheme.warn).opacity(0.18))
                    .foregroundStyle(entry.processClear ? QRTheme.radar : QRTheme.warn)
                    .clipShape(Capsule())
                Spacer()
                if let score = entry.score {
                    Text(String(format: "%.0f", score))
                        .font(.caption.monospacedDigit().weight(.semibold))
                        .foregroundStyle(QRTheme.muted)
                }
            }
            HStack {
                Text("Radar \(entry.radarAction)")
                Text("·")
                Text(entry.createdAt.formatted(date: .abbreviated, time: .omitted))
            }
            .font(.caption)
            .foregroundStyle(QRTheme.muted)
        }
        .padding(.vertical, 4)
        .accessibilityElement(children: .combine)
        .accessibilityLabel(
            "\(entry.ticker), decision \(entry.decision), radar \(entry.radarAction), \(entry.createdAt.formatted(date: .abbreviated, time: .omitted))"
        )
    }
}
