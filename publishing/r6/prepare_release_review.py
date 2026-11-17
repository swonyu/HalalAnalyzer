#!/usr/bin/env python3
"""Prepare exact R6 shipping source and release adapters; execute no release stage."""
from pathlib import Path
import argparse
import ast
import difflib
import hashlib
import json
import re
import shutil
import subprocess

CANDIDATE = "f2c27c9271da3a17bb01c50b6cdad94643e1d0f2"
NATIVE_SEAL = "2da71c3c9e9da9a472af9fdd380ad7585164ccbf5da7de0e8156007b7d589464"
NATIVE_ADAPTER = "92e8acefece9e3cc297e7c1600673ca0673976337a8e90559ab063794b6848a5"
NATIVE_PACKAGE = "5e5e507fda4032965aad6c159f125ec5e0ff03465624a99091bf401157ecd102"
PARENT_PINS = {
    "production-manifest.json": "52d699ffb591489c330497f2e8a4af9da3683b8d728130dea2049d244321a6d6",
    "release_support.py": "931ec0e2d74bd9df21f418ade88758f70806bdc03fa00ced250ab09b9de3f872",
    "run_release_stage.py": "b9e4fa24f976e20c0e14c812a71a09ce187ccd7ee0c6bb3a6a12a9ecd3c73316",
    "publishing_runner_frozen.py": "1980cdf5a564a802198183fd79ee2f0a325b486908bab45e01beaadb02e50f99",
    "native_coordination_frozen.py": "243dc8943a5d91ed3a26673223f862a4f30a1c8b0a35088e7476d02ea4f78c6c",
}


def sha(path):
    assert path.is_file() and not path.is_symlink(), str(path)
    return hashlib.sha256(path.read_bytes()).hexdigest()


