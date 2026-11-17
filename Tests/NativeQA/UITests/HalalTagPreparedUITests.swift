import Foundation
import XCTest
import CryptoKit
import ImageIO
import UIKit

/// Three original appearance/maximum-text cases, with unchanged executable code.
/// Ten functional bodies are also present; their helper/binding adaptation is documented separately.
final class HalalTagAppearanceUITests: XCTestCase {
    private var app: XCUIApplication!
    private var binding: QAInstallation!
    private var previousAppearance: XCUIDevice.Appearance?
    private var caseID = ""
    private var captureIndex = 0
    private var gestureCount = 0
    private var captures: [[String: Any]] = []
    private var gestures: [[String: Any]] = []
    private var readCoverage: [[String: Any]] = []
    private var matchEvidence: [String: Any] = [:]
    private var matchReadGestureStart: Int?
    private var audits: [String] = []
    private var actions: [String] = []
    private let stateTimeout: TimeInterval = 3
    private let sample = "Water, dates, citric acid"
    private let flagged = "Flagged terms found"
    private let unknown = "No supported match — status unknown"
    private let coverage = "Coverage is limited to a small English term list and E120/E471 formats. Other languages, ingredients, synonyms, and complex label claims may not be recognised. Unmatched text does not establish halal status."

    override func setUpWithError() throws {
        try super.setUpWithError()
        continueAfterFailure = false
        binding = try QAInstallation.loadConfiguration(testBundle: Bundle(for: HalalTagAppearanceUITests.self))
        // Only the explicitly bound dedicated QA app is ever addressed.
        app = XCUIApplication(bundleIdentifier: binding.qaBundleIdentifier!)
    }

    override func tearDownWithError() throws {
        app?.terminate()
        app = nil
        if let previousAppearance { XCUIDevice.shared.appearance = previousAppearance }
        previousAppearance = nil
        try super.tearDownWithError()
    }

    func testLightAppearanceAndContrastJourney() throws {
        try launch("light-large", appearance: .light)
        try journey(includeFocusedSample: false)
    }

    func testDarkAppearanceAndContrastJourney() throws {
        try launch("dark-large", appearance: .dark)
        try journey(includeFocusedSample: false)
    }

    func testMaximumTextReachabilityAndFocusedSampleReplacement() throws {
        try launch("light-accessibility5", appearance: .light)
        try journey(includeFocusedSample: true)
    }

    private func launch(_ selected: String, appearance: XCUIDevice.Appearance) throws {
        caseID = selected
        previousAppearance = XCUIDevice.shared.appearance
        XCUIDevice.shared.appearance = appearance
        try wait("The requested system appearance did not take effect") { XCUIDevice.shared.appearance == appearance }
        XCUIDevice.shared.orientation = .portrait
        app.terminate()
        app.launchArguments = ["--appearance-case", selected, "--appearance-run-id", binding.runID!]
        app.launch()
        try wait("Bound QA launch did not expose the editor", timeout: 10) { self.app.textViews.matching(NSPredicate(format: "label == %@", "Ingredient text")).count == 1 }
        try assertInput("")
        try noResult()
        let bar = app.navigationBars.matching(identifier: "HalalTag")
        try wait("The native HalalTag navigation title must exist once") { bar.count == 1 && bar.element(boundBy: 0).staticTexts.matching(NSPredicate(format: "label == %@", "HalalTag")).count == 1 }
        try capture("entry")
        try audit("entry")
    }

