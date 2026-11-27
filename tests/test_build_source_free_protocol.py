"""Pending Build boundaries: fake App, in-memory Core and mock provider transports."""
import json
from contextlib import contextmanager
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError

from application_state.agent_conversation import types as t
from application_state.agent_conversation import repository
from application_state.errors import ApplicationStateIntegrityError
from tests.test_build_source_free_routing import (
    pending_execution_pair, pending_execution, seal_pending_receipt,
)
from tests.test_surface_native_context import provenance_for
from tests.test_surface_native_turn_records import retained, stored_row, submission


def pending_submission(*, with_source=False, lore_page=False):
    receipt, policy = pending_execution_pair(with_source=with_source)
    if lore_page:
        from dataclasses import replace
        from application_state.agent_conversation.native_execution import BuildPendingExecutionPolicyV1
        action = policy.action.model_copy(update={
            'intent': policy.action.intent.model_copy(update={
                'message': 'Create a new page titled "Maelthor" from the context we just discussed. Do not search again.'}),
            'capabilities': replace(policy.action.capabilities, reviews=('lore_page',))})
        policy = BuildPendingExecutionPolicyV1.model_validate(policy.model_copy(update={'action': action}))
    intent = policy.action.intent
    provenance = provenance_for(receipt.work_context).model_copy(
        update={'surface_instance_id': intent.surface_instance_id})
    data = receipt.model_dump(mode='json', by_alias=True)
    data.pop('context_receipt_sha256')
    receipt = seal_pending_receipt(data | {'provenance_sha256': t.canonical_sha256(provenance)})
    execution = pending_execution(receipt, policy)
    return t.TurnSubmission(world_id=intent.world_id, conversation_id=receipt.conversation_observation.conversation_id,
        idempotency_key=uuid4(), expected_conversation_revision=1,
        user_text=intent.message, provenance=provenance, submitted_intent_v2=intent,
        graph_context_receipt=receipt, graph_context_execution=execution)


def test_pending_submission_and_actual_stored_row_roundtrip_without_core():
    sub = pending_submission()
    assert t.TurnSubmission.model_validate_json(sub.model_dump_json(by_alias=True)) == sub
    turn = retained(sub)
    row, references = stored_row(turn)
    restored = repository._turn_from_row(None, row, references=references)
    assert restored == turn
    assert restored.graph_context_receipt.source_observation.binding is None
    assert not hasattr(restored.graph_context_receipt, 'source_authority')
    assert restored.graph_context_execution.schema_ == 'dmb_build_pending_execution_v1'


@pytest.mark.parametrize('side', ['receipt', 'execution'])
def test_stored_pending_and_legacy_components_cannot_be_crossed(side):
    pending = retained(pending_submission())
    legacy = retained(submission('build'))
    row, references = stored_row(pending)
    old_row, _ = stored_row(legacy)
    key = 'graph_context_' + side
    row[key] = old_row[key]
    with pytest.raises((ApplicationStateIntegrityError, ValidationError, ValueError)):
        repository._turn_from_row(None, row, references=references)


def test_pending_typed_turn_reconstruction_cannot_retain_a_mutated_observation():
    turn = retained(pending_submission())
    observed = turn.graph_context_receipt.source_observation.model_copy(
        update={'requested_revision_id': 'different-request'})
    receipt = turn.graph_context_receipt.model_copy(update={'source_observation': observed})
    with pytest.raises(ValidationError):
        t.Turn.model_validate(turn.model_copy(update={'graph_context_receipt': receipt}))


@pytest.mark.parametrize('field,value', [
    ('user_text', 'Changed request'), ('world_id', 'other-world'),
    ('submitted_intent_fingerprint_v2', 'f' * 64),
])
def test_stored_pending_request_identity_cannot_be_substituted(field, value):
    turn = retained(pending_submission())
    data = turn.model_dump(mode='json', by_alias=True) | {field: value}
    with pytest.raises(ValidationError):
        t.Turn.model_validate_json(json.dumps(data))


def test_pending_prefix_does_not_admit_unowned_terminal_prose():
    turn = retained(pending_submission())
    data = turn.model_dump(mode='json', by_alias=True) | {'assistant_text': 'Unowned answer'}
    with pytest.raises(ValidationError, match='registered terminal output owner'):
        t.Turn.model_validate_json(json.dumps(data))


@pytest.mark.parametrize('field,value', [
    ('assembled_input_sha256', 'f' * 64), ('provider_envelope_input_tokens', 121),
])
def test_pending_first_controller_cannot_replace_its_resealed_initial_envelope(field, value):
    from tests.test_build_source_free_routing import pending_work_prefix
    from application_state.agent_conversation.build_source_free import effective_pending_source
    receipt, policy = pending_execution_pair()
    data = receipt.model_dump(mode='json', by_alias=True)
    data.pop('context_receipt_sha256')
    data['assembled_input'][field] = value
    receipt = seal_pending_receipt(data)
    execution = pending_execution(receipt, policy, pending_work_prefix(policy, scope='anchored'))
    with pytest.raises(ValueError, match='first provider authorization must match'):
        effective_pending_source(receipt, execution)


def test_repository_pending_wire_decode_has_one_component_freshness_owner(monkeypatch):
    from application_state.agent_conversation.native_context import BuildPendingContextReceiptV1
    from application_state.agent_conversation.native_execution import BuildPendingExecutionV1
    turn = retained(pending_submission())
    row, references = stored_row(turn)
    def duplicate_decode(*args, **kwargs):
        raise AssertionError('Stored pending component was independently decoded again')
    monkeypatch.setattr(BuildPendingContextReceiptV1, 'model_validate_json', duplicate_decode)
    monkeypatch.setattr(BuildPendingExecutionV1, 'model_validate_json', duplicate_decode)
    restored = repository._turn_from_row(None, row, references=references)
    assert restored.model_dump_json(by_alias=True) == turn.model_dump_json(by_alias=True)


@pytest.mark.parametrize('status,attempt', [('accepted', 0), ('running', 1)])
def test_stored_pending_live_turn_cannot_carry_a_completion_timestamp(status, attempt):
    turn = retained(pending_submission(), status=status, attempt=attempt)
    row, references = stored_row(turn)
    assert repository._turn_from_row(None, row, references=references) == turn
    data = turn.model_dump(mode='json', by_alias=True)
    data['completed_at'] = data['accepted_at']
    with pytest.raises(ValidationError, match='lifecycle'):
        t.Turn.model_validate_json(json.dumps(data))
    row['completed_at'] = turn.accepted_at
    with pytest.raises((ApplicationStateIntegrityError, ValidationError, ValueError)):
        repository._turn_from_row(None, row, references=references)


def test_pending_conversation_observation_is_the_existing_pointer_not_a_new_owner():
    from application_state.agent_conversation.build_source_free import (
        capture_pending_conversation, validate_pending_conversation_pointer)
    receipt, _ = pending_execution_pair()
    observed = receipt.conversation_observation
    pointer = t.WorldPointer(world_id=receipt.source_observation.managed_world_id,
        active_conversation_id=observed.conversation_id, revision=observed.pointer_revision)
    assert capture_pending_conversation(pointer, world_id=pointer.world_id,
        conversation_id=observed.conversation_id) == observed
    assert validate_pending_conversation_pointer(receipt, pointer) is None
    # Reset -> reopen the same conversation retains the ID but changes revision.
    moved = pointer.model_copy(update={'revision': pointer.revision + 2})
    original = receipt.model_dump_json(by_alias=True)
    with pytest.raises(ValueError, match='pointer changed'):
        validate_pending_conversation_pointer(receipt, moved)
    assert receipt.model_dump_json(by_alias=True) == original


@pytest.mark.parametrize('change', [{'world_id': 'foreign-world'}, {'active_conversation_id': uuid4()},
                                   {'active_conversation_id': None}])
def test_pending_pointer_cannot_borrow_another_world_or_chat(change):
    from application_state.agent_conversation.build_source_free import validate_pending_conversation_pointer
    receipt, _ = pending_execution_pair()
    pointer = t.WorldPointer(world_id=receipt.source_observation.managed_world_id,
        active_conversation_id=receipt.conversation_observation.conversation_id, revision=0)
    with pytest.raises(ValueError, match='active World conversation'):
        validate_pending_conversation_pointer(receipt, pointer.model_copy(update=change))


def test_pending_submission_and_stored_turn_cannot_change_the_captured_chat():
    sub = pending_submission()
    values = sub.model_dump(mode='json', by_alias=True) | {'conversation_id': str(uuid4())}
    with pytest.raises(ValidationError, match='unchanged Build request'):
        t.TurnSubmission.model_validate_json(json.dumps(values))
    turn = retained(sub)
    values = turn.model_dump(mode='json', by_alias=True) | {'conversation_id': str(uuid4())}
    with pytest.raises(ValidationError, match='admitted request'):
        t.Turn.model_validate_json(json.dumps(values))


def test_pending_draft_cannot_replace_a_resealed_captured_pointer():
    from tests.test_surface_native_build_work import case
    from application_state.agent_conversation.build_source_free import effective_pending_source
    captured = case()
    # Use the actual matching captured record from the original immutable request.
    original, policy = pending_execution_pair(captured_case=captured)
    data = original.model_dump(mode='json', by_alias=True)
    data.pop('context_receipt_sha256')
    data['conversation_observation']['pointer_revision'] += 1
    changed = seal_pending_receipt(data)
    execution = pending_execution(changed, policy, captured[1].events[:5])
    with pytest.raises(ValueError, match='captured conversation pointer'):
        effective_pending_source(changed, execution)


def settlement_harness(monkeypatch, *, with_source=True, scope='source_lookup', lore_page=False):
    """Real service decisions, fake transaction/row owners; not SQL qualification."""
    from contextlib import contextmanager
    from datetime import UTC, datetime, timedelta
    from types import SimpleNamespace
    from application_state.agent_conversation import service as service_module
    from tests.test_surface_native_execution import BUILD_TURN_ID
    from tests.test_build_source_free_routing import pending_work_prefix, settled_source, prepared_query
    sub = pending_submission(with_source=with_source, lore_page=lore_page)
    events = pending_work_prefix(sub.graph_context_execution.policy, scope=scope)
    if lore_page:
        from tests.test_surface_native_execution import build_resolution
        from application_state.agent_conversation.build_intentional_response import resolution_for
        work = build_resolution(sub.graph_context_execution.policy, events[0], 3,
            requested='review_lore_page_from_conversation')
        events[-1] = work.model_copy(update={'resolution': resolution_for(
            sub.graph_context_execution.policy, work.requested_work, source_scope=scope)})
    execution = pending_execution(sub.graph_context_receipt, sub.graph_context_execution.policy, events)
    now = datetime.now(UTC)
    turn = retained(sub, turn_id=BUILD_TURN_ID, status='running', attempt=1, revision=2,
        claim_expires_at=now + timedelta(minutes=2), graph_context_execution=execution)
    observed = turn.graph_context_receipt.conversation_observation
    state = SimpleNamespace(turn=turn, now=now, depth=0, locks=[], access_calls=0,
        materialized=0, persisted=0, denied=False, on_prepare=None, access_delay=False,
        foreign_source=False, cas_failure=False, access_delay_before=False,
        pointer=t.WorldPointer(world_id=turn.world_id, active_conversation_id=turn.conversation_id,
                               revision=observed.pointer_revision))
    conn = SimpleNamespace()
    state.conn = conn
    state.successor = False
    def leaf_query(sql, args):
        assert state.depth == 1
        assert sql == 'SELECT 1 FROM agent.turn_retry WHERE predecessor_id=%s' and args == (state.turn.turn_id,)
        return SimpleNamespace(fetchone=lambda: (1,) if state.successor else None)
    conn.execute = leaf_query
    state.leaf_query = leaf_query
    class RulesCursor:
        def __enter__(self): return self
        def __exit__(self, *args): return False
        def execute(self, sql, args):
            assert state.depth == 1 and 'FROM agent.turn_rules_execution WHERE' in sql
            assert args == (state.turn.turn_id, state.turn.attempt)
        def fetchone(self):
            payload = getattr(state, 'rules_payload', None)
            return None if payload is None else {'revision': getattr(state, 'rules_revision', 1), 'payload': payload}
    conn.cursor = lambda **kwargs: RulesCursor()
    @contextmanager
    def uow(*args, **kwargs):
        assert state.depth == 0
        state.depth += 1
        try:
            yield conn
        finally:
            state.depth -= 1
    state.uow = uow
    monkeypatch.setattr(service_module, 'unit_of_work', uow)
    monkeypatch.setattr(service_module, '_ready_dsn', lambda: 'synthetic-no-database')
    def world_lock(_conn, world):
        assert _conn is conn and state.depth == 1 and world == turn.world_id
        state.locks.append('world')
        return state.pointer
    def conversation_lock(_conn, world, conversation_id):
        assert _conn is conn and state.depth == 1 and conversation_id == state.turn.conversation_id
        state.locks.append('conversation')
        return t.Conversation(world_id=world, conversation_id=conversation_id, status='active',
            revision=2, next_turn_sequence=2, created_at=now, updated_at=now, archived_at=None)
    def turn_lock(_conn, world, turn_id):
        assert _conn is conn and state.depth == 1 and turn_id == turn.turn_id
        state.locks.append('turn')
        return state.turn
    monkeypatch.setattr(service_module.repo, 'lock_world_state', world_lock)
    monkeypatch.setattr(service_module.repo, 'lock_conversation', conversation_lock)
    monkeypatch.setattr(service_module.repo, 'database_clock', lambda _conn: state.now)
    service = service_module.AgentConversationService()
    monkeypatch.setattr(service, '_lock_execution_append_turn', turn_lock)
    def authorize(_conn, current, prepared):
        assert _conn is conn and state.depth == 1 and current.turn_id == turn.turn_id
        state.access_calls += 1
        if prepared is None and state.access_delay_before:
            state.now += timedelta(hours=1)
        if prepared is not None and state.access_delay:
            state.now += timedelta(hours=1)
        return not state.denied
    def materialize(current):
        assert state.depth == 0  # no App locks across external source IO
        state.materialized += 1
        if state.on_prepare:
            state.on_prepare()
        authority = settled_source(managed_world_id=current.world_id,
            **({'native_world_id': 'foreign-native'} if state.foreign_source else {}))
        query = prepared_query(authority).model_copy(update={'question': current.user_text})
        return authority, query
    def persist(_conn, *, world_id, turn_id, expected_revision, execution):
        assert _conn is conn and state.depth == 1
        if state.cas_failure:
            return None
        assert state.turn.revision == expected_revision
        state.persisted += 1
        state.turn = t.Turn.model_validate(state.turn.model_copy(update={
            'revision': expected_revision + 1, 'graph_context_execution': execution}))
        return state.turn
    monkeypatch.setattr(service, '_persist_execution_append', persist)
    state.service, state.authorize = service, authorize
    event_id = uuid4()
    def run(*, revision=2, event=event_id, attempt=1):
        return service.settle_pending_build_source(turn.world_id, turn.conversation_id, turn.turn_id,
            expected_revision=revision, expected_attempt=attempt, event_id=event,
            materialize_source=materialize, authorize_current_access=authorize)
    return state, run


def test_service_pending_settlement_rechecks_and_admits_once_without_holding_app_locks(monkeypatch):
    state, run = settlement_harness(monkeypatch)
    updated, changed = run()
    assert changed and updated.revision == 3
    assert state.locks == ['world', 'conversation', 'turn'] * 2
    assert state.access_calls == 2 and state.materialized == state.persisted == 1 and state.depth == 0
    replay, changed = run()
    assert not changed and replay == updated
    assert state.materialized == state.persisted == 1


@pytest.mark.parametrize('failure', ['pointer_before', 'claim_before', 'access_before', 'access_delay_before',
    'pointer_after', 'claim_after', 'expiry_after', 'access_after', 'access_delay', 'foreign_source', 'cas_failure'])
def test_service_pending_settlement_discards_changed_scope_claim_or_access(monkeypatch, failure):
    from datetime import timedelta
    from application_state.errors import ApplicationStateConflictError, ApplicationStateValidationError
    state, run = settlement_harness(monkeypatch)
    def changed():
        if failure.startswith('pointer'):
            state.pointer = state.pointer.model_copy(update={'revision': state.pointer.revision + 2})
        if failure.startswith('claim'):
            state.turn = state.turn.model_copy(update={'revision': state.turn.revision + 1})
        if failure.startswith('access_'):
            state.denied = True
        if failure == 'expiry_after':
            state.now += timedelta(hours=1)
    if failure == 'access_delay_before':
        state.access_delay_before = True
    elif failure.endswith('_before'):
        changed()
    elif failure in {'pointer_after', 'claim_after', 'expiry_after', 'access_after'}:
        state.on_prepare = changed
    else:
        setattr(state, failure, True)
    with pytest.raises((ApplicationStateConflictError, ApplicationStateValidationError)):
        run()
    assert state.persisted == 0 and state.depth == 0
    assert state.materialized == (0 if failure.endswith('_before') else 1)


@pytest.mark.parametrize('scope,with_source', [('anchored', True), ('source_lookup', False)])
def test_service_pending_settlement_never_prepares_for_anchored_or_unobserved_scope(monkeypatch, scope, with_source):
    from application_state.errors import ApplicationStateConflictError, ApplicationStateValidationError
    state, run = settlement_harness(monkeypatch, with_source=with_source, scope=scope)
    with pytest.raises((ApplicationStateConflictError, ApplicationStateValidationError)):
        run()
    assert state.materialized == state.persisted == 0 and state.depth == 0


def test_service_pending_settlement_cannot_replace_an_admitted_source(monkeypatch):
    from application_state.errors import ApplicationStateConflictError
    state, run = settlement_harness(monkeypatch)
    updated, _ = run()
    with pytest.raises(ApplicationStateConflictError, match='already settled'):
        run(revision=updated.revision, event=uuid4())
    assert state.materialized == state.persisted == 1


def test_service_pending_settlement_does_not_coerce_a_boolean_claim_attempt(monkeypatch):
    from application_state.errors import ApplicationStateValidationError
    state, run = settlement_harness(monkeypatch)
    with pytest.raises(ApplicationStateValidationError):
        run(attempt=True)
    assert state.locks == [] and state.materialized == state.persisted == 0


def test_new_pending_admission_refuses_reset_then_reopen_before_mutation(monkeypatch):
    from contextlib import contextmanager
    from application_state.agent_conversation import service as service_module
    from application_state.agent_conversation import work_plan
    from application_state.errors import ApplicationStateConflictError
    sub = pending_submission()
    captured = sub.graph_context_receipt.conversation_observation
    @contextmanager
    def uow(*args, **kwargs):
        yield object()
    monkeypatch.setattr(service_module, 'unit_of_work', uow)
    monkeypatch.setattr(service_module, 'assert_connection_at_head', lambda conn: None)
    monkeypatch.setattr(work_plan, 'validate_bound_intent', lambda *args: None)
    monkeypatch.setattr(service_module.repo, 'get_turn_by_world_key', lambda *args: None)
    monkeypatch.setattr(service_module, '_lock_pointer', lambda conn, world: t.WorldPointer(
        world_id=world, active_conversation_id=sub.conversation_id, revision=captured.pointer_revision + 2))
    def mutation(*args, **kwargs):
        raise AssertionError('Stale pending admission reached a conversation/Turn mutation')
    monkeypatch.setattr(service_module.repo, 'advance_conversation_for_turn', mutation)
    monkeypatch.setattr(service_module.repo, 'insert_turn', mutation)
    with pytest.raises(ApplicationStateConflictError, match='pointer changed'):
        service_module.AgentConversationService().accept_turn(sub)


def test_existing_pending_receipt_replay_does_not_refresh_its_captured_pointer(monkeypatch):
    from contextlib import contextmanager
    from application_state.agent_conversation import service as service_module
    from application_state.agent_conversation import work_plan
    sub = pending_submission()
    turn = retained(sub)
    @contextmanager
    def uow(*args, **kwargs):
        yield object()
    monkeypatch.setattr(service_module, 'unit_of_work', uow)
    monkeypatch.setattr(service_module, 'assert_connection_at_head', lambda conn: None)
    monkeypatch.setattr(work_plan, 'validate_bound_intent', lambda *args: None)
    monkeypatch.setattr(service_module.repo, 'get_turn_by_world_key', lambda *args: (
        turn, 'retained-request', 'retained-idempotency', None, turn.submitted_intent_fingerprint_v2))
    def refresh(*args, **kwargs):
        raise AssertionError('Replay attempted to replace the captured pointer')
    monkeypatch.setattr(service_module, '_lock_pointer', refresh)
    assert service_module.AgentConversationService().accept_turn(sub) == turn


def test_pending_settlement_replay_cannot_borrow_another_admission_revision(monkeypatch):
    from application_state.errors import ApplicationStateConflictError
    state, run = settlement_harness(monkeypatch)
    updated, _ = run()
    with pytest.raises(ApplicationStateConflictError, match='already settled'):
        run(revision=updated.revision)
    assert state.materialized == state.persisted == 1


@pytest.mark.parametrize('change', ['pointer', 'attempt', 'access', 'expiry'])
def test_pending_settlement_lost_response_replay_keeps_live_access_and_claim_fences(monkeypatch, change):
    from datetime import timedelta
    from application_state.errors import ApplicationStateConflictError
    state, run = settlement_harness(monkeypatch)
    run()
    if change == 'pointer':
        state.pointer = state.pointer.model_copy(update={'revision': state.pointer.revision + 2})
    elif change == 'attempt':
        state.turn = state.turn.model_copy(update={'attempt': state.turn.attempt + 1})
    elif change == 'access':
        state.denied = True
    else:
        state.now += timedelta(hours=1)
    with pytest.raises(ApplicationStateConflictError):
        run()
    assert state.materialized == state.persisted == 1


def pending_catalog_case(*, scope='source_lookup', pages=None, with_source=False):
    from application_state.agent_conversation.build_source_free import BuildAppPageCatalogObservedV1
    from application_state.agent_conversation.build_related_pages import PagePointer
    from tests.test_build_source_free_routing import pending_work_prefix
    receipt, policy = pending_execution_pair(with_source=with_source)  # App lookup needs no Core binding
    primary_id = str(uuid4())
    data = receipt.model_dump(mode='json', by_alias=True)
    data.pop('context_receipt_sha256')
    data['work_context']['source_basis']['document_id'] = primary_id
    receipt = seal_pending_receipt(data)
    intent = policy.action.intent
    intent = intent.model_copy(update={'primary_work': intent.primary_work.model_copy(update={'object_id': primary_id})})
    policy = policy.model_copy(update={'action': policy.action.model_copy(update={'intent': intent})})
    events = pending_work_prefix(policy, scope=scope)
    pages = pages if pages is not None else [PagePointer(world_id=policy.action.intent.world_id,
        document_id=uuid4(), registry_revision=1, title='Maelthor', visibility='internal')]
    catalog = BuildAppPageCatalogObservedV1(event_id=uuid4(), sequence=len(events),
        admitted_from_revision=2, pending_context_receipt_sha256=receipt.context_receipt_sha256,
        work_event_id=events[-1].event_id, pages=tuple(pages))
    return receipt, policy, events, catalog


def test_pending_app_catalog_without_core_is_navigation_not_source_authority():
    from application_state.agent_conversation.build_source_free import effective_pending_app_catalog, effective_pending_source
    receipt, policy, events, catalog = pending_catalog_case()
    assert receipt.source_observation.binding is None
    before = pending_execution(receipt, policy, events)
    assert effective_pending_app_catalog(receipt, before) is None
    execution = pending_execution(receipt, policy, [*events, catalog])
    assert effective_pending_app_catalog(receipt, execution) == catalog.pages
    assert effective_pending_source(receipt, execution) is None
    assert execution.policy.action.related_page_catalog is None
    assert 'markdown' not in type(catalog.pages[0]).model_fields
    empty = catalog.model_copy(update={'pages': ()})
    assert effective_pending_app_catalog(receipt, pending_execution(receipt, policy, [*events, empty])) == ()


@pytest.mark.parametrize('change', ['world', 'current_page', 'receipt', 'work', 'twice', 'before_work'])
def test_pending_app_catalog_cannot_cross_its_work_receipt_or_world(change):
    from application_state.agent_conversation.build_source_free import effective_pending_app_catalog
    receipt, policy, events, catalog = pending_catalog_case()
    if change in {'world', 'current_page'}:
        values = ({'world_id': 'another-world'} if change == 'world' else
                  {'document_id': UUID(receipt.work_context.source_basis.document_id)})
        catalog = catalog.model_copy(update={'pages': (catalog.pages[0].model_copy(update=values),)})
    elif change == 'receipt':
        catalog = catalog.model_copy(update={'pending_context_receipt_sha256': 'a' * 64})
    elif change == 'work':
        catalog = catalog.model_copy(update={'work_event_id': uuid4()})
    elif change == 'twice':
        events.append(catalog)
        catalog = catalog.model_copy(update={'event_id': uuid4(), 'sequence': len(events)})
    else:
        events = []
        catalog = catalog.model_copy(update={'sequence': 0})
    expected = {'world': 'foreign World or current page', 'current_page': 'foreign World or current page',
        'receipt': 'differs from its evidence-seeking work', 'work': 'differs from its evidence-seeking work',
        'twice': 'may be observed once', 'before_work': 'must be unique'}
    with pytest.raises(ValueError, match=expected[change]):
        effective_pending_app_catalog(receipt, pending_execution(receipt, policy, [*events, catalog]))


def test_pending_anchored_work_cannot_discover_an_app_catalog():
    receipt, policy, events, catalog = pending_catalog_case(scope='anchored')
    with pytest.raises(ValueError, match='does not request evidence acquisition'):
        pending_execution(receipt, policy, [*events, catalog])


def test_pending_app_catalog_rejects_duplicate_and_unsorted_pointers():
    from application_state.agent_conversation.build_source_free import BuildAppPageCatalogObservedV1
    _, _, _, catalog = pending_catalog_case()
    values = catalog.model_dump(mode='json', by_alias=True)
    with pytest.raises(ValueError, match='sorted and distinct'):
        BuildAppPageCatalogObservedV1.model_validate_json(json.dumps(values | {'pages': [values['pages'][0]] * 2}))
    pages = [values['pages'][0] | {'document_id': str(uuid4())} for _ in range(2)]
    pages.sort(key=lambda p: p['document_id'], reverse=True)
    with pytest.raises(ValueError, match='sorted and distinct'):
        BuildAppPageCatalogObservedV1.model_validate_json(json.dumps(values | {'pages': pages}))


def test_pending_app_catalog_roundtrips_through_the_actual_stored_turn_decoder():
    from application_state.agent_conversation.build_source_free import BuildAppPageCatalogObservedV1, effective_pending_app_catalog
    from application_state.agent_conversation.build_related_pages import PagePointer
    from tests.test_build_source_free_routing import pending_work_prefix
    sub = pending_submission()
    receipt, initial = sub.graph_context_receipt, sub.graph_context_execution
    events = pending_work_prefix(initial.policy)
    catalog = BuildAppPageCatalogObservedV1(event_id=uuid4(), sequence=len(events),
        admitted_from_revision=2, pending_context_receipt_sha256=receipt.context_receipt_sha256,
        work_event_id=events[-1].event_id, pages=(PagePointer(world_id=sub.world_id,
            document_id=uuid4(), registry_revision=1, title='Existing saved page', visibility='internal'),))
    execution = pending_execution(receipt, initial.policy, [*events, catalog])
    from tests.test_surface_native_execution import BUILD_TURN_ID
    turn = retained(sub, turn_id=BUILD_TURN_ID, status='running', revision=3, attempt=1, graph_context_execution=execution)
    row, references = stored_row(turn)
    restored = repository._turn_from_row(None, row, references=references)
    assert effective_pending_app_catalog(restored.graph_context_receipt, restored.graph_context_execution) == catalog.pages


def test_pending_app_catalog_can_precede_exact_native_source_settlement():
    from application_state.agent_conversation.build_source_free import effective_pending_app_catalog, effective_pending_source
    from tests.test_build_source_free_routing import pending_settlement
    receipt, policy, events, catalog = pending_catalog_case(with_source=True)
    settled = pending_settlement(receipt, policy, events[-1]).model_copy(update={'sequence': 5})
    execution = pending_execution(receipt, policy, [*events, catalog, settled])
    assert effective_pending_app_catalog(receipt, execution) == catalog.pages
    assert effective_pending_source(receipt, execution) == (settled.source_authority, settled.native_query)


def app_discovery_harness(monkeypatch, *, scope='source_lookup'):
    from application_state.agent_conversation.build_related_pages import PagePointer
    state, _ = settlement_harness(monkeypatch, with_source=False, scope=scope)
    state.discovered = 0
    state.pages = [PagePointer(world_id=state.turn.world_id, document_id=uuid4(),
        registry_revision=1, title='Saved Maelthor', visibility='internal')]
    def discover(current):
        assert state.depth == 0
        state.discovered += 1
        if state.on_prepare:
            state.on_prepare()
        return state.pages
    event_id = uuid4()
    def run(*, event=event_id, revision=2):
        return state.service.observe_pending_build_app_catalog(state.turn.world_id,
            state.turn.conversation_id, state.turn.turn_id, expected_revision=revision,
            expected_attempt=1, event_id=event, discover_pages=discover,
            authorize_current_access=state.authorize)
    return state, run


def test_service_app_catalog_without_core_discovers_outside_locks_and_replays_exact_call(monkeypatch):
    from application_state.agent_conversation.build_source_free import effective_pending_app_catalog
    state, run = app_discovery_harness(monkeypatch)
    updated, changed = run()
    assert changed and updated.revision == 3 and state.discovered == state.persisted == 1
    assert state.locks == ['world', 'conversation', 'turn'] * 2
    assert state.access_calls == 2 and state.materialized == 0 and state.depth == 0
    assert effective_pending_app_catalog(updated.graph_context_receipt, updated.graph_context_execution) == tuple(state.pages)
    replay, changed = run()
    assert replay == updated and not changed and state.discovered == state.persisted == 1


@pytest.mark.parametrize('failure', ['pointer_after', 'access_after', 'expiry_after', 'cas_failure', 'foreign_page'])
def test_service_app_catalog_rejects_changed_access_claim_scope_or_append(monkeypatch, failure):
    from datetime import timedelta
    from application_state.errors import ApplicationStateConflictError, ApplicationStateValidationError
    state, run = app_discovery_harness(monkeypatch)
    def changed():
        if failure == 'pointer_after':
            state.pointer = state.pointer.model_copy(update={'revision': state.pointer.revision + 2})
        elif failure == 'access_after':
            state.denied = True
        elif failure == 'expiry_after':
            state.now += timedelta(hours=1)
    state.on_prepare = changed
    if failure == 'cas_failure':
        state.cas_failure = True
    elif failure == 'foreign_page':
        state.pages = [state.pages[0].model_copy(update={'world_id': 'foreign-world'})]
    with pytest.raises((ApplicationStateConflictError, ApplicationStateValidationError)):
        run()
    assert state.discovered == 1 and state.persisted == 0 and state.depth == 0
    if failure == 'foreign_page':
        assert state.access_calls == 1  # never pass foreign pointers to the access owner


def test_service_anchored_work_cannot_discover_app_catalog(monkeypatch):
    from application_state.errors import ApplicationStateValidationError
    state, run = app_discovery_harness(monkeypatch, scope='anchored')
    with pytest.raises(ApplicationStateValidationError):
        run()
    assert state.discovered == state.persisted == 0


def test_service_app_catalog_cannot_reselect_after_discovery(monkeypatch):
    from application_state.errors import ApplicationStateConflictError
    state, run = app_discovery_harness(monkeypatch)
    updated, _ = run()
    with pytest.raises(ApplicationStateConflictError):
        run(revision=updated.revision, event=uuid4())
    assert state.discovered == state.persisted == 1


def pending_page_phase_case():
    from application_state.agent_conversation.native_execution import BuildAppPageSelectionAuthorizedV1
    from application_state.agent_conversation.build_related_pages import RelatedPagesSelection, RelatedPageRead, PageReference
    from tests.test_surface_native_execution import controller, outcomes
    receipt, policy, events, catalog = pending_catalog_case()
    initial = controller('build', policy, sequence=5)
    values = initial.model_dump(mode='json', by_alias=True) | {
        'kind': 'build_app_page_selection_authorized_v1', 'context_phase': 'navigate',
        'catalog_event_id': str(catalog.event_id), 'admitted_from_revision': 3}
    auth = BuildAppPageSelectionAuthorizedV1.model_validate_json(json.dumps(values))
    selected = RelatedPagesSelection(event_id=uuid4(), sequence=8,
        controller_attempt_id=auth.provider_attempt_id, controller_envelope_sha256=auth.envelope_sha256,
        controller_response_sha256='a' * 64, document_ids=[catalog.pages[0].document_id])
    markdown = 'Ethel recalled a dream. The password remains uncertain.'
    from hashlib import sha256
    page = PageReference(**catalog.pages[0].model_dump(), content_sha256=sha256(markdown.encode()).hexdigest())
    read = RelatedPageRead(event_id=uuid4(), sequence=9, read_id=uuid4(),
        selection_event_id=selected.event_id, page=page, markdown=markdown)
    return receipt, policy, [*events, catalog, auth, *outcomes(auth, 6), selected, read]


def test_pending_app_page_phase_reads_only_its_acknowledged_saved_pointer_without_core():
    from application_state.agent_conversation.build_source_free import effective_pending_app_catalog, effective_pending_source
    receipt, policy, events = pending_page_phase_case()
    execution = pending_execution(receipt, policy, events)
    assert receipt.source_observation.binding is None
    assert effective_pending_source(receipt, execution) is None
    assert effective_pending_app_catalog(receipt, execution)[0].document_id == events[-1].page.document_id
    assert type(execution).model_validate_json(execution.model_dump_json(by_alias=True)) == execution


@pytest.mark.parametrize('change', ['catalog', 'no_ack', 'selection_attempt', 'selection_envelope',
    'foreign_choice', 'read_selection', 'read_revision', 'read_world', 'read_title', 'duplicate_read'])
def test_pending_app_page_phase_cannot_borrow_catalog_choices_or_read_pointer(change):
    receipt, policy, events = pending_page_phase_case()
    if change == 'catalog':
        events[5] = events[5].model_copy(update={'catalog_event_id': uuid4()})
    elif change == 'no_ack':
        events = events[:6] + [events[8].model_copy(update={'sequence': 6})]
    elif change.startswith('selection_'):
        field = 'controller_attempt_id' if change == 'selection_attempt' else 'controller_envelope_sha256'
        events[8] = events[8].model_copy(update={field: uuid4() if field.endswith('_id') else 'b' * 64})
    elif change == 'foreign_choice':
        events[8] = events[8].model_copy(update={'document_ids': [uuid4()]})
    elif change == 'read_selection':
        events[9] = events[9].model_copy(update={'selection_event_id': uuid4()})
    elif change.startswith('read_'):
        field, value = {'read_revision': ('registry_revision', 2), 'read_world': ('world_id', 'foreign-world'),
                        'read_title': ('title', 'A new title')}[change]
        events[9] = events[9].model_copy(update={'page': events[9].page.model_copy(update={field: value})})
    else:
        events.append(events[9].model_copy(update={'event_id': uuid4(), 'read_id': uuid4(), 'sequence': 10}))
    with pytest.raises(ValueError):
        pending_execution(receipt, policy, events)


def test_pending_app_page_phase_pre_dispatch_retry_does_not_reopen_first_work():
    from tests.test_surface_native_execution import controller, outcomes
    receipt, policy, events = pending_page_phase_case()
    first = events[5]
    not_sent = t.ProviderOutcomeEventV1(kind='provider_outcome', event_id=uuid4(), sequence=6,
        provider_attempt_id=first.provider_attempt_id, outcome='known_not_sent')
    retry = first.model_copy(update={'event_id': uuid4(), 'provider_attempt_id': uuid4(), 'sequence': 7})
    selection = events[8].model_copy(update={'sequence': 10, 'controller_attempt_id': retry.provider_attempt_id})
    read = events[9].model_copy(update={'sequence': 11})
    valid = [*events[:6], not_sent, retry, *outcomes(retry, 8), selection, read]
    assert len(pending_execution(receipt, policy, valid).events) == 12
    late_first = controller('build', policy, sequence=8)
    with pytest.raises(ValueError, match='precede work selection'):
        pending_execution(receipt, policy, [*events[:6], not_sent, retry.model_copy(update={'sequence': 7}),
            t.ProviderOutcomeEventV1(kind='provider_outcome', event_id=uuid4(), sequence=8,
                provider_attempt_id=retry.provider_attempt_id, outcome='known_not_sent'),
            late_first.model_copy(update={'sequence': 9})])


def test_pending_app_page_phase_cannot_repeat_a_received_decision():
    receipt, policy, events = pending_page_phase_case()
    retry = events[5].model_copy(update={'event_id': uuid4(), 'provider_attempt_id': uuid4(), 'sequence': 8})
    with pytest.raises(ValueError, match='unique unresolved captured catalog phase'):
        pending_execution(receipt, policy, [*events[:8], retry])


def test_pending_app_page_controller_uses_its_existing_mode_specific_context_limit():
    from application_state.agent_conversation.build_source_free import effective_pending_source
    receipt, policy, events = pending_page_phase_case()
    auth = events[5].model_copy(update={'input_tokens': 63_000, 'output_token_reserve': 2_000})
    execution = pending_execution(receipt, policy, [*events[:5], auth])
    with pytest.raises(ValueError, match='frozen context window'):
        effective_pending_source(receipt, execution)


