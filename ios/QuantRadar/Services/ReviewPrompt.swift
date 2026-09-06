import StoreKit
import SwiftUI
import UIKit

enum ReviewPrompt {
    static let launchKey = "qr.launch.count"
    static let waitKey = "qr.saw.wait"
    static let askedKey = "qr.review.asked"

    static var storage: UserDefaults = .standard

    static func recordLaunch() {
        #if DEBUG
        if ScreenshotLaunch.isEnabled { return }
        #endif
        let n = storage.integer(forKey: launchKey) + 1
        storage.set(n, forKey: launchKey)
    }

    static func recordVerdict(_ verdict: RadarVerdict) {
        #if DEBUG
        if ScreenshotLaunch.isEnabled { return }
        #endif
        switch verdict.actionCode {
        case "WAIT", "NO", "AVOID":
            storage.set(true, forKey: waitKey)
        default:
            break
        }
        maybeRequest()
    }

    static func shouldRequestReview() -> Bool {
        guard !storage.bool(forKey: askedKey) else { return false }
        guard storage.integer(forKey: launchKey) >= 2 else { return false }
        return storage.bool(forKey: waitKey)
    }

    static func maybeRequest() {
        guard shouldRequestReview() else { return }
        storage.set(true, forKey: askedKey)
        #if !os(macOS)
        if let scene = UIApplication.shared.connectedScenes
            .compactMap({ $0 as? UIWindowScene })
            .first(where: { $0.activationState == .foregroundActive })
            ?? UIApplication.shared.connectedScenes.compactMap({ $0 as? UIWindowScene }).first
        {
            SKStoreReviewController.requestReview(in: scene)
        }
        #endif
    }
}
