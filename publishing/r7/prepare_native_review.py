#!/usr/bin/env python3
"""Seal a fresh R7 helper package; no Mac/native/build/upload execution."""
from pathlib import Path
import argparse
import ast
import difflib
import hashlib
import json
import re
import shutil
import subprocess

PARENT_COMMIT = 'aa7f756e6c4bb5441e6945e4454141756934252f'
SHIPPING_COMMIT = 'f2c27c9271da3a17bb01c50b6cdad94643e1d0f2'
PARENT_ADAPTER = '92e8acefece9e3cc297e7c1600673ca0673976337a8e90559ab063794b6848a5'
PARENT_SEAL = '2da71c3c9e9da9a472af9fdd380ad7585164ccbf5da7de0e8156007b7d589464'
OLD_SCOPE = 'halaltag-production-composition-nineteen-journeys-r6'
NEW_SCOPE = 'halaltag-production-composition-nineteen-journeys-r7'
OLD_ID = 'com.saleh.halaltag.productioncomposition.qa.r20261117r6'
NEW_ID = 'com.saleh.halaltag.productioncomposition.qa.r20261117r7'


def sha(path):
    assert path.is_file() and not path.is_symlink()
    return hashlib.sha256(path.read_bytes()).hexdigest()


def dump(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2)+'\n')