def pending_page_input_case():
    from hashlib import sha256
    from application_state.agent_conversation.build_decision_context import identity
    from application_state.agent_conversation.build_source_free import pending_app_page_selection_input
    receipt, policy, events = pending_page_phase_case()
    history = [{'user': f'User detail {i}', 'assistant': f'Already discussed detail {i}'} for i in range(60)]
    from application_state.agent_conversation.build_intentional_response import semantic_routing_state
    history[10]['collaboration'] = {'kind': 'lore_page', 'destination': {
        'instruction': 'Create a page for Maelthor visitor notes', 'title': 'Maelthor visitor notes'}}
    state = semantic_routing_state(policy.action.intent.message, {
        'history': history, 'allowed_operations': ['answer_from_sources'],
        'current_page': {'title': 'Current draft'}, 'page_target': None, 'working_draft': None}, None)
    history = state['interaction']['history']
    initial = json.dumps({'model': policy.provider_roles.controller.model, 'state': state, 'questions': {}})
    values = receipt.model_dump(mode='json', by_alias=True)
    values.pop('context_receipt_sha256')
    initial_hash = sha256(initial.encode()).hexdigest()
    values['assembled_input']['assembled_input_sha256'] = initial_hash
    receipt = seal_pending_receipt(values)
    first = events[0]
    first = first.model_copy(update={'envelope_sha256': initial_hash,
        'dispatch_identity_sha256': identity(envelope_sha256=initial_hash, provider=first.provider,
            model=first.model, api_mode=first.api_mode, context_mode=first.context_mode)})
    events[0] = first
    events[3] = events[3].model_copy(update={'controller_envelope_sha256': initial_hash})
    events[4] = events[4].model_copy(update={'pending_context_receipt_sha256': receipt.context_receipt_sha256})
    execution = pending_execution(receipt, policy, events[:5])
    request = pending_app_page_selection_input(receipt, execution, initial)
    raw = json.dumps(request)
    envelope_hash = sha256(raw.encode()).hexdigest()
    auth = events[5].model_copy(update={'envelope_sha256': envelope_hash,
        'dispatch_identity_sha256': identity(envelope_sha256=envelope_hash, provider=first.provider,
            model=first.model, api_mode=first.api_mode, context_mode=first.context_mode)})
    return receipt, execution, auth, initial, raw, history


def test_pending_app_page_input_preserves_full_dialogue_and_only_navigation_aliases():
    from application_state.agent_conversation.build_source_free import validate_pending_app_page_selection_request
    receipt, execution, auth, initial, raw, history = pending_page_input_case()
    body = validate_pending_app_page_selection_request(receipt, execution, auth, raw, initial)
    assert body['state']['history'] == history and len(history) == 60
    assert set(body['questions']) == {'page1'}
    assert body['state']['saved_pages'][0]['choice'] == 'page1'
    catalog = execution.events[-1]
    for host_value in [str(catalog.event_id), str(catalog.pages[0].document_id), catalog.pages[0].world_id,
                       receipt.context_receipt_sha256, str(receipt.conversation_observation.conversation_id)]:
        assert host_value not in raw
    assert 'registry_revision' not in raw and 'admitted_from_revision' not in raw


@pytest.mark.parametrize('change', ['history', 'title', 'choices', 'host_metadata', 'initial_request', 'catalog_binding'])
def test_pending_app_page_input_cannot_change_frozen_context_or_wire_offer(change):
    from application_state.agent_conversation.build_source_free import validate_pending_app_page_selection_request
    receipt, execution, auth, initial, raw, history = pending_page_input_case()
    body = json.loads(raw)
    if change == 'history':
        body['state']['history'] = history[1:]
    elif change == 'title':
        body['state']['saved_pages'][0]['title'] = 'Replacement page'
    elif change == 'choices':
        body['questions']['page1']['criteria']['invent'] = None
    elif change == 'host_metadata':
        body['state']['receipt'] = receipt.context_receipt_sha256
    elif change == 'initial_request':
        initial += ' '
    else:
        auth = auth.model_copy(update={'catalog_event_id': uuid4()})
    with pytest.raises(ValueError):
        validate_pending_app_page_selection_request(receipt, execution, auth, json.dumps(body), initial)


@pytest.mark.parametrize('end', [6, 7, 8, 9])
def test_pending_native_preparation_cannot_cross_an_unresolved_app_page_phase(end):
    from application_state.agent_conversation.build_source_free import pending_source_work
    receipt, policy, events = pending_page_phase_case()
    partial = pending_execution(receipt, policy, events[:end])
    with pytest.raises(ValueError, match='must resolve before native source preparation'):
        pending_source_work(partial)
    complete = pending_execution(receipt, policy, events)
    with pytest.raises(ValueError, match='further-source coverage'):
        pending_source_work(complete)


def pending_page_dispatch_harness(monkeypatch):
    from types import SimpleNamespace
    from datetime import timedelta
    from tests.test_surface_native_execution import BUILD_TURN_ID
    state, _ = settlement_harness(monkeypatch, with_source=False)
    receipt, execution, auth, initial, raw, _ = pending_page_input_case()
    provenance = provenance_for(receipt.work_context).model_copy(
        update={'surface_instance_id': execution.policy.action.intent.surface_instance_id})
    data = receipt.model_dump(mode='json', by_alias=True)
    data.pop('context_receipt_sha256')
    receipt = seal_pending_receipt(data | {'provenance_sha256': t.canonical_sha256(provenance)})
    events = list(execution.events)
    events[-1] = events[-1].model_copy(update={'pending_context_receipt_sha256': receipt.context_receipt_sha256})
    execution = pending_execution(receipt, execution.policy, events)
    sub = t.TurnSubmission(world_id=execution.policy.action.intent.world_id,
        conversation_id=receipt.conversation_observation.conversation_id, idempotency_key=uuid4(),
        expected_conversation_revision=1, user_text=execution.policy.action.intent.message,
        provenance=provenance, submitted_intent_v2=execution.policy.action.intent,
        graph_context_receipt=receipt, graph_context_execution=pending_execution(receipt, execution.policy))
    state.turn = retained(sub, turn_id=BUILD_TURN_ID, status='running', revision=3, attempt=1,
        claim_expires_at=state.now + timedelta(minutes=2), graph_context_execution=execution)
    state.pointer = t.WorldPointer(world_id=sub.world_id, active_conversation_id=sub.conversation_id,
        revision=receipt.conversation_observation.pointer_revision)
    first = events[0]
    state.prompt = {'kind': 'prompt_reference', 'sequence': 0, 'elapsed_ms': 0,
        'evidence_id': str(uuid4()), 'provider_attempt_id': str(first.provider_attempt_id),
        'provider': first.provider, 'model': first.model, 'api_mode': first.api_mode,
        'serializer_version': first.serializer_version, 'payload_sha256': first.envelope_sha256,
        'payload_utf8_bytes': len(initial.encode())}
    state.initial_request, state.prepared_request = initial, raw
    state.prompt_count = 1
    def query(sql, args):
        if sql == 'SELECT 1 FROM agent.turn_retry WHERE predecessor_id=%s':
            return state.leaf_query(sql, args)
        assert state.depth == 1 and args == (state.turn.turn_id,)
        assert sql == 'SELECT payload FROM agent.turn_context_trace WHERE turn_id=%s'
        return SimpleNamespace(fetchall=lambda: [({'observations': [state.prompt] * state.prompt_count},)])
    state.conn.execute = query
    def run(*, authorization=auth, request=raw, first_request=initial):
        return state.service.authorize_pending_app_page_selection(state.turn.world_id,
            state.turn.conversation_id, state.turn.turn_id, expected_revision=3, expected_attempt=1,
            authorization=authorization, prepared_request_json=request, initial_request_json=first_request,
            authorize_current_access=state.authorize)
    return state, run, auth, raw


def test_locked_pending_page_dispatch_is_one_shot_and_replays_original_call_nonfresh(monkeypatch):
    state, run, auth, _ = pending_page_dispatch_harness(monkeypatch)
    admitted, fresh = run()
    assert fresh and admitted.revision == 4 and state.persisted == 1
    assert state.locks == ['world', 'conversation', 'turn'] and state.access_calls == 1
    replay, fresh = run()
    assert not fresh and replay == admitted and state.persisted == 1 and state.access_calls == 2
    assert state.materialized == 0


@pytest.mark.parametrize('failure', ['pointer', 'expiry', 'attempt', 'access', 'access_delay',
    'wire', 'missing_prompt', 'duplicate_prompt', 'prompt_hash', 'prompt_role', 'cas_failure', 'admission_revision', 'successor'])
def test_locked_pending_page_dispatch_rejects_stale_or_unproven_calls(monkeypatch, failure):
    from datetime import timedelta
    from application_state.errors import ApplicationStateConflictError, ApplicationStateValidationError
    state, run, auth, raw = pending_page_dispatch_harness(monkeypatch)
    if failure == 'pointer':
        state.pointer = state.pointer.model_copy(update={'revision': state.pointer.revision + 2})
    elif failure == 'expiry':
        state.now += timedelta(hours=1)
    elif failure == 'attempt':
        state.turn = state.turn.model_copy(update={'attempt': 2})
    elif failure == 'access':
        state.denied = True
    elif failure == 'access_delay':
        state.access_delay = True
    elif failure == 'wire':
        body = json.loads(raw)
        body['state']['host_receipt'] = 'forbidden'
        raw = json.dumps(body)
    elif failure in {'missing_prompt', 'duplicate_prompt'}:
        state.prompt_count = 0 if failure == 'missing_prompt' else 2
    elif failure == 'prompt_hash':
        state.prompt['payload_sha256'] = 'b' * 64
    elif failure == 'prompt_role':
        state.prompt['provider'] = 'another-provider'
    elif failure == 'cas_failure':
        state.cas_failure = True
    elif failure == 'successor':
        state.successor = True
    else:
        auth = auth.model_copy(update={'admitted_from_revision': 4})
    with pytest.raises((ApplicationStateConflictError, ApplicationStateValidationError)):
        run(authorization=auth, request=raw)
    assert state.persisted == state.materialized == 0


@pytest.mark.parametrize('event_kind', ['authorization', 'sdk_entry', 'response', 'selection', 'page_read'])
def test_pending_generic_append_cannot_bypass_prepared_dispatch_owner(monkeypatch, event_kind):
    from application_state.agent_conversation import service as service_module
    from application_state.errors import ApplicationStateValidationError
    state, _, auth, _ = pending_page_dispatch_harness(monkeypatch)
    monkeypatch.setattr(service_module, '_execution_append_transaction', lambda measure: state.uow())
    if event_kind in {'selection', 'page_read'}:
        _, _, events = pending_page_phase_case()
        event = events[8 if event_kind == 'selection' else 9]
    else:
        event = auth if event_kind == 'authorization' else t.ProviderOutcomeEventV1(kind='provider_outcome',
            event_id=uuid4(), sequence=6, provider_attempt_id=auth.provider_attempt_id,
            outcome='sdk_entered' if event_kind == 'sdk_entry' else 'response_received')
    with pytest.raises(ApplicationStateValidationError, match='exact prepared-input admission owner'):
        state.service._append_graph_execution_event(state.turn.world_id, state.turn.conversation_id,
            state.turn.turn_id, expected_revision=3, expected_attempt=1, event=event, duplicate_key='event_id')
    assert state.persisted == 0


@pytest.mark.parametrize('when', ['before', 'after'])
def test_pending_source_preparation_rejects_a_saved_successor_before_or_during_io(monkeypatch, when):
    from application_state.errors import ApplicationStateConflictError
    state, run = settlement_harness(monkeypatch)
    if when == 'before':
        state.successor = True
    else:
        state.on_prepare = lambda: setattr(state, 'successor', True)
    with pytest.raises(ApplicationStateConflictError, match='saved successor'):
        run()
    assert state.persisted == 0 and state.materialized == (0 if when == 'before' else 1)


def pending_sdk_entry_harness(monkeypatch):
    from types import SimpleNamespace
    state, admit, authorization, raw = pending_page_dispatch_harness(monkeypatch)
    admitted, fresh = admit()
    assert fresh and admitted.revision == 4
    state.sdk_prompt = state.prompt | {
        'evidence_id': str(uuid4()), 'provider_attempt_id': str(authorization.provider_attempt_id),
        'payload_sha256': authorization.envelope_sha256, 'payload_utf8_bytes': len(raw.encode())}
    state.sdk_prompt_count = 1
    def query(sql, args):
        if sql == 'SELECT 1 FROM agent.turn_retry WHERE predecessor_id=%s':
            return state.leaf_query(sql, args)
        assert state.depth == 1 and args == (state.turn.turn_id,)
        assert sql == 'SELECT payload FROM agent.turn_context_trace WHERE turn_id=%s'
        return SimpleNamespace(fetchall=lambda: [({'observations': [state.prompt] +
            [state.sdk_prompt] * state.sdk_prompt_count},)])
    state.conn.execute = query
    entry = t.ProviderOutcomeEventV1(kind='provider_outcome', event_id=uuid4(), sequence=6,
        provider_attempt_id=authorization.provider_attempt_id, outcome='sdk_entered')
    def enter(*, event=entry, request=raw, revision=4):
        return state.service.enter_pending_app_page_sdk(state.turn.world_id, state.turn.conversation_id,
            state.turn.turn_id, expected_revision=revision, expected_attempt=1, outcome=event,
            prepared_request_json=request, authorize_current_access=state.authorize)
    return state, enter, entry, raw


def test_pending_sdk_entry_requires_captured_prompt_and_grants_only_once(monkeypatch):
    from application_state.errors import ApplicationStateConflictError
    state, enter, entry, _ = pending_sdk_entry_harness(monkeypatch)
    updated, fresh = enter()
    assert fresh and updated.revision == 5 and state.persisted == 2
    with pytest.raises(ApplicationStateConflictError):
        enter()  # a lost response does not grant a second dispatch
    restored, fresh = enter(revision=updated.revision)
    assert not fresh and restored == updated and state.persisted == 2
    with pytest.raises(ApplicationStateConflictError):
        enter(revision=updated.revision, event=entry.model_copy(update={'event_id': uuid4()}))
    assert state.materialized == 0


@pytest.mark.parametrize('failure', ['pointer', 'access', 'expiry', 'access_delay', 'successor',
    'missing_prompt', 'duplicate_prompt', 'prompt_hash', 'prompt_role', 'wire', 'foreign_attempt', 'cas_failure'])
def test_pending_sdk_entry_refuses_stale_access_or_unproven_wire(monkeypatch, failure):
    from datetime import timedelta
    from application_state.errors import ApplicationStateConflictError, ApplicationStateValidationError
    state, enter, entry, raw = pending_sdk_entry_harness(monkeypatch)
    if failure == 'pointer':
        state.pointer = state.pointer.model_copy(update={'revision': state.pointer.revision + 2})
    elif failure == 'access':
        state.denied = True
    elif failure == 'expiry':
        state.now += timedelta(hours=1)
    elif failure == 'access_delay':
        state.access_delay = True
    elif failure == 'successor':
        state.successor = True
    elif failure in {'missing_prompt', 'duplicate_prompt'}:
        state.sdk_prompt_count = 0 if failure == 'missing_prompt' else 2
    elif failure == 'prompt_hash':
        state.sdk_prompt['payload_sha256'] = 'b' * 64
    elif failure == 'prompt_role':
        state.sdk_prompt['api_mode'] = 'another-api'
    elif failure == 'wire':
        raw += ' '
    elif failure == 'foreign_attempt':
        entry = entry.model_copy(update={'provider_attempt_id': uuid4()})
    else:
        state.cas_failure = True
    with pytest.raises((ApplicationStateConflictError, ApplicationStateValidationError)):
        enter(event=entry, request=raw)
    assert state.persisted == 1 and state.materialized == 0


def pending_response_collector(*, acknowledged=True, components=None):
    from threading import Lock
    from types import SimpleNamespace
    from tests.test_agent_context_trace_collector import Store
    from apps.live_control_server.services.agent_context_trace_collector import ContextTraceCollector
    if components is None:
        receipt, policy, events = pending_page_phase_case()
        execution = pending_execution(receipt, policy, events[:8 if acknowledged else 7])
    else:
        receipt, execution = components
        policy = execution.policy
    controller = [event for event in execution.events if isinstance(event, t.ProviderAttemptAuthorizedEventV1)][-1]
    turn = SimpleNamespace(world_id=policy.action.intent.world_id,
        conversation_id=receipt.conversation_observation.conversation_id, turn_id=uuid4(),
        revision=5, attempt=1, sequence=1, graph_context_receipt=receipt, graph_context_execution=execution)
    store = Store()
    fence = SimpleNamespace(service=store, turn=turn, trace=None,
        renewer=SimpleNamespace(_lock=Lock(), _turn=turn, _claim=turn))
    return ContextTraceCollector(fence), store, controller


def test_pending_controller_response_uses_actual_collector_and_exact_replay_identity():
    from application_state.errors import ApplicationStateValidationError
    capture, store, controller = pending_response_collector()
    raw = json.dumps({'answers': {'page1': {'selected': 'read'}}})
    capture.controller_decision_response(raw, producing_provider_attempt_id=controller.provider_attempt_id)
    materials = store.trace.observations[-1].materials
    assert len(materials) == 1 and materials[0].text == raw
    assert materials[0].item_id == f'unvalidated-controller-decision:{controller.provider_attempt_id}:{capture.bound_context_receipt_sha256}'
    capture.controller_decision_response(raw, producing_provider_attempt_id=controller.provider_attempt_id)
    assert len(store.trace.observations) == 1
    with pytest.raises(ApplicationStateValidationError, match='different bytes'):
        capture.controller_decision_response(raw + ' ', producing_provider_attempt_id=controller.provider_attempt_id)


@pytest.mark.parametrize('failure', ['unacknowledged', 'foreign_producer', 'receipt_changed'])
def test_pending_controller_capture_preserves_acknowledgement_producer_and_receipt_guards(failure):
    from application_state.errors import ApplicationStateValidationError
    capture, store, controller = pending_response_collector(acknowledged=failure != 'unacknowledged')
    producer = uuid4() if failure == 'foreign_producer' else controller.provider_attempt_id
    if failure == 'receipt_changed':
        capture.bound_context_receipt_sha256 = 'b' * 64
    with pytest.raises(ApplicationStateValidationError):
        capture.controller_decision_response('{}', producing_provider_attempt_id=producer)
    assert not store.trace.observations


def pending_selection_proof_case():
    from hashlib import sha256
    from generationengine.types import DecisionResult, ChoiceDecisionAnswer, InferenceObservation
    from application_state.agent_conversation.build_related_pages import RelatedPagesSelection
    from tests.test_surface_native_execution import outcomes
    receipt, before, authorization, initial, request, _ = pending_page_input_case()
    execution = pending_execution(receipt, before.policy, [*before.events, authorization, *outcomes(authorization, 6)])
    response = DecisionResult(answers={'page1': ChoiceDecisionAnswer(selected='read', probabilities={'read': .9, 'skip': .1})},
        observation=InferenceObservation(provider='typesafe', resolved_model='jev-1.14.0', response_model='jev-1.14.0',
            latency_ms=1, retry_count=0, state='completed', provider_attempt_count=1))
    raw = response.model_dump_json(by_alias=True)
    capture, store, _ = pending_response_collector(components=(receipt, execution))
    capture.controller_decision_response(raw, producing_provider_attempt_id=authorization.provider_attempt_id)
    catalog = before.events[-1]
    selected = RelatedPagesSelection(event_id=uuid4(), sequence=8,
        controller_attempt_id=authorization.provider_attempt_id, controller_envelope_sha256=authorization.envelope_sha256,
        controller_response_sha256=sha256(raw.encode()).hexdigest(), document_ids=[catalog.pages[0].document_id])
    proof = {'request_json': request, 'response_json': raw, 'initial_request_json': initial}
    return receipt, execution, selected, proof, store.trace.model_dump(mode='json', by_alias=True)


def test_pending_selection_binds_actual_captured_sdk_votes_to_exact_saved_page():
    from application_state.agent_conversation.build_source_free import validate_pending_app_page_selection_result
    receipt, execution, selected, proof, trace = pending_selection_proof_case()
    assert validate_pending_app_page_selection_result(receipt, execution, selected, proof, trace) == tuple(selected.document_ids)


@pytest.mark.parametrize('failure', ['missing_capture', 'foreign_capture', 'changed_capture', 'wrong_vote',
    'foreign_controller', 'response_bytes', 'request_bytes', 'hidden_retry'])
def test_pending_selection_rejects_unproven_controller_votes(failure):
    from hashlib import sha256
    from application_state.agent_conversation.build_source_free import validate_pending_app_page_selection_result
    receipt, execution, selected, proof, trace = pending_selection_proof_case()
    material = trace['observations'][-1]['materials'][0]
    if failure == 'missing_capture':
        trace['observations'] = []
    elif failure == 'foreign_capture':
        material['item_id'] = 'unvalidated-controller-decision:foreign:foreign'
    elif failure == 'changed_capture':
        material['text'] += ' '
    elif failure == 'wrong_vote':
        selected = selected.model_copy(update={'document_ids': []})
    elif failure == 'foreign_controller':
        selected = selected.model_copy(update={'controller_attempt_id': uuid4()})
    elif failure == 'response_bytes':
        proof['response_json'] += ' '
    elif failure == 'request_bytes':
        proof['request_json'] += ' '
    else:
        response = json.loads(proof['response_json'])
        response['observation']['retry_count'] = 1
        proof['response_json'] = json.dumps(response)
        material['text'] = proof['response_json']
        selected = selected.model_copy(update={'controller_response_sha256': sha256(proof['response_json'].encode()).hexdigest()})
    with pytest.raises(ValueError):
        validate_pending_app_page_selection_result(receipt, execution, selected, proof, trace)


def pending_selection_service_harness(monkeypatch):
    from types import SimpleNamespace
    from hashlib import sha256
    from generationengine.types import DecisionResult, ChoiceDecisionAnswer, InferenceObservation
    from application_state.agent_conversation.build_related_pages import RelatedPagesSelection
    state, enter, entry, _ = pending_sdk_entry_harness(monkeypatch)
    _, fresh = enter()
    assert fresh and state.turn.revision == 5
    response = DecisionResult(answers={'page1': ChoiceDecisionAnswer(selected='read', probabilities={'read': .9, 'skip': .1})},
        observation=InferenceObservation(provider='typesafe', resolved_model='jev-1.14.0', response_model='jev-1.14.0',
            latency_ms=1, retry_count=0, state='completed', provider_attempt_count=1))
    raw = response.model_dump_json(by_alias=True)
    received = t.ProviderOutcomeEventV1(kind='provider_outcome', event_id=uuid4(), sequence=7,
        provider_attempt_id=entry.provider_attempt_id, outcome='response_received')
    def acknowledge(*, event=received, revision=5):
        return state.service.record_pending_app_controller_outcome(state.turn.world_id,
            state.turn.conversation_id, state.turn.turn_id, expected_revision=revision, expected_attempt=1,
            outcome=event, authorize_current_access=state.authorize)
    _, fresh = acknowledge()
    assert fresh and state.turn.revision == 6
    capture, store, _ = pending_response_collector(components=(state.turn.graph_context_receipt, state.turn.graph_context_execution))
    capture.controller_decision_response(raw, producing_provider_attempt_id=entry.provider_attempt_id)
    state.stored_trace = store.trace.model_dump(mode='json', by_alias=True)
    state.stored_trace['observations'][-1]['sequence'] = 2
    state.stored_trace['observations'] = [state.prompt, state.sdk_prompt | {'sequence': 1}, *state.stored_trace['observations']]
    def query(sql, args):
        if sql == 'SELECT 1 FROM agent.turn_retry WHERE predecessor_id=%s':
            return state.leaf_query(sql, args)
        assert state.depth == 1
        if sql == 'SELECT payload FROM agent.turn_context_trace WHERE turn_id=%s':
            assert args == (state.turn.turn_id,)
            return SimpleNamespace(fetchall=lambda: [(state.stored_trace,)])
        assert sql == 'SELECT payload FROM agent.turn_context_trace WHERE turn_id=%s AND attempt=%s'
        assert args == (state.turn.turn_id, state.turn.attempt)
        return SimpleNamespace(fetchone=lambda: (state.stored_trace,))
    state.conn.execute = query
    catalog = state.turn.graph_context_execution.events[4]
    authorization = state.turn.graph_context_execution.events[5]
    selection = RelatedPagesSelection(event_id=uuid4(), sequence=8,
        controller_attempt_id=entry.provider_attempt_id, controller_envelope_sha256=authorization.envelope_sha256,
        controller_response_sha256=sha256(raw.encode()).hexdigest(), document_ids=[catalog.pages[0].document_id])
    proof = {'request_json': state.prepared_request, 'response_json': raw, 'initial_request_json': state.initial_request}
    def select(*, event=selection, producer_proof=proof, revision=6):
        return state.service.record_pending_app_page_selection(state.turn.world_id, state.turn.conversation_id,
            state.turn.turn_id, expected_revision=revision, expected_attempt=1, selection=event,
            producer_proof=producer_proof, authorize_current_access=state.authorize)
    return state, acknowledge, select, selection, proof


def test_pending_selection_service_loads_stored_capture_and_admits_exact_choices_once(monkeypatch):
    state, acknowledge, select, selection, _ = pending_selection_service_harness(monkeypatch)
    replay, fresh = acknowledge(revision=6)
    assert not fresh and replay == state.turn
    updated, fresh = select()
    assert fresh and updated.revision == 7 and updated.graph_context_execution.events[-1] == selection
    replay, fresh = select(revision=7)
    assert not fresh and replay == updated and state.persisted == 4
    assert state.materialized == 0


@pytest.mark.parametrize('failure', ['stored_capture_missing', 'stored_capture_changed', 'caller_trace',
    'wrong_vote', 'pointer', 'access', 'expiry', 'successor', 'cas_failure'])
def test_pending_selection_service_refuses_unproven_or_stale_choices(monkeypatch, failure):
    from datetime import timedelta
    from application_state.errors import ApplicationStateConflictError, ApplicationStateValidationError
    state, _, select, selection, proof = pending_selection_service_harness(monkeypatch)
    if failure == 'stored_capture_missing':
        state.stored_trace['observations'] = state.stored_trace['observations'][:2]
    elif failure == 'stored_capture_changed':
        state.stored_trace['observations'][-1]['materials'][0]['text'] += ' '
    elif failure == 'caller_trace':
        proof = proof | {'trace': state.stored_trace}
    elif failure == 'wrong_vote':
        selection = selection.model_copy(update={'document_ids': []})
    elif failure == 'pointer':
        state.pointer = state.pointer.model_copy(update={'revision': state.pointer.revision + 2})
    elif failure == 'access':
        state.denied = True
    elif failure == 'expiry':
        state.now += timedelta(hours=1)
    elif failure == 'successor':
        state.successor = True
    else:
        state.cas_failure = True
    with pytest.raises((ApplicationStateConflictError, ApplicationStateValidationError)):
        select(event=selection, producer_proof=proof)
    assert state.persisted == 3 and state.materialized == 0


def test_pending_outcome_cannot_report_a_response_before_sdk_entry(monkeypatch):
    from application_state.errors import ApplicationStateValidationError
    state, admit, authorization, _ = pending_page_dispatch_harness(monkeypatch)
    admit()
    event = t.ProviderOutcomeEventV1(kind='provider_outcome', event_id=uuid4(), sequence=6,
        provider_attempt_id=authorization.provider_attempt_id, outcome='response_received')
    with pytest.raises(ApplicationStateValidationError, match='observed SDK entry'):
        state.service.record_pending_app_controller_outcome(state.turn.world_id, state.turn.conversation_id,
            state.turn.turn_id, expected_revision=4, expected_attempt=1, outcome=event,
            authorize_current_access=state.authorize)
    assert state.persisted == 1


def test_pending_outcome_records_known_not_sent_without_sdk_entry(monkeypatch):
    state, admit, authorization, _ = pending_page_dispatch_harness(monkeypatch)
    admit()
    event = t.ProviderOutcomeEventV1(kind='provider_outcome', event_id=uuid4(), sequence=6,
        provider_attempt_id=authorization.provider_attempt_id, outcome='known_not_sent')
    updated, fresh = state.service.record_pending_app_controller_outcome(state.turn.world_id,
        state.turn.conversation_id, state.turn.turn_id, expected_revision=4, expected_attempt=1,
        outcome=event, authorize_current_access=state.authorize)
    assert fresh and updated.revision == 5 and updated.graph_context_execution.events[-1] == event
    assert not any(getattr(row, 'outcome', None) == 'sdk_entered' and
        getattr(row, 'provider_attempt_id', None) == authorization.provider_attempt_id
        for row in updated.graph_context_execution.events)


def pending_page_read_harness(monkeypatch):
    from types import SimpleNamespace
    from pathlib import Path
    from hashlib import sha256
    from apps.live_control_server.services import build_related_pages as public_owner
    state, _, choose, _, _ = pending_selection_service_harness(monkeypatch)
    _, fresh = choose()
    assert fresh and state.turn.revision == 7
    page = state.turn.graph_context_execution.events[4].pages[0]
    markdown = 'Ethel remembered a dream; the password was reported, not established as played truth.'
    state.snapshot = SimpleNamespace(record=SimpleNamespace(world_id=page.world_id,
        document_id=str(page.document_id), kind='worldbuilding_source', status='active', content_status='committed',
        revision=page.registry_revision, title=page.title, visibility_state=page.visibility,
        source_domain='worldbuilding', document_class='person', authority_state='draft'),
        loaded_revision=page.registry_revision, content_sha256=sha256(markdown.encode()).hexdigest(), markdown=markdown)
    state.physical_page_reads = 0
    state.on_page_read = None
    def snapshot(root, document_id):
        assert state.depth == 0 and root == Path('/synthetic-app-read') and document_id == str(page.document_id)
        state.physical_page_reads += 1
        if state.on_page_read:
            state.on_page_read()
        return state.snapshot
    monkeypatch.setattr(public_owner, 'root', lambda: Path('/synthetic-app-read'))
    monkeypatch.setattr(public_owner, 'get_committed_page_snapshot', snapshot)
    event_id, read_id = uuid4(), uuid4()
    def read(*, revision=7, event=event_id, identity=read_id, document=page.document_id, materializer=public_owner.materialize):
        return state.service.read_pending_app_page(state.turn.world_id, state.turn.conversation_id, state.turn.turn_id,
            expected_revision=revision, expected_attempt=1, document_id=document, event_id=event, read_id=identity,
            materialize_page=materializer, authorize_current_access=state.authorize)
    return state, read, page


def test_pending_page_read_uses_public_snapshot_owner_once_without_core_or_app_locks(monkeypatch):
    from application_state.agent_conversation.build_source_free import effective_pending_source
    from application_state.errors import ApplicationStateConflictError
    state, read, page = pending_page_read_harness(monkeypatch)
    assert state.turn.graph_context_receipt.source_observation.binding is None
    updated, fresh = read()
    assert fresh and updated.revision == 8 and state.physical_page_reads == 1
    event = updated.graph_context_execution.events[-1]
    assert event.page.document_id == page.document_id and event.markdown == state.snapshot.markdown
    assert effective_pending_source(updated.graph_context_receipt, updated.graph_context_execution) is None
    replay, fresh = read(revision=8)
    assert not fresh and replay == updated and state.physical_page_reads == 1
    with pytest.raises(ApplicationStateConflictError):
        read()  # stale claim fails before any IO
    with pytest.raises(ApplicationStateConflictError):
        read(revision=8, event=uuid4(), identity=uuid4())
    assert state.physical_page_reads == 1


@pytest.mark.parametrize('failure', ['unselected', 'access_before', 'pointer_after', 'access_after',
    'expiry_after', 'successor_after', 'revision_changed', 'digest_changed', 'cas_failure',
    'event_collision', 'claim_after', 'access_delay_after'])
def test_pending_page_read_discards_changed_scope_access_or_snapshot(monkeypatch, failure):
    from datetime import timedelta
    from application_state.errors import ApplicationStateConflictError, ApplicationStateValidationError
    state, read, _ = pending_page_read_harness(monkeypatch)
    def change():
        if failure == 'pointer_after':
            state.pointer = state.pointer.model_copy(update={'revision': state.pointer.revision + 2})
        elif failure == 'access_after':
            state.denied = True
        elif failure == 'expiry_after':
            state.now += timedelta(hours=1)
        elif failure == 'successor_after':
            state.successor = True
        elif failure == 'claim_after':
            state.turn = state.turn.model_copy(update={'revision': state.turn.revision + 1})
        elif failure == 'access_delay_after':
            state.access_delay = True
    state.on_page_read = change
    if failure == 'access_before':
        state.denied = True
    elif failure == 'revision_changed':
        state.snapshot.record.revision += 1
        state.snapshot.loaded_revision += 1
    elif failure == 'digest_changed':
        state.snapshot.markdown += 'Uncommitted replacement.'
    elif failure == 'cas_failure':
        state.cas_failure = True
    kwargs = ({'document': uuid4()} if failure == 'unselected' else
              {'event': state.turn.graph_context_execution.events[-1].event_id} if failure == 'event_collision' else {})
    with pytest.raises((ApplicationStateConflictError, ApplicationStateValidationError)):
        read(**kwargs)
    assert state.persisted == 4
    assert state.physical_page_reads == (0 if failure in {'unselected', 'access_before', 'event_collision'} else 1)


def test_pending_page_read_does_not_pass_foreign_materialization_to_access_owner(monkeypatch):
    from application_state.errors import ApplicationStateValidationError
    state, read, page = pending_page_read_harness(monkeypatch)
    before = state.access_calls
    def foreign(pointer):
        assert state.depth == 0
        from hashlib import sha256
        return pointer.model_dump(mode='json') | {'world_id': 'foreign-world',
            'content_sha256': sha256(b'foreign').hexdigest(), 'markdown': 'foreign'}
    with pytest.raises(ApplicationStateValidationError, match='changed the selected saved pointer'):
        read(materializer=foreign)
    assert state.access_calls == before + 1 and state.persisted == 4


def test_pending_opening_uses_exact_semantic_input_pair_and_append_binding():
    from application_state.agent_conversation.native_context import is_semantic_build_input, NativeBuildProviderInputV2
    from application_state.agent_conversation.service import AgentConversationService
    from tests.test_surface_native_execution import component
    receipt, policy = pending_execution_pair()
    execution = pending_execution(receipt, policy)
    assert is_semantic_build_input(receipt)
    historical, historical_execution = component('build')
    assert not is_semantic_build_input(historical)
    values = receipt.assembled_input.model_dump(mode='python')
    values.pop('assembler_version')
    crossed = receipt.model_copy(update={'assembled_input': NativeBuildProviderInputV2(**values)})
    assert not is_semantic_build_input(crossed)
    owner = AgentConversationService()
    bound = owner._bind_execution_append(receipt, execution)
    assert type(bound) is type(execution) and bound == execution and bound is not execution
    for context, ledger in [(historical, execution), (receipt, historical_execution)]:
        with pytest.raises(ValueError, match='concrete Build receipt and execution'):
            owner._bind_execution_append(context, ledger)


@pytest.mark.parametrize('family', ['pending', 'historical'])
def test_existing_draft_owner_accepts_exact_pending_and_historical_pairs(family):
    from types import SimpleNamespace
    from application_state.agent_conversation.build_draft_context import validate_record, native_build_action
    from tests.test_surface_native_build_work import case
    historical, historical_execution, captured, *_ = case()
    if family == 'pending':
        receipt, policy = pending_execution_pair(captured_case=(historical, historical_execution, captured))
        execution = pending_execution(receipt, policy, historical_execution.events[:5])
    else:
        receipt, execution = historical, historical_execution
    record = captured.record
    turn = SimpleNamespace(world_id=record.snapshot.world_id, conversation_id=record.conversation_id,
        turn_id=record.turn_id, attempt=record.attempt, submitted_intent_fingerprint_v2=record.submitted_intent_fingerprint,
        graph_context_receipt=receipt, graph_context_execution=execution)
    assert native_build_action(execution) is execution.policy.action
    validate_record(record, turn)


@pytest.mark.parametrize('change', ['historical_receipt', 'historical_execution', 'pointer'])
def test_existing_draft_owner_refuses_crossed_pending_pair_or_changed_pointer(change):
    from types import SimpleNamespace
    from application_state.agent_conversation.build_draft_context import validate_record
    from tests.test_surface_native_build_work import case
    historical, old_execution, captured, *_ = case()
    receipt, policy = pending_execution_pair(captured_case=(historical, old_execution, captured))
    execution = pending_execution(receipt, policy, old_execution.events[:5])
    if change == 'historical_receipt':
        receipt = historical
    elif change == 'historical_execution':
        execution = old_execution
    else:
        receipt = receipt.model_copy(update={'conversation_observation': receipt.conversation_observation.model_copy(
            update={'pointer_revision': receipt.conversation_observation.pointer_revision + 1})})
    record = captured.record
    turn = SimpleNamespace(world_id=record.snapshot.world_id, conversation_id=record.conversation_id,
        turn_id=record.turn_id, attempt=record.attempt, submitted_intent_fingerprint_v2=record.submitted_intent_fingerprint,
        graph_context_receipt=receipt, graph_context_execution=execution)
    with pytest.raises(ValueError):
        validate_record(record, turn)


