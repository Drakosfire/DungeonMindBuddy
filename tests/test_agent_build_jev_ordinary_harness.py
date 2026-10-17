"""Actual ordinary Build route through GE SDKs and real disposable APP."""

import json
from dataclasses import replace
from hashlib import sha256
from uuid import uuid4

import httpx
import httpx2
import pytest

from application_state.agent_conversation import AgentConversationService
from application_state.agent_conversation import types as ledger
from application_state.build_proposal.service import BuildProposalService
from apps.live_control_server.models.build_document_proposal import BuildWriteCapability
from apps.live_control_server.services import build_document_proposal as proposals
from apps.live_control_server.services.build_jev_harness import BuildJevHarness
from apps.live_control_server.integrations.dungeonmind import selected_observation_reads
from tests.test_agent_build_jev_driver_decisions import driver_case
from tests.test_agent_build_jev_dispatch import build_case as _build_case
from tests.test_agent_build_governed_graph import execute


@pytest.fixture
def build_case(tmp_path, monkeypatch, application_state_dsn):
    monkeypatch.setenv("TYPESAFE_JEV_API_KEY", "synthetic-only")
    monkeypatch.setenv("OPENAI_API_KEY", "synthetic-only")
    return _build_case.__wrapped__(tmp_path, monkeypatch, application_state_dsn)


class DecisionWire(httpx2.AsyncBaseTransport):
    def __init__(self, *, operation="answer_from_sources", timeout=False):
        self.calls, self.operation, self.timeout = [], operation, timeout

    async def handle_async_request(self, request):
        self.calls.append(request)
        if self.timeout:
            raise httpx2.ReadTimeout("synthetic timeout", request=request)
        body = json.loads(request.content)
        state = body["state"]["decision"]["state"]
        acquired = state.get("evidence", [])
        answers = {}
        for key, q in body["questions"].items():
            if q["type"] == "noul":
                answers[key] = {"type": "noul", "noul": 0.99}
                continue
            labels = q["criteria"]
            if key == "operation":
                selected = self.operation
            elif key == "sufficiency":
                selected = "sufficient" if acquired else "more_evidence"
            elif key == "next":
                selected = next((x for x in labels if x.startswith("graph:")), "none")
            elif key == "support":
                selected = acquired[0]["id"] if acquired else "none"
            else:
                selected = "not_useful"
            answers[key] = {
                "type": "choice",
                "choice": selected,
                "confidence": 1,
                "probabilities": {x: float(x == selected) for x in labels},
            }
        return httpx2.Response(
            200,
            request=request,
            json={
                "model": body["model"],
                "usage": {"input_tokens": 23, "output_tokens": 4},
                "answers": answers,
            },
        )


class WriterWire(httpx.AsyncBaseTransport):
    def __init__(self, *, timeout=False, answer_status="source_grounded_partial"):
        self.calls, self.timeout, self.answer_status = [], timeout, answer_status

    async def handle_async_request(self, request):
        self.calls.append(request)
        if self.timeout:
            raise httpx.ReadTimeout("synthetic timeout", request=request)
        body = json.loads(request.content)
        packet = json.loads(body["input"])
        if body["text"]["format"].get("name") == "build_document_proposal":
            text = json.dumps(
                {
                    "replacement_markdown": "| NPC | Job |\n| --- | --- |\n| Nia | Baker |",
                    "summary": "A creative NPC suggestion.",
                    "assumptions": ["Nia is invented."],
                }
            )
        else:
            text = json.dumps(
                {
                    "answer_context_status": self.answer_status,
                    "answer_segments": [
                        {
                            "kind": "source_passage_claim",
                            "text": "Frank believes the western gate is haunted.",
                            "passage_handles": [packet["opened_passages"][0]["handle"]],
                        }
                    ],
                }
            )
        return httpx.Response(
            200,
            request=request,
            json={
                "id": "resp_ordinary",
                "object": "response",
                "created_at": 1,
                "status": "completed",
                "model": "gpt-6-luna",
                "output": [
                    {
                        "type": "message",
                        "id": "msg",
                        "role": "assistant",
                        "status": "completed",
                        "content": [
                            {"type": "output_text", "text": text, "annotations": []}
                        ],
                    }
                ],
                "usage": {
                    "input_tokens": 100,
                    "output_tokens": 40,
                    "total_tokens": 140,
                },
            },
        )


