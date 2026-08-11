import Foundation

struct RadarVerdict: Codable, Identifiable, Hashable {
    var id: String { ticker }

    let ok: Bool
    let ticker: String
    let companyName: String?
    let sector: String?
    let primaryScore: PrimaryScore?
    let primary: PrimaryAction?
    let summary: String?
    let engagement: Engagement?
    let dataQuality: DataQuality?
    let market: MarketSnapshot?
    let meta: Meta?
    let gate: Gate?
    let warnings: [String]?

    enum CodingKeys: String, CodingKey {
        case ok, ticker, sector, summary, engagement, market, meta, gate, warnings
        case companyName = "company_name"
        case primaryScore = "primary_score"
        case primary
        case dataQuality = "data_quality"
    }

    struct PrimaryScore: Codable, Hashable {
        let value: Double?
        let scale: Double?
        let label: String?
        let withheld: Bool?
        let note: String?
    }

    struct PrimaryAction: Codable, Hashable {
        let action: String?
        let label: String?
        let reason: String?
    }

    struct Engagement: Codable, Hashable {
        let avoidedLine: String?
        let freezeLabel: String?
        let postureNote: String?

        enum CodingKeys: String, CodingKey {
            case avoidedLine = "avoided_line"
            case freezeLabel = "freeze_label"
            case postureNote = "posture_note"
        }
    }

    struct DataQuality: Codable, Hashable {
        let usable: Bool?
        let reliability: String?
        let optionsActionable: Bool?

        enum CodingKeys: String, CodingKey {
            case usable, reliability
            case optionsActionable = "options_actionable"
        }
    }

    struct MarketSnapshot: Codable, Hashable {
        let marketState: String?
        let spyChangePct: Double?
        let sectorEtf: String?
        let sectorChangePct: Double?
        let vixCurrent: Double?
        let vixTrend: String?

        enum CodingKeys: String, CodingKey {
            case marketState = "market_state"
            case spyChangePct = "spy_change_pct"
            case sectorEtf = "sector_etf"
            case sectorChangePct = "sector_change_pct"
            case vixCurrent = "vix_current"
            case vixTrend = "vix_trend"
        }
    }

    struct Meta: Codable, Hashable {
        let mode: String?
        let fetchTime: String?
        let disclaimer: String?
        let dataPath: String?

        enum CodingKeys: String, CodingKey {
            case mode, disclaimer
            case fetchTime = "fetch_time"
            case dataPath = "data_path"
        }
    }

    struct Gate: Codable, Hashable {
        let market: String?
        let sector: String?
        let stock: String?
    }

    var actionCode: String {
        (primary?.action ?? "WAIT").uppercased()
    }

    var scoreText: String {
        if primaryScore?.withheld == true { return "—" }
        guard let v = primaryScore?.value else { return "—" }
        return String(format: "%.0f", v)
    }
}
