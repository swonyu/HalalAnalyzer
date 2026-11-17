"""Pure checks for three supplementary native cases. No commands or image transformations."""
from collections import defaultdict
import hashlib
import json
import math
from pathlib import Path

from appearance_png import inspect_png

CASE_TESTS = {
    'light-large': 'testLightAppearanceAndContrastJourney',
    'dark-large': 'testDarkAppearanceAndContrastJourney',
    'light-accessibility5': 'testMaximumTextReachabilityAndFocusedSampleReplacement',
}
TEST_CLASS = 'HalalTagAppearanceUITests'
APP_ID = 'com.saleh.halaltag.productioncomposition.qa.r20261117r7'
DEVICE_NAME = 'iPhone SE (3rd generation)'
DEVICE_TYPE = 'com.apple.CoreSimulator.SimDeviceType.iPhone-SE-3rd-generation'
MODEL = 'iPhone14,6'
RUNTIME = 'com.apple.CoreSimulator.SimRuntime.iOS-27-0'
RUNTIME_BUILD = '24A5423a'
MATCH_LABELS = [('matched-name', 'Pork-related terms'),
                ('matched-disposition', 'Flagged term — verify the label'),
                ('matched-text', 'Matched text: pork'),
                ('matched-explanation', 'Verify what the label refers to and obtain ingredient-origin information from the manufacturer or a qualified certifier.')]
READ_KEYS = {'entry-scope', 'coverage'} | {key for key, _ in MATCH_LABELS}

REQUIRED_POSES = {'entry', 'keyboard', 'flagged-result', 'entry-scope', 'matched-explanation',
                  'coverage', 'privacy-action', 'privacy-sheet', 'privacy-section', 'unknown-result', 'completed'}
REQUIRED_AUDITS = {'entry', 'flagged-result', 'entry-scope', 'matched-explanation', 'coverage',
                   'privacy-action', 'privacy-sheet', 'unknown-result',
                   'privacy-section-What this screen does', 'privacy-section-What a result means',
                   'privacy-section-Your text and privacy', 'privacy-section-Language and coverage'}
REQUIRED_POSES |= {key for key, _ in MATCH_LABELS}
REQUIRED_AUDITS |= {key for key, _ in MATCH_LABELS}
ONLINE_LINKS = [('privacy-online-link', 'Read the privacy policy online'), ('support-online-link', 'Open support instructions')]
REQUIRED_POSES |= {key for key, _ in ONLINE_LINKS}
REQUIRED_AUDITS |= {key for key, _ in ONLINE_LINKS}
EXPECTED_ACTIONS = ['screen', 'open-privacy', 'close-privacy', 'clear-result',
                    'replace-with-unknown-sample', 'clear-sample']

def require(ok, message):
    if not ok: raise ValueError(message)

def number(value): return type(value) in (int, float) and math.isfinite(value)

def read_json(path, maximum=2_000_000):
    require(path.is_file() and not path.is_symlink() and path.stat().st_size <= maximum, 'Missing, linked or oversized JSON: ' + str(path))
    return json.loads(path.read_text())

def frame(value, size=(375, 667)):
    require(isinstance(value, dict) and set(value) == {'x', 'y', 'width', 'height'} and all(number(v) for v in value.values()), 'Malformed native frame')
    require([value[k] for k in ('x', 'y', 'width', 'height')] == [0, 0, *size], 'Native full-screen geometry differs from pinned SE')

def validate_discovery(types, runtimes):
    found = [x for x in types.get('devicetypes', []) if x.get('name') == DEVICE_NAME]
    require(len(found) == 1 and found[0].get('identifier') == DEVICE_TYPE and found[0].get('modelIdentifier') == MODEL and found[0].get('productFamily') == 'iPhone', 'The pinned compact iPhone type was not freshly found')
    runtime = [x for x in runtimes.get('runtimes', []) if x.get('identifier') == RUNTIME]
    require(len(runtime) == 1 and runtime[0].get('isAvailable') is True and runtime[0].get('buildversion') == RUNTIME_BUILD and runtime[0].get('version') == '27.0', 'The pinned installed runtime/build is unavailable')
    return {'device': found[0], 'runtime': runtime[0]}

