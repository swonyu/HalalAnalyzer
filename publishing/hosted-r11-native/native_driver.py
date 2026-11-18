#!/usr/bin/env python3
"""Distinct hosted HalalTag R12 executor proposal; unbound and not invoked.

The default action checks local proposal files only. Native execution is a
separate explicit mode requiring a root-bound public hosted attempt and exact
platform inventory. No local Mac entry point or old acknowledgment is accepted.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import platform
import re
import shutil
import signal
import stat
import sys
import time
import uuid


sys.dont_write_bytecode = True
from gate_checks import model_result, require_native_gate, require_production_gate
import console_diagnostics as diagnostics
HERE = Path(__file__).absolute().parent
MANIFEST = "Tests/NativeQA/UITests/HalalTagSyntheticQAInstallation.json"
APP_ID = "com.saleh.halaltag.productioncomposition.qa.r20261117r11"
TEST_ID = APP_ID + ".uitests"
TARGET = "HalalTagQAUItests"
ENV_MODE = "ISOLATED_SYNTHETIC_QA"
EXPECTED_SUPPORT = {
    "publishing_runner_frozen.py": "1980cdf5a564a802198183fd79ee2f0a325b486908bab45e01beaadb02e50f99",
    "appearance_evidence_guard.py": "e520953ae9220ac280f9f700fbace00c2eda9987b495b8b1f356e1c475e1cde3",
    "arabic_appearance_evidence_guard.py": "27a84445670a1fed8b83b04d9fbd6787dea41a355ce9d3dc111c058fc81eaacb",
    "appearance_png.py": "0d22ed3a871d4abdf5c8272a3a7319b4c8698d45d77554d5261140e4ac9c7f2d",
    "system_size_evidence.py": "e2e58acbb2de819be1e1cc4e0149f7311981c243473c07992df0ca1f67b8e83b",
    "simctl-ui-help-root-20261117.stderr": "2fa67269b4a75d4856edcaf9f65ed4bd830bd0ecae95e370173fa8ed2fe87084",
    "simctl-list-help-installed.stderr": "4c7f0c98a485121183a1bc0b5ae8549958692117107664b4ee1c3fbf0f3c4693",
    "verify_shipping_archive.py": "277a91484bf76524164ff5494d184a547363537233169a74dd460a78c2b0ebe3",
    "shipping-contract.json": "10eafbf563c09ab0c0d97aeffe4f8bbb172dbe3a7b21a3dbdbf1f7e694eafaab",
    "original_attachments.py": "c7230af7e5fddc3a7905188ae1ed8edf1caa97cb6bd65e72ebdf1f913943e2eb",
    "artifact_binding.py": "91775120ca90c398639644d9f4b0fef6150dfb5d529ad86441af06541bff7467",
    "case_evidence.py": "f6e56b316e9d71cbb5eb15f0a5ca81c9b293bf994f9eaf54654ba59dd3d652c4",
    "source-contract.json": "744156409e5e9002c1b368871304f39b4a0d146a797eac1169552d8fdf8c8d4d",
    "nineteen-case-plan.json": "8e6e78d37f6a5a162bff2cb5fb79fc3b91382f333b143554833ab4ec64a05a62",
    "evidence_pack.py": "ee493ee09002132ae47ebfe97b061f17ed6a4c6e1bb1505a944a54c27cd7980a",
    "current_original_union.py": "f25f226051b0fc3acc3dad33042954ca65f8d8ded114514101c67970c519fd7c",
    'appearance_evidence_guard_installed.py': '2f2995f9754555102137cc3b58dfd4f7b8b42fe4ee0b08a48f8031052d2844b7',
    'arabic_appearance_evidence_guard_installed.py': 'c5267c20c6ca04c1626af05205d9236d89c34fa8ad366f15e8feeffb7872dfa9',
    'case_evidence_installed.py': '20de550e3140b9f6fe955679aaddf7760e3ed96618d7833ca693658682579e2c',
    'overflow_evidence.py': '171fe384f6f6ab8a923453205d852427f36e4f74c43283a31ce82e03208e74f7',
    'release_contract.py': '4fe13b6f11f3d9bb07e49761ada2a10c793ac32b20477a26719af8dbcc1fd9cb',
    'github_evidence_transport.py': 'a0c75535e3b6f721f806b55957d2e26d0a39d75690496961157fb771c4cf53fc',
    'release_evidence.py': 'e9c9c44a99f85d47b2c2c07dc680bd5a0ec447a25ea000ded4b256ef4636f9d7',
    'delivery_gate.py': '26dce04c25d15cfa93dbd7945003634eb7529d51bde4a3446f5b45d6015483eb',
    'console_diagnostics.py': '51d371a9c12ef8c892342f7c19b55bfd25e6911e660698ab468a13b27239b7dd',
}


def require(value, message):
    if not value:
        raise ValueError(message)


def digest(path):
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def load_pure(name, path):
    require(name not in sys.modules, "Refuse an ambiguous preloaded support module")
    spec = importlib.util.spec_from_file_location(name, path)
    require(spec is not None and spec.loader is not None, "Support loader unavailable")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def verify_support():
    for name, expected in EXPECTED_SUPPORT.items():
        path = HERE / name
        require(path.is_file() and not path.is_symlink() and digest(path) == expected,
                "Reviewed retained support changed: " + name)


def copy_source(checkout, rows, destination):
    require(not destination.exists() and not destination.is_symlink(), "Preserve existing source stage")
    destination.mkdir(parents=True)
    for row in rows:
        original = checkout / row["path"]
        target = destination / row["path"]
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("xb") as stream:
            stream.write(original.read_bytes())
        target.chmod(int(row["mode"][-3:], 8))
    return verify_stage(destination, rows)


def verify_stage(directory, rows, configured=None):
    require(directory.is_dir() and not directory.is_symlink(), "Source stage is missing or linked")
    actual = {}
    for path in directory.rglob("*"):
        require(not path.is_symlink(), "Source stage contains a symbolic link")
        if path.is_dir():
            continue
        require(path.is_file() and stat.S_ISREG(path.stat().st_mode), "Source stage has a special member")
        actual[path.relative_to(directory).as_posix()] = path
    require(set(actual) == {row["path"] for row in rows}, "Source stage added or omitted an input; reconcile before continuing")
    snapshots = {}
    for row in rows:
        path = actual[row["path"]]; data = path.read_bytes()
        require(stat.S_IMODE(path.stat().st_mode) == int(row["mode"][-3:], 8), "Source Git mode changed")
        if row["path"] == MANIFEST and configured is not None:
            require(json.loads(data) == configured, "Run-owned QA manifest changed unexpectedly")
        else:
            blob = hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()
            require(blob == row["git_blob"] and len(data) == row["bytes"], "Original source bytes changed")
            if row.get("sha256"):
                require(hashlib.sha256(data).hexdigest() == row["sha256"], "Original native SHA changed")
        snapshots[row["path"]] = {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest(),
                                  "mode": f"{stat.S_IMODE(path.stat().st_mode):04o}"}
    return snapshots




def source_manifest(base, source, rows, additional, destination):
    suffixes = base.SOURCE_SUFFIXES
    files = {row["path"]: digest(source / row["path"]) for row in rows
             if Path(row["path"]).suffix in suffixes or Path(row["path"]).name == "Package.resolved"}
    value = {"schema_version": 2, "inventory_policy": base.inventory_policy(),
             "roots": [{"key": "halal", "path": str(source.resolve()), "files": files}],
             "additional_files": {str(path.resolve()): digest(path) for path in additional}}
    base.write_json(destination, value)
    return destination


def write_json(path, value):
    """Only replace a task-owned receipt, never any source or original log."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".hosted-tmp")
    require(not temporary.exists() and not temporary.is_symlink(), "Retain ambiguous prior receipt write")
    with temporary.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False)
        stream.write("\n"); stream.flush(); os.fsync(stream.fileno())
    os.replace(temporary, path)


