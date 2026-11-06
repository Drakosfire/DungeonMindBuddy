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