def ordinary_case(build_case, monkeypatch, *, authoring=False):
    adapter, _, calls, _ = driver_case(build_case, monkeypatch)
    # The native selected-observation adapter, with all host admission/persistence
    # still real, returns the same source-bound synthetic observation as object read.
    from apps.live_control_server.integrations.dungeonmind import world_graph_reads

    original = world_graph_reads.get_object_with_reviewed_sources_direct_v3

    def selected(services, request):
        value = original(services, request)
        return replace(
            value,
            result=value.result.model_copy(
                update={
                    "operation": "observations",
                    "requested_node_id": None,
                    "matched_node_ids": ["frank"],
                }
            ),
        )

    monkeypatch.setattr(
        selected_observation_reads, "select_observations_direct", selected
    )
    source, request, _ = build_case
    if authoring:
        service = AgentConversationService()
        # Create a normal World conversation through its owning API.
        from tests.application_state.test_agent_conversation_postgres import _new

        conversation = _new(service, "elderwyld")
        pointer = service.get_world_pointer("elderwyld")
        cap = BuildWriteCapability(
            idempotency_key=uuid4(),
            conversation_id=conversation.conversation_id,
            expected_pointer_revision=pointer.revision,
            draft_markdown=source.markdown,
            basis=dict(
                world_id="elderwyld",
                document_id=source.record.document_id,
                registry_revision=source.loaded_revision,
                content_sha256=source.content_sha256,
                visibility="internal",
                draft_sha256=sha256(source.markdown.encode()).hexdigest(),
                caret=0,
                draft_generation=0,
                selection_generation=0,
            ),
        )
        request = request.model_copy(
            update={
                "message": "Put an invented NPC table on the page.",
                "build_write_capability": cap,
            }
        )
        monkeypatch.setattr(
            proposals,
            "managed_world_data_root",
            lambda: __import__(
                "apps.live_control_server.routes.agent", fromlist=["agent"]
            )._managed_world_root(),
        )
        monkeypatch.setattr(proposals, "get_world_container", lambda *_: object())
        monkeypatch.setattr(proposals, "_model", lambda: "gpt-6-luna")
    return (source, request, adapter.bootstrap), calls


def test_ordinary_source_question_uses_jev_and_exactly_one_cited_writer(
    build_case, monkeypatch, tmp_path
):
    case, calls = ordinary_case(build_case, monkeypatch)
    decisions, writer = DecisionWire(), WriterWire()
    response = execute(
        case,
        tmp_path,
        BuildJevHarness(decision_transport=decisions, writer_transport=writer),
    )
    assert response.answer.text == "Frank believes the western gate is haunted."
    assert len(writer.calls) == 1 and len(decisions.calls) == 4
    assert calls == {"graph": 1, "source": 1}
    service = AgentConversationService()
    turn = service.list_turns(
        "elderwyld", service.get_world_pointer("elderwyld").active_conversation_id
    )[0]
    assert turn.status == "completed" and len(turn.completion.source_citations) == 1
    assert isinstance(
        turn.graph_context_execution.policy, ledger.BuildContainedActionControllerWriterPolicyV1
    )
    selections = [
        e
        for e in turn.graph_context_execution.events
        if isinstance(e, ledger.BuildJevActionSelectionV1)
    ]
    assert len(selections) == 1 and selections[0].operation == "answer_from_sources"
    packet = json.loads(json.loads(writer.calls[0].content)["input"])
    disposition = packet["retrieval_disposition"]
    assert disposition["coverage_status"] == "heuristic_exclusions"
    assert disposition["deferred_unread_ids"] == []
    assert "coverage_judgments" not in disposition
    assert turn.graph_context_execution.policy.frontier_policy == "evidence_bound_deferred_frontier_v1"
    assert response.knowledge_context.delivery_replay is False


