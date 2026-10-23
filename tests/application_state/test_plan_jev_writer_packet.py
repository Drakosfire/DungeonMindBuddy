"""Actual locked Plan writer admission; source content remains byte-exact."""
import json
from types import SimpleNamespace
from uuid import uuid4
import psycopg
import pytest
from application_state.agent_conversation import types as t
from application_state.agent_conversation.plan_jev_graph_packet import project, producing_closures
from application_state.agent_conversation.rules_authority_types import canonical_bytes, canonical_sha256
from application_state.errors import ApplicationStateValidationError
from tests.application_state.test_plan_jev_decision_admission import prepare_case, append, digest, snapshot
from tests.application_state.test_agent_conversation_postgres import _provider_authorization_event



@pytest.fixture(autouse=True)
def current_native_writer_policy(monkeypatch):
    from application_state.agent_conversation import AgentConversationService
    original=AgentConversationService.accept_turn
    def accept(service,submission):
        execution=submission.graph_context_execution
        if isinstance(execution.policy,t.PlanJevRetrievalPolicyV1) and not isinstance(execution.policy,t.PlanNativeSourceSectionsPolicyV1):
            policy=t.PlanNativeSourceSectionsPolicyV1.model_validate(execution.policy.model_dump(mode='json',by_alias=True)|{
                'native_source_section_policy':'exact_native_source_sections_v1'})
            wire=execution.model_dump(mode='json',by_alias=True)
            wire['policy']=policy.model_dump(mode='json',by_alias=True)
            wire['execution_policy_sha256']=t.canonical_sha256({'schema':execution.schema_,
                'context_receipt_sha256':execution.context_receipt_sha256,'policy':wire['policy']})
            submission=submission.model_copy(update={'graph_context_execution':type(execution).model_validate(wire)})
        return original(service,submission)
    monkeypatch.setattr(AgentConversationService,'accept_turn',accept)

def trace(case):
    with psycopg.connect(case.dsn) as conn:
        return conn.execute("SELECT payload FROM agent.turn_context_trace WHERE turn_id=%s AND attempt=%s",
            (case.turn.turn_id, case.turn.attempt)).fetchone()[0]


def evidence(case, packets=None):
    return {"graph_packets": packets or {}, "source_names": {}, "plan_markdown": case.plan_markdown,
        "session_evidence": [], "dialogue": [{"role": "user", "content": "Earlier conversation reference."}]}


def writer_request(case, proof, extra_messages=()):
    projection = project(case.turn, proof, trace(case))
    raw = json.dumps({"model": "synthetic-model", "tools": [], "input": [
        {"role": "user", "content": canonical_bytes(projection.frame).decode()}, *extra_messages]}, ensure_ascii=False)
    producer = uuid4()
    base = _provider_authorization_event(attempt_id=producer, sequence=len(case.turn.graph_context_execution.events))
    auth = t.PlanJevWriterAuthorizedV1.model_validate(base.model_dump(mode="python") | {
        "kind": "plan_jev_writer_authorized_v1", "api_mode": "codex_responses", "envelope_sha256": digest(raw),
        "frame_sha256": canonical_sha256(projection.frame), "included_source_read_event_ids": list(projection.source_event_ids),
        "included_graph_event_ids": list(projection.graph_event_ids), "included_assertion_ids": list(projection.assertion_ids),
        "included_relationship_ids": list(projection.relationship_ids), "included_evidence_ref_ids": list(projection.evidence_ref_ids)})
    return auth, raw


def admit_writer(case, *, packets=None, extra_messages=()):
    proof = evidence(case, packets)
    auth, raw = writer_request(case, proof, extra_messages)
    case.turn, fresh = case.service.authorize_plan_jev_writer(case.turn.world_id, case.turn.conversation_id,
        case.turn.turn_id, expected_revision=case.turn.revision, expected_attempt=case.turn.attempt,
        authorization=auth, producer_proof={"prepared_request_json": raw, "evidence": proof})
    assert fresh
    case.raw, case.producer = raw, auth.provider_attempt_id
    return auth, proof


