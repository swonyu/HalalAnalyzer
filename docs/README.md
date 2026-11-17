# HalalTag bilingual privacy and support pages

These pages describe the on-device text-screening feature with English and Arabic controls. Their policy date is 17 November 2026. The app behavior was compared with frozen native candidate `be0b7ab202c38d81aab6a908cd69902c18b5ded9`; this source comparison does not establish native acceptance, signing, upload or release.

The described app keeps ingredient text and results transient and saves only the interface language preference in its app-local settings. It includes no account flow, remote screening API, camera/OCR/barcode feature, advertising SDK or analytics SDK. Its limited matching list does not establish halal status. Arabic controls do not add general Arabic ingredient matching. Separate device services, GitHub Pages logging and public support requests are explained in both languages.

## Page map

| Purpose | English | Arabic |
| --- | --- | --- |
| Privacy and limitations | `index.html` | `privacy-ar.html` |
| Support | `support.html` | `support-ar.html` |

The pages use system fonts, logical RTL styles, visible keyboard focus, a skip link, wrapping navigation, 44px navigation targets, and light/dark color schemes. They contain no JavaScript, form, analytics or external asset. Existing English entry points link to their Arabic counterparts. The app's frozen native candidate opens the English entry points; the page language controls provide Arabic access.

## Verified website branch and app documentation mirror

On 17 November 2026, the current `swonyu/HalalAnalyzer` website branch `docs/public-support-20261117-01a49` was read at commit `d86eb20622a0f2c06d2ae238de2ca7fa20e61eb4`. It is an orphan branch with six files at its **root**: `.nojekyll`, four HTML pages and `styles.css`. It has no `/docs` directory. Do not merge this unrelated root over the app source or restore the earlier site-preparation instructions.

The five HTML/CSS files in this app repository's `docs/` directory match that verified branch byte for byte. They also match the recovered `halaltag-public-pages-r2/docs` package. The exact Git blob and SHA-256 comparison is recorded in `publishing/r5/public-docs-reconciliation.json`. This documentation reconciliation preserves the website's separate role and does not publish or reconfigure it.

The existing public entry points are <https://swonyu.github.io/HalalAnalyzer/> and <https://swonyu.github.io/HalalAnalyzer/support.html>. Branch contents alone do not establish which Pages branch/path is configured or which bytes are live. Before a website operation, verify the current Pages configuration and actual HTTPS contents, preserve the existing host and `.nojekyll`, and compare the latest remote head again. Do not redeploy an older preparation solely because it exists locally.

## Source and store checks

1. Verify the accepted and signed candidate still matches the documented input/result and language-setting behavior. Any SDK or data-handling change requires a corresponding policy and App Privacy review.
2. Verify the actual English and Arabic HTTPS pages, local links, public issue destination, RTL and text reflow before binding localized App Store URLs. A branch commit or local render is not a deployment receipt.
3. Keep public support information accurate. The existing channel, <https://github.com/swonyu/HalalAnalyzer/issues/new>, requires GitHub sign-in and makes requests public. The pages promise no response time, confidentiality or removal guarantee.

## Public contact information still needs verification

The public issue channel is a real support route. It does not by itself establish the public contact information described in Apple's Support URL requirements, such as a legal address, email address or telephone number as applicable. An approved additional public contact has not been established in this continuation. Do not publish private account or App Review contact information, or invent contact details. Verify the developer's approved public contact before reporting this store requirement as complete.

Primary references: [Apple platform version information](https://developer.apple.com/help/app-store-connect/reference/app-information/platform-version-information/), [GitHub Pages data collection](https://docs.github.com/en/pages/getting-started-with-github-pages/what-is-github-pages#data-collection), and [GitHub Privacy Statement](https://docs.github.com/en/site-policy/privacy-policies/github-general-privacy-statement).
