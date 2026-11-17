#!/usr/bin/env python3
"""Synthetic malformed-evidence regression tests; never native UI acceptance."""
from pathlib import Path
import ast
import copy
import importlib.util
import math
import sys
import unittest

# The original PNG parser is supplied by the prepared native package; this file
# never invokes PNG/device/build tools. For source-only guard checks its import
# is unused and replaced by a module that refuses execution.
import types
if 'appearance_png' not in sys.modules:
    module = types.ModuleType('appearance_png')
    def no_png(_):
        raise AssertionError('This synthetic geometry test must not inspect images')
    module.inspect_png = no_png
    sys.modules['appearance_png'] = module
ROOT = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('geometry_guard', ROOT / 'appearance_evidence_guard.py')
g = importlib.util.module_from_spec(spec)
spec.loader.exec_module(g)


def rect(y, height=40, x=22, width=331):
    return dict(x=x, y=y, width=width, height=height)


def viewport():
    return rect(93, 463, 2, 371)


def budget(index, kind, key, frame, view, distance, used=0, **other):
    step=.40*view['height']
    return dict(id=index, kind=kind, key=key, initial_frame=frame, initial_viewport=view,
                distance=distance, minimum_planned_step=step, limit=math.ceil(distance/step)+2,
                used=used, complete=True, **other)


def fixture():
    """Complete synthetic ledger for checking guard rejection, no PNGs/runtimes."""
    value=dict(case_id='light-large',status='CASE_COMPLETED',actions=g.EXPECTED_ACTIONS.copy(),
               captures=[],audits=[],gestures=[],gesture_count=0,gesture_budgets=[],
               read_coverage=[],audit_recoveries=[],online_link_exposure=[],
               geometry_policy=g.GEOMETRY_POLICY,case_gesture_limit=g.CASE_GESTURE_LIMIT)
    def capture(pose):
        value['captures'].append(dict(pose=pose));return len(value['captures'])
    def recovered_audit(key, index, frame):
        value['audits'].append(key);bid=len(value['gesture_budgets']);view=viewport()
        value['gesture_budgets'].append(budget(bid,'audit-recovery',key,frame,view,0,target_relative_y=frame['y']-view['y']))
        value['audit_recoveries'].append(dict(key=key,capture_index=index,audit_index=len(value['audits']),budget_id=bid,
            before_frame=frame,before_viewport=view,after_frame=frame,after_viewport=view,
            restored_frame=frame,restored_viewport=view,displacement=0,restored=True))
    for pose in ['entry','keyboard','flagged-result','privacy-action','privacy-sheet','unknown-result']:
        capture(pose)
        if pose!='keyboard':value['audits'].append(pose)
    children=[]
    for key,y in [('entry-scope',120)]+[(key,120+index*60) for index,(key,_) in enumerate(g.MATCH_LABELS)]+[('coverage',400)]:
        frame=rect(y);view=viewport();bid=len(value['gesture_budgets']);idx=capture(key)
        value['gesture_budgets'].append(budget(bid,'read',key,frame,view,abs(frame['y']-view['y'])+frame['height']))
        value['read_coverage'].append(dict(key=key,budget_id=bid,capture_index=idx,start=0,end=40,height=40,frame=frame,viewport=view))
        recovered_audit(key,idx,frame)
        if key.startswith('matched-'):
            label=dict(g.MATCH_LABELS)[key];children.append(dict(key=key,label=label,is_static_text=True,frame=frame))
    value['match_semantics']=dict(container_identifier='screening-match-pork',container_is_static_text=False,
        container_frame=rect(110,240,20,335),children=children,gesture_count=0,navigation_gesture_count=0,
        audit_recovery_gesture_count=0,budget_ids=[b['id'] for b in value['gesture_budgets'] if b['key'].startswith('matched-')])
    for key in sorted(k for k in g.REQUIRED_AUDITS if k.startswith('privacy-section-')):
        recovered_audit(key,capture('privacy-section'),rect(120,22))
    for index,(key,label) in enumerate(g.ONLINE_LINKS):
        frame=rect(200+index*80,44);idx=capture(key)
        value['online_link_exposure'].append(dict(key=key,label=label,element_type='link',frame=frame,viewport=viewport(),capture_index=idx))
        recovered_audit(key,idx,frame)
    capture('completed')
    return value