def test_ordinary_selected_proposal_is_persisted_in_same_conversation(
    build_case, monkeypatch, tmp_path
):
    case, calls = ordinary_case(build_case, monkeypatch, authoring=True)
    decisions, writer = DecisionWire(operation="propose_build_insertion"), WriterWire()
    response = execute(
        case,
        tmp_path,
        BuildJevHarness(decision_transport=decisions, writer_transport=writer),
    )
    assert response.answer.text == ledger.BUILD_PROPOSAL_READY_TEXT
    assert len(writer.calls) == len(decisions.calls) == 1 and calls == {
        "graph": 0,
        "source": 0,
    }
    completion = response.knowledge_context.completion
    assert isinstance(completion, ledger.BuildAuthoringCompletionV1)
    action = BuildProposalService().get("elderwyld", completion.action_id)
    assert action.state == "proposed" and not action.inserted_in_draft
    assert action.proposal.assumptions == ["Nia is invented."]
    assert action.authorization.provider_attempt_id == completion.provider_attempt_id


def test_default_ordinary_route_selects_jev_without_a_test_runtime_override(
    build_case, monkeypatch, tmp_path
):
    case, _ = ordinary_case(build_case, monkeypatch)
    from apps.live_control_server.services import build_jev_harness as module

    decisions, writer = DecisionWire(), WriterWire()
    decision_provider, writer_provider = (
        module.TypeSafeDecisionProvider,
        module.OpenAITextProvider,
    )

    def make_decision(**kwargs):
        return decision_provider(**{**kwargs, "transport": decisions})

    def make_writer(**kwargs):
        return writer_provider(**{**kwargs, "transport": writer})

    monkeypatch.setattr(module, "TypeSafeDecisionProvider", make_decision)
    monkeypatch.setattr(module, "OpenAITextProvider", make_writer)
    response = execute(case, tmp_path, None)
    assert (
        response.knowledge_context.completion.schema_ == "dmb_build_graph_completion_v2"
    )
    assert len(writer.calls) == 1 and len(decisions.calls) == 4


@pytest.mark.parametrize("failure", ["controller", "writer"])
def test_unknown_provider_never_falls_back_or_replays(
    build_case, monkeypatch, tmp_path, failure
):
    case, _ = ordinary_case(build_case, monkeypatch, authoring=True)
    decisions = DecisionWire(
        operation="propose_build_insertion", timeout=failure == "controller"
    )
    writer = WriterWire(timeout=failure == "writer")
    runtime = BuildJevHarness(decision_transport=decisions, writer_transport=writer)
    from apps.live_control_server.services.agent_turn_service import (
        AgentTurnServiceError,
    )

    with pytest.raises(AgentTurnServiceError):
        execute(case, tmp_path, runtime)
    counts = len(decisions.calls), len(writer.calls)
    assert counts == (1, 0 if failure == "controller" else 1)
    assert len(runtime.calls) == sum(counts)
    assert runtime.calls[-1]["status"] == "error"
    assert runtime.calls[-1]["usage"]["status"] == "unavailable"
    with pytest.raises(AgentTurnServiceError):
        execute(case, tmp_path, runtime)
    assert (len(decisions.calls), len(writer.calls)) == counts


@pytest.mark.parametrize("mutation", ["caret", "instruction"])
def test_changed_selected_instruction_or_capability_refuses_before_writer(
    build_case, monkeypatch, tmp_path, mutation
):
    case, _ = ordinary_case(build_case, monkeypatch, authoring=True)
    decisions, writer = DecisionWire(operation="propose_build_insertion"), WriterWire()

    class ChangedHarness(BuildJevHarness):
        def _proposal(self, adapter, driver):
            if mutation == "caret":
                cap = adapter.request.build_write_capability
                adapter.request = adapter.request.model_copy(
                    update={
                        "build_write_capability": cap.model_copy(
                            update={
                                "basis": cap.basis.model_copy(
                                    update={"caret": cap.basis.caret + 1}
                                )
                            }
                        )
                    }
                )
            else:
                adapter.request = adapter.request.model_copy(
                    update={"message": "A different instruction"}
                )
            return super()._proposal(adapter, driver)

    from apps.live_control_server.services.agent_turn_service import (
        AgentTurnServiceError,
    )

    with pytest.raises(AgentTurnServiceError):
        execute(
            case,
            tmp_path,
            ChangedHarness(decision_transport=decisions, writer_transport=writer),
        )
    assert len(decisions.calls) == 1 and writer.calls == []


