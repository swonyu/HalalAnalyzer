import SwiftUI
import UIKit

struct ContentView: View {
    @AppStorage(ScreeningLanguage.preferenceKey) private var storedLanguage = ""
    @State private var session = IngredientScreeningSession()
    @State private var showingLimitations = false
    @FocusState private var ingredientEditorFocused: Bool
    @State private var softwareKeyboardVisible = false
    @State private var pendingScreenReveal = false
    @State private var readingAnchor: ScreeningScrollAnchor?
    @State private var clearRevealRequest = 0

    private let samples = [
        "Gelatin, sugar, natural flavors",
        "Water, dates, citric acid",
        "Ethanol, vanilla extract, color E120"
    ]

    private var language: ScreeningLanguage {
        ScreeningLanguage.resolve(storedValue: storedLanguage)
    }
    private var copy: ScreeningCopy { ScreeningCopy(language: language) }

    var body: some View {
        NavigationStack {
            VStack(spacing: 0) {
                ScrollViewReader { scroll in
                    ScrollView {
                        VStack(alignment: .leading, spacing: 22) {
                            if session.currentResult == nil {
                                header
                            }
                            inputSection
                                .id(ScreeningScrollAnchor.input)

                            if let result = session.currentResult {
                                resultSection(result)
                            }

                            sampleSection
                        }
                        .padding(20)
                    }
                    .clipped()
                    // Keep the actual evidence being read visible when text size
                    // or localized wrapping changes the surrounding content.
                    .scrollPosition(id: $readingAnchor)
                    .scrollDismissesKeyboard(.interactively)
                    // Ordinary outer padding insets the scroll view itself. Safe-area
                    // margins alone allow its content to continue under navigation.
                    .padding(.top, 1)
                    .onReceive(NotificationCenter.default.publisher(for: UIResponder.keyboardDidShowNotification)) { _ in
                        softwareKeyboardVisible = true
                        guard ingredientEditorFocused else { return }
                        // Keep the existing primary action above the actual keyboard.
                        // No content or action is duplicated or removed while editing.
                        scroll.scrollTo(ScreeningScrollAnchor.screen, anchor: .bottom)
                    }
                    .onReceive(NotificationCenter.default.publisher(for: UIResponder.keyboardDidHideNotification)) { _ in
                        softwareKeyboardVisible = false
                        let revealScreenedInput = pendingScreenReveal
                        pendingScreenReveal = false
                        guard revealScreenedInput, session.currentResult != nil else { return }
                        // Only the actual Screen action requests this return.
                        // Dismissing a keyboard while reading never moves the page.
                        // After screening, keep the input available for correction
                        // together with the new outcome on ordinary text sizes.
                        scroll.scrollTo(ScreeningScrollAnchor.input, anchor: .top)
                    }
                    .onChange(of: session.currentResult) { previous, current in
                        if current?.matches.isEmpty != false {
                            readingAnchor = nil
                        }
                        guard ingredientEditorFocused, previous != nil, current == nil else { return }
                        // The first edit restores the scope header and changes the
                        // content height. Follow that layout change once, retaining
                        // the same usable primary action for continued editing.
                        DispatchQueue.main.async {
                            guard ingredientEditorFocused, session.currentResult == nil else { return }
                            scroll.scrollTo(ScreeningScrollAnchor.screen, anchor: .bottom)
                        }
                    }
                    .onChange(of: clearRevealRequest) { _, request in
                        // Clear removes long evidence from the layout. Return to
                        // the surviving input only for this explicit action, after
                        // that shorter layout exists; ordinary reading never jumps.
                        DispatchQueue.main.async {
                            guard request == clearRevealRequest, !ingredientEditorFocused,
                                  session.input.isEmpty, session.currentResult == nil else { return }
                            scroll.scrollTo(ScreeningScrollAnchor.input, anchor: .top)
                        }
                    }
                }

                clearAction
            }
            .background(Color(.systemGroupedBackground))
            .navigationTitle("HalalTag")
            .navigationBarTitleDisplayMode(.inline)
            .tint(Color(.label))
            .toolbar {
                ToolbarItem(placement: .topBarLeading) {
                    Button {
                        showingLimitations = true
                    } label: {
                        Label(copy(.privacyAction), systemImage: "info.circle")
                    }
                    .accessibilityLabel(copy(.privacyAction))
                    .accessibilityIdentifier("privacy-info")
                }
            }
            .sheet(isPresented: $showingLimitations) {
                ScreeningInformationView(storedLanguage: $storedLanguage)
            }
        }
        .environment(\.locale, language.locale)
        .environment(\.layoutDirection, language.isRightToLeft ? .rightToLeft : .leftToRight)
    }

