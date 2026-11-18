"""Pure, complete HalalTag hosted evidence packaging; no native or network action.

Native reports are opaque original bytes. Only Candidate/.git is excluded.
The caller must stop all input writers before calling this module. No source
file is modified, followed through a symlink, deleted, or silently omitted.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import stat
import tarfile


MAXIMUM_ARTIFACT_BYTES = 500_000_000
MAXIMUM_VERDICT_BYTES = 16_384
ROOT_NAMES = frozenset({"Attempt", "Candidate"})
OUTPUT_NAMES = ("evidence.tar.gz", "complete-member-index.json", "verdict.json")
CHUNK = 1024 * 1024


class PackagingFailure(ValueError):
    """No complete publishable package was returned; originals remain untouched."""


def require(value, message):
    if not value:
        raise PackagingFailure(message)


def json_bytes(value):
    return (json.dumps(value, ensure_ascii=True, sort_keys=True, indent=2, allow_nan=False) + "\n").encode()


def unique_object(pairs):
    value = {}
    for key, item in pairs:
        require(key not in value, "Duplicate caller verdict key")
        value[key] = item
    return value


def validate_verdict(raw):
    require(isinstance(raw, bytes) and 0 < len(raw) <= MAXIMUM_VERDICT_BYTES,
            "Caller verdict must be nonempty bytes within the small verdict bound")
    value = json.loads(raw, object_pairs_hook=unique_object,
                       parse_constant=lambda _: (_ for _ in ()).throw(PackagingFailure("Nonfinite caller verdict")))
    require(isinstance(value, dict), "Caller verdict must be a strict JSON object")
    # Interpret neither a native report nor the caller's pass/fail decision.


def fingerprint(info):
    # Reading may change atime; it must not change identity, content or mode.
    return (info.st_dev, info.st_ino, info.st_mode, info.st_size, info.st_mtime_ns,
            info.st_ctime_ns, info.st_uid, info.st_gid, info.st_nlink)


def safe_name(value):
    require(isinstance(value, str) and value not in ("", ".", "..") and "/" not in value
            and "\\" not in value and not any(ord(c) < 32 or ord(c) == 127 for c in value),
            "Unsafe evidence member name; original retained, not omitted")


def checked_path(value, *, present):
    require(isinstance(value, Path) and value.is_absolute() and value != Path(value.anchor)
            and ".." not in value.parts and str(value) == os.path.normpath(str(value)),
            "Input/output root must be a canonical non-filesystem-root absolute Path")
    for part in value.parts[1:]:
        safe_name(part)
    paths = list(reversed(value.parents)) + ([value] if present else [])
    for path in paths:
        info = path.lstat()
        require(stat.S_ISDIR(info.st_mode) and not stat.S_ISLNK(info.st_mode),
                "A root or root ancestor is linked, special or not a directory")
    require(str(value.resolve(strict=present)) == str(value),
            "Noncanonical absolute root alias; refuse before any output is created")
    if not present:
        require(not os.path.lexists(value), "Output directory already exists; never replace prior evidence")
    return value


def is_within(path, parent):
    return path == parent or parent in path.parents


def directory_fd(path):
    before = path.lstat()
    require(stat.S_ISDIR(before.st_mode), "Root is not an ordinary directory")
    fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        require(fingerprint(os.fstat(fd)) == fingerprint(before), "Directory changed while being opened")
        return fd
    except BaseException:
        os.close(fd)
        raise


def physical_ancestors(fd):
    """Read actual directory identities through descriptors, not lexical spelling."""
    identities = set()
    current = os.dup(fd)
    try:
        for _ in range(1024):
            info = os.fstat(current)
            require(stat.S_ISDIR(info.st_mode), "Physical ancestor is not a directory")
            identity = (info.st_dev, info.st_ino)
            require(identity not in identities, "Physical ancestry repeated before its filesystem root")
            identities.add(identity)
            parent = os.open("..", os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=current)
            try:
                parent_info = os.fstat(parent)
                if (parent_info.st_dev, parent_info.st_ino) == identity:
                    os.close(parent)
                    return identities
            except BaseException:
                os.close(parent)
                raise
            os.close(current); current = parent
        raise PackagingFailure("Physical ancestry exceeds the bounded directory depth")
    finally:
        os.close(current)


def verify_physical_separation(snapshot, roots_fd, output_parent_fd):
    """Refuse aliased containment before mkdir, including case/Unicode aliases."""
    directories = {
        label: {witness[:2] for name, witness in snapshot["witnesses"].items()
                if name.split("/", 1)[0] == label and stat.S_ISDIR(witness[2])}
        for label in ROOT_NAMES
    }
    ancestors = {label: physical_ancestors(fd) for label, fd in roots_fd.items()}
    root_ids = {}
    for label, fd in roots_fd.items():
        info = os.fstat(fd)
        require(fingerprint(info) == snapshot["witnesses"][label], "Input root changed before physical separation check")
        root_ids[label] = (info.st_dev, info.st_ino)
    require(not directories["Attempt"].intersection(directories["Candidate"])
            and root_ids["Attempt"] not in ancestors["Candidate"]
            and root_ids["Candidate"] not in ancestors["Attempt"],
            "Input roots physically overlap through an alias; refuse before mkdir")
    output_ancestors = physical_ancestors(output_parent_fd)
    require(not output_ancestors.intersection(directories["Attempt"] | directories["Candidate"]),
            "Output parent is physically inside an input tree; refuse before mkdir")


def metadata(info, kind):
    return {"type": kind, "mode": stat.S_IMODE(info.st_mode), "uid": info.st_uid, "gid": info.st_gid,
            "mtime_ns": info.st_mtime_ns, "source_link_count": info.st_nlink}


def hash_open_file(fd, expected):
    require(stat.S_ISREG(os.fstat(fd).st_mode) and fingerprint(os.fstat(fd)) == fingerprint(expected),
            "Original file identity or mode changed before hashing")
    digest, count = hashlib.sha256(), 0
    while True:
        block = os.read(fd, CHUNK)
        if not block:
            break
        digest.update(block); count += len(block)
    require(count == expected.st_size and fingerprint(os.fstat(fd)) == fingerprint(expected),
            "Original file changed while hashing")
    return digest.hexdigest(), count


def snapshot_inputs(roots, descriptors):
    """Inventory every original directory/file/link through no-follow descriptors."""
    members, witnesses, excluded = {}, {}, []

    def walk(path_name, fd, expected):
        require(fingerprint(os.fstat(fd)) == fingerprint(expected), "Original directory changed before enumeration")
        members[path_name] = metadata(expected, "directory")
        witnesses[path_name] = fingerprint(expected)
        with os.scandir(fd) as entries:
            names = sorted(entry.name for entry in entries)
        for name in names:
            safe_name(name)
            child_name = path_name + "/" + name
            if child_name == "Candidate/.git":
                excluded.append({"path": child_name, "reason": "Only approved Git metadata exclusion; no descendant read"})
                continue
            info = os.stat(name, dir_fd=fd, follow_symlinks=False)
            witnesses[child_name] = fingerprint(info)
            if stat.S_ISDIR(info.st_mode):
                child_fd = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
                try:
                    walk(child_name, child_fd, info)
                finally:
                    os.close(child_fd)
            elif stat.S_ISREG(info.st_mode):
                child_fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW, dir_fd=fd)
                try:
                    digest, count = hash_open_file(child_fd, info)
                finally:
                    os.close(child_fd)
                members[child_name] = dict(metadata(info, "file"), bytes=count, sha256=digest, hardlink_target=None)
            elif stat.S_ISLNK(info.st_mode):
                target = os.readlink(name, dir_fd=fd)
                require(fingerprint(os.stat(name, dir_fd=fd, follow_symlinks=False)) == fingerprint(info),
                        "Original symbolic link changed while indexing")
                raw = os.fsencode(target)
                members[child_name] = dict(metadata(info, "symlink"), target=target, bytes=len(raw),
                                          sha256=hashlib.sha256(raw).hexdigest(), hash_scope="link_target_bytes")
            else:
                raise PackagingFailure("Unsupported special original member retained: " + child_name)
        require(fingerprint(os.fstat(fd)) == fingerprint(expected), "Original directory changed during enumeration")

    for label in sorted(ROOT_NAMES):
        checked_path(roots[label], present=True)
        expected = roots[label].lstat()
        walk(label, descriptors[label], expected)
        require(fingerprint(roots[label].lstat()) == fingerprint(expected), "Original root path changed")
    first_inode = {}
    for name, row in sorted(members.items()):
        if row["type"] == "file":
            inode = witnesses[name][:2]
            if inode in first_inode:
                row["hardlink_target"] = first_inode[inode]
            else:
                first_inode[inode] = name
    return {"members": dict(sorted(members.items())), "excluded": excluded, "witnesses": witnesses}


def open_original(name, roots_fd, expected):
    parts = PurePosixPath(name).parts
    require(parts and parts[0] in ROOT_NAMES and len(parts) > 1, "Invalid original file selection")
    current = os.dup(roots_fd[parts[0]])
    try:
        for part in parts[1:-1]:
            safe_name(part)
            next_fd = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=current)
            os.close(current); current = next_fd
        fd = os.open(parts[-1], os.O_RDONLY | os.O_NOFOLLOW, dir_fd=current)
        try:
            require(stat.S_ISREG(os.fstat(fd).st_mode) and fingerprint(os.fstat(fd)) == expected,
                    "Original file changed before archive read")
            return fd
        except BaseException:
            os.close(fd)
            raise
    finally:
        os.close(current)


def mtime_text(nanoseconds):
    seconds, remainder = divmod(abs(nanoseconds), 1_000_000_000)
    return ("-" if nanoseconds < 0 else "") + f"{seconds}.{remainder:09d}"


def tar_info(name, row):
    info = tarfile.TarInfo(name)
    info.mode = row["mode"]; info.uid = row["uid"]; info.gid = row["gid"]
    info.uname = ""; info.gname = ""
    info.mtime = row["mtime_ns"] // 1_000_000_000
    info.pax_headers = {"mtime": mtime_text(row["mtime_ns"])}
    if row["type"] == "directory":
        info.type = tarfile.DIRTYPE
    elif row["type"] == "symlink":
        info.type = tarfile.SYMTYPE; info.linkname = row["target"]
    elif row["hardlink_target"] is not None:
        info.type = tarfile.LNKTYPE; info.linkname = row["hardlink_target"]
    else:
        info.type = tarfile.REGTYPE; info.size = row["bytes"]
    return info


class CheckedReader:
    def __init__(self, stream):
        self.stream = stream; self.digest = hashlib.sha256(); self.count = 0

    def read(self, amount=-1):
        block = self.stream.read(amount)
        self.digest.update(block); self.count += len(block)
        return block


def exclusive_output(output_fd, name):
    require(name in OUTPUT_NAMES, "Unreviewed packaging output name")
    return os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=output_fd)


def write_output(output_fd, name, raw):
    fd = exclusive_output(output_fd, name)
    with os.fdopen(fd, "wb") as stream:
        stream.write(raw); stream.flush(); os.fsync(stream.fileno())


def write_archive(output_fd, roots_fd, snapshot):
    fd = exclusive_output(output_fd, "evidence.tar.gz")
    with os.fdopen(fd, "wb") as stream:
        with tarfile.open(fileobj=stream, mode="w:gz", format=tarfile.PAX_FORMAT,
                          dereference=False, compresslevel=6) as archive:
            # Only indexed INCLUDED members reach tarfile. An excluded .git inode
            # can never become a retained evidence member's stored hardlink anchor.
            for name, row in snapshot["members"].items():
                info = tar_info(name, row)
                if info.isfile():
                    source_fd = open_original(name, roots_fd, snapshot["witnesses"][name])
                    with os.fdopen(source_fd, "rb") as original:
                        checked = CheckedReader(original)
                        archive.addfile(info, checked)
                        require(checked.count == row["bytes"] and checked.digest.hexdigest() == row["sha256"]
                                and original.read(1) == b""
                                and fingerprint(os.fstat(original.fileno())) == snapshot["witnesses"][name],
                                "Original bytes or mode changed during archive write: " + name)
                else:
                    archive.addfile(info)
        stream.flush(); os.fsync(stream.fileno())


def output_record(output_fd, name):
    info = os.stat(name, dir_fd=output_fd, follow_symlinks=False)
    require(stat.S_ISREG(info.st_mode) and stat.S_IMODE(info.st_mode) == 0o600,
            "Packaging output was replaced or its mode changed")
    fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW, dir_fd=output_fd)
    try:
        digest, count = hash_open_file(fd, info)
    finally:
        os.close(fd)
    return {"name": name, "bytes": count, "sha256": digest, "mode": 0o600}


def verify_archive(output_fd, snapshot):
    fd = os.open("evidence.tar.gz", os.O_RDONLY | os.O_NOFOLLOW, dir_fd=output_fd)
    expected, found = snapshot["members"], set()
    with os.fdopen(fd, "rb") as stream:
        with tarfile.open(fileobj=stream, mode="r:gz") as archive:
            for member in archive:
                name = member.name
                require(name in expected and name not in found, "Unexpected, unsafe or duplicate archived member")
                found.add(name); row = expected[name]
                require(member.mode == row["mode"] and member.uid == row["uid"] and member.gid == row["gid"]
                        and member.pax_headers.get("mtime") == mtime_text(row["mtime_ns"]),
                        "Archived original mode/owner/time metadata differs: " + name)
                if row["type"] == "directory":
                    require(member.isdir() and member.size == 0, "Original directory metadata was lost")
                elif row["type"] == "symlink":
                    require(member.issym() and member.size == 0 and member.linkname == row["target"]
                            and hashlib.sha256(os.fsencode(member.linkname)).hexdigest() == row["sha256"],
                            "Original symbolic-link metadata was lost")
                else:
                    if row["hardlink_target"] is None:
                        require(member.isfile() and member.size == row["bytes"], "Original regular file storage changed")
                    else:
                        target = row["hardlink_target"]
                        require(member.islnk() and member.size == 0 and member.linkname == target and target in found
                                and expected[target]["type"] == "file" and expected[target]["hardlink_target"] is None
                                and archive.getmember(target).isfile(), "Original included hardlink relation was lost")
                    source = archive.extractfile(member)
                    require(source is not None, "Original archived file cannot be read")
                    digest, count = hashlib.sha256(), 0
                    with source:
                        for block in iter(lambda: source.read(CHUNK), b""):
                            digest.update(block); count += len(block)
                    require(count == row["bytes"] and digest.hexdigest() == row["sha256"],
                            "Archived original file bytes differ: " + name)
    require(found == set(expected), "Archive omitted original members or empty directories")


def pack_evidence(roots: dict[str, Path], output_dir: Path, *, maximum_artifact_bytes: int,
                  verdict_bytes: bytes) -> dict:
    """Return a verified complete package only; failures retain originals and outputs.

    Required disjoint roots are Attempt and Candidate. The output directory is
    exclusive, fresh, and outside both input trees. Its cap counts exactly the
    gzip tar, complete original-member index and unchanged caller verdict bytes.
    This function neither parses a native report nor grants upload authority.
    """
    roots_fd, output_fd, output_parent_fd = {}, None, None
    try:
        require(type(maximum_artifact_bytes) is int and 0 < maximum_artifact_bytes <= MAXIMUM_ARTIFACT_BYTES,
                "Bounded root-approved artifact cap must be positive and at most 500000000 bytes")
        validate_verdict(verdict_bytes)
        require(isinstance(roots, dict) and set(roots) == ROOT_NAMES, "Exactly Attempt and Candidate roots are required")
        roots = {name: checked_path(roots[name], present=True) for name in sorted(ROOT_NAMES)}
        checked_path(output_dir, present=False)
        require(not is_within(roots["Attempt"], roots["Candidate"])
                and not is_within(roots["Candidate"], roots["Attempt"]), "Input roots must be disjoint")
        require(all(not is_within(output_dir, root) and not is_within(root, output_dir) for root in roots.values()),
                "Packaging output may not contain or be contained by an input root")
        for name, path in roots.items():
            roots_fd[name] = directory_fd(path)
        require(len({(os.fstat(fd).st_dev, os.fstat(fd).st_ino) for fd in roots_fd.values()}) == 2,
                "Input roots refer to the same physical directory")
        before = snapshot_inputs(roots, roots_fd)
        output_parent_fd = directory_fd(output_dir.parent)
        verify_physical_separation(before, roots_fd, output_parent_fd)
        os.mkdir(output_dir.name, mode=0o700, dir_fd=output_parent_fd)
        output_fd = os.open(output_dir.name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=output_parent_fd)
        output_identity = (os.fstat(output_fd).st_dev, os.fstat(output_fd).st_ino)
        checked_path(output_dir, present=True)
        require((output_dir.lstat().st_dev, output_dir.lstat().st_ino) == output_identity, "Fresh output directory identity changed")
        index = {"schema_version": 1, "scope": "Complete original Attempt and Candidate trees",
                 "source_roots": {name: str(path) for name, path in roots.items()}, "members": before["members"],
                 "excluded_subtrees": before["excluded"], "only_permitted_exclusion": "Candidate/.git",
                 "cache_or_DerivedData_exclusions": [], "native_report_parsed": False,
                 "caller_verdict": {"name": "verdict.json", "bytes": len(verdict_bytes),
                                    "sha256": hashlib.sha256(verdict_bytes).hexdigest()},
                 "maximum_total_artifact_bytes": maximum_artifact_bytes,
                 "symlinks_followed": False, "hardlink_scope": "Every relation among included files; outside-scope inode targets never read"}
        raw_index = json_bytes(index)
        write_output(output_fd, "complete-member-index.json", raw_index)
        write_output(output_fd, "verdict.json", verdict_bytes)
        write_archive(output_fd, roots_fd, before)
        archive_before_verify = output_record(output_fd, "evidence.tar.gz")
        verify_archive(output_fd, before)
        after = snapshot_inputs(roots, roots_fd)
        require(before == after, "Original complete tree, modes, links or bytes changed during packaging; no package accepted")
        with os.scandir(output_fd) as entries:
            require({entry.name for entry in entries} == set(OUTPUT_NAMES), "Unexpected packaging output member")
        outputs = {name: output_record(output_fd, name) for name in OUTPUT_NAMES}
        require(outputs["evidence.tar.gz"] == archive_before_verify, "Archive bytes changed after verification")
        require(outputs["complete-member-index.json"]["bytes"] == len(raw_index)
                and outputs["complete-member-index.json"]["sha256"] == hashlib.sha256(raw_index).hexdigest()
                and outputs["verdict.json"]["bytes"] == len(verdict_bytes)
                and outputs["verdict.json"]["sha256"] == hashlib.sha256(verdict_bytes).hexdigest(),
                "Index or caller verdict bytes changed")
        checked_path(output_dir, present=True)
        require((output_dir.lstat().st_dev, output_dir.lstat().st_ino) == output_identity, "Output directory path was replaced")
        total = sum(row["bytes"] for row in outputs.values())
        require(total <= maximum_artifact_bytes,
                f"Complete evidence plus index and verdict is {total} bytes, exceeding cap {maximum_artifact_bytes}; "
                "all originals and completed package retained, no publishable success")
        return {"status": "COMPLETE_EVIDENCE_PACKAGE_VERIFIED_WITHIN_BOUND_CAP", "output_directory": str(output_dir),
                "outputs": outputs, "total_artifact_bytes": total, "maximum_artifact_bytes": maximum_artifact_bytes,
                "indexed_member_count": len(before["members"]), "source_members_before_after_identical": True,
                "all_tar_members_bytes_modes_links_verified": True, "native_report_parsed": False,
                "native_acceptance_established_by_packer": False, "upload_authorized_by_packer": False,
                "upload_verified": False, "store_release": False, "originals_deleted_or_rewritten": False}
    except PackagingFailure:
        raise
    except (OSError, ValueError, TypeError, tarfile.TarError) as error:
        raise PackagingFailure("Complete packaging refused; originals and partial outputs retained: " + str(error)) from error
    finally:
        for fd in [output_fd, output_parent_fd, *roots_fd.values()]:
            if fd is not None:
                os.close(fd)