def test_approved_ordinary_proposal_saves_and_reopens_through_real_markdown_boundary(
    build_case, monkeypatch, tmp_path
):
    case, _ = ordinary_case(build_case, monkeypatch, authoring=True)
    decisions, writer = DecisionWire(operation="propose_build_insertion"), WriterWire()
    response = execute(
        case,
        tmp_path,
        BuildJevHarness(decision_transport=decisions, writer_transport=writer),
    )
    action = BuildProposalService().get(
        "elderwyld", response.knowledge_context.completion.action_id
    )
    source = case[0]
    assert action.proposal and not action.inserted_in_draft
    # Explicit operator insertion and Save are distinct from Agent preparation.
    from tests.test_worldbuilding_source_body_durability import _save_source
    from apps.live_control_server.services.workspace_document_registry import (
        get_workspace_document_snapshot,
    )

    draft = source.markdown + "\n\n" + action.proposal.replacement_markdown + "\n"
    saved = _save_source(tmp_path, source.record, draft)
    reopened = get_workspace_document_snapshot(tmp_path, saved.document_id)
    assert (
        reopened.markdown == draft and reopened.loaded_revision > source.loaded_revision
    )
    assert "| Nia | Baker |" in reopened.markdown
    assert len(writer.calls) == 1


def test_writer_keeps_frozen_dialogue_separate_from_source_evidence():
    from apps.live_control_server.services.build_jev_writer import (
        WriterProjection,
        with_dialogue,
    )

    pair = dict(
        turn_id=str(uuid4()),
        user="What about the gate?",
        assistant="Frank reported it haunted.",
    )
    for role in ("user", "assistant"):
        pair[f"{role}_sha256"] = sha256(pair[role].encode()).hexdigest()
    staged = WriterProjection('{"opened_passages":[]}', 4, str(uuid4()))
    result = with_dialogue(staged, [pair])
    packet = json.loads(result.input_json)
    assert packet["dialogue_reference"] == [pair]
    assert packet["opened_passages"] == []
    assert result.event_sequence == staged.event_sequence
    assert result.source_event_ids == staged.source_event_ids
    with pytest.raises(ValueError, match="digest"):
        with_dialogue(staged, [{**pair, "assistant": "Different text"}])


@pytest.mark.parametrize(
    "mutation", ["missing", "duplicate", "capability", "controller_envelope"]
)
def test_durable_execution_rejects_unbound_action_selection(
    build_case, monkeypatch, tmp_path, mutation
):
    from pydantic import ValidationError

    case, _ = ordinary_case(build_case, monkeypatch, authoring=True)
    execute(
        case,
        tmp_path,
        BuildJevHarness(
            decision_transport=DecisionWire(operation="propose_build_insertion"),
            writer_transport=WriterWire(),
        ),
    )
    service = AgentConversationService()
    turn = service.list_turns(
        "elderwyld", service.get_world_pointer("elderwyld").active_conversation_id
    )[0]
    execution = turn.graph_context_execution
    packet = execution.model_dump(mode="json", by_alias=True)
    type(execution).model_validate(packet)
    events = packet["events"]
    index = next(
        i
        for i, event in enumerate(events)
        if event["kind"] == "build_jev_action_selected_v1"
    )
    if mutation == "missing":
        events.pop(index)
    elif mutation == "duplicate":
        events.insert(index, {**events[index], "event_id": str(uuid4())})
    elif mutation == "capability":
        events[index]["capability_sha256"] = "0" * 64
    else:
        events[index]["controller_envelope_sha256"] = "0" * 64
    for sequence, event in enumerate(events):
        event["sequence"] = sequence
    with pytest.raises(
        ValidationError, match="Build (action selection|writer requires)"
    ):
        type(execution).model_validate(packet)


