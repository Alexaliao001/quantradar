import SwiftUI
import WidgetKit

struct SPYEntry: TimelineEntry {
    let date: Date
    let ticker: String
    let score: String
    let action: String
}

struct SPYProvider: TimelineProvider {
    func placeholder(in context: Context) -> SPYEntry {
        SPYEntry(date: Date(), ticker: "SPY", score: "—", action: "WAIT")
    }

    func getSnapshot(in context: Context, completion: @escaping (SPYEntry) -> Void) {
        completion(SPYEntry(date: Date(), ticker: "SPY", score: "—", action: "WAIT"))
    }

    func getTimeline(in context: Context, completion: @escaping (Timeline<SPYEntry>) -> Void) {
        Task {
            let entry: SPYEntry
            if let bars = try? await FreeMarketDataClient.dailyBars(symbol: "SPY", rangeHintDays: 90) {
                let v = FreeMechanicalScorer.score(
                    symbol: "SPY",
                    company: "SPDR S&P 500",
                    bars: bars.bars,
                    spyBars: bars.bars,
                    source: bars.source
                )
                entry = SPYEntry(
                    date: Date(),
                    ticker: "SPY",
                    score: v.scoreText,
                    action: v.primary?.action ?? "WAIT"
                )
            } else {
                entry = SPYEntry(date: Date(), ticker: "SPY", score: "—", action: "WAIT")
            }
            let next = Date().addingTimeInterval(30 * 60)
            completion(Timeline(entries: [entry], policy: .after(next)))
        }
    }
}

struct QuantRadarWidgetView: View {
    let entry: SPYEntry

    var body: some View {
        VStack(alignment: .leading, spacing: 6) {
            Text("QuantRadar")
                .font(.caption2.weight(.semibold))
                .foregroundStyle(.secondary)
            Text(entry.ticker)
                .font(.title2.bold())
            Text(entry.score)
                .font(.system(size: 28, weight: .bold, design: .rounded))
            Text(entry.action)
                .font(.caption.weight(.bold))
            Text("Educational only")
                .font(.caption2)
                .foregroundStyle(.secondary)
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .leading)
        .containerBackground(for: .widget) {
            Color(red: 0.043, green: 0.059, blue: 0.055)
        }
    }
}

@main
struct QuantRadarWidget: Widget {
    var body: some WidgetConfiguration {
        StaticConfiguration(kind: "QuantRadarSPY", provider: SPYProvider()) { entry in
            QuantRadarWidgetView(entry: entry)
        }
        .configurationDisplayName("SPY posture")
        .description("Today’s mechanical SPY radar on your Home Screen.")
        .supportedFamilies([.systemSmall, .systemMedium])
    }
}
