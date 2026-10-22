"""HTTP admission joins real acceptance journals and real APP state; IO is mocked."""
import json
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from apps.live_control_server.main import create_app
from apps.live_control_server.services import world_mechanics_associations as orchestration
from apps.live_control_server.services.agent_graph_auth import NativeGraphPrincipal, native_graph_gm_dependency
from apps.live_control_server.services.threat_draft_store import create_threat_draft, append_candidate_ref, get_threat_draft
from apps.live_control_server.models.threat_draft import CreateWorldThreatDraftRequest, ThreatDraftCandidateRefV1
from apps.live_control_server.models.statblock_mechanics_acceptance import AcceptThreatDraftMechanicsRequestV1
from apps.live_control_server.services.statblock_mechanics_acceptance import begin_or_resume_acceptance
from apps.live_control_server.integrations.dungeonmind_statblocks.models import ExactRevisionResourceV1
from apps.live_control_server.integrations.dungeonmind_statblocks.generated import ValidationResponseV1
from apps.live_control_server.integrations.dungeonmind_statblocks.mechanics_locator import CreateStatblockResult, locator_from_exact_revision
from apps.live_control_server.integrations.dungeonmind_statblocks.definition_digest import canonicalize_definition_dict, source_definition_digest_from_body
from application_state.world_mechanics import service as state

FIXTURES=Path(__file__).parent/'fixtures/statblocks/v1'


@pytest.fixture
def prepared(application_state_dsn,monkeypatch,tmp_path):
    def fixture(name):return json.loads((FIXTURES/name).read_text())
    definition=fixture('create-request.json')['definition']
    digest=source_definition_digest_from_body(definition)
    exact=fixture('exact-revision-response.json')
    exact.update(definition=definition,canonical_definition=canonicalize_definition_dict(definition),definition_digest=digest)
    exact['validation_receipt'].update(definition_digest=digest,status='valid',issues=[])
    revision=ExactRevisionResourceV1.model_validate(exact)
    class DMS:
        calls=0
        def validate_definition(self,body):
            return ValidationResponseV1(definition_digest=digest,validation_receipt=revision.validation_receipt)
        def create_statblock(self,body):
            return CreateStatblockResult(locator=locator_from_exact_revision(revision),server_metadata={})
        def get_exact_revision(self,statblock_id,revision_id):
            self.calls+=1
            assert (statblock_id,revision_id)==(revision.statblock_id,revision.revision_id)
            return revision
        def close(self):pass
    dms=DMS()
    draft=create_threat_draft(tmp_path,CreateWorldThreatDraftRequest(
        scope_mode='world',world_id='elderwyld',campaign_id=None,name='Keeper',description='Synthetic',threat_kind='creature',
        generation_intent={'ruleset':{'system':'dnd5e','edition':'2024'}},
        graph_context_snapshot={'graph_revision_id':'rev:head'},created_by='gm'))
    append_candidate_ref(tmp_path,draft_id=draft.draft_id,expected_version=1,candidate_ref=ThreatDraftCandidateRefV1(
        candidate_id='cand_fixture1',generated_from_draft_version=1,request_id='generate1',created_at='2026-10-22T00:00:00Z'))
    accepted=begin_or_resume_acceptance(tmp_path,draft_id=draft.draft_id,client=dms,request=AcceptThreatDraftMechanicsRequestV1(
        operation_id=str(uuid4()),expected_draft_version=1,definition=definition,validation_receipt=revision.validation_receipt,
        validation_definition_digest=digest,source_candidate_id='cand_fixture1',change_summary='Synthetic acceptance',actor='gm'))
    assert accepted.result_label=='mechanics_saved'
    draft=get_threat_draft(tmp_path,draft.draft_id)
    target=dict(managed_world_id='elderwyld',native_world_id='world:opaque',binding_version=1,
        graph_revision_id='rev:head',node_id='node:keeper',label='Keeper',kind='npc',role='',campaign_scope=None)
    node=SimpleNamespace(node_id=target['node_id'],label=target['label'],kind='npc',role='',campaign_scope=None)
    view=SimpleNamespace(managed_world_id='elderwyld',native_world_id='world:opaque',binding_version=1,
        projection=SimpleNamespace(nodes=[node],snapshot=SimpleNamespace(is_head=True,revision_id='rev:head')))
    binding=SimpleNamespace(native_world_id='world:opaque',binding_version=1)
    monkeypatch.setattr(orchestration,'project_managed_world_graph',lambda request:view)
    monkeypatch.setattr(orchestration,'resolve_managed_world_binding',lambda world:binding)
    monkeypatch.setattr(orchestration,'build_statblock_v1_client',lambda:dms)
    monkeypatch.setenv('DMB_ARTIFACT_DATA_ROOT',str(tmp_path))
    from apps.live_control_server.routes import world_mechanics_associations as routes
    monkeypatch.setattr(routes,'resolve_managed_world_binding',lambda world:binding)
    app=create_app();app.dependency_overrides[native_graph_gm_dependency]=lambda:NativeGraphPrincipal('gm-test','gm','local_operator')
    body=dict(request_id=str(uuid4()),draft_id=draft.draft_id,expected_draft_version=draft.version,target=target,expected_version=0)
    return SimpleNamespace(client=TestClient(app),app=app,body=body,dms=dms,view=view,binding=binding,root=tmp_path,draft=draft,revision=revision)