@pytest.mark.parametrize("recovery_state", ["live", "expired", "interrupted"])
def test_ordinary_retry_recovers_persisted_proposal_without_model_replay(
    build_case, monkeypatch, tmp_path, application_state_dsn, recovery_state
):
    case, _ = ordinary_case(build_case, monkeypatch, authoring=True)
    decisions, writer = DecisionWire(operation="propose_build_insertion"), WriterWire()
    runtime = BuildJevHarness(decision_transport=decisions, writer_transport=writer)
    original = AgentConversationService.complete_turn

    def simulated_crash(*args, **kwargs):
        raise SystemExit("synthetic crash after proposal persistence")

    monkeypatch.setattr(AgentConversationService, "complete_turn", simulated_crash)
    with pytest.raises(SystemExit):
        execute(case, tmp_path, runtime)
    monkeypatch.setattr(AgentConversationService, "complete_turn", original)
    service = AgentConversationService()
    before = service.list_turns(
        "elderwyld", service.get_world_pointer("elderwyld").active_conversation_id
    )[0]
    if recovery_state == "expired":
        import psycopg

        with psycopg.connect(application_state_dsn) as conn:
            conn.execute(
                "UPDATE agent.turn SET claim_expires_at=clock_timestamp()-interval '1 minute' WHERE turn_id=%s",
                (before.turn_id,),
            )
        from application_state.agent_conversation.build_authoring import (
            completion_for_proposal,
        )
        from application_state.errors import ApplicationStateConflictError

        action = BuildProposalService().get(
            "elderwyld", case[1].build_write_capability.idempotency_key
        )
        with pytest.raises(ApplicationStateConflictError, match="expired"):
            service.complete_turn(
                ledger.TurnResult(
                    world_id=before.world_id,
                    conversation_id=before.conversation_id,
                    turn_id=before.turn_id,
                    expected_revision=before.revision,
                    assistant_text=ledger.BUILD_PROPOSAL_READY_TEXT,
                    completion=completion_for_proposal(
                        action, before.graph_context_receipt
                    ),
                    producing_provider_attempt_id=action.authorization.provider_attempt_id,
                    claim_graph_event_ids={},
                )
            )
    elif recovery_state == "interrupted":
        service.fail_turn(
            ledger.TurnFailure(
                world_id=before.world_id,
                conversation_id=before.conversation_id,
                turn_id=before.turn_id,
                expected_revision=before.revision,
                failure_code="synthetic_transport_interrupt",
            ),
            interrupted=True,
        )
    response = execute(case, tmp_path, runtime)
    after = service.inspect_turn(world_id=before.world_id, turn_id=before.turn_id)
    assert after.attempt == before.attempt

    assert response.answer.text == ledger.BUILD_PROPOSAL_READY_TEXT
    assert response.knowledge_context.delivery_replay is True
    assert len(decisions.calls) == len(writer.calls) == 1


def test_ordinary_followup_writer_receives_exact_frozen_dialogue(
    build_case, monkeypatch, tmp_path
):
    case, _ = ordinary_case(build_case, monkeypatch)
    decisions, writer = DecisionWire(), WriterWire()
    runtime = BuildJevHarness(decision_transport=decisions, writer_transport=writer)
    first = execute(case, tmp_path, runtime)
    source, request, bootstrap = case
    followup = request.model_copy(
        update={"turn_id": str(uuid4()), "message": "What about that gate?"}
    )
    execute((source, followup, bootstrap), tmp_path, runtime)
    packet = json.loads(json.loads(writer.calls[-1].content)["input"])
    history = packet["dialogue_reference"]
    assert len(history) == 1
    assert history[0]["user"] == request.message
    assert history[0]["assistant"] == first.answer.text
    assert (
        history[0]["assistant_sha256"] == sha256(first.answer.text.encode()).hexdigest()
    )
    assert (
        packet["dialogue_policy"] == "conversation_reference_only_not_source_evidence"
    )