class GeometryEvidence(unittest.TestCase):
    def test_complete_synthetic_evidence_passes_and_bilingual_logic_matches(self):
        value=fixture();g.validate_completion(value,'light-large',value['captures'])
        a=ast.parse((ROOT/'appearance_evidence_guard.py').read_text())
        b=ast.parse((ROOT/'arabic_appearance_evidence_guard.py').read_text())
        names={node.name for node in a.body if isinstance(node,ast.FunctionDef)}-{'validate_host'}
        for name in names:
            left=next(n for n in a.body if isinstance(n,ast.FunctionDef) and n.name==name)
            right=next(n for n in b.body if isinstance(n,ast.FunctionDef) and n.name==name)
            self.assertEqual(ast.dump(left),ast.dump(right),name)

    def test_actual_r6b_heading_distance_needs_more_than_four_and_clipped_finish_is_rejected(self):
        view=viewport();initial=rect(1499,137);distance=1499+137-(93+463)
        b=budget(0,'reveal','privacy-What a result means',initial,view,distance,used=5,
                 final_frame=rect(254,137),final_viewport=view,
                 initial_anchor_frame=initial,final_anchor_frame=rect(254,137))
        self.assertEqual(b['limit'],8)
        captures=[];events=[]
        for i,y in enumerate([1499,1250,1001,752,503],1):
            before=len(captures)+1;captures += [dict(pose='before-gesture'),dict(pose='after-gesture')]
            events.append(dict(index=i,key=b['key'],direction=-1,budget_id=0,budget_step=i,kind='reveal',
                before=rect(y,137),after=rect(y-249,137),viewport=view,requested_travel=.56*463,
                route=rect(93+.22*463,.56*463,4,4),editor_frames=[],indicator_frames=[],
                before_capture_index=before,after_capture_index=before+1))
        value=dict(geometry_policy=g.GEOMETRY_POLICY,case_gesture_limit=168,gesture_budgets=[b],gestures=events,gesture_count=5)
        g.validate_gesture_budgets(value,captures)
        clipped=copy.deepcopy(value);clipped['gesture_budgets'][0]['final_frame']=rect(503,137)
        with self.assertRaises(ValueError):g.validate_gesture_budgets(clipped,captures)
        forged=copy.deepcopy(value);forged['gesture_budgets'][0]['final_frame']=rect(200,137)
        with self.assertRaises(ValueError):g.validate_gesture_budgets(forged,captures)
        forged=copy.deepcopy(value);forged['gesture_budgets'][0]['final_frame']=rect(200,137)
        forged['gesture_budgets'][0]['final_anchor_frame']=rect(200,137)
        with self.assertRaises(ValueError):g.validate_gesture_budgets(forged,captures)
        broken=copy.deepcopy(value);broken['gestures'][1]['before']=rect(1300,137)
        with self.assertRaises(ValueError):g.validate_gesture_budgets(broken,captures)
        obsolete=copy.deepcopy(value);obsolete['gesture_budgets'][0]['limit']=4
        with self.assertRaises(ValueError):g.validate_gesture_budgets(obsolete,captures)
        wrong=copy.deepcopy(value);wrong['gestures'][0]['budget_id']=1
        with self.assertRaises(ValueError):g.validate_gesture_budgets(wrong,captures)
        bad_route=copy.deepcopy(value);bad_route['gestures'][0]['editor_frames']=[bad_route['gestures'][0]['route']]
        with self.assertRaises(ValueError):g.validate_gesture_budgets(bad_route,captures)

    def test_complete_read_must_still_restore_actual_523_point_audit_rewind(self):
        value=fixture();row=value['audit_recoveries'][3];bid=row['budget_id']
        row['after_frame']=dict(row['after_frame'],y=row['after_frame']['y']+523)
        row['displacement']=523
        b=value['gesture_budgets'][bid];b.update(initial_frame=row['after_frame'],distance=523,
            limit=math.ceil(523/b['minimum_planned_step'])+2)
        with self.assertRaises(ValueError):g.validate_completion(value,'light-large',value['captures'])
        missing=fixture();missing['audit_recoveries'].pop(3)
        with self.assertRaises(ValueError):g.validate_completion(missing,'light-large',missing['captures'])

    def test_original_seven_point_link_clip_and_missing_link_audit_are_rejected(self):
        value=fixture();row=value['online_link_exposure'][0]
        row['frame']=rect(562,44);row['viewport']=rect(91,508,2,371)
        with self.assertRaises(ValueError):g.validate_online_links(value,value['captures'])
        value=fixture();value['audits'].remove('privacy-online-link')
        with self.assertRaises(ValueError):g.validate_completion(value,'light-large',value['captures'])

    def test_no_gap_and_no_fabricated_interval_or_recovery_binding(self):
        for mutate in [lambda v:v['read_coverage'][3].update(start=20),
                       lambda v:v['read_coverage'][3].update(end=60,height=60),
                       lambda v:v['audit_recoveries'][3].update(restored=False),
                       lambda v:v['audit_recoveries'][3].update(before_frame=rect(140))]:
            value=fixture();mutate(value)
            with self.assertRaises(ValueError):g.validate_completion(value,'light-large',value['captures'])

if __name__=='__main__':unittest.main(verbosity=2)
