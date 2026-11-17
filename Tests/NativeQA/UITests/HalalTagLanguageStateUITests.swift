import Foundation
import XCTest

/// Real UI persistence checks. This never writes a language preference directly.
/// It addresses only the dedicated artifact verified by QAInstallation.
final class HalalTagLanguageStateUITests: XCTestCase {
    private var app: XCUIApplication!
    private var binding: QAInstallation!

    override func setUpWithError() throws {
        try super.setUpWithError()
        continueAfterFailure = false
        binding = try QAInstallation.loadConfiguration(testBundle: Bundle(for: Self.self))
        app = XCUIApplication(bundleIdentifier: binding.qaBundleIdentifier!)
        try launchFreshProcess()
        try selectLanguage("en")
        try wait("A fresh launch must start with an empty draft") { (self.editor.value as? String) == "" }
        try assertNoResult()
    }

    override func tearDownWithError() throws {
        var resetFailure: Error?
        if app?.state == .runningForeground {
            do { try selectLanguage("en") } catch { resetFailure = error }
        }
        app?.terminate()
        app = nil
        try super.tearDownWithError()
        if let resetFailure { throw resetFailure }
    }

    func testLanguageSwitchPreservesUnscreenedDraftAndDoesNotInventAResult() throws {
        let draft = "pork, E471; English draft"
        XCTAssertLessThan(app.buttons["privacy-info"].frame.midX, app.frame.midX,
                          "English leading navigation action must be on the left")
        try enter(draft)
        try selectLanguage("ar")
        XCTAssertEqual(editor.label, "نص المكونات")
        XCTAssertEqual(editor.value as? String, draft)
        XCTAssertEqual(app.buttons["screen-input"].label, "فحص النص")
        XCTAssertGreaterThan(app.buttons["privacy-info"].frame.midX, app.frame.midX,
                             "Arabic leading navigation action must move to the right")
        try assertNoResult()
        try selectLanguage("en")
        XCTAssertEqual(editor.label, "Ingredient text")
        XCTAssertEqual(editor.value as? String, draft)
        XCTAssertLessThan(app.buttons["privacy-info"].frame.midX, app.frame.midX,
                          "Returning to English must restore LTR navigation")
        try assertNoResult()
        capture("draft-retained-both-directions")
    }

    func testLanguageSwitchPreservesScreenedEvidenceAndEditingInvalidatesResult() throws {
        let draft = "pork, E471"
        try enter(draft)
        try tapScreen()
        try wait("English flagged result must exist") { self.app.staticTexts["Flagged terms found"].exists }
        try selectLanguage("ar")
        XCTAssertEqual(editor.value as? String, draft)
        try wait("Arabic flagged result must preserve the same evidence") {
            self.app.staticTexts["وُجدت كلمات تستدعي الانتباه"].exists &&
            self.app.descendants(matching: .any).matching(identifier: "screening-match-pork").count == 1 &&
            self.app.descendants(matching: .any).matching(identifier: "screening-match-e471").count == 1
        }
        XCTAssertEqual(app.staticTexts["matched-terms-heading"].label, "الكلمات المطابقة")
        capture("arabic-screened-evidence")
        try selectLanguage("en")
        XCTAssertEqual(editor.value as? String, draft)
        try wait("Returning to English must preserve the result") { self.app.staticTexts["Flagged terms found"].exists }
        try reveal(editor)
        editor.tap()
        editor.typeText(" ")
        try wait("An edit must invalidate the previous result") { (self.editor.value as? String) != draft }
        try assertNoResult()
        let clear = app.buttons["clear-input"]
        XCTAssertTrue(clear.isHittable)
        clear.tap()
        try wait("Clear must empty the text") { (self.editor.value as? String) == "" }
        try assertNoResult()
    }

