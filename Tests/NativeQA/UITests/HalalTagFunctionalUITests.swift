import Foundation
import XCTest

/// Production composition preparation: all ten original test method bodies retained.
/// The shared QA guard, launch binding and independently readable match helper are
/// separately reviewed adaptations. Native compile and execution are still unverified.
final class HalalTagPreparedUITests: XCTestCase {
    private var app: XCUIApplication!
    private let stateTimeout: TimeInterval = 3

    private enum Outcome: String, CaseIterable {
        case flagged = "Flagged terms found"
        case review = "Source or context needs review"
        case unknown = "No supported match — status unknown"
    }

    private enum Copy {
        static let entryScope = "Match a small set of English ingredient terms. Results identify words to check; they do not determine halal status."
        static let coverage = "Coverage is limited to a small English term list and E120/E471 formats. Other languages, ingredients, synonyms, and complex label claims may not be recognised. Unmatched text does not establish halal status."
        static let flaggedSummary = "This text includes words in the limited flagged list. A word match cannot establish ingredient presence or halal status. Check the original label and ingredient source."
        static let reviewSummary = "The matched terms need source or context checks. This app cannot verify label claims, processing, or certification."
        static let unknownSummary = "No supported terms were matched. Unrecognised ingredients, spellings, and languages may be missed. No conclusion about the product can be drawn."
        static let informationScope = "It matches a limited set of English ingredient words and E120/E471 formats in text you choose to type or paste. It has no camera, OCR, barcode scanning, trained AI model, or remote screening service."
        static let sampleGelatin = "Gelatin, sugar, natural flavors"
        static let sampleUnknown = "Water, dates, citric acid"
        static let sampleFlagged = "Ethanol, vanilla extract, color E120"
    }

    override func setUpWithError() throws {
        try super.setUpWithError()
        continueAfterFailure = false

        // Nothing constructs, terminates or launches an application until all
        // runner-only configuration checks succeed. There is no default target.
        let configuration = try QAInstallation.loadConfiguration(
            testBundle: Bundle(for: HalalTagPreparedUITests.self)
        )
        app = XCUIApplication(bundleIdentifier: configuration.qaBundleIdentifier!)
        app.terminate()
        // Receipt arguments configure only the external simulator QA host.
        // They never change shipping behavior, text, geometry or test expectations.
        app.launchArguments = ["--appearance-case", "light-large",
            "--appearance-run-id", configuration.runID!,
            "--language-launch-id", UUID().uuidString,
            "-AppleLanguages", "(en)", "-AppleLocale", "en_US"]
        app.launch()
        try requireEventually("Ingredient text is absent after QA launch", timeout: 10) {
            self.editor.exists
        }
        // Do not clear an unexpected restored session to make a fresh test pass.
        try assertInput("")
        try assertNoResult()
        attachText("QA run binding", "runID=\(configuration.runID!)\nqaBundleIdentifier=\(configuration.qaBundleIdentifier!)\nartifactSHA256=\(configuration.qaArtifactSHA256!)\nbuildEvidence=\(configuration.buildEvidenceReference!)\ninstallationEvidence=\(configuration.installationEvidenceReference!)\ndestinationEvidence=\(configuration.destinationEvidenceReference!)")
    }

    override func tearDownWithError() throws {
        // app can only be assigned after the fail-closed QA guard.
        app?.terminate()
        app = nil
        try super.tearDownWithError()
    }

    // HTUI-01 — H-01, H-04, H-07 (partial).
    func testFreshLaunchShowsScopeAndDisabledEmptyActions() throws {
        try requirePresent(text(Copy.entryScope), "The bounded English-screening scope must be exposed")
        try requirePresent(text("Changing the text clears the result. No result is a halal certificate."), "The noncertification warning must be exposed")
        try requirePresent(screenButton, "The existing Screen text action is missing")
        try requirePresent(clearButton, "The existing Clear action is missing")
        try requireEventually("Empty Screen text must be disabled") { !self.screenButton.isEnabled }
        try requireEventually("Empty Clear must be disabled") { !self.clearButton.isEnabled }
        try requireFullyVisible(editor, "The fresh ingredient editor")
        try requireFullyVisible(button("Privacy and limitations"), "The pre-screening limitations control")
        for sample in [Copy.sampleGelatin, Copy.sampleUnknown, Copy.sampleFlagged] {
            try requirePresent(button(sample), "Missing existing sample: \(sample)")
        }
        capture("fresh-scope-and-empty-actions")
    }

