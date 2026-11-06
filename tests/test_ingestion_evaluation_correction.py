"""Correction evaluator conserves every prior row outside exact child effects."""
import copy
import pytest
from ingestion_evaluation.correction import conserve_correction_rows


def case(operation):
    before = {'app':{'ingest.run':[['parent',1]],'ingest.component_payload':[['prior',3]],'source.revision':[['source',1]]},
              'native':{'graph':[['head',1]]}}
    after = copy.deepcopy(before)
    if operation == 'correct_types':
        old = {'ingest.run':[],'ingest.component_payload':[]}
        new = {'ingest.run':[['child',1]],'ingest.component_payload':[['candidate',1],['index',1]]}
        for table,rows in new.items(): after['app'][table] += rows
    else:
        before['app']['ingest.run'].append(['held',1])
        after['app']['ingest.run'].append(['decided',1])
        old,new = {'ingest.run':[['held',1]]},{'ingest.run':[['decided',1]]}
    return before,after,old,new


@pytest.mark.parametrize('operation',['correct_types','semantic_disposition'])
def test_exact_child_effect_only(operation):
    before,after,old,new = case(operation)
    conserve_correction_rows(before,after,operation,old,new)


@pytest.mark.parametrize('operation',['correct_types','semantic_disposition'])
@pytest.mark.parametrize('damage',['native','source','parent','prior_output','extra_child','missing_owned'])
def test_unowned_effects_rejected(operation,damage):
    before,after,old,new = case(operation)
    if damage == 'native': after['native']['graph'] = [['changed',1]]
    elif damage == 'source': after['app']['source.revision'] = [['changed',1]]
    elif damage == 'parent': after['app']['ingest.run'][0] = ['changed',1]
    elif damage == 'prior_output': after['app']['ingest.component_payload'] = [['changed',3]]
    elif damage == 'extra_child': after['app']['ingest.run'].append(['other',1])
    else: new['ingest.run'] = [['absent',1]]
    with pytest.raises(ValueError): conserve_correction_rows(before,after,operation,old,new)


def test_correction_once_unknown_and_readonly_recovery(tmp_path):
    from tests.test_ingestion_evaluation_source_authority import Backend
    from ingestion_evaluation.correction import CorrectionRunner
    backend = Backend()
    backend.inputs = {'operation':'correct_types'}
    runner = CorrectionRunner({'mode':'reviewed_correction_v1','_output':str(tmp_path)},'pin',backend)
    q = runner.qualify()['qualification_sha256']
    backend.transport_error = backend.verification_error = True
    assert runner.execute(q)['state'] == 'committed_unverified'
    with pytest.raises(ValueError,match='Already dispatched'): runner.execute(q)
    backend.verification_error = False
    assert runner.inspect()['state'] == 'verified'
    assert runner.report()['state'] == 'verified'
    assert backend.calls == 1
    assert (tmp_path/'correction-execution.json').exists()
    assert not (tmp_path/'source-execution.json').exists()


@pytest.mark.parametrize('operation',['correct_types','semantic_disposition'])
@pytest.mark.parametrize('fail',[False,True])
def test_fixed_correction_route_never_enables_native_write(monkeypatch,operation,fail):
    import os
    import httpx
    import fastapi.testclient
    from types import SimpleNamespace
    from ingestion_evaluation.authority import local_route
    class Buddy:
        auth_path = 'synthetic:auth'
        dsns = {}
        db = {'app':{'product_env':'TEST_CORRECTION_APP'},'native':{'product_env':'TEST_CORRECTION_NATIVE'}}
        def _dsn(self,role,*,write=False):
            assert not (role == 'native' and write)
            return role+(':write' if write else ':read')
        def _bind(self,*,read_only):
            for role in self.db:
                os.environ[self.db[role]['product_env']] = self._dsn(role,write=role=='app' and not read_only)
    buddy = Buddy()
    monkeypatch.setenv('TEST_CORRECTION_TOKEN','synthetic-token')
    monkeypatch.setenv('DMB_AGENT_GRAPH_SESSION_STORE',buddy.auth_path)
    monkeypatch.delenv('DMB_AGENT_GRAPH_LOCAL_PROFILE',raising=False)
    calls=[]
    original = httpx.HTTPTransport.handle_request
    class Client:
        def __init__(self,*args,**kwargs): pass
        def __enter__(self): return self
        def __exit__(self,*args): pass
        def post(self,route,json):
            calls.append(route)
            assert os.environ['TEST_CORRECTION_APP'] == 'app:write'
            assert os.environ['TEST_CORRECTION_NATIVE'] == 'native:read'
            with pytest.raises(AssertionError,match='External HTTP'):
                httpx.HTTPTransport.handle_request(None,None)
            if fail: raise RuntimeError('synthetic route interruption')
            return SimpleNamespace(status_code=200,content=b'{}')
    monkeypatch.setattr(fastapi.testclient,'TestClient',Client)
    run='97fdc6bc-57df-505a-a434-c331648b089e'
    if fail:
        with pytest.raises(RuntimeError,match='interruption'):
            local_route(buddy,operation,{},'TEST_CORRECTION_TOKEN',run_id=run)
    else: assert local_route(buddy,operation,{},'TEST_CORRECTION_TOKEN',run_id=run)['status']==200
    suffix='recap-candidate-corrections' if operation=='correct_types' else 'semantic-disposition'
    assert calls == [f'/api/live/extract-promote/runs/{run}/{suffix}']
    assert os.environ['TEST_CORRECTION_APP']=='app:read'
    assert os.environ['TEST_CORRECTION_NATIVE']=='native:read'
    assert httpx.HTTPTransport.handle_request is original


