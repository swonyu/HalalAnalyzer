"""Pure artifact identity helpers retained from historical appearance adapter R2.

Only fixed identities change to the independently verified current R11 values.
This does not recover or claim equivalence to the missing current native adapter.
"""
from pathlib import Path
import hashlib
import json
import plistlib
from typing import Any

APP_ID = "com.saleh.halaltag.productioncomposition.qa.r20261117r11"
TEST_ID = APP_ID + ".uitests"
PRODUCTION_ID = "HalalTag.v1.1"
STORE_APP_ID = "HalalTag.v1.1"
TARGET = "HalalTagQAUItests"
ENV_MODE = "ISOLATED_SYNTHETIC_QA"

def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(ok: bool, detail: str) -> None:
    if not ok:
        raise RuntimeError(detail)


def read_json(path: Path) -> Any:
    require(path.is_file() and not path.is_symlink() and path.stat().st_size <= 2_000_000,
            "Missing, linked or oversized JSON input: " + str(path))
    return json.loads(path.read_text())


def bundle_snapshot(root: Path) -> dict[str, Any]:
    """Bound the actual app bytes, excluding no file, before and after installation."""
    require(root.is_dir() and not root.is_symlink(), "App artifact is not a regular directory")
    rows = []
    total = 0
    for path in sorted(root.rglob("*")):
        require(not path.is_symlink(), "App bundle symlink requires manual review")
        if path.is_dir():
            continue
        require(path.is_file(), "Nonregular app bundle entry")
        total += path.stat().st_size
        require(len(rows) < 2000 and total <= 200_000_000, "QA app artifact exceeds inspection bounds")
        rows.append({"path": path.relative_to(root).as_posix(), "sha256": sha(path),
                     "bytes": path.stat().st_size})
    encoded = json.dumps(rows, sort_keys=True, separators=(",", ":")).encode()
    return {"sha256": hashlib.sha256(encoded).hexdigest(), "files": rows,
            "file_count": len(rows), "bytes": total,
            "method": "sha256(canonical JSON of sorted relative paths, per-file SHA256 and size)"}


def plist(path: Path) -> dict[str, Any]:
    require(path.is_file() and not path.is_symlink() and path.stat().st_size < 5_000_000,
            "Missing, linked or oversized plist: " + str(path))
    value = plistlib.loads(path.read_bytes())
    require(isinstance(value, dict), "Property-list root is not a dictionary")
    return value


def test_target(value: dict[str, Any]) -> dict[str, Any]:
    if "TestConfigurations" in value:
        configurations = value["TestConfigurations"]
        require(isinstance(configurations, list) and len(configurations) == 1,
                "Expected one xctestrun configuration")
        require(configurations[0].get("IsEnabled", True) is True, "Test configuration is disabled")
        targets = configurations[0].get("TestTargets")
    else:
        targets = [entry for key, entry in value.items() if key != "__xctestrun_metadata__"]
    require(isinstance(targets, list) and len(targets) == 1 and isinstance(targets[0], dict),
            "Expected exactly one UI test target")
    target = targets[0]
    require(target.get("BlueprintName") == TARGET and target.get("IsUITestBundle") is True,
            "Wrong or unrecognized xctestrun test target")
    require(not target.get("SkipTestIdentifiers"), "The generated xctestrun skips tests")
    require(not target.get("OnlyTestIdentifiers"), "Unexpected xctestrun test restriction")
    return target


def resolve_product(raw: Any, xctestrun: Path, derived_data: Path, testhost: Path | None = None) -> Path:
    require(isinstance(raw, str) and raw, "Missing xctestrun product path")
    raw = raw.replace("__TESTROOT__", str(xctestrun.parent))
    if testhost is not None:
        raw = raw.replace("__TESTHOST__", str(testhost))
    require("__" not in raw and "$(" not in raw, "Unresolved xctestrun product path")
    path = Path(raw)
    if not path.is_absolute():
        path = xctestrun.parent / path
    resolved = path.resolve(strict=True)
    require(resolved.is_relative_to(derived_data.resolve()),
            "Generated product escapes the owned DerivedData")
    require(not path.is_symlink() and resolved.is_dir(), "Generated product is linked or missing")
    return resolved


def read_products(path: Path, derived_data: Path, run_id: str) -> dict[str, Path]:
    target = test_target(plist(path))
    environment = target.get("EnvironmentVariables")
    require(isinstance(environment, dict)
            and environment.get("HALALTAG_UI_QA_RUN_MODE") == ENV_MODE
            and environment.get("HALALTAG_UI_QA_RUN_ID") == run_id,
            "Actual xctestrun runner environment did not resolve the QA configuration")
    app_environment = target.get("UITargetAppEnvironmentVariables", {})
    require(isinstance(app_environment, dict) and not any(
        key.startswith("HALALTAG_UI_QA_") for key in app_environment),
        "QA configuration must not be forwarded as app-side flags")
    host = resolve_product(target.get("TestHostPath"), path, derived_data)
    app = resolve_product(target.get("UITargetAppPath"), path, derived_data)
    tests = resolve_product(target.get("TestBundlePath"), path, derived_data, host)
    require(app.suffix == ".app" and tests.suffix == ".xctest" and host.suffix == ".app",
            "Unrecognized app/test/runner product layout")
    require(plist(app / "Info.plist").get("CFBundleIdentifier") == APP_ID,
            "Actual built app identity differs from the dedicated QA identity")
    require(plist(tests / "Info.plist").get("CFBundleIdentifier") == TEST_ID,
            "Actual UI-test bundle identity differs from the reviewed test identity")
    require(plist(host / "Info.plist").get("CFBundleIdentifier") not in (APP_ID, TEST_ID, PRODUCTION_ID, STORE_APP_ID),
            "Runner wrapper identity is not distinct")
    return {"app": app, "tests": tests, "host": host}


def validate_build_settings(app_settings: Any, test_settings: Any) -> list[dict[str, Any]]:
    """Bind each explicit query to exactly its expected target and QA identity."""
    combined = []
    for rows, target, identity in ((app_settings, "HalalTagQA", APP_ID),
                                   (test_settings, TARGET, TEST_ID)):
        require(isinstance(rows, list) and len(rows) == 1,
                "Unexpected effective build target inventory for " + target)
        entry = rows[0]
        require(isinstance(entry, dict) and entry.get("target") == target,
                "Unexpected effective build target for " + target)
        setting = entry.get("buildSettings")
        require(isinstance(setting, dict)
                and setting.get("PRODUCT_BUNDLE_IDENTIFIER") == identity
                and setting.get("PLATFORM_NAME") == "iphonesimulator"
                and setting.get("CODE_SIGNING_ALLOWED") == "NO",
                "Actual QA target identity/platform/signing settings differ")
        combined.append(entry)
    return combined