def functions(text):
    # Reuse the reviewed quote/comment-aware source scanner, without importing
    # a native adapter or executing any Swift/Xcode/simulator code.
    module=ast.parse(text)
    body=[n for n in module.body if isinstance(n,ast.FunctionDef) and n.name in ('method_bodies','function_bodies')]
    assert len(body)==2
    scope={'re':re}
    exec(compile(ast.Module(body=body,type_ignores=[]),'<pure Swift body scanner>','exec'),scope)
    return scope


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--parent-preparation',type=Path,required=True)
    parser.add_argument('--repository',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();parent,repo,out=(p.resolve() for p in (args.parent_preparation,args.repository,args.output))
    assert sha(parent/'run_halaltag_native_qa.py')==PARENT_ADAPTER
    assert sha(parent/'sealed-project-inputs.json')==PARENT_SEAL
    assert not subprocess.check_output(['git','-C',str(repo),'status','--porcelain=v1'],text=True),'Commit reviewed source before sealing'
    subprocess.run(['git','-C',str(repo),'merge-base','--is-ancestor',PARENT_COMMIT,'HEAD'],check=True)
    commit=subprocess.check_output(['git','-C',str(repo),'rev-parse','HEAD'],text=True).strip()
    assert not out.exists() and not any(p.is_symlink() for p in parent.rglob('*'))
    original_rows=json.loads((parent/'sealed-project-inputs.json').read_text())['files']
    assert len(original_rows)==47
    for row in original_rows:
        assert sha(parent/'Source'/row['path'])==row['sha256']
    shutil.copytree(parent,out)
    rows=[]
    for row in original_rows:
        path=Path(row['path']);assert not path.is_absolute() and '..' not in path.parts
        source=repo/path;assert source.is_file() and not source.is_symlink()
        shutil.copyfile(source,out/'Source'/path)
        rows.append(dict(path=path.as_posix(),sha256=sha(source),bytes=source.stat().st_size))
    dump(out/'sealed-project-inputs.json',dict(schema_version=1,status='SEALED_PREPARED_SOURCE_ONLY',scope=NEW_SCOPE,files=rows))
    # The exact fourteen production files from the previous release manifest
    # are also derivable from the preserved native source inventory. Preserve
    # every shipping-code/resource/project byte, not just the four main pins.
    shipping=[]
    for row in rows:
        name=row['path']
        if name.startswith('HalalAnalyzer حلال ام حرام؟'):
            actual=(repo/name).read_bytes()
            assert actual==subprocess.check_output(['git','-C',str(repo),'show',SHIPPING_COMMIT+':'+name])
            shipping.append(dict(path=name,sha256=hashlib.sha256(actual).hexdigest(),bytes=len(actual)))
    assert len(shipping)==14
    dump(out/'shipping-retention.json',dict(shipping_commit=SHIPPING_COMMIT,byte_identical=True,files=shipping))
    for name in ['appearance_evidence_guard.py','arabic_appearance_evidence_guard.py','test_geometry_evidence.py']:
        shutil.copyfile(repo/'publishing/r7'/name,out/name)
    p=out/'production_case_evidence.py';p.write_text(p.read_text().replace(OLD_ID,NEW_ID))
    before=(parent/'run_halaltag_native_qa.py').read_text()
    after=before.replace(OLD_SCOPE,NEW_SCOPE).replace(OLD_ID,NEW_ID).replace('ProductionCompositionR6-NativeQA','ProductionCompositionR7-NativeQA')
    for key,name in {'SEAL_SHA':'sealed-project-inputs.json','EVIDENCE_GUARD_SHA':'appearance_evidence_guard.py',
                     'ARABIC_GUARD_SHA':'arabic_appearance_evidence_guard.py','NINETEEN_GUARD_SHA':'production_case_evidence.py'}.items():
        after,count=re.subn('^'+key+' = "[0-9a-f]+"',key+' = "'+sha(out/name)+'"',after,flags=re.M);assert count==1
    ast.parse(after);(out/'run_halaltag_native_qa.py').write_text(after)
    (out/'adapter-from-r6b.diff').write_text(''.join(difflib.unified_diff(before.splitlines(True),after.splitlines(True),fromfile='r6b/run_halaltag_native_qa.py',tofile='r7/run_halaltag_native_qa.py')))
    for name in ['appearance_evidence_guard.py','arabic_appearance_evidence_guard.py']:
        (out/(name+'.from-r6b.diff')).write_text(''.join(difflib.unified_diff((parent/name).read_text().splitlines(True),(out/name).read_text().splitlines(True),fromfile='r6b/'+name,tofile='r7/'+name)))
    scanner=functions((repo/'Tests/validate_composition.py').read_text());retention=[]
    for old in sorted((parent/'Source/Tests/NativeQA/UITests').glob('*.swift')):
        current=out/'Source'/old.relative_to(parent/'Source')
        assert scanner['method_bodies'](old.read_text())==scanner['method_bodies'](current.read_text())
        retention.append(dict(path=current.relative_to(out/'Source').as_posix(),parent_sha256=sha(old),candidate_sha256=sha(current),
                              all_method_bodies_identical=True,entire_file_identical=old.read_bytes()==current.read_bytes()))
    dump(out/'source-retention.json',dict(status='SOURCE_ONLY_NOT_NATIVE_TESTED',all_nineteen_method_bodies_unchanged=True,
        shipping_f2_bytes_unchanged=True,helpers_and_gesture_budgets_unchanged=False,
        helper_changes='R7 measured-distance navigation, separate audit recovery, fully exposed online-link poses; unfiltered audit unchanged',files=retention))
    ack=json.loads((out/'coordinator-acknowledgment-UNCONFIGURED.json').read_text());assert ack['acknowledged'] is False
    ack.update(scope=NEW_SCOPE,executing_continuation='d57f4cd77813',preparation_revision='R7-measured-geometry-and-audit-recovery',
        original_deadline_utc='2026-11-17T22:26:12Z',explicit_user_extension_hours=24,extended_deadline_utc='2026-11-18T22:26:12Z',
        budget_restarted=False,note='UNCONFIGURED R7; fresh root-owned exclusive native slot and exact source/package pins required. All shipping f2 bytes retained. Original deadline explicitly extended by the user, not restarted.')
    for key,name in [('adapter_sha256','run_halaltag_native_qa.py'),('sealed_index_sha256','sealed-project-inputs.json'),
                     ('appearance_guard_sha256','appearance_evidence_guard.py'),('arabic_guard_sha256','arabic_appearance_evidence_guard.py'),
                     ('nineteen_case_guard_sha256','production_case_evidence.py')]:ack[key]=sha(out/name)
    dump(out/'coordinator-acknowledgment-UNCONFIGURED.json',ack)
    reference=json.loads((out/'reference-inputs.json').read_text())
    reference.update(candidate_commit=commit,shipping_source_commit=SHIPPING_COMMIT,parent_preparation=str(parent),
        parent_scope=OLD_SCOPE,parent_adapter_sha256=PARENT_ADAPTER,parent_seal_sha256=PARENT_SEAL,
        parent_native_run='20261117T160346Z-2944-09b5555115',parent_native_result='211 model checks passed;16/19 UI passed,3 failed;cleanup complete/lock released',
        last_native_run='20261117T160346Z-2944-09b5555115',last_native_result='FAILED16/19;not acceptance',
        preparation_revision='R7-measured-geometry-and-audit-recovery',native_execution='NOT_RUN',current_native_execution='NOT_RUN',
        current_model_regression_execution='NOT_RUN',model_regression_execution='NOT_RUN',
        geometry_guard_sha256=sha(out/'appearance_evidence_guard.py'),arabic_geometry_guard_sha256=sha(out/'arabic_appearance_evidence_guard.py'),
        original_deadline_utc='2026-11-17T22:26:12Z',explicit_user_extension_hours=24,extended_deadline_utc='2026-11-18T22:26:12Z')
    dump(out/'reference-inputs.json',reference)
    contract=(parent/'Tests/test_adapter_contract.py').read_text().replace(OLD_SCOPE,NEW_SCOPE)
    start=contract.index('    def test_all_nine_executable_fixtures_preserved_except_reviewed_source_binding(self):')
    end=contract.index('    def test_arabic_guard_preserves_all_original_audit_geometry_thresholds(self):',start)
    replacement='''    def test_original_nineteen_methods_and_unrelated_helpers_remain_unchanged(self):
        import re
        sys.path.insert(0,str(ROOT/'Source/Tests'))
        import validate_composition as source
        new=ROOT/'Source/Tests/NativeQA/UITests'
        old=ROOT/'Source/Tests/Evidence/ReviewedNine'
        changed={'journey','readPorkEvidence','reveal','readBlock','drag','capture'}
        for name in ['HalalTagPreparedUITests.swift','HalalTagArabicAppearanceUITests.swift','HalalTagLanguageStateUITests.swift']:
            previous=(old/(name+'.txt')).read_text();current=(new/name).read_text()
            self.assertEqual(source.method_bodies(previous),source.method_bodies(current))
            if name=='HalalTagLanguageStateUITests.swift':self.assertEqual(previous,current)
            else:
                a,b=source.function_bodies(previous),source.function_bodies(current)
                for key,body in a.items():
                    if key not in changed:self.assertEqual(body,b[key],key)
                self.assertEqual(a['audit'],b['audit'])
                self.assertNotIn('issueHandler',current)
                self.assertNotIn('catch',b['auditPreservingViewport'])
        retained=json.loads((ROOT/'shipping-retention.json').read_text())
        self.assertTrue(retained['byte_identical']);self.assertEqual(len(retained['files']),14)
        for row in retained['files']:
            self.assertEqual(hashlib.sha256((ROOT/'Source'/row['path']).read_bytes()).hexdigest(),row['sha256'])

    def test_r7_guard_pins_replace_obsolete_budget_claims_explicitly(self):
        reference=json.loads((ROOT/'reference-inputs.json').read_text())
        self.assertEqual(hashlib.sha256((ROOT/'appearance_evidence_guard.py').read_bytes()).hexdigest(),reference['geometry_guard_sha256'])
        self.assertEqual(hashlib.sha256((ROOT/'arabic_appearance_evidence_guard.py').read_bytes()).hexdigest(),reference['arabic_geometry_guard_sha256'])
        self.assertEqual(appearance.CASE_GESTURE_LIMIT,168)
        self.assertEqual(appearance.CAPTURE_LIMIT,400)
        self.assertEqual(appearance.ATTACHMENT_LIMIT,2944)

'''
    contract=contract[:start]+replacement+contract[end:]
    # The existing module imports English guard as 'appearance' in the adapter;
    # tests use that exact pinned instance.
    contract=contract.replace('self.assertEqual(appearance.CASE_GESTURE_LIMIT','self.assertEqual(adapter.appearance.CASE_GESTURE_LIMIT')
    contract=contract.replace('self.assertEqual(appearance.CAPTURE_LIMIT','self.assertEqual(adapter.appearance.CAPTURE_LIMIT')
    contract=contract.replace('self.assertEqual(appearance.ATTACHMENT_LIMIT','self.assertEqual(adapter.appearance.ATTACHMENT_LIMIT')
    ast.parse(contract);(out/'Tests/test_adapter_contract.py').write_text(contract)
    shutil.copyfile(repo/'publishing/r7/README.md',out/'HANDOFF.txt')
    for name in ['publishing_runner_frozen.py','appearance_png.py','system_size_evidence.py','simctl-ui-help-root-20261117.stderr']:
        assert sha(out/name)==sha(parent/name),name
    for row in rows:assert sha(out/'Source'/row['path'])==row['sha256']
    print(json.dumps(dict(candidate_commit=commit,shipping_commit=SHIPPING_COMMIT,source_files=len(rows),
        adapter_sha256=sha(out/'run_halaltag_native_qa.py'),seal_sha256=sha(out/'sealed-project-inputs.json'),
        acknowledged=False,native_execution='NOT_RUN',output=str(out)),indent=2))

if __name__=='__main__':main()