@pytest.mark.parametrize(
    "reason",
    [
        "invalid_decision_do_not_replay",
        "invalid_acquisition_do_not_replay",
        "retained_view_exceeds_context_policy",
    ],
)
def test_refused_after_actual_acquisition_never_calls_writer(
    build_case, monkeypatch, tmp_path, reason
):
    case, reads = ordinary_case(build_case, monkeypatch)
    decisions, writer = DecisionWire(), WriterWire()

    class RefusingHarness(BuildJevHarness):
        @staticmethod
        def _acquire(adapter, driver):
            BuildJevHarness._acquire(adapter, driver)
            driver._machine.refuse(reason)

    from apps.live_control_server.services.agent_turn_service import (
        AgentTurnServiceError,
    )

    with pytest.raises(AgentTurnServiceError):
        execute(
            case,
            tmp_path,
            RefusingHarness(decision_transport=decisions, writer_transport=writer),
        )
    assert reads == {"graph": 1, "source": 1}
    assert writer.calls == []


@pytest.mark.parametrize("status", ["insufficient_evidence", "unresolved_conflict"])
def test_terminal_gap_is_explicit_in_single_partial_writer(
    build_case, monkeypatch, tmp_path, status
):
    case, _ = ordinary_case(build_case, monkeypatch)
    decisions, writer = (
        DecisionWire(),
        WriterWire(answer_status="source_grounded_partial"),
    )

    class PartialHarness(BuildJevHarness):
        @staticmethod
        def _acquire(adapter, driver):
            BuildJevHarness._acquire(adapter, driver)
            driver._machine._step = driver._machine._finish(
                status, "support_missing_or_conflicting"
            )

    response = execute(
        case,
        tmp_path,
        PartialHarness(decision_transport=decisions, writer_transport=writer),
    )
    packet = json.loads(json.loads(writer.calls[0].content)["input"])
    assert packet["retrieval_disposition"]["status"] == status
    assert (
        response.knowledge_context.completion.answer_context_status
        == "source_grounded_partial"
    )
    assert len(writer.calls) == 1


def test_predispatch_veto_does_not_count_a_model_call(
    build_case, monkeypatch, tmp_path
):
    case, _ = ordinary_case(build_case, monkeypatch)
    decisions, writer = DecisionWire(), WriterWire()

    class VetoHarness(BuildJevHarness):
        async def _decide(self, adapter, driver):
            driver.authorize = lambda _: False
            return await super()._decide(adapter, driver)

    runtime = VetoHarness(decision_transport=decisions, writer_transport=writer)
    from apps.live_control_server.services.agent_turn_service import (
        AgentTurnServiceError,
    )

    with pytest.raises(AgentTurnServiceError):
        execute(case, tmp_path, runtime)
    assert decisions.calls == writer.calls == runtime.calls == []


def test_failed_structured_writer_keeps_reported_usage(
    build_case, monkeypatch, tmp_path
):
    case, _ = ordinary_case(build_case, monkeypatch, authoring=True)

    class BadOutput(WriterWire):
        async def handle_async_request(self, request):
            response = await super().handle_async_request(request)
            data = response.json()
            data["output"][0]["content"][0]["text"] = '{"invalid_proposal":true}'
            return httpx.Response(200, request=request, json=data)

    decisions, writer = DecisionWire(operation="propose_build_insertion"), BadOutput()
    runtime = BuildJevHarness(decision_transport=decisions, writer_transport=writer)
    from apps.live_control_server.services.agent_turn_service import (
        AgentTurnServiceError,
    )

    with pytest.raises(AgentTurnServiceError):
        execute(case, tmp_path, runtime)
    assert len(runtime.calls) == 2
    assert runtime.calls[-1]["status"] == "error"
    assert runtime.calls[-1]["usage"]["input_tokens"] == 100
    assert runtime.calls[-1]["usage"]["output_tokens"] == 40
    assert runtime.calls[-1]["usage"]["status"] == "reported"


