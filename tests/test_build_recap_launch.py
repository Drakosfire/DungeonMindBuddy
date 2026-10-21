"""Durable Build Recap request recovery; no external model or real World mutation."""
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from tests.test_build_recap_source import source, context  # noqa: F401
from tests.test_graph_preview_runner import FixtureClient, _first_paragraph_span_id
from apps.live_control_server.main import create_app
from apps.live_control_server.models.build_recap_launch import BuildRecapLaunchRequest
from apps.live_control_server.services import build_recap_launch as service
from apps.live_control_server.services import graph_preview_runner as wrapper
from apps.live_control_server.services.agent_graph_auth import native_graph_gm_dependency
from apps.live_control_server.services.graph_run_registry import GraphRunRegistryError

pytestmark=pytest.mark.usefixtures("application_state_dsn")


@pytest.fixture
def request_body(source):
    record,_,_,digest=source
    return BuildRecapLaunchRequest(request_id=uuid4(),document_id=record.document_id,expected_revision=record.revision,
        expected_content_sha256=digest,managed_world_id="managed-a",campaign_id="longmont-c2",session=30)


@pytest.fixture
def execute(tmp_path,source,context,monkeypatch):
    monkeypatch.setattr(service,"read_recap_ingest_context",lambda **kwargs:context)
    actual=wrapper.run_recap_production_extraction
    calls=[]
    def run(**kwargs):
        # The exact request is durable before production work starts.
        reserved=kwargs["reserved_run"]
        recovered=service.recover_build_recap_launch(tmp_path,request_id=UUID(reserved.lineage['build_launch']['request']['request_id']),
            document_id=UUID(source[0].document_id),managed_world_id="managed-a")
        assert recovered.status.value=="draft" and recovered.run_id==reserved.run_id
        calls.append(reserved.run_id)
        kwargs['category_client']=FixtureClient(span_ref=_first_paragraph_span_id(wrapper._normalized_from_registered(tmp_path,kwargs['build_source_artifact_id'])))
        return actual(**kwargs)
    monkeypatch.setattr(service,"run_recap_production_extraction",run)
    return calls


def test_same_request_recovers_one_actual_run_without_repeating_context_or_inference(tmp_path,source,context,request_body,execute,monkeypatch):
    first=service.launch_build_recap(tmp_path,request_body)
    assert first.status.value=="reviewable"
    source[1].write_text("Newer document bytes.\n")
    monkeypatch.setattr(service,"read_recap_ingest_context",lambda **k:pytest.fail("recovery must not re-read current World/context"))
    second=service.launch_build_recap(tmp_path,request_body)
    assert first==second and execute==[first.run_id]
    assert first.lineage['build_launch']['request']==request_body.model_dump(mode='json')
    assert first.lineage['build_launch']['server_configuration']['model']==wrapper.DEEPSEEK_MODEL


@pytest.mark.parametrize('field,value',[('session',31),('campaign_id','other'),('expected_revision',99),
    ('expected_content_sha256','b'*64),('managed_world_id','managed-b'),('document_id',str(uuid4()))])
def test_reused_request_identity_rejects_changed_configuration_before_reading_source(tmp_path,request_body,execute,monkeypatch,field,value):
    service.launch_build_recap(tmp_path,request_body)
    monkeypatch.setattr(service,'read_recap_ingest_context',lambda **k:pytest.fail('do not retarget a request'))
    changed=BuildRecapLaunchRequest.model_validate({**request_body.model_dump(mode='json'),field:value})
    with pytest.raises(GraphRunRegistryError) as failure:service.launch_build_recap(tmp_path,changed)
    assert failure.value.status_code==409 and len(execute)==1


def test_unknown_execution_is_recovered_as_draft_without_automatic_replay(tmp_path,request_body,context,monkeypatch):
    monkeypatch.setattr(service,'read_recap_ingest_context',lambda **k:context)
    calls=[]
    def interrupted(**kwargs):calls.append(kwargs['reserved_run'].run_id);raise RuntimeError('simulated lost execution')
    monkeypatch.setattr(service,'run_recap_production_extraction',interrupted)
    with pytest.raises(RuntimeError):service.launch_build_recap(tmp_path,request_body)
    recovered=service.launch_build_recap(tmp_path,request_body)
    assert recovered.status.value=='draft' and calls==[recovered.run_id]


