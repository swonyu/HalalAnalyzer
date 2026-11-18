#!/usr/bin/env python3
"""File-only collection of complete hosted evidence, including failed attempts."""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import stat
import sys


sys.dont_write_bytecode = True
import hosted_binding as bound
import console_diagnostics as diagnostics
from gate_checks import require_native_gate, require_production_gate

HERE = Path(__file__).absolute().parent


def require(value, message):
    if not value:
        raise ValueError(message)


def digest(path):
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def original(attempt, path_text, *, directory=False):
    require(isinstance(path_text, str) and path_text, "Missing original output path")
    path = Path(path_text)
    require(path.is_absolute() and str(path) == path_text and not path.is_symlink()
            and path.resolve() == path and path.is_relative_to(attempt.resolve()), "Original path is not inside this exact attempt")
    require(path.is_dir() if directory else path.is_file(), "Original output is absent or has the wrong type")
    return path


def command_record(attempt, report, name):
    steps = [step for step in report.get("steps", []) if step.get("name") == name]
    require(len(steps) == 1, "Actual command missing or repeated: " + name)
    step = steps[0]
    require(step.get("status") == "passed" and type(step.get("returncode")) is int and step["returncode"] == 0
            and type(step.get("pid")) is int and step["pid"] > 0, "Actual command did not execute and pass: " + name)
    output, error = original(attempt, step.get("stdout")), original(attempt, step.get("stderr"))
    require(output.parent == error.parent, "Original command streams have different ownership")
    actual = bound.read_json(original(attempt, str(output.parent / "result.json")))
    started = bound.read_json(original(attempt, str(output.parent / "command.json")))
    require(actual == step and started.get("status") == "starting", "Raw command result differs from report")
    for key in ("name", "argv", "cwd", "environment_overrides", "timeout_seconds", "started_at", "stdout", "stderr"):
        require(actual.get(key) == started.get(key), "Command changed after its original start record")
    return step, output