def raw_tree_inventory(root):
    """Snapshot every original host member without parsing or following links."""
    require(root.is_dir() and not root.is_symlink(), "Original host root is linked or missing")
    result = {}
    for folder, dirs, names in os.walk(root, followlinks=False):
        for name in sorted(dirs + names):
            path = Path(folder) / name
            mode = path.lstat().st_mode
            key = path.relative_to(root).as_posix()
            value = {"mode": f"{stat.S_IMODE(mode):04o}"}
            if stat.S_ISLNK(mode):
                value.update(kind="symlink", link_target=os.readlink(path))
            elif stat.S_ISDIR(mode):
                value.update(kind="directory")
            else:
                require(stat.S_ISREG(mode), "Unexpected special host member")
                value.update(kind="file", bytes=path.stat().st_size, sha256=digest(path))
            result[key] = value
    return result


def phase_args(source, output, manifest, slot, *, production):
    """All values are explicit; no historical Mac defaults or old ACK is used."""
    return argparse.Namespace(apps=["halal"], skip_production=not production,
        deadline_minutes=20 if production else 45, output_root=output,
        source_manifest=manifest, advertising_preparation_root=None, halal_root=source,
        slot_authorized=slot, sim_device_name="iPhone SE (3rd generation)",
        sim_runtime_id="com.apple.CoreSimulator.SimRuntime.iOS-26-5")


def finish_phase(base, runner, action):
    """Use the exact frozen ownership/process/clock/cleanup implementation."""
    code, cleanup_safe = 0, False
    try:
        runner.checkpoint()
        runner.lock.acquire()
        runner.report["lock"] = "acquired"
        runner.report["lock_owner"] = runner.lock.record
        runner.report["free_output_disk_bytes"] = shutil.disk_usage(runner.output).free
        runner.flush()
        action()
    except base.Occupied as error:
        diagnostics.observe_exception("phase-occupied", error)
        runner.report["lock"] = "occupied"
        runner.error("lock", str(error)); code = 75
    except base.BatchStopped as error:
        diagnostics.observe_exception("phase-stopped", error)
        runner.error("batch", str(error))
        code = 128 + runner.cancel_signal if runner.cancel_signal is not None else 124
    except Exception as error:
        diagnostics.observe_exception("phase-error", error)
        runner.error("batch", type(error).__name__ + ": " + str(error)); code = 2
    finally:
        try:
            cleanup_safe = runner.cleanup()
        except Exception as error:
            diagnostics.observe_exception("phase-cleanup-error", error)
            cleanup_safe = False
            runner.report["lock"] = "retained" if runner.lock.acquired else runner.report["lock"]
            runner.report["errors"].append({"stage": "cleanup", "message": type(error).__name__ + ": " + str(error),
                                            "at": base.utc_now()})
        if not cleanup_safe or runner.report["errors"] or runner.cancel_signal is not None:
            code = code or (128 + runner.cancel_signal if runner.cancel_signal is not None else 1)
        runner.report.update(finished_at=base.utc_now(), elapsed_seconds=round(time.monotonic() - runner.started, 3),
            exit_code=code, cleanup_safe=cleanup_safe, cancel_signal=runner.cancel_signal,
            all_owned_processes_closed=all(child["closed"] for child in runner.owned))
        runner.flush()
        diagnostics.phase_terminal(runner.output / "report.json", runner.args.output_root.parent, "phase-terminal")
        diagnostics.lock_observation(runner.args.output_root.parent, "phase-terminal")
    return code