    // HTUI-02 — H-04, H-06 (partial).
    func testWhitespaceCannotBeScreenedAndCanBeCleared() throws {
        try enterFreshText("   ")
        try requireEventually("Whitespace Screen text must stay disabled") { !self.screenButton.isEnabled }
        try requireEventually("Whitespace is input, so Clear must be enabled") { self.clearButton.isEnabled }
        try assertNoResult()
        try tapVisible(clearButton, "Clear whitespace")
        try assertEmptyActions()
    }

    // HTUI-03 — H-01, H-02, H-07 (representative UI evidence only).
    func testDirectTermShowsWordEvidenceAndQualifiedWarning() throws {
        try enterFreshText("pork")
        try submitText()
        try assertOutcome(.flagged)
        try assertCombinedMatch([
            "Pork-related terms",
            "Flagged term — verify the label",
            "Matched text: pork",
            "Verify what the label refers to"
        ])
        capture("direct-term-word-evidence")
    }

    // HTUI-04 — H-01, H-02, H-07 (bounded unknown/boundary example).
    func testUnknownAndUnsupportedPrefixesRemainUnknown() throws {
        try enterFreshText("water, chamomile, E1200, E4710")
        try submitText()
        try assertOutcome(.unknown)
        try requireEventually("Unknown input must not expose a Matched terms section") {
            !self.text("Matched terms").exists
        }
        capture("unknown-is-not-certification")
    }

    // HTUI-05 — H-02, H-07 (one supported qualifier, not a general parser).
    func testAlcoholFreeIsContextReviewWithoutDirectFlag() throws {
        try enterFreshText("alcohol-free")
        try submitText()
        try assertOutcome(.review)
        try assertCombinedMatch([
            "Alcohol-related terms",
            "Label context — claim not verified",
            "Matched text: alcohol",
            "A nearby qualifier or label claim also needs review"
        ])
        try requireEventually("A contextual-only match must not expose the direct-flag disposition") {
            !self.anyLabelContaining("Flagged term — verify the label").exists
        }
        capture("context-claim-not-verified")
    }

    // HTUI-06 — H-04. No submit or navigation between the edit and invalidation check.
    func testFirstEditInvalidatesResultAndRestoringTextDoesNotResurrectIt() throws {
        try enterFreshText("pork")
        try submitText()
        try assertOutcome(.flagged)
        try tapVisible(editor, "Edit the screened text")
        // Refocusing may place the caret anywhere. Prove one real edit without
        // assuming an end-of-text caret or changing the app's selection behavior.
        editor.typeText("x")
        let oneInsertion: Set<String> = ["xpork", "pxork", "poxrk", "porxk", "porkx"]
        try requireEventually("Expected exactly one inserted x in the screened fixture", timeout: 1) {
            guard let value = self.editor.value as? String else { return false }
            return oneInsertion.contains(value)
        }
        try assertNoResult(timeout: 1)
        capture("first-edit-invalidates-result")
        editor.typeText(XCUIKeyboardKey.delete.rawValue)
        try assertInput("pork")
        try assertNoResult(timeout: 1)
        try submitText()
        try assertOutcome(.flagged)
    }

