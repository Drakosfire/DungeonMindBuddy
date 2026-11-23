"""Durable Build Worldbuilding launches through document and run owners."""
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier, Lock
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from tests.test_build_recap_source import source  # noqa: F401
from apps.live_control_server.main import create_app
from apps.live_control_server.models.build_worldbuilding_launch import BuildWorldbuildingLaunchRequest
from apps.live_control_server.services import build_worldbuilding_launch as service
from apps.live_control_server.services.graph_run_registry import GraphRunRegistryError

pytestmark = pytest.mark.usefixtures('application_state_dsn')

@pytest.fixture
def body(source):
    record, _, _, digest = source
    return BuildWorldbuildingLaunchRequest(request_id=uuid4(), document_id=record.document_id,
        managed_world_id='managed-a', expected_revision=record.revision, expected_content_sha256=digest,
        profile_id='worldbuilding_shepherds_flock_v0', profile_version='0.1')

@pytest.mark.parametrize('profile,version', [('worldbuilding_shepherds_flock_v0','0.1'), ('worldbuilding_gazetteer_v1','1.10')])
def test_reservation_survives_lost_response_without_reexecution(tmp_path, body, monkeypatch, profile, version):
    from apps.live_control_server.services import graph_preview_runner, worldbuilding_ge_execution
    body=body.model_copy(update={'profile_id':profile,'profile_version':version})
    calls=[]
    def interrupted(**kwargs):
        reserved=kwargs['reserved_run']; calls.append(reserved.run_id)
        assert service.recover_build_worldbuilding_launch(request_id=body.request_id,document_id=body.document_id,
            managed_world_id=body.managed_world_id).run_id==reserved.run_id
        raise RuntimeError('simulated interrupted response')
    monkeypatch.setattr(graph_preview_runner,'run_worldbuilding_production_extraction',interrupted)
    monkeypatch.setattr(worldbuilding_ge_execution,'run_gazetteer_with_generation_engine',interrupted)
    with pytest.raises(RuntimeError): service.launch_build_worldbuilding(tmp_path,body)
    recovered=service.launch_build_worldbuilding(tmp_path,body)
    assert recovered.status.value=='draft' and calls==[recovered.run_id]
    for change in ({'expected_revision':body.expected_revision+1},{'profile_version':'1.10','profile_id':'worldbuilding_gazetteer_v1'} if profile!='worldbuilding_gazetteer_v1' else {'expected_content_sha256':'b'*64}, {'managed_world_id':'managed-b'}):
        with pytest.raises(GraphRunRegistryError):service.launch_build_worldbuilding(tmp_path,body.model_copy(update=change))


def test_concurrent_same_request_dispatches_once(tmp_path,body,monkeypatch):
    from apps.live_control_server.services import graph_preview_runner
    barrier=Barrier(2); original=service.create_source_artifact_from_workspace_document; calls=[]; lock=Lock()
    def capture(*args,**kwargs):
        result=original(*args,**kwargs);barrier.wait(timeout=10);return result
    def dispatch(**kwargs):
        with lock: calls.append(kwargs['reserved_run'].run_id)
        return SimpleNamespace(run=kwargs['reserved_run'])
    monkeypatch.setattr(service,'create_source_artifact_from_workspace_document',capture)
    monkeypatch.setattr(graph_preview_runner,'run_worldbuilding_production_extraction',dispatch)
    with ThreadPoolExecutor(max_workers=2) as pool:
        results=list(pool.map(lambda _:service.launch_build_worldbuilding(tmp_path,body),range(2)))
    assert results[0].run_id==results[1].run_id and calls==[results[0].run_id]


def test_authorized_http_recovery_and_wrong_world_denial(tmp_path,body,monkeypatch):
    from apps.live_control_server.services import graph_preview_runner
    monkeypatch.setattr(graph_preview_runner,'run_worldbuilding_production_extraction',lambda **kw:SimpleNamespace(run=kw['reserved_run']))
    monkeypatch.setattr('apps.live_control_server.routes.build_extraction.repo_root',lambda:tmp_path)
    monkeypatch.setenv('DMB_DEPLOYMENT_ENVIRONMENT','local');monkeypatch.setenv('DMB_AUTH_MODE','local_operator')
    monkeypatch.setenv('DMB_AGENT_GRAPH_AUTH_MODE','local_operator');monkeypatch.setenv('DMB_AGENT_GRAPH_AUTH_ENVIRONMENT','local')
    monkeypatch.setenv('DMB_AGENT_GRAPH_LOCAL_OPERATOR_TOKEN','test-build-recap-local-operator-token')
    with TestClient(create_app(),client=('127.0.0.1',50000),headers={'Authorization':'Bearer test-build-recap-local-operator-token'}) as client:
        base='/api/live/graph-preview/build-worldbuilding-launches'
        first=client.post(base,json=body.model_dump(mode='json'));assert first.status_code==200,first.text
        params={'document_id':str(body.document_id),'managed_world_id':body.managed_world_id}
        recovered=client.get(f'{base}/{body.request_id}',params=params)
        assert recovered.status_code==200 and recovered.json()==first.json()
        assert client.get(f'{base}/{body.request_id}',params={**params,'managed_world_id':'managed-b'}).status_code==409
        assert client.get(f'{base}/{body.request_id}?document_id={body.document_id}&managed_world_id=managed-a&managed_world_id=managed-b').status_code==400


def test_reserved_run_enters_real_controller_without_leaking_binding_to_model(tmp_path,body,monkeypatch):
    from apps.live_control_server.services import graph_preview_runner as wrapper
    from tests.test_graph_preview_runner import FixtureClient, _first_paragraph_span_id
    real=wrapper.run_worldbuilding_production_extraction
    seen=[]
    prompts=[]
    class Capture(FixtureClient):
        def run_pass(self,pass_name,**kwargs):
            serialized=kwargs['instructions']+'\n'+kwargs['user_content']
            prompts.append(serialized)
            seen.append(pass_name)
            return super().run_pass(pass_name,**kwargs)
    def execute(**kwargs):
        source=wrapper._normalized_from_registered(tmp_path,kwargs['source_artifact_id'])
        kwargs['category_client']=Capture(span_ref=_first_paragraph_span_id(source))
        return real(**kwargs)
    monkeypatch.setattr(wrapper,'run_worldbuilding_production_extraction',execute)
    first=service.launch_build_worldbuilding(tmp_path,body)
    assert seen and first.status.value=='failed'
    assert 'unknown source evidence handle' in first.diagnostics.errors
    for forbidden in (str(body.request_id),str(body.document_id),body.managed_world_id,body.expected_content_sha256):
        assert all(forbidden not in prompt for prompt in prompts)
    assert first.lineage['build_launch']['request']==body.model_dump(mode='json')
    assert service.launch_build_worldbuilding(tmp_path,body).run_id==first.run_id