    private func journey(includeFocusedSample: Bool) throws {
        let editor = try unique(app.textViews.matching(NSPredicate(format: "label == %@", "Ingredient text")), "Ingredient text")
        let screen = try button("Screen text")
        let clear = try button("Clear")
        try wait("Empty Screen and Clear must be disabled") { !screen.isEnabled && !clear.isEnabled }
        try readBlock(try text("Match a small set of English ingredient terms. Results identify words to check; they do not determine halal status."), key: "entry-scope", sheet: false)
        try reveal(editor, key: "editor", sheet: false)
        editor.tap()
        editor.typeText("pork")
        try assertInput("pork")
        try wait("Expected the actual software keyboard") { self.app.keyboards.count > 0 }
        try capture("keyboard")
        try reveal(screen, key: "screen-with-keyboard", sheet: false)
        try tap(screen, "screen")
        try wait("Screen must dismiss the keyboard") { self.app.keyboards.count == 0 }
        try assertInput("pork")
        try wait("Current flagged outcome is missing or competing") {
            self.app.staticTexts.matching(NSPredicate(format: "label == %@", self.flagged)).count == 1 &&
            self.app.staticTexts.matching(NSPredicate(format: "label == %@", self.unknown)).count == 0 &&
            self.app.staticTexts.matching(NSPredicate(format: "label == %@", "Source or context needs review")).count == 0
        }
        try reveal(try text(flagged), key: "flagged-heading", sheet: false)
        try capture("flagged-result")
        try audit("flagged-result")
        try readPorkEvidence()
        try readBlock(try text(coverage), key: "coverage", sheet: false)

        let privacy = try button("Read privacy and limitations")
        try reveal(privacy, key: "privacy-action", sheet: false)
        try capture("privacy-action")
        try audit("privacy-action")
        try tap(privacy, "open-privacy")
        try wait("Privacy sheet did not open") { self.app.navigationBars.matching(identifier: "Privacy & limitations").count == 1 }
        try capture("privacy-sheet")
        try audit("privacy-sheet")
        for heading in ["What this screen does", "What a result means", "Your text and privacy", "Language and coverage"] {
            try reveal(try text(heading), key: "privacy-" + heading, sheet: true)
            try capture("privacy-section")
            try audit("privacy-section-" + heading)
        }
        try tap(try button("Done"), "close-privacy")
        try wait("Privacy sheet did not dismiss") { self.app.navigationBars.matching(identifier: "Privacy & limitations").count == 0 }
        try assertInput("pork")
        try wait("Privacy must preserve the current result") { self.app.staticTexts.matching(NSPredicate(format: "label == %@", self.flagged)).count == 1 }
        try tap(clear, "clear-result")
        try assertInput("")
        try noResult()

        if includeFocusedSample {
            try reveal(editor, key: "focused-sample-editor", sheet: false)
            editor.tap()
            editor.typeText("unscreened replacement fixture")
            try assertInput("unscreened replacement fixture")
            try wait("Focused sample case requires a visible keyboard") { self.app.keyboards.count > 0 }
            try capture("focused-before-sample")
        }
        let sampleButton = try button(sample)
        try reveal(sampleButton, key: "sample", sheet: false)
        try tap(sampleButton, "replace-with-unknown-sample")
        try assertInput(sample)
        try wait("Sample must replace the old outcome with unknown") {
            self.app.staticTexts.matching(NSPredicate(format: "label == %@", self.unknown)).count == 1 &&
            self.app.staticTexts.matching(NSPredicate(format: "label == %@", self.flagged)).count == 0 &&
            self.app.staticTexts.matching(NSPredicate(format: "label == %@", "Matched terms")).count == 0
        }
        try reveal(try text(unknown), key: "unknown-result", sheet: false)
        try capture("unknown-result")
        try audit("unknown-result")
        try tap(clear, "clear-sample")
        try assertInput("")
        try noResult()
        try wait("Final empty actions must be disabled") { !screen.isEnabled && !clear.isEnabled }
        try capture("completed")
        try attachJSON("Appearance case completed", ["schema_version": 1, "run_id": binding.runID!, "case_id": caseID,
            "test_name": name, "actions": actions, "audits": audits, "captures": captures,
            "gestures": gestures, "gesture_count": gestureCount, "read_coverage": readCoverage,
            "match_semantics": matchEvidence, "status": "CASE_COMPLETED"])
    }

