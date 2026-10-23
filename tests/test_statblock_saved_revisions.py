"""Manual Save through real HTTP, acceptance journal and APP; synthetic DMS IO."""
from copy import deepcopy
from uuid import uuid4
import pytest
from tests.test_world_mechanics_associations import prepared
from apps.live_control_server.services import statblock_saved_revision as service
from apps.live_control_server.services.threat_draft_store import get_threat_draft
from apps.live_control_server.integrations.dungeonmind_statblocks.models import ExactRevisionResourceV1
from apps.live_control_server.integrations.dungeonmind_statblocks.generated import ValidationResponseV1
from apps.live_control_server.integrations.dungeonmind_statblocks.definition_digest import source_definition_digest_from_body,canonicalize_definition_dict
from apps.live_control_server.integrations.dungeonmind_statblocks.errors import downstream_timeout,downstream_conflict


@pytest.fixture
def revision_case(prepared,monkeypatch):
    p=prepared
    class DMS:
        def __init__(self):
            self.versions={p.revision.revision_id:p.revision};self.keys={};self.appends=0;self.timeout=False
        def get_exact_revision(self,sb,rev):return self.versions[rev]
        def validate_definition(self,body):
            definition=body.definition.model_dump(mode='json') if hasattr(body,'definition') else body['definition']
            digest=source_definition_digest_from_body(definition)
            receipt=p.revision.validation_receipt.model_copy(update={'definition_digest':digest})
            return ValidationResponseV1(definition_digest=digest,validation_receipt=receipt)
        def append_revision(self,sb,body):
            key=body['idempotency_key']
            if key in self.keys:
                assert self.keys[key][0]==body
                return self.keys[key][1]
            if body['parent_revision_id']!=list(self.versions)[-1]:
                raise downstream_conflict('stale',error_code='stale_parent_revision')
            self.appends+=1
            definition=body['definition'];digest=source_definition_digest_from_body(definition)
            raw=p.revision.model_dump(mode='json')|dict(revision_id='rev_saved'+str(self.appends),parent_revision_id=body['parent_revision_id'],
                definition=definition,definition_digest=digest,canonical_definition=canonicalize_definition_dict(definition),asset_bindings=body['asset_bindings'],
                provenance={'accepted_through':body['accepted_through']})
            raw['validation_receipt']=raw['validation_receipt']|dict(definition_digest=digest)
            exact=ExactRevisionResourceV1.model_validate(raw)
            self.keys[key]=(deepcopy(body),exact);self.versions[exact.revision_id]=exact
            if self.timeout:self.timeout=False;raise downstream_timeout()
            return exact
        def close(self):pass
    p.manual=DMS();monkeypatch.setattr(service,'build_statblock_v1_client',lambda:p.manual)
    p.url=f'/api/live/threat-drafts/{p.draft.draft_id}/mechanics-revisions'
    definition=deepcopy(p.revision.model_dump(mode='json')['definition']);definition['identity']['name']='Stronger keeper'
    p.request=dict(operation_id=str(uuid4()),world_id='elderwyld',base=p.draft.accepted_mechanics_ref.to_mechanics_locator().model_dump(mode='json'),definition=definition,change_summary='Stronger enemy')
    return p


def test_manual_success_exact_replay_history_old_new_and_original_unchanged(revision_case):
    p=revision_case;before=get_threat_draft(p.root,p.draft.draft_id)
    response=p.client.post(p.url,json=p.request);assert response.status_code==200,response.text
    saved=response.json();assert saved['state']=='committed' and p.manual.appends==1
    assert p.client.post(p.url,json=p.request).json()==saved and p.manual.appends==1
    history=p.client.get(p.url,params={'world_id':'elderwyld'}).json()
    assert history['original']==p.request['base'] and history['operations'][0]['result']==saved['result']
    for locator in (history['original'],saved['result']):
        opened=p.client.get(p.url+'/'+locator['revision_id'],params={'world_id':'elderwyld'})
        assert opened.status_code==200,opened.text
        assert opened.json()['locator']==locator
    assert get_threat_draft(p.root,p.draft.draft_id)==before


def test_timeout_after_remote_commit_blocks_new_key_and_recovers_exact_once(revision_case):
    p=revision_case;p.manual.timeout=True
    response=p.client.post(p.url,json=p.request);assert response.status_code==200,response.text
    assert response.json()['state']=='outcome_unknown' and p.manual.appends==1
    assert p.client.post(p.url,json=p.request|dict(operation_id=str(uuid4()))).status_code==409
    changed=deepcopy(p.request);changed['change_summary']='Different intent'
    assert p.client.post(p.url,json=changed).status_code==409
    recovery=p.client.post(p.url.replace('mechanics-revisions','mechanics-revision-operations')+'/'+p.request['operation_id']+':recover',params={'world_id':'elderwyld'})
    assert recovery.status_code==200,recovery.text
    assert recovery.json()['state']=='committed' and p.manual.appends==1


