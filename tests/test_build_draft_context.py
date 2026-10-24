"""Current-draft identity and provenance tests; no provider or retained state IO."""
from hashlib import sha256
from types import SimpleNamespace
from uuid import UUID

import pytest
from pydantic import ValidationError

from application_state.agent_conversation.build_draft_context import (
    POLICY, BuildDraftSnapshotV1, BuildDraftContextRequestV1, BuildDraftContextRecordV1, digest,
    validate_record, validate_writer_reference, writer_reference,
)


def snapshot(text="Unsaved orchid keepers 🌸"):
    return BuildDraftSnapshotV1(world_id="example-world", document_id="example-page",
        registry_revision=3, content_sha256="a" * 64, visibility="internal",
        draft_markdown=text, draft_sha256=sha256(text.encode()).hexdigest(),
        editor_sha256="b" * 64, draft_generation=8)


def owner(snap=None):
    snap = snap or snapshot()
    record = BuildDraftContextRecordV1(record_id=UUID(int=1), turn_id=UUID(int=2),
        conversation_id=UUID(int=3), attempt=1, submitted_intent_fingerprint="c" * 64, expected_pointer_revision=1, snapshot=snap)
    context_sha = digest(BuildDraftContextRequestV1(snapshot=snap, conversation_id=record.conversation_id, expected_pointer_revision=1).model_dump(mode="json", by_alias=True))
    turn = SimpleNamespace(submitted_intent_v2=SimpleNamespace(build_draft_context_sha256=context_sha), turn_id=record.turn_id, conversation_id=record.conversation_id,
        world_id=snap.world_id, attempt=1, submitted_intent_fingerprint_v2=record.submitted_intent_fingerprint,
        graph_context_execution=SimpleNamespace(policy=SimpleNamespace(
            working_draft_context_policy=POLICY, working_draft_snapshot_sha256=snap.snapshot_sha256, working_draft_context_sha256=context_sha)),
        graph_context_receipt=SimpleNamespace(source_basis=SimpleNamespace(
            model_dump=lambda **_: snap.saved_basis())))
    return record, turn


def test_draft_body_is_complete_in_writer_and_absent_from_routing_reference():
    record, turn = owner()
    validate_record(record, turn)
    value = writer_reference(record)
    validate_writer_reference(value, record, turn)
    assert value["draft_markdown"] == record.snapshot.draft_markdown
    assert "draft_markdown" not in record.snapshot.reference()
    assert "saved_source" not in value["role"] and "not_world_or_played_truth" in value["role"]
    assert not any(key in value for key in ("source_read_id", "section_read_ids", "evidence_ref_id"))


@pytest.mark.parametrize("text", ["", "A" * 100_000, "中文 🌸\nSecond paragraph"])
def test_no_new_arbitrary_length_limit_and_exact_utf8_digest(text):
    snap = snapshot(text)
    assert BuildDraftSnapshotV1.model_validate_json(snap.model_dump_json(by_alias=True)) == snap
    with pytest.raises(ValidationError, match="captured Markdown digest"):
        BuildDraftSnapshotV1.model_validate({**snap.model_dump(), "draft_markdown": text + "changed"})


@pytest.mark.parametrize("field,value", [
    ("world_id", "another-world"), ("attempt", 2), ("turn_id", UUID(int=4)),
    ("conversation_id", UUID(int=4)), ("submitted_intent_fingerprint_v2", "d" * 64),
])
def test_frozen_turn_identity_rejects_other_attempt_or_owner(field, value):
    record, turn = owner()
    setattr(turn, field, value)
    with pytest.raises(ValueError, match="accepted turn"):
        validate_record(record, turn)


def test_frozen_context_capability_and_complete_writer_body_are_required():
    record, turn = owner()
    changed = {**writer_reference(record), "draft_markdown": "Saved text substituted"}
    with pytest.raises(ValueError, match="included context record"):
        validate_writer_reference(changed, record, turn)
    turn.graph_context_execution.policy.working_draft_snapshot_sha256 = "d" * 64
    with pytest.raises(ValueError, match="frozen context capability"):
        validate_record(record, turn)


def test_newer_work_is_an_independent_snapshot_without_mutating_previous_record():
    first, turn = owner()
    second = snapshot("A newer unsaved paragraph")
    assert second.snapshot_sha256 != first.snapshot.snapshot_sha256
    assert first.snapshot.draft_markdown == "Unsaved orchid keepers 🌸"
    with pytest.raises(ValidationError):
        first.snapshot.draft_markdown = second.draft_markdown
    validate_record(first, turn)