    func testLanguagePreferenceSurvivesRelaunchButDraftAndResultDoNot() throws {
        try enter("pork")
        try tapScreen()
        try selectLanguage("ar")
        try wait("Selected Arabic must be visible before relaunch") { self.editor.label == "نص المكونات" }
        XCTAssertEqual(editor.value as? String, "pork")
        app.terminate()
        try launchFreshProcess()
        // Every launch requests English device/app default language. Persisted
        // Arabic must still win, proving this is the in-app choice, not the OS.
        XCTAssertEqual(editor.label, "نص المكونات")
        XCTAssertEqual(app.buttons["screen-input"].label, "فحص النص")
        XCTAssertEqual(editor.value as? String, "")
        XCTAssertFalse(app.buttons["screen-input"].isEnabled)
        XCTAssertFalse(app.buttons["clear-input"].isEnabled)
        try assertNoResult()
        capture("arabic-preference-after-real-process-relaunch")
    }

    private var editor: XCUIElement { app.textViews["ingredient-editor"] }

    private func launchFreshProcess() throws {
        app.launchArguments = [
            "--appearance-case", "light-large", "--appearance-run-id", binding.runID!,
            "--language-launch-id", UUID().uuidString,
            "-AppleLanguages", "(en)", "-AppleLocale", "en_US"
        ]
        app.launch()
        try wait("The dedicated app must expose its real editor", timeout: 10) { self.editor.exists }
    }

    private func selectLanguage(_ code: String) throws {
        if !app.buttons["app-language-menu"].exists {
            let info = app.buttons["privacy-info"]
            try wait("The privacy action must be reachable") { info.exists && info.isHittable }
            info.tap()
        }
        let menu = app.buttons["app-language-menu"]
        try wait("The language menu must be reachable") { menu.exists && menu.isHittable }
        menu.tap()
        let option = app.buttons["language-" + code]
        try wait("The requested language must exist") { option.exists && option.isHittable }
        option.tap()
        let done = app.buttons["privacy-done"]
        try wait("Done must remain reachable after switching language") { done.exists && done.isHittable }
        done.tap()
        let expected = code == "ar" ? "نص المكونات" : "Ingredient text"
        try wait("The chosen language must update the real editor") { self.editor.label == expected }
    }

    private func enter(_ text: String) throws {
        try reveal(editor)
        editor.tap()
        editor.typeText(text)
        try wait("The exact draft must remain visible") { (self.editor.value as? String) == text }
    }

    private func tapScreen() throws {
        let action = app.buttons["screen-input"]
        try reveal(action)
        XCTAssertTrue(action.isEnabled)
        action.tap()
        try wait("Screen must dismiss the keyboard") { self.app.keyboards.count == 0 }
    }

    private func reveal(_ element: XCUIElement) throws {
        let scroll = app.scrollViews.containing(.button, identifier: "screen-input").firstMatch
        try wait("The real screening scroll view must exist") { scroll.exists }
        for _ in 0..<8 {
            if element.exists && element.isHittable { return }
            if element.frame.midY < scroll.frame.midY { scroll.swipeDown() } else { scroll.swipeUp() }
        }
        XCTFail("The real control could not be reached within the bounded gesture budget")
        throw PreparationFailure.blocked("Unreachable control in language-state journey")
    }

    private func assertNoResult() throws {
        let labels = ["Flagged terms found", "Source or context needs review", "No supported match — status unknown",
                      "وُجدت كلمات تستدعي الانتباه", "يلزم التحقق من المصدر أو السياق", "لا توجد مطابقة مدعومة — الحالة غير معروفة"]
        try wait("No stale or invented result may appear") {
            labels.allSatisfy { !self.app.staticTexts[$0].exists }
        }
    }

    private func capture(_ name: String) {
        let screenshot = XCTAttachment(screenshot: app.screenshot())
        screenshot.name = name
        screenshot.lifetime = .keepAlways
        add(screenshot)
        let tree = XCTAttachment(string: app.debugDescription)
        tree.name = name + "-accessibility-tree"
        tree.lifetime = .keepAlways
        add(tree)
    }

    private func wait(_ message: String, timeout: TimeInterval = 3, condition: @escaping () -> Bool) throws {
        let expectation = XCTNSPredicateExpectation(predicate: NSPredicate { _, _ in condition() }, object: nil)
        guard XCTWaiter.wait(for: [expectation], timeout: timeout) == .completed else {
            XCTFail(message)
            throw PreparationFailure.blocked(message)
        }
    }
}
