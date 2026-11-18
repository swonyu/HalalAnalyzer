"""File/source/context contracts for the distinct hosted HalalTag proposal.

Only verify_checkout invokes a process, and its fixed commands are read-only Git.
No Apple tool, app, simulator, native lock, network or remote mutation exists here.
"""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess
from release_contract import validate_binding as validate_release_binding


SOURCE_COMMIT = "7ef009beb0c1f6f355eeceb931d899553ea8cad5"
SOURCE_TREE = "97b9e5eca0e4bc5c82ceb8b133fc823eed1af4bf"
SCOPE = "HALALTAG_R11_INSTALLED_RUNTIME_NATIVE_AND_COMPLETE_EVIDENCE_V3"
BRANCH = "continuation/halaltag-r11-hosted-native-v5-d57"
REPOSITORY = "swonyu/HalalAnalyzer"
DEVELOPER_DIR = "/Applications/Xcode_27.app/Contents/Developer"
DEADLINE = "2026-11-18T22:26:12Z"
PREFIX = "publishing/hosted-r11-native/"
SOURCE_INDEX_SHA = "f008307c5e9255651ef183b5f02af930f5081cfc3e4fb3cbf27f9ad431e316ca"
COVERAGE_SHA = "64287ca28115b9b7b1d42a7c03a5cda024fcee919068e7f979df06a212a46da6"
BASE_SHA = "1980cdf5a564a802198183fd79ee2f0a325b486908bab45e01beaadb02e50f99"
SHIPPING_SHA = "cda0ad4b956bf555f991690039414e9f6d41cf3e8cff610faa3073cf1d786040"
ARCHIVE_PEER_SHA = "665514f0ae110657efe1cecaccb44f16243579f7c2befb4ce0409ef9bec672e2"
CASE_PEER_SHA = "c97ca9d4d3123b05e26aa8a41b698322ebfea407ca0349d959391e22296f56c9"
PACKER_PEER_SHA = "fb79c6e57d22413bf9159cfb40c4c66518bba3a2d9ededd5d164eb0675ba839b"
ACCEPTED_INVENTORY_SHA = "670920b501f267016525f3d1893bd603288bf731b1f5844efe714716c9f6a46c"
INSTALLED_RUNTIME_BUILD = "24A434"


def require(ok, message):
    if not ok:
        raise ValueError(message)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def unique_pairs(pairs):
    values = {}
    for key, value in pairs:
        require(key not in values, "Duplicate JSON key")
        values[key] = value
    return values


def read_json(path):
    require(path.is_file() and not path.is_symlink() and path.stat().st_size <= 5_000_000,
            "Missing, linked or oversized JSON input")
    return json.loads(path.read_bytes(), object_pairs_hook=unique_pairs,
                      parse_constant=lambda _: (_ for _ in ()).throw(ValueError("Nonfinite JSON")))


def relative(value):
    require(isinstance(value, str) and value and not value.startswith("/") and "\\" not in value
            and all(part not in ("", ".", "..") for part in value.split("/")), "Unsafe source/control path")
    return value


def file_at(root, name):
    path = root / relative(name)
    require(path.is_file() and not path.is_symlink() and stat.S_ISREG(path.stat().st_mode), "Missing regular source/control")
    for parent in path.parents:
        if parent == root:
            break
        require(not parent.is_symlink(), "Linked source/control parent")
    return path


def digest_matches(path, expected):
    require(isinstance(expected, str) and re.fullmatch(r"[a-f0-9]{64}", expected), "Unbound expected digest")
    require(path.is_file() and not path.is_symlink() and sha(path.read_bytes()) == expected, "Bound file bytes differ")


def candidate_contract(config):
    value = {k: v for k, v in config.items() if k not in ("authorization", "root_review_sha256")}
    return sha(json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode())