    /// Keep Clear reachable while the content scrolls, with room for its real
    /// Dynamic Type font to grow beyond the navigation bar's constrained height.
    private var clearAction: some View {
        Button {
            ingredientEditorFocused = false
            pendingScreenReveal = false
            readingAnchor = nil
            session.clear()
            clearRevealRequest += 1
        } label: {
            Text(copy(.clear))
                .font(.body)
                .fixedSize(horizontal: false, vertical: true)
                .frame(maxWidth: .infinity)
        }
        .buttonStyle(ReadableScreeningActionStyle())
        .accessibilityIdentifier("clear-input")
        .disabled(session.input.isEmpty && session.currentResult == nil)
        .accessibilityHint(session.input.isEmpty && session.currentResult == nil
                           ? copy(.clearEmptyHint)
                           : copy(.clearHint))
        .padding(.horizontal, 20)
        .padding(.vertical, 12)
        .background(Color(.systemGroupedBackground))
    }

    private var header: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text(copy(.textScreening))
                .font(.title2.bold())
                .fixedSize(horizontal: false, vertical: true)
                .accessibilityAddTraits(.isHeader)

            NativeScreeningMatchText(text: copy(.entryScope), language: language,
                                     textStyle: .subheadline,
                                     surfaceColor: .systemGroupedBackground)
        }
    }

    private var inputSection: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text(copy(.ingredients))
                .font(.headline)

            TextEditor(text: $session.input)
                .environment(\.layoutDirection, ScreeningLanguage.inputIsRightToLeft(session.input, fallback: language) ? .rightToLeft : .leftToRight)
                .focused($ingredientEditorFocused)
                // A compact, scrollable editor leaves the primary action and
                // sample choices reachable on small phones without shrinking text.
                .frame(minHeight: 120)
                // Keep the real RTL editor indicator inside the input surface,
                // leaving an ordinary content gutter for scrolling the page.
                .padding(.horizontal, 20)
                .padding(.vertical, 10)
                .scrollContentBackground(.hidden)
                .background(.background, in: RoundedRectangle(cornerRadius: 8))
                .overlay {
                    RoundedRectangle(cornerRadius: 8)
                        .stroke(Color(.separator), lineWidth: 0.5)
                }
                .overlay(alignment: .topLeading) {
                    if session.input.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty {
                        Text(copy(.placeholder))
                            .foregroundStyle(.primary)
                            .padding(.horizontal, 16)
                            .padding(.vertical, 18)
                            .allowsHitTesting(false)
                            .accessibilityHidden(true)
                    }
                }
                .accessibilityLabel(copy(.ingredientText))
                .accessibilityIdentifier("ingredient-editor")
                .accessibilityHint(copy(.editorHint))

            Button {
                pendingScreenReveal = softwareKeyboardVisible
                ingredientEditorFocused = false
                session.screen()
            } label: {
                // The action name is sufficient. A decorative magnifier forces
                // a second line at maximum text size and makes this action harder
                // to reveal above the keyboard on a small phone.
                Text(copy(.screenText))
                    .font(.body)
                    .fixedSize(horizontal: false, vertical: true)
                    .frame(maxWidth: .infinity)
            }
            .buttonStyle(ReadableScreeningActionStyle())
            .accessibilityIdentifier("screen-input")
            .id(ScreeningScrollAnchor.screen)
            .disabled(session.input.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty)
            .accessibilityHint(session.input.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty
                               ? copy(.screenEmptyHint)
                               : copy(.screenHint))

            if session.currentResult == nil {
                Text(copy(.editingNotice))
                    .font(.footnote)
                    .foregroundStyle(.primary)
            }
        }
    }

    private var sampleSection: some View {
        VStack(alignment: .leading, spacing: 10) {
            Text(copy(.trySample))
                .font(.headline)

            ForEach(samples, id: \.self) { sample in
                NativeScreeningSampleButton(title: copy.sampleLabel(sample), language: language,
                                            hint: copy(.sampleHint)) {
                    ingredientEditorFocused = false
                    session.useSample(sample)
                }
            }
        }
    }

    private func resultSection(_ result: IngredientScreeningResult) -> some View {
        VStack(alignment: .leading, spacing: 14) {
            NativeScreeningHeading(text: copy.outcomeTitle(result.outcome), language: language,
                                   textStyle: .title3, emphasis: true,
                                   headingIdentifier: "screening-outcome-heading")

            if !result.matches.isEmpty {
                VStack(alignment: .leading, spacing: 10) {
                    NativeScreeningHeading(text: copy(.matchedTerms), language: language)

                    ForEach(result.matches) { match in
                        VStack(alignment: .leading, spacing: 5) {
                            NativeScreeningMatchText(text: copy.matchName(match), language: language,
                                                     textStyle: .subheadline, weight: .semibold,
                                                     isHeading: true)
                                .id(ScreeningScrollAnchor.matchName(match.id))
                            NativeScreeningMatchText(text: copy.dispositionTitle(match.disposition),
                                                     language: language, textStyle: .subheadline)
                                .id(ScreeningScrollAnchor.matchDisposition(match.id))
                            NativeScreeningMatchText(text: copy.matchedText(match.terms),
                                                     language: language, textStyle: .footnote)
                                .id(ScreeningScrollAnchor.matchText(match.id))
                            NativeScreeningMatchText(text: copy.matchExplanation(match),
                                                     language: language, textStyle: .footnote)
                                .id(ScreeningScrollAnchor.matchExplanation(match.id))
                        }
                        .scrollTargetLayout()
                        .frame(maxWidth: .infinity, alignment: .leading)
                        .padding(12)
                        .background(Color(.secondarySystemGroupedBackground), in: RoundedRectangle(cornerRadius: 8))
                        // Each real text remains independently navigable, even
                        // when the evidence spans multiple screens at large type.
                        .accessibilityElement(children: .contain)
                        .accessibilityIdentifier("screening-match-\(match.id)")
                    }
                }
            }

            // Show the actual word evidence before the longer explanation.
            Text(copy.outcomeSummary(result.outcome))
                .font(.subheadline)

            Text(copy(.coverage))
                .font(.footnote)
                .foregroundStyle(.primary)

            NativeScreeningInformationButton(title: copy(.readPrivacy), language: language) {
                showingLimitations = true
            }
        }
        .frame(maxWidth: .infinity, alignment: .leading)
    }
}