def post(p,body=None):return p.client.post('/api/live/world-mechanics/associations?world_id=elderwyld',json=body or p.body)


def test_http_exact_proof_append_replay_and_reopen(prepared,monkeypatch):
    p=prepared;r=post(p);assert r.status_code==200,r.text
    record=r.json()['association'];assert r.json()['replayed'] is False
    assert record['proof']['accepted_from_draft_version']==1
    assert record['request']['expected_draft_version']==2
    assert record['proof']['accepted_from_candidate_id']=='cand_fixture1'
    assert record['actor']=='gm-test' and p.dms.calls==1
    monkeypatch.setattr(orchestration,'get_threat_draft',lambda *a:pytest.fail('Replay read external state'))
    monkeypatch.setenv('DMB_ARTIFACT_DATA_ROOT',str(p.root/'unavailable'))
    replay=post(p);assert replay.json()=={'association':record,'replayed':True}
    assert p.dms.calls==1
    listed=p.client.get('/api/live/world-mechanics/associations?world_id=elderwyld')
    assert listed.json()==[record]
    changed={**p.body,'expected_draft_version':3}
    assert post(p,changed).status_code==409


@pytest.mark.parametrize('change',['head','mapping','label','kind','draft','foreign','node'])
def test_http_stale_or_forged_target_never_writes(prepared,change):
    p=prepared
    if change=='head':p.view.projection.snapshot.revision_id='rev:new'
    elif change=='mapping':p.binding.binding_version=2
    elif change=='label':p.body['target']['label']='Forged'
    elif change=='kind':p.view.projection.nodes[0].kind='location';p.body['target']['kind']='location'
    elif change=='draft':p.body['expected_draft_version']+=1
    elif change=='foreign':p.body['target']['managed_world_id']='foreign'
    elif change=='node':p.body['target']['node_id']='node:missing'
    response=post(p);assert response.status_code==409,response.text
    assert state.list_current(world_id='elderwyld')==[]


def test_http_missing_acceptance_proof_and_tampered_exact_revision_refused(prepared,monkeypatch):
    p=prepared
    monkeypatch.setattr(orchestration,'list_acceptance_operations_for_draft',lambda *a,**kw:[])
    assert post(p).status_code==500
    assert p.dms.calls==0 and state.list_current(world_id='elderwyld')==[]


def test_http_exact_mechanics_tampering_refused(prepared):
    p=prepared
    p.revision.definition.identity.name='Tampered'
    assert post(p).status_code==503
    assert state.list_current(world_id='elderwyld')==[]


def test_http_authentication_required_and_request_forbids_mechanics_injection(prepared,monkeypatch):
    p=prepared
    assert post(p,{**p.body,'proof':{'locator':'invented'}}).status_code==422
    p.app.dependency_overrides.clear()
    monkeypatch.setenv('DMB_AGENT_GRAPH_AUTH_MODE','local_operator')
    monkeypatch.setenv('DMB_AGENT_GRAPH_AUTH_ENVIRONMENT','development')
    monkeypatch.setenv('DMB_AGENT_GRAPH_LOCAL_OPERATOR_TOKEN','a'*40)
    assert post(p).status_code == 403
    local=TestClient(p.app,client=('127.0.0.1',50000))
    assert local.post('/api/live/world-mechanics/associations?world_id=elderwyld',json=p.body).status_code==401
    assert state.list_current(world_id='elderwyld')==[]


def test_http_final_draft_recheck_refuses_concurrent_change(prepared,monkeypatch):
    from contextlib import contextmanager
    p=prepared; read=orchestration.locked_threat_draft
    @contextmanager
    def changed(*args):
        with read(*args) as result:
            yield result.model_copy(update={"version":result.version+1})
    monkeypatch.setattr(orchestration,'locked_threat_draft',changed)
    assert post(p).status_code==409
    assert state.list_current(world_id='elderwyld')==[]


def test_http_corrupt_acceptance_journal_is_not_absence(prepared,monkeypatch):
    from apps.live_control_server.services.statblock_acceptance_reconciliation import AcceptanceReconciliationError
    def unavailable(*a,**kw):raise AcceptanceReconciliationError('Stored acceptance proof is invalid',status_code=500)
    monkeypatch.setattr(orchestration,'list_acceptance_operations_for_draft',unavailable)
    assert post(prepared).status_code==500
    assert prepared.dms.calls==0
    assert state.list_current(world_id='elderwyld')==[]


def test_draft_lock_is_held_through_short_app_append(prepared,monkeypatch):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Event
    p=prepared; append=state.append_verified; entered=Event(); observed=[]
    with ThreadPoolExecutor(max_workers=1) as pool:
        def read():
            entered.set()
            return get_threat_draft(p.root,p.draft.draft_id)
        def verify_lock(**kw):
            future=pool.submit(read);observed.append(future)
            assert entered.wait(timeout=2)
            assert not future.done()
            return append(**kw)
        monkeypatch.setattr(state,'append_verified',verify_lock)
        assert post(p).status_code==200
        assert observed[0].result(timeout=3)==p.draft
