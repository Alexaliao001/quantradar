import SwiftUI

struct VerdictCardView: View {
    let verdict: RadarVerdict
    var showsShare: Bool = true
    @Environment(\.accessibilityReduceMotion) private var reduceMotion
    @State private var revealStep = 3

    var body: some View {
        VStack(alignment: .leading, spacing: 16) {
            HStack(alignment: .top) {
                VStack(alignment: .leading, spacing: 4) {
                    Text(verdict.ticker)
                        .font(.system(size: 28, weight: .bold, design: .rounded))
                        .foregroundStyle(QRTheme.text)
                    if let name = verdict.companyName {
                        Text(name)
                            .font(.subheadline)
                            .foregroundStyle(QRTheme.muted)
                    }
                }
                Spacer()
                scoreBadge
            }

            actionPill

            if let reason = verdict.primary?.reason {
                Text(reason)
                    .font(.body)
                    .foregroundStyle(QRTheme.text)
            }

            if let summary = verdict.summary {
                Text(summary)
                    .font(.subheadline)
                    .foregroundStyle(QRTheme.muted)
            }

            if let avoided = verdict.engagement?.avoidedLine {
                Label(avoided, systemImage: "shield.lefthalf.filled")
                    .font(.footnote)
                    .foregroundStyle(QRTheme.radar)
            }

            gatesRow
            marketRow

            if let history = verdict.depth?.history, !history.isEmpty {
                PostureStripView(history: history)
            }
            if let depth = verdict.depth {
                DepthFactsView(depth: depth)
            }

            if showsShare {
                ShareLink(item: verdict.shareText) {
                    Label("Share", systemImage: "square.and.arrow.up")
                        .font(.subheadline.weight(.medium))
                        .foregroundStyle(QRTheme.radar)
                }
            }
        }
        .padding(18)
        .background(
            RoundedRectangle(cornerRadius: 20, style: .continuous)
                .fill(QRTheme.panel)
                .overlay(
                    RoundedRectangle(cornerRadius: 20, style: .continuous)
                        .stroke(QRTheme.radar.opacity(0.25), lineWidth: 1)
                )
        )
        .task(id: "\(verdict.ticker)-\(verdict.scoreText)-\(verdict.actionCode)") {
            guard !reduceMotion else {
                revealStep = 3
                return
            }
            revealStep = 0
            for step in 1...3 {
                try? await Task.sleep(nanoseconds: 140_000_000)
                withAnimation(.easeOut(duration: 0.2)) {
                    revealStep = step
                }
            }
        }
    }

    private var scoreBadge: some View {
        VStack(spacing: 2) {
            Text(verdict.scoreText)
                .font(.system(size: 32, weight: .bold, design: .rounded))
                .foregroundStyle(QRTheme.radar)
            Text("score")
                .font(.caption2)
                .foregroundStyle(QRTheme.muted)
        }
        .frame(width: 72, height: 72)
        .background(QRTheme.radarDim)
        .clipShape(RoundedRectangle(cornerRadius: 16, style: .continuous))
        .accessibilityElement(children: .ignore)
        .accessibilityLabel("Mechanical posture score \(verdict.scoreText) out of 100")
    }

    private var actionPill: some View {
        Text((verdict.primary?.label ?? verdict.actionCode).uppercased())
            .font(.caption.weight(.bold))
            .tracking(1.2)
            .padding(.horizontal, 12)
            .padding(.vertical, 6)
            .background(actionColor.opacity(0.2))
            .foregroundStyle(actionColor)
            .clipShape(Capsule())
            .accessibilityLabel("Radar action \(verdict.primary?.label ?? verdict.actionCode)")
    }

    private var actionColor: Color {
        switch verdict.actionCode {
        case "SETUP", "BUY", "LONG", "YES": return QRTheme.radar
        case "NO", "AVOID": return QRTheme.danger
        default: return QRTheme.warn
        }
    }

    @ViewBuilder
    private var gatesRow: some View {
        if let g = verdict.gate {
            HStack(spacing: 8) {
                gateChip("Market", g.market, step: 1)
                gateChip("Sector", g.sector, step: 2)
                gateChip("Stock", g.stock, step: 3)
            }
            .accessibilityElement(children: .combine)
            .accessibilityLabel(
                "Radar lock. Market \(g.market ?? "unknown"), sector \(g.sector ?? "unknown"), stock \(g.stock ?? "unknown")"
            )
        }
    }

    private func gateChip(_ title: String, _ value: String?, step: Int) -> some View {
        VStack(spacing: 2) {
            Text(title)
                .font(.caption2)
                .foregroundStyle(QRTheme.muted)
            Text(value ?? "—")
                .font(.caption.weight(.semibold))
                .foregroundStyle(QRTheme.text)
        }
        .frame(maxWidth: .infinity)
        .padding(.vertical, 8)
        .background(QRTheme.bg.opacity(0.6))
        .clipShape(RoundedRectangle(cornerRadius: 10, style: .continuous))
        .overlay(alignment: .top) {
            Capsule()
                .fill(revealStep >= step ? QRTheme.radar : QRTheme.muted.opacity(0.25))
                .frame(width: revealStep >= step ? 28 : 8, height: 2)
                .padding(.top, 3)
        }
        .opacity(revealStep >= step ? 1 : 0.42)
        .scaleEffect(revealStep >= step ? 1 : 0.97)
    }

    @ViewBuilder
    private var marketRow: some View {
        if let m = verdict.market {
            HStack {
                if let spy = m.spyChangePct {
                    Text(String(format: "SPY %+.2f%%", spy))
                }
                if let vix = m.vixCurrent {
                    Text(String(format: "VIX %.1f", vix))
                }
                if let trend = m.vixTrend {
                    Text("VIX \(trend)")
                }
            }
            .font(.caption)
            .foregroundStyle(QRTheme.muted)
        }
    }
}
