"""Pure original-attachment parsing, copied verbatim from accepted Lumina export v2.

No main, network, command, native tool or source-test execution is included.
The new Halal successor uses this shared parser only on its actual exports.
"""
import hashlib
import json
from pathlib import Path, PurePosixPath
import stat
import struct
import uuid

MAX_JSON_BYTES = 64 * 1024 * 1024

class InspectionFailure(Exception):
    pass


def require(value, message):
    if not value:
        raise InspectionFailure(message)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def file_hash(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def unique_object(items):
    result = {}
    for key, value in items:
        require(key not in result, "Duplicate JSON key")
        result[key] = value
    return result


def json_bytes(data):
    require(len(data) <= MAX_JSON_BYTES, "JSON exceeds inspection limit; raw bytes retained")
    return json.loads(data, object_pairs_hook=unique_object,
                      parse_constant=lambda _: (_ for _ in ()).throw(InspectionFailure("Nonfinite JSON value")))


def read_json(path):
    return json_bytes(path.read_bytes())


def canonical_name(name):
    require(isinstance(name, str) and bool(name) and "\\" not in name
            and not any(ord(c) < 32 for c in name), "Invalid evidence member name")
    p = PurePosixPath(name)
    require(not p.is_absolute() and all(x not in {"", ".", ".."} for x in name.split("/"))
            and str(p) == name, "Noncanonical or traversing evidence path")
    return p


def snapshot(directory):
    values = {}
    for path in sorted(directory.rglob("*")):
        require(not path.is_symlink(), "Inspection payload unexpectedly contains a symlink")
        if path.is_file():
            values[str(path.relative_to(directory))] = {
                "bytes": path.stat().st_size, "sha256": file_hash(path), "mode": stat.S_IMODE(path.stat().st_mode)}
        else:
            require(path.is_dir(), "Unexpected inspection payload type")
    return values


def activity_kept_attachments(value, test_id):
    require(isinstance(value, dict) and value.get("testIdentifier") == test_id
            and isinstance(value.get("testIdentifierURL"), str) and value["testIdentifierURL"]
            and isinstance(value.get("testName"), str) and value["testName"]
            and isinstance(value.get("testRuns"), list) and value["testRuns"],
            "Original activities do not have the observed test/testRuns schema")
    found = {}
    def walk(items, device_id, configuration):
        require(isinstance(items, list), "Original activities/children are not an array")
        for item in items:
            require(isinstance(item, dict) and isinstance(item.get("title"), str) and item["title"],
                    "Original activity lacks its observed title")
            attachments = item.get("attachments", [])
            require(isinstance(attachments, list), "Original attachment collection is not an array")
            for attachment in attachments:
                require(isinstance(attachment, dict) and isinstance(attachment.get("lifetime"), str)
                        and attachment["lifetime"] in {"", "keepAlways", "deleteOnSuccess"},
                        "Original attachment lacks its observed lifetime")
                identifier = attachment.get("uuid")
                require(isinstance(identifier, str) and isinstance(attachment.get("name"), str) and attachment["name"],
                        "Original attachment lacks name/UUID metadata")
                try:
                    identifier = str(uuid.UUID(identifier)).upper()
                except ValueError:
                    raise InspectionFailure("Original attachment UUID is malformed") from None
                if attachment["lifetime"] == "":
                    # R17 contains an issue-description reference with name/UUID
                    # but no retained payload, timestamp or lifetime. Preserve
                    # that raw reference without inventing an available file.
                    require(not attachment.get("payloadId"), "Unknown-lifetime retained payload requires review")
                    continue
                if attachment["lifetime"] != "keepAlways":
                    continue
                name, stamp, payload = attachment.get("name"), attachment.get("timestamp"), attachment.get("payloadId")
                require(isinstance(name, str) and name and type(stamp) in {int, float}
                        and float("-inf") < stamp < float("inf") and isinstance(payload, str) and payload,
                        "Kept original attachment metadata/payload is missing or malformed")
                record = {"testIdentifier": test_id, "testIdentifierURL": value["testIdentifierURL"],
                          "deviceId": device_id, "configurationName": configuration,
                          "uuid": identifier, "name": name, "timestamp": stamp, "payloadId": payload}
                require(identifier not in found or found[identifier] == record, "Original attachment identity conflict")
                found[identifier] = record
            if "childActivities" in item:
                walk(item["childActivities"], device_id, configuration)
    for run in value["testRuns"]:
        require(isinstance(run, dict) and isinstance(run.get("activities"), list)
                and isinstance(run.get("device"), dict) and isinstance(run.get("testPlanConfiguration"), dict),
                "Original activity run lacks activities/device/configuration schema")
        device_id = run["device"].get("deviceId")
        configuration = run["testPlanConfiguration"].get("configurationName")
        require(isinstance(device_id, str) and device_id and isinstance(configuration, str) and configuration,
                "Original activity run lacks device/configuration identity")
        walk(run["activities"], device_id, configuration)
    return list(found.values())


def exported_manifest(directory, activities=None):
    manifest_path = directory / "manifest.json"
    manifest = read_json(manifest_path)
    require(isinstance(manifest, list), "Apple attachment manifest is not the observed array schema")
    records, files = [], set()
    for group in manifest:
        require(isinstance(group, dict) and isinstance(group.get("attachments"), list)
                and isinstance(group.get("testIdentifier"), str) and isinstance(group.get("testIdentifierURL"), str),
                "Apple manifest group is malformed")
        for entry in group["attachments"]:
            require(isinstance(entry, dict), "Apple attachment record is malformed")
            name = entry.get("exportedFileName")
            member = canonical_name(name)
            require(len(member.parts) == 1 and name != "manifest.json", "Unexpected Apple attachment filename")
            path = directory / name
            require(path.is_file() and not path.is_symlink(), "Listed original attachment is missing")
            record = {**entry, "testIdentifier": group["testIdentifier"], "testIdentifierURL": group["testIdentifierURL"],
                      "bytes": path.stat().st_size, "sha256": file_hash(path), "mode": stat.S_IMODE(path.stat().st_mode)}
            try:
                record["attachment_uuid_from_exported_filename"] = str(uuid.UUID(path.stem)).upper()
            except ValueError:
                record["attachment_uuid_from_exported_filename"] = None
            if path.suffix.lower() == ".png":
                with path.open("rb") as stream:
                    header = stream.read(24)
                require(len(header) == 24 and header[:8] == b"\x89PNG\r\n\x1a\n" and header[12:16] == b"IHDR",
                        "PNG attachment header invalid")
                width, height = struct.unpack(">II", header[16:24])
                require(width > 0 and height > 0, "PNG attachment dimensions invalid")
                record["pixel_dimensions"] = {"width": width, "height": height}
                record["category"] = "original_png"
            elif path.suffix.lower() in {".txt", ".json", ".xml"}:
                record["category"] = "original_text_attachment_AX_content_not_assumed"
            else:
                record["category"] = "other_original_attachment_retained"
            records.append(record)
            files.add(name)
    actual = snapshot(directory)
    require(set(actual) == files | {"manifest.json"}, "Exporter produced missing or unmanifested files; all originals retained")
    matched_files, matches, missing = set(), [], []
    for attachment in activities or []:
        available = {x["exportedFileName"] for x in records
                     if x["attachment_uuid_from_exported_filename"] == attachment["uuid"]
                     and x["testIdentifier"] == attachment["testIdentifier"]
                     and x["testIdentifierURL"].removesuffix("()") == attachment["testIdentifierURL"].removesuffix("()")
                     and x.get("deviceId") == attachment["deviceId"]
                     and x.get("configurationName") == attachment["configurationName"]
                     and x.get("suggestedHumanReadableName") == attachment["name"]
                     and x.get("timestamp") == attachment["timestamp"]}
        if len(available) != 1 or not matched_files.isdisjoint(available):
            missing.append(attachment)
        else:
            filename = available.pop()
            matched_files.add(filename)
            matches.append({**attachment, "exportedFileName": filename})
    require(not missing, "One or more original keepAlways attachments are missing from the unfiltered export")
    return {"apple_manifest_sha256": file_hash(manifest_path), "original_file_count": len(files),
            "manifest_entry_count": len(records), "kept_activity_attachment_count": len(activities) if activities is not None else None,
            "activity_cross_check_completed": activities is not None,
            "kept_activity_identity_matches": matches,
            "kept_activity_attachments_missing": [], "files": records,
            "scope": "All files emitted by unfiltered xcresulttool export; activity completeness is stated separately. No pixel or text rewriting."}