def validate_host(folder, run_id):
    actual = sorted(p.relative_to(folder).as_posix() for p in folder.rglob('*') if p.is_file())
    require(actual == sorted(case + '/started.json' for case in CASE_TESTS), 'Expected exactly three actual native host receipts')
    rows = {}
    for case in CASE_TESTS:
        value = read_json(folder / case / 'started.json', 32_000)
        require(value.get('schema_version') == 1 and value.get('run_id') == run_id and value.get('case_id') == case and value.get('bundle_id') == APP_ID, 'Host run/case/app identity mismatch')
        style = 2 if case == 'dark-large' else 1
        category = 'UICTContentSizeCategoryAccessibilityXXXL' if case == 'light-accessibility5' else 'UICTContentSizeCategoryL'
        require(all(value.get(k) == style for k in ('requested_style', 'window_style', 'host_style')), 'Requested appearance was not resolved by the actual window and host')
        require(all(value.get(k) == category for k in ('requested_content_size', 'window_content_size', 'host_content_size')), 'Requested Dynamic Type was not resolved by the actual window and host')
        for key in ('screen_bounds', 'scene_bounds', 'window_frame', 'host_frame'): frame(value.get(key))
        frame(value.get('screen_native_bounds'), (750, 1334))
        require(value.get('screen_scale') == value.get('screen_native_scale') == 2 and value.get('orientation') == 1, 'Actual SE scale/orientation mismatch')
        require(value.get('artificial_window_resize') is False and value.get('fixed_inner_container') is False, 'Unreviewed resized content/window')
        rows[case] = value
    return rows

GEOMETRY_POLICY = 'R7_MEASURED_DISTANCE_AND_SEPARATE_AUDIT_RECOVERY'
# Explicit replacement for R6b's 4/8/40 policy, from the preserved R6b geometry.
CASE_GESTURE_LIMIT = math.ceil((2 * 4406.5 + 9152.5) / (.40 * 463)) + 2 * 17 + 12 * math.ceil(523 / (.40 * 463))
CAPTURE_LIMIT = 2 * CASE_GESTURE_LIMIT + 64
ATTACHMENT_LIMIT = 8 * CASE_GESTURE_LIMIT + 4 * CAPTURE_LIMIT


def measured_rect(value):
    require(isinstance(value, dict) and set(value) == {'x', 'y', 'width', 'height'} and
            all(number(v) for v in value.values()) and value['width'] > 0 and value['height'] > 0,
            'Invalid positive native rectangle')
    return value


def contains(outer, inner, tolerance=0):
    return (inner['x'] >= outer['x'] - tolerance and inner['y'] >= outer['y'] - tolerance and
            inner['x'] + inner['width'] <= outer['x'] + outer['width'] + tolerance and
            inner['y'] + inner['height'] <= outer['y'] + outer['height'] + tolerance)


def intersects(left, right):
    return (left['x'] < right['x'] + right['width'] and left['x'] + left['width'] > right['x'] and
            left['y'] < right['y'] + right['height'] and left['y'] + left['height'] > right['y'])


def same_size(left, right):
    return abs(left['width'] - right['width']) <= 2 and abs(left['height'] - right['height']) <= 2


def same_frame(left, right):
    return all(abs(left[key] - right[key]) <= 2 for key in ('x', 'y', 'width', 'height'))