def dump(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def rebind(text, key, value):
    text, count = re.subn(r"^" + key + r" = '[0-9a-f]+'", key + " = '" + value + "'", text, flags=re.M)
    assert count == 1, key
    return text


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--parent-preparation", type=Path, required=True)
    parser.add_argument("--native-preparation", type=Path, required=True)
    parser.add_argument("--native-source-mac", type=Path, required=True)
    parser.add_argument("--repository", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    parent, native, repo, out = (p.resolve() for p in
                                (args.parent_preparation, args.native_preparation, args.repository, args.output))
    assert args.native_source_mac.is_absolute() and args.native_source_mac.name == "Source"
    assert args.native_source_mac.as_posix().startswith("/Users/saleh/Library/Caches/")
    assert ".." not in args.native_source_mac.parts
    for name, expected in PARENT_PINS.items():
        assert sha(parent / name) == expected, name
    assert sha(native / "sealed-project-inputs.json") == NATIVE_SEAL
    assert sha(native / "run_halaltag_native_qa.py") == NATIVE_ADAPTER
    reference = json.loads((native / "reference-inputs.json").read_text())
    assert reference["candidate_commit"] == CANDIDATE
    seal = json.loads((native / "sealed-project-inputs.json").read_text())
    assert seal["scope"] == "halaltag-production-composition-nineteen-journeys-r6"
    sealed = {row["path"]: row for row in seal["files"]}
    assert len(sealed) == 47
    for relative, row in sealed.items():
        source = native / "Source" / relative
        assert sha(source) == row["sha256"] and source.stat().st_size == row["bytes"], relative
    manifest = json.loads((parent / "production-manifest.json").read_text())
    assert len(manifest["source_files"]) == manifest["source_file_count"] == 14
    assert not out.exists(), "Create a new preparation; preserve prior artifacts"
    out.mkdir(parents=True)
    for row in manifest["source_files"]:
        relative = row["path"]
        path = Path(relative)
        assert not path.is_absolute() and ".." not in path.parts
        source = native / "Source" / path
        committed = subprocess.check_output(["git", "-C", str(repo), "show", CANDIDATE + ":" + relative])
        assert source.read_bytes() == committed, relative
        assert relative in sealed
        destination = out / "ProductionSource" / path
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, destination)
        row.update(sha256=sha(destination), bytes=destination.stat().st_size)
        row["identical_to_git_base"] = row["sha256"] == row["git_base_sha256"]
    manifest.update(scope="halaltag-production-release-r6b", preparation_revision="R6b-model-receipt-guard", executing_continuation="d57f4cd77813")
    manifest["git_provenance"] = {
        "shipping_candidate_commit": CANDIDATE,
        "recovered_r4_commit": "44df4e1438d26780f52c349348224998df4482b9",
        "remote_r3_base_commit": "4633d6d6179f194bdc3d7b74b01041aca360f598",
        "source_origin": "The fourteen shipping files in the immutable R6 native review preparation",
        "native_source_file_count": 47,
        "native_candidate_seal_sha256": NATIVE_SEAL,
        "subsequent_documentation_changes_copied": False,
        "parent_release_manifest_sha256": PARENT_PINS["production-manifest.json"],
    }
    gate = manifest["native_gate"]
    gate.update(required_scope=seal["scope"], sealed_index_sha256=NATIVE_SEAL,
                content_sha256=reference["content_view_sha256"],
                run_root="/Users/saleh/Library/Caches/HalalTag-ProductionCompositionR6-NativeQA",
                source_root=args.native_source_mac.as_posix())
    gate.pop("source_full_zip_sha256", None)
    gate["native_review_zip_sha256"] = NATIVE_PACKAGE
    gate["native_adapter_sha256"] = NATIVE_ADAPTER
    model_sources = ["HalalAnalyzer حلال ام حرام؟/IngredientScreening.swift",
                     "HalalAnalyzer حلال ام حرام؟/ScreeningLocalization.swift",
                     "Tests/Model/BilingualModelChecks.swift"]
    gate["model_source_binding"] = {relative: sealed[relative] for relative in model_sources}
    gate["required_model_check_labels"] = [label + separator for separator in (";", "؛") for label in (
        "Separated entries cannot form an additive code: ",
        "Separated entries cannot form a multiword ingredient: ",
        "A qualifier in an earlier entry cannot suppress a direct term: ",
        "A qualifier in a later entry cannot suppress a direct term: ",
    )] + ["Arabic semicolons preserve valid within-entry terms and phrases"]
    native_plan = json.loads((native / "Source/Tests/NativeQA/nineteen-case-plan.json").read_text())
    assert gate["case_plan"] == native_plan["cases"]
    assert len(gate["case_plan"]) == 19
    dump(out / "production-manifest.json", manifest)
    support = (parent / "release_support.py").read_text().replace("HalalTag R5", "HalalTag R6b")
    support = support.replace("isolated R5 run report", "isolated R6b run report")
    support = support.replace("Exact R5 native acceptance", "Exact R6b native acceptance")
    support = rebind(support, "MANIFEST_SHA", sha(out / "production-manifest.json"))
    fragment = (repo / "publishing/r6/model-release-gate.txt").read_text()
    hook = "def validate_native_gate(report_path, spec):"
    assert support.count(hook) == 1 and "def validate_model_gate(" not in support
    support = support.replace(hook, fragment + "\n\n" + hook)
    hook = "    inventory_path = root / 'verified-nineteen-test-inventory.json'"
    assert support.count(hook) == 1
    support = support.replace(hook, """    require(report.get('acknowledgment', {}).get('adapter_sha256') == gate['native_adapter_sha256'],
            'Native adapter identity differs from the reviewed R6 model runner')
    model = validate_model_gate(root, report, gate)
""" + hook)
    hook = "            'proof_hashes': proofs, 'scope': gate['required_scope']}"
    assert support.count(hook) == 1
    support = support.replace(hook, "            'proof_hashes': proofs, 'model_checks': model, 'scope': gate['required_scope']}")
    (out / "release_support.py").write_text(support)
    runner = (parent / "run_release_stage.py").read_text().replace("HalalTag-ProductionReleaseR5", "HalalTag-ProductionReleaseR6b")
    runner = rebind(runner, "SUPPORT_SHA", sha(out / "release_support.py"))
    (out / "run_release_stage.py").write_text(runner)
    for name in ["publishing_runner_frozen.py", "native_coordination_frozen.py",
                 "release-configuration-UNCONFIGURED.json"]:
        shutil.copyfile(parent / name, out / name)
    for stage in ["unsigned-archive", "developer-archive", "distribution-export"]:
        name = "acknowledgment-" + stage + "-UNCONFIGURED.json"
        acknowledgment = json.loads((parent / name).read_text())
        assert acknowledgment["acknowledged"] is False
        acknowledgment.update(scope=manifest["scope"], executing_continuation="d57f4cd77813",
            adapter_sha256=sha(out / "run_release_stage.py"),
            support_sha256=sha(out / "release_support.py"),
            production_manifest_sha256=sha(out / "production-manifest.json"),
            note="UNCONFIGURED R6b file-only preparation. Root must bind an actual accepted R6b model and nineteen-case report, exact stage, fresh serial slot, current store identity and authorized Apple communication. No upload action exists.")
        dump(out / name, acknowledgment)
    diffs = []
    for name in ["release_support.py", "run_release_stage.py"]:
        before, after = (parent / name).read_text(), (out / name).read_text()
        ast.parse(after, filename=name)
        diffs.extend(difflib.unified_diff(before.splitlines(True), after.splitlines(True),
                                        fromfile="r5/" + name, tofile="r6b/" + name))
    (out / "adapter-from-r5.diff").write_text("".join(diffs))
    shutil.copyfile(repo / "publishing/r6/RELEASE-ADAPTER.md", out / "HANDOFF.md")
    receipt = {"status": "FILE_ONLY_PREPARATION_NO_STAGE_EXECUTED",
        "preparer_sha256": sha(Path(__file__)),
        "shipping_candidate_commit": CANDIDATE, "shipping_file_count": 14,
        "all_shipping_files_equal_frozen_native_source_and_git_commit": True,
        "native_source_seal_sha256": NATIVE_SEAL, "native_source_file_count": 47,
        "all_nineteen_case_specifications_unchanged": True,
        "native_source_mac": args.native_source_mac.as_posix(),
        "parent_release_pins": PARENT_PINS,
        "current_pins": {name: sha(out / name) for name in PARENT_PINS},
        "original_budget_and_cutoff_preserved": True,
        "native_pass_required_before_any_archive": True,
        "exact_model_receipt_required_before_any_archive": True,
        "native_stage_invoked": False, "release_adapter_invoked": False,
        "signing_performed": False, "upload_performed": False,
        "configured_acknowledgment_created": False}
    dump(out / "preparation-review.json", receipt)
    print(json.dumps(receipt, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