def pending_initial_opening_harness(monkeypatch):
    from types import SimpleNamespace
    from datetime import UTC, datetime
    from application_state.agent_conversation import context_trace_store
    from application_state.agent_conversation.context_trace import TurnContextTraceV1, TracePromptReference, TraceProviderCall
    state, _, _, _ = pending_page_dispatch_harness(monkeypatch)
    receipt, policy = state.turn.graph_context_receipt, state.turn.graph_context_execution.policy
    first = state.turn.graph_context_execution.events[0]
    from hashlib import sha256
    from application_state.agent_conversation.build_intentional_response import WORK, decision_instructions
    from application_state.agent_conversation.build_decision_context import identity
    body = json.loads(state.initial_request)
    body['questions'] = {'requested_work': {'type': 'choice',
        'instructions': decision_instructions(policy.action.requested_work_menu_sha256), 'criteria': dict.fromkeys(WORK)}}
    state.initial_request = json.dumps(body)
    envelope = sha256(state.initial_request.encode()).hexdigest()
    first = first.model_copy(update={'envelope_sha256': envelope,
        'dispatch_identity_sha256': identity(envelope_sha256=envelope, provider=first.provider,
            model=first.model, api_mode=first.api_mode, context_mode=first.context_mode)})
    values = receipt.model_dump(mode='json', by_alias=True)
    values.pop('context_receipt_sha256')
    values['assembled_input']['assembled_input_sha256'] = envelope
    receipt = seal_pending_receipt(values)
    state.prompt.update(payload_sha256=envelope, payload_utf8_bytes=len(state.initial_request.encode()))
    state.turn = t.Turn.model_validate(state.turn.model_copy(update={
        'revision': 2, 'graph_context_receipt': receipt,
        'graph_context_execution': pending_execution(receipt, policy)}))
    state.opening_trace = TurnContextTraceV1(trace_id=uuid4(), world_id=state.turn.world_id,
        conversation_id=state.turn.conversation_id, turn_id=state.turn.turn_id, attempt=1,
        started_at=datetime.now(UTC), execution_start_sequence=0, observations=[])
    prompt = TracePromptReference(**state.prompt)
    authorized = TraceProviderCall(sequence=1, elapsed_ms=0, provider_attempt_id=first.provider_attempt_id,
        provider=first.provider, model=first.model, outcome='authorized')
    def trace_row(conn, turn_id, attempt):
        assert conn is state.conn and state.depth == 1 and turn_id == state.turn.turn_id and attempt == 1
        return state.opening_trace.trace_id, state.opening_trace.model_dump(mode='json', by_alias=True)
    def save(conn, trace):
        assert conn is state.conn and state.depth == 1
        state.opening_trace = trace
    monkeypatch.setattr(context_trace_store, '_trace_row', trace_row)
    monkeypatch.setattr(context_trace_store, '_save_trace', save)
    def query(sql, args):
        if sql == 'SELECT 1 FROM agent.turn_retry WHERE predecessor_id=%s':
            return state.leaf_query(sql, args)
        assert sql == 'SELECT payload FROM agent.turn_context_trace WHERE turn_id=%s' and args == (state.turn.turn_id,)
        return SimpleNamespace(fetchall=lambda: [(state.opening_trace.model_dump(mode='json', by_alias=True),)])
    state.conn.execute = query
    def open_request(*, event=first, raw=None, prompt_record=prompt):
        return state.service.authorize_pending_build_opening_with_prompt(state.turn.world_id,
            state.turn.conversation_id, state.turn.turn_id, expected_revision=2, expected_attempt=1,
            provider_attempt_event=event, prepared_decision_json=state.initial_request if raw is None else raw,
            trace_id=state.opening_trace.trace_id, prompt=prompt_record, authorized=authorized,
            authorize_current_access=state.authorize)
    return state, open_request, first, prompt


def test_pending_initial_opening_uses_actual_prompt_owner_and_guarded_sdk_lifecycle(monkeypatch):
    state, open_request, first, _ = pending_initial_opening_harness(monkeypatch)
    admitted, fresh, trace = open_request()
    assert fresh and admitted.revision == 3 and len(trace.observations) == 2
    assert trace.observations[0].payload_sha256 == first.envelope_sha256
    entry = t.ProviderOutcomeEventV1(kind='provider_outcome', event_id=uuid4(), sequence=1,
        provider_attempt_id=first.provider_attempt_id, outcome='sdk_entered')
    entered, fresh = state.service.enter_pending_app_page_sdk(state.turn.world_id, state.turn.conversation_id,
        state.turn.turn_id, expected_revision=3, expected_attempt=1, outcome=entry,
        prepared_request_json=state.initial_request, authorize_current_access=state.authorize)
    assert fresh and entered.revision == 4
    received = t.ProviderOutcomeEventV1(kind='provider_outcome', event_id=uuid4(), sequence=2,
        provider_attempt_id=first.provider_attempt_id, outcome='response_received')
    updated, fresh = state.service.record_pending_app_controller_outcome(state.turn.world_id, state.turn.conversation_id,
        state.turn.turn_id, expected_revision=4, expected_attempt=1, outcome=received,
        authorize_current_access=state.authorize)
    assert fresh and updated.revision == 5 and state.materialized == 0
    assert updated.graph_context_receipt.source_observation.binding is None


@pytest.mark.parametrize('failure', ['wire', 'accounting', 'prompt_binding', 'access', 'pointer', 'expiry', 'successor', 'cas_failure'])
def test_pending_initial_opening_refuses_changed_input_or_stale_claim(monkeypatch, failure):
    from datetime import timedelta
    from application_state.errors import ApplicationStateConflictError, ApplicationStateValidationError
    state, open_request, first, prompt = pending_initial_opening_harness(monkeypatch)
    raw = state.initial_request
    if failure == 'wire':
        raw += ' '
    elif failure == 'accounting':
        first = first.model_copy(update={'input_tokens': first.input_tokens + 1})
    elif failure == 'prompt_binding':
        prompt = prompt.model_copy(update={'provider_attempt_id': uuid4()})
    elif failure == 'access':
        state.denied = True
    elif failure == 'pointer':
        state.pointer = state.pointer.model_copy(update={'revision': state.pointer.revision + 2})
    elif failure == 'expiry':
        state.now += timedelta(hours=1)
    elif failure == 'successor':
        state.successor = True
    else:
        state.cas_failure = True
    with pytest.raises((ApplicationStateConflictError, ApplicationStateValidationError)):
        open_request(event=first, raw=raw, prompt_record=prompt)
    assert state.persisted == 0 and not state.opening_trace.observations


def test_pending_append_binding_returns_validated_execution_after_source_settlement():
    from application_state.agent_conversation.service import AgentConversationService
    from tests.test_build_source_free_routing import pending_work_prefix, pending_settlement
    receipt, policy = pending_execution_pair(with_source=True)
    events = pending_work_prefix(policy)
    execution = pending_execution(receipt, policy, [*events, pending_settlement(receipt, policy, events[-1])])
    bound = AgentConversationService()._bind_execution_append(receipt, execution)
    assert type(bound) is type(execution) and bound == execution and bound is not execution
    changed = execution.model_copy(update={'context_receipt_sha256': 'a' * 64})
    with pytest.raises(ValueError):
        AgentConversationService()._bind_execution_append(receipt, changed)


def pending_runtime_freeze_case():
    from types import SimpleNamespace
    from hashlib import sha256
    from application_state.agent_conversation.build_source_free import BuildSourceObservationV1, BuildConversationObservationV1
    from application_state.agent_conversation.native_context import BuildWorkContextV1
    from application_state.agent_conversation.build_intentional_response import budget_fields, semantic_routing_state, semantic_request_id, decision_instructions, WORK
    from apps.live_control_server.services.build_jev_harness import BuildJevHarness
    from apps.live_control_server.services.build_jev_driver import DriverDecisionProjection
    from apps.live_control_server.services.agent_turn_service import _turn_idempotency_key
    from tests.test_build_jev_estimated_continuations import counter
    _, policy = pending_execution_pair()
    intent = policy.action.intent
    markdown = '# Current page\nCaptured saved authoring context.'
    digest = sha256(markdown.encode()).hexdigest()
    intent = intent.model_copy(update={'primary_work': intent.primary_work.model_copy(update={'expected_content_sha256': digest})})
    request = SimpleNamespace(surface=SimpleNamespace(surface_id='build'), message=intent.message,
        client_thread_id=intent.client_thread_id, turn_id=str(uuid4()), build_write_capability=None,
        build_image_move_capture=None, build_draft_context=None, build_authored_references=None)
    source = SimpleNamespace(world_id=intent.world_id, document_id=intent.primary_work.object_id,
        revision=intent.primary_work.expected_revision, content_sha256=digest, visibility_state='internal',
        title='Current page', markdown=markdown)
    accounting = counter()
    budget = BuildJevHarness.budget(request, accounting=accounting, world_context=True, named_citations=True)
    budget['buildJevActions'].update(budget_fields(budget['buildJevActions']))
    conversation = BuildConversationObservationV1(conversation_id=uuid4(), pointer_revision=3)
    history = [{'user': f'Question {i}', 'assistant': f'Existing context {i}'} for i in range(40)]
    host = {'allowed_operations': budget['buildJevActions']['allowed_surface_operations'],
        'current_page': {'document_id': source.document_id, 'title': source.title},
        'capability_sha256': None, 'conversation_id': str(conversation.conversation_id),
        'pointer_revision': conversation.pointer_revision, 'history': history, 'working_draft': None, 'page_target': None}
    state = semantic_routing_state(request.message, host, None)
    questions = {'requested_work': {'type': 'choice', 'instructions': decision_instructions(), 'criteria': dict.fromkeys(WORK)}}
    body = {'model': 'jev-1.14.0', 'state': state, 'questions': questions}
    raw = json.dumps(body)
    projection = DriverDecisionProjection(state_json=json.dumps(state), questions_json=json.dumps(questions),
        request_id=semantic_request_id(state, world_id=intent.world_id, client_thread_id=request.client_thread_id,
            idempotency_key=_turn_idempotency_key(intent.world_id, request.turn_id)), event_sequence=0,
        prior_provider_attempt_id=None, graph_payloads=(), source_event_ids=(), section_read_ids=(),
        host_phase='select', host_interaction_json=json.dumps(host))
    basis = t.BuildSourceContextBasisV1(world_id=source.world_id, document_id=source.document_id,
        registry_revision=source.revision, content_sha256=digest, visibility='internal')
    provenance = provenance_for(BuildWorkContextV1(source_basis=basis)).model_copy(update={'surface_instance_id': intent.surface_instance_id})
    return dict(request=request, work=SimpleNamespace(build_source=source),
        view={'payloadJson': raw, 'payloadUtf8Bytes': len(raw.encode()), 'payloadSha256': sha256(raw.encode()).hexdigest(),
              'provider': 'typesafe', 'model': 'jev-1.14.0', 'apiMode': 'typesafe_decision', 'contextMode': 'default'},
        budget=budget, authority=None, native_query=None, provenance=provenance, submitted_intent=intent,
        projection=projection, accounting=accounting, included_history=[(uuid4(), row['assistant']) for row in history],
        source_observation=BuildSourceObservationV1(managed_world_id=intent.world_id, binding=None,
            requested_revision_id=None, observed_head_revision_id=None), conversation_observation=conversation)


def test_real_build_runtime_freezer_emits_pending_input_without_source_or_catalog():
    from apps.live_control_server.services.plan_source_turn import freeze_build
    from application_state.agent_conversation.native_context import BuildPendingContextReceiptV1, NativeBuildPendingProviderInputV3
    kwargs = pending_runtime_freeze_case()
    receipt, execution, membership = freeze_build(**kwargs)
    assert type(receipt) is BuildPendingContextReceiptV1 and type(receipt.assembled_input) is NativeBuildPendingProviderInputV3
    assert not hasattr(receipt, 'source_authority') and receipt.source_observation.binding is None
    assert execution.policy.action.related_page_catalog is None and not execution.events
    assert len(receipt.assembled_input.included_history) == 40 and membership == ([], [], [])
    wire = kwargs['view']['payloadJson']
    assert str(receipt.conversation_observation.conversation_id) not in wire
    assert receipt.context_receipt_sha256 not in wire


@pytest.mark.parametrize('failure', ['authority', 'catalog', 'pointer', 'world', 'partial_observation', 'wire'])
def test_real_build_runtime_freezer_rejects_crossed_or_acquired_pending_inputs(failure):
    from apps.live_control_server.services.plan_source_turn import freeze_build
    from tests.test_build_source_free_routing import settled_source
    kwargs = pending_runtime_freeze_case()
    if failure == 'authority':
        kwargs['authority'] = settled_source(managed_world_id=kwargs['submitted_intent'].world_id)
    elif failure == 'catalog':
        kwargs['budget']['buildJevActions']['related_page_catalog'] = []
    elif failure == 'pointer':
        kwargs['conversation_observation'] = kwargs['conversation_observation'].model_copy(update={'pointer_revision': 4})
    elif failure == 'world':
        kwargs['source_observation'] = kwargs['source_observation'].model_copy(update={'managed_world_id': 'foreign-world'})
    elif failure == 'partial_observation':
        kwargs['conversation_observation'] = None
    else:
        kwargs['view']['payloadJson'] += ' '
    with pytest.raises(ValueError):
        freeze_build(**kwargs)


def test_real_build_runtime_freezer_keeps_historical_shared_path_separate():
    from apps.live_control_server.services.plan_source_turn import freeze_build
    from tests.test_build_source_free_routing import settled_source
    from application_state.agent_conversation.native_context import SurfaceNativeContextReceiptV1, NativeBuildProviderInputV2
    from application_state.agent_conversation.native_plan_statements import NativePlanQueryUnavailableV1
    kwargs = pending_runtime_freeze_case()
    kwargs.pop('source_observation')
    kwargs.pop('conversation_observation')
    kwargs['authority'] = settled_source(managed_world_id=kwargs['submitted_intent'].world_id)
    kwargs['native_query'] = NativePlanQueryUnavailableV1(managed_world_id=kwargs['submitted_intent'].world_id,
        reason='native_graph_binding_unavailable')
    receipt, execution, _ = freeze_build(**kwargs)
    assert type(receipt) is SurfaceNativeContextReceiptV1 and type(receipt.assembled_input) is NativeBuildProviderInputV2
    assert receipt.source_authority == kwargs['authority']
    assert execution.policy.policy_version == 'surface_native_execution_v1'


def test_pending_budget_defers_discovery_but_preserves_actual_authoring_capabilities(monkeypatch):
    from types import SimpleNamespace
    from apps.live_control_server.services.build_jev_harness import BuildJevHarness
    from apps.live_control_server.services import build_related_pages
    from application_state.agent_conversation.build_draft_context import BuildDraftContextRequestV1
    from application_state.agent_conversation.build_intentional_response import policy_capabilities
    from tests.test_surface_native_build_work import case
    kwargs = pending_runtime_freeze_case()
    _, _, captured, *_ = case()
    request = kwargs['request']
    request.build_draft_context = BuildDraftContextRequestV1(snapshot=captured.record.snapshot,
        conversation_id=captured.record.conversation_id, expected_pointer_revision=captured.record.expected_pointer_revision)
    request.reviewed_step = None
    calls = []
    catalog = [{'title': 'Other saved page'}]
    def discover(actual):
        assert actual is request
        calls.append(actual)
        return catalog
    monkeypatch.setattr(build_related_pages, 'discover', discover)
    harness = BuildJevHarness(accounting=kwargs['accounting'], world_context=True, named_citations=True, related_pages=True)
    deferred = harness.configured_budget(request, defer_related_pages=True)
    assert not calls and 'related_page_catalog' not in deferred['buildJevActions']
    ordinary = harness.configured_budget(request)
    assert calls == [request] and ordinary['buildJevActions']['related_page_catalog'] == catalog
    assert policy_capabilities(SimpleNamespace(**deferred['buildJevActions'])) == policy_capabilities(SimpleNamespace(**ordinary['buildJevActions']))
    for key in ['collaboration_output_policy', 'connected_page_review_policy', 'relationship_review_policy', 'source_quote_binding_policy']:
        assert deferred['buildJevActions'][key] == ordinary['buildJevActions'][key]


def pending_adapter_driver_case(*, empty_pointer=False, observed=None, overrides=None):
    from types import SimpleNamespace
    from apps.live_control_server.services.agent_turn_service import _PolicyExecutionAdapter
    kwargs = pending_runtime_freeze_case()
    request = kwargs['request']
    request.primary_work = kwargs['submitted_intent'].primary_work
    request.graph_request = kwargs['submitted_intent'].graph_request
    request.reviewed_step = None
    conversation_id = kwargs['conversation_observation'].conversation_id
    pointer = t.WorldPointer(world_id=kwargs['submitted_intent'].world_id,
        active_conversation_id=None if empty_pointer else conversation_id, revision=3)
    state = SimpleNamespace(pointer=pointer, created=0, history_reads=0, access_calls=0)
    history = [{'turn_id': str(uuid4()), 'user': f'Question {i}', 'assistant': f'Existing context {i}'} for i in range(40)]
    def get_pointer(world):
        assert world == pointer.world_id
        return state.pointer
    def get_active(world):
        assert world == pointer.world_id
        return None if state.pointer.active_conversation_id is None else SimpleNamespace(conversation_id=state.pointer.active_conversation_id)
    def create(command):
        assert command.expected_pointer_revision == state.pointer.revision
        assert command.expected_active_conversation_id == state.pointer.active_conversation_id
        state.created += 1
        state.pointer = state.pointer.model_copy(update={'active_conversation_id': conversation_id, 'revision': state.pointer.revision + 1})
    def dialogue(world, conversation):
        assert world == pointer.world_id and conversation == state.pointer.active_conversation_id
        state.history_reads += 1
        return history
    def access(*args):
        state.access_calls += 1
        return True
    service = SimpleNamespace(get_world_pointer=get_pointer, get_active_conversation=get_active,
        new_conversation=create, list_build_dialogue=dialogue)
    inputs = dict(service=service, request=request, world_id=pointer.world_id, work=kwargs['work'],
        bootstrap=None, playable_target=None, submitted_intent=kwargs['submitted_intent'], existing_turn=None,
        budget=kwargs['budget'], pending_build_source_observation=kwargs['source_observation'],
        pending_build_conversation_observation=observed, pending_build_access=access)
    inputs.update(overrides or {})
    adapter = _PolicyExecutionAdapter(**inputs)
    return adapter, state


@pytest.mark.parametrize('empty_pointer', [False, True])
def test_pending_adapter_driver_prepares_full_semantic_work_without_core_or_catalog(empty_pointer):
    adapter, state = pending_adapter_driver_case(empty_pointer=empty_pointer)
    driver = adapter.create_build_jev_driver()
    assert driver._native and adapter.native_source_authority is None and adapter.bootstrap is None
    assert state.created == int(empty_pointer) and state.history_reads == 1 and state.access_calls == 0
    assert adapter.pending_build_conversation_observation.conversation_id == state.pointer.active_conversation_id
    assert adapter.pending_build_conversation_observation.pointer_revision == state.pointer.revision
    assert adapter.expected_conversation_id == state.pointer.active_conversation_id
    request = driver.step
    assert len(request.state['interaction']['history']) == 40
    assert {question.name for question in request.questions} == {'requested_work', 'source_need'}
    wire = json.dumps(request.state)
    assert str(state.pointer.active_conversation_id) not in wire
    assert 'related_page_catalog' not in wire and 'native_world_id' not in wire


@pytest.mark.parametrize('failure', ['authority', 'catalog', 'access_owner', 'source_world'])
def test_pending_adapter_refuses_acquired_or_unowned_inputs(failure):
    from tests.test_build_source_free_routing import settled_source
    kwargs = pending_runtime_freeze_case()
    overrides = {}
    if failure == 'authority':
        overrides['native_source_authority'] = settled_source(managed_world_id=kwargs['submitted_intent'].world_id)
    elif failure == 'catalog':
        kwargs['budget']['buildJevActions']['related_page_catalog'] = []
        overrides['budget'] = kwargs['budget']
    elif failure == 'access_owner':
        overrides['pending_build_access'] = None
    else:
        overrides['pending_build_source_observation'] = kwargs['source_observation'].model_copy(update={'managed_world_id': 'foreign-world'})
    with pytest.raises(ValueError):
        pending_adapter_driver_case(overrides=overrides)


def test_pending_driver_preserves_original_conversation_observation_after_reset_reopen():
    adapter, state = pending_adapter_driver_case()
    from application_state.agent_conversation.build_source_free import capture_pending_conversation
    adapter.pending_build_conversation_observation = capture_pending_conversation(state.pointer,
        world_id=state.pointer.world_id, conversation_id=state.pointer.active_conversation_id)
    state.pointer = state.pointer.model_copy(update={'revision': state.pointer.revision + 2})
    with pytest.raises(ValueError, match='original observation'):
        adapter.create_build_jev_driver()
    assert state.history_reads == 0


@pytest.mark.parametrize('capture', ['expected', 'draft', 'write', 'image'])
def test_pending_empty_pointer_rejects_stale_capture_before_conversation_creation(capture):
    from application_state.agent_conversation.build_draft_context import BuildDraftContextRequestV1
    from tests.test_surface_native_build_work import case
    adapter, state = pending_adapter_driver_case(empty_pointer=True)
    if capture == 'expected':
        adapter.expected_conversation_id = uuid4()
    elif capture == 'draft':
        _, _, record, *_ = case()
        adapter.request.build_draft_context = BuildDraftContextRequestV1(snapshot=record.record.snapshot,
            conversation_id=record.record.conversation_id, expected_pointer_revision=record.record.expected_pointer_revision)
    else:
        # These host captures are rejected before their fields can be consumed.
        setattr(adapter.request, 'build_write_capability' if capture == 'write' else 'build_image_move_capture', object())
    with pytest.raises(ValueError, match='cannot create a replacement'):
        adapter.create_build_jev_driver()
    assert state.created == state.history_reads == 0 and state.pointer.active_conversation_id is None


from contextlib import contextmanager as _pending_test_contextmanager


@_pending_test_contextmanager
def pending_transport_case(monkeypatch):
    from types import SimpleNamespace
    from datetime import UTC, datetime, timedelta
    from hashlib import sha256
    from generationengine.decision_dispatch import PreparedDecisionDispatch, DecisionContextMode
    from apps.live_control_server.services.agent_turn_service import _PolicyExecutionAdapter, _ClaimFence
    from apps.live_control_server.services.agent_context_trace_collector import ContextTraceCollector
    from apps.live_control_server.services import agent_prompt_evidence
    from apps.live_control_server.services.build_jev_dispatch import prepared_driver_view
    from apps.live_control_server.services.plan_source_turn import freeze_build
    from application_state.agent_conversation import context_trace_store
    from application_state.agent_conversation.context_trace import TurnContextTraceV1
    from tests.test_surface_native_execution import BUILD_TURN_ID
    state, _ = settlement_harness(monkeypatch, with_source=False)
    kwargs = pending_runtime_freeze_case()
    receipt, execution, _ = freeze_build(**kwargs)
    intent = kwargs['submitted_intent']
    sub = t.TurnSubmission(world_id=intent.world_id, conversation_id=receipt.conversation_observation.conversation_id,
        idempotency_key=uuid4(), expected_conversation_revision=1, user_text=intent.message,
        provenance=kwargs['provenance'], submitted_intent_v2=intent,
        graph_context_receipt=receipt, graph_context_execution=execution)
    state.turn = retained(sub, turn_id=BUILD_TURN_ID, status='running', revision=2, attempt=1,
        claim_expires_at=state.now + timedelta(minutes=2))
    state.pointer = t.WorldPointer(world_id=intent.world_id, active_conversation_id=sub.conversation_id,
        revision=receipt.conversation_observation.pointer_revision)
    state.trace = TurnContextTraceV1(trace_id=uuid4(), world_id=intent.world_id, conversation_id=sub.conversation_id,
        turn_id=BUILD_TURN_ID, attempt=1, started_at=datetime.now(UTC), execution_start_sequence=0, observations=[])
    raw = kwargs['view']['payloadJson'].encode()
    prepared = PreparedDecisionDispatch(str(uuid4()), 'typesafe', 'vercel_ai_gateway', 'jev-1.14.0',
        'POST', 'https://ai-gateway.vercel.sh/typesafe/v1/systemone', raw, sha256(raw).hexdigest(), len(raw), DecisionContextMode.DEFAULT)
    view = prepared_driver_view(prepared, kwargs['projection'], accounting=kwargs['accounting'])
    first = t.ProviderAttemptAuthorizedEventV5(kind='provider_attempt_authorized_v5', event_id=uuid4(), sequence=0,
        provider_attempt_id=UUID(prepared.attempt_id), envelope_sha256=view['payloadSha256'],
        serializer_version=view['serializerVersion'], provider=view['provider'], model=view['model'], api_mode=view['apiMode'],
        tool_schema_sha256=t.canonical_sha256([]), input_accounting_kind='estimated_token_count',
        input_estimator=kwargs['accounting'].descriptor['policy'], input_tokens=kwargs['accounting'].estimate(json.loads(raw)),
        output_token_reserve=0, included_assertion_ids=[], included_relationship_ids=[], included_evidence_ref_ids=[],
        included_graph_event_ids=[], included_source_read_event_ids=[], context_mode=view['contextMode'],
        context_phase=view['contextPhase'], max_question_input_tokens=view['maxQuestionInputTokens'],
        dispatch_identity_sha256=view['dispatchIdentitySha256'])
    def trace_row(conn, turn_id, attempt):
        assert conn is state.conn and turn_id == BUILD_TURN_ID and attempt == 1
        return state.trace.trace_id, state.trace.model_dump(mode='json', by_alias=True)
    def save(conn, trace):
        assert conn is state.conn
        state.trace = trace
    monkeypatch.setattr(context_trace_store, '_trace_row', trace_row)
    monkeypatch.setattr(context_trace_store, '_save_trace', save)
    def query(sql, args):
        if sql == 'SELECT 1 FROM agent.turn_retry WHERE predecessor_id=%s':
            return state.leaf_query(sql, args)
        assert sql == 'SELECT payload FROM agent.turn_context_trace WHERE turn_id=%s' and args == (BUILD_TURN_ID,)
        return SimpleNamespace(fetchall=lambda: [(state.trace.model_dump(mode='json', by_alias=True),)])
    state.conn.execute = query
    def prompt_store(payload, *, digest, size):
        assert payload == raw.decode() and digest == sha256(raw).hexdigest() and size == len(raw)
        return uuid4()
    monkeypatch.setattr(agent_prompt_evidence, 'store_prompt', prompt_store)
    def append_observation(*, observation, **binding):
        assert binding['turn_id'] == BUILD_TURN_ID and binding['expected_revision'] == state.turn.revision
        state.trace = TurnContextTraceV1.model_validate(state.trace.model_copy(update={
            'observations': [*state.trace.observations, observation]}))
        return state.trace
    monkeypatch.setattr(state.service, 'append_context_trace', append_observation)
    request = kwargs['request']
    request.primary_work, request.graph_request = intent.primary_work, intent.graph_request
    adapter = _PolicyExecutionAdapter(service=state.service, request=request, world_id=intent.world_id,
        work=kwargs['work'], bootstrap=None, playable_target=None, submitted_intent=intent,
        existing_turn=state.turn, budget=kwargs['budget'], pending_build_source_observation=receipt.source_observation,
        pending_build_conversation_observation=receipt.conversation_observation, pending_build_access=state.authorize)
    fence = _ClaimFence(state.service, state.turn, pending_build_access=state.authorize)
    adapter.fence = fence
    adapter.context_capture = ContextTraceCollector(fence, initial_trace=state.trace)
    adapter._prepared_build_decision = prepared
    adapter.last_provider_attempt_id = first.provider_attempt_id
    try:
        yield state, adapter, view, first
    finally:
        fence.stop()


def test_pending_transport_routes_actual_prompt_and_sdk_lifecycle_through_reviewed_owners(monkeypatch):
    with pending_transport_case(monkeypatch) as (state, adapter, view, first):
        updated, fresh = adapter.context_capture.authorize_build_opening(view, first)
        assert fresh and updated.revision == 3 and adapter.fence.turn == updated
        assert adapter.record_lifecycle({'transition': 'sdk_entered', 'runtimeApiRequestId': 'actual-sdk-attempt'})
        assert adapter.record_lifecycle({'transition': 'response_received', 'runtimeApiRequestId': 'actual-sdk-attempt'})
        assert state.turn.revision == 5 and state.persisted == 3 and state.materialized == 0
        assert [row.outcome for row in state.turn.graph_context_execution.events if isinstance(row, t.ProviderOutcomeEventV1)] == ['sdk_entered', 'response_received']
        assert adapter.context_capture.provider_attempts_by_request['actual-sdk-attempt'] == first.provider_attempt_id


def test_pending_transport_refuses_changed_prepared_bytes_before_sdk_entry(monkeypatch):
    from dataclasses import replace
    with pending_transport_case(monkeypatch) as (state, adapter, view, first):
        adapter.context_capture.authorize_build_opening(view, first)
        adapter._prepared_build_decision = replace(adapter._prepared_build_decision,
            body=adapter._prepared_build_decision.body + b' ')
        assert not adapter.record_lifecycle({'transition': 'sdk_entered'})
        assert state.persisted == 1 and adapter.failure is not None


def test_pending_transport_never_grants_sdk_entry_twice(monkeypatch):
    with pending_transport_case(monkeypatch) as (state, adapter, view, first):
        adapter.context_capture.authorize_build_opening(view, first)
        assert adapter.record_lifecycle({'transition': 'sdk_entered'})
        assert not adapter.record_lifecycle({'transition': 'sdk_entered'})
        assert state.persisted == 2


def test_pending_app_access_rechecks_live_world_owner_without_native_source_authority():
    from types import SimpleNamespace
    from application_state.agent_conversation.build_related_pages import PagePointer
    from apps.live_control_server.services.agent_turn_service import _pending_build_app_access
    state = {'allow': True, 'calls': []}
    def live(world):
        state['calls'].append(world)
        return None if state['allow'] else False
    access = _pending_build_app_access('world-one', live)
    turn = SimpleNamespace(world_id='world-one')
    page = PagePointer(world_id='world-one', document_id=uuid4(), registry_revision=1, title='Maelthor', visibility='internal')
    assert access(object(), turn, None) is True
    assert access(object(), turn, (page,)) is True
    state['allow'] = False
    assert access(object(), turn, (page,)) is False
    assert state['calls'] == ['world-one'] * 3


@pytest.mark.parametrize('kind', ['foreign_turn', 'foreign_page', 'native_source'])
def test_pending_app_access_cannot_authorize_foreign_worlds_or_core_material(kind):
    from types import SimpleNamespace
    from application_state.agent_conversation.build_related_pages import PagePointer
    from apps.live_control_server.services.agent_turn_service import _pending_build_app_access
    from tests.test_build_source_free_routing import settled_source, prepared_query
    access = _pending_build_app_access('world-one', lambda world: None)
    turn = SimpleNamespace(world_id='foreign-world' if kind == 'foreign_turn' else 'world-one')
    if kind == 'native_source':
        source = settled_source(managed_world_id='world-one')
        pages = (source, prepared_query(source))
    else:
        pages = (PagePointer(world_id='foreign-world' if kind == 'foreign_page' else 'world-one',
            document_id=uuid4(), registry_revision=1, title='Saved page', visibility='internal'),)
    assert access(object(), turn, pages) is False


def test_agent_route_injects_existing_live_conversation_authorizer(monkeypatch):
    from types import SimpleNamespace
    from pathlib import Path
    from apps.live_control_server.routes import agent as route
    from apps.live_control_server.services import hosted_native_graph_access as access_owner
    request = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace()))
    body = SimpleNamespace(turn_id=str(uuid4()))
    calls, allowed = [], {'value': True}
    def require(actual_request, world_id, *, authorize_local):
        assert actual_request is request and authorize_local is route.enforce_native_graph_gm
        calls.append(world_id)
        if not allowed['value']:
            raise PermissionError('World access was revoked')
    monkeypatch.setattr(access_owner, 'require_conversation_access', require)
    monkeypatch.setattr(route, '_chat_turn_principal', lambda *args: SimpleNamespace(subject='test-gm', role='gm'))
    monkeypatch.setattr(route, '_conversation_service', lambda request: object())
    monkeypatch.setattr(route, 'repo_root', lambda: Path('/synthetic-app'))
    monkeypatch.setattr(route, 'session_dir', lambda: Path('/synthetic-app/sessions'))
    monkeypatch.setattr(route, 'HermesSessionPointerStore', lambda path: object())
    monkeypatch.setattr(route, '_finalize_unlogged_agent_trace', lambda *args, **kwargs: None)
    def backend(actual_body, **kwargs):
        assert actual_body is body
        authorize = kwargs['authorize_build_world']
        assert authorize('world-one') is None
        allowed['value'] = False
        with pytest.raises(PermissionError):
            authorize('world-one')
        return SimpleNamespace(model_dump=lambda **kwargs: {'checked': True})
    monkeypatch.setattr(route, 'execute_agent_turn', backend)
    assert route._execute_agent_turn(body, request) == {'checked': True}
    assert calls == ['world-one', 'world-one']


def pending_startup_case():
    from types import SimpleNamespace
    kwargs = pending_runtime_freeze_case()
    request, intent = kwargs['request'], kwargs['submitted_intent']
    request.primary_work, request.graph_request = intent.primary_work, intent.graph_request
    request.retry_of = request.reviewed_step = request.selected_knowledge = request.graph_selection = None
    principal = SimpleNamespace(role='gm', managed_world_id=intent.world_id)
    return kwargs, request, principal


def test_pending_startup_observes_metadata_between_live_access_checks(monkeypatch):
    from apps.live_control_server.services.agent_turn_service import _prepare_pending_build_startup
    from apps.live_control_server.integrations.dungeonmind import native_corpus_source
    kwargs, request, principal = pending_startup_case()
    calls = []
    def authorize(world):
        calls.append(('access', world))
    def observe(**fields):
        calls.append(('metadata', fields))
        return kwargs['source_observation']
    monkeypatch.setattr(native_corpus_source, 'observe_build_source_pointer', observe)
    observed, conversation, access = _prepare_pending_build_startup(request,
        world_id=kwargs['submitted_intent'].world_id, principal=principal, durable_turn=None, authorize_world=authorize)
    assert observed == kwargs['source_observation'] and conversation is None and callable(access)
    assert [kind for kind, _ in calls] == ['access', 'metadata', 'access']
    assert calls[1][1] == {'managed_world_id': principal.managed_world_id,
        'principal': principal, 'revision_id': request.graph_request.revision_pin, 'defer_head': True}


def test_pending_startup_does_not_open_core_to_find_head():
    from types import SimpleNamespace
    from apps.live_control_server.integrations.dungeonmind.native_corpus_source import observe_build_source_pointer

    bound = SimpleNamespace(managed_world_id='managed', native_world_id='native',
                            binding_version=1, provisioning_id=None)
    principal = SimpleNamespace(role='gm', managed_world_id='managed')
    repository = SimpleNamespace(get_head=lambda *args: pytest.fail('Opening intent read Core head'))
    deferred = observe_build_source_pointer(managed_world_id='managed', principal=principal,
        repository=repository, resolve_identity=lambda _: bound, defer_head=True)
    assert deferred.deferred_head and deferred.requested_or_observed_revision is None
    pinned = observe_build_source_pointer(managed_world_id='managed', principal=principal,
        repository=repository, resolve_identity=lambda _: bound, defer_head=True, revision_id='pinned')
    assert not pinned.deferred_head and pinned.requested_or_observed_revision == 'pinned'
    assert 'deferred_head' not in pinned.model_dump(mode='json')


@pytest.mark.parametrize('reason', ['references', 'reviewed', 'selected_knowledge', 'graph_selection', 'retry', 'no_owner', 'not_gm', 'reference_image'])
def test_pending_startup_keeps_explicit_or_unowned_requests_on_their_original_path(monkeypatch, reason):
    from apps.live_control_server.services.agent_turn_service import _prepare_pending_build_startup
    from apps.live_control_server.integrations.dungeonmind import native_corpus_source
    kwargs, request, principal = pending_startup_case()
    monkeypatch.setattr(native_corpus_source, 'observe_build_source_pointer', lambda **fields: pytest.fail('Ineligible request observed a new source'))
    if reason == 'references':
        request.build_authored_references = object()
    elif reason == 'reviewed':
        request.reviewed_step = object()
    elif reason == 'selected_knowledge':
        request.selected_knowledge = object()
    elif reason == 'graph_selection':
        request.graph_selection = object()
    elif reason == 'retry':
        request.retry_of = uuid4()
    elif reason == 'not_gm':
        principal.role = 'player'
    elif reason == 'reference_image':
        from types import SimpleNamespace
        request.build_write_capability = SimpleNamespace(reference_image_id=uuid4())
    result = _prepare_pending_build_startup(request, world_id=kwargs['submitted_intent'].world_id,
        principal=principal, durable_turn=None, authorize_world=None if reason == 'no_owner' else lambda world: None)
    assert result == (None, None, None)


def test_retained_pending_startup_reuses_original_observations_without_reopening_source(monkeypatch):
    from types import SimpleNamespace
    from apps.live_control_server.services.agent_turn_service import _prepare_pending_build_startup
    from apps.live_control_server.services.plan_source_turn import freeze_build
    from apps.live_control_server.integrations.dungeonmind import native_corpus_source
    kwargs, request, principal = pending_startup_case()
    receipt, _, _ = freeze_build(**kwargs)
    monkeypatch.setattr(native_corpus_source, 'observe_build_source_pointer', lambda **fields: pytest.fail('Retained source was refreshed'))
    observed, conversation, access = _prepare_pending_build_startup(request, world_id=principal.managed_world_id,
        principal=principal, durable_turn=SimpleNamespace(graph_context_receipt=receipt), authorize_world=lambda world: None)
    assert observed == receipt.source_observation and conversation == receipt.conversation_observation and callable(access)


@pytest.mark.parametrize('deny_after_metadata', [False, True])
def test_pending_startup_refuses_denied_or_revoked_world_before_dispatch(monkeypatch, deny_after_metadata):
    from apps.live_control_server.services.agent_turn_service import _prepare_pending_build_startup, AgentTurnServiceError
    from apps.live_control_server.integrations.dungeonmind import native_corpus_source
    kwargs, request, principal = pending_startup_case()
    state = {'observed': 0}
    def observe(**fields):
        state['observed'] += 1
        return kwargs['source_observation']
    def authorize(world):
        return None if deny_after_metadata and state['observed'] == 0 else False
    monkeypatch.setattr(native_corpus_source, 'observe_build_source_pointer', observe)
    with pytest.raises(AgentTurnServiceError) as error:
        _prepare_pending_build_startup(request, world_id=principal.managed_world_id,
            principal=principal, durable_turn=None, authorize_world=authorize)
    assert error.value.status_code == 403 and state['observed'] == int(deny_after_metadata)


