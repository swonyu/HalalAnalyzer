# HalalTag R6: preserve Arabic ingredient boundaries

R6 adds the Arabic semicolon (`؛`, U+061B) to the existing ingredient-entry separators. The previous list separated ASCII semicolons and Arabic commas but allowed tokens on opposite sides of an Arabic semicolon to form an additive code or a phrase. It also allowed a qualifier in one entry to affect a separate entry.

The only shipping-code change is that additional separator character. The frozen R5 candidate and its existing packages remain preserved. R6 does not expand the English ingredient list or introduce general Arabic ingredient-name recognition.

Nine new model assertions cover ASCII and Arabic semicolon controls: split E120/E471 codes, a split vanilla-extract phrase, prefix/suffix qualifiers across an entry boundary, and valid within-entry matches. Every pre-existing model assertion remains. These assertions have been prepared but have not been executed in the cloud, which has no Swift compiler.

The native adapter runs the sealed Foundation-only model harness before the QA build, within the same root-owned lock and 35-minute window. It uses a unique binary/module-cache directory, retains compilation and execution output, requires successful commands and all nine new check labels, and binds the result to all three compiled source files. Its lifecycle, simulator settings, original nineteen UI methods, assertions, no-retry policy and cleanup reserve remain unchanged.

The original nineteen UI cases remain compulsory. R4's failed/incomplete result and the unexecuted R5 package are not R6 acceptance. The newly added model checks are also separate from UI accessibility and production signing acceptance.

Exact planned Mac source location:

`/Users/saleh/Library/Caches/Publishing-Continuation-20261117-d597fc87411f/HalalTag/Production-Composition-R6-d57f4cd77813/preparation/Source`

The coordinator must verify current ownership and use a fresh exact acknowledgment. Original cutoff: **17 November 2026 22:26:12 UTC**. No new native slot, budget reset, signing, upload or publication is authorized by this preparation itself.
