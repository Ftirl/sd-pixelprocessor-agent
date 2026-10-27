import copy
import hashlib
import json
import os
from pathlib import Path
import struct
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from graph_evidence import digest, exact_value
from runtime_safety import snapshot_user_packages, assert_preexisting_packages_unchanged
from workflow_guards import (EvidenceRegistry, OperationJournal, check_visual_decision,
                             cook_budget_action, check_frame_commit, identity_key, WriterLease, case_evidence_hash)
from project_validation import require_verified_dependencies, check_build_stage_order
from assembly_contracts import check_transport,check_compact_layout,check_portable_delivery
from install_transaction import install


def identity(name='F'):
    return dict(package='package',resource=name,source_hash='source',graph_hash='graph',
                interface_hash='interface',environment_hash='runtime',cases_hash=case_evidence_hash(case_record()))


def case_record():
    return {'required_paths':['main'], 'cases':[{'inputs':{'x':2},'path':'main',
            'native':[2.0],'oracle':[2.0],'oracle_independent':True,'tolerance':0}]}


def numeric(name='F'):
    return {'name':name,'identity_key':identity_key(identity(name)), 'required_paths':['main'],
            'source_hash':'source','readback_ok':True,'marked_output':True,
            'native_cook_ok':True,'cases':[{'inputs':{'x':2},'path':'main',
            'native':[2.0],'oracle':[2.0],'oracle_independent':True,'tolerance':0}]}


