"""Real APP and SDK boundary: a relevance vote cannot erase acquired primary work."""

import json
from copy import deepcopy
from uuid import uuid4

import httpx
import httpx2
import pytest

from application_state.agent_conversation import AgentConversationService, types as t
from application_state.agent_conversation import build_primary_context as primary
from application_state.agent_conversation.source_writer_output import (
    reconstruct,
    finite_output_schema,
)
from tests.test_build_jev_estimated_continuations import counter
from tests.test_build_writer_selection import SelectionWire, SavedWriter
from tests.test_agent_build_jev_ordinary_harness import (
    ordinary_case,
    build_case as _build_case,
)
from tests.test_agent_build_governed_graph import execute
from apps.live_control_server.services.build_jev_harness import BuildJevHarness


@pytest.fixture
def build_case(tmp_path, monkeypatch, application_state_dsn):
    return _build_case.__wrapped__(tmp_path, monkeypatch, application_state_dsn)


class Decisions(SelectionWire):
    def __init__(self):
        super().__init__("saved_only")

    async def handle_async_request(self, request):
        response = await super().handle_async_request(request)
        body = json.loads(request.content)
        data = response.json()
        if body["state"].get("writer_selection_policy"):
            for value in data["answers"].values():
                value.update(
                    choice="irrelevant",
                    confidence=0.25,
                    probabilities={
                        "direct_support": 0.34,
                        "qualification_or_conflict": 0.04,
                        "uncertain": 0.18,
                        "irrelevant": 0.44,
                    },
                )
        return httpx2.Response(200, request=request, json=data)


class AuthoredWriter(SavedWriter):
    async def handle_async_request(self, request):
        response = await super().handle_async_request(request)
        self.output = response.json()["output"][0]["content"][0]["text"]
        return response


@pytest.fixture
def completed(build_case, monkeypatch, tmp_path):
    case, reads = ordinary_case(build_case, monkeypatch)
    decisions, writer = Decisions(), AuthoredWriter()
    harness = BuildJevHarness(
        decision_transport=decisions, writer_transport=writer, accounting=counter()
    )
    result = execute(case, tmp_path, harness)
    service = AgentConversationService()
    (turn,) = service.list_turns(
        "elderwyld", service.get_world_pointer("elderwyld").active_conversation_id
    )
    packet = json.loads(json.loads(writer.calls[0].content)["input"])
    return turn, packet, writer, decisions, reads, result


def test_primary_work_survives_actual_irrelevant_vote_without_rewriting_closure(
    completed,
):
    turn, packet, writer, decisions, reads, result = completed
    execution = turn.graph_context_execution
    assert isinstance(execution.policy, t.BuildPrimaryWorkPolicyV1)
    settled = primary.selection(execution)
    assert set(settled.judgments.values()) == {"irrelevant"}
    assert (
        settled.section_read_ids
        == settled.expanded_unit_ids
        == settled.requested_unit_ids
        == []
    )
    assert len(settled.omitted_unit_ids) == 1
    assert packet["exposure"]["saved_sections"] == []
    lane = packet["artifact_under_edit"]
    assert lane == primary.project(execution, turn.graph_context_receipt.source_basis)
    assert len(lane["sections"]) == 1
    assert reads == {"graph": 0, "source": 0}
    assert len(writer.calls) == 1
    (writer_auth,) = [
        e
        for e in execution.events
        if isinstance(e, t.ProviderAttemptAuthorizedEventV3) and e.provider == "openai"
    ]
    (inclusion,) = [
        e
        for e in execution.events
        if isinstance(e, t.BuildSectionProviderInclusionV1)
        and e.provider_attempt_id == writer_auth.provider_attempt_id
    ]
    assert set(inclusion.section_event_ids) == {
        e.event_id for e in primary.records(execution)
    }
    assert any(isinstance(e, t.BuildSectionAnswerBindingV1) for e in execution.events)
    assert all(
        s.kind in {"saved_source_claim", "connective"}
        for s in turn.completion.answer_segments
    )
    assert turn.completion.answer_basis == "saved_source"
    # Persisted/reloaded strict execution keeps the explicit new capability.
    assert (
        t.PlanWorldGraphExecutionV3.model_validate(
            execution.model_dump(mode="json", by_alias=True)
        )
        == execution
    )
    selection_request = next(
        json.loads(r.content)
        for r in decisions.calls
        if json.loads(r.content)["state"].get("writer_selection_policy")
    )
    assert len(selection_request["state"]["sources"]) == 1
    assert "authored" in primary.ROLE


