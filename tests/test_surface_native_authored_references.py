"""Author-picked Core targets are not search hits or model-selected offers."""
from dataclasses import replace
from types import SimpleNamespace
from uuid import uuid4

import pytest

from application_state.agent_conversation.authored_graph_references import (
    AuthoredGraphReferenceV1, AuthoredGraphReferencesV1,
)
from apps.live_control_server.services import native_graph_reads as native
from tests.test_native_plan_assertions import lane as lane, publish, admit_unrelated, GM
from tests.test_native_plan_statements import bound


def references(lane):
    world = lane.world.world_id
    return AuthoredGraphReferencesV1(references=(AuthoredGraphReferenceV1(
        managed_world_id=world, native_world_id=world, binding_version=1,
        graph_revision=lane.repo.get_head(world).head_revision_id,
        node_id=lane.ids['B'], label='Untrusted display label'),))


def test_author_picked_entity_uses_core_at_current_pin_without_becoming_a_search_hit(
    lane, monkeypatch,
):
    publish(lane, qualified=True)
    selected = references(lane)
    origin = selected.references[0].graph_revision
    admit_unrelated(lane, 'after-author-selection')
    def forbidden(*_args):
        pytest.fail('Source body opened during target metadata discovery')
    monkeypatch.setattr(native, 'open_admitted_native_text', forbidden)
    context, query = native.prepare_query(lane.world.world_id, 'zz-no-matching-entity-zz', GM,
        repository=lane.repo, resolve_binding=lambda _: bound(lane),
        authored_references=selected)
    assert query.schema_ == 'dmb_native_graph_query_v4'
    assert not query.discovered_entity_ids and not query.matches and not query.assertion_matches
    assert query.authority.revision_id != origin
    assert query.authority.revision_id == lane.repo.get_head(lane.world.world_id).head_revision_id
    assert context.query == query and len(query.authored_targets) == 1
    target = query.authored_targets[0]
    assert target.node_id == lane.ids['B'] and target.status == 'complete'
    assert target.selection_revision_id == origin
    assert target.assertion_matches and not target.matches
    assert all(m.discovered_entity_ids == (lane.ids['B'],) for m in target.assertion_matches)
    assert 'Untrusted display label' not in query.model_dump_json()
    assert type(query).model_validate_json(query.model_dump_json(by_alias=True)) == query


@pytest.mark.parametrize('mutation', ['world', 'native', 'binding', 'revision', 'node', 'role'])
def test_authored_origin_must_exist_in_its_selected_snapshot_before_any_body_read(
    lane, monkeypatch, mutation,
):
    publish(lane)
    selected = references(lane)
    ref = selected.references[0]
    field, value = {'world': ('managed_world_id', 'another-world'),
        'native': ('native_world_id', 'another-native-world'),
        'binding': ('binding_version', 99), 'revision': ('graph_revision', 'rev:missing'),
        'node': ('node_id', 'ent:missing'), 'role': ('label', ref.label)}[mutation]
    selected = selected.model_copy(update={'references': (ref.model_copy(update={field: value}),)})
    def forbidden(*_args):
        pytest.fail('Rejected author selection opened source bodies')
    monkeypatch.setattr(native, 'open_admitted_native_text', forbidden)
    with pytest.raises(ValueError):
        native.prepare_query(lane.world.world_id, 'zz-no-matching-entity-zz',
            replace(GM, role='player') if mutation == 'role' else GM,
            repository=lane.repo, resolve_binding=lambda _: bound(lane),
            authored_references=selected)


def human_grant(context, selected):
    from application_state.agent_conversation.authored_graph_references import BuildAuthoredReferenceAuthorizedV2
    return BuildAuthoredReferenceAuthorizedV2(event_id=uuid4(), sequence=1,
        capture_event_id=uuid4(), node_id=selected.references[0].node_id,
        query_sha256=context.query.sha256, context_receipt_sha256='a' * 64,
        execution_policy_sha256='b' * 64)


