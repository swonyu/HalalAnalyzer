#!/usr/bin/env python3
"""Export the complete frozen HalalTag R7 Git tree and complete bounded reading pack.

Read-only local bare Git. Exclusive new files only. No uploads, browser/native
commands, source edits, acknowledgment configuration or Git ref changes.
"""
from pathlib import Path
from datetime import datetime,timezone
import argparse
import hashlib
import json
import runpy
import sys

HERE=Path(__file__).resolve().parent
ENGINE_SHA='6b3e8847c2587e729e23b78fc77c9087ed62bb4d6a1f53af89c0af4e1414ae62'
COMMIT='156c5eeb60eb1e06cf369235ed33af265460a9cb'
TREE='a12a81a8fb1a0fe9085fc316aca8d9eedd7bd718'
BASELINE='aa7f756e6c4bb5441e6945e4454141756934252f'
SCREENING_DIGEST='0040fd6ba06ee0cd1a67eeab913b66298aeba5dcfaeef5cf55ec1644e1965c49'
MAC_BARE=Path('/Users/saleh/Library/Caches/Publishing-Continuation-20261117-d597fc87411f/Recovery-d57f4cd77813/GitCheckpoint/halaltag.git')
MAC_OUTPUT=Path('/Users/saleh/Library/Caches/Grok-HalalTag-R7-Full-Source-20261117-d57f4-156c5ee')


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
 parser=argparse.ArgumentParser(description=__doc__)
 parser.add_argument('--bare-repository',type=Path,default=MAC_BARE)
 parser.add_argument('--output',type=Path,default=MAC_OUTPUT)
 args=parser.parse_args();repo=args.bare_repository.expanduser().absolute();out=args.output.expanduser().absolute()
 if not repo.is_dir() or repo.is_symlink() or out.exists() or out.is_symlink():
  raise RuntimeError('Expected existing regular bare Git and a new output directory; refusing overwrite')
 if '..' in repo.parts or '..' in out.parts or out.is_relative_to(repo):
  raise RuntimeError('Unsafe or overlapping export path')
 engine_path=HERE/'source_export_engine.py'
 if engine_path.is_symlink() or sha(engine_path)!=ENGINE_SHA:raise RuntimeError('Reviewed export engine changed')
 engine=runpy.run_path(str(engine_path))
 require=engine['require'];git=engine['git'];save=engine['save_json']
 require(git(repo,'rev-parse','--is-bare-repository').strip()==b'true','Use the existing bare checkpoint')
 spec=json.loads((HERE/'source-spec.json').read_text())
 require(spec==dict(app='HalalTag',slug='halaltag',commit=COMMIT,tree=TREE,count=95,bytes=1290553,baseline_commit=BASELINE),
         'Frozen complete source specification changed')
 report,blobs=engine['inspect_app'](spec,repo)
 require(report['screening_digest']==SCREENING_DIGEST and report['tracked_files']==95 and report['utf8_text_files']==94,
         'Exact complete source scan differs from the reviewed tree')
 review_path=HERE/'screened-review-ledger.json'
 review=json.loads(review_path.read_text());engine['validate_review']([report],review)
 # Verify required supporting material before writing an output directory.
 supporting=['source-spec.json','screened-review-ledger.json','VERSION-AND-UI-STATUS.json',
             'REVIEW-INSTRUCTIONS.txt','export_halaltag_r7.py','source_export_engine.py']
 payloads={}
 for name in supporting:
  path=HERE/name;require(path.is_file() and not path.is_symlink(),'Missing/linked support document:'+name)
  payloads[name]=path.read_bytes()
 out.mkdir(parents=True,exist_ok=False);source=out/'Source';source.mkdir()
 result=engine['export_app'](spec,repo,report,blobs,source)
 save(out/'exact-tree-screening.json',report)
 for name,data in payloads.items():
  with (out/name).open('xb') as stream:stream.write(data)
 receipt=dict(schema_version=1,status='COMPLETE_SOURCE_EXPORTED_NOT_UPLOADED',
  created_at_utc=datetime.now(timezone.utc).isoformat(),export_environment=sys.platform,
  bare_repository=str(repo),exact_commit=COMMIT,exact_tree=TREE,complete_tracked_files=95,
  original_tracked_bytes=1290553,utf8_text_files=94,binary_files=1,
  every_tracked_file_in_zip=True,every_utf8_file_reproduced_byte_exact=True,omitted_tracked_paths=[],
  original_source_edited=False,git_refs_modified=False,native_invoked=False,upload_invoked=False,
  ui_images_exported=False,ui_evidence='Separate original R6b audit; no R7 screenshots claimed',
  review_ledger_sha256=sha(review_path),source_spec_sha256=sha(HERE/'source-spec.json'),
  exporter_sha256=sha(Path(__file__)),engine_sha256=ENGINE_SHA,export=result,
  supporting_documents=[dict(path=name,bytes=len(data),sha256=hashlib.sha256(data).hexdigest()) for name,data in payloads.items()])
 save(out/'EXPORT-RECEIPT.json',receipt)
 print(json.dumps(receipt,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
