import XCTest

/// Full user path for the first-launch BABA crash report:
/// onboarding dismiss -> chase check -> scan BABA -> verdict renders ->
/// log decision -> add to watch -> tab churn. Real network, fail-closed OK.
final class BABAFlowUITests: XCTestCase {
    private var app: XCUIApplication!

    override func setUp() {
        super.setUp()
        continueAfterFailure = false
        app = XCUIApplication()
        app.launchArguments = ["-qr-force-unlock"]
        app.launch()
    }

    override func tearDown() {
        app = nil
        super.tearDown()
    }

    private func dismissOnboardingIfNeeded() {
        let open = app.buttons["Open radar"]
        if open.waitForExistence(timeout: 5) {
            open.tap()
        }
    }

    private func goToScanTab() {
        let scan = app.tabBars.buttons["Scan"]
        XCTAssertTrue(scan.waitForExistence(timeout: 10), "Scan tab missing")
        scan.tap()
    }

    func testScanBABAEndToEnd() throws {
        dismissOnboardingIfNeeded()
        goToScanTab()

        let field = app.textFields["tickerField"]
        XCTAssertTrue(field.waitForExistence(timeout: 10), "Scan tab should show ticker field")
        field.tap()
        field.typeText("BABA")

        let scanButton = app.buttons["runScanButton"]
        XCTAssertTrue(scanButton.waitForExistence(timeout: 5))
        scanButton.tap()

        // Wait through the scan for either a verdict card or the fail-closed copy.
        let verdictTicker = app.staticTexts["BABA"]
        let failClosed = app.staticTexts.matching(
            NSPredicate(format: "label CONTAINS 'fail closed' OR label CONTAINS 'unavailable'")
        ).firstMatch
        let deadline = Date().addingTimeInterval(90)
        while Date() < deadline {
            if verdictTicker.exists || failClosed.exists { break }
            RunLoop.current.run(until: Date().addingTimeInterval(1))
        }
        XCTAssertTrue(
            verdictTicker.exists || failClosed.exists,
            "BABA scan must render a verdict or fail closed — neither happened (possible crash/hang)"
        )

        // If the verdict rendered, the score badge and gates row must be there.
        if verdictTicker.exists {
            XCTAssertTrue(app.staticTexts["score"].waitForExistence(timeout: 10))
            XCTAssertTrue(app.staticTexts["90-day posture"].waitForExistence(timeout: 10))
        }

        // App must still be alive and tab-churnable after the full render.
        XCTAssertTrue(app.state == .runningForeground)
    }

    func testTabChurnAfterScan() throws {
        dismissOnboardingIfNeeded()
        for name in ["Scan", "Plan", "Today", "Settings", "Scan", "Plan"] {
            let tab = app.tabBars.buttons[name]
            XCTAssertTrue(tab.waitForExistence(timeout: 5), "tab \(name) missing")
            tab.tap()
        }
        XCTAssertTrue(app.state == .runningForeground)
    }

    func testLogDecisionOnBABA() throws {
        dismissOnboardingIfNeeded()
        goToScanTab()
        let field = app.textFields["tickerField"]
        XCTAssertTrue(field.waitForExistence(timeout: 10))
        field.tap()
        field.typeText("BABA")
        app.buttons["runScanButton"].tap()

        // Verdict card: ticker header + score badge render for any action code.
        let ticker = app.staticTexts["BABA"]
        let rendered = ticker.waitForExistence(timeout: 90)
            && app.staticTexts["score"].waitForExistence(timeout: 10)
        XCTAssertTrue(rendered, "BABA verdict must render")

        let logButton = app.buttons.matching(
            NSPredicate(format: "label CONTAINS 'Log:'")
        ).firstMatch
        XCTAssertTrue(logButton.waitForExistence(timeout: 10), "decision log button missing")
        logButton.tap()
        XCTAssertTrue(
            app.staticTexts["Saved privately on this device"]
                .waitForExistence(timeout: 5)
        )

        // The Plan tab must then list the entry without crashing.
        app.tabBars.buttons["Plan"].tap()
        XCTAssertTrue(app.staticTexts["Decision journal"].waitForExistence(timeout: 5))
        XCTAssertTrue(app.state == .runningForeground)
    }
}