def test_correction_manifest_mode_and_cli_are_closed(tmp_path):
    import json,subprocess,sys
    from pathlib import Path
    from ingestion_evaluation.runner import digest,tooling_identity,verify_manifest
    def pin(name,value):
        p=tmp_path/name;p.write_text(json.dumps(value))
        return {'path':str(p),'sha256':digest(p.read_bytes())}
    manifest={'schema':'dmb_ingestion_evaluation_v1','mode':'reviewed_correction_v1',
        'tooling_sha256':tooling_identity(),'runtime':pin('runtime.json',{'root':str(tmp_path),'files':[]}),
        'output':str(tmp_path/'records'),'app_append_tables':[],
        'correction':{'operation':'correct_types','principal':'local_operator',
            'review_pins':[pin('review.json',{'synthetic':True})],
            'expected_child':{'run_id':'97fdc6bc-57df-505a-a434-c331648b089e',
                'candidate_sha256':'a'*64,'manifest_sha256':'b'*64}},
        'items':[{'id':'correction','retained_run_id':'parent','expected_run_revision':5,'request':pin('request.json',{})}]}
    path=tmp_path/'manifest.json';path.write_text(json.dumps(manifest))
    verify_manifest(path)
    script=Path(__file__).resolve().parents[1]/'scripts/evaluate_ingestion.py'
    for command in ['capture','source-execute','publication-execute']:
        result=subprocess.run([sys.executable,str(script),command,'--manifest',str(path)],capture_output=True,text=True)
        assert result.returncode != 0 and 'own explicit manifest mode' in result.stderr
    result=subprocess.run([sys.executable,str(script),'correction-report','--manifest',str(path)],capture_output=True,text=True)
    assert result.returncode==0,result.stderr
    assert json.loads(result.stdout)['state']=='not_dispatched'
    manifest['correction']['review_pins']=[];path.write_text(json.dumps(manifest))
    with pytest.raises(ValueError,match='independent reviews'):verify_manifest(path)


@pytest.mark.parametrize('damage',[None,'basis_sha256','review_decision_ref','reviewer_id','from_revision','state'])
def test_committed_disposition_requires_exact_receipt(damage):
    from ingestion_evaluation.correction import CorrectionBackend
    backend=CorrectionBackend.__new__(CorrectionBackend)
    backend.operation='semantic_disposition'
    backend.item={'expected_run_revision':5}
    backend.spec={'principal':'local_operator'}
    expected={'run_id':'child','decision':'accepted','basis_sha256':'basis','review_decision_ref':'review'}
    receipt={'state':'accepted','basis_sha256':'basis','review_decision_ref':'review',
             'reviewer_id':'local_operator','from_revision':5}
    if damage:receipt[damage]='different'
    backend._owned=lambda run:{'ingest.run':[['row',1]]}
    backend._run_row=lambda run:{'revision':6,'lineage':{'semantic_disposition':receipt}}
    assert backend.committed({'expected':expected}) is (damage is None)


def test_disposition_rejects_other_correction_family_before_lookup(tmp_path):
    import json
    from types import SimpleNamespace
    from ingestion_evaluation.correction import CorrectionBackend
    from ingestion_evaluation.runner import digest
    backend=CorrectionBackend.__new__(CorrectionBackend)
    p=tmp_path/'basis.json';p.write_text(json.dumps({'request_version':9}))
    backend.spec={'child_basis':{'path':str(p),'sha256':digest(p.read_bytes())}}
    backend.request={'expected_revision':5,'candidate_sha256':'a'*64,
                     'decision':'accepted','review_decision_ref':'synthetic:review'}
    data=SimpleNamespace(run=SimpleNamespace(lineage={'semantic_candidate_manifest':{}}))
    with pytest.raises(ValueError,match='V12-wrapped V8 type-only'):
        backend._decision(data)