    // HTUI-07 — H-04. Clear is tested after a result and after unscreened editing.
    func testClearRemovesScreenedAndUnscreenedState() throws {
        try enterFreshText("pork")
        try submitText()
        try assertOutcome(.flagged)
        try tapVisible(clearButton, "Clear the screened input")
        try assertEmptyActions()
        try enterFreshText("water")
        try assertNoResult()
        try requireEventually("Nonblank unscreened input must enable Screen text") { self.screenButton.isEnabled }
        try tapVisible(clearButton, "Clear unscreened input")
        try assertEmptyActions()
        capture("clear-resets-input-and-result")
    }

    // HTUI-08 — H-02, H-04. Two shipped samples replace, rather than append.
    func testSampleReplacesExistingTextAndResultWithoutAppending() throws {
        try tapLowerContentControl(button(Copy.sampleGelatin), "Select the existing gelatin sample")
        try assertInput(Copy.sampleGelatin)
        try assertOutcome(.review)
        try assertCombinedMatch([
            "Gelatin",
            "Source-dependent — verify the origin",
            "Matched text: gelatin"
        ])
        try tapLowerContentControl(button(Copy.sampleUnknown), "Replace the current sample with the unknown sample")
        try assertInput(Copy.sampleUnknown)
        try assertOutcome(.unknown)
        try requireEventually("Replacing the sample must remove prior match evidence") {
            !self.text("Matched terms").exists && !self.anyLabelContaining("Matched text: gelatin").exists
        }
        capture("sample-replaces-text-and-outcome")
    }

    // HTUI-09 — H-01, H-11 (in-app sheet only; hosted support remains separate).
    func testLimitationsOpenBeforeAndAfterScreeningWithoutLosingState() throws {
        try tapVisible(button("Privacy and limitations"), "Open limitations before screening")
        try assertInformationSheet()
        try closeInformationSheet()
        try assertEmptyActions()

        try tapLowerContentControl(button(Copy.sampleUnknown), "Select the existing unknown sample")
        try assertInput(Copy.sampleUnknown)
        try assertOutcome(.unknown)
        try tapLowerContentControl(button("Read privacy and limitations"), "Open result limitations")
        try assertInformationSheet()
        try closeInformationSheet()
        try assertInput(Copy.sampleUnknown)
        try assertOutcome(.unknown)
        capture("limitations-return-preserves-current-result")
    }

    // HTUI-10 — H-03, H-06, H-07. No scrolling, keyboard dismissal shortcut,
    // coordinate tap or automatic visibility repair is allowed in this test.
    func testScreenActionAndNewResultAreNotHiddenByKeyboard() throws {
        try enterFreshText("pork")
        try requireEventually("This case requires the QA device's software keyboard to be shown") {
            self.app.keyboards.firstMatch.exists
        }
        capture("keyboard-before-screening")
        try requireFullyVisible(screenButton, "Screen text while the software keyboard is open")
        try requireFullyVisible(clearButton, "Clear while the software keyboard is open")
        try submitText()
        try assertOutcome(.flagged)
        try requireFullyVisible(outcome(.flagged), "The new outcome heading immediately after screening")
        try requireFullyVisible(clearButton, "Clear after screening")
        try assertInput("pork")
        capture("result-without-scroll-or-keyboard-workaround")
    }

    // MARK: Existing accessibility labels

    private var editor: XCUIElement {
        app.textViews.matching(NSPredicate(format: "label == %@", "Ingredient text")).firstMatch
    }
    private var screenButton: XCUIElement { button("Screen text") }
    private var clearButton: XCUIElement { button("Clear") }
    private func button(_ label: String) -> XCUIElement {
        app.buttons.matching(NSPredicate(format: "label == %@", label)).firstMatch
    }
    private func text(_ label: String) -> XCUIElement {
        app.staticTexts.matching(NSPredicate(format: "label == %@", label)).firstMatch
    }
    private func outcome(_ value: Outcome) -> XCUIElement { text(value.rawValue) }
    private func anyLabelContaining(_ fragment: String) -> XCUIElement {
        app.descendants(matching: .any).matching(NSPredicate(format: "label CONTAINS %@", fragment)).firstMatch
    }

    // MARK: Bounded state and interaction checks