def runner_class(base, binding, appearance, arabic, system_size, cases, attachments, png, current_union):
    class HostedHalalRunner(base.Runner):
        def __init__(self, args, source, native_rows, coverage):
            super().__init__(args)
            self.qa_run_id = str(uuid.UUID(self.run_id))
            self.simulator_name = "HalalTag-Hosted-R12-" + self.run_id[:16]
            self.source = source
            self.native_rows = native_rows
            self.coverage = coverage
            self.project_copy = self.output / "RunSource"
            self.qa_project = self.project_copy / "Tests/NativeQA"
            self.derived_data = self.output / "DerivedData"
            self.original_size, self.original_style = None, None
            self.known_host_root = None
            self.settings_restore_required = False
            self.report.update(scope="DISTINCT_HOSTED_R12_NINETEEN_CASES", qa_run_id=self.qa_run_id,
                native_ui_result="NOT_RUN", original_native_adapter_recovered=False,
                source_commit="b2d1ea13460fe9a8f3aedc1912f474737a1ec2ed",
                case_execution_mode="NINETEEN_ORIGINAL_METHODS_ONCE_EACH",
                automatic_test_retries=0, source_assertions_changed=False,
                original_app_id=APP_ID, expected_model_checks=211, expected_ui_methods=19,
                expected_host_launches=20, expected_supplementary_launch_uuids=17)
            self.flush()

        def xcode(self):
            return ["/usr/bin/xcodebuild", "-project", str(self.qa_project / "HalalTagQA.xcodeproj"),
                "-scheme", "HalalTagQA", "-configuration", "Debug", "-sdk", "iphonesimulator",
                "-destination", "platform=iOS Simulator,id=" + self.simulator,
                "-derivedDataPath", str(self.derived_data), "-jobs", "2",
                "-disableAutomaticPackageResolution", "-skipPackageUpdates",
                "CODE_SIGNING_ALLOWED=NO", "CODE_SIGNING_REQUIRED=NO", "COMPILER_INDEX_STORE_ENABLE=NO",
                "HALALTAG_UI_QA_RUN_MODE=" + ENV_MODE, "HALALTAG_UI_QA_RUN_ID=" + self.qa_run_id]

        def test_settings_command(self):
            result = self.xcode()
            for flag in ("-scheme", "-destination", "-derivedDataPath"):
                index = result.index(flag); del result[index:index + 2]
            return result + ["-target", TARGET, "-showBuildSettings", "-json"]

        def build_tests(self, name):
            self.run(name, self.xcode() + ["-resultBundlePath", str(self.output / (name + ".xcresult")),
                     "build-for-testing"], self.qa_project, 720)
            found = list((self.derived_data / "Build/Products").glob("*.xctestrun"))
            require(len(found) == 1, "One actual retained xctestrun is required")
            return found[0], binding.read_products(found[0], self.derived_data, self.qa_run_id)

        def installed_app(self, expected, name):
            step = self.run(name, ["/usr/bin/xcrun", "simctl", "get_app_container", self.simulator, APP_ID, "app"], self.output, 30)
            path = Path(Path(step["stdout"]).read_text().strip())
            require(path.is_absolute() and path.suffix == ".app" and not path.is_symlink()
                    and self.simulator.upper() in {part.upper() for part in path.resolve().parts},
                    "Installed artifact is not in the exact owned simulator")
            require(binding.plist(path / "Info.plist").get("CFBundleIdentifier") == APP_ID
                    and binding.bundle_snapshot(path) == expected, "Installed QA app bytes differ from bound build")
            return path

        def host_root(self, name):
            step = self.run(name, ["/usr/bin/xcrun", "simctl", "get_app_container", self.simulator, APP_ID, "data"], self.output, 30)
            container = Path(Path(step["stdout"]).read_text().strip())
            require(container.is_absolute() and container.is_dir() and not container.is_symlink()
                    and self.simulator.upper() in {part.upper() for part in container.resolve().parts},
                    "Actual host data path is not bound to the owned simulator")
            value = container / "Documents/AppearanceQA" / self.qa_run_id
            if self.known_host_root is not None:
                require(value == self.known_host_root, "Actual run host container changed")
            self.known_host_root = value
            return value

        def preserve_raw_hosts(self, label):
            source = self.known_host_root
            if source is None:
                return {"status": "NO_OWNED_HOST_PATH_OBSERVED"}
            require(self.simulator.upper() in {part.upper() for part in source.resolve().parts}
                    and source.name == self.qa_run_id, "Raw host preservation path is not the owned run")
            folder = self.output / "raw-host-snapshots" / label
            require(not os.path.lexists(folder), "Preserve any earlier raw host snapshot")
            folder.mkdir(parents=True)
            if not os.path.lexists(source):
                value = {"status": "OWNED_RUN_HOST_PATH_NOT_PRESENT", "source": str(source)}
            else:
                before = raw_tree_inventory(source)
                shutil.copytree(source, folder / "Original", symlinks=True, copy_function=shutil.copy2)
                require(before == raw_tree_inventory(source) == raw_tree_inventory(folder / "Original"),
                        "Original host bytes/modes changed during raw preservation")
                value = {"status": "ALL_RAW_HOST_MEMBERS_PRESERVED_WITHOUT_PARSING", "source": str(source), "members": before}
            base.write_json(folder / "copy-receipt.json", value)
            return value

        def owned_booted(self, name, *, cleanup=False, startup=False):
            require(not startup or (not cleanup and name == "retain-original-setting-destination"),
                    "Startup inventory allowance is restricted to the first owned destination")
            if cleanup:
                # Preserve the original full-list cleanup query and five-second limit.
                value = self.json_command(name, ["/usr/bin/xcrun", "simctl", "list", "devices", "--json"],
                                          self.output, 5, cleanup=True)
                system_size.owned_booted_device(value, simulator=self.simulator, name=self.simulator_name,
                    runtime=self.args.sim_runtime_id, preexisting=self.preexisting_devices,
                    discovery_known=self.simulator_discovery_known)
                return True
            # V9 originals prove the UUID observation and a subsequent full
            # inventory of the still-Booted device; custom-name search returned
            # no rows. Each result must independently pass the unchanged full
            # ID-or-name predicate within one original60/15-second budget.
            end = time.monotonic() + (60 if startup else 15)
            for suffix, argv in (("uuid", ["/usr/bin/xcrun", "simctl", "list", "devices", self.simulator, "--json"]),
                                 ("full", ["/usr/bin/xcrun", "simctl", "list", "devices", "--json"])):
                remaining = end - time.monotonic()
                require(remaining > 0, "Shared owned-device inventory deadline exhausted")
                value = self.json_command(name + "-" + suffix, argv,
                    self.output, remaining, cleanup=False)
                system_size.owned_booted_device(value, simulator=self.simulator, name=self.simulator_name,
                    runtime=self.args.sim_runtime_id, preexisting=self.preexisting_devices,
                    discovery_known=self.simulator_discovery_known)
                require(time.monotonic() <= end, "Shared owned-device inventory deadline overrun")
            return True

        def read_setting(self, name, kind, *, cleanup=False):
            require(kind in ("appearance", "content_size"), "Unknown simulator setting")
            step = self.run(name, ["/usr/bin/xcrun", "simctl", "ui", self.simulator, kind],
                            self.output, 5 if cleanup else 15, cleanup=cleanup)
            text = Path(step["stdout"]).read_text()
            if kind == "content_size":
                return system_size.parse_content_size(text)
            require(text in ("light", "light\n", "light\r\n", "dark", "dark\n", "dark\r\n"), "Unknown actual system appearance")
            return text.strip()

        def case_settings(self, case):
            key = case["execution_id"]
            owned = self.owned_booted(key + "-owned-before-setting")
            self.settings_restore_required = True
            self.report["settings_restore_required"] = True
            self.flush()
            value = {"run_id": self.qa_run_id, "execution_id": key, "case_id": case["case_id"],
                     "device_id": self.simulator, "owned_destination_before": owned}
            for field, kind, desired in (("style", "appearance", case["style"]), ("content_size", "content_size", case["size"])):
                step = self.run(key + "-set-" + kind, ["/usr/bin/xcrun", "simctl", "ui", self.simulator, kind, desired], self.output, 15)
                observed = self.read_setting(key + "-read-" + kind, kind)
                require(observed == desired, "Actual requested simulator setting was not established")
                value[field] = {"requested": desired, "readback_before_test": observed, "set_command_status": step["status"],
                                "set_command_result": str(Path(step["stdout"]).parent / "result.json")}
            return value

        def cleanup_simulator(self):
            restored = True
            if self.known_host_root is not None:
                try:
                    require(all(child["closed"] for child in self.owned), "Owned processes remain before final raw host capture")
                    self.report["final_raw_host_preservation"] = self.preserve_raw_hosts("final-after-owned-process-cleanup")
                except Exception as error:
                    self.error("preserve-final-raw-hosts", str(error))
            if self.settings_restore_required:
                restored = False
                try:
                    require(all(child["closed"] for child in self.owned), "Owned processes remain before setting restoration")
                    require(self.original_style in ("light", "dark") and self.original_size in system_size.VALID_SIZES,
                            "No verified original settings to restore")
                    self.owned_booted("cleanup-owned-settings-destination", cleanup=True)
                    observed = {}
                    for kind, original in (("appearance", self.original_style), ("content_size", self.original_size)):
                        self.run("cleanup-restore-" + kind, ["/usr/bin/xcrun", "simctl", "ui", self.simulator, kind, original],
                                 self.output, 5, cleanup=True)
                        observed[kind] = self.read_setting("cleanup-readback-" + kind, kind, cleanup=True)
                        require(observed[kind] == original, "Original owned setting restoration failed")
                    restored = True
                    self.report["settings_cleanup"] = {"restored_exactly": True, "device_id": self.simulator,
                        "original_style": self.original_style, "original_size": self.original_size, "actual": observed,
                        "other_devices_touched": False}
                except Exception as error:
                    self.error("cleanup-owned-settings", str(error))
                    self.report["settings_cleanup"] = {"restored_exactly": False, "other_devices_touched": False}
                self.flush()
            shutdown = super().cleanup_simulator()
            return restored and shutdown

        def run_model(self):
            folder = self.output / "ModelChecks"; folder.mkdir()
            cache = folder / "ModuleCache"; cache.mkdir()
            rows = self.coverage["model_source_files"]
            sources = [self.project_copy / row["path"] for row in rows]
            executable = folder / "BilingualModelChecks"
            compiled = self.run("compile-original-model-checks", ["/usr/bin/xcrun", "--sdk", "macosx", "swiftc",
                "-parse-as-library", "-swift-version", "5", "-module-cache-path", str(cache),
                *map(str, sources), "-o", str(executable)], self.project_copy, 120)
            require(executable.is_file() and not executable.is_symlink(), "Original model executable missing")
            executed = self.run("execute-original-model-checks", [str(executable)], folder, 30)
            actual = binding.read_json(Path(executed["stdout"]))
            accepted = model_result(actual, self.coverage)
            verify_stage(self.project_copy, self.native_rows)
            receipt = {**accepted, "actual_result": actual, "source_binding": rows, "binary_sha256": digest(executable),
                "compile_stdout": compiled["stdout"], "compile_stderr": compiled["stderr"],
                "execution_stdout": executed["stdout"], "execution_stderr": executed["stderr"],
                "execution_stdout_sha256": digest(Path(executed["stdout"]))}
            base.write_json(self.output / "model-checks-receipt.json", receipt)
            self.report["model_checks"] = receipt
            self.flush()

        def execute(self):
            copy_source(self.source, self.native_rows, self.project_copy)
            require(cases.plan() == self.coverage["ui_cases"], "Case helper and original complete coverage differ")
            cases.verify_source_inputs(self.project_copy)
            self.validate_manifest("before-qa-builds")
            version = self.run("xcode-version", ["/usr/bin/xcodebuild", "-version"], self.output, 30)
            require(Path(version["stdout"]).read_text().strip().splitlines() == ["Xcode 26.6", "Build version 17F113"],
                    "Fresh installed Xcode build differs from reviewed inventory")
            for sdk in ("iphoneos", "iphonesimulator"):
                step = self.run(sdk + "-sdk", ["/usr/bin/xcrun", "--sdk", sdk, "--show-sdk-version"], self.output, 30)
                require(Path(step["stdout"]).read_text().strip() == "26.5", "Fresh SDK differs from reviewed inventory")
            types = self.json_command("exact-device-types", ["/usr/bin/xcrun", "simctl", "list", "devicetypes", "--json"], self.output, 30)
            runtimes = self.json_command("exact-runtimes", ["/usr/bin/xcrun", "simctl", "list", "runtimes", "--json"], self.output, 30)
            base.write_json(self.output / "actual-platform.json", appearance.validate_discovery(types, runtimes))
            self.run_model()
            # Device-independent syntax must be accepted before creating or
            # booting a simulator. The exact bytes and 15-second limit remain.
            help_step = self.run("actual-ui-help", ["/usr/bin/xcrun", "simctl", "help", "ui"], self.output, 15)
            require(Path(help_step["stdout"]).read_bytes() == b""
                    and digest(Path(help_step["stderr"])) == EXPECTED_SUPPORT["simctl-ui-help-root-20261117.stderr"],
                    "Installed setting syntax differs from the retained exact original help")
            list_help_step = self.run("actual-list-help", ["/usr/bin/xcrun", "simctl", "help", "list"], self.output, 15)
            require(Path(list_help_step["stdout"]).read_bytes() == b""
                    and digest(Path(list_help_step["stderr"])) == EXPECTED_SUPPORT["simctl-list-help-installed.stderr"],
                    "Installed device filter syntax differs from the exact accepted tooling help")
            self.create_simulator(self.output)
            self.owned_booted("retain-original-setting-destination", startup=True)
            self.original_style = self.read_setting("retain-original-appearance", "appearance")
            self.original_size = self.read_setting("retain-original-content-size", "content_size")
            base.write_json(self.output / "original-system-settings.json", {"device_id": self.simulator,
                "style": self.original_style, "content_size": self.original_size, "settings_not_yet_changed": True})
            destination = self.output / "destination-receipt.json"
            base.write_json(destination, {"simulator": self.report["simulator"], "dedicated_synthetic_device": True,
                "run_id": self.qa_run_id, "preexisting_device_ids": sorted(self.preexisting_devices)})
            app_settings = self.json_command("qa-app-settings", self.xcode() + ["-showBuildSettings", "-json"], self.qa_project, 60)
            test_settings = self.json_command("qa-test-settings", self.test_settings_command(), self.qa_project, 60)
            base.write_json(self.output / "effective-qa-settings.json", binding.validate_build_settings(app_settings, test_settings))
            initial_run, initial = self.build_tests("initial-build-for-testing")
            verify_stage(self.project_copy, self.native_rows)
            app_snapshot = binding.bundle_snapshot(initial["app"])
            build_receipt = self.output / "build-receipt.json"
            base.write_json(build_receipt, {"run_id": self.qa_run_id, "app": str(initial["app"]), "app_snapshot": app_snapshot,
                "app_id": APP_ID, "test_id": TEST_ID, "initial_xctestrun_sha256": digest(initial_run),
                "source_inputs": verify_stage(self.project_copy, self.native_rows)})
            self.run("install-dedicated-qa-app", ["/usr/bin/xcrun", "simctl", "install", self.simulator, str(initial["app"])], self.output, 90)
            installed = self.installed_app(app_snapshot, "verify-initial-install")
            installation = self.output / "installation-receipt.json"
            base.write_json(installation, {"run_id": self.qa_run_id, "device_id": self.simulator, "bundle_id": APP_ID,
                "app_snapshot": app_snapshot, "installed_path": str(installed), "dedicated_and_synthetic": True})
            manifest = binding.read_json(self.project_copy / MANIFEST)
            require(manifest.get("configurationStatus") == "UNCONFIGURED", "Original manifest was unexpectedly configured")
            manifest.update(configurationStatus="CONFIGURED_ISOLATED_QA", runID=self.qa_run_id,
                qaBundleIdentifier=APP_ID, productionBundleIdentifier="HalalTag.v1.1", uiTestBundleIdentifier=TEST_ID,
                installationIsDedicatedAndSynthetic=True, qaArtifactSHA256=app_snapshot["sha256"],
                buildEvidenceReference=str(build_receipt), installationEvidenceReference=str(installation),
                destinationEvidenceReference=str(destination))
            base.write_json(self.project_copy / MANIFEST, manifest)
            verify_stage(self.project_copy, self.native_rows, manifest)
            retained_run, products = self.build_tests("configured-build-for-testing")
            require(binding.bundle_snapshot(products["app"]) == app_snapshot,
                    "Configuring only the test resource changed app bytes")
            require(binding.read_json(products["tests"] / "HalalTagSyntheticQAInstallation.json") == manifest,
                    "Actual test resource is not bound to the verified installation")
            self.installed_app(app_snapshot, "verify-configured-install")
            xctestrun_sha, tests_sha = digest(retained_run), binding.bundle_snapshot(products["tests"])["sha256"]
            base.write_json(self.output / "execution-binding.json", {"run_id": self.qa_run_id, "manifest": manifest,
                "app_snapshot": app_snapshot, "test_bundle_sha256": tests_sha, "xctestrun_sha256": xctestrun_sha,
                "xctestrun": str(retained_run), "test_bundle": str(products["tests"]), "original_cases": self.coverage["ui_cases"]})
            self.execute_cases(retained_run, products, app_snapshot, xctestrun_sha, tests_sha, manifest)

        def execute_cases(self, retained_run, products, app_snapshot, xctestrun_sha, tests_sha, manifest):
            host_source = self.host_root("verify-initial-empty-host-container")
            previous = cases.host_snapshot(host_source, allow_missing=True)
            require(previous == {}, "New run-specific host path was not empty before the first actual launch")
            observed, maps, host_assignments = [], {}, {}
            retained_hosts = self.output / "native-host-originals"
            retained_hosts.mkdir()
            self.report["case_xcresults"] = {}
            for case in self.coverage["ui_cases"]:
                self.checkpoint()
                key = case["execution_id"]
                folder = self.output / "cases" / key; folder.mkdir(parents=True)
                self.validate_manifest("before-" + key)
                verify_stage(self.project_copy, self.native_rows, manifest)
                before = cases.host_snapshot(host_source, allow_missing=True)
                require(before == previous, "Prior original host evidence changed before the next method")
                setting = self.case_settings(case)
                base.write_json(folder / "system-settings.json", setting)
                result_path = folder / "HalalTag-NativeUITest.xcresult"
                row = {"execution_id": key, "result_bundle": str(result_path), "settings": setting,
                       "host_before": before, "host_after": None, "summary": None, "tree": None,
                       "xcodebuild_status": "NOT_RUN", "collection_errors": []}
                self.report["native_ui_result"] = "EXECUTED_EVIDENCE_PENDING"
                self.report["case_xcresults"][key] = str(result_path)
                self.flush()
                step = self.run(key + "-original-method", ["/usr/bin/xcodebuild", "test-without-building",
                    "-xctestrun", str(retained_run), "-destination", "platform=iOS Simulator,id=" + self.simulator,
                    "-resultBundlePath", str(result_path),
                    "-only-testing:" + TARGET + "/" + case["test_class"] + "/" + case["method"],
                    "-parallel-testing-enabled", "NO", "-maximum-concurrent-test-simulator-destinations", "1",
                    "-maximum-parallel-testing-workers", "1"], self.qa_project,
                    self.coverage["native_case_timeout_seconds"], check=False)
                row["xcodebuild_status"] = step["status"]
                # Collect each original output independently. A failed assertion
                # must not prevent its unfiltered screenshots from being retained.
                if result_path.is_dir() and not result_path.is_symlink():
                    for field, command in (("summary", "summary"), ("tree", "tests")):
                        try:
                            row[field] = self.json_command(key + "-" + command,
                                ["/usr/bin/xcrun", "xcresulttool", "get", "test-results", command,
                                 "--path", str(result_path)], self.output, 60)
                            base.write_json(folder / (field + ".json"), row[field])
                        except Exception as error:
                            row["collection_errors"].append(field + ": " + str(error))
                    try:
                        exported = folder / "attachments"
                        self.run(key + "-export-all-original-attachments", ["/usr/bin/xcrun", "xcresulttool", "export", "attachments",
                            "--path", str(result_path), "--output-path", str(exported)], self.output, 90)
                        base.write_json(folder / "attachment-index-preliminary.json", attachments.exported_manifest(exported))
                        test_id, test_url = actual_case_identity(row["tree"], case)
                        activity = self.json_command(key + "-original-activities", ["/usr/bin/xcrun", "xcresulttool", "get",
                            "test-results", "activities", "--path", str(result_path), "--test-id", test_url], self.output, 60)
                        base.write_json(folder / "activities.json", activity)
                        require(activity.get("testIdentifier") == test_id and
                                activity.get("testIdentifierURL", "").removesuffix("()") == test_url.removesuffix("()")
                                and len(activity.get("testRuns", [])) == 1,
                                "Actual activity result is missing, repeated or bound to another test")
                        kept = attachments.activity_kept_attachments(activity, test_id)
                        base.write_json(folder / "kept-original-attachments.json", kept)
                        maps[key] = attachments.exported_manifest(exported, kept)
                        base.write_json(folder / "attachment-index.json", maps[key])
                    except Exception as error:
                        row["collection_errors"].append("original attachments: " + str(error))
                else:
                    row["collection_errors"].append("No actual xcresult directory; no original native acceptance")
                # Ownership remains mandatory even while collecting a failed test.
                setting["owned_destination_after"] = self.owned_booted(key + "-owned-after-test")
                setting["style"]["readback_after_test"] = self.read_setting(key + "-post-appearance", "appearance")
                setting["content_size"]["readback_after_test"] = self.read_setting(key + "-post-content-size", "content_size")
                base.write_json(folder / "system-settings.json", setting)
                host_source = self.host_root(key + "-actual-host-container")
                row["raw_host_copy"] = self.preserve_raw_hosts(key + "-after-test")
                after = cases.host_snapshot(host_source, allow_missing=True)
                row["host_after"] = after
                for name, details in after.items():
                    original = host_source / name
                    target = retained_hosts / name
                    if target.exists():
                        require(digest(target) == digest(original)
                                and stat.S_IMODE(target.stat().st_mode) == stat.S_IMODE(original.stat().st_mode),
                                "Previously retained original host changed")
                    else:
                        target.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(original, target)
                        require(digest(target) == digest(original), "Host copy differs from actual original")
                try:
                    host_assignments[key] = cases.validate_host_delta(before, after, case, self.qa_run_id)
                except Exception as error:
                    row["collection_errors"].append("host delta: " + str(error))
                previous = after
                self.installed_app(app_snapshot, key + "-verified-installed-app")
                require(digest(retained_run) == xctestrun_sha
                        and binding.bundle_snapshot(products["app"]) == app_snapshot
                        and binding.bundle_snapshot(products["tests"])["sha256"] == tests_sha,
                        "Retained installed app, test bundle or xctestrun changed")
                verify_stage(self.project_copy, self.native_rows, manifest)
                self.validate_manifest("after-" + key)
                observed.append(row)
                base.write_json(folder / "observed-case.json", row)
                base.write_json(self.output / "observed-cases.json", {"status": "ORIGINAL_RESULTS_RETAINED_NOT_YET_ACCEPTED",
                    "run_id": self.qa_run_id, "expected_case_order": [x["execution_id"] for x in self.coverage["ui_cases"]], "cases": observed})
            require(all(not row["collection_errors"] for row in observed), "Original case evidence is incomplete; no native acceptance")
            strict = cases.validate_all_cases(observed, self.qa_run_id, self.simulator)
            base.write_json(self.output / "strict-nineteen-case-proof.json", strict)
            require(manifest["runID"] == self.qa_run_id == strict["run_id"],
                    "Functional installation binding and actual host/settings run differ")
            for case, row in zip(self.coverage["ui_cases"], observed):
                if case["group"] in ("functional", "state"):
                    verified = cases.validate_one_result(row["summary"], row["tree"], case, self.simulator)
                    proof = cases.validate_basic_attachments(self.output / "cases" / case["execution_id"] / "attachments",
                        maps[case["execution_id"]], case, verified, manifest, self.simulator_name)
                    base.write_json(self.output / "cases" / case["execution_id"] / "verified-original-evidence.json", proof)
            # These exact original EN/AR guards are not rewritten by this adapter.
            # All raw per-case exports stay separately preserved.
            for group, guard in (("en", appearance), ("ar", arabic)):
                selected = [case for case in self.coverage["ui_cases"] if case["group"] == group]
                derived = self.output / "derived-evidence-unions" / group; derived.mkdir(parents=True)
                union = current_union.combine_original_attachments({case["case_id"]: self.output / "cases" / case["execution_id"] / "attachments"
                    for case in selected}, derived / "attachments", attachment_limit=guard.ATTACHMENT_LIMIT)
                base.write_json(derived / "attachment-union-binding.json", union)
                hosts = derived / "hosts"; hosts.mkdir()
                settings = []
                for case in selected:
                    row = next(row for row in observed if row["execution_id"] == case["execution_id"])
                    names = sorted(set(row["host_after"]) - set(row["host_before"]))
                    require(len(names) == 1, "Each original appearance method must have exactly one actual host")
                    for name in names:
                        original = retained_hosts / name; target = hosts / name; target.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(original, target); require(digest(original) == digest(target), "Derived host copy changed bytes")
                    value = row["settings"]["content_size"]
                    settings.append({"run_id": self.qa_run_id, "device_id": self.simulator, "case_id": case["case_id"], **value})
                system_size.validate_case_settings(settings, run_id=self.qa_run_id, simulator=self.simulator)
                original_hosts = guard.validate_host(hosts, self.qa_run_id)
                system_size.validate_system_hosts(original_hosts)
                proof = guard.validate_attachments(derived / "attachments", hosts,
                    run_id=self.qa_run_id, simulator=self.simulator, simulator_name=self.simulator_name)
                base.write_json(derived / "original-full-appearance-proof.json", proof)
            self.report["native_ui_result"] = "NINETEEN_ORIGINAL_CASES_AND_ORIGINAL_EVIDENCE_PASSED"
            self.report["verified_test_inventory"] = strict
            self.report["original_host_receipts"] = 20
            self.report["supplementary_unique_launch_uuids"] = 17
            self.report["manual_original_pixel_review"] = "PENDING_NOT_PERFORMED_BY_EXECUTOR"
            self.flush()

    return HostedHalalRunner


