import Foundation

/// Text screening only. No outcome establishes a product's halal status.
enum ScreeningOutcome: Equatable {
    case flaggedTerms
    case sourceDependent
    case unknown

    var title: String {
        switch self {
        case .flaggedTerms: return "Flagged terms found"
        case .sourceDependent: return "Source or context needs review"
        case .unknown: return "No supported match — status unknown"
        }
    }

    var summary: String {
        switch self {
        case .flaggedTerms:
            return "This text includes words in the limited flagged list. A word match cannot establish ingredient presence or halal status. Check the original label and ingredient source."
        case .sourceDependent:
            return "The matched terms need source or context checks. This app cannot verify label claims, processing, or certification."
        case .unknown:
            return "No supported terms were matched. Unrecognised ingredients, spellings, and languages may be missed. No conclusion about the product can be drawn."
        }
    }
}

enum ScreeningMatchDisposition: Equatable {
    case flaggedTerm
    case sourceDependent
    case contextReview

    var title: String {
        switch self {
        case .flaggedTerm: return "Flagged term — verify the label"
        case .sourceDependent: return "Source-dependent — verify the origin"
        case .contextReview: return "Label context — claim not verified"
        }
    }
}

struct IngredientScreeningMatch: Identifiable, Equatable {
    let id: String
    let name: String
    let disposition: ScreeningMatchDisposition
    let terms: [String]
    let explanation: String
}

struct IngredientScreeningResult: Equatable {
    /// Exact input snapshot, retained only in memory for the current screen.
    let input: String
    let matches: [IngredientScreeningMatch]

    var outcome: ScreeningOutcome {
        if matches.contains(where: { $0.disposition == .flaggedTerm }) {
            return .flaggedTerms
        }
        return matches.isEmpty ? .unknown : .sourceDependent
    }
}

/// Editing always invalidates a prior result, even if the user later restores
/// the old text. Selecting a sample sets its input before screening it.
struct IngredientScreeningSession {
    var input: String {
        didSet {
            if !input.utf8.elementsEqual(oldValue.utf8) { result = nil }
        }
    }
    private(set) var result: IngredientScreeningResult?

    init(input: String = "") {
        self.input = input
        self.result = nil
    }

    var currentResult: IngredientScreeningResult? {
        guard let result, result.input.utf8.elementsEqual(input.utf8) else { return nil }
        return result
    }

    mutating func screen() {
        guard !input.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty else {
            result = nil
            return
        }
        result = IngredientScreening.analyze(input)
    }

    mutating func useSample(_ text: String) {
        input = text
        screen()
    }

    mutating func clear() {
        input = ""
        result = nil
    }
}

enum IngredientScreening {
    static let coverageNotice = "Coverage is limited to a small English term list and E120/E471 formats. Other languages, ingredients, synonyms, and complex label claims may not be recognised. Unmatched text does not establish halal status."

    static func analyze(_ text: String) -> IngredientScreeningResult {
        let normalized = text.folding(
            options: [.caseInsensitive, .diacriticInsensitive],
            locale: Locale(identifier: "en_US_POSIX")
        )
        // Keep ingredient separators so phrases cannot span separate entries.
        let ingredientSeparators = CharacterSet(charactersIn: ",;•،؛").union(.newlines)
        let segments = normalized.components(separatedBy: ingredientSeparators)
            .map { $0.components(separatedBy: CharacterSet.alphanumerics.inverted).filter { !$0.isEmpty } }

        let matches = rules.compactMap { rule -> IngredientScreeningMatch? in
            var terms: [String] = []
            var hasDirectOccurrence = false
            var hasContextOccurrence = false

            for tokens in segments {
                for phrase in rule.phrases where tokens.count >= phrase.count {
                    for start in 0...(tokens.count - phrase.count) {
                        let end = start + phrase.count
                        guard tokens[start..<end].elementsEqual(phrase) else { continue }
                        let term = phrase.joined(separator: " ")
                        if !terms.contains(term) { terms.append(term) }
                        if needsContextReview(tokens: tokens, range: start..<end) {
                            hasContextOccurrence = true
                        } else {
                            hasDirectOccurrence = true
                        }
                    }
                }
            }

            guard !terms.isEmpty else { return nil }
            // A contextual occurrence must not suppress a separate direct match.
            let disposition: ScreeningMatchDisposition = hasDirectOccurrence ? rule.disposition : .contextReview
            let contextNote = hasContextOccurrence
                ? " A nearby qualifier or label claim also needs review; it is not verified by this app."
                : ""
            return IngredientScreeningMatch(
                id: rule.id,
                name: rule.name,
                disposition: disposition,
                terms: terms,
                explanation: rule.explanation + contextNote
            )
        }

        return IngredientScreeningResult(input: text, matches: matches)
    }