@pytest.mark.parametrize('reject_decision', [False, True])
def test_pending_harness_captures_actual_received_response_before_work_validation_and_closes_client(monkeypatch, reject_decision):
    import asyncio
    from types import SimpleNamespace
    from generationengine.types import DecisionResult, ChoiceDecisionAnswer, InferenceObservation
    from apps.live_control_server.services import build_jev_harness as owner
    from apps.live_control_server.services.build_jev_transitions import DecisionIntent, DecisionQuestion
    from apps.live_control_server.services.build_jev_driver import canonical
    receipt, policy = pending_execution_pair()
    response = DecisionResult(answers={'requested_work': ChoiceDecisionAnswer(
        selected='discuss', probabilities={'discuss': 1.0, 'clarify_request': 0.0})}, observation=InferenceObservation(
        provider='typesafe', resolved_model='jev-1.14.0', response_model='jev-1.14.0',
        latency_ms=1, retry_count=0, state='completed', provider_attempt_count=1))
    captured, order = [], []
    producer = uuid4()
    def capture(raw, *, producing_provider_attempt_id):
        captured.append((raw, producing_provider_attempt_id))
        order.append('capture')
    collector = SimpleNamespace(controller_decision_response=capture,
        provider_usage=lambda calls: None, observe=lambda observation: order.append('failure'))
    adapter = SimpleNamespace(trace=None, context_capture=collector,
        last_provider_attempt_id=producer, turn=object(), failure=None,
        _broker_execution=lambda: SimpleNamespace(policy=policy))
    class Client:
        async def decide(self, request):
            order.append('received')
            return response
        async def aclose(self):
            order.append('closed')
    monkeypatch.setattr(owner, 'decision_client', lambda **kwargs: Client())
    class Driver:
        step = DecisionIntent(request_id='work', phase='select', state={}, questions=(
            DecisionQuestion(name='requested_work', kind='choice', question='What work?', options=('discuss', 'clarify_request')),))
        def stage(self):
            return SimpleNamespace(state=lambda: {})
        def accept_decision(self, model, answers, *, actual_response):
            assert captured == [(canonical(response.model_dump(mode='json')), producer)]
            assert actual_response is response and model == 'jev-1.14.0'
            order.append('validate')
            if reject_decision:
                raise ValueError('decision refused')
    harness = owner.BuildJevHarness()
    harness.adapter, harness.calls, harness._inflight, harness.timings = adapter, [], {}, []
    if reject_decision:
        with pytest.raises(ValueError, match='decision refused'):
            asyncio.run(harness._decide(adapter, Driver()))
        assert order == ['received', 'capture', 'validate', 'failure', 'closed']
    else:
        asyncio.run(harness._decide(adapter, Driver()))
        assert order == ['received', 'capture', 'validate', 'closed']


@_pending_test_contextmanager
def pending_app_runtime_case(monkeypatch, *, seed=None, initial_request_json=None):
    from types import SimpleNamespace, MethodType
    from datetime import UTC, datetime
    from apps.live_control_server.services.agent_turn_service import _ClaimFence, _PolicyExecutionAdapter
    from apps.live_control_server.services.agent_context_trace_collector import ContextTraceCollector
    from application_state.agent_conversation.context_trace import TurnContextTraceV1
    from apps.live_control_server.services import agent_prompt_evidence
    from tests.test_build_jev_estimated_continuations import counter
    state = seed if seed is not None else pending_page_dispatch_harness(monkeypatch)[0]
    state.trace = TurnContextTraceV1(trace_id=uuid4(), world_id=state.turn.world_id,
        conversation_id=state.turn.conversation_id, turn_id=state.turn.turn_id, attempt=1,
        started_at=datetime.now(UTC), execution_start_sequence=0, observations=[state.prompt] if seed is None or initial_request_json is not None else [])
    def query(sql, args):
        if sql == 'SELECT 1 FROM agent.turn_retry WHERE predecessor_id=%s':
            return state.leaf_query(sql, args)
        payload = state.trace.model_dump(mode='json', by_alias=True)
        if sql == 'SELECT payload FROM agent.turn_context_trace WHERE turn_id=%s AND attempt=%s':
            assert args == (state.turn.turn_id, state.turn.attempt)
            return SimpleNamespace(fetchone=lambda: (payload,))
        assert sql == 'SELECT payload FROM agent.turn_context_trace WHERE turn_id=%s'
        assert args == (state.turn.turn_id,)
        return SimpleNamespace(fetchall=lambda: [(payload,)])
    state.conn.execute = query
    def append_observation(*, observation, **binding):
        assert binding['expected_revision'] == state.turn.revision
        state.trace = TurnContextTraceV1.model_validate(state.trace.model_copy(update={
            'observations': [*state.trace.observations, observation]}))
        state.writer_trace = state.trace.model_dump(mode='json', by_alias=True)
        return state.trace
    monkeypatch.setattr(state.service, 'append_context_trace', append_observation)
    state.prompt_payloads = {}
    def store(raw, *, digest, size, owner=None):
        assert hashlib.sha256(raw.encode()).hexdigest() == digest and len(raw.encode()) == size
        identity = uuid4()
        state.prompt_payloads[str(identity)] = raw
        return identity
    import hashlib
    monkeypatch.setattr(agent_prompt_evidence, 'store_prompt', store)
    monkeypatch.setattr(agent_prompt_evidence, 'read_prompt', lambda ref:
        (state.initial_request if seed is None else initial_request_json)
        if (seed is None or initial_request_json is not None) and str(ref.provider_attempt_id) == state.prompt['provider_attempt_id']
        else state.prompt_payloads[str(ref.evidence_id)])
    fence = _ClaimFence(state.service, state.turn, pending_build_access=state.authorize)
    adapter = SimpleNamespace(turn=state.turn, fence=fence, failure=None, trace=None,
        pending_build_access=state.authorize, rules_runtime=None,
        budget={'apiMode': 'typesafe_decision'}, _build_jev_accounting=counter(),
        request=SimpleNamespace(build_draft_context=None),
        last_provider_attempt_id=state.turn.graph_context_execution.events[0].provider_attempt_id)
    adapter._broker_receipt = lambda: fence.turn.graph_context_receipt
    adapter._broker_execution = lambda: fence.turn.graph_context_execution
    adapter._is_build_turn = lambda: True
    for name in ('record_prepared_build_decision', 'record_lifecycle', '_capture_prepared_prompt'):
        setattr(adapter, name, MethodType(getattr(_PolicyExecutionAdapter, name), adapter))
    adapter.context_capture = ContextTraceCollector(fence, initial_trace=state.trace)
    try:
        yield state, adapter
    finally:
        fence.stop()


@pytest.mark.parametrize('choice', ['read', 'skip'])
@pytest.mark.parametrize('catalog_state', ['retained', 'fresh', 'empty'])
def test_pending_app_runtime_real_sdk_admits_actual_choice_and_reads_only_selected_snapshot(monkeypatch, choice, catalog_state):
    import asyncio
    import httpx2
    from hashlib import sha256
    from apps.live_control_server.services.build_pending_app_pages import acquire_pending_app_pages
    from apps.live_control_server.services.build_jev_harness import BuildJevHarness
    from apps.live_control_server.services import build_related_pages
    from application_state.agent_conversation.build_related_pages import RelatedPageRead, RelatedPagesSelection
    monkeypatch.setenv('TYPESAFE_JEV_API_KEY', 'synthetic-only')
    calls, bodies = [], []
    class Transport(httpx2.AsyncBaseTransport):
        async def handle_async_request(self, request):
            body = json.loads(request.content)
            calls.append(body)
            return httpx2.Response(200, request=request, json={'model': body['model'],
                'usage': {'input_tokens': 23, 'output_tokens': 4}, 'answers': {
                    key: {'type': 'choice', 'choice': choice, 'confidence': 1,
                        'probabilities': {'read': float(choice == 'read'), 'skip': float(choice == 'skip')}}
                    for key in body['questions']}})
    with pending_app_runtime_case(monkeypatch) as (state, adapter):
        page = state.turn.graph_context_execution.events[-1].pages[0]
        def materialize(pointer):
            assert pointer == page
            bodies.append(pointer.document_id)
            text = 'The saved page describes Ethel and the dream password.'
            return dict(pointer.model_dump(mode='json'), content_sha256=sha256(text.encode()).hexdigest(), markdown=text)
        monkeypatch.setattr(build_related_pages, 'materialize', materialize)
        discoveries = []
        def discover(request):
            assert request is adapter.request
            discoveries.append(request)
            return [] if catalog_state == 'empty' else [page.model_dump(mode='json')]
        if catalog_state == 'retained':
            monkeypatch.setattr(build_related_pages, 'discover', lambda request: pytest.fail('Retained catalog rediscovered'))
        else:
            execution = state.turn.graph_context_execution
            execution = type(execution).model_validate_json(execution.model_copy(update={
                'events': execution.events[:-1]}).model_dump_json(by_alias=True))
            state.turn = t.Turn.model_validate(state.turn.model_copy(update={'graph_context_execution': execution}))
            adapter.fence.renewer.update_turn(state.turn)
            monkeypatch.setattr(build_related_pages, 'discover', discover)

        harness = BuildJevHarness(decision_transport=Transport())
        harness.adapter, harness.calls, harness.timings, harness._inflight = adapter, [], [], {}
        asyncio.run(acquire_pending_app_pages(adapter, harness))
        assert len(discoveries) == (0 if catalog_state == 'retained' else 1)
        if catalog_state == 'empty':
            assert not calls and not bodies and state.materialized == 0
            asyncio.run(acquire_pending_app_pages(adapter, harness))
            assert len(discoveries) == 1 and not calls and not bodies
            return
        assert len(calls) == 1 and len(calls[0]['state']['history']) == 60
        assert str(page.document_id) not in json.dumps(calls[0])
        selected, = [event for event in state.turn.graph_context_execution.events if type(event) is RelatedPagesSelection]
        assert selected.document_ids == ([page.document_id] if choice == 'read' else [])
        assert bodies == selected.document_ids
        if bodies:
            from apps.live_control_server.services.build_pending_source import prepare_pending_native_source
            # Reading a saved page is not permission for a redundant Core search.
            assert prepare_pending_native_source(adapter) is False
        assert len([event for event in state.turn.graph_context_execution.events if type(event) is RelatedPageRead]) == len(bodies)
        asyncio.run(acquire_pending_app_pages(adapter, harness))
        assert len(calls) == 1 and bodies == selected.document_ids
        assert state.materialized == 0


@pytest.mark.parametrize('failure', ['access', 'unknown'])
def test_pending_app_runtime_denied_or_unknown_dispatch_cannot_read_or_resend(monkeypatch, failure):
    import asyncio
    import httpx2
    from generationengine import GenerationEngineError
    from apps.live_control_server.services.build_pending_app_pages import acquire_pending_app_pages
    from apps.live_control_server.services.build_jev_harness import BuildJevHarness
    from apps.live_control_server.services import build_related_pages
    monkeypatch.setenv('TYPESAFE_JEV_API_KEY', 'synthetic-only')
    calls = []
    with pending_app_runtime_case(monkeypatch) as (state, adapter):
        class Transport(httpx2.AsyncBaseTransport):
            async def handle_async_request(self, request):
                calls.append(request)
                if failure == 'unknown':
                    raise httpx2.ReadTimeout('synthetic uncertain delivery', request=request)
                state.denied = True
                body = json.loads(request.content)
                return httpx2.Response(200, request=request, json={'model': body['model'], 'answers': {
                    key: {'type': 'choice', 'choice': 'read', 'confidence': 1,
                        'probabilities': {'read': 1.0, 'skip': 0.0}} for key in body['questions']}})
        monkeypatch.setattr(build_related_pages, 'materialize', lambda page: pytest.fail('Unresolved choice read a page'))
        monkeypatch.setattr(build_related_pages, 'discover', lambda request: pytest.fail('Retained catalog rediscovered'))
        harness = BuildJevHarness(decision_transport=Transport())
        harness.adapter, harness.calls, harness.timings, harness._inflight = adapter, [], [], {}
        with pytest.raises(GenerationEngineError):
            asyncio.run(acquire_pending_app_pages(adapter, harness))
        assert len(calls) == 1 and state.materialized == 0
        with pytest.raises(GenerationEngineError):
            asyncio.run(acquire_pending_app_pages(adapter, harness))
        assert len(calls) == 1 and state.materialized == 0


@pytest.mark.parametrize('label,scope', [('discuss', 'anchored'), ('clarify_request', 'uncertain'),
    ('clarify_creation', 'uncertain'), ('write_current_page', 'anchored')])
def test_pending_app_runtime_does_not_acquire_for_retained_or_source_free_work(label, scope):
    import asyncio
    from types import SimpleNamespace
    from apps.live_control_server.services.build_pending_app_pages import acquire_pending_app_pages
    from tests.test_build_source_free_routing import pending_work_prefix
    from application_state.agent_conversation.build_intentional_response import resolution_for
    receipt, policy = pending_execution_pair()
    events = pending_work_prefix(policy, scope=scope)
    work = events[-1]
    resolution = resolution_for(policy, label, source_scope=scope)
    events[-1] = type(work).model_validate(work.model_dump(mode='python') | {
        'requested_work': label, 'intent_family': resolution['intent_family'],
        'operation': resolution['operation'], 'resolution': resolution})
    execution = pending_execution(receipt, policy, events)
    adapter = SimpleNamespace(_broker_receipt=lambda: receipt, _broker_execution=lambda: execution)
    # No claim, discovery, controller, source or page-read ports are available.
    asyncio.run(acquire_pending_app_pages(adapter, object()))


@pytest.mark.parametrize('reference_image', [False, True])
def test_pending_harness_execute_routes_to_pending_completion_before_legacy_acquisition(reference_image):
    from types import SimpleNamespace
    from apps.live_control_server.services.build_jev_harness import BuildJevHarness
    receipt, _ = pending_execution_pair()
    driver = SimpleNamespace(_interaction={'history': []}, _selection_intent=None,
        selection=SimpleNamespace(typed_graph_reference=None), operation='answer_from_sources')
    routed, stopped = [], []
    adapter = SimpleNamespace(native_source_authority=None, failure=None,
        request=SimpleNamespace(build_authored_references=None, build_write_capability=SimpleNamespace(reference_image_id=uuid4()) if reference_image else None),
        create_build_jev_driver=lambda **kwargs: driver, _broker_receipt=lambda: receipt,
        stop=lambda: stopped.append(True))
    class Harness(BuildJevHarness):
        def _native_completion(self, actual_adapter, actual_driver):
            routed.append((actual_adapter, actual_driver))
            return 'pending-completion-boundary'
    from application_state.agent_conversation.rules_authority_policy import rules_capability
    adapter.pending_build_source_observation = receipt.source_observation
    adapter.enable_rules_lookup = lambda capability: pytest.fail('Pending Build activated the legacy Rules adapter')
    harness = Harness(rules_capability=rules_capability(graph=True))
    harness._capture_failure = lambda adapter, exc: None
    if reference_image:
        with pytest.raises(ValueError, match='image reference requires an edit'):
            harness.execute(adapter)
        assert not routed and stopped == [True]
    else:
        assert harness.execute(adapter) == 'pending-completion-boundary'
        assert routed == [(adapter, driver)] and stopped == [True]


@_pending_test_contextmanager
def pending_source_runtime_case(monkeypatch, *, with_source=True, local_auth=None):
    from types import SimpleNamespace
    from apps.live_control_server.services.agent_turn_service import _ClaimFence
    from apps.live_control_server.services.build_pending_source import PendingBuildSourcePreparation
    from tests.test_build_source_free_routing import settled_source, prepared_query
    state, _ = settlement_harness(monkeypatch, with_source=with_source)
    state.source_prepares, state.query_searches, state.query_reopens = [], [], []
    state.acquisition_epoch = 1
    state.source_change = state.query_change = False
    state.revoke_during_prepare = False
    observed = state.turn.graph_context_receipt.source_observation
    state.current_binding = observed.binding
    def prepare(world, principal, *, revision_id, resolve_identity):
        assert state.depth == 0 and world == state.turn.world_id
        assert resolve_identity(world) == state.current_binding
        state.source_prepares.append(revision_id)
        if state.on_prepare:
            state.on_prepare()
        if state.revoke_during_prepare:
            state.denied = True
        source = settled_source(managed_world_id=world,
            revision_id='new-head-must-not-substitute' if state.source_change else revision_id,
            acquisition_epoch=state.acquisition_epoch)
        return SimpleNamespace(authority=source), source
    def query(turn, context):
        assert state.depth == 0
        state.query_searches.append(turn.user_text)
        result = prepared_query(context.authority).model_copy(update={'question': turn.user_text})
        return SimpleNamespace(query=result), result
    def reopen(query, principal):
        assert state.depth == 0
        state.query_reopens.append(query)
        return SimpleNamespace(query=query.model_copy(update={'question': 'changed'}) if state.query_change else query)
    if local_auth is None:
        principal = SimpleNamespace(role='gm', managed_world_id=state.turn.world_id)
    else:
        from apps.live_control_server.services.agent_graph_auth import NativeGraphPrincipal
        principal = NativeGraphPrincipal(subject='local-dogfood', role='gm', auth_method=local_auth)
    owner = PendingBuildSourcePreparation(world_id=state.turn.world_id, principal=principal,
        app_access=state.authorize, prepare_source=prepare, resolve_query=query,
        resolve_identity=lambda world: state.current_binding, reopen_query=reopen)
    fence = _ClaimFence(state.service, state.turn, pending_build_access=state.authorize)
    adapter = SimpleNamespace(turn=state.turn, fence=fence,
        native_corpus_context=None, native_source_authority=None, native_query_context=None, native_query=None,
        pending_build_source_preparation=owner,
        _broker_receipt=lambda: fence.turn.graph_context_receipt,
        _broker_execution=lambda: fence.turn.graph_context_execution)
    try:
        yield state, adapter, owner
    finally:
        fence.stop()


def test_pending_source_runtime_settles_original_revision_then_reopens_without_another_search(monkeypatch):
    from apps.live_control_server.services.build_pending_source import prepare_pending_native_source
    with pending_source_runtime_case(monkeypatch) as (state, adapter, owner):
        assert prepare_pending_native_source(adapter)
        source, query = adapter.native_source_authority, adapter.native_query
        assert state.source_prepares == ['observed-revision'] and state.query_searches == [state.turn.user_text]
        assert not state.query_reopens and state.persisted == 1
        assert prepare_pending_native_source(adapter)
        assert state.source_prepares == ['observed-revision', 'observed-revision']
        assert state.query_searches == [state.turn.user_text] and state.query_reopens == [query]
        assert adapter.native_source_authority == source and adapter.native_query == query
        assert state.persisted == 1 and state.access_calls == 4 and state.depth == 0


@pytest.mark.parametrize('failure', ['binding', 'revision', 'access', 'access_after_prepare', 'pointer', 'expiry', 'cas'])
def test_pending_source_runtime_refuses_changed_scope_or_claim_before_publishing_context(monkeypatch, failure):
    from datetime import timedelta
    from application_state.errors import ApplicationStateError
    from apps.live_control_server.services.build_pending_source import prepare_pending_native_source
    with pending_source_runtime_case(monkeypatch) as (state, adapter, owner):
        if failure == 'binding':
            state.current_binding = state.current_binding.model_copy(update={'binding_version': 2})
        elif failure == 'revision':
            state.source_change = True
        elif failure == 'access':
            state.denied = True
        elif failure == 'access_after_prepare':
            state.revoke_during_prepare = True
        elif failure == 'pointer':
            state.pointer = state.pointer.model_copy(update={'revision': state.pointer.revision + 1})
        elif failure == 'expiry':
            state.now += timedelta(hours=1)
        else:
            state.cas_failure = True
        with pytest.raises((ApplicationStateError, ValueError)):
            prepare_pending_native_source(adapter)
        assert state.persisted == 0 and adapter.native_corpus_context is None
        assert adapter.native_source_authority is None and adapter.native_query_context is None and adapter.native_query is None


def test_pending_source_runtime_does_not_replace_absent_captured_scope(monkeypatch):
    from apps.live_control_server.services.build_pending_source import prepare_pending_native_source
    with pending_source_runtime_case(monkeypatch, with_source=False) as (state, adapter, owner):
        assert prepare_pending_native_source(adapter) is False
        assert not state.source_prepares and not state.query_searches and state.persisted == 0


@pytest.mark.parametrize('failure', ['query', 'binding', 'access', 'expiry', 'access_delay', 'prepare_delay', 'source', 'pointer_during', 'successor'])
def test_pending_source_runtime_reopening_refuses_mutation_revocation_or_expiry_without_search(monkeypatch, failure):
    from datetime import timedelta
    from application_state.errors import ApplicationStateError
    from apps.live_control_server.services.build_pending_source import prepare_pending_native_source
    with pending_source_runtime_case(monkeypatch) as (state, adapter, owner):
        assert prepare_pending_native_source(adapter)
        source, query = adapter.native_source_authority, adapter.native_query
        if failure == 'query':
            state.query_change = True
        elif failure == 'binding':
            state.current_binding = state.current_binding.model_copy(update={'binding_version': 2})
        elif failure == 'access':
            state.denied = True
        elif failure == 'expiry':
            state.now += timedelta(hours=1)
        elif failure == 'access_delay':
            state.access_delay_before = True
        elif failure == 'source':
            state.source_change = True
        elif failure == 'pointer_during':
            state.on_prepare = lambda: setattr(state, 'pointer', state.pointer.model_copy(
                update={'revision': state.pointer.revision + 1}))
        elif failure == 'successor':
            state.successor = True
        else:
            state.on_prepare = lambda: setattr(state, 'now', state.now + timedelta(hours=1))
        with pytest.raises((ApplicationStateError, ValueError)):
            prepare_pending_native_source(adapter)
        assert adapter.native_source_authority == source and adapter.native_query == query
        assert len(state.query_searches) == 1 and state.persisted == 1


@pytest.mark.parametrize('auth_method', ['local_operator', 'local_session'])
def test_pending_source_runtime_preserves_actual_local_principal_and_live_app_scope(monkeypatch, auth_method):
    from application_state.errors import ApplicationStateError
    from apps.live_control_server.services.build_pending_source import prepare_pending_native_source
    with pending_source_runtime_case(monkeypatch, local_auth=auth_method) as (state, adapter, owner):
        assert not hasattr(owner.principal, 'managed_world_id')
        assert prepare_pending_native_source(adapter)
        assert len(state.query_searches) == 1 and state.access_calls == 2
        state.denied = True
        with pytest.raises(ApplicationStateError):
            prepare_pending_native_source(adapter)
        assert len(state.query_searches) == 1 and state.persisted == 1


@pytest.mark.parametrize('first_epoch,next_epoch,accepted', [(1, 2, True), (2, 1, False)])
def test_pending_source_runtime_reopening_preserves_retained_authority_with_monotonic_fresh_epoch(monkeypatch, first_epoch, next_epoch, accepted):
    from apps.live_control_server.services.build_pending_source import prepare_pending_native_source
    with pending_source_runtime_case(monkeypatch) as (state, adapter, owner):
        state.acquisition_epoch = first_epoch
        assert prepare_pending_native_source(adapter)
        original = adapter.native_source_authority
        state.acquisition_epoch = next_epoch
        if accepted:
            assert prepare_pending_native_source(adapter)
            assert adapter.native_corpus_context.authority.acquisition_epoch == next_epoch
            assert adapter.native_source_authority == original
            assert adapter.native_source_authority.acquisition_epoch == first_epoch
        else:
            with pytest.raises(ValueError, match='original source authority'):
                prepare_pending_native_source(adapter)
        assert len(state.query_searches) == 1 and state.persisted == 1


def test_pending_source_runtime_optional_hosted_world_binding_cannot_authorize_another_world(monkeypatch):
    from types import SimpleNamespace
    from application_state.errors import ApplicationStateError
    from apps.live_control_server.services.build_pending_source import prepare_pending_native_source
    with pending_source_runtime_case(monkeypatch) as (state, adapter, owner):
        owner.principal = SimpleNamespace(role='gm', managed_world_id='foreign-world')
        with pytest.raises(ApplicationStateError):
            prepare_pending_native_source(adapter)
        assert not state.source_prepares and not state.query_searches and state.persisted == 0


@_pending_test_contextmanager
def pending_retained_runtime_case(monkeypatch, *, lore_page=False):
    from types import SimpleNamespace
    from apps.live_control_server.services.agent_turn_service import _ClaimFence
    from tests.test_build_retained_conversation import fixture_closure
    from application_state.agent_conversation import repository
    state, _ = settlement_harness(monkeypatch, with_source=False, scope='anchored', lore_page=lore_page)
    _, turns = fixture_closure(60)
    state.turn = t.Turn.model_validate(state.turn.model_copy(update={'sequence': 61}))
    for turn in turns:
        turn.world_id, turn.conversation_id = state.turn.world_id, state.turn.conversation_id
        turn.graph_context_execution.events = tuple(event.model_copy(update={
            'source_basis': event.source_basis.model_copy(update={'world_id': state.turn.world_id})})
            for event in turn.graph_context_execution.events)
    state.retained_reads, state.on_capture = 0, None
    def rows(conn, turn):
        assert state.depth == 1 and conn is state.conn and turn == state.turn
        state.retained_reads += 1
        if state.on_capture:
            state.on_capture()
        return turns, None
    monkeypatch.setattr(repository, 'list_retained_build_turns', rows)
    fence = _ClaimFence(state.service, state.turn, pending_build_access=state.authorize)
    adapter = SimpleNamespace(turn=state.turn, fence=fence, pending_build_access=state.authorize,
        _broker_receipt=lambda: fence.turn.graph_context_receipt,
        _broker_execution=lambda: fence.turn.graph_context_execution)
    try:
        yield state, adapter, turns
    finally:
        fence.stop()


def test_pending_retained_runtime_freezes_full_existing_context_without_search_and_reuses_closure(monkeypatch):
    import asyncio
    from apps.live_control_server.services.build_pending_retained import admit_pending_conversation
    from apps.live_control_server.services.build_pending_app_pages import acquire_pending_app_pages
    from apps.live_control_server.services.build_pending_source import prepare_pending_native_source
    from application_state.agent_conversation.retained_conversation import admission, dialogue_messages, authored_frame
    from application_state.agent_conversation.writer_evidence_selection import native_conversation_terminal
    with pending_retained_runtime_case(monkeypatch) as (state, adapter, turns):
        assert admit_pending_conversation(adapter)
        value = admission(state.turn.graph_context_execution)
        assert type(value) is t.BuildPriorBodyEvidenceAdmittedV3 and len(value.history) == 60
        assert len(value.authored_context) == 1 and len(value.authored_context[0].occurrences) == 2
        messages = dialogue_messages(state.turn.graph_context_execution)
        assert len(messages) == 120 and 'Constraint 0' in messages[0]['content']
        assert 'Correction:' in messages[-2]['content']
        visible = json.dumps([messages, authored_frame(state.turn.graph_context_execution)])
        assert str(state.turn.turn_id) not in visible and str(state.turn.conversation_id) not in visible
        assert native_conversation_terminal(state.turn) == {'status': 'ready', 'reason': 'native_discussion_from_conversation'}
        asyncio.run(acquire_pending_app_pages(adapter, object()))
        assert prepare_pending_native_source(adapter) is False
        assert admit_pending_conversation(adapter)
        assert state.retained_reads == state.persisted == 1 and state.materialized == 0
        assert state.locks == ['world', 'conversation', 'turn'] * 2 and state.access_calls == 3


@pytest.mark.parametrize('failure', ['pointer', 'expiry', 'access', 'successor', 'access_after', 'expiry_after', 'cas'])
def test_pending_retained_runtime_refuses_lost_claim_access_or_pointer_without_admitting_context(monkeypatch, failure):
    from datetime import timedelta
    from application_state.errors import ApplicationStateError
    from apps.live_control_server.services.build_pending_retained import admit_pending_conversation
    with pending_retained_runtime_case(monkeypatch) as (state, adapter, turns):
        if failure == 'pointer':
            state.pointer = state.pointer.model_copy(update={'revision': state.pointer.revision + 1})
        elif failure == 'expiry':
            state.now += timedelta(hours=1)
        elif failure == 'access':
            state.denied = True
        elif failure == 'successor':
            state.successor = True
        elif failure == 'access_after':
            state.on_capture = lambda: setattr(state, 'denied', True)
        elif failure == 'expiry_after':
            state.on_capture = lambda: setattr(state, 'now', state.now + timedelta(hours=1))
        else:
            state.cas_failure = True
        with pytest.raises(ApplicationStateError):
            admit_pending_conversation(adapter)
        assert state.persisted == 0 and state.materialized == 0
        assert not any(type(event) is t.BuildPriorBodyEvidenceAdmittedV3 for event in state.turn.graph_context_execution.events)


@pytest.mark.parametrize('field', ['turn_id', 'conversation_id', 'attempt', 'conversation_sequence', 'pointer_revision'])
def test_pending_retained_stored_turn_cannot_borrow_another_closure_identity(monkeypatch, field):
    from apps.live_control_server.services.build_pending_retained import admit_pending_conversation
    with pending_retained_runtime_case(monkeypatch) as (state, adapter, turns):
        admit_pending_conversation(adapter)
        execution = state.turn.graph_context_execution
        event = execution.events[-1]
        value = uuid4() if field in {'turn_id', 'conversation_id'} else getattr(event, field) + 1
        changed = event.model_copy(update={field: value})
        execution = execution.model_copy(update={'events': [*execution.events[:-1], changed]})
        with pytest.raises(ValidationError):
            t.Turn.model_validate_json(state.turn.model_copy(update={'graph_context_execution': execution}).model_dump_json(by_alias=True))


def test_pending_retained_admission_blocks_generic_append_and_new_catalog_acquisition(monkeypatch):
    from application_state.errors import ApplicationStateError
    from apps.live_control_server.services.build_pending_retained import admit_pending_conversation
    from application_state.agent_conversation.build_source_free import pending_source_work
    with pending_retained_runtime_case(monkeypatch) as (state, adapter, turns):
        admit_pending_conversation(adapter)
        event = state.turn.graph_context_execution.events[-1]
        with pytest.raises(ValueError, match='cannot acquire another source'):
            pending_source_work(state.turn.graph_context_execution)
        with pytest.raises(ApplicationStateError):
            state.service._append_graph_execution_event(state.turn.world_id, state.turn.conversation_id,
                state.turn.turn_id, expected_revision=state.turn.revision, expected_attempt=1,
                event=event, duplicate_key='event_id')
        with pytest.raises(ApplicationStateError):
            state.service.observe_pending_build_app_catalog(state.turn.world_id, state.turn.conversation_id,
                state.turn.turn_id, expected_revision=state.turn.revision, expected_attempt=1, event_id=uuid4(),
                discover_pages=lambda turn: pytest.fail('Retained context acquired a new catalog'),
                authorize_current_access=state.authorize)
        assert state.persisted == 1 and state.retained_reads == 1 and state.materialized == 0


def test_pending_retained_lookup_cannot_admit_conversation_as_a_lookup_substitute(monkeypatch):
    from application_state.errors import ApplicationStateError
    from apps.live_control_server.services.build_pending_retained import admit_pending_conversation
    with pending_source_runtime_case(monkeypatch) as (state, adapter, owner):
        assert admit_pending_conversation(adapter) is False
        with pytest.raises(ApplicationStateError):
            state.service.admit_pending_build_prior_body_evidence(state.turn.world_id,
                state.turn.conversation_id, state.turn.turn_id,
                expected_revision=state.turn.revision, expected_attempt=1, event_id=uuid4(),
                authorize_current_access=state.authorize)
        assert state.persisted == 0 and state.materialized == 0


def test_pending_retained_capture_refuses_foreign_history_and_conflicting_duplicate(monkeypatch):
    from application_state.errors import ApplicationStateError
    from apps.live_control_server.services.build_pending_retained import admit_pending_conversation
    with pending_retained_runtime_case(monkeypatch) as (state, adapter, turns):
        turns[0].world_id = 'foreign-world'
        with pytest.raises(ApplicationStateError):
            admit_pending_conversation(adapter)
        assert state.persisted == 0
        turns[0].world_id = state.turn.world_id
        admit_pending_conversation(adapter)
        with pytest.raises(ApplicationStateError):
            state.service.admit_pending_build_prior_body_evidence(state.turn.world_id,
                state.turn.conversation_id, state.turn.turn_id,
                expected_revision=state.turn.revision, expected_attempt=1, event_id=uuid4(),
                authorize_current_access=state.authorize)
        assert state.persisted == 1 and state.retained_reads == 2


@_pending_test_contextmanager
def pending_writer_runtime_case(monkeypatch, *, source_free_work=None, lore_page=False, app_pages=False):
    from types import SimpleNamespace
    from apps.live_control_server.services.build_pending_retained import admit_pending_conversation
    from apps.live_control_server.services.build_jev_writer_selection import WriterSelectionDriver
    from application_state.agent_conversation.writer_evidence_selection import native_conversation_terminal
    seed = pending_app_writer_seed if app_pages else pending_retained_runtime_case
    with seed(monkeypatch, lore_page=lore_page) as (state, adapter, turns):
        if app_pages:
            pass
        elif source_free_work is None:
            admit_pending_conversation(adapter)
        else:
            from application_state.agent_conversation.build_intentional_response import resolution_for, operation_id_for, digest
            execution = state.turn.graph_context_execution
            work = execution.events[-1]
            resolution = resolution_for(execution.policy, source_free_work, source_scope='source_lookup')
            work = work.model_copy(update={'requested_work': source_free_work,
                'resolution': resolution, 'intent_family': resolution['intent_family'],
                'operation': resolution['operation'],
                'broker_operation_id': operation_id_for(state.turn.turn_id, state.turn.attempt, work.machine_request_id, source_free_work),
                'arguments_sha256': digest({'instruction': state.turn.user_text} if resolution['operation'] != 'answer_from_sources' else {})})
            execution = pending_execution(state.turn.graph_context_receipt, execution.policy,
                [*execution.events[:-1], work])
            state.turn = t.Turn.model_validate(state.turn.model_copy(update={'graph_context_execution': execution}))
            adapter.turn = state.turn
            adapter.fence.renewer.update_turn(state.turn)
        trace = {'world_id': state.turn.world_id, 'conversation_id': str(state.turn.conversation_id),
            'turn_id': str(state.turn.turn_id), 'attempt': state.turn.attempt, 'capture_status': 'recording', 'observations': []}
        def query(sql, args):
            if sql == 'SELECT 1 FROM agent.turn_retry WHERE predecessor_id=%s':
                return state.leaf_query(sql, args)
            assert sql == 'SELECT payload FROM agent.turn_context_trace WHERE turn_id=%s AND attempt=%s'
            assert args == (state.turn.turn_id, state.turn.attempt)
            return SimpleNamespace(fetchone=lambda: (trace,))
        state.conn.execute = query
        state.writer_trace = trace
        adapter.context_capture = SimpleNamespace(trace=SimpleNamespace(model_dump=lambda **kwargs: trace))
        adapter.last_provider_attempt_id = next(row.provider_attempt_id for row in reversed(state.turn.graph_context_execution.events)
            if isinstance(row,t.ProviderAttemptAuthorizedEventV3))
        from application_state.agent_conversation.writer_evidence_selection import native_work_terminal
        terminal = native_work_terminal(state.turn)
        selector = WriterSelectionDriver(adapter, SimpleNamespace(_material=lambda: ((), (), ())), terminal)
        yield state, adapter, selector, turns


def test_pending_writer_closes_empty_acquired_catalog_and_constructs_full_retained_input(monkeypatch):
    from types import SimpleNamespace
    from apps.live_control_server.services.plan_jev_writer import PlanJevWriter
    from application_state.agent_conversation.rules_authority_plan_packet import PlanRulesEvidenceFrameV1
    from application_state.agent_conversation.native_writer import model_frame
    with pending_writer_runtime_case(monkeypatch) as (state, adapter, selector, turns):
        assert not selector.catalog
        selection = selector.settle_empty()
        assert selection.mode == 'empty_catalog' and selection.expanded_unit_ids == []
        rules_frame = PlanRulesEvidenceFrameV1(schema='dmb_plan_rules_evidence_v1', ruleset='synthetic', lookups=(), supports=())
        rules = SimpleNamespace(frame=lambda: rules_frame, authoring=None)
        writer = PlanJevWriter(adapter, {}, rules)
        assert writer.shared
        dialogue = [json.loads(message['content']) for message in writer.messages
                    if 'conversation_turn' in json.loads(message['content'])]
        assert len(dialogue) == 120
        assert dialogue[0]['conversation'] == turns[0].user_text
        assert dialogue[-2]['conversation'] == turns[-1].user_text
        assert 'Correction:' in dialogue[-2]['conversation']
        rendered = json.dumps(writer.messages)
        assert 'Ashbell has three bridges' in rendered
        for value in (str(state.turn.turn_id), str(state.turn.conversation_id),
                state.turn.graph_context_receipt.context_receipt_sha256,
                str(turns[0].graph_context_execution.events[0].source_basis.document_id)):
            assert value not in rendered
        frame = model_frame(state.turn.graph_context_receipt, state.turn.graph_context_execution)
        assert frame['native_body_evidence']['source_authority_status'] == 'not_prepared'
        assert frame['native_statements']['status'] == 'not_prepared'
        assert frame['native_body_evidence']['coverage']['search_performed'] is False
        assert state.persisted == 2 and state.retained_reads == 1 and state.materialized == 0


@pytest.mark.parametrize('failure', ['catalog', 'basis', 'controller', 'terminal', 'invented_read',
    'mode', 'proof', 'trace_world', 'access', 'expiry', 'cas'])
def test_pending_writer_selection_refuses_changed_proof_or_lost_access_claim(monkeypatch, failure):
    from datetime import timedelta
    from application_state.errors import ApplicationStateError
    with pending_writer_runtime_case(monkeypatch) as (state, adapter, selector, turns):
        original = state.service.record_pending_build_writer_selection
        def record(*args, selection, **kwargs):
            if failure == 'catalog':
                selection = selection.model_copy(update={'catalog_sha256': 'b' * 64})
            elif failure == 'basis':
                selection = selection.model_copy(update={'basis_sha256': 'b' * 64})
            elif failure == 'controller':
                selection = selection.model_copy(update={'controller_attempt_id': uuid4()})
            elif failure == 'terminal':
                selection = selection.model_copy(update={'terminal_disposition': {'status': 'ready', 'reason': 'invented'}})
            elif failure == 'invented_read':
                selection = selection.model_copy(update={'source_event_ids': [uuid4()]})
            elif failure == 'mode':
                selection = selection.model_copy(update={'mode': 'jev'})
            elif failure == 'proof':
                kwargs['producer_proof'] = {}
            elif failure == 'trace_world':
                state.writer_trace['world_id'] = 'foreign-world'
            elif failure == 'access':
                state.denied = True
            elif failure == 'expiry':
                state.now += timedelta(hours=1)
            else:
                state.cas_failure = True
            return original(*args, selection=selection, **kwargs)
        monkeypatch.setattr(state.service, 'record_pending_build_writer_selection', record)
        with pytest.raises(ApplicationStateError):
            selector.settle_empty()
        assert state.persisted == 1 and state.retained_reads == 1 and state.materialized == 0
        assert not any(type(event) is t.BuildWriterEvidenceSelectionV2 for event in state.turn.graph_context_execution.events)


