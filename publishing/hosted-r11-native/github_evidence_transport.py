"""One-shot GitHub draft-asset reads/uploads with explicit credential boundaries.

The only writes are POSTs of new assets to one already root-bound release.
No retries, overwrite, deletion, tag mutation, release creation or publication.
Authenticated requests never follow redirects. Signed download redirects are
fetched without Authorization, cookies or logged query strings.
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import time
import urllib.error
import urllib.parse
import urllib.request

from release_contract import REPOSITORY, canonical, require


API = "https://api.github.com"
UPLOADS = "https://uploads.github.com"
CDN_HOSTS = frozenset({"release-assets.githubusercontent.com", "objects.githubusercontent.com"})
MAX_JSON = 1_000_000
CHUNK = 1024 * 1024


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def strict_json(raw):
    def pairs(items):
        value = {}
        for key, item in items:
            require(key not in value, "Duplicate GitHub response key")
            value[key] = item
        return value
    return json.loads(raw, object_pairs_hook=pairs,
                      parse_constant=lambda _: (_ for _ in ()).throw(ValueError("Nonfinite GitHub JSON")))


def file_record(path):
    require(isinstance(path, Path) and path.is_absolute() and path.resolve() == path
            and all(not p.is_symlink() for p in [path, *path.parents]), "Linked or noncanonical evidence file")
    info = path.lstat()
    require(stat.S_ISREG(info.st_mode), "Evidence asset is not an original regular file")
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        before = os.fstat(fd)
        require((before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns, before.st_ctime_ns)
                == (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns), "Asset changed before read")
        digest, count = hashlib.sha256(), 0
        while block := os.read(fd, CHUNK):
            digest.update(block); count += len(block)
        after = os.fstat(fd)
        require((before.st_dev, before.st_ino, before.st_mode, before.st_size, before.st_mtime_ns, before.st_ctime_ns)
                == (after.st_dev, after.st_ino, after.st_mode, after.st_size, after.st_mtime_ns, after.st_ctime_ns)
                and count == before.st_size, "Asset changed while hashing")
        return {"bytes": count, "sha256": digest.hexdigest()}
    finally:
        os.close(fd)


def check_asset(asset, *, name, expected, release_id):
    require(isinstance(asset, dict) and type(asset.get("id")) is int and asset["id"] > 0,
            "Missing actual GitHub asset identity")
    require(asset.get("name") == name and asset.get("state") == "uploaded"
            and type(asset.get("size")) is int and asset["size"] == expected["bytes"]
            and asset.get("digest") == "sha256:" + expected["sha256"],
            "GitHub asset name/state/length/digest does not match the complete original file")
    require(asset.get("url") == f"{API}/repos/{REPOSITORY}/releases/assets/{asset['id']}",
            "Asset is outside the exact bound repository API")
    # Membership in the exact release is separately proven by its complete asset list.
    require(type(release_id) is int and release_id > 0, "Missing bound release identity")
    return {"id": asset["id"], "name": name, "bytes": expected["bytes"],
            "sha256": expected["sha256"], "state": "uploaded"}


class GitHubEvidenceTransport:
    def __init__(self, token, release_id, ledger, *, seconds=240, opener=None):
        require(isinstance(token, str) and 0 < len(token) < 4096 and "\n" not in token and "\r" not in token,
                "A scoped existing GitHub token is required")
        require(type(release_id) is int and release_id > 0 and 0 < seconds <= 270,
                "Unbound release or network time budget")
        require(isinstance(ledger, Path) and ledger.is_absolute() and ledger.parent.resolve() == ledger.parent
                and not ledger.exists() and not ledger.is_symlink(), "Fresh original request ledger required")
        self.token, self.release_id, self.ledger = token, release_id, ledger
        self.deadline = time.monotonic() + seconds
        self.opener = opener if opener is not None else urllib.request.build_opener(
            urllib.request.ProxyHandler({}), NoRedirect())
        fd = os.open(ledger, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        os.close(fd)

    def event(self, **value):
        # Callers supply fixed purpose labels, API paths and raw JSON only.
        # Tokens, request headers and signed redirect URLs are never supplied.
        with self.ledger.open("ab") as stream:
            stream.write(json.dumps(value, sort_keys=True, ensure_ascii=True, allow_nan=False).encode() + b"\n")
            stream.flush(); os.fsync(stream.fileno())

    def timeout(self):
        left = self.deadline - time.monotonic()
        require(left > 0, "The one-shot evidence network budget expired")
        return min(30, left)

    def headers(self, accept="application/vnd.github+json"):
        return {"Authorization": "Bearer " + self.token, "Accept": accept,
                "X-GitHub-Api-Version": "2022-11-28", "User-Agent": "HalalTag-evidence-only-v3"}

    def json_request(self, method, path, *, body_path=None, name=None):
        prefix = f"/repos/{REPOSITORY}/"
        read_paths = {f"{prefix}releases/{self.release_id}",
                      f"{prefix}releases/{self.release_id}/assets?per_page=100"}
        tag_prefix = prefix + "git/ref/tags/evidence/halaltag-r11-7ef009beb0c1-"
        if method == "GET":
            require(path in read_paths or (path.startswith(tag_prefix)
                    and re.fullmatch(r"[a-f0-9]{32}", path[len(tag_prefix):])), "Unreviewed API read route")
            require(body_path is None and name is None, "A read cannot carry an upload")
            url, data, expected_status = API + path, None, 200
        else:
            require(method == "POST" and path == f"{prefix}releases/{self.release_id}/assets"
                    and isinstance(name, str) and re.fullmatch(r"[A-Za-z0-9._-]{1,220}", name)
                    and body_path is not None, "Only one new named asset POST to the bound release is permitted")
            url = UPLOADS + path + "?name=" + urllib.parse.quote(name, safe="")
            data, expected_status = body_path, 201
        headers, fd, stream = self.headers(), None, None
        try:
            before = None
            if data is not None:
                before = file_record(data)
                fd = os.open(data, os.O_RDONLY | os.O_NOFOLLOW)
                stream = os.fdopen(fd, "rb"); fd = None
                headers.update({"Content-Type": "application/octet-stream", "Content-Length": str(before["bytes"])})
            self.event(status="STARTED", method=method, api_path=path, asset_name=name,
                       request_body=before, retry_count=0)
            request = urllib.request.Request(url, data=stream, headers=headers, method=method)
            try:
                response = self.opener.open(request, timeout=self.timeout())
            except urllib.error.HTTPError as error:
                response = error
            with response:
                code = response.getcode()
                raw = response.read(MAX_JSON + 1)
            require(len(raw) <= MAX_JSON, "GitHub JSON response exceeded the reviewed bound")
            self.event(status="RESPONSE", method=method, api_path=path, asset_name=name,
                       http_status=code, raw_body_base64=base64.b64encode(raw).decode())
            require(code == expected_status,
                    "GitHub returned an unexpected status; uncertain or duplicate uploads are never retried or deleted")
            if before is not None:
                require(file_record(body_path) == before, "Original upload input changed")
            return strict_json(raw)
        except Exception as error:
            self.event(status="FAILED", method=method, api_path=path, asset_name=name,
                       error_type=type(error).__name__, retry_count=0)
            # Network exception strings can contain secret signed URLs. Do not print them.
            raise ValueError("One-shot GitHub evidence request failed: " + type(error).__name__) from None
        finally:
            if stream is not None:
                stream.close()
            if fd is not None:
                os.close(fd)

    def release(self):
        return self.json_request("GET", f"/repos/{REPOSITORY}/releases/{self.release_id}")

    def tag(self, tag):
        return self.json_request("GET", f"/repos/{REPOSITORY}/git/ref/tags/" + tag)

    def assets(self):
        result = self.json_request("GET", f"/repos/{REPOSITORY}/releases/{self.release_id}/assets?per_page=100")
        require(isinstance(result, list) and len(result) < 100
                and len({x.get("id") for x in result}) == len(result), "Incomplete or duplicate release asset list")
        return result

    def upload(self, path, name, *, expected, maximum_bytes):
        require(type(maximum_bytes) is int and 0 < expected["bytes"] <= maximum_bytes < 2**31,
                "Complete asset exceeds its approved limit")
        require(file_record(path) == expected, "Upload differs from the exact reviewed complete file")
        asset = self.json_request("POST", f"/repos/{REPOSITORY}/releases/{self.release_id}/assets", body_path=path, name=name)
        check_asset(asset, name=name, expected=expected, release_id=self.release_id)
        return asset

    def download(self, asset, destination, *, expected, maximum_bytes):
        require(type(maximum_bytes) is int and 0 < expected["bytes"] <= maximum_bytes < 2**31,
                "Download is outside the exact complete-asset bound")
        require(type(asset.get("id")) is int and asset["id"] > 0, "Unbound download asset")
        require(isinstance(destination, Path) and destination.is_absolute()
                and destination.parent.resolve() == destination.parent
                and not os.path.lexists(destination), "A fresh unaliased download destination is required")
        path = f"/repos/{REPOSITORY}/releases/assets/{asset['id']}"
        require(asset.get("url") == API + path, "Download asset belongs to a different API")
        self.event(status="DOWNLOAD_STARTED", asset_id=asset["id"], expected=expected, retry_count=0)
        response, fd = None, None
        try:
            request = urllib.request.Request(API + path, headers=self.headers("application/octet-stream"), method="GET")
            try:
                response = self.opener.open(request, timeout=self.timeout())
            except urllib.error.HTTPError as error:
                response = error
            code = response.getcode()
            if code == 302:
                location = response.headers.get("Location", "")
                response.close(); response = None
                parsed = urllib.parse.urlsplit(location)
                require(parsed.scheme == "https" and parsed.hostname in CDN_HOSTS
                        and parsed.port in (None, 443) and parsed.username is None and parsed.password is None
                        and not parsed.fragment, "GitHub returned an unsupported asset redirect")
                self.event(status="SIGNED_CDN_REDIRECT", asset_id=asset["id"],
                           destination_host=parsed.hostname, authorization_forwarded=False)
                # Build a new request with no Authorization, cookies or API headers.
                request = urllib.request.Request(location, headers={"User-Agent": "HalalTag-evidence-only-v3"}, method="GET")
                try:
                    response = self.opener.open(request, timeout=self.timeout())
                except urllib.error.HTTPError as error:
                    response = error
                code = response.getcode()
            require(code == 200, "Asset download did not return a complete binary response")
            length = response.headers.get("Content-Length")
            if length is not None:
                require(length.isdecimal() and int(length) == expected["bytes"], "Download length header differs")
            fd = os.open(destination, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
            digest, count = hashlib.sha256(), 0
            with os.fdopen(fd, "wb") as output:
                fd = None
                while True:
                    self.timeout()
                    block = response.read(min(CHUNK, expected["bytes"] - count + 1))
                    if not block:
                        break
                    count += len(block)
                    require(count <= expected["bytes"], "Download exceeds the exact original length")
                    output.write(block); digest.update(block)
                output.flush(); os.fsync(output.fileno())
            actual = {"bytes": count, "sha256": digest.hexdigest()}
            require(actual == expected and file_record(destination) == expected, "Downloaded original bytes differ")
            self.event(status="DOWNLOAD_VERIFIED", asset_id=asset["id"], actual=actual)
            return actual
        except Exception as error:
            self.event(status="DOWNLOAD_FAILED", asset_id=asset["id"], error_type=type(error).__name__, retry_count=0)
            raise ValueError("One-shot GitHub evidence download failed: " + type(error).__name__) from None
        finally:
            if response is not None:
                response.close()
            if fd is not None:
                os.close(fd)