def record(case, *, with_source=False, incomplete=False):
    authority = case.turn.graph_context_receipt.graph_authority
    raw = json.dumps({"schema": "dmb_world_graph_retrieval_result_v1", "snapshot": {
        "worldId": authority.native_world_id, "revisionId": authority.graph_revision},
        "nodes": [{"nodeId": "pond", "label": "Park Pond", "kind": "location"}],
        "attributes": [{"assertionId": "pond-road", "subjectNodeId": "pond", "predicate": "has_road",
            "value": "A wooden walkway", "epistemicKind": "reported", "temporalScope": "past",
            "evidenceRefIds": ["evidence:pond"], "sourceArtifactId": "artifact:pond"}],
        "sourceAnchors": [{"anchorId": "anchor:pond", "evidenceRefId": "evidence:pond"}]}, ensure_ascii=False)
    event = t.ValidatedGraphOperationEventV3(kind="validated_graph_operation_v3", event_id=uuid4(),
        sequence=len(case.turn.graph_context_execution.events), operation_id=uuid4(), operation="search_assertions",
        request_arguments_sha256="a" * 64, graph_revision=authority.graph_revision, result_packet_sha256=canonical_sha256(json.loads(raw)),
        assertion_ids=["pond-road"], relationship_ids=[], evidence_ref_ids=["evidence:pond"],
        evidence_sufficiency_status="insufficient" if incomplete else "sufficient",
        coverage_status="incomplete" if incomplete else "complete", truncated=incomplete, source_opened=False,
        returned_source_pins=([t.GraphSourceScopeAnchorV2(anchor_id="anchor:pond", evidence_ref_id="evidence:pond",
            source_artifact_id="artifact:pond", source_revision_id="source:pond:1")] if with_source else []))
    case.turn, _ = case.service.append_validated_graph_operation(case.turn.world_id, case.turn.conversation_id,
        case.turn.turn_id, expected_revision=case.turn.revision, expected_attempt=case.turn.attempt, operation_event=event)
    return {event.event_id: raw}


def test_writer_admission_binds_real_plan_and_qualified_records(application_state_dsn):
    case = prepare_case(application_state_dsn); append(case)
    packets = record(case)
    case.redecide("finish_retrieval"); append(case)
    auth, proof = admit_writer(case, packets=packets)
    projected = project(case.turn, proof, trace(case))
    actual = projected.frame["graph_records"][0]
    assert actual["record"]["epistemicKind"] == "reported" and actual["record"]["temporalScope"] == "past"
    assert "sourceArtifactId" not in actual["record"] and actual["evidence"] == ["e0"]
    assert projected.frame["entity_index"] == [{"nodeId": "pond", "label": "Park Pond", "kind": "location"}]
    closures = producing_closures(case.turn, auth, SimpleNamespace(prepared_request_json=case.raw, graph_packets=packets))
    assert closures == (("assertion", "pond-road", ("evidence:pond",)),)
    replay, fresh = case.service.authorize_plan_jev_writer(case.turn.world_id, case.turn.conversation_id,
        case.turn.turn_id, expected_revision=case.turn.revision, expected_attempt=case.turn.attempt,
        authorization=auth, producer_proof={"prepared_request_json": case.raw, "evidence": proof})
    assert replay == case.turn and not fresh


