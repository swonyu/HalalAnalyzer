#!/usr/bin/env python3
"""Prepare a new review package without native execution or shared mutations."""
from pathlib import Path
import argparse
import difflib
import hashlib
import json
import re
import shutil
import subprocess

PARENT_COMMIT = "be0b7ab202c38d81aab6a908cd69902c18b5ded9"
PARENT_ADAPTER = "b03259fe1de451149ffa82b856abff33003cdead1fd6480475e8e2c6ffd3c2e1"
PARENT_SEAL = "4006359aa30c81ba088c2b3fcfbae6a403d2c3a33583c8b6db501db2883bc2aa"
OLD_ID = "com.saleh.halaltag.productioncomposition.qa.r20261117r5"
NEW_ID = "com.saleh.halaltag.productioncomposition.qa.r20261117r6"
OLD_SCOPE = "halaltag-production-composition-nineteen-journeys-r5"
NEW_SCOPE = "halaltag-production-composition-nineteen-journeys-r6"
CONTENT = "HalalAnalyzer حلال ام حرام؟/ContentView.swift"
MODEL = "HalalAnalyzer حلال ام حرام؟/IngredientScreening.swift"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def dump(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--parent-preparation", required=True, type=Path)
    parser.add_argument("--repository", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    base, repo, out = (p.resolve() for p in
                       (args.parent_preparation, args.repository, args.output))
    assert sha(base / "run_halaltag_native_qa.py") == PARENT_ADAPTER
    assert sha(base / "sealed-project-inputs.json") == PARENT_SEAL
    subprocess.run(["git", "-C", str(repo), "merge-base", "--is-ancestor",
                    PARENT_COMMIT, "HEAD"], check=True)
    commit = subprocess.check_output(["git", "-C", str(repo), "rev-parse", "HEAD"], text=True).strip()
    status = subprocess.check_output(["git", "-C", str(repo), "status", "--porcelain=v1"], text=True)
    assert not status, "Commit and review the candidate before packaging its source"
    assert not out.exists(), "Output must be a new directory; prior packages are preserved"
    out.mkdir(parents=True)
    original_rows = json.loads((base / "sealed-project-inputs.json").read_text())["files"]
    assert len(original_rows) == 47
    rows = []
    for entry in original_rows:
        relative = Path(entry["path"])
        assert not relative.is_absolute() and ".." not in relative.parts
        source = repo / relative
        assert source.is_file() and not source.is_symlink()
        target = out / "Source" / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
        rows.append({"path": relative.as_posix(), "sha256": sha(target), "bytes": target.stat().st_size})
    dump(out / "sealed-project-inputs.json", {"schema_version": 1,
         "status": "SEALED_PREPARED_SOURCE_ONLY", "scope": NEW_SCOPE, "files": rows})
    content = sha(repo / CONTENT)
    old_content = sha(base / "Source" / CONTENT)
    model = sha(repo / MODEL)
    old_model = sha(base / "Source" / MODEL)
    for name in ["publishing_runner_frozen.py", "appearance_png.py", "system_size_evidence.py",
                 "simctl-ui-help-root-20261117.stderr"]:
        shutil.copyfile(base / name, out / name)
    for name in ["appearance_evidence_guard.py", "arabic_appearance_evidence_guard.py", "production_case_evidence.py"]:
        text = (base / name).read_text()
        assert OLD_ID in text
        (out / name).write_text(text.replace(OLD_ID, NEW_ID))
    original_runner = (base / "run_halaltag_native_qa.py").read_text()
    runner = original_runner.replace(OLD_ID, NEW_ID).replace(OLD_SCOPE, NEW_SCOPE)
    runner = runner.replace("ProductionCompositionR5-NativeQA", "ProductionCompositionR6-NativeQA")
    runner = runner.replace("R5 changes only QA identity", "R6 changes only QA identity")
    fragment = (repo / "publishing/r6/model-check-step.txt").read_text()
    hook = "    def xcode(self) -> list[str]:"
    assert runner.count(hook) == 1 and "def run_model_checks" not in runner
    runner = runner.replace(hook, fragment + "\n" + hook)
    before = '        self.run("xcode-version", ["/usr/bin/xcodebuild", "-version"], self.output, 30)'
    assert runner.count(before) == 1
    runner = runner.replace(before, before + "\n        self.run_model_checks()")
    pins = {"SEAL_SHA": "sealed-project-inputs.json", "EVIDENCE_GUARD_SHA": "appearance_evidence_guard.py",
            "ARABIC_GUARD_SHA": "arabic_appearance_evidence_guard.py", "NINETEEN_GUARD_SHA": "production_case_evidence.py"}
    for key, name in pins.items():
        runner, count = re.subn(r'^' + key + r' = "[0-9a-f]+"', key + ' = "' + sha(out / name) + '"', runner, flags=re.M)
        assert count == 1
    (out / "run_halaltag_native_qa.py").write_text(runner)
    (out / "adapter-from-r5.diff").write_text("".join(difflib.unified_diff(
        original_runner.splitlines(True), runner.splitlines(True),
        fromfile="r5/run_halaltag_native_qa.py", tofile="r6/run_halaltag_native_qa.py")))
    ack = json.loads((base / "coordinator-acknowledgment-UNCONFIGURED.json").read_text())
    assert ack["acknowledged"] is False
    ack.update(scope=NEW_SCOPE, executing_continuation="d57f4cd77813", candidate_content_sha256=content,
               candidate_model_sha256=model,
               note="UNCONFIGURED R6 source package; root must verify ownership, recovery, exact-source pins and a fresh serial native slot. Original budget and cutoff are preserved.")
    for key, name in [("adapter_sha256", "run_halaltag_native_qa.py"),
                      ("sealed_index_sha256", "sealed-project-inputs.json"),
                      ("appearance_guard_sha256", "appearance_evidence_guard.py"),
                      ("arabic_guard_sha256", "arabic_appearance_evidence_guard.py"),
                      ("nineteen_case_guard_sha256", "production_case_evidence.py")]:
        ack[key] = sha(out / name)
    dump(out / "coordinator-acknowledgment-UNCONFIGURED.json", ack)
    (out / "Tests").mkdir()
    (out / "Tests/test_adapter_contract.py").write_text(
        (base / "Tests/test_adapter_contract.py").read_text().replace(OLD_SCOPE, NEW_SCOPE))
    retention = []
    for old in sorted((base / "Source/Tests/NativeQA/UITests").glob("*.swift")):
        relative = old.relative_to(base / "Source")
        current = out / "Source" / relative
        assert current.read_text().replace(model, old_model) == old.read_text(), str(relative)
        retention.append({"path": relative.as_posix(), "parent_sha256": sha(old),
                          "candidate_sha256": sha(current), "all_other_bytes_identical": True})
    dump(out / "source-retention.json", {"status": "SOURCE_ONLY_NOT_NATIVE_TESTED",
         "all_nineteen_method_bodies_unchanged": True,
         "all_assertions_audits_helpers_and_gesture_budgets_unchanged": True, "files": retention})
    reference = json.loads((base / "reference-inputs.json").read_text())
    reference.update(parent_preparation=str(base), parent_scope=OLD_SCOPE,
        candidate_commit=commit, recovered_parent_commit=PARENT_COMMIT,
        prepared_by_continuation="d57f4cd77813", parent_adapter_sha256=PARENT_ADAPTER,
        parent_seal_sha256=PARENT_SEAL, parent_content_view_sha256=old_content,
        content_view_sha256=content, ingredient_screening_sha256=model,
        parent_ingredient_screening_sha256=old_model, model_regression_execution="NOT_RUN", native_execution="NOT_RUN",
        parent_native_result="R5 preserved but not executed; R6 semantic boundary repair supersedes its planned native slot",
        parent_native_run=None,
        last_native_result="R4 incomplete failed run; not acceptance",
        last_native_run="20261117T140443Z-79482-fc201494a8")
    # Do not carry an older patch's digest forward as the candidate patch.
    patch = subprocess.check_output(["git", "-C", str(repo), "diff", PARENT_COMMIT, "HEAD", "--", MODEL])
    (out / "product-from-r5.patch").write_bytes(patch)
    reference["product_patch_sha256"] = hashlib.sha256(patch).hexdigest()
    dump(out / "reference-inputs.json", reference)
    shutil.copyfile(repo / "publishing/r6/README.md", out / "HANDOFF.txt")
    print(json.dumps({"output": str(out), "candidate_commit": commit,
          "scope": NEW_SCOPE, "source_files": len(rows), "content_sha256": content,
          "native_execution": "NOT_RUN", "acknowledged": False}, indent=2))


if __name__ == "__main__":
    main()