def test_pending_writer_projection_refuses_historical_schema_or_foreign_work_provenance(monkeypatch):
    from application_state.agent_conversation.native_writer import model_frame, model_work_frame, LEGACY_SCHEMA
    with pending_writer_runtime_case(monkeypatch) as (state, adapter, selector, turns):
        selector.settle_empty()
        receipt, execution = state.turn.graph_context_receipt, state.turn.graph_context_execution
        with pytest.raises(ValueError, match='historical writer'):
            model_frame(receipt, execution, schema=LEGACY_SCHEMA)
        provenance = state.turn.provenance.model_copy(update={'world_id': 'foreign-world'})
        with pytest.raises(ValueError):
            model_work_frame(receipt, execution, provenance=provenance, idempotency_key=state.turn.idempotency_key,
                work_proof={}, world_id=state.turn.world_id, conversation_id=state.turn.conversation_id,
                turn_id=state.turn.turn_id, attempt=state.turn.attempt)


def test_pending_writer_selection_cannot_use_generic_append(monkeypatch):
    from application_state.errors import ApplicationStateError
    with pending_writer_runtime_case(monkeypatch) as (state, adapter, selector, turns):
        event = selector.settle_empty()
        with pytest.raises(ApplicationStateError):
            state.service._append_graph_execution_event(state.turn.world_id, state.turn.conversation_id,
                state.turn.turn_id, expected_revision=state.turn.revision, expected_attempt=1,
                event=event, duplicate_key='event_id')
        assert state.persisted == 2 and state.materialized == 0


@pytest.mark.parametrize('field,value', [('expected_attempt', True), ('expected_attempt', 0),
    ('expected_attempt', '1'), ('expected_revision', True), ('expected_revision', 0), ('expected_revision', 3.0)])
def test_pending_writer_selection_requires_strict_positive_claim_integers_before_io(monkeypatch, field, value):
    from application_state.errors import ApplicationStateValidationError
    with pending_writer_runtime_case(monkeypatch) as (state, adapter, selector, turns):
        original = state.service.record_pending_build_writer_selection
        before = (state.access_calls, list(state.locks), state.persisted)
        def record(*args, **kwargs):
            kwargs[field] = value
            return original(*args, **kwargs)
        monkeypatch.setattr(state.service, 'record_pending_build_writer_selection', record)
        with pytest.raises(ApplicationStateValidationError):
            selector.settle_empty()
        assert (state.access_calls, state.locks, state.persisted) == before
        assert state.depth == 0


@_pending_test_contextmanager
def pending_rules_runtime_case(monkeypatch, *, source_free_work=None, lore_page=False, app_pages=False):
    from types import SimpleNamespace
    from apps.live_control_server.services.agent_turn_service import _turn_idempotency_key
    from apps.live_control_server.services.plan_jev_rules_runtime import PlanRulesRuntime
    from application_state.agent_conversation.rules_authority_policy import rules_capability
    with pending_writer_runtime_case(monkeypatch, source_free_work=source_free_work, lore_page=lore_page, app_pages=app_pages) as (state, adapter, selector, turns):
        request_id = str(uuid4())
        adapter.request = SimpleNamespace(turn_id=request_id, surface=SimpleNamespace(surface_id='build'))
        adapter.world_id, adapter.expected_conversation_id = state.turn.world_id, None
        adapter.submitted_intent = state.turn.graph_context_execution.policy.action.intent
        adapter.rules_runtime = None
        adapter.service = state.service
        adapter._is_build_turn = lambda: True
        state.turn = t.Turn.model_validate(state.turn.model_copy(update={
            'idempotency_key': _turn_idempotency_key(state.turn.world_id, request_id)}))
        adapter.turn = state.turn
        adapter.fence.renewer.update_turn(state.turn)
        configure_pending_rules_storage(state)
        runtime = PlanRulesRuntime(adapter, rules_capability(graph=True))
        yield state, adapter, runtime


def test_pending_rules_runtime_uses_real_ledger_scope_and_frame_without_lookup_or_source(monkeypatch):
    with pending_rules_runtime_case(monkeypatch) as (state, adapter, runtime):
        frame = runtime.frame()
        assert not frame.lookups and not frame.supports
        scope = runtime.native.record.execution.scope
        assert (scope.world_id, scope.conversation_id, scope.turn_id, scope.product_attempt) == (
            state.turn.world_id, state.turn.conversation_id, state.turn.turn_id, state.turn.attempt)
        assert not runtime.native.record.execution.events
        assert state.rules_inserts == state.rules_locks == 1
        assert runtime.frame() == frame and state.rules_inserts == 1
        assert state.persisted == 1 and state.materialized == 0
        assert adapter.rules_runtime is runtime


@pytest.mark.parametrize('failure', ['expiry', 'revision', 'idempotency', 'attempt', 'fingerprint'])
def test_pending_rules_runtime_refuses_stale_or_crossed_parent_before_ledger_creation(monkeypatch, failure):
    from datetime import timedelta
    from application_state.errors import ApplicationStateError
    with pending_rules_runtime_case(monkeypatch) as (state, adapter, runtime):
        if failure == 'expiry':
            state.now += timedelta(hours=1)
        elif failure == 'revision':
            state.turn = state.turn.model_copy(update={'revision': state.turn.revision + 1})
        elif failure == 'idempotency':
            adapter.fence.renewer.update_turn(state.turn.model_copy(update={'idempotency_key': uuid4()}))
        elif failure == 'attempt':
            adapter.fence.renewer.update_turn(state.turn.model_copy(update={'attempt': 2}))
        else:
            adapter.fence.renewer.update_turn(state.turn.model_copy(update={'submitted_intent_fingerprint_v2': 'f' * 64}))
        with pytest.raises((ApplicationStateError, ValueError)):
            runtime.frame()
        assert state.rules_inserts == 0 and state.materialized == 0 and state.persisted == 1


@_pending_test_contextmanager
def pending_writer_dispatch_case(monkeypatch, *, source_free_work=None, lore_page=False, app_pages=False):
    import asyncio
    import httpx
    from datetime import UTC, datetime
    from hashlib import sha256
    from types import MethodType
    from openai import AsyncOpenAI
    from generationengine.text_dispatch import PreparedTextDispatch
    from apps.live_control_server.services.plan_jev_writer import PlanJevWriter
    from apps.live_control_server.services.build_jev_writer_selection import WriterSelectionDriver
    from apps.live_control_server.services.agent_turn_service import _PolicyExecutionAdapter
    from apps.live_control_server.services.agent_context_trace_collector import ContextTraceCollector
    from apps.live_control_server.services import agent_prompt_evidence
    from application_state.agent_conversation.context_trace import TurnContextTraceV1
    from application_state.agent_conversation.writer_evidence_selection import native_work_terminal
    from application_state.agent_conversation.native_writer import output_request_fields
    from tests.test_build_jev_estimated_continuations import counter
    with pending_rules_runtime_case(monkeypatch, source_free_work=source_free_work, lore_page=lore_page, app_pages=app_pages) as (state, adapter, rules):
        adapter.budget = {'estimator': state.turn.graph_context_execution.policy.provider_input_accounting.estimator,
            'apiMode': 'typesafe_decision'}
        adapter.trace, adapter.failure = None, None
        adapter._build_jev_accounting = counter()
        rules.frame()
        selector = WriterSelectionDriver(adapter, type('Material', (), {'_material': lambda self: ((), (), ())})(),
            native_work_terminal(state.turn))
        selector.settle_empty()
        trace = TurnContextTraceV1(trace_id=uuid4(), world_id=state.turn.world_id,
            conversation_id=state.turn.conversation_id, turn_id=state.turn.turn_id, attempt=state.turn.attempt,
            started_at=datetime.now(UTC), execution_start_sequence=0, observations=[])
        def append_observation(*, observation, **binding):
            nonlocal trace
            assert binding['expected_revision'] == state.turn.revision
            trace = TurnContextTraceV1.model_validate(trace.model_copy(update={
                'observations': [*trace.observations, observation]}))
            state.writer_trace = trace.model_dump(mode='json', by_alias=True)
            return trace
        monkeypatch.setattr(state.service, 'append_context_trace', append_observation)
        monkeypatch.setattr(agent_prompt_evidence, 'store_prompt', lambda raw, **kwargs: uuid4())
        adapter.context_capture = ContextTraceCollector(adapter.fence, initial_trace=trace)
        for name in ('record_lifecycle', '_capture_prepared_prompt', 'stop'):
            setattr(adapter, name, MethodType(getattr(_PolicyExecutionAdapter, name), adapter))
        writer = PlanJevWriter(adapter, {}, rules, dialogue=getattr(adapter, 'app_test_dialogue', ()))
        body = {'model': writer.model, 'input': writer.messages, 'instructions': writer.instructions,
            **output_request_fields(writer.output_reserve), 'text': {'format': writer.output_format},
            'tools': [], 'stream': False, 'reasoning': {'effort': writer.reasoning_effort}, 'service_tier': 'fast'}
        async def serialize():
            wire = []
            def response(request):
                wire.append(request.content)
                return httpx.Response(200, request=request, json={'id': 'resp_synthetic', 'object': 'response',
                    'created_at': 1, 'model': writer.model, 'status': 'completed', 'output': []})
            async with AsyncOpenAI(api_key='synthetic', http_client=httpx.AsyncClient(
                    transport=httpx.MockTransport(response))) as client:
                await client.responses.create(**body)
            assert len(wire) == 1
            return wire[0]
        raw = asyncio.run(serialize())
        prepared = PreparedTextDispatch(str(uuid4()), 'openai', 'responses', writer.model, 'POST',
            'https://api.openai.com/v1/responses', raw, sha256(raw).hexdigest(), len(raw))
        yield state, adapter, rules, writer, prepared


def test_pending_writer_dispatch_binds_actual_sdk_bytes_and_rules_then_grants_entry_once(monkeypatch):
    from types import SimpleNamespace
    from application_state.agent_conversation.native_writer import verify_input_records
    with pending_writer_dispatch_case(monkeypatch) as (state, adapter, rules, writer, prepared):
        assert writer.authorize(prepared)
        assert state.rules_revision == 2 and state.persisted == 3
        events = state.rules_payload['events']
        assert [event['kind'] for event in events] == ['provider_authorized', 'provider_included']
        evidence = verify_input_records(state.turn.graph_context_receipt, state.turn.graph_context_execution,
            writer.authorization, prepared.body.decode(), provenance=state.turn.provenance,
            idempotency_key=state.turn.idempotency_key, work_proof={}, world_id=state.turn.world_id,
            conversation_id=state.turn.conversation_id, turn_id=state.turn.turn_id, attempt=state.turn.attempt)
        assert evidence.work_frame['retained_authored_context']
        entered = SimpleNamespace(request=prepared, outcome='sending', http_status=None)
        assert writer.record(entered)
        assert not writer.record(entered)
        assert state.materialized == 0
        assert state.rules_payload['events'][-1]['kind'] == 'provider_included'


@pytest.mark.parametrize('failure', ['omitted_history', 'changed_history', 'changed_work', 'read_inventory',
    'work_hash', 'capture', 'rules_revision', 'access', 'expiry', 'claim_attempt'])
def test_pending_writer_dispatch_refuses_altered_input_or_lost_authority_before_sdk_entry(monkeypatch, failure):
    from dataclasses import replace
    from datetime import timedelta
    from hashlib import sha256
    from application_state.errors import ApplicationStateError
    with pending_writer_dispatch_case(monkeypatch) as (state, adapter, rules, writer, prepared):
        if failure in {'omitted_history', 'changed_history', 'changed_work'}:
            body = json.loads(prepared.body)
            messages = body['input']
            if failure in {'omitted_history', 'changed_history'}:
                index = next(index for index, row in enumerate(messages)
                    if 'conversation_turn' in json.loads(row['content']))
                if failure == 'omitted_history':
                    messages.pop(index)
                else:
                    value = json.loads(messages[index]['content'])
                    value['conversation'] = 'Invented replacement history'
                    messages[index]['content'] = json.dumps(value)
            else:
                index = next(index for index, row in enumerate(messages) if 'build_work' in json.loads(row['content']))
                value = json.loads(messages[index]['content'])
                value['build_work']['retained_authored_context'] = []
                messages[index]['content'] = json.dumps(value)
            writer.messages = messages
            raw = json.dumps(body).encode()
            prepared = replace(prepared, body=raw, body_sha256=sha256(raw).hexdigest(), body_size=len(raw))
        elif failure in {'read_inventory', 'work_hash', 'claim_attempt'}:
            original = state.service.authorize_pending_build_writer
            def admit(*args, authorization, **kwargs):
                if failure == 'read_inventory':
                    authorization = authorization.model_copy(update={'native_read_event_ids': ()})
                elif failure == 'work_hash':
                    authorization = authorization.model_copy(update={'work_frame_sha256': 'b' * 64})
                else:
                    kwargs['expected_attempt'] = True
                return original(*args, authorization=authorization, **kwargs)
            monkeypatch.setattr(state.service, 'authorize_pending_build_writer', admit)
        elif failure == 'capture':
            state.capture_status = 'paused'
        elif failure == 'rules_revision':
            state.rules_revision += 1
        elif failure == 'access':
            state.denied = True
        else:
            state.now += timedelta(hours=1)
        with pytest.raises((ApplicationStateError, ValueError)):
            writer.authorize(prepared)
        assert writer.prepared is None and state.persisted == 2 and state.materialized == 0
        assert not any(getattr(event, 'kind', None) == 'native_build_writer_authorized_v2'
            for event in state.turn.graph_context_execution.events)


@pytest.mark.parametrize('failure', ['bytes', 'access', 'expiry'])
def test_pending_writer_sdk_entry_refuses_changed_bytes_or_lost_live_claim(monkeypatch, failure):
    from dataclasses import replace
    from datetime import timedelta
    from types import SimpleNamespace
    with pending_writer_dispatch_case(monkeypatch) as (state, adapter, rules, writer, prepared):
        assert writer.authorize(prepared)
        if failure == 'bytes':
            adapter._prepared_build_writer = replace(prepared, body=prepared.body + b' ')
        elif failure == 'access':
            state.denied = True
        else:
            state.now += timedelta(hours=1)
        assert not writer.record(SimpleNamespace(request=prepared, outcome='sending', http_status=None))
        assert state.persisted == 3 and state.materialized == 0
        assert not any(getattr(event, 'outcome', None) == 'sdk_entered'
            and event.provider_attempt_id == writer.authorization.provider_attempt_id
            for event in state.turn.graph_context_execution.events)


def test_pending_writer_rules_input_cannot_bypass_atomic_owner_or_reopen_acquisition(monkeypatch):
    from application_state.errors import ApplicationStateError
    from application_state.agent_conversation.rules_authority_events import RulesProviderAuthorizedV1
    from application_state.agent_conversation.rules_authority_store import require_open_plan_jev_acquisition_locked
    from application_state.agent_conversation import repository
    with pending_writer_dispatch_case(monkeypatch) as (state, adapter, rules, writer, prepared):
        scope = rules.native.record.execution.scope
        event = RulesProviderAuthorizedV1(kind='provider_authorized', event_id=uuid4(), sequence=0,
            execution_id=scope.execution_id, provider_attempt_id=uuid4(), request_envelope_sha256=prepared.body_sha256,
            matched_outputs=(), declared_support_refs=())
        with pytest.raises(ApplicationStateError, match='atomic admission'):
            state.service.append_rules_provider_event(scope, expected_turn_revision=state.turn.revision,
                expected_ledger_revision=1, event=event, prepared_request_json=prepared.body.decode())
        assert state.rules_revision == 1 and state.persisted == 2
        assert writer.authorize(prepared)
        monkeypatch.setattr(repository, 'get_turn', lambda conn, world, turn_id: state.turn)
        with pytest.raises(ApplicationStateError, match='closes Rules acquisition'):
            require_open_plan_jev_acquisition_locked(state.conn, scope)


def test_pending_writer_unknown_transport_stays_durable_and_cannot_dispatch_again(monkeypatch):
    from types import SimpleNamespace
    with pending_writer_dispatch_case(monkeypatch) as (state, adapter, rules, writer, prepared):
        assert writer.authorize(prepared)
        assert writer.record(SimpleNamespace(request=prepared, outcome='sending', http_status=None))
        assert writer.record(SimpleNamespace(request=prepared, outcome='outcome_unknown', http_status=None))
        assert [event.outcome for event in state.turn.graph_context_execution.events
            if isinstance(event, t.ProviderOutcomeEventV1)
            and event.provider_attempt_id == writer.authorization.provider_attempt_id] == ['sdk_entered', 'outcome_unknown']
        assert state.rules_payload['events'][-1]['status'] == 'unknown'
        assert not writer.record(SimpleNamespace(request=prepared, outcome='sending', http_status=None))
        assert not writer.authorize(prepared)
        assert state.materialized == 0 and state.turn.assistant_text is None and state.turn.completion is None


def test_pending_writer_rules_cas_failure_never_admits_or_dispatches_writer(monkeypatch):
    from application_state.errors import ApplicationStateError
    with pending_writer_dispatch_case(monkeypatch) as (state, adapter, rules, writer, prepared):
        state.rules_cas_failure = True
        with pytest.raises(ApplicationStateError, match='Rules provider ledger CAS'):
            writer.authorize(prepared)
        assert state.persisted == 2 and state.rules_revision == 1
        assert writer.prepared is None and state.materialized == 0


def test_pending_writer_actual_serialized_request_omits_host_bindings_and_preserves_all_dialogue(monkeypatch):
    with pending_writer_dispatch_case(monkeypatch) as (state, adapter, rules, writer, prepared):
        body = json.loads(prepared.body)
        dialogue = [json.loads(row['content']) for row in body['input']
            if 'conversation_turn' in json.loads(row['content'])]
        assert len(dialogue) == 120 and dialogue[0]['conversation'] == 'Constraint 0'
        assert dialogue[-2]['conversation'].startswith('Correction:')
        raw = prepared.body.decode()
        for value in (str(state.turn.turn_id), str(state.turn.conversation_id),
            str(state.turn.idempotency_key), state.turn.graph_context_receipt.context_receipt_sha256,
            state.turn.graph_context_execution.execution_policy_sha256, str(rules.native.authorization_id)):
            assert value not in raw
        assert 'not_prepared' in raw and 'Ashbell has three bridges' in raw


@_pending_test_contextmanager
def pending_writer_completion_case(monkeypatch, *, source_free_work=None, lore_page=False, app_pages=False):
    from application_state.agent_conversation import repository
    with pending_writer_dispatch_case(monkeypatch, source_free_work=source_free_work, lore_page=lore_page, app_pages=app_pages) as (state, adapter, rules, writer, prepared):
        configure_pending_completion_storage(monkeypatch,state)
        yield state, adapter, rules, writer, prepared


@pytest.mark.parametrize('pretty', [False, True])
def test_pending_writer_real_sdk_reply_is_proved_completed_and_stored_readable_without_acquisition(monkeypatch, pretty):
    import asyncio
    import httpx
    from tests.test_surface_native_turn_records import stored_row
    from application_state.agent_conversation import repository
    calls = []
    text = 'We retained the three bridges, the “memory” fare, and the unresolved identity.'
    def respond(request):
        calls.append(json.loads(request.content))
        candidate = {'answer_segments': [{'kind': 'discussion', 'text': text}], 'limitations': []}
        if 'collaboration' in calls[-1]['text']['format']['schema']['properties']:
            candidate['collaboration'] = None
        output = json.dumps(candidate, indent=2 if pretty else None, ensure_ascii=False)
        return httpx.Response(200, request=request, json={'id': 'resp_pending', 'object': 'response',
            'created_at': 1, 'model': calls[-1]['model'], 'status': 'completed', 'output': [{
                'type': 'message', 'id': 'msg_pending', 'role': 'assistant', 'status': 'completed',
                'content': [{'type': 'output_text', 'text': output, 'annotations': []}]}]})
    with pending_writer_completion_case(monkeypatch) as (state, adapter, rules, writer, prepared):
        completed = asyncio.run(writer.run(transport=httpx.MockTransport(respond), api_key='synthetic'))
        assert completed.status == 'completed' and completed.assistant_text == text
        assert state.completions == 1 and len(calls) == 1
        assert state.materialized == 0 and state.retained_reads == 1
        assert state.rules_payload['state'] == 'unused'
        assert completed.graph_context_execution.events[-1].kind == 'completion_binding'
        row, references = stored_row(completed)
        assert repository._turn_from_row(None, row, references=references) == completed
        from copy import deepcopy
        from application_state.errors import ApplicationStateIntegrityError
        missing_timestamp = completed.model_dump(mode='json', by_alias=True)
        missing_timestamp['completed_at'] = None
        with pytest.raises(ValidationError, match='lifecycle'):
            t.Turn.model_validate_json(json.dumps(missing_timestamp))
        for change in ('text', 'completion_text', 'context', 'binding', 'lifecycle', 'timestamp'):
            altered = deepcopy(row)
            if change == 'text':
                altered['assistant_text'] = 'Unbound changed text'
            elif change == 'completion_text':
                altered['completion']['answer_segments'][0]['text'] = 'Unbound changed completion'
            elif change == 'context':
                altered['completion']['context_receipt_sha256'] = 'b' * 64
            elif change == 'binding':
                altered['graph_context_execution']['events'][-1]['completion_sha256'] = 'b' * 64
            elif change == 'lifecycle':
                altered['status'] = 'running'
            else:
                altered['completed_at'] = None
            with pytest.raises((ApplicationStateIntegrityError, ValidationError, ValueError)):
                repository._turn_from_row(None, altered, references=references)


@pytest.mark.parametrize('failure', ['pointer', 'access', 'expiry', 'trace', 'text', 'output_proof', 'rules_revision', 'generic_owner'])
def test_pending_writer_final_acceptance_refuses_changed_capture_or_current_owner(monkeypatch, failure):
    import asyncio
    import httpx
    from datetime import timedelta
    from application_state.errors import ApplicationStateError
    calls = []
    def respond(request):
        calls.append(request)
        output = json.dumps({'answer_segments': [{'kind': 'discussion', 'text': 'The identity remains unresolved.'}],
            'limitations': []})
        return httpx.Response(200, request=request, json={'id': 'resp_pending', 'object': 'response', 'created_at': 1,
            'model': json.loads(request.content)['model'], 'status': 'completed', 'output': [{
                'type': 'message', 'id': 'msg_pending', 'role': 'assistant', 'status': 'completed',
                'content': [{'type': 'output_text', 'text': output, 'annotations': []}]}]})
    with pending_writer_completion_case(monkeypatch) as (state, adapter, rules, writer, prepared):
        original = state.service.complete_pending_native_base_turn
        def accept(result, **kwargs):
            if failure == 'pointer':
                state.pointer = state.pointer.model_copy(update={'revision': state.pointer.revision + 1})
            elif failure == 'access':
                state.denied = True
            elif failure == 'expiry':
                state.now += timedelta(hours=1)
            elif failure == 'trace':
                state.writer_trace = dict(state.writer_trace, observations=[])
            elif failure == 'text':
                result = result.model_copy(update={'assistant_text': 'Unbound replacement'})
            elif failure == 'output_proof':
                kwargs['output_proof'] = kwargs['output_proof'].model_copy(update={'raw_output_json': '{}'})
            elif failure == 'rules_revision':
                state.rules_revision += 1
            else:
                kwargs.pop('authorize_current_access')
                return state.service.complete_native_base_turn(result, **kwargs)
            return original(result, **kwargs)
        monkeypatch.setattr(state.service, 'complete_pending_native_base_turn', accept)
        with pytest.raises((ApplicationStateError, ValueError)):
            asyncio.run(writer.run(transport=httpx.MockTransport(respond), api_key='synthetic'))
        assert len(calls) == 1 and state.completions == 0 and state.materialized == 0
        assert state.turn.completion is None and state.turn.assistant_text is None
        assert not any(event.kind == 'completion_binding' for event in state.turn.graph_context_execution.events)


def test_pending_writer_unbound_source_reference_cannot_become_an_accepted_reply(monkeypatch):
    import asyncio
    import httpx
    from generationengine import GenerationEngineError
    calls = []
    def respond(request):
        calls.append(request)
        output = json.dumps({'answer_segments': [{'kind': 'source_passage_claim',
            'text': 'An unsupported fact.', 'passage_handles': ['unbound-source']}], 'limitations': []})
        return httpx.Response(200, request=request, json={'id': 'resp_pending_bad', 'object': 'response', 'created_at': 1,
            'model': json.loads(request.content)['model'], 'status': 'completed', 'output': [{
                'type': 'message', 'id': 'msg_pending_bad', 'role': 'assistant', 'status': 'completed',
                'content': [{'type': 'output_text', 'text': output, 'annotations': []}]}]})
    with pending_writer_completion_case(monkeypatch) as (state, adapter, rules, writer, prepared):
        with pytest.raises(GenerationEngineError):
            asyncio.run(writer.run(transport=httpx.MockTransport(respond), api_key='synthetic'))
        assert len(calls) == 1 and state.completions == 0 and state.materialized == 0
        assert state.turn.completion is None and state.turn.assistant_text is None


@pytest.mark.parametrize('label', ['clarify_request', 'clarify_creation', 'review_blank_lore_page'])
def test_pending_source_free_terminal_settles_writer_without_retained_or_source_acquisition(monkeypatch, label):
    from types import SimpleNamespace
    from apps.live_control_server.services.plan_jev_writer import PlanJevWriter
    from application_state.agent_conversation.rules_authority_plan_packet import PlanRulesEvidenceFrameV1
    from application_state.agent_conversation.writer_evidence_selection import native_terminal
    from application_state.agent_conversation.build_source_free import pending_source_free_terminal
    with pending_writer_runtime_case(monkeypatch, source_free_work=label) as (state, adapter, selector, turns):
        terminal = {'status': 'ready', 'reason': 'pending_source_free_' + label}
        assert native_terminal(state.turn) == terminal
        selected = selector.settle_empty()
        assert selected.terminal_disposition == terminal and selected.mode == 'empty_catalog'
        rules = SimpleNamespace(frame=lambda: PlanRulesEvidenceFrameV1(
            schema='dmb_plan_rules_evidence_v1', ruleset='synthetic', lookups=(), supports=()), authoring=None)
        writer = PlanJevWriter(adapter, {}, rules)
        assert writer.shared and writer.messages
        assert state.retained_reads == 0 and state.materialized == 0 and state.persisted == 1
        execution = state.turn.graph_context_execution
        # An unacknowledged response cannot become a source-free terminal.
        changed = list(execution.events)
        changed[2] = changed[2].model_copy(update={'outcome': 'outcome_unknown'})
        assert pending_source_free_terminal(execution.model_copy(update={'events': tuple(changed)})) is None
        from tests.test_build_source_free_routing import pending_settlement
        acquired = pending_settlement(state.turn.graph_context_receipt, execution.policy,
            next(row for row in execution.events if type(row) is t.BuildRequestedWorkResolutionV1))
        assert pending_source_free_terminal(execution.model_copy(update={'events': (*execution.events, acquired)})) is None
        # Stored selection cannot claim another source-free outcome.
        altered = selected.model_copy(update={'terminal_disposition': {'status': 'ready', 'reason': 'invented'}})
        with pytest.raises(ValueError, match='source-free work terminal'):
            from application_state.agent_conversation.build_source_free import validate_pending_empty_writer_selection
            validate_pending_empty_writer_selection(execution, altered)
        # No label shortcut for factual lookup/discussion work.
        assert pending_source_free_terminal(execution.model_copy(update={'events': tuple(
            row.model_copy(update={'requested_work': 'discuss'})
            if type(row) is t.BuildRequestedWorkResolutionV1 else row for row in execution.events)})) is None
        work = next(row for row in execution.events if type(row) is t.BuildRequestedWorkResolutionV1)
        forged = work.model_copy(update={'resolution': work.resolution | {'barrier': 'invented'}})
        with pytest.raises(ValueError, match='frozen response contract'):
            pending_source_free_terminal(execution.model_copy(update={'events': tuple(
                forged if row.event_id == work.event_id else row for row in execution.events)}))


@pytest.mark.parametrize('label', ['clarify_request', 'clarify_creation', 'review_blank_lore_page'])
def test_pending_source_free_real_sdk_completion(monkeypatch, label):
    import asyncio
    import httpx
    calls = []
    def respond(request):
        calls.append(json.loads(request.content))
        candidate = {'answer_segments': [{'kind': 'discussion', 'text': 'What should this new page describe?'}], 'limitations': []}
        if 'collaboration' in calls[-1]['text']['format']['schema']['properties']:
            candidate['collaboration'] = None
        return httpx.Response(200, request=request, json={'id': 'resp_source_free', 'object': 'response',
            'created_at': 1, 'model': calls[-1]['model'], 'status': 'completed', 'output': [{
                'type': 'message', 'id': 'msg_source_free', 'role': 'assistant', 'status': 'completed',
                'content': [{'type': 'output_text', 'text': json.dumps(candidate), 'annotations': []}]}]})
    with pending_writer_completion_case(monkeypatch, source_free_work=label) as (state, adapter, rules, writer, prepared):
        completed = asyncio.run(writer.run(transport=httpx.MockTransport(respond), api_key='synthetic'))
        assert completed.status == 'completed' and state.completions == 1 and len(calls) == 1
        assert state.retained_reads == 0 and state.materialized == 0
        row, references = stored_row(completed)
        assert repository._turn_from_row(None, row, references=references) == completed


@pytest.mark.parametrize('failure', [None, 'bare_discussion', 'unbound_citation'])
def test_pending_sixty_turn_context_produces_stored_maelthor_page_draft_without_search(monkeypatch, failure):
    import asyncio
    import httpx
    calls = []
    def respond(request):
        calls.append(json.loads(request.content))
        candidate = {'answer_segments': [{'kind': 'proposal', 'label': 'invented_idea',
            'text': 'Authored note context: Maelthor stands beside three bridges. The fare is a truthful memory.'}],
            'limitations': [], 'collaboration': {'kind': 'lore_page',
                'destination': {'request': 'current_author_request', 'title': 'Maelthor'},
                'open_questions': ['Who is the traveler?']}}
        if failure == 'bare_discussion':
            candidate['collaboration'] = None
            candidate['answer_segments'] = [{'kind': 'discussion', 'text': 'Here is your page.'}]
        if failure == 'unbound_citation':
            candidate['answer_segments'] = [{'kind': 'source_passage_claim',
                'text': 'An unsupported fact.', 'passage_handles': ['not-supplied']}]
        return httpx.Response(200, request=request, json={'id': 'resp_maelthor', 'object': 'response',
            'created_at': 1, 'model': calls[-1]['model'], 'status': 'completed', 'output': [{
                'type': 'message', 'id': 'msg_maelthor', 'role': 'assistant', 'status': 'completed',
                'content': [{'type': 'output_text', 'text': json.dumps(candidate), 'annotations': []}]}]})
    with pending_writer_completion_case(monkeypatch, lore_page=True) as (state, adapter, rules, writer, prepared):
        if failure:
            from generationengine import GenerationEngineError
            from application_state.errors import ApplicationStateError
            with pytest.raises((GenerationEngineError, ApplicationStateError, ValueError)):
                asyncio.run(writer.run(transport=httpx.MockTransport(respond), api_key='synthetic'))
            assert len(calls) == 1 and state.completions == 0
            assert state.turn.completion is None and state.materialized == 0
            return
        completed = asyncio.run(writer.run(transport=httpx.MockTransport(respond), api_key='synthetic'))
        assert completed.status == 'completed' and len(calls) == 1 and state.completions == 1
        assert completed.completion.collaboration.kind == 'lore_page'
        assert completed.completion.collaboration.destination.title == 'Maelthor'
        assert 'three bridges' in completed.assistant_text
        assert calls[0]['text']['format']['name'] == 'lore_page_response'
        assert calls[0]['reasoning']['effort'] == 'none'
        assert state.retained_reads == 1 and state.materialized == 0
        admission = next(row for row in completed.graph_context_execution.events
            if type(row) is t.BuildPriorBodyEvidenceAdmittedV3)
        assert len(admission.history) == 60
        rendered = json.dumps(calls[0]['input'])
        assert 'Correction:' in rendered and 'Ashbell has three bridges' in rendered
        assert 'Do not search again' in rendered
        row, references = stored_row(completed)
        assert repository._turn_from_row(None, row, references=references) == completed
        from apps.live_control_server.services.agent_turn_service import project_plan_turn_context, AgentTurnServiceError
        from apps.live_control_server.models.agent_turn import AgentBuildPendingContextResponseV1
        projected = project_plan_turn_context(completed, delivery_replay=True)
        assert type(projected) is AgentBuildPendingContextResponseV1
        assert projected.completion.collaboration.destination.title == 'Maelthor'
        assert AgentBuildPendingContextResponseV1.model_validate_json(
            projected.model_dump_json(by_alias=True)) == projected
        from apps.live_control_server.models.agent_turn import AgentTurnRequest
        from apps.live_control_server.services.agent_turn_service import _completed_turn_replay
        intent=completed.graph_context_execution.policy.action.intent
        request=AgentTurnRequest.model_validate({'schema':'dmb_agent_turn_request_v1',
            'client_thread_id':intent.client_thread_id,'turn_id':adapter.request.turn_id,
            'surface':{'surface_id':'build','instance_id':intent.surface_instance_id},
            'owner_scope':{'kind':'world','world_id':completed.world_id},
            'primary_work':intent.primary_work.model_dump(mode='python'),
            'client_work_state':intent.client_work_state,'graph_request':intent.graph_request.model_dump(mode='python'),
            'graph_selection':None,'message':intent.message})
        replay=_completed_turn_replay(request,owner={'kind':'world','id':completed.world_id,'name':'Synthetic World'},turn=completed)
        assert type(replay.knowledge_context) is AgentBuildPendingContextResponseV1
        assert replay.answer.text==completed.assistant_text and replay.graph.status=='not_requested'
        assert all(value is None for key,value in replay.graph.model_dump().items() if key!='status')
        with pytest.raises(AgentTurnServiceError,match='admitted request'):
            _completed_turn_replay(request.model_copy(update={'message':'Different request'}),
                owner={'kind':'world','id':completed.world_id},turn=completed)
        for changes in ({'turn_id':str(uuid4())},
                {'owner_scope':request.owner_scope.model_copy(update={'world_id':'foreign'})}):
            with pytest.raises(AgentTurnServiceError,match='admitted request'):
                _completed_turn_replay(request.model_copy(update=changes),
                    owner={'kind':'world','id':completed.world_id},turn=completed)
        with pytest.raises(AgentTurnServiceError,match='admitted request'):
            _completed_turn_replay(request,owner={'kind':'world','id':'foreign'},turn=completed)
        from types import SimpleNamespace
        from fastapi import FastAPI, HTTPException
        from fastapi.testclient import TestClient
        from apps.live_control_server.routes import agent as route
        from apps.live_control_server.services import hosted_native_graph_access as access
        order=[]
        def authorize(*args,**kwargs):
            order.append('auth')
        def pointer(world):
            order.append('pointer')
            return state.pointer
        fake=SimpleNamespace(get_world_pointer=pointer,
            get_active_conversation=lambda world: SimpleNamespace(conversation_id=completed.conversation_id),
            list_turns=lambda *args,**kwargs:[completed],
            conversation_draft_turn_ids=lambda *args:{completed.turn_id},
            reviewed_variant_turn_ids=lambda *args:set())
        monkeypatch.setattr(access,'require_conversation_access',authorize)
        monkeypatch.setattr(route,'_verified_world_id',lambda world:world)
        monkeypatch.setattr(route,'_conversation_service',lambda request:fake)
        app=FastAPI();app.include_router(route.router)
        with TestClient(app) as client:
            response=client.get(f'/agent/worlds/{completed.world_id}/conversation',
                params={'include_turn_correlation':'true'})
            assert response.status_code==200,response.text
            body=response.json()
            assert body['schema']=='dmb_agent_conversation_history_v3'
            assert body['turns'][0]['knowledge_context']['schema']=='dmb_agent_build_pending_context_response_v1'
            assert body['turns'][0]['knowledge_context']['completion']['collaboration']['destination']['title']=='Maelthor'
            assert body['turns'][0]['conversation_draft_available'] is True
            assert order==['auth','pointer','pointer']
            order.clear()
            def deny(*args,**kwargs):
                order.append('denied')
                raise HTTPException(status_code=403,detail='Synthetic denied principal')
            monkeypatch.setattr(access,'require_conversation_access',deny)
            denied=client.get(f'/agent/worlds/{completed.world_id}/conversation')
            assert denied.status_code==403 and order==['denied']
        wire = projected.model_dump(mode='json', by_alias=True)
        assert 'native_query' not in wire['receipt'] and 'graph_authority' not in wire['receipt']
        from pydantic import TypeAdapter
        from apps.live_control_server.models.agent_turn import (
            AgentBuildGraphTurnResponseV1, AgentConversationHistoryBuildTurnV2,
            AgentConversationHistoryBuildTurnV3, AgentTurnResponseV2)
        for owner in (AgentBuildGraphTurnResponseV1, AgentConversationHistoryBuildTurnV2,
                AgentConversationHistoryBuildTurnV3):
            accepted = TypeAdapter(owner.model_fields['knowledge_context'].annotation).validate_python(wire)
            assert type(accepted) is AgentBuildPendingContextResponseV1
        with pytest.raises(ValueError):
            TypeAdapter(AgentTurnResponseV2.model_fields['plan_context'].annotation).validate_python(wire)
        from apps.live_control_server.models.agent_turn import AgentRulesAnswerContextV1
        assert type(TypeAdapter(AgentRulesAnswerContextV1.model_fields['base_context'].annotation)
            .validate_python(wire)) is AgentBuildPendingContextResponseV1
        with pytest.raises(ValueError, match='exact receipt'):
            AgentBuildPendingContextResponseV1.model_validate(projected.model_copy(update={'execution': None}))
        with pytest.raises(ValueError, match='requires its completion'):
            AgentBuildPendingContextResponseV1.model_validate(projected.model_copy(update={'completion': None}))
        foreign = projected.completion.model_copy(update={'surface_id': 'plan', 'collaboration': None})
        with pytest.raises(ValueError, match='exact receipt'):
            AgentBuildPendingContextResponseV1.model_validate(projected.model_copy(update={'completion': foreign}))
        wire['completion']['context_receipt_sha256'] = '0' * 64
        with pytest.raises(ValueError, match='exact receipt'):
            AgentBuildPendingContextResponseV1.model_validate(wire)
        changed = completed.model_copy(update={'assistant_text': 'Changed stored answer'})
        with pytest.raises(AgentTurnServiceError):
            project_plan_turn_context(changed, delivery_replay=True)


