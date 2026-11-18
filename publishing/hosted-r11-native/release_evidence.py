#!/usr/bin/env python3
"""Reserve and verify complete evidence assets on one root-created draft only."""
from __future__ import annotations

import argparse
import base64
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import stat
import sys

import hosted_binding as bound
from github_evidence_transport import GitHubEvidenceTransport, check_asset, file_record, strict_json
from overflow_evidence import verify_completed_package
from release_contract import (BODY, POLICY, TAG, SOURCE_COMMIT, asset_name, canonical,
                              expected_claim, require, validate_binding, validate_remote_release)


HERE = Path(__file__).absolute().parent


def write_original(path, raw):
    require(isinstance(raw, bytes) and not os.path.lexists(path), "Never replace prior evidence bytes")
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, "wb") as stream:
        stream.write(raw); stream.flush(); os.fsync(stream.fileno())


def reservation_path(attempt):
    return attempt.with_name(attempt.name + "-ReleaseReservation")


def route_path(attempt):
    return attempt.with_name(attempt.name + "-EvidenceRoute.json")


def directory_records(directory, *, omit=()):
    require(directory.is_dir() and not directory.is_symlink() and directory.resolve() == directory,
            "Unaliased evidence directory required")
    records = {}
    for path in sorted(directory.rglob("*")):
        require(not path.is_symlink() and path.is_file(), "Reservation evidence must contain only original regular files")
        name = path.relative_to(directory).as_posix()
        if name not in omit:
            records[name] = {**file_record(path), "mode": stat.S_IMODE(path.stat().st_mode)}
    return records


def verify_asset_set(transport, expected):
    actual = transport.assets()
    require(len(actual) == len(expected) and {x.get("name") for x in actual} == set(expected),
            "Existing release assets are unexpected, incomplete or reused")
    for asset in actual:
        row = expected[asset["name"]]
        require(asset["id"] == row["id"], "A release asset was replaced")
        check_asset(asset, name=asset["name"], expected={k: row[k] for k in ("bytes", "sha256")},
                    release_id=transport.release_id)
    return actual


def verify_remote_context(transport, binding):
    release, tag = transport.release(), transport.tag(TAG)
    validate_remote_release(binding, release, tag)
    return release, tag


def reserve(context, env, *, transport_factory=GitHubEvidenceTransport):
    config, index, coverage, review, checkout, attempt = context
    binding = config["evidence_release"]
    validate_binding(binding)
    require(not os.path.lexists(attempt) and not os.path.lexists(Path("/tmp/dot-ios-build.lock")),
            "Native attempt already exists or ownership is occupied; no waiting/reclamation")
    directory = reservation_path(attempt)
    require(not os.path.lexists(directory), "Reservation directory already exists; never retry")
    directory.mkdir(mode=0o700)
    token = env.get("HALALTAG_EVIDENCE_TOKEN", "")
    transport = transport_factory(token, binding["release_id"], directory / "transport.jsonl", seconds=45)
    try:
        verify_remote_context(transport, binding)
        require(transport.assets() == [], "Root-created evidence draft is not empty; never reuse it")
        claim = canonical(expected_claim(config, env))
        path = directory / "reservation.json"
        write_original(path, claim)
        expected = file_record(path)
        name = asset_name(env, "reservation.json")
        asset = transport.upload(path, name, expected=expected, maximum_bytes=16_384)
        transport.download(asset, directory / "reservation.downloaded.json", expected=expected, maximum_bytes=16_384)
        row = check_asset(asset, name=name, expected=expected, release_id=binding["release_id"])
        verify_asset_set(transport, {name: row})
        release, tag = verify_remote_context(transport, binding)
        proof = {"schema_version": 1, "status": "ONE_SHOT_RESERVATION_UPLOADED_AND_DOWNLOADED_NATIVE_NOT_RUN",
                 "claim": expected_claim(config, env), "claim_asset": row,
                 "bound_release": release, "bound_tag": tag,
                 "original_files": directory_records(directory),
                 "native_pass": False, "full_evidence_delivered": False, "store_release": False}
        write_original(directory / "reservation-proof.json", canonical(proof))
        verify_reservation(context, env)
        print(json.dumps({"reservation_verified": True, "release_id": binding["release_id"],
                          "claim_asset_id": row["id"], "native_pass": False, "full_evidence_delivered": False}))
        return proof
    finally:
        # This contains fixed API paths and raw JSON responses, never token/header/CDN query bytes.
        print(json.dumps({"reservation_original_transport_ledger_base64":
                          base64.b64encode(transport.ledger.read_bytes()).decode()}))


