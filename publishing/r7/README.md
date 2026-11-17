# HalalTag R7: measured visibility and audit recovery

R7 is a native-test-helper successor. All shipping files remain byte-identical to
`f2c27c9271da3a17bb01c50b6cdad94643e1d0f2`; all nineteen top-level UI methods
retain their original bytes. The two functional/state test files and the
combined, unfiltered `contrast`, `textClipped`, `dynamicType` audit are unchanged.
There is no production color change, audit filter, swallowed failure, retry,
reduced text assertion, substituted screenshot, or native execution in this
preparation.

## Evidence that requires this repair

The preserved R6b run `20261117T160346Z-2944-09b5555115` completed at
2026-11-17T16:21:26.839975Z with **211 model checks passing and 16/19 UI cases
passing**. Three UI failures remain failed, not acceptance:

- English AX5: the original four-drag reveal limit stopped at heading y503,
  height137, below viewport y93…556. Every drag had moved249pt. The target began
  at y1499. Privacy content measured9152.5pt; later sections are farther away.
- Arabic AX5: the original unfiltered audit restored text dimensions but rewound
  scroll position by up to523pt. Recovery consumed the original eight-gesture
  match budget. Returning after complete reading also passed that rewind to the
  next child.
- English light: the privacy link ended at606 while the scroll view ended599.
  The audit's issue crop showed the fixed Done overlay. This does not establish
  that the blue link tint is defective. The same contrast gate must run from a
  fully exposed, measured link pose.

`r6b-failure-triage.json` retains exact run/source IDs and original attachment
references/hashes. Root owns the original xcresults; the current folder does not
substitute a report for them. R6b cleanup restored style/size, shut down its own
simulator and released its own lock. A fresh process/owner/lock guard is still
required before any later native launch.

## Measured finite policy

Every reveal, reading operation and audit recovery declares its own budget:
`ceil(measured travel / (0.40 × actual viewport height)) + 2`, limited to64
steps. The0.40 planned fraction is below R6b's observed249/463 and261.5/484.5
progress ratios; the two extra steps allow final measured positioning. These
are finite allowances, not assumptions that every gesture succeeds. Every real
gesture still must progress in the requested direction, stay on the measured
content gutter and avoid the editor and native scroll indicator. Its original
before/after PNG and AX capture indices are retained.

A reveal succeeds only when the complete target or target union lies inside the
actual scroll viewport and each real element is hittable. Its terminal frame is
recorded and the guard rejects a partially exposed completion. Near a privacy
section, a partially visible link is revealed together with both links and the
original heading only when the union fits. The original four section captures
and audits remain. Each real privacy/support Link also receives an explicit full
exposure capture and the unchanged combined audit.

A successful audit's measured scroll displacement has a **separate** recovery
budget. Recovery restores the original relative y position within2pt, with
unchanged text/viewport dimensions, measurable directional progress and
strictly decreasing displacement. It finishes before the reading helper returns,
including the full-text branch. It cannot turn a failed audit into a pass: the
audit throws before any recovery receipt can be produced. The ~10pt drag
threshold observed in R6b only informs the requested motion; actual geometry
and progress remain the acceptance criteria. New native execution must verify
this controller on the pinned runtime.

The case ceiling is explicitly replaced, not described as the old40 limit:

`ceil((2×4406.5 + 9152.5) / (0.40×463)) + 2×17 + 12×ceil(523/(0.40×463)) = 168`.

This bounds two main-document traversals, one privacy traversal, settling for up
to17 control/group reveals, and the measured rewind allowance for the12 minimum
reading/section/link audit poses. Every operation still uses its tighter actual
geometry limit, and every extra reading interval is separately recorded. The
ceiling does not guarantee acceptance if actual geometry or displacement grows;
that case fails for review. Capture ceiling400 equals2×168+64; attachment
ceiling2944 equals8×168+4×400. The existing750MB original-attachment cap and
35-minute batch window, including cleanup, are unchanged.

The pure evidence guards recompute every operation budget, independently count
navigation and recovery, verify continuous intervals against actual frame and
viewport measurements, bind recovery to the original captured pose and actual
first/last motion, and require both full links. They retain source/run/device,
PNG hash, original AX, action, nineteen-method, zero-skip/failure/warning and
cleanup requirements.

## Verification and remaining gate

Five focused synthetic evidence tests reject the observed insufficient/clipped
geometry, an unaccounted gesture, a route through the editor, unrecovered523pt
scroll displacement after full reading, a missing link audit, a skipped interval
and fabricated recovery binding. These tests validate rejection logic; they are
not screenshots or UI passes. The static composition check preserves all
nineteen method bodies and unrelated helpers and verifies all shipping source
pins. Exact receipts are in this folder after execution.

Native compilation, all nineteen UI cases, physical/VoiceOver/iPad checks,
production archive/signing/store upload/review/release remain separate actual
gates. Root is the sole native/store coordinator. The installation and
coordinator acknowledgments remain UNCONFIGURED until root verifies a new
exclusive slot and exact source/package pins.

The original deadline is2026-11-17T22:26:12Z. The user's explicit additional24h
extends it to2026-11-18T22:26:12Z. The original start/budget history is preserved;
no deadline restart is implied.