def validate_gesture_budgets(value, captures):
    require(value.get('geometry_policy') == GEOMETRY_POLICY and
            value.get('case_gesture_limit') == CASE_GESTURE_LIMIT == 168,
            'Missing exact measured-distance/recovery policy')
    budgets, gestures = value.get('gesture_budgets'), value.get('gestures')
    require(isinstance(budgets, list) and 1 <= len(budgets) <= 100,
            'Missing or unbounded operation budgets')
    require(isinstance(gestures, list) and value.get('gesture_count') == len(gestures) <= CASE_GESTURE_LIMIT,
            'Invalid bounded gesture inventory')
    by_budget = defaultdict(list)
    for index, event in enumerate(gestures, 1):
        require(event.get('index') == index and event.get('direction') in (-1, 1),
                'Gesture identity/direction mismatch')
        bid = event.get('budget_id')
        require(type(bid) is int and 0 <= bid < len(budgets), 'Unaccounted gesture budget')
        before, after, viewport = (measured_rect(event.get(k)) for k in ('before', 'after', 'viewport'))
        require(event['direction'] * (after['y'] - before['y']) > 1 and same_size(before, after),
                'Gesture lacks actual directional progress or changes target geometry')
        travel = event.get('requested_travel')
        require(number(travel) and 12 <= travel <= .56 * viewport['height'] + .001,
                'Gesture travel exceeds the measured viewport route')
        route = measured_rect(event.get('route'))
        require(contains(viewport, route) and abs(route['height'] - travel) <= .001 and route['width'] == 4,
                'Gesture route is not inside the actual viewport')
        for key in ('editor_frames', 'indicator_frames'):
            require(isinstance(event.get(key), list), 'Missing native occluder inventory')
            require(all(not intersects(route, measured_rect(r)) for r in event[key]),
                    'Gesture route intersects an editor or native scroll indicator')
        for key, pose in [('before_capture_index', 'before-gesture'), ('after_capture_index', 'after-gesture')]:
            capture = event.get(key)
            require(type(capture) is int and 1 <= capture <= len(captures) and captures[capture - 1]['pose'] == pose,
                    'Real gesture lacks its original before/after capture')
        require(event['after_capture_index'] == event['before_capture_index'] + 1,
                'Real gesture capture pair is not consecutive')
        by_budget[bid].append(event)
    for bid, budget in enumerate(budgets):
        require(budget.get('id') == bid and budget.get('kind') in ('reveal', 'read', 'audit-recovery') and
                isinstance(budget.get('key'), str) and budget['key'] and budget.get('complete') is True,
                'Operation budget is missing, unfinished or has an invalid identity')
        frame, viewport = measured_rect(budget.get('initial_frame')), measured_rect(budget.get('initial_viewport'))
        require(viewport['height'] > 80 and viewport['width'] > 100, 'Invalid measured operation viewport')
        if budget['kind'] == 'reveal':
            distance = max(0, frame['y'] + frame['height'] - viewport['y'] - viewport['height'], viewport['y'] - frame['y'])
            require(frame['height'] <= viewport['height'] and frame['width'] <= viewport['width'],
                    'A reveal budget cannot make oversized content fit')
            final, final_view = measured_rect(budget.get('final_frame')), measured_rect(budget.get('final_viewport'))
            require(same_size(frame, final) and same_size(viewport, final_view) and contains(final_view, final),
                    'Reveal budget completed with a partially exposed control/group')
            initial_anchor = measured_rect(budget.get('initial_anchor_frame'))
            final_anchor = measured_rect(budget.get('final_anchor_frame'))
            require(contains(frame, initial_anchor, 2) and contains(final, final_anchor, 2) and
                    same_size(initial_anchor, final_anchor) and
                    abs((final['y'] - frame['y']) - (final_anchor['y'] - initial_anchor['y'])) <= 2 and
                    abs((final['x'] - frame['x']) - (final_anchor['x'] - initial_anchor['x'])) <= 2,
                    'Reveal union is not the actual measured anchor translation')
        elif budget['kind'] == 'read':
            distance = abs(frame['y'] - viewport['y']) + frame['height']
        else:
            target = budget.get('target_relative_y')
            require(number(target), 'Recovery has no prior measured relative position')
            distance = abs((frame['y'] - viewport['y']) - target)
        step = .40 * viewport['height']
        limit = math.ceil(distance / step) + 2
        require(number(budget.get('distance')) and abs(budget['distance'] - distance) <= .001 and
                number(budget.get('minimum_planned_step')) and abs(budget['minimum_planned_step'] - step) <= .001 and
                type(budget.get('limit')) is int and budget['limit'] == limit <= 64,
                'Operation bound does not follow its original measured geometry')
        rows = by_budget[bid]
        require(type(budget.get('used')) is int and budget['used'] == len(rows) <= limit,
                'Measured operation used more gestures than its finite budget')
        if budget['kind'] == 'reveal':
            if rows:
                require(same_frame(rows[0]['before'], initial_anchor) and same_frame(rows[-1]['after'], final_anchor),
                        'Reveal completion is not bound to the actual first/last movement')
            else:
                require(same_frame(initial_anchor, final_anchor) and same_frame(frame, final),
                        'Zero-movement reveal changed its measured target')
        for step_index, event in enumerate(rows, 1):
            if step_index > 1:
                require(same_frame(rows[step_index - 2]['after'], event['before']),
                        'Gesture chain has an unobserved frame jump')
            require(event.get('budget_step') == step_index and event.get('kind') == budget['kind'] and
                    event.get('key') == budget['key'], 'Gesture is charged to the wrong operation or counter')
    return budgets, gestures


