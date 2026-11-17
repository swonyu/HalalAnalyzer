# HalalTag R6b production release preparation

The release source is frozen at `f2c27c9271da3a17bb01c50b6cdad94643e1d0f2`. The preparer takes exactly fourteen shipping files from its sealed forty-seven-file native preparation, checks every shipping byte against that Git commit, and excludes the QA host and tests. Later documentation commits cannot change this source selection.

The parent is the preserved R5 release preparation. R6b changes the candidate identity, native paths, source hashes and resulting integrity pins. Its additional model gate requires the actual successful R6 model receipt, original compiler and executable stdout/stderr with matching hashes, one successful compile and one successful execution in order, the preserved executable hash, and the exact model, localization and harness source bindings. The actual executable JSON must report passing checks and all nine semicolon regressions exactly once. Older model check labels may repeat, as the actual 211-check R6 stdout established; the failed R6 adapter imposed an invalid global uniqueness requirement. R6b repairs only that receipt rule while preserving the source. Missing, substituted or changed model evidence prevents every release stage.

All existing nineteen-case UI requirements remain: exact original methods and case order, nineteen passed with no failures, skips, expected failures or runtime warnings, original result bundles and bound evidence, seventeen distinct supplementary launches, exact shipping sources, completed cleanup and a released lock. The model result alone does not establish UI acceptance. R4 failed, R5 was preserved without execution, and R6 stopped after its real model execution because of the receipt-guard defect. None establishes accepted R6b native evidence.

`prepare_release_review.py` only reads and copies files, reads Git objects, parses Python syntax and writes an unconfigured review package. It does not import the release adapter or reserve a slot. `adapter-from-r5.diff` records the exact executable delta. This preparation has not been executed as a release stage.

The root coordinator retains three serial stages: unsigned archive, developer archive and distribution export. The stage implementation, signing and entitlement checks, single-use schedule acknowledgments, twenty-minute stage cap, two-minute cleanup reserve, frozen lifecycle and coordination code remain unchanged. All three acknowledgments and the release configuration remain unconfigured. They must refer to actual current store identity/build evidence, an accepted native report and a fresh root-owned slot inside the original cutoff, **17 November 2026 22:26:12 UTC**.

The exact required native source path is:

`/Users/saleh/Library/Caches/Publishing-Continuation-20261117-d597fc87411f/HalalTag/Production-Composition-R6b-d57f4cd77813/preparation/Source`

Source identity remains `HalalTag.v1.1`, team `WY272L3F3N`, version `1.0`, build `1`, iOS deployment target `26.5`, and iPhone/iPad support. A version or build override must come from the coordinator's verified release configuration. Source configuration does not establish signing, installation, upload or release.

The adapter exports locally and has no upload operation. Current store screenshots, accurate metadata, required contact details, App Privacy answers, age rating, upload/processing, submission, approval and availability remain separate gates. See `STORE-HANDOFF.md` and `store-localizations.json` for the source-bound draft metadata and screenshot acquisition plan when those files are available.
