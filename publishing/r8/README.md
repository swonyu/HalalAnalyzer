# HalalTag R8: two actual R7 accessibility findings

R7 at `156c5eeb60eb1e06cf369235ed33af265460a9cb` actually finished at
2026-11-17T17:35:58.571065Z: 211 model checks passed, 17/19 native UI tests
passed, two AX5 cases failed, with no skips, expected failures or runtime
warnings. Cleanup restored appearance and text size, shut down its own QA
simulator and released its own lock. It is a failed run, not release acceptance.

The English case failed the original unfiltered contrast/text-clipped/Dynamic
Type audit on the 575-point entry-scope SwiftUI text node in a 479-point safe
viewport. Original pixels do not establish a low-contrast text color. R8 uses
the existing real UILabel wrapper for only that exact paragraph, preserving its
copy, preferred subheadline style, Dynamic Type, RTL and actual accessibility
geometry. This remains a rendering experiment until the same audit passes.

The Arabic case completed evidence and privacy reading, then Clear left the
shorter content completely above the viewport. Its original fatal screenshot
is blank below the navigation bar until the disabled Clear button; the actual
editor exists but has a zero-size frame. R8 gives explicit Clear a guarded
post-layout return to the real surviving input. It cancels stale Screen reveal,
dismisses focus and clears the old reading anchor. The deferred action does
not run after a newer request, new input/result, or fresh editor focus.

No native test method, journey/helper body, audit type, coverage assertion or
gesture budget is changed. Only the exact ContentView source binding and the
fresh isolated QA identity/scope are updated. All 211 model checks and all 19
original native journeys must execute again; source inspection is not a pass.

The original deadline was 2026-11-17T22:26:12Z. The user's explicit additional
24 hours extends it to 2026-11-18T22:26:12Z without resetting the start.
Root remains the sole native/store/browser coordinator. All acknowledgment
templates stay unconfigured. No native/archive/signing/upload has run for R8.
