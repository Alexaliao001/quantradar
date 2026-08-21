import Foundation

/// Memory + disk cache for free OHLCV bars.
/// SPY defaults to 30 min TTL; other symbols 15 min.
actor BarsCache {
    static let shared = BarsCache()

    struct Entry: Codable, Sendable {
        let bars: [FreeBar]
        let sourceRaw: String
        let fetchedAt: Date

        var source: FreeDataSourceID? { FreeDataSourceID(rawValue: sourceRaw) }

        func asResult() -> FreeBarsResult? {
            guard let source else { return nil }
            return FreeBarsResult(bars: bars, source: source)
        }
    }

    private var memory: [String: Entry] = [:]
    private let diskDir: URL
    private let encoder = JSONEncoder()
    private let decoder = JSONDecoder()

    init(diskDir: URL? = nil) {
        if let diskDir {
            self.diskDir = diskDir
        } else {
            let base = FileManager.default.urls(for: .cachesDirectory, in: .userDomainMask).first
                ?? FileManager.default.temporaryDirectory
            self.diskDir = base.appendingPathComponent("qr_bars_cache", isDirectory: true)
        }
        try? FileManager.default.createDirectory(at: self.diskDir, withIntermediateDirectories: true)
    }

    static func ttl(for symbol: String) -> TimeInterval {
        symbol == "SPY" ? 30 * 60 : 15 * 60
    }

    func get(_ symbol: String, maxAge: TimeInterval? = nil) -> FreeBarsResult? {
        let key = FreeMarketDataClient.normalize(symbol)
        guard !key.isEmpty else { return nil }
        let age = maxAge ?? Self.ttl(for: key)
        let now = Date()

        if let mem = memory[key], now.timeIntervalSince(mem.fetchedAt) <= age {
            return mem.asResult()
        }

        let file = diskURL(for: key)
        guard
            let data = try? Data(contentsOf: file),
            let entry = try? decoder.decode(Entry.self, from: data),
            now.timeIntervalSince(entry.fetchedAt) <= age,
            let result = entry.asResult()
        else { return nil }

        memory[key] = entry
        return result
    }

    func set(_ symbol: String, result: FreeBarsResult) {
        let key = FreeMarketDataClient.normalize(symbol)
        guard !key.isEmpty else { return }
        let entry = Entry(bars: result.bars, sourceRaw: result.source.rawValue, fetchedAt: Date())
        memory[key] = entry
        if let data = try? encoder.encode(entry) {
            try? data.write(to: diskURL(for: key), options: .atomic)
        }
    }

    func clear() {
        memory.removeAll()
        if let files = try? FileManager.default.contentsOfDirectory(at: diskDir, includingPropertiesForKeys: nil) {
            for f in files { try? FileManager.default.removeItem(at: f) }
        }
    }

    private func diskURL(for symbol: String) -> URL {
        let safe = symbol.replacingOccurrences(of: "/", with: "_")
        return diskDir.appendingPathComponent("\(safe).json")
    }
}
