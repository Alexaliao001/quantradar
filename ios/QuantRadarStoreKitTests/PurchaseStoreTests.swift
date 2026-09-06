import XCTest
import StoreKit
import StoreKitTest
@testable import QuantRadar

/// Apple's local StoreKit test environment, never a live charge or debug unlock.
@MainActor
final class PurchaseStoreTests: XCTestCase {
    private func session() throws -> SKTestSession {
        let url = try XCTUnwrap(Bundle(for: Self.self).url(forResource: "Products", withExtension: "storekit"))
        let test = try SKTestSession(contentsOf: url)
        test.resetToDefaultState()
        test.clearTransactions()
        test.disableDialogs = true
        guard test.disableDialogs else {
            throw NSError(domain: "StoreKitTestConfiguration", code: 1,
                          userInfo: [NSLocalizedDescriptionKey: "Local StoreKit configuration could not be activated."])
        }
        return test
    }

    private func store() async -> PurchaseStore {
        let store = PurchaseStore()
        store.debugForceUnlocked = false
        store.debugForceLivePlus = false
        await store.bootstrap()
        return store
    }

    private func waitForEntitlement(_ store: PurchaseStore, unlocked: Bool) async -> Bool {
        for _ in 0..<30 {
            if store.isUnlocked == unlocked { return true }
            try? await Task.sleep(nanoseconds: 100_000_000)
        }
        return false
    }

    func testPurchaseRestoreAndRefundThroughStoreKit() async throws {
        let test = try session()
        defer { test.clearTransactions() }
        let first = await store()
        XCTAssertFalse(first.effectiveUnlocked)
        XCTAssertEqual(first.unlockProduct?.type, .nonConsumable)
        let bought = await first.purchaseUnlock()
        XCTAssertTrue(bought)
        XCTAssertTrue(first.isUnlocked)
        XCTAssertTrue(first.effectiveUnlocked)

        let restored = await store()
        await restored.restore()
        XCTAssertTrue(restored.isUnlocked)
        XCTAssertNil(restored.lastError)
        let transaction = try XCTUnwrap(test.allTransactions().first { $0.productIdentifier == AppAccess.unlockProductID })
        try test.refundTransaction(identifier: transaction.identifier)
        let revoked = await waitForEntitlement(restored, unlocked: false)
        XCTAssertTrue(revoked)
        XCTAssertFalse(restored.effectiveUnlocked)
        await restored.restore()
        XCTAssertFalse(restored.isUnlocked)
    }

    func testCancelledPurchaseDoesNotUnlock() async throws {
        let test = try session()
        defer { test.clearTransactions() }
        let purchases = await store()
        _ = try XCTUnwrap(purchases.unlockProduct)
        try await test.setSimulatedError(.generic(.userCancelled), forAPI: .purchase)
        let bought = await purchases.purchaseUnlock()
        XCTAssertFalse(bought)
        XCTAssertFalse(purchases.effectiveUnlocked)
        XCTAssertFalse(purchases.isBusy)
    }

    func testPendingPurchaseOnlyUnlocksAfterApproval() async throws {
        let test = try session()
        defer { test.clearTransactions() }
        test.askToBuyEnabled = true
        let purchases = await store()
        let bought = await purchases.purchaseUnlock()
        XCTAssertFalse(bought)
        XCTAssertFalse(purchases.effectiveUnlocked)
        XCTAssertEqual(purchases.lastError, "Purchase pending approval.")
        let transaction = try XCTUnwrap(test.allTransactions().first { $0.productIdentifier == AppAccess.unlockProductID })
        try test.approveAskToBuyTransaction(identifier: transaction.identifier)
        let granted = await waitForEntitlement(purchases, unlocked: true)
        XCTAssertTrue(granted)
    }
}