def test_concurrent_request_race_has_one_production_executor(tmp_path,request_body,context,execute,monkeypatch):
    barrier=Barrier(2)
    def read_context(**kwargs):barrier.wait(timeout=10);return context
    monkeypatch.setattr(service,'read_recap_ingest_context',read_context)
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures=[pool.submit(service.launch_build_recap,tmp_path,request_body) for _ in range(2)]
        results=[f.result(timeout=30) for f in futures]
    assert results[0].run_id==results[1].run_id
    assert execute==[results[0].run_id]


def test_reserved_revision_cas_precedes_model_execution(tmp_path,request_body,context,monkeypatch):
    from src.graph_memory.extraction import graph_preview_runner as controller
    monkeypatch.setattr(service,'read_recap_ingest_context',lambda **k:context)
    real_advance=controller._advance_run
    def lose_cas(root,run,**kwargs):
        if kwargs['status'].value=='prepared':real_advance(root,run,**kwargs)
        return real_advance(root,run,**kwargs)
    monkeypatch.setattr(controller,'_advance_run',lose_cas)
    class NoModel:
        def run_pass(self,*a,**k):pytest.fail('lost reservation must not call model')
    with pytest.raises(GraphRunRegistryError):service.launch_build_recap(tmp_path,request_body,category_client=NoModel())
    recovered=service.launch_build_recap(tmp_path,request_body,category_client=NoModel())
    assert recovered.status.value=='prepared'


def test_authenticated_routes_recover_the_exact_build_envelope(tmp_path,request_body,execute,monkeypatch):
    monkeypatch.setattr('apps.live_control_server.routes.graph_preview.repo_root',lambda:tmp_path)
    app=create_app();app.dependency_overrides[native_graph_gm_dependency]=lambda:None
    with TestClient(app) as client:
        first=client.post('/api/live/graph-preview/build-recap-launches',json=request_body.model_dump(mode='json'))
        assert first.status_code==200,first.text
        payload=first.json();assert payload['run']['status']=='reviewable'
        assert payload['document_id']==str(request_body.document_id)
        assert payload['source_content_sha256']==request_body.expected_content_sha256
        assert payload['graph_review_handoff']['href'].startswith('/build?')
        recovered=client.get(f'/api/live/graph-preview/build-recap-launches/{request_body.request_id}',params={
            'document_id':str(request_body.document_id),'managed_world_id':'managed-a'})
        assert recovered.status_code==200 and recovered.json()==payload
        wrong=client.get(f'/api/live/graph-preview/build-recap-launches/{request_body.request_id}',params={
            'document_id':str(request_body.document_id),'managed_world_id':'managed-b'})
        assert wrong.status_code==409
    assert len(execute)==1


def test_unauthenticated_launch_and_recovery_never_touch_source(tmp_path,request_body,monkeypatch):
    monkeypatch.delenv('DMB_AGENT_GRAPH_AUTH_MODE',raising=False)
    monkeypatch.setattr(service,'launch_build_recap',lambda *a,**k:pytest.fail('unauthenticated launch'))
    monkeypatch.setattr(service,'recover_build_recap_launch',lambda *a,**k:pytest.fail('unauthenticated recovery'))
    with TestClient(create_app()) as client:
        assert client.post('/api/live/graph-preview/build-recap-launches',json=request_body.model_dump(mode='json')).status_code==503
        assert client.get(f'/api/live/graph-preview/build-recap-launches/{request_body.request_id}',params={
            'document_id':str(request_body.document_id),'managed_world_id':'managed-a'}).status_code==503


@pytest.mark.parametrize('field,value',[('session',True),('expected_revision',True),('mode','worldbuilding'),('raw_text','foreign source'),('model_id','unapproved')])
def test_launch_body_refuses_implicit_reinterpretation(request_body,field,value):
    with pytest.raises(ValidationError):BuildRecapLaunchRequest.model_validate({**request_body.model_dump(mode='json'),field:value})


def test_failed_model_run_is_recovered_without_retry(tmp_path,request_body,context,monkeypatch):
    monkeypatch.setattr(service,'read_recap_ingest_context',lambda **k:context)
    client=FixtureClient(mode='refusal')
    first=service.launch_build_recap(tmp_path,request_body,category_client=client)
    assert first.status.value=='failed'
    monkeypatch.setattr(service,'run_recap_production_extraction',lambda **k:pytest.fail('failed request must not execute again'))
    assert service.launch_build_recap(tmp_path,request_body)==first