    private func readPorkEvidence() throws {
        let expected: [(key: String, label: String)] = [
            ("matched-name", "Pork-related terms"),
            ("matched-disposition", "Flagged term — verify the label"),
            ("matched-text", "Matched text: pork"),
            ("matched-explanation", "Verify what the label refers to and obtain ingredient-origin information from the manufacturer or a qualified certifier.")
        ]
        let card = try unique(app.descendants(matching: .any).matching(identifier: "screening-match-pork"),
                              "real pork evidence container")
        try check(card.elementType != .staticText, "Match evidence is still one combined text element")
        let children = card.descendants(matching: .staticText).allElementsBoundByIndex
        try check(children.count == expected.count && children.map(\.label) == expected.map { $0.label },
                  "Match evidence lost, duplicated or reordered a real text element")
        let containerFrame = card.frame
        var childEvidence: [[String: Any]] = []
        var previousBottom = containerFrame.minY
        for (index, child) in children.enumerated() {
            let frame = child.frame
            try check(child.exists && frame.width > 0 && frame.height > 0 &&
                      containerFrame.insetBy(dx: -2, dy: -2).contains(frame) &&
                      frame.minY >= previousBottom - 2,
                      "Match evidence has overlapping or detached text: " + expected[index].key)
            previousBottom = frame.maxY
            childEvidence.append(["key": expected[index].key, "label": child.label,
                                  "is_static_text": child.elementType == .staticText, "frame": rect(frame)])
        }
        matchEvidence = ["container_identifier": card.identifier,
                         "container_is_static_text": card.elementType == .staticText,
                         "container_frame": rect(containerFrame), "children": childEvidence]
        try attachJSON("Appearance actual match semantics", matchEvidence)
        // Splitting the card does not increase its original eight-gesture budget.
        // Each real text also keeps the unchanged continuous-reading assertions.
        let start = gestureCount
        matchReadGestureStart = start
        defer { matchReadGestureStart = nil }
        for (index, child) in children.enumerated() {
            try check(child.label == expected[index].label, "Match evidence label changed while reading")
            try readBlock(child, key: expected[index].key, sheet: false)
        }
        try check(gestureCount - start <= 8, "Match evidence exceeded its original eight-gesture section budget")
        matchEvidence["gesture_count"] = gestureCount - start
    }

