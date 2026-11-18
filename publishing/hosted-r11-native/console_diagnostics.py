"""Diagnostic-only console recovery; no native, ownership, upload or acceptance action.

The bounded raw-byte framing is adapted from Lumina's independently authored v5
helper. Additional routines select only this hosted attempt's exact metadata.
"""
from __future__ import annotations
import base64
import hashlib
import json
import os
from pathlib import Path
import stat
import traceback
from typing import Any

DIAGNOSTIC_CHUNK_BYTES = 8192
DIAGNOSTIC_LOG_TAIL_BYTES = 16384
DIAGNOSTIC_REPORT_BYTES = 4194304
DIAGNOSTIC_COMMAND_BYTES = 262144
LOCK_PATH = Path("/tmp/dot-ios-build.lock")
SOURCE_COMMIT = "7ef009beb0c1f6f355eeceb931d899553ea8cad5"
BOUND_REVIEW = {}

def console_diagnostic(kind: str, value: dict[str, Any]) -> None:
    """Observations only: no output permission, acceptance or environment dump."""
    print(json.dumps({"schema": "halaltag.native.console-diagnostic.v1", "kind": kind,
                      "diagnostic_only": True, "complete_native_evidence": False,
                      "workflow_commit": os.environ.get("GITHUB_SHA"),
                      "source_commit": SOURCE_COMMIT,
                      "root_review_sha256": BOUND_REVIEW.get("root_review_sha256"),
                      "github_run_id": os.environ.get("GITHUB_RUN_ID"),
                      "github_run_attempt": os.environ.get("GITHUB_RUN_ATTEMPT"),
                      "record": value}, ensure_ascii=False), flush=True)

def console_original_bytes(path: Path, label: str, limit: int, *, tail: bool = False) -> None:
    """Mirror bounded exact original bytes; partial records never imply completion."""
    descriptor = None
    try:
        descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode):
            raise ValueError("Diagnostic input is not a regular original file")
        offset = max(0, before.st_size - limit) if tail else 0
        os.lseek(descriptor, offset, os.SEEK_SET)
        chunks = []
        remaining = min(limit, max(0, before.st_size - offset))
        while remaining:
            block = os.read(descriptor, min(DIAGNOSTIC_CHUNK_BYTES, remaining))
            if not block:
                break
            chunks.append(block)
            remaining -= len(block)
        after = os.fstat(descriptor)
        data = b"".join(chunks)
        try:
            current = path.lstat()
            path_same = stat.S_ISREG(current.st_mode) and (
                current.st_dev, current.st_ino, current.st_size, current.st_mtime_ns, current.st_ctime_ns) == (
                after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns, after.st_ctime_ns)
        except OSError:
            path_same = False
        stable = path_same and (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns, before.st_ctime_ns) == (
            after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns, after.st_ctime_ns)
        entire = stable and offset == 0 and len(data) == before.st_size
        console_diagnostic("original-file-metadata", {
            "label": label, "original_path": str(path), "original_bytes_before": before.st_size,
            "original_bytes_after": after.st_size, "captured_offset": offset, "captured_bytes": len(data),
            "capture_limit_bytes": limit, "read_metadata_unchanged": stable,
            "pathname_still_identifies_opened_original": path_same,
            "payload_is_entire_file": entire, "partial_original_bytes": not entire,
            "captured_bytes_sha256": hashlib.sha256(data).hexdigest(),
            "whole_file_sha256": hashlib.sha256(data).hexdigest() if entire else None,
            "encoding": "base64", "chunk_count": len(chunks),
        })
        position = offset
        for sequence, block in enumerate(chunks):
            console_diagnostic("original-file-chunk", {
                "label": label, "sequence": sequence, "offset": position,
                "bytes": len(block), "data_base64": base64.b64encode(block).decode("ascii"),
            })
            position += len(block)
    except (OSError, ValueError) as error:
        console_diagnostic("original-file-read-error", {
            "label": label, "original_path": str(path), "error_type": type(error).__name__, "error": str(error),
        })
    finally:
        if descriptor is not None:
            os.close(descriptor)


def bind_context(config):
    """Called only after the existing hosted binding was independently validated."""
    if config.get("source_commit") != SOURCE_COMMIT:
        raise ValueError("Diagnostic source context differs")
    BOUND_REVIEW.clear()
    BOUND_REVIEW["root_review_sha256"] = config.get("root_review_sha256")


def observe_exception(label, error):
    """A caught exception is visible without changing its original handling."""
    try:
        console_diagnostic("caught-exception", {
            "label": label, "error_type": type(error).__name__, "error": str(error),
            "traceback": "".join(traceback.format_exception(type(error), error, error.__traceback__)),
        })
    except Exception:
        pass  # A closed job console cannot change native ownership or its verdict.


def owned_path(path, root):
    path, root = Path(path), Path(root)
    relative = path.relative_to(root)
    if ".." in relative.parts or path.resolve() != path:
        raise ValueError("Diagnostic path is noncanonical or escapes the owned attempt")
    if not root.is_absolute() or root.is_symlink() or root.resolve() != root:
        raise ValueError("Diagnostic attempt root is aliased")
    for parent in (path, *path.parents):
        if parent.is_symlink():
            raise ValueError("Diagnostic original path is linked")
        if parent == root:
            break
    return path


