//
//  ContentView.swift
//  HalalAnalyzer حلال ام حرام؟
//
//  Created by saleh alayed on 10/12/1447 AH.
//

import SwiftUI

struct ContentView: View {
    @State private var ingredientText = ""
    @State private var analysis: AnalysisResult?

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

                    if let analysis {
                        resultSection(analysis)
                    }
                }
                .padding(20)
            }
            .background(Color(.systemGroupedBackground))
            .navigationTitle("Halal Analyzer")
            .toolbar {
                ToolbarItem(placement: .topBarTrailing) {
                    Button("Clear") {
                        ingredientText = ""
                        analysis = nil
                    }
                    .disabled(ingredientText.isEmpty && analysis == nil)
                }
            }
        }
    }

    private var header: some View {
        VStack(alignment: .leading, spacing: 8) {
            Label("حلال ام حرام؟", systemImage: "checkmark.seal.fill")
                .font(.title.bold())
                .foregroundStyle(.green)

            Text("Paste ingredients or additives to get a quick local screening. Ambiguous items are marked for review.")
                .font(.subheadline)
                .foregroundStyle(.secondary)
        }
    }

    private var inputSection: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text("Ingredients")
                .font(.headline)

            TextEditor(text: $ingredientText)
                .frame(minHeight: 150)
                .padding(10)
                .scrollContentBackground(.hidden)
                .background(.background, in: RoundedRectangle(cornerRadius: 8))
                .overlay {
                    RoundedRectangle(cornerRadius: 8)
                        .stroke(Color(.separator), lineWidth: 0.5)
                }
                .overlay(alignment: .topLeading) {
                    if ingredientText.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty {
                        Text("Example: gelatin, whey, E471, vanilla extract...")
                            .foregroundStyle(.tertiary)
                            .padding(.horizontal, 16)
                            .padding(.vertical, 18)
                            .allowsHitTesting(false)
                    }
                }

            Button {
                analysis = IngredientAnalyzer.analyze(ingredientText)
            } label: {
                Label("Analyze", systemImage: "magnifyingglass")
                    .frame(maxWidth: .infinity)
            }
            .buttonStyle(.borderedProminent)
            .disabled(ingredientText.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty)
        }
    }

    private var sampleSection: some View {
        VStack(alignment: .leading, spacing: 10) {
            Text("Samples")
                .font(.headline)

            ForEach(samples, id: \.self) { sample in
                Button {
                    ingredientText = sample
                    analysis = IngredientAnalyzer.analyze(sample)
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
                    }
                    .padding(12)
                    .background(.background, in: RoundedRectangle(cornerRadius: 8))
                }
                .buttonStyle(.plain)
            }
        }
    }

    private func resultSection(_ result: AnalysisResult) -> some View {
        VStack(alignment: .leading, spacing: 14) {
            Label(result.title, systemImage: result.icon)
                .font(.title3.bold())
                .foregroundStyle(result.color)

            Text(result.summary)
                .font(.subheadline)
                .foregroundStyle(.secondary)

            if !result.matches.isEmpty {
                VStack(alignment: .leading, spacing: 8) {
                    Text("Matched items")
                        .font(.headline)

                    ForEach(result.matches) { match in
                        VStack(alignment: .leading, spacing: 4) {
                            Text(match.name)
                                .font(.subheadline.weight(.semibold))
                            Text(match.reason)
                                .font(.caption)
                                .foregroundStyle(.secondary)
                        }
                        .frame(maxWidth: .infinity, alignment: .leading)
                        .padding(10)
                        .background(result.color.opacity(0.1), in: RoundedRectangle(cornerRadius: 8))
                    }
                }
            }
        }
        .padding(16)
        .background(.background, in: RoundedRectangle(cornerRadius: 8))
    }
}

private enum IngredientAnalyzer {
    static func analyze(_ text: String) -> AnalysisResult {
        let normalizedText = text.folding(options: [.caseInsensitive, .diacriticInsensitive], locale: .current)
        let matches = rules.filter { rule in
            rule.keywords.contains { normalizedText.localizedCaseInsensitiveContains($0) }
        }

        if matches.contains(where: { $0.status == .haram }) {
            return AnalysisResult(
                status: .haram,
                matches: matches,
                summary: "This list contains ingredients commonly considered haram. Check the product source and certification before consuming."
            )
        }

        if matches.contains(where: { $0.status == .review }) {
            return AnalysisResult(
                status: .review,
                matches: matches,
                summary: "No clearly haram item was found, but some ingredients depend on source or processing method."
            )
        }

        return AnalysisResult(
            status: .halal,
            matches: matches,
            summary: "No flagged ingredients were detected in this basic screening. Certification is still the best confirmation."
        )
    }

    private static let rules: [IngredientRule] = [
        IngredientRule(name: "Alcohol / Ethanol", keywords: ["alcohol", "ethanol", "beer", "wine", "rum"], status: .haram, reason: "Intoxicating alcohol is not halal."),
        IngredientRule(name: "Pork", keywords: ["pork", "porcine", "lard", "bacon", "ham"], status: .haram, reason: "Pig-derived ingredients are haram."),
        IngredientRule(name: "Carmine / E120", keywords: ["carmine", "cochineal", "e120"], status: .review, reason: "This coloring is debated and may require scholar or certification guidance."),
        IngredientRule(name: "Gelatin", keywords: ["gelatin", "gelatine"], status: .review, reason: "Gelatin can be halal, beef, fish, or pork-derived depending on source."),
        IngredientRule(name: "Mono- and Diglycerides / E471", keywords: ["e471", "mono", "diglycerides"], status: .review, reason: "These emulsifiers can come from plant or animal fat."),
        IngredientRule(name: "Enzymes", keywords: ["enzyme", "rennet"], status: .review, reason: "Enzymes may be microbial, plant-based, or animal-derived."),
        IngredientRule(name: "Vanilla Extract", keywords: ["vanilla extract"], status: .review, reason: "Some extracts use alcohol as a solvent.")
    ]
}

private struct IngredientRule: Identifiable {
    let id = UUID()
    let name: String
    let keywords: [String]
    let status: AnalysisStatus
    let reason: String
}

private struct AnalysisResult {
    let status: AnalysisStatus
    let matches: [IngredientRule]
    let summary: String

    var title: String {
        switch status {
        case .halal:
            return "Looks Halal"
        case .review:
            return "Needs Review"
        case .haram:
            return "Likely Haram"
        }
    }

    var icon: String {
        switch status {
        case .halal:
            return "checkmark.circle.fill"
        case .review:
            return "questionmark.circle.fill"
        case .haram:
            return "xmark.octagon.fill"
        }
    }

    var color: Color {
        switch status {
        case .halal:
            return .green
        case .review:
            return .orange
        case .haram:
            return .red
        }
    }
}

private enum AnalysisStatus {
    case halal
    case review
    case haram
}

#Preview {
    ContentView()
}