@pytest.mark.parametrize(
    "fault",
    [
        "missing",
        "text",
        "unread",
        "duplicate",
        "basis",
        "role",
        "duplicate_lane",
        "graph_claim",
    ],
)
def test_independent_completion_owner_refuses_changed_primary_work(completed, fault):
    turn, original, writer, _, _, _ = completed
    packet = deepcopy(original)
    output = json.loads(writer.output)
    if fault == "missing":
        del packet["artifact_under_edit"]
    elif fault == "text":
        packet["artifact_under_edit"]["sections"][0]["text"] = (
            "Unsent draft or unrelated source."
        )
    elif fault == "unread":
        packet["artifact_under_edit"]["sections"][0]["read_id"] = str(uuid4())
    elif fault == "duplicate":
        packet["artifact_under_edit"]["sections"] *= 2
    elif fault == "basis":
        packet["source_basis"]["registry_revision"] += 1
    elif fault == "role":
        packet["artifact_under_edit"]["role"] = "accepted_world_truth"
    elif fault == "duplicate_lane":
        packet["exposure"]["saved_sections"] = [
            e.model_dump(mode="json")
            for e in primary.records(turn.graph_context_execution)
        ]
    elif fault == "graph_claim":
        output["answer_segments"][0]["kind"] = "graph_claim"
    (auth,) = [
        e
        for e in turn.graph_context_execution.events
        if isinstance(e, t.ProviderAttemptAuthorizedEventV3) and e.provider == "openai"
    ]
    with pytest.raises(ValueError):
        reconstruct(json.dumps(output), packet, turn, auth)


def test_finite_schema_exposes_only_actual_primary_selectors(completed):
    turn, packet, _, _, _, _ = completed
    schema = finite_output_schema(packet, requested_detail_gaps=True)
    assert schema["$defs"]["SavedFact"]["properties"]["section_read_ids"]["items"][
        "enum"
    ] == [packet["artifact_under_edit"]["sections"][0]["read_id"]]
    old_policy = t.BuildEncodedAssessmentPolicyV1.model_validate(
        turn.graph_context_execution.policy.model_dump(
            by_alias=True,
            exclude={"primary_work_context_policy", "writer_status_policy"},
        )
    )
    historical = turn.graph_context_execution.model_copy(update={"policy": old_policy})
    historical_packet = deepcopy(packet)
    historical_packet.pop("writer_status_policy", None)
    with pytest.raises(ValueError, match="Historical policy"):
        primary.validate_packet(
            historical_packet, historical, turn.graph_context_receipt.source_basis
        )


def test_primary_context_rejects_foreign_basis_and_excludes_late_reads(completed):
    turn, packet, _, _, _, _ = completed
    execution = turn.graph_context_execution
    (original,) = primary.records(execution)
    foreign = original.model_copy(
        update={
            "source_basis": original.source_basis.model_copy(
                update={
                    "registry_revision": original.source_basis.registry_revision + 1
                }
            )
        }
    )
    changed = execution.model_copy(
        update={
            "events": [
                foreign if e.event_id == original.event_id else e
                for e in execution.events
            ]
        }
    )
    with pytest.raises(ValueError, match="another saved basis"):
        primary.project(changed, turn.graph_context_receipt.source_basis)
    late = original.model_copy(
        update={
            "event_id": uuid4(),
            "read_id": uuid4(),
            "sequence": len(execution.events),
        }
    )
    extended = execution.model_copy(update={"events": [*execution.events, late]})
    assert (
        primary.project(extended, turn.graph_context_receipt.source_basis)
        == packet["artifact_under_edit"]
    )
    assert late.read_id not in primary.writer_read_ids(extended)