def actual_case_identity(tree, case):
    expected = case["test_class"] + "/" + case["method"] + "()"
    leaves = []
    def walk(node):
        require(isinstance(node, dict), "Malformed original test tree")
        if node.get("nodeType") == "Test Case":
            leaves.append(node)
        for child in node.get("children", []):
            walk(child)
    require(isinstance(tree, dict) and isinstance(tree.get("testNodes"), list), "Missing original test tree")
    for node in tree["testNodes"]:
        walk(node)
    require(len(leaves) == 1 and leaves[0].get("nodeIdentifier") == expected,
            "Actual one-leaf identity differs from the selected original method")
    url = leaves[0].get("nodeIdentifierURL")
    require(isinstance(url, str) and url.startswith("test://com.apple.xcode/")
            and url.removesuffix("()").endswith("/" + TARGET + "/" + expected.removesuffix("()")),
            "Actual case URL is not bound to its original target/class/method")
    return expected, url


def production_action(base, runner, source, shipping_rows, native_report_path, native_sha):
    runner.validate_manifest("before-production-archive")
    verify_stage(source, shipping_rows)
    require(digest(native_report_path) == native_sha, "Accepted native report changed before production")
    spec = {"key": "halal", "root": source,
            "project": source / "HalalAnalyzer حلال ام حرام؟.xcodeproj", "scheme": "HalalAnalyzer حلال ام حرام؟"}
    (runner.output / "halal").mkdir()
    runner.validate_project(spec)
    runner.production_archive(spec)
    archive = runner.output / "halal/Production.xcarchive"
    settings = runner.output / "halal/production-settings.json"
    receipt = runner.output / "halal/shipping-integrity-receipt.json"
    runner.run("halal-shipping-integrity-verifier", [sys.executable, str(HERE / "verify_shipping_archive.py"),
        "--shipping-source", str(source), "--archive", str(archive), "--settings", str(settings),
        "--output", str(receipt)], runner.output, 120)
    value = json.loads(receipt.read_bytes())
    require(value.get("status") == "UNSIGNED_ARCHIVE_INTEGRITY_CHECKS_PASSED", "Actual shipping integrity verifier failed")
    runner.report["shipping_integrity_result"] = value["status"]
    runner.report["shipping_integrity_receipt"] = {"path": str(receipt), "sha256": digest(receipt)}
    runner.report["production_archive"] = str(archive)
    runner.report["production_settings"] = str(settings)
    verify_stage(source, shipping_rows)
    require(digest(native_report_path) == native_sha, "Accepted native report changed during production")
    runner.validate_manifest("after-production-archive")
    runner.flush()