private enum ScreeningScrollAnchor: Hashable {
    case input
    case screen
    case matchName(String)
    case matchDisposition(String)
    case matchText(String)
    case matchExplanation(String)
}

/// Every match field is visible native text on the actual card surface. The
/// enclosing card keeps its four independently navigable children and order.
@MainActor
private struct NativeScreeningMatchText: UIViewRepresentable {
    let text: String
    let language: ScreeningLanguage
    let textStyle: UIFont.TextStyle
    var weight: UIFont.Weight? = nil
    var isHeading = false
    var surfaceColor: UIColor = .secondarySystemGroupedBackground

    func makeUIView(context: Context) -> UILabel {
        let label = UILabel()
        label.numberOfLines = 0
        label.lineBreakMode = .byWordWrapping
        label.adjustsFontSizeToFitWidth = false
        label.adjustsFontForContentSizeCategory = true
        label.isAccessibilityElement = true
        label.textAlignment = .natural
        label.textColor = .label
        label.backgroundColor = surfaceColor
        label.isOpaque = true
        label.setContentCompressionResistancePriority(.required, for: .vertical)
        return label
    }

    func updateUIView(_ label: UILabel, context: Context) {
        label.text = text
        label.textAlignment = language.isRightToLeft ? .right : .left
        label.backgroundColor = surfaceColor
        let baseFont = UIFont.preferredFont(forTextStyle: textStyle,
                                            compatibleWith: label.traitCollection)
        if let weight {
            let descriptor = baseFont.fontDescriptor.addingAttributes([
                .traits: [UIFontDescriptor.TraitKey.weight: weight.rawValue]
            ])
            label.font = UIFont(descriptor: descriptor, size: baseFont.pointSize)
        } else {
            label.font = baseFont
        }
        label.accessibilityTraits = isHeading ? [.staticText, .header] : [.staticText]
        label.accessibilityLanguage = language.rawValue
        label.semanticContentAttribute = language.isRightToLeft
            ? .forceRightToLeft : .forceLeftToRight
    }

