#!/usr/bin/env python3
"""Prepare an isolated release-only scheduling-horizon correction; execute no stage."""
from pathlib import Path
import argparse
import ast
import difflib
import hashlib
import json
import re
import shutil

PARENT_PINS={
 'production-manifest.json':'b5bece02f9433870a3183a5be9572f6c004cbe92499cd3168135f5e9688c2076',
 'release_support.py':'ed5cfc3d1bf2976e91875a4757ef81ab43559fffd6c01002b356949ace081e50',
 'run_release_stage.py':'ff97c414e4c4494cf4074f00f32c7ec722715ebe9f1994d5767998cd55541cce',
 'publishing_runner_frozen.py':'1980cdf5a564a802198183fd79ee2f0a325b486908bab45e01beaadb02e50f99',
 'native_coordination_frozen.py':'243dc8943a5d91ed3a26673223f862a4f30a1c8b0a35088e7476d02ea4f78c6c'}
ORIGINAL='2026-11-17T22:26:12Z'
EXTENDED='2026-11-18T22:26:12Z'


def sha(path):
 assert path.is_file() and not path.is_symlink()
 return hashlib.sha256(path.read_bytes()).hexdigest()


def dump(path,value):path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')


def rebind(text,key,value):
 text,count=re.subn(r'^'+key+r" = '[0-9a-f]+'",key+" = '"+value+"'",text,flags=re.M)
 assert count==1,key
 return text


