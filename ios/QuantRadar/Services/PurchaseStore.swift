import Foundation
import StoreKit

@MainActor
final class PurchaseStore: ObservableObject {
    @Published private(set) var isUnlocked = false
    @Published private(set) var isLivePlus = false
    @Published private(set) var unlockProduct: Product?
    @Published private(set) var liveMonthlyProduct: Product?
    @Published private(set) var liveYearlyProduct: Product?
    @Published var lastError: String?
    @Published private(set) var isBusy = false

    private static let debugUnlockKey = "qr.debug.force_unlocked"
    private static let debugLiveKey = "qr.debug.force_liveplus"

    /// DEBUG / Simulator convenience — never ships as true entitlements.
    /// Default via init (not `Self.` in property init) for Xcode 15 / Swift 5.10.
    @Published var debugForceUnlocked = false {
        didSet { UserDefaults.standard.set(debugForceUnlocked, forKey: PurchaseStore.debugUnlockKey) }
    }

    @Published var debugForceLivePlus = false {
        didSet { UserDefaults.standard.set(debugForceLivePlus, forKey: PurchaseStore.debugLiveKey) }
    }

    private var updatesTask: Task<Void, Never>?

    var effectiveUnlocked: Bool {
        #if DEBUG
        return isUnlocked || debugForceUnlocked
        #else
        return isUnlocked
        #endif
    }

    var effectiveLivePlus: Bool {
        #if DEBUG
        return isLivePlus || debugForceLivePlus
        #else
        return isLivePlus
        #endif
    }

    var watchlistLimit: Int {
        AppAccess.watchlistLimit(livePlus: effectiveLivePlus && effectiveUnlocked)
    }

    init() {
        debugForceUnlocked = UserDefaults.standard.bool(forKey: PurchaseStore.debugUnlockKey)
        debugForceLivePlus = UserDefaults.standard.bool(forKey: PurchaseStore.debugLiveKey)
        updatesTask = Task { await listenForTransactions() }
        Task { await bootstrap() }
    }

    deinit {
        updatesTask?.cancel()
    }

    func bootstrap() async {
        await refreshEntitlements()
        await loadProducts()
    }

    func loadProducts() async {
        do {
            let ids: Set<String> = [
                AppAccess.unlockProductID,
                AppAccess.liveMonthlyProductID,
                AppAccess.liveYearlyProductID,
            ]
            let products = try await Product.products(for: ids)
            unlockProduct = products.first { $0.id == AppAccess.unlockProductID }
            liveMonthlyProduct = products.first { $0.id == AppAccess.liveMonthlyProductID }
            liveYearlyProduct = products.first { $0.id == AppAccess.liveYearlyProductID }
        } catch {
            lastError = error.localizedDescription
        }
    }

    func refreshEntitlements() async {
        var unlocked = false
        var live = false
        for await result in Transaction.currentEntitlements {
            guard case .verified(let tx) = result else { continue }
            switch tx.productID {
            case AppAccess.unlockProductID:
                unlocked = true
            case AppAccess.liveMonthlyProductID, AppAccess.liveYearlyProductID:
                if tx.revocationDate == nil {
                    live = true
                }
            default:
                break
            }
        }
        isUnlocked = unlocked
        isLivePlus = live
    }

    @discardableResult
    func purchaseUnlock() async -> Bool {
        guard let product = unlockProduct else {
            await loadProducts()
            guard let product = unlockProduct else {
                lastError = "Unlock product unavailable. Try again later."
                return false
            }
            return await purchase(product)
        }
        return await purchase(product)
    }

    @discardableResult
    func purchaseLivePlus(yearly: Bool) async -> Bool {
        guard effectiveUnlocked else {
            lastError = "Unlock the core radar first ($9.99)."
            return false
        }
        let product = yearly ? liveYearlyProduct : liveMonthlyProduct
        guard let product else {
            await loadProducts()
            let again = yearly ? liveYearlyProduct : liveMonthlyProduct
            guard let again else {
                lastError = "Live+ product unavailable."
                return false
            }
            return await purchase(again)
        }
        return await purchase(product)
    }

    func restore() async {
        isBusy = true
        defer { isBusy = false }
        do {
            try await AppStore.sync()
            await refreshEntitlements()
            lastError = nil
        } catch {
            lastError = error.localizedDescription
        }
    }

    private func purchase(_ product: Product) async -> Bool {
        isBusy = true
        defer { isBusy = false }
        do {
            let result = try await product.purchase()
            switch result {
            case .success(let verification):
                guard case .verified(let tx) = verification else {
                    lastError = "Purchase could not be verified."
                    return false
                }
                await tx.finish()
                await refreshEntitlements()
                lastError = nil
                return true
            case .userCancelled:
                return false
            case .pending:
                lastError = "Purchase pending approval."
                return false
            @unknown default:
                return false
            }
        } catch {
            lastError = error.localizedDescription
            return false
        }
    }

    private func listenForTransactions() async {
        for await result in Transaction.updates {
            guard case .verified(let tx) = result else { continue }
            await tx.finish()
            await refreshEntitlements()
        }
    }
}