def read_metadata(path, root):
    path = owned_path(path, root)
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode) or before.st_size > DIAGNOSTIC_REPORT_BYTES:
            raise ValueError("Diagnostic metadata is nonregular or exceeds its explicit read bound")
        parts = []
        while True:
            block = os.read(descriptor, min(DIAGNOSTIC_CHUNK_BYTES, DIAGNOSTIC_REPORT_BYTES + 1 - sum(map(len, parts))))
            if not block:
                break
            parts.append(block)
            if sum(map(len, parts)) > DIAGNOSTIC_REPORT_BYTES:
                raise ValueError("Diagnostic metadata grew beyond its read bound")
        after = os.fstat(descriptor)
        if (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns, before.st_ctime_ns) != (
                after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns, after.st_ctime_ns):
            raise ValueError("Diagnostic metadata changed while reading")
        return json.loads(b"".join(parts))
    finally:
        os.close(descriptor)


def mirror_owned(path, label, root, *, tail=False, limit=None):
    try:
        path = owned_path(path, root)
        bound = DIAGNOSTIC_LOG_TAIL_BYTES if tail else (DIAGNOSTIC_REPORT_BYTES if limit is None else limit)
        console_original_bytes(path, label, bound, tail=tail)
    except Exception as error:
        observe_exception("diagnostic-read:" + label, error)


def phase_terminal(report_path, root, label):
    """Preserve exact phase report and every original command/status record."""
    mirror_owned(report_path, label + ":report.json", root)
    try:
        report = read_metadata(report_path, root)
        if not isinstance(report, dict) or not isinstance(report.get("steps", []), list):
            raise ValueError("Diagnostic phase report has the wrong shape")
        for index, step in enumerate(report.get("steps", [])):
            if not isinstance(step, dict) or not isinstance(step.get("stdout"), str):
                raise ValueError("Diagnostic command record has the wrong shape")
            folder = owned_path(Path(step["stdout"]).parent, root)
            prefix = label + ":step:" + str(index) + ":" + str(step.get("name"))
            for name in ("command.json", "result.json"):
                mirror_owned(folder / name, prefix + ":" + name, root, limit=DIAGNOSTIC_COMMAND_BYTES)
            if step.get("status") != "passed":
                for name in ("stdout.log", "stderr.log"):
                    mirror_owned(folder / name, prefix + ":partial-tail:" + name, root, tail=True)
    except Exception as error:
        observe_exception("diagnostic-phase:" + label, error)


def lock_observation(attempt, label):
    """Read the known lock only; never signal, release, alter or reclaim it."""
    try:
        if not os.path.lexists(LOCK_PATH):
            console_diagnostic("lock-observation", {"label": label, "present": False, "mutation": False})
            return
        info = LOCK_PATH.lstat()
        record = {"label": label, "present": True, "path": str(LOCK_PATH), "mode": stat.S_IMODE(info.st_mode),
                  "device": info.st_dev, "inode": info.st_ino, "is_directory": stat.S_ISDIR(info.st_mode),
                  "is_symlink": stat.S_ISLNK(info.st_mode), "mutation": False}
        console_diagnostic("lock-observation", record)
        if not stat.S_ISDIR(info.st_mode) or stat.S_ISLNK(info.st_mode):
            return
        owner_root = LOCK_PATH.resolve()
        owner = owner_root / "owner.json"
        value = read_metadata(owner, owner_root)
        expected_slot = "github-halal-r11-" + os.environ.get("GITHUB_RUN_ID", "") + "-1-"
        if (not isinstance(value, dict) or value.get("owner") != "ios-app-publishing-and-quality"
                or value.get("slot_authorized") not in (expected_slot + "native", expected_slot + "production")
                or not isinstance(value.get("output"), str)
                or not Path(value["output"]).is_relative_to(attempt)):
            raise ValueError("Lock owner is not proven to be this attempt; no foreign bytes emitted")
        owned_path(Path(value["output"]), attempt)
        console_original_bytes(owner, label + ":exact-owned-lock-owner", DIAGNOSTIC_COMMAND_BYTES)
    except Exception as error:
        observe_exception("diagnostic-lock:" + label, error)


def attempt_terminal(attempt, label):
    """Observation is supplemental; all existing native and collector gates stand."""
    try:
        mirror_owned(attempt / "attempt.json", label + ":attempt.json", attempt)
        try:
            state = read_metadata(attempt / "attempt.json", attempt)
            for key in ("native_report", "production_report"):
                if isinstance(state.get(key), str):
                    phase_terminal(Path(state[key]), attempt, label + ":" + key)
        except Exception as error:
            observe_exception("diagnostic-attempt:" + label, error)
        lock_observation(attempt, label)
    except Exception as error:
        observe_exception("diagnostic-terminal:" + label, error)
