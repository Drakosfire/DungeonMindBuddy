"""Cited writer producer contract, including the real SDK→APP completion seam."""

import json
from copy import deepcopy

import psycopg

import pytest

from application_state.agent_conversation import AgentConversationService
from application_state.agent_conversation import types as t
from application_state.agent_conversation.source_writer_output import (
    CitedSourceAnswer,
    LIMITATIONS,
    POLICY,
    normalize,
    output_schema,
    validate_completion_proof,
)
from application_state.errors import ApplicationStateValidationError
from apps.live_control_server.services.build_jev_harness import BuildJevHarness
from tests.test_agent_build_jev_ordinary_harness import (
    DecisionWire,
    WriterWire,
    ordinary_case,
    build_case as _build_case,
)
from tests.test_agent_build_governed_graph import execute
from tests.test_build_jev_estimated_continuations import counter


@pytest.fixture
def build_case(tmp_path, monkeypatch, application_state_dsn):
    return _build_case.__wrapped__(tmp_path, monkeypatch, application_state_dsn)


def packet(status="provisionally_supported", coverage="heuristic_partial"):
    return {"retrieval_disposition": {"status": status, "coverage_status": coverage}}


def answer():
    return {
        "answer_context_status": "source_grounded_partial",
        "answer_segments": [
            {
                "kind": "source_passage_claim",
                "text": "The toll is steep.",
                "passage_handles": ["p1"],
            }
        ],
        "limitations": ["partial_retrieval"],
    }


def test_partial_facts_keep_selectors_and_host_only_limitations():
    value = answer()
    value["answer_segments"].extend(
        [
            {
                "kind": "saved_source_claim",
                "text": "An authored idea.",
                "section_read_ids": ["s1"],
            },
            {"kind": "suggestion", "text": "You could lower it."},
        ]
    )
    result = normalize(json.dumps(value), packet())
    assert result["answer_segments"][:2] == value["answer_segments"][:2]
    assert result["answer_segments"][2] == {
        "kind": "connective",
        "text": "Suggestion: You could lower it.",
    }
    assert result["answer_segments"][3] == {
        "kind": "connective",
        "text": LIMITATIONS["partial_retrieval"],
    }
    assert value["answer_segments"][1]["section_read_ids"] == ["s1"]


def test_original_toll_uncited_connective_is_rejected():
    old = {
        "answer_context_status": "source_insufficient_evidence",
        "answer_segments": [
            {
                "kind": "connective",
                "text": "The toll is steep and visitors are unhappy.",
            }
        ],
    }
    with pytest.raises(ValueError):
        normalize(json.dumps(old), packet("insufficient_evidence"))


@pytest.mark.parametrize(
    "mutation",
    [
        lambda a: a.pop("limitations"),
        lambda a: a.update(limitations=["unknown"]),
        lambda a: a.update(limitations=["partial_retrieval", "partial_retrieval"]),
        lambda a: a.update(limitations=[]),
        lambda a: a.update(answer_context_status="source_grounded"),
        lambda a: a.update(answer_context_status="source_insufficient_evidence"),
        lambda a: a["answer_segments"][0].update(passage_handles=[]),
        lambda a: a["answer_segments"][0].update(passage_handles=["p1", "p1"]),
        lambda a: a["answer_segments"][0].update(text=" "),
        lambda a: a["answer_segments"][0].update(kind="connective"),
        lambda a: a.update(
            answer_segments=[{"kind": "suggestion", "text": "", "fact": True}]
        ),
    ],
)
def test_closed_output_rejects_missing_forged_and_inconsistent_fields(mutation):
    value = answer()
    mutation(value)
    with pytest.raises(ValueError):
        normalize(json.dumps(value), packet())


@pytest.mark.parametrize(
    "status,code",
    [
        ("insufficient_evidence", "missing_requested_details"),
        ("unresolved_conflict", "unresolved_conflict"),
    ],
)
def test_host_only_abstention_and_partial_answers(status, code):
    value = {
        "answer_context_status": "source_insufficient_evidence",
        "answer_segments": [],
        "limitations": ["partial_retrieval", code],
    }
    result = normalize(json.dumps(value), packet(status))
    assert result["answer_segments"]
    assert all(s["text"] in LIMITATIONS.values() for s in result["answer_segments"])
    value["limitations"].remove(code)
    with pytest.raises(ValueError, match="host retrieval limitation"):
        normalize(json.dumps(value), packet(status))