def inspect_contract(directory):
    config = read_json(directory / "candidate.json")
    require(config.get("scope") == SCOPE and config.get("source_commit") == SOURCE_COMMIT
            and config.get("source_tree") == SOURCE_TREE and config.get("repository") == REPOSITORY
            and config.get("branch") == BRANCH and config.get("runner_label") == "xcode-27"
            and config.get("developer_dir") == DEVELOPER_DIR and config.get("deadline_utc") == DEADLINE,
            "Source/platform/scope differs from the reviewed distinct proposal")
    require(config.get("native_phase_minutes") == 45 and config.get("production_phase_minutes") == 20
            and config.get("cleanup_reserve_seconds") == 120 and config.get("automatic_retries") == 0
            and config.get("native_case_count") == 19 and config.get("model_check_count") == 211
            and config.get("production_archive_required") is True, "Original bounded gate scope changed")
    for filename, field, expected in (
        ("source-index.json", "source_index_sha256", SOURCE_INDEX_SHA),
        ("coverage-contract.json", "coverage_contract_sha256", COVERAGE_SHA),
        ("publishing_runner_frozen.py", "lifecycle_sha256", BASE_SHA),
        ("verify_shipping_archive.py", "shipping_verifier_sha256", SHIPPING_SHA),
    ):
        require(config.get(field) == expected, "Reviewed support pin changed")
        digest_matches(directory / filename, expected)
    index, coverage = read_json(directory / "source-index.json"), read_json(directory / "coverage-contract.json")
    require(index.get("commit") == SOURCE_COMMIT and index.get("tree") == SOURCE_TREE
            and len(index.get("files", [])) == 165
            and len({relative(row["path"]) for row in index["files"]}) == 165
            and sum(row.get("native_input") is True for row in index["files"]) == 47, "Complete exact R11 source is required")
    require(coverage.get("source_commit") == SOURCE_COMMIT and coverage.get("model_check_count") == 211
            and len(coverage.get("expected_model_check_labels", [])) == 211
            and len(coverage.get("ui_cases", [])) == 19 and coverage.get("expected_process_launches") == 20
            and coverage.get("unique_UUID_supplementary_launches") == 17 and coverage.get("retry_count") == 0,
            "Complete current native identity contract missing")
    digest_matches(directory / "accepted-inventory.json", ACCEPTED_INVENTORY_SHA)
    inventory = read_json(directory / "accepted-inventory.json")
    require(config.get("platform_revision") == inventory["platform"]["platform_revision"]
            and config["platform_revision"].get("runtime_build") == INSTALLED_RUNTIME_BUILD
            and config["platform_revision"].get("original_runtime_build") == "24A5423a"
            and config["inventory_prerequisite"].get("accepted_inventory_sha256") == ACCEPTED_INVENTORY_SHA
            and config["inventory_prerequisite"].get("workflow_commit") == "07fe75910f00019fb16493ad17cc509bfe6e6120"
            and config["inventory_prerequisite"].get("run_id") == 44348679786
            and config["inventory_prerequisite"].get("artifact_id") == 14448295189
            and config["inventory_prerequisite"].get("artifact_download_sha256")
                == "669cee0e9c4d216ffb44a0bc474c71c95b763ad97b79a36cd62b6c437be0b005",
            "The separately verified installed-runtime inventory binding changed")
    validate_release_binding(config.get("evidence_release"), allow_unbound=True)
    return config, index, coverage


