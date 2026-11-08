"""Object-unit retrieval at the frozen query and APP read-grant boundaries."""
from types import SimpleNamespace
from uuid import uuid4
import json

import pytest
from pydantic import ValidationError
from application_state.agent_conversation.native_plan_assertions import (
    NativeGraphQueryV4, NativeGraphQueryV3, NativePlanAssertionMatchV1,
    NativeObjectMatchV1, object_record_ids, object_selection_handle,
    NativePlanAssertionReadAuthorizedV1,
)
from application_state.agent_conversation.native_plan_statements import (
    NativePlanQueryAuthorityV1, NativePlanStatementMatchV1, validate_selected_record_events,
)
from application_state.agent_conversation import types as t
from application_state.agent_conversation.jev_retrieval_contract import (
    NativeRetrievalDecisionInputV1, prepare_decision,
)
from apps.live_control_server.services.plan_jev_driver import PlanJevDriver


def query(count=3, objects=2):
    roots = tuple(f'ent:object-{i}' for i in range(objects))
    ref = dict(authority_id='synthetic', revision='1', descriptor_sha256='a'*64)
    return NativeGraphQueryV4(authority=NativePlanQueryAuthorityV1(
        managed_world_id='test', native_world_id='test', binding_version=1,
        revision_id='rev:1', domain_ref=ref, profile_ref=ref,
        acquisition_epoch=1, scope_mode='world', campaign_id=None),
        question='What happened?', search_result_sha256='b'*64,
        discovered_entity_ids=roots, matches=(), authored_targets=(),
        status='complete', gap_codes=(),
        object_matches=tuple(NativeObjectMatchV1(entity_id=r, label=f'Object {i}') for i,r in enumerate(roots)),
        assertion_matches=tuple(NativePlanAssertionMatchV1(
            assertion_id=f'asrt:{i}', subject_entity_id=roots[i % objects],
            discovered_entity_ids=(roots[i % objects],), assertion_sha256='c'*64,
            label=f'Object {i % objects} · dnd5e:summary') for i in range(count)))


def driver(q):
    result=PlanJevDriver.__new__(PlanJevDriver)
    result.adapter=SimpleNamespace(native_query=q)
    result.native_statement_attempts=set()
    result.native_assertion_attempts=set()
    return result


def test_captured_fanout_shape_keeps_all_records_with_twenty_votes():
    q=query(1221,20)
    d=driver(q)
    offered=d._native_object_candidates()
    assert len(offered)==20
    handles=tuple(c.handle for c in offered)
    assert set(object_record_ids(q,handles,assertion=True))=={m.assertion_id for m in q.assertion_matches}
    req=NativeRetrievalDecisionInputV1(request_id=uuid4(),parent_attempt_id=uuid4(),
        scope_sha256='d'*64,question=q.question,candidates=offered,
        source_authority_status='unavailable',source_revision=None,graph_revision='rev:1',
        allowed_operations=('select_candidates','finish_retrieval'))
    prepared=prepare_decision(req)
    assert len(prepared.questions)==21
    for candidate, visible in zip(offered, prepared.state['candidates']):
        count = len(object_record_ids(q, (candidate.handle,), assertion=True))
        assert f'Opening now reads {count} assertions and 0 statements' in visible['kind']
        assert 'not relevance or answer sufficiency' in visible['kind']
    # Every record remains in the frozen query, none is repeated into semantic choices.
    assert 'asrt:' not in json.dumps(prepared.state)
    d.native_assertion_attempts.update(object_record_ids(q,(handles[0],),assertion=True))
    assert len(d._native_object_candidates())==19
    assert len(d._native_object_candidates(examined=True))==1


def test_read_size_is_remaining_per_object_not_additive_or_success_count():
    q = query()
    shared = q.assertion_matches[0].model_copy(update={
        'discovered_entity_ids': q.discovered_entity_ids})
    statement = NativePlanStatementMatchV1(statement_id='ent:statement',
        discovered_entity_ids=q.discovered_entity_ids,
        discovery_assertion_ids=('asrt:discovery',), campaign_id='c1',
        logical_source={'session': 's1'}, episode='s1', label='Shared statement')
    q = q.model_copy(update={'assertion_matches': (shared, *q.assertion_matches[1:]),
        'matches': (statement,)})
    d = driver(q)
    offered = d._native_object_candidates()
    assert all('Opening now reads 2 assertions and 1 statements' in c.kind for c in offered)
    # Per-object counts overlap; selecting both still opens only three assertions.
    handles = tuple(c.handle for c in offered)
    assert len(object_record_ids(q, handles, assertion=True)) == 3
    # Attempts are consumed even when support was unavailable; no successful-read
    # inference and no reoffer of the attempted shared record in either object.
    d.native_assertion_attempts.add('asrt:0')
    d.native_statement_attempts.add('ent:statement')
    assert all('Opening now reads 1 assertions and 0 statements' in c.kind
        for c in d._native_object_candidates())
    d.native_assertion_attempts.add('asrt:2')
    examined = d._native_object_candidates(examined=True, opened={(True, 'asrt:2')})
    assert len(examined) == 1
    assert examined[0].kind == 'Previously selected native object: partial; not an answer-sufficiency verdict'
    assert [c.handle for c in d._native_object_candidates()] == [handles[1]]