def test_duplicate_json_and_missing_disposition_reject():
    with pytest.raises(ValueError, match="Duplicate"):
        normalize('{"answer_segments":[],"answer_segments":[]}', packet())
    with pytest.raises(ValueError, match="disposition"):
        normalize(json.dumps(answer()), {})


def test_schema_and_historical_fields():
    schema = output_schema()
    assert schema["additionalProperties"] is False
    assert set(schema["required"]) == {
        "answer_context_status",
        "answer_segments",
        "limitations",
    }
    assert "connective" not in json.dumps(schema)
    assert CitedSourceAnswer.model_fields["limitations"].is_required()
    assert (
        "source_writer_output_policy"
        not in t.BuildReadBatchActionControllerWriterPolicyV1.model_fields
    )
    assert "writer_request_json" not in t.TurnResult.model_fields
    assert set(t.BuildGraphCompletionV2.model_fields) == {
        "schema_",
        "context_receipt_sha256",
        "answer_basis",
        "answer_context_status",
        "answer_segments",
        "citation_map",
        "source_citations",
    }


def test_real_writer_completion_proof_blocks_forgery_then_completes_and_reopens(
    build_case, monkeypatch, tmp_path, application_state_dsn
):
    case, _ = ordinary_case(build_case, monkeypatch)
    original = AgentConversationService.complete_turn
    attempted = []

    def guarded(service, result):
        assert isinstance(result, t.CitedSourceTurnResult)
        producing_turn = service.list_turns(result.world_id, result.conversation_id)[0]
        with psycopg.connect(application_state_dsn) as conn:
            trace = conn.execute(
                "SELECT payload FROM agent.turn_context_trace WHERE turn_id=%s AND attempt=%s",
                (result.turn_id, producing_turn.attempt),
            ).fetchone()[0]
        validate_completion_proof(result, producing_turn, trace)
        for field, value in [
            ("capture_status", "incomplete"),
            ("turn_id", "foreign"),
            ("attempt", 999),
        ]:
            changed_trace = deepcopy(trace)
            changed_trace[field] = value
            with pytest.raises(ValueError, match="capture"):
                validate_completion_proof(result, producing_turn, changed_trace)
        changed_trace = deepcopy(trace)
        draft = next(
            o
            for o in changed_trace["observations"]
            if o["kind"] == "context_snapshot"
            and any(
                m["item_id"].startswith("unvalidated-provider-answer:")
                for m in o["materials"]
            )
        )
        draft["materials"].extend(deepcopy(draft["materials"]))
        with pytest.raises(ValueError, match="captured producer bytes"):
            validate_completion_proof(result, producing_turn, changed_trace)
        # Independent review reproduced this exact legacy-type bypass on real APP.
        legacy = t.BuildGraphCompletionV1(
            context_receipt_sha256=result.completion.context_receipt_sha256,
            answer_basis="saved_source",
            answer_context_status="source_only_insufficient_evidence",
            answer_segments=[{"kind": "connective", "text": "UNVALIDATED LEGACY FACT"}],
            citation_map=None,
        )
        legacy_plain = t.TurnResult(
            world_id=result.world_id,
            conversation_id=result.conversation_id,
            turn_id=result.turn_id,
            expected_revision=result.expected_revision,
            assistant_text="UNVALIDATED LEGACY FACT",
            completion=legacy,
            producing_provider_attempt_id=result.producing_provider_attempt_id,
            claim_graph_event_ids={},
        )
        with pytest.raises(
            ApplicationStateValidationError, match="producer output proof"
        ):
            original(service, legacy_plain)
        with pytest.raises(ApplicationStateValidationError, match="normalization"):
            original(
                service,
                result.model_copy(
                    update={
                        "completion": legacy,
                        "assistant_text": "UNVALIDATED LEGACY FACT",
                    }
                ),
            )
        # Each invalid completion reaches the actual APP transaction and is refused.
        for changed in [
            t.TurnResult.model_validate(
                result.model_dump(
                    by_alias=True,
                    exclude={"writer_request_json", "raw_provider_output_json"},
                )
            ),
            result.model_copy(
                update={
                    "raw_provider_output_json": result.raw_provider_output_json + " "
                }
            ),
            result.model_copy(
                update={"writer_request_json": result.writer_request_json + " "}
            ),
        ]:
            with pytest.raises(ApplicationStateValidationError):
                original(service, changed)
            attempted.append("rejected")
        forged = result.completion.model_copy(deep=True)
        forged.answer_segments[-1].text = "An uncited factual assertion."
        forged_result = result.model_copy(
            update={
                "completion": forged,
                "assistant_text": "\n".join(s.text for s in forged.answer_segments),
            }
        )
        with pytest.raises(ApplicationStateValidationError, match="normalization"):
            original(service, forged_result)
        attempted.append("rejected")
        assert (
            service.list_turns(result.world_id, result.conversation_id)[0].revision
            == producing_turn.revision
        )
        return original(service, result)

    monkeypatch.setattr(AgentConversationService, "complete_turn", guarded)
    wire = WriterWire()
    response = execute(
        case,
        tmp_path,
        BuildJevHarness(
            decision_transport=DecisionWire(),
            writer_transport=wire,
            accounting=counter(),
        ),
    )
    assert len(wire.calls) == 1 and len(attempted) == 4
    assert "Frank believes" in response.answer.text
    service = AgentConversationService()
    turn = service.list_turns(
        "elderwyld", service.get_world_pointer("elderwyld").active_conversation_id
    )[0]
    assert turn.status == "completed"
    assert turn.graph_context_execution.policy.source_writer_output_policy == POLICY
    assert (
        turn.completion.source_citations
        and turn.completion.answer_segments[-1].text == LIMITATIONS["partial_retrieval"]
    )
    assert (
        t.BuildGraphCompletionV2.model_validate(
            turn.completion.model_dump(mode="json", by_alias=True)
        )
        == turn.completion
    )