def validate_audit_recoveries(value, captures, budgets):
    records = value.get('audit_recoveries')
    require(isinstance(records, list), 'Missing audit-displacement recovery ledger')
    captured_geometry = {(row['key'], row['capture_index']): row for row in
                         value['read_coverage'] + value['online_link_exposure']}
    expected = set(captured_geometry)
    section_records = [(row.get('key'), row.get('capture_index')) for row in records
                       if isinstance(row.get('key'), str) and row['key'].startswith('privacy-section-')]
    require(len(section_records) == 4 and {key for key, _ in section_records} ==
            {key for key in REQUIRED_AUDITS if key.startswith('privacy-section-')},
            'An original privacy section audit or recovery is missing')
    expected |= set(section_records)
    require(len(records) == len(expected) and {(row.get('key'), row.get('capture_index')) for row in records} == expected,
            'Audit recovery misses or duplicates a captured reading/link/section interval')
    audit_indices, budget_ids = set(), set()
    for row in records:
        key, capture, bid, audit_index = (row.get(k) for k in ('key', 'capture_index', 'budget_id', 'audit_index'))
        require(type(capture) is int and 1 <= capture <= len(captures) and
                captures[capture - 1]['pose'] == ('privacy-section' if key.startswith('privacy-section-') else key),
                'Audit recovery has no original visible capture')
        require(type(audit_index) is int and 1 <= audit_index <= len(value['audits']) and
                value['audits'][audit_index - 1] == key and audit_index not in audit_indices,
                'Recovery is not bound to one completed unfiltered audit')
        audit_indices.add(audit_index)
        require(type(bid) is int and 0 <= bid < len(budgets) and bid not in budget_ids,
                'Recovery reuses or omits a measured operation budget')
        budget_ids.add(bid)
        budget = budgets[bid]
        require(budget['kind'] == 'audit-recovery' and budget['key'] == key and row.get('restored') is True,
                'Displaced audit was not independently restored')
        before, after, final, view, after_view, final_view = (measured_rect(row.get(k)) for k in
            ('before_frame', 'after_frame', 'restored_frame', 'before_viewport', 'after_viewport', 'restored_viewport'))
        original = captured_geometry.get((key, capture))
        require(original is None or (original['frame'] == before and original['viewport'] == view),
                'Recovery changed the originally captured reading/link pose')
        target = before['y'] - view['y']
        displacement = after['y'] - after_view['y'] - target
        require(same_size(before, after) and same_size(before, final) and same_size(view, after_view) and same_size(view, final_view),
                'Audit/recovery changed native element or viewport dimensions')
        require(number(row.get('displacement')) and abs(row['displacement'] - displacement) <= .001 and
                abs((final['y'] - final_view['y']) - target) <= 2 and
                budget['initial_frame'] == after and budget['initial_viewport'] == after_view and
                abs(budget['target_relative_y'] - target) <= .001,
                'Previously exposed relative interval was not restored')
        require(abs(displacement) <= 2 or budget['used'] > 0, 'Claimed recovery has no actual measured movement')
        actual = [event for event in value['gestures'] if event['budget_id'] == bid]
        if actual:
            require(actual[0]['before'] == after and actual[-1]['after'] == final,
                    'Recovered interval is not bound to the actual first/last movement')
            previous_error = abs(displacement)
            for event in actual:
                remaining = abs(event['after']['y'] - event['viewport']['y'] - target)
                require(remaining <= 2 or remaining < previous_error - 1,
                        'Recovery movement does not approach the original relative interval')
                previous_error = remaining
    require(budget_ids == {bid for bid, budget in enumerate(budgets) if budget['kind'] == 'audit-recovery'},
            'Unbound or fabricated audit-recovery budget')


