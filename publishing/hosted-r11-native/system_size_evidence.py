"""Pure system-size ownership, readback and original-artifact checks. No commands."""
from pathlib import Path
import hashlib
import json
import shutil

HELP_SHA256 = '2fa67269b4a75d4856edcaf9f65ed4bd830bd0ecae95e370173fa8ed2fe87084'
CASE_ORDER = ('dark-large', 'light-large', 'light-accessibility5')
CASE_SIZES = {'dark-large': 'large', 'light-large': 'large',
              'light-accessibility5': 'accessibility-extra-extra-extra-large'}
VALID_SIZES = frozenset(('extra-small', 'small', 'medium', 'large', 'extra-large',
    'extra-extra-large', 'extra-extra-extra-large', 'accessibility-medium',
    'accessibility-large', 'accessibility-extra-large', 'accessibility-extra-extra-large',
    'accessibility-extra-extra-extra-large'))

def require(ok, message):
    if not ok: raise ValueError(message)

def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()

def parse_content_size(text):
    require(isinstance(text, str), 'Content-size output is not text')
    for value in VALID_SIZES:
        if text in (value, value+'\n', value+'\r\n'):
            return value
    raise ValueError('Missing, unknown, unsupported or malformed actual system content-size output')

def owned_booted_device(value, *, simulator, name, runtime, preexisting, discovery_known):
    require(discovery_known is True and isinstance(simulator, str) and simulator
            and simulator not in preexisting, 'Simulator is not freshly owned by this run')
    devices = value.get('devices') if isinstance(value, dict) else None
    require(isinstance(devices, dict), 'Malformed current simulator inventory')
    rows = []
    for rt, group in devices.items():
        require(isinstance(group, list) and all(isinstance(d, dict) for d in group), 'Malformed device group')
        rows.extend((rt, d) for d in group if d.get('udid') == simulator or d.get('name') == name)
    require(len(rows) == 1, 'Owned simulator ID/name is missing or ambiguous')
    rt, device = rows[0]
    require(rt == runtime and device.get('udid') == simulator and device.get('name') == name
            and device.get('state') == 'Booted', 'Owned simulator identity/runtime/boot state differs')
    return device

def validate_system_hosts(hosts):
    require(set(hosts) == set(CASE_ORDER), 'Missing or extra actual host cases')
    for case, host in hosts.items():
        category = 'UICTContentSizeCategoryAccessibilityXXXL' if case == 'light-accessibility5' else 'UICTContentSizeCategoryL'
        require(host.get('content_size_source') == 'INHERITED_SYSTEM_SETTING'
                and host.get('application_content_size') == host.get('scene_content_size')
                == host.get('window_content_size') == host.get('host_content_size')
                == host.get('requested_content_size') == category,
                'Initial inherited application/scene/window/host category differs: '+case)

def validate_case_settings(receipts, *, run_id, simulator):
    require(isinstance(receipts, list) and [x.get('case_id') for x in receipts] == list(CASE_ORDER),
            'System-setting receipt case inventory differs')
    for row in receipts:
        desired = CASE_SIZES[row['case_id']]
        require(row.get('run_id') == run_id and row.get('device_id') == simulator
                and row.get('requested') == row.get('readback_before_test')
                == row.get('readback_after_test') == desired
                and row.get('set_command_status') == 'passed',
                'System setting was not exactly established and retained for the case')

def combine_original_attachments(case_folders, destination):
    """Retain original exports separately; make a hash-verified union for the unchanged guard."""
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
        require(isinstance(attachments, list) and len(attachments) <= 600, 'Unbounded attachment row')
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
