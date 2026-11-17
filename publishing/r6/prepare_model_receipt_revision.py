#!/usr/bin/env python3
"""Copy frozen R6 and repair only its overbroad model-label receipt guard."""
from pathlib import Path
import argparse
import ast
import difflib
import hashlib
import json
import shutil
import subprocess

CANDIDATE = "f2c27c9271da3a17bb01c50b6cdad94643e1d0f2"
PARENT_ADAPTER = "49c1d9dd1635f4fe1820d88a806c53fa28df20b122766239d9a1f6de085e10bf"
SEAL = "2da71c3c9e9da9a472af9fdd380ad7585164ccbf5da7de0e8156007b7d589464"


def sha(path):
    assert path.is_file() and not path.is_symlink()
    return hashlib.sha256(path.read_bytes()).hexdigest()


def dump(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--parent-preparation", type=Path, required=True)
    parser.add_argument("--repository", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    parent, repo, out = (p.resolve() for p in (args.parent_preparation, args.repository, args.output))
    assert sha(parent / "run_halaltag_native_qa.py") == PARENT_ADAPTER
    assert sha(parent / "sealed-project-inputs.json") == SEAL
    reference = json.loads((parent / "reference-inputs.json").read_text())
    assert reference["candidate_commit"] == CANDIDATE
    rows = json.loads((parent / "sealed-project-inputs.json").read_text())["files"]
    assert len(rows) == 47 and not out.exists()
    for row in rows:
        path = parent / "Source" / row["path"]
        assert sha(path) == row["sha256"] and path.stat().st_size == row["bytes"]
        assert path.read_bytes() == subprocess.check_output([
            "git", "-C", str(repo), "show", CANDIDATE + ":" + row["path"]])
    assert not any(p.is_symlink() for p in parent.rglob("*"))
    shutil.copytree(parent, out)
    before = (parent / "run_halaltag_native_qa.py").read_text()
    old = "require(len(set(checks)) == len(checks) and set(boundary_checks) <= set(checks),"
    new = "require(all(checks.count(label) == 1 for label in boundary_checks),"
    assert before.count(old) == 1
    after = before.replace(old, new)
    ast.parse(after)
    (out / "run_halaltag_native_qa.py").write_text(after)
    (out / "adapter-from-r5.diff").rename(out / "predecessor-adapter-from-r5.diff")
    (out / "adapter-from-r6.diff").write_text("".join(difflib.unified_diff(
        before.splitlines(True), after.splitlines(True), fromfile="r6/run_halaltag_native_qa.py",
        tofile="r6b/run_halaltag_native_qa.py")))
    ack = json.loads((out / "coordinator-acknowledgment-UNCONFIGURED.json").read_text())
    assert ack["acknowledged"] is False
    ack.update(adapter_sha256=sha(out / "run_halaltag_native_qa.py"),
        preparation_revision="R6b-model-receipt-guard",
        note="UNCONFIGURED R6b adapter-only repair; same frozen f2 candidate and forty-seven-file seal. Root must configure a fresh serial slot and the exact R6b Source path. Original budget and cutoff remain.")
    dump(out / "coordinator-acknowledgment-UNCONFIGURED.json", ack)
    reference.update(preparation_revision="R6b-model-receipt-guard",
        receipt_guard_parent_adapter_sha256=PARENT_ADAPTER,
        preserved_r6_native_run="20261117T151221Z-4519-57fb808fc2",
        preserved_r6_observation="Real model compilation and execution exited zero with 211 passing checks; the adapter then rejected a repeated legacy label before UI execution.",
        current_model_regression_execution="NOT_RUN", current_native_execution="NOT_RUN")
    dump(out / "reference-inputs.json", reference)
    shutil.copyfile(repo / "publishing/r6/R6B-ADAPTER.md", out / "HANDOFF.txt")
    assert sha(out / "sealed-project-inputs.json") == SEAL
    for row in rows:
        assert sha(out / "Source" / row["path"]) == row["sha256"]
    print(json.dumps({"candidate_commit": CANDIDATE, "preparation_revision": "R6b-model-receipt-guard",
        "sealed_index_sha256": SEAL, "adapter_sha256": sha(out / "run_halaltag_native_qa.py"),
        "source_files": len(rows), "native_execution": "NOT_RUN", "acknowledged": False}, indent=2))


if __name__ == "__main__":
    main()