def execute_bound(context, hosted):
    config, index, coverage, review, checkout, attempt = context
    diagnostics.bind_context(config)
    require(not os.path.lexists(attempt), "Preserve an existing or ambiguous hosted attempt")
    require(not os.path.lexists(Path("/tmp/dot-ios-build.lock")), "Fresh VM native slot is occupied; no wait or reclamation")
    from release_evidence import verify_reservation, preserve_reservation
    verify_reservation(context, os.environ)
    attempt.mkdir(mode=0o700)
    preserve_reservation(attempt)
    state = {"status": "STARTED_NOT_ACCEPTED", "scope": config["scope"], "source_commit": config["source_commit"],
        "source_tree": config["source_tree"], "workflow_commit": os.environ["GITHUB_SHA"],
        "github_run_id": os.environ["GITHUB_RUN_ID"], "github_run_attempt": 1,
        "started_at": datetime.now(timezone.utc).isoformat(), "native_report": None, "production_report": None,
        "native_invoked": False, "native_acceptance_established": False, "store_release": False,
        "image_os": os.environ["ImageOS"], "image_version": os.environ["ImageVersion"],
        "original_work_deadline_utc": config["deadline_utc"], "errors": []}
    write_json(attempt / "attempt.json", state)
    active, cancelled, handlers = [None], [None], {}
    def stop(number, _frame):
        if cancelled[0] is None:
            cancelled[0] = number
        if active[0] is not None and active[0].cancel_signal is None:
            active[0].cancel_signal = number
    for number in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP):
        handlers[number] = signal.signal(number, stop)
    code = 2
    try:
        verified = hosted.verify_checkout(checkout, index, review, os.environ["GITHUB_SHA"], attempt / "git-before")
        write_json(attempt / "source-verification.json", verified)
        verify_support()
        require(cancelled[0] is None, "Cancelled before native work")
        frozen = attempt / "FrozenOriginalSource"
        copy_source(checkout, index["files"], frozen)
        native_rows = [row for row in index["files"] if row.get("native_input")]
        # No frozen lifecycle is imported before actual root/context/source checks.
        base = load_pure("halal_exact_frozen_lifecycle", HERE / "publishing_runner_frozen.py")
        png = load_pure("appearance_png", HERE / "appearance_png.py")
        artifact = load_pure("halal_original_artifact_binding", HERE / "artifact_binding.py")
        cases = load_pure("halal_installed_runtime_case_evidence", HERE / "case_evidence_installed.py")
        attachments = load_pure("halal_complete_original_attachments", HERE / "original_attachments.py")
        english = load_pure("halal_installed_runtime_english_evidence", HERE / "appearance_evidence_guard_installed.py")
        arabic = load_pure("halal_installed_runtime_arabic_evidence", HERE / "arabic_appearance_evidence_guard_installed.py")
        sizes = load_pure("halal_unchanged_system_size", HERE / "system_size_evidence.py")
        current_union = load_pure("halal_current_scope_original_union", HERE / "current_original_union.py")
        original_controls = [checkout / row["path"] for row in review["control_files"]]
        original_controls += [HERE / "candidate.json", HERE / "root-review.json"]
        manifest = source_manifest(base, frozen, index["files"], original_controls, attempt / "native-source-manifest.json")
        runner_type = runner_class(base, artifact, english, arabic, sizes, cases, attachments, png, current_union)
        native = runner_type(phase_args(frozen, attempt / "Native", manifest,
            "github-halal-r12-" + os.environ["GITHUB_RUN_ID"] + "-1-native", production=False), frozen, native_rows, coverage)
        active[0] = native
        if cancelled[0] is not None:
            native.cancel_signal = cancelled[0]
        state["native_report"] = str(native.output / "report.json")
        state["native_invocation_attempted"] = True
        write_json(attempt / "attempt.json", state)
        code = finish_phase(base, native, native.execute)
        active[0] = None
        state["native_invoked"] = any(type(step.get("pid")) is int and
            (step.get("name") in ("compile-original-model-checks", "initial-build-for-testing", "configured-build-for-testing")
             or str(step.get("name", "")).endswith("-original-method")) for step in native.report["steps"])
        native_report_path = native.output / "report.json"
        state["native_report_sha256"] = digest(native_report_path)
        write_json(attempt / "attempt.json", state)
        require(code == 0 and cancelled[0] is None, "Original native phase did not complete successfully")
        state["native_gate"] = require_native_gate(hosted.read_json(native_report_path), coverage)
        require(not os.path.lexists(base.LOCK_PATH), "Native ownership was not released before production")
        verify_stage(frozen, index["files"])
        hosted.verify_checkout(checkout, index, review, os.environ["GITHUB_SHA"], attempt / "git-between-phases")
        state["status"] = "ORIGINAL_MODEL_UI_AND_CLEANUP_PASSED_ARCHIVE_PENDING"
        write_json(attempt / "attempt.json", state)
        contract = hosted.read_json(HERE / "shipping-contract.json")
        shipping_names = {row["path"] for row in contract["source_files"]}
        shipping_rows = [row for row in index["files"] if row["path"] in shipping_names]
        require(len(shipping_rows) == 14, "Exact original shipping source is incomplete")
        shipping = attempt / "FrozenShippingSource"
        copy_source(checkout, shipping_rows, shipping)
        native_sha = state["native_report_sha256"]
        production_manifest = source_manifest(base, shipping, shipping_rows,
            original_controls + [native_report_path], attempt / "production-source-manifest.json")
        require(cancelled[0] is None, "Cancelled before production")
        production = base.Runner(phase_args(shipping, attempt / "Production", production_manifest,
            "github-halal-r12-" + os.environ["GITHUB_RUN_ID"] + "-1-production", production=True))
        active[0] = production
        if cancelled[0] is not None:
            production.cancel_signal = cancelled[0]
        production.report.update(scope="DISTINCT_HOSTED_R12_UNSIGNED_PRODUCTION_ARCHIVE",
            source_commit=config["source_commit"], accepted_native_report_sha256=native_sha,
            source_assertions_changed=False, native_phase_completed_before_archive=True,
            distribution_signing=False, store_release=False)
        production.flush()
        state["production_report"] = str(production.output / "report.json")
        write_json(attempt / "attempt.json", state)
        code = finish_phase(base, production,
            lambda: production_action(base, production, shipping, shipping_rows, native_report_path, native_sha))
        active[0] = None
        production_report_path = production.output / "report.json"
        state["production_report_sha256"] = digest(production_report_path)
        write_json(attempt / "attempt.json", state)
        require(code == 0 and cancelled[0] is None, "Original production phase did not complete successfully")
        production_report = hosted.read_json(production_report_path)
        state["archive_gate"] = require_production_gate(production_report,
            hosted.read_json(Path(production_report["shipping_integrity_receipt"]["path"])), native_sha)
        require(not os.path.lexists(base.LOCK_PATH), "Production ownership was not released")
        require(digest(native_report_path) == native_sha, "Accepted native report changed after production")
        verify_stage(frozen, index["files"]); verify_stage(shipping, shipping_rows)
        hosted.verify_checkout(checkout, index, review, os.environ["GITHUB_SHA"], attempt / "git-after")
        state["status"] = "MODEL_UI_AND_UNSIGNED_ARCHIVE_PASSED_ARTIFACT_AND_REVIEW_PENDING"
        state["native_acceptance_established"] = True
        code = 0
    except Exception as error:
        diagnostics.observe_exception("attempt-error", error)
        state["status"] = "FAILED_OR_INCOMPLETE_OR_INTERRUPTED"
        state["errors"].append(type(error).__name__ + ": " + str(error))
        code = code or 2
    finally:
        # Unexpected errors outside a normal phase still preserve exact ownership.
        if active[0] is not None:
            unresolved = active[0]
            if not unresolved.report.get("finished_at"):
                try:
                    safe = unresolved.cleanup()
                    unresolved.report.update(cleanup_safe=safe, exit_code=code or 2,
                        all_owned_processes_closed=all(child["closed"] for child in unresolved.owned),
                        finished_at=datetime.now(timezone.utc).isoformat())
                    unresolved.flush()
                except Exception as error:
                    diagnostics.observe_exception("attempt-unexpected-cleanup-error", error)
                    state["errors"].append("Unexpected cleanup failed; ownership retained: " + str(error))
        if cancelled[0] is not None:
            code = 128 + cancelled[0]
            state["status"] = "FAILED_OR_INCOMPLETE_OR_INTERRUPTED"
            state["native_acceptance_established"] = False
        state.update(exit_code=code, cancellation_signal=cancelled[0], finished_at=datetime.now(timezone.utc).isoformat(),
                     artifact_delivery="PENDING_SEPARATE_COLLECTION_AND_UPLOAD", manual_original_pixel_review="PENDING")
        write_json(attempt / "attempt.json", state)
        diagnostics.attempt_terminal(attempt, "native-terminal")
        for number, previous in handlers.items():
            signal.signal(number, previous)
    print(json.dumps({"attempt": str(attempt), "status": state["status"], "exit_code": code, "store_release": False}))
    return code


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", nargs="?", choices=("inspect", "native"), default="inspect")
    args = parser.parse_args(argv)
    hosted = load_pure("halal_hosted_binding", HERE / "hosted_binding.py")
    if args.mode == "inspect":
        config, index, coverage = hosted.inspect_contract(HERE)
        verify_support()
        print(json.dumps({"status": "FILES_ONLY_VALIDATED_NOT_NATIVE_AUTHORIZATION", "scope": config["scope"],
            "source_files": len(index["files"]), "model_checks": len(coverage["expected_model_check_labels"]),
            "ui_cases": len(coverage["ui_cases"]), "native_invoked": False, "store_release": False}))
        return 0
    context = hosted.load_bound(HERE, os.environ, datetime.now(timezone.utc), sys.platform,
                                platform.machine(), platform.mac_ver()[0])
    return execute_bound(context, hosted)


if __name__ == "__main__":
    raise SystemExit(main())
