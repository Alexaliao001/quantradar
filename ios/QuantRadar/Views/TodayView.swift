import SwiftUI

struct TodayView: View {
    @EnvironmentObject private var radar: RadarService

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
                        Text(AppAccess.appStorePriceNote)
                            .font(.footnote)
                            .foregroundStyle(QRTheme.muted)
                        Text("Free-data radar · cached SPY · $0 API cost")
                            .font(.caption2)
                            .foregroundStyle(QRTheme.radar)
                    }

                    if let v = radar.latest ?? radar.demo {
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
                        Text(radar.errorMessage ?? "Demo unavailable.")
                            .foregroundStyle(QRTheme.warn)
                    }

                    Label("Paid owner · full radar unlocked", systemImage: "checkmark.seal.fill")
                        .font(.subheadline.weight(.medium))
                        .foregroundStyle(QRTheme.radar)
                        .padding(12)
                        .frame(maxWidth: .infinity, alignment: .leading)
                        .background(QRTheme.panel)
                        .clipShape(RoundedRectangle(cornerRadius: 12, style: .continuous))

                    Text(radar.latest?.meta?.disclaimer ?? "Educational radar only — not investment advice.")
                        .font(.caption2)
                        .foregroundStyle(QRTheme.muted)
                }
                .padding(20)
            }
            .background(QRTheme.bg.ignoresSafeArea())
            .navigationTitle("Today")
            .toolbar {
                ToolbarItem(placement: .topBarTrailing) {
                    Button {
                        Task { _ = await radar.analyze(ticker: radar.latest?.ticker ?? "SPY", bypassCache: true) }
                    } label: {
                        Image(systemName: "arrow.clockwise")
                    }
                    .disabled(radar.isLoading || radar.isWarmingUp)
                }
            }
            .task { await radar.warmUpToday() }
        }
    }
}
