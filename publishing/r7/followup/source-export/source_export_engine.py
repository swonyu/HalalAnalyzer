#!/usr/bin/env python3
"""Prepare byte-exact, screened Git-tree reading packages; never upload or build.

Default repositories and output are the coordinator's explicitly designated Mac
paths. --scan-only --cloud-repositories is a read-only preparation mode; it does
not replace the Mac export receipt. All outputs use exclusive creation.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import re
import runpy
import subprocess
import sys
import zipfile

HERE = Path(__file__).resolve().parent
MAC_REPOS = Path('/Users/saleh/Library/Caches/Publishing-Continuation-20261117-d597fc87411f/Recovery-d57f4cd77813/GitCheckpoint')
MAC_OUTPUT = Path('/Users/saleh/Library/Caches/Grok-Full-App-Review-20261117-d57f4-Updated')
APPS = [
    dict(app='Lumina', slug='lumina', commit='add412734658eef9aece0ec19618841f00ecc2c9', tree='bd24617458da59c202aeec45bb080fc57817b7b5', count=174, bytes=3351378,
         baseline_commit='079aeb0d150111e9ba09239eb6cb7c428ef0c179'),
    dict(app='HalalTag', slug='halaltag', commit='aa7f756e6c4bb5441e6945e4454141756934252f', tree='62a2cde8d544471171a8d405c920a59a3ba30afe', count=87, bytes=1164247,
         baseline_commit='4633d6d6179f194bdc3d7b74b01041aca360f598'),
    dict(app='CareerFinder', slug='career', commit='56784d740a25d07d2fbd4616f57e55cf0cb4453f', tree='6bcbd5f218cb4785407892130fee9e9688b768d5', count=1268, bytes=36124786,
         baseline_commit='842472684b194e993355f632902ccc81366c164c'),
]

TOKEN_PATTERNS = {
    'private_key_pem': r'-----BEGIN (?:RSA |EC |OPENSSH |DSA |ENCRYPTED )?PRIVATE KEY-----',
    'github_token': r'\b(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{60,})\b',
    'aws_access_key': r'\b(?:AKIA|ASIA)[0-9A-Z]{16}\b',
    'provider_api_key': r'\b(?:sk-(?:proj-|ant-api03-)?[A-Za-z0-9_-]{24,}|xai-[A-Za-z0-9_-]{24,}|AIza[0-9A-Za-z_-]{30,})\b',
    'stripe_live_key': r'\b(?:sk|rk)_live_[0-9A-Za-z]{16,}\b',
    'slack_token': r'\bxox[baprs]-[A-Za-z0-9-]{20,}\b',
    'jwt_literal': r'\beyJ[A-Za-z0-9_-]{8,}\.eyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{16,}\b',
    'credential_url': r'''https?://[^\s/:@"'<>]+:[^\s/@"'<>]{3,}@''',
    'signed_cloud_url': r'(?:X-Amz-Signature|X-Goog-Signature|SharedAccessSignature)=+[A-Za-z0-9%+/=_-]{16,}',
    'connection_account_key': r'AccountKey=[A-Za-z0-9+/=]{32,}',
}
RULES = {k: re.compile(v) for k, v in TOKEN_PATTERNS.items()}
ASSIGNMENT = re.compile(r'''(?i)\b(?:api[_-]?key|access[_-]?token|auth[_-]?token|client[_-]?secret|private[_-]?key|secret[_-]?key|password)["']?\s*[:=]\s*["']([^"'\r\n]{6,})["']''')
EMAIL = re.compile(r'(?<![\w.-])[A-Za-z0-9.!#$%&*+/=?^_{}|~-]+@([A-Za-z0-9](?:[A-Za-z0-9.-]*[A-Za-z0-9])?\.[A-Za-z]{2,})(?![\w.-])')
PHONE = re.compile(r'''(?i)\b(?:phone|mobile|telephone)["']?\s*[:=]\s*["'](\+?[0-9][0-9 ()-]{7,}[0-9])["']''')
LOCAL_PATH = re.compile(r'''/(?:Users|home)/[^/\s"'<>]+''')
SENSITIVE_NAME = re.compile(r'(^|/)(?:\.env(?:\.(?!example$|sample$|template$)[^/]+)?|id_rsa|id_ed25519|credentials(?:\.json)?|service-account[^/]*\.json)$|\.(?:p12|p8|pem|key|mobileprovision|keystore|jks)$', re.I)
SAFE_CATEGORIES = {'reserved_domain_example', 'local_provenance_path', 'asset_filename_email_false_positive'}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def json_bytes(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + '\n').encode('utf-8')


def save_json(path, value):
    with path.open('xb') as f:
        f.write(json_bytes(value))


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def git(repo, *args):
    # Never run a shell, fetch, checkout, build, hook, or mutable Git operation.
    return subprocess.check_output(['git', '--git-dir=' + str(repo), *args], stderr=subprocess.PIPE)


def safe_path(path):
    parts = PurePosixPath(path).parts
    return bool(parts) and not path.startswith('/') and '..' not in parts and '.git' not in parts and '\\' not in path and '\x00' not in path


def tree_entries(repo, commit):
    entries = []
    for raw in git(repo, 'ls-tree', '-rz', '-l', commit).split(b'\0'):
        if not raw:
            continue
        meta, name = raw.split(b'\t', 1)
        mode, kind, oid, size = meta.decode('ascii').split()
        path = name.decode('utf-8')
        require(kind == 'blob' and mode in ('100644', '100755'), 'Nonregular tracked entry: ' + path)
        require(safe_path(path), 'Unsafe tracked path: ' + path)
        entries.append(dict(path=path, git_mode=mode, git_blob_sha1=oid, bytes=int(size)))
    require(len(entries) == len({e['path'] for e in entries}), 'Duplicate tracked paths')
    return entries


def batch_blobs(repo, entries):
    objects = list(dict.fromkeys(e['git_blob_sha1'] for e in entries))
    result = subprocess.run(['git', '--git-dir=' + str(repo), 'cat-file', '--batch'],
                            input=('\n'.join(objects) + '\n').encode('ascii'),
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
    stream = io.BytesIO(result.stdout)
    blobs = {}
    for expected in objects:
        header = stream.readline().decode('ascii').strip().split()
        require(len(header) == 3 and header[:2] == [expected, 'blob'], 'Git blob response mismatch')
        data = stream.read(int(header[2]))
        require(stream.read(1) == b'\n', 'Git blob separator mismatch')
        require(hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest() == expected, 'Git blob hash mismatch')
        blobs[expected] = data
    require(stream.read() == b'', 'Unexpected trailing Git blob output')
    return blobs


def utf8(data):
    try:
        text = data.decode('utf-8')
        return text if '\x00' not in text else None
    except UnicodeDecodeError:
        return None


def sample_marker(value):
    return any(x in value.lower() for x in ('example', 'placeholder', 'your_', 'your-', 'sample', 'dummy', 'test-', 'test_', 'fixture', 'fake', 'replace_me', 'changeme')) or value.lower() in ('password', 'password123', 'not-a-real-key') or '${' in value


def scan_content(path, data, parent_sha=None):
    findings = []
    text = utf8(data)
    content = text if text is not None else data.decode('latin1')
    digest = sha(data)

    def add(kind, category, match=None, value=None):
        finding = dict(path=path, content_sha256=digest, kind=kind, category=category,
                       byte_or_character_offset=match.start() if match else None,
                       line=content.count('\n', 0, match.start()) + 1 if match else None,
                       strict_utf8=text is not None)
        if parent_sha:
            finding['outer_blob_sha256'] = parent_sha
        if value is not None:
            finding['sample_marker_present'] = sample_marker(value)
            finding['matched_character_count'] = len(value)
        finding['id'] = sha(json_bytes(finding))
        findings.append(finding)

    for kind, pattern in RULES.items():
        for match in pattern.finditer(content):
            add(kind, 'credential_candidate', match, match.group())
    # Contact/assignment scans operate on real text, not random decoded pixel bytes.
    if text is not None:
        for match in ASSIGNMENT.finditer(text):
            value = match.group(1)
            if re.fullmatch(r'[A-Z][A-Z0-9_]+', value) or value.startswith(('process.env.', 'os.environ', 'Bundle.main')):
                continue
            add('quoted_credential_assignment', 'credential_candidate', match, value)
        for match in EMAIL.finditer(text):
            domain = match.group(1).lower()
            category = 'contact_email_candidate'
            if domain in ('example.com', 'example.org', 'example.net', 'localhost.localdomain') or domain.endswith(('.example.com', '.example.org', '.example.net', '.invalid', '.example', '.test', '.localhost')):
                category = 'reserved_domain_example'
            elif re.search(r'@\d+x\.(?:png|jpg|jpeg|webp)$', match.group(), re.I):
                category = 'asset_filename_email_false_positive'
            add('email_address', category, match)
        for match in PHONE.finditer(text):
            add('phone_literal', 'contact_phone_candidate', match, match.group(1))
        for match in LOCAL_PATH.finditer(text):
            add('local_user_path', 'local_provenance_path', match)
    if SENSITIVE_NAME.search(path):
        add('credential_capable_filename', 'credential_file_review')
    if data.startswith(b'version https://git-lfs.github.com/spec/v1'):
        add('git_lfs_pointer', 'external_asset_dependency')
    return findings


def nested_scan(path, data):
    if PurePosixPath(path).suffix.lower() not in ('.zip', '.jar'):
        return [], None
    findings, members = [], []
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        infos = archive.infolist()
        require(len(infos) <= 5000 and sum(i.file_size for i in infos) <= 64 * 1024 * 1024, 'Nested archive scan budget exceeded: ' + path)
        require(len(infos) == len({i.filename for i in infos}), 'Duplicate nested archive members: ' + path)
        for info in infos:
            require(safe_path(info.filename) and not info.flag_bits & 1, 'Unsafe/encrypted nested archive member: ' + path)
            if info.is_dir():
                continue
            member = archive.read(info)
            member_path = path + '::' + info.filename
            members.append(dict(path=info.filename, bytes=len(member), sha256=sha(member), utf8_text=utf8(member) is not None))
            findings.extend(scan_content(member_path, member, parent_sha=sha(data)))
            require(PurePosixPath(info.filename).suffix.lower() not in ('.zip', '.jar'), 'Recursive archive requires explicit review: ' + member_path)
    return findings, dict(path=path, sha256=sha(data), member_count=len(members), total_member_bytes=sum(m['bytes'] for m in members), members=members)


def inspect_app(app, repo):
    require(git(repo, 'cat-file', '-t', app['commit']).strip() == b'commit', 'Pinned commit missing: ' + app['app'])
    require(git(repo, 'rev-parse', app['commit'] + '^{tree}').decode().strip() == app['tree'], 'Pinned tree mismatch: ' + app['app'])
    entries = tree_entries(repo, app['commit'])
    require(len(entries) == app['count'] and sum(e['bytes'] for e in entries) == app['bytes'], 'Pinned inventory mismatch: ' + app['app'])
    old_oids = {e['git_blob_sha1'] for e in tree_entries(repo, app['baseline_commit'])}
    blobs = batch_blobs(repo, entries)
    findings, nested = [], []
    for e in entries:
        data = blobs[e['git_blob_sha1']]
        require(len(data) == e['bytes'], 'Blob length mismatch: ' + e['path'])
        e['sha256'] = sha(data)
        e['utf8_text'] = utf8(data) is not None
        e['same_blob_as_baseline_tree'] = e['git_blob_sha1'] in old_oids
        findings.extend(scan_content(e['path'], data))
        extra, info = nested_scan(e['path'], data)
        findings.extend(extra)
        if info:
            nested.append(info)
    findings.sort(key=lambda x: (x['path'], x['line'] or 0, x['kind'], x['id']))
    result = dict(app=app['app'], commit=app['commit'], tree=app['tree'], tracked_files=len(entries),
                  tracked_bytes=sum(e['bytes'] for e in entries), utf8_text_files=sum(e['utf8_text'] for e in entries),
                  files=entries, nested_archives=nested, findings=findings, category_counts=dict(Counter(f['category'] for f in findings)))
    result['screening_digest'] = sha(json_bytes(result))
    return result, blobs


def validate_review(reports, review):
    require(review.get('schema_version') == 1, 'Unsupported review ledger')
    require(review.get('decision') == 'APPROPRIATE_FOR_AUTHORIZED_GROK_REVIEW', 'Review ledger not ready')
    for report in reports:
        item = review['apps'][report['app']]
        require(item['commit'] == report['commit'] and item['screening_digest'] == report['screening_digest'], 'Review ledger differs from exact scanned bytes: ' + report['app'])
        required = {f['id'] for f in report['findings'] if f['category'] not in SAFE_CATEGORIES}
        dispositions = item['candidate_dispositions']
        require(required == set(dispositions), 'Missing or unexpected candidate disposition: ' + report['app'])
        require(all(d.get('decision') == 'SAFE_CONTEXT_CONFIRMED' and len(d.get('reason', '')) >= 20 for d in dispositions.values()), 'Unresolved screening finding: ' + report['app'])
        new_binary = {e['path']: e['sha256'] for e in report['files'] if not e['utf8_text'] and not e['same_blob_as_baseline_tree']}
        visuals = item['new_binary_review']
        require(set(new_binary) == set(visuals), 'Missing new binary review: ' + report['app'])
        for path, digest in new_binary.items():
            require(visuals[path].get('sha256') == digest and visuals[path].get('decision') == 'SAFE_CONTEXT_CONFIRMED', 'New binary review mismatch: ' + path)


def export_app(app, repo, report, blobs, out):
    name = app['app'] + '-' + app['commit'][:8] + '-complete-source'
    prefix = app['app'] + '-' + app['commit'][:8] + '/'
    archive_path, pack_path = out / (name + '.zip'), out / (name + '.txt')
    manifest_path, scan_path = out / (name + '-manifest.json'), out / (name + '-scan.json')
    with archive_path.open('xb') as f:
        subprocess.run(['git', '--git-dir=' + str(repo), 'archive', '--format=zip', '--prefix=' + prefix, app['commit']], stdout=f, stderr=subprocess.PIPE, check=True)
    entries = [dict(e) for e in report['files']]
    with zipfile.ZipFile(archive_path) as archive:
        paths = [i.filename[len(prefix):] for i in archive.infolist() if not i.is_dir()]
        require(len(paths) == len(set(paths)) and set(paths) == {e['path'] for e in entries}, 'Git archive omitted/added/duplicated a tracked path')
        require(archive.comment.decode('ascii') == app['commit'], 'Archive commit comment mismatch')
        for e in entries:
            require(archive.read(prefix + e['path']) == blobs[e['git_blob_sha1']], 'Git archive changed original bytes: ' + e['path'])
            e['archive_member'] = prefix + e['path']
    with pack_path.open('xb') as f:
        header = (app['app'] + ' COMPLETE TRACKED UTF-8 SOURCE READING PACK\n'
                  + 'Git commit: ' + app['commit'] + '\nGit tree: ' + app['tree'] + '\n'
                  + 'Tracked files in companion ZIP: ' + str(len(entries)) + '\n'
                  + 'UTF-8 text files reproduced byte-exact below: ' + str(report['utf8_text_files']) + '\n'
                  + 'All binary/non-UTF-8 files are unchanged in the ZIP and fully indexed in the manifest.\n'
                  + 'No tracked file is omitted or redacted. .git history, untracked work, installed dependencies and external assets are outside this Git-tree snapshot.\n'
                  + 'Source export is not native acceptance, signed upload, store review, or public release. See the separate versioned UI audit and current-state notes.\n\n')
        f.write(header.encode('utf-8'))
        for e in entries:
            if not e['utf8_text']:
                continue
            f.write(('===== BEGIN TRACKED FILE =====\nPath: ' + json.dumps(e['path'], ensure_ascii=False) + '\nGit mode: ' + e['git_mode'] + '\nGit blob SHA1: ' + e['git_blob_sha1'] + '\nSHA256: ' + e['sha256'] + '\nOriginal UTF-8 bytes: ' + str(e['bytes']) + '\n===== ORIGINAL CONTENT =====\n').encode('utf-8'))
            e['reading_pack_content_byte_offset'] = f.tell()
            e['reading_pack_content_byte_length'] = e['bytes']
            f.write(blobs[e['git_blob_sha1']])
            f.write(('\n===== END TRACKED FILE ' + json.dumps(e['path'], ensure_ascii=False) + ' =====\n\n').encode('utf-8'))
    with pack_path.open('rb') as f:
        for e in entries:
            if e['utf8_text']:
                f.seek(e['reading_pack_content_byte_offset'])
                require(sha(f.read(e['bytes'])) == e['sha256'], 'Reading pack byte range mismatch')
    # A complete large TXT remains available. These exact consecutive byte ranges
    # support the observed Grok per-message capacity limit without dropping files.
    pack_bytes = pack_path.read_bytes()
    batches_dir = out / (name + '-reading-batches')
    batches_dir.mkdir()
    batches, start = [], 0
    while start < len(pack_bytes):
        end = min(start + 128 * 1024, len(pack_bytes))
        if end < len(pack_bytes):
            newline = pack_bytes.rfind(b'\n', start + 96 * 1024, end)
            if newline >= 0:
                end = newline + 1
        while True:
            try:
                pack_bytes[start:end].decode('utf-8')
                break
            except UnicodeDecodeError:
                end -= 1
                require(end > start, 'Unable to make a valid UTF-8 reading batch')
        part = pack_bytes[start:end]
        filename = name + '.part-' + str(len(batches) + 1).zfill(3) + '.txt'
        with (batches_dir / filename).open('xb') as f:
            f.write(part)
        affected = [e['path'] for e in entries if e['utf8_text']
                    and e['reading_pack_content_byte_offset'] < end
                    and e['reading_pack_content_byte_offset'] + e['bytes'] > start]
        batches.append(dict(file=filename, full_pack_byte_offset=start, bytes=len(part), sha256=sha(part), intersecting_source_paths=affected))
        start = end
    require(b''.join((batches_dir / item['file']).read_bytes() for item in batches) == pack_bytes,
            'Reading batches do not reconstruct the entire complete TXT')
    save_json(batches_dir / 'READING-BATCH-INDEX.json', dict(app=app['app'], commit=app['commit'],
              complete_reading_pack=pack_path.name, complete_reading_pack_sha256=sha(pack_bytes),
              complete_reading_pack_bytes=len(pack_bytes), maximum_part_bytes=128 * 1024,
              byte_exact_concatenation_verified=True, chunks_may_split_files=True,
              instructions='Start with one part per reading request. Use the offsets/path intersections to track coverage; these are consecutive complete-TXT bytes, not a selected-source substitute.', parts=batches))
    reading_zip = out / (name + '-reading-pack.zip')
    with zipfile.ZipFile(reading_zip, 'x', compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        archive.write(pack_path, pack_path.name)
        for path in sorted(batches_dir.iterdir()):
            archive.write(path, 'reading-batches/' + path.name)
    with zipfile.ZipFile(reading_zip) as archive:
        require(archive.read(pack_path.name) == pack_bytes, 'Compressed complete TXT mismatch')
        require(len(archive.namelist()) == len(batches) + 2, 'Reading pack ZIP membership mismatch')
        for item in batches:
            require(sha(archive.read('reading-batches/' + item['file'])) == item['sha256'], 'Compressed reading batch mismatch')
    save_json(scan_path, {k: v for k, v in report.items() if k != 'files'})
    manifest = dict(schema_version=2, app=app['app'], commit=app['commit'], tree=app['tree'],
                    tracked_file_count=len(entries), utf8_text_file_count=report['utf8_text_files'],
                    binary_or_nontext_file_count=len(entries) - report['utf8_text_files'],
                    tracked_file_bytes=report['tracked_bytes'], complete_archive_membership_verified=True,
                    every_git_blob_hash_verified=True, every_text_pack_byte_range_verified=True,
                    automatic_redaction_performed=False, omitted_tracked_paths=[], files=entries,
                    archive=dict(name=archive_path.name, bytes=archive_path.stat().st_size, sha256=sha(archive_path.read_bytes())),
                    reading_pack=dict(name=pack_path.name, bytes=pack_path.stat().st_size, sha256=sha(pack_path.read_bytes()), rule='Strict UTF-8 without NUL; original text bytes are preserved.'),
                    bounded_reading=dict(zip=reading_zip.name, sha256=sha(reading_zip.read_bytes()), bytes=reading_zip.stat().st_size,
                                         index=(batches_dir/'READING-BATCH-INDEX.json').relative_to(out).as_posix(), parts=len(batches), maximum_part_bytes=128 * 1024),
                    scan_report=dict(name=scan_path.name, sha256=sha(scan_path.read_bytes())))
    save_json(manifest_path, manifest)
    return dict(app=app['app'], commit=app['commit'], tree=app['tree'], tracked_files=len(entries), utf8_text_files=report['utf8_text_files'],
                archive=manifest['archive'], reading_pack=manifest['reading_pack'],
                bounded_reading=manifest['bounded_reading'],
                manifest=dict(name=manifest_path.name, sha256=sha(manifest_path.read_bytes())), scan_report=manifest['scan_report'])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=MAC_OUTPUT)
    parser.add_argument('--scan-only', action='store_true')
    parser.add_argument('--cloud-repositories', type=Path, help='Preparation only: existing cloud repo root; requires --scan-only')
    parser.add_argument('--review-ledger', type=Path, default=HERE / 'screened-review-ledger.json')
    args = parser.parse_args()
    require(not args.cloud_repositories or args.scan_only, 'Cloud override only permits read-only scan preparation')
    require(not args.output.exists(), 'Preserve existing destination; use a new output directory')
    if not args.scan_only:
        require(sys.platform == 'darwin', 'Full export is intended for the Mac coordinator; this cloud task prepares only')
    reports, materials, repos = [], {}, {}
    for app in APPS:
        repo = args.cloud_repositories / app['slug'] / '.git' if args.cloud_repositories else MAC_REPOS / (app['slug'] + '.git')
        report, blobs = inspect_app(app, repo)
        reports.append(report)
        materials[app['app']] = blobs
        repos[app['app']] = repo
    if not args.scan_only:
        review = json.loads(args.review_ledger.read_text())
        validate_review(reports, review)
    args.output.mkdir(parents=True, exist_ok=False)
    save_json(args.output / 'exact-tree-screening.json', dict(schema_version=1, method='All tracked bytes, recognizable literal credentials, text contacts, sensitive filenames, and all ZIP/JAR members. Candidate values/snippets are withheld.',
              limitations='Heuristic screening cannot prove absence of every secret/private fact. New binary images require separate hash-bound visual review before export; scan-only mode does not establish that review. Older binary bytes match the explicitly pinned baseline trees and were not all freshly visually re-reviewed. A matching baseline blob is not an upload receipt. No OCR or live-account access.', reports=reports))
    if args.scan_only:
        save_json(args.output / 'SCAN-ONLY-RECEIPT.json', dict(created_at_utc=datetime.now(timezone.utc).isoformat(), scan_only=True,
                  archives_created=False, source_edits=False, git_mutations=False, native_actions=False, external_transfer_performed=False,
                  apps=[dict(app=r['app'], commit=r['commit'], screening_digest=r['screening_digest'], tracked_files=r['tracked_files'], category_counts=r['category_counts']) for r in reports]))
        print(json.dumps(dict(scan_only=True, output=str(args.output), apps=[{k:r[k] for k in ('app','commit','tracked_files','utf8_text_files','category_counts')} for r in reports])))
        return
    (args.output / 'Source').mkdir()
    exports = [export_app(app, repos[app['app']], reports[i], materials[app['app']], args.output / 'Source') for i, app in enumerate(APPS)]
    # Copy only the explicit reviewed preparation documents, never arbitrary local files.
    support_names = ['00-READ-FIRST-INSTRUCTIONS.txt', 'UI-EVIDENCE-STATUS.json', 'UI-AUDIT-UPDATE.txt',
                     'screened-review-ledger.json', 'new-binary-visual-review.json', 'binary-supplemental-review.json',
                     'MAC-EXPORT-HANDOFF.txt', 'BATCH-REVIEW-REQUESTS.txt', 'export_complete_sources.py',
                     'assemble_actual_ui_audit.py', 'actual-ui-inputs.json', 'historical-image-provenance-v3.json',
                     'lumina-r13-nutrition-contrast-triage.json']
    supporting = []
    for name in support_names:
        path = args.review_ledger if name == 'screened-review-ledger.json' else HERE / name
        require(path.is_file(), 'Missing preparation document: ' + name)
        data = path.read_bytes()
        with (args.output / name).open('xb') as f:
            f.write(data)
        supporting.append(dict(name=name, sha256=sha(data), bytes=len(data)))
    audit = runpy.run_path(str(HERE / 'assemble_actual_ui_audit.py'))['assemble'](args.output)
    index = dict(created_at_utc=datetime.now(timezone.utc).isoformat(), exact_commits_pinned=True, complete_tracked_trees=True,
                 exports=exports, supporting_documents=supporting, screening_manifest_sha256=sha((args.output / 'exact-tree-screening.json').read_bytes()),
                 source_edits=False, git_mutations=False, native_actions=False, external_transfer_performed=False,
                 upload_status='NOT_ATTEMPTED', ui_audit_attachments='Separate versioned actual UI evidence must be attached by the coordinator; status/index documents alone are not the screenshots or an upload receipt.')
    index['actual_ui_audit'] = audit
    save_json(args.output / 'complete-source-export-index.json', index)
    upload_files = []
    for path in sorted(args.output.rglob('*')):
        if path.is_file():
            upload_files.append(dict(path=path.relative_to(args.output).as_posix(), bytes=path.stat().st_size, sha256=sha(path.read_bytes())))
    save_json(args.output / 'UPLOAD-MANIFEST-NOT-A-RECEIPT.json', dict(prepared_at_utc=datetime.now(timezone.utc).isoformat(), external_transfer_performed=False,
              status='PREPARED_ONLY_NOT_UPLOADED', files=upload_files,
              required_delivery_receipt=['existing Grok conversation identifier', 'exact attached filenames and hashes', 'observed submission and processing state', 'Grok acknowledgment of readable source and real UI attachments', 'date/time'],
              required_ui_evidence_refresh=True))
    print(json.dumps(dict(export_prepared=True, external_transfer_performed=False, output=str(args.output), apps=[dict(app=e['app'], commit=e['commit'], tracked_files=e['tracked_files']) for e in exports])))


if __name__ == '__main__':
    try:
        main()
    except (RuntimeError, subprocess.CalledProcessError, OSError, ValueError, KeyError, zipfile.BadZipFile) as error:
        # Never print command stderr, blobs or candidate values on failure.
        print(json.dumps(dict(status='STOPPED_WITHOUT_UPLOAD', reason=str(error)[:500], error_type=type(error).__name__)), file=sys.stderr)
        raise SystemExit(1)
