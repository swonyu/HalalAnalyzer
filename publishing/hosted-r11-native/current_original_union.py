"""NEW current-R11-scope union of complete original appearance exports.

This standalone pure helper is a narrow adaptation of the preserved legacy
union. It is not a recovered private support and does not patch that support.
No native, app, command, API, lock or upload operation is performed here.
"""
from pathlib import Path
import hashlib
import json
import shutil


CASE_ORDER = ('dark-large', 'light-large', 'light-accessibility5')


def require(ok, message):
    if not ok: raise ValueError(message)


def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()


def combine_original_attachments(case_folders, destination, *, attachment_limit):
    """Retain original exports separately; make a hash-verified union for the unchanged guard."""
    require(type(attachment_limit) is int and attachment_limit == 2944,
            'Only the exact current R11 attachment limit of 2944 is permitted')
    require(set(case_folders) == set(CASE_ORDER) and not destination.exists(), 'Unsafe aggregation destination/cases')
    destination.mkdir()
    rows, copied, bindings = [], set(), []
    total = 0
    for case in CASE_ORDER:
        folder = case_folders[case]
        manifest_path = folder/'manifest.json'
        require(manifest_path.is_file() and not manifest_path.is_symlink()
                and manifest_path.stat().st_size <= 2_000_000, 'Missing original case manifest')
        manifest = json.loads(manifest_path.read_text())
        require(isinstance(manifest, list) and len(manifest) == 1 and isinstance(manifest[0], dict),
                'Each original result must export exactly one test attachment row')
        attachments = manifest[0].get('attachments')
        require(isinstance(attachments, list) and len(attachments) <= attachment_limit, 'Unbounded attachment row')
        names = []
        case_files = []
        for item in attachments:
            name = item.get('exportedFileName') if isinstance(item, dict) else None
            require(isinstance(name, str) and name and Path(name).name == name and name not in copied
                    and name != 'manifest.json', 'Unsafe or duplicate original attachment name')
            source = folder/name
            require(source.is_file() and not source.is_symlink(), 'Missing or linked original attachment')
            total += source.stat().st_size
            require(total <= 750_000_000, 'Combined attachment bytes exceed the existing scope bound')
            digest = sha(source)
            target = destination/name
            shutil.copy2(source, target)
            require(sha(source) == sha(target) == digest, 'Original attachment changed during copy')
            copied.add(name); names.append(name)
            case_files.append({'name':name, 'bytes':source.stat().st_size, 'sha256':digest})
        require(len(names) == len(set(names)), 'Duplicate attachment inside a case')
        actual = list(folder.iterdir())
        require(all(p.is_file() and not p.is_symlink() for p in actual)
                and {p.name for p in actual} == set(names)|{'manifest.json'}, 'Extra or missing original export files')
        rows.extend(manifest)
        bindings.append({'case_id':case, 'original_manifest':str(manifest_path),
                         'original_manifest_sha256':sha(manifest_path), 'files':case_files})
    (destination/'manifest.json').write_text(json.dumps(rows, indent=2)+'\n')
    return {'status':'DERIVED_UNION_OF_EXACT_ORIGINAL_EXPORTS', 'original_results_replaced':False,
            'image_transformations':False, 'total_attachment_bytes':total,
            'union_manifest_sha256':sha(destination/'manifest.json'), 'cases':bindings}