class SavedThenGraphWire(DecisionWire):
    async def handle_async_request(self, request):
        response = await super().handle_async_request(request)
        body, value = json.loads(request.content), response.json()
        state = body["state"]["decision"]["state"]
        acquired = state.get("evidence", [])
        for key, q in body["questions"].items():
            if key == "joint_support" and len(acquired) < 2:
                value["answers"][key]["noul"] = 0.01
            elif key == "sufficiency" and len(acquired) < 2:
                selected = "more_evidence"
                value["answers"][key].update(
                    choice=selected,
                    probabilities={x: float(x == selected) for x in q["criteria"]},
                )
            elif key == "next":
                selected = next(
                    (x for x in q["criteria"] if x.startswith("saved:")),
                    next((x for x in q["criteria"] if x.startswith("graph:")), "none"),
                )
                value["answers"][key].update(
                    choice=selected,
                    probabilities={x: float(x == selected) for x in q["criteria"]},
                )
        import httpx2

        return httpx2.Response(200, request=request, json=value)


class OutputWire(WriterWire):
    def __init__(self, variant):
        super().__init__()
        self.variant = variant

    async def handle_async_request(self, request):
        response = await super().handle_async_request(request)
        value = response.json()
        output = value["output"][0]["content"][0]
        answer = json.loads(output["text"])
        if self.variant in {"saved", "saved_only"}:
            packet = json.loads(json.loads(request.content)["input"])
            section = packet["exposure"]["saved_sections"][0]
            if self.variant == "saved_only":
                answer["answer_segments"] = []
                answer["answer_context_status"] = "source_grounded_partial"
            answer["answer_segments"].append(
                {
                    "kind": "saved_source_claim",
                    "text": "An authored note.",
                    "section_read_ids": [section["read_id"]],
                }
            )
        elif self.variant == "abstention":
            answer.update(
                answer_context_status="source_insufficient_evidence",
                answer_segments=[],
                limitations=["missing_requested_details", "partial_retrieval"],
            )
        elif self.variant == "unknown_handle":
            answer["answer_segments"][0]["passage_handles"] = ["foreign"]
        elif self.variant == "suggestion":
            answer["answer_segments"].append(
                {"kind": "suggestion", "text": "You could ask Frank."}
            )
        output["text"] = json.dumps(answer)
        import httpx

        return httpx.Response(200, request=request, json=value)