@pytest.mark.parametrize("mutation", ["plan", "record", "request", "frame", "model", "hidden_tool", "missing_trace"])
def test_writer_cannot_admit_changed_or_foreign_material(application_state_dsn, mutation):
    case = prepare_case(application_state_dsn); append(case); packets = record(case)
    case.redecide("finish_retrieval"); append(case)
    proof = evidence(case, packets); auth, raw = writer_request(case, proof)
    if mutation == "plan": proof = proof | {"plan_markdown": "changed"}
    elif mutation == "record": proof = proof | {"graph_packets": {key: value.replace("wooden", "stone") for key, value in packets.items()}}
    elif mutation == "request": raw += " "
    elif mutation == "frame": auth = auth.model_copy(update={"frame_sha256": "f" * 64})
    elif mutation == "model":
        body = json.loads(raw); body["model"] = "foreign"; raw = json.dumps(body); auth = auth.model_copy(update={"envelope_sha256": digest(raw)})
    elif mutation == "hidden_tool":
        body = json.loads(raw); body["input"].append({"type": "custom_tool_call", "name": "fake"}); raw = json.dumps(body)
        auth = auth.model_copy(update={"envelope_sha256": digest(raw)})
    else:
        with psycopg.connect(case.dsn) as conn:
            conn.execute("DELETE FROM agent.turn_context_trace WHERE turn_id=%s", (case.turn.turn_id,))
    before = snapshot(case)
    with pytest.raises(ApplicationStateValidationError):
        case.service.authorize_plan_jev_writer(case.turn.world_id, case.turn.conversation_id,
            case.turn.turn_id, expected_revision=case.turn.revision, expected_attempt=case.turn.attempt,
            authorization=auth, producer_proof={"prepared_request_json": raw, "evidence": proof})
    assert snapshot(case) == before



def read_source(case, *, incomplete=False):
    from application_state.agent_conversation.context_trace import TraceSourcePassage
    packets = record(case, with_source=True, incomplete=incomplete)
    execution = case.turn.graph_context_execution
    authority = case.turn.graph_context_receipt.graph_authority
    origin = execution.events[-1]
    scope = execution.policy.source_read_scope
    extension = t.SourceScopeExtensionEventV3(kind="source_scope_extension_v3", event_id=uuid4(),
        sequence=len(execution.events), origin_graph_event_id=origin.event_id,
        context_receipt_sha256=execution.context_receipt_sha256, execution_policy_sha256=execution.execution_policy_sha256,
        world_id=case.turn.world_id, native_world_id=authority.native_world_id, binding_version=authority.binding_version,
        campaign_id=None, graph_revision=authority.graph_revision, retrieval_session_id=scope.retrieval_session_id,
        pins=origin.returned_source_pins)
    case.turn, _ = case.service.extend_source_scope(case.turn.world_id, case.turn.conversation_id, case.turn.turn_id,
        expected_revision=case.turn.revision, expected_attempt=case.turn.attempt, extension=extension)
    authorization = t.SourceReadAuthorizationEventV2(kind="source_read_authorized_v2", event_id=uuid4(),
        sequence=len(case.turn.graph_context_execution.events), read_call_id=uuid4(),
        context_receipt_sha256=execution.context_receipt_sha256, execution_policy_sha256=execution.execution_policy_sha256,
        retrieval_session_id=scope.retrieval_session_id, world_id=scope.world_id, campaign_id=None,
        graph_revision=authority.graph_revision, anchors=origin.returned_source_pins, max_chars=12000)
    case.turn, _ = case.service.authorize_source_read(case.turn.world_id, case.turn.conversation_id, case.turn.turn_id,
        expected_revision=case.turn.revision, expected_attempt=case.turn.attempt, authorization=authorization)
    text = "The account reports a wooden walkway."
    receipt = t.SourceReadAnchorReceiptV2(source_read_id="synthetic-pond-read", anchor_id="anchor:pond",
        evidence_ref_id="evidence:pond", source_artifact_id="artifact:pond", source_revision_id="source:pond:1",
        outcome="enough", content_sha256=digest(text), line_start=3, line_end=3,
        returned_chars=len(text), truncated=incomplete,
        evidence_sufficiency_status="insufficient" if incomplete else "sufficient")
    event = t.ValidatedSourceReadEventV2(kind="validated_source_read_v2", event_id=uuid4(),
        sequence=len(case.turn.graph_context_execution.events), read_call_id=authorization.read_call_id, receipts=[receipt])
    passage = TraceSourcePassage(sequence=0, elapsed_ms=1, source_read_event_id=event.event_id,
        read_call_id=authorization.read_call_id, world_id=case.turn.world_id, graph_revision=authority.graph_revision,
        source_read_id=receipt.source_read_id, anchor_id=receipt.anchor_id, evidence_ref_id=receipt.evidence_ref_id,
        source_artifact_id=receipt.source_artifact_id, source_revision_id=receipt.source_revision_id,
        line_start=3, line_end=3, outcome="enough", returned_chars=len(text), content_sha256=digest(text), text=text)
    case.turn, _ = case.service.record_validated_source_read(case.turn.world_id, case.turn.conversation_id, case.turn.turn_id,
        expected_revision=case.turn.revision, expected_attempt=case.turn.attempt, receipt=event, source_passages=[passage])
    case.trace_sequence = len(trace(case)["observations"])
    return packets, text, event.event_id