def verify_reservation(context, env):
    config, _, _, _, _, attempt = context
    validate_binding(config["evidence_release"])
    directory = reservation_path(attempt)
    proof = bound.read_json(directory / "reservation-proof.json")
    require(proof.get("status") == "ONE_SHOT_RESERVATION_UPLOADED_AND_DOWNLOADED_NATIVE_NOT_RUN"
            and proof.get("claim") == expected_claim(config, env)
            and proof.get("native_pass") is False and proof.get("full_evidence_delivered") is False
            and proof.get("store_release") is False, "A verified claim for this exact first attempt is missing")
    validate_remote_release(config["evidence_release"], proof["bound_release"], proof["bound_tag"])
    require(directory_records(directory, omit=("reservation-proof.json",)) == proof.get("original_files"),
            "Original reservation evidence changed after read-back")
    claim = canonical(expected_claim(config, env))
    require((directory / "reservation.json").read_bytes() == claim
            and (directory / "reservation.downloaded.json").read_bytes() == claim, "Claim bytes differ from this actual run")
    row = proof["claim_asset"]
    require(row.get("name") == asset_name(env, "reservation.json") and row.get("state") == "uploaded"
            and type(row.get("id")) is int and row["id"] > 0
            and row.get("bytes") == len(claim) and row.get("sha256") == hashlib.sha256(claim).hexdigest(),
            "Missing exact claim asset receipt")
    return proof


def preserve_reservation(attempt):
    """Preserve even failed preflight originals; following symlinks is prohibited."""
    source, target = reservation_path(attempt), attempt / "ReleaseReservation"
    if not os.path.lexists(source):
        return
    require(source.is_dir() and not source.is_symlink() and source.resolve() == source,
            "Ambiguous original reservation directory")
    if not os.path.lexists(target):
        shutil.copytree(source, target, symlinks=True, copy_function=shutil.copy2)
    require(directory_records(source) == directory_records(target),
            "Copied reservation originals differ; never overwrite either copy")