    func sizeThatFits(_ proposal: ProposedViewSize, uiView: UILabel,
                      context: Context) -> CGSize? {
        guard let width = proposal.width, width.isFinite, width > 0 else { return nil }
        let size = uiView.sizeThatFits(CGSize(width: width,
                                            height: CGFloat.greatestFiniteMagnitude))
        return CGSize(width: width, height: ceil(size.height))
    }
}

/// A real UIKit heading keeps its visible text, Dynamic Type and native
/// accessibility semantics together in the scrolling result hierarchy.
/// This is a bounded rendering experiment; it does not override audit results.
@MainActor
private struct NativeScreeningHeading: UIViewRepresentable {
    let text: String
    let language: ScreeningLanguage
    var textStyle: UIFont.TextStyle = .headline
    var emphasis = false
    var headingIdentifier = "matched-terms-heading"
    var surfaceColor: UIColor = .systemGroupedBackground

    func makeUIView(context: Context) -> UILabel {
        let label = UILabel()
        label.numberOfLines = 0
        label.lineBreakMode = .byWordWrapping
        label.adjustsFontSizeToFitWidth = false
        label.adjustsFontForContentSizeCategory = true
        label.isAccessibilityElement = true
        label.accessibilityTraits = [.staticText, .header]
        label.textAlignment = .natural
        label.textColor = .label
        label.backgroundColor = surfaceColor
        label.isOpaque = true
        return label
    }

    func updateUIView(_ label: UILabel, context: Context) {
        label.text = text
        label.textAlignment = language.isRightToLeft ? .right : .left
        label.backgroundColor = surfaceColor
        let baseFont = UIFont.preferredFont(forTextStyle: textStyle,
                                            compatibleWith: label.traitCollection)
        if emphasis, let descriptor = baseFont.fontDescriptor.withSymbolicTraits(
            baseFont.fontDescriptor.symbolicTraits.union(.traitBold)
        ) {
            label.font = UIFont(descriptor: descriptor, size: baseFont.pointSize)
        } else {
            label.font = baseFont
        }
        label.accessibilityLanguage = language.rawValue
        label.accessibilityIdentifier = headingIdentifier
        label.semanticContentAttribute = language.isRightToLeft
            ? .forceRightToLeft : .forceLeftToRight
    }

    func sizeThatFits(_ proposal: ProposedViewSize, uiView: UILabel,
                      context: Context) -> CGSize? {
        guard let width = proposal.width, width.isFinite, width > 0 else {
            return nil
        }
        let measured = uiView.sizeThatFits(
            CGSize(width: width, height: CGFloat.greatestFiniteMagnitude)
        )
        return CGSize(width: width, height: ceil(measured.height))
    }
}

/// Sample selection replaces the current text directly. Give its complete title
/// the card width, without a navigation chevron or a separate SwiftUI text node.
@MainActor
private struct NativeScreeningSampleButton: UIViewRepresentable {
    let title: String
    let language: ScreeningLanguage
    let hint: String
    let action: () -> Void

    final class Coordinator: NSObject {
        var action: () -> Void
        init(action: @escaping () -> Void) { self.action = action }
        @objc func activate() { action() }
    }

    func makeCoordinator() -> Coordinator { Coordinator(action: action) }

    func makeUIView(context: Context) -> UIButton {
        let button = UIButton(type: .system)
        button.titleLabel?.numberOfLines = 0
        button.titleLabel?.lineBreakMode = .byWordWrapping
        button.titleLabel?.adjustsFontSizeToFitWidth = false
        button.titleLabel?.adjustsFontForContentSizeCategory = true
        button.titleLabel?.textAlignment = .natural
        button.titleLabel?.backgroundColor = .secondarySystemGroupedBackground
        button.titleLabel?.isOpaque = true
        button.contentHorizontalAlignment = .leading
        button.contentEdgeInsets = UIEdgeInsets(top: 12, left: 12, bottom: 12, right: 12)
        button.backgroundColor = .secondarySystemGroupedBackground
        button.layer.cornerRadius = 8
        button.clipsToBounds = true
        button.setTitleColor(.label, for: .normal)
        button.setContentCompressionResistancePriority(.required, for: .vertical)
        button.addTarget(context.coordinator, action: #selector(Coordinator.activate),
                         for: .touchUpInside)
        return button
    }

    func updateUIView(_ button: UIButton, context: Context) {
        context.coordinator.action = action
        button.setTitle(title, for: .normal)
        button.titleLabel?.font = .preferredFont(forTextStyle: .subheadline,
                                                compatibleWith: button.traitCollection)
        button.accessibilityLanguage = language.rawValue
        button.accessibilityHint = hint
        button.titleLabel?.accessibilityLanguage = language.rawValue
        button.semanticContentAttribute = language.isRightToLeft
            ? .forceRightToLeft : .forceLeftToRight
    }