def pending_app_coverage_case():
    from hashlib import sha256
    from tests.test_surface_native_execution import outcomes
    from application_state.agent_conversation.build_related_pages import PageReference
    receipt, before, auth, initial, _, history = pending_page_input_case()
    page = before.events[-1].pages[0]
    selected = t.RelatedPagesSelection(event_id=uuid4(), sequence=8,
        controller_attempt_id=auth.provider_attempt_id, controller_envelope_sha256=auth.envelope_sha256,
        controller_response_sha256='a' * 64, document_ids=[page.document_id])
    markdown = 'Ethel dreamed of Maelthor. The cult password is “Remember the rain”.'
    read = t.RelatedPageRead(event_id=uuid4(), sequence=9, read_id=uuid4(), selection_event_id=selected.event_id,
        page=PageReference(**page.model_dump(), content_sha256=sha256(markdown.encode()).hexdigest()), markdown=markdown)
    execution = pending_execution(receipt, before.policy, [*before.events, auth, *outcomes(auth, 6), selected, read])
    return receipt, execution, initial, history, read


def test_pending_app_coverage_input_uses_exact_saved_text_and_full_dialogue_without_native_preparation():
    from application_state.agent_conversation.build_pending_app_coverage import pending_app_coverage_input
    from application_state.agent_conversation.build_source_free import effective_pending_source
    receipt, execution, initial, history, read = pending_app_coverage_case()
    wire = pending_app_coverage_input(receipt, execution, initial)
    assert wire['state']['history'] == history and len(history) == 60
    page, = wire['state']['saved_authored_pages']
    assert page == {'source': 'page1', 'title': read.page.title, 'role': read.role, 'markdown': read.markdown}
    assert 'Remember the rain' in json.dumps(wire, ensure_ascii=False)
    assert set(wire['questions']['source_requirement']['criteria']) == {'saved_pages_sufficient', 'native_sources_required'}
    assert effective_pending_source(receipt, execution) is None
    rendered = json.dumps(wire)
    for binding in (str(read.event_id), str(read.read_id), str(read.page.document_id),
            receipt.context_receipt_sha256, execution.execution_policy_sha256):
        assert binding not in rendered


@pytest.mark.parametrize('failure', ['missing_read', 'changed_text', 'changed_page', 'no_ack',
    'changed_history', 'duplicate_read', 'empty_choice'])
def test_pending_app_coverage_refuses_unread_or_changed_evidence_and_context(failure):
    from application_state.agent_conversation.build_pending_app_coverage import pending_app_coverage_input
    receipt, execution, initial, _, read = pending_app_coverage_case()
    events = list(execution.events)
    if failure == 'missing_read':
        events.pop()
    elif failure == 'changed_text':
        events[-1] = read.model_copy(update={'markdown': 'Different saved content'})
    elif failure == 'changed_page':
        events[-1] = read.model_copy(update={'page': read.page.model_copy(update={'registry_revision': 99})})
    elif failure == 'no_ack':
        events[7] = events[7].model_copy(update={'outcome': 'outcome_unknown'})
    elif failure == 'changed_history':
        initial = initial.replace('User detail 0', 'Changed first user detail')
    elif failure == 'duplicate_read':
        events.append(read.model_copy(update={'event_id': uuid4(), 'sequence': 10}))
    else:
        events = events[:8] + [events[8].model_copy(update={'document_ids': []})]
    with pytest.raises(ValueError):
        pending_app_coverage_input(receipt, execution.model_copy(update={'events': events}), initial)


def test_pending_app_coverage_projects_owned_metadata_but_preserves_meaningful_authored_markdown():
    from hashlib import sha256
    from application_state.agent_conversation.build_pending_app_coverage import pending_app_coverage_input
    receipt, execution, initial, _, original = pending_app_coverage_case()
    host_id, external_id = str(uuid4()), str(uuid4())
    raw = (f'[From Earlier notes](/build?world=world-one&documentId={host_id}) · saved revision 7, lines 5–5\n\n'
        f'Original PDF SHA-256: `{"b" * 64}`.\n\n'
        'Ethel dreamed of Maelthor; the password is “Remember the rain”.\n\n'
        f'[External reference](https://example.test/build?documentId={external_id})\n\n'
        f'```text\nOriginal PDF SHA-256: `{"c" * 64}`.\n```\n\n'
        f'The author supplied this literal code: `{"d" * 64}`.\n')
    read = original.model_copy(update={'markdown': raw, 'page': original.page.model_copy(update={
        'content_sha256': sha256(raw.encode()).hexdigest()})})
    execution = pending_execution(receipt, execution.policy, [*execution.events[:-1], read])
    wire = pending_app_coverage_input(receipt, execution, initial)
    projected = wire['state']['saved_authored_pages'][0]['markdown']
    assert host_id not in projected and 'b' * 64 not in projected and 'saved revision' not in projected
    assert 'Earlier notes' in projected and 'Remember the rain' in projected
    assert f'https://example.test/build?documentId={external_id}' in projected
    assert 'c' * 64 in projected and 'd' * 64 in projected
    assert len(projected.splitlines()) == len(raw.splitlines())
    assert execution.events[-1].markdown == raw
    assert execution.events[-1].page.content_sha256 == sha256(raw.encode()).hexdigest()


def pending_app_coverage_proof_case(verdict='saved_pages_sufficient'):
    from hashlib import sha256
    from generationengine.types import DecisionResult, ChoiceDecisionAnswer, InferenceObservation
    from application_state.agent_conversation.build_pending_app_coverage import (
        BuildAppCoverageAuthorizedV1, BuildAppCoverageDecidedV1, pending_app_coverage_input)
    from application_state.agent_conversation.build_decision_context import identity
    from tests.test_surface_native_execution import outcomes
    receipt, before, initial, _, read = pending_app_coverage_case()
    raw = json.dumps(pending_app_coverage_input(receipt, before, initial))
    template = before.events[5].model_dump(mode='python')
    template.pop('catalog_event_id')
    auth = BuildAppCoverageAuthorizedV1.model_validate(template | {
        'kind':'build_app_coverage_authorized_v1','event_id':uuid4(),'sequence':len(before.events),
        'provider_attempt_id':uuid4(),'envelope_sha256':sha256(raw.encode()).hexdigest(),
        'dispatch_identity_sha256':identity(envelope_sha256=sha256(raw.encode()).hexdigest(),
            provider=template['provider'],model=template['model'],api_mode=template['api_mode'],context_mode=template['context_mode']),
        'work_event_id':before.events[3].event_id,'read_event_ids':(read.event_id,), 'admitted_from_revision':4})
    execution = pending_execution(receipt,before.policy,[*before.events,auth,*outcomes(auth,len(before.events)+1)])
    result=DecisionResult(answers={'source_requirement':ChoiceDecisionAnswer(selected=verdict,
        probabilities={key:.9 if key==verdict else .1 for key in ('saved_pages_sufficient','native_sources_required')})},
        observation=InferenceObservation(provider='typesafe',resolved_model='jev-1.14.0',response_model='jev-1.14.0',
            latency_ms=1,retry_count=0,state='completed',provider_attempt_count=1))
    response=result.model_dump_json(by_alias=True)
    collector,store,_=pending_response_collector(components=(receipt,execution))
    collector.controller_decision_response(response,producing_provider_attempt_id=auth.provider_attempt_id)
    decision=BuildAppCoverageDecidedV1(event_id=uuid4(),sequence=len(execution.events),
        controller_attempt_id=auth.provider_attempt_id,controller_envelope_sha256=auth.envelope_sha256,
        controller_response_sha256=sha256(response.encode()).hexdigest(),verdict=verdict)
    proof={'request_json':raw,'response_json':response,'initial_request_json':initial}
    return receipt,execution,decision,proof,store.trace.model_dump(mode='json',by_alias=True)


@pytest.mark.parametrize('verdict',['saved_pages_sufficient','native_sources_required'])
def test_pending_app_coverage_verdict_binds_captured_vote_and_controls_only_further_preparation(verdict):
    from application_state.agent_conversation.build_pending_app_coverage import validate_coverage_result
    from application_state.agent_conversation.build_source_free import pending_source_work
    receipt,execution,decision,proof,trace=pending_app_coverage_proof_case(verdict)
    assert validate_coverage_result(receipt,execution,decision,proof,trace)==verdict
    admitted=pending_execution(receipt,execution.policy,[*execution.events,decision])
    assert type(admitted).model_validate_json(admitted.model_dump_json(by_alias=True))==admitted
    if verdict=='saved_pages_sufficient':
        with pytest.raises(ValueError,match='further-source'):
            pending_source_work(admitted)
    else:
        assert pending_source_work(admitted).event_id==execution.events[3].event_id
    # Dispatch or response acknowledgement alone never authorizes new source IO.
    with pytest.raises(ValueError,match='further-source'):
        pending_source_work(execution)


@pytest.mark.parametrize('failure',['missing_capture','changed_capture','changed_vote','changed_body',
    'changed_history','hidden_retry','tie','foreign_producer','unresolved','read_ids','late_read'])
def test_pending_app_coverage_contract_refuses_unproven_or_changed_verdict(failure):
    from hashlib import sha256
    from application_state.agent_conversation.build_pending_app_coverage import validate_coverage_result
    receipt,execution,decision,proof,trace=pending_app_coverage_proof_case()
    if failure=='missing_capture':trace['observations']=[]
    elif failure=='changed_capture':trace['observations'][-1]['materials'][0]['text']='{}'
    elif failure=='changed_vote':decision=decision.model_copy(update={'verdict':'native_sources_required'})
    elif failure=='changed_body':proof['request_json']=proof['request_json'].replace('Remember the rain','Changed password')
    elif failure=='changed_history':proof['initial_request_json']=proof['initial_request_json'].replace('User detail 0','Changed first detail')
    elif failure in ('hidden_retry','tie'):
        response=json.loads(proof['response_json'])
        if failure=='hidden_retry':response['observation']['retry_count']=1
        else:response['answers']['source_requirement']['probabilities']={key:.5 for key in ('saved_pages_sufficient','native_sources_required')}
        proof['response_json']=json.dumps(response)
        decision=decision.model_copy(update={'controller_response_sha256':sha256(proof['response_json'].encode()).hexdigest()})
        trace['observations'][-1]['materials'][0]['text']=proof['response_json']
    elif failure=='foreign_producer':decision=decision.model_copy(update={'controller_attempt_id':uuid4()})
    elif failure=='unresolved':
        events=list(execution.events);events[-1]=events[-1].model_copy(update={'outcome':'outcome_unknown'})
        execution=execution.model_copy(update={'events':events})
    elif failure=='read_ids':
        events=list(execution.events);events[10]=events[10].model_copy(update={'read_event_ids':(uuid4(),)})
        execution=execution.model_copy(update={'events':events})
    else:
        read=execution.events[9].model_copy(update={'event_id':uuid4(),'sequence':len(execution.events)})
        with pytest.raises(ValueError):
            pending_execution(receipt,execution.policy,[*execution.events,read])
        return
    with pytest.raises(ValueError):
        validate_coverage_result(receipt,execution,decision,proof,trace)


def pending_app_coverage_service_case(monkeypatch):
    from types import SimpleNamespace
    from datetime import timedelta
    from tests.test_surface_native_execution import BUILD_TURN_ID
    state,_,_,_=pending_page_dispatch_harness(monkeypatch)
    receipt,execution,decision,proof,_=pending_app_coverage_proof_case()
    provenance=provenance_for(receipt.work_context).model_copy(update={
        'surface_instance_id':execution.policy.action.intent.surface_instance_id})
    data=receipt.model_dump(mode='json',by_alias=True);data.pop('context_receipt_sha256')
    receipt=seal_pending_receipt(data|{'provenance_sha256':t.canonical_sha256(provenance)})
    events=list(execution.events)
    events[4]=events[4].model_copy(update={'pending_context_receipt_sha256':receipt.context_receipt_sha256})
    execution=pending_execution(receipt,execution.policy,events)
    sub=t.TurnSubmission(world_id=execution.policy.action.intent.world_id,
        conversation_id=receipt.conversation_observation.conversation_id,idempotency_key=uuid4(),
        expected_conversation_revision=1,user_text=execution.policy.action.intent.message,provenance=provenance,
        submitted_intent_v2=execution.policy.action.intent,graph_context_receipt=receipt,
        graph_context_execution=pending_execution(receipt,execution.policy))
    state.turn=retained(sub,turn_id=BUILD_TURN_ID,status='running',revision=4,attempt=1,
        claim_expires_at=state.now+timedelta(minutes=2),
        graph_context_execution=pending_execution(receipt,execution.policy,events[:10]))
    state.pointer=t.WorldPointer(world_id=sub.world_id,active_conversation_id=sub.conversation_id,
        revision=receipt.conversation_observation.pointer_revision)
    auth=events[10]
    first=events[0]
    state.prompt=state.prompt|{'provider_attempt_id':str(first.provider_attempt_id),
        'payload_sha256':first.envelope_sha256,'payload_utf8_bytes':len(proof['initial_request_json'].encode())}
    state.sdk_prompt=state.prompt|{'evidence_id':str(uuid4()),'provider_attempt_id':str(auth.provider_attempt_id),
        'payload_sha256':auth.envelope_sha256,'payload_utf8_bytes':len(proof['request_json'].encode())}
    state.sdk_prompt_count=1
    collector,store,_=pending_response_collector(components=(receipt,execution))
    collector.controller_decision_response(proof['response_json'],producing_provider_attempt_id=auth.provider_attempt_id)
    state.coverage_trace=store.trace.model_dump(mode='json',by_alias=True)
    def query(sql,args):
        if sql=='SELECT 1 FROM agent.turn_retry WHERE predecessor_id=%s':return state.leaf_query(sql,args)
        assert state.depth==1
        if sql=='SELECT payload FROM agent.turn_context_trace WHERE turn_id=%s':
            assert args==(state.turn.turn_id,)
            return SimpleNamespace(fetchall=lambda:[({'observations':[state.prompt]+[state.sdk_prompt]*state.sdk_prompt_count},)])
        assert sql=='SELECT payload FROM agent.turn_context_trace WHERE turn_id=%s AND attempt=%s'
        assert args==(state.turn.turn_id,state.turn.attempt)
        return SimpleNamespace(fetchone=lambda:(state.coverage_trace,))
    state.conn.execute=query
    authorize=state.authorize
    state.access_refs=[]
    def access(conn,turn,pages):
        assert pages and all(type(page).__name__=='PageReference' for page in pages)
        state.access_refs.append(pages)
        return authorize(conn,turn,pages)
    state.coverage_access=access
    def admit(**changes):
        fields=dict(expected_revision=4,expected_attempt=1,authorization=auth,
            prepared_request_json=proof['request_json'],initial_request_json=proof['initial_request_json'],
            authorize_current_access=access)|changes
        return state.service.authorize_pending_app_coverage(state.turn.world_id,state.turn.conversation_id,
            state.turn.turn_id,**fields)
    def lifecycle(event,**changes):
        fields=dict(expected_revision=state.turn.revision,expected_attempt=1,outcome=event,
            authorize_current_access=access)|changes
        if event.outcome=='sdk_entered':
            return state.service.enter_pending_app_page_sdk(state.turn.world_id,state.turn.conversation_id,
                state.turn.turn_id,prepared_request_json=proof['request_json'],**fields)
        return state.service.record_pending_app_controller_outcome(state.turn.world_id,state.turn.conversation_id,
            state.turn.turn_id,**fields)
    def settle(**changes):
        fields=dict(expected_revision=state.turn.revision,expected_attempt=1,decision=decision,
            producer_proof=proof,authorize_current_access=access)|changes
        return state.service.record_pending_app_coverage(state.turn.world_id,state.turn.conversation_id,
            state.turn.turn_id,**fields)
    return state,admit,lifecycle,settle,events[11],events[12],decision,proof


def test_pending_app_coverage_locked_admission_dispatch_and_verdict_are_one_shot(monkeypatch):
    from application_state.errors import ApplicationStateError
    state,admit,lifecycle,settle,entry,response,decision,proof=pending_app_coverage_service_case(monkeypatch)
    turn,fresh=admit();assert fresh and state.persisted==1
    replay,fresh=admit();assert not fresh and replay==turn and state.persisted==1
    turn,fresh=lifecycle(entry);assert fresh and state.persisted==2
    replay,fresh=lifecycle(entry);assert not fresh and replay==turn and state.persisted==2
    with pytest.raises(ApplicationStateError):
        lifecycle(entry.model_copy(update={'event_id':uuid4()}))
    lifecycle(response)
    completed,fresh=settle();assert fresh and completed.graph_context_execution.events[-1]==decision
    replay,fresh=settle();assert not fresh and replay==completed and state.persisted==4
    assert state.materialized==0 and state.access_refs


@pytest.mark.parametrize('failure',['pointer','access','access_after','expiry','claim','bool_attempt','body','initial','cas'])
def test_pending_app_coverage_service_discards_changed_authorization_scope(monkeypatch,failure):
    from datetime import timedelta
    from application_state.errors import ApplicationStateError
    state,admit,_,_,_,_,_,proof=pending_app_coverage_service_case(monkeypatch)
    changes={}
    if failure=='pointer':state.pointer=state.pointer.model_copy(update={'revision':state.pointer.revision+1})
    elif failure=='access':state.denied=True
    elif failure=='access_after':
        original=state.coverage_access
        def changed(conn,turn,pages):
            allowed=original(conn,turn,pages)
            return allowed and len(state.access_refs)<2
        changes['authorize_current_access']=changed
    elif failure=='expiry':state.access_delay=True
    elif failure=='claim':changes['expected_revision']=3
    elif failure=='bool_attempt':changes['expected_attempt']=True
    elif failure=='body':changes['prepared_request_json']=proof['request_json'].replace('Remember the rain','Different password')
    elif failure=='initial':changes['initial_request_json']='{}'
    else:state.cas_failure=True
    with pytest.raises(ApplicationStateError):admit(**changes)
    assert state.persisted==0 and state.materialized==0


@pytest.mark.parametrize('failure',['missing_capture','access','expiry','unknown','generic'])
def test_pending_app_coverage_verdict_requires_actual_capture_access_claim_and_dedicated_owner(monkeypatch,failure):
    from application_state.errors import ApplicationStateError
    state,admit,lifecycle,settle,entry,response,decision,_=pending_app_coverage_service_case(monkeypatch)
    admit();lifecycle(entry)
    if failure=='unknown':response=response.model_copy(update={'outcome':'outcome_unknown'})
    lifecycle(response)
    before=state.persisted
    if failure=='missing_capture':state.coverage_trace['observations']=[]
    elif failure=='access':state.denied=True
    elif failure=='expiry':state.access_delay=True
    if failure=='generic':
        from application_state.agent_conversation import service as service_module
        monkeypatch.setattr(service_module,'_execution_append_transaction',lambda measure:state.uow())
        with pytest.raises(ApplicationStateError,match='exact prepared-input admission owner'):
            state.service._append_graph_execution_event(state.turn.world_id,state.turn.conversation_id,state.turn.turn_id,
                expected_revision=state.turn.revision,expected_attempt=1,event=decision,duplicate_key='event_id')
    else:
        with pytest.raises(ApplicationStateError):settle()
    assert state.persisted==before and state.materialized==0


def test_pending_app_reads_cannot_prepare_native_sources_before_coverage_starts(monkeypatch):
    from application_state.agent_conversation.build_source_free import pending_source_work
    from application_state.errors import ApplicationStateError
    from tests.test_build_source_free_routing import pending_settlement
    state,_,_,_,_,_,_,_=pending_app_coverage_service_case(monkeypatch)
    receipt,execution=state.turn.graph_context_receipt,state.turn.graph_context_execution
    with pytest.raises(ValueError,match='further-source coverage'):
        pending_source_work(execution)
    work=execution.events[3]
    settlement=pending_settlement(receipt,execution.policy,work).model_copy(update={'sequence':len(execution.events)})
    with pytest.raises(ValueError,match='further-source coverage'):
        pending_execution(receipt,execution.policy,[*execution.events,settlement])
    calls=[]
    def forbidden(turn):
        calls.append(turn)
        raise AssertionError('Read-complete App work attempted native preparation without coverage')
    with pytest.raises(ApplicationStateError,match='further-source coverage'):
        state.service.settle_pending_build_source(state.turn.world_id,state.turn.conversation_id,state.turn.turn_id,
            expected_revision=state.turn.revision,expected_attempt=1,event_id=uuid4(),
            materialize_source=forbidden,authorize_current_access=state.authorize)
    assert not calls and state.persisted==state.materialized==0


@pytest.mark.parametrize('verdict',['saved_pages_sufficient','native_sources_required','unknown','skip'])
def test_pending_app_coverage_runtime_actual_sdk_preserves_context_and_never_repeats_reads_or_dispatch(monkeypatch,verdict):
    monkeypatch.setenv('TYPESAFE_JEV_API_KEY','synthetic-no-network')
    import asyncio
    import httpx2
    from hashlib import sha256
    from generationengine import GenerationEngineError
    from apps.live_control_server.services import build_related_pages
    from apps.live_control_server.services.build_pending_app_pages import acquire_pending_app_pages
    from apps.live_control_server.services.build_pending_app_coverage import assess_pending_app_coverage
    from apps.live_control_server.services.build_jev_harness import BuildJevHarness
    calls,reads=[],[]
    class Transport(httpx2.AsyncBaseTransport):
        async def handle_async_request(self,request):
            body=json.loads(request.content);calls.append(body)
            coverage='source_requirement' in body['questions']
            if coverage and verdict=='unknown':raise httpx2.ReadTimeout('Synthetic unknown coverage',request=request)
            choices=('saved_pages_sufficient','native_sources_required') if coverage else ('read','skip')
            chosen=verdict if coverage else 'skip' if verdict=='skip' else 'read'
            return httpx2.Response(200,request=request,json={'model':body['model'],
                'usage':{'input_tokens':23,'output_tokens':4},'answers':{
                    name:{'type':'choice','choice':chosen,'confidence':1,
                        'probabilities':{key:float(key==chosen) for key in choices}} for name in body['questions']}})
    with pending_app_runtime_case(monkeypatch) as (state,adapter):
        def materialize(pointer):
            reads.append(pointer.document_id)
            text='Ethel dreamed of Maelthor; the password remains uncertain.'
            return pointer.model_dump(mode='json')|{'markdown':text,'content_sha256':sha256(text.encode()).hexdigest()}
        monkeypatch.setattr(build_related_pages,'materialize',materialize)
        harness=BuildJevHarness(decision_transport=Transport())
        harness.adapter,harness.calls,harness.timings,harness._inflight=adapter,[],[],{}
        asyncio.run(acquire_pending_app_pages(adapter,harness))
        if verdict=='skip':
            assert asyncio.run(assess_pending_app_coverage(adapter,harness)) is None
            assert len(calls)==1 and not reads
            return
        if verdict=='unknown':
            with pytest.raises(GenerationEngineError):asyncio.run(assess_pending_app_coverage(adapter,harness))
            with pytest.raises(ValueError,match='unresolved'):asyncio.run(assess_pending_app_coverage(adapter,harness))
            assert state.turn.graph_context_execution.events[-1].outcome=='outcome_unknown'
        else:
            assert asyncio.run(assess_pending_app_coverage(adapter,harness))==verdict
            assert asyncio.run(assess_pending_app_coverage(adapter,harness))==verdict
        assert len(calls)==2 and len(reads)==1 and state.materialized==0
        coverage=calls[-1]
        assert len(coverage['state']['history'])==60
        assert coverage['state']['saved_authored_pages'][0]['markdown'].startswith('Ethel dreamed')
        for value in (str(state.turn.turn_id),str(reads[0]),state.turn.graph_context_receipt.context_receipt_sha256):
            assert value not in json.dumps(coverage)
        if verdict!='unknown':
            state.denied=True
            from application_state.errors import ApplicationStateError
            with pytest.raises(ApplicationStateError):asyncio.run(assess_pending_app_coverage(adapter,harness))
            assert len(calls)==2 and len(reads)==1


@_pending_test_contextmanager
def pending_app_writer_seed(monkeypatch, *, lore_page=False):
    import asyncio
    import httpx2
    from hashlib import sha256
    from apps.live_control_server.services import build_related_pages
    from apps.live_control_server.services.build_pending_app_pages import acquire_pending_app_pages
    from apps.live_control_server.services.build_pending_app_coverage import assess_pending_app_coverage
    from apps.live_control_server.services.build_jev_harness import BuildJevHarness
    monkeypatch.setenv('TYPESAFE_JEV_API_KEY','synthetic-no-network')
    class Transport(httpx2.AsyncBaseTransport):
        async def handle_async_request(self,request):
            body=json.loads(request.content)
            coverage='source_requirement' in body['questions']
            keys=('saved_pages_sufficient','native_sources_required') if coverage else ('read','skip')
            chosen=keys[0]
            return httpx2.Response(200,request=request,json={'model':body['model'],
                'usage':{'input_tokens':23,'output_tokens':4},'answers':{name:{'type':'choice','choice':chosen,
                    'confidence':1,'probabilities':{key:float(key==chosen) for key in keys}} for name in body['questions']}})
    with pending_app_runtime_case(monkeypatch) as (state,adapter):
        def materialize(pointer):
            text='Ethel dreamed of Maelthor. The cult password is “Remember the rain”.'
            return pointer.model_dump(mode='json')|{'markdown':text,'content_sha256':sha256(text.encode()).hexdigest()}
        monkeypatch.setattr(build_related_pages,'materialize',materialize)
        harness=BuildJevHarness(decision_transport=Transport())
        harness.adapter,harness.calls,harness.timings,harness._inflight=adapter,[],[],{}
        asyncio.run(acquire_pending_app_pages(adapter,harness))
        assert asyncio.run(assess_pending_app_coverage(adapter,harness))=='saved_pages_sufficient'
        original_access=adapter.pending_build_access
        state.writer_page_checks=0
        def writer_access(conn,current,pages):
            assert pages and all(type(page).__name__=='PageReference' for page in pages)
            state.writer_page_checks+=1
            return original_access(conn,current,pages)
        adapter.pending_build_access=adapter.fence.pending_build_access=writer_access
        history=json.loads(state.initial_request)['state']['interaction']['history']
        adapter.app_test_dialogue=tuple({'role':role,'content':row[role]} for row in history for role in ('user','assistant'))
        yield state,adapter,[]


@pytest.mark.parametrize('failure',[None,'alias','access','access_after'])
def test_pending_app_writer_real_sdk_reply_binds_saved_page_and_stored_citation_without_search(monkeypatch,failure):
    import asyncio
    import httpx
    from application_state.errors import ApplicationStateError
    from generationengine import GenerationEngineError
    calls=[]
    def respond(request):
        calls.append(json.loads(request.content))
        text='Ethel dreamed of Maelthor. The cult password is “Remember the rain”.'
        if failure=='access_after':state.denied=True
        candidate={'answer_segments':[{'kind':'related_page_claim','text':text,
            'read_id':'invented-source' if failure=='alias' else 'source0'}],'limitations':[]}
        return httpx.Response(200,request=request,json={'id':'resp_app_page','object':'response','created_at':1,
            'model':calls[-1]['model'],'status':'completed','output':[{'type':'message','id':'msg_app_page',
                'role':'assistant','status':'completed','content':[{'type':'output_text','text':json.dumps(candidate),'annotations':[]}]}]})
    with pending_writer_completion_case(monkeypatch,app_pages=True) as (state,adapter,rules,writer,prepared):
        if failure=='access':state.denied=True
        if failure:
            with pytest.raises((ValueError,ApplicationStateError,GenerationEngineError)):
                asyncio.run(writer.run(transport=httpx.MockTransport(respond),api_key='synthetic'))
            assert state.completions==0 and state.turn.completion is None
            assert len(calls)==(0 if failure=='access' else 1)
            return
        completed=asyncio.run(writer.run(transport=httpx.MockTransport(respond),api_key='synthetic'))
        assert completed.status=='completed' and state.completions==1 and len(calls)==1
        claim=completed.completion.answer_segments[0]
        page=next(row for row in completed.graph_context_execution.events if type(row) is t.RelatedPageRead)
        assert claim.kind=='related_page_claim' and claim.read_id==page.read_id and claim.page==page.page
        assert 'Remember the rain' in completed.assistant_text
        assert state.writer_page_checks>=4 and state.materialized==0
        assert 'Already discussed detail 0' in json.dumps(calls[0]['input'])
        assert 'Already discussed detail 59' in json.dumps(calls[0]['input'])
        for binding in (str(page.read_id),str(page.page.document_id),str(completed.turn_id),
                completed.graph_context_receipt.context_receipt_sha256):
            assert binding not in json.dumps(calls[0]['input'])
        row,references=stored_row(completed)
        assert repository._turn_from_row(None,row,references=references)==completed
        from copy import deepcopy
        from application_state.errors import ApplicationStateIntegrityError
        forged=deepcopy(row)
        forged['completion']['answer_segments'][0]['page']['registry_revision']+=1
        with pytest.raises(ApplicationStateIntegrityError):
            repository._turn_from_row(None,forged,references=references)


def configure_pending_rules_storage(state):
    from types import SimpleNamespace
    state.rules_payload, state.rules_inserts, state.rules_locks = None, 0, 0
    state.rules_revision = 1
    state.capture_status = 'recording'
    state.rules_cas_failure = False
    class Cursor:
        def __enter__(self):
            return self
        def __exit__(self, *args):
            return False
        def execute(self, sql, args):
            assert state.depth == 1
            self.row = None
            if 'FROM agent.turn WHERE' in sql:
                assert args == (state.turn.world_id, state.turn.conversation_id, state.turn.turn_id)
                state.rules_locks += 1
                self.row = {key: getattr(state.turn, key) for key in ('status', 'revision', 'attempt',
                    'claim_expires_at', 'idempotency_key', 'submitted_intent_fingerprint_v1', 'submitted_intent_fingerprint_v2')}
                self.row['graph_execution_schema'] = state.turn.graph_context_execution.schema_
            else:
                assert 'FROM agent.turn_rules_execution' in sql
                assert args == (state.turn.turn_id, state.turn.attempt)
                if state.rules_payload is not None:
                    self.row = {'revision': state.rules_revision, 'payload': state.rules_payload}
        def fetchone(self):
            return self.row
    state.conn.cursor = lambda **kwargs: Cursor()
    def execute(sql, args=None):
        assert state.depth == 1
        if sql == 'SELECT clock_timestamp()':
            return SimpleNamespace(fetchone=lambda: (state.now,))
        if sql == 'SELECT 1 FROM agent.turn_retry WHERE predecessor_id=%s':
            return state.leaf_query(sql, args)
        if "SELECT payload->>'capture_status'" in sql:
            return SimpleNamespace(fetchone=lambda: (state.capture_status,))
        if sql == 'SELECT payload FROM agent.turn_context_trace WHERE turn_id=%s AND attempt=%s':
            return SimpleNamespace(fetchone=lambda: (state.writer_trace,))
        if sql == 'SELECT payload FROM agent.turn_context_trace WHERE turn_id=%s':
            return SimpleNamespace(fetchall=lambda: [(state.writer_trace,)])
        if 'UPDATE agent.turn_rules_execution SET revision=revision+1,payload=%s' in sql:
            if state.rules_cas_failure:
                return SimpleNamespace(rowcount=0)
            assert args[1:] == (state.turn.turn_id, state.turn.attempt, state.rules_revision)
            state.rules_payload = args[0].obj
            state.rules_revision += 1
            return SimpleNamespace(rowcount=1)
        assert 'INSERT INTO agent.turn_rules_execution' in sql
        assert state.rules_payload is None and args[:2] == (state.turn.turn_id, state.turn.attempt)
        state.rules_inserts += 1
        state.rules_payload = args[2].obj
        return SimpleNamespace(rowcount=1)
    state.conn.execute = execute


def configure_pending_completion_storage(monkeypatch,state):
    state.completions = 0
    monkeypatch.setattr(repository, 'lock_turn', lambda conn, world, turn_id: state.turn)
    def complete(conn, **fields):
        assert conn is state.conn and state.depth == 1
        assert fields['world_id'] == state.turn.world_id and fields['turn_id'] == state.turn.turn_id
        assert fields['expected_revision'] == state.turn.revision and fields['expected_attempt'] == state.turn.attempt
        if state.turn.claim_expires_at <= state.now:
            return None
        state.turn = t.Turn.model_validate_json(state.turn.model_copy(update={
            'status': 'completed', 'revision': state.turn.revision + 1,
            'assistant_text': fields['assistant_text'], 'completion': fields['completion'],
            'graph_context_execution': fields['graph_context_execution'],
            'claim_expires_at': None, 'completed_at': state.now, 'updated_at': state.now,
        }).model_dump_json(by_alias=True))
        state.completions += 1
        return state.turn
    monkeypatch.setattr(repository, 'complete_claimed_turn', complete)


@pytest.mark.parametrize('mode',['sufficient','unknown','needed'])
def test_pending_main_build_harness_completes_app_citation_without_native_preparation_or_repeated_calls(monkeypatch,mode):
    import httpx
    import httpx2
    from types import SimpleNamespace,MethodType
    from hashlib import sha256
    from generationengine import GenerationEngineError
    from apps.live_control_server.services import build_related_pages,plan_jev_driver
    from apps.live_control_server.services.agent_turn_service import _PolicyExecutionAdapter,_turn_idempotency_key
    from apps.live_control_server.services.build_jev_harness import BuildJevHarness
    monkeypatch.setenv('TYPESAFE_JEV_API_KEY','synthetic-no-network')
    monkeypatch.setenv('OPENAI_API_KEY','synthetic-no-network')
    decisions,writers,reads=[],[],[]
    class Transport(httpx2.AsyncBaseTransport):
        async def handle_async_request(self,request):
            body=json.loads(request.content);decisions.append(body)
            coverage='source_requirement' in body['questions']
            if coverage and mode=='unknown':raise httpx2.ReadTimeout('Synthetic unknown coverage',request=request)
            keys=('saved_pages_sufficient','native_sources_required') if coverage else ('read','skip')
            chosen=keys[1] if coverage and mode=='needed' else keys[0]
            return httpx2.Response(200,request=request,json={'model':body['model'],'usage':{'input_tokens':23,'output_tokens':4},
                'answers':{name:{'type':'choice','choice':chosen,'confidence':1,'probabilities':{
                    key:float(key==chosen) for key in keys}} for name in body['questions']}})
    def reply(request):
        writers.append(json.loads(request.content))
        candidate={'answer_segments':[{'kind':'related_page_claim','text':'The cult password is “Remember the rain”.',
            'read_id':'source0'}],'limitations':[]}
        return httpx.Response(200,request=request,json={'id':'resp_main','object':'response','created_at':1,
            'model':writers[-1]['model'],'status':'completed','output':[{'type':'message','id':'msg_main',
                'role':'assistant','status':'completed','content':[{'type':'output_text','text':json.dumps(candidate),'annotations':[]}]}]})
    with pending_app_runtime_case(monkeypatch) as (state,adapter):
        def materialize(pointer):
            reads.append(pointer.document_id)
            text='Ethel dreamed of Maelthor. The cult password is “Remember the rain”.'
            return pointer.model_dump(mode='json')|{'markdown':text,'content_sha256':sha256(text.encode()).hexdigest()}
        monkeypatch.setattr(build_related_pages,'materialize',materialize)
        def forbidden(*args,**kwargs):raise AssertionError('Sufficient App evidence opened native retrieval')
        monkeypatch.setattr(plan_jev_driver,'PlanJevDriver',forbidden)
        request_id=str(uuid4())
        adapter.request=SimpleNamespace(turn_id=request_id,surface=SimpleNamespace(surface_id='build'),
            build_draft_context=None,build_write_capability=None)
        adapter.world_id,adapter.expected_conversation_id=state.turn.world_id,None
        adapter.submitted_intent=state.turn.graph_context_execution.policy.action.intent
        adapter.service,adapter.pending_build_source_preparation=state.service,None
        adapter.budget={'apiMode':'typesafe_decision','estimator':state.turn.graph_context_execution.policy.provider_input_accounting.estimator}
        adapter.stop=MethodType(_PolicyExecutionAdapter.stop,adapter)
        adapter.build_frozen_history=tuple(json.loads(state.initial_request)['state']['interaction']['history'])
        state.turn=t.Turn.model_validate(state.turn.model_copy(update={
            'idempotency_key':_turn_idempotency_key(state.turn.world_id,request_id)}))
        adapter.turn=state.turn;adapter.fence.renewer.update_turn(state.turn)
        state.writer_trace=state.trace.model_dump(mode='json',by_alias=True)
        configure_pending_rules_storage(state)
        configure_pending_completion_storage(monkeypatch,state)
        from application_state.agent_conversation.rules_authority_policy import rules_capability
        harness=BuildJevHarness(decision_transport=Transport(),writer_transport=httpx.MockTransport(reply),
            rules_capability=rules_capability(graph=True))
        harness.adapter,harness.calls,harness.timings,harness._inflight=adapter,[],[],{}
        work=SimpleNamespace(operation='answer_from_sources',selection=SimpleNamespace(paragraph_placement=None),
            _material=lambda:((),(),()))
        if mode=='unknown':
            with pytest.raises(GenerationEngineError):harness._native_completion(adapter,work)
        elif mode=='needed':
            with pytest.raises(ValueError,match='no current host owner'):harness._native_completion(adapter,work)
        else:
            completed=harness._native_completion(adapter,work)
            assert completed.status=='completed' and state.completions==1
            assert completed.completion.answer_segments[0].kind=='related_page_claim'
            row,references=stored_row(completed)
            assert repository._turn_from_row(None,row,references=references)==completed
            assert len(writers)==1 and 'Already discussed detail 59' in json.dumps(writers[0]['input'])
        assert len(decisions)==2 and len(reads)==1 and state.materialized==0
        if mode!='sufficient':assert state.completions==0 and not writers


