import Foundation
import XCTest
import CryptoKit
import ImageIO
import UIKit

/// Original Arabic methods with the same R7 measured-geometry helper contract as English.
final class HalalTagArabicAppearanceUITests: XCTestCase {
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
    private var gestureBudgets: [[String: Any]] = []
    private var auditRecoveries: [[String: Any]] = []
    private var linkExposure: [[String: Any]] = []
    private var audits: [String] = []
    private var actions: [String] = []
    private let stateTimeout: TimeInterval = 3
    private let sample = "Water, dates, citric acid"
    private let flagged = "وُجدت كلمات تستدعي الانتباه"
    private let unknown = "لا توجد مطابقة مدعومة — الحالة غير معروفة"
    private let coverage = "تقتصر التغطية على قائمة صغيرة من الكلمات الإنجليزية وصيغ الرمزين \u{2066}E120/E471\u{2069}. قد لا يتعرف التطبيق على اللغات الأخرى أو المكونات أو المرادفات أو الادعاءات المعقدة على الملصق. لا يثبت النص غير المطابق صفة الحلال."

    override func setUpWithError() throws {
        try super.setUpWithError()
        continueAfterFailure = false
        binding = try QAInstallation.loadConfiguration(testBundle: Bundle(for: HalalTagArabicAppearanceUITests.self))
        // Only the explicitly bound dedicated QA app is ever addressed.
        app = XCUIApplication(bundleIdentifier: binding.qaBundleIdentifier!)
    }