def validate_complete(attempt, config, coverage, env):
    """Re-read actual file evidence; invoke no native adapter, process or Apple tool."""
    import case_evidence_installed as cases
    import original_attachments as attachments
    import appearance_evidence_guard_installed as english
    import arabic_appearance_evidence_guard_installed as arabic
    import system_size_evidence as sizes
    import verify_shipping_archive as shipping
    import artifact_binding as artifact
    state = bound.read_json(original(attempt, str(attempt / "attempt.json")))
    require(state.get("status") == "MODEL_UI_AND_UNSIGNED_ARCHIVE_PASSED_ARTIFACT_AND_REVIEW_PENDING"
            and type(state.get("exit_code")) is int and state["exit_code"] == 0 and state.get("errors") == []
            and state.get("cancellation_signal") is None and state.get("native_acceptance_established") is True
            and state.get("source_commit") == config["source_commit"] and state.get("source_tree") == config["source_tree"]
            and state.get("workflow_commit") == env["GITHUB_SHA"] and state.get("github_run_id") == env["GITHUB_RUN_ID"]
            and state.get("github_run_attempt") == 1, "Original attempt is failed, partial, interrupted or bound to another source/run")
    native_path = original(attempt, state.get("native_report"))
    production_path = original(attempt, state.get("production_report"))
    require(digest(native_path) == state.get("native_report_sha256")
            and digest(production_path) == state.get("production_report_sha256"), "Original final report bytes changed")
    native, production = bound.read_json(native_path), bound.read_json(production_path)
    require_native_gate(native, coverage)
    native_root = native_path.parent
    run_id = native.get("qa_run_id")
    simulator = native.get("simulator", {})
    cases.verify_source_inputs(original(attempt, str(native_root / "RunSource"), directory=True))
    _, model_stdout = command_record(attempt, native, "execute-original-model-checks")
    require(bound.read_json(model_stdout) == native["model_checks"]["actual_result"]
            and digest(model_stdout) == native["model_checks"]["execution_stdout_sha256"], "Actual raw model output differs")
    require(digest(original(attempt, str(native_root / "ModelChecks/BilingualModelChecks")))
            == native["model_checks"]["binary_sha256"], "Actual original model binary changed")
    for name in ("compile-original-model-checks", "initial-build-for-testing", "configured-build-for-testing",
                 "cleanup-restore-appearance", "cleanup-restore-content_size",
                 "cleanup-readback-appearance", "cleanup-readback-content_size", "cleanup-simulator-verify"):
        command_record(attempt, native, name)
    original_settings = bound.read_json(original(attempt, str(native_root / "original-system-settings.json")))
    for kind, field in (("appearance", "style"), ("content_size", "content_size")):
        _, readback = command_record(attempt, native, "cleanup-readback-" + kind)
        actual = sizes.parse_content_size(readback.read_text()) if kind == "content_size" else readback.read_text().strip()
        require(actual == original_settings[field], "Actual cleanup readback did not restore the original setting")
    observed_path = original(attempt, str(native_root / "observed-cases.json"))
    observed = bound.read_json(observed_path)
    require(observed.get("run_id") == run_id and isinstance(observed.get("cases"), list), "Actual original case collection is missing")
    rows = observed["cases"]
    strict = cases.validate_all_cases(rows, run_id, simulator["udid"])
    require(strict == native["verified_test_inventory"]
            and strict == bound.read_json(original(attempt, str(native_root / "strict-nineteen-case-proof.json"))),
            "Actual nineteen-case result differs from native report")
    execution = bound.read_json(original(attempt, str(native_root / "execution-binding.json")))
    manifest = execution.get("manifest", {})
    require(execution.get("run_id") == manifest.get("runID") == run_id
            and manifest.get("configurationStatus") == "CONFIGURED_ISOLATED_QA"
            and manifest.get("installationIsDedicatedAndSynthetic") is True,
            "Actual functional/test resource binding differs from host/settings run")
    configured = bound.read_json(original(attempt, str(native_root / "RunSource/Tests/NativeQA/UITests/HalalTagSyntheticQAInstallation.json")))
    require(configured == manifest, "Retained run-owned configuration differs from execution binding")
    source_rows = [row for row in bound.read_json(HERE / "source-index.json")["files"] if row.get("native_input")]
    stage = original(attempt, str(native_root / "RunSource"), directory=True)
    require(all(not path.is_symlink() for path in stage.rglob("*")), "Retained native stage contains a new link")
    actual_stage = {path.relative_to(stage).as_posix() for path in stage.rglob("*") if not path.is_dir()}
    require(actual_stage == {row["path"] for row in source_rows}, "Retained native stage membership changed")
    for row in source_rows:
        path = original(attempt, str(stage / row["path"]))
        require(stat.S_IMODE(path.stat().st_mode) == int(row["mode"][-3:], 8), "Retained native source mode changed")
        if row["path"] != "Tests/NativeQA/UITests/HalalTagSyntheticQAInstallation.json":
            require(path.stat().st_size == row["bytes"] and digest(path) == row["sha256"], "Retained native input bytes changed")
    xctestrun = original(attempt, execution.get("xctestrun"))
    derived = original(attempt, str(native_root / "DerivedData"), directory=True)
    products = artifact.read_products(xctestrun, derived, run_id)
    require(digest(xctestrun) == execution.get("xctestrun_sha256")
            and artifact.bundle_snapshot(products["app"]) == execution.get("app_snapshot")
            and artifact.bundle_snapshot(products["tests"])["sha256"] == execution.get("test_bundle_sha256")
            and bound.read_json(products["tests"] / "HalalTagSyntheticQAInstallation.json") == manifest,
            "Actual retained app/test products or xctestrun changed")
    for case, row, result in zip(coverage["ui_cases"], rows, strict["case_results"]):
        key = case["execution_id"]
        folder = original(attempt, str(native_root / "cases" / key), directory=True)
        require(row.get("collection_errors") == [], "Original case export was incomplete")
        actual_result = original(attempt, row.get("result_bundle"), directory=True)
        require(actual_result == folder / "HalalTag-NativeUITest.xcresult"
                and native["case_xcresults"].get(key) == str(actual_result), "Original result bundle binding differs")
        test_command, _ = command_record(attempt, native, key + "-original-method")
        argv = test_command["argv"]
        require(argv[argv.index("-resultBundlePath") + 1] == str(actual_result), "Actual command wrote another result bundle")
        for field, suffix in (("summary", "summary"), ("tree", "tests")):
            _, output = command_record(attempt, native, key + "-" + suffix)
            require(bound.read_json(output) == row[field]
                    == bound.read_json(original(attempt, str(folder / (field + ".json")))), "Original summary/tree evidence differs")
        settings = bound.read_json(original(attempt, str(folder / "system-settings.json")))
        require(settings == row["settings"], "Actual case setting receipt differs")
        for kind in ("appearance", "content_size"):
            setter, _ = command_record(attempt, native, key + "-set-" + kind)
            desired = case["style"] if kind == "appearance" else case["size"]
            require(setter["argv"] == ["/usr/bin/xcrun", "simctl", "ui", simulator["udid"], kind, desired],
                    "Original setting command targeted another device or value")
            _, before = command_record(attempt, native, key + "-read-" + kind)
            _, after = command_record(attempt, native, key + ("-post-appearance" if kind == "appearance" else "-post-content-size"))
            for output in (before, after):
                actual = sizes.parse_content_size(output.read_text()) if kind == "content_size" else output.read_text().strip()
                require(actual == desired, "Original raw system-setting readback differs")
        command_record(attempt, native, key + "-export-all-original-attachments")
        _, activity_stdout = command_record(attempt, native, key + "-original-activities")
        activity = bound.read_json(original(attempt, str(folder / "activities.json")))
        require(activity == bound.read_json(activity_stdout) and len(activity.get("testRuns", [])) == 1,
                "Actual original activities changed or contain repeated runs")
        kept = attachments.activity_kept_attachments(activity, result["test_identifier"])
        attachment_folder = original(attempt, str(folder / "attachments"), directory=True)
        mapping = attachments.exported_manifest(attachment_folder, kept)
        require(mapping == bound.read_json(original(attempt, str(folder / "attachment-index.json"))), "Original attachments changed after acceptance")
        if case["group"] in ("functional", "state"):
            actual = cases.validate_basic_attachments(attachment_folder, mapping, case, result, manifest, simulator["name"])
            require(actual == bound.read_json(original(attempt, str(folder / "verified-original-evidence.json"))),
                    "Original functional/state evidence differs")
    hosts = cases.host_snapshot(original(attempt, str(native_root / "native-host-originals"), directory=True))
    require(hosts == rows[-1]["host_after"], "Retained original host bytes/modes differ from actual final chain")
    for group, guard in (("en", english), ("ar", arabic)):
        folder = original(attempt, str(native_root / "derived-evidence-unions" / group), directory=True)
        hosts = original(attempt, str(folder / "hosts"), directory=True)
        sizes.validate_system_hosts(guard.validate_host(hosts, run_id))
        proof = guard.validate_attachments(original(attempt, str(folder / "attachments"), directory=True), hosts,
            run_id=run_id, simulator=simulator["udid"], simulator_name=simulator["name"])
        require(proof == bound.read_json(original(attempt, str(folder / "original-full-appearance-proof.json"))),
                "Unchanged full original appearance guard does not reproduce")
    for name in ("halal-production-settings", "halal-production-archive", "halal-shipping-integrity-verifier"):
        command_record(attempt, production, name)
    verifier_path = original(attempt, production.get("shipping_integrity_receipt", {}).get("path"))
    require(digest(verifier_path) == production["shipping_integrity_receipt"]["sha256"], "Actual verifier receipt bytes changed")
    verifier = bound.read_json(verifier_path)
    require_production_gate(production, verifier, state["native_report_sha256"])
    repeated = shipping.verify(original(attempt, str(attempt / "FrozenShippingSource"), directory=True),
        original(attempt, production.get("production_archive"), directory=True),
        original(attempt, production.get("production_settings")), HERE / "shipping-contract.json")
    require(repeated == verifier, "Actual existing production archive no longer satisfies the reviewed verifier")
    return {"status": "ACTUAL_MODEL_UI_UNSIGNED_ARCHIVE_FILES_REVERIFIED", "model_checks": 211,
            "ui_methods": 19, "host_receipts": 20, "supplementary_launch_uuids": 17,
            "source_commit": config["source_commit"], "workflow_commit": env["GITHUB_SHA"],
            "run_id": env["GITHUB_RUN_ID"], "native_tools_invoked_by_collector": False,
            "manual_original_pixel_review": "PENDING", "Grok_delivery": "PENDING", "store_release": False}