@pytest.mark.parametrize("field,value", [("registry_revision", True), ("draft_generation", False),
    ("registry_revision", 0), ("draft_generation", -1), ("editor_sha256", "bad")])
def test_malformed_capture_identity_is_rejected(field, value):
    with pytest.raises(ValidationError):
        BuildDraftSnapshotV1.model_validate({**snapshot().model_dump(), field: value})


@pytest.fixture
def draft_build_case(tmp_path, monkeypatch, application_state_dsn):
    from tests.test_agent_build_jev_ordinary_harness import build_case
    return build_case.__wrapped__(tmp_path, monkeypatch, application_state_dsn)


@pytest.mark.parametrize("same_as_saved", [False,True,"world"])
def test_actual_governed_turn_freezes_read_only_draft_with_request_identity(
    draft_build_case, monkeypatch, tmp_path, same_as_saved,
):
    from uuid import uuid4
    from application_state.agent_conversation import AgentConversationService, types as t
    from apps.live_control_server.models.agent_turn import AgentTurnRequest
    from apps.live_control_server.services.build_jev_harness import BuildJevHarness
    from tests.application_state.test_agent_conversation_postgres import _new
    from tests.test_build_world_context import world_case, WorldDecisions
    from tests.test_agent_build_jev_ordinary_harness import WriterWire
    from tests.test_agent_build_governed_graph import execute
    from tests.test_build_jev_estimated_continuations import counter

    (source, request, bootstrap), _ = world_case(draft_build_case, monkeypatch)
    service = AgentConversationService()
    conversation = _new(service, "elderwyld")
    pointer = service.get_world_pointer("elderwyld")
    text = "Frank believes the western gate is haunted." if same_as_saved=="world" else source.markdown if same_as_saved else "New unsaved prose not in the stored page."
    snap = BuildDraftSnapshotV1(world_id="elderwyld", document_id=source.record.document_id,
        registry_revision=source.loaded_revision, content_sha256=source.content_sha256,
        visibility="internal", draft_markdown=text, draft_sha256=sha256(text.encode()).hexdigest(),
        editor_sha256="b" * 64, draft_generation=1)
    context = BuildDraftContextRequestV1(snapshot=snap, conversation_id=conversation.conversation_id,
        expected_pointer_revision=pointer.revision)
    request = AgentTurnRequest.model_validate({**request.model_dump(mode="json", by_alias=True),
        "turn_id": str(uuid4()), "client_work_state": "saved_dirty",
        "build_draft_context": context.model_dump(mode="json", by_alias=True)})
    harness = BuildJevHarness(world_context=True, named_citations=True,
        decision_transport=WorldDecisions(), writer_transport=WriterWire(), accounting=counter())
    response = execute((source, request, bootstrap), tmp_path, harness)
    assert response.answer.status == "ok"
    import json
    packet = json.loads(json.loads(harness.writer_transport.calls[0].content)["input"])
    assert packet["working_draft_context"]["draft_markdown"] == text
    assert json.dumps(packet, ensure_ascii=False).count(json.dumps(text, ensure_ascii=False)[1:-1]) == 1
    if same_as_saved is True:
        assert any(row.get("text_ref")=="working_draft_context" and "text" not in row
            for row in packet["artifact_under_edit"]["sections"])
    if same_as_saved=="world":
        assert any(row.get("text_ref")=="working_draft_context" for row in packet["opened_passages"])
    (turn,) = service.list_turns("elderwyld", conversation.conversation_id)
    events = [e for e in turn.graph_context_execution.events if isinstance(e, t.BuildDraftContextCapturedV1)]
    assert len(events) == 1
    inclusions = [e for e in turn.graph_context_execution.events if isinstance(e, t.BuildDraftProviderInclusionV1)]
    assert inclusions
    assert all(e.draft_event_id == events[0].event_id for e in inclusions)
    writer_auth = next(e for e in turn.graph_context_execution.events if isinstance(e, t.ProviderAttemptAuthorizedEventV1)
        and (e.provider, e.model, e.api_mode) == turn.graph_context_execution.policy.provider_roles.writer.identity())
    assert any(e.provider_attempt_id == writer_auth.provider_attempt_id and e.envelope_sha256 == writer_auth.envelope_sha256 for e in inclusions)
    from application_state.agent_conversation.build_draft_context import validate_inclusion_input
    producing = next(e for e in inclusions if e.provider_attempt_id == writer_auth.provider_attempt_id)
    raw_input = harness.writer_transport.calls[0].content.decode()
    validate_inclusion_input(producing, turn.graph_context_execution, raw_input)
    forged = json.loads(raw_input)
    forged_packet = json.loads(forged["input"])
    forged_packet["working_draft_context"]["draft_markdown"] = "Substituted saved text"
    forged["input"] = json.dumps(forged_packet)
    forged_json = json.dumps(forged)
    forged_inclusion = producing.model_copy(update={"envelope_sha256": sha256(forged_json.encode()).hexdigest()})
    with pytest.raises(ValueError, match="admitted context"):
        validate_inclusion_input(forged_inclusion, turn.graph_context_execution, forged_json)
    # Ambiguous JSON must not conceal an extra model-visible draft body.
    duplicated = raw_input[:-1] + ',"model":"gpt-6-luna"}'
    duplicate_inclusion = producing.model_copy(update={"envelope_sha256": sha256(duplicated.encode()).hexdigest()})
    with pytest.raises(ValueError, match="Duplicate"):
        validate_inclusion_input(duplicate_inclusion, turn.graph_context_execution, duplicated)
    record = events[0].record
    assert record.snapshot == snap and record.conversation_id == conversation.conversation_id
    assert turn.graph_context_execution.policy.working_draft_context_sha256 == digest(context.model_dump(mode="json", by_alias=True))
    assert record.submitted_intent_fingerprint == turn.submitted_intent_fingerprint_v2
    validate_record(record, turn)
    # Reopened APP rows independently bind draft records to their owning attempt.
    for field, replacement in (("turn_id", str(uuid4())), ("conversation_id", str(uuid4())),
        ("submitted_intent_fingerprint", "d" * 64), ("attempt", turn.attempt + 1)):
        payload = turn.model_dump(mode="json", by_alias=True)
        retained = next(e for e in payload["graph_context_execution"]["events"] if e["kind"] == "build_draft_context_captured_v1")
        retained["record"][field] = replacement
        with pytest.raises(ValidationError, match="accepted turn|frozen context capability"):
            t.Turn.model_validate(payload)
    # Same IDs with a different working copy are a conflict, never an implicit retry.
    from apps.live_control_server.services.agent_turn_service import AgentTurnServiceError
    changed = request.model_dump(mode="json", by_alias=True)
    changed_text = text + " A newer edit."
    changed["build_draft_context"]["snapshot"].update(draft_markdown=changed_text,
        draft_sha256=sha256(changed_text.encode()).hexdigest(), draft_generation=2)
    altered = AgentTurnRequest.model_validate(changed)
    before_calls = (len(harness.decision_transport.calls), len(harness.writer_transport.calls))
    with pytest.raises(AgentTurnServiceError) as conflict:
        execute((source, altered, bootstrap), tmp_path, harness)
    assert conflict.value.code == "turn_idempotency_conflict"
    assert (len(harness.decision_transport.calls), len(harness.writer_transport.calls)) == before_calls
    # Source visibility is server-owned and must be checked before any new model call.
    stale = request.model_dump(mode="json", by_alias=True)
    stale["turn_id"] = str(uuid4())
    stale["build_draft_context"]["snapshot"]["visibility"] = "player_safe"
    stale_request = AgentTurnRequest.model_validate(stale)
    with pytest.raises(AgentTurnServiceError) as stale_failure:
        execute((source, stale_request, bootstrap), tmp_path, harness)
    assert stale_failure.value.code == "build_editor_context_changed"
    assert stale_failure.value.provider_dispatched is False
    assert (len(harness.decision_transport.calls), len(harness.writer_transport.calls)) == before_calls
    if same_as_saved is not True:
        assert source.markdown != text
    from apps.live_control_server.services.workspace_document_registry import get_workspace_document_snapshot
    assert get_workspace_document_snapshot(tmp_path, source.record.document_id).markdown == source.markdown


