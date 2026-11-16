import SwiftUI

struct ContentView: View {
    @State private var session = IngredientScreeningSession()
    @State private var showingLimitations = false

    private let samples = [
        "Gelatin, sugar, natural flavors",
        "Water, dates, citric acid",
        "Ethanol, vanilla extract, color E120"
    ]

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: 22) {
                    header
                    inputSection
                    sampleSection

                    if let result = session.currentResult {
                        resultSection(result)
                    }
                }
                .padding(20)
            }
            .background(Color(.systemGroupedBackground))
            .navigationTitle("Halal Analyzer")
            .toolbar {
                ToolbarItem(placement: .topBarLeading) {
                    Button {
                        showingLimitations = true
                    } label: {
                        Label("Privacy and limitations", systemImage: "info.circle")
                    }
                    .accessibilityLabel("Privacy and limitations")
                }

                ToolbarItem(placement: .topBarTrailing) {
                    Button("Clear") {
                        session.clear()
                    }
                    .disabled(session.input.isEmpty && session.currentResult == nil)
                }
            }
            .sheet(isPresented: $showingLimitations) {
                ScreeningInformationView()
            }
        }
    }

    private var header: some View {
        VStack(alignment: .leading, spacing: 8) {
            Label("Ingredient screening", systemImage: "text.magnifyingglass")
                .font(.title.bold())

            Text("Match a small set of English ingredient terms. Results identify words to check; they do not determine halal status.")
                .font(.subheadline)
                .foregroundStyle(.secondary)
        }
    }

    private var inputSection: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text("Ingredients")
                .font(.headline)

            TextEditor(text: $session.input)
                .frame(minHeight: 150)
                .padding(10)
                .scrollContentBackground(.hidden)
                .background(.background, in: RoundedRectangle(cornerRadius: 8))
                .overlay {
                    RoundedRectangle(cornerRadius: 8)
                        .stroke(Color(.separator), lineWidth: 0.5)
                }
                .overlay(alignment: .topLeading) {
                    if session.input.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty {
                        Text("Example: gelatin, whey, E471, vanilla extract...")
                            .foregroundStyle(.tertiary)
                            .padding(.horizontal, 16)
                            .padding(.vertical, 18)
                            .allowsHitTesting(false)
                            .accessibilityHidden(true)
                    }
                }
                .accessibilityLabel("Ingredient text")
                .accessibilityHint("Type or paste English ingredient text, then activate Screen text. Editing clears the previous result.")

            Button {
                session.screen()
            } label: {
                Label("Screen text", systemImage: "magnifyingglass")
                    .frame(maxWidth: .infinity)
            }
            .buttonStyle(.borderedProminent)
            .disabled(session.input.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty)

            Text("Changing the text clears the result. No result is a halal certificate.")
                .font(.footnote)
                .foregroundStyle(.secondary)
        }
    }

    private var sampleSection: some View {
        VStack(alignment: .leading, spacing: 10) {
            Text("Try sample text")
                .font(.headline)

            ForEach(samples, id: \.self) { sample in
                Button {
                    session.useSample(sample)
                } label: {
                    HStack {
                        Text(sample)
                            .font(.subheadline)
                            .foregroundStyle(.primary)
                            .multilineTextAlignment(.leading)
                        Spacer()
                        Image(systemName: "chevron.right")
                            .font(.caption.weight(.semibold))
                            .foregroundStyle(.secondary)
                            .accessibilityHidden(true)
                    }
                    .padding(12)
                    .background(.background, in: RoundedRectangle(cornerRadius: 8))
                }
                .buttonStyle(.plain)
                .accessibilityHint("Replaces the text and screens this sample.")
            }
        }
    }

    private func resultSection(_ result: IngredientScreeningResult) -> some View {
        VStack(alignment: .leading, spacing: 14) {
            Label(result.outcome.title, systemImage: result.outcome.symbol)
                .font(.title3.bold())
                .foregroundStyle(result.outcome.color)
                .accessibilityAddTraits(.isHeader)

            Text(result.outcome.summary)
                .font(.subheadline)

            if !result.matches.isEmpty {
                VStack(alignment: .leading, spacing: 10) {
                    Text("Matched terms")
                        .font(.headline)
                        .accessibilityAddTraits(.isHeader)

                    ForEach(result.matches) { match in
                        VStack(alignment: .leading, spacing: 5) {
                            Text(match.name)
                                .font(.subheadline.weight(.semibold))
                            Text(match.disposition.title)
                                .font(.subheadline)
                            Text("Matched text: \(match.terms.joined(separator: ", "))")
                                .font(.footnote)
                            Text(match.explanation)
                                .font(.footnote)
                                .foregroundStyle(.secondary)
                        }
                        .frame(maxWidth: .infinity, alignment: .leading)
                        .padding(12)
                        .background(Color(.secondarySystemGroupedBackground), in: RoundedRectangle(cornerRadius: 8))
                        .accessibilityElement(children: .combine)
                    }
                }
            }

            Text(IngredientScreening.coverageNotice)
                .font(.footnote)
                .foregroundStyle(.secondary)

            Button("Read privacy and limitations") {
                showingLimitations = true
            }
        }
        .padding(16)
        .background(.background, in: RoundedRectangle(cornerRadius: 8))
    }
}

private extension ScreeningOutcome {
    var symbol: String {
        switch self {
        case .flaggedTerms: return "exclamationmark.triangle"
        case .sourceDependent: return "questionmark.circle"
        case .unknown: return "text.magnifyingglass"
        }
    }

    var color: Color {
        switch self {
        case .flaggedTerms, .sourceDependent: return .primary
        case .unknown: return .secondary
        }
    }
}

private struct ScreeningInformationView: View {
    @Environment(\.dismiss) private var dismiss

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: 24) {
                    section("What this screen does", text: "It matches a limited set of English ingredient words and E120/E471 formats in text you choose to type or paste. It has no camera, OCR, barcode scanning, trained AI model, or remote screening service.")
                    section("What a result means", text: "A match only shows that a term appeared. It does not establish ingredient presence, origin, processing, cross-contamination, or halal status. Simple statements such as alcohol-free are marked for context review; this app cannot verify such claims. Unmatched text remains unknown. Check the original label and ask the manufacturer or a qualified certifier when needed.")
                    section("Your text and privacy", text: "This app screens text on your device and keeps the current text and result in memory. It does not save or transmit them, include analytics, or request camera, photos, microphone, or location permissions. Clear removes the current text and result. Your keyboard and other iOS services remain subject to your device settings.")
                    section("Language and coverage", text: IngredientScreening.coverageNotice)
                }
                .frame(maxWidth: .infinity, alignment: .leading)
                .padding(20)
            }
            .navigationTitle("Privacy & limitations")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .confirmationAction) {
                    Button("Done") { dismiss() }
                }
            }
        }
    }

    private func section(_ title: String, text: String) -> some View {
        VStack(alignment: .leading, spacing: 8) {
            Text(title)
                .font(.headline)
                .accessibilityAddTraits(.isHeader)
            Text(text)
                .font(.body)
        }
    }
}

#Preview {
    ContentView()
}