@pytest.mark.parametrize(
    "variant", ["abstention", "suggestion", "saved", "unknown_handle"]
)
def test_ordinary_output_variants_keep_single_writer_and_saved_indexes(
    build_case, monkeypatch, tmp_path, variant
):
    case, _ = ordinary_case(build_case, monkeypatch)
    wire = OutputWire(variant)
    harness = BuildJevHarness(
        decision_transport=SavedThenGraphWire()
        if variant == "saved"
        else DecisionWire(),
        writer_transport=wire,
        accounting=counter(),
    )
    if variant == "unknown_handle":
        with pytest.raises(Exception, match="could not complete safely"):
            execute(case, tmp_path, harness)
        assert len(wire.calls) == 1
        return
    response = execute(case, tmp_path, harness)
    assert len(wire.calls) == 1
    service = AgentConversationService()
    turn = service.list_turns(
        "elderwyld", service.get_world_pointer("elderwyld").active_conversation_id
    )[0]
    assert turn.status == "completed" and turn.assistant_text == response.answer.text
    if variant == "abstention":
        assert turn.completion.source_citations == []
        assert all(
            s.text in LIMITATIONS.values() for s in turn.completion.answer_segments
        )
    elif variant == "suggestion":
        assert (
            turn.completion.answer_segments[1].text
            == "Suggestion: You could ask Frank."
        )
        assert {c.segment_index for c in turn.completion.source_citations} == {0}
    else:
        assert turn.completion.answer_segments[1].kind == "saved_source_claim"
        bindings = [
            b
            for e in turn.graph_context_execution.events
            if isinstance(e, t.BuildSectionAnswerBindingV1)
            for b in e.bindings
        ]
        assert len(bindings) == 1 and bindings[0].segment_index == 1


class SavedOnlyDecisionWire(DecisionWire):
    def __init__(self, *, empty=False):
        super().__init__()
        self.empty = empty

    async def handle_async_request(self, request):
        response = await super().handle_async_request(request)
        body, value = json.loads(request.content), response.json()
        for key, q in body["questions"].items():
            if key == "next":
                selected = (
                    "none"
                    if self.empty
                    else next(
                        (x for x in q["criteria"] if x.startswith("saved:")), "none"
                    )
                )
                value["answers"][key].update(
                    choice=selected,
                    probabilities={x: float(x == selected) for x in q["criteria"]},
                )
        import httpx2

        return httpx2.Response(200, request=request, json=value)


@pytest.mark.parametrize("empty", [False, True])
def test_saved_only_and_empty_evidence_use_mandatory_proof_and_reopen(
    build_case, monkeypatch, tmp_path, empty
):
    case, reads = ordinary_case(build_case, monkeypatch)
    original = AgentConversationService.complete_turn
    seen = []

    def guarded(service, result):
        assert isinstance(result, t.CitedSourceTurnResult)
        assert isinstance(result.completion, t.BuildGraphCompletionV1)
        packet = json.loads(json.loads(result.writer_request_json)["input"])
        assert packet["opened_passages"] == []
        plain = t.TurnResult.model_validate(
            result.model_dump(
                by_alias=True,
                exclude={"writer_request_json", "raw_provider_output_json"},
            )
        )
        with pytest.raises(
            ApplicationStateValidationError, match="producer output proof"
        ):
            original(service, plain)
        forged = result.completion.model_copy(deep=True)
        forged.answer_segments[0].text = "Uncaptured saved fact"
        with pytest.raises(ApplicationStateValidationError, match="normalization"):
            original(
                service,
                result.model_copy(
                    update={
                        "completion": forged,
                        "assistant_text": "\n".join(
                            s.text for s in forged.answer_segments
                        ),
                    }
                ),
            )
        if not empty:
            assert result.build_section_bindings
            with pytest.raises(ApplicationStateValidationError, match="normalization"):
                original(
                    service, result.model_copy(update={"build_section_bindings": []})
                )
        seen.append(result)
        return original(service, result)

    monkeypatch.setattr(AgentConversationService, "complete_turn", guarded)
    wire = OutputWire("abstention" if empty else "saved_only")
    response = execute(
        case,
        tmp_path,
        BuildJevHarness(
            decision_transport=SavedOnlyDecisionWire(empty=empty),
            writer_transport=wire,
            accounting=counter(),
        ),
    )
    assert (
        len(wire.calls) == 1 and len(seen) == 1 and reads == {"graph": 0, "source": 0}
    )
    service = AgentConversationService()
    turn = service.list_turns(
        "elderwyld", service.get_world_pointer("elderwyld").active_conversation_id
    )[0]
    assert turn.status == "completed" and turn.assistant_text == response.answer.text
    assert turn.completion.citation_map is None
    assert not any(
        isinstance(s, t.PlanWorldGraphClaimSegmentV1)
        for s in turn.completion.answer_segments
    )
    if empty:
        assert all(
            s.text in LIMITATIONS.values() for s in turn.completion.answer_segments
        )
    else:
        assert turn.completion.answer_segments[0].kind == "saved_source_claim"
