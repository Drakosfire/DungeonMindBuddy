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
    NativePlanQueryV1, NativePlanStatementReadAuthorizedV1, NativePlanStatementReadObservedV1,
    selection_handle, validate_record_reads,
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
    # Every record remains in the frozen query, none is repeated into semantic choices.
    assert 'asrt:' not in json.dumps(prepared.state)
    d.native_assertion_attempts.update(object_record_ids(q,(handles[0],),assertion=True))
    assert len(d._native_object_candidates())==19
    assert len(d._native_object_candidates(examined=True))==1


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


@pytest.mark.parametrize('surface', ['plan','build'])
def test_current_dispatch_owns_new_codec_and_keeps_host_context_private(surface):
    from tests.test_surface_native_execution import component
    from apps.live_control_server.services.plan_jev_dispatch import PlanJevDispatch
    from application_state.agent_conversation.jev_retrieval_contract import (
        NativeRetrievalDecisionInputV2, NativeBuildRetrievalDecisionInputV4, parse_native_retrieval_input,
    )
    receipt,_=component(surface)
    adapter=SimpleNamespace(request=SimpleNamespace(message='Find the requested source.'),
        fence=SimpleNamespace(turn=SimpleNamespace(graph_context_receipt=receipt)))
    dispatch=PlanJevDispatch(adapter,driver(query())._native_object_candidates())
    assert type(dispatch.parent) is (NativeBuildRetrievalDecisionInputV4 if surface=='build' else NativeRetrievalDecisionInputV2)
    assert parse_native_retrieval_input(dispatch.parent.model_dump(by_alias=True),surface_id=surface)==dispatch.parent
    assert dispatch._host_phase()==('navigate' if surface=='build' else None)
    prepared=prepare_decision(dispatch.parent)
    assert 'context_accounting' not in prepared.state and 'phase' not in prepared.state
    assert all(q.question.endswith('Apply relevance_guidance.') for q in prepared.questions[1:])