def test_human_grant_reuses_core_assertion_support_and_preserves_qualifications(lane):
    publish(lane, qualified=True)
    selected = references(lane)
    context, query = native.prepare_query(lane.world.world_id, 'zz-no-matching-entity-zz', GM,
        repository=lane.repo, resolve_binding=lambda _: bound(lane), authored_references=selected)
    before = lane.repo.get_head(lane.world.world_id)
    grant = human_grant(context, selected)
    captured = native.read_authored_reference(context, grant, GM)
    assert captured.node_id == selected.references[0].node_id
    assert captured.query_sha256 == query.sha256
    assert not captured.statement_reads
    read = next(row for row in captured.assertion_reads if row.assertion.predicate == 'dnd5e:summary')
    assert read.assertion.metadata.claim_mode == 'dungeonbuddy.claim:belief'
    assert read.assertion.metadata.standing == 'provisional'
    assert read.spans and read.spans[0].text
    assert lane.repo.get_head(lane.world.world_id) == before
    assert 'provider_attempt_id' not in grant.model_dump()
    from application_state.agent_conversation.authored_graph_references import BuildAuthoredReferenceReadV2
    record = BuildAuthoredReferenceReadV2(event_id=uuid4(), sequence=2,
        authorization_event_id=grant.event_id, capture_event_id=grant.capture_event_id,
        **{name: getattr(captured, name) for name in ('node_id', 'statement_reads', 'assertion_reads',
            'unavailable_statement_ids', 'unavailable_assertion_ids', 'status')})
    assert type(record).model_validate_json(record.model_dump_json(by_alias=True)) == record


@pytest.mark.parametrize('mutation', ['query', 'node', 'binding', 'role', 'provider'])
def test_human_reader_refuses_other_context_or_provider_origin_before_support(lane, monkeypatch, mutation):
    publish(lane)
    selected = references(lane)
    context, _query = native.prepare_query(lane.world.world_id, 'zz-no-matching-entity-zz', GM,
        repository=lane.repo, resolve_binding=lambda _: bound(lane), authored_references=selected)
    grant = human_grant(context, selected)
    if mutation == 'query':
        grant = grant.model_copy(update={'query_sha256': 'f' * 64})
    elif mutation == 'node':
        grant = grant.model_copy(update={'node_id': 'ent:unrequested'})
    elif mutation == 'binding':
        context = replace(context, resolve_binding=lambda _: SimpleNamespace(binding_version=99))
    elif mutation == 'provider':
        from tests.test_native_plan_assertions import grant as model_grant
        grant = model_grant(context, ('unoffered-assertion',))
    def forbidden(*_args):
        pytest.fail('Wrong authored grant opened support bodies')
    monkeypatch.setattr(native, 'open_admitted_native_text', forbidden)
    with pytest.raises(ValueError):
        native.read_authored_reference(context, grant,
            replace(GM, role='player') if mutation == 'role' else GM)


def test_human_target_reuses_qualified_statement_support_without_promoting_reported_content(lane):
    from tests.test_source_statements import commit, BODY
    prepared, _result = commit(lane)
    selected = references(lane)
    context, query = native.prepare_query(lane.world.world_id, 'zz-no-matching-entity-zz', GM,
        repository=lane.repo, resolve_binding=lambda _: bound(lane), authored_references=selected)
    assert not query.matches and query.authored_targets[0].matches
    captured = native.read_authored_reference(context, human_grant(context, selected), GM)
    assert len(captured.statement_reads) == 1
    read = captured.statement_reads[0]
    assert read.support.payload == prepared.envelope['payload']
    assert read.support.payload['embedded_content_factive'] is False
    assert read.support.clause_text == BODY.splitlines(keepends=True)[0]


def test_human_target_unavailable_assertion_support_stays_an_explicit_gap(lane, monkeypatch):
    publish(lane)
    selected = references(lane)
    context, _query = native.prepare_query(lane.world.world_id, 'zz-no-matching-entity-zz', GM,
        repository=lane.repo, resolve_binding=lambda _: bound(lane), authored_references=selected)
    monkeypatch.setattr(native, 'open_admitted_native_text', lambda *_: SimpleNamespace(status='unavailable'))
    captured = native.read_authored_reference(context, human_grant(context, selected), GM)
    assert captured.status == 'partial' and captured.unavailable_assertion_ids
    assert not captured.assertion_reads
    assert context.query.universal_absence_claimed is False


