"""Pure checks for the distinct HalalTag R11 hosted evidence proposal.

No process, simulator, network, app, lock or native adapter is invoked here.
These checks cannot establish installation/source binding, the existing full
appearance guards, model acceptance, completed cleanup, or archive acceptance.
The six unavailable private supports are not represented as recovered files.
"""
from __future__ import annotations

from datetime import datetime
import hashlib
import json
import math
from pathlib import Path, PurePosixPath
import re
import stat
import uuid


SOURCE_COMMIT = "7ef009beb0c1f6f355eeceb931d899553ea8cad5"
SOURCE_TREE = "97b9e5eca0e4bc5c82ceb8b133fc823eed1af4bf"
PLAN_SHA256 = "8e6e78d37f6a5a162bff2cb5fb79fc3b91382f333b143554833ab4ec64a05a62"
SOURCE_CONTRACT_SHA256 = "7fcfb6678900c48fd8332d572d4df9594402ec781eb92715923012b5cbe8cf5f"
TARGET = "HalalTagQAUItests"
APP_ID = "com.saleh.halaltag.productioncomposition.qa.r20261117r11"
DEVICE_NAME = "iPhone SE (3rd generation)"
RUNTIME_BUILD = "24A434"
HERE = Path(__file__).resolve().parent


class EvidenceFailure(ValueError):
    pass


def require(value, message):
    if not value:
        raise EvidenceFailure(message)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def unique_object(pairs):
    value = {}
    for key, item in pairs:
        require(key not in value, "Duplicate original JSON key")
        value[key] = item
    return value


def parse_json(data):
    require(isinstance(data, bytes) and len(data) <= 64 * 1024 * 1024, "JSON exceeds the inspection bound")
    return json.loads(data, object_pairs_hook=unique_object,
                      parse_constant=lambda _: (_ for _ in ()).throw(EvidenceFailure("Nonfinite JSON value")))