    private func enterFreshText(_ value: String) throws {
        try assertInput("")
        try tapVisible(editor, "Focus the ingredient editor")
        editor.typeText(value)
        try assertInput(value)
    }

    private func submitText() throws {
        try tapVisible(screenButton, "Activate Screen text")
    }

    private func assertInput(_ expected: String) throws {
        try requireEventually("Ingredient text did not exactly equal the synthetic fixture \(String(reflecting: expected))") {
            (self.editor.value as? String) == expected
        }
    }

    private func assertEmptyActions() throws {
        try assertInput("")
        try assertNoResult()
        try requireEventually("Empty actions did not reset coherently") {
            self.screenButton.exists && self.clearButton.exists &&
            !self.screenButton.isEnabled && !self.clearButton.isEnabled
        }
    }

    private func assertNoResult(timeout: TimeInterval = 1) throws {
        try requireEventually("An obsolete result, match heading or result footer is still exposed", timeout: timeout) {
            Outcome.allCases.allSatisfy { !self.outcome($0).exists } &&
            !self.text("Matched terms").exists &&
            !self.button("Read privacy and limitations").exists &&
            !self.text(Copy.coverage).exists
        }
    }

    private func assertOutcome(_ expected: Outcome) throws {
        try requireEventually("Expected exactly the \(expected.rawValue) outcome, with no competing outcome") {
            self.outcome(expected).exists &&
            Outcome.allCases.filter { $0 != expected }.allSatisfy { !self.outcome($0).exists }
        }
        let summary: String
        switch expected {
        case .flagged: summary = Copy.flaggedSummary
        case .review: summary = Copy.reviewSummary
        case .unknown: summary = Copy.unknownSummary
        }
        try requirePresent(text(summary), "The exact qualified outcome summary is missing")
        try requirePresent(text(Copy.coverage), "The result coverage notice is missing")
    }

    private func assertCombinedMatch(_ fragments: [String]) throws {
        // The reviewed card exposes four real, independently navigable texts.
        // Preserve every original expected fragment while requiring exact first
        // three labels, one uncombined container, ordering and actual geometry.
        let identifier: String
        switch fragments.first {
        case "Pork-related terms": identifier = "screening-match-pork"
        case "Alcohol-related terms": identifier = "screening-match-alcohol"
        case "Gelatin": identifier = "screening-match-gelatin"
        default: try fail("No reviewed evidence-card mapping for this original fixture")
        }
        let matches = app.descendants(matching: .any).matching(identifier: identifier)
        try requireEventually("Expected one independently readable match card containing: \(fragments.joined(separator: " | "))") {
            guard (3...4).contains(fragments.count), matches.count == 1 else { return false }
            let card = matches.element(boundBy: 0)
            guard card.exists, card.elementType != .staticText else { return false }
            let children = card.descendants(matching: .staticText).allElementsBoundByIndex
            guard children.count == 4,
                  Array(children.prefix(3).map(\.label)) == Array(fragments.prefix(3)),
                  !children[3].label.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty,
                  fragments.count == 3 || children[3].label.contains(fragments[3]) else { return false }
            let containerFrame = card.frame
            guard !containerFrame.isNull, !containerFrame.isInfinite,
                  containerFrame.width > 0, containerFrame.height > 0 else { return false }
            var previousBottom = containerFrame.minY
            for child in children {
                let frame = child.frame
                guard child.exists, !frame.isNull, !frame.isInfinite,
                      frame.width > 0, frame.height > 0,
                      containerFrame.insetBy(dx: -2, dy: -2).contains(frame),
                      frame.minY >= previousBottom - 2 else { return false }
                previousBottom = frame.maxY
            }
            return true
        }
        attachText("Independent match evidence", matches.element(boundBy: 0).debugDescription)
    }