def native_build_case(lane, selected):
    """Actual Core catalog and APP records; this is not an ordinary Build request."""
    import json
    from application_state.agent_conversation import types as t
    from application_state.agent_conversation.native_context import SurfaceNativeContextReceiptV1
    from tests.test_surface_native_execution import component, execution
    from tests.test_surface_native_context import seal, provenance_for
    from tests.application_state.test_agent_conversation_postgres import _new
    from application_state.agent_conversation import AgentConversationService
    core, query = native.prepare_query(lane.world.world_id, 'zz-no-matching-entity-zz', GM,
        repository=lane.repo, resolve_binding=lambda _: bound(lane), authored_references=selected)
    context, record = component('build')
    work = context.work_context.model_copy(update={'source_basis': context.work_context.source_basis.model_copy(
        update={'world_id': lane.world.world_id})})
    intent = record.policy.action.intent.model_dump(mode='json', by_alias=True)
    intent.update(schema='dmb_build_graph_intent_v2', world_id=lane.world.world_id,
        message=query.question, authored_references=selected.model_dump(mode='json', by_alias=True))
    intent['graph_request']['world_id'] = lane.world.world_id
    intent = t.BuildGraphIntentV2.model_validate_json(json.dumps(intent))
    provenance = provenance_for(work).model_copy(update={'surface_instance_id': intent.surface_instance_id})
    source = t.NativeCorpusAuthorityV1(**{name: getattr(query.authority, name)
        for name in ('managed_world_id', 'native_world_id', 'binding_version', 'revision_id',
            'domain_ref', 'profile_ref', 'acquisition_epoch')})
    context_wire = context.model_dump(mode='json', by_alias=True)
    context_wire['assembled_input']['tokenizer_name'] = record.policy.controller_continuation_accounting.policy
    context_wire.update(work_context=work.model_dump(mode='json', by_alias=True),
        native_query=query.model_dump(mode='json', by_alias=True),
        source_authority=source.model_dump(mode='json', by_alias=True), provenance_sha256=t.canonical_sha256(provenance))
    context = SurfaceNativeContextReceiptV1.model_validate_json(json.dumps(seal(context_wire)))
    policy = record.policy.model_copy(update={'action': record.policy.action.model_copy(update={'intent': intent}),
        'source_authority_sha256': t.canonical_sha256(source), 'native_query_sha256': t.canonical_sha256(query)})
    record = execution(context.context_receipt_sha256, policy)
    service = AgentConversationService()
    cid = _new(service, lane.world.world_id).conversation_id
    accepted = service.accept_turn(t.TurnSubmission(world_id=lane.world.world_id, conversation_id=cid,
        idempotency_key=uuid4(), expected_conversation_revision=1, user_text=intent.message,
        provenance=provenance, submitted_intent_v2=intent, graph_context_receipt=context,
        graph_context_execution=record))
    turn = service.claim_turn(lane.world.world_id, cid, accepted.turn_id, expected_revision=accepted.revision).turn
    return core, service, turn


def append_native(service, turn, method, **values):
    updated, fresh = getattr(service, method)(turn.world_id, turn.conversation_id, turn.turn_id,
        expected_revision=turn.revision, expected_attempt=turn.attempt, **values)
    assert fresh
    return updated


def read_human(lane, *, statement=False):
    if statement:
        from tests.test_source_statements import commit
        commit(lane)
    publish(lane, qualified=True)
    selected = references(lane)
    admit_unrelated(lane, 'human-input-before-app-admission')
    core, service, turn = native_build_case(lane, selected)
    turn = append_native(service, turn, 'capture_native_authored_references', event_id=uuid4())
    turn = append_native(service, turn, 'authorize_native_authored_reference', event_id=uuid4(), node_id=selected.references[0].node_id)
    grant = turn.graph_context_execution.events[-1]
    turn = append_native(service, turn, 'observe_native_authored_reference', event_id=uuid4(),
        authorization_event_id=grant.event_id, materialize=lambda auth: native.read_authored_reference(core, auth, GM))
    return core, service, turn


def test_app_locks_real_human_input_and_native_support_without_a_model_vote(lane):
    from application_state.agent_conversation.native_writer import model_frame
    from application_state.agent_conversation.authored_graph_references import native_writer_context
    core, service, turn = read_human(lane)
    stored = service.inspect_turn(world_id=turn.world_id, turn_id=turn.turn_id)
    assert stored == turn
    execution = stored.graph_context_execution
    assert [e.kind for e in execution.events] == ['build_authored_references_captured_v1',
        'build_authored_reference_authorized_v2', 'build_authored_reference_read_v2']
    assert not any(hasattr(e, 'provider_attempt_id') for e in execution.events)
    captured, grant, read = execution.events
    assert captured.references.references[0].graph_revision != core.query.authority.revision_id
    assert captured.read_graph_revision == core.query.authority.revision_id
    assert read.capture_event_id == grant.capture_event_id == captured.event_id
    frame = model_frame(stored.graph_context_receipt, execution)
    assert frame['native_assertions']['assertions'] and not frame['native_statements']['statements']
    assert any(row['assertion']['metadata']['claim_mode'] == 'dungeonbuddy.claim:belief'
        for row in frame['native_assertions']['assertions'])
    assert 'Untrusted display label' not in str(frame) + str(native_writer_context(execution))


