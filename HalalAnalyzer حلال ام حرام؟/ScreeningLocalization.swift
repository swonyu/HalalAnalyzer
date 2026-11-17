import Foundation

/// This setting controls presentation only. It never translates or changes input.
enum ScreeningLanguage: String, CaseIterable {
    case english = "en"
    case arabic = "ar"

    static let preferenceKey = "HalalTag.interfaceLanguage"
    var locale: Locale { Locale(identifier: rawValue) }
    var isRightToLeft: Bool { self == .arabic }
    var nativeName: String { self == .arabic ? "العربية" : "English" }

    static func resolve(storedValue: String, preferredLanguages: [String] = Locale.preferredLanguages) -> ScreeningLanguage {
        if let selected = ScreeningLanguage(rawValue: storedValue) { return selected }
        for identifier in preferredLanguages {
            let base = identifier.lowercased().split(whereSeparator: { $0 == "-" || $0 == "_" }).first.map(String.init)
            if let base, let supported = ScreeningLanguage(rawValue: base) { return supported }
        }
        return .english
    }

    /// Keep a pasted English paragraph LTR inside the Arabic interface, and an
    /// Arabic paragraph RTL inside English. Numbers alone use the UI direction.
    static func inputIsRightToLeft(_ text: String, fallback: ScreeningLanguage) -> Bool {
        for scalar in text.unicodeScalars where CharacterSet.letters.contains(scalar) {
            let value = scalar.value
            return (0x0590...0x08FF).contains(value) || (0xFB1D...0xFDFF).contains(value) || (0xFE70...0xFEFF).contains(value)
        }
        return fallback.isRightToLeft
    }
}

enum ScreeningCopyKey: CaseIterable {
    case privacyAction
    case clear
    case clearEmptyHint
    case clearHint
    case textScreening
    case entryScope
    case ingredients
    case placeholder
    case ingredientText
    case editorHint
    case screenText
    case screenEmptyHint
    case screenHint
    case editingNotice
    case trySample
    case sampleHint
    case sampleOne
    case sampleTwo
    case sampleThree
    case matchedTerms
    case readPrivacy
    case whatDoesTitle
    case whatDoesBody
    case meaningTitle
    case meaningBody
    case privacyTitle
    case privacyBody
    case coverageTitle
    case coverage
    case sheetTitle
    case done
    case onlineTitle
    case onlinePrivacy
    case onlinePrivacyHint
    case onlineSupport
    case onlineSupportHint
    case publicSupportNotice
    case appLanguage
    case languageHint
    case flaggedTitle
    case sourceTitle
    case unknownTitle
    case flaggedSummary
    case sourceSummary
    case unknownSummary
    case flaggedDisposition
    case sourceDisposition
    case contextDisposition
    case alcoholName
    case porkName
    case carmineName
    case gelatinName
    case glyceridesName
    case enzymesName
    case vanillaName
    case alcoholExplanation
    case porkExplanation
    case carmineExplanation
    case gelatinExplanation
    case glyceridesExplanation
    case enzymesExplanation
    case vanillaExplanation
    case contextNote
}

/// Exhaustive, reviewable copy for the current small screening UI.
/// English rule evaluation stays in IngredientScreening, which is unchanged.
struct ScreeningCopy {
    let language: ScreeningLanguage