    private func assertInformationSheet() throws {
        try requirePresent(app.navigationBars["Privacy & limitations"], "The limitations sheet title is missing")
        for heading in ["What this screen does", "What a result means", "Your text and privacy", "Language and coverage"] {
            try requirePresent(text(heading), "Missing limitations section: \(heading)")
        }
        try requirePresent(text(Copy.informationScope), "The no-camera/OCR/AI/remote-screening scope is missing")
        try requirePresent(text(Copy.coverage), "The limited-English coverage notice is missing in the sheet")
        try requireFullyVisible(button("Done"), "The limitations dismissal control")
        capture("privacy-and-limitations-sheet")
    }

    private func closeInformationSheet() throws {
        try tapVisible(button("Done"), "Dismiss limitations")
        try requireEventually("The limitations sheet did not dismiss") {
            !self.app.navigationBars["Privacy & limitations"].exists
        }
    }

    private func tapVisible(_ element: XCUIElement, _ purpose: String) throws {
        try requireFullyVisible(element, purpose)
        try requireEventually("\(purpose): the visible control is disabled") { element.isEnabled }
        element.tap()
    }

    /// Only ordinary lower-page navigation for samples / the result help link.
    /// At most one explicit upward gesture; never used for Screen text, editor,
    /// outcome visibility or keyboard remediation. An insufficient route fails
    /// with its snapshot and needs review, not an expanded blind swipe loop.
    private func tapLowerContentControl(_ element: XCUIElement, _ purpose: String) throws {
        try requirePresent(element, "\(purpose): missing existing control")
        if !isFullyVisible(element) {
            guard !app.keyboards.firstMatch.exists else {
                try fail("\(purpose): the keyboard is open; this helper will not hide a keyboard obstruction")
            }
            let content = app.scrollViews.firstMatch
            try requirePresent(content, "\(purpose): expected main scroll container is absent; inspect the native tree")
            capture("before-one-deliberate-content-scroll")
            content.swipeUp()
        }
        try tapVisible(element, "\(purpose) (at most one deliberate content scroll)")
    }

    private func isFullyVisible(_ element: XCUIElement) -> Bool {
        guard element.exists, element.isHittable, app.windows.firstMatch.exists else { return false }
        let frame = element.frame
        guard !frame.isEmpty, !frame.isNull, !frame.isInfinite,
              app.windows.firstMatch.frame.contains(frame) else { return false }
        let keyboard = app.keyboards.firstMatch
        return !keyboard.exists || !keyboard.frame.intersects(frame)
    }

    private func requireFullyVisible(_ element: XCUIElement, _ purpose: String) throws {
        try requireEventually("\(purpose) is not fully inside the window and hittable without keyboard overlap; no visibility workaround was applied") {
            self.isFullyVisible(element)
        }
    }

    private func requirePresent(_ element: XCUIElement, _ message: String) throws {
        try requireEventually(message) { element.exists }
    }

    private func requireEventually(
        _ message: String,
        timeout: TimeInterval? = nil,
        file: StaticString = #filePath,
        line: UInt = #line,
        _ condition: @escaping () -> Bool
    ) throws {
        if condition() { return }
        let predicate = NSPredicate { _, _ in condition() }
        let expectation = XCTNSPredicateExpectation(predicate: predicate, object: nil)
        guard XCTWaiter.wait(for: [expectation], timeout: timeout ?? stateTimeout) == .completed else {
            try fail(message, file: file, line: line)
        }
    }

    private func fail(_ message: String, file: StaticString = #filePath, line: UInt = #line) throws -> Never {
        capture("failure")
        if let app = app { attachText("Synthetic QA accessibility tree", app.debugDescription) }
        XCTFail(message, file: file, line: line)
        throw PreparationFailure.blocked(message)
    }

    private func capture(_ name: String) {
        guard let app = app else { return }
        let attachment = XCTAttachment(screenshot: app.screenshot())
        attachment.name = name
        attachment.lifetime = .keepAlways
        add(attachment)
    }

    private func attachText(_ name: String, _ value: String) {
        let attachment = XCTAttachment(string: value)
        attachment.name = name
        attachment.lifetime = .keepAlways
        add(attachment)
    }
}