@pytest.mark.parametrize("mutation", ["numeric_type", "uuid_encoding"])
def test_historical_saved_sections_keep_exact_serialized_types(completed, mutation):
    turn, packet, _, _, _, _ = completed
    old_policy = t.BuildEncodedAssessmentPolicyV1.model_validate(
        turn.graph_context_execution.policy.model_dump(
            by_alias=True,
            exclude={"primary_work_context_policy", "writer_status_policy"},
        )
    )
    historical = turn.graph_context_execution.model_copy(update={"policy": old_policy})
    old_packet = deepcopy(packet)
    old_packet.pop("writer_status_policy", None)
    old_packet["schema"] = "dmb_build_source_passage_writer_v1"
    del old_packet["artifact_under_edit"]
    old_packet["exposure"]["saved_sections"] = [
        e.model_dump(mode="json", by_alias=True)
        for e in primary.records(turn.graph_context_execution)
    ]
    assert primary.validate_packet(
        old_packet, historical, turn.graph_context_receipt.source_basis
    )
    row = old_packet["exposure"]["saved_sections"][0]
    if mutation == "numeric_type":
        row["line_start"] = str(row["line_start"])
    else:
        row["event_id"] = row["event_id"].upper()
    with pytest.raises(ValueError):
        primary.validate_packet(
            old_packet, historical, turn.graph_context_receipt.source_basis
        )


@pytest.mark.parametrize(
    "status,coverage,partial",
    [
        ("insufficient_evidence", "catalog_exhausted", True),
        ("unresolved_conflict", "catalog_exhausted", True),
        ("provisionally_supported", "heuristic_partial", True),
        ("provisionally_supported", "catalog_exhausted", False),
    ],
)
def test_status_schema_matches_existing_host_admission(
    completed, status, coverage, partial
):
    turn, packet, _, _, _, _ = completed
    assert isinstance(
        turn.graph_context_execution.policy, t.BuildPrimaryWorkStatusPolicyV1
    )
    current = deepcopy(packet)
    current["retrieval_disposition"].update(status=status, coverage_status=coverage)
    schema = finite_output_schema(current, requested_detail_gaps=True)
    allowed = schema["properties"]["answer_context_status"]["enum"]
    assert ("source_grounded" not in allowed) == partial
    historical = deepcopy(current)
    del historical["writer_status_policy"]
    assert (
        "source_grounded"
        in finite_output_schema(historical, requested_detail_gaps=True)["properties"][
            "answer_context_status"
        ]["enum"]
    )
    del current["writer_status_policy"]
    with pytest.raises(ValueError, match="status capability"):
        primary.validate_packet(
            current,
            turn.graph_context_execution,
            turn.graph_context_receipt.source_basis,
        )


class FullSupportWriter(AuthoredWriter):
    async def handle_async_request(self, request):
        response = await super().handle_async_request(request)
        body = response.json()
        output = json.loads(body["output"][0]["content"][0]["text"])
        output.update(answer_context_status="source_grounded", limitations=[])
        self.output = body["output"][0]["content"][0]["text"] = json.dumps(output)
        return httpx.Response(200, request=request, json=body)


@pytest.mark.parametrize("capture_failure", [False, True])
def test_refused_full_support_is_captured_before_terminal_check(
    build_case, monkeypatch, tmp_path, capture_failure
):
    case, _ = ordinary_case(build_case, monkeypatch)
    writer = FullSupportWriter()
    harness = BuildJevHarness(
        decision_transport=Decisions(), writer_transport=writer, accounting=counter()
    )
    from apps.live_control_server.services.agent_turn_service import (
        AgentTurnServiceError,
    )

    if capture_failure:
        from apps.live_control_server.services.agent_context_trace_collector import (
            ContextTraceCollector,
        )

        def fail_capture(*args, **kwargs):
            raise RuntimeError("synthetic Debug capture failure")

        monkeypatch.setattr(ContextTraceCollector, "answer_draft", fail_capture)
    with pytest.raises(AgentTurnServiceError) as failure:
        execute(case, tmp_path, harness)
    assert "full support" in str(failure.value.__cause__)
    service = AgentConversationService()
    (turn,) = service.list_turns(
        "elderwyld", service.get_world_pointer("elderwyld").active_conversation_id
    )
    traces = service.list_context_trace_attempts(
        world_id="elderwyld", turn_id=turn.turn_id
    )
    materials = [
        m
        for tr in traces
        for o in tr.observations
        if o.kind == "context_snapshot"
        for m in o.materials
    ]
    assert sum(m.text == writer.output for m in materials) == (
        0 if capture_failure else 1
    )
    if capture_failure:
        assert "synthetic Debug capture failure" in str(
            failure.value.__cause__.__cause__
        )
    assert any(
        o.kind == "failure" and o.code == "build_writer_strengthened_partial_retrieval"
        for tr in traces
        for o in tr.observations
    )
    assert turn.completion is None and len(writer.calls) == 1
