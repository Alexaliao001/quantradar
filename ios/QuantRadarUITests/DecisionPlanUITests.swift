import XCTest

/// User-owned text only: no market fixture, network success or forced purchase.
final class DecisionPlanUITests: XCTestCase {
    func testWriteReviewAndRelaunchWithoutUnlock() {
        continueAfterFailure = false
        let app = XCUIApplication()
        addUIInterruptionMonitor(withDescription: "First-use keyboard help") { alert in
            for title in ["Continue", "继续"] where alert.buttons[title].exists {
                alert.buttons[title].tap()
                return true
            }
            return false
        }
        app.launchArguments = ["-qr-ui-test-reset", "-hasSeenOnboarding", "YES"]
        app.launch()
        let newPlan = app.buttons["newDecisionPlan"]
        XCTAssertTrue(newPlan.waitForExistence(timeout: 15))
        attach(app, "01-plan-home")
        newPlan.tap()
        XCTAssertFalse(app.buttons["saveDecisionPlan"].isEnabled)
        type("EXAMPLE", into: "planTicker", app: app)
        type("Practice only: test whether I can wait for my written condition.", into: "planReason", app: app)
        type("Wait for the condition in my own research notes.", into: "planTrigger", app: app)
        type("Stop reviewing this idea if my original reason no longer holds.", into: "planInvalidation", app: app)
        app.buttons["saveDecisionPlan"].tap()
        let ticker = app.staticTexts["EXAMPLE"].firstMatch
        XCTAssertTrue(ticker.waitForExistence(timeout: 5))
        ticker.tap()
        XCTAssertTrue(app.staticTexts["Original record preserved"].waitForExistence(timeout: 5))
        attach(app, "02-original-plan")
        type("Practice review: I did not act. I kept the original condition instead of moving it.", into: "reviewLesson", app: app)
        let saveReview = app.buttons["saveDecisionReview"]
        reveal(saveReview, app: app)
        saveReview.tap()
        XCTAssertTrue(app.staticTexts["savedReviewOutcome"].waitForExistence(timeout: 5))
        attach(app, "03-process-review")

        app.terminate()
        app.launchArguments = ["-hasSeenOnboarding", "YES"]
        app.launch()
        XCTAssertTrue(app.buttons["newDecisionPlan"].waitForExistence(timeout: 15))
        app.segmentedControls.buttons["Reviewed"].tap()
        XCTAssertTrue(app.staticTexts["EXAMPLE"].firstMatch.waitForExistence(timeout: 5))
        app.staticTexts["EXAMPLE"].firstMatch.tap()
        XCTAssertTrue(app.staticTexts["Practice only: test whether I can wait for my written condition."].exists)
        let outcome = app.staticTexts["savedReviewOutcome"]
        reveal(outcome, app: app)
        XCTAssertEqual(outcome.label, "Did not act")
        XCTAssertFalse(app.buttons["saveDecisionReview"].exists)
        attach(app, "04-review-survives-relaunch")
    }

    private func type(_ value: String, into identifier: String, app: XCUIApplication) {
        let field = app.descendants(matching: .any).matching(identifier: identifier).firstMatch
        reveal(field, app: app)
        field.tap()
        field.typeText(value)
        let done = app.buttons["dismissPlanKeyboard"].firstMatch
        if done.waitForExistence(timeout: 2) { done.tap() }
    }

    private func reveal(_ element: XCUIElement, app: XCUIApplication) {
        for _ in 0..<8 {
            if element.exists && element.isHittable { return }
            app.collectionViews.firstMatch.swipeUp()
        }
        XCTAssertTrue(element.isHittable)
    }

    private func attach(_ app: XCUIApplication, _ name: String) {
        let image = XCTAttachment(screenshot: app.screenshot())
        image.name = name
        image.lifetime = .keepAlways
        add(image)
    }
}