    private func unique(_ query: XCUIElementQuery, _ label: String) throws -> XCUIElement {
        try wait("Missing or ambiguous " + label) { query.count == 1 }
        return query.element(boundBy: 0)
    }
    private func button(_ label: String) throws -> XCUIElement { try unique(app.buttons.matching(NSPredicate(format: "label == %@", label)), label) }
    private func text(_ label: String) throws -> XCUIElement { try unique(app.staticTexts.matching(NSPredicate(format: "label == %@", label)), label) }
    private func assertInput(_ expected: String) throws {
        try wait("Input does not exactly equal the synthetic expected text") {
            let q = self.app.textViews.matching(NSPredicate(format: "label == %@", "Ingredient text"))
            return q.count == 1 && (q.element(boundBy: 0).value as? String) == expected
        }
    }
    private func noResult() throws {
        try wait("Obsolete outcome or result footer remains") {
            [self.flagged, self.unknown, "Source or context needs review", "Matched terms", self.coverage].allSatisfy {
                self.app.staticTexts.matching(NSPredicate(format: "label == %@", $0)).count == 0
            } && self.app.buttons.matching(NSPredicate(format: "label == %@", "Read privacy and limitations")).count == 0
        }
    }
    private func content(_ sheet: Bool) throws -> XCUIElement {
        let q = sheet ? app.scrollViews.containing(.staticText, identifier: "What this screen does") : app.scrollViews.containing(.button, identifier: "Screen text")
        return try unique(q, "active content scroll view")
    }
    private func viewport(_ container: XCUIElement, sheet: Bool) throws -> CGRect {
        // iOS also exposes full-frame keyboard/input windows. Identify the
        // unique product window by its actual navigation content, then retain
        // the original full-size, uniqueness and viewport requirements.
        let windows = app.windows.containing(.navigationBar, identifier: sheet ? "Privacy & limitations" : "HalalTag")
            .allElementsBoundByIndex.filter { $0.exists && $0.frame == app.frame }
        try check(windows.count == 1, "Expected one actual full-size QA app window")
        let window = windows[0]
        var rect = container.frame.intersection(window.frame)
        let bars = app.navigationBars.matching(identifier: sheet ? "Privacy & limitations" : "HalalTag")
        if bars.count == 1 {
            let navigationFrame = bars.element(boundBy: 0).frame
            try attachJSON("Appearance actual scroll boundary", ["sheet": sheet,
                "scroll_frame": self.rect(container.frame), "navigation_frame": self.rect(navigationFrame)])
            try check(container.frame.minY >= navigationFrame.maxY - 0.5,
                      "Actual scroll view extends beneath the native navigation bar")
            let top = max(rect.minY, navigationFrame.maxY)
            rect = CGRect(x: rect.minX, y: top, width: rect.width, height: max(0, rect.maxY - top))
        }
        if app.keyboards.count > 0 {
            let bottom = min(rect.maxY, app.keyboards.element(boundBy: 0).frame.minY)
            rect.size.height = max(0, bottom - rect.minY)
        }
        try check(rect.width > 100 && rect.height > 80 && !rect.isInfinite && !rect.isNull, "No usable actual content viewport")
        return rect.insetBy(dx: 2, dy: 2)
    }
    private func reveal(_ element: XCUIElement, key: String, sheet: Bool) throws {
        let scroll = try content(sheet)
        for attempt in 0...4 {
            let visible = try viewport(scroll, sheet: sheet)
            if element.exists && element.isHittable && visible.contains(element.frame) { return }
            try check(attempt < 4, "Control not reachable within four measured gestures: " + key)
            try check(element.exists && element.frame.width > 0 && element.frame.height > 0 && element.frame.height <= visible.height, "Missing/oversized control needs investigation: " + key)
            let direction = element.frame.maxY > visible.maxY ? -1.0 : 1.0
            try drag(scroll, anchor: element, direction: direction, key: key, sheet: sheet)
        }
    }
    private func readBlock(_ element: XCUIElement, key: String, sheet: Bool) throws {
        let scroll = try content(sheet)
        var furthest: CGFloat = 0
        var began = false
        var auditDisplaced = false
        for attempt in 0...8 {
            let visible = try viewport(scroll, sheet: sheet)
            let frame = element.frame
            try check(element.exists && frame.width > 0 && frame.height > 0, "Missing readable block: " + key)
            if !began && (frame.minY < visible.minY || frame.minY >= visible.maxY - 30) {
                try check(attempt < 8, "Text start not reached within bounded gestures: " + key)
                try drag(scroll, anchor: element, direction: frame.minY < visible.minY ? 1 : -1, key: key, sheet: sheet)
                continue
            }
            let intersection = frame.intersection(visible)
            let start = intersection.isNull ? CGFloat.infinity : max(0, intersection.minY - frame.minY)
            let end = intersection.isNull ? -CGFloat.infinity : min(frame.height, intersection.maxY - frame.minY)
            // The original audit can move the actual scroll offset. Restore
            // exposure using measured gestures inside this SAME eight-step and
            // forty-total budget; never count an unseen or skipped text region.
            if auditDisplaced && (intersection.isNull || intersection.height <= 10 ||
                                  end <= furthest + 2 || start > furthest + 2) {
                try check(attempt < 8, "Audit-displaced text not restored within original bounded gestures: " + key)
                let nextUnreadY = frame.minY + furthest
                try drag(scroll, anchor: element,
                    direction: nextUnreadY >= visible.maxY - 2 ? -1 : 1, key: key, sheet: sheet)
                continue
            }
            try check(!intersection.isNull && intersection.height > 10 && element.isHittable, "Readable text is not exposed: " + key)
            try check(start <= furthest + 2, "A reveal gesture skipped an unobserved text region: " + key)
            began = true
            auditDisplaced = false
            furthest = max(furthest, end)
            let captureNumber = captureIndex + 1
            try capture(key)
            readCoverage.append(["key": key, "capture_index": captureNumber,
                "start": Double(start), "end": Double(end), "height": Double(frame.height),
                "frame": rect(frame), "viewport": rect(visible)])
            let beforeAudit = element.frame
            try audit(key)
            // Reacquire real geometry after the unchanged unfiltered audit.
            let afterAudit = element.frame
            let afterViewport = try viewport(scroll, sheet: sheet)
            try attachJSON("Appearance audit viewport observation", ["key": key,
                "before_frame": rect(beforeAudit), "after_frame": rect(afterAudit),
                "before_viewport": rect(visible), "after_viewport": rect(afterViewport),
                "read_through": Double(furthest), "attempt": attempt])
            try check(element.exists && abs(afterAudit.width - beforeAudit.width) <= 2 &&
                      abs(afterAudit.height - beforeAudit.height) <= 2,
                      "Audit did not restore the readable block's actual geometry: " + key)
            auditDisplaced = abs(afterAudit.minY - beforeAudit.minY) > 2 ||
                             abs(afterViewport.minY - visible.minY) > 2 ||
                             abs(afterViewport.maxY - visible.maxY) > 2
            if furthest >= frame.height - 2 { return }
            try check(attempt < 8, "Text not covered within eight bounded reveal steps: " + key)
            let nextUnreadY = afterAudit.minY + furthest
            let direction = auditDisplaced && nextUnreadY < afterViewport.minY ? 1.0 : -1.0
            try drag(scroll, anchor: element, direction: direction, key: key, sheet: sheet)
        }
    }
    private func drag(_ scroll: XCUIElement, anchor: XCUIElement, direction: Double, key: String, sheet: Bool) throws {
        try check(gestureCount < 40, "The bounded 40-gesture case budget was exhausted")
        if let matchReadGestureStart {
            try check(gestureCount - matchReadGestureStart < 8,
                      "Match evidence exhausted its original eight-gesture section budget")
        }
        let visible = try viewport(scroll, sheet: sheet)
        let before = anchor.frame
        // Derive a left gutter from real visible content. The previous trailing
        // path intersected the native indicator thumb and scrubbed the document.
        let contentFrames = (scroll.staticTexts.allElementsBoundByIndex +
                             scroll.buttons.allElementsBoundByIndex +
                             scroll.textViews.allElementsBoundByIndex).map(\.frame)
            .filter { $0.width > 0 && $0.height > 0 && $0.intersects(visible) }
        try check(!contentFrames.isEmpty, "No measured content margin for gesture: " + key)
        let gutterLeft = visible.minX + 2
        let gutterRight = (contentFrames.map(\.minX).min() ?? visible.minX) - 2
        try check(gutterRight - gutterLeft >= 4, "No safe measured left gutter: " + key)
        let x = (gutterLeft + gutterRight) / 2
        let startY = direction < 0 ? visible.minY + visible.height * 0.78 : visible.minY + visible.height * 0.22
        let endY = direction < 0 ? visible.minY + visible.height * 0.22 : visible.minY + visible.height * 0.78
        let route = CGRect(x: x - 2, y: min(startY, endY), width: 4,
                           height: abs(endY - startY))
        let editorFrames = scroll.textViews.allElementsBoundByIndex.map(\.frame)
            .filter { $0.width > 0 && $0.height > 0 }
        let indicatorFrames = scroll.descendants(matching: .any)
            .matching(NSPredicate(format: "label CONTAINS[c] %@", "scroll bar"))
            .allElementsBoundByIndex.map(\.frame)
            .filter { $0.width > 0 && $0.height > 0 }
        try check(visible.contains(route) && !editorFrames.contains { $0.intersects(route) } &&
                  !indicatorFrames.contains { $0.intersects(route) },
                  "Measured drag route intersects an editor or native scroll indicator: " + key)
        try attachJSON("Appearance measured drag route", ["key": key, "direction": direction,
            "route": rect(route), "gutter_left": Double(gutterLeft), "gutter_right": Double(gutterRight),
            "editor_frames": editorFrames.map { rect($0) },
            "indicator_frames": indicatorFrames.map { rect($0) }])
        let origin = scroll.coordinate(withNormalizedOffset: .zero)
        let start = origin.withOffset(CGVector(dx: x - scroll.frame.minX, dy: startY - scroll.frame.minY))
        let end = origin.withOffset(CGVector(dx: x - scroll.frame.minX, dy: endY - scroll.frame.minY))
        try capture("before-gesture")
        start.press(forDuration: 0.1, thenDragTo: end, withVelocity: .slow, thenHoldForDuration: 0.2)
        try wait("Content gesture made no progress in the requested direction: " + key) {
            direction * Double(anchor.frame.minY - before.minY) > 1
        }
        gestureCount += 1
        let event: [String: Any] = ["index": gestureCount, "key": key, "direction": direction,
            "before": rect(before), "after": rect(anchor.frame), "viewport": rect(visible)]
        gestures.append(event)
        try attachJSON("Appearance measured gesture", event)
        try capture("after-gesture")
    }
    private func tap(_ element: XCUIElement, _ key: String) throws {
        try check(element.exists && element.isHittable && element.isEnabled, "Action is unavailable: " + key)
        try check(app.windows.element(boundBy: 0).frame.contains(element.frame), "Action lies outside its window: " + key)
        if app.keyboards.count > 0 { try check(!element.frame.intersects(app.keyboards.element(boundBy: 0).frame), "Keyboard covers action: " + key) }
        element.tap()
        actions.append(key)
    }
    private func audit(_ pose: String) throws {
        // No issue handler/filter: any real issue fails the case and is retained by XCTest.
        try app.performAccessibilityAudit(for: [.contrast, .textClipped, .dynamicType])
        audits.append(pose)
    }
    private func capture(_ pose: String) throws {
        guard let app, app.state == .runningForeground else { return }
        captureIndex += 1
        let captureName = "appearance-\(caseID)-\(captureIndex)-\(pose.replacingOccurrences(of: " ", with: "-"))"
        let shot = XCUIScreen.main.screenshot()
        let png = shot.pngRepresentation
        let attachment = XCTAttachment(data: png, uniformTypeIdentifier: "public.png")
        attachment.name = captureName
        attachment.lifetime = .keepAlways
        add(attachment)
        let hash = SHA256.hash(data: png).map { String(format: "%02x", $0) }.joined()
        let source = CGImageSourceCreateWithData(png as CFData, nil)
        let properties = source.flatMap { CGImageSourceCopyPropertiesAtIndex($0, 0, nil) as? [CFString: Any] }
        let width = (properties?[kCGImagePropertyPixelWidth] as? NSNumber)?.intValue ?? -1
        let height = (properties?[kCGImagePropertyPixelHeight] as? NSNumber)?.intValue ?? -1
        let value: [String: Any] = ["schema_version": 1, "run_id": binding.runID!, "case_id": caseID,
            "test_name": name, "capture_name": captureName, "pose": pose, "index": captureIndex,
            "png_sha256": hash, "png_bytes": png.count, "pixel_width": width, "pixel_height": height,
            "app_frame": rect(app.frame), "window_frame": rect(app.windows.element(boundBy: 0).frame),
            "orientation": XCUIDevice.shared.orientation.rawValue,
            "system_appearance": XCUIDevice.shared.appearance.rawValue,
            "UIImage_width": shot.image.size.width, "UIImage_height": shot.image.size.height,
            "UIImage_scale": shot.image.scale, "CGImage_width": shot.image.cgImage?.width ?? -1,
            "CGImage_height": shot.image.cgImage?.height ?? -1]
        try attachJSON("Appearance PNG geometry - " + captureName, value)
        attachText("Appearance AX - " + captureName, app.debugDescription)
        captures.append(value)
        // Original PNG/metadata are attached BEFORE any assertion, including failures.
        XCTAssertEqual(width, 750, "Expected the pinned SE native screenshot width")
        XCTAssertEqual(height, 1334, "Expected the pinned SE native screenshot height")
        XCTAssertLessThanOrEqual(captureIndex, 150, "Bounded capture budget exceeded")
        XCTAssertEqual(app.frame.size.width, 375)
        XCTAssertEqual(app.frame.size.height, 667)
    }
    private func rect(_ value: CGRect) -> [String: Double] { ["x": Double(value.minX), "y": Double(value.minY), "width": Double(value.width), "height": Double(value.height)] }
    private func attachText(_ label: String, _ value: String) {
        let item = XCTAttachment(string: value); item.name = label; item.lifetime = .keepAlways; add(item)
    }
    private func attachJSON(_ label: String, _ value: [String: Any]) throws {
        let data = try JSONSerialization.data(withJSONObject: value, options: [.sortedKeys])
        attachText(label, String(decoding: data, as: UTF8.self))
    }
    private func check(_ condition: Bool, _ message: String) throws {
        if !condition { try capture("failure"); XCTFail(message); throw PreparationFailure.blocked(message) }
    }
    private func wait(_ message: String, timeout: TimeInterval? = nil, _ condition: @escaping () -> Bool) throws {
        if condition() { return }
        let expectation = XCTNSPredicateExpectation(predicate: NSPredicate { _, _ in condition() }, object: nil)
        try check(XCTWaiter.wait(for: [expectation], timeout: timeout ?? stateTimeout) == .completed, message)
    }
}

