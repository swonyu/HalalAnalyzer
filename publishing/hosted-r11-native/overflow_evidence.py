"""Verify a completed over-cap package without changing the frozen 500 MB packer.

This module grants no network authority and never changes the caller's verdict.
Only the frozen packer's final, complete-package size rejection can select the
separately root-bound draft-asset route. Every other packaging error propagates.
"""
from __future__ import annotations

import gzip
import hashlib
import json
import os
from pathlib import Path
import re
import stat

import evidence_pack as pack


FROZEN_PACKER_SHA256 = "ee493ee09002132ae47ebfe97b061f17ed6a4c6e1bb1505a944a54c27cd7980a"
RELEASE_LIMITS = {"evidence.tar.gz": 2_000_000_000,
                  "complete-member-index.json": 40_000_000,
                  "verdict.json": 16_384}
MAXIMUM_DELIVERY_RECEIPT_BYTES = 1_000_000
OVERFLOW = re.compile(r"Complete evidence plus index and verdict is ([1-9][0-9]*) bytes, "
                      r"exceeding cap ([1-9][0-9]*); all originals and completed package retained, "
                      r"no publishable success")


def require(value, message):
    if not value:
        raise pack.PackagingFailure(message)


def verify_frozen_packer():
    path = Path(pack.__file__)
    require(not path.is_symlink() and hashlib.sha256(path.read_bytes()).hexdigest() == FROZEN_PACKER_SHA256,
            "The original complete-evidence packer changed")
    require(pack.MAXIMUM_ARTIFACT_BYTES == 500_000_000 and pack.MAXIMUM_VERDICT_BYTES == 16_384,
            "Original package or verdict limit changed")


def gzip_crc_to_eof(output_fd):
    """Tar iteration may stop before the trailer; explicitly read every gzip byte."""
    fd = os.open("evidence.tar.gz", os.O_RDONLY | os.O_NOFOLLOW, dir_fd=output_fd)
    with os.fdopen(fd, "rb") as raw:
        with gzip.GzipFile(fileobj=raw, mode="rb") as stream:
            while stream.read(pack.CHUNK):
                pass


def expected_index(roots, snapshot, verdict_bytes, cap):
    return {"schema_version": 1, "scope": "Complete original Attempt and Candidate trees",
            "source_roots": {name: str(path) for name, path in roots.items()},
            "members": snapshot["members"], "excluded_subtrees": snapshot["excluded"],
            "only_permitted_exclusion": "Candidate/.git", "cache_or_DerivedData_exclusions": [],
            "native_report_parsed": False,
            "caller_verdict": {"name": "verdict.json", "bytes": len(verdict_bytes),
                               "sha256": hashlib.sha256(verdict_bytes).hexdigest()},
            "maximum_total_artifact_bytes": cap, "symlinks_followed": False,
            "hardlink_scope": "Every relation among included files; outside-scope inode targets never read"}


