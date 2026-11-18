#!/usr/bin/env python3
"""Read-only checks for a distinct HalalTag R11 unsigned archive proposal.

This module never builds, signs, runs an app, invokes an Apple tool or acquires a
lock. A passing result establishes only the checked existing archive's integrity.
The future coordinator must separately require the exact native acceptance and
completed process/simulator/lock cleanup before authorizing its archive phase.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import plistlib
import re
import stat
import struct
import sys


CONTRACT_SHA256 = "5ef3cc1d338d09734afceb1515963bc793ba4924bce441f831053f716d430c22"
QA_MARKERS = (
    b"com.saleh.halaltag.productioncomposition.qa.r20261117r11",
    b"HalalTagSyntheticQAInstallation", b"HalalTagAppearanceQA",
)


class ArchiveFailure(ValueError):
    pass


def require(value, message):
    if not value:
        raise ArchiveFailure(message)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def unique_pairs(values):
    result = {}
    for key, value in values:
        require(key not in result, "Duplicate JSON key")
        result[key] = value
    return result


def read_json(path):
    require(path.is_file() and not path.is_symlink(), "Missing or linked JSON input")
    return json.loads(path.read_bytes(), object_pairs_hook=unique_pairs,
                      parse_constant=lambda _: (_ for _ in ()).throw(ArchiveFailure("Nonfinite JSON value")))


def same_value(left, right):
    if type(left) is not type(right):
        return False
    if isinstance(left, dict):
        return left.keys() == right.keys() and all(same_value(left[k], right[k]) for k in left)
    if isinstance(left, list):
        return len(left) == len(right) and all(same_value(a, b) for a, b in zip(left, right))
    return left == right


def regular_file(path):
    require(path.is_file() and not path.is_symlink() and stat.S_ISREG(path.stat().st_mode),
            "Missing or nonregular file: " + str(path))
    return path


def file_inventory(directory):
    require(directory.is_dir() and not directory.is_symlink(), "Missing or linked input directory")
    values = {}
    for path in sorted(directory.rglob("*")):
        require(not path.is_symlink(), "Archive/source contains a symbolic link: " + str(path))
        if path.is_dir():
            continue
        data = regular_file(path).read_bytes()
        values[path.relative_to(directory).as_posix()] = {
            "bytes": len(data), "sha256": sha(data), "mode": f"{stat.S_IMODE(path.stat().st_mode):04o}"}
    return values


def version(value):
    require(isinstance(value, str) and re.fullmatch(r"\d+(?:\.\d+){0,2}", value), "Malformed version")
    numbers = tuple(int(x) for x in value.split("."))
    return numbers + (0,) * (3 - len(numbers))


def packed_version(value):
    return (value >> 16, (value >> 8) & 255, value & 255)


def macho_device_version(data, minimum, sdk):
    """Check the actual thin ARM64 executable's LC_BUILD_VERSION, without tools.

    An unexpected universal/legacy layout requires a separately reviewed parser;
    it is never silently treated as the original device architecture.
    """
    require(len(data) >= 32, "Truncated Mach-O header")
    magic, cpu, subtype, kind, commands, size, flags, reserved = struct.unpack_from("<8I", data)
    require(magic == 0xFEEDFACF and cpu == 0x0100000C and kind == 2,
            "Archive executable is not the reviewed thin ARM64 device layout")
    require(commands > 0 and 32 + size <= len(data), "Malformed Mach-O load-command bounds")
    cursor, observed = 32, []
    for _ in range(commands):
        require(cursor + 8 <= 32 + size, "Truncated Mach-O load command")
        command, length = struct.unpack_from("<2I", data, cursor)
        require(length >= 8 and length % 8 == 0 and cursor + length <= 32 + size,
                "Invalid Mach-O load-command size")
        require(command != 0x1D, "Code-signature load command present in claimed unsigned executable")
        if command == 0x32:  # Apple LC_BUILD_VERSION; PLATFORM_IOS is 2.
            require(length >= 24, "Truncated Mach-O build-version command")
            _, _, platform, minos, sdk_value, tools = struct.unpack_from("<6I", data, cursor)
            require(length == 24 + tools * 8 and platform == 2,
                    "Executable is not an iOS device build")
            observed.append({"platform": platform, "minimum": packed_version(minos), "sdk": packed_version(sdk_value)})
        cursor += length
    require(cursor == 32 + size and len(observed) == 1, "Ambiguous or missing Mach-O device build version")
    require(observed[0]["minimum"] == version(minimum) and observed[0]["sdk"] == version(sdk),
            "Executable minimum OS or SDK differs from the source-bound shipping contract")
    return {"architecture": "arm64", "format": "thin Mach-O 64", **observed[0]}


def load_contract(path):
    data = regular_file(path).read_bytes()
    require(sha(data) == CONTRACT_SHA256, "Shipping contract differs from this reviewed verifier")
    contract = read_json(path)
    require(contract["shipping_file_count"] == len(contract["source_files"]) == 14,
            "Complete fourteen-file shipping contract missing")
    return contract


def icon_parts(name):
    require(isinstance(name, str) and name and Path(name).name == name and "\\" not in name,
            "Unsafe compiled icon declaration or filename")
    stem = name[:-4] if name.endswith(".png") else name
    match = re.fullmatch(r"([^/@~]+)(?:@([123])x)?(?:~(iphone|ipad))?", stem)
    require(match is not None, "Unreviewed icon filename suffix")
    return match.groups()


def declared_icon_matches(declared, filename, family):
    base, scale, device = icon_parts(declared)
    actual_base, actual_scale, actual_device = icon_parts(filename)
    return (actual_base == base and (scale is None or scale == actual_scale)
            and (device is None or device == actual_device)
            and actual_device in (None, family))


def check_source(source, contract):
    observed = file_inventory(source)
    expected = {row["path"]: {key: row[key] for key in ("bytes", "sha256", "mode")}
                for row in contract["source_files"]}
    require(len(expected) == 14 and observed == expected, "Shipping source bytes, membership or Git modes changed")
    return observed


def check_settings(settings_path, source, contract):
    raw = read_json(settings_path)
    require(isinstance(raw, list) and raw, "Missing effective Release build settings")
    apps = []
    for target in raw:
        require(isinstance(target, dict) and isinstance(target.get("buildSettings"), dict), "Malformed target settings")
        settings = target["buildSettings"]
        for key in ("SWIFT_ACTIVE_COMPILATION_CONDITIONS", "OTHER_SWIFT_FLAGS", "GCC_PREPROCESSOR_DEFINITIONS"):
            text = str(settings.get(key, ""))
            require(not re.search(r"(?:^|[^A-Za-z0-9_])(?:-D\s*)?(?:DEBUG|UI_TESTING|HALALTAG_QA)(?:$|[^A-Za-z0-9_])", text),
                    "QA or Debug compilation flag in Release settings")
        if settings.get("WRAPPER_EXTENSION") == "app" and settings.get("PRODUCT_TYPE") == "com.apple.product-type.application":
            apps.append(settings)
    require(len(apps) == 1, "Exactly one shipping app target is required")
    settings = apps[0]
    required = {
        "CONFIGURATION": "Release", "PLATFORM_NAME": "iphoneos",
        "PRODUCT_BUNDLE_IDENTIFIER": contract["bundle_identifier"], "DEVELOPMENT_TEAM": contract["development_team"],
        "MARKETING_VERSION": contract["marketing_version"], "CURRENT_PROJECT_VERSION": contract["build_version"],
        "INFOPLIST_KEY_CFBundleDisplayName": contract["display_name"], "TARGETED_DEVICE_FAMILY": "1,2",
        "ASSETCATALOG_COMPILER_APPICON_NAME": contract["app_icon_name"],
        "CODE_SIGNING_ALLOWED": "NO", "CODE_SIGNING_REQUIRED": "NO", "CODE_SIGN_IDENTITY": "",
        "ENABLE_TESTABILITY": "NO",
    }
    for key, expected in required.items():
        require(settings.get(key) == expected, "Changed effective shipping setting: " + key)
    require(version(settings.get("IPHONEOS_DEPLOYMENT_TARGET")) == version(contract["minimum_ios_version"])
            and version(settings.get("SDK_VERSION")) == version(contract["sdk_version"]), "Effective target/SDK changed")
    require(Path(settings.get("SRCROOT", "")).resolve() == source.resolve(), "Build settings refer to another source root")
    require(not settings.get("CODE_SIGN_ENTITLEMENTS") and not settings.get("PROVISIONING_PROFILE_SPECIFIER"),
            "Unexpected signing capability/profile in offline unsigned source")
    return settings


def check_archive(archive, settings, source, contract):
    require(archive.is_dir() and not archive.is_symlink() and archive.suffix == ".xcarchive", "Invalid archive directory")
    applications = archive / "Products/Applications"
    require(applications.is_dir() and not applications.is_symlink(), "Archive lacks Applications directory")
    apps = list(applications.iterdir())
    require(len(apps) == 1 and apps[0].suffix == ".app" and apps[0].is_dir() and not apps[0].is_symlink(),
            "Exactly one regular archived app is required")
    app = apps[0]
    inventory = file_inventory(app)
    require(app.name == settings.get("WRAPPER_NAME"), "Archive app name differs from actual build settings")
    info = plistlib.loads(regular_file(app / "Info.plist").read_bytes())
    required = {"CFBundleIdentifier": contract["bundle_identifier"], "CFBundleDisplayName": contract["display_name"],
                "CFBundleShortVersionString": contract["marketing_version"], "CFBundleVersion": contract["build_version"],
                "CFBundlePackageType": "APPL", "UIDeviceFamily": contract["device_families"],
                "CFBundleSupportedPlatforms": ["iPhoneOS"], "DTPlatformName": "iphoneos",
                "ITSAppUsesNonExemptEncryption": False}
    for key, expected in required.items():
        require(same_value(info.get(key), expected), "Changed compiled shipping metadata: " + key)
    require(version(info.get("MinimumOSVersion")) == version(contract["minimum_ios_version"]), "Compiled minimum OS changed")
    require(info.get("DTXcodeBuild") == contract["xcode_build"], "Archive originated from an unreviewed Xcode build")
    declarations = {}
    for key in ("CFBundleIcons", "CFBundleIcons~ipad"):
        primary = info.get(key, {}).get("CFBundlePrimaryIcon", {})
        require(primary.get("CFBundleIconName") == contract["app_icon_name"] and primary.get("CFBundleIconFiles"),
                "Missing actual iPhone/iPad AppIcon metadata")
        names = primary["CFBundleIconFiles"]
        require(isinstance(names, list) and all(isinstance(name, str) for name in names)
                and len(names) == len(set(names)), "Malformed or duplicate declared icon resources")
        declarations[key] = names
    require(regular_file(app / "Assets.car").stat().st_size > 0, "Missing compiled assets")
    dimensions, pngs = set(), {}
    for path in app.glob("*.png"):
        header = regular_file(path).read_bytes()[:24]
        require(len(header) == 24 and header[:8] == b"\x89PNG\r\n\x1a\n" and header[12:16] == b"IHDR", "Invalid compiled icon PNG header")
        size = struct.unpack(">II", header[16:24])
        dimensions.add(size); pngs[path.name] = size
    icon_bindings = {}
    for key, family, required_size in (("CFBundleIcons", "iphone", (120, 120)),
                                       ("CFBundleIcons~ipad", "ipad", (152, 152))):
        linked = {}
        for name in declarations[key]:
            matches = {filename: size for filename, size in pngs.items() if declared_icon_matches(name, filename, family)}
            require(matches, "Declared icon resource absent from its actual family: " + name)
            linked[name] = matches
        require(required_size in {size for matches in linked.values() for size in matches.values()},
                "Expected family icon size is not bound to declared resources")
        icon_bindings[family] = linked
    privacy = plistlib.loads(regular_file(app / "PrivacyInfo.xcprivacy").read_bytes())
    original_privacy = plistlib.loads(regular_file(source / "HalalAnalyzer حلال ام حرام؟/PrivacyInfo.xcprivacy").read_bytes())
    require(same_value(privacy, original_privacy), "Compiled privacy disclosure differs from exact shipping source")
    localizations = []
    for language in contract["localizations"]:
        path = regular_file(app / (language + ".lproj") / "InfoPlist.strings")
        raw = path.read_bytes()
        try:
            values = plistlib.loads(raw)
        except plistlib.InvalidFileException:
            original = regular_file(source / "HalalAnalyzer حلال ام حرام؟" / (language + ".lproj") / "InfoPlist.strings").read_bytes()
            require(raw == original, "Unexpected localization encoding or changed strings")
            values = {"CFBundleDisplayName": contract["display_name"]}
        require(same_value(values, {"CFBundleDisplayName": contract["display_name"]}), "Localized brand is missing or changed")
        localizations.append(language)
    forbidden_names = {"_CodeSignature", "embedded.mobileprovision", "HalalTagSyntheticQAInstallation.json", "QARun.json"}
    for path in app.rglob("*"):
        require(path.name not in forbidden_names and path.suffix not in {".xctest", ".xcresult", ".swift"},
                "Signing material, QA resource or test source present in unsigned shipping app")
    executable_name = info.get("CFBundleExecutable")
    require(isinstance(executable_name, str) and executable_name and Path(executable_name).name == executable_name
            and executable_name == settings.get("EXECUTABLE_NAME"), "Archive executable binding differs")
    executable_path = regular_file(app / executable_name)
    require(stat.S_IMODE(executable_path.stat().st_mode) == 0o755, "Shipping executable must retain reviewed 0755 mode")
    executable = executable_path.read_bytes()
    require(not any(marker in executable for marker in QA_MARKERS), "Synthetic QA code marker in shipping executable")
    binary = macho_device_version(executable, contract["minimum_ios_version"], contract["sdk_version"])
    metadata = plistlib.loads(regular_file(archive / "Info.plist").read_bytes())
    properties = metadata.get("ApplicationProperties", {})
    require(properties.get("ApplicationPath") == "Applications/" + app.name
            and properties.get("CFBundleIdentifier") == contract["bundle_identifier"], "Archive metadata identifies another app")
    require(file_inventory(app) == inventory, "Archived application changed during verification")
    return {"app_name": app.name, "app_files": inventory, "actual_macho": binary,
            "privacy_matches_source": True, "localizations": localizations,
            "compiled_png_dimensions": sorted(dimensions), "compiled_icon_bindings": icon_bindings,
            "executable_mode": "0755", "code_signature_load_command_present": False, "unsigned": True}


def verify(source, archive, settings_path, contract_path):
    contract = load_contract(contract_path)
    before = check_source(source, contract)
    settings_before = regular_file(settings_path).read_bytes()
    settings = check_settings(settings_path, source, contract)
    checks = check_archive(archive, settings, source, contract)
    require(check_source(source, contract) == before and settings_path.read_bytes() == settings_before,
            "Source or effective build settings changed during verification")
    return {"schema_version": 1, "status": "UNSIGNED_ARCHIVE_INTEGRITY_CHECKS_PASSED",
            "source_commit": contract["source_commit"], "source_tree": contract["source_tree"],
            "shipping_contract_sha256": CONTRACT_SHA256, "effective_settings_sha256": sha(settings_before),
            "source_files": before, "archive_checks": checks,
            "native_acceptance_established": False, "distribution_signing_established": False, "store_release": False,
            "scope": "File inspection only; a coordinator must independently bind actual 211 model and 19 UI acceptance, completed cleanup, and this archive's production command evidence."}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("shipping-source", "archive", "settings", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    try:
        result = verify(args.shipping_source, args.archive, args.settings, Path(__file__).with_name("shipping-contract.json"))
        code = 0
    except Exception as failure:
        result = {"status": "UNSIGNED_ARCHIVE_INTEGRITY_CHECKS_FAILED", "error": type(failure).__name__ + ": " + str(failure),
                  "native_acceptance_established": False, "distribution_signing_established": False, "store_release": False}
        code = 1
    target = args.output.absolute()
    for original in (args.shipping_source, args.archive):
        require(not target.resolve().is_relative_to(original.resolve()), "Receipt may not alter an input directory")
    require(target.resolve() != args.settings.resolve() and not target.exists() and not target.is_symlink(),
            "Existing input/receipt must be preserved")
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2); stream.write("\n")
    print(json.dumps({"status": result["status"], "native_invoked": False, "store_release": False}))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