def _backend_database_probe():
    """Synthetic owning-backend probe; subprocess imports the selected product runtime."""
    import os,json,tempfile,sys
    from pathlib import Path
    from contextlib import contextmanager
    from types import SimpleNamespace
    sys.path[:0]=[os.getcwd(),str(Path(os.getcwd())/"src")]
    import psycopg
    from psycopg import sql
    from tests.test_graph_preview_runner import FixtureClient,_run_recap_extraction
    from apps.live_control_server.services import recap_semantic_candidate_correction as owner
    from apps.live_control_server.services import graph_run_registry as registry
    from apps.live_control_server.models.extract_promote import RecapCandidateCorrectionRequestV8
    from application_state.ingest import service
    from ingestion_evaluation import authority
    from ingestion_evaluation.correction import CorrectionBackend,CorrectionRunner
    from ingestion_evaluation.runner import digest
    from apps.live_control_server.integrations.dungeonmind import native_registry_source as native
    from uuid import NAMESPACE_URL,uuid5
    from unittest.mock import patch
    assert Path(owner.__file__).is_relative_to(Path(os.getcwd()))
    assert Path(service.__file__).is_relative_to(Path(os.getcwd()))
    dsn=os.environ['DUNGEONBUDDY_APPLICATION_STATE_DATABASE_URL']
    class TestBuddy:
        @contextmanager
        def connection(self,role):
            assert role=='app'
            with psycopg.connect(dsn) as conn:
                conn.execute('SET TRANSACTION READ ONLY')
                yield conn
        def capture_lease(self):
            from contextlib import nullcontext
            return nullcontext()
        def snapshot(self):
            with self.connection('app') as conn:
                tables={}
                for schema,name in conn.execute("SELECT table_schema,table_name FROM information_schema.tables WHERE table_type='BASE TABLE' AND table_schema NOT IN ('pg_catalog','information_schema') ORDER BY 1,2"):
                    query=sql.SQL('SELECT md5(row_to_json(t)::text),count(*) FROM {} t GROUP BY 1 ORDER BY 1').format(sql.Identifier(schema,name))
                    tables[schema+'.'+name]=[list(row) for row in conn.execute(query)]
            return {'app':tables,'native':{'synthetic:unchanged':[['native-readonly',1]]}}
    with tempfile.TemporaryDirectory() as directory:
        root=Path(directory)
        _,result=_run_recap_extraction(root,client=FixtureClient())
        parent=result.run
        data=registry.load_reviewable_extraction_data(root,parent.run_id)
        payload=json.loads(data.candidate_bytes);node=payload['nodes'][0]
        request=RecapCandidateCorrectionRequestV8.model_validate({
            'schema':'dmb_recap_candidate_correction_request_v8','parent_run_id':parent.run_id,
            'expected_parent_revision':parent.revision,'parent_candidate_sha256':digest(data.candidate_bytes),
            'source_revision_sha256':digest(data.source_bytes),'span_index_sha256':digest(data.span_bytes),
            'profile_id':parent.profile_id,'node_type_replacements':[{'node_id':node['node_id'],
                'expected_node_type':node['node_type'],'replacement_node_type':'event'}]})
        manifest=request.model_dump(mode='json',exclude={'schema_','parent_run_id','parent_candidate_sha256'})
        manifest['schema']=owner.MANIFEST_SCHEMA_V8
        candidate=owner.replay_candidate(payload,manifest,source_bytes=data.source_bytes,span_bytes=data.span_bytes)
        operation_sha=owner._sha(owner._canonical_bytes(manifest))
        child_id=str(uuid5(NAMESPACE_URL,f'dmb:{owner.SOURCE_BINDING_DERIVATION_V11}:{parent.run_id}:{digest(data.candidate_bytes)}:{operation_sha}'))
        item={'retained_run_id':parent.run_id,'expected_run_revision':parent.revision,
              'campaign_id':parent.campaign_id,'session_id':parent.session_id,'profile_id':parent.profile_id,
              'source_artifact_id':parent.source_artifact_id,'effective_sha256':digest(data.source_bytes),
              'span_index_sha256':digest(data.span_bytes),'candidate_sha256':digest(data.candidate_bytes)}
        expected={'run_id':child_id,'candidate_sha256':owner._sha(owner._canonical_bytes(candidate)),'manifest_sha256':operation_sha}
        backend=CorrectionBackend.__new__(CorrectionBackend)
        backend.manifest={'world_id':'synthetic','native_context':{'revision_id':'synthetic:head'}}
        backend.item=item;backend.spec={'operation':'correct_types','expected_child':expected,'principal':'local_operator'}
        backend.operation='correct_types';backend.request=request.model_dump(mode='json',by_alias=True)
        backend.buddy=TestBuddy();backend._configuration=lambda:'synthetic:operator';backend.redact=lambda value:value
        # Owning service dispatch is exercised here; fixed ASGI auth/window is
        # covered separately. This does not claim real native repository access.
        backend.dispatch=lambda:owner.correct_recap_candidate(request).model_dump(mode='json',by_alias=True)
        records=root/'records';records.mkdir(mode=0o700)
        runner=CorrectionRunner({'mode':'reviewed_correction_v1','_output':str(records)},'synthetic:manifest',backend)
        with patch.object(owner,'repo_root',return_value=root),patch.object(native,'binding',return_value={'native_world_id':data.source_artifact.world_id}),patch.object(authority,'read_core',return_value=(None,backend.manifest['native_context'],None,None)):
            for field in ('effective_sha256','candidate_sha256','span_index_sha256','profile_id'):
                original=item[field];item[field]='synthetic:drift'
                try:
                    backend.preflight()
                    raise AssertionError('drift was accepted: '+field)
                except ValueError:
                    pass
                finally:
                    item[field]=original
            q=runner.qualify()['qualification_sha256']
            outcome=runner.execute(q)
            assert outcome['state']=='verified',(outcome,(records/'correction-dispatch-error.json').read_text() if (records/'correction-dispatch-error.json').exists() else '')
            assert runner.inspect()['state']=='verified'
            child=registry.get_extraction_run(root,child_id)
            assert owner.verify_child_replay(child,parent,root)
            basis=child.lineage['semantic_source_binding_basis_v12']
            basis_path=root/'reviewed-child-basis.json';basis_path.write_text(json.dumps(basis))
            decision={'expected_revision':child.revision,'candidate_sha256':expected['candidate_sha256'],
                      'decision':'accepted','review_decision_ref':'synthetic:actual-child-review'}
            backend.operation='semantic_disposition'
            backend.spec={'operation':'semantic_disposition','expected_child':{'run_id':child_id},
                'principal':'local_operator','child_basis':{'path':str(basis_path),'sha256':digest(basis_path.read_bytes())},
                'basis_sha256':child.lineage['semantic_disposition']['basis_sha256'],'review_decision_ref':decision['review_decision_ref']}
            backend.item={**item,'retained_run_id':child_id,'expected_run_revision':child.revision,'candidate_sha256':expected['candidate_sha256']}
            backend.request=decision
            def decide():
                actual=service.RecapSemanticBasisV12.model_validate(basis)
                return service.record_recap_semantic_disposition(child_id,expected_revision=child.revision,basis=actual,
                    decision=service.RecapSemanticDispositionCommandV1(state='accepted',reviewer_id='local_operator',
                        review_decision_ref=decision['review_decision_ref'])).model_dump(mode='json')
            backend.dispatch=decide
            records2=root/'decision-records';records2.mkdir(mode=0o700)
            runner2=CorrectionRunner({'mode':'reviewed_correction_v1','_output':str(records2)},'synthetic:decision-manifest',backend)
            q2=runner2.qualify()['qualification_sha256']
            outcome2=runner2.execute(q2)
            assert outcome2['state']=='verified',outcome2
            assert runner2.inspect()['state']=='verified'
            # An extra change to the exact target row must not disappear when
            # row subtraction permits the one intended disposition CAS.
            with psycopg.connect(dsn) as conn:
                conn.execute("UPDATE ingest.run SET created_at=created_at+interval '1 second' WHERE run_id=%s",(child_id,))
            damaged=runner2.inspect()
            assert damaged['state']=='committed_unverified',damaged
            assert 'outside exact child CAS' in damaged['verification_error']
        print(json.dumps({'correction':'verified','disposition':'verified','primary_effects':False}))


def test_backend_with_selected_product_runtime(application_state_dsn):
    import os,subprocess,sys
    from pathlib import Path
    runtime=os.environ.get('DMB_EVALUATION_TEST_RUNTIME')
    if not runtime:
        pytest.skip('Set DMB_EVALUATION_TEST_RUNTIME to the pinned reviewed product union')
    script=Path(__file__).resolve()
    env=dict(os.environ)
    env['PYTHONPATH']=str(script.parents[1]/'src')+os.pathsep+str(Path(runtime)/'src')
    result=subprocess.run([sys.executable,str(script),'--backend-probe'],cwd=runtime,env=env,
                          capture_output=True,text=True,timeout=120)
    assert result.returncode==0,result.stdout+result.stderr
    assert '"disposition": "verified"' in result.stdout


if __name__=='__main__':
    import sys
    if sys.argv[1:]==['--backend-probe']:
        _backend_database_probe()