def test_draft_context_does_not_replace_the_existing_proposal_authority(draft_build_case, monkeypatch, tmp_path):
    from application_state.agent_conversation import AgentConversationService, types as t
    from application_state.build_proposal.service import BuildProposalService
    from apps.live_control_server.models.agent_turn import AgentTurnRequest
    from apps.live_control_server.services.build_jev_harness import BuildJevHarness
    from tests.test_agent_build_jev_ordinary_harness import ordinary_case, DecisionWire, WriterWire
    from tests.test_agent_build_governed_graph import execute
    from tests.test_build_jev_estimated_continuations import counter

    (source, request, bootstrap), _ = ordinary_case(draft_build_case, monkeypatch, authoring=True)
    cap = request.build_write_capability
    cap = cap.model_copy(update={"basis": cap.basis.model_copy(update={"editor_sha256": "b" * 64})})
    snap = BuildDraftSnapshotV1(**{k: getattr(cap.basis, k) for k in (
        "world_id", "document_id", "registry_revision", "content_sha256", "visibility",
        "draft_sha256", "editor_sha256", "draft_generation")}, draft_markdown=cap.draft_markdown)
    context = BuildDraftContextRequestV1(snapshot=snap, conversation_id=cap.conversation_id,
        expected_pointer_revision=cap.expected_pointer_revision)
    payload = {**request.model_dump(mode="json", by_alias=True),
        "build_write_capability": cap.model_dump(mode="json", by_alias=True),
        "build_draft_context": context.model_dump(mode="json", by_alias=True)}
    request = AgentTurnRequest.model_validate(payload)
    harness = BuildJevHarness(world_context=True, named_citations=True, accounting=counter(),
        decision_transport=DecisionWire(operation="propose_build_insertion"), writer_transport=WriterWire())
    response = execute((source, request, bootstrap), tmp_path, harness)
    assert isinstance(response.knowledge_context.completion, t.BuildAuthoringCompletionV1)
    record = BuildProposalService().get("elderwyld", response.knowledge_context.completion.action_id)
    assert record.reservation.basis == cap.basis and not record.inserted_in_draft
    turn = AgentConversationService().list_turns("elderwyld", cap.conversation_id)[0]
    assert len([e for e in turn.graph_context_execution.events if isinstance(e,t.BuildDraftContextCapturedV1)]) == 1
    # A write target cannot quietly borrow a different readable working copy.
    payload["build_draft_context"]["snapshot"].update(draft_generation=999)
    with pytest.raises(ValidationError, match="same capture"):
        AgentTurnRequest.model_validate(payload)