def make_verdict(attempt, config, coverage, env):
    """Malformed/missing/wrong-shaped reports fail without preventing packaging."""
    verdict = {"schema_version": 1, "scope": config["scope"], "source_commit": config["source_commit"],
        "workflow_commit": env["GITHUB_SHA"], "github_run_id": env["GITHUB_RUN_ID"], "github_run_attempt": 1,
        "computation_gate_passed": False, "originals_preserved_without_filtering": True,
        "manual_original_pixel_review": "PENDING", "store_release": False, "errors": []}
    try:
        verdict["verified_evidence"] = validate_complete(attempt, config, coverage, env)
        require(env.get("HALALTAG_NATIVE_STEP_OUTCOME") == "success", "Actual native workflow step was not successful")
        verdict["computation_gate_passed"] = True
    except Exception as error:
        verdict["errors"].append(type(error).__name__ + ": " + str(error))
    return verdict


def emit_outputs(values):
    path = Path(os.environ["GITHUB_OUTPUT"])
    require(path.is_file() and not path.is_symlink(), "Actual GitHub output file is unavailable")
    with path.open("a", encoding="utf-8") as stream:
        for key, value in values.items():
            text = str(value)
            require(re.fullmatch(r"[a-z][a-z0-9_]*", key) and "\n" not in text and "\r" not in text, "Unsafe output field")
            stream.write(key + "=" + text + "\n")


