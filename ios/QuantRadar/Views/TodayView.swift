import SwiftUI

struct TodayView: View {
    @EnvironmentObject private var radar: RadarService
    @EnvironmentObject private var purchases: PurchaseStore
    @State private var showPaywall = false
    @State private var briefingAsked = false

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: 20) {
                    VStack(alignment: .leading, spacing: 6) {
                        Text("Market posture")
                            .font(.caption.weight(.semibold))
                            .foregroundStyle(QRTheme.radar)
                        Text("Should you act today?")
                            .font(.title.bold())
                            .foregroundStyle(QRTheme.text)
                        Text(AppAccess.differentiationLine)
                            .font(.footnote.weight(.medium))
                            .foregroundStyle(QRTheme.text)
                        Text(DisciplineLedger.summaryLine)
                            .font(.caption)
                            .foregroundStyle(QRTheme.muted)
                    }

                    if let v = radar.todayVerdict {
                        VerdictCardView(verdict: v)
                        if radar.isWarmingUp || radar.isLoading {
                            HStack(spacing: 8) {
                                ProgressView().tint(QRTheme.radar).controlSize(.small)
                                Text("Refreshing live posture…")
                                    .font(.caption)
                                    .foregroundStyle(QRTheme.muted)
                            }
                        }
                    } else if radar.isLoading || radar.isWarmingUp {
                        ProgressView().tint(QRTheme.radar)
                    } else {
                        Text(radar.errorMessage ?? "Market posture unavailable.")
                            .foregroundStyle(QRTheme.warn)
                    }

                    if purchases.effectiveUnlocked, !radar.sectorHeat.isEmpty {
                        VStack(alignment: .leading, spacing: 8) {
                            Text("Sector posture")
                                .font(.caption.weight(.semibold))
                                .foregroundStyle(QRTheme.muted)
                            LazyVGrid(columns: [GridItem(.adaptive(minimum: 96), spacing: 8)], spacing: 8) {
                                ForEach(radar.sectorHeat, id: \.etf) { row in
                                    VStack(alignment: .leading, spacing: 2) {
                                        Text(row.label)
                                            .font(.caption2)
                                            .foregroundStyle(QRTheme.muted)
                                        Text(row.action)
                                            .font(.caption.weight(.bold))
                                            .foregroundStyle(QRTheme.text)
                                    }
                                    .padding(8)
                                    .frame(maxWidth: .infinity, alignment: .leading)
                                    .background(QRTheme.panel)
                                    .clipShape(RoundedRectangle(cornerRadius: 10, style: .continuous))
                                }
                            }
                        }
                    }

                    if purchases.effectiveUnlocked {
                        Label("Unlocked · full radar", systemImage: "checkmark.seal.fill")
                            .font(.subheadline.weight(.medium))
                            .foregroundStyle(QRTheme.radar)
                            .padding(12)
                            .frame(maxWidth: .infinity, alignment: .leading)
                            .background(QRTheme.panel)
                            .clipShape(RoundedRectangle(cornerRadius: 12, style: .continuous))
                    } else {
                        Button { showPaywall = true } label: {
                            Label("Unlock any ticker · \(unlockPrice)", systemImage: "lock.open")
                                .font(.subheadline.weight(.medium))
                                .frame(maxWidth: .infinity, alignment: .leading)
                                .padding(12)
                                .background(QRTheme.panel)
                                .foregroundStyle(QRTheme.radar)
                                .clipShape(RoundedRectangle(cornerRadius: 12, style: .continuous))
                        }
                        Text(AppAccess.previewLine)
                            .font(.caption2)
                            .foregroundStyle(QRTheme.muted)
                    }

                    Text(radar.todayVerdict?.meta?.disclaimer ?? "Educational radar only — not investment advice.")
                        .font(.caption2)
                        .foregroundStyle(QRTheme.muted)
                }
                .padding(20)
                .frame(maxWidth: 760)
                .frame(maxWidth: .infinity)
            }
            .background(QRTheme.bg.ignoresSafeArea())
            .navigationTitle("Today")
            .toolbar {
                ToolbarItem(placement: .topBarTrailing) {
                    Button {
                        Task {
                            await radar.refreshToday(bypassCache: true)
                            if purchases.effectiveUnlocked {
                                await radar.refreshSectors()
                            }
                        }
                    } label: {
                        Image(systemName: "arrow.clockwise")
                    }
                    .disabled(radar.isLoading || radar.isWarmingUp)
                }
            }
            .task {
                await radar.warmUpToday()
                if let v = radar.todayVerdict, !v.isWithheld {
                    DisciplineLedger.record(action: v.actionCode, ticker: v.ticker, close: nil)
                    ReviewPrompt.recordVerdict(v)
                }
                if purchases.effectiveUnlocked {
                    await radar.refreshSectors()
                }
                if !briefingAsked {
                    briefingAsked = true
                    #if DEBUG
                    if ScreenshotLaunch.isEnabled { return }
                    #endif
                    await DailyBriefing.requestAndSchedule()
                }
            }
            .onChange(of: radar.todayVerdict?.ticker) { _, _ in
                if let v = radar.todayVerdict { ReviewPrompt.recordVerdict(v) }
            }
            .sheet(isPresented: $showPaywall) {
                PaywallView()
                    .environmentObject(purchases)
            }
        }
    }

    private var unlockPrice: String {
        purchases.unlockProduct?.displayPrice ?? "$9.99"
    }
}
