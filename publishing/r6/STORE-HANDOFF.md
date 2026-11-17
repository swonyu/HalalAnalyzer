# HalalTag R6 store handoff

## Exact source and actual delivery state

This handoff describes frozen candidate `f2c27c9271da3a17bb01c50b6cdad94643e1d0f2`, with shipping bundle `HalalTag.v1.1`, version `1.0`, build `1`, iOS deployment target `26.5`, and iPhone/iPad support. R6 changes only Arabic-semicolon entry separation in the shipping model. Its visible UI is the preserved R5 UI. The actual R6 batch compiled and executed the model harness with 211 passing checks, then its adapter rejected an allowed repeated legacy check label before any UI case ran. R6b repairs that receipt rule while preserving the frozen source. Accepted model/UI evidence for R6b is still pending.

The root coordinator observed App Store record `6773625937`, version `1.0`, in **Prepare for Submission**, with no attached build, four iPhone screenshots, and review attachment `01-scanner.png`. This child did not inspect the images themselves. Their presence and filename do not establish current UI accuracy. Review their real contents before replacing or retrying an upload. No store field, screenshot or attachment was written by this child.

`store-localizations.json` contains the complete English and Arabic descriptions, keywords, promotional text, and reviewer notes. The combined reviewer notes are 2,840 UTF-8 bytes. English and Arabic keywords use 61 and 79 bytes; descriptions use 1,015 and 901 characters. `store-metadata-validation.json` records these checks. Preserve the current app name unless separately reviewed. These are source-bound drafts, not a saved store form or release receipt.

## Product claims checked against the source

The application screens typed or pasted English terms using seven small local rule groups. Its interface and explanations support English and Arabic; it does not translate Arabic ingredient names. It supplies three sample texts, matched-word explanations, source/context cautions, an unknown result when no supported rule matches, and privacy/limitations help. Editing invalidates the previous result. Clear removes the current draft and result. Language switching preserves the current state, and the language choice is saved locally. A new app process starts without the previous draft or result.

The copy makes these limits explicit. No result certifies halal status, verifies ingredient presence or proves sourcing. The shipped source has no camera, OCR, barcode reader, remote analysis API, account, purchase flow, ads, analytics SDK, saved history or favorites. Historical scanner copy and assets must be checked against the actual candidate before reuse.

Source references: `ContentView.swift`, `IngredientScreening.swift`, `ScreeningLocalization.swift`, `PrivacyInfo.xcprivacy`, the shipping project, and the exact fourteen-file release manifest. The unchanged R5 UI and new R6 model still require actual native acceptance; a source review does not establish screen-reader, contrast or physical-device success.

## Privacy answer facts

| Question area | Verified source facts | Remaining action |
| --- | --- | --- |
| Ingredient text and results | Held in the current in-memory session; no app transmission or persistent history is implemented. | Check the final shipping artifact and actual release behavior before submitting answers. |
| Language preference | App-local UserDefaults stores the interface choice. The manifest declares `CA92.1`. | Verify the exact manifest is packaged and the preference behaves correctly on a fresh process. |
| Tracking and SDKs | Tracking is false; tracking domains and collected-data arrays are empty. No advertising, analytics or third-party SDK is included in the reviewed shipping source. | Keep answers aligned with the actual signed artifact. Reassess if integrations change. |
| Permissions | No camera, photos, microphone or location request appears in the shipping feature. | Do not advertise scanner functionality or request those permissions through unrelated preparations. |
| External support | Fixed links open GitHub-hosted privacy/support pages. An optional public GitHub issue exposes the chosen account name, text and attachments to others. | Final privacy answers must account for the operator's actual support practices; do not treat all support data as automatically exempt. |

The source supports an on-device screening/data-minimization statement. It does not alone establish every App Privacy answer for external support or a completed store questionnaire. Apple defines collection in relation to data leaving the device and requires all conditions to be met for optional disclosure. Review the actual external support handling before finalizing any “Data Not Collected” answer. No App Privacy form has been saved by this child.

The proposed English privacy URL is `https://swonyu.github.io/HalalAnalyzer/`; Arabic is `https://swonyu.github.io/HalalAnalyzer/privacy-ar.html`. Support URLs are the corresponding `support.html` and `support-ar.html` pages. The local documents exactly preserve the verified public support branch; live URL reachability and approved public contact remain separate checks. Current source has no account, so an in-app account-deletion flow is not applicable to this candidate.

Complete the current age-rating questionnaire from the app's actual content. The app contains alcohol-related ingredient examples in an informational screening context. Do not automatically answer every content question “No,” or assign an age rating merely because a term appears. The root coordinator must answer the actual questionnaire accurately.

## Real screenshot acquisition plan

This is a planned capture specification. No screenshot was generated, captured or uploaded by this child.

