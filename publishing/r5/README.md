# HalalTag R5 privacy text rendering repair

Status: source prepared; native acceptance is pending.

## Recovered R4 evidence

The recovered R4 source is commit `44df4e1438d26780f52c349348224998df4482b9`,
whose parent is `4633d6d6179f194bdc3d7b74b01041aca360f598`. Its preservation
bundle is 7,975 bytes with SHA256
`08f41c409e7018ac186028bfc02eda2682d3ecd3b83154d7b71906dcecca14ba`.

The Mac run `20261117T140443Z-79482-fc201494a8` supersedes R4's older
not-run preparation notes. Its QA target compiled and installed. The English
dark-large and light-large methods both failed the unfiltered accessibility
audit with `Contrast failed for SwiftUI.AccessibilityNode`. The remaining
17 methods did not run after a simulator setting command timed out. The terminal
report records exit 2, `cleanup_complete: false` and a retained native build
lock. This is neither a 19-case pass nor a production archive.

The official failed-element PNGs are `668613C9-0DAE-4CF0-9596-02D8A22B8940.png`
(dark) and `10B711B2-3C6C-431B-BB8C-55D312664E3B.png` (light), in those cases'
attachments. Both show the top toolbar area instead of a readable paragraph.
The last attached AX trees place “Your text and privacy” above the scroll
viewport: y 27–49.5 in dark mode and y 9–31.5 in light mode, while the actual
scroll viewport starts at y 91. These observations identify a discrepancy
between the scrolling text's accessibility representation and its visible
content; they do not establish a numeric contrast ratio or an OS defect.

## Candidate change

Privacy section titles and paragraphs now use the same measured native UILabel
wrappers as the result text. Each label paints the real sheet background,
retains Dynamic Type, natural text alignment, English/Arabic language and
direction, and the heading trait where appropriate. Copy, font styles,
navigation, spacing, actions, parser behavior and persistence are unchanged.
The original main-screen wrapper defaults are unchanged.

No accessibility frames are overridden. No hidden duplicate label, audit
filter, skip, gesture-budget increase or assertion removal was introduced.
All nineteen native method bodies and interaction helpers are retained. Only
the source hash in the common QA guard is rebound. The dedicated QA identity
and nineteen-case scope advance to R5 so old installation evidence cannot be
mistaken for new acceptance. Its installation resource remains UNCONFIGURED.

The existing source validator passes 85 checks for this candidate. That result
does not prove the rendering repair works. The new native run must retest the
two observed failures and complete the full nineteen-case acceptance suite,
with all actual evidence and cleanup verified by the root coordinator.

## File-only native package preparation

`prepare_native_review.py` accepts the exact preserved R4 preparation, this
repository and a new output directory. It copies the original 47-file source
inventory, retains the frozen lifecycle runner and all test methods, and binds
the existing adapter and evidence guards to the new QA identity and source.
It does not execute a native command or authorize a native slot.

The root coordinator owns serial native builds, recovery of the retained R4
lock, review of the package, signing and all store actions. The original cutoff
remains 18 November 2026 at 01:26:12 Asia/Riyadh (17 November 22:26:12 UTC).
Consumed active engineering hours remain unknown. No new clock is started.

## Additional open integration gates

- The older production release scripts are R3-bound and need a reviewed
  source binding for the accepted candidate before they can archive it.
- The repository's older `docs` still describe an earlier English-only source.
  Preserve and reconcile the separately prepared/pushed bilingual support
  pages, including the saved language preference disclosure.
- Native iPad/physical-device/VoiceOver evidence, signed release identity,
  actual store upload/processing/review/public availability, and advertising
  prerequisites remain separate gates. No such state is claimed here.
