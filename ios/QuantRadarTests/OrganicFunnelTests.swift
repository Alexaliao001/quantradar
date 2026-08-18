import XCTest
@testable import QuantRadar

@MainActor
final class OrganicFunnelTests: XCTestCase {
    func testShareTextContainsTickerAndDisclaimer() {
        let verdict = RadarService.synthetic(for: "AAPL", reason: "test")
        XCTAssertTrue(verdict.shareText.contains("AAPL"))
        XCTAssertTrue(verdict.shareText.contains("QuantRadar"))
        XCTAssertTrue(verdict.shareText.contains("not investment advice"))
        XCTAssertFalse(verdict.shareText.lowercased().contains("massive"))
    }

    func testScorerNeverEmitsBUY() {
        let bars = Self.grind(start: 100, end: 118, count: 60, lastVolume: 2_000_000)
        let spy = Self.grind(start: 400, end: 410, count: 60, lastVolume: 1_000_000)
        let verdict = FreeMechanicalScorer.score(
            symbol: "AAPL",
            company: "Apple",
            bars: bars,
            spyBars: spy,
            source: .yahooQuery1
        )
        XCTAssertTrue(verdict.ok)
        let action = verdict.primary?.action ?? ""
        XCTAssertTrue(["SETUP", "WAIT", "NO"].contains(action), "unexpected \(action)")
        XCTAssertNotEqual(action, "BUY")
        XCTAssertFalse((verdict.summary ?? "").lowercased().contains("massive"))
        XCTAssertFalse((verdict.primaryScore?.note ?? "").lowercased().contains("massive"))
        XCTAssertEqual(verdict.meta?.disclaimer, "Educational radar only — not investment advice.")
    }

    func testScorerSetupOnSupportiveTrend() {
        let bars = Self.grind(start: 100, end: 112, count: 80, lastVolume: 2_400_000)
        let spy = Self.grind(start: 400, end: 408, count: 80, lastVolume: 1_000_000)
        let verdict = FreeMechanicalScorer.score(
            symbol: "MSFT",
            company: "Microsoft",
            bars: bars,
            spyBars: spy,
            source: .yahooQuery1
        )
        XCTAssertTrue(["SETUP", "WAIT"].contains(verdict.primary?.action ?? ""))
        if verdict.primary?.action == "SETUP" {
            XCTAssertEqual(verdict.primary?.label, "Setup zone")
        }
    }

    func testBundledSampleStillWAIT() throws {
        let path = URL(fileURLWithPath: #filePath)
            .deletingLastPathComponent()
            .deletingLastPathComponent()
            .appendingPathComponent("QuantRadar/Resources/SampleVerdict.json")
        let data = try Data(contentsOf: path)
        let verdict = try JSONDecoder().decode(RadarVerdict.self, from: data)
        XCTAssertEqual(verdict.ticker, "INTC")
        XCTAssertEqual(verdict.primary?.action, "WAIT")
    }

    private static func grind(start: Double, end: Double, count: Int, lastVolume: Double) -> [FreeBar] {
        (0..<count).map { i in
            let t = Double(i) / Double(max(count - 1, 1))
            let close = start + (end - start) * t
            let vol = i == count - 1 ? lastVolume : 1_000_000
            return FreeBar(
                date: Date(timeIntervalSince1970: 1_700_000_000 + Double(i) * 86_400),
                close: close,
                volume: vol
            )
        }
    }
}