// The reviewed fail-closed QAInstallation guard is appended by the preparation script.

enum PreparationFailure: Error, CustomStringConvertible {
    case blocked(String)
    var description: String {
        switch self { case .blocked(let reason): return reason }
    }
}

/// This is runner configuration, not a user approval workflow or a claim that source
/// hashes independently prove what is installed. Packaging/install evidence
/// must be verified by the integration owner before configuring this resource.
struct QAInstallation: Decodable {
    let schemaVersion: Int
    let configurationStatus: String
    let runID: String?
    let qaBundleIdentifier: String?
    let productionBundleIdentifier: String?
    let uiTestBundleIdentifier: String?
    let installationIsDedicatedAndSynthetic: Bool
    let qaArtifactSHA256: String?
    let buildEvidenceReference: String?
    let installationEvidenceReference: String?
    let destinationEvidenceReference: String?
    let contentViewSHA256: String
    let ingredientScreeningSHA256: String
    let screeningLocalizationSHA256: String
    let privacyManifestSHA256: String

    static func loadConfiguration(testBundle: Bundle) throws -> QAInstallation {
        let environment = ProcessInfo.processInfo.environment
        guard environment["HALALTAG_UI_QA_RUN_MODE"] == "ISOLATED_SYNTHETIC_QA" else {
            throw PreparationFailure.blocked("QA launch refused: the runner is not configured for an isolated synthetic installation. Do not substitute the production app.")
        }
        guard let url = testBundle.url(forResource: "HalalTagSyntheticQAInstallation", withExtension: "json") else {
            throw PreparationFailure.blocked("QA launch refused: the separately reviewed installation manifest is not a UI-test-bundle resource. The supplied example is intentionally unconfigured.")
        }
        let manifest = try JSONDecoder().decode(QAInstallation.self, from: Data(contentsOf: url))
        guard manifest.schemaVersion == 1,
              manifest.configurationStatus == "CONFIGURED_ISOLATED_QA",
              manifest.installationIsDedicatedAndSynthetic,
              let runID = manifest.runID, UUID(uuidString: runID) != nil,
              environment["HALALTAG_UI_QA_RUN_ID"] == runID else {
            throw PreparationFailure.blocked("QA launch refused: isolated-installation configuration/run binding is missing or inconsistent.")
        }
        guard let qaID = manifest.qaBundleIdentifier,
              let productionID = manifest.productionBundleIdentifier,
              nonemptyIdentity(qaID), nonemptyIdentity(productionID),
              qaID != productionID,
              let testID = manifest.uiTestBundleIdentifier,
              testID == testBundle.bundleIdentifier,
              testID != qaID, testID != productionID else {
            throw PreparationFailure.blocked("QA launch refused: require the actual verified dedicated QA identity, the distinct production identity, and the exact UI test bundle identity. No app identifier or naming convention is supplied by this preparation.")
        }
        guard let artifact = manifest.qaArtifactSHA256,
              artifact.range(of: "^[0-9a-f]{64}$", options: .regularExpression) != nil,
              artifact != String(repeating: "0", count: 64),
              usableReference(manifest.buildEvidenceReference),
              usableReference(manifest.installationEvidenceReference),
              usableReference(manifest.destinationEvidenceReference) else {
            throw PreparationFailure.blocked("QA launch refused: exact synthetic artifact, installation and destination evidence are required.")
        }
        guard manifest.contentViewSHA256 == "06b6d75101b40eb4b99b9b59c1de876e54b6df85f772b3ed633f7fcf1a83a2fc",
              manifest.ingredientScreeningSHA256 == "fc8aab56d0fbdf7682cc77bf74a0a1811c813e93447b6985379f24c122e4167a",
              manifest.screeningLocalizationSHA256 == "097a18920ff95fda968c6cee1591360b50b0c077673bf40cb6c0970e8aa8be70",
              manifest.privacyManifestSHA256 == "a331d51864743ebe4e00dd22360b4a538b6b3ac26a6b3eb54094e60a36959a12" else {
            throw PreparationFailure.blocked("QA launch refused: declared source hashes differ from the reviewed snapshot. Re-review the suite and evidence; do not silently refresh hashes.")
        }
        return manifest
    }

    private static func nonemptyIdentity(_ value: String) -> Bool {
        !value.isEmpty && value == value.trimmingCharacters(in: .whitespacesAndNewlines)
    }

    private static func usableReference(_ value: String?) -> Bool {
        guard let value = value else { return false }
        let trimmed = value.trimmingCharacters(in: .whitespacesAndNewlines)
        return !trimmed.isEmpty && !["UNCONFIGURED", "TODO", "PENDING"].contains(trimmed.uppercased())
    }
}
