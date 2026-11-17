#!/usr/bin/env python3
"""Reconstruct exactly the frozen R7 native inputs from local bare Git objects.

Read-only Git commands; exclusive creation of a fresh preparation and receipt.
No fetching, ref updates, checkout, hook/filter execution, acknowledgment
configuration, native/build/test/release execution, network or store action.
"""
from pathlib import Path, PurePosixPath
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
import stat
import subprocess
import sys

HERE=Path(__file__).resolve().parent
COMMIT='156c5eeb60eb1e06cf369235ed33af265460a9cb'
TREE='a12a81a8fb1a0fe9085fc316aca8d9eedd7bd718'
PARENT='aa7f756e6c4bb5441e6945e4454141756934252f'
SHIPPING='f2c27c9271da3a17bb01c50b6cdad94643e1d0f2'
SCOPE='halaltag-production-composition-nineteen-journeys-r7'
SUPPORT_MANIFEST_SHA='1111dfbf6b9159579b6e9ee94d82687f903be0ce2e111c6babb708639f495c95'
SEAL_SHA='49c63a850d040e6428c90ce8597c742d8df3f7ee7cb0484643ac152787fcea0d'
ADAPTER_SHA='e0becc1b7320367dc30d8a1187ccf3ebe1d0bec652b34fe50a082d131fae1b4f'
LIFECYCLE_SHA='1980cdf5a564a802198183fd79ee2f0a325b486908bab45e01beaadb02e50f99'


def require(ok,message):
 if not ok:raise RuntimeError(message)


def digest(raw):return hashlib.sha256(raw).hexdigest()


def safe_relative(value):
 require(isinstance(value,str) and value and '\\' not in value and '\0' not in value,'Invalid relative path')
 path=PurePosixPath(value)
 require(not path.is_absolute() and path.as_posix()==value and all(p not in ('','.','..') for p in path.parts),
         'Unsafe relative path: '+value)
 return path


def existing_regular(path):
 require(path.is_file() and not path.is_symlink(),'Missing/linked file: '+str(path))
 return path.read_bytes()


def no_link_ancestors(path):
 for parent in (path,*path.parents):
  if parent.exists() or parent.is_symlink():
   require(not parent.is_symlink(),'A staging/Git path uses a symlink: '+str(parent))


def git(bare,*args):
 result=subprocess.run(['git','--no-optional-locks','--git-dir='+str(bare),*args],
  stdout=subprocess.PIPE,stderr=subprocess.PIPE,check=False)
 require(result.returncode==0,'Local read-only Git operation failed: '+' '.join(args)+'\n'+result.stderr.decode('utf-8',errors='replace'))
 return result.stdout


def git_tree(bare,commit):
 rows={}
 for item in git(bare,'ls-tree','-r','-z',commit).split(b'\0'):
  if not item:continue
  meta,name=item.split(b'\t',1);mode,kind,oid=meta.decode('ascii').split(' ')
  relative=name.decode('utf-8');safe_relative(relative)
  require(relative not in rows,'Duplicate Git path')
  rows[relative]=dict(mode=mode,kind=kind,oid=oid)
 return rows


def blob(bare,row):
 require(row['kind']=='blob' and row['mode'] in ('100644','100755'),'Native input is not a regular Git blob')
 raw=git(bare,'cat-file','blob',row['oid'])
 require(hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()==row['oid'],'Git blob identity differs')
 return raw


def write_new(path,raw,mode=0o644):
 path.parent.mkdir(parents=True,exist_ok=True)
 with path.open('xb') as file:file.write(raw)
 os.chmod(path,mode)
 require(existing_regular(path)==raw,'Written staging bytes differ: '+str(path))