    func sizeThatFits(_ proposal: ProposedViewSize, uiView: UIButton,
                      context: Context) -> CGSize? {
        guard let width = proposal.width, width.isFinite, width > 24,
              let label = uiView.titleLabel else { return nil }
        let size = label.sizeThatFits(CGSize(width: width - 24,
                                            height: CGFloat.greatestFiniteMagnitude))
        return CGSize(width: width, height: max(44, ceil(size.height) + 24))
    }
}

/// Keep the real action, visible title, Dynamic Type and accessibility identity
/// on a native control. This does not override accessibility frames or audit results.
@MainActor
private struct NativeScreeningInformationButton: UIViewRepresentable {
    let title: String
    let language: ScreeningLanguage
    let action: () -> Void

    final class Coordinator: NSObject {
        var action: () -> Void
        init(action: @escaping () -> Void) { self.action = action }
        @objc func activate() { action() }
    }

    func makeCoordinator() -> Coordinator { Coordinator(action: action) }

    func makeUIView(context: Context) -> UIButton {
        let button = UIButton(type: .system)
        button.titleLabel?.numberOfLines = 0
        button.titleLabel?.lineBreakMode = .byWordWrapping
        button.titleLabel?.adjustsFontSizeToFitWidth = false
        button.titleLabel?.adjustsFontForContentSizeCategory = true
        button.titleLabel?.textAlignment = .natural
        button.contentHorizontalAlignment = .leading
        button.contentEdgeInsets = UIEdgeInsets(top: 8, left: 0, bottom: 8, right: 0)
        button.backgroundColor = .systemGroupedBackground
        button.isOpaque = true
        button.setTitleColor(.label, for: .normal)
        button.setContentCompressionResistancePriority(.required, for: .vertical)
        button.addTarget(context.coordinator, action: #selector(Coordinator.activate),
                         for: .touchUpInside)
        return button
    }

    func updateUIView(_ button: UIButton, context: Context) {
        context.coordinator.action = action
        button.setTitle(title, for: .normal)
        button.titleLabel?.font = .preferredFont(forTextStyle: .body,
                                                compatibleWith: button.traitCollection)
        button.accessibilityLanguage = language.rawValue
        button.accessibilityIdentifier = "screening-privacy-action"
        button.titleLabel?.accessibilityLanguage = language.rawValue
        button.semanticContentAttribute = language.isRightToLeft
            ? .forceRightToLeft : .forceLeftToRight
    }

    func sizeThatFits(_ proposal: ProposedViewSize, uiView: UIButton,
                      context: Context) -> CGSize? {
        guard let width = proposal.width, width.isFinite, width > 0,
              let label = uiView.titleLabel else { return nil }
        let size = label.sizeThatFits(CGSize(width: width,
                                            height: CGFloat.greatestFiniteMagnitude))
        return CGSize(width: width, height: max(44, ceil(size.height) + 16))
    }
}

/// Keep inactive action names readable. The real Button still supplies its
/// standard interaction and disabled accessibility state; only paint changes.
private struct ReadableScreeningActionStyle: ButtonStyle {
    @Environment(\.isEnabled) private var isEnabled

    func makeBody(configuration: Configuration) -> some View {
        let foreground = isEnabled ? Color(.systemBackground) : Color(.label)
        let background = isEnabled ? Color(.label) : Color(.secondarySystemGroupedBackground)
        return configuration.label
            .foregroundStyle(foreground)
            .padding(.horizontal, 12)
            .padding(.vertical, 8)
            .frame(minHeight: 44)
            .background(background, in: RoundedRectangle(cornerRadius: 10))
            .overlay {
                RoundedRectangle(cornerRadius: 10)
                    .strokeBorder(isEnabled ? Color(.systemBackground) : Color(.label),
                                  lineWidth: configuration.isPressed ? 2 : (isEnabled ? 0 : 1))
            }
            .contentShape(RoundedRectangle(cornerRadius: 10))
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
        case .unknown: return .primary
        }
    }
}

private struct ScreeningInformationView: View {
    @Environment(\.dismiss) private var dismiss
    @Binding var storedLanguage: String
    private var language: ScreeningLanguage { ScreeningLanguage.resolve(storedValue: storedLanguage) }
    private var copy: ScreeningCopy { ScreeningCopy(language: language) }

