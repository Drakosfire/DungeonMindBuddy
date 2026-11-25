"""Stored pending Build codec boundary; no database, providers or source grants."""
import json
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


def pending_submission(*, with_source=False):
    receipt, policy = pending_execution_pair(with_source=with_source)
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


def settlement_harness(monkeypatch, *, with_source=True, scope='source_lookup'):
    """Real service decisions, fake transaction/row owners; not SQL qualification."""
    from contextlib import contextmanager
    from datetime import UTC, datetime, timedelta
    from types import SimpleNamespace
    from application_state.agent_conversation import service as service_module
    from tests.test_surface_native_execution import BUILD_TURN_ID
    from tests.test_build_source_free_routing import pending_work_prefix, settled_source, prepared_query
    sub = pending_submission(with_source=with_source)
    events = pending_work_prefix(sub.graph_context_execution.policy, scope=scope)
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
    assert pending_source_work(complete).event_id == events[3].event_id


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
        'principal': principal, 'revision_id': request.graph_request.revision_pin}


@pytest.mark.parametrize('reason', ['references', 'reviewed', 'selected_knowledge', 'graph_selection', 'retry', 'no_owner', 'not_gm'])
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
def pending_app_runtime_case(monkeypatch):
    from types import SimpleNamespace, MethodType
    from datetime import UTC, datetime
    from apps.live_control_server.services.agent_turn_service import _ClaimFence, _PolicyExecutionAdapter
    from apps.live_control_server.services.agent_context_trace_collector import ContextTraceCollector
    from application_state.agent_conversation.context_trace import TurnContextTraceV1
    from apps.live_control_server.services import agent_prompt_evidence
    from tests.test_build_jev_estimated_continuations import counter
    state, _, _, _ = pending_page_dispatch_harness(monkeypatch)
    state.trace = TurnContextTraceV1(trace_id=uuid4(), world_id=state.turn.world_id,
        conversation_id=state.turn.conversation_id, turn_id=state.turn.turn_id, attempt=1,
        started_at=datetime.now(UTC), execution_start_sequence=0, observations=[state.prompt])
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
        return state.trace
    monkeypatch.setattr(state.service, 'append_context_trace', append_observation)
    def store(raw, *, digest, size):
        assert hashlib.sha256(raw.encode()).hexdigest() == digest and len(raw.encode()) == size
        return uuid4()
    import hashlib
    monkeypatch.setattr(agent_prompt_evidence, 'store_prompt', store)
    monkeypatch.setattr(agent_prompt_evidence, 'read_prompt', lambda ref: state.initial_request)
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
    ('clarify_creation', 'uncertain'), ('review_blank_lore_page', 'uncertain')])
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
