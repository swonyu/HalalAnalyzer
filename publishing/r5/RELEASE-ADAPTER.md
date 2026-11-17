# HalalTag R5 production release preparation

The release preparation copies fourteen shipping files from the frozen native candidate `be0b7ab202c38d81aab6a908cd69902c18b5ded9`, checks each file against that Git commit, and excludes every QA host and test file. Documentation successors do not alter that candidate or its existing native package.

The reviewed predecessor is `halaltag-production-release-r3`. Its release stage implementation, signing checks, serial ownership checks, no-retry native evidence gate, cleanup reserve and original deadline remain intact. The R5 preparation changes only source identity, scope, paths, provenance and the resulting integrity pins. `adapter-from-r3.diff` makes these changes reviewable.

## Prepare files without executing the adapter

Run `prepare_release_review.py` with the preserved R3 release preparation, frozen R5 native preparation, this repository, the exact Mac `preparation/Source` path selected by the root coordinator, and a new output directory. The preparer only reads/copies files, reads Git objects, parses Python syntax and writes review artifacts. It does not import or execute the release adapter, start native tools, reserve a schedule slot, configure a real acknowledgment, sign or upload.

The preparation refuses a different predecessor, a changed R5 seal, a different native adapter, a changed shipping file, a different nineteen-case plan or an existing output directory. Preserve failed partial outputs as evidence and use a fresh output path for a deliberate correction.

## Actual gates retained for the release owner

Before any stage, the adapter requires the actual R5 native report, all nineteen original passing cases with zero failed/skipped/expected-failure/runtime-warning outcomes, unchanged original result evidence, seventeen distinct supplementary launches, exact shipping-source bindings, completed cleanup and a released lock. R3/R4 receipts and a queued R5 test cannot satisfy this gate.

The stages remain:

1. `unsigned-archive`: creates and verifies a local production archive. It establishes neither signing nor installability.
2. `developer-archive`: requires the verified unsigned stage, actual App Store identity and unused version/build configuration, plus root-authorized Apple provisioning communication. It verifies the developer signing identity and entitlements.
3. `distribution-export`: requires the verified developer archive and the same current identity/configuration. It exports locally and verifies the distribution signature, team, application identifier, disabled debugging, exact privacy manifest, English/Arabic resources and absence of QA content.

Each stage requires a fresh exact root acknowledgment in the serial schedule, valid evidence hashes, a single-use slot and a window inside **17 November 2026 22:26:12 UTC**. The cap remains twenty minutes including cleanup. Any unresolved native ownership prevents acquisition. The preparer leaves acknowledgments and release configuration explicitly unconfigured.

The adapter has no upload operation. A verified exported IPA still requires store upload, processing, reviewer access, accurate metadata/privacy answers, submission, approval and actual availability evidence before any release claim.

## Verified source configuration and remaining store work

The frozen source declares shipping bundle `HalalTag.v1.1`, team `WY272L3F3N`, version `1.0`, build `1`, iOS deployment target `26.5`, and iPhone/iPad support. These source values do not prove a matching current App Store record or an unused build number. Preserve the identity and inspect current store records before signing. Version/build overrides must come from the root-verified release configuration.

The app includes a 1024 × 1024 RGB icon with no alpha channel. Its privacy manifest declares no tracking or collected data and declares app-local UserDefaults access (`CA92.1`) for the language setting. The reviewed shipping inventory contains no advertising, analytics or third-party SDK. Compiled resource inclusion and final App Privacy answers remain distinct checks. Do not add an ad SDK or claim advertising is active from a separate preparation.

The bilingual public pages have been reconciled with the verified separate website branch; see `docs/README.md` and `public-docs-reconciliation.json`. Current live pages, approved public contact information, localized store metadata, accurate native screenshots and App Store account state still need real evidence. Public GitHub issues do not establish all Support URL contact requirements.

Apple's current upload minimum, checked 17 November 2026, is Xcode 26 with the iOS 26 SDK or later, and an iOS deployment target of at least 13. This source's deployment target meets that floor; the actual archive toolchain must be established from the release receipt. Do not confuse an SDK requirement with a requirement to raise the deployment target. The updated age-rating questionnaire must also be completed in the store record.

Apple currently requires screenshots for iPhone and, for this iPad-capable app, iPad 13-inch support. Screenshots must show the actual app and match accepted dimensions; audit crops and HTML previews are not store screenshots. Final screenshot acceptance remains unverified here.

Primary references checked 17 November 2026:

- [Current upload and age-rating requirements](https://developer.apple.com/news/upcoming-requirements/)
- [Upload builds and processing](https://developer.apple.com/help/app-store-connect/manage-builds/upload-builds/)
- [Screenshot specifications](https://developer.apple.com/help/app-store-connect/reference/app-information/screenshot-specifications/)
- [App icon configuration](https://developer.apple.com/help/app-store-connect/manage-app-information/add-an-app-icon)
- [App Privacy information](https://developer.apple.com/help/app-store-connect/manage-app-information/manage-app-privacy)
- [Support URL and localized metadata](https://developer.apple.com/help/app-store-connect/reference/app-information/platform-version-information/)
- [Required reason APIs](https://developer.apple.com/documentation/bundleresources/describing-use-of-required-reason-api)
