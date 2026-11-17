#!/usr/bin/env python3
"""File-only R9 preparation. No native tools, signing, network, Git writes or upload."""
from pathlib import Path
import argparse, ast, difflib, hashlib, json, re, shutil, subprocess

PARENT_COMMIT = 'f2cd50817dbb0918e8ce85c6e47d31b337a6e25c'
PARENT_ADAPTER = '74ee000e6fc082954a3f9d176ec4bf2a1c8c508a75d19ef0a46cd90b91d2023c'
PARENT_SEAL = '241979e9ebe2d52be61dd4abb1060ad1f4d7f0fdbe85e3840d18c176391416be'
PARENT_CONTENT = 'b61194e8c199ce03d4950c39fa6a42f27fca061a11e7b99bb2da753c19c2fbec'
CONTENT = 'a694d60e5cde54e96ae497b5e04803cec11700206e6630b6346bc43c8b9163dc'
OLD_SCOPE = 'halaltag-production-composition-nineteen-journeys-r8'
NEW_SCOPE = 'halaltag-production-composition-nineteen-journeys-r9'
OLD_ID = 'com.saleh.halaltag.productioncomposition.qa.r20261117r8'
NEW_ID = 'com.saleh.halaltag.productioncomposition.qa.r20261117r9'
APP = 'HalalAnalyzer حلال ام حرام؟'
PARENT_PIN_INDEX = '45207e729192890cab32a6e57c71c3f93ddacebc580fe9fb858140a8c9daa3dc'
EXPECTED_UI = {
    'HalalTagPreparedUITests.swift': '334cd81ad14739c78257cde44d69c3d85987d50a52c034dbc5f41709d58c439c',
    'HalalTagArabicAppearanceUITests.swift': 'c48ba3e57194ff29fb0cfaaa57f2de00333a7442a2d5891709bf8119acf3959b',
}
CHANGED_SOURCE = {
    APP+'/ContentView.swift',
    'Tests/NativeQA/UITests/HalalTagPreparedUITests.swift',
    'Tests/NativeQA/UITests/HalalTagArabicAppearanceUITests.swift',
    'Tests/NativeQA/App/HalalTagQAApp.swift',
    'Tests/NativeQA/HalalTagQA.xcodeproj/project.pbxproj',
    'Tests/NativeQA/README.txt',
    'Tests/NativeQA/nineteen-case-plan.json',
    'Tests/NativeQA/UITests/HalalTagSyntheticQAInstallation.json',
    'Tests/validate_composition.py',
}

def sha(path):
    assert path.is_file() and not path.is_symlink(), path
    return hashlib.sha256(path.read_bytes()).hexdigest()

def dump(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2)+'\n')

def relative_file(root, name):
    part=Path(name)
    assert not part.is_absolute() and '..' not in part.parts
    file=root/part
    assert file.is_file() and not any(p.is_symlink() for p in [file,*file.parents]), file
    return file