# Test-only predicate at merged5d63a5c74; relative imports qualified for tests.
def _original_record_predicate(query, execution):
    """Shared native selected-record checks; source admission remains with Core."""
    from application_state.agent_conversation import types as t
    from application_state.agent_conversation.native_plan_assertions import (NativePlanQueryV2, NativePlanAssertionReadAuthorizedV1,
        NativePlanAssertionReadObservedV1, selection_handle as assertion_handle)
    from application_state.agent_conversation.native_plan_assertions import NativeGraphQueryV4, object_record_ids
    statements = {m.statement_id: m for m in query.matches} if isinstance(query, NativePlanQueryV1) else {}
    assertions = {m.assertion_id: m for m in query.assertion_matches} if isinstance(query, NativePlanQueryV2) else {}
    provider = outcome = selection = None
    grants, observations, attempted = {}, {}, set()
    writer = False
    pending_object_reads = set()
    for event in execution.events:
        if isinstance(event, t.ProviderAttemptAuthorizedEventV1):
            if pending_object_reads or (isinstance(query, NativeGraphQueryV4)
                    and set(grants) != {e.authorization_event_id for e in observations.values()}):
                raise ValueError('Native object selection must acquire and settle its complete record closure before another provider')
            shared_writer = False
            if event.kind in {"native_writer_authorized_v1", "native_build_writer_authorized_v2"}:
                from application_state.agent_conversation.native_execution import NATIVE_WRITER_TYPES
                shared_writer = type(event) in NATIVE_WRITER_TYPES
            if shared_writer or isinstance(event, t.PlanJevWriterAuthorizedV1):
                if not shared_writer:
                    expected = t.PlanNativeWriterAuthorizedV2 if isinstance(query, NativePlanQueryV2) else t.PlanNativeWriterAuthorizedV1
                    if not isinstance(event, expected) or (not isinstance(query, NativePlanQueryV2) and isinstance(event, t.PlanNativeWriterAuthorizedV2)):
                        raise ValueError('Native query Plan requires its own writer inclusion')
                if set(grants) != {e.authorization_event_id for e in observations.values()}:
                    raise ValueError('Native writer requires every selected read grant to be settled')
                # The shared root closes one inclusion set across every native
                # family; immutable Plan codecs retain their original lists.
                families = [] if shared_writer else [(NativePlanStatementReadObservedV1, event.native_statement_read_event_ids)]
                if not shared_writer and isinstance(query, NativePlanQueryV2):
                    families.append((NativePlanAssertionReadObservedV1, event.native_assertion_read_event_ids))
                for observed_type, included in families:
                    if (len(included) != len(set(included))
                            or set(included) != {e.event_id for e in observations.values() if isinstance(e, observed_type)}):
                        raise ValueError('Native writer changed selected support exposure')
                writer = True
            provider, outcome, selection = event.provider_attempt_id, None, None
        elif isinstance(event, t.ProviderOutcomeEventV1) and event.provider_attempt_id == provider:
            outcome = event.outcome
        elif isinstance(event, t.PlanJevRetrievalSelectionV1):
            selection = event
            if isinstance(query, NativeGraphQueryV4):
                pending_object_reads = {(family, identity) for family in (False, True)
                    for identity in object_record_ids(query, event.selected_handles, assertion=family,
                        attempted=(i for f, i in attempted if f == family))}
        elif isinstance(event, (NativePlanStatementReadAuthorizedV1, NativePlanAssertionReadAuthorizedV1)):
            assertion = isinstance(event, NativePlanAssertionReadAuthorizedV1)
            ids = event.assertion_ids if assertion else event.statement_ids
            matches = assertions if assertion else statements
            handle = assertion_handle if assertion else selection_handle
            if isinstance(query, NativeGraphQueryV4) and selection is not None:
                expected_ids = object_record_ids(query, selection.selected_handles,
                    assertion=assertion, attempted=(i for family, i in attempted if family == assertion))
                selected_closure = set(ids) == set(expected_ids)
            else:
                selected_closure = (selection is not None and
                    {handle(query, matches[i]) for i in ids if i in matches} <= set(selection.selected_handles))
            keys = {(assertion, identity) for identity in ids}
            if (writer or outcome != 'response_received' or selection is None
                    or selection.operation != 'select_candidates' or event.provider_attempt_id != provider
                    or not isinstance(query, NativePlanQueryV1) or event.query_sha256 != query.sha256
                    or not set(ids) <= set(matches) or attempted & keys
                    or not selected_closure):
                raise ValueError('Native selected read lacks its exact current controller/query grant')
            grants[event.event_id] = event
            attempted.update(keys)
            pending_object_reads.difference_update(keys)
        elif isinstance(event, (NativePlanStatementReadObservedV1, NativePlanAssertionReadObservedV1)):
            grant = grants.get(event.authorization_event_id)
            assertion = isinstance(event, NativePlanAssertionReadObservedV1)
            expected = NativePlanAssertionReadAuthorizedV1 if assertion else NativePlanStatementReadAuthorizedV1
            ids = {r.assertion.assertion_id for r in event.reads} if assertion else {r.support.statement_id for r in event.reads}
            unavailable = event.unavailable_assertion_ids if assertion else event.unavailable_statement_ids
            granted = set(grant.assertion_ids if assertion else grant.statement_ids) if isinstance(grant, expected) else None
            if (writer or granted is None or grant.provider_attempt_id != provider or outcome != 'response_received'
                    or any(e.authorization_event_id == grant.event_id for e in observations.values())
                    or granted != ids | set(unavailable)):
                raise ValueError('Native read observation differs from selected grant')
            validate_record_reads(query.authority, event.reads,
                assertions if assertion else statements, assertion=assertion)
            observations[event.event_id] = event



def _record_judgment(check, q, events):
    try:
        check(q, SimpleNamespace(events=events))
    except (ValueError, TypeError, KeyError, AttributeError) as exc:
        return type(exc).__name__, str(exc)
    return 'PASS', None


def _settled_record_case(*, historical=False, statement=False):
    from application_state.agent_conversation.native_plan_assertions import (
        NativePlanQueryV2, NativePlanAssertionReadObservedV1,
        selection_handle as assertion_handle,
    )
    q = query()
    if statement:
        match = NativePlanStatementMatchV1(statement_id='ent:statement',
            discovered_entity_ids=(q.discovered_entity_ids[0],), discovery_assertion_ids=('asrt:discovery',),
            campaign_id='campaign', logical_source={'object_id': 'recap'}, episode='1', label='Statement')
        raw = q.model_dump(by_alias=True)
        for field in ('object_matches', 'authored_targets', 'assertion_matches'):
            raw.pop(field)
        raw.update(schema='dmb_native_plan_query_v1', matches=(match,))
        q = NativePlanQueryV1.model_validate(raw)
        ids, handles = (match.statement_id,), (selection_handle(q, match),)
    elif historical:
        raw = q.model_dump(by_alias=True)
        raw.pop('object_matches')
        raw.pop('authored_targets')
        raw['schema'] = 'dmb_native_plan_query_v2'
        q = NativePlanQueryV2.model_validate(raw)
        ids = (q.assertion_matches[0].assertion_id,)
        handles = (assertion_handle(q, q.assertion_matches[0]),)
    else:
        handles = (object_selection_handle(q, q.discovered_entity_ids[0]),)
        ids = object_record_ids(q, handles, assertion=True)
    ledger = execution(q, ids, handles=handles)
    if statement:
        ledger.events[-1] = NativePlanStatementReadAuthorizedV1(
            event_id=uuid4(), sequence=3, provider_attempt_id=ledger.events[0].provider_attempt_id,
            query_sha256=q.sha256, statement_ids=ids)
        observation = NativePlanStatementReadObservedV1(event_id=uuid4(), sequence=4,
            authorization_event_id=ledger.events[-1].event_id, reads=(),
            unavailable_statement_ids=ids, status='partial')
    else:
        observation = NativePlanAssertionReadObservedV1(event_id=uuid4(), sequence=4,
            authorization_event_id=ledger.events[-1].event_id, reads=(),
            unavailable_assertion_ids=ids, status='partial')
    ledger.events.append(observation)
    return q, ledger