def validate_online_links(value, captures):
    rows = value.get('online_link_exposure')
    require(isinstance(rows, list) and len(rows) == len(ONLINE_LINKS), 'Missing explicit online link coverage')
    for row, (key, label) in zip(rows, ONLINE_LINKS):
        require(row.get('key') == key and row.get('label') == label and row.get('element_type') == 'link',
                'Online link identity/type differs from actual source')
        target, viewport = measured_rect(row.get('frame')), measured_rect(row.get('viewport'))
        require(contains(viewport, target), 'Online link is clipped or below the actual scroll viewport')
        idx = row.get('capture_index')
        require(type(idx) is int and 1 <= idx <= len(captures) and captures[idx - 1]['pose'] == key,
                'Online link exposure has no original screenshot/AX pair')


def validate_match_semantics(value, budgets, gestures):
    require(isinstance(value, dict) and value.get('container_identifier') == 'screening-match-pork' and value.get('container_is_static_text') is False, 'Missing real independently navigable match container')
    keys = {key for key, _ in MATCH_LABELS}
    ids = [bid for bid, budget in enumerate(budgets) if budget['key'] in keys]
    require(value.get('budget_ids') == ids and all(budgets[bid]['kind'] in ('read', 'audit-recovery') for bid in ids),
            'Match section lost its independent measured reading/recovery budgets')
    rows = [event for event in gestures if event['budget_id'] in ids]
    navigation = sum(event['kind'] != 'audit-recovery' for event in rows)
    recovery = sum(event['kind'] == 'audit-recovery' for event in rows)
    require(value.get('gesture_count') == len(rows) and value.get('navigation_gesture_count') == navigation and
            value.get('audit_recovery_gesture_count') == recovery,
            'Match-section gesture accounting hides or reassigns audit recovery')
    outer = measured_rect(value.get('container_frame'))
    children = value.get('children')
    require(isinstance(children, list) and len(children) == len(MATCH_LABELS), 'Missing or duplicate match information')
    previous_bottom = outer['y']
    for item, (key, label) in zip(children, MATCH_LABELS):
        require(item.get('key') == key and item.get('label') == label and item.get('is_static_text') is True, 'Match text is missing, synthetic or reordered')
        r = measured_rect(item.get('frame'))
        require(r['x'] >= outer['x'] - 2 and r['x'] + r['width'] <= outer['x'] + outer['width'] + 2 and r['y'] >= previous_bottom - 2 and r['y'] + r['height'] <= outer['y'] + outer['height'] + 2, 'Match text overlaps or lies outside its real container')
        previous_bottom = r['y'] + r['height']


