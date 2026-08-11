import Foundation

/// Install = purchase on the App Store ($9.99 paid app).
/// Everyone running this binary is treated as a paid owner — no freemium quota.
enum AppAccess {
    static let watchlistLimit = 20
    static let appStorePriceNote = "$9.99 paid · zero-COGS free-data radar (not web Massive)"
}
