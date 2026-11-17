#!/usr/bin/env python3
"""Seal the reviewed R8 source with unchanged R7 journeys and lifecycle.

File-only preparation: no native, simulator, build, push, or network execution.
"""
from pathlib import Path
import argparse, ast, difflib, hashlib, json, re, shutil, subprocess

PARENT_COMMIT = '19256d4001b86363297f4a71f97b64f797b2933a'
PARENT_NATIVE_COMMIT = '156c5eeb60eb1e06cf369235ed33af265460a9cb'
PARENT_SHIPPING_COMMIT = 'f2c27c9271da3a17bb01c50b6cdad94643e1d0f2'
PARENT_ADAPTER = 'e0becc1b7320367dc30d8a1187ccf3ebe1d0bec652b34fe50a082d131fae1b4f'
PARENT_SEAL = '49c63a850d040e6428c90ce8597c742d8df3f7ee7cb0484643ac152787fcea0d'
PARENT_CONTENT = '06b6d75101b40eb4b99b9b59c1de876e54b6df85f772b3ed633f7fcf1a83a2fc'
CONTENT = 'b61194e8c199ce03d4950c39fa6a42f27fca061a11e7b99bb2da753c19c2fbec'
OLD_SCOPE = 'halaltag-production-composition-nineteen-journeys-r7'
NEW_SCOPE = 'halaltag-production-composition-nineteen-journeys-r8'
OLD_ID = 'com.saleh.halaltag.productioncomposition.qa.r20261117r7'
NEW_ID = 'com.saleh.halaltag.productioncomposition.qa.r20261117r8'
APP = 'HalalAnalyzer حلال ام حرام؟'

def sha(path):
    assert path.is_file() and not path.is_symlink()
    return hashlib.sha256(path.read_bytes()).hexdigest()