def main():
 parser=argparse.ArgumentParser(description=__doc__)
 parser.add_argument('--parent-preparation',type=Path,required=True)
 parser.add_argument('--output',type=Path,required=True)
 args=parser.parse_args();parent=args.parent_preparation.resolve();out=args.output.resolve()
 assert not out.exists() and not any(p.is_symlink() for p in parent.rglob('*'))
 for name,pin in PARENT_PINS.items():assert sha(parent/name)==pin,name
 shutil.copytree(parent,out)
 (out/'preparation-review.json').rename(out/'predecessor-preparation-review.json')
 old=(parent/'native_coordination_frozen.py').read_text()
 before='CONSERVATIVE_CHECKPOINT = datetime(2026, 11, 17, 22, 26, 12, tzinfo=timezone.utc)'
 after='CONSERVATIVE_CHECKPOINT = datetime(2026, 11, 18, 22, 26, 12, tzinfo=timezone.utc)'
 assert old.count(before)==1
 new=old.replace(before,after)
 new=new.replace('''# The user requested 24 ACTIVE engineering hours. This elapsed-time checkpoint
# is a conservative scheduling boundary, not an independently verified hard
# deadline or proof of active hours consumed. No user budget is restarted here.''','''# Release-only successor: the user explicitly added another 24 hours to the
# original 2026-11-17T22:26:12Z cutoff. The original start/budget is not reset.
# The frozen predecessor remains separately preserved and hash-bound.''')
 new=new.replace('BUDGET_BASIS = "24 active engineering hours requested; active usage and remaining balance unverified; elapsed checkpoint used conservatively"',
  'BUDGET_BASIS = "Original budget/start preserved; user explicitly extended the original cutoff by 24h to 2026-11-18T22:26:12Z"')
 hook='    proposed_end = min(current + timedelta(minutes=queue["native_hard_cap_minutes"] + 1), CONSERVATIVE_CHECKPOINT)'
 assert new.count(hook)==1
 new=new.replace(hook,hook+'\n    require(proposed_end > current, "No positive scheduling window remains before the explicitly extended cutoff")')
 # This is coordination support for the release adapter, not a new historical
 # batch launcher. Preserve all predecessor functions for review but disable
 # the copied CLI entry point, which would reference unrelated historical tasks.
 tail='if __name__ == "__main__":\n    try:\n        raise SystemExit(main())\n    except (RuntimeError, OSError, ValueError) as error:\n        print("BLOCKED: " + str(error), file=sys.stderr)\n        raise SystemExit(2)'
 assert new.count(tail)==1
 new=new.replace(tail,'if __name__ == "__main__":\n    raise SystemExit("R7 release coordination is import-only; use the exact reviewed release adapter")')
 ast.parse(new);(out/'native_coordination_extended.py').write_text(new)
 manifest=json.loads((out/'production-manifest.json').read_text())
 assert manifest['conservative_scheduling_checkpoint']==manifest['extended_deadline_utc']==EXTENDED
 assert manifest['original_deadline_utc']==ORIGINAL and manifest['explicit_user_extension_hours']==24
 manifest.update(preparation_revision='R7-release-explicit-extension-coordination',
  coordination_provenance={'predecessor_sha256':PARENT_PINS['native_coordination_frozen.py'],
   'extended_preflight_sha256':sha(out/'native_coordination_extended.py'),
   'original_checkpoint':ORIGINAL,'explicit_user_extension_hours':24,'extended_checkpoint':EXTENDED,
   'historical_cli_disabled':True,'positive_window_required':True,'lifecycle_changed':False})
 dump(out/'production-manifest.json',manifest)
 support=rebind((parent/'release_support.py').read_text(),'MANIFEST_SHA',sha(out/'production-manifest.json'))
 ast.parse(support);(out/'release_support.py').write_text(support)
 runner=(parent/'run_release_stage.py').read_text()
 runner=rebind(runner,'SUPPORT_SHA',sha(out/'release_support.py'))
 runner=rebind(runner,'COORDINATION_SHA',sha(out/'native_coordination_extended.py'))
 hook="    pins = {'adapter_sha256': support.sha(Path(__file__)),"
 assert runner.count(hook)==1
 runner=runner.replace(hook,"""    pins = {'conservative_scheduling_checkpoint': spec['conservative_scheduling_checkpoint'],
            'original_deadline_utc': spec['original_deadline_utc'],
            'extended_deadline_utc': spec['extended_deadline_utc'],
            'explicit_user_extension_hours': spec['explicit_user_extension_hours'],
            'adapter_sha256': support.sha(Path(__file__)),""")
 old_load="coordination = load('halal_release_frozen_coordination', HERE / 'native_coordination_frozen.py', COORDINATION_SHA)"
 new_load="coordination = load('halal_release_extended_coordination', HERE / 'native_coordination_extended.py', COORDINATION_SHA)"
 assert runner.count(old_load)==1;runner=runner.replace(old_load,new_load)
 ast.parse(runner);(out/'run_release_stage.py').write_text(runner)
 for stage in ['unsigned-archive','developer-archive','distribution-export']:
  name='acknowledgment-'+stage+'-UNCONFIGURED.json';ack=json.loads((parent/name).read_text())
  assert ack['acknowledged'] is False
  ack.update(conservative_scheduling_checkpoint=EXTENDED,original_deadline_utc=ORIGINAL,
   extended_deadline_utc=EXTENDED,explicit_user_extension_hours=24,
   adapter_sha256=sha(out/'run_release_stage.py'),support_sha256=sha(out/'release_support.py'),
   production_manifest_sha256=sha(out/'production-manifest.json'),coordination_sha256=sha(out/'native_coordination_extended.py'))
  dump(out/name,ack)
 for name in ['publishing_runner_frozen.py','native_coordination_frozen.py','release-configuration-UNCONFIGURED.json']:
  assert (out/name).read_bytes()==(parent/name).read_bytes()
 for row in manifest['source_files']:
  path=out/'ProductionSource'/row['path'];assert sha(path)==row['sha256'] and path.stat().st_size==row['bytes']
 diffs=[]
 for previous,current in [('native_coordination_frozen.py','native_coordination_extended.py'),
                          ('release_support.py','release_support.py'),('run_release_stage.py','run_release_stage.py')]:
  diffs.extend(difflib.unified_diff((parent/previous).read_text().splitlines(True),(out/current).read_text().splitlines(True),fromfile='r7/'+previous,tofile='r7-extension/'+current))
 (out/'explicit-extension-adapter.diff').write_text(''.join(diffs))
 (out/'HANDOFF.md').write_text('''# R7 release coordination extension correction

File-only successor; no native, archive, signing, export or upload stage executed.
The exact R7 native candidate remains156c5eeb and every shipping f2 byte remains
unchanged. The original R7 release package and frozen coordination file remain
preserved. The new hash-pinned coordination copy uses the user-authorized
2026-11-18T22:26:12Z cutoff and rejects nonpositive proposed windows. This fixes
an interval-conflict blind spot after the original Nov17 cutoff. The historical
batch-launcher CLI is disabled; only the reviewed release adapter imports it.
All three unconfigured templates now carry the same extended checkpoint, and
validate_ack binds the explicit original/extended deadline metadata to manifest.

The exact source/model/19-case native gate, source checks, lifecycle, process
scan, lock checks, schedule records and conflict rules remain unchanged. No
existing schedule/lock is modified by preparation; no configured acknowledgment
is created. The original start/budget are preserved, with the explicit24h extension.
''')
 receipt=dict(status='FILE_ONLY_EXTENSION_REPAIR_NOT_EXECUTED',native_candidate_commit='156c5eeb60eb1e06cf369235ed33af265460a9cb',
  shipping_candidate_commit='f2c27c9271da3a17bb01c50b6cdad94643e1d0f2',shipping_files_unchanged=14,
  original_checkpoint=ORIGINAL,extended_checkpoint=EXTENDED,explicit_user_extension_hours=24,budget_restarted=False,
  parent_pins=PARENT_PINS,current_pins={name:sha(out/name) for name in PARENT_PINS},
  extended_coordination_sha256=sha(out/'native_coordination_extended.py'),
  frozen_predecessor_preserved=True,lifecycle_unchanged=True,all_three_acknowledgments_false=True,
  native_adapter_unchanged=True,native_source_unchanged=True,native_invoked=False,release_adapter_invoked=False,
  signing_invoked=False,upload_invoked=False,preparer_sha256=sha(Path(__file__)))
 dump(out/'extension-preparation-review.json',receipt);print(json.dumps(receipt,indent=2))

if __name__=='__main__':main()
