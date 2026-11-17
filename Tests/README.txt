HalalTag production-composition checks

From the repository root, the following performs read-only source checks only:
  PYTHONDONTWRITEBYTECODE=1 python3 Tests/validate_composition.py

It parses both Xcode projects independently, verifies real target membership,
checks unchanged shipping identity/signing/archive settings, verifies the four
reviewed product hashes, compares all original ten method bodies, verifies all
nine executable fixtures, checks explicit nineteen-case ordering and manifests,
and reports the current icon PNG header. It never invokes Xcode, a simulator,
an SDK, a device, Git or a network service. Source checks are not UI evidence.

Tests/Model/BilingualModelChecks.swift is the previously reviewed focused Swift
model suite. It has not been compiled or executed by this cloud composition.
The UI suite is in Tests/NativeQA and intentionally cannot launch without a
separately verified synthetic installation manifest. See its README and exact
nineteen-case plan. Original fixtures and semantic changes are preserved in
Tests/Evidence. No original audit filter, gesture budget or test body is removed.
