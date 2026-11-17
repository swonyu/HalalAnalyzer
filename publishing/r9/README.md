# HalalTag R9 reviewed-source successor

R9 is an isolated successor of frozen R8 `f2cd50817dbb0918e8ce85c6e47d31b337a6e25c`. It is **not compiled or native-tested** yet. The original R8 package, run and images remain unchanged.

## Observed R8 result

R8 finished at 2026-11-17T19:14:41.978979Z with 211 model checks passing and 15 of 19 native methods passing. The four failures were English and Arabic light/normal privacy-Link contrast, English AX5 external navigation after a gutter drag, and Arabic AX5 left-gutter collision with the editor's native scroll indicator. The final batch rejected the incomplete UI pass count. All 19 methods actually ran. Appearance/content size were restored exactly to light/large, the owned simulator was shut down, cleanup completed and the lock was released. The report has no literal cleanup_safe property; the individual fields are retained in r8-failure-review.json.

The original Link audit crops show the fixed Done action after a viewport shift; they do not measure the Link's glyphs. Independently, the original pre-audit sRGB pixels contain RGB(0,136,255) link text on white, a measured 3.5201447457:1 ratio. Default 17pt regular body is inferred from source, not a runtime font measurement. Native audits remain decisive.

## Product repair

Only four lines are added to ContentView:
- Both existing underlined Link labels use semantic primary foreground; URLs, wrapping, 44pt minimum, hints and Link semantics remain.
- NativeScreeningMatchText and NativeScreeningHeading set actual UILabel alignment from selected UI language in updateUIView. Copy, native font/Dynamic Type, size measurement, traits and RTL semantics remain.

## Gesture repair and evidence

The two bilingual drag helpers now measure both content gutters. Every real Button and Link is included in the obstacle inventory, alongside actual editor and native-indicator frames. Buttons retain a 2pt measured edge margin; Links receive a larger 24pt exclusion after R8 activated one from 9pt outside its AX text frame. These margins are guarded routing hypotheses, not a claim to know undocumented system hit regions.

Each gutter records its actual bounds and safe vertical intervals, with a further 2pt boundary clearance. The longest available requested travel wins; if only a shorter safe interval exists, requested_travel and selected_travel remain distinct. The actual gesture, before/after frames and captures, direction, endpoint coordinates and operation budget are retained. The guard independently reconstructs both gutters, expanded obstacles and route selection. A clipped control, an unsafe route, missing interval, forged frame chain or failed audit still fails.

All 19 method bodies, original unfiltered combined audits, continuous reading and final-exposure assertions remain. The existing 168-gesture/400-capture case bounds, operation limits, 45-minute batch, 120-second cleanup reserve, 20-minute per-case bound and zero retries remain. Shorter routes can exhaust the existing finite budget; such exhaustion must be reported, never converted to a pass.

## Verification and next gate

Eight pure-Python evidence tests pass, including all five prior geometry regressions and three new actual-pose/short-travel regressions. The 92 source composition checks pass. Product and Swift drag received independent file-only reviews; the new evidence guard review is tracked separately. None of these is native acceptance.

The preparation script is file-only and requires a clean committed candidate. It copies only explicitly pinned R8 runtime/support inputs, never the old actual acknowledgment, and seals exactly 47 source files. Historical adapter diffs remain in the unchanged R8 package/Git history; the new package contains the current R8-to-R9 diffs.

Root owns native scheduling, staging, actual acknowledgment, build, signing, upload and push. Required next acceptance is the complete sealed 211-model/19-UI run, current Arabic/English normal and AX5 screenshots, then production release gates. No store release is claimed.

Original cutoff: 2026-11-17T22:26:12Z. Explicit user extension: +24 hours to 2026-11-18T22:26:12Z. The work budget was not restarted.