    func callAsFunction(_ key: ScreeningCopyKey) -> String {
        switch key {
        case .privacyAction: return language == .english ? "Privacy and limitations" : "الخصوصية والقيود"
        case .clear: return language == .english ? "Clear" : "مسح"
        case .clearEmptyHint: return language == .english ? "There is no text or result to clear." : "لا يوجد نص أو نتيجة لمسحها."
        case .clearHint: return language == .english ? "Clears the ingredient text and its current result." : "يمسح نص المكونات والنتيجة الحالية."
        case .textScreening: return language == .english ? "Text screening" : "فحص النص"
        case .entryScope: return language == .english ? "Match a small set of English ingredient terms. Results identify words to check; they do not determine halal status." : "يطابق التطبيق مجموعة صغيرة من أسماء المكونات الإنجليزية. تحدد النتائج كلمات تحتاج إلى التحقق، ولا تحدد إن كان المنتج حلالًا."
        case .ingredients: return language == .english ? "Ingredients" : "المكونات"
        case .placeholder: return language == .english ? "Example: gelatin, whey, E471, vanilla extract..." : "مثال بالإنجليزية: \u{2066}gelatin, whey, E471, vanilla extract...\u{2069}"
        case .ingredientText: return language == .english ? "Ingredient text" : "نص المكونات"
        case .editorHint: return language == .english ? "Type or paste English ingredient text, then activate Screen text. Editing clears the previous result." : "اكتب أو الصق أسماء المكونات بالإنجليزية، ثم اختر فحص النص. يؤدي تعديل النص إلى مسح النتيجة السابقة."
        case .screenText: return language == .english ? "Screen text" : "فحص النص"
        case .screenEmptyHint: return language == .english ? "Enter ingredient text before screening." : "أدخل نص المكونات قبل الفحص."
        case .screenHint: return language == .english ? "Screens the ingredient text on this device." : "يفحص نص المكونات على هذا الجهاز."
        case .editingNotice: return language == .english ? "Changing the text clears the result. No result is a halal certificate." : "يؤدي تغيير النص إلى مسح النتيجة. لا تُعد أي نتيجة شهادة حلال."
        case .trySample: return language == .english ? "Try sample text" : "جرّب نصًا نموذجيًا"
        case .sampleHint: return language == .english ? "Replaces the text and screens this sample." : "يستبدل النص بهذا المثال الإنجليزي ويفحصه."
        case .sampleOne: return language == .english ? "Gelatin, sugar, natural flavors" : "مثال بالإنجليزية: \u{2066}Gelatin, sugar, natural flavors\u{2069}"
        case .sampleTwo: return language == .english ? "Water, dates, citric acid" : "مثال بالإنجليزية: \u{2066}Water, dates, citric acid\u{2069}"
        case .sampleThree: return language == .english ? "Ethanol, vanilla extract, color E120" : "مثال بالإنجليزية: \u{2066}Ethanol, vanilla extract, color E120\u{2069}"
        case .matchedTerms: return language == .english ? "Matched terms" : "الكلمات المطابقة"
        case .readPrivacy: return language == .english ? "Read privacy and limitations" : "اقرأ الخصوصية والقيود"
        case .whatDoesTitle: return language == .english ? "What this screen does" : "وظيفة هذه الشاشة"
        case .whatDoesBody: return language == .english ? "It matches a limited set of English ingredient words and E120/E471 formats in text you choose to type or paste. It has no camera, OCR, barcode scanning, trained AI model, or remote screening service." : "يطابق التطبيق مجموعة محدودة من كلمات المكونات الإنجليزية وصيغ الرمزين \u{2066}E120/E471\u{2069} في النص الذي تكتبه أو تلصقه. لا يستخدم كاميرا أو تعرّفًا ضوئيًا على الحروف أو مسحًا للرموز الشريطية أو نموذج ذكاء اصطناعي مدرّبًا أو خدمة فحص عن بُعد."
        case .meaningTitle: return language == .english ? "What a result means" : "معنى النتيجة"
        case .meaningBody: return language == .english ? "A match only shows that a term appeared. It does not establish ingredient presence, origin, processing, cross-contamination, or halal status. Simple statements such as alcohol-free are marked for context review; this app cannot verify such claims. Unmatched text remains unknown. Check the original label and ask the manufacturer or a qualified certifier when needed." : "تعني المطابقة فقط ظهور كلمة في النص. ولا تثبت وجود المكوّن أو مصدره أو طريقة تصنيعه أو التلوث التبادلي أو صفة الحلال. تُحال عبارات بسيطة مثل «خالٍ من الكحول» إلى مراجعة السياق؛ ولا يستطيع التطبيق التحقق من هذه الادعاءات. يبقى النص غير المطابق غير محسوم. راجع الملصق الأصلي واسأل الشركة المصنّعة أو جهة مختصة بمنح شهادات الحلال عند الحاجة."
        case .privacyTitle: return language == .english ? "Your text and privacy" : "نصك وخصوصيتك"
        case .privacyBody: return language == .english ? "This app screens text on your device and keeps the current text and result in memory. It does not save or transmit them, include analytics, or request camera, photos, microphone, or location permissions. Clear removes the current text and result. Your language choice is saved in this app’s settings. A fresh app launch starts with an empty draft and no result. Your keyboard and other iOS services remain subject to your device settings." : "يفحص التطبيق النص على جهازك ويحتفظ بالنص الحالي والنتيجة في الذاكرة فقط. لا يحفظهما أو يرسلهما، ولا يتضمن تحليلات استخدام أو يطلب أذونات الكاميرا أو الصور أو الميكروفون أو الموقع. يمسح زر المسح النص الحالي والنتيجة. يُحفظ اختيار اللغة في إعدادات التطبيق. عند بدء تشغيل التطبيق من جديد تكون المسودة فارغة ولا توجد نتيجة. تخضع لوحة المفاتيح وخدمات iOS الأخرى لإعدادات جهازك."
        case .coverageTitle: return language == .english ? "Language and coverage" : "اللغة ونطاق التغطية"
        case .coverage: return language == .english ? "Coverage is limited to a small English term list and E120/E471 formats. Other languages, ingredients, synonyms, and complex label claims may not be recognised. Unmatched text does not establish halal status." : "تقتصر التغطية على قائمة صغيرة من الكلمات الإنجليزية وصيغ الرمزين \u{2066}E120/E471\u{2069}. قد لا يتعرف التطبيق على اللغات الأخرى أو المكونات أو المرادفات أو الادعاءات المعقدة على الملصق. لا يثبت النص غير المطابق صفة الحلال."
        case .sheetTitle: return language == .english ? "Privacy & limitations" : "الخصوصية والقيود"
        case .done: return language == .english ? "Done" : "تم"
        case .onlineTitle: return language == .english ? "Support and online privacy" : "الدعم والخصوصية عبر الإنترنت"
        case .onlinePrivacy: return language == .english ? "Read the privacy policy online" : "اقرأ سياسة الخصوصية عبر الإنترنت"
        case .onlinePrivacyHint: return language == .english ? "Opens the HalalTag privacy page in your browser." : "يفتح صفحة خصوصية HalalTag في المتصفح."
        case .onlineSupport: return language == .english ? "Open support instructions" : "افتح تعليمات الدعم"
        case .onlineSupportHint: return language == .english ? "Opens instructions for using HalalTag and its public support channel." : "يفتح تعليمات استخدام HalalTag وقناة الدعم العامة."
        case .publicSupportNotice: return language == .english ? "These pages are hosted by GitHub. Posting a support request requires a GitHub account and makes your request public. Do not include private or sensitive information." : "تستضيف GitHub هذه الصفحات. يتطلب نشر طلب دعم حسابًا في GitHub، ويصبح طلبك متاحًا للعامة. لا تُدرج معلومات خاصة أو حساسة."
        case .appLanguage: return language == .english ? "App language" : "لغة التطبيق"
        case .languageHint: return language == .english ? "Choose English or Arabic. The ingredient text and result stay unchanged." : "اختر الإنجليزية أو العربية. يبقى نص المكونات والنتيجة دون تغيير."
        case .flaggedTitle: return language == .english ? "Flagged terms found" : "وُجدت كلمات تستدعي الانتباه"
        case .sourceTitle: return language == .english ? "Source or context needs review" : "يلزم التحقق من المصدر أو السياق"
        case .unknownTitle: return language == .english ? "No supported match — status unknown" : "لا توجد مطابقة مدعومة — الحالة غير معروفة"
        case .flaggedSummary: return language == .english ? "This text includes words in the limited flagged list. A word match cannot establish ingredient presence or halal status. Check the original label and ingredient source." : "يتضمن النص كلمات من قائمة محدودة تستدعي الانتباه. لا تثبت مطابقة الكلمات وجود المكوّن أو صفة الحلال. راجع الملصق الأصلي ومصدر المكوّن."
        case .sourceSummary: return language == .english ? "The matched terms need source or context checks. This app cannot verify label claims, processing, or certification." : "تحتاج الكلمات المطابقة إلى التحقق من المصدر أو السياق. لا يستطيع التطبيق التحقق من ادعاءات الملصق أو التصنيع أو الشهادات."
        case .unknownSummary: return language == .english ? "No supported terms were matched. Unrecognised ingredients, spellings, and languages may be missed. No conclusion about the product can be drawn." : "لم تُطابق أي كلمة مدعومة. قد يفوّت التطبيق مكونات أو تهجئات أو لغات غير معروفة لديه. لا يمكن استنتاج حكم بشأن المنتج."
        case .flaggedDisposition: return language == .english ? "Flagged term — verify the label" : "كلمة تستدعي الانتباه — تحقّق من الملصق"
        case .sourceDisposition: return language == .english ? "Source-dependent — verify the origin" : "يعتمد على المصدر — تحقّق من الأصل"
        case .contextDisposition: return language == .english ? "Label context — claim not verified" : "سياق الملصق — الادعاء غير متحقق منه"
        case .alcoholName: return language == .english ? "Alcohol-related terms" : "كلمات مرتبطة بالكحول"
        case .porkName: return language == .english ? "Pork-related terms" : "كلمات مرتبطة بالخنزير"
        case .carmineName: return language == .english ? "Carmine / E120" : "الكارمين / \u{2066}E120\u{2069}"
        case .gelatinName: return language == .english ? "Gelatin" : "الجيلاتين"
        case .glyceridesName: return language == .english ? "Mono- and diglycerides / E471" : "أحادي وثنائي الغليسريدات / \u{2066}E471\u{2069}"
        case .enzymesName: return language == .english ? "Enzymes / rennet" : "الإنزيمات / المنفحة"
        case .vanillaName: return language == .english ? "Vanilla extract" : "مستخلص الفانيليا"
        case .alcoholExplanation: return language == .english ? "The word alone does not establish the substance, concentration, processing, or presence in the final product." : "لا تحدد الكلمة وحدها المادة أو تركيزها أو طريقة تصنيعها أو وجودها في المنتج النهائي."
        case .porkExplanation: return language == .english ? "Verify what the label refers to and obtain ingredient-origin information from the manufacturer or a qualified certifier." : "تحقّق مما يشير إليه الملصق، واطلب معلومات عن أصل المكوّن من الشركة المصنّعة أو جهة مختصة بمنح شهادات الحلال."
        case .carmineExplanation: return language == .english ? "This term or identifier does not supply the product's sourcing, processing, or certification details." : "لا توفر هذه الكلمة أو هذا الرمز تفاصيل عن مصادر المنتج أو تصنيعه أو شهاداته."
        case .gelatinExplanation: return language == .english ? "The term alone does not identify the origin, processing, or certification of this ingredient." : "لا تحدد الكلمة وحدها أصل هذا المكوّن أو طريقة تصنيعه أو شهاداته."
        case .glyceridesExplanation: return language == .english ? "The name or identifier alone does not establish the ingredient source or certification." : "لا يثبت الاسم أو الرمز وحده مصدر المكوّن أو حصوله على شهادة."
        case .enzymesExplanation: return language == .english ? "Ask for the specific enzyme, its origin, processing, and any applicable certification." : "اسأل عن نوع الإنزيم ومصدره وطريقة تصنيعه وأي شهادة ذات صلة."
        case .vanillaExplanation: return language == .english ? "The phrase does not establish the extraction process or the final product's composition or certification." : "لا تثبت العبارة طريقة الاستخلاص أو تركيب المنتج النهائي أو حصوله على شهادة."
        case .contextNote: return language == .english ? " A nearby qualifier or label claim also needs review; it is not verified by this app." : " تحتاج أيضًا كلمة توضيحية قريبة أو ادعاء على الملصق إلى مراجعة؛ ولم يتحقق التطبيق منه."
        }
    }