    /// Recognise a few common qualifiers only to withhold a direct flag. This
    /// is not a general negation parser and never proves absence or safety.
    private static func needsContextReview(tokens: [String], range: Range<Int>) -> Bool {
        let start = range.lowerBound
        let end = range.upperBound

        if end < tokens.count, tokens[end] == "free" { return true }
        if start > 0 {
            let previous = tokens[start - 1]
            if ["no", "without", "non"].contains(previous) { return true }
            if tokens[start] == "alcohol", ["sugar", "fatty"].contains(previous) { return true }
        }
        if start >= 2 {
            let first = tokens[start - 2]
            let second = tokens[start - 1]
            if first == "no", second == "added" { return true }
            if first == "free", ["from", "of"].contains(second) { return true }
        }
        return false
    }

    private struct Rule {
        let id: String
        let name: String
        let phrases: [[String]]
        let disposition: ScreeningMatchDisposition
        let explanation: String
    }

    // Deliberately small, explicit coverage. No broad substring such as "ham"
    // inside "chamomile", or "mono" inside "monosodium", is accepted.
    private static let rules: [Rule] = [
        Rule(id: "alcohol", name: "Alcohol-related terms",
             phrases: [["alcohol"], ["ethanol"], ["beer"], ["wine"], ["rum"]],
             disposition: .flaggedTerm,
             explanation: "The word alone does not establish the substance, concentration, processing, or presence in the final product."),
        Rule(id: "pork", name: "Pork-related terms",
             phrases: [["pork"], ["porcine"], ["lard"], ["bacon"], ["ham"]],
             disposition: .flaggedTerm,
             explanation: "Verify what the label refers to and obtain ingredient-origin information from the manufacturer or a qualified certifier."),
        Rule(id: "e120", name: "Carmine / E120",
             phrases: [["carmine"], ["cochineal"], ["e120"], ["e", "120"]],
             disposition: .sourceDependent,
             explanation: "This term or identifier does not supply the product's sourcing, processing, or certification details."),
        Rule(id: "gelatin", name: "Gelatin",
             phrases: [["gelatin"], ["gelatine"]],
             disposition: .sourceDependent,
             explanation: "The term alone does not identify the origin, processing, or certification of this ingredient."),
        Rule(id: "e471", name: "Mono- and diglycerides / E471",
             phrases: [["e471"], ["e", "471"], ["monoglyceride"], ["monoglycerides"], ["diglyceride"], ["diglycerides"]],
             disposition: .sourceDependent,
             explanation: "The name or identifier alone does not establish the ingredient source or certification."),
        Rule(id: "enzymes", name: "Enzymes / rennet",
             phrases: [["enzyme"], ["enzymes"], ["rennet"]],
             disposition: .sourceDependent,
             explanation: "Ask for the specific enzyme, its origin, processing, and any applicable certification."),
        Rule(id: "vanilla", name: "Vanilla extract",
             phrases: [["vanilla", "extract"]],
             disposition: .sourceDependent,
             explanation: "The phrase does not establish the extraction process or the final product's composition or certification.")
    ]
}