@pytest.mark.parametrize('version', ['object', 'historical', 'statement'])
def test_record_recovery_and_every_grouping_match_original_on_valid_partial_prefixes(version):
    from copy import deepcopy
    from application_state.agent_conversation.native_record_execution import _RecordState, _advance, validate
    q, ledger = _settled_record_case(historical=version == 'historical', statement=version == 'statement')
    original_query, original_events = q.model_dump_json(), deepcopy(ledger.events)
    for size in range(len(ledger.events) + 1):
        events = ledger.events[:size]
        assert _record_judgment(validate, q, events) == _record_judgment(_original_record_predicate, q, events) == ('PASS', None)
        expected = _advance(_RecordState(), q, events)
        for mask in range(1 << max(0, size - 1)):
            state, start = _RecordState(), 0
            for end in range(1, size + 1):
                if end == size or mask & (1 << (end - 1)):
                    state = _advance(state, q, events[start:end])
                    start = end
            assert state == expected
    assert q.model_dump_json() == original_query and ledger.events == original_events


@pytest.mark.parametrize('change', ['provider', 'query', 'ids', 'operation', 'handles',
    'outcome', 'grant_family', 'observation_family', 'observation_grant', 'missing_unavailable',
    'double_observation', 'pending_provider', 'duplicate_attempt', 'legacy_inclusion'])
def test_record_negative_cases_match_original_without_dropping_other_owner_checks(change):
    from application_state.agent_conversation.native_record_execution import validate
    q, ledger = _settled_record_case()
    if change == 'provider':
        ledger.events[3] = ledger.events[3].model_copy(update={'provider_attempt_id': uuid4()})
    elif change == 'query':
        ledger.events[3] = ledger.events[3].model_copy(update={'query_sha256': 'f'*64})
    elif change == 'ids':
        ledger.events[3] = ledger.events[3].model_copy(update={'assertion_ids': ('asrt:foreign',)})
    elif change == 'operation':
        ledger.events[2] = ledger.events[2].model_copy(update={'operation': 'finish_retrieval'})
    elif change == 'handles':
        ledger.events[2] = ledger.events[2].model_copy(update={'selected_handles': ('native-object:foreign',)})
    elif change == 'outcome':
        ledger.events[1] = ledger.events[1].model_copy(update={'outcome': None})
    elif change == 'grant_family':
        ledger.events[3] = NativePlanStatementReadAuthorizedV1(event_id=ledger.events[3].event_id,
            sequence=3, provider_attempt_id=ledger.events[0].provider_attempt_id,
            query_sha256=q.sha256, statement_ids=('ent:foreign',))
    elif change == 'observation_family':
        ledger.events[4] = NativePlanStatementReadObservedV1(event_id=uuid4(), sequence=4,
            authorization_event_id=ledger.events[3].event_id, reads=(),
            unavailable_statement_ids=ledger.events[3].assertion_ids, status='partial')
    elif change == 'observation_grant':
        ledger.events[4] = ledger.events[4].model_copy(update={'authorization_event_id': uuid4()})
    elif change == 'missing_unavailable':
        ledger.events[4] = ledger.events[4].model_copy(update={'unavailable_assertion_ids': ()})
    elif change == 'double_observation':
        ledger.events.append(ledger.events[4].model_copy(update={'event_id': uuid4()}))
    elif change == 'pending_provider':
        ledger.events.pop()
        ledger.events.append(t.ProviderAttemptAuthorizedEventV1.model_construct(
            kind='provider_attempt_authorized_v1', provider_attempt_id=uuid4()))
    elif change == 'duplicate_attempt':
        ledger.events.append(ledger.events[3].model_copy(update={'event_id': uuid4()}))
    elif change == 'legacy_inclusion':
        ledger.events.append(t.PlanNativeWriterAuthorizedV2.model_construct(
            kind='plan_native_writer_authorized_v2', provider_attempt_id=uuid4(),
            native_statement_read_event_ids=[], native_assertion_read_event_ids=[]))
    assert _record_judgment(validate, q, ledger.events) == _record_judgment(_original_record_predicate, q, ledger.events)
    assert _record_judgment(validate, q, ledger.events)[0] == 'ValueError'


