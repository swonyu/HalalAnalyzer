"""File/fixture boundaries only. No Apple tool, Git process or native invocation."""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest import mock

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("halaltag_inventory_fixture_module", HERE / "inventory_only.py")
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def encoded(value):
    return json.dumps(value).encode()


class InventoryBoundaries(unittest.TestCase):
    def setUp(self):
        self.process_guard = mock.patch.object(MODULE.subprocess, "run", side_effect=AssertionError("No process allowed in fixture checks"))
        self.process_guard.start()
        self.addCleanup(self.process_guard.stop)

    def platform_values(self):
        return {
            "ui-help": b"", "ui-help-stderr": (HERE / "expected-simctl-ui-help.stderr").read_bytes(),
            "xcode-version": b"Xcode 26.6\nBuild version 17F113\n",
            "iphoneos-sdk": b"26.5\n", "iphonesimulator-sdk": b"26.5\n",
            "device-type-inventory": encoded({"devicetypes": [{"name": "iPhone SE (3rd generation)",
                "identifier": "com.apple.CoreSimulator.SimDeviceType.iPhone-SE-3rd-generation",
                "modelIdentifier": "iPhone14,6", "productFamily": "iPhone"}]}),
            "runtime-inventory": encoded({"runtimes": [{"identifier": "com.apple.CoreSimulator.SimRuntime.iOS-26-5",
                "version": "26.5", "buildversion": "23F77", "isAvailable": True,
                "supportedDeviceTypes": [{"identifier": "com.apple.CoreSimulator.SimDeviceType.iPhone-SE-3rd-generation",
                    "name": "iPhone SE (3rd generation)", "productFamily": "iPhone"}]}]}),
        }

    def context_values(self):
        config, _, _ = MODULE.inspect_contract(HERE)
        config["authorization"] = "ROOT_REVIEWED_INVENTORY_ONLY"
        review = {"scope": MODULE.SCOPE, "source_commit": MODULE.SOURCE_COMMIT,
            "candidate_contract_sha256": MODULE.candidate_contract(config),
            "native_build_test_archive_authorized": False, "additional_spend_usd": 0,
            "proposal_receipt_sha256": "a" * 64, "independent_peer_receipt_sha256": "b" * 64}
        env = {"GITHUB_ACTIONS": "true", "GITHUB_REPOSITORY": "swonyu/HalalAnalyzer",
            "GITHUB_EVENT_NAME": "push", "GITHUB_REF": "refs/heads/" + MODULE.BRANCH,
            "GITHUB_RUN_ATTEMPT": "1", "RUNNER_OS": "macOS", "RUNNER_ARCH": "ARM64",
            "RUNNER_ENVIRONMENT": "github-hosted", "REPOSITORY_VISIBILITY": "public",
            "DEVELOPER_DIR": MODULE.DEVELOPER_DIR, "GITHUB_RUN_ID": "123456", "GITHUB_SHA": "c" * 40}
        return config, review, env

    def test_exact_inventory_is_not_native_geometry_or_acceptance(self):
        result = MODULE.evaluate_platform(self.platform_values(), "26.7.2", False)
        self.assertEqual(result["actual_window_and_png_geometry"], "NOT_RUN_REQUIRES_ORIGINAL_NATIVE_ASSERTIONS")

    def test_original_build_and_other_runtime_choices_remain_rejected(self):
        for build in ("24A5423a", "24A434", "24A94425", "24B8117", "24B91016s"):
            values = self.platform_values()
            runtime = json.loads(values["runtime-inventory"])["runtimes"][0]
            runtime["buildversion"] = build
            values["runtime-inventory"] = encoded({"runtimes": [runtime]})
            with self.subTest(build=build), self.assertRaises(ValueError):
                MODULE.evaluate_platform(values, "26.7.2", False)
        runtime = json.loads(self.platform_values()["runtime-inventory"])["runtimes"][0]
        for rows in ([], [runtime, runtime], [{**runtime, "isAvailable": False}],
                     [{**runtime, "version": "27.1"}]):
            values = self.platform_values(); values["runtime-inventory"] = encoded({"runtimes": rows})
            with self.subTest(rows=rows), self.assertRaises(ValueError):
                MODULE.evaluate_platform(values, "26.7.2", False)
        good = MODULE.evaluate_platform(self.platform_values(), "26.7.2", False)
        self.assertEqual(good["platform_revision"]["original_inventory_gate"], "FAILED_RUNTIME_BUILD_UNAVAILABLE")
        self.assertEqual(good["platform_revision"]["runtime_build"], "23F77")
        self.assertEqual(good["actual_window_and_png_geometry"], "NOT_RUN_REQUIRES_ORIGINAL_NATIVE_ASSERTIONS")

    def test_candidate_cannot_erase_original_failure_or_change_successor(self):
        original, _, _ = MODULE.inspect_contract(HERE)
        for key, value in (("runtime_build", "24A5423a"), ("original_inventory_gate", "PASSED"),
                           ("original_inventory_artifact_sha256", "0" * 64)):
            with self.subTest(key=key), tempfile.TemporaryDirectory() as folder:
                root = Path(folder)
                for name in ("source-index.json", "coverage-contract.json", "expected-simctl-ui-help.stderr"):
                    (root / name).write_bytes((HERE / name).read_bytes())
                altered = deepcopy(original); altered["platform_revision"][key] = value
                (root / "candidate.json").write_bytes(encoded(altered))
                with self.assertRaises(ValueError): MODULE.inspect_contract(root)
        config, review, env = self.context_values()
        env["GITHUB_REF"] = "refs/heads/continuation/halaltag-r11-hosted-preflight-d57"
        with self.assertRaises(ValueError):
            MODULE.validate_context(config, review, env, datetime(2026, 11, 18, 16, tzinfo=timezone.utc), "darwin", "arm64")

    def test_runtime_build_sdk_and_xcode_mismatches_fail_closed(self):
        for key, value in (("runtime-inventory", encoded({"runtimes": [{"identifier": "com.apple.CoreSimulator.SimRuntime.iOS-26-5",
                 "version": "27.0", "buildversion": "DIFFERENT", "isAvailable": True}]})),
                ("iphoneos-sdk", b"27.1\n"), ("xcode-version", b"Xcode 27.1\nBuild version 27A9275\n")):
            values = self.platform_values(); values[key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                MODULE.evaluate_platform(values, "26.7.2", False)

    def test_missing_duplicate_and_different_device_never_fall_back(self):
        good = json.loads(self.platform_values()["device-type-inventory"])["devicetypes"][0]
        for rows in ([], [good, good], [{**good, "name": "iPhone 18 Pro"}], [{**good, "modelIdentifier": "iPhone99,1"}]):
            values = self.platform_values(); values["device-type-inventory"] = encoded({"devicetypes": rows})
            with self.subTest(rows=rows), self.assertRaises(ValueError):
                MODULE.evaluate_platform(values, "26.7.2", False)
        with self.assertRaises(ValueError):
            MODULE.evaluate_platform(self.platform_values(), "26.7.2", True)

    def test_duplicate_nonfinite_and_malformed_json_are_rejected(self):
        for data in (b'{"x":1,"x":2}', b'{"x":NaN}', b'{"x":'):
            with self.subTest(data=data), self.assertRaises(ValueError):
                MODULE.strict_json(data)
        for root in ([], {"runtimes": "wrong"}, {"runtimes": [None]}):
            values = self.platform_values(); values["runtime-inventory"] = encoded(root)
            with self.subTest(root=root), self.assertRaises(ValueError):
                MODULE.evaluate_platform(values, "26.7.2", False)

    def test_context_requires_bound_public_hosted_first_attempt(self):
        config, review, env = self.context_values()
        now = datetime(2026, 11, 18, 3, tzinfo=timezone.utc)
        MODULE.validate_context(config, review, env, now, "darwin", "arm64")
        for key, value in (("GITHUB_RUN_ATTEMPT", "2"), ("REPOSITORY_VISIBILITY", "private"),
                           ("RUNNER_ENVIRONMENT", "self-hosted"), ("GITHUB_EVENT_NAME", "workflow_dispatch"),
                           ("GITHUB_REPOSITORY", "someone/HalalAnalyzer")):
            changed = {**env, key: value}
            with self.subTest(key=key), self.assertRaises(ValueError):
                MODULE.validate_context(config, review, changed, now, "darwin", "arm64")
        for system, machine in (("linux", "arm64"), ("darwin", "x86_64")):
            with self.assertRaises(ValueError): MODULE.validate_context(config, review, env, now, system, machine)
        with self.assertRaises(ValueError):
            MODULE.validate_context({**config, "authorization": "UNBOUND"}, review, env, now, "darwin", "arm64")
        with self.assertRaises(ValueError):
            MODULE.validate_context(config, review, env, datetime(2026, 11, 18, 22, 20, tzinfo=timezone.utc), "darwin", "arm64")

    def test_default_is_file_inspection_and_command_surface_is_read_only(self):
        with mock.patch.object(MODULE.sys, "argv", ["inventory_only.py"]):
            self.assertEqual(MODULE.main(), 0)
        for args in MODULE.COMMANDS.values():
            self.assertNotIn("archive", args)
            self.assertNotIn("build", args)
            self.assertNotIn("test", args)
            if "simctl" in args:
                self.assertIn(args[2], ("list", "help"))
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            with self.assertRaises(ValueError): MODULE.command("simulator-create", root, root, 1)
            self.assertEqual(list(root.iterdir()), [])

    def test_started_record_and_raw_streams_exist_during_success_timeout_and_interruption(self):
        for outcome in ("success", "timeout", "interruption"):
            with self.subTest(outcome=outcome), tempfile.TemporaryDirectory() as folder:
                root = Path(folder)
                def fake_command(argv, *, cwd, stdout, stderr, timeout, check):
                    record = root / "commands" / "xcode-version"
                    self.assertEqual(MODULE.read_json(record / "started.json")["status"], "STARTED")
                    self.assertEqual(MODULE.read_json(record / "started.json")["argv"], argv)
                    self.assertFalse((record / "result.json").exists())
                    self.assertEqual(Path(stdout.name), record / "stdout.bin")
                    self.assertEqual(Path(stderr.name), record / "stderr.bin")
                    stdout.write(b"original partial stdout\n"); stdout.flush()
                    stderr.write(b"original partial stderr\n"); stderr.flush()
                    self.assertEqual((record / "stdout.bin").read_bytes(), b"original partial stdout\n")
                    self.assertEqual((record / "stderr.bin").read_bytes(), b"original partial stderr\n")
                    self.assertGreater(timeout, 0); self.assertLessEqual(timeout, 30)
                    if outcome == "timeout":
                        raise MODULE.subprocess.TimeoutExpired(argv, timeout)
                    if outcome == "interruption":
                        raise KeyboardInterrupt()
                    return SimpleNamespace(returncode=0)
                with mock.patch.object(MODULE.subprocess, "run", side_effect=fake_command):
                    if outcome == "success":
                        self.assertEqual(MODULE.command("xcode-version", root, root, MODULE.time.monotonic() + 300),
                                         b"original partial stdout\n")
                    else:
                        expected = ValueError if outcome == "timeout" else KeyboardInterrupt
                        with self.assertRaises(expected):
                            MODULE.command("xcode-version", root, root, MODULE.time.monotonic() + 300)
                record = root / "commands" / "xcode-version"
                terminal = MODULE.read_json(record / "result.json")
                self.assertEqual(terminal["status"], "PASSED" if outcome == "success" else "FAILED_OR_INTERRUPTED")
                for stream in ("stdout", "stderr"):
                    raw = (record / (stream + ".bin")).read_bytes()
                    self.assertEqual(terminal[stream + "_sha256"], MODULE.sha(raw))
                    self.assertEqual(terminal[stream + "_bytes"], len(raw))

    def test_any_occupied_native_lock_path_including_dangling_link_fails_closed(self):
        with tempfile.TemporaryDirectory() as folder:
            lock = Path(folder) / "native.lock"
            self.assertFalse(MODULE.occupied_native_lock(lock))
            lock.symlink_to(Path(folder) / "missing-target")
            self.assertFalse(lock.exists())
            self.assertTrue(MODULE.occupied_native_lock(lock))
            with self.assertRaises(ValueError):
                MODULE.evaluate_platform(self.platform_values(), "26.7.2", MODULE.occupied_native_lock(lock))
            lock.unlink(); lock.mkdir()
            self.assertTrue(MODULE.occupied_native_lock(lock))
            lock.rmdir(); lock.write_bytes(b"owned lock")
            self.assertTrue(MODULE.occupied_native_lock(lock))

    def test_actual_root_binding_and_control_bytes_are_verified_before_commands(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder) / "checkout"
            directory = root / "publishing/hosted-r11"; directory.mkdir(parents=True)
            temp = Path(folder) / "runner-temp"; temp.mkdir()
            controls = []
            for name in ("inventory_only.py", "source-index.json", "coverage-contract.json", "expected-simctl-ui-help.stderr"):
                data = (HERE / name).read_bytes(); path = directory / name; path.write_bytes(data); path.chmod(0o644)
                controls.append({"path": "publishing/hosted-r11/" + name, "bytes": len(data),
                                 "sha256": MODULE.sha(data), "mode": "0644"})
            config, review, env = self.context_values()
            review["control_files"] = controls
            review_bytes = encoded(review); (directory / "root-review.json").write_bytes(review_bytes)
            config["root_review_sha256"] = MODULE.sha(review_bytes)
            (directory / "candidate.json").write_bytes(encoded(config))
            env.update(GITHUB_WORKSPACE=str(root), RUNNER_TEMP=str(temp))
            with mock.patch.object(MODULE, "HERE", directory), mock.patch.dict(os.environ, env), \
                 mock.patch.object(MODULE.sys, "platform", "darwin"), mock.patch.object(MODULE.platform, "machine", return_value="arm64"):
                # Collection bypasses only the wall-clock start limit so retained
                # evidence can still be packed after its inventory window closes.
                self.assertEqual(MODULE.bound_paths(collecting=True)[4], root)
                (directory / "inventory_only.py").write_text("altered control bytes")
                with self.assertRaises(ValueError): MODULE.bound_paths(collecting=True)

    def source_fixture(self, root):
        workflow = "c" * 40
        rows = []
        tree = []
        for name, data in (("app.swift", b"original source\n"), ("Tests/check.swift", b"original assertion\n")):
            path = root / name; path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(data); path.chmod(0o644)
            blob = hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()
            rows.append({"path": name, "mode": "100644", "git_blob": blob, "bytes": len(data),
                         "native_input": True, "sha256": MODULE.sha(data)})
            tree.append(b"100644 blob " + blob.encode() + b"\t" + name.encode() + b"\0")
        controls = ["publishing/hosted-r11/inventory_only.py", "publishing/hosted-r11/candidate.json", "publishing/hosted-r11/root-review.json"]
        for name in controls: tree.append(b"100644 blob " + b"d" * 40 + b"\t" + name.encode() + b"\0")
        values = {"git-head": workflow.encode() + b"\n", "git-parent": (workflow + " " + MODULE.SOURCE_COMMIT).encode() + b"\n",
                  "git-tree": b"".join(tree), "git-status": b""}
        return {"files": rows}, {"control_files": [{"path": controls[0]}]}, values, workflow

    def test_source_mutation_mode_extra_path_and_wrong_parent_are_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); index, review, values, workflow = self.source_fixture(root)
            self.assertEqual(len(MODULE.verify_source(root, index, review, values, workflow)), 2)
            original = (root / "app.swift").read_bytes()
            (root / "app.swift").write_bytes(b"weakened source\n")
            with self.assertRaises(ValueError): MODULE.verify_source(root, index, review, values, workflow)
            (root / "app.swift").write_bytes(original); (root / "app.swift").chmod(0o755)
            with self.assertRaises(ValueError): MODULE.verify_source(root, index, review, values, workflow)
            (root / "app.swift").chmod(0o644)
            for changed in ({**values, "git-parent": (workflow + " " + "e" * 40).encode()},
                            {**values, "git-tree": values["git-tree"] + b"100644 blob " + b"f" * 40 + b"\textra.swift\0"},
                            {**values, "git-status": b" M app.swift\n"}):
                with self.assertRaises(ValueError): MODULE.verify_source(root, index, review, changed, workflow)

    def test_malformed_report_preserves_every_original_and_is_not_accepted(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); output = root / "evidence"; output.mkdir()
            raw = b'{"status":broken'; (output / "RESULT.json").write_bytes(raw)
            (output / "raw-inventory.bin").write_bytes(b"complete original\0bytes")
            step = root / "step-output"; step.write_text("")
            with mock.patch.object(MODULE, "bound_paths", return_value=(None, None, None, None, root, output)), \
                 mock.patch.dict(os.environ, {"GITHUB_OUTPUT": str(step)}):
                self.assertEqual(MODULE.collect(), 0)
            self.assertEqual((output / "RESULT.json").read_bytes(), raw)
            self.assertFalse(MODULE.read_json(output / "COLLECTION.json")["platform_inventory_accepted"])
            self.assertIn("platform_eligible=false", step.read_text())
            self.assertTrue(output.with_suffix(".tar.gz").is_file())

    def test_over_cap_refuses_upload_without_deleting_originals(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); output = root / "evidence"; output.mkdir()
            (output / "RESULT.json").write_text('{"status":"FAILED"}')
            raw = b"complete raw inventory"; (output / "original.txt").write_bytes(raw)
            step = root / "step-output"; step.write_text("")
            with mock.patch.object(MODULE, "bound_paths", return_value=(None, None, None, None, root, output)), \
                 mock.patch.object(MODULE, "ARCHIVE_LIMIT", 10), mock.patch.dict(os.environ, {"GITHUB_OUTPUT": str(step)}):
                with self.assertRaises(ValueError): MODULE.collect()
            self.assertEqual((output / "original.txt").read_bytes(), raw)
            self.assertTrue(output.with_suffix(".tar.gz").is_file())
            self.assertEqual(step.read_text(), "")


    def test_stale_r11_identity_index_and_branch_cannot_be_reused_for_r12(self):
        original, _, _ = MODULE.inspect_contract(HERE)
        for field, value in (("source_commit", "7ef009beb0c1f6f355eeceb931d899553ea8cad5"),
                             ("source_tree", "97b9e5eca0e4bc5c82ceb8b133fc823eed1af4bf")):
            with self.subTest(candidate_field=field), tempfile.TemporaryDirectory() as folder:
                root = Path(folder)
                for name in ("source-index.json", "coverage-contract.json", "expected-simctl-ui-help.stderr"):
                    (root / name).write_bytes((HERE / name).read_bytes())
                altered = deepcopy(original); altered[field] = value
                (root / "candidate.json").write_bytes(encoded(altered))
                with self.assertRaises(ValueError): MODULE.inspect_contract(root)
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            index = MODULE.read_json(HERE / "source-index.json")
            index["commit"] = "7ef009beb0c1f6f355eeceb931d899553ea8cad5"
            raw = encoded(index); (root / "source-index.json").write_bytes(raw)
            (root / "coverage-contract.json").write_bytes((HERE / "coverage-contract.json").read_bytes())
            (root / "expected-simctl-ui-help.stderr").write_bytes((HERE / "expected-simctl-ui-help.stderr").read_bytes())
            altered = deepcopy(original); altered["source_index_sha256"] = MODULE.sha(raw)
            (root / "candidate.json").write_bytes(encoded(altered))
            with self.assertRaises(ValueError): MODULE.inspect_contract(root)
        config, review, env = self.context_values()
        env["GITHUB_REF"] = "refs/heads/continuation/halaltag-r11-hosted-preflight-v3-d57"
        with self.assertRaises(ValueError):
            MODULE.validate_context(config, review, env, datetime(2026, 11, 18, 18, tzinfo=timezone.utc), "darwin", "arm64")



    def test_runtime_must_explicitly_support_exact_se3_without_ambiguity(self):
        good = self.platform_values()
        original = json.loads(good["runtime-inventory"])["runtimes"][0]
        support = original["supportedDeviceTypes"][0]
        for supports in (None, [], [support, support], [{**support, "name": "iPhone 17 Pro"}],
                         [{**support, "productFamily": "iPad"}], [None]):
            values = self.platform_values(); runtime = deepcopy(original)
            if supports is None: runtime.pop("supportedDeviceTypes")
            else: runtime["supportedDeviceTypes"] = supports
            values["runtime-inventory"] = encoded({"runtimes": [runtime]})
            with self.subTest(supports=supports), self.assertRaises(ValueError):
                MODULE.evaluate_platform(values, "26.7.2", False)

    def test_fresh_ui_help_must_match_every_original_byte(self):
        original = self.platform_values()
        for key, value in (("ui-help", b"unexpected stdout"), ("ui-help-stderr", b""),
                           ("ui-help-stderr", original["ui-help-stderr"][:-1] + b"x"),
                           ("ui-help-stderr", None)):
            values = {**original, key: value}
            with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                MODULE.evaluate_platform(values, "26.7.2", False)
        accepted = MODULE.evaluate_platform(original, "26.7.2", False)
        self.assertEqual(accepted["actual_ui_help"]["stderr_sha256"], MODULE.UI_HELP_SHA256)
        self.assertEqual(accepted["runtime_supported_se3"]["identifier"],
                         "com.apple.CoreSimulator.SimDeviceType.iPhone-SE-3rd-generation")
        for key, value in (("xcode-version", b"Xcode 27.0\nBuild version 27A266a\n"),
                           ("iphoneos-sdk", b"27.0\n"), ("iphonesimulator-sdk", b"27.0\n")):
            with self.subTest(old_platform_field=key), self.assertRaises(ValueError):
                MODULE.evaluate_platform({**original, key: value}, "26.7.2", False)
        with self.assertRaises(ValueError): MODULE.evaluate_platform(original, "27.0.1", False)



if __name__ == "__main__":
    unittest.main()
