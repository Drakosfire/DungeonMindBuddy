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
    conn = object()
    @contextmanager
    def uow(*args, **kwargs):
        assert state.depth == 0
        state.depth += 1
        try:
            yield conn
        finally:
            state.depth -= 1
    monkeypatch.setattr(service_module, 'unit_of_work', uow)
    monkeypatch.setattr(service_module, '_ready_dsn', lambda: 'synthetic-no-database')
    def world_lock(_conn, world):
        assert _conn is conn and state.depth == 1 and world == turn.world_id
        state.locks.append('world')
        return state.pointer
    def conversation_lock(_conn, world, conversation_id):
        assert _conn is conn and state.depth == 1 and conversation_id == turn.conversation_id
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