def main():
    context = bound.load_bound(HERE, os.environ, datetime.now(timezone.utc), sys.platform,
                               platform.machine(), platform.mac_ver()[0], collecting=True)
    config, index, coverage, review, checkout, attempt = context
    diagnostics.bind_context(config)
    try:
        require(not os.path.lexists(Path("/tmp/dot-ios-build.lock")),
                "Native ownership remains occupied or uncertain; no stable complete package can be claimed")
        # If execution stopped before creating a directory, retain that precise absence
        # alongside complete candidate/control files, without claiming an attempted run.
        if not os.path.lexists(attempt):
            attempt.mkdir(mode=0o700)
            with (attempt / "EXECUTION-NOT-OBSERVED.json").open("x") as stream:
                json.dump({"status": "NO_NATIVE_ATTEMPT_DIRECTORY_OBSERVED", "native_acceptance_established": False}, stream)
        require(attempt.is_dir() and not attempt.is_symlink(), "Ambiguous attempt directory cannot be packaged")
        from release_evidence import preserve_reservation, verify_reservation, route_path, write_original
        preserve_reservation(attempt)
        verdict = make_verdict(attempt, config, coverage, os.environ)
        try:
            proof = verify_reservation(context, os.environ)
            verdict["verified_reservation_asset_id"] = proof["claim_asset"]["id"]
        except Exception as error:
            verdict["computation_gate_passed"] = False
            verdict["errors"].append("Reservation evidence: " + type(error).__name__ + ": " + str(error))
        try:
            verdict["source_after_collection"] = bound.verify_checkout(checkout, index, review,
                os.environ["GITHUB_SHA"], attempt / "git-collection")
        except Exception as error:
            verdict["computation_gate_passed"] = False
            verdict["errors"].append("Final source binding: " + type(error).__name__ + ": " + str(error))
        from overflow_evidence import prepare_complete_evidence
        target = attempt.with_name(attempt.name + "-Evidence")
        encoded = (json.dumps(verdict, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False) + "\n").encode()
        receipt = prepare_complete_evidence({"Attempt": attempt, "Candidate": checkout}, target,
            maximum_artifact_bytes=config["cost"]["maximum_output_bytes"], verdict_bytes=encoded)
        write_original(route_path(attempt), (json.dumps(receipt, indent=2, sort_keys=True) + "\n").encode())
        archive = target / "evidence.tar.gz"
        emit_outputs({"upload_allowed": str(receipt["route"] == "actions_artifact").lower(),
            "release_upload_allowed": str(receipt["route"] == "root_bound_draft_assets").lower(),
            "evidence_route": receipt["route"], "evidence_directory": target,
            "computation_gate_passed": str(verdict["computation_gate_passed"]).lower(),
            "archive_sha256": digest(archive), "archive_bytes": archive.stat().st_size})
        print(json.dumps({"packaging": receipt, "computation_gate_passed": verdict["computation_gate_passed"], "store_release": False}))
        return 0  # Failed computation remains explicit; final workflow gate must reject it.
    except Exception as error:
        diagnostics.observe_exception("collector-error", error)
        raise
    finally:
        diagnostics.attempt_terminal(attempt, "collector-terminal")



if __name__ == "__main__":
    raise SystemExit(main())
