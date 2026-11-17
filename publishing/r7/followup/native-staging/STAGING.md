# Exact R7 native staging from a local Git checkpoint

This package contains only 22 frozen native-support files, their hash inventory,
and a staging script. It does not contain Source, app images, Git credentials or
an executed result. The script reconstructs the 47 exact native inputs from raw
local Git blobs at `156c5eeb60eb1e06cf369235ed33af265460a9cb`; it does not use
HEAD or a mutable branch name. This is the native preparation subset, not the
complete 95-file tracked-source export supplied separately.

The full tree is `a12a81a8fb1a0fe9085fc316aca8d9eedd7bd718`, with parent
`aa7f756e6c4bb5441e6945e4454141756934252f`. All fourteen shipping files remain
byte-identical to `f2c27c9271da3a17bb01c50b6cdad94643e1d0f2`.

## Ref distinction

The native bundle `HalalTag-R7-156c5ee.bundle` advertises exactly
`156c5eeb60eb1e06cf369235ed33af265460a9cb HEAD` and requires parent `aa7f756e`.
It was created before the documentation checkpoint; its bytes are frozen.

The current cloud branch `continuation/publishing-r7-20261117-d57f` now points to
`dda637fd5366aaec35f06a2bd5a1c533b2746a86`. That later commit adds only seven
publication/review files and does not change any of the 47 frozen native inputs.
The separate documentation bundle advertises `dda637fd... HEAD` and requires
`156c5eeb...`. Do not infer the native candidate from current branch HEAD.

Preserve an exact native ref such as:
`refs/heads/continuation/publishing-native-r7-20261117-d57f`.
Do not move or overwrite the existing R6 ref. If the proposed native ref already
exists at another commit, stop and review it rather than forcing an update.

## Root-only import, if the exact commit is absent

Inspect the native bundle's advertised HEAD and prerequisites before import.
The following commands describe the intended action; the stager itself never
imports a bundle, changes a ref, performs a push or contacts a network.

```sh
git --git-dir=/Users/saleh/Library/Caches/Publishing-Continuation-20261117-d597fc87411f/Recovery-d57f4cd77813/GitCheckpoint/halaltag.git bundle verify /ABSOLUTE/PATH/HalalTag-R7-156c5ee.bundle
git bundle list-heads /ABSOLUTE/PATH/HalalTag-R7-156c5ee.bundle
```

Verify the advertised HEAD is exactly `156c5eeb...` and the destination native
ref is absent (or already identical). Only then root may import with an explicit
refspec, without force:

```sh
git --git-dir=/Users/saleh/Library/Caches/Publishing-Continuation-20261117-d597fc87411f/Recovery-d57f4cd77813/GitCheckpoint/halaltag.git fetch --no-tags --no-write-fetch-head /ABSOLUTE/PATH/HalalTag-R7-156c5ee.bundle HEAD:refs/heads/continuation/publishing-native-r7-20261117-d57f
```

The fetch does not publish. Root separately owns safe checkpoint publishing and
must verify current remote refs before pushing.

## Reconstruct a fresh preparation

Run from the extracted support package, substituting its actual location:

```sh
python3 -B /ABSOLUTE/PATH/stage_from_git.py \
  --bare-repository /Users/saleh/Library/Caches/Publishing-Continuation-20261117-d597fc87411f/Recovery-d57f4cd77813/GitCheckpoint/halaltag.git \
  --output-preparation /Users/saleh/Library/Caches/Publishing-Continuation-20261117-d597fc87411f/HalalTag/Production-Composition-R7-d57f4cd77813/preparation
```

The script validates the support manifest, exact commit/tree/parent, Git blob
identities, all 47 source SHA-256 digests and sizes, and all 14 unchanged shipping
files before its first destination write. It rejects symlinks, unexpected
files, parent traversal, an existing preparation or an existing staging receipt.
Files are created exclusively; no existing work is overwritten. If interrupted,
retain the partial staging directory and inspect it; the script refuses to
silently resume or erase it.

The result is `preparation/Source`, the original 22 support files unchanged, and
`STAGING-RECEIPT.json` in the preparation's parent. A staging receipt proves bytes
were reconstructed; it is not a native test, installation or release receipt.
The coordinator acknowledgment remains false and UNCONFIGURED.

## Minimal review before root schedules native work

- Scope: `halaltag-production-composition-nineteen-journeys-r7`.
- QA bundle: `com.saleh.halaltag.productioncomposition.qa.r20261117r7`.
- Shipping bundle: `HalalTag.v1.1`, unchanged.
- All 19 top-level test methods, all shipping f2 bytes and frozen lifecycle remain.
- Only measured visibility/recovery helpers, explicit evidence bounds and QA
  identity change; combined contrast/clipped-text/Dynamic Type audit is unchanged.
- Source seal: `49c63a850d040e6428c90ce8597c742d8df3f7ee7cb0484643ac152787fcea0d`.
- Native adapter: `e0becc1b7320367dc30d8a1187ccf3ebe1d0bec652b34fe50a082d131fae1b4f`.
- English guard: `a64b3d9a7d44cb3d9c905c93d4830205a12c7d3981b28f43b208e4f75753387c`.
- Arabic guard: `b7f7a2bedde6b8637009e175eae12d59723b200780b2c441108a1c2679830259`.
- Nineteen-case guard: `90c8237cba74d0e0e98c9d0e4724af2e96dc858bba7599cc7d09a042c3535e6f`.
- Lifecycle: `1980cdf5a564a802198183fd79ee2f0a325b486908bab45e01beaadb02e50f99`.

Root must freshly check ownership, processes and the native lock before creating
an actual acknowledgment or invoking the adapter. This preparation performs
none of those native actions. Last actual acceptance remains failed R6b:
211 model checks passed, 16/19 UI passed, three failed. R7 is not native-tested.