def test_writer_source_passage_comes_once_from_protected_receipt(application_state_dsn):
    case = prepare_case(application_state_dsn); append(case)
    packets, text, read_event_id = read_source(case)
    case.redecide("finish_retrieval"); append(case)
    proof = evidence(case, packets) | {"source_names": {"synthetic-pond-read": "Synthetic Session Notes"}}
    auth, raw = writer_request(case, proof)
    frame = project(case.turn, proof, trace(case)).frame
    from application_state.agent_conversation.surface_source_answer import passage_handle
    source_receipt = next(e for e in case.turn.graph_context_execution.events if e.event_id == read_event_id).receipts[0]
    assert frame["opened_passages"] == [{"passage_handle": passage_handle(source_receipt), "evidence": "e0", "source_name": "Synthetic Session Notes",
        "text": text, "line_start": 3, "line_end": 3, "outcome": "enough",
        "truncated": False, "evidence_sufficiency": "sufficient"}]
    assert frame["unopened_evidence"] == [] and auth.included_source_read_event_ids == [read_event_id]
    assert raw.count(text) == 1 and "artifact:pond" not in raw and "source:pond:1" not in raw
    case.service.authorize_plan_jev_writer(case.turn.world_id, case.turn.conversation_id, case.turn.turn_id,
        expected_revision=case.turn.revision, expected_attempt=case.turn.attempt, authorization=auth,
        producer_proof={"prepared_request_json": raw, "evidence": proof})


def test_changed_source_prose_cannot_gain_producing_authority(application_state_dsn):
    case = prepare_case(application_state_dsn); append(case)
    packets, text, _ = read_source(case)
    case.redecide("finish_retrieval"); append(case)
    proof = evidence(case, packets); auth, raw = writer_request(case, proof)
    changed = raw.replace(text, "The account proves a stone bridge.")
    auth = auth.model_copy(update={"envelope_sha256": digest(changed)})
    with pytest.raises(ApplicationStateValidationError):
        case.service.authorize_plan_jev_writer(case.turn.world_id, case.turn.conversation_id, case.turn.turn_id,
            expected_revision=case.turn.revision, expected_attempt=case.turn.attempt, authorization=auth,
            producer_proof={"prepared_request_json": changed, "evidence": proof})