def test_record_state_is_disjoint_from_grant_selection_and_observed_models():
    from dataclasses import FrozenInstanceError
    from application_state.agent_conversation.native_record_execution import _RecordState, _advance
    q, ledger = _settled_record_case()
    state = _advance(_RecordState(), q, ledger.events)
    assert state.grants[0].ids == ledger.events[3].assertion_ids
    assert state.observations[0].event_id == ledger.events[4].event_id
    ledger.events[2].__dict__['selected_handles'] = ['foreign']
    ledger.events[3].__dict__['assertion_ids'] = ('foreign',)
    ledger.events[4].__dict__['unavailable_assertion_ids'] = ()
    assert state.grants[0].ids != ledger.events[3].assertion_ids
    assert state.selection.selected_handles != tuple(ledger.events[2].selected_handles)
    with pytest.raises(FrozenInstanceError):
        state.writer = True


def test_unavailable_query_source_only_events_do_not_require_a_record_catalog():
    from application_state.agent_conversation.native_plan_statements import NativePlanQueryUnavailableV1
    from application_state.agent_conversation.native_record_execution import validate
    q = NativePlanQueryUnavailableV1(managed_world_id='test', reason='native_graph_head_unavailable')
    events = [t.ProviderAttemptAuthorizedEventV1.model_construct(
        kind='provider_attempt_authorized_v1', provider_attempt_id=uuid4()),
        t.PlanJevRetrievalSelectionV1.model_construct(operation='select_candidates',
            selected_handles=('native-full-document:source',))]
    assert _record_judgment(validate, q, events) == _record_judgment(_original_record_predicate, q, events) == ('PASS', None)


def test_seeded_partial_record_histories_match_original_predicate():
    import random
    from application_state.agent_conversation.native_record_execution import validate
    rng = random.Random(20261110)
    for _ in range(300):
        q, ledger = _settled_record_case(historical=rng.choice([False, True]))
        ledger.events = ledger.events[:rng.randrange(6)]
        if ledger.events:
            index = rng.randrange(len(ledger.events))
            event = ledger.events[index]
            updates = rng.choice([{'provider_attempt_id': uuid4()}, {'event_id': uuid4()},
                {'outcome': None}, {'authorization_event_id': uuid4()}, {'query_sha256': 'd'*64},
                {'operation': 'finish_retrieval'}, {'selected_handles': ('native-object:foreign',)}])
            if all(hasattr(event, name) for name in updates):
                ledger.events[index] = event.model_copy(update=updates)
        assert _record_judgment(validate, q, ledger.events) == _record_judgment(_original_record_predicate, q, ledger.events)


@pytest.mark.parametrize('handles', [None, 42, True, 3.5, [['nested']], {'key': 'value'}])
def test_legacy_malformed_json_handles_remain_lazy_until_a_read_uses_them(handles):
    from application_state.agent_conversation.native_record_execution import validate
    q, ledger = _settled_record_case(historical=True)
    ledger.events[2] = ledger.events[2].model_copy(update={"selected_handles": handles})
    assert _record_judgment(validate, q, ledger.events[:3]) == _record_judgment(
        _original_record_predicate, q, ledger.events[:3]) == ("PASS", None)
    assert _record_judgment(validate, q, ledger.events[:4]) == _record_judgment(
        _original_record_predicate, q, ledger.events[:4])
    assert _record_judgment(validate, q, ledger.events[:4])[0] != "PASS"


def test_malformed_json_operation_and_outcome_are_semantic_flags_not_mutable_aliases():
    from application_state.agent_conversation.native_record_execution import _RecordState, _advance
    q, ledger = _settled_record_case(historical=True)
    operation, outcome = [], []
    ledger.events[1] = ledger.events[1].model_copy(update={"outcome": outcome})
    ledger.events[2] = ledger.events[2].model_copy(update={"operation": operation})
    prefix = ledger.events[:3]
    assert _record_judgment(validate_selected_record_events, q, prefix) == _record_judgment(
        _original_record_predicate, q, prefix) == ("PASS", None)
    state = _advance(_RecordState(), q, prefix)
    assert state.response_received is False and state.selection.select_candidates is False
    operation.append("changed")
    outcome.append("changed")
    assert state.response_received is False and state.selection.select_candidates is False