def write_diff(out, name, before, after, label):
    (out/name).write_text(''.join(difflib.unified_diff(before.splitlines(True),after.splitlines(True),
        fromfile='r8/'+label,tofile='r9/'+label)))

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--parent-preparation',type=Path,required=True)
    parser.add_argument('--repository',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    parent,repo,out=(p.absolute() for p in (args.parent_preparation,args.repository,args.output))
    assert repo.resolve()==repo and parent.resolve()==parent
    assert out.is_relative_to(repo/'.git/recovery') and not out.exists()
    assert not any(p.is_symlink() for p in [out,*out.parents])
    def git(*args):return subprocess.check_output(['git','-C',str(repo),*args],text=True).strip()
    assert not git('status','--porcelain=v1'), 'A clean committed candidate is required'
    commit=git('rev-parse','HEAD')
    assert commit!=PARENT_COMMIT
    subprocess.run(['git','-C',str(repo),'merge-base','--is-ancestor',PARENT_COMMIT,commit],check=True)
    spec=repo/'publishing/r9'
    assert sha(spec/'parent-support-pins.json')==PARENT_PIN_INDEX
    pins=json.loads((spec/'parent-support-pins.json').read_text())
    assert len(pins)==24
    for row in pins:
        file=relative_file(parent,row['path'])
        assert sha(file)==row['sha256'] and file.stat().st_size==row['bytes']
    assert sha(parent/'run_halaltag_native_qa.py')==PARENT_ADAPTER
    assert sha(parent/'sealed-project-inputs.json')==PARENT_SEAL
    original=json.loads((parent/'sealed-project-inputs.json').read_text())['files']
    assert len(original)==47
    rows=[];changed=[]
    for row in original:
        old=relative_file(parent/'Source',row['path'])
        new=relative_file(repo,row['path'])
        assert sha(old)==row['sha256'] and old.stat().st_size==row['bytes']
        actual=sha(new)
        rows.append(dict(path=row['path'],sha256=actual,bytes=new.stat().st_size))
        if actual!=row['sha256']:changed.append(row['path'])
    assert set(changed)==CHANGED_SOURCE
    assert sha(repo/APP/'ContentView.swift')==CONTENT
    retention=[]
    method_count=0
    native_diff=''
    for old in sorted((parent/'Source/Tests/NativeQA/UITests').glob('*.swift')):
        current=repo/'Tests/NativeQA/UITests'/old.name
        before,after=old.read_text(),current.read_text()
        method_count+=len(re.findall(r'^    func test\w+\(',after,re.M))
        allowed=after
        if old.name in EXPECTED_UI:
            assert sha(current)==EXPECTED_UI[old.name]
            a,b=allowed.index('    private func drag('),allowed.index('    private func tap(')
            c,d=before.index('    private func drag('),before.index('    private func tap(')
            allowed=allowed[:a]+before[c:d]+allowed[b:]
            native_diff+=''.join(difflib.unified_diff(before[c:d].splitlines(True),after[a:b].splitlines(True),
                fromfile='r8/'+old.name,tofile='r9/'+old.name))
        if old.name=='HalalTagPreparedUITests.swift':
            assert allowed.count(CONTENT)==1
            allowed=allowed.replace(CONTENT,PARENT_CONTENT)
        assert allowed==before, old.name
        retention.append(dict(path=str(current.relative_to(repo)),parent_sha256=sha(old),
            candidate_sha256=sha(current),all_method_bodies_unchanged=True,
            helper_change='private drag only' if old.name in EXPECTED_UI else None))
    assert method_count==19
    old_plan=json.loads((parent/'Source/Tests/NativeQA/nineteen-case-plan.json').read_text())
    new_plan=json.loads((repo/'Tests/NativeQA/nineteen-case-plan.json').read_text())
    assert old_plan['cases']==new_plan['cases'] and new_plan['case_count']==19 and new_plan['retry_count']==0
    out.mkdir(parents=True)
    (out/'Source').mkdir();(out/'Tests').mkdir()
    for row in rows:
        destination=out/'Source'/row['path'];destination.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(repo/row['path'],destination)
    dump(out/'sealed-project-inputs.json',dict(schema_version=1,status='SEALED_PREPARED_SOURCE_ONLY',scope=NEW_SCOPE,files=rows))
    # Copy only the actual runtime, contracts and current evidence. Never copy an
    # old ACTUAL acknowledgment or historical failed native output.
    unchanged=['publishing_runner_frozen.py','appearance_png.py','system_size_evidence.py',
               'simctl-ui-help-root-20261117.stderr']
    for name in unchanged:shutil.copyfile(parent/name,out/name)
    for name in ['appearance_evidence_guard.py','arabic_appearance_evidence_guard.py','test_geometry_evidence.py',
                 'r8-en-ax5-route-input.json','r8-ar-ax5-route-input.json']:
        shutil.copyfile(spec/name,out/name)
    production=(parent/'production_case_evidence.py').read_text()
    assert OLD_ID in production
    (out/'production_case_evidence.py').write_text(production.replace(OLD_ID,NEW_ID))
    before=(parent/'run_halaltag_native_qa.py').read_text()
    after=before.replace(OLD_SCOPE,NEW_SCOPE).replace(OLD_ID,NEW_ID).replace('ProductionCompositionR8-NativeQA','ProductionCompositionR9-NativeQA')
    pin_names={'SEAL_SHA':'sealed-project-inputs.json','EVIDENCE_GUARD_SHA':'appearance_evidence_guard.py',
               'ARABIC_GUARD_SHA':'arabic_appearance_evidence_guard.py','NINETEEN_GUARD_SHA':'production_case_evidence.py'}
    old_pins={}
    for key,name in pin_names.items():
        match=re.search('^'+key+' = "([0-9a-f]+)"',after,re.M);assert match
        old_pins[key]=match.group(1)
        after,count=re.subn('^'+key+' = "[0-9a-f]+"',key+' = "'+sha(out/name)+'"',after,flags=re.M);assert count==1
    ast.parse(after)
    restored=after.replace(NEW_SCOPE,OLD_SCOPE).replace(NEW_ID,OLD_ID).replace('ProductionCompositionR9-NativeQA','ProductionCompositionR8-NativeQA')
    for key,name in pin_names.items():
        restored=restored.replace(key+' = "'+sha(out/name)+'"',key+' = "'+old_pins[key]+'"')
    assert restored==before, 'Only exact adapter source/guard pins and R9 identity may change'
    (out/'run_halaltag_native_qa.py').write_text(after)
    write_diff(out,'adapter-from-r8.diff',before,after,'run_halaltag_native_qa.py')
    for name in ['appearance_evidence_guard.py','arabic_appearance_evidence_guard.py']:
        write_diff(out,name+'.from-r8.diff',(parent/name).read_text(),(out/name).read_text(),name)
    write_diff(out,'product-from-r8.patch',(parent/'Source'/APP/'ContentView.swift').read_text(),
               (repo/APP/'ContentView.swift').read_text(),'ContentView.swift')
    (out/'native-drag-from-r8.patch').write_text(native_diff)
    shipping=[row for row in rows if row['path'].startswith(APP)]
    assert len(shipping)==14 and [row['path'] for row in shipping if row['path'] in changed]==[APP+'/ContentView.swift']
    dump(out/'shipping-retention.json',dict(shipping_commit=commit,parent_shipping_commit=PARENT_COMMIT,
        byte_identical=False,unchanged_file_count=13,changed_files=[APP+'/ContentView.swift'],files=shipping))
    dump(out/'source-retention.json',dict(status='SOURCE_ONLY_NOT_NATIVE_TESTED',parent_native_commit=PARENT_COMMIT,
        candidate_commit=commit,all_nineteen_method_bodies_unchanged=True,unfiltered_audits_unchanged=True,
        gesture_operation_and_case_budgets_unchanged=True,helpers_unchanged=False,
        helper_change='Both measured gutters and recorded interactive action exclusion in private drag only',
        source_files_changed=changed,source_files_unchanged=47-len(changed),files=retention))
    ack=json.loads((parent/'coordinator-acknowledgment-UNCONFIGURED.json').read_text())
    assert ack['acknowledged'] is False and all(ack[k] is None for k in ['coordinator','coordinator_reference','slot_id','acknowledged_at','window_starts_at','window_ends_at'])
    ack.update(scope=NEW_SCOPE,candidate_content_sha256=CONTENT,
        preparation_revision='R9-semantic-link-color-language-alignment-and-measured-safe-routes',
        note='UNCONFIGURED R9: root must allocate one fresh exclusive slot. R8 finished211model/15of19UI;R9 not run. All19 methods/audits,finite45min batch120s cleanup/20min percase and zero retries retained.')
    for key,name in [('adapter_sha256','run_halaltag_native_qa.py'),('sealed_index_sha256','sealed-project-inputs.json'),
                     ('appearance_guard_sha256','appearance_evidence_guard.py'),('arabic_guard_sha256','arabic_appearance_evidence_guard.py'),
                     ('nineteen_case_guard_sha256','production_case_evidence.py')]:ack[key]=sha(out/name)
    assert ack['extended_deadline_utc']=='2026-11-18T22:26:12Z' and ack['total_hard_cap_minutes']==45 and ack['cleanup_reserve_seconds']==120 and ack['per_case_timeout_seconds']==1200
    dump(out/'coordinator-acknowledgment-UNCONFIGURED.json',ack)
    reference=json.loads((parent/'reference-inputs.json').read_text())
    reference.update(candidate_commit=commit,shipping_source_commit=commit,parent_native_commit=PARENT_COMMIT,
        parent_shipping_source_commit=PARENT_COMMIT,parent_preparation=str(parent),parent_scope=OLD_SCOPE,
        parent_adapter_sha256=PARENT_ADAPTER,parent_seal_sha256=PARENT_SEAL,parent_content_view_sha256=PARENT_CONTENT,
        content_view_sha256=CONTENT,product_patch_sha256=sha(out/'product-from-r8.patch'),
        parent_native_run='20261117T183904Z-97763-72dad329c7',
        parent_native_result='211 model checks passed;15/19 UI passed,4 failed;cleanup complete/lock released',
        last_native_run='20261117T183904Z-97763-72dad329c7',last_native_result='FAILED15/19;not acceptance',
        preparation_revision=ack['preparation_revision'],native_execution='NOT_RUN',current_native_execution='NOT_RUN',
        model_regression_execution='NOT_RUN',current_model_regression_execution='NOT_RUN',
        geometry_guard_sha256=sha(out/'appearance_evidence_guard.py'),
        arabic_geometry_guard_sha256=sha(out/'arabic_appearance_evidence_guard.py'),
        timing_provenance='R8elapsed2137.487s;ENAX5454.702s;ARAX5598.920s;R9durationunmeasured;45mincapunchanged')
    dump(out/'reference-inputs.json',reference)
    contract=(parent/'Tests/test_adapter_contract.py').read_text().replace(OLD_SCOPE,NEW_SCOPE).replace('synthetic-r8-45-window','synthetic-r9-45-window')
    ast.parse(contract);(out/'Tests/test_adapter_contract.py').write_text(contract)
    shutil.copyfile(spec/'README.md',out/'HANDOFF.txt')
    assert all(sha(out/name)==sha(parent/name) for name in unchanged)
    assert all(sha(out/'Source'/row['path'])==row['sha256'] for row in rows)
    support=[dict(path=str(f.relative_to(out)),bytes=f.stat().st_size,sha256=sha(f))
             for f in sorted(out.rglob('*')) if f.is_file() and 'Source' not in f.relative_to(out).parts]
    assert len(support)==23
    receipt=dict(status='SEALED_FILE_ONLY_PREPARATION_NOT_NATIVE_ACCEPTANCE',candidate_commit=commit,
        candidate_tree=git('rev-parse','HEAD^{tree}'),parent_commit=PARENT_COMMIT,
        source_file_count=47,support_file_count=len(support),support_files=support,
        seal_sha256=sha(out/'sealed-project-inputs.json'),adapter_sha256=sha(out/'run_halaltag_native_qa.py'),
        lifecycle_sha256=sha(out/'publishing_runner_frozen.py'),acknowledged=False,
        native_invoked=False,push_invoked=False,signing_invoked=False,store_upload_invoked=False,
        output=str(out),original_deadline_utc='2026-11-17T22:26:12Z',explicit_user_extension_hours=24,
        extended_deadline_utc='2026-11-18T22:26:12Z',budget_restarted=False)
    dump(out.parent/(out.name+'-INPUT-MANIFEST.json'),receipt)
    print(json.dumps(receipt,indent=2))

if __name__=='__main__':main()
