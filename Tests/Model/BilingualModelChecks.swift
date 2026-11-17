import Foundation

/// Compile with the exact candidate IngredientScreening.swift and
/// ScreeningLocalization.swift. This has NOT been executed in the cloud.
@main
struct BilingualModelChecks {
    enum Failure: Error { case assertion(String) }
    static func main() throws {
        var passed: [String] = []
        func expect(_ condition: @autoclosure () -> Bool, _ label: String) throws {
            guard condition() else { throw Failure.assertion(label) }
            passed.append(label)
        }
        try expect(ScreeningLanguage.resolve(storedValue: "ar", preferredLanguages: ["en-US"]) == .arabic, "Stored Arabic overrides English device language")
        try expect(ScreeningLanguage.resolve(storedValue: "en", preferredLanguages: ["ar-SA"]) == .english, "Stored English overrides Arabic device language")
        try expect(ScreeningLanguage.resolve(storedValue: "", preferredLanguages: ["ar-SA"]) == .arabic, "Initial Arabic regional locale")
        try expect(ScreeningLanguage.resolve(storedValue: "invalid", preferredLanguages: ["fr-FR", "ar_SA"]) == .arabic, "Corrupt preference falls back to first supported locale")
        try expect(ScreeningLanguage.resolve(storedValue: "invalid", preferredLanguages: ["fr-FR"]) == .english, "Unsupported-only locale falls back to English")
        try expect(ScreeningLanguage.resolve(storedValue: "", preferredLanguages: []) == .english, "Empty locale list is deterministic")
        try expect(ScreeningLanguage.inputIsRightToLeft("ماء، E471", fallback: .english), "Arabic mixed-script draft direction")
        try expect(!ScreeningLanguage.inputIsRightToLeft("E471, ماء", fallback: .arabic), "English-first mixed draft remains LTR")
        try expect(ScreeningLanguage.inputIsRightToLeft("123", fallback: .arabic), "Number-only draft uses selected UI direction")
        try expect(!ScreeningLanguage.inputIsRightToLeft("", fallback: .english), "Empty English draft remains LTR")

        let english = ScreeningCopy(language: .english)
        let arabic = ScreeningCopy(language: .arabic)
        for key in ScreeningCopyKey.allCases {
            let en = english(key), ar = arabic(key)
            try expect(!en.isEmpty && !ar.isEmpty && en != ar, "Nonempty bilingual copy: \(key)")
            try expect(ar.unicodeScalars.contains { (0x0600...0x06FF).contains($0.value) }, "Arabic script present: \(key)")
        }
        for outcome in [ScreeningOutcome.flaggedTerms, .sourceDependent, .unknown] {
            try expect(english.outcomeTitle(outcome) == outcome.title, "Existing English title preserved: \(outcome)")
            try expect(english.outcomeSummary(outcome) == outcome.summary, "Existing English summary preserved: \(outcome)")
        }
        for disposition in [ScreeningMatchDisposition.flaggedTerm, .sourceDependent, .contextReview] {
            try expect(english.dispositionTitle(disposition) == disposition.title, "Existing English disposition preserved: \(disposition)")
        }
        try expect(english(.coverage) == IngredientScreening.coverageNotice, "Existing coverage assertion preserved verbatim")
        let all = IngredientScreening.analyze("alcohol, pork, carmine, gelatin, E471, enzymes, vanilla extract")
        let knownIDs: Set<String> = ["alcohol", "pork", "e120", "gelatin", "e471", "enzymes", "vanilla"]
        try expect(Set(all.matches.map(\.id)) == knownIDs, "All seven existing rule groups are covered by localization")
        for match in all.matches {
            try expect(english.matchName(match) == match.name, "Existing English rule name: \(match.id)")
            try expect(english.matchExplanation(match) == match.explanation, "Existing English explanation: \(match.id)")
            try expect(arabic.matchName(match) != match.name, "Arabic rule name: \(match.id)")
            try expect(arabic.matchExplanation(match) != match.explanation, "Arabic explanation: \(match.id)")
        }
        let contextual = IngredientScreening.analyze("no pork, alcohol-free, gelatin-free")
        try expect(contextual.matches.allSatisfy { $0.disposition == .contextReview }, "Existing qualified claims remain context review")
        for match in contextual.matches {
            try expect(arabic.matchExplanation(match).hasSuffix(arabic(.contextNote)), "Arabic context caveat retained: \(match.id)")
        }
        try expect(IngredientScreening.analyze("no pork, pork").outcome == .flaggedTerms, "Contextual occurrence cannot suppress a direct term")
        try expect(IngredientScreening.analyze("chamomile, monosodium glutamate").outcome == .unknown, "No broad substring false positives")
        try expect(IngredientScreening.analyze("pork، gelatin").matches.count == 2, "Arabic separator preserves existing English matches")
        for input in ["جيلاتين", "الكارمين", "خنزير", "حلال", "ماء، تمر", "E١٢٠", "إي١٢٠"] {
            try expect(IngredientScreening.analyze(input).outcome == .unknown, "Unsupported Arabic input stays unknown: \(input)")
        }
        try expect(IngredientScreening.analyze("ماء، E471").outcome == .sourceDependent, "ASCII E471 match does not certify mixed Arabic text")
        try expect(arabic.matchedText(["e471"]) == "النص المطابق: \u{2066}e471\u{2069}", "Latin evidence remains ordered in RTL output")
        for sample in ["Gelatin, sugar, natural flavors", "Water, dates, citric acid", "Ethanol, vanilla extract, color E120"] {
            try expect(english.sampleLabel(sample) == sample, "English sample unchanged: \(sample)")
            try expect(arabic.sampleLabel(sample).contains("\u{2066}" + sample + "\u{2069}"), "Arabic sample preview contains exact inserted English text")
        }
        var session = IngredientScreeningSession(input: "pork, E471")
        session.screen()
        let snapshot = session.currentResult
        if let result = snapshot {
            _ = arabic.outcomeTitle(result.outcome)
            _ = english.outcomeTitle(result.outcome)
        }
        try expect(session.currentResult == snapshot && session.input == "pork, E471", "Presentation access does not mutate the draft or result")
        session.input += " "
        try expect(session.currentResult == nil, "Editing still invalidates prior result")
        session.input = "pork, E471"
        try expect(session.currentResult == nil, "Restoring old text does not revive a stale result")
        session.screen(); session.clear()
        try expect(session.input.isEmpty && session.currentResult == nil, "Clear still removes text and result")
        try expect(IngredientScreeningSession().currentResult == nil, "A new in-memory session has no stored result")
        let evidence: [String: Any] = ["status": "PASS", "check_count": passed.count, "checks": passed,
            "scope": "Model/presentation checks only; not UI, persistence, accessibility, native archive or release acceptance."]
        let data = try JSONSerialization.data(withJSONObject: evidence, options: [.sortedKeys, .prettyPrinted])
        print(String(decoding: data, as: UTF8.self))
    }
}