def test_native_plan_writer_accepts_opened_source_citation_atomically(application_state_dsn):
    from application_state.agent_conversation.rules_authority_events import (
        RulesPlanPacketProviderAuthorizedV1, RulesPlanPacketProviderIncludedV1, RulesNativeProviderOutcomeV1,
    )
    from application_state.agent_conversation.rules_authority_plan_packet import build_plan_rules_frame
    from application_state.agent_conversation.native_rules_output import NativeRulesOutputProofV1, normalize_unused_native_output
    from tests.application_state.test_plan_jev_decision_admission import rules_scope
    from tests.application_state.test_plan_rules_packet_admission import graph_finish
    case = prepare_case(application_state_dsn); append(case)
    packets, _, _ = read_source(case)
    case.redecide("finish_retrieval"); append(case)
    scope = rules_scope(case)
    record = case.service.begin_rules_execution(scope, expected_turn_revision=case.turn.revision)
    rules_frame = build_plan_rules_frame(record.execution, ())
    admit_writer(case, packets=packets, extra_messages=({"role": "user", "content": canonical_bytes(rules_frame).decode()},))
    auth = RulesPlanPacketProviderAuthorizedV1(kind="plan_packet_provider_authorized", event_id=uuid4(),
        sequence=len(record.execution.events), execution_id=scope.execution_id, provider_attempt_id=case.producer,
        request_envelope_sha256=digest(case.raw), plan_context_receipt_sha256=case.turn.graph_context_receipt.context_receipt_sha256,
        matched_outputs=(), declared_support_refs=())
    record = case.service.append_rules_provider_event(scope, expected_turn_revision=case.turn.revision,
        expected_ledger_revision=record.revision, event=auth, prepared_request_json=case.raw)
    included = RulesPlanPacketProviderIncludedV1(kind="plan_packet_provider_included", event_id=uuid4(),
        sequence=len(record.execution.events), execution_id=scope.execution_id, provider_attempt_id=case.producer,
        request_envelope_sha256=digest(case.raw), plan_context_receipt_sha256=auth.plan_context_receipt_sha256,
        matched_outputs=(), support_refs=())
    record = case.service.append_rules_provider_event(scope, expected_turn_revision=case.turn.revision,
        expected_ledger_revision=record.revision, event=included, prepared_request_json=case.raw)
    graph_finish(case, case.producer)
    from application_state.agent_conversation.plan_jev_graph_packet import frame_in_request
    selected = frame_in_request(case.raw)['opened_passages'][0]['passage_handle']
    raw_output = json.dumps({"schema":"dmb_surface_evidence_answer_v4","limitations":[],"requested_detail_gaps":[],"answer_segments": [
        {"kind": "graph_claim", "claim_id": "pond-description", "text": "The account reports a wooden walkway by Park Pond.",
         "target_kind": "assertion", "target_id": "pond-road", "passage_handles":[selected]}]})
    capture = SimpleNamespace(authorization_id="synthetic-plan-packet", api_request_id="synthetic-graph-writer",
        provider="test-provider", model="synthetic-model", api_mode="codex_responses", request_sha256=digest(case.raw),
        status="answered", finish_reason="stop", text=raw_output, text_sha256=digest(raw_output),
        text_utf8_bytes=len(raw_output.encode()), tool_calls=())
    record = case.service.append_rules_provider_event(scope, expected_turn_revision=case.turn.revision,
        expected_ledger_revision=record.revision, event=RulesNativeProviderOutcomeV1.from_capture(capture,
            event_id=uuid4(), sequence=len(record.execution.events), execution_id=scope.execution_id,
            provider_attempt_id=case.producer, request_envelope_sha256=digest(case.raw)))
    proof = NativeRulesOutputProofV1.from_capture(capture, prepared_request_json=case.raw,
        rules_execution_id=scope.execution_id, producing_provider_attempt_id=case.producer)
    proof = proof.model_copy(update={"graph_packets": packets})
    completion, bindings, answer = normalize_unused_native_output(case.turn, record.execution, proof)
    result = t.TurnResult(world_id=case.turn.world_id, conversation_id=case.turn.conversation_id, turn_id=case.turn.turn_id,
        expected_revision=case.turn.revision, assistant_text=answer, completion=completion,
        producing_provider_attempt_id=case.producer, claim_graph_event_ids=bindings)
    completed = case.service.complete_native_base_turn(result, output_proof=proof, expected_rules_revision=record.revision)
    entry = completed.completion.citation_map.entries[0]
    assert entry.source_opened and entry.source_read_ids == ["synthetic-pond-read"]
    assert entry.evidence_ref_ids == ["evidence:pond"] and completed.assistant_text == answer
    assert case.service.complete_native_base_turn(result, output_proof=proof, expected_rules_revision=record.revision) == completed