class GuardsTests(unittest.TestCase):
    def test_same_name_content_changes_and_unreadable_snapshot(self):
        class G:
            data={'nodes':[{'id':'1','value':1}],'edges':[],'roots':['1'],'nested':{}}
            def getIdentifier(self): return 'G'
            def getNodes(self): return self.data['nodes']
        class P:
            g=G()
            def getFilePath(self): return 'p.sbs'
            def getChildrenResources(self,recurse): return [self.g]
        class M:
            p=P()
            def getUserPackages(self): return [self.p]
        m=M();reader=lambda g:copy.deepcopy(g.data)
        for field,new in [('nodes',[{'id':'1','value':2}]),('edges',[['1','2']]),('roots',['2']),('nested',{'f':1})]:
            old=copy.deepcopy(m.p.g.data)
            before=snapshot_user_packages(m,reader)
            m.p.g.data[field]=new
            with self.assertRaises(RuntimeError):
                assert_preexisting_packages_unchanged(before,m,owned_package=m.p,graph_reader=reader)
            m.p.g.data=old
        with self.assertRaises(ValueError):
            snapshot_user_packages(m,lambda g:exact_value(object()))

    def test_exact_value_and_unknown_types(self):
        self.assertNotEqual(digest(exact_value(1.0000001)),digest(exact_value(1.0000002)))
        with self.assertRaises(ValueError): exact_value(object())

    def test_content_bound_freshness_and_dependency_invalidation(self):
        f,c=identity(),identity('C'); current={('package','F'):f,('package','C'):c}
        registry=EvidenceRegistry();registry.verify(f,numeric(),[],current)
        registry.verify(c,numeric('C'),[('package','F')],current)
        require_verified_dependencies('caller',[('package','C')],registry,current=current)
        for field in ('source_hash','graph_hash','interface_hash','environment_hash','cases_hash'):
            changed=copy.deepcopy(current);changed[('package','F')][field]='changed'
            with self.assertRaises(ValueError): registry.require(('package','C'),changed)
        self.assertEqual(registry.invalidate(('package','F')),{('package','F'),('package','C')})

    def test_same_name_other_package_and_legacy_list_rejected(self):
        f=identity();registry=EvidenceRegistry();current={('package','F'):f}
        registry.verify(f,numeric(),[],current)
        with self.assertRaises(ValueError):registry.require(('other','F'),current)
        with self.assertRaises(ValueError):require_verified_dependencies('C',['F'],{'F'})

    def test_failed_numeric_cannot_be_registered(self):
        f=identity();record=numeric();record['cases'][0]['native']=[9]
        with self.assertRaises(ValueError):EvidenceRegistry().verify(f,record,[],{('package','F'):f})

    def test_wrong_artifact_and_missing_branch_cannot_be_registered(self):
        f=identity()
        for record in (dict(numeric(),identity_key='stale'), dict(numeric(),required_paths=['main','else']),
                       dict(numeric(),required_paths=[]),dict(numeric(),name='other')):
            with self.assertRaises(ValueError):EvidenceRegistry().verify(f,record,[],{('package','F'):f})

    def test_changed_case_cannot_reuse_old_identity_even_if_values_match(self):
        f=identity();r=numeric();r['cases'][0]['inputs']={'x':7}
        with self.assertRaisesRegex(ValueError,'CASE_EVIDENCE_CHANGED'):
            EvidenceRegistry().verify(f,r,[],{('package','F'):f})

    def test_modified_and_unknown_build_events(self):
        events=[{'kind':x,'function':'F'} for x in ('function_created','function_readback','function_cooked','function_oracle_pass','function_gate_pass')]
        events += [{'kind':'function_modified','function':'F'},{'kind':'caller_start','caller':'C','requires':['F']}]
        self.assertTrue(check_build_stage_order(events))
        self.assertTrue(check_build_stage_order([{'kind':'typo'}]))

    def test_journal_restart_conflict_and_duplicate_protection(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'op.json';j=OperationJournal(p)
            fields=dict(run_id='r',operation_id='o',target='p:g',before_hash='before',expected_after_hash='after',checkpoint='backup')
            j.begin(**fields);j.transition('inflight');j.transition('unknown')
            j=OperationJournal(p)
            self.assertEqual(j.reconcile(target='p:g',observed_hash='after',alive=True),'ALREADY_APPLIED_VERIFY_OUTPUT')
            self.assertEqual(j.reconcile(target='p:g',observed_hash='before',alive=True),'UNCHANGED_REPLAN_WITH_NEW_OPERATION_ID')
            self.assertEqual(j.reconcile(target='p:g',observed_hash='user-edit',alive=True),'CONFLICT_PRESERVE_USER_STATE')
            self.assertEqual(j.reconcile(target='other',observed_hash='after',alive=True),'STOP_TARGET_MISMATCH')
            self.assertEqual(j.reconcile(target='p:g',observed_hash='after',alive=False),'STOP_WRITES_HOST_UNRESPONSIVE')
            with self.assertRaises(FileExistsError):j.begin(**fields)
            with self.assertRaises(ValueError):j.transition('committed')

    def test_commit_requires_observed_identity_and_output_checks(self):
        with tempfile.TemporaryDirectory() as d:
            j=OperationJournal(Path(d)/'op')
            j.begin(run_id='r',operation_id='o',target='g',before_hash='a',expected_after_hash='b',checkpoint='c')
            j.transition('inflight')
            with self.assertRaises(ValueError):j.commit(target='g',observed_hash='b',output_checks={'image':'FAIL'})
            with self.assertRaises(ValueError):j.commit(target='g',observed_hash='c',output_checks={'image':'PASS'})
            j.commit(target='g',observed_hash='b',output_checks={'image':'PASS'})
            self.assertEqual(json.loads(j.path.read_text())['state'],'committed')

    def test_parallel_writer_and_stale_lease_are_not_silently_taken_over(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'writer.lock'
            with WriterLease(p,run_id='one',target='g'):
                with self.assertRaises(FileExistsError):
                    with WriterLease(p,run_id='two',target='g'):pass
            self.assertFalse(p.exists())
            p.write_text('{}')
            with self.assertRaises(FileExistsError):
                with WriterLease(p,run_id='three',target='g'):pass

    def visual_record(self):
        return dict(mode='PROVISIONAL_VISUAL_ASSEMBLY',user_choice='visual_first',authorization_ref='user-turn',
                    residuals=['noise residual'],visual_evidence=['image+diff'],unverified_conditions=['new camera'],
                    reopen_triggers=['camera change'],scope=['F'],evidence_key='e1',
                    checks={k:'PASS' for k in ('structure','state_order','transport','native_cook','finite','range')})

    def test_visual_choice_reused_but_not_expanded(self):
        r=self.visual_record()
        self.assertEqual(check_visual_decision(r,scope=['F'],evidence_key='e1'),[])
        self.assertTrue(check_visual_decision(r,scope=['G'],evidence_key='e1'))
        self.assertTrue(check_visual_decision(r,scope=['F'],evidence_key='e2'))
        r['user_choice']='';self.assertTrue(check_visual_decision(r,scope=['F'],evidence_key='e1'))

    def test_visual_does_not_waive_features_or_safety(self):
        for key in ('missing_features','safety_failures'):
            r=self.visual_record();r[key]=['gap']
            self.assertIn('NON_WAIVABLE_GAP',check_visual_decision(r,scope=['F'],evidence_key='e1'))
        r=self.visual_record();r['checks']['transport']='FAIL'
        self.assertTrue(check_visual_decision(r,scope=['F'],evidence_key='e1'))

    def test_budget_stops_escalation_without_changing_quality(self):
        args=dict(elapsed=1,limit=5,alive=True,finite=True,memory_ok=True)
        self.assertEqual(cook_budget_action(**args),'NEXT_PLANNED_STAGE')
        for changes in ({'elapsed':6},{'finite':False},{'memory_ok':False},{'alive':False}):
            self.assertTrue(cook_budget_action(**dict(args,**changes)).startswith('STOP'))

    def test_partial_frames_and_history_reset(self):
        prev=dict(frame=2,output_hash='p2',configuration_hash='config')
        c=dict(frame=3,history_hash='p2',configuration_hash='config',expected_passes=['B','D','A'],
               completed_passes=['B','D','A'],accepted=True,output_hash='p3')
        self.assertEqual(check_frame_commit(prev,c),[])
        for change in ({'frame':2},{'frame':4},{'configuration_hash':'new'},{'history_hash':'wrong'},
                       {'completed_passes':['A','B','D']},{'completed_passes':['B']},{'accepted':False}):
            self.assertTrue(check_frame_commit(prev,dict(c,**change)))

    def contract(self):
        return dict(schema_version=1,fields=[dict(name='X',type='float4',channels=[0,1,2,3],range=[-100,100])],
                    size=[16,4],format='RGBA32F',encoding='identity',pixel_center=True,filter='nearest',
                    wrap='clamp',mip=0,vflip=False,frame_role='current',snapshot_id='f0')

    def test_transport_mismatch_and_large_integer(self):
        p=self.contract();self.assertEqual(check_transport(p,p),[])
        for key,val in [('size',[32,4]),('vflip',True),('snapshot_id','f1'),('filter','linear')]:
            self.assertTrue(check_transport(p,dict(p,**{key:val})))
        p['fields'][0]['type']='uint32';p['fields'][0]['range']=[0,2**32-1]
        self.assertIn('LOSSY_UINT32_FLOAT_TRANSPORT',check_transport(p,p))

    def test_portable_delivery_requires_all_categories_and_reload(self):
        r=dict(artifact_hash='h',scan_evidence='scan',scanned_categories=['instances','nested_graphs','parent_resources','bitmap_paths','external_files'],
               isolated_directory='isolated-copy',reload_artifact_hash='h',checks={k:'PASS' for k in ('native_reload','final_output','intermediate_outputs','global_parameters')})
        self.assertEqual(check_portable_delivery(r),[])
        for change in ({'external_dependencies':['image.tif']},{'scanned_categories':['instances']},
                       {'reload_artifact_hash':'old'},{'requires_host_scheduler':True}):
            self.assertTrue(check_portable_delivery(dict(r,**change)))

    def test_new_references_are_routed_and_revision_is_separate(self):
        entry=(ROOT/'SKILL.md').read_text(encoding='utf-8')
        for name in ('EXECUTION_RULES','OPERATIONAL_RECOVERY','LARGE_PROJECT_ASSEMBLY','DEPENDENCY_COMPACT_LAYOUT'):
            self.assertIn(name+'.md',entry)
            self.assertTrue((ROOT/'references'/(name+'.md')).is_file())
        self.assertTrue((ROOT/'BEHAVIOR_REVISION').read_text().strip())
        self.assertLess((ROOT/'SKILL.md').stat().st_size,22000)

    def test_layout_private_leaf_rigid_subtree_and_topology(self):
        b={'leaf':(0,800),'root':(100,0),'a':(-100,200),'b':(0,200),'other':(500,0)}
        a=dict(b,leaf=(0,192));kw=dict(edges=[('leaf','root'),('a','b')],leaf_pairs=[('leaf','root')],
                                   rigid_groups=[['a','b']],fixed_nodes=['other'],logic_before='h',logic_after='h')
        self.assertEqual(check_compact_layout(b,a,**kw),[])
        self.assertTrue(check_compact_layout(b,dict(a,b=(20,200)),**kw))
        self.assertTrue(check_compact_layout(b,a,**dict(kw,edges=kw['edges']+[('leaf','other')])) )
        self.assertTrue(check_compact_layout(b,a,**dict(kw,logic_after='different')))

    def test_manual_ksr_fixture_improves_height_without_removing_nodes(self):
        data=json.loads((ROOT/'evals/fixtures/ksr_positions.json').read_text(encoding='utf-8'))['functions']
        old=data['V2_KerrSchildRadius_v1']['nodes'];new=data['V2_KerrSchildRadius_v1__Layout_optimization']['nodes']
        self.assertEqual(set(old),set(new));self.assertEqual(len(old),154)
        height=lambda d:max(p[1] for p in d.values())-min(p[1] for p in d.values())
        self.assertLess(height(new),height(old))

    def test_archived_ftp_native_readers_match_independent_polynomial(self):
        base=ROOT/'evals/fixtures';f=json.loads((base/'ftp_curve.json').read_text(encoding='utf-8'))
        arrays={}
        for name,record in f['raw'].items():
            raw=(base/record['file']).read_bytes()
            self.assertEqual(hashlib.sha256(raw).hexdigest(),record['sha256'])
            arrays[name]=struct.unpack('<'+'f'*(len(raw)//4),raw)
        for y,row in enumerate(f['rows']):
            for ix in range(16):
                t=ix/15
                for c in range(4):
                    x=sum(row[k][c]*t**k for k in range(4))
                    dx=sum(k*row[k][c]*t**(k-1) for k in range(1,4))
                    idx=(y*16+ix)*4+c
                    self.assertAlmostEqual(arrays['ReaderX'][idx],x,delta=2e-6+2e-6*abs(x))
                    self.assertAlmostEqual(arrays['ReaderDX'][idx],dx,delta=2e-6+2e-6*abs(dx))
                    self.assertEqual(arrays['writer'][(y*32+2*ix)*4+c],arrays['ReaderX'][idx])
                    self.assertEqual(arrays['writer'][(y*32+2*ix+1)*4+c],arrays['ReaderDX'][idx])

    def package(self,path):
        path.mkdir();(path/'VERSION').write_text('test',encoding='utf-8');(path/'data').write_text('new',encoding='utf-8')
        rows=[dict(path=p.name,bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in path.iterdir()]
        (path/'MANIFEST.json').write_text(json.dumps(dict(version='test',files=rows)),encoding='utf-8')

    def test_install_swap_failure_restores_old_and_copy_failure_never_removes_it(self):
        with tempfile.TemporaryDirectory() as tmp:
            base=Path(tmp);src=base/'source';dst=base/'installed';self.package(src)
            dst.mkdir();(dst/'old').write_text('user version',encoding='utf-8')
            def failing_rename(a,b):
                if '.stage.' in str(a): raise OSError('injected swap failure')
                os.rename(a,b)
            with self.assertRaises(OSError): install(src,dst,rename=failing_rename)
            self.assertEqual((dst/'old').read_text(),'user version')
            def fail_copy(a,b):raise OSError('injected copy failure')
            with self.assertRaises(OSError):install(src,dst,copy=fail_copy)
            self.assertEqual((dst/'old').read_text(),'user version')
            result=install(src,dst)
            self.assertEqual((Path(result['backup'])/'old').read_text(),'user version')
            self.assertEqual((dst/'data').read_text(),'new')

    def test_corrupt_source_cannot_replace_installed(self):
        with tempfile.TemporaryDirectory() as tmp:
            base=Path(tmp);src=base/'source';dst=base/'installed';self.package(src)
            dst.mkdir();(dst/'old').write_text('old');(src/'data').write_text('corrupt')
            with self.assertRaises(ValueError):install(src,dst)
            self.assertTrue((dst/'old').exists())

    def test_install_restore_failure_retains_backup_and_recovery_lock(self):
        with tempfile.TemporaryDirectory() as tmp:
            base=Path(tmp);src=base/'source';dst=base/'installed';self.package(src)
            dst.mkdir();(dst/'old').write_text('recoverable')
            def fail_swap_and_restore(a,b):
                if '.stage.' in str(a) or '.backup.' in str(a):raise OSError('injected')
                os.rename(a,b)
            with self.assertRaises(OSError):install(src,dst,rename=fail_swap_and_restore)
            self.assertTrue((base/'installed.install-lock').exists())
            self.assertEqual(len(list(base.glob('installed.backup.*/old'))),1)


if __name__=='__main__':unittest.main()
