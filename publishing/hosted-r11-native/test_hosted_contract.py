"""Pure boundary fixtures; never import or invoke the native or frozen runner."""
import ast
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
from pathlib import Path
import stat
import sys
import tempfile
import unittest


sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent


def pure(name):
    spec = importlib.util.spec_from_file_location(name, HERE / (name + ".py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


GATE, BIND = pure("gate_checks"), pure("hosted_binding")
COVERAGE = json.loads((HERE / "coverage-contract.json").read_bytes())


def passed_native():
    device = "00112233-4455-6677-8899-aabbccddeeff"
    return {"scope": "DISTINCT_HOSTED_R11_NINETEEN_CASES", "source_commit": BIND.SOURCE_COMMIT,
        "exit_code": 0, "cleanup_safe": True, "all_owned_processes_closed": True, "lock": "released", "errors": [],
        "cancel_signal": None, "source_manifest_status": "passed", "skip_production": True, "deadline_minutes": 45,
        "cleanup_reserve_seconds": 120, "native_ui_result": "NINETEEN_ORIGINAL_CASES_AND_ORIGINAL_EVIDENCE_PASSED",
        "automatic_test_retries": 0, "original_host_receipts": 20, "supplementary_unique_launch_uuids": 17,
        "source_assertions_changed": False, "model_checks": {"actual_result": {"status": "PASS", "check_count": 211,
            "checks": deepcopy(COVERAGE["expected_model_check_labels"])}},
        "verified_test_inventory": {"status": "EXACT_19_CASE_STRUCTURE_AND_20_HOST_CHAIN_VERIFIED",
            "case_order": [case["execution_id"] for case in COVERAGE["ui_cases"]],
            "verified_ui_case_count": 19, "verified_host_count": 20, "verified_supplementary_launch_uuid_count": 17},
        "settings_cleanup": {"restored_exactly": True}, "simulator_cleanup": {"shutdown_verified": True, "udid": device},
        "simulator": {"udid": device}, "steps": [{"name": case["execution_id"] + "-original-method", "status": "passed",
            "argv": ["/usr/bin/xcodebuild", "test-without-building",
                     "-only-testing:HalalTagQAUItests/" + case["test_class"] + "/" + case["method"]]}
            for case in COVERAGE["ui_cases"]]}


def bound_context():
    config = json.loads((HERE / "candidate.json").read_bytes())
    config["authorization"] = "ROOT_REVIEWED_DISTINCT_HOSTED_NATIVE_AND_ARCHIVE"
    config["inventory_prerequisite"] = {"authorization": "ROOT_VERIFIED_EXACT_PLATFORM_INVENTORY", "workflow_commit": "1" * 40,
        "run_id": 123, "run_attempt": 1, "artifact_id": 456, "artifact_download_sha256": "2" * 64,
        "accepted_inventory_sha256": "3" * 64}
    config["cost"].update(authorization="ROOT_VERIFIED_NO_EXTRA_SPEND", private_receipt_sha256="4" * 64,
        maximum_output_bytes=400_000_000, reserved_included_storage_bytes=420_000_000,
        valid_until_utc="2026-11-18T22:26:12Z")
    config["evidence_release"].update(authorization="ROOT_VERIFIED_NEW_EMPTY_EVIDENCE_ONLY_DRAFT",
        release_id=101, author_id=202, author_login="synthetic-owner", created_at="2026-11-18T09:00:00Z",
        creation_receipt_sha256="a" * 64, free_route_review_receipt_sha256="b" * 64,
        root_existing_auth_route_verified=True, root_created_tag_and_draft_before_native=True,
        fresh_empty_asset_list_verified=True)
    review = {"authorization": config["authorization"], "scope": BIND.SCOPE, "source_commit": BIND.SOURCE_COMMIT,
        "candidate_contract_sha256": BIND.candidate_contract(config), "inventory_prerequisite": config["inventory_prerequisite"],
        "cost": config["cost"], "platform_revision": config["platform_revision"],
        "evidence_release": config["evidence_release"], "release_asset_peer_sha256": "c" * 64,
        "archive_verifier_peer_sha256": BIND.ARCHIVE_PEER_SHA,
        "case_evidence_peer_sha256": BIND.CASE_PEER_SHA, "proposal_receipt_sha256": "5" * 64,
        "native_executor_peer_sha256": "6" * 64, "evidence_packer_peer_sha256": BIND.PACKER_PEER_SHA}
    env = {"GITHUB_ACTIONS": "true", "GITHUB_REPOSITORY": BIND.REPOSITORY, "GITHUB_EVENT_NAME": "push",
        "GITHUB_REF": "refs/heads/" + BIND.BRANCH, "GITHUB_RUN_ATTEMPT": "1", "RUNNER_OS": "macOS", "RUNNER_ARCH": "ARM64",
        "HALALTAG_HOSTED_ENVIRONMENT": "github-hosted", "DEVELOPER_DIR": BIND.DEVELOPER_DIR,
        "ImageOS": "macos27", "ImageVersion": "synthetic-fixture-only", "GITHUB_RUN_ID": "123", "GITHUB_SHA": "8" * 40}
    return config, review, env


class HostedContract(unittest.TestCase):
    def test_exact_ordered_model_retains_intentional_duplicates(self):
        value = passed_native()["model_checks"]["actual_result"]
        self.assertLess(len(set(value["checks"])), 211)
        self.assertEqual(GATE.model_result(value, COVERAGE)["check_count"], 211)
        value["checks"][0], value["checks"][1] = value["checks"][1], value["checks"][0]
        with self.assertRaises(ValueError): GATE.model_result(value, COVERAGE)

    def test_complete_native_required_before_archive(self):
        self.assertEqual(GATE.require_native_gate(passed_native(), COVERAGE)["ui_methods"], 19)
        for key, value in (("native_ui_result", "EXECUTED_EVIDENCE_PENDING"), ("exit_code", 143),
                           ("cleanup_safe", False), ("lock", "retained"), ("all_owned_processes_closed", False),
                           ("deadline_minutes", 46), ("automatic_test_retries", 1), ("original_host_receipts", 19)):
            report = passed_native(); report[key] = value
            with self.subTest(key=key), self.assertRaises(ValueError): GATE.require_native_gate(report, COVERAGE)

    def test_wrong_method_retries_or_missing_real_command_rejected(self):
        for change in ("wrong", "retry", "missing", "duplicate"):
            report = passed_native()
            if change == "wrong": report["steps"][0]["argv"][-1] += "OtherMethod"
            elif change == "retry": report["steps"][0]["argv"].append("-retry-tests-on-failure")
            elif change == "missing": report["steps"].pop()
            else: report["steps"].append(deepcopy(report["steps"][0]))
            with self.subTest(change=change), self.assertRaises(ValueError): GATE.require_native_gate(report, COVERAGE)

    def test_production_requires_actual_verifier_cleanup_and_native_binding(self):
        native_sha = "a" * 64
        report = {"scope": "DISTINCT_HOSTED_R11_UNSIGNED_PRODUCTION_ARCHIVE", "source_commit": BIND.SOURCE_COMMIT,
            "exit_code": 0, "cleanup_safe": True, "all_owned_processes_closed": True, "lock": "released", "errors": [],
            "cancel_signal": None, "source_manifest_status": "passed", "skip_production": False, "deadline_minutes": 20,
            "cleanup_reserve_seconds": 120, "accepted_native_report_sha256": native_sha,
            "shipping_integrity_result": "UNSIGNED_ARCHIVE_INTEGRITY_CHECKS_PASSED", "steps": [
                {"name": name, "status": "passed"} for name in ("halal-production-settings", "halal-production-archive", "halal-shipping-integrity-verifier")]}
        verifier = {"status": "UNSIGNED_ARCHIVE_INTEGRITY_CHECKS_PASSED", "source_commit": BIND.SOURCE_COMMIT,
            "shipping_contract_sha256": "5ef3cc1d338d09734afceb1515963bc793ba4924bce441f831053f716d430c22",
            "archive_checks": {"unsigned": True, "executable_mode": "0755", "code_signature_load_command_present": False}}
        self.assertFalse(GATE.require_production_gate(report, verifier, native_sha)["store_release"])
        for change in ("wrong-native", "failed-verifier", "unsigned-unknown", "unclean"):
            r, v = deepcopy(report), deepcopy(verifier)
            if change == "wrong-native": r["accepted_native_report_sha256"] = "b" * 64
            elif change == "failed-verifier": r["steps"][-1]["status"] = "failed"
            elif change == "unsigned-unknown": v["archive_checks"].pop("unsigned")
            else: r["cleanup_safe"] = False
            with self.subTest(change=change), self.assertRaises(ValueError): GATE.require_production_gate(r, v, native_sha)

    def test_native_context_fails_unbound_wrong_platform_attempt_and_cost(self):
        now = datetime(2026, 11, 18, 10, tzinfo=timezone.utc)
        args = bound_context()
        BIND.validate_context(*args, now, "darwin", "arm64", "27.0.1")
        for change in ("unbound", "local", "retry", "paid", "space", "expired", "wrong-platform"):
            config, review, env = bound_context()
            system = "darwin"
            if change == "unbound": config["authorization"] = "UNBOUND"
            elif change == "local": env.pop("GITHUB_ACTIONS")
            elif change == "retry": env["GITHUB_RUN_ATTEMPT"] = "2"
            elif change == "paid": config["cost"]["additional_spend_usd"] = 1
            elif change == "space": config["cost"]["reserved_included_storage_bytes"] = 1
            elif change == "expired": config["cost"]["valid_until_utc"] = "2026-11-18T10:30:00Z"
            else: system = "linux"
            review["candidate_contract_sha256"] = BIND.candidate_contract(config)
            with self.subTest(change=change), self.assertRaises(ValueError):
                BIND.validate_context(config, review, env, now, system, "arm64", "27.0.1")
        # Collection can preserve expired work; it cannot authorize another run.
        config, review, env = bound_context()
        late = datetime(2026, 11, 18, 23, tzinfo=timezone.utc)
        with self.assertRaises(ValueError): BIND.validate_context(config, review, env, late, "darwin", "arm64", "27.0.1")
        BIND.validate_context(config, review, env, late, "darwin", "arm64", "27.0.1", collecting=True)

    def test_strict_json_control_and_actual_stage_membership(self):
        tree = ast.parse((HERE / "native_driver.py").read_text())
        names = {"require", "digest", "copy_source", "verify_stage"}
        module = ast.Module(body=[n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in names], type_ignores=[])
        scope = {"hashlib": hashlib, "stat": stat, "json": json, "MANIFEST": "manifest.json"}
        exec(compile(module, "selected-pure-stage-functions", "exec"), scope)
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); source = root / "source"; source.mkdir()
            body = b"exact synthetic source\n"; (source / "run.sh").write_bytes(body); (source / "run.sh").chmod(0o755)
            rows = [{"path": "run.sh", "mode": "100755", "bytes": len(body),
                     "git_blob": hashlib.sha1(b"blob " + str(len(body)).encode() + b"\0" + body).hexdigest(),
                     "sha256": hashlib.sha256(body).hexdigest()}]
            stage = root / "stage"; scope["copy_source"](source, rows, stage)
            self.assertEqual(stat.S_IMODE((stage / "run.sh").stat().st_mode), 0o755)
            (stage / "extra.txt").write_text("unexpected")
            with self.assertRaises(ValueError): scope["verify_stage"](stage, rows)
            bad = root / "duplicate.json"; bad.write_text('{"x":1,"x":2}')
            with self.assertRaises(ValueError): BIND.read_json(bad)

    def test_native_entry_is_explicit_and_inherited_lifecycle_is_not_overridden(self):
        tree = ast.parse((HERE / "native_driver.py").read_text())
        functions = {n.name:n for n in tree.body if isinstance(n, ast.FunctionDef)}
        klass = next(n for n in functions["runner_class"].body if isinstance(n, ast.ClassDef))
        overrides = {n.name for n in klass.body if isinstance(n, ast.FunctionDef)}
        self.assertFalse(overrides & {"run", "stop_owned", "cleanup", "checkpoint", "create_simulator", "validate_manifest", "production_archive"})
        main = ast.get_source_segment((HERE / "native_driver.py").read_text(), functions["main"])
        self.assertIn('default="inspect"', main)
        self.assertLess(main.index('hosted.load_bound'), main.index('execute_bound'))
        lifecycle = (HERE / "publishing_runner_frozen.py").read_bytes()
        self.assertEqual(hashlib.sha256(lifecycle).hexdigest(), BIND.BASE_SHA)

    def test_missing_truncated_or_wrong_shaped_reports_fail_without_rewriting(self):
        collector = pure("collect_evidence")
        packer = pure("evidence_pack")
        config, _, env = bound_context()
        env["HALALTAG_NATIVE_STEP_OUTCOME"] = "success"
        with tempfile.TemporaryDirectory() as folder:
            base = Path(folder)
            candidate = base / "Candidate"; candidate.mkdir()
            (candidate / "control.txt").write_text("synthetic exact control, no native code")
            for number, raw in enumerate((None, b'{"status":', b'[]', b'{"status":"queued"}', b'{"x":1,"x":2}')):
                attempt = base / str(number); attempt.mkdir()
                path = attempt / "attempt.json"
                if raw is not None: path.write_bytes(raw)
                (attempt / "original-failure.log").write_bytes(b'unchanged failed native output\n')
                before = {p.name:p.read_bytes() for p in attempt.iterdir()}
                verdict = collector.make_verdict(attempt, config, COVERAGE, env)
                self.assertFalse(verdict["computation_gate_passed"])
                self.assertTrue(verdict["errors"])
                self.assertEqual(before, {p.name:p.read_bytes() for p in attempt.iterdir()})
                encoded = (json.dumps(verdict) + "\n").encode()
                output = base / ("Evidence-" + str(number))
                packed = packer.pack_evidence({"Attempt": attempt, "Candidate": candidate}, output,
                    maximum_artifact_bytes=100_000, verdict_bytes=encoded)
                self.assertEqual(packed["status"], "COMPLETE_EVIDENCE_PACKAGE_VERIFIED_WITHIN_BOUND_CAP")
                self.assertEqual((output / "verdict.json").read_bytes(), encoded)
                indexed = json.loads((output / "complete-member-index.json").read_bytes())
                self.assertIn("Attempt/original-failure.log", indexed["members"])
                if raw is not None: self.assertIn("Attempt/attempt.json", indexed["members"])
                self.assertEqual(before, {p.name:p.read_bytes() for p in attempt.iterdir()})

    def test_raw_host_preservation_keeps_malformed_bytes_and_link_metadata(self):
        import os
        import shutil
        from types import SimpleNamespace
        tree = ast.parse((HERE / "native_driver.py").read_text())
        selected = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in {"require", "digest", "raw_tree_inventory"}]
        factory = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "runner_class")
        klass = next(n for n in factory.body if isinstance(n, ast.ClassDef))
        method = next(n for n in klass.body if isinstance(n, ast.FunctionDef) and n.name == "preserve_raw_hosts")
        module = ast.Module(body=selected+[method], type_ignores=[])
        def write(path, value): path.write_text(json.dumps(value))
        scope = {"hashlib": hashlib, "stat": stat, "os": os, "Path": Path, "shutil": shutil,
                 "base": SimpleNamespace(write_json=write)}
        exec(compile(module, "selected-pure-host-copy-functions", "exec"), scope)
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); simulator = "00112233-4455-6677-8899-aabbccddeeff"; run = "11223344-5566-7788-99aa-bbccddeeff00"
            source = root / simulator / "Documents/AppearanceQA" / run
            (source / "case").mkdir(parents=True)
            raw = b'{"interrupted original JSON":'
            (source / "case/started.json").write_bytes(raw)
            (source / "original-link").symlink_to("absent-original-target")
            obj = SimpleNamespace(known_host_root=source, simulator=simulator, qa_run_id=run, output=root / "Output")
            value = scope["preserve_raw_hosts"](obj, "failure-before-parser")
            copied = obj.output / "raw-host-snapshots/failure-before-parser/Original"
            self.assertEqual((copied / "case/started.json").read_bytes(), raw)
            self.assertTrue((copied / "original-link").is_symlink())
            self.assertEqual(os.readlink(copied / "original-link"), "absent-original-target")
            self.assertEqual(value["status"], "ALL_RAW_HOST_MEMBERS_PRESERVED_WITHOUT_PARSING")


if __name__ == "__main__":
    unittest.main(verbosity=2)