def test_partial_graph_and_enough_but_truncated_source_remain_qualified(application_state_dsn):
    case = prepare_case(application_state_dsn); append(case)
    packets, _, _ = read_source(case, incomplete=True)
    case.redecide("finish_retrieval"); append(case)
    proof = evidence(case, packets)
    frame = project(case.turn, proof, trace(case)).frame
    assert frame["retrieval_results"] == [{
        "records": [0], "evidence": ["e0"],
        "coverage": "incomplete", "truncated": True, "evidence_sufficiency": "insufficient"}]
    passage = frame["opened_passages"][0]
    assert passage["outcome"] == "enough" and passage["truncated"]
    assert passage["evidence_sufficiency"] == "insufficient"
    auth, raw = writer_request(case, proof)
    case.turn, _ = case.service.authorize_plan_jev_writer(case.turn.world_id, case.turn.conversation_id, case.turn.turn_id,
        expected_revision=case.turn.revision, expected_attempt=case.turn.attempt, authorization=auth,
        producer_proof={"prepared_request_json": raw, "evidence": proof})
    changed = raw.replace('incomplete', 'complete')
    auth = auth.model_copy(update={"envelope_sha256": digest(changed)})
    with pytest.raises(ApplicationStateValidationError):
        case.service.authorize_plan_jev_writer(case.turn.world_id, case.turn.conversation_id, case.turn.turn_id,
            expected_revision=case.turn.revision, expected_attempt=case.turn.attempt, authorization=auth,
            producer_proof={"prepared_request_json": changed, "evidence": proof})


@pytest.mark.parametrize("bounded", [True, False])
def test_bounded_search_qualifies_unclosed_records_without_aborting_writer(application_state_dsn, bounded):
    case = prepare_case(application_state_dsn); append(case)
    packets = record(case)
    original_event = case.turn.graph_context_execution.events[-1]
    packet = json.loads(next(iter(packets.values())))
    packet['relationships'] = [{'edgeId': 'other-road', 'predicate': 'leads_to',
        'sourceNodeId': 'pond', 'targetNodeId': 'other', 'evidenceRefIds': ['evidence:outside-page']}]
    raw = json.dumps(packet)
    event = original_event.model_copy(update={'event_id': uuid4(), 'operation_id': uuid4(),
        'sequence': len(case.turn.graph_context_execution.events),
        'result_packet_sha256': canonical_sha256(packet), 'relationship_ids': ['other-road'],
        'coverage_status': 'incomplete' if bounded else 'complete', 'truncated': bounded,
        'evidence_sufficiency_status': 'insufficient' if bounded else 'sufficient'})
    case.turn, _ = case.service.append_validated_graph_operation(case.turn.world_id, case.turn.conversation_id,
        case.turn.turn_id, expected_revision=case.turn.revision, expected_attempt=case.turn.attempt, operation_event=event)
    packets[event.event_id] = raw
    case.redecide('finish_retrieval'); append(case)
    if not bounded:
        with pytest.raises(ValueError, match='exact admitted evidence closure'):
            admit_writer(case, packets=packets)
        return
    auth, proof = admit_writer(case, packets=packets)
    projected = project(case.turn, proof, trace(case))
    assert [r['target_id'] for r in projected.frame['graph_records']] == ['pond-road']
    assert projected.relationship_ids == ()
    assert {'operation': 'graph_retrieval', 'reason': 'incomplete_evidence_closure'} in projected.frame['retrieval_gaps']
    assert producing_closures(case.turn, auth, SimpleNamespace(prepared_request_json=case.raw,
        graph_packets=packets)) == (('assertion', 'pond-road', ('evidence:pond',)),)