def verify_completed_package(roots, output_dir, *, verdict_bytes, cap, require_overflow):
    """Reopen complete originals and all outputs, without importing a native runner."""
    verify_frozen_packer()
    require(type(cap) is int and 0 < cap <= 500_000_000, "Original Actions cap must remain bounded")
    pack.validate_verdict(verdict_bytes)
    require(isinstance(roots, dict) and set(roots) == pack.ROOT_NAMES, "Complete input roots required")
    roots = {name: pack.checked_path(roots[name], present=True) for name in sorted(pack.ROOT_NAMES)}
    pack.checked_path(output_dir, present=True)
    require(not pack.is_within(roots["Attempt"], roots["Candidate"])
            and not pack.is_within(roots["Candidate"], roots["Attempt"]), "Input roots overlap")
    require(all(not pack.is_within(output_dir, root) and not pack.is_within(root, output_dir)
                for root in roots.values()), "Output and input roots overlap")
    descriptors, output_fd, parent_fd = {}, None, None
    try:
        for name, path in roots.items():
            descriptors[name] = pack.directory_fd(path)
        before = pack.snapshot_inputs(roots, descriptors)
        parent_fd = pack.directory_fd(output_dir.parent)
        pack.verify_physical_separation(before, descriptors, parent_fd)
        output_fd = pack.directory_fd(output_dir)
        identity = pack.fingerprint(os.fstat(output_fd))
        require(stat.S_IMODE(os.fstat(output_fd).st_mode) == 0o700, "Output directory mode changed")
        with os.scandir(output_fd) as entries:
            require({entry.name for entry in entries} == set(pack.OUTPUT_NAMES), "Incomplete or extra package output")
        outputs = {name: pack.output_record(output_fd, name) for name in pack.OUTPUT_NAMES}
        total = sum(row["bytes"] for row in outputs.values())
        require((total > cap) if require_overflow else (total <= cap), "Wrong evidence delivery route for actual bytes")
        if require_overflow:
            require(all(0 < row["bytes"] <= RELEASE_LIMITS[name] for name, row in outputs.items()),
                    "A complete asset exceeds its stricter reviewed release bound; no omissions or split")
        index_bytes = pack.json_bytes(expected_index(roots, before, verdict_bytes, cap))
        require(outputs["complete-member-index.json"]["bytes"] == len(index_bytes)
                and outputs["complete-member-index.json"]["sha256"] == hashlib.sha256(index_bytes).hexdigest(),
                "Full index does not match every current original member")
        require(outputs["verdict.json"]["bytes"] == len(verdict_bytes)
                and outputs["verdict.json"]["sha256"] == hashlib.sha256(verdict_bytes).hexdigest(),
                "Original caller verdict changed")
        pack.verify_archive(output_fd, before)
        gzip_crc_to_eof(output_fd)
        require(pack.snapshot_inputs(roots, descriptors) == before, "An original input changed during verification")
        require({name: pack.output_record(output_fd, name) for name in pack.OUTPUT_NAMES} == outputs,
                "A package output changed during verification")
        require(pack.fingerprint(output_dir.lstat()) == identity, "Output directory identity changed")
        return {"status": "COMPLETE_OVERFLOW_VERIFIED_DELIVERY_PENDING" if require_overflow
                          else "COMPLETE_ACTIONS_PACKAGE_VERIFIED_DELIVERY_PENDING",
                "route": "root_bound_draft_assets" if require_overflow else "actions_artifact",
                "outputs": outputs, "total_bytes": total, "actions_cap_bytes": cap,
                "indexed_member_count": len(before["members"]), "original_source_snapshot_unchanged": True,
                "all_tar_members_bytes_modes_links_verified": True, "gzip_crc_to_eof_verified": True,
                "original_caller_verdict_unchanged": True, "only_exclusion": "Candidate/.git",
                "upload_verified": False, "native_acceptance_established_by_packer": False,
                "store_release": False}
    finally:
        for fd in [output_fd, parent_fd, *descriptors.values()]:
            if fd is not None:
                os.close(fd)


def prepare_complete_evidence(roots, output_dir, *, maximum_artifact_bytes, verdict_bytes):
    verify_frozen_packer()
    overflow = None
    try:
        pack.pack_evidence(roots, output_dir, maximum_artifact_bytes=maximum_artifact_bytes,
                           verdict_bytes=verdict_bytes)
    except pack.PackagingFailure as error:
        overflow = OVERFLOW.fullmatch(str(error))
        if overflow is None or int(overflow.group(2)) != maximum_artifact_bytes:
            raise
    verified = verify_completed_package(roots, output_dir, verdict_bytes=verdict_bytes,
        cap=maximum_artifact_bytes, require_overflow=overflow is not None)
    if overflow is not None:
        require(int(overflow.group(1)) == verified["total_bytes"], "Frozen overflow count differs from actual bytes")
        verified["frozen_packer_final_size_rejection_preserved"] = overflow.group(0)
    return verified