def test_pending_native_retrieval_owner_uses_only_actual_settlement_without_repreparing_or_relabeling(monkeypatch):
    from application_state.agent_conversation import native_reads, native_retrieval
    from application_state.agent_conversation.build_pending_native import prepared_pending_source
    from application_state.agent_conversation.native_context import BuildPendingContextReceiptV1
    from application_state.agent_conversation.native_execution import BuildPendingExecutionV1
    from apps.live_control_server.services.build_pending_source import prepare_pending_native_source
    with pending_source_runtime_case(monkeypatch) as (state,adapter,source_owner):
        assert native_retrieval._action(state.turn.graph_context_execution) is None
        with pytest.raises(ValueError,match='no admitted native source settlement'):
            native_retrieval.owner(state.turn)
        assert prepare_pending_native_source(adapter)
        receipt,execution=native_retrieval.owner(state.turn)
        assert type(receipt) is BuildPendingContextReceiptV1 and type(execution) is BuildPendingExecutionV1
        assert native_reads._owner(state.turn, require_source=True) == (receipt, execution)
        native_reads.validate_execution_binding(receipt, execution)
        authority,query=prepared_pending_source(receipt,execution)
        assert authority==adapter.native_source_authority and query==adapter.native_query
        pins=native_retrieval.source_pins(receipt,execution)
        assert pins=={'source_authority_status':'available','source_revision':'observed-revision','graph_revision':'observed-revision'}
        assert native_retrieval._action(execution)==execution.policy.action
        first=native_retrieval.scope_digest(state.turn)
        assert len(first)==64 and first==native_retrieval.scope_digest(state.turn)
        assert len(state.source_prepares)==len(state.query_searches)==1 and not state.query_reopens
        assert not hasattr(receipt,'source_authority') and not hasattr(receipt,'native_query')
        assert not hasattr(execution.policy,'source_authority_sha256')
        with pytest.raises(ValueError):native_retrieval.source_pins(receipt)


@pytest.mark.parametrize('failure',['not_running','changed_text','changed_world','changed_receipt','changed_query','foreign_pair','namespace'])
def test_pending_native_retrieval_owner_refuses_mutated_or_borrowed_prepared_scope(monkeypatch,failure):
    from types import SimpleNamespace
    from application_state.agent_conversation import native_retrieval
    from apps.live_control_server.services.build_pending_source import prepare_pending_native_source
    with pending_source_runtime_case(monkeypatch) as (state,adapter,source_owner):
        assert prepare_pending_native_source(adapter)
        turn=state.turn
        if failure=='not_running':turn=turn.model_copy(update={'status':'failed'})
        elif failure=='changed_text':turn=turn.model_copy(update={'user_text':'Changed user request'})
        elif failure=='changed_world':turn=turn.model_copy(update={'world_id':'foreign'})
        elif failure=='changed_receipt':
            changed=turn.graph_context_receipt.model_copy(update={'context_receipt_sha256':'0'*64})
            turn=turn.model_copy(update={'graph_context_receipt':changed})
        elif failure=='changed_query':
            events=list(turn.graph_context_execution.events)
            events[-1]=events[-1].model_copy(update={'native_query':events[-1].native_query.model_copy(update={'question':'Another request'})})
            turn=turn.model_copy(update={'graph_context_execution':turn.graph_context_execution.model_copy(update={'events':events})})
        elif failure=='foreign_pair':
            other=pending_submission().graph_context_receipt
            turn=turn.model_copy(update={'graph_context_receipt':other})
        else:turn=SimpleNamespace(**turn.__dict__)
        with pytest.raises(ValueError):native_retrieval.owner(turn)
        from application_state.agent_conversation import native_reads
        with pytest.raises(ValueError):native_reads._owner(turn, require_source=True)
        if failure in {'changed_receipt', 'changed_query', 'foreign_pair'}:
            with pytest.raises(ValueError):
                native_reads.validate_execution_binding(
                    turn.graph_context_receipt, turn.graph_context_execution
                )
        assert len(state.source_prepares)==len(state.query_searches)==1 and not state.query_reopens


@pytest.mark.parametrize('surface',['plan','build','play'])
@pytest.mark.parametrize('unavailable',[False,True])
def test_existing_surface_native_retrieval_owner_and_pin_projection_keep_their_concrete_contract(surface,unavailable):
    from datetime import UTC,datetime,timedelta
    from application_state.agent_conversation import native_retrieval
    from application_state.agent_conversation.native_context import SurfaceNativeContextReceiptV1
    from application_state.agent_conversation.native_execution import SurfaceNativeExecutionV1
    from tests.test_surface_native_execution import component
    context,record=component(surface,unavailable=unavailable)
    sub=submission(surface).model_copy(update={'graph_context_receipt':context,'graph_context_execution':record,
        'submitted_intent_v2':record.policy.action.intent,
        'provenance':provenance_for(context.work_context).model_copy(update={
            'surface_instance_id':record.policy.action.intent.surface_instance_id}),
        'play_context_receipt':context.work_context.play_basis if surface=='play' else None})
    current=retained(sub,status='running',attempt=1,claim_expires_at=datetime.now(UTC)+timedelta(minutes=1))
    receipt,execution=native_retrieval.owner(current)
    assert type(receipt) is SurfaceNativeContextReceiptV1 and type(execution) is SurfaceNativeExecutionV1
    assert native_retrieval._action(execution)==record.policy.action
    pins=native_retrieval.source_pins(receipt)
    assert pins==native_retrieval.source_pins(receipt,execution)
    assert pins['source_authority_status']==('unavailable' if unavailable else 'available')
    assert len(native_retrieval.scope_digest(current))==64


@pytest.mark.parametrize('record_kind', ['statement', 'assertion'])
def test_pending_native_selected_records_use_actual_query_and_existing_closure(monkeypatch, record_kind):
    from uuid import uuid4
    from application_state.agent_conversation import native_reads, native_retrieval
    from application_state.agent_conversation.native_plan_assertions import object_selection_handle
    from apps.live_control_server.services.build_pending_source import prepare_pending_native_source
    from tests import test_build_source_free_routing as routing
    from tests.test_native_plan_assertions import _object_catalog_query
    from tests.test_surface_native_execution import controller, outcomes, choice
    original = routing.prepared_query
    def populated(source):
        base = original(source)
        return _object_catalog_query().model_copy(update={'authority': base.authority, 'question': base.question})
    monkeypatch.setattr(routing, 'prepared_query', populated)
    with pending_source_runtime_case(monkeypatch) as (state, adapter, _):
        assert prepare_pending_native_source(adapter)
        turn = state.turn
        receipt, execution = native_retrieval.owner(turn)
        from application_state.agent_conversation.build_pending_native import prepared_pending_source
        _, query = prepared_pending_source(receipt, execution)
        auth = controller('build', execution.policy, sequence=len(execution.events), semantic=False)
        responses = outcomes(auth, auth.sequence + 1)
        selected = choice(receipt, execution, auth, auth.sequence + 3, 'select_candidates',
            (object_selection_handle(query, query.object_matches[0].entity_id),))
        def decoded(events):
            candidate = execution.model_copy(update={'events': events})
            current = turn.model_copy(update={'graph_context_execution': candidate})
            return type(turn).model_validate_json(current.model_dump_json(by_alias=True))
        prefix = [*execution.events, auth, *responses, selected]
        selected_turn = decoded(prefix)
        assert native_retrieval.current_selection(selected_turn) == selected
        ids = ('ent:shared', 'ent:a') if record_kind == 'statement' else ('assertion:shared', 'assertion:a')
        grant = native_reads.authorize_read(selected_turn, event_id=uuid4(), record_kind=record_kind, record_ids=ids)
        granted = decoded([*prefix, grant])
        observed = native_reads.observe_read(granted, event_id=uuid4(), authorization_event_id=grant.event_id,
            reads=(), unavailable_ids=ids)
        completed = decoded([*prefix, grant, observed])
        assert completed.graph_context_execution.events[-1].status == 'partial'
        with pytest.raises(ValueError):
            native_reads.authorize_read(selected_turn, event_id=uuid4(), record_kind=record_kind, record_ids=(ids[0],))
        with pytest.raises(ValueError):
            native_reads.authorize_read(selected_turn, event_id=uuid4(), record_kind=record_kind, record_ids=('foreign',))
        with pytest.raises(ValueError):
            native_reads.observe_read(granted, event_id=uuid4(), authorization_event_id=grant.event_id,
                reads=(), unavailable_ids=(ids[0],))
        with pytest.raises(ValueError):
            decoded([*prefix, grant, observed, observed.model_copy(update={'event_id': uuid4(), 'sequence': observed.sequence + 1})])
        with pytest.raises(ValueError):
            decoded([*execution.events, auth, *responses,
                selected.model_copy(update={'controller_envelope_sha256': '0' * 64})])
        with pytest.raises(ValueError):
            decoded([*execution.events[:-1], auth.model_copy(update={'sequence': len(execution.events) - 1})])
        assert len(state.source_prepares) == len(state.query_searches) == 1 and not state.query_reopens



@contextmanager
def pending_native_dispatch_case(monkeypatch, *, select_rules=False):
    import json
    from hashlib import sha256
    from types import SimpleNamespace
    from generationengine.types import DecisionResult, ChoiceDecisionAnswer, InferenceObservation
    from application_state.agent_conversation import native_retrieval
    from application_state.agent_conversation.build_decision_context import identity
    from application_state.agent_conversation.jev_retrieval_contract import NativeBuildRetrievalDecisionInputV3, prepare_decision
    from apps.live_control_server.services.build_pending_source import prepare_pending_native_source
    from tests.test_surface_native_execution import controller
    with pending_source_runtime_case(monkeypatch) as (state, adapter, _):
        assert prepare_pending_native_source(adapter)
        receipt, execution = native_retrieval.owner(state.turn)
        auth = controller('build', execution.policy, sequence=len(execution.events), semantic=False)
        from application_state.agent_conversation.plan_jev_rules_lookup import rules_candidate
        parent = NativeBuildRetrievalDecisionInputV3(request_id=auth.decision_request_id,
            parent_attempt_id=auth.provider_attempt_id, scope_sha256=native_retrieval.scope_digest(state.turn),
            question=state.turn.user_text, candidates=(rules_candidate(),) if select_rules else (),
            allowed_operations=('select_candidates', 'finish_retrieval') if select_rules else ('discover_more', 'finish_retrieval'),
            **native_retrieval.source_pins(receipt, execution))
        prepared = prepare_decision(parent, controller_accounting=native_retrieval.controller_accounting(execution))
        raw = json.dumps({'model': prepared.model, 'state': prepared.state, 'questions': {
            row.name: {'type': 'choice', 'instructions': row.question, 'criteria': dict.fromkeys(row.options)}
            for row in prepared.questions}})
        envelope = sha256(raw.encode()).hexdigest()
        auth = auth.model_copy(update={
            'parent_request_sha256': parent.digest,
            'envelope_sha256': envelope, 'tool_schema_sha256': t.canonical_sha256([]),
            'build_context': auth.build_context.model_copy(update={'dispatch_identity_sha256': identity(
                envelope_sha256=envelope, provider=auth.provider, model=auth.model, api_mode=auth.api_mode,
                context_mode=auth.build_context.context_mode)})})
        proof = {'parent_request_json': parent.model_dump_json(by_alias=True), 'request_json': raw}
        result = DecisionResult(answers={row.name: ChoiceDecisionAnswer(
            selected='include' if row.name.startswith('candidate_') else 'finish_retrieval',
            probabilities={key: .9 if key == ('include' if row.name.startswith('candidate_') else 'finish_retrieval') else .1 for key in row.options})
            for row in prepared.questions}, observation=InferenceObservation(provider='typesafe',
                resolved_model='jev-1.14.0', response_model='jev-1.14.0', latency_ms=1,
                retry_count=0, state='completed', provider_attempt_count=1))
        response = result.model_dump_json(by_alias=True)
        state.native_trace = {'world_id': state.turn.world_id, 'conversation_id': str(state.turn.conversation_id),
            'turn_id': str(state.turn.turn_id), 'attempt': state.turn.attempt, 'capture_status': 'recording',
            'observations': [{'kind': 'context_snapshot', 'stage': 'after', 'materials': [{
                'item_id': f'unvalidated-native-retrieval-result:{auth.provider_attempt_id}', 'text': response}]}]}
        state.native_prompt = {'kind': 'prompt_reference', 'sequence': 0, 'elapsed_ms': 0,
            'evidence_id': str(uuid4()), 'provider_attempt_id': str(auth.provider_attempt_id),
            'provider': auth.provider, 'model': auth.model, 'api_mode': auth.api_mode,
            'serializer_version': auth.serializer_version, 'payload_sha256': auth.envelope_sha256,
            'payload_utf8_bytes': len(raw.encode())}
        state.prompt_count = 1
        def query(sql, args):
            if sql == 'SELECT 1 FROM agent.turn_retry WHERE predecessor_id=%s': return state.leaf_query(sql, args)
            assert state.depth == 1
            if sql == 'SELECT payload FROM agent.turn_context_trace WHERE turn_id=%s':
                assert args == (state.turn.turn_id,)
                return SimpleNamespace(fetchall=lambda: [({'observations': [state.native_prompt] * state.prompt_count},)])
            assert sql == 'SELECT payload FROM agent.turn_context_trace WHERE turn_id=%s AND attempt=%s'
            assert args == (state.turn.turn_id, state.turn.attempt)
            return SimpleNamespace(fetchone=lambda: (state.native_trace,))
        state.conn.execute = query
        def call(method, **kwargs):
            return getattr(state.service, method)(state.turn.world_id, state.turn.conversation_id, state.turn.turn_id,
                expected_revision=state.turn.revision, expected_attempt=state.turn.attempt,
                authorize_current_access=state.authorize, **kwargs)
        yield state, auth, proof, response, call


def test_pending_native_dispatch_selection_join_exact_bytes_capture_and_one_shot_entry(monkeypatch):
    from hashlib import sha256
    from tests.test_surface_native_execution import outcomes, choice
    with pending_native_dispatch_case(monkeypatch) as (state, auth, proof, response, call):
        before = state.persisted
        assert call('authorize_pending_native_retrieval', authorization=auth, prepared_input_proof=proof)[1]
        assert call('authorize_pending_native_retrieval', authorization=auth, prepared_input_proof=proof)[1] is False
        entry, outcome = outcomes(auth, len(state.turn.graph_context_execution.events))
        outcome = outcome.model_copy(update={'response_sha256': sha256(response.encode()).hexdigest()})
        assert call('enter_pending_app_page_sdk', outcome=entry, prepared_request_json=proof['request_json'])[1]
        assert call('enter_pending_app_page_sdk', outcome=entry, prepared_request_json=proof['request_json'])[1] is False
        assert call('record_pending_app_controller_outcome', outcome=outcome)[1]
        selected = choice(state.turn.graph_context_receipt, state.turn.graph_context_execution, auth,
            len(state.turn.graph_context_execution.events), 'finish_retrieval').model_copy(update={
                'controller_response_sha256': sha256(response.encode()).hexdigest()})
        evidence = proof | {'response_json': response}
        assert call('record_pending_native_selection', selection=selected, producer_proof=evidence)[1]
        assert call('record_pending_native_selection', selection=selected, producer_proof=evidence)[1] is False
        assert state.persisted == before + 4
        assert len(state.source_prepares) == len(state.query_searches) == 1 and not state.query_reopens


@pytest.mark.parametrize('failure', ['wire', 'parent', 'pointer', 'access', 'expired', 'successor', 'cas', 'access_changed'])
def test_pending_native_authorization_refuses_bad_proof_or_lost_current_fence(monkeypatch, failure):
    from datetime import timedelta
    from application_state.errors import ApplicationStateConflictError, ApplicationStateValidationError
    with pending_native_dispatch_case(monkeypatch) as (state, auth, proof, _, call):
        before = state.persisted
        if failure == 'wire': proof = proof | {'request_json': proof['request_json'] + ' '}
        elif failure == 'parent': proof = proof | {'parent_request_json': proof['parent_request_json'].replace(state.turn.user_text, 'Changed request')}
        elif failure == 'pointer': state.pointer = state.pointer.model_copy(update={'revision': state.pointer.revision + 1})
        elif failure == 'access': state.denied = True
        elif failure == 'expired': state.now += timedelta(hours=1)
        elif failure == 'successor': state.successor = True
        elif failure == 'cas': state.cas_failure = True
        elif failure == 'access_changed':
            original = state.authorize
            calls = []
            def changed(conn, turn, pages):
                calls.append(1)
                return original(conn, turn, pages) and len(calls) == 1
            state.authorize = changed
        with pytest.raises((ApplicationStateConflictError, ApplicationStateValidationError)):
            call('authorize_pending_native_retrieval', authorization=auth, prepared_input_proof=proof)
        assert state.persisted == before
        assert not any(e.event_id == auth.event_id for e in state.turn.graph_context_execution.events)


@pytest.mark.parametrize('failure', ['missing_prompt', 'changed_prompt', 'wire', 'access', 'expired'])
def test_pending_native_sdk_entry_refuses_missing_capture_or_lost_access(monkeypatch, failure):
    from datetime import timedelta
    from application_state.errors import ApplicationStateConflictError, ApplicationStateValidationError
    from tests.test_surface_native_execution import outcomes
    with pending_native_dispatch_case(monkeypatch) as (state, auth, proof, _, call):
        call('authorize_pending_native_retrieval', authorization=auth, prepared_input_proof=proof)
        before = state.persisted
        entry = outcomes(auth, len(state.turn.graph_context_execution.events))[0]
        if failure == 'missing_prompt': state.prompt_count = 0
        elif failure == 'changed_prompt': state.native_prompt['payload_sha256'] = '0' * 64
        elif failure == 'wire': proof = proof | {'request_json': proof['request_json'] + ' '}
        elif failure == 'access': state.denied = True
        else: state.now += timedelta(hours=1)
        with pytest.raises((ApplicationStateConflictError, ApplicationStateValidationError)):
            call('enter_pending_app_page_sdk', outcome=entry, prepared_request_json=proof['request_json'])
        assert state.persisted == before
        assert not any(e.event_id == entry.event_id for e in state.turn.graph_context_execution.events)


@pytest.mark.parametrize('failure', ['capture', 'foreign_trace', 'response', 'selection', 'access', 'expired', 'cas', 'unknown', 'generic'])
def test_pending_native_selection_refuses_unbound_output_and_lost_fence(monkeypatch, failure):
    from datetime import timedelta
    from hashlib import sha256
    from application_state.errors import ApplicationStateConflictError, ApplicationStateValidationError
    from tests.test_surface_native_execution import outcomes, choice
    with pending_native_dispatch_case(monkeypatch) as (state, auth, proof, response, call):
        call('authorize_pending_native_retrieval', authorization=auth, prepared_input_proof=proof)
        entry, outcome = outcomes(auth, len(state.turn.graph_context_execution.events))
        outcome = outcome.model_copy(update={'response_sha256': sha256(response.encode()).hexdigest()})
        call('enter_pending_app_page_sdk', outcome=entry, prepared_request_json=proof['request_json'])
        if failure == 'unknown': outcome = outcome.model_copy(update={'outcome': 'outcome_unknown'})
        call('record_pending_app_controller_outcome', outcome=outcome)
        selected = choice(state.turn.graph_context_receipt, state.turn.graph_context_execution, auth,
            len(state.turn.graph_context_execution.events), 'finish_retrieval').model_copy(update={
                'controller_response_sha256': sha256(response.encode()).hexdigest()})
        evidence = proof | {'response_json': response}
        before = state.persisted
        if failure == 'capture': state.native_trace['observations'] = []
        elif failure == 'foreign_trace': state.native_trace['world_id'] = 'foreign'
        elif failure == 'response': evidence['response_json'] += ' '
        elif failure == 'selection': selected = selected.model_copy(update={'operation': 'discover_more'})
        elif failure == 'access': state.denied = True
        elif failure == 'expired': state.now += timedelta(hours=1)
        elif failure == 'cas': state.cas_failure = True
        with pytest.raises((ApplicationStateConflictError, ApplicationStateValidationError)):
            if failure == 'generic':
                from application_state.agent_conversation import service as service_module
                monkeypatch.setattr(service_module, '_execution_append_transaction', lambda measure: state.uow())
                state.service._append_graph_execution_event(state.turn.world_id, state.turn.conversation_id,
                    state.turn.turn_id, expected_revision=state.turn.revision, expected_attempt=1,
                    event=selected, duplicate_key='event_id', plan_jev_selection_proof=evidence)
            else:
                call('record_pending_native_selection', selection=selected, producer_proof=evidence)
        assert state.persisted == before
        assert not any(e.event_id == selected.event_id for e in state.turn.graph_context_execution.events)


@pytest.mark.parametrize('operation', ['select_candidates', 'finish_retrieval'])
@pytest.mark.parametrize('failure', [None, 'unknown_choice', 'access'])
def test_pending_native_runtime_actual_sdk_preserves_full_dialogue_and_prepared_scope(monkeypatch, operation, failure):
    import asyncio
    import httpx2
    from application_state.agent_conversation.jev_retrieval_contract import RetrievalCandidate
    from application_state.agent_conversation.native_retrieval import current_selection
    from apps.live_control_server.services.build_pending_source import prepare_pending_native_source
    from apps.live_control_server.services.build_pending_native_retrieval import PendingNativeRetrievalDriver
    from apps.live_control_server.services.build_jev_harness import BuildJevHarness
    monkeypatch.setenv('TYPESAFE_JEV_API_KEY', 'synthetic-only')
    calls = []
    class Transport(httpx2.AsyncBaseTransport):
        async def handle_async_request(self, request):
            body = json.loads(request.content)
            calls.append(body)
            answers = {}
            for name, question in body['questions'].items():
                chosen = ('include' if operation == 'select_candidates' else 'exclude') if name.startswith('candidate_') else 'finish_retrieval'
                if failure == 'unknown_choice': chosen = 'not_offered'
                answers[name] = {'type': 'choice', 'choice': chosen, 'confidence': 1,
                    'probabilities': {key: float(key == chosen) for key in question['criteria']}}
            if failure == 'access': state.denied = True
            return httpx2.Response(200, request=request, json={'model': body['model'],
                'usage': {'input_tokens': 23, 'output_tokens': 4}, 'answers': answers})
    with pending_source_runtime_case(monkeypatch) as (state, source_adapter, _):
        assert prepare_pending_native_source(source_adapter)
        with pending_app_runtime_case(monkeypatch, seed=state) as (_, adapter):
            dialogue = tuple({'role': role, 'content': f'{role} full captured context {i}'}
                for i in range(60) for role in ('user', 'assistant'))
            candidates = (RetrievalCandidate(handle='native-object:host-only-choice', label='Maelthor',
                kind='Native Graph object; open its complete admitted support'),)
            driver = PendingNativeRetrievalDriver(adapter, candidates, dialogue=dialogue,
                allowed_operations=('select_candidates', 'finish_retrieval'))
            harness = BuildJevHarness(decision_transport=Transport(), accounting=adapter._build_jev_accounting)
            harness.adapter, harness.calls, harness.timings, harness._inflight = adapter, [], [], {}
            if failure:
                from generationengine import GenerationEngineError
                from application_state.errors import ApplicationStateError
                with pytest.raises((GenerationEngineError, ApplicationStateError)):
                    asyncio.run(harness._decide(adapter, driver))
                assert driver.selection is None and len(calls) == 1
                replacement = PendingNativeRetrievalDriver(adapter, candidates, dialogue=dialogue,
                    allowed_operations=('select_candidates', 'finish_retrieval'))
                with pytest.raises((GenerationEngineError, ApplicationStateError, ValueError)):
                    asyncio.run(harness._decide(adapter, replacement))
                assert replacement.selection is None and len(calls) == 1
                assert len(state.source_prepares) == len(state.query_searches) == 1 and not state.query_reopens
                return
            asyncio.run(harness._decide(adapter, driver))
            assert len(calls) == 1
            assert calls[0]['state']['dialogue_reference'] == list(dialogue)
            raw = json.dumps(calls[0])
            for host in (driver.receipt.context_receipt_sha256, driver.before.execution_policy_sha256,
                         str(driver.parent.request_id), str(driver.parent.parent_attempt_id),
                         driver.parent.scope_sha256, driver.parent.source_revision, candidates[0].handle):
                assert host not in raw
            selected = current_selection(adapter.fence.turn)
            assert selected == driver.selection and selected.operation == operation
            assert selected.selected_handles == ([candidates[0].handle] if operation == 'select_candidates' else [])
            assert selected.actual_input_tokens == 23 and selected.actual_output_tokens == 4
            assert len(state.source_prepares) == len(state.query_searches) == 1 and not state.query_reopens


@pytest.mark.parametrize('mode', ['complete', 'advanced_epoch', 'unavailable', 'foreign_authority', 'changed_text'])
def test_pending_native_direct_source_uses_settlement_and_existing_exact_body_validator(monkeypatch, mode):
    from application_state.agent_conversation import native_corpus as bodies, native_reads, native_retrieval
    from apps.live_control_server.services.build_pending_source import prepare_pending_native_source
    from tests.test_surface_native_execution import controller, outcomes, choice
    from tests.test_native_corpus_source_access import lane, admit, BODY, GM
    from apps.live_control_server.integrations.dungeonmind import native_corpus_source as core
    memory = lane.__wrapped__()
    admit(memory)
    context = core.prepare_native_source_context(managed_world_id=memory.bound.managed_world_id,
        principal=GM, repository=memory.repo, resolve_identity=lambda _: memory.bound)
    snapshot = core.capture_native_sources(managed_world_id=memory.bound.managed_world_id, principal=GM, prepared=context)
    with pending_source_runtime_case(monkeypatch) as (state, adapter, _):
        assert prepare_pending_native_source(adapter)
        receipt, execution = native_retrieval.owner(state.turn)
        from application_state.agent_conversation.build_pending_native import prepared_pending_source
        authority, _ = prepared_pending_source(receipt, execution)
        catalog = bodies.build_native_body_catalog(authority, snapshot.members[0], BODY)
        member = catalog.source
        target = {'source_artifact_id': member.artifact.source_artifact_id,
            'source_revision_id': member.revision.source_revision_id, 'content_sha256': member.revision.content_sha256}
        handle = bodies.native_direct_source_handle(authority, **target)
        auth = controller('build', execution.policy, sequence=len(execution.events), semantic=False)
        selected = choice(receipt, execution, auth, auth.sequence + 3, 'select_candidates', (handle,))
        def decoded(events):
            candidate = state.turn.model_copy(update={'graph_context_execution': execution.model_copy(update={'events': events})})
            return t.Turn.model_validate_json(candidate.model_dump_json(by_alias=True))
        prefix = [*execution.events, auth, *outcomes(auth, auth.sequence + 1), selected]
        current = decoded(prefix)
        grants = native_reads.authorize_direct_sources_locked(current, grants=({'event_id': uuid4(), **target},))
        assert len(grants) == 1 and grants[0].authority == authority
        grant, = grants
        current = decoded([*prefix, grant])
        callbacks = []
        def read(actual):
            callbacks.append(actual)
            assert actual == grant
            if mode == 'unavailable': return None
            effective = authority.model_copy(update={'acquisition_epoch': authority.acquisition_epoch + 1}) if mode == 'advanced_epoch' else authority
            if mode == 'foreign_authority': effective = authority.model_copy(update={'revision_id': 'foreign'})
            result_catalog = bodies.build_native_body_catalog(effective, snapshot.members[0], BODY)
            excerpt = bodies.select_native_full_document(result_catalog, BODY)
            if mode == 'changed_text': excerpt = excerpt.model_copy(update={'text': BODY + 'unsupported'})
            return result_catalog, excerpt
        if mode in {'foreign_authority', 'changed_text'}:
            with pytest.raises(ValueError):
                observed = native_reads.observe_direct_source_locked(current, event_id=uuid4(), authorization_event_id=grant.event_id, read=read)
                decoded([*prefix, grant, observed])
        else:
            observed = native_reads.observe_direct_source_locked(current, event_id=uuid4(), authorization_event_id=grant.event_id, read=read)
            completed = decoded([*prefix, grant, observed])
            assert (completed.graph_context_execution.events[-1].excerpt is None) == (mode == 'unavailable')
            with pytest.raises(ValueError):
                native_reads.observe_direct_source_locked(completed, event_id=uuid4(), authorization_event_id=grant.event_id, read=read)
        assert callbacks == [grant]
        with pytest.raises(ValueError):
            native_reads.authorize_direct_sources_locked(decoded(prefix), grants=({'event_id': uuid4(), **(target | {'content_sha256': '0' * 64})},))
        assert len(state.source_prepares) == len(state.query_searches) == 1 and not state.query_reopens


@pytest.mark.parametrize('record_kind', ['direct', 'statement', 'assertion'])
@pytest.mark.parametrize('failure', [None, 'pointer', 'access', 'expired', 'successor', 'access_after', 'expiry_after', 'cas', 'grant', 'generic', 'producer'])
def test_pending_native_materialization_checks_live_owner_and_never_reopens_replay(monkeypatch, record_kind, failure):
    from datetime import timedelta
    from application_state.agent_conversation import native_corpus as bodies, native_retrieval
    from application_state.agent_conversation.native_plan_assertions import object_selection_handle
    from application_state.agent_conversation.build_pending_native import prepared_pending_source
    from application_state.errors import ApplicationStateError
    from apps.live_control_server.services.build_pending_source import prepare_pending_native_source
    from tests import test_build_source_free_routing as routing
    from tests.test_native_plan_assertions import _object_catalog_query
    from tests.test_surface_native_execution import controller, outcomes, choice
    original = routing.prepared_query
    def populated(source):
        base = original(source)
        return _object_catalog_query().model_copy(update={'authority': base.authority, 'question': base.question})
    monkeypatch.setattr(routing, 'prepared_query', populated)
    with pending_source_runtime_case(monkeypatch) as (state, adapter, _):
        assert prepare_pending_native_source(adapter)
        receipt, execution = native_retrieval.owner(state.turn)
        authority, query = prepared_pending_source(receipt, execution)
        target = {'source_artifact_id': 'fixture-artifact', 'source_revision_id': 'fixture-revision', 'content_sha256': 'a' * 64}
        handle = bodies.native_direct_source_handle(authority, **target) if record_kind == 'direct' else object_selection_handle(query, 'A')
        auth = controller('build', execution.policy, sequence=len(execution.events), semantic=False)
        selected = choice(receipt, execution, auth, auth.sequence + 3, 'select_candidates', (handle,))
        state.turn = t.Turn.model_validate_json(state.turn.model_copy(update={'graph_context_execution':
            execution.model_copy(update={'events': [*execution.events, auth, *outcomes(auth, auth.sequence + 1), selected]})
        }).model_dump_json(by_alias=True))
        def call(method, **kwargs):
            return getattr(state.service, method)(state.turn.world_id, state.turn.conversation_id, state.turn.turn_id,
                expected_revision=state.turn.revision, expected_attempt=1, authorize_current_access=state.authorize, **kwargs)
        ids = ('ent:shared', 'ent:a') if record_kind == 'statement' else ('assertion:shared', 'assertion:a')
        if record_kind == 'direct':
            grant_id = uuid4()
            assert call('authorize_pending_native_direct_sources', grants=({'event_id': grant_id, **target},))[1]
        else:
            grant_id = uuid4()
            assert call('authorize_pending_native_read', event_id=grant_id, record_kind=record_kind, record_ids=ids)[1]
        grant = state.turn.graph_context_execution.events[-1]
        callbacks = []
        def read(actual):
            assert state.depth == 1 and actual == grant and type(actual) is type(grant)
            callbacks.append(actual)
            if failure == 'access_after': state.denied = True
            if failure == 'expiry_after': state.now += timedelta(hours=1)
            return None if record_kind == 'direct' else ((), ids)
        if failure == 'pointer': state.pointer = state.pointer.model_copy(update={'revision': state.pointer.revision + 1})
        elif failure == 'access': state.denied = True
        elif failure == 'expired': state.now += timedelta(hours=1)
        elif failure == 'successor': state.successor = True
        elif failure == 'cas': state.cas_failure = True
        before = state.persisted
        observation_id = uuid4()
        def observe():
            return call('observe_pending_native_direct_source' if record_kind == 'direct' else 'observe_pending_native_read',
                event_id=observation_id, authorization_event_id=uuid4() if failure == 'grant' else grant_id, read=read)
        if failure is None:
            assert observe()[1]
            assert observe()[1] is False and callbacks == [grant]
            assert state.persisted == before + 1
            observation_id = uuid4()
            with pytest.raises(ApplicationStateError): observe()
            assert callbacks == [grant]
        else:
            with pytest.raises(ApplicationStateError):
                if failure == 'generic':
                    from application_state.agent_conversation import service as service_module
                    monkeypatch.setattr(service_module, '_execution_append_transaction', lambda measure: state.uow())
                    if record_kind == 'direct':
                        state.service.observe_native_direct_source(state.turn.world_id, state.turn.conversation_id,
                            state.turn.turn_id, expected_revision=state.turn.revision, expected_attempt=1,
                            event_id=observation_id, authorization_event_id=grant_id, read=read)
                    else:
                        state.service.observe_native_read(state.turn.world_id, state.turn.conversation_id,
                            state.turn.turn_id, expected_revision=state.turn.revision, expected_attempt=1,
                            event_id=observation_id, authorization_event_id=grant_id, reads=(), unavailable_ids=ids)
                elif failure == 'producer':
                    call('_pending_native_read_operation', producer=lambda *args: pytest.fail('generic producer invoked'))
                else: observe()
            assert state.persisted == before
            assert len(callbacks) == int(failure in {'access_after', 'expiry_after', 'cas'})
        assert len(state.source_prepares) == len(state.query_searches) == 1 and not state.query_reopens