Apple's current required categories are iPhone with Dynamic Island (medium display) and, for this iPad-capable app, iPad 13-inch. Choose an actually available supported destination, confirm its native pixel output, and capture the accepted final UI directly. Portrait examples accepted for these categories are:

| Category | Portrait pixels | Practical destination examples |
| --- | --- | --- |
| iPhone Dynamic Island, medium | 1179 × 2556 or 1206 × 2622 | iPhone 15/15 Pro, or iPhone 16 Pro/17/17 Pro as available |
| iPad 13-inch | 2064 × 2752 or 2048 × 2732 | 13-inch iPad Pro or iPad Air supported by the installed runtime |

The compact iPhone SE native audit is 750 × 1334. Its audit attachments remain useful QA evidence, but they do not satisfy those primary capture categories. Keep original audit evidence separate. Screenshots must be PNG/JPEG without alpha, with real UI and no debug or audit overlays. Do not stretch a compact screenshot, reconstruct UI, or use generated imagery as app evidence.

For each of English and Arabic, capture four coherent views on iPhone and iPad, up to sixteen images total:

1. Fresh text-entry screen with the supported-language/scope notice and sample controls visible.
2. `Gelatin, sugar, natural flavors` showing source/context review and the explanation.
3. `Water, dates, citric acid` showing an unknown result, with no implication of certification.
4. Privacy and limitations showing useful explanatory content, or the direct flagged-term sample if a complete result is more legible at that destination. The actual image must keep the corresponding limitations visible or clearly available.

Screen the sample inputs through the normal UI, dismiss the keyboard where it would obscure content, and verify natural Arabic layout with the English input kept legible. Use non-sensitive sample text. Record candidate commit, actual installed version/build, bundle, build receipt, device/runtime, pixel dimensions, locale, appearance, journey, filename and SHA-256. Inspect every full-size image for clipping, stale results, wrong-language copy and misleading statements before upload. Re-read the live store inventory first; retain valid current images and deliberately replace stale material only after reviewing its contents. Record upload and saved-field evidence separately.

## Public support contact

The current local support pages for HalalTag, Lumina and Career Finder expose public GitHub issue routes. The bounded public-source search recorded in `public-contact-search.json` did not establish an explicitly published app-support email, telephone number or legal address. That is a specific remaining gap, not proof that no suitable public contact exists anywhere.

Apple's Support URL documentation calls for actual contact information. Do not repurpose private App Review contact fields, commit-author addresses or unrelated account details as an approved public contact. The root coordinator reported that HalalTag's private App Review contact is filled, while Lumina/Career contact fields were blank; these are distinct from a public support website. No contact was invented or published here.

## Strict review dispositions

- **Validated model defect, fixed in R6; model retested, accepted UI run pending:** Arabic `؛` did not terminate an ingredient entry. It could join `E` and `120`, join `vanilla` and `extract`, or let a neighboring qualifier suppress a separate direct match. R6 adds the separator and nine focused assertions. All 211 model checks, including the nine boundary assertions, passed in the actual R6 binary execution. The R6b native adapter compiles and executes the sealed model harness before its unchanged nineteen UI cases; the release adapter requires the real receipt, binary, logs and source bindings.
- **Historical native appearance finding:** R4 failed two actual appearance cases and stopped before the other seventeen. R5 replaced the affected visible privacy text with existing native UILabel wrappers. R6 preserves that repair and all original assertions. Only an accepted fresh native run can resolve it; historical archives or source checks do not establish a pass.
- **Source security/privacy review:** User text is consumed as text by local matching and native rendering. Fixed HTTPS support destinations are not derived from input. There is no embedded web content, remote ingredient service, account token or persistent ingredient-history path in this source. These bounded observations do not substitute for final artifact inspection and native behavior.
- **Unverified performance risk, not a confirmed defect:** The editor accepts arbitrarily long text and screening is synchronous. No representative-device latency failure has been measured. Do not claim a pass, invent a limit or change the frozen candidate from speculation; observe a normal large-label case if the coordinator's existing journey checks expose a practical problem.
- **Store blockers still need actual evidence:** Accepted native/model run, release signing/artifacts, real accepted screenshots, current privacy/age-rating forms and public support contact, then upload/processing/submission/review/availability. The successful model execution, planned R6b run and these drafts are not completed release gates.

Primary references checked on 17 November 2026:

- [Metadata limits, support contact and review information](https://developer.apple.com/help/app-store-connect/reference/app-information/platform-version-information/)
- [Current screenshot categories and dimensions](https://developer.apple.com/help/app-store-connect/reference/app-information/screenshot-specifications/)
- [App Privacy definitions and optional-disclosure conditions](https://developer.apple.com/app-store/app-privacy-details/)
- [Age-rating values and definitions](https://developer.apple.com/help/app-store-connect/reference/app-information/age-ratings-values-and-definitions/)
