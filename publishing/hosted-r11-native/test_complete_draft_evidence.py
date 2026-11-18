"""Synthetic boundary tests only: no native runner, subprocess or real network."""
import ast
import contextlib
from copy import deepcopy
import hashlib
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import evidence_pack as pack
import overflow_evidence as overflow
import release_contract as contract
import github_evidence_transport as network
import release_evidence as delivery
import delivery_gate
from test_hosted_contract import bound_context


HERE = Path(__file__).resolve().parent
VERDICT = b'{"computation_gate_passed":false,"store_release":false}\n'


def roots_at(root):
    attempt, candidate = root / "Attempt", root / "Candidate"
    attempt.mkdir(); candidate.mkdir()
    (candidate / ".git").mkdir(); (candidate / ".git" / "excluded").write_bytes(b"synthetic Git metadata")
    (attempt / "Original.bin").write_bytes(bytes(range(256)) * 20)
    (attempt / "Empty").mkdir()
    os.link(attempt / "Original.bin", attempt / "Hardlink.bin")
    (attempt / "Link").symlink_to("Original.bin")
    (candidate / "source.swift").write_text("// synthetic pure fixture\n")
    return {"Attempt": attempt, "Candidate": candidate}


class Response(io.BytesIO):
    def __init__(self, body, status=200, headers=None):
        super().__init__(body); self.status = status; self.headers = headers or {}
    def getcode(self):
        return self.status


class Opener:
    def __init__(self, responses):
        self.responses, self.requests = list(responses), []
    def open(self, request, timeout):
        self.requests.append(request)
        if not self.responses:
            raise AssertionError("Unexpected retry or real network request")
        return self.responses.pop(0)


def metadata(name, body, asset_id=11):
    return {"id": asset_id, "name": name, "state": "uploaded", "size": len(body),
            "digest": "sha256:" + hashlib.sha256(body).hexdigest(),
            "url": f"https://api.github.com/repos/{contract.REPOSITORY}/releases/assets/{asset_id}"}


def context_at(root):
    config, review, env = bound_context()
    config["root_review_sha256"] = "f" * 64
    candidate = root / "Candidate"; candidate.mkdir()
    (candidate / "synthetic-source.txt").write_text("Not app code; fixture only\n")
    return (config, {}, {}, review, candidate, root / "Attempt"), env


class DraftBackend:
    def __init__(self, binding):
        self.binding, self.rows, self.bodies, self.operations = binding, {}, {}, []
        self.next_id, self.fail_after_upload, self.bad_download = 1000, False, False
    def factory(self, token, release_id, ledger, *, seconds):
        backend = self
        class Fake:
            def __init__(self):
                self.release_id, self.ledger = release_id, ledger
                delivery.write_original(ledger, b'')
            def record(self, action):
                backend.operations.append(action)
                with self.ledger.open('ab') as stream:
                    stream.write((json.dumps({'synthetic':True,'action':action})+'\n').encode())
            def release(self):
                self.record('GET release')
                return {'id':release_id,'draft':True,'prerelease':True,'tag_name':contract.TAG,
                    'target_commitish':contract.SOURCE_COMMIT,'name':contract.TITLE,'body':contract.BODY,
                    'created_at':backend.binding['created_at'],'published_at':None,'immutable':False,
                    'author':{'id':backend.binding['author_id'],'login':backend.binding['author_login']},
                    'url':f'https://api.github.com/repos/{contract.REPOSITORY}/releases/{release_id}',
                    'upload_url':f'https://uploads.github.com/repos/{contract.REPOSITORY}/releases/{release_id}/assets{{?name,label}}'}
            def tag(self, name):
                self.record('GET tag')
                return {'ref':'refs/tags/'+name,'object':{'type':'commit','sha':contract.SOURCE_COMMIT}}
            def assets(self):
                self.record('GET assets'); return deepcopy(list(backend.rows.values()))
            def upload(self, path, name, *, expected, maximum_bytes):
                self.record('POST '+name)
                if name in backend.rows: raise ValueError('synthetic duplicate 422')
                raw=path.read_bytes(); assert network.file_record(path)==expected and len(raw)<=maximum_bytes
                backend.next_id+=1; row=metadata(name,raw,backend.next_id)
                backend.rows[name]=row; backend.bodies[row['id']]=raw
                if backend.fail_after_upload: raise ValueError('synthetic uncertain response after server write')
                return deepcopy(row)
            def download(self, asset, destination, *, expected, maximum_bytes):
                self.record('DOWNLOAD '+asset['name'])
                raw=backend.bodies[asset['id']]
                if backend.bad_download: raw+=b'corruption'
                delivery.write_original(destination,raw)
                if network.file_record(destination)!=expected: raise ValueError('synthetic corrupt download')
                return expected
        return Fake()