def dump(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2)+'\n')

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--parent-preparation', type=Path, required=True)
    parser.add_argument('--repository', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    parent, repo, out = (p.resolve() for p in (args.parent_preparation,args.repository,args.output))
    assert sha(parent/'run_halaltag_native_qa.py') == PARENT_ADAPTER
    assert sha(parent/'sealed-project-inputs.json') == PARENT_SEAL
    assert not subprocess.check_output(['git','-C',str(repo),'status','--porcelain=v1'],text=True)
    subprocess.run(['git','-C',str(repo),'merge-base','--is-ancestor',PARENT_COMMIT,'HEAD'],check=True)
    commit = subprocess.check_output(['git','-C',str(repo),'rev-parse','HEAD'],text=True).strip()
    assert not out.exists() and not any(p.is_symlink() for p in parent.rglob('*'))
    original = json.loads((parent/'sealed-project-inputs.json').read_text())['files']
    assert len(original) == 47 and sha(repo/APP/'ContentView.swift') == CONTENT
    for row in original: assert sha(parent/'Source'/row['path']) == row['sha256']
    shutil.copytree(parent,out)
    rows = []
    for row in original:
        path = Path(row['path']); assert not path.is_absolute() and '..' not in path.parts
        source = repo/path; assert source.is_file() and not source.is_symlink()
        shutil.copyfile(source,out/'Source'/path)
        rows.append(dict(path=path.as_posix(),sha256=sha(source),bytes=source.stat().st_size))
    dump(out/'sealed-project-inputs.json',dict(schema_version=1,status='SEALED_PREPARED_SOURCE_ONLY',scope=NEW_SCOPE,files=rows))
    shipping = []; changed = []
    for row in rows:
        name = row['path']
        if not name.startswith(APP): continue
        actual = (repo/name).read_bytes()
        previous = subprocess.check_output(['git','-C',str(repo),'show',PARENT_SHIPPING_COMMIT+':'+name])
        if actual != previous: changed.append(name)
        shipping.append(dict(path=name,sha256=hashlib.sha256(actual).hexdigest(),bytes=len(actual)))
    assert len(shipping)==14 and changed==[APP+'/ContentView.swift']
    dump(out/'shipping-retention.json',dict(shipping_commit=commit,parent_shipping_commit=PARENT_SHIPPING_COMMIT,
        byte_identical=False,unchanged_file_count=13,changed_files=changed,files=shipping))
    before_content=(parent/'Source'/APP/'ContentView.swift').read_text()
    after_content=(repo/APP/'ContentView.swift').read_text()
    (out/'product-from-r7.patch').write_text(''.join(difflib.unified_diff(before_content.splitlines(True),after_content.splitlines(True),fromfile='r7/ContentView.swift',tofile='r8/ContentView.swift')))
    for name in ['appearance_evidence_guard.py','arabic_appearance_evidence_guard.py','production_case_evidence.py']:
        text=(parent/name).read_text(); assert OLD_ID in text
        (out/name).write_text(text.replace(OLD_ID,NEW_ID))
        assert (out/name).read_text().replace(NEW_ID,OLD_ID)==text
    before=(parent/'run_halaltag_native_qa.py').read_text()
    after=before.replace(OLD_SCOPE,NEW_SCOPE).replace(OLD_ID,NEW_ID).replace('ProductionCompositionR7-NativeQA','ProductionCompositionR8-NativeQA')
    for key,name in {'SEAL_SHA':'sealed-project-inputs.json','EVIDENCE_GUARD_SHA':'appearance_evidence_guard.py',
                     'ARABIC_GUARD_SHA':'arabic_appearance_evidence_guard.py','NINETEEN_GUARD_SHA':'production_case_evidence.py'}.items():
        after,count=re.subn('^'+key+' = "[0-9a-f]+"',key+' = "'+sha(out/name)+'"',after,flags=re.M); assert count==1
    ast.parse(after);(out/'run_halaltag_native_qa.py').write_text(after)
    (out/'adapter-from-r7.diff').write_text(''.join(difflib.unified_diff(before.splitlines(True),after.splitlines(True),fromfile='r7/run_halaltag_native_qa.py',tofile='r8/run_halaltag_native_qa.py')))
    retention=[]
    for old in sorted((parent/'Source/Tests/NativeQA/UITests').glob('*.swift')):
        current=out/'Source'/old.relative_to(parent/'Source')
        if old.name=='HalalTagPreparedUITests.swift':
            assert old.read_text().count(PARENT_CONTENT)==1 and current.read_text().count(CONTENT)==1
            assert old.read_text().replace(PARENT_CONTENT,CONTENT)==current.read_text()
        else: assert old.read_bytes()==current.read_bytes()
        retention.append(dict(path=current.relative_to(out/'Source').as_posix(),parent_sha256=sha(old),candidate_sha256=sha(current),
                              all_method_and_helper_bodies_identical=True,entire_file_identical=old.read_bytes()==current.read_bytes()))
    dump(out/'source-retention.json',dict(status='SOURCE_ONLY_NOT_NATIVE_TESTED',all_nineteen_method_bodies_unchanged=True,
        helpers_and_gesture_budgets_unchanged=True,unfiltered_audits_unchanged=True,shipping_f2_bytes_unchanged=False,
        shipping_change='Only ContentView: exact entryScope native renderer and explicit Clear return to real input',files=retention))
    ack=json.loads((out/'coordinator-acknowledgment-UNCONFIGURED.json').read_text());assert ack['acknowledged'] is False
    ack.update(scope=NEW_SCOPE,executing_continuation='d57f4cd77813',preparation_revision='R8-entry-scope-and-explicit-clear-return',
        candidate_content_sha256=CONTENT,
        original_deadline_utc='2026-11-17T22:26:12Z',explicit_user_extension_hours=24,extended_deadline_utc='2026-11-18T22:26:12Z',
        budget_restarted=False,note='UNCONFIGURED R8; fresh root-owned exclusive native slot required. R7 failed17/19; R8 has not run. All19 original journeys, helpers, audits and budgets retained.')
    for key,name in [('adapter_sha256','run_halaltag_native_qa.py'),('sealed_index_sha256','sealed-project-inputs.json'),
                     ('appearance_guard_sha256','appearance_evidence_guard.py'),('arabic_guard_sha256','arabic_appearance_evidence_guard.py'),
                     ('nineteen_case_guard_sha256','production_case_evidence.py')]:ack[key]=sha(out/name)
    dump(out/'coordinator-acknowledgment-UNCONFIGURED.json',ack)
    reference=json.loads((out/'reference-inputs.json').read_text())
    reference.update(candidate_commit=commit,shipping_source_commit=commit,parent_preparation=str(parent),parent_native_commit=PARENT_NATIVE_COMMIT,
        parent_scope=OLD_SCOPE,parent_adapter_sha256=PARENT_ADAPTER,parent_seal_sha256=PARENT_SEAL,
        parent_native_run='20261117T170914Z-39588-7dd1ee578a',parent_native_result='211 model checks passed;17/19 UI passed,2 failed;cleanup complete/lock released',
        last_native_run='20261117T170914Z-39588-7dd1ee578a',last_native_result='FAILED17/19;not acceptance',
        preparation_revision='R8-entry-scope-and-explicit-clear-return',native_execution='NOT_RUN',current_native_execution='NOT_RUN',
        current_model_regression_execution='NOT_RUN',model_regression_execution='NOT_RUN',
        content_view_sha256=CONTENT,parent_content_view_sha256=PARENT_CONTENT,product_patch_sha256=sha(out/'product-from-r7.patch'),
        parent_shipping_source_commit=PARENT_SHIPPING_COMMIT,
        geometry_guard_sha256=sha(out/'appearance_evidence_guard.py'),arabic_geometry_guard_sha256=sha(out/'arabic_appearance_evidence_guard.py'),
        original_deadline_utc='2026-11-17T22:26:12Z',explicit_user_extension_hours=24,extended_deadline_utc='2026-11-18T22:26:12Z')
    dump(out/'reference-inputs.json',reference)
    contract=(parent/'Tests/test_adapter_contract.py').read_text().replace(OLD_SCOPE,NEW_SCOPE)
    old_assert="self.assertTrue(retained['byte_identical']);self.assertEqual(len(retained['files']),14)"
    new_assert="self.assertFalse(retained['byte_identical']);self.assertEqual(len(retained['files']),14)\n        self.assertEqual(retained['unchanged_file_count'],13)\n        self.assertEqual(retained['changed_files'],['HalalAnalyzer حلال ام حرام؟/ContentView.swift'])"
    assert contract.count(old_assert)==1;contract=contract.replace(old_assert,new_assert)
    ast.parse(contract);(out/'Tests/test_adapter_contract.py').write_text(contract)
    shutil.copyfile(repo/'publishing/r8/README.md',out/'HANDOFF.txt')
    for name in ['publishing_runner_frozen.py','appearance_png.py','system_size_evidence.py','simctl-ui-help-root-20261117.stderr','test_geometry_evidence.py']:
        assert sha(out/name)==sha(parent/name),name
    for row in rows:assert sha(out/'Source'/row['path'])==row['sha256']
    print(json.dumps(dict(candidate_commit=commit,shipping_commit=commit,source_files=47,shipping_files_changed=1,
        adapter_sha256=sha(out/'run_halaltag_native_qa.py'),seal_sha256=sha(out/'sealed-project-inputs.json'),
        acknowledged=False,native_execution='NOT_RUN',output=str(out)),indent=2))

if __name__=='__main__':main()