@pytest.mark.parametrize('mutation', ['capture', 'query', 'root', 'policy', 'node', 'duplicate',
    'inventory', 'assertion', 'partial', 'origin', 'read_revision'])
def test_native_app_rejects_rebound_or_invented_human_context(lane, mutation):
    from copy import deepcopy
    from application_state.agent_conversation.native_execution import SurfaceNativeExecutionV1, validate_context_binding
    from application_state.agent_conversation import types as t
    import json
    _core, _service, turn = read_human(lane)
    context, execution = turn.graph_context_receipt, turn.graph_context_execution
    wire = execution.model_dump(mode='json', by_alias=True)
    captured, grant, read = wire['events']
    if mutation == 'capture':
        grant['capture_event_id'] = str(uuid4())
    elif mutation == 'query':
        grant['query_sha256'] = 'f' * 64
    elif mutation == 'root':
        grant['context_receipt_sha256'] = 'f' * 64
    elif mutation == 'policy':
        grant['execution_policy_sha256'] = 'f' * 64
    elif mutation == 'node':
        grant['node_id'] = 'ent:unrequested'
    elif mutation == 'duplicate':
        again = deepcopy(read)
        again.update(event_id=str(uuid4()), sequence=3)
        wire['events'].append(again)
    elif mutation == 'inventory':
        read['assertion_reads'] = []
    elif mutation == 'assertion':
        read['assertion_reads'][0]['assertion']['predicate'] = 'unsupported:predicate'
    elif mutation == 'partial':
        read['status'] = 'partial'
    elif mutation == 'origin':
        wire['policy']['action']['intent']['authored_references']['references'][0]['graph_revision'] = 'rev:other'
        captured['references'] = deepcopy(wire['policy']['action']['intent']['authored_references'])
        captured['submitted_intent_fingerprint'] = t.submitted_turn_intent_fingerprint_v2(
            t.BuildGraphIntentV2.model_validate_json(json.dumps(wire['policy']['action']['intent'])))
        wire['execution_policy_sha256'] = t.canonical_sha256({key: wire[key] for key in ('schema', 'context_receipt_sha256', 'policy')})
        grant['execution_policy_sha256'] = wire['execution_policy_sha256']
    else:
        captured['read_graph_revision'] = 'rev:other'
    with pytest.raises(ValueError):
        changed = SurfaceNativeExecutionV1.model_validate_json(json.dumps(wire))
        validate_context_binding(context, changed)


@pytest.mark.parametrize('mutation', ['turn', 'conversation', 'attempt'])
def test_retained_native_capture_cannot_be_rebound_to_another_request(lane, mutation):
    from application_state.agent_conversation.native_execution import validate_request_identity
    _core, _service, turn = read_human(lane)
    execution = turn.graph_context_execution
    captured = execution.events[0].model_copy(update={
        {'turn': 'turn_id', 'conversation': 'conversation_id', 'attempt': 'attempt'}[mutation]:
            2 if mutation == 'attempt' else uuid4()})
    changed = execution.model_copy(update={'events': [captured, *execution.events[1:]]})
    with pytest.raises(ValueError, match='another request or attempt'):
        validate_request_identity(turn.graph_context_receipt, changed, turn)


def test_app_refuses_human_result_from_raw_append_and_preserves_retained_grant(lane):
    from application_state.errors import ApplicationStateValidationError
    core, service, turn = read_human(lane)
    read = turn.graph_context_execution.events[-1]
    with pytest.raises(ApplicationStateValidationError, match='immutable read transaction'):
        service._append_graph_execution_event(turn.world_id, turn.conversation_id, turn.turn_id,
            expected_revision=turn.revision, expected_attempt=turn.attempt,
            event=read.model_copy(update={'event_id': uuid4(), 'sequence': len(turn.graph_context_execution.events)}), duplicate_key='event_id')
    assert service.inspect_turn(world_id=turn.world_id, turn_id=turn.turn_id) == turn


