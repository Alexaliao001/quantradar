import SwiftUI

struct WatchlistView: View {
    @EnvironmentObject private var watchlist: WatchlistStore
    @EnvironmentObject private var radar: RadarService
    @EnvironmentObject private var purchases: PurchaseStore
    @EnvironmentObject private var journal: DecisionJournal
    @State private var showPaywall = false
    @State private var showComposer = false
    @State private var journalFilter = "Open"

    private var visibleEntries: [DecisionEntry] {
        journal.entries.filter { journalFilter == "All" || (journalFilter == "Reviewed" ? $0.review != nil : $0.review == nil) }
    }

    var body: some View {
        NavigationStack {
            List {
                Section {
                    VStack(alignment: .leading, spacing: 12) {
                        Text("Before the trade.").font(.title.bold())
                        Text("Write your conditions now. Review your process later.")
                            .font(.subheadline).foregroundStyle(QRTheme.muted)
                        Button { showComposer = true } label: {
                            Label("Write a decision", systemImage: "square.and.pencil")
                                .font(.headline).frame(maxWidth: .infinity).padding(.vertical, 5)
                        }
                        .buttonStyle(.borderedProminent).tint(QRTheme.radar).foregroundStyle(.black)
                        .accessibilityIdentifier("newDecisionPlan")
                        Text("\(journal.dueCount()) due for review · Private on this device · No purchase needed")
                            .font(.caption).foregroundStyle(QRTheme.muted)
                    }
                    .padding(.vertical, 8)
                }
                Section {
                    Picker("Journal filter", selection: $journalFilter) {
                        ForEach(["Open", "Reviewed", "All"], id: \.self) { Text($0).tag($0) }
                    }
                    .pickerStyle(.segmented)
                    if journal.entries.isEmpty {
                        VStack(alignment: .leading, spacing: 6) {
                            Text("No decisions logged yet")
                                .font(.headline)
                            Text("Name your reason, the condition you will wait for, and what would change your mind. The original stays beside your later review.")
                                .font(.caption)
                                .foregroundStyle(QRTheme.muted)
                        }
                        .padding(.vertical, 6)
                    } else {
                        if visibleEntries.isEmpty { Text("No \(journalFilter.lowercased()) decisions yet.").foregroundStyle(QRTheme.muted) }
                        ForEach(visibleEntries) { entry in
                            NavigationLink { DecisionDetailView(entryID: entry.id) } label: { decisionRow(entry) }
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
            .sheet(isPresented: $showComposer) {
                NavigationStack { DecisionPlanComposer() }.tint(QRTheme.radar)
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
                Text(entry.review == nil ? (entry.plan == nil ? "Quick log" : "Written plan") : "Reviewed")
                Text("·")
                Text(entry.createdAt.formatted(date: .abbreviated, time: .omitted))
            }
            .font(.caption)
            .foregroundStyle(QRTheme.muted)
            if let plan = entry.plan, entry.review == nil {
                Text("Review \(plan.reviewOn.formatted(date: .abbreviated, time: .omitted))")
                    .font(.caption).foregroundStyle(QRTheme.radar)
            }
        }
        .padding(.vertical, 4)
        .accessibilityElement(children: .combine)
        .accessibilityLabel(
            "\(entry.ticker), decision \(entry.decision), radar \(entry.radarAction), \(entry.createdAt.formatted(date: .abbreviated, time: .omitted))"
        )
    }
}