@pytest.mark.parametrize("invalid_reference", [False,True])
def test_draft_only_answer_is_durable_without_saved_or_world_citations(draft_build_case, monkeypatch, tmp_path, invalid_reference):
    import json
    import httpx
    from application_state.agent_conversation import AgentConversationService, types as t
    from apps.live_control_server.models.agent_turn import AgentTurnRequest
    from apps.live_control_server.services.build_jev_harness import BuildJevHarness
    from tests.test_agent_build_jev_ordinary_harness import ordinary_case, WriterWire
    from tests.test_build_writer_selection import SelectionWire
    from tests.test_agent_build_governed_graph import execute
    from tests.test_build_jev_estimated_continuations import counter

    class DraftWriter(WriterWire):
        async def handle_async_request(self, request):
            response = await super().handle_async_request(request)
            packet = json.loads(json.loads(request.content)["input"])
            lane = packet["working_draft_context"]
            data = response.json()
            data["output"][0]["content"][0]["text"] = json.dumps({
                "answer_context_status":"authored_grounded", "limitations":[], "requested_detail_gaps":[],
                "answer_segments":[{"kind":"draft_reference_claim", "draft_record_id":"00000000-0000-4000-8000-000000000000" if invalid_reference else lane["record_id"],
                    "text":"Your current draft says: "+lane["draft_markdown"]}]})
            return httpx.Response(200, request=request, json=data)

    (source, request, bootstrap), reads = ordinary_case(draft_build_case, monkeypatch, authoring=True)
    cap = request.build_write_capability
    text = "Orchid keepers hold a midnight lantern watch."
    snap = BuildDraftSnapshotV1(**{k:getattr(cap.basis,k) for k in (
        "world_id","document_id","registry_revision","content_sha256","visibility","draft_generation")},
        draft_markdown=text,draft_sha256=sha256(text.encode()).hexdigest(),editor_sha256="b"*64)
    context = BuildDraftContextRequestV1(snapshot=snap, conversation_id=cap.conversation_id,
        expected_pointer_revision=cap.expected_pointer_revision)
    payload = {**request.model_dump(mode="json", by_alias=True), "build_write_capability":None,
        "message":"What does my current draft say about the orchid keepers?", "client_work_state":"saved_dirty",
        "build_draft_context":context.model_dump(mode="json",by_alias=True)}
    request = AgentTurnRequest.model_validate(payload)
    writer = DraftWriter()
    harness = BuildJevHarness(world_context=True,named_citations=True,accounting=counter(),
        decision_transport=SelectionWire("empty"),writer_transport=writer)
    if invalid_reference:
        from apps.live_control_server.services.agent_turn_service import AgentTurnServiceError
        with pytest.raises(AgentTurnServiceError):
            execute((source,request,bootstrap),tmp_path,harness)
        service=AgentConversationService()
        failed=service.list_turns("elderwyld",cap.conversation_id)[0]
        assert failed.status=="interrupted" and failed.completion is None
        traces=service.list_context_trace_attempts(world_id="elderwyld",turn_id=failed.turn_id)
        raw=[m.get("text","") for trace in traces for o in trace.model_dump(mode="json",by_alias=True)["observations"]
            if o["kind"]=="context_snapshot" for m in o.get("materials",[]) if m.get("role")=="assistant"]
        assert any('00000000-0000-4000-8000-000000000000' in value for value in raw)
        return
    response = execute((source,request,bootstrap),tmp_path,harness)
    completion = response.knowledge_context.completion
    assert isinstance(completion,t.BuildDraftContextCompletionV1)
    assert completion.answer_context_status == "authored_grounded"
    assert completion.source_citations == [] and completion.citation_map is None
    assert completion.answer_segments[0].kind == "draft_reference_claim"
    assert reads == {"graph":0,"source":0}
    assert len(writer.calls) == 1
    turn = AgentConversationService().list_turns("elderwyld",cap.conversation_id)[0]
    assert turn.completion == completion
    assert t.Turn.model_validate_json(turn.model_dump_json(by_alias=True)).completion == completion
    from apps.live_control_server.services.workspace_document_registry import get_workspace_document_snapshot
    assert get_workspace_document_snapshot(tmp_path,source.record.document_id).markdown == source.markdown

    # A new user turn captures newer prose without mutating the first turn's snapshot.
    from uuid import uuid4
    later_text=text+" The keepers now trade copper lanterns."
    later_payload=request.model_dump(mode="json",by_alias=True)
    later_payload["turn_id"]=str(uuid4())
    later_payload["message"]="What does the newer draft say?"
    later_payload["build_draft_context"]["snapshot"].update(draft_markdown=later_text,
        draft_sha256=sha256(later_text.encode()).hexdigest(),draft_generation=2)
    later_request=AgentTurnRequest.model_validate(later_payload)
    later_runtime=BuildJevHarness(world_context=True,named_citations=True,accounting=counter(),
        decision_transport=SelectionWire("empty"),writer_transport=DraftWriter())
    later=execute((source,later_request,bootstrap),tmp_path,later_runtime)
    assert "trade copper lanterns" in later.answer.text
    assert later.knowledge_context.completion.source_citations==[]
    retained=AgentConversationService().list_turns("elderwyld",cap.conversation_id)
    snapshots=[e.record.snapshot.draft_markdown for row in retained for e in row.graph_context_execution.events if isinstance(e,t.BuildDraftContextCapturedV1)]
    assert set(snapshots)=={text,later_text}
    assert get_workspace_document_snapshot(tmp_path,source.record.document_id).markdown==source.markdown
    from alembic import command
    from application_state.cli import alembic_config
    with pytest.raises(RuntimeError, match="retained working-draft"):
        command.downgrade(alembic_config(), "20261023_0060")
    assert any(row.completion==completion for row in AgentConversationService().list_turns("elderwyld",cap.conversation_id))


def test_draft_answer_does_not_force_an_evidence_gap_into_a_creative_proposal():
    from application_state.agent_conversation.build_draft_answer import DraftWriterAnswerV1
    answer = DraftWriterAnswerV1.model_validate({"answer_context_status":"insufficient_evidence",
        "answer_segments":[{"kind":"discussion","text":"The requested related source was not available."}],
        "limitations":["missing_requested_details"],"requested_detail_gaps":[]})
    assert answer.answer_context_status == "insufficient_evidence"
    with pytest.raises(ValidationError,match="explicit qualification"):
        DraftWriterAnswerV1.model_validate({**answer.model_dump(mode="json"),"limitations":[]})