@pytest.mark.parametrize('statement', [False, True])
def test_actual_sdk_human_support_normalizes_to_exact_reopenable_citation(lane, monkeypatch, statement):
    """APP-read prefix plus actual SDK writer/citation owner, not ordinary Build delivery."""
    from application_state.agent_conversation.native_writer import model_frame
    from application_state.agent_conversation.native_completion import normalize_output
    from tests.test_surface_native_completion import producing_case, answer
    from apps.live_control_server.services.native_statement_clause_reads import open_clause, open_assertion_source
    core, _service, turn = read_human(lane, statement=statement)
    context, record = turn.graph_context_receipt, turn.graph_context_execution
    work = dict(world_id=turn.world_id, conversation_id=turn.conversation_id, turn_id=turn.turn_id,
        attempt=turn.attempt, provenance=turn.provenance, idempotency_key=turn.idempotency_key, work_proof={})
    frame = model_frame(context, record)
    if statement:
        candidate = answer([dict(kind='native_statement_report', text='The source reports an uncertain flight.',
            statement_handles=[frame['native_statements']['statements'][0]['statement_handle']]),
            dict(kind='native_assertion_claim', text='The Graph retains the qualified description.',
                assertion_handles=[row['assertion_handle'] for row in frame['native_assertions']['assertions']])])
    else:
        candidate = answer([dict(kind='native_assertion_claim', text='The Graph retains the qualified description.',
            assertion_handles=[row['assertion_handle'] for row in frame['native_assertions']['assertions']])])
    from tests.test_surface_native_execution import controller, outcomes, build_resolution, execution
    semantic = controller('build', record.policy, sequence=len(record.events))
    events = [*record.events, semantic, *outcomes(semantic, len(record.events) + 1)]
    events.append(build_resolution(record.policy, semantic, len(events), turn_id=turn.turn_id))
    record = execution(context.context_receipt_sha256, record.policy, events)
    stored, auth, proof = producing_case(context, record, candidate, work=work)
    result = normalize_output(context, stored, auth, **proof)
    import os
    if statement and (destination := os.environ.get('DMB_NATIVE_AUTHORED_WIRE')):
        import json
        from pathlib import Path
        Path(destination).write_text(json.dumps(dict(receipt=context.model_dump(mode='json', by_alias=True),
            completion=result.model_dump(mode='json', by_alias=True)), indent=2) + '\n')
    read = turn.graph_context_execution.events[-1]
    assert auth.native_read_event_ids == (read.event_id,)
    citations = result.native_clause_citations if statement else result.native_assertion_citations
    assert citations and all(c.read_revision_id == core.query.authority.revision_id for c in citations)
    if not statement:
        assert all(c.read_event_id == read.event_id for c in citations)
        assert result.answer_segments[0].qualifications
    # This source-owner check receives the already proved producing component;
    # ordinary Build factory/completion persistence is still a separate gate.
    completed = turn.model_copy(update={'status': 'completed', 'completion': result,
        'graph_context_execution': stored})
    monkeypatch.setattr(native, 'reopen_context', lambda query, principal: core
        if query == core.query and principal == GM else pytest.fail('Original pinned query changed'))
    service = SimpleNamespace(inspect_turn=lambda **_: completed)
    opened = (open_clause if statement else open_assertion_source)(world_id=turn.world_id,
        turn_id=turn.turn_id, citation_index=0, principal=GM, service=service)
    assert opened.content and opened.citation == citations[0]
    assert opened.citation.provider_attempt_id == auth.provider_attempt_id


@pytest.mark.parametrize('mutation', ['turn', 'conversation', 'attempt'])
def test_native_human_writer_work_cannot_borrow_another_capture(lane, mutation):
    from application_state.agent_conversation.native_writer import model_work_frame
    _core, _service, turn = read_human(lane)
    work = dict(world_id=turn.world_id, conversation_id=turn.conversation_id, turn_id=turn.turn_id,
        attempt=turn.attempt, provenance=turn.provenance, idempotency_key=turn.idempotency_key, work_proof={})
    work[{'turn': 'turn_id', 'conversation': 'conversation_id', 'attempt': 'attempt'}[mutation]] = (
        2 if mutation == 'attempt' else uuid4())
    with pytest.raises(ValueError, match='another request or attempt'):
        model_work_frame(turn.graph_context_receipt, turn.graph_context_execution, **work)