@pytest.mark.parametrize('mode', ['complete', 'later_head', 'binding_changed', 'principal_lost', 'app_access_lost', 'section', 'section_binding_changed', 'section_access_lost', 'navigation_direct', 'navigation_denied', 'section_navigation', 'section_navigation_epoch', 'section_capture_scope', 'section_capture_epoch', 'loop_direct', 'section_loop', 'loop_invalid', 'loop_objects', 'loop_objects_context', 'loop_selection', 'loop_selection_history', 'loop_selection_access', 'loop_selection_unknown', 'loop_selection_main', 'loop_selection_main_object'])
def test_pending_guarded_direct_read_uses_public_core_with_original_real_authority(monkeypatch, mode):
    from types import SimpleNamespace
    from application_state.agent_conversation import native_corpus as bodies
    from application_state.errors import ApplicationStateError
    from apps.live_control_server.integrations.dungeonmind import native_corpus_source as core
    from apps.live_control_server.services import native_graph_reads
    from apps.live_control_server.services.build_pending_source import PendingBuildSourcePreparation, prepare_pending_native_source
    from apps.live_control_server.services.agent_turn_service import _ClaimFence
    from dungeonmind.application.vnext import list_admitted_native_text_sources
    from tests.test_native_corpus_source_access import lane, admit, BODY
    from tests.test_surface_native_execution import controller, outcomes, choice
    memory = lane.__wrapped__()
    writer_mode = mode.startswith('loop_selection')
    state = pending_page_dispatch_harness(monkeypatch)[0] if writer_mode else settlement_harness(monkeypatch, with_source=True)[0]
    section_mode = mode.startswith('section')
    source_body = ('# Maelthor\n\n' + state.turn.user_text + '\n\n# Elsewhere\n\nOther material.\n' if section_mode
                   else '# Check\n\nThe check revealed that Maelthor guards the ferry.\n' if mode in {'loop_objects', 'loop_objects_context', 'loop_selection_main_object'} else BODY)
    admission = admit(memory, body=source_body, multiple=mode in {'loop_objects', 'loop_objects_context', 'loop_selection_main_object'})
    if mode in {'loop_objects', 'loop_objects_context', 'loop_selection_main_object'}:
        from worldkeeper.application import contracts as wk
        from apps.live_control_server.integrations.worldkeeper import registry_standing_consumer as transport
        from graph_memory.vnext.domain_runtime import GM_LABEL, CAMPAIGN_SCOPE_AXIS
        from tests.test_native_corpus_source_access import NOW
        support_ref = admission.bindings[-1].evidence_ref_id
        if mode in {'loop_objects', 'loop_selection_main_object'}:
            from hashlib import sha256
            from dungeonmind.application.vnext import publish_native_source_evidence_extension
            from dungeonmind.contracts.vnext.native_source import NativeSourceEvidenceExtensionV1
            raw = source_body.encode()
            extension = publish_native_source_evidence_extension(repository=memory.repo,
                domain_contract=memory.domain, semantic_profile=memory.profile, audience_labels=(GM_LABEL,),
                request=NativeSourceEvidenceExtensionV1(space_id='world:test', extension_id='pending-object-support',
                    original_admission_id=admission.admission_id, source_artifact_id=admission.source_artifact_id,
                    source_revision_id=admission.source_revision_id, expected_body_sha256=sha256(raw).hexdigest(),
                    expected_parent_revision_id=memory.repo.get_head('world:test').head_revision_id,
                    expected_source_authority_epoch=memory.repo.open_native_source_view('world:test').epoch,
                    created_at=NOW, spans=[dict(client_ref='fact-support', evidence_role='support', start_byte=0,
                        end_byte=len(raw), expected_slice_sha256=sha256(raw).hexdigest())]))
            support_ref = extension.bindings[0].evidence_ref_id
        metadata = wk.AssertionMetadata(scope=(wk.ScopeBinding(CAMPAIGN_SCOPE_AXIS, 'c1'),),
            visibility=wk.Visibility('labels_any', (GM_LABEL,)), epistemic_basis='asserted',
            claim_mode='dungeonbuddy.claim:fact', standing='established',
            evidence_ref_ids=(support_ref,), temporal_scope=wk.TemporalScope(kind='unknown'))
        runtime = transport.runtime(memory.repo, memory.domain, memory.profile, now=NOW, operation_id='pending-native-object')
        runtime.commit_prepared_change(runtime.prepare_change(wk.WorldChangeIntent('world:test', 'fixture', (
            wk.CreateObject('check', (wk.CreateFact('name', 'dnd5e:name', wk.LiteralFactValue('check'), metadata),
                wk.CreateFact('summary', 'dnd5e:summary', wk.LiteralFactValue('The check revealed that Maelthor guards the ferry.'), metadata))),
        ))), confirmed_by='pending-core-test')
    memory.bound = SimpleNamespace(**(vars(memory.bound) | {'managed_world_id': state.turn.world_id}))
    principal = SimpleNamespace(role='gm', managed_world_id=state.turn.world_id)
    observation = core.observe_build_source_pointer(managed_world_id=state.turn.world_id,
        principal=principal, repository=memory.repo, resolve_identity=lambda _: memory.bound,
        defer_head=mode == "loop_selection_main_object")
    original_receipt = state.turn.graph_context_receipt
    payload = original_receipt.model_dump(mode='json', by_alias=True)
    payload.pop('context_receipt_sha256')
    receipt = seal_pending_receipt(payload | {'source_observation': observation.model_dump(mode='json', by_alias=True)})
    original_execution = state.turn.graph_context_execution
    policy = original_execution.policy.model_copy(update={'source_observation_sha256': t.canonical_sha256(observation)})
    events = list(original_execution.events)
    if writer_mode:
        events[-1] = events[-1].model_copy(update={'pending_context_receipt_sha256': receipt.context_receipt_sha256, 'pages': ()})
    state.turn = t.Turn.model_validate_json(state.turn.model_copy(update={'graph_context_receipt': receipt,
        'graph_context_execution': pending_execution(receipt, policy, events)}).model_dump_json(by_alias=True))
    prepares, searches, opens = [], [], []
    def prepare(world, actual_principal, *, revision_id, resolve_identity):
        assert state.depth == 0 and actual_principal is principal
        prepares.append(revision_id)
        context = core.prepare_native_source_context(managed_world_id=world, principal=actual_principal,
            revision_id=revision_id, repository=memory.repo, resolve_identity=resolve_identity)
        return context, context.authority
    def resolve_query(turn, context):
        assert state.depth == 0
        searches.append(turn.user_text)
        return native_graph_reads.prepare_query(turn.world_id, turn.user_text, principal,
            source_context=context, resolve_binding=lambda _: memory.bound)
    owner = PendingBuildSourcePreparation(world_id=state.turn.world_id, principal=principal,
        app_access=state.authorize, prepare_source=prepare, resolve_query=resolve_query,
        resolve_identity=lambda _: memory.bound)
    fence = _ClaimFence(state.service, state.turn, pending_build_access=state.authorize)
    adapter = SimpleNamespace(turn=state.turn, fence=fence, native_corpus_context=None,
        native_source_authority=None, native_query_context=None, native_query=None,
        pending_build_source_preparation=owner,
        _broker_receipt=lambda: fence.turn.graph_context_receipt,
        _broker_execution=lambda: fence.turn.graph_context_execution)
    actual_open = core.open_admitted_native_text
    def opened(*args, **kwargs):
        opens.append(1)
        return actual_open(*args, **kwargs)
    monkeypatch.setattr(core, 'open_admitted_native_text', opened)
    try:
        assert prepare_pending_native_source(adapter)
        assert not opens and len(prepares) == len(searches) == 1
        context, authority = adapter.native_corpus_context, adapter.native_source_authority
        item = list_admitted_native_text_sources(context.access).sources[0]
        target = dict(source_artifact_id=item.source_artifact.source_artifact_id,
            source_revision_id=item.source_revision.source_revision_id, content_sha256=item.source_revision.content_sha256)
        def call(method, **kwargs):
            return getattr(state.service, method)(state.turn.world_id, state.turn.conversation_id, state.turn.turn_id,
                expected_revision=state.turn.revision, expected_attempt=1, authorize_current_access=state.authorize, **kwargs)
        def choose(handle):
            execution = state.turn.graph_context_execution
            auth = controller('build', execution.policy, sequence=len(execution.events), semantic=False)
            selected = choice(receipt, execution, auth, auth.sequence + 3, 'select_candidates', (handle,))
            state.turn = t.Turn.model_validate_json(state.turn.model_copy(update={'graph_context_execution':
                execution.model_copy(update={'events': [*execution.events, auth, *outcomes(auth, auth.sequence + 1), selected]})
            }).model_dump_json(by_alias=True))
        if writer_mode or mode in {'loop_direct', 'section_loop', 'loop_invalid', 'loop_objects', 'loop_objects_context'}:
            import asyncio
            import httpx2
            from generationengine import GenerationEngineError
            from apps.live_control_server.services.build_pending_native_retrieval import run_pending_native_retrieval
            from apps.live_control_server.services.build_jev_harness import BuildJevHarness
            monkeypatch.setenv('TYPESAFE_JEV_API_KEY', 'synthetic-only')
            calls = []
            class Transport(httpx2.AsyncBaseTransport):
                async def handle_async_request(self, request):
                    body = json.loads(request.content)
                    step = len(calls)
                    calls.append(body)
                    if writer_mode and 'sources' in body['state']:
                        return httpx2.Response(200, request=request, json={'model': body['model'],
                            'usage': {'input_tokens': 31, 'output_tokens': 5}, 'answers': {
                                key: {'type': 'choice', 'choice': 'not_offered' if mode == 'loop_selection_unknown' else 'direct_support',
                                    'confidence': 1, 'probabilities': {choice: float(choice == 'direct_support') for choice in question['criteria']}}
                                for key, question in body['questions'].items()}})
                    wanted = ('Native Graph object' if mode in {'loop_objects', 'loop_objects_context', 'loop_selection_main_object'} and step == 0
                              else 'Explicit admitted full-source read' if mode not in {'section_loop', 'loop_objects', 'loop_objects_context'} and step == 0
                              else 'Source lexical navigation' if mode == 'section_loop' and step == 0
                              else 'Exact source section' if mode == 'section_loop' and step == 1 else None)
                    offered = body['state'].get('candidates', [])
                    pick = next((i for i, row in enumerate(offered) if wanted and row['kind'].startswith(wanted)), None)
                    if wanted: assert pick is not None
                    answers = {}
                    for name, question in body['questions'].items():
                        chosen = ('include' if name == f'candidate_{pick}' else 'exclude') if name.startswith('candidate_') else 'finish_retrieval'
                        if mode == 'loop_invalid': chosen = 'not_offered'
                        answers[name] = {'type': 'choice', 'choice': chosen, 'confidence': 1,
                            'probabilities': {key: float(key == chosen) for key in question['criteria']}}
                    return httpx2.Response(200, request=request, json={'model': body['model'],
                        'usage': {'input_tokens': 23, 'output_tokens': 4}, 'answers': answers})
            with pending_app_runtime_case(monkeypatch, seed=state,
                    initial_request_json=state.initial_request if writer_mode else None) as (_, runtime_adapter):
                runtime_adapter.native_corpus_context = context
                runtime_adapter.native_source_authority = authority
                runtime_adapter.native_query_context = adapter.native_query_context
                runtime_adapter.native_query = adapter.native_query
                runtime_adapter.request.message = state.turn.user_text
                dialogue = tuple({'role': role, 'content': f'{role} captured context {i}'}
                    for i in range(60) for role in ('user', 'assistant'))
                harness = BuildJevHarness(decision_transport=Transport(), accounting=runtime_adapter._build_jev_accounting)
                harness.adapter, harness.calls, harness.timings, harness._inflight = runtime_adapter, [], [], {}
                if mode in {'loop_selection_main', 'loop_selection_main_object'}:
                    import httpx
                    from types import MethodType
                    from apps.live_control_server.services.agent_turn_service import _PolicyExecutionAdapter, _turn_idempotency_key
                    from application_state.agent_conversation.rules_authority_policy import rules_capability
                    nonce = str(uuid4())
                    runtime_adapter.request = SimpleNamespace(turn_id=nonce, surface=SimpleNamespace(surface_id='build'),
                        message=state.turn.user_text, build_draft_context=None, build_write_capability=None)
                    runtime_adapter.world_id, runtime_adapter.expected_conversation_id = state.turn.world_id, None
                    runtime_adapter.submitted_intent = state.turn.graph_context_execution.policy.action.intent
                    runtime_adapter.service = state.service
                    runtime_adapter.budget['estimator'] = state.turn.graph_context_execution.policy.provider_input_accounting.estimator
                    runtime_adapter.stop = MethodType(_PolicyExecutionAdapter.stop, runtime_adapter)
                    state.turn = t.Turn.model_validate_json(state.turn.model_copy(update={
                        'idempotency_key': _turn_idempotency_key(state.turn.world_id, nonce)}).model_dump_json(by_alias=True))
                    runtime_adapter.turn = state.turn
                    runtime_adapter.fence.renewer.update_turn(state.turn)
                    runtime_adapter.build_frozen_history = json.loads(state.initial_request)['state']['interaction']['history']
                    runtime_adapter.pending_build_source_preparation = owner
                    owner.reopen_query = lambda query, principal: adapter.native_query_context
                    state.writer_trace = state.trace.model_dump(mode='json', by_alias=True)
                    configure_pending_rules_storage(state)
                    configure_pending_completion_storage(monkeypatch, state)
                    writers = []
                    def reply(request):
                        writers.append(json.loads(request.content))
                        candidate = {'answer_segments': [{'kind': 'native_body_claim',
                            'text': 'The source says “Éphanna heard the guard.”', 'excerpt_handles': ['body0']}], 'limitations': []}
                        if mode == 'loop_selection_main_object':
                            candidate['answer_segments'] = [{'kind': 'native_assertion_claim',
                                'text': 'The cited source supplies this Check record.', 'assertion_handles': ['assertion0']}]
                        schema = writers[-1]['text']['format']['schema']
                        candidate['schema'] = schema['properties']['schema']['const']
                        candidate['requested_detail_gaps'] = []
                        from jsonschema import validate
                        validate(candidate, writers[-1]['text']['format']['schema'])
                        return httpx.Response(200, request=request, json={'id': 'resp_main_native', 'object': 'response',
                            'created_at': 1, 'model': writers[-1]['model'], 'status': 'completed', 'output': [{'type': 'message',
                                'id': 'msg_main_native', 'role': 'assistant', 'status': 'completed',
                                'content': [{'type': 'output_text', 'text': json.dumps(candidate), 'annotations': []}]}]})
                    monkeypatch.setenv('OPENAI_API_KEY', 'synthetic-only')
                    from apps.live_control_server.services import plan_jev_driver
                    monkeypatch.setattr(plan_jev_driver, 'PlanJevDriver', lambda *a, **kw: pytest.fail('Pending cannot enter legacy driver'))
                    harness.rules_capability = rules_capability(graph=True)
                    harness.writer_transport = httpx.MockTransport(reply)
                    work = SimpleNamespace(operation='answer_from_sources',
                        selection=SimpleNamespace(operation='answer_from_sources', paragraph_placement=None),
                        _material=lambda: ((), (), ()))
                    completed = harness._native_completion(runtime_adapter, work)
                    assert completed.status == 'completed' and state.completions == 1
                    assert (completed.completion.native_assertion_citations if mode == 'loop_selection_main_object'
                        else completed.completion.native_body_citations)
                    from apps.live_control_server.services.agent_turn_service import project_plan_turn_context
                    projected = project_plan_turn_context(completed, delivery_replay=False)
                    if mode == 'loop_selection_main_object':
                        assert projected.deferred_build_citations.assertions
                        assert receipt.source_observation.deferred_head
                        assert receipt.source_observation.requested_or_observed_revision is None
                        assert {cite.read_revision_id for cite in completed.completion.native_assertion_citations} == {
                            projected.deferred_build_citations.settled_revision_id
                        }
                    else:
                        assert projected.deferred_build_citations is None
                    row, references = stored_row(completed)
                    assert repository._turn_from_row(None, row, references=references) == completed
                    assert len(calls) == (2 if mode == 'loop_selection_main_object' else 3)
                    assert len(opens) == (0 if mode == 'loop_selection_main_object' else 1)
                    assert len(writers) == len(searches) == 1
                    assert all(len(body['state'].get('dialogue_reference', body['state'].get('conversation', {}).get('history', []))) in {60, 120}
                        for body in calls)
                    return
                def run(): return asyncio.run(run_pending_native_retrieval(runtime_adapter, harness, dialogue=dialogue))
                if mode == 'loop_invalid':
                    with pytest.raises(GenerationEngineError): run()
                    with pytest.raises(ValueError, match='cannot be resent'): run()
                    assert len(calls) == 1 and not opens
                else:
                    assert run() == {}
                    assert len(calls) == (3 if mode == 'section_loop' else 2)
                    assert len(opens) == (2 if mode == 'section_loop' else 0 if mode in {'loop_objects', 'loop_objects_context', 'loop_selection_main_object'} else 1)
                    if mode in {'loop_objects', 'loop_objects_context', 'loop_selection_main_object'}:
                        from application_state.agent_conversation.native_plan_assertions import NativePlanAssertionReadObservedV1
                        observed = [e for e in state.turn.graph_context_execution.events if type(e) is NativePlanAssertionReadObservedV1]
                        assert observed
                        if mode in {'loop_objects', 'loop_selection_main_object'}:
                            assert any(e.reads for e in observed)
                            assert any('Maelthor guards the ferry' in r.assertion.model_dump_json() for e in observed for r in e.reads)
                        else:
                            assert all(not e.reads and e.unavailable_assertion_ids for e in observed)
                    assert all(body['state']['dialogue_reference'] == list(dialogue) for body in calls)
                    before = len(calls), len(opens)
                    assert run() == {} and (len(calls), len(opens)) == before
                    assert state.turn.graph_context_execution.events[-1].operation == 'finish_retrieval'
                    if writer_mode:
                        from apps.live_control_server.services.build_jev_writer_selection import WriterSelectionDriver
                        from application_state.agent_conversation.native_writer import model_frame
                        work = SimpleNamespace(_material=lambda: ((), (), ()))
                        selector = WriterSelectionDriver(runtime_adapter, work, {'status': 'ready', 'reason': 'native_retrieval_finished'})
                        assert selector.catalog and len(selector.state['conversation']['history']) == 60
                        before = len(calls), len(opens)
                        if mode == 'loop_selection_history': selector.state['conversation']['history'] = selector.state['conversation']['history'][1:]
                        elif mode == 'loop_selection_access': state.denied = True
                        if mode != 'loop_selection':
                            from application_state.errors import ApplicationStateError
                            with pytest.raises((GenerationEngineError, ApplicationStateError)):
                                asyncio.run(harness._decide(runtime_adapter, selector))
                            assert selector.receipt is None
                            assert len(calls) == before[0] + int(mode == 'loop_selection_unknown') and len(opens) == before[1]
                        else:
                            asyncio.run(harness._decide(runtime_adapter, selector))
                            assert selector.receipt.mode == 'jev' and len(calls) == before[0] + 1 and len(opens) == before[1]
                            assert len(calls[-1]['state']['conversation']['history']) == 60
                            frame = model_frame(state.turn.graph_context_receipt, state.turn.graph_context_execution)
                            assert frame['native_body_evidence']['excerpts']
                            import httpx
                            from types import MethodType
                            from apps.live_control_server.services.agent_turn_service import _PolicyExecutionAdapter, _turn_idempotency_key
                            from apps.live_control_server.services.plan_jev_rules_runtime import PlanRulesRuntime
                            from apps.live_control_server.services.plan_jev_writer import PlanJevWriter
                            from application_state.agent_conversation.rules_authority_policy import rules_capability
                            nonce = str(uuid4())
                            runtime_adapter.request = SimpleNamespace(turn_id=nonce, surface=SimpleNamespace(surface_id='build'),
                                message=state.turn.user_text, build_draft_context=None, build_write_capability=None)
                            runtime_adapter.world_id, runtime_adapter.expected_conversation_id = state.turn.world_id, None
                            runtime_adapter.submitted_intent = state.turn.graph_context_execution.policy.action.intent
                            runtime_adapter.service = state.service
                            runtime_adapter.budget['estimator'] = state.turn.graph_context_execution.policy.provider_input_accounting.estimator
                            runtime_adapter.stop = MethodType(_PolicyExecutionAdapter.stop, runtime_adapter)
                            state.turn = t.Turn.model_validate_json(state.turn.model_copy(update={
                                'idempotency_key': _turn_idempotency_key(state.turn.world_id, nonce)}).model_dump_json(by_alias=True))
                            runtime_adapter.turn = state.turn
                            runtime_adapter.fence.renewer.update_turn(state.turn)
                            state.writer_trace = state.trace.model_dump(mode='json', by_alias=True)
                            configure_pending_rules_storage(state)
                            configure_pending_completion_storage(monkeypatch, state)
                            rules = PlanRulesRuntime(runtime_adapter, rules_capability(graph=True))
                            writer = PlanJevWriter(runtime_adapter, {}, rules, dialogue=dialogue)
                            writers = []
                            def reply(request):
                                writers.append(json.loads(request.content))
                                candidate = {'answer_segments': [{'kind': 'native_body_claim',
                                    'text': 'The source says “Éphanna heard the guard.”', 'excerpt_handles': ['body0']}], 'limitations': []}
                                return httpx.Response(200, request=request, json={'id': 'resp_pending_native', 'object': 'response',
                                    'created_at': 1, 'model': writer.model, 'status': 'completed', 'output': [{'type': 'message',
                                        'id': 'msg_pending_native', 'role': 'assistant', 'status': 'completed',
                                        'content': [{'type': 'output_text', 'text': json.dumps(candidate), 'annotations': []}]}]})
                            monkeypatch.setenv('OPENAI_API_KEY', 'synthetic-only')
                            completed = asyncio.run(writer.run(transport=httpx.MockTransport(reply)))
                            assert completed.status == 'completed' and state.completions == 1 and len(writers) == 1
                            assert 'Éphanna' in completed.assistant_text
                            assert completed.completion.native_body_citations
                            row, references = stored_row(completed)
                            assert repository._turn_from_row(None, row, references=references) == completed
                assert prepares == [observation.observed_head_revision_id] and len(searches) == 1
            return
        if 'navigation' in mode:
            from apps.live_control_server.services.native_source_navigation import navigator
            from apps.live_control_server.services.corpus_source_navigation import NativeBodyNavigation
            adapter.pending_build_access = state.authorize
            adapter.request = SimpleNamespace(message=state.turn.user_text)
            if mode == 'section_navigation_epoch':
                admit(memory, 'later', body='# Later source\nNot the original source.\n')
                adapter.native_corpus_context = core.prepare_native_source_context(
                    managed_world_id=state.turn.world_id, principal=principal,
                    revision_id=authority.revision_id, repository=memory.repo,
                    resolve_identity=lambda _: memory.bound)
                assert adapter.native_corpus_context.authority.acquisition_epoch > authority.acquisition_epoch
            nav = navigator(adapter)
            assert type(nav) is NativeBodyNavigation and navigator(adapter) is nav
            offers = nav.offered()
            assert not opens
            handle = next(row.handle for row in offers if row.handle.startswith(
                'native-corpus-search:' if section_mode else 'native-direct-source:'))
            choose(handle)
            fence.renewer.update_turn(state.turn)
            if mode == 'navigation_denied':
                state.denied = True
                with pytest.raises(ApplicationStateError): nav.select((handle,))
                assert not opens
                return
            nav.select((handle,))
            if section_mode:
                handle = next(row.handle for row in nav.offered() if row.handle.startswith('native-body:'))
                choose(handle)
                fence.renewer.update_turn(state.turn)
                before_open = len(opens)
                nav.select((handle,))
                assert len(opens) == before_open + 1
                selected_read = state.turn.graph_context_execution.events[-1]
                assert state.turn.user_text in selected_read.excerpt.text
                search = next(e for e in state.turn.graph_context_execution.events if type(e) is bodies.NativeBodySearchObservedV1)
                assert search.catalogs[0].authority.revision_id == authority.revision_id
                if mode == 'section_navigation_epoch':
                    assert search.catalogs[0].authority.acquisition_epoch > authority.acquisition_epoch
            else:
                assert state.turn.graph_context_execution.events[-1].excerpt.text == BODY and len(opens) == 1
            before_open = len(opens)
            if section_mode:
                nav.select((handle,))
            else:
                with pytest.raises(ValueError): nav.select((handle,))
            assert len(opens) == before_open and handle not in {row.handle for row in nav.offered()}
            recovered = NativeBodyNavigation(adapter)
            assert handle not in {row.handle for row in recovered.offered()} and len(opens) == before_open
            assert prepares == [observation.observed_head_revision_id] and len(searches) == 1
            return
        grant_id = uuid4()
        if section_mode:
            from hashlib import sha256
            choose(bodies.native_corpus_search_handle(sha256(state.turn.user_text.encode()).hexdigest()))
            call('authorize_pending_native_body_search', event_id=grant_id)
            search_id = uuid4()
            capture_calls, captured_results = [], []
            def capture():
                capture_calls.append(1)
                assert state.depth == 1
                result = core.capture_native_sources(managed_world_id=state.turn.world_id, principal=principal, prepared=context)
                captured_results.append(result)
                if mode in {'section_capture_scope', 'section_capture_epoch'}:
                    from dataclasses import replace
                    changed = ({'revision_id': 'foreign'} if mode == 'section_capture_scope'
                               else {'acquisition_epoch': authority.acquisition_epoch - 1})
                    return replace(result, authority=result.authority.model_copy(update=changed))
                return result
            if mode in {'section_capture_scope', 'section_capture_epoch'}:
                before = state.persisted
                with pytest.raises(ApplicationStateError):
                    call('observe_pending_native_body_search', event_id=search_id, authorization_event_id=grant_id, capture=capture)
                assert state.persisted == before and capture_calls == [1]
                changed = ({'revision_id': 'foreign'} if mode == 'section_capture_scope'
                           else {'acquisition_epoch': authority.acquisition_epoch - 1})
                altered_authority = authority.model_copy(update=changed)
                member = captured_results[0].members[0].model_copy(update={'proof_epoch': 0})
                altered_catalog = bodies.build_native_body_catalog(altered_authority, member, source_body)
                observed = bodies.NativeBodySearchObservedV1(event_id=search_id,
                    sequence=len(state.turn.graph_context_execution.events), authorization_event_id=grant_id,
                    catalogs=(altered_catalog,), matches=(), unavailable_source_count=0)
                candidate = state.turn.graph_context_execution.model_copy(update={
                    'events': [*state.turn.graph_context_execution.events, observed]})
                with pytest.raises(ValueError, match='changed its source authority'):
                    type(candidate).model_validate_json(candidate.model_dump_json(by_alias=True))
                return
            call('observe_pending_native_body_search', event_id=search_id, authorization_event_id=grant_id, capture=capture)
            assert call('observe_pending_native_body_search', event_id=search_id, authorization_event_id=grant_id, capture=capture)[1] is False
            assert capture_calls == [1]
            search = state.turn.graph_context_execution.events[-1]
            hit = search.matches[0]
            catalog = next(c for c in search.catalogs if c.catalog_sha256 == hit.catalog_sha256)
            section = next(s for s in catalog.sections if s.section_id == hit.section_id)
            choose(bodies.native_body_handle(catalog.catalog_sha256, section.section_id))
            grant_id = uuid4()
            call('authorize_pending_native_body_reads', grants=({'event_id': grant_id, 'search_event_id': search_id,
                'catalog_sha256': catalog.catalog_sha256, 'retrieval_kind': 'section', 'section_id': section.section_id},))
            expected_text = source_body[section.char_start:section.char_end]
            opens.clear()
        else:
            choose(bodies.native_direct_source_handle(authority, **target))
            call('authorize_pending_native_direct_sources', grants=({'event_id': grant_id, **target},))
            expected_text = BODY
        if mode == 'later_head': admit(memory, 'later', body='# Elsewhere\nDifferent source.\n')
        elif mode.endswith('binding_changed'): memory.bound = SimpleNamespace(**(vars(memory.bound) | {'binding_version': 2}))
        elif mode == 'principal_lost': principal.role = 'player'
        elif mode in {'app_access_lost', 'section_access_lost'}: state.denied = True
        before = state.persisted
        event_id = uuid4()
        callbacks = []
        def read(grant):
            callbacks.append(grant)
            assert state.depth == 1 and grant.authority == authority
            return core.read_direct_native_source(context, authority=grant.authority,
                source_artifact_id=grant.source_artifact_id, source_revision_id=grant.source_revision_id,
                content_sha256=grant.content_sha256)
        def read_member(actual_authority, member):
            callbacks.append(member)
            assert state.depth == 1 and actual_authority == authority
            return core.read_native_corpus_member(authority=actual_authority, member=member,
                principal=principal, prepared=context)
        def observe():
            if section_mode:
                return call('observe_pending_native_body_reads', reads=({'event_id': event_id,
                    'authorization_event_id': grant_id},), read=read_member)
            return call('observe_pending_native_direct_source', event_id=event_id,
                authorization_event_id=grant_id, read=read)
        if mode in {'binding_changed', 'principal_lost', 'app_access_lost', 'section_binding_changed', 'section_access_lost'}:
            with pytest.raises(ApplicationStateError): observe()
            assert state.persisted == before and not opens
            assert len(callbacks) == int(mode not in {'app_access_lost', 'section_access_lost'})
        else:
            updated, fresh = observe()
            observed = updated.graph_context_execution.events[-1]
            assert fresh and observed.excerpt.text == expected_text and len(opens) == 1
            result_catalog = catalog if section_mode else observed.catalog
            assert result_catalog.authority.revision_id == observation.observed_head_revision_id
            assert result_catalog.authority.acquisition_epoch >= authority.acquisition_epoch
            assert observe()[1] is False and len(opens) == len(callbacks) == 1
        assert prepares == [observation.observed_head_revision_id] and len(searches) == 1
    finally:
        fence.stop()


@pytest.mark.parametrize('failure', [None, 'question', 'source_pin', 'offer', 'foreign_turn'])
def test_pending_native_rules_offer_keeps_actual_selected_parent_binding(monkeypatch, failure):
    from hashlib import sha256
    from application_state.agent_conversation.plan_jev_rules_lookup import _selected_offer, RULES_HANDLE
    from tests.test_surface_native_execution import outcomes, choice
    with pending_native_dispatch_case(monkeypatch, select_rules=True) as (state, auth, proof, response, call):
        call('authorize_pending_native_retrieval', authorization=auth, prepared_input_proof=proof)
        entry, outcome = outcomes(auth, len(state.turn.graph_context_execution.events))
        outcome = outcome.model_copy(update={'response_sha256': sha256(response.encode()).hexdigest()})
        call('enter_pending_app_page_sdk', outcome=entry, prepared_request_json=proof['request_json'])
        call('record_pending_app_controller_outcome', outcome=outcome)
        selected = choice(state.turn.graph_context_receipt, state.turn.graph_context_execution, auth,
            len(state.turn.graph_context_execution.events), 'select_candidates', (RULES_HANDLE,)).model_copy(update={
                'controller_response_sha256': sha256(response.encode()).hexdigest()})
        call('record_pending_native_selection', selection=selected, producer_proof=proof | {'response_json': response})
        parent = json.loads(proof['parent_request_json'])
        turn = state.turn
        if failure == 'question': parent['question'] = 'Foreign question'
        elif failure == 'source_pin': parent['source_revision'] = 'foreign'
        elif failure == 'offer': parent['candidates'][0]['label'] = 'Campaign lore, not rules'
        elif failure == 'foreign_turn': turn = turn.model_copy(update={'world_id': 'foreign'})
        if failure:
            with pytest.raises(ValueError): _selected_offer(turn, json.dumps(parent))
        else:
            assert _selected_offer(turn, json.dumps(parent, indent=2)) == selected
        assert len(state.source_prepares) == len(state.query_searches) == 1 and not state.query_reopens


@pytest.mark.parametrize('settled', [False, True])
def test_pending_native_finish_requires_real_owned_rules_ledger_closure(monkeypatch, settled):
    import asyncio
    import httpx2
    from hashlib import sha256
    from application_state.errors import ApplicationStateError
    from application_state.agent_conversation.plan_jev_rules_lookup import RULES_HANDLE, prepare_authorization
    from application_state.agent_conversation.rules_authority_policy import rules_capability, rules_submission_authorization_id
    from application_state.agent_conversation.rules_authority_types import RulesScopeV1
    from application_state.agent_conversation.rules_authority_events import empty_execution, RulesExecutionV1, RulesQueryObservedV1
    from apps.live_control_server.services.build_pending_native_retrieval import PendingNativeRetrievalDriver
    from apps.live_control_server.services.build_jev_harness import BuildJevHarness
    from tests.test_surface_native_execution import outcomes, choice
    monkeypatch.setenv('TYPESAFE_JEV_API_KEY', 'synthetic-only')
    with pending_native_dispatch_case(monkeypatch, select_rules=True) as (state, auth, proof, response, call):
        call('authorize_pending_native_retrieval', authorization=auth, prepared_input_proof=proof)
        entry, outcome = outcomes(auth, len(state.turn.graph_context_execution.events))
        outcome = outcome.model_copy(update={'response_sha256': sha256(response.encode()).hexdigest()})
        call('enter_pending_app_page_sdk', outcome=entry, prepared_request_json=proof['request_json'])
        call('record_pending_app_controller_outcome', outcome=outcome)
        selected = choice(state.turn.graph_context_receipt, state.turn.graph_context_execution, auth,
            len(state.turn.graph_context_execution.events), 'select_candidates', (RULES_HANDLE,)).model_copy(update={
                'controller_response_sha256': sha256(response.encode()).hexdigest()})
        call('record_pending_native_selection', selection=selected, producer_proof=proof | {'response_json': response})
        cap = rules_capability(graph=True)
        turn = state.turn
        scope = RulesScopeV1(schema='dmb_rules_scope_v1', execution_id=uuid4(), world_id=turn.world_id,
            conversation_id=turn.conversation_id, turn_id=turn.turn_id, product_attempt=turn.attempt,
            ruleset_id=cap.ruleset_id, corpus_sha256=cap.corpus_sha256,
            authorization_id=rules_submission_authorization_id(world_id=turn.world_id,
                conversation_id=turn.conversation_id, idempotency_key=turn.idempotency_key,
                submitted_intent_sha256=turn.submitted_intent_fingerprint_v2, capability=cap),
            capability_policy_sha256=cap.policy_sha256, budget=cap.budget)
        ledger = empty_execution(scope)
        grant = prepare_authorization(ledger, turn, proof['parent_request_json'])
        events = [grant]
        if settled:
            events.append(RulesQueryObservedV1(kind='query_observed', event_id=uuid4(), sequence=1,
                execution_id=scope.execution_id, call_id=grant.call_id, query_id=grant.query_id,
                packet_sha256='a' * 64, presentation_utf8=0, status='no_evidence', support_refs=(), emitted_support_ids=()))
        ledger = RulesExecutionV1.model_validate(ledger.model_copy(update={'events': tuple(events),
            'budget_use': ledger.budget_use.model_copy(update={'calls': 1, 'distinct_questions': 1})}).model_dump(mode='python', by_alias=True))
        state.rules_payload = ledger.model_dump(mode='json', by_alias=True)
        class Transport(httpx2.AsyncBaseTransport):
            async def handle_async_request(self, request):
                body = json.loads(request.content)
                return httpx2.Response(200, request=request, json={'model': body['model'], 'usage': {'input_tokens': 11, 'output_tokens': 2}, 'answers': {
                    key: {'type': 'choice', 'choice': 'finish_retrieval', 'confidence': 1,
                        'probabilities': {name: float(name == 'finish_retrieval') for name in q['criteria']}}
                    for key, q in body['questions'].items()}})
        with pending_app_runtime_case(monkeypatch, seed=state) as (_, adapter):
            harness = BuildJevHarness(decision_transport=Transport(), accounting=adapter._build_jev_accounting)
            harness.adapter, harness.calls, harness.timings, harness._inflight = adapter, [], [], {}
            driver = PendingNativeRetrievalDriver(adapter, (), allowed_operations=('select_candidates', 'finish_retrieval'))
            if settled:
                asyncio.run(harness._decide(adapter, driver))
                assert driver.selection.operation == 'finish_retrieval'
            else:
                with pytest.raises(ApplicationStateError, match='unresolved Rules read'):
                    asyncio.run(harness._decide(adapter, driver))
                assert driver.selection is None
                assert not any(getattr(e, 'operation', None) == 'finish_retrieval' for e in state.turn.graph_context_execution.events)

@pytest.mark.parametrize('mode', ['fresh', 'reuse', 'scope_changed', 'access_lost', 'access_changes', 'expired', 'expires_during', 'bool_revision'])
def test_pending_rules_open_reuses_only_exact_frozen_scope_under_current_claim(monkeypatch, mode):
    from application_state.errors import ApplicationStateError
    from application_state.agent_conversation.rules_authority_policy import rules_capability, rules_submission_authorization_id
    from application_state.agent_conversation.rules_authority_types import RulesScopeV1
    from application_state.agent_conversation.rules_authority_events import empty_execution
    state, _ = settlement_harness(monkeypatch)
    configure_pending_rules_storage(state)
    cap, turn = rules_capability(graph=True), state.turn
    scope = RulesScopeV1(schema='dmb_rules_scope_v1', execution_id=uuid4(), world_id=turn.world_id,
        conversation_id=turn.conversation_id, turn_id=turn.turn_id, product_attempt=turn.attempt,
        ruleset_id=cap.ruleset_id, corpus_sha256=cap.corpus_sha256,
        authorization_id=rules_submission_authorization_id(world_id=turn.world_id,
            conversation_id=turn.conversation_id, idempotency_key=turn.idempotency_key,
            submitted_intent_sha256=turn.submitted_intent_fingerprint_v2, capability=cap),
        capability_policy_sha256=cap.policy_sha256, budget=cap.budget)
    if mode != 'fresh':
        state.rules_payload = empty_execution(scope).model_dump(mode='json', by_alias=True)
    candidate = scope.model_copy(update={'execution_id': uuid4()})
    if mode == 'scope_changed': candidate = candidate.model_copy(update={'authorization_id': 'f' * 64})
    if mode == 'access_lost': state.denied = True
    if mode == 'expired': state.now = turn.claim_expires_at
    access = state.authorize
    if mode in {'access_changes', 'expires_during'}:
        calls = []
        def access(*args):
            calls.append(1)
            if mode == 'expires_during':
                if len(calls) == 2: state.now = turn.claim_expires_at
                return True
            return len(calls) == 1
    def run():
        return state.service.begin_pending_rules_execution(candidate, expected_turn_revision=True if mode == 'bool_revision' else turn.revision,
            authorize_current_access=access)
    if mode in {'scope_changed', 'access_lost', 'access_changes', 'expired', 'expires_during', 'bool_revision'}:
        with pytest.raises(ApplicationStateError): run()
    else:
        record = run()
        assert record.execution.scope == (candidate if mode == 'fresh' else scope)
        assert state.rules_inserts == int(mode == 'fresh')
        assert run().execution.scope == record.execution.scope
        assert state.rules_inserts == int(mode == 'fresh')

@pytest.mark.parametrize('settled', [False, True])
def test_pending_rules_runtime_restores_completed_calls_without_lookup_or_resend(settled):
    from types import SimpleNamespace
    from application_state.agent_conversation.rules_authority_events import RulesToolAuthorizedV1, RulesQueryObservedV1
    from apps.live_control_server.services.plan_jev_rules_runtime import PlanRulesRuntime
    from application_state.agent_conversation.rules_authority_policy import rules_capability
    receipt = pending_submission().graph_context_receipt
    grant = RulesToolAuthorizedV1.model_construct(call_id='stored-call')
    observation = RulesQueryObservedV1.model_construct(call_id='stored-call')
    record = SimpleNamespace(execution=SimpleNamespace(events=[grant, *([observation] if settled else [])]))
    bindings = []
    native = SimpleNamespace(record=record, _bind=lambda: bindings.append('bind'))
    fence = SimpleNamespace(turn=SimpleNamespace(graph_context_receipt=receipt),
        rules_checkpoint=lambda action, read: action())
    runtime = object.__new__(PlanRulesRuntime)
    runtime.adapter, runtime.selected, runtime.call_ids = SimpleNamespace(fence=fence), False, ()
    runtime._initialize = lambda: native
    if settled:
        runtime.restore_pending()
        assert runtime.selected and runtime.call_ids == ('stored-call',)
        with pytest.raises(ValueError, match='cannot repeat'): runtime.lookup_selected('never-used')
    else:
        with pytest.raises(ValueError, match='cannot resend'): runtime.restore_pending()
        assert not runtime.selected and runtime.call_ids == ()
    assert bindings == ['bind']

@pytest.mark.parametrize('kind', ['build_app_page_selection_authorized_v1', 'build_app_coverage_authorized_v1'])
@pytest.mark.parametrize('mutation', [None, 'schema', 'payload', 'duplicate', 'sequence'])
def test_pending_app_prompt_capture_keeps_exact_authorization_and_family(monkeypatch, kind, mutation):
    from application_state.agent_conversation.context_trace_store import validate_prompt_authorization
    from application_state.errors import ApplicationStateValidationError
    state, _, _, _ = pending_page_dispatch_harness(monkeypatch)
    from application_state.agent_conversation.context_trace import TracePromptReference
    prompt = TracePromptReference.model_validate(state.prompt)
    event = dict(kind=kind, sequence=0, provider_attempt_id=str(prompt.provider_attempt_id),
        provider=prompt.provider, model=prompt.model, api_mode=prompt.api_mode,
        serializer_version=prompt.serializer_version, envelope_sha256=prompt.payload_sha256)
    execution = dict(schema='dmb_build_pending_execution_v1', events=[event])
    if mutation == 'schema': execution['schema'] = 'dmb_surface_native_execution_v1'
    if mutation == 'payload': event['envelope_sha256'] = 'f' * 64
    if mutation == 'duplicate': execution['events'].append(dict(event))
    if mutation is not None:
        with pytest.raises(ApplicationStateValidationError):
            validate_prompt_authorization(prompt, execution, int(mutation == 'sequence'))
    else:
        validate_prompt_authorization(prompt, execution, 0)