    override func tearDownWithError() throws {
        var resetFailure: Error?
        if app?.state == .runningForeground {
            do { try selectLanguage("en") } catch { resetFailure = error }
        }
        app?.terminate()
        app = nil
        if let previousAppearance { XCUIDevice.shared.appearance = previousAppearance }
        previousAppearance = nil
        try super.tearDownWithError()
        if let resetFailure { throw resetFailure }
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

    private func selectLanguage(_ code: String) throws {
        if !app.buttons["app-language-menu"].exists {
            let info = app.buttons["privacy-info"]
            try wait("Privacy action must be reachable to select a language") { info.exists && info.isHittable }
            info.tap()
        }
        let menu = app.buttons["app-language-menu"]
        try wait("Language menu must be reachable") { menu.exists && menu.isHittable }
        menu.tap()
        let option = app.buttons["language-" + code]
        try wait("The language option must exist") { option.exists && option.isHittable }
        option.tap()
        let done = app.buttons["privacy-done"]
        try wait("Done must stay reachable after switching language") { done.exists && done.isHittable }
        done.tap()
        let expected = code == "ar" ? "نص المكونات" : "Ingredient text"
        try wait("The real editor label must use the selected language") { self.app.textViews["ingredient-editor"].label == expected }
    }

    private func launch(_ selected: String, appearance: XCUIDevice.Appearance) throws {
        caseID = selected
        previousAppearance = XCUIDevice.shared.appearance
        XCUIDevice.shared.appearance = appearance
        try wait("The requested system appearance did not take effect") { XCUIDevice.shared.appearance == appearance }
        XCUIDevice.shared.orientation = .portrait
        app.terminate()
        app.launchArguments = ["--appearance-case", selected, "--appearance-run-id", binding.runID!, "--language-launch-id", UUID().uuidString, "-AppleLanguages", "(en)", "-AppleLocale", "en_US"]
        app.launch()
        try wait("Bound QA launch did not expose the editor", timeout: 10) { self.app.textViews["ingredient-editor"].exists }
        try selectLanguage("ar")
        try wait("Bound QA launch did not expose the editor", timeout: 10) { self.app.textViews.matching(NSPredicate(format: "label == %@", "نص المكونات")).count == 1 }
        try assertInput("")
        try noResult()
        let bar = app.navigationBars.matching(identifier: "HalalTag")
        try wait("The native HalalTag navigation title must exist once") { bar.count == 1 && bar.element(boundBy: 0).staticTexts.matching(NSPredicate(format: "label == %@", "HalalTag")).count == 1 }
        try capture("entry")
        try audit("entry")
    }

    private func journey(includeFocusedSample: Bool) throws {
        let editor = try unique(app.textViews.matching(NSPredicate(format: "label == %@", "نص المكونات")), "نص المكونات")
        let screen = try button("فحص النص")
        let clear = try button("مسح")
        try wait("Empty Screen and Clear must be disabled") { !screen.isEnabled && !clear.isEnabled }
        try readBlock(try text("يطابق التطبيق مجموعة صغيرة من أسماء المكونات الإنجليزية. تحدد النتائج كلمات تحتاج إلى التحقق، ولا تحدد إن كان المنتج حلالًا."), key: "entry-scope", sheet: false)
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
            self.app.staticTexts.matching(NSPredicate(format: "label == %@", "يلزم التحقق من المصدر أو السياق")).count == 0
        }
        try reveal(try text(flagged), key: "flagged-heading", sheet: false)
        try capture("flagged-result")
        try audit("flagged-result")
        try readPorkEvidence()
        try readBlock(try text(coverage), key: "coverage", sheet: false)

        let privacy = try button("اقرأ الخصوصية والقيود")
        try reveal(privacy, key: "privacy-action", sheet: false)
        try capture("privacy-action")
        try audit("privacy-action")
        try tap(privacy, "open-privacy")
        try wait("Privacy sheet did not open") { self.app.navigationBars.matching(identifier: "الخصوصية والقيود").count == 1 }
        try capture("privacy-sheet")
        try audit("privacy-sheet")
        for heading in ["وظيفة هذه الشاشة", "معنى النتيجة", "نصك وخصوصيتك", "اللغة ونطاق التغطية"] {
            let section = try text(heading)
            try reveal(section, key: "privacy-" + heading, sheet: true)
            try preparePrivacySection(section, key: "privacy-" + heading)
            let captureNumber = captureIndex + 1
            try capture("privacy-section")
            try auditPreservingViewport(section, key: "privacy-section-" + heading, sheet: true, captureNumber: captureNumber)
        }
        try auditPrivacyLinks()
        try tap(try button("تم"), "close-privacy")
        try wait("Privacy sheet did not dismiss") { self.app.navigationBars.matching(identifier: "الخصوصية والقيود").count == 0 }
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
        let sampleButton = try button("مثال بالإنجليزية: \u{2066}Water, dates, citric acid\u{2069}")
        try reveal(sampleButton, key: "sample", sheet: false)
        try tap(sampleButton, "replace-with-unknown-sample")
        try assertInput(sample)
        try wait("Sample must replace the old outcome with unknown") {
            self.app.staticTexts.matching(NSPredicate(format: "label == %@", self.unknown)).count == 1 &&
            self.app.staticTexts.matching(NSPredicate(format: "label == %@", self.flagged)).count == 0 &&
            self.app.staticTexts.matching(NSPredicate(format: "label == %@", "الكلمات المطابقة")).count == 0
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
            "match_semantics": matchEvidence, "gesture_budgets": gestureBudgets,
            "audit_recoveries": auditRecoveries, "online_link_exposure": linkExposure,
            "geometry_policy": "R7_MEASURED_DISTANCE_AND_SEPARATE_AUDIT_RECOVERY",
            "case_gesture_limit": 168, "status": "CASE_COMPLETED"])
    }

    private func readPorkEvidence() throws {
        let expected: [(key: String, label: String)] = [
            ("matched-name", "كلمات مرتبطة بالخنزير"),
            ("matched-disposition", "كلمة تستدعي الانتباه — تحقّق من الملصق"),
            ("matched-text", "النص المطابق: \u{2066}pork\u{2069}"),
            ("matched-explanation", "تحقّق مما يشير إليه الملصق، واطلب معلومات عن أصل المكوّن من الشركة المصنّعة أو جهة مختصة بمنح شهادات الحلال.")
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
        // Each child keeps continuous reading and exact semantics. Navigation
        // and actual audit-recovery gestures now have independent geometry bounds.
        let start = gestureCount
        let budgetStart = gestureBudgets.count
        for (index, child) in children.enumerated() {
            try check(child.label == expected[index].label, "Match evidence label changed while reading")
            try readBlock(child, key: expected[index].key, sheet: false)
        }
        let matching = gestures.filter { ($0["index"] as! Int) > start }
        matchEvidence["gesture_count"] = gestureCount - start
        matchEvidence["navigation_gesture_count"] = matching.filter { $0["kind"] as? String != "audit-recovery" }.count
        matchEvidence["audit_recovery_gesture_count"] = matching.filter { $0["kind"] as? String == "audit-recovery" }.count
        matchEvidence["budget_ids"] = Array(budgetStart..<gestureBudgets.count)
    }

    private func unique(_ query: XCUIElementQuery, _ label: String) throws -> XCUIElement {
        try wait("Missing or ambiguous " + label) { query.count == 1 }
        return query.element(boundBy: 0)
    }
    private func button(_ label: String) throws -> XCUIElement { try unique(app.buttons.matching(NSPredicate(format: "label == %@", label)), label) }
    private func text(_ label: String) throws -> XCUIElement { try unique(app.staticTexts.matching(NSPredicate(format: "label == %@", label)), label) }
    private func assertInput(_ expected: String) throws {
        try wait("Input does not exactly equal the synthetic expected text") {
            let q = self.app.textViews.matching(NSPredicate(format: "label == %@", "نص المكونات"))
            return q.count == 1 && (q.element(boundBy: 0).value as? String) == expected
        }
    }
    private func noResult() throws {
        try wait("Obsolete outcome or result footer remains") {
            [self.flagged, self.unknown, "يلزم التحقق من المصدر أو السياق", "الكلمات المطابقة", self.coverage].allSatisfy {
                self.app.staticTexts.matching(NSPredicate(format: "label == %@", $0)).count == 0
            } && self.app.buttons.matching(NSPredicate(format: "label == %@", "اقرأ الخصوصية والقيود")).count == 0
        }
    }
    private func content(_ sheet: Bool) throws -> XCUIElement {
        let q = sheet ? app.scrollViews.containing(.staticText, identifier: "وظيفة هذه الشاشة") : app.scrollViews.containing(.button, identifier: "فحص النص")
        return try unique(q, "active content scroll view")
    }
    private func viewport(_ container: XCUIElement, sheet: Bool) throws -> CGRect {
        // iOS also exposes full-frame keyboard/input windows. Identify the
        // unique product window by its actual navigation content, then retain
        // the original full-size, uniqueness and viewport requirements.
        let windows = app.windows.containing(.navigationBar, identifier: sheet ? "الخصوصية والقيود" : "HalalTag")
            .allElementsBoundByIndex.filter { $0.exists && $0.frame == app.frame }
        try check(windows.count == 1, "Expected one actual full-size QA app window")
        let window = windows[0]
        var rect = container.frame.intersection(window.frame)
        let bars = app.navigationBars.matching(identifier: sheet ? "الخصوصية والقيود" : "HalalTag")
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
    // R6b measured up to 9152.5pt of privacy content, 4406.5pt of main
    // content, a 463pt viewport, and a 523pt audit rewind. R7 records every
    // operation's tighter geometry-derived budget and every recovery gesture.
    private func beginBudget(_ kind: String, key: String, frame: CGRect,
                             viewport: CGRect, distance: CGFloat,
                             targetRelativeY: CGFloat? = nil) throws -> Int {
        try check(distance.isFinite && distance >= 0 && viewport.height > 80,
                  "Invalid measured gesture distance: " + key)
        let step = viewport.height * 0.40
        let limit = Int(ceil(distance / step)) + 2
        try check(limit <= 64 && gestureBudgets.count < 100,
                  "Measured operation exceeds the independently bounded geometry policy: " + key)
        let index = gestureBudgets.count
        var value: [String: Any] = ["id": index, "kind": kind, "key": key,
            "initial_frame": rect(frame), "initial_viewport": rect(viewport),
            "distance": Double(distance), "minimum_planned_step": Double(step),
            "limit": limit, "used": 0, "complete": false]
        if let targetRelativeY { value["target_relative_y"] = Double(targetRelativeY) }
        gestureBudgets.append(value)
        return index
    }
    private func finishBudget(_ id: Int) throws {
        try check(id >= 0 && id < gestureBudgets.count, "Unknown gesture budget")
        gestureBudgets[id]["complete"] = true
    }
    private func reveal(_ element: XCUIElement, key: String, sheet: Bool) throws {
        try revealTogether([element], key: key, sheet: sheet)
    }
    private func revealTogether(_ elements: [XCUIElement], key: String, sheet: Bool) throws {
        let scroll = try content(sheet)
        let initialViewport = try viewport(scroll, sheet: sheet)
        try check(!elements.isEmpty && elements.allSatisfy { $0.exists && $0.frame.width > 0 && $0.frame.height > 0 },
                  "Missing control needs investigation: " + key)
        let initialFrame = elements.map(\.frame).dropFirst().reduce(elements[0].frame) { $0.union($1) }
        try check(initialFrame.height <= initialViewport.height && initialFrame.width <= initialViewport.width,
                  "Oversized control/group needs investigation: " + key)
        let distance = max(0, max(initialFrame.maxY - initialViewport.maxY,
                                  initialViewport.minY - initialFrame.minY))
        let budget = try beginBudget("reveal", key: key, frame: initialFrame,
                                     viewport: initialViewport, distance: distance)
        gestureBudgets[budget]["initial_anchor_frame"] = rect(elements[0].frame)
        let limit = gestureBudgets[budget]["limit"] as! Int
        for attempt in 0...limit {
            let visible = try viewport(scroll, sheet: sheet)
            let target = elements.map(\.frame).dropFirst().reduce(elements[0].frame) { $0.union($1) }
            if elements.allSatisfy({ $0.exists && $0.isHittable }) && visible.contains(target) {
                gestureBudgets[budget]["final_frame"] = rect(target)
                gestureBudgets[budget]["final_anchor_frame"] = rect(elements[0].frame)
                gestureBudgets[budget]["final_viewport"] = rect(visible)
                try finishBudget(budget)
                return
            }
            try check(attempt < limit && elements.allSatisfy { $0.exists && $0.frame.width > 0 && $0.frame.height > 0 } &&
                      target.height <= visible.height && target.width <= visible.width,
                      "Control not fully reachable within its measured geometry budget: " + key)
            let error = target.maxY > visible.maxY ? target.maxY - visible.maxY : target.minY - visible.minY
            let direction = error > 0 ? -1.0 : 1.0
            // The observed native drag has a ~10pt touch threshold. Leave a
            // small interior margin; actual containment and progress decide.
            let settlingMargin = min(12, (visible.height - target.height) / 2)
            let travel = min(visible.height * 0.56, abs(error) + settlingMargin + 10)
            try drag(scroll, anchor: elements[0], direction: direction, key: key,
                     sheet: sheet, budget: budget, requestedTravel: travel)
        }
    }
    private func readBlock(_ element: XCUIElement, key: String, sheet: Bool) throws {
        let scroll = try content(sheet)
        let initialViewport = try viewport(scroll, sheet: sheet)
        let initialFrame = element.frame
        try check(element.exists && initialFrame.width > 0 && initialFrame.height > 0,
                  "Missing readable block: " + key)
        let distance = abs(initialFrame.minY - initialViewport.minY) + initialFrame.height
        let budget = try beginBudget("read", key: key, frame: initialFrame,
                                     viewport: initialViewport, distance: distance)
        let limit = gestureBudgets[budget]["limit"] as! Int
        var furthest: CGFloat = 0
        var began = false
        for attempt in 0...limit {
            let visible = try viewport(scroll, sheet: sheet)
            let frame = element.frame
            try check(element.exists && frame.width > 0 && frame.height > 0, "Missing readable block: " + key)
            if !began && (frame.minY < visible.minY || frame.minY >= visible.maxY - 30) {
                try check(attempt < limit, "Text start not reached within its measured geometry budget: " + key)
                let error = frame.minY - (visible.minY + 12)
                try drag(scroll, anchor: element, direction: error > 0 ? -1 : 1,
                         key: key, sheet: sheet, budget: budget,
                         requestedTravel: min(visible.height * 0.56, abs(error) + 10))
                continue
            }
            let intersection = frame.intersection(visible)
            let start = intersection.isNull ? CGFloat.infinity : max(0, intersection.minY - frame.minY)
            let end = intersection.isNull ? -CGFloat.infinity : min(frame.height, intersection.maxY - frame.minY)
            try check(!intersection.isNull && intersection.height > 10 && element.isHittable, "Readable text is not exposed: " + key)
            try check(start <= furthest + 2, "A reveal gesture skipped an unobserved text region: " + key)
            try check(!began || end > furthest + 1, "Reading made no new continuous progress: " + key)
            began = true
            furthest = max(furthest, end)
            let captureNumber = captureIndex + 1
            try capture(key)
            readCoverage.append(["key": key, "capture_index": captureNumber,
                "budget_id": budget, "start": Double(start), "end": Double(end),
                "height": Double(frame.height), "frame": rect(frame), "viewport": rect(visible)])
            try auditPreservingViewport(element, key: key, sheet: sheet, captureNumber: captureNumber)
            // Recovery is complete before returning even when the whole text
            // was visible. A later child never inherits an audit's scroll rewind.
            if furthest >= frame.height - 2 {
                try finishBudget(budget)
                return
            }
            try check(attempt < limit, "Text not covered within its measured geometry budget: " + key)
            let restoredViewport = try viewport(scroll, sheet: sheet)
            let nextUnreadY = element.frame.minY + furthest
            let travel = min(restoredViewport.height * 0.56,
                             max(12, nextUnreadY - (restoredViewport.minY + restoredViewport.height * 0.35)) + 10)
            try drag(scroll, anchor: element, direction: -1, key: key, sheet: sheet,
                     budget: budget, requestedTravel: travel)
        }
    }
    private func auditPreservingViewport(_ element: XCUIElement, key: String,
                                        sheet: Bool, captureNumber: Int) throws {
        let scroll = try content(sheet)
        let before = element.frame
        let beforeViewport = try viewport(scroll, sheet: sheet)
        // This call remains combined and unfiltered. A failed audit throws;
        // it is never caught, retried, or turned into a passing receipt.
        try audit(key)
        let after = element.frame
        let afterViewport = try viewport(scroll, sheet: sheet)
        try check(element.exists && abs(after.width - before.width) <= 2 && abs(after.height - before.height) <= 2 &&
                  abs(afterViewport.width - beforeViewport.width) <= 2 && abs(afterViewport.height - beforeViewport.height) <= 2,
                  "Audit did not restore the readable block's actual geometry: " + key)
        let targetRelativeY = before.minY - beforeViewport.minY
        let displacement = (after.minY - afterViewport.minY) - targetRelativeY
        let budget = try beginBudget("audit-recovery", key: key, frame: after,
            viewport: afterViewport, distance: abs(displacement), targetRelativeY: targetRelativeY)
        let limit = gestureBudgets[budget]["limit"] as! Int
        var restored = false
        for attempt in 0...limit {
            let visible = try viewport(scroll, sheet: sheet)
            let current = element.frame
            try check(element.exists && abs(current.width - before.width) <= 2 && abs(current.height - before.height) <= 2 &&
                      abs(visible.width - beforeViewport.width) <= 2 && abs(visible.height - beforeViewport.height) <= 2,
                      "Actual geometry changed during audit recovery: " + key)
            let error = (current.minY - visible.minY) - targetRelativeY
            if abs(error) <= 2 { restored = true; break }
            try check(attempt < limit, "Audit-displaced interval was not restored within its measured recovery budget: " + key)
            try drag(scroll, anchor: element, direction: error > 0 ? -1 : 1,
                     key: key, sheet: sheet, budget: budget,
                     requestedTravel: min(visible.height * 0.56, abs(error) + 10))
            let resultingViewport = try viewport(scroll, sheet: sheet)
            let remaining = abs((element.frame.minY - resultingViewport.minY) - targetRelativeY)
            try check(remaining <= 2 || remaining < abs(error) - 1,
                      "Audit recovery did not approach the previously exposed interval: " + key)
        }
        try check(restored, "Prior visible interval was not restored: " + key)
        try finishBudget(budget)
        let finalViewport = try viewport(scroll, sheet: sheet)
        let record: [String: Any] = ["key": key, "audit_index": audits.count,
            "capture_index": captureNumber, "budget_id": budget,
            "before_frame": rect(before), "before_viewport": rect(beforeViewport),
            "after_frame": rect(after), "after_viewport": rect(afterViewport),
            "restored_frame": rect(element.frame), "restored_viewport": rect(finalViewport),
            "displacement": Double(displacement), "restored": true]
        auditRecoveries.append(record)
        try attachJSON("Appearance audit viewport recovery", record)
    }
    private func privacyLinks() throws -> [XCUIElement] {
        try ["اقرأ سياسة الخصوصية عبر الإنترنت", "افتح تعليمات الدعم"].map {
            try unique(app.links.matching(NSPredicate(format: "label == %@", $0)), $0)
        }
    }
    private func preparePrivacySection(_ heading: XCUIElement, key: String) throws {
        let scroll = try content(true)
        let visible = try viewport(scroll, sheet: true)
        let links = try privacyLinks()
        // The R6b link was 7pt outside the real scroll viewport. If a link
        // intersects this section's pose, expose both links and the original
        // heading together before the same audit, only when their union fits.
        if links.contains(where: { $0.frame.intersects(visible) && !visible.contains($0.frame) }) {
            try revealTogether([heading] + links, key: key + "-nearby-links", sheet: true)
        }
        try check((try viewport(scroll, sheet: true)).contains(heading.frame) && heading.isHittable,
                  "Original privacy heading lost its fully visible audit pose: " + key)
    }
    private func auditPrivacyLinks() throws {
        let links = try privacyLinks()
        for (index, link) in links.enumerated() {
            let key = index == 0 ? "privacy-online-link" : "support-online-link"
            let initialViewport = try viewport(try content(true), sheet: true)
            let pair = links[0].frame.union(links[1].frame)
            if pair.height <= initialViewport.height {
                try revealTogether(links, key: key, sheet: true)
            } else {
                try reveal(link, key: key, sheet: true)
            }
            let visible = try viewport(try content(true), sheet: true)
            try check(link.exists && link.elementType == .link && link.isHittable && visible.contains(link.frame),
                      "Online link is not fully exposed inside the real scroll viewport: " + key)
            let captureNumber = captureIndex + 1
            try capture(key)
            linkExposure.append(["key": key, "label": link.label, "element_type": "link",
                "frame": rect(link.frame), "viewport": rect(visible), "capture_index": captureNumber])
            try auditPreservingViewport(link, key: key, sheet: true, captureNumber: captureNumber)
        }
    }
    private func drag(_ scroll: XCUIElement, anchor: XCUIElement, direction: Double, key: String,
                      sheet: Bool, budget: Int, requestedTravel: CGFloat) throws {
        try check(gestureCount < 168, "The independently bounded 168-gesture R7 case ceiling was exhausted")
        try check(budget >= 0 && budget < gestureBudgets.count,
                  "Gesture lacks its measured operation budget: " + key)
        let used = gestureBudgets[budget]["used"] as! Int
        let limit = gestureBudgets[budget]["limit"] as! Int
        try check(used < limit && gestureBudgets[budget]["complete"] as? Bool == false,
                  "Measured operation budget exhausted: " + key)
        let visible = try viewport(scroll, sheet: sheet)
        let before = anchor.frame
        let contentFrames = (scroll.staticTexts.allElementsBoundByIndex +
                             scroll.buttons.allElementsBoundByIndex +
                             scroll.links.allElementsBoundByIndex +
                             scroll.textViews.allElementsBoundByIndex).map(\.frame)
            .filter { $0.width > 0 && $0.height > 0 && $0.intersects(visible) }
        try check(!contentFrames.isEmpty, "No measured content margin for gesture: " + key)
        let gutterLeft = visible.minX + 2
        let gutterRight = (contentFrames.map(\.minX).min() ?? visible.minX) - 2
        try check(gutterRight - gutterLeft >= 4, "No safe measured left gutter: " + key)
        let x = (gutterLeft + gutterRight) / 2
        let travel = min(visible.height * 0.56, max(12, requestedTravel))
        let startY = direction < 0 ? visible.minY + visible.height * 0.78 : visible.minY + visible.height * 0.22
        let endY = startY + CGFloat(direction) * travel
        let route = CGRect(x: x - 2, y: min(startY, endY), width: 4, height: travel)
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
            "budget_id": budget, "route": rect(route), "gutter_left": Double(gutterLeft),
            "gutter_right": Double(gutterRight), "editor_frames": editorFrames.map { rect($0) },
            "indicator_frames": indicatorFrames.map { rect($0) }])
        let origin = scroll.coordinate(withNormalizedOffset: .zero)
        let start = origin.withOffset(CGVector(dx: x - scroll.frame.minX, dy: startY - scroll.frame.minY))
        let end = origin.withOffset(CGVector(dx: x - scroll.frame.minX, dy: endY - scroll.frame.minY))
        let beforeCapture = captureIndex + 1
        try capture("before-gesture")
        start.press(forDuration: 0.1, thenDragTo: end, withVelocity: .slow, thenHoldForDuration: 0.2)
        try wait("Content gesture made no progress in the requested direction: " + key) {
            direction * Double(anchor.frame.minY - before.minY) > 1
        }
        gestureCount += 1
        gestureBudgets[budget]["used"] = used + 1
        let event: [String: Any] = ["index": gestureCount, "key": key, "direction": direction,
            "budget_id": budget, "budget_step": used + 1, "kind": gestureBudgets[budget]["kind"]!,
            "before": rect(before), "after": rect(anchor.frame), "viewport": rect(visible),
            "requested_travel": Double(travel), "route": rect(route),
            "editor_frames": editorFrames.map { rect($0) },
            "indicator_frames": indicatorFrames.map { rect($0) },
            "before_capture_index": beforeCapture,
            "after_capture_index": captureIndex + 1]
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
        XCTAssertLessThanOrEqual(captureIndex, 400, "Bounded R7 capture budget exceeded")
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

