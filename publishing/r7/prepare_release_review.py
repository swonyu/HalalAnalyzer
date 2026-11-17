#!/usr/bin/env python3
"""File-only R7 release rebind; never import/execute a release/native adapter."""
from pathlib import Path
import argparse
import ast
import difflib
import hashlib
import json
import re
import shutil
import subprocess

NATIVE_COMMIT='156c5eeb60eb1e06cf369235ed33af265460a9cb'
SHIPPING_COMMIT='f2c27c9271da3a17bb01c50b6cdad94643e1d0f2'
NATIVE_SEAL='49c63a850d040e6428c90ce8597c742d8df3f7ee7cb0484643ac152787fcea0d'
NATIVE_ADAPTER='e0becc1b7320367dc30d8a1187ccf3ebe1d0bec652b34fe50a082d131fae1b4f'
NATIVE_PACKAGE='617db0f165550ddbf5ea878a1718d89d06a8759e46784168cafaee7fddda4edc'
PARENT_PINS={
 'production-manifest.json':'4334b0b1c78610592846330f177559c38aba430dd42c0ea14d63d814b2fb8e50',
 'release_support.py':'98831a44ebd99bbafedae46b25218777ce229cacc83d076b7756d4036c18c5ed',
 'run_release_stage.py':'9ac183044c3b33833311451fd28ec83756f663d4ece1563e415eda715aebe0a3',
 'publishing_runner_frozen.py':'1980cdf5a564a802198183fd79ee2f0a325b486908bab45e01beaadb02e50f99',
 'native_coordination_frozen.py':'243dc8943a5d91ed3a26673223f862a4f30a1c8b0a35088e7476d02ea4f78c6c'}


def sha(path):
 assert path.is_file() and not path.is_symlink()
 return hashlib.sha256(path.read_bytes()).hexdigest()


def dump(path,value):
 path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')


def rebind(text,key,value):
 text,count=re.subn(r'^'+key+r" = '[0-9a-f]+'",key+" = '"+value+"'",text,flags=re.M)
 assert count==1,key
 return text