def validate_completion(value, case, geometries):
    require(value.get('case_id') == case and value.get('status') == 'CASE_COMPLETED', 'Case did not reach strict completion')
    require(value.get('actions') == EXPECTED_ACTIONS, 'Functional action inventory differs')
    audits = value.get('audits')
    require(isinstance(audits, list) and REQUIRED_AUDITS <= set(audits), 'A required unfiltered native audit is missing')
    captures = value.get('captures')
    require(isinstance(captures, list) and captures == geometries and len(captures) <= CAPTURE_LIMIT, 'Completion capture ledger differs from actual attachments')
    poses = {x['pose'] for x in captures}
    require(REQUIRED_POSES <= poses and sum(x['pose'] == 'privacy-section' for x in captures) == 4, 'Required screenshot/content pose missing')
    if case == 'light-accessibility5': require('focused-before-sample' in poses, 'Focused-editor sample path not captured')
    budgets, gestures = validate_gesture_budgets(value, captures)
    validate_match_semantics(value.get('match_semantics'), budgets, gestures)
    coverage = value.get('read_coverage')
    require(isinstance(coverage, list), 'No native continuous text-coverage ledger')
    groups = defaultdict(list)
    for row in coverage:
        require(row.get('key') in READ_KEYS, 'Unexpected text-coverage target')
        require(all(number(row.get(k)) for k in ('start', 'end', 'height')), 'Invalid text-coverage interval')
        idx = row.get('capture_index')
        require(type(idx) is int and 1 <= idx <= len(captures) and captures[idx-1]['pose'] == row['key'], 'Text-coverage receipt lacks matching original capture')
        groups[row['key']].append(row)
    require(set(groups) == READ_KEYS, 'Missing explanatory-text coverage')
    for key, rows in groups.items():
        matched_budgets = [bid for bid, b in enumerate(budgets) if b['key'] == key and b['kind'] == 'read']
        require(len(matched_budgets) == 1, 'Text block lacks one finite independent reading budget')
        bid = matched_budgets[0]
        require(len(rows) <= budgets[bid]['limit'] + 1 and all(row.get('budget_id') == bid for row in rows),
                'Unbounded or incorrectly charged text reveal sequence')
        furthest, height = 0, rows[0]['height']
        for index, row in enumerate(rows):
            require(abs(row['height'] - height) <= 2 and 0 <= row['start'] <= furthest + 2 and row['start'] < row['end'] <= height + 2, 'A gap, inconsistent height or invalid text interval remains')
            require(index == 0 or row['end'] > furthest + 1, 'Reading made no new continuous progress')
            target, view = measured_rect(row.get('frame')), measured_rect(row.get('viewport'))
            start = max(0, view['y'] - target['y'])
            end = min(target['height'], view['y'] + view['height'] - target['y'])
            require(abs(row['start'] - start) <= .001 and abs(row['end'] - end) <= .001 and
                    abs(row['height'] - target['height']) <= .001 and end - start > 10,
                    'Claimed text coverage differs from the actually exposed interval')
            furthest = max(furthest, row['end'])
        require(furthest >= height - 2, 'Text block was not continuously covered: ' + key)
    require({bid for bid, b in enumerate(budgets) if b['kind'] == 'read'} ==
            {row['budget_id'] for row in coverage}, 'A reading operation has no actual continuous coverage')
    validate_online_links(value, captures)
    validate_audit_recoveries(value, captures, budgets)