def validate_context(config, review, env, now, system, machine, macos, *, collecting=False):
    require(config.get("authorization") == "ROOT_REVIEWED_DISTINCT_HOSTED_NATIVE_AND_ARCHIVE",
            "Native authorization remains UNBOUND")
    require(review.get("authorization") == config["authorization"] and review.get("scope") == SCOPE
            and review.get("source_commit") == SOURCE_COMMIT
            and review.get("candidate_contract_sha256") == candidate_contract(config)
            and review.get("inventory_prerequisite") == config.get("inventory_prerequisite")
            and review.get("cost") == config.get("cost")
            and review.get("platform_revision") == config.get("platform_revision")
            and review.get("evidence_release") == config.get("evidence_release"), "Root review does not bind the exact attempt")
    validate_release_binding(config.get("evidence_release"))
    require(review.get("archive_verifier_peer_sha256") == ARCHIVE_PEER_SHA, "Reviewed shipping verifier peer missing")
    require(review.get("case_evidence_peer_sha256") == CASE_PEER_SHA, "Reviewed exact case-evidence peer missing")
    require(review.get("evidence_packer_peer_sha256") == PACKER_PEER_SHA, "Reviewed exact complete-packer peer missing")
    for key in ("proposal_receipt_sha256", "native_executor_peer_sha256", "release_asset_peer_sha256"):
        require(re.fullmatch(r"[a-f0-9]{64}", str(review.get(key, ""))), "Missing actual peer/proposal pin: " + key)
    required = {"GITHUB_ACTIONS": "true", "GITHUB_REPOSITORY": REPOSITORY,
                "GITHUB_EVENT_NAME": "push", "GITHUB_REF": "refs/heads/" + BRANCH,
                "GITHUB_RUN_ATTEMPT": "1", "RUNNER_OS": "macOS", "RUNNER_ARCH": "ARM64",
                "HALALTAG_HOSTED_ENVIRONMENT": "github-hosted", "DEVELOPER_DIR": DEVELOPER_DIR}
    require(all(env.get(k) == v for k, v in required.items()) and system == "darwin" and machine == "arm64"
            and macos.split(".")[0] == "27" and env.get("ImageOS") and env.get("ImageVersion"),
            "Only the fresh reviewed public standard hosted Mac lane is authorized")
    require(re.fullmatch(r"[1-9][0-9]*", env.get("GITHUB_RUN_ID", ""))
            and re.fullmatch(r"[a-f0-9]{40}", env.get("GITHUB_SHA", "")), "Malformed actual run identity")
    evidence = config.get("inventory_prerequisite", {})
    require(evidence.get("authorization") == "ROOT_VERIFIED_EXACT_PLATFORM_INVENTORY"
            and evidence.get("run_attempt") == 1, "Actual platform inventory prerequisite remains UNBOUND")
    for key, length in (("workflow_commit", 40), ("artifact_download_sha256", 64), ("accepted_inventory_sha256", 64)):
        require(re.fullmatch(r"[a-f0-9]{" + str(length) + r"}", str(evidence.get(key, ""))), "Unbound inventory evidence digest")
    require(all(type(evidence.get(key)) is int and evidence[key] > 0 for key in ("run_id", "artifact_id")), "Unbound inventory identity")
    cost = config.get("cost", {})
    require(cost.get("authorization") == "ROOT_VERIFIED_NO_EXTRA_SPEND"
            and re.fullmatch(r"[a-f0-9]{64}", str(cost.get("private_receipt_sha256", "")))
            and cost.get("public_standard_runner") == "xcode-27" and cost.get("additional_spend_usd") == 0
            and cost.get("paid_usage_blocked") is True and cost.get("retention_days") == 1
            and cost.get("cache_allowed") is False and cost.get("delete_prior_evidence_allowed") is False,
            "Actual current zero-dollar policy remains UNBOUND")
    cap, reserve = cost.get("maximum_output_bytes"), cost.get("reserved_included_storage_bytes")
    require(type(cap) is int and 0 < cap <= 500_000_000 and type(reserve) is int and reserve >= cap + 1_000_000,
            "Actual included-storage allowance remains UNBOUND")
    expires = datetime.fromisoformat(cost["valid_until_utc"].replace("Z", "+00:00"))
    deadline = datetime.fromisoformat(DEADLINE.replace("Z", "+00:00"))
    require(expires.tzinfo is not None, "Naive storage approval expiry")
    if not collecting:
        require((deadline - now).total_seconds() >= 100 * 60 and (expires - now).total_seconds() >= 100 * 60,
                "Insufficient continuing work/storage approval window")


def load_bound(directory, env, now, system, machine, macos, *, collecting=False):
    config, index, coverage = inspect_contract(directory)
    review_path = directory / "root-review.json"
    digest_matches(review_path, config.get("root_review_sha256"))
    review = read_json(review_path)
    validate_context(config, review, env, now, system, machine, macos, collecting=collecting)
    checkout = directory.parents[1]
    require(checkout.resolve() == checkout == Path(env["GITHUB_WORKSPACE"]), "Unexpected or aliased actual hosted checkout")
    event = read_json(Path(env["GITHUB_EVENT_PATH"]))
    require(event.get("repository", {}).get("full_name") == REPOSITORY
            and event["repository"].get("private") is False, "Actual public event binding missing")
    controls = review.get("control_files")
    require(isinstance(controls, list) and controls and len({row["path"] for row in controls}) == len(controls),
            "Complete control-file review is missing")
    required = {PREFIX + n for n in ("hosted_binding.py", "native_driver.py", "gate_checks.py", "case_evidence.py",
        "original_attachments.py", "artifact_binding.py", "publishing_runner_frozen.py",
        "appearance_evidence_guard.py", "arabic_appearance_evidence_guard.py", "appearance_png.py",
        "system_size_evidence.py", "simctl-ui-help-root-20261117.stderr", "verify_shipping_archive.py",
        "shipping-contract.json", "source-index.json", "coverage-contract.json", "accepted-inventory.json",
        "source-contract.json", "nineteen-case-plan.json", "collect_evidence.py", "evidence_pack.py",
        "current_original_union.py", "appearance_evidence_guard_installed.py",
        "arabic_appearance_evidence_guard_installed.py", "case_evidence_installed.py",
        "overflow_evidence.py", "release_contract.py", "github_evidence_transport.py",
        "release_evidence.py", "delivery_gate.py", "console_diagnostics.py")}
    required.add(".github/workflows/halaltag-r11-native.yml")
    require(required <= {row["path"] for row in controls}, "A required runtime/input control is not reviewed")
    for row in controls:
        path = file_at(checkout, row["path"])
        require(path.stat().st_size == row["bytes"] and sha(path.read_bytes()) == row["sha256"]
                and stat.S_IMODE(path.stat().st_mode) == int(row["mode"], 8), "Changed reviewed control")
    inventory_path = directory / "accepted-inventory.json"
    digest_matches(inventory_path, config["inventory_prerequisite"]["accepted_inventory_sha256"])
    observed = read_json(inventory_path)
    require(observed.get("source_commit") == SOURCE_COMMIT and observed.get("platform_eligible") is True
            and observed.get("status") == "EXACT_PLATFORM_INVENTORY_ACCEPTED_NATIVE_NOT_RUN"
            and observed.get("native_build_test_archive_invoked") is False
            and observed.get("simulator_mutation_invoked") is False
            and observed.get("scope") == "HALALTAG_R11_INSTALLED_RUNTIME_HOSTED_INVENTORY_V3"
            and observed.get("platform", {}).get("platform_revision") == config["platform_revision"]
            and observed["platform"].get("runtime", {}).get("buildversion") == INSTALLED_RUNTIME_BUILD
            and observed["platform"]["runtime"].get("identifier") == "com.apple.CoreSimulator.SimRuntime.iOS-27-0"
            and observed["platform"].get("device_type", {}).get("modelIdentifier") == "iPhone14,6",
            "No actual accepted exact installed-platform inventory")
    temp = Path(env["RUNNER_TEMP"])
    require(temp.is_absolute() and temp.is_dir() and not temp.is_symlink() and temp.resolve() == temp
            and all(not parent.is_symlink() for parent in temp.parents)
            and not temp.is_relative_to(checkout) and not checkout.is_relative_to(temp), "Invalid or aliased hosted temporary directory")
    return config, index, coverage, review, checkout, temp / ("HalalTag-R11-Hosted-V3-" + env["GITHUB_RUN_ID"] + "-1")