def test_overlap_deduplicates_and_attempted_records_cannot_reopen():
    q=query()
    first=q.assertion_matches[0].model_copy(update={'discovered_entity_ids':q.discovered_entity_ids})
    q=q.model_copy(update={'assertion_matches':(first,*q.assertion_matches[1:])})
    handles=tuple(object_selection_handle(q,r) for r in q.discovered_entity_ids)
    assert len(object_record_ids(q,handles,assertion=True))==3
    assert object_record_ids(q,handles,assertion=True,attempted=('asrt:0','asrt:1'))==('asrt:2',)
    assert not object_record_ids(q,('native-object:foreign',),assertion=True)
    other=q.model_copy(update={'search_result_sha256':'e'*64})
    assert not object_record_ids(other,handles,assertion=True)


def test_object_catalog_cannot_hide_or_invent_discovered_roots():
    raw=query().model_dump(by_alias=True)
    with pytest.raises(ValidationError):
        NativeGraphQueryV4.model_validate(raw|{'object_matches':raw['object_matches'][:1]})
    with pytest.raises(ValidationError):
        NativeGraphQueryV4.model_validate(raw|{'object_matches':raw['object_matches']*2})
    with pytest.raises(ValueError):
        object_selection_handle(query(),'ent:foreign')


def execution(q,ids,*,handles=None,writer=False):
    attempt=uuid4()
    provider=t.ProviderAttemptAuthorizedEventV1.model_construct(kind='provider_attempt_authorized_v1',provider_attempt_id=attempt)
    outcome=t.ProviderOutcomeEventV1.model_construct(provider_attempt_id=attempt,outcome='response_received')
    selection=t.PlanJevRetrievalSelectionV1.model_construct(
        operation='select_candidates',selected_handles=handles or (object_selection_handle(q,q.discovered_entity_ids[0]),))
    grant=NativePlanAssertionReadAuthorizedV1(event_id=uuid4(),sequence=3,
        provider_attempt_id=attempt,query_sha256=q.sha256,assertion_ids=ids)
    events=[provider,outcome,selection,grant]
    if writer:
        events.append(t.ProviderAttemptAuthorizedEventV1.model_construct(
            kind='provider_attempt_authorized_v1',provider_attempt_id=uuid4()))
    return SimpleNamespace(events=events)


def test_app_rejects_partial_foreign_or_per_record_grants_for_object_selection():
    q=query()
    valid=object_record_ids(q,(object_selection_handle(q,q.discovered_entity_ids[0]),),assertion=True)
    validate_selected_record_events(q,execution(q,valid))
    for ids in (valid[:1],('asrt:foreign',),('asrt:1',)):
        with pytest.raises(ValueError,match='exact current controller/query grant'):
            validate_selected_record_events(q,execution(q,ids))
    with pytest.raises(ValueError):
        validate_selected_record_events(q,execution(q,valid,handles=('native-assertion:old',)))


def test_omitted_other_family_blocks_next_provider():
    q=query()
    statement=NativePlanStatementMatchV1(statement_id='ent:statement',
        discovered_entity_ids=(q.discovered_entity_ids[0],),discovery_assertion_ids=('asrt:witness',),
        campaign_id='c1',logical_source={'object_id':'recap'},episode='1',label='Qualified statement')
    q=q.model_copy(update={'matches':(statement,)})
    ids=object_record_ids(q,(object_selection_handle(q,q.discovered_entity_ids[0]),),assertion=True)
    with pytest.raises(ValueError,match='complete record closure'):
        validate_selected_record_events(q,execution(q,ids,writer=True))


def test_historical_query_keeps_its_exact_per_record_grant_meaning():
    from application_state.agent_conversation.native_plan_assertions import selection_handle
    raw=query().model_dump(by_alias=True)
    raw.pop('object_matches')
    raw['schema']='dmb_native_graph_query_v3'
    old=NativeGraphQueryV3.model_validate(raw)
    validate_selected_record_events(old,execution(old,('asrt:0',),handles=(selection_handle(old,old.assertion_matches[0]),)))


def test_unobserved_complete_grant_blocks_followup_provider():
    q=query()
    handles=(object_selection_handle(q,q.discovered_entity_ids[0]),)
    ids=object_record_ids(q,handles,assertion=True)
    with pytest.raises(ValueError,match='settle its complete record closure'):
        validate_selected_record_events(q,execution(q,ids,writer=True))


@pytest.mark.parametrize("handles", [(), ("native-full-document:source",),
    ("native-body:source:section", "rules:lookup", "saved-page:page")])
@pytest.mark.parametrize("assertion", [False, True])
def test_source_only_selection_has_no_object_closure_or_query_hash(monkeypatch, handles, assertion):
    q = query(1221, 20)
    def unexpected_hash(_):
        raise AssertionError("Source-only selection serialized the unrelated Graph query")
    monkeypatch.setattr(NativeGraphQueryV4, 'sha256', property(unexpected_hash))
    assert object_record_ids(q, handles, assertion=assertion) == ()


def test_mixed_source_and_object_selection_retains_exact_closure():
    q = query()
    handle = object_selection_handle(q, q.discovered_entity_ids[0])
    mixed = ('native-full-document:source', handle, 'rules:lookup')
    assert object_record_ids(q, mixed, assertion=True) == ('asrt:0', 'asrt:2')
    assert object_record_ids(q, mixed, assertion=True, attempted=('asrt:0',)) == ('asrt:2',)
    validate_selected_record_events(q, execution(q, ('asrt:0', 'asrt:2'), handles=mixed))
    with pytest.raises(ValueError, match='exact current controller/query grant'):
        validate_selected_record_events(q, execution(q, ('asrt:0', 'asrt:2'),
            handles=('native-full-document:source',)))