def test_compact_first_sdk_keeps_nonempty_logical_membership_and_wire_hash(
    build_case, monkeypatch, tmp_path
):
    from graph_memory.interaction.authority_classifier import (
        claims_from_retrieval_result,
    )
    from graph_memory.interaction.session import (
        GraphRetrievalSession,
        CoverageState,
        SourceAnchorState,
    )
    from apps.live_control_server.services.build_initial_packet_codec import (
        decode,
        CODEC,
    )
    from apps.live_control_server.services.agent_turn_service import (
        _expected_initial_claim_packet,
    )

    source, request, bootstrap = ordinary_case(build_case, monkeypatch)[0]
    claims = claims_from_retrieval_result(
        {
            "relationships": [
                {
                    "edgeId": "rel:seed",
                    "sourceNodeId": "node:one",
                    "targetNodeId": "node:two",
                    "predicate": "guards",
                    "evidenceRefIds": ["ev:one"],
                }
            ],
            "sourceAnchors": [
                {
                    "anchorId": "anchor:one",
                    "revisionId": "native-rev-3",
                    "evidenceRefId": "ev:one",
                    "readable": True,
                    "supportingGraphObjectIds": [],
                }
            ],
        },
        revision_id="native-rev-3",
    )
    session = GraphRetrievalSession(
        snapshot=bootstrap.retrieval_session.snapshot,
        question=request.message,
        coverage=CoverageState(state="ready"),
        claims=claims,
        source_anchors=[SourceAnchorState(anchor_id="anchor:one", readable=True)],
    )
    bootstrap = replace(
        bootstrap,
        retrieval_session=session,
        candidate_relationship_ids=("rel:seed",),
        candidate_evidence_ref_ids=("ev:one",),
        evidence_by_anchor_id={"anchor:one": "ev:one"},
        source_scope_anchors=(
            {
                "anchor_id": "anchor:one",
                "evidence_ref_id": "ev:one",
                "source_artifact_id": "artifact:one",
                "source_revision_id": "source-rev:one",
            },
        ),
    )
    decisions, writer = DecisionWire(), WriterWire()
    captured = []

    class FirstOnly(BuildJevHarness):
        async def _decide(self, adapter, driver):
            await super()._decide(adapter, driver)
            captured.append(adapter.turn)
            raise SystemExit("prepared first call proof only")

    with pytest.raises(SystemExit):
        execute(
            (source, request, bootstrap),
            tmp_path,
            FirstOnly(decision_transport=decisions, writer_transport=writer),
        )
    (turn,) = captured
    assert isinstance(
        turn.graph_context_execution.policy,
        ledger.BuildCompactActionControllerWriterPolicyV1,
    )
    assert turn.graph_context_execution.policy.initial_packet_codec == CODEC
    auth = turn.graph_context_execution.events[0]
    assert auth.included_relationship_ids == ["rel:seed"]
    assert auth.included_evidence_ref_ids == ["ev:one"]
    assert auth.envelope_sha256 == sha256(decisions.calls[0].content).hexdigest()
    assert (
        turn.graph_context_receipt.assembled_input.assembled_input_sha256
        == auth.envelope_sha256
    )
    state = json.loads(decisions.calls[0].content)["state"]
    assert decode(state["initialClaimPacket"]) == _expected_initial_claim_packet(
        bootstrap
    )
    assert writer.calls == []


@pytest.mark.parametrize("mutation", ["boolean_to_integer", "integer_to_float"])
def test_compact_sdk_type_substitution_never_dispatches(
    build_case, monkeypatch, tmp_path, mutation
):
    from apps.live_control_server.services.build_jev_driver import BuildJevDriver
    from apps.live_control_server.services.agent_turn_service import AgentTurnServiceError

    original = BuildJevDriver.authorize
    checked = []

    def authorize(driver, prepared):
        body = json.loads(prepared.body)
        assert body["state"]["schema"] == "dmb_build_jev_driver_decision_v2"
        if mutation == "boolean_to_integer":
            from apps.live_control_server.services.build_initial_packet_codec import decode, encode
            packet = decode(body["state"]["initialClaimPacket"])
            assert packet["candidates"][0]["selected"] is False
            packet["candidates"][0]["selected"] = 0
            body["state"]["initialClaimPacket"] = encode(packet)
        else:
            value = body["state"]["source_basis"]["registry_revision"]
            assert type(value) is int
            body["state"]["source_basis"]["registry_revision"] = float(value)
        wire = json.dumps(body).encode()
        changed = replace(prepared, body=wire, body_size=len(wire),
                          body_sha256=sha256(wire).hexdigest())
        # Same Python equality, different JSON types: the exact wire gate must refuse.
        assert json.loads(prepared.body) == body
        accepted = original(driver, changed)
        checked.append(accepted)
        return accepted

    monkeypatch.setattr(BuildJevDriver, "authorize", authorize)
    decisions, writer = DecisionWire(), WriterWire()
    harness = BuildJevHarness(decision_transport=decisions, writer_transport=writer)
    case, _ = ordinary_case(build_case, monkeypatch)
    # Synthetic native projection includes a real JSON boolean in navigation metadata.
    from copy import deepcopy
    session = case[2].retrieval_session
    projection = session.project_for_hermes()
    projection["candidates"] = [{"node_id": "frank", "selected": False}]
    monkeypatch.setattr(type(session), "project_for_hermes", lambda self: deepcopy(projection))
    with pytest.raises(AgentTurnServiceError):
        execute(case, tmp_path, harness)
    assert checked == [False]
    assert decisions.calls == writer.calls == []
    assert harness.adapter.fence is None
    assert harness.adapter.turn is None