def test_stale_parent_refused_without_rebase_and_unknown_version_rejected(revision_case):
    p=revision_case
    assert p.client.post(p.url,json=p.request).json()['state']=='committed'
    stale=p.client.post(p.url,json=p.request|dict(operation_id=str(uuid4())))
    assert stale.status_code==200,stale.text
    assert stale.json()['state']=='refused' and stale.json()['refusal_code']=='stale_parent_revision'
    assert p.manual.appends==1
    assert p.client.get(p.url+'/rev_other',params={'world_id':'elderwyld'}).status_code==409


@pytest.mark.parametrize('change',['world','digest','ruleset'])
def test_foreign_or_changed_source_never_dispatches(revision_case,change):
    p=revision_case
    if change=='world':p.request['world_id']='other-world'
    elif change=='digest':p.request['base']['definition_digest']='sha256:'+'a'*64
    else:p.request['definition']['ruleset']['edition']='2014'
    response=p.client.post(p.url,json=p.request)
    assert response.status_code==409,response.text
    assert p.manual.appends==0


def test_new_revision_can_be_parent_without_extending_original_acceptance(revision_case):
    p=revision_case
    first=p.client.post(p.url,json=p.request).json();assert first['state']=='committed'
    request=p.request|dict(operation_id=str(uuid4()),base=first['result'])
    response=p.client.post(p.url,json=request);assert response.status_code==200,response.text
    assert response.json()['state']=='committed' and p.manual.appends==2
    assert get_threat_draft(p.root,p.draft.draft_id).accepted_mechanics_ref.to_mechanics_locator().model_dump(mode='json')==p.request['base']


@pytest.mark.parametrize('change',[None,'parent','statblock','content','digest'])
def test_real_producer_adapter_checks_exact_append_response(change):
    import httpx,json
    from tests.test_dungeonmind_statblocks_client import _fixture,_client,_reseal_revision_payload
    from apps.live_control_server.integrations.dungeonmind_statblocks.errors import StatblockIntegrationError
    original=_fixture('exact-revision-response.json')
    definition=deepcopy(original['definition']);definition['identity']['name']='Manual successor'
    body=dict(idempotency_key=str(uuid4()),parent_revision_id=original['revision_id'],definition=definition,change_summary='Manual change')
    result=_reseal_revision_payload(original|dict(definition=definition,revision_id='rev_manual1',parent_revision_id=body['parent_revision_id']))
    if change=='parent':result['parent_revision_id']='rev_wrong'
    elif change=='statblock':result['statblock_id']='sb_wrong'
    elif change=='content':
        result['definition']['identity']['name']='Unrequested';result=_reseal_revision_payload(result)
    elif change=='digest':result['definition_digest']='sha256:'+'0'*64
    calls=[]
    def handler(request):
        calls.append(request);wire=json.loads(request.content)
        assert wire['idempotency_key']==body['idempotency_key'] and wire['parent_revision_id']==body['parent_revision_id']
        return httpx.Response(200,json=result)
    client=_client(httpx.MockTransport(handler))
    try:
        if change:
            with pytest.raises(StatblockIntegrationError):client.append_revision(original['statblock_id'],body)
        else:assert client.append_revision(original['statblock_id'],body).revision_id=='rev_manual1'
        assert len(calls)==1
    finally:client.close()


def test_http_manual_revision_auth_required(revision_case,monkeypatch):
    p=revision_case;p.app.dependency_overrides.clear()
    monkeypatch.setenv('DMB_AGENT_GRAPH_AUTH_MODE','local_operator')
    monkeypatch.setenv('DMB_AGENT_GRAPH_AUTH_ENVIRONMENT','development')
    monkeypatch.setenv('DMB_AGENT_GRAPH_LOCAL_OPERATOR_TOKEN','a'*40)
    assert p.client.post(p.url,json=p.request).status_code==403
    assert p.manual.appends==0


def test_committed_replay_does_not_require_producer_availability(revision_case,monkeypatch):
    p=revision_case;first=p.client.post(p.url,json=p.request);assert first.json()['state']=='committed'
    monkeypatch.setattr(service,'build_statblock_v1_client',lambda:pytest.fail('Acknowledged Save must replay locally'))
    assert p.client.post(p.url,json=p.request).json()==first.json()


