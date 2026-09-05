import SwiftUI

struct PostureStripView: View {
    let history: [String]

    var body: some View {
        VStack(alignment: .leading, spacing: 6) {
            Text("90-day posture")
                .font(.caption2.weight(.semibold))
                .foregroundStyle(QRTheme.muted)
            GeometryReader { geo in
                let n = max(history.count, 1)
                let w = max(1.0, geo.size.width / CGFloat(n))
                HStack(spacing: 0) {
                    ForEach(Array(history.enumerated()), id: \.offset) { _, action in
                        Rectangle()
                            .fill(color(action))
                            .frame(width: w, height: 14)
                    }
                }
                .clipShape(RoundedRectangle(cornerRadius: 3, style: .continuous))
            }
            .frame(height: 14)
            .accessibilityHidden(true)
        }
        .accessibilityElement(children: .ignore)
        .accessibilityLabel(accessibilitySummary)
    }

    private func color(_ action: String) -> Color {
        switch action.uppercased() {
        case "SETUP": return QRTheme.radar
        case "NO", "AVOID": return QRTheme.danger
        default: return QRTheme.warn.opacity(0.85)
        }
    }

    private var accessibilitySummary: String {
        let setup = history.filter { $0.uppercased() == "SETUP" }.count
        let wait = history.filter { $0.uppercased() == "WAIT" }.count
        let no = history.count - setup - wait
        return "Posture history: \(setup) setup, \(wait) wait, \(max(0, no)) avoid sessions"
    }
}

struct DepthFactsView: View {
    let depth: RadarVerdict.Depth

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            if depth.earningsForcedWait == true, let d = depth.earningsDays {
                Text(earningsLine(d))
                    .font(.footnote.weight(.medium))
                    .foregroundStyle(QRTheme.warn)
            }
            if let ago = depth.lastSetupAgoDays, let fwd = depth.lastSetupForwardPct, ago > 0 {
                Text(String(format: "Last SETUP %d sessions ago · %+.1f%% since. Educational — not a promise.", ago, fwd))
                    .font(.footnote)
                    .foregroundStyle(QRTheme.muted)
            }
            if let n = depth.setupCount, n > 0, let m5 = depth.medianForward5dPct {
                let m20 = depth.medianForward20dPct
                let extra = m20.map { String(format: " · 20-day median %+.1f%%", $0) } ?? ""
                Text(String(format: "When SETUP printed here: 5-day median %+.1f%% (n=%d)%@.", m5, n, extra))
                    .font(.caption)
                    .foregroundStyle(QRTheme.muted)
            }
        }
    }

    private func earningsLine(_ d: Int) -> String {
        if d == 0 { return "Earnings today — radar stays on WAIT." }
        if d > 0 { return "Earnings in \(d) days — radar stays on WAIT." }
        return "Earnings \(-d) days ago — radar stays on WAIT."
    }
}