def test_writer_cannot_claim_full_support_when_frontier_is_heuristic(
    build_case, monkeypatch, tmp_path
):
    from apps.live_control_server.services.agent_turn_service import AgentTurnServiceError
    case, _ = ordinary_case(build_case, monkeypatch)
    decisions, writer = DecisionWire(), WriterWire(answer_status="source_grounded")
    with pytest.raises(AgentTurnServiceError) as rejected:
        execute(case, tmp_path, BuildJevHarness(decision_transport=decisions, writer_transport=writer))
    assert "unresolved retrieval" in str(rejected.value.__cause__)
    assert len(writer.calls) == 1  # consumed; never rewrite/retry the writer


def test_ordinary_deferred_actions_stay_unread_and_citations_survive_reopen(
    build_case, monkeypatch, tmp_path
):
    class DeferredWire(DecisionWire):
        async def handle_async_request(self, request):
            response = await super().handle_async_request(request)
            value = response.json()
            for key, answer in value["answers"].items():
                if key.startswith("use_"):
                    answer["probabilities"] = {"not_useful": .6, "useful": .1, "unknown": .3}
            return httpx2.Response(200, request=request, json=value)
    case, calls = ordinary_case(build_case, monkeypatch)
    decisions, writer = DeferredWire(), WriterWire()
    response = execute(case, tmp_path, BuildJevHarness(decision_transport=decisions, writer_transport=writer))
    assert response.answer.text == "Frank believes the western gate is haunted."
    assert calls == {"graph": 1, "source": 1} and len(writer.calls) == 1
    packet = json.loads(json.loads(writer.calls[0].content)["input"])
    frontier = packet["retrieval_disposition"]
    assert frontier["coverage_status"] == "heuristic_partial"
    assert frontier["deferred_unread_ids"] and frontier["excluded_unread_count"] == 0
    assert "probabilities" not in json.dumps(frontier)
    service = AgentConversationService()
    turn = service.list_turns("elderwyld", service.get_world_pointer("elderwyld").active_conversation_id)[0]
    assert turn.status == "completed" and len(turn.completion.source_citations) == 1
    policy = turn.graph_context_execution.policy
    assert type(policy) is ledger.BuildContainedActionControllerWriterPolicyV1
    # Reading historical policy bytes must not introduce new frontier fields.
    old = policy.model_dump(mode="json", by_alias=True)
    old.pop("evidence_codec")
    phase = ledger.BuildPhaseActionControllerWriterPolicyV1.model_validate(old)
    assert "evidence_codec" not in phase.model_dump()
    old.pop("phase_input_policy")
    frontier = ledger.BuildFrontierActionControllerWriterPolicyV1.model_validate(old)
    assert "phase_input_policy" not in frontier.model_dump()
    old.pop("frontier_policy")
    historical = ledger.BuildContinuationActionControllerWriterPolicyV1.model_validate(old)
    assert historical.model_dump(mode="json", by_alias=True) == old
    from pydantic import TypeAdapter
    restored = TypeAdapter(ledger.BuildFrontierActionControllerWriterPolicyV1 | ledger.BuildContinuationActionControllerWriterPolicyV1).validate_python(old)
    assert type(restored) is ledger.BuildContinuationActionControllerWriterPolicyV1
    assert "frontier_policy" not in restored.model_dump()