def main():
 parser=argparse.ArgumentParser(description=__doc__)
 parser.add_argument('--bare-repository',type=Path,required=True)
 parser.add_argument('--output-preparation',type=Path,required=True)
 args=parser.parse_args()
 bare=args.bare_repository.expanduser().absolute();out=args.output_preparation.expanduser().absolute()
 require('..' not in bare.parts and '..' not in out.parts,'Parent traversal is not allowed')
 no_link_ancestors(bare);no_link_ancestors(out)
 bare=bare.resolve();out=out.resolve()
 require(bare.is_dir() and not out.exists(),'Bare repository missing or preparation already exists; refusing overwrite')
 require(out.name=='preparation','Output must be a fresh preparation directory')
 require(not out.is_relative_to(bare) and not bare.is_relative_to(out),'Output and Git repository must be separate')
 receipt_path=out.parent/'STAGING-RECEIPT.json'
 require(not receipt_path.exists() and not receipt_path.is_symlink(),'Staging receipt already exists; refusing overwrite')
 support_root=HERE/'native-support'
 require(support_root.is_dir() and not support_root.is_symlink(),'Support directory missing or linked')
 raw_manifest=existing_regular(HERE/'support-manifest.json')
 require(digest(raw_manifest)==SUPPORT_MANIFEST_SHA,'Support manifest differs from the reviewed stager')
 manifest=json.loads(raw_manifest)
 require(manifest['native_commit']==COMMIT and manifest['native_tree']==TREE and manifest['native_source_count']==47,
         'Support manifest names a different candidate')
 support={}
 for row in manifest['files']:
  relative=safe_relative(row['path']).as_posix();require(relative not in support,'Duplicate support path')
  raw=existing_regular(support_root/relative)
  require(len(raw)==row['bytes'] and digest(raw)==row['sha256'],'Support bytes differ: '+relative)
  support[relative]=raw
 actual=[]
 for path in support_root.rglob('*'):
  require(not path.is_symlink(),'Linked support entry')
  if path.is_file():actual.append(path.relative_to(support_root).as_posix())
 require(len(support)==manifest['support_file_count']==22 and set(actual)==set(support),'Support inventory differs')
 require(digest(support['sealed-project-inputs.json'])==SEAL_SHA,'Frozen 47-file seal differs')
 require(digest(support['run_halaltag_native_qa.py'])==ADAPTER_SHA,'Native adapter differs')
 require(digest(support['publishing_runner_frozen.py'])==LIFECYCLE_SHA,'Frozen lifecycle differs')
 seal=json.loads(support['sealed-project-inputs.json'])
 require(seal['scope']==SCOPE and len(seal['files'])==47,'Wrong native source scope/count')
 acknowledgment=json.loads(support['coordinator-acknowledgment-UNCONFIGURED.json'])
 require(acknowledgment['acknowledged'] is False and acknowledgment['scope']==SCOPE and
         acknowledgment['adapter_sha256']==ADAPTER_SHA and acknowledgment['sealed_index_sha256']==SEAL_SHA,
         'Acknowledgment is configured or not bound to this frozen package')
 require(git(bare,'rev-parse','--is-bare-repository').strip()==b'true','Expected the existing bare checkpoint, not a worktree')
 require(git(bare,'rev-parse','--verify',COMMIT+'^{commit}').decode().strip()==COMMIT,'Exact frozen native commit is unavailable')
 require(git(bare,'rev-parse',COMMIT+'^{tree}').decode().strip()==TREE,'Native commit tree differs')
 require(git(bare,'rev-parse',COMMIT+'^').decode().strip()==PARENT,'Frozen native commit parent differs')
 tree=git_tree(bare,COMMIT)
 require(len(tree)==manifest['full_tracked_source_count_at_commit']==95,'Exact native Git tree inventory differs')
 sources={};modes={}
 for row in seal['files']:
  relative=safe_relative(row['path']).as_posix()
  require(relative not in sources and relative in tree,'Duplicate/missing sealed Git source path')
  raw=blob(bare,tree[relative])
  require(len(raw)==row['bytes'] and digest(raw)==row['sha256'],'Git source does not match frozen seal: '+relative)
  sources[relative]=raw;modes[relative]=0o755 if tree[relative]['mode']=='100755' else 0o644
 shipping=json.loads(support['shipping-retention.json'])
 require(shipping['shipping_commit']==SHIPPING and shipping['byte_identical'] is True and len(shipping['files'])==14,
         'Shipping retention receipt differs')
 shipping_tree=git_tree(bare,SHIPPING)
 for row in shipping['files']:
  relative=row['path'];require(relative in sources and relative in shipping_tree,'Missing retained shipping source')
  require(sources[relative]==blob(bare,shipping_tree[relative]) and digest(sources[relative])==row['sha256'],
          'Shipping source is not byte-identical to f2: '+relative)
 # All input blobs and support files are checked before the first destination
 # write. The stager never changes a Git ref, index, working tree or old package.
 out.mkdir(parents=True,exist_ok=False)
 for relative,raw in support.items():write_new(out/relative,raw)
 for relative,raw in sources.items():write_new(out/'Source'/relative,raw,modes[relative])
 final_sources={p.relative_to(out/'Source').as_posix() for p in (out/'Source').rglob('*') if p.is_file()}
 require(final_sources==set(sources),'Final native source inventory differs')
 final_files={p.relative_to(out).as_posix() for p in out.rglob('*') if p.is_file()}
 require(final_files==set(support)|{'Source/'+p for p in sources},'Unexpected final preparation file')
 receipt=dict(status='STAGED_EXACT_FROZEN_SOURCE_NOT_NATIVE_EXECUTED',
  staged_at_utc=datetime.now(timezone.utc).isoformat(),native_commit=COMMIT,native_tree=TREE,
  native_commit_parent=PARENT,shipping_commit=SHIPPING,shipping_files_unchanged=14,
  bare_repository=str(bare),preparation=str(out),source_root=str(out/'Source'),
  native_source_count=47,support_file_count=22,source_seal_sha256=SEAL_SHA,
  adapter_sha256=ADAPTER_SHA,lifecycle_sha256=LIFECYCLE_SHA,support_manifest_sha256=SUPPORT_MANIFEST_SHA,
  stager_sha256=digest(Path(__file__).read_bytes()),coordinator_acknowledged=False,
  reconstruction='Raw git ls-tree/cat-file blobs at the exact commit; no checkout or filters',
  git_refs_modified=False,prior_packages_modified=False,native_invoked=False,release_invoked=False,push_invoked=False,
  original_deadline_utc='2026-11-17T22:26:12Z',explicit_user_extension_hours=24,
  extended_deadline_utc='2026-11-18T22:26:12Z',budget_restarted=False)
 write_new(receipt_path,(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n').encode('utf-8'))
 print(json.dumps(receipt,ensure_ascii=False,indent=2))

if __name__=='__main__':
 try:main()
 except (RuntimeError,OSError,ValueError,KeyError) as error:
  print('STAGING_REFUSED: '+str(error),file=sys.stderr);sys.exit(1)
