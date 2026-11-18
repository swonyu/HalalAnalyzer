#!/usr/bin/env python3
"""Inventory-only hosted preflight; contains no build, test or simulator mutation.

This is an explicit installed-runtime inventory successor after a preserved failed gate.
The default action inspects files only. Hosted inventory requires a root-bound
review, an exact public source tree and a fresh first-attempt GitHub context.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import stat
import subprocess
import sys
import tarfile
import time


HERE = Path(__file__).absolute().parent
SOURCE_COMMIT = "b2d1ea13460fe9a8f3aedc1912f474737a1ec2ed"
SOURCE_TREE = "eaeb5fe8c1c7a7486282a907cc7906e6c3799eba"
BRANCH = "continuation/halaltag-r12-hosted-tooling-v6-d57"
SCOPE = "HALALTAG_R12_XCODE26_SCOPED_DEVICE_TOOLING_INVENTORY_V6"
DEVELOPER_DIR = "/Applications/Xcode_26.6.app/Contents/Developer"
DEADLINE = "2026-11-18T22:26:12Z"
COST_RECEIPT = "378b0128b192d9b57546b2b93a1bd1aaf78b9fd6da0a8dd75f94ed70b2fe3fb6"
ARCHIVE_LIMIT = 20_000_000
UI_HELP_SHA256 = '2fa67269b4a75d4856edcaf9f65ed4bd830bd0ecae95e370173fa8ed2fe87084'
UI_HELP_BYTES = 1776
PLATFORM_REVISION = {'review_scope': 'EXPLICIT_R12_XCODE26_6_IOS26_5_SUCCESSOR_AFTER_PRESERVED_HOSTED27_FAILURES', 'runtime_identifier': 'com.apple.CoreSimulator.SimRuntime.iOS-26-5', 'runtime_version': '26.5', 'runtime_build': '23F77', 'original_runtime_build': '24A5423a', 'original_inventory_run_id': 44346043468, 'original_inventory_run_attempt': 1, 'original_inventory_workflow_commit': '7394b369aaf85fb99830af6ceeb2de4f4c35097e', 'original_inventory_gate': 'FAILED_RUNTIME_BUILD_UNAVAILABLE', 'original_inventory_artifact_id': 14446386073, 'original_inventory_artifact_sha256': '85c3a63040eba18dd325b9f65fe0d1a2e1df4573f8aa70a71c4fb7fa38978d4b', 'original_inventory_inner_archive_sha256': '36f3e7702636819f335bc2aacdc4b05f427fa93024ee850128ad89da7d3b37ee', 'xcode_version': '26.6', 'xcode_build': '17F113', 'sdk_version': '26.5', 'macos_major': '26', 'runner_label': 'macos-26', 'developer_dir': '/Applications/Xcode_26.6.app/Contents/Developer', 'original_shipping_minimum_ios_version': '26.5', 'prior_installed_runtime_identifier': 'com.apple.CoreSimulator.SimRuntime.iOS-27-0', 'prior_installed_runtime_build': '24A434', 'prior_installed_runtime_inventory_run_id': 44348679786, 'preserved_hosted27_native_failures': [{'run_id': 44366149496, 'run_attempt': 1, 'source_commit': '7ef009beb0c1f6f355eeceb931d899553ea8cad5', 'workflow_commit': '3617bb12b347244ec1e97f3b82f29bd2ba2e5e3a', 'report_sha256': '38e1be44c83ebdd088d691d908d29fad2b627d4f6247c94b9048779ea5638b20', 'failed_step': 'actual-ui-help', 'ui_cases_run': 0, 'complete_native_evidence_delivered': False}, {'run_id': 44371048297, 'run_attempt': 1, 'source_commit': '7ef009beb0c1f6f355eeceb931d899553ea8cad5', 'workflow_commit': 'b1ef5d7fe1eed9b2db25fb521b117a04d1868d8c', 'report_sha256': '37b479c6245d7d969680d323be351d1f1b02e6677c22a3588c7027163b9ac32d', 'failed_step': 'retain-original-setting-destination', 'ui_cases_run': 0, 'complete_native_evidence_delivered': False}], 'alternative_observation': {'repository': 'swonyu/ahmad-career', 'native_run_id': 44341452115, 'native_run_attempt': 2, 'native_job_id': 134987358820, 'xcode_build_observed': '17F113', 'runtime_build_observed_in_original_runtime_path': '23F77', 'original_sdk_stat_cache_build': '23F81a', 'latest_boot_run_id': 44368339432, 'latest_boot_job_id': 135028031585, 'latest_observed_image': 'macos-26-arm64', 'latest_observed_image_version': '20261112.0504.1', 'halaltag_native_acceptance_transferred': False}, 'runtime_supported_se3_entry_required': True, 'original_ui_help_stderr_sha256': '2fa67269b4a75d4856edcaf9f65ed4bd830bd0ecae95e370173fa8ed2fe87084'}
TOOLING_REVISION = {'per_command_timeout_seconds': 30, 'postboot_performance_or_native_acceptance': False, 'preserved_failure_artifact_id': 14463448814, 'preserved_failure_artifact_sha256': '7df53e2af581105ae6ac8f620277750a4d249dbb881976e56177c1cab1aeea6c', 'preserved_failure_attempt': 1, 'preserved_failure_control_commit': 'b82906dbf93b4cd91e6bc8228641d1e30c06770a', 'preserved_failure_report_sha256': '35012427fab053279efd28f60a6336c2c461bfb948a502d863ce9fd578c68d5b', 'preserved_failure_run_id': 44381758745, 'purpose': 'READ_ONLY_INSTALLED_LIST_HELP_AND_UUID_NAME_FILTER_COMPLETENESS', 'queries': ['device-by-uuid', 'device-by-name'], 'query_source': 'FRESH_FULL_PREBOOT_DEVICE_INVENTORY', 'same_name_across_at_least_two_runtimes_required': True, 'simulator_mutation_authorized': False, 'total_inventory_seconds': 300, 'probe_existing_device_name': 'iPhone 17 Pro', 'probe_existing_device_type': 'com.apple.CoreSimulator.SimDeviceType.iPhone-17-Pro', 'app_native_device_type_unchanged': 'com.apple.CoreSimulator.SimDeviceType.iPhone-SE-3rd-generation', 'probe_device_is_not_app_native_destination': True}
COMMANDS = {
    "git-head": ["git", "rev-parse", "HEAD"],
    "git-parent": ["git", "rev-list", "--parents", "-n", "1", "HEAD"],
    "git-tree": ["git", "ls-tree", "-rz", "--full-tree", "HEAD"],
    "git-status": ["git", "status", "--porcelain=v1", "--untracked-files=all"],
    "xcode-version": ["/usr/bin/xcodebuild", "-version"],
    "iphoneos-sdk": ["/usr/bin/xcrun", "--sdk", "iphoneos", "--show-sdk-version"],
    "iphonesimulator-sdk": ["/usr/bin/xcrun", "--sdk", "iphonesimulator", "--show-sdk-version"],
    "runtime-inventory": ["/usr/bin/xcrun", "simctl", "list", "runtimes", "--json"],
    "device-type-inventory": ["/usr/bin/xcrun", "simctl", "list", "devicetypes", "--json"],
    "device-inventory": ["/usr/bin/xcrun", "simctl", "list", "devices", "--json"],
    "list-help": ["/usr/bin/xcrun", "simctl", "help", "list"],
    "ui-help": ["/usr/bin/xcrun", "simctl", "help", "ui"],
    "process-inventory": ["/bin/ps", "-axo", "pid=,ppid=,comm="],
    "git-status-after": ["git", "status", "--porcelain=v1", "--untracked-files=all"],
}


def require(ok, message):
    if not ok:
        raise ValueError(message)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def unique_pairs(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, "Duplicate JSON key: " + key)
        result[key] = value
    return result


def strict_json(data):
    def reject_constant(value):
        raise ValueError("Nonfinite JSON value: " + value)
    return json.loads(data, object_pairs_hook=unique_pairs, parse_constant=reject_constant)


def read_json(path):
    require(path.is_file() and not path.is_symlink() and path.stat().st_size <= 5_000_000,
            "Missing, linked or oversized JSON: " + str(path))
    return strict_json(path.read_bytes())


def dump(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as handle:
        json.dump(value, handle, indent=2, ensure_ascii=False, sort_keys=True, allow_nan=False)
        handle.write("\n")


def safe_relative(value):
    require(isinstance(value, str) and value and not Path(value).is_absolute()
            and all(part not in ("", ".", "..") for part in value.split("/"))
            and "\\" not in value, "Unsafe relative path")
    return value


def checked_file(root, relative):
    path = root / safe_relative(relative)
    require(path.is_file() and not path.is_symlink(), "Missing or linked file: " + relative)
    for parent in path.parents:
        if parent == root:
            break
        require(not parent.is_symlink(), "Linked parent: " + relative)
    require(stat.S_ISREG(path.stat().st_mode), "Nonregular file: " + relative)
    return path


def candidate_contract(config):
    copy = dict(config)
    for key in ("authorization", "root_review_sha256"):
        copy.pop(key, None)
    return sha(json.dumps(copy, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode())


def inspect_contract(directory):
    config = read_json(directory / "candidate.json")
    require(config.get("scope") == SCOPE and config.get("source_commit") == SOURCE_COMMIT
            and config.get("source_tree") == SOURCE_TREE, "Source/scope contract differs")
    require(config.get("native_build_test_archive_authorized") is False
            and config.get("runner_label") == "macos-26"
            and config.get("repository") == "swonyu/HalalAnalyzer"
            and config.get("branch") == BRANCH, "Only the reviewed inventory lane is supported")
    require(config.get("developer_dir") == DEVELOPER_DIR and config.get("deadline") == DEADLINE
            and config.get("artifact_byte_limit") == ARCHIVE_LIMIT
            and config.get("retention_days") == 1 and config.get("additional_spend_usd") == 0
            and config.get("private_zero_spend_receipt_sha256") == COST_RECEIPT,
            "Unreviewed platform/deadline/cost policy")
    require(config.get("platform_revision") == PLATFORM_REVISION,
            "Unreviewed installed-runtime successor or missing preserved original failure")
    require(config.get("expected_ui_help_stderr_sha256") == UI_HELP_SHA256
            and config.get("expected_ui_help_stderr_bytes") == UI_HELP_BYTES,
            "Unreviewed exact UI-help syntax contract")
    expected_help = checked_file(directory, "expected-simctl-ui-help.stderr").read_bytes()
    require(len(expected_help) == UI_HELP_BYTES and sha(expected_help) == UI_HELP_SHA256,
            "Preserved exact appearance/content-size UI-help bytes differ")
    require(config.get("tooling_revision") == TOOLING_REVISION,
            "Unreviewed read-only scoped tooling contract")
    for name, key in (("source-index.json", "source_index_sha256"),
                      ("coverage-contract.json", "coverage_contract_sha256")):
        require(sha((directory / name).read_bytes()) == config.get(key), "Changed bound contract: " + name)
    index = read_json(directory / "source-index.json")
    require(index.get("commit") == SOURCE_COMMIT and index.get("tree") == SOURCE_TREE
            and isinstance(index.get("files"), list) and len(index["files"]) == 165,
            "Complete original public tree must contain 165 files")
    require(len({safe_relative(row["path"]) for row in index["files"]}) == 165
            and sum(row.get("native_input") is True for row in index["files"]) == 47,
            "Original/native source inventory differs")
    coverage = read_json(directory / "coverage-contract.json")
    require(coverage.get("native_acceptance") == "NOT_RUN"
            and coverage.get("model_check_count") == 211
            and len(coverage.get("expected_model_check_labels", [])) == 211
            and len(coverage.get("ui_cases", [])) == 19
            and len({(row["test_class"], row["method"]) for row in coverage["ui_cases"]}) == 19,
            "Full original model/UI contract is missing")
    return config, index, coverage


def validate_context(config, review, env, now, system, machine, *, collecting=False):
    require(config.get("authorization") == "ROOT_REVIEWED_INVENTORY_ONLY", "Unbound root authorization")
    require(review.get("scope") == SCOPE and review.get("source_commit") == SOURCE_COMMIT
            and review.get("candidate_contract_sha256") == candidate_contract(config)
            and review.get("native_build_test_archive_authorized") is False
            and review.get("additional_spend_usd") == 0,
            "Root review does not authorize this exact inventory-only contract")
    for name in ("proposal_receipt_sha256", "independent_peer_receipt_sha256"):
        require(isinstance(review.get(name), str) and re.fullmatch(r"[0-9a-f]{64}", review[name]),
                "Missing concrete review pin: " + name)
    required = {"GITHUB_ACTIONS": "true", "GITHUB_REPOSITORY": "swonyu/HalalAnalyzer",
                "GITHUB_EVENT_NAME": "push", "GITHUB_REF": "refs/heads/" + BRANCH,
                "GITHUB_RUN_ATTEMPT": "1", "RUNNER_OS": "macOS", "RUNNER_ARCH": "ARM64",
                "RUNNER_ENVIRONMENT": "github-hosted", "REPOSITORY_VISIBILITY": "public",
                "DEVELOPER_DIR": DEVELOPER_DIR}
    require(all(env.get(key) == value for key, value in required.items())
            and system == "darwin" and machine == "arm64", "Wrong hosted/public/first-attempt environment")
    require(re.fullmatch(r"[1-9][0-9]*", env.get("GITHUB_RUN_ID", "")) is not None
            and re.fullmatch(r"[0-9a-f]{40}", env.get("GITHUB_SHA", "")) is not None,
            "Invalid actual run/commit context")
    if not collecting:
        remaining = (datetime.fromisoformat(DEADLINE.replace("Z", "+00:00")) - now).total_seconds()
        require(remaining >= 600, "Insufficient remaining authorized work budget")


def bound_paths(*, collecting=False):
    config, index, coverage = inspect_contract(HERE)
    review_path = HERE / "root-review.json"
    require(sha(review_path.read_bytes()) == config.get("root_review_sha256"), "Root review bytes differ")
    review = read_json(review_path)
    validate_context(config, review, os.environ, datetime.now(timezone.utc), sys.platform,
                     platform.machine(), collecting=collecting)
    repo = HERE.parents[1]
    require(repo.resolve() == Path(os.environ["GITHUB_WORKSPACE"]).resolve()
            and not repo.is_symlink(), "Only the actual hosted checkout is allowed")
    temp = Path(os.environ["RUNNER_TEMP"])
    require(temp.is_absolute() and temp.is_dir() and not temp.is_symlink(), "Invalid hosted temporary root")
    files = review.get("control_files")
    require(isinstance(files, list) and files and len({r["path"] for r in files}) == len(files),
            "Missing complete control-file review")
    for row in files:
        path = checked_file(repo, row["path"])
        require(path.stat().st_size == row["bytes"] and sha(path.read_bytes()) == row["sha256"]
                and stat.S_IMODE(path.stat().st_mode) == int(row["mode"], 8),
                "Changed reviewed control file: " + row["path"])
    require("publishing/hosted-r11/inventory_only.py" in {r["path"] for r in files},
            "The actual inventory driver is not bound")
    output = temp / ("HalalTag-R12-Hosted-Tooling-V6-" + os.environ["GITHUB_RUN_ID"] + "-1")
    return config, index, coverage, review, repo, output


def command(label, repo, output, deadline, *, selection=None):
    if label in COMMANDS:
        require(selection is None, "Static inventory command cannot accept a filter override")
        argv = COMMANDS[label]
    else:
        argv = scoped_query_argv(label, selection)
    seconds = min(30, deadline - time.monotonic())
    require(seconds > 0, "Inventory work deadline reached")
    folder = output / "commands" / label
    folder.mkdir(parents=True, exist_ok=False)
    error, code = None, None
    stdout_path, stderr_path = folder / "stdout.bin", folder / "stderr.bin"
    # A cancellation may prevent a terminal receipt. Preserve the exact argv and
    # both raw streams before launch so that partial evidence survives that case.
    with stdout_path.open("xb") as stdout, stderr_path.open("xb") as stderr:
        dump(folder / "started.json", {"status": "STARTED", "argv": argv,
             "started_utc": datetime.now(timezone.utc).isoformat(), "timeout_seconds": seconds})
        try:
            result = subprocess.run(argv, cwd=repo, stdout=stdout,
                                    stderr=stderr, timeout=seconds, check=False)
            code = result.returncode
        except subprocess.TimeoutExpired:
            error = "Inventory command timed out; no retry"
        except BaseException as failure:
            error = "Inventory command interrupted: " + type(failure).__name__
            raise
        finally:
            stdout.flush(); stderr.flush()
            dump(folder / "result.json", {"status": "PASSED" if code == 0 else "FAILED_OR_INTERRUPTED",
                 "argv": argv, "exit_code": code, "error": error,
                 "finished_utc": datetime.now(timezone.utc).isoformat(),
                 "stdout_sha256": sha(stdout_path.read_bytes()), "stderr_sha256": sha(stderr_path.read_bytes()),
                 "stdout_bytes": stdout_path.stat().st_size, "stderr_bytes": stderr_path.stat().st_size,
                 "timeout_seconds": seconds})
    require(code == 0, "Inventory command failed: " + label)
    return stdout_path.read_bytes()


def occupied_native_lock(path=Path("/tmp/dot-ios-build.lock")):
    return os.path.lexists(path)


def verify_source(repo, index, review, values, workflow_commit):
    require(values["git-head"].decode().strip() == workflow_commit, "Checkout differs from actual workflow commit")
    require(values["git-parent"].decode().strip().split() == [workflow_commit, SOURCE_COMMIT],
            "Hosted inventory must be one explicit successor of the reviewed R12 source")
    require(values["git-status"] == b"", "The hosted source/control checkout is dirty")
    tree = {}
    for record in values["git-tree"].split(b"\0"):
        if not record:
            continue
        metadata, path = record.split(b"\t", 1)
        mode, kind, blob = metadata.decode().split()
        name = path.decode("utf-8")
        require(kind == "blob" and mode in ("100644", "100755") and name not in tree,
                "Nonregular or duplicate Git tree member")
        tree[name] = (mode, blob)
    expected = {row["path"] for row in index["files"]}
    controls = {row["path"] for row in review["control_files"]}
    controls |= {"publishing/hosted-r11/candidate.json", "publishing/hosted-r11/root-review.json"}
    require(not expected.intersection(controls) and set(tree) == expected | controls,
            "Unexpected source/control additions or omissions")
    rows = []
    for row in index["files"]:
        path = checked_file(repo, row["path"])
        data = path.read_bytes()
        blob = hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()
        require(tree[row["path"]] == (row["mode"], row["git_blob"])
                and blob == row["git_blob"] and len(data) == row["bytes"]
                and stat.S_IMODE(path.stat().st_mode) == int(row["mode"][-3:], 8),
                "Original Git source bytes or mode changed: " + row["path"])
        if row.get("native_input") is True:
            require(sha(data) == row["sha256"], "Native source SHA-256 changed: " + row["path"])
        rows.append({"path": row["path"], "bytes": len(data), "sha256": sha(data), "git_blob": blob})
    return rows


def verify_coverage(repo, coverage):
    plan = read_json(repo / "Tests/NativeQA/nineteen-case-plan.json")
    require(plan.get("cases") == coverage["ui_cases"] and plan.get("case_count") == 19
            and plan.get("expected_process_launches") == 20
            and plan.get("unique_UUID_supplementary_launches") == 17
            and plan.get("retry_count") == 0, "The actual original nineteen-case plan differs")
    actual = set()
    for row in coverage["ui_source_files"]:
        path = checked_file(repo, row["path"])
        data = path.read_bytes()
        require(sha(data) == row["sha256"] and len(data) == row["bytes"], "An original UI source changed")
        text = data.decode("utf-8")
        classes = re.findall(r"^final class (\w+)\s*:\s*XCTestCase", text, re.MULTILINE)
        methods = re.findall(r"^\s*func\s+(test\w+)\s*\(", text, re.MULTILINE)
        require(classes == [row["test_class"]] and len(methods) == len(set(methods)), "Ambiguous UI class/method inventory")
        actual.update((classes[0], method) for method in methods)
    require(actual == {(row["test_class"], row["method"]) for row in plan["cases"]}
            and len(actual) == 19, "The full exact original UI identity set is required")
    for row in coverage["model_source_files"]:
        path = checked_file(repo, row["path"])
        require(sha(path.read_bytes()) == row["sha256"] and path.stat().st_size == row["bytes"],
                "An original model source changed")
    historical = read_json(repo / "publishing/r6/observed-model-result-r6.json")["observed"]
    require(historical.get("check_count") == 211 and historical.get("checks") == coverage["expected_model_check_labels"],
            "The complete model label sequence, including original repeated labels, differs")
    require(all(historical["checks"].count(label) == 1 for label in coverage["boundary_check_labels"])
            and len(coverage["boundary_check_labels"]) == 9,
            "The nine existing boundary regression labels must each remain present once")
    return {"source_assertions_changed": False, "ui_method_count": 19, "model_check_count_expected": 211,
            "expected_process_launches": 20, "supplementary_launch_uuids": 17,
            "historical_model_fixture_is_current_execution": False, "native_acceptance": "NOT_RUN"}


def evaluate_platform(values, macos_version, lock_exists):
    require(macos_version.split(".")[0] == "26", "Unreviewed macOS platform")
    require(values["xcode-version"].decode().strip().splitlines() == ["Xcode 26.6", "Build version 17F113"],
            "The reviewed installed Xcode build is unavailable")
    require(all(values[name].decode().strip() == "26.5" for name in ("iphoneos-sdk", "iphonesimulator-sdk")),
            "Exact iOS 26.5 SDKs are unavailable")
    types = strict_json(values["device-type-inventory"])
    runtimes = strict_json(values["runtime-inventory"])
    require(isinstance(types, dict) and isinstance(types.get("devicetypes"), list)
            and all(isinstance(x, dict) for x in types["devicetypes"]), "Malformed device-type inventory")
    require(isinstance(runtimes, dict) and isinstance(runtimes.get("runtimes"), list)
            and all(isinstance(x, dict) for x in runtimes["runtimes"]), "Malformed runtime inventory")
    devices = [x for x in types["devicetypes"] if x.get("name") == "iPhone SE (3rd generation)"]
    require(len(devices) == 1 and devices[0].get("identifier") == "com.apple.CoreSimulator.SimDeviceType.iPhone-SE-3rd-generation"
            and devices[0].get("modelIdentifier") == "iPhone14,6" and devices[0].get("productFamily") == "iPhone",
            "Exact SE3 device type/model is unavailable or ambiguous")
    runtime = [x for x in runtimes["runtimes"] if x.get("identifier") == "com.apple.CoreSimulator.SimRuntime.iOS-26-5"]
    require(len(runtime) == 1 and runtime[0].get("isAvailable") is True
            and runtime[0].get("version") == "26.5" and runtime[0].get("buildversion") == "23F77",
            "Exact reviewed successor iOS 26.5 runtime build 23F77 is unavailable")
    supported = runtime[0].get("supportedDeviceTypes")
    require(isinstance(supported, list) and all(isinstance(x, dict) for x in supported),
            "Exact runtime does not expose a complete supported device-type list")
    runtime_se3 = [x for x in supported
                   if x.get("identifier") == "com.apple.CoreSimulator.SimDeviceType.iPhone-SE-3rd-generation"]
    require(len(runtime_se3) == 1 and runtime_se3[0].get("name") == "iPhone SE (3rd generation)"
            and runtime_se3[0].get("productFamily") == "iPhone",
            "Exact installed runtime does not unambiguously support the original SE3")
    help_stderr = values.get("ui-help-stderr")
    require(values.get("ui-help") == b"" and isinstance(help_stderr, bytes)
            and len(help_stderr) == UI_HELP_BYTES and sha(help_stderr) == UI_HELP_SHA256,
            "Fresh exact UI-help bytes differ; preserve originals for explicit review")
    require(lock_exists is False, "A preexisting native lock must be reviewed; no takeover")
    return {"device_type": devices[0], "runtime": runtime[0],
            "runtime_supported_se3": runtime_se3[0],
            "actual_ui_help": {"stdout_bytes": 0, "stderr_bytes": len(help_stderr),
                               "stderr_sha256": sha(help_stderr), "exact_supported_syntax_verified": True},
            "platform_revision": PLATFORM_REVISION,
            "actual_window_and_png_geometry": "NOT_RUN_REQUIRES_ORIGINAL_NATIVE_ASSERTIONS"}



def probe_device_rows(raw):
    value = strict_json(raw)
    groups = value.get("devices") if isinstance(value, dict) else None
    require(isinstance(groups, dict), "Malformed full or scoped device inventory")
    rows = []
    for runtime, group in groups.items():
        require(isinstance(runtime, str) and runtime and isinstance(group, list)
                and all(isinstance(device, dict) for device in group), "Malformed device runtime group")
        for device in group:
            identifier = device.get("udid")
            require(isinstance(identifier, str)
                    and re.fullmatch(r"[0-9A-F]{8}(?:-[0-9A-F]{4}){3}-[0-9A-F]{12}", identifier)
                    and isinstance(device.get("name"), str) and device["name"]
                    and isinstance(device.get("state"), str) and device["state"],
                    "Missing or malformed current device identity")
            rows.append({"runtime":runtime, "udid":identifier, "name":device["name"],
                         "state":device["state"], "isAvailable":device.get("isAvailable"),
                         "deviceTypeIdentifier":device.get("deviceTypeIdentifier")})
    return rows


def select_probe_device(raw):
    rows = probe_device_rows(raw)
    require(len({row["udid"] for row in rows}) == len(rows), "Full inventory contains duplicate device IDs")
    selected = [row for row in rows if row["runtime"] == "com.apple.CoreSimulator.SimRuntime.iOS-26-5"
                and row["name"] == "iPhone 17 Pro"
                and row["deviceTypeIdentifier"] == "com.apple.CoreSimulator.SimDeviceType.iPhone-17-Pro"
                and row["isAvailable"] is True and row["state"] == "Shutdown"]
    require(len(selected) == 1, "No unambiguous existing shutdown probe iPhone17Pro is available for read-only filter evidence")
    same_name = [row for row in rows if row["name"] == selected[0]["name"]]
    require(len(same_name) >= 2 and len({row["runtime"] for row in same_name}) >= 2,
            "A multi-runtime same-name inventory is required to establish complete name filtering")
    return selected[0]


def scoped_query_argv(label, selection):
    require(label in ("device-by-uuid", "device-by-name") and isinstance(selection, dict),
            "Unreviewed scoped query label or missing observed selection")
    identifier = selection.get("udid")
    require(isinstance(identifier, str)
            and re.fullmatch(r"[0-9A-F]{8}(?:-[0-9A-F]{4}){3}-[0-9A-F]{12}", identifier)
            and selection.get("name") == "iPhone 17 Pro"
            and selection.get("runtime") == "com.apple.CoreSimulator.SimRuntime.iOS-26-5"
            and selection.get("deviceTypeIdentifier") == "com.apple.CoreSimulator.SimDeviceType.iPhone-17-Pro"
            and selection.get("isAvailable") is True and selection.get("state") == "Shutdown",
            "Scoped query must use the exact observed shutdown probe iPhone17Pro identity")
    term = identifier if label == "device-by-uuid" else selection["name"]
    return ["/usr/bin/xcrun", "simctl", "list", "devices", term, "--json"]


def evaluate_tooling(values, selection):
    require(selection == select_probe_device(values["device-inventory"]),
            "Scoped queries are not bound to the complete current device inventory")
    help_raw = values.get("list-help-stderr")
    require(values.get("list-help") == b"" and isinstance(help_raw, bytes)
            and 100 <= len(help_raw) <= 65536, "Missing or unexpected list-help streams")
    help_text = help_raw.decode("utf-8")
    require("simctl list" in help_text and "devices" in help_text and "json" in help_text
            and "search" in help_text.lower(), "Installed list help does not document the reviewed filter surface")
    full = probe_device_rows(values["device-inventory"])
    observed = {}
    for label, field in (("device-by-uuid", "udid"), ("device-by-name", "name")):
        # Preserve every matching identity across every runtime, including name collisions.
        # Other substring-search matches do not affect the original ID-or-name predicate.
        expected = [row for row in full if row[field] == selection[field]]
        actual = [row for row in probe_device_rows(values[label]) if row[field] == selection[field]]
        canonical = lambda rows: sorted(json.dumps(row, sort_keys=True, separators=(",", ":")) for row in rows)
        require(expected and canonical(actual) == canonical(expected),
                "Scoped filter omitted, duplicated or changed an exact identity: " + label)
        observed[label] = {"argv":scoped_query_argv(label, selection), "matching_identities":actual,
                           "matching_count":len(actual), "stdout_sha256":sha(values[label]),
                           "complete_against_fresh_full_inventory":True}
    return {"selection":selection, "full_inventory_sha256":sha(values["device-inventory"]),
            "full_inventory_device_count":len(full), "list_help_stdout_bytes":0,
            "list_help_stderr_bytes":len(help_raw), "list_help_stderr_sha256":sha(help_raw),
            "queries":observed, "same_name_across_runtimes_preserved":True,
            "simulator_mutation_invoked":False, "native_acceptance":"NOT_RUN",
            "postboot_performance_established":False,
            "new_native_helper_still_requires_separate_review_and_root_authorization":True}



def inventory():
    config, index, coverage, review, repo, output = bound_paths()
    output.mkdir(mode=0o700, exist_ok=False)
    deadline = time.monotonic() + 300
    result = {"scope": SCOPE, "source_commit": SOURCE_COMMIT, "native_build_test_archive_invoked": False,
              "simulator_mutation_invoked": False, "platform_eligible": False, "status": "FAILED"}
    context = {key: os.environ.get(key) for key in ("GITHUB_REPOSITORY", "GITHUB_SHA", "GITHUB_RUN_ID",
               "GITHUB_RUN_ATTEMPT", "GITHUB_REF", "RUNNER_OS", "RUNNER_ARCH", "RUNNER_ENVIRONMENT", "ImageOS", "ImageVersion")}
    dump(output / "context.json", {**context, "macos_version": platform.mac_ver()[0],
         "developer_dir": DEVELOPER_DIR, "started_at": datetime.now(timezone.utc).isoformat()})
    try:
        values = {key: command(key, repo, output, deadline) for key in ("git-head", "git-parent", "git-tree", "git-status")}
        rows = verify_source(repo, index, review, values, os.environ["GITHUB_SHA"])
        dump(output / "actual-source-index.json", {"files": rows, "source_count": 165, "native_input_count": 47})
        dump(output / "coverage-identity-proof.json", verify_coverage(repo, coverage))
        for key in COMMANDS:
            if key == "git-status-after":
                selection = select_probe_device(values["device-inventory"])
                dump(output / "READ-ONLY-PROBE-SELECTION.json", {"selection":selection,
                     "full_inventory_sha256":sha(values["device-inventory"]),
                     "simulator_mutation_authorized":False})
                for label in ("device-by-uuid", "device-by-name"):
                    values[label] = command(label, repo, output, deadline, selection=selection)
            if key not in values:
                values[key] = command(key, repo, output, deadline)
        values["ui-help-stderr"] = checked_file(output, "commands/ui-help/stderr.bin").read_bytes()
        require(values["git-status-after"] == b"", "The source/control checkout changed during inventory")
        result["platform"] = evaluate_platform(values, platform.mac_ver()[0], occupied_native_lock())
        values["list-help-stderr"] = checked_file(output, "commands/list-help/stderr.bin").read_bytes()
        result["tooling"] = evaluate_tooling(values, selection)
        result.update(status="EXACT_PLATFORM_AND_SCOPED_TOOLING_ACCEPTED_NATIVE_NOT_RUN", platform_eligible=True)
    except Exception as failure:
        result["error"] = type(failure).__name__ + ": " + str(failure)
    dump(output / "RESULT.json", result)
    print(json.dumps(result, indent=2))
    return 0 if result["platform_eligible"] else 1


def collect():
    _, _, _, _, _, output = bound_paths(collecting=True)
    require(output.is_dir() and not output.is_symlink(), "No completed/partial inventory output exists")
    verdict = False
    error = None
    try:
        result = read_json(output / "RESULT.json")
        verdict = (isinstance(result, dict) and result.get("status") == "EXACT_PLATFORM_AND_SCOPED_TOOLING_ACCEPTED_NATIVE_NOT_RUN"
                   and result.get("platform_eligible") is True and result.get("native_build_test_archive_invoked") is False
                   and result.get("simulator_mutation_invoked") is False)
    except Exception as failure:
        error = type(failure).__name__ + ": " + str(failure)
    dump(output / "COLLECTION.json", {"platform_inventory_accepted": verdict, "report_error": error,
         "native_acceptance": "NOT_RUN", "missing_malformed_or_failed_report_is_not_acceptance": True})
    files = []
    for path in sorted(output.rglob("*")):
        require(not path.is_symlink(), "Linked inventory output requires review")
        if path.is_dir():
            continue
        require(path.is_file() and stat.S_ISREG(path.stat().st_mode), "Nonregular inventory output")
        data = path.read_bytes()
        files.append({"path": path.relative_to(output).as_posix(), "bytes": len(data), "sha256": sha(data)})
    dump(output / "FILES.json", {"all_original_files_retained": True, "omissions": [], "files": files})
    archive = output.with_suffix(".tar.gz")
    require(not archive.exists(), "Prior complete evidence archive is preserved; no overwrite")
    with tarfile.open(archive, "x:gz") as packed:
        for path in sorted(output.rglob("*")):
            if path.is_file():
                packed.add(path, arcname=path.relative_to(output).as_posix(), recursive=False)
    expected = {r["path"]: r for r in files}
    expected["FILES.json"] = {"bytes": (output / "FILES.json").stat().st_size, "sha256": sha((output / "FILES.json").read_bytes())}
    with tarfile.open(archive, "r:gz") as packed:
        require(len(packed.getmembers()) == len(expected) and {m.name for m in packed.getmembers()} == set(expected),
                "Incomplete evidence archive")
        for member in packed.getmembers():
            require(member.isfile() and member.size == expected[member.name]["bytes"], "Unexpected archive member")
            require(sha(packed.extractfile(member).read()) == expected[member.name]["sha256"], "Archive bytes differ")
    require(archive.stat().st_size <= ARCHIVE_LIMIT, "Complete evidence exceeds reviewed cap; originals retained, upload refused")
    receipt = {"archive": str(archive), "bytes": archive.stat().st_size, "sha256": sha(archive.read_bytes()),
               "platform_inventory_accepted": verdict, "native_acceptance": "NOT_RUN", "omissions": []}
    dump(output.with_suffix(".archive-receipt.json"), receipt)
    target = Path(os.environ["GITHUB_OUTPUT"])
    require(target.is_absolute() and not target.is_symlink(), "Invalid actual step output file")
    with target.open("a", encoding="utf-8") as handle:
        handle.write("archive=" + str(archive) + "\narchive_sha256=" + receipt["sha256"] + "\n")
        handle.write("platform_eligible=" + str(verdict).lower() + "\n")
    print(json.dumps(receipt, indent=2))
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", nargs="?", default="inspect", choices=("inspect", "inventory", "collect"))
    args = parser.parse_args()
    try:
        if args.mode == "inspect":
            config, index, coverage = inspect_contract(HERE)
            print(json.dumps({"status": "FILE_CONTRACT_INSPECTED", "authorization": config["authorization"],
                              "public_source_files": len(index["files"]), "expected_model_checks": 211, "expected_ui_methods": 19,
                              "inventory_commands_invoked": False, "native_build_test_archive_invoked": False}))
            return 0
        return inventory() if args.mode == "inventory" else collect()
    except Exception as failure:
        print(type(failure).__name__ + ": " + str(failure), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