def encoded(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode()


def same_value(left, right):
    return encoded(left) == encoded(right)


def canonical_uuid(value):
    require(isinstance(value, str), "Missing canonical UUID")
    try:
        canonical = str(uuid.UUID(value))
    except ValueError:
        raise EvidenceFailure("Malformed UUID") from None
    require(canonical.lower() == value.lower(), "UUID is not in original canonical form")
    return canonical.upper()


def read_pinned(name, expected):
    path = HERE / name
    require(path.is_file() and not path.is_symlink(), "Missing or linked companion contract")
    raw = path.read_bytes()
    require(sha(raw) == expected, "Companion contract differs from this reviewed validator")
    return parse_json(raw)


def plan():
    value = read_pinned("nineteen-case-plan.json", PLAN_SHA256)
    require(value.get("case_count") == 19 and len(value.get("cases", [])) == 19
            and value.get("expected_process_launches") == 20
            and value.get("unique_UUID_supplementary_launches") == 17
            and value.get("retry_count") == 0, "Original nineteen-case plan is incomplete")
    return value["cases"]


def checked_case(case):
    require(isinstance(case, dict), "Case must be the original plan object")
    matches = [row for row in plan() if row["execution_id"] == case.get("execution_id")]
    require(len(matches) == 1 and same_value(matches[0], case), "Case selector, order metadata or expectations changed")
    return matches[0]


def verify_source_inputs(source_root):
    contract = read_pinned("source-contract.json", SOURCE_CONTRACT_SHA256)
    require(contract.get("source_commit") == SOURCE_COMMIT and contract.get("source_tree") == SOURCE_TREE,
            "Source identity changed")
    rows = []
    for expected in contract["source_files"]:
        path = source_root / expected["path"]
        require(path.is_file() and not path.is_symlink(), "Missing or linked original source input")
        for parent in path.parents:
            if parent == source_root:
                break
            require(not parent.is_symlink(), "Source parent is linked")
        raw = path.read_bytes()
        require(len(raw) == expected["bytes"] and sha(raw) == expected["sha256"]
                and stat.S_IMODE(path.stat().st_mode) == 0o644, "Original source bytes or Git mode changed")
        rows.append({"path": expected["path"], "bytes": len(raw), "sha256": sha(raw), "mode": "0644"})
    return {"source_commit": SOURCE_COMMIT, "source_tree": SOURCE_TREE, "files": rows,
            "source_assertions_changed": False, "native_invoked": False}


def validate_one_result(summary, tree, case, simulator):
    """Require exactly one original passing leaf, preserving the former strict shape."""
    case = checked_case(case)
    simulator = canonical_uuid(simulator)
    require(isinstance(summary, dict) and isinstance(tree, dict), "Malformed original summary or test tree")
    for key, wanted in (("totalTestCount", 1), ("passedTests", 1), ("failedTests", 0),
                        ("skippedTests", 0), ("expectedFailures", 0)):
        require(type(summary.get(key)) is int and summary[key] == wanted, "Unexpected original result count: " + key)
    require(summary.get("result") == "Passed" and summary.get("testFailures") == []
            and summary.get("runtimeWarnings") == [], "Original case is failed, skipped, warned or incomplete")
    configurations, devices = summary.get("devicesAndConfigurations"), tree.get("devices")
    require(isinstance(configurations, list) and len(configurations) == 1
            and isinstance(configurations[0], dict) and isinstance(devices, list) and len(devices) == 1,
            "One actual device/configuration is required")
    device = configurations[0].get("device")
    for actual in (device, devices[0]):
        require(isinstance(actual, dict) and canonical_uuid(actual.get("deviceId")) == simulator
                and actual.get("platform") == "iOS Simulator" and actual.get("modelName") == DEVICE_NAME
                and actual.get("osVersion") == "27.0" and actual.get("osBuildNumber") == RUNTIME_BUILD
                and actual.get("architecture") == "arm64", "Result destination differs from the exact owned SE3 runtime")
    for key, wanted in (("passedTests", 1), ("failedTests", 0), ("skippedTests", 0), ("expectedFailures", 0)):
        require(type(configurations[0].get(key)) is int and configurations[0][key] == wanted,
                "Per-device result count differs")
    configuration = configurations[0].get("testPlanConfiguration")
    require(isinstance(configuration, dict) and isinstance(configuration.get("configurationName"), str)
            and configuration["configurationName"]
            and same_value(tree.get("testPlanConfigurations"), [configuration]),
            "Summary/tree configuration identity differs")
    expected_id = case["test_class"] + "/" + case["method"] + "()"
    expected_url = f"test://com.apple.xcode/HalalTagQA/{TARGET}/{case['test_class']}/{case['method']}"
    leaves, bundles, suites = [], [], []
    def walk(node, parent=None):
        require(isinstance(node, dict) and node.get("result") == "Passed", "Unpassed or malformed original tree node")
        children = node.get("children", [])
        require(isinstance(children, list), "Malformed original tree children")
        kind = node.get("nodeType")
        if kind == "Test Plan":
            require(parent is None and len(children) == 1, "Unexpected original test plan")
        elif kind == "UI test bundle":
            require(parent == "Test Plan" and node.get("name") == TARGET and len(children) == 1,
                    "Unexpected UI test bundle")
            bundles.append(node["name"])
        elif kind == "Test Suite":
            require(parent == "UI test bundle" and node.get("name") == case["test_class"] and len(children) == 1,
                    "Unexpected UI test class")
            suites.append(node["name"])
        elif kind == "Test Case":
            require(parent == "Test Suite" and not children and node.get("nodeIdentifier") == expected_id
                    and node.get("name") == case["method"] + "()", "Wrong or repeated original method")
            duration = node.get("durationInSeconds")
            require(type(duration) in (int, float) and math.isfinite(duration) and duration >= 0,
                    "Original method lacks a finite execution duration")
            url = node.get("nodeIdentifierURL")
            require(isinstance(url, str) and url.removesuffix("()") == expected_url,
                    "Original method URL differs from its source identity")
            leaves.append({"identifier": expected_id, "url": url, "duration_seconds": duration})
        else:
            raise EvidenceFailure("Unsupported original tree node type: " + str(kind))
        for child in children:
            walk(child, kind)
    roots = tree.get("testNodes")
    require(isinstance(roots, list) and len(roots) == 1, "Expected one original result test plan")
    walk(roots[0])
    require(len(leaves) == 1 and bundles == [TARGET] and suites == [case["test_class"]],
            "Original method identity is missing or duplicated")
    return {"execution_id": case["execution_id"], "target": TARGET, "device_id": simulator,
            "test_identifier": expected_id, "test_url": leaves[0]["url"],
            "configuration": configuration, "duration_seconds": leaves[0]["duration_seconds"],
            "passed": 1, "failed": 0, "skipped": 0, "expected_failures": 0,
            "runtime_warnings": [], "scope": "One supplied original case result verified structurally; no test invoked."}


def safe_host_path(name):
    require(isinstance(name, str) and name and "\\" not in name and not any(ord(x) < 32 for x in name),
            "Invalid original host path")
    path = PurePosixPath(name)
    require(not path.is_absolute() and str(path) == name and all(x not in ("", ".", "..") for x in name.split("/")),
            "Noncanonical original host path")
    return path


def host_snapshot(folder, *, allow_missing=False):
    """Read the original run-specific directory; only an explicit initial absence is allowed."""
    require(type(allow_missing) is bool and not folder.is_symlink(), "Linked host root or malformed missing policy")
    if not folder.exists():
        require(allow_missing, "Original run-specific host directory is missing")
        return {}
    require(folder.is_dir(), "Original host root is not a directory")
    result = {}
    for path in sorted(folder.rglob("*")):
        require(not path.is_symlink(), "Linked original host path")
        if path.is_dir():
            continue
        require(path.is_file() and stat.S_ISREG(path.stat().st_mode) and path.name == "started.json",
                "Unexpected file in original run-specific host directory")
        raw = path.read_bytes()
        require(0 < len(raw) <= 32_000, "Original host receipt is empty or oversized")
        name = path.relative_to(folder).as_posix()
        safe_host_path(name)
        result[name] = {"sha256": sha(raw), "bytes": len(raw), "mode": f"{stat.S_IMODE(path.stat().st_mode):04o}",
                        "record": parse_json(raw)}
        require(len(result) <= 20, "Unexpected extra actual host launches")
    return result


def snapshot_shape(snapshot):
    require(isinstance(snapshot, dict) and len(snapshot) <= 20, "Malformed host snapshot")
    for name, entry in snapshot.items():
        safe_host_path(name)
        require(isinstance(entry, dict) and set(entry) == {"sha256", "bytes", "mode", "record"}
                and isinstance(entry["sha256"], str) and re.fullmatch(r"[a-f0-9]{64}", entry["sha256"])
                and type(entry["bytes"]) is int and 0 < entry["bytes"] <= 32_000
                and isinstance(entry["mode"], str) and re.fullmatch(r"[0-7]{4}", entry["mode"])
                and isinstance(entry["record"], dict), "Malformed original host file binding")


def numeric(value):
    return type(value) in (int, float) and math.isfinite(value)


def frame(value, width=375, height=667):
    require(isinstance(value, dict) and set(value) == {"x", "y", "width", "height"}
            and all(numeric(item) for item in value.values())
            and [value[key] for key in ("x", "y", "width", "height")] == [0, 0, width, height],
            "Original full-screen SE3 geometry differs")


def validate_host(name, entry, case, run_id):
    path = safe_host_path(name)
    value = entry["record"]
    require(type(value.get("schema_version")) is int and value["schema_version"] == 1
            and value.get("run_id") == run_id and value.get("case_id") == case["case_id"]
            and value.get("bundle_id") == APP_ID, "Original host run/case/app binding differs")
    if case["group"] == "en":
        require(path.parts == (case["case_id"], "started.json") and "language_launch_id" not in value,
                "Original English case must retain its non-UUID host path")
        launch = None
    else:
        require(len(path.parts) == 3 and path.parts[0] == case["case_id"] and path.parts[2] == "started.json",
                "Original supplementary host must retain its launch UUID path")
        launch = canonical_uuid(path.parts[1])
        require(value.get("language_launch_id") == path.parts[1], "Host UUID differs from original path")
    style = 2 if case["style"] == "dark" else 1
    category = "UICTContentSizeCategoryAccessibilityXXXL" if case["size"] == "accessibility-extra-extra-extra-large" else "UICTContentSizeCategoryL"
    require(all(type(value.get(key)) is int and value[key] == style for key in ("requested_style", "window_style", "host_style")),
            "Original host appearance did not resolve as requested")
    require(value.get("content_size_source") == "INHERITED_SYSTEM_SETTING"
            and all(value.get(key) == category for key in ("requested_content_size", "application_content_size",
                "scene_content_size", "window_content_size", "host_content_size")),
            "Original inherited application/scene/window/host text size differs")
    for key in ("screen_bounds", "scene_bounds", "window_frame", "host_frame"):
        frame(value.get(key))
    frame(value.get("screen_native_bounds"), 750, 1334)
    require(all(numeric(value.get(key)) and value[key] == 2 for key in ("screen_scale", "screen_native_scale"))
            and type(value.get("orientation")) is int and value["orientation"] == 1
            and value.get("artificial_window_resize") is False and value.get("fixed_inner_container") is False,
            "Original scale/orientation/window configuration differs")
    require(all(numeric(value.get(key)) and 0 <= value[key] <= 667 for key in ("safe_area_top", "safe_area_bottom")),
            "Original host safe-area values are invalid")
    recorded = value.get("recorded_at")
    require(isinstance(recorded, str) and recorded, "Missing original host time")
    try:
        parsed = datetime.fromisoformat(recorded.replace("Z", "+00:00"))
    except ValueError:
        raise EvidenceFailure("Malformed original host time") from None
    require(parsed.tzinfo is not None, "Original host time has no timezone")
    return launch


def validate_host_delta(before, after, case, run_id):
    case = checked_case(case)
    canonical_uuid(run_id)
    snapshot_shape(before); snapshot_shape(after)
    require(set(before) <= set(after), "An earlier original host receipt disappeared")
    require(all(same_value(before[name], after[name]) for name in before), "An earlier original host receipt changed")
    added = sorted(set(after) - set(before))
    require(len(added) == case["expected_launches"], "Actual new host-launch count differs from the original method")
    launches = [validate_host(name, after[name], case, run_id) for name in added]
    uuids = [value for value in launches if value is not None]
    require(len(uuids) == len(set(uuids)), "A supplementary launch UUID was reused inside a method")
    return {"execution_id": case["execution_id"], "original_paths_added": added, "new_host_count": len(added),
            "launch_uuids": uuids, "before_snapshot_sha256": sha(encoded(before)),
            "after_snapshot_sha256": sha(encoded(after)), "original_host_bytes_rewritten": False}


def validate_settings(settings, case, run_id, simulator):
    case = checked_case(case)
    require(isinstance(settings, dict) and settings.get("run_id") == run_id
            and settings.get("execution_id") == case["execution_id"] and settings.get("case_id") == case["case_id"]
            and canonical_uuid(settings.get("device_id")) == canonical_uuid(simulator)
            and settings.get("owned_destination_before") is True and settings.get("owned_destination_after") is True,
            "Settings are not bound to this exact owned method/destination")
    for key, expected in (("style", case["style"]), ("content_size", case["size"])):
        row = settings.get(key)
        require(isinstance(row, dict) and row.get("requested") == row.get("readback_before_test")
                == row.get("readback_after_test") == expected and row.get("set_command_status") == "passed",
                "Actual requested/pre/post simulator setting differs: " + key)
    return {"execution_id": case["execution_id"], "actual_style": case["style"], "actual_content_size": case["size"],
            "source": "Supplied source-bound runner readback receipt; raw setting commands remain required original evidence"}


def validate_all_cases(rows, run_id, simulator):
    """Verify the exact original row order and host chain; do not upgrade native acceptance."""
    cases = plan()
    canonical_uuid(run_id); canonical_uuid(simulator)
    require(isinstance(rows, list) and len(rows) == 19
            and [row.get("execution_id") if isinstance(row, dict) else None for row in rows]
            == [case["execution_id"] for case in cases], "Original cases are missing, duplicated, added or reordered")
    previous, results, deltas, paths, launches = {}, [], [], [], []
    for case, row in zip(cases, rows):
        require(row.get("xcodebuild_status") == "passed", "Original case command did not pass")
        path = row.get("result_bundle")
        require(isinstance(path, str) and Path(path).is_absolute() and Path(path).suffix == ".xcresult"
                and ".." not in Path(path).parts and str(Path(path)) == path, "Missing or noncanonical original result path")
        paths.append(path)
        results.append(validate_one_result(row.get("summary"), row.get("tree"), case, simulator))
        validate_settings(row.get("settings"), case, run_id, simulator)
        require(same_value(row.get("host_before"), previous), "Host snapshots do not form one original uninterrupted chain")
        delta = validate_host_delta(row.get("host_before"), row.get("host_after"), case, run_id)
        deltas.append(delta); launches.extend(delta["launch_uuids"])
        previous = row["host_after"]
    require(len(paths) == len(set(paths)) == 19, "Nineteen distinct original result bundles are required")
    require(len(previous) == 20 and len(launches) == len(set(launches)) == 17,
            "The exact twenty actual hosts and seventeen unique supplementary launch UUIDs are required")
    return {"status": "EXACT_19_CASE_STRUCTURE_AND_20_HOST_CHAIN_VERIFIED", "source_commit": SOURCE_COMMIT,
            "run_id": run_id, "device_id": canonical_uuid(simulator), "verified_ui_case_count": 19,
            "verified_host_count": 20, "verified_supplementary_launch_uuid_count": 17,
            "case_order": [case["execution_id"] for case in cases], "case_results": results,
            "host_deltas": deltas, "final_host_snapshot_sha256": sha(encoded(previous)), "original_result_paths": paths,
            "native_invoked_by_validator": False, "native_acceptance_established": False, "store_release": False,
            "remaining_required_gates": ["Exact source/app/install/xctestrun binding", "All original attachment preservation",
                "Unmodified English and Arabic full appearance guards", "Exact ordered 211 model checks",
                "Owned settings/process/simulator/lock cleanup", "Separate shipping archive and release gates"]}


def human_name_matches(name, label, extension):
    return isinstance(name, str) and name.endswith(extension) and (name == label + extension or name.startswith(label + "_"))


def validate_basic_attachments(folder, mapping, case, result, binding, simulator_name):
    """Consume the accepted complete original-attachment map for functional/state cases.

    This does not replace the parent's unmodified EN/AR geometry/audit guards.
    PNG checks here concern original mapped dimensions, not visual correctness.
    """
    case = checked_case(case)
    require(case["group"] in ("functional", "state"), "Detailed appearance cases require their unchanged full guards")
    require(isinstance(mapping, dict) and mapping.get("activity_cross_check_completed") is True
            and mapping.get("kept_activity_attachments_missing") == [] and isinstance(mapping.get("files"), list),
            "Complete original-attachment identity checking has not passed")
    require(isinstance(result, dict) and result.get("execution_id") == case["execution_id"]
            and type(result.get("passed")) is int and result["passed"] == 1,
            "Attachment map lacks this original verified case result")
    require(isinstance(simulator_name, str) and simulator_name, "Actual owned simulator name missing")
    require(folder.is_dir() and not folder.is_symlink(), "Original export root is missing or linked")
    manifest_path = folder / "manifest.json"
    require(manifest_path.is_file() and not manifest_path.is_symlink()
            and sha(manifest_path.read_bytes()) == mapping.get("apple_manifest_sha256"), "Original Apple manifest changed")
    rows, names = mapping["files"], set()
    for item in rows:
        require(isinstance(item, dict) and item.get("testIdentifier") == result["test_identifier"]
                and isinstance(item.get("testIdentifierURL"), str)
                and item["testIdentifierURL"].removesuffix("()") == result["test_url"].removesuffix("()")
                and canonical_uuid(item.get("deviceId")) == result["device_id"]
                and item.get("deviceName") == simulator_name
                and item.get("configurationName") == result["configuration"]["configurationName"]
                and item.get("isAssociatedWithFailure") is False, "Attachment method/device/configuration/failure binding differs")
        name = item.get("exportedFileName")
        require(isinstance(name, str) and PurePosixPath(name).name == name and name not in ("", ".", "..", "manifest.json")
                and "\\" not in name and name not in names, "Duplicate or unsafe original attachment filename")
        path = folder / name
        require(path.is_file() and not path.is_symlink() and stat.S_ISREG(path.stat().st_mode), "Missing original attachment")
        raw = path.read_bytes()
        require(sha(raw) == item.get("sha256") and len(raw) == item.get("bytes")
                and stat.S_IMODE(path.stat().st_mode) == item.get("mode"), "Mapped original attachment bytes or mode changed")
        names.add(name)
    require(all(path.is_file() and not path.is_symlink() for path in folder.iterdir())
            and {path.name for path in folder.iterdir()} == names | {"manifest.json"}, "Unmapped or missing original export files")
    contract = read_pinned("source-contract.json", SOURCE_CONTRACT_SHA256)
    captures = contract["functional_direct_captures"][case["execution_id"]] if case["group"] == "functional" else [case["required_capture"]]
    matched = []
    for label in captures:
        images = [item for item in rows if human_name_matches(item.get("suggestedHumanReadableName"), label, ".png")]
        require(len(images) == 1 and images[0].get("pixel_dimensions") == {"width": 750, "height": 1334},
                "Missing or ambiguous original direct-capture SE3 screenshot: " + label)
        entry = {"capture": label, "png": images[0]["exportedFileName"], "png_sha256": images[0]["sha256"]}
        if case["group"] == "state":
            trees = [item for item in rows if human_name_matches(item.get("suggestedHumanReadableName"), label + "-accessibility-tree", ".txt")]
            require(len(trees) == 1 and trees[0]["bytes"] > 0, "Missing original state accessibility tree")
            entry.update(accessibility_tree=trees[0]["exportedFileName"], accessibility_tree_sha256=trees[0]["sha256"])
        matched.append(entry)
    if case["group"] == "functional":
        references = {"runID": "runID", "qaBundleIdentifier": "qaBundleIdentifier", "artifactSHA256": "qaArtifactSHA256",
                      "buildEvidence": "buildEvidenceReference", "installationEvidence": "installationEvidenceReference",
                      "destinationEvidence": "destinationEvidenceReference"}
        require(isinstance(binding, dict) and all(isinstance(binding.get(key), str) and binding[key] for key in references.values()),
                "Actual installed QA binding is missing")
        canonical_uuid(binding["runID"])
        require(binding["qaBundleIdentifier"] == APP_ID and re.fullmatch(r"[0-9a-f]{64}", binding["qaArtifactSHA256"])
                and binding["qaArtifactSHA256"] != "0" * 64, "Wrong actual QA artifact binding")
        records = [item for item in rows if human_name_matches(item.get("suggestedHumanReadableName"), "QA run binding", ".txt")]
        require(len(records) == 1, "Expected one original functional setup binding attachment")
        text = (folder / records[0]["exportedFileName"]).read_text(encoding="utf-8")
        observed = {}
        for line in text.splitlines():
            key, separator, value = line.partition("=")
            require(separator and key not in observed, "Malformed or duplicate original QA binding line")
            observed[key] = value
        require(observed == {key: binding[value] for key, value in references.items()}, "Original setup text differs from actual installed QA binding")
    return {"execution_id": case["execution_id"], "original_file_count": len(names), "direct_captures": matched,
            "functional_setup_binding_verified": case["group"] == "functional",
            "whitespace_screenshot_invented": False, "original_bytes_rewritten": False,
            "visual_accessibility_review": "NOT_ESTABLISHED_BY_THIS_STRUCTURAL_CHECK", "native_invoked": False}