def main():
 parser=argparse.ArgumentParser(description=__doc__)
 parser.add_argument('--parent-preparation',type=Path,required=True)
 parser.add_argument('--native-preparation',type=Path,required=True)
 parser.add_argument('--repository',type=Path,required=True)
 parser.add_argument('--native-source-mac',type=Path,required=True)
 parser.add_argument('--output',type=Path,required=True)
 args=parser.parse_args()
 parent,native,repo,out=(p.resolve() for p in (args.parent_preparation,args.native_preparation,args.repository,args.output))
 for name,pin in PARENT_PINS.items():assert sha(parent/name)==pin,name
 assert sha(native/'sealed-project-inputs.json')==NATIVE_SEAL
 assert sha(native/'run_halaltag_native_qa.py')==NATIVE_ADAPTER
 assert json.loads((native/'reference-inputs.json').read_text())['candidate_commit']==NATIVE_COMMIT
 path=args.native_source_mac
 assert path.is_absolute() and path.name=='Source' and '..' not in path.parts
 assert path.as_posix().startswith('/Users/saleh/Library/Caches/') and 'Production-Composition-R7-' in str(path)
 seal=json.loads((native/'sealed-project-inputs.json').read_text())
 assert seal['scope']=='halaltag-production-composition-nineteen-journeys-r7'
 rows={r['path']:r for r in seal['files']};assert len(rows)==47
 for relative,row in rows.items():
  actual=native/'Source'/relative
  assert sha(actual)==row['sha256'] and actual.stat().st_size==row['bytes']
 manifest=json.loads((parent/'production-manifest.json').read_text())
 assert len(manifest['source_files'])==manifest['source_file_count']==14
 assert not out.exists() and not any(p.is_symlink() for p in parent.rglob('*'))
 shutil.copytree(parent,out)
 for row in manifest['source_files']:
  relative=row['path'];assert relative in rows
  actual=(native/'Source'/relative).read_bytes()
  assert actual==(parent/'ProductionSource'/relative).read_bytes()
  for commit in [SHIPPING_COMMIT,NATIVE_COMMIT]:
   assert actual==subprocess.check_output(['git','-C',str(repo),'show',commit+':'+relative])
  assert hashlib.sha256(actual).hexdigest()==row['sha256'] and len(actual)==row['bytes']
  assert (out/'ProductionSource'/relative).read_bytes()==actual
 manifest.update(scope='halaltag-production-release-r7',preparation_revision='R7-measured-geometry-and-audit-recovery',
  conservative_scheduling_checkpoint='2026-11-18T22:26:12Z',
  original_deadline_utc='2026-11-17T22:26:12Z',explicit_user_extension_hours=24,
  extended_deadline_utc='2026-11-18T22:26:12Z',active_budget_restarted=False)
 provenance=manifest['git_provenance']
 provenance.update(shipping_candidate_commit=SHIPPING_COMMIT,native_candidate_commit=NATIVE_COMMIT,
  source_origin='The unchanged fourteen f2 shipping files in the immutable R7 native preparation',
  native_candidate_seal_sha256=NATIVE_SEAL,parent_release_manifest_sha256=PARENT_PINS['production-manifest.json'])
 gate=manifest['native_gate']
 gate.update(required_scope=seal['scope'],sealed_index_sha256=NATIVE_SEAL,
  run_root='/Users/saleh/Library/Caches/HalalTag-ProductionCompositionR7-NativeQA',source_root=path.as_posix(),
  native_review_zip_sha256=NATIVE_PACKAGE,native_adapter_sha256=NATIVE_ADAPTER,
  appearance_guard_sha256=sha(native/'appearance_evidence_guard.py'),
  arabic_guard_sha256=sha(native/'arabic_appearance_evidence_guard.py'),
  nineteen_case_guard_sha256=sha(native/'production_case_evidence.py'))
 assert gate['case_plan']==json.loads((native/'Source/Tests/NativeQA/nineteen-case-plan.json').read_text())['cases']
 assert len(gate['case_plan'])==19
 for relative,binding in gate['model_source_binding'].items():assert rows[relative]==binding
 assert len(gate['required_model_check_labels'])==9
 dump(out/'production-manifest.json',manifest)
 before=(parent/'release_support.py').read_text()
 support=before.replace('HalalTag R6b','HalalTag R7').replace('isolated R6b run report','isolated R7 run report').replace('Exact R6b native acceptance','Exact R7 native acceptance').replace('reviewed R6 model runner','reviewed R7 model runner')
 support=rebind(support,'MANIFEST_SHA',sha(out/'production-manifest.json'))
 marker='    model = validate_model_gate(root, report, gate)'
 assert support.count(marker)==1
 support=support.replace(marker,"""    require(all(report.get('acknowledgment', {}).get(key) == gate[key] for key in
                ['appearance_guard_sha256', 'arabic_guard_sha256', 'nineteen_case_guard_sha256']),
            'Native appearance/geometry guards differ from the exact reviewed R7 policy')
"""+marker)
 ast.parse(support);(out/'release_support.py').write_text(support)
 runner=(parent/'run_release_stage.py').read_text().replace('HalalTag-ProductionReleaseR6b','HalalTag-ProductionReleaseR7')
 runner=rebind(runner,'SUPPORT_SHA',sha(out/'release_support.py'))
 ast.parse(runner);(out/'run_release_stage.py').write_text(runner)
 for stage in ['unsigned-archive','developer-archive','distribution-export']:
  name='acknowledgment-'+stage+'-UNCONFIGURED.json';ack=json.loads((out/name).read_text())
  assert ack['acknowledged'] is False
  ack.update(scope=manifest['scope'],executing_continuation='d57f4cd77813',
   adapter_sha256=sha(out/'run_release_stage.py'),support_sha256=sha(out/'release_support.py'),
   production_manifest_sha256=sha(out/'production-manifest.json'),
   original_deadline_utc='2026-11-17T22:26:12Z',explicit_user_extension_hours=24,extended_deadline_utc='2026-11-18T22:26:12Z',
   note='UNCONFIGURED R7 file-only preparation. Root must supply actual accepted R7 model and nineteen-case evidence, exact stage, fresh serial slot and verified store/signing identity. No upload action exists.')
  dump(out/name,ack)
 for name in ['publishing_runner_frozen.py','native_coordination_frozen.py','release-configuration-UNCONFIGURED.json']:
  assert (out/name).read_bytes()==(parent/name).read_bytes()
 diffs=[]
 for name in ['release_support.py','run_release_stage.py']:
  diffs.extend(difflib.unified_diff((parent/name).read_text().splitlines(True),(out/name).read_text().splitlines(True),fromfile='r6b/'+name,tofile='r7/'+name))
 (out/'adapter-from-r6b.diff').write_text(''.join(diffs))
 # Function-level check: the executed model gate itself remains byte-identical.
 def function(text,name):
  tree=ast.parse(text);node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name==name)
  return '\n'.join(text.splitlines()[node.lineno-1:node.end_lineno])
 assert function(before,'validate_model_gate')==function(support,'validate_model_gate')
 (out/'HANDOFF.md').write_text('''# HalalTag R7 production release preparation

Status: prepared files only; no archive, signing, export, upload or release.

Fourteen shipping files remain byte-identical to f2c27c9271da3a17bb01c50b6cdad94643e1d0f2.
They match the sealed R7 native candidate156c5eeb60eb1e06cf369235ed33af265460a9cb.
The release gate requires the exact R7 run, source path,47-file seal, adapter and
all three appearance/case-guard pins, real model compile/execute receipt, all nine
boundary labels, all19 original UI selectors passing with no skips, failures,
warnings or automatic retries, original result/evidence hashes, complete cleanup
and released own lock. Prior R6b16/19 is a failed gate and cannot authorize this.

The model gate, lifecycle and coordination implementation remain byte-identical.
All three stage acknowledgments and release identity configuration are deliberately
UNCONFIGURED. Root must verify an actual exclusive native slot and current signing/
store identity. No upload action is added. Parent R6b package and failures remain.

Original deadline2026-11-17T22:26:12Z; explicit user additional24h extends it to
2026-11-18T22:26:12Z, preserving the original start and budget history.
''')
 receipt=dict(status='FILE_ONLY_PREPARATION_NO_STAGE_EXECUTED',native_candidate_commit=NATIVE_COMMIT,
  shipping_candidate_commit=SHIPPING_COMMIT,shipping_files=14,all_shipping_bytes_unchanged=True,
  native_source_files=47,native_source_seal_sha256=NATIVE_SEAL,native_source_mac=path.as_posix(),
  parent_pins=PARENT_PINS,current_pins={name:sha(out/name) for name in PARENT_PINS},
  model_gate_function_unchanged=True,all19_case_specifications_unchanged=True,
  original_deadline_utc='2026-11-17T22:26:12Z',explicit_user_extension_hours=24,extended_deadline_utc='2026-11-18T22:26:12Z',
  budget_restarted=False,native_stage_invoked=False,release_adapter_invoked=False,
  signing_performed=False,upload_performed=False,configured_acknowledgment_created=False,
  preparer_sha256=sha(Path(__file__)))
 dump(out/'preparation-review.json',receipt);print(json.dumps(receipt,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
