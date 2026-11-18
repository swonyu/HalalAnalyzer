"""Pure final report contracts; no import or execution of any native adapter."""


def require(value, message):
    if not value:
        raise ValueError(message)


def model_result(value, coverage):
    require(isinstance(value, dict) and value.get("status") == "PASS"
            and type(value.get("check_count")) is int and value["check_count"] == 211
            and value.get("checks") == coverage["expected_model_check_labels"],
            "Actual model output does not contain the exact ordered 211 checks")
    require(len(coverage["boundary_check_labels"]) == 9
            and all(value["checks"].count(name) == 1 for name in coverage["boundary_check_labels"]),
            "Original nine boundary checks did not each run once")
    return {"status": "PASS", "check_count": 211, "ordered_labels_exact": True,
            "intentional_original_repeated_labels_retained": True, "boundary_labels_once": 9}


def require_native_gate(report, coverage):
    require(isinstance(report, dict) and report.get("scope") == "DISTINCT_HOSTED_R11_NINETEEN_CASES"
            and report.get("source_commit") == "7ef009beb0c1f6f355eeceb931d899553ea8cad5"
            and type(report.get("exit_code")) is int and report["exit_code"] == 0
            and report.get("cleanup_safe") is True and report.get("all_owned_processes_closed") is True
            and report.get("lock") == "released" and report.get("errors") == []
            and report.get("cancel_signal") is None and report.get("source_manifest_status") == "passed"
            and report.get("skip_production") is True and report.get("deadline_minutes") == 45
            and report.get("cleanup_reserve_seconds") == 120,
            "Native phase is incomplete, interrupted, failed or not safely cleaned up")
    require(report.get("native_ui_result") == "NINETEEN_ORIGINAL_CASES_AND_ORIGINAL_EVIDENCE_PASSED"
            and report.get("automatic_test_retries") == 0 and report.get("original_host_receipts") == 20
            and report.get("supplementary_unique_launch_uuids") == 17
            and report.get("source_assertions_changed") is False,
            "All original UI methods and unchanged evidence gates have not passed")
    model_result(report.get("model_checks", {}).get("actual_result"), coverage)
    proof = report.get("verified_test_inventory", {})
    expected = [case["execution_id"] for case in coverage["ui_cases"]]
    require(proof.get("status") == "EXACT_19_CASE_STRUCTURE_AND_20_HOST_CHAIN_VERIFIED"
            and proof.get("case_order") == expected and proof.get("verified_ui_case_count") == 19
            and proof.get("verified_host_count") == 20 and proof.get("verified_supplementary_launch_uuid_count") == 17,
            "Exact original case/host proof is absent")
    require(report.get("settings_cleanup", {}).get("restored_exactly") is True
            and report.get("simulator_cleanup", {}).get("shutdown_verified") is True
            and report["simulator_cleanup"].get("udid") == report.get("simulator", {}).get("udid"),
            "Original settings and exact owned device shutdown are unverified")
    methods = [step for step in report.get("steps", []) if str(step.get("name", "")).endswith("-original-method")]
    require(len(methods) == 19 and [step["name"] for step in methods] == [key + "-original-method" for key in expected]
            and all(step.get("status") == "passed" for step in methods), "Actual nineteen serial original commands are missing or repeated")
    for step, case in zip(methods, coverage["ui_cases"]):
        command = step.get("argv", [])
        selector = "-only-testing:HalalTagQAUItests/" + case["test_class"] + "/" + case["method"]
        require(isinstance(command, list) and command[:2] == ["/usr/bin/xcodebuild", "test-without-building"]
                and [item for item in command if item.startswith("-only-testing:")] == [selector]
                and not any(item.startswith(("-skip-testing", "-retry-tests", "-test-iterations", "-run-tests-until")) for item in command),
                "Actual native command changed the original method or retry scope")
    return {"model_checks": 211, "ui_methods": 19, "host_receipts": 20, "supplementary_launch_uuids": 17,
            "native_cleanup_verified": True, "unsigned_archive_still_required": True,
            "manual_original_pixel_review": "PENDING", "store_release": False}


def require_production_gate(report, verifier, native_report_sha256):
    require(isinstance(report, dict) and report.get("scope") == "DISTINCT_HOSTED_R11_UNSIGNED_PRODUCTION_ARCHIVE"
            and report.get("source_commit") == "7ef009beb0c1f6f355eeceb931d899553ea8cad5"
            and type(report.get("exit_code")) is int and report["exit_code"] == 0
            and report.get("cleanup_safe") is True and report.get("all_owned_processes_closed") is True
            and report.get("lock") == "released" and report.get("errors") == []
            and report.get("cancel_signal") is None and report.get("source_manifest_status") == "passed"
            and report.get("skip_production") is False and report.get("deadline_minutes") == 20
            and report.get("cleanup_reserve_seconds") == 120
            and report.get("accepted_native_report_sha256") == native_report_sha256,
            "Production phase is absent, interrupted, failed, unbound or not safely cleaned up")
    require(isinstance(verifier, dict) and verifier.get("status") == "UNSIGNED_ARCHIVE_INTEGRITY_CHECKS_PASSED"
            and verifier.get("source_commit") == report["source_commit"]
            and verifier.get("shipping_contract_sha256") == "5ef3cc1d338d09734afceb1515963bc793ba4924bce441f831053f716d430c22"
            and verifier.get("archive_checks", {}).get("unsigned") is True
            and verifier["archive_checks"].get("executable_mode") == "0755"
            and verifier["archive_checks"].get("code_signature_load_command_present") is False,
            "Actual unsigned shipping verifier did not pass its reviewed contract")
    steps = report.get("steps", [])
    for name in ("halal-production-settings", "halal-production-archive", "halal-shipping-integrity-verifier"):
        found = [step for step in steps if step.get("name") == name]
        require(len(found) == 1 and found[0].get("status") == "passed", "Original production command missing/repeated/failed: " + name)
    require(report.get("shipping_integrity_result") == "UNSIGNED_ARCHIVE_INTEGRITY_CHECKS_PASSED",
            "Actual production verifier receipt was not bound")
    return {"unsigned_archive_integrity": "PASSED", "distribution_signing": "NOT_PERFORMED",
            "physical_device_acceptance": "NOT_PERFORMED", "manual_original_pixel_review": "PENDING", "store_release": False}
