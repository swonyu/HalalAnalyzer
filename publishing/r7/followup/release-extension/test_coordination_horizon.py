#!/usr/bin/env python3
"""Execute only extracted preflight functions with synthetic schedule/process inputs.

No native module import, OS process scan, lock mutation, adapter execution or Mac action.
"""
from pathlib import Path
from datetime import datetime,timedelta,timezone
import ast
import json
import os
import re
import tempfile
import types
import unittest

ROOT=Path(__file__).resolve().parent/'preparation'
ORIGINAL=datetime(2026,11,17,22,26,12,tzinfo=timezone.utc)
EXTENDED=datetime(2026,11,18,22,26,12,tzinfo=timezone.utc)


def extracted(path,schedule,current,checkpoint,ps_calls):
 text=path.read_text();tree=ast.parse(text)
 functions=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in ('require','date','preflight','clear')]
 assert len(functions)==4
 def fake_ps(*args,**kwargs):
  ps_calls.append(args)
  return types.SimpleNamespace(stdout='PID PPID ELAPSED STATE COMMAND\n')
 scope=dict(Path=Path,datetime=datetime,timezone=timezone,timedelta=timedelta,
  now=lambda:current,CONSERVATIVE_CHECKPOINT=checkpoint,SCHEDULE=schedule,LOCK=schedule/'synthetic-absent-lock',
  read_json=lambda p:json.loads(p.read_text()),live=lambda p:False,os=os,
  subprocess=types.SimpleNamespace(run=fake_ps),NATIVE_COMMAND=re.compile(r'\b(xcodebuild)\b'))
 exec(compile(ast.Module(body=functions,type_ignores=[]),'<extracted-preflight-only>','exec'),scope)
 return scope


def fixture(folder,start,end):
 (folder/'other-interval.json').write_text(json.dumps(dict(slot_id='synthetic-other-owner',
  status='pending',window_starts_at=start.isoformat(),window_ends_at=end.isoformat())))


class CoordinationHorizon(unittest.TestCase):
 def test_after_original_cutoff_interval_only_conflict_is_still_blocked(self):
  current=datetime(2026,11,18,0,0,tzinfo=timezone.utc)
  with tempfile.TemporaryDirectory(prefix='halal-synthetic-schedule-') as tmp:
   folder=Path(tmp);fixture(folder,current+timedelta(minutes=10),current+timedelta(minutes=20))
   old_calls=[];new_calls=[]
   old=extracted(ROOT/'native_coordination_frozen.py',folder,current,ORIGINAL,old_calls)
   new=extracted(ROOT/'native_coordination_extended.py',folder,current,EXTENDED,new_calls)
   queue=dict(native_hard_cap_minutes=20,created_at=current.isoformat())
   previous=old['preflight'](set(),queue);corrected=new['preflight'](set(),queue)
   self.assertTrue(old['clear'](previous),'Reproduce the preserved expired-horizon defect')
   self.assertLess(datetime.fromisoformat(previous['proposed_window_ends_at']),current)
   self.assertFalse(new['clear'](corrected))
   self.assertEqual(corrected['proposed_window_ends_at'],(current+timedelta(minutes=21)).isoformat())
   self.assertEqual(len(corrected['schedule_blockers']),1)
   self.assertTrue(corrected['schedule_blockers'][0]['window_active'])
   self.assertEqual(corrected['schedule_blockers'][0]['status'],'pending')
   self.assertEqual(len(old_calls),len(new_calls),1)

 def test_pre_cutoff_behavior_and_existing_process_lock_rules_are_preserved(self):
  current=datetime(2026,11,17,17,0,tzinfo=timezone.utc)
  with tempfile.TemporaryDirectory(prefix='halal-synthetic-schedule-') as tmp:
   folder=Path(tmp);fixture(folder,current+timedelta(minutes=10),current+timedelta(minutes=20))
   old=extracted(ROOT/'native_coordination_frozen.py',folder,current,ORIGINAL,[])
   new=extracted(ROOT/'native_coordination_extended.py',folder,current,EXTENDED,[])
   queue=dict(native_hard_cap_minutes=20,created_at=current.isoformat())
   self.assertEqual(old['preflight'](set(),queue),new['preflight'](set(),queue))
   old_text=(ROOT/'native_coordination_frozen.py').read_text()
   new_text=(ROOT/'native_coordination_extended.py').read_text()
   def node(text,name):
    return next(n for n in ast.parse(text).body if isinstance(n,ast.FunctionDef) and n.name==name)
   before=node(old_text,'preflight');after=node(new_text,'preflight')
   self.assertEqual(len(after.body),len(before.body)+1)
   # Only the new positive-window assertion differs inside preflight.
   after.body.pop(2)
   self.assertEqual(ast.dump(before),ast.dump(after))
   self.assertEqual(ast.dump(node(old_text,'clear')),ast.dump(node(new_text,'clear')))

 def test_expired_extended_horizon_fails_closed_and_templates_align(self):
  current=EXTENDED+timedelta(seconds=1);calls=[]
  with tempfile.TemporaryDirectory(prefix='halal-synthetic-schedule-') as tmp:
   new=extracted(ROOT/'native_coordination_extended.py',Path(tmp),current,EXTENDED,calls)
   with self.assertRaisesRegex(RuntimeError,'No positive scheduling window'):
    new['preflight'](set(),dict(native_hard_cap_minutes=20,created_at=current.isoformat()))
   self.assertEqual(calls,[])
  spec=json.loads((ROOT/'production-manifest.json').read_text())
  self.assertEqual(spec['conservative_scheduling_checkpoint'],'2026-11-18T22:26:12Z')
  for path in ROOT.glob('acknowledgment-*-UNCONFIGURED.json'):
   ack=json.loads(path.read_text());self.assertIs(ack['acknowledged'],False)
   for key in ['conservative_scheduling_checkpoint','original_deadline_utc','extended_deadline_utc','explicit_user_extension_hours']:
    self.assertEqual(ack[key],spec[key])

if __name__=='__main__':unittest.main(verbosity=2)