def test_native_retrieval_and_writer_wait_for_all_human_targets(lane):
    from application_state.errors import ApplicationStateValidationError
    from tests.test_surface_native_execution import controller, outcomes, build_resolution, execution, native_writer
    from application_state.agent_conversation.native_retrieval import validate_decision_phases
    publish(lane)
    selected = references(lane)
    _core, service, turn = native_build_case(lane, selected)
    turn = append_native(service, turn, 'capture_native_authored_references', event_id=uuid4())
    record = turn.graph_context_execution
    semantic = controller('build', record.policy, sequence=len(record.events))
    events = [*record.events, semantic, *outcomes(semantic, len(record.events) + 1)]
    events.append(build_resolution(record.policy, semantic, len(events), turn_id=turn.turn_id))
    record = execution(turn.graph_context_receipt.context_receipt_sha256, record.policy, events)
    retrieval = controller('build', record.policy, sequence=len(events), semantic=False)
    with pytest.raises(ValueError, match='settled author-requested'):
        validate_decision_phases(record.model_copy(update={'events': [*events, retrieval]}))
    writer = native_writer('build', record.policy, sequence=len(events))
    with pytest.raises(ValueError, match='settled reads'):
        validate_decision_phases(record.model_copy(update={'events': [*events, writer]}))
    with pytest.raises(ApplicationStateValidationError):
        append_native(service, turn, 'authorize_native_authored_reference', event_id=uuid4(), node_id='ent:unrequested')
    assert service.inspect_turn(world_id=turn.world_id, turn_id=turn.turn_id) == turn


def test_human_acquisition_cannot_resume_after_native_finish(lane):
    from tests.test_surface_native_execution import controller, outcomes, build_resolution, choice, execution
    from application_state.agent_conversation.native_retrieval import validate_decision_phases
    _core, _service, turn = read_human(lane)
    record, context = turn.graph_context_execution, turn.graph_context_receipt
    semantic = controller('build', record.policy, sequence=len(record.events))
    events = [*record.events, semantic, *outcomes(semantic, len(record.events) + 1)]
    events.append(build_resolution(record.policy, semantic, len(events), turn_id=turn.turn_id))
    retrieval = controller('build', record.policy, sequence=len(events), semantic=False)
    events += [retrieval, *outcomes(retrieval, len(events) + 1)]
    events.append(choice(context, record, retrieval, len(events), 'finish_retrieval'))
    finished = execution(context.context_receipt_sha256, record.policy, events)
    late = record.events[1].model_copy(update={'event_id': uuid4(), 'sequence': len(events)})
    with pytest.raises(ValueError, match='cannot resume'):
        validate_decision_phases(finished.model_copy(update={'events': [*events, late]}))


@pytest.mark.parametrize('records', ['grant', 'read', 'pair'])
def test_empty_reference_input_refuses_orphan_human_records_without_capture(records):
    from application_state.agent_conversation import types as t
    from application_state.agent_conversation.authored_graph_references import (
        BuildAuthoredReferenceAuthorizedV2, BuildAuthoredReferenceReadV2)
    from application_state.agent_conversation.native_execution import validate_context_binding
    from tests.test_surface_native_execution import component, execution
    context, record = component('build')
    wire = record.policy.action.intent.model_dump(mode='json', by_alias=True)
    wire.update(schema='dmb_build_graph_intent_v2',
        authored_references=AuthoredGraphReferencesV1(references=()).model_dump(mode='json', by_alias=True))
    intent = t.BuildGraphIntentV2.model_validate(wire)
    policy = record.policy.model_copy(update={'action': record.policy.action.model_copy(update={'intent': intent})})
    record = execution(context.context_receipt_sha256, policy)
    validate_context_binding(context, record)  # Empty input without captures/reads remains legitimate.
    grant = BuildAuthoredReferenceAuthorizedV2(event_id=uuid4(), sequence=0, capture_event_id=uuid4(),
        node_id='ent:unrequested', query_sha256=record.policy.native_query_sha256,
        context_receipt_sha256=record.context_receipt_sha256, execution_policy_sha256=record.execution_policy_sha256)
    read = BuildAuthoredReferenceReadV2(event_id=uuid4(), sequence=1 if records == 'pair' else 0,
        capture_event_id=grant.capture_event_id, authorization_event_id=grant.event_id, node_id=grant.node_id,
        statement_reads=(), assertion_reads=(), unavailable_statement_ids=(), unavailable_assertion_ids=(), status='complete')
    events = [grant, read] if records == 'pair' else [grant] if records == 'grant' else [read]
    with pytest.raises(ValueError, match='captured|captured before'):
        changed = execution(context.context_receipt_sha256, policy, events)
        validate_context_binding(context, changed)