    var body: some View {
        NavigationStack {
            VStack(spacing: 0) {
                ScrollView {
                    VStack(alignment: .leading, spacing: 24) {
                        section(copy(.whatDoesTitle), text: copy(.whatDoesBody))
                        section(copy(.meaningTitle), text: copy(.meaningBody))
                        section(copy(.privacyTitle), text: copy(.privacyBody))
                        section(copy(.coverageTitle), text: copy(.coverage))
                        onlineResources
                    }
                    .frame(maxWidth: .infinity, alignment: .leading)
                    .padding(20)
                }
                .clipped()
                .padding(.top, 1)

                // A persistent content action gives the real label room to
                // scale while leaving every privacy section scrollable.
                Button { dismiss() } label: {
                    Text(copy(.done))
                        .font(.body)
                        .fixedSize(horizontal: false, vertical: true)
                        .frame(maxWidth: .infinity)
                }
                .buttonStyle(ReadableScreeningActionStyle())
                .accessibilityIdentifier("privacy-done")
                .padding(.horizontal, 20)
                .padding(.vertical, 12)
                .background(Color(.systemBackground))
            }
            .background(Color(.systemBackground))
            .navigationTitle(copy(.sheetTitle))
            .navigationBarTitleDisplayMode(.inline)
            // Keep the title over an explicit opaque surface as the sheet scrolls.
            .toolbarBackground(Color(.systemBackground), for: .navigationBar)
            .toolbarBackground(.visible, for: .navigationBar)
            .toolbar {
                ToolbarItem(placement: .topBarLeading) {
                    Menu {
                        languageOption(.english)
                        languageOption(.arabic)
                    } label: {
                        Image(systemName: "globe")
                    }
                    .accessibilityLabel(copy(.appLanguage))
                    .accessibilityValue(language.nativeName)
                    .accessibilityHint(copy(.languageHint))
                    .accessibilityIdentifier("app-language-menu")
                }
            }
        }
        .environment(\.locale, language.locale)
        .environment(\.layoutDirection, language.isRightToLeft ? .rightToLeft : .leftToRight)
    }

    private func languageOption(_ option: ScreeningLanguage) -> some View {
        Button {
            storedLanguage = option.rawValue
        } label: {
            if language == option {
                Label(option.nativeName, systemImage: "checkmark")
            } else {
                Text(option.nativeName)
            }
        }
        .accessibilityIdentifier("language-" + option.rawValue)
    }

    private var onlineResources: some View {
        VStack(alignment: .leading, spacing: 12) {
            NativeScreeningHeading(text: copy(.onlineTitle), language: language,
                                   headingIdentifier: "privacy-online-heading",
                                   surfaceColor: .systemBackground)

            if let privacyURL = URL(string: "https://swonyu.github.io/HalalAnalyzer/") {
                Link(destination: privacyURL) {
                    Text(copy(.onlinePrivacy))
                        .underline()
                        .foregroundStyle(.primary)
                        .fixedSize(horizontal: false, vertical: true)
                        .frame(minHeight: 44, alignment: .leading)
                }
                .accessibilityHint(copy(.onlinePrivacyHint))
            }

            if let supportURL = URL(string: "https://swonyu.github.io/HalalAnalyzer/support.html") {
                Link(destination: supportURL) {
                    Text(copy(.onlineSupport))
                        .underline()
                        .foregroundStyle(.primary)
                        .fixedSize(horizontal: false, vertical: true)
                        .frame(minHeight: 44, alignment: .leading)
                }
                .accessibilityHint(copy(.onlineSupportHint))
            }

            NativeScreeningMatchText(text: copy(.publicSupportNotice), language: language,
                                    textStyle: .body, surfaceColor: .systemBackground)
        }
    }

    private func section(_ title: String, text: String) -> some View {
        VStack(alignment: .leading, spacing: 8) {
            // Keep the visible text, measured size and native accessibility
            // semantics together while this section scrolls past the toolbar.
            // The same real sheet surface is painted behind each text element.
            NativeScreeningHeading(text: title, language: language,
                                   headingIdentifier: "privacy-section-" + title,
                                   surfaceColor: .systemBackground)
            NativeScreeningMatchText(text: text, language: language,
                                    textStyle: .body, surfaceColor: .systemBackground)
        }
    }
}

#Preview {
    ContentView()
}
