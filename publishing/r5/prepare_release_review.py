#!/usr/bin/env python3
"""Prepare exact R5 shipping source and release adapters; execute no release stage."""
from pathlib import Path
import argparse
import ast
import difflib
import hashlib
import json
import re
import shutil
import subprocess

CANDIDATE = "be0b7ab202c38d81aab6a908cd69902c18b5ded9"
NATIVE_SEAL = "4006359aa30c81ba088c2b3fcfbae6a403d2c3a33583c8b6db501db2883bc2aa"
NATIVE_ADAPTER = "b03259fe1de451149ffa82b856abff33003cdead1fd6480475e8e2c6ffd3c2e1"
NATIVE_PACKAGE = "03ac50ea28ab57b5ac3d2d11349ec4480bf0777dede19b7cb694171013c90817"
PARENT_PINS = {
    "production-manifest.json": "cb5eef6bf94e5ea8e0fc4f32094c8a62906ce1a284e6b2b0e05aa9f9fbe78a24",
    "release_support.py": "ede14b8d6c338701023b1e79172a73ed7d1f64edb6cd3843c6e83d774f8cbbbd",
    "run_release_stage.py": "a8e2dff8f4628ae1e7bb0ec780d4079ac96e1cb3b84a2faf5016a64bb4c5c68c",
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
    assert seal["scope"] == "halaltag-production-composition-nineteen-journeys-r5"
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
    manifest.update(scope="halaltag-production-release-r5", executing_continuation="d57f4cd77813")
    manifest["git_provenance"] = {
        "shipping_candidate_commit": CANDIDATE,
        "recovered_r4_commit": "44df4e1438d26780f52c349348224998df4482b9",
        "remote_r3_base_commit": "4633d6d6179f194bdc3d7b74b01041aca360f598",
        "source_origin": "The fourteen shipping files in the immutable R5 native review preparation",
        "native_source_file_count": 47,
        "native_candidate_seal_sha256": NATIVE_SEAL,
        "subsequent_documentation_changes_copied": False,
        "parent_release_manifest_sha256": PARENT_PINS["production-manifest.json"],
    }
    gate = manifest["native_gate"]
    gate.update(required_scope=seal["scope"], sealed_index_sha256=NATIVE_SEAL,
                content_sha256=reference["content_view_sha256"],
                run_root="/Users/saleh/Library/Caches/HalalTag-ProductionCompositionR5-NativeQA",
                source_root=args.native_source_mac.as_posix())
    gate.pop("source_full_zip_sha256")
    gate["native_review_zip_sha256"] = NATIVE_PACKAGE
    native_plan = json.loads((native / "Source/Tests/NativeQA/nineteen-case-plan.json").read_text())
    assert gate["case_plan"] == native_plan["cases"]
    assert len(gate["case_plan"]) == 19
    dump(out / "production-manifest.json", manifest)
    support = (parent / "release_support.py").read_text().replace("HalalTag R3", "HalalTag R5")
    support = support.replace("isolated R3 run report", "isolated R5 run report")
    support = support.replace("Exact R3 native acceptance", "Exact R5 native acceptance")
    support = rebind(support, "MANIFEST_SHA", sha(out / "production-manifest.json"))
    (out / "release_support.py").write_text(support)
    runner = (parent / "run_release_stage.py").read_text().replace("HalalTag-ProductionReleaseR3", "HalalTag-ProductionReleaseR5")
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
            note="UNCONFIGURED R5 file-only preparation. Root must bind an actual passed frozen-R5 report, exact stage, fresh serial slot, current store identity and authorized Apple communication. No upload action exists.")
        dump(out / name, acknowledgment)
    diffs = []
    for name in ["release_support.py", "run_release_stage.py"]:
        before, after = (parent / name).read_text(), (out / name).read_text()
        ast.parse(after, filename=name)
        diffs.extend(difflib.unified_diff(before.splitlines(True), after.splitlines(True),
                                        fromfile="r3/" + name, tofile="r5/" + name))
    (out / "adapter-from-r3.diff").write_text("".join(diffs))
    shutil.copyfile(repo / "publishing/r5/RELEASE-ADAPTER.md", out / "HANDOFF.md")
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
        "native_stage_invoked": False, "release_adapter_invoked": False,
        "signing_performed": False, "upload_performed": False,
        "configured_acknowledgment_created": False}
    dump(out / "preparation-review.json", receipt)
    print(json.dumps(receipt, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