def test_application_failure_after_remote_commit_recovers_without_second_revision(revision_case,monkeypatch):
    from application_state.errors import ApplicationStateUnavailableError
    p=revision_case;settle=service.operations.settle
    def fail_commit(record,**kwargs):
        if kwargs['state']=='committed':raise ApplicationStateUnavailableError('Synthetic DB interruption')
        return settle(record,**kwargs)
    monkeypatch.setattr(service.operations,'settle',fail_commit)
    failed=p.client.post(p.url,json=p.request);assert failed.status_code==503
    assert p.manual.appends==1
    monkeypatch.setattr(service.operations,'settle',settle)
    recovered=p.client.post(p.url,json=p.request)
    assert recovered.status_code==200 and recovered.json()['state']=='committed' and p.manual.appends==1


@pytest.mark.parametrize('change',['parent','provenance','receipt'])
def test_unverified_producer_result_remains_unknown_until_exact_recovery(revision_case,monkeypatch,change):
    p=revision_case;append=p.manual.append_revision
    def forged(sb,body):
        result=append(sb,body).model_copy(deep=True)
        if change=='parent':result.parent_revision_id='rev_wrong'
        elif change=='provenance':result.provenance={'accepted_through':{'buddy_manual_revision':'wrong'}}
        else:
            from apps.live_control_server.integrations.dungeonmind_statblocks.generated.models import ValidationStatus
            result.validation_receipt.status=ValidationStatus.invalid
        return result
    monkeypatch.setattr(p.manual,'append_revision',forged)
    response=p.client.post(p.url,json=p.request)
    assert response.status_code==200,response.text
    assert response.json()['state']=='outcome_unknown' and p.manual.appends==1
    monkeypatch.setattr(p.manual,'append_revision',append)
    assert p.client.post(p.url,json=p.request).json()['state']=='committed' and p.manual.appends==1


def test_manual_save_does_not_replace_association_or_retained_fight(revision_case):
    from tests.test_world_mechanics_associations import post
    from application_state.world_mechanics.service import list_current
    from application_state.combat_encounters.service import create_encounter,get_encounter
    from application_state.combat_encounters.types import CreateCombatEncounterRequest
    p=revision_case
    association=post(p);assert association.status_code==200,association.text
    before=list_current(world_id='elderwyld')
    fight=create_encounter(world_id='elderwyld',request=CreateCombatEncounterRequest(title='Retained manual fight'))
    response=p.client.post(p.url,json=p.request);assert response.json()['state']=='committed'
    assert list_current(world_id='elderwyld')==before
    assert get_encounter(world_id='elderwyld',encounter_id=fight.encounter_id)==fight


def test_http_recovery_fences_a_paused_preflight_before_it_can_dispatch(revision_case,monkeypatch):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Event
    from apps.live_control_server.models.statblock_saved_revision import SaveMechanicsRevisionRequest
    from application_state.errors import ApplicationStateConflictError
    p=revision_case;ready=Event();release=Event();claim=service.operations.claim
    def pause(record):
        ready.set();assert release.wait(timeout=5);return claim(record)
    monkeypatch.setattr(service.operations,'claim',pause)
    with ThreadPoolExecutor(max_workers=1) as pool:
        future=pool.submit(service.save,p.root,draft_id=p.draft.draft_id,request=SaveMechanicsRevisionRequest.model_validate(p.request),client=p.manual)
        assert ready.wait(timeout=5)
        response=p.client.post(p.url.replace('mechanics-revisions','mechanics-revision-operations')+'/'+p.request['operation_id']+':recover',params={'world_id':'elderwyld'})
        assert response.status_code==200 and response.json() is None
        release.set()
        with pytest.raises(ApplicationStateConflictError,match='canceled before dispatch'):future.result(timeout=5)
    assert p.manual.appends==0



def test_source_media_bindings_survive_nullable_input_output_projection(revision_case):
    from apps.live_control_server.integrations.dungeonmind_statblocks.generated.models import AssetBindingV1Output
    p=revision_case
    binding=AssetBindingV1Output.model_validate(dict(role='portrait',asset=dict(asset_id='synthetic-portrait',provider_kind='image_pipeline',
        url='https://example.test/keeper.png',mime_type='image/png',created_at='2026-10-22T00:00:00Z')))
    p.revision.asset_bindings=[binding]
    result=p.client.post(p.url,json=p.request)
    assert result.status_code==200,result.text
    assert result.json()['state']=='committed'
    assert p.manual.versions[result.json()['result']['revision_id']].asset_bindings==[binding]