    func outcomeTitle(_ outcome: ScreeningOutcome) -> String {
        switch outcome {
        case .flaggedTerms: return self(.flaggedTitle)
        case .sourceDependent: return self(.sourceTitle)
        case .unknown: return self(.unknownTitle)
        }
    }

    func outcomeSummary(_ outcome: ScreeningOutcome) -> String {
        switch outcome {
        case .flaggedTerms: return self(.flaggedSummary)
        case .sourceDependent: return self(.sourceSummary)
        case .unknown: return self(.unknownSummary)
        }
    }

    func dispositionTitle(_ disposition: ScreeningMatchDisposition) -> String {
        switch disposition {
        case .flaggedTerm: return self(.flaggedDisposition)
        case .sourceDependent: return self(.sourceDisposition)
        case .contextReview: return self(.contextDisposition)
        }
    }

    func matchName(_ match: IngredientScreeningMatch) -> String {
        switch match.id {
        case "alcohol": return self(.alcoholName)
        case "pork": return self(.porkName)
        case "e120": return self(.carmineName)
        case "gelatin": return self(.gelatinName)
        case "e471": return self(.glyceridesName)
        case "enzymes": return self(.enzymesName)
        case "vanilla": return self(.vanillaName)
        default: return match.name // Future rules require a translation and test review.
        }
    }