def deliver(context, env, *, transport_factory=GitHubEvidenceTransport):
    config, index, coverage, review, checkout, attempt = context
    binding = config["evidence_release"]
    validate_binding(binding)
    proof = verify_reservation(context, env)
    require(not os.path.lexists(Path("/tmp/dot-ios-build.lock")), "Native ownership must be safely released before upload")
    target = attempt.with_name(attempt.name + "-Evidence")
    route = bound.read_json(route_path(attempt))
    require(route.get("route") == "root_bound_draft_assets"
            and route.get("upload_verified") is False, "Only actual complete overflow may use draft assets")
    verdict_bytes = (target / "verdict.json").read_bytes()
    roots = {"Attempt": attempt, "Candidate": checkout}
    verified = verify_completed_package(roots, target, verdict_bytes=verdict_bytes,
        cap=config["cost"]["maximum_output_bytes"], require_overflow=True)
    require(verified["outputs"] == route["outputs"] and verified["total_bytes"] == route["total_bytes"],
            "Complete package differs from the actual collection result")
    directory = attempt.with_name(attempt.name + "-ReleaseDelivery")
    require(not os.path.lexists(directory), "Prior or uncertain release delivery exists; never retry")
    directory.mkdir(mode=0o700)
    downloads = directory / "DownloadedOriginals"; downloads.mkdir(mode=0o700)
    transport = transport_factory(env.get("HALALTAG_EVIDENCE_TOKEN", ""), binding["release_id"],
                                  directory / "transport.jsonl", seconds=270)
    try:
        verify_remote_context(transport, binding)
        expected_assets = {proof["claim_asset"]["name"]: proof["claim_asset"]}
        verify_asset_set(transport, expected_assets)
        receipts = {}
        for original in ("evidence.tar.gz", "complete-member-index.json", "verdict.json"):
            expected = {k: verified["outputs"][original][k] for k in ("bytes", "sha256")}
            name = asset_name(env, original)
            asset = transport.upload(target / original, name, expected=expected,
                                     maximum_bytes=POLICY["maximum_asset_bytes"][original])
            transport.download(asset, downloads / original, expected=expected,
                               maximum_bytes=POLICY["maximum_asset_bytes"][original])
            row = check_asset(asset, name=name, expected=expected, release_id=binding["release_id"])
            expected_assets[name] = row; receipts[original] = row
        downloaded = verify_completed_package(roots, downloads, verdict_bytes=verdict_bytes,
            cap=config["cost"]["maximum_output_bytes"], require_overflow=True)
        require(downloaded["outputs"] == verified["outputs"], "Read-back originals differ from complete source evidence")
        verify_asset_set(transport, expected_assets)
        verify_remote_context(transport, binding)
        verdict = strict_json(verdict_bytes)
        receipt = {"schema_version": 1, "status": "THREE_COMPLETE_ORIGINAL_ASSETS_DOWNLOADED_AND_VERIFIED",
                   "repository": config["repository"], "release_id": binding["release_id"], "tag": TAG,
                   "draft": True, "source_commit": SOURCE_COMMIT, "workflow_commit": env["GITHUB_SHA"],
                   "run_id": env["GITHUB_RUN_ID"], "run_attempt": 1,
                   "root_review_sha256": config["root_review_sha256"], "reservation": proof["claim_asset"],
                   "assets": receipts, "complete_package_verification": downloaded,
                   "unchanged_original_verdict": verdict,
                   "original_transport_ledger_before_self_upload_base64":
                       base64.b64encode(transport.ledger.read_bytes()).decode(),
                   "this_receipt_asset_upload_and_download": "PENDING_RECORDED_IN_TERMINAL_JOB_LOG",
                   "store_release": False, "release_published": False, "extra_spend_authorized": False}
        raw = canonical(receipt)
        require(len(raw) <= POLICY["maximum_asset_bytes"]["delivery-receipt.json"], "Complete delivery receipt exceeds its bound")
        path = directory / "delivery-receipt.json"; write_original(path, raw)
        expected = file_record(path); name = asset_name(env, "delivery-receipt.json")
        asset = transport.upload(path, name, expected=expected, maximum_bytes=1_000_000)
        transport.download(asset, directory / "delivery-receipt.downloaded.json", expected=expected, maximum_bytes=1_000_000)
        row = check_asset(asset, name=name, expected=expected, release_id=binding["release_id"])
        expected_assets[name] = row
        verify_asset_set(transport, expected_assets)
        verify_remote_context(transport, binding)
        terminal = {"status": "COMPLETE_DRAFT_EVIDENCE_AND_RECEIPT_DOWNLOADED_VERIFIED",
                    "release_id": binding["release_id"], "receipt_asset_id": row["id"],
                    "receipt_sha256": row["sha256"], "receipt_bytes": row["bytes"],
                    "archive_sha256": verified["outputs"]["evidence.tar.gz"]["sha256"],
                    "archive_bytes": verified["outputs"]["evidence.tar.gz"]["bytes"],
                    "computation_gate_passed": verdict.get("computation_gate_passed") is True,
                    "draft_verified": True, "all_five_assets_exact": True, "store_release": False}
        write_original(directory / "terminal-receipt.json", canonical(terminal))
        from collect_evidence import emit_outputs
        emit_outputs({"release_delivery_verified": "true", "release_id": binding["release_id"],
                      "delivery_receipt_asset_id": row["id"], "delivery_receipt_sha256": row["sha256"],
                      "archive_sha256": terminal["archive_sha256"], "archive_bytes": terminal["archive_bytes"]})
        print(json.dumps(terminal))
        return terminal
    finally:
        # Final receipt upload cannot include its own HTTP response recursively.
        # Preserve all later original API response bytes in the actual workflow log.
        print(json.dumps({"delivery_original_transport_ledger_base64":
                          base64.b64encode(transport.ledger.read_bytes()).decode()}))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("reserve", "deliver"))
    args = parser.parse_args()
    context = bound.load_bound(HERE, os.environ, datetime.now(timezone.utc), sys.platform,
        platform.machine(), platform.mac_ver()[0], collecting=args.mode == "deliver")
    (reserve if args.mode == "reserve" else deliver)(context, os.environ)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