def validate_attachments(folder, host_folder, *, run_id, simulator, simulator_name):
    hosts = validate_host(host_folder, run_id)
    manifest = read_json(folder / 'manifest.json')
    expected = {TEST_CLASS + '/' + method + '()': case for case, method in CASE_TESTS.items()}
    require(isinstance(manifest, list) and len(manifest) == 3 and {x.get('testIdentifier') for x in manifest} == set(expected), 'Attachment rows do not match the exact three new cases')
    result, exported, total_bytes = {}, set(), 0
    for row in manifest:
        case = expected[row['testIdentifier']]
        images, geometries, trees, completions = [], [], {}, []
        require(isinstance(row.get('attachments'), list) and len(row['attachments']) <= ATTACHMENT_LIMIT, 'Unbounded/invalid attachment inventory')
        for item in row['attachments']:
            require(item.get('deviceId', '').upper() == simulator.upper() and item.get('deviceName') == simulator_name and item.get('isAssociatedWithFailure') is False, 'Attachment is not clean evidence from the owned destination')
            name, human = item.get('exportedFileName'), item.get('suggestedHumanReadableName')
            require(isinstance(name, str) and Path(name).name == name and name not in exported and isinstance(human, str), 'Unsafe/duplicate attachment path')
            exported.add(name)
            path = folder / name
            require(path.is_file() and not path.is_symlink(), 'Missing or linked attachment')
            total_bytes += path.stat().st_size
            require(total_bytes <= 750_000_000, 'Attachment bytes exceed the fixed bounded scope')
            if human.startswith('Appearance PNG geometry - '): geometries.append((item, path, read_json(path, 16_000)))
            elif human.startswith('Appearance case completed'): completions.append(read_json(path))
            elif human.startswith('Appearance AX - '): trees[human] = path
            elif name.endswith('.png') and human.startswith('appearance-'): images.append((item, path, inspect_png(path.read_bytes())))
        require(1 <= len(images) == len(geometries) == len(trees) <= CAPTURE_LIMIT and len(completions) == 1, 'Missing original PNG/geometry/AX pairs or one final case receipt')
        geometries.sort(key=lambda x: x[2].get('index', -1))
        values, used, verified = [], set(), []
        for index, (item, path, value) in enumerate(geometries, 1):
            require(value.get('schema_version') == 1 and value.get('index') == index and value.get('run_id') == run_id and value.get('case_id') == case, 'Capture sequence/run/case binding is invalid')
            name = value.get('capture_name')
            require(isinstance(name, str) and name.startswith('appearance-' + case + '-'), 'Capture name is not case bound')
            frame(value.get('app_frame')); frame(value.get('window_frame'))
            require(value.get('orientation') == 1 and value.get('system_appearance') == (2 if case == 'dark-large' else 1), 'Capture system appearance/orientation mismatch')
            require(value.get('pixel_width') == 750 and value.get('pixel_height') == 1334, 'PNG does not match native SE pixels')
            matches = [i for i, (meta, img, png) in enumerate(images) if i not in used and meta['suggestedHumanReadableName'].startswith(name + '_') and png['sha256'] == value.get('png_sha256') and png['bytes'] == value.get('png_bytes')]
            require(len(matches) == 1, 'No unique hash-bound original PNG')
            used.add(matches[0])
            ax = [p for label, p in trees.items() if label.startswith('Appearance AX - ' + name + '_')]
            require(len(ax) == 1 and ax[0].stat().st_size > 0, 'Capture has no original accessibility tree')
            image = images[matches[0]][1]
            verified.append({'capture_name': name, 'pose': value['pose'], 'original_png': str(image), 'sha256': value['png_sha256'], 'geometry': str(path), 'accessibility_tree': str(ax[0])})
            values.append(value)
        require(len(used) == len(images), 'Unmatched original image')
        completion = completions[0]
        require(completion.get('run_id') == run_id, 'Final case receipt has wrong run')
        validate_completion(completion, case, values)
        result[case] = {'host': hosts[case], 'captures': verified, 'capture_count': len(verified), 'gesture_count': completion['gesture_count'], 'audits': completion['audits'], 'functional_actions': completion['actions']}
    return {'status': 'THREE_NATIVE_CASES_AND_BOUND_ORIGINAL_EVIDENCE_VERIFIED', 'run_id': run_id,
            'device_id': simulator, 'cases': result, 'manual_pixel_review': 'REQUIRED_NOT_PERFORMED_BY_GUARD',
            'image_transformations': [], 'baseline_ten_tests': 'SEPARATE_UNCHANGED_SUITE',
            'store_screenshot_upload': 'NOT_PERFORMED'}