    func matchExplanation(_ match: IngredientScreeningMatch) -> String {
        guard language == .arabic else { return match.explanation }
        let key: ScreeningCopyKey
        switch match.id {
        case "alcohol": key = .alcoholExplanation
        case "pork": key = .porkExplanation
        case "e120": key = .carmineExplanation
        case "gelatin": key = .gelatinExplanation
        case "e471": key = .glyceridesExplanation
        case "enzymes": key = .enzymesExplanation
        case "vanilla": key = .vanillaExplanation
        default: return match.explanation
        }
        let originalContextNote = ScreeningCopy(language: .english)(.contextNote)
        return self(key) + (match.explanation.hasSuffix(originalContextNote) ? self(.contextNote) : "")
    }

    func matchedText(_ terms: [String]) -> String {
        let evidence = terms.joined(separator: ", ")
        return language == .english ? "Matched text: \(evidence)" : "النص المطابق: \u{2066}\(evidence)\u{2069}"
    }

    func sampleLabel(_ sample: String) -> String {
        switch sample {
        case "Gelatin, sugar, natural flavors": return self(.sampleOne)
        case "Water, dates, citric acid": return self(.sampleTwo)
        case "Ethanol, vanilla extract, color E120": return self(.sampleThree)
        default: return sample
        }
    }
}