def verify_checkout(checkout, index, review, workflow_commit, evidence):
    evidence.mkdir(parents=True, exist_ok=False)
    values = {}
    commands = {"head": ["git", "rev-parse", "HEAD"], "parent": ["git", "rev-list", "--parents", "-n", "1", "HEAD"],
                "tree": ["git", "ls-tree", "-rz", "--full-tree", "HEAD"],
                "status": ["git", "status", "--porcelain=v1", "--untracked-files=all"]}
    for name, argv in commands.items():
        record = {"argv": argv, "status": "STARTED"}
        (evidence / (name + "-started.json")).write_text(json.dumps(record, indent=2) + "\n")
        output, error = evidence / (name + ".stdout"), evidence / (name + ".stderr")
        with output.open("xb") as out, error.open("xb") as err:
            result = subprocess.run(argv, cwd=checkout, stdout=out, stderr=err, timeout=30, check=False)
        (evidence / (name + "-result.json")).write_text(json.dumps({**record, "status": "PASSED" if result.returncode == 0 else "FAILED",
            "exit_code": result.returncode, "stdout_sha256": sha(output.read_bytes()), "stderr_sha256": sha(error.read_bytes())}, indent=2) + "\n")
        require(result.returncode == 0, "Read-only source Git check failed")
        values[name] = output.read_bytes()
    require(values["head"].decode().strip() == workflow_commit
            and values["parent"].decode().strip().split() == [workflow_commit, SOURCE_COMMIT]
            and values["status"] == b"", "Native control must be one clean explicit successor of exact R11")
    actual = {}
    for record in values["tree"].split(b"\0"):
        if not record:
            continue
        metadata, raw_path = record.split(b"\t", 1)
        mode, kind, blob = metadata.decode().split()
        name = relative(raw_path.decode())
        require(kind == "blob" and mode in ("100644", "100755") and name not in actual, "Nonregular/duplicate Git member")
        actual[name] = (mode, blob)
    original = {row["path"] for row in index["files"]}
    additions = {row["path"] for row in review["control_files"]} | {PREFIX + "candidate.json", PREFIX + "root-review.json"}
    require(not original.intersection(additions) and set(actual) == original | additions, "Unreviewed source/control additions or omissions")
    for row in index["files"]:
        path = file_at(checkout, row["path"]); data = path.read_bytes()
        blob = hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()
        require(actual[row["path"]] == (row["mode"], row["git_blob"]) and blob == row["git_blob"]
                and len(data) == row["bytes"] and stat.S_IMODE(path.stat().st_mode) == int(row["mode"][-3:], 8),
                "Original R11 Git source bytes/mode differ")
        if row.get("native_input"):
            require(sha(data) == row["sha256"], "Original native source SHA differs")
    return {"source_commit": SOURCE_COMMIT, "source_tree": SOURCE_TREE, "workflow_commit": workflow_commit,
            "original_git_files": 165, "native_inputs": 47, "source_assertions_changed": False}