class CompleteDraftEvidence(unittest.TestCase):
    def test_complete_overflow_preserves_hardlinks_symlinks_empty_dirs_and_false_verdict(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder); roots=roots_at(root); out=root/'Evidence'
            value=overflow.prepare_complete_evidence(roots,out,maximum_artifact_bytes=1,verdict_bytes=VERDICT)
            self.assertEqual(value['route'],'root_bound_draft_assets')
            self.assertFalse(value['native_acceptance_established_by_packer'])
            self.assertEqual((out/'verdict.json').read_bytes(),VERDICT)
            members=json.loads((out/'complete-member-index.json').read_bytes())['members']
            self.assertIn('Attempt/Empty',members);self.assertIn('Attempt/Link',members)
            self.assertEqual(sum(x.get('hardlink_target') is not None for x in members.values()),1)
            self.assertNotIn('Candidate/.git',members)
            self.assertEqual(overflow.FROZEN_PACKER_SHA256,hashlib.sha256((HERE/'evidence_pack.py').read_bytes()).hexdigest())
            self.assertEqual(pack.MAXIMUM_ARTIFACT_BYTES,500_000_000)

    def test_real_package_exact_cap_boundary_and_wrong_route_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);roots=roots_at(root);out=root/'Evidence'
            first=overflow.prepare_complete_evidence(roots,out,maximum_artifact_bytes=500_000_000,verdict_bytes=VERDICT)
            self.assertEqual(first['route'],'actions_artifact')
            index=json.loads((out/'complete-member-index.json').read_bytes());cap=first['total_bytes']
            for _ in range(4):
                index['maximum_total_artifact_bytes']=cap
                raw=pack.json_bytes(index)
                cap=(out/'evidence.tar.gz').stat().st_size+len(raw)+len(VERDICT)
            index['maximum_total_artifact_bytes']=cap;(out/'complete-member-index.json').write_bytes(pack.json_bytes(index))
            value=overflow.verify_completed_package(roots,out,verdict_bytes=VERDICT,cap=cap,require_overflow=False)
            self.assertEqual(value['total_bytes'],cap)
            with self.assertRaises(ValueError):overflow.verify_completed_package(roots,out,verdict_bytes=VERDICT,cap=cap,require_overflow=True)
            index['maximum_total_artifact_bytes']=cap-1;(out/'complete-member-index.json').write_bytes(pack.json_bytes(index))
            value=overflow.verify_completed_package(roots,out,verdict_bytes=VERDICT,cap=cap-1,require_overflow=True)
            self.assertEqual(value['total_bytes'],cap)

    def test_wrong_index_truncated_gzip_changed_source_and_missing_output_fail_closed(self):
        for mutation in ('index','gzip','source','missing'):
            with self.subTest(mutation=mutation),tempfile.TemporaryDirectory() as folder:
                root=Path(folder);roots=roots_at(root);out=root/'Evidence'
                overflow.prepare_complete_evidence(roots,out,maximum_artifact_bytes=1,verdict_bytes=VERDICT)
                if mutation=='index':
                    p=out/'complete-member-index.json';v=json.loads(p.read_bytes());v['members'].pop('Attempt/Empty');p.write_bytes(pack.json_bytes(v))
                elif mutation=='gzip':
                    p=out/'evidence.tar.gz';b=bytearray(p.read_bytes());b[-8]^=1;p.write_bytes(b)
                elif mutation=='source':(roots['Attempt']/'Original.bin').write_bytes(b'changed')
                else:(out/'verdict.json').unlink()
                with self.assertRaises((ValueError,OSError,EOFError)):
                    overflow.verify_completed_package(roots,out,verdict_bytes=VERDICT,cap=1,require_overflow=True)

    def test_non_size_packer_failure_and_symlink_output_never_become_overflow(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);roots=roots_at(root)
            with patch.object(pack,'pack_evidence',side_effect=pack.PackagingFailure('Original complete tree changed')):
                with self.assertRaisesRegex(ValueError,'tree changed'):
                    overflow.prepare_complete_evidence(roots,root/'E',maximum_artifact_bytes=1,verdict_bytes=VERDICT)
            out=root/'E';overflow.prepare_complete_evidence(roots,out,maximum_artifact_bytes=1,verdict_bytes=VERDICT)
            alias=root/'alias';alias.symlink_to(out,target_is_directory=True)
            with self.assertRaises(ValueError):overflow.verify_completed_package(roots,alias,verdict_bytes=VERDICT,cap=1,require_overflow=True)

    def test_release_bounds_remain_strictly_below_two_gib(self):
        self.assertEqual(overflow.RELEASE_LIMITS,{'evidence.tar.gz':2_000_000_000,'complete-member-index.json':40_000_000,'verdict.json':16_384})
        self.assertTrue(all(x<2**31 for x in contract.POLICY['maximum_asset_bytes'].values()))
        self.assertFalse(contract.POLICY['asset_overwrite_delete_retry_allowed'])
        self.assertFalse(contract.POLICY['release_create_update_publish_delete_allowed'])

    def test_runtime_variants_change_only_exact_build_constant_all_functions_identical(self):
        for name in ('appearance_evidence_guard','arabic_appearance_evidence_guard','case_evidence'):
            old=(HERE/(name+'.py')).read_text();new=(HERE/(name+'_installed.py')).read_text()
            self.assertEqual(old.replace('24A5423a','24A434'),new)
            def funcs(text):return {n.name:ast.dump(n,include_attributes=False) for n in ast.parse(text).body if isinstance(n,(ast.FunctionDef,ast.ClassDef))}
            self.assertEqual(funcs(old),funcs(new))
        observed=json.loads((HERE/'accepted-inventory.json').read_bytes())
        self.assertEqual(observed['platform']['runtime']['buildversion'],'24A434')
        self.assertFalse(observed['native_build_test_archive_invoked'])

    def test_redirect_download_strips_authorization_and_logs_no_token_or_signed_query(self):
        raw=b'original exact bytes';asset=metadata('evidence',raw)
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);opener=Opener([Response(b'',302,{'Location':'https://release-assets.githubusercontent.com/path?secret=SYNTHETIC_PRIVATE_URL_NONCE'}),Response(raw,200,{'Content-Length':str(len(raw))})])
            t=network.GitHubEvidenceTransport('TOKEN-SYNTHETIC',101,root/'ledger',opener=opener)
            t.download(asset,root/'download',expected={'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()},maximum_bytes=100)
            self.assertIn('Authorization',dict(opener.requests[0].header_items()))
            self.assertNotIn('Authorization',dict(opener.requests[1].header_items()))
            self.assertNotIn('Cookie',dict(opener.requests[1].header_items()))
            log=(root/'ledger').read_text();self.assertNotIn('TOKEN-SYNTHETIC',log);self.assertNotIn('SYNTHETIC_PRIVATE_URL_NONCE',log);self.assertNotIn('secret=',log)
            self.assertIsNone(network.NoRedirect().redirect_request(None,None,302,'',{},'https://elsewhere.invalid'))

    def test_untrusted_redirect_second_redirect_or_bad_binary_never_accepted(self):
        for variant in ('evil-host','userinfo','second-redirect','wrong-bytes','too-long'):
            with self.subTest(variant=variant),tempfile.TemporaryDirectory() as folder:
                root=Path(folder);raw=b'exact';asset=metadata('evidence',raw);expected={'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}
                url='https://release-assets.githubusercontent.com/path?secret=SIGNED'
                if variant=='evil-host':url='https://not-github.invalid/path'
                if variant=='userinfo':url='https://user:secret@release-assets.githubusercontent.com/path'
                responses=[Response(b'',302,{'Location':url})]
                if variant=='second-redirect':responses.append(Response(b'',302,{'Location':url}))
                elif variant=='wrong-bytes':responses.append(Response(b'wrong'))
                elif variant=='too-long':responses.append(Response(raw+b'extra'))
                opener=Opener(responses);t=network.GitHubEvidenceTransport('TOKEN',101,root/'ledger',opener=opener)
                with self.assertRaises(ValueError):t.download(asset,root/'download',expected=expected,maximum_bytes=10)
                self.assertLessEqual(len(opener.requests),2)

    def test_duplicate_uncertain_or_digest_mismatched_upload_is_one_post_no_delete(self):
        for status in (422,502,201):
            with self.subTest(status=status),tempfile.TemporaryDirectory() as folder:
                root=Path(folder);p=root/'original';p.write_bytes(b'original');name='reservation-fixture.json';row=metadata(name,p.read_bytes())
                if status==201:row['digest']='sha256:'+'0'*64
                opener=Opener([Response(json.dumps(row if status==201 else {'message':'synthetic failure'}).encode(),status)])
                t=network.GitHubEvidenceTransport('TOKEN',101,root/'ledger',opener=opener)
                with self.assertRaises(ValueError):t.upload(p,name,expected=network.file_record(p),maximum_bytes=100)
                self.assertEqual(len(opener.requests),1);self.assertEqual(opener.requests[0].method,'POST')
                self.assertTrue(opener.requests[0].full_url.startswith('https://uploads.github.com/repos/swonyu/HalalAnalyzer/releases/101/assets?'))
                self.assertEqual(p.read_bytes(),b'original')

    def test_unbound_draft_wrong_tag_published_or_changed_body_rejected_before_native(self):
        with tempfile.TemporaryDirectory() as folder:
            context,env=context_at(Path(folder));binding=context[0]['evidence_release'];backend=DraftBackend(binding)
            f=backend.factory('synthetic',101,Path(folder)/'ledger',seconds=45);release,tag=f.release(),f.tag(contract.TAG)
            contract.validate_remote_release(binding,release,tag)
            for mutation in ('unbound','published','tag','body','target','permissions','nonempty-policy'):
                b,r,t=deepcopy(binding),deepcopy(release),deepcopy(tag)
                if mutation=='unbound':b['authorization']='UNBOUND'
                elif mutation=='published':r['draft']=False
                elif mutation=='tag':t['object']['sha']='0'*40
                elif mutation=='body':r['body']+='changed'
                elif mutation=='target':r['target_commitish']='main'
                elif mutation=='permissions':b['policy']['runtime_token_permission']='admin'
                else:b['policy']['initial_assets']=[123]
                with self.subTest(mutation=mutation),self.assertRaises(ValueError):contract.validate_remote_release(b,r,t)

    def test_reservation_requires_empty_draft_and_verified_exact_readback(self):
        for problem in ('unexpected-assets','uncertain-post','bad-readback'):
            with self.subTest(problem=problem),tempfile.TemporaryDirectory() as folder,contextlib.redirect_stdout(io.StringIO()):
                context,env=context_at(Path(folder));backend=DraftBackend(context[0]['evidence_release'])
                if problem=='unexpected-assets':backend.rows['prior']=metadata('prior',b'prior')
                elif problem=='uncertain-post':backend.fail_after_upload=True
                else:backend.bad_download=True
                with self.assertRaises(ValueError):delivery.reserve(context,env,transport_factory=backend.factory)
                self.assertFalse(context[-1].exists())
                self.assertFalse((delivery.reservation_path(context[-1])/'reservation-proof.json').exists())
                self.assertLessEqual(sum(x.startswith('POST') for x in backend.operations),1)
                with self.assertRaises(ValueError):delivery.verify_reservation(context,env)

    def test_successful_reservation_still_not_native_pass_and_reuse_wrong_run_tamper_rejected(self):
        with tempfile.TemporaryDirectory() as folder,contextlib.redirect_stdout(io.StringIO()):
            context,env=context_at(Path(folder));backend=DraftBackend(context[0]['evidence_release'])
            proof=delivery.reserve(context,env,transport_factory=backend.factory)
            self.assertFalse(proof['native_pass']);self.assertFalse(proof['full_evidence_delivered']);self.assertFalse(context[-1].exists())
            with self.assertRaises(ValueError):delivery.reserve(context,env,transport_factory=backend.factory)
            wrong=dict(env,GITHUB_RUN_ID='999')
            with self.assertRaises(ValueError):delivery.verify_reservation(context,wrong)
            (delivery.reservation_path(context[-1])/'reservation.json').write_bytes(b'changed')
            with self.assertRaises(ValueError):delivery.verify_reservation(context,env)

    def test_full_draft_roundtrip_preserves_failed_verdict_and_all_five_assets(self):
        with tempfile.TemporaryDirectory() as folder,contextlib.redirect_stdout(io.StringIO()):
            root=Path(folder);context,env=context_at(root);config=context[0];config['cost']['maximum_output_bytes']=1
            backend=DraftBackend(config['evidence_release']);delivery.reserve(context,env,transport_factory=backend.factory)
            attempt=context[-1];attempt.mkdir();delivery.preserve_reservation(attempt)
            (attempt/'original-raw-failure.bin').write_bytes(b'Original failing output\x00\xff')
            target=attempt.with_name(attempt.name+'-Evidence')
            route=overflow.prepare_complete_evidence({'Attempt':attempt,'Candidate':context[-2]},target,maximum_artifact_bytes=1,verdict_bytes=VERDICT)
            delivery.write_original(delivery.route_path(attempt),contract.canonical(route))
            output=root/'github-output';output.write_text('')
            with patch.dict(os.environ,{'GITHUB_OUTPUT':str(output)}):terminal=delivery.deliver(context,env,transport_factory=backend.factory)
            self.assertFalse(terminal['computation_gate_passed']);self.assertFalse(terminal['store_release'])
            self.assertEqual(len(backend.rows),5)
            receipt=json.loads(backend.bodies[terminal['receipt_asset_id']])
            self.assertFalse(receipt['unchanged_original_verdict']['computation_gate_passed'])
            self.assertTrue(receipt['complete_package_verification']['gzip_crc_to_eof_verified'])
            self.assertEqual(len([x for x in backend.operations if x.startswith('POST')]),5)
            with self.assertRaises(ValueError):delivery.deliver(context,env,transport_factory=backend.factory)

    def test_final_gate_requires_full_native_and_either_exact_delivery_route(self):
        env={k:'success' for k in ('INSPECT_OUTCOME','RESERVATION_OUTCOME','NATIVE_OUTCOME','COLLECT_OUTCOME')}
        env.update(COMPUTATION_GATE_PASSED='true',ARCHIVE_SHA256='a'*64,ARCHIVE_BYTES='501000000',
            EVIDENCE_ROUTE='root_bound_draft_assets',UPLOAD_OUTCOME='skipped',RELEASE_OUTCOME='success',
            RELEASE_DELIVERY_VERIFIED='true',RELEASE_ID='101',DELIVERY_RECEIPT_ASSET_ID='102',
            DELIVERY_RECEIPT_SHA256='b'*64,RELEASE_ARCHIVE_SHA256='a'*64,RELEASE_ARCHIVE_BYTES='501000000')
        self.assertTrue(delivery_gate.evaluate(env)['original_model_ui_unsigned_archive_and_evidence_passed'])
        for key,value in [('NATIVE_OUTCOME','failure'),('COMPUTATION_GATE_PASSED','false'),('RESERVATION_OUTCOME','skipped'),
                          ('RELEASE_DELIVERY_VERIFIED','false'),('RELEASE_ARCHIVE_SHA256','c'*64),('UPLOAD_OUTCOME','success')]:
            with self.subTest(key=key):self.assertFalse(delivery_gate.evaluate(dict(env,**{key:value}))['original_model_ui_unsigned_archive_and_evidence_passed'])
        normal=dict(env,EVIDENCE_ROUTE='actions_artifact',UPLOAD_OUTCOME='success',RELEASE_OUTCOME='skipped',ARTIFACT_ID='123',ARTIFACT_DIGEST='d'*64)
        self.assertTrue(delivery_gate.evaluate(normal)['original_model_ui_unsigned_archive_and_evidence_passed'])
        self.assertFalse(delivery_gate.evaluate(dict(normal,ARTIFACT_DIGEST='queued'))['original_model_ui_unsigned_archive_and_evidence_passed'])
        self.assertFalse(delivery_gate.evaluate(normal)['store_release'])

    def test_digest_output_names_are_supported_without_output_injection(self):
        from collect_evidence import emit_outputs
        with tempfile.TemporaryDirectory() as folder:
            output=Path(folder)/'out';output.write_text('')
            with patch.dict(os.environ,{'GITHUB_OUTPUT':str(output)}):
                emit_outputs({'archive_sha256':'a'*64,'delivery_receipt_sha256':'b'*64})
                for values in ({'bad-key':'x'},{'archive_sha256':'x\ninjected=true'},{'x\ny':'z'}):
                    with self.assertRaises(ValueError):emit_outputs(values)
            self.assertEqual(output.read_text(),'archive_sha256='+'a'*64+'\ndelivery_receipt_sha256='+'b'*64+'\n')


if __name__=='__main__':
    unittest.main()
