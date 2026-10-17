"""Exact question-derived gaps stay nonfactual across SDK and APP completion."""

import json
from copy import deepcopy

import httpx
import psycopg
import pytest

from application_state.agent_conversation import AgentConversationService
from application_state.agent_conversation import source_writer_output as owner
from application_state.agent_conversation import types as ledger
from application_state.errors import ApplicationStateValidationError
from apps.live_control_server.services.build_jev_harness import BuildJevHarness
from tests.test_agent_build_jev_ordinary_harness import (
    DecisionWire,
    WriterWire,
    ordinary_case,
)
from tests.test_build_cited_writer_output import build_case as _build_case

from tests.test_build_jev_estimated_continuations import counter
from tests.test_agent_build_governed_graph import execute


@pytest.fixture
def build_case(tmp_path, monkeypatch, application_state_dsn):
    return _build_case.__wrapped__(tmp_path, monkeypatch, application_state_dsn)


def packet(question="What is the toll?"):
    return {
        "source_writer_output_policy": owner.POLICY,
        "requested_detail_gap_policy": owner.GAP_POLICY,
        "user_question": question,
        "opened_passages": [],
        "exposure": {"saved_sections": []},
        "retrieval_disposition": {
            "status": "insufficient_evidence",
            "coverage_status": "heuristic_partial",
        },
    }


def answer(phrase="toll"):
    return {
        "answer_context_status": "source_grounded_partial",
        "answer_segments": [
            {
                "kind": "source_passage_claim",
                "text": "A guard collects a steep toll.",
                "passage_handles": ["p1"],
            }
        ],
        "limitations": ["missing_requested_details", "partial_retrieval"],
        "requested_detail_gaps": [{"question_phrase": phrase}],
    }


def test_partial_and_abstention_gap_rendering_preserves_facts():
    raw = answer()
    result = owner.normalize(json.dumps(raw), packet())
    assert result["answer_segments"][0] == raw["answer_segments"][0]
    assert result["answer_segments"][1] == {
        "kind": "connective",
        "text": "The selected source excerpts do not establish: “toll”.",
    }
    raw.update(answer_context_status="source_insufficient_evidence", answer_segments=[])
    assert (
        owner.normalize(json.dumps(raw), packet())["answer_segments"][0]["kind"]
        == "connective"
    )
    raw.update(
        answer_context_status="source_grounded",
        requested_detail_gaps=[],
        answer_segments=[answer()["answer_segments"][0]],
        limitations=[],
    )
    assert (
        owner.normalize(
            json.dumps(raw),
            {
                **packet(),
                "retrieval_disposition": {
                    "status": "provisionally_supported",
                    "coverage_status": "catalog_exhausted",
                },
            },
        )["answer_segments"]
        == raw["answer_segments"]
    )


@pytest.mark.parametrize("phrase", [True, 1.0, 12, "Toll", "missing", "", "toll "])
def test_invalid_or_foreign_phrases_refused(phrase):
    with pytest.raises(ValueError):
        owner.normalize(json.dumps(answer(phrase)), packet())


def test_duplicate_overlap_and_injected_prose_scope_refused():
    for extra in [
        {"text": "No exemptions exist"},
        {"scope": "world"},
        {"source_ids": []},
    ]:
        raw = answer()
        raw["requested_detail_gaps"][0].update(extra)
        with pytest.raises(ValueError):
            owner.normalize(json.dumps(raw), packet())
    for phrases in [["toll", "toll"], ["the toll", "toll"]]:
        raw = answer()
        raw["requested_detail_gaps"] = [
            {"question_phrase": phrase} for phrase in phrases
        ]
        with pytest.raises(ValueError):
            owner.normalize(json.dumps(raw), packet())
    with pytest.raises(ValueError, match="exactly once"):
        owner.normalize(json.dumps(answer("aa")), packet("aaa?"))
    raw = answer()
    raw["requested_detail_gaps"] = [
        {"question_phrase": phrase} for phrase in ["toll", "What"]
    ]
    assert (
        "“What”"
        in owner.normalize(json.dumps(raw), packet())["answer_segments"][1]["text"]
    )
    raw = answer()
    raw["limitations"] = ["partial_retrieval"]
    with pytest.raises(ValueError, match="missing-details"):
        owner.normalize(json.dumps(raw), packet())


def test_unicode_codepoints_and_literal_markdown():
    assert (
        "“cost”"
        in owner.normalize(json.dumps(answer("cost")), packet("🌲 cost?"))[
            "answer_segments"
        ][1]["text"]
    )
    phrase = "![mage](https://x.invalid) <b> &amp; `spell`"
    rendered = owner.normalize(json.dumps(answer(phrase)), packet(phrase))[
        "answer_segments"
    ][1]["text"]
    assert r"\!\[mage\]\(https://x\.invalid\)" in rendered
    assert r"\<b\>" in rendered and r"\&amp;" in rendered and r"\`spell\`" in rendered
    for phrase in [" ", "\nsecret", "x" * 257, "!!!", "no\x00one"]:
        with pytest.raises(ValueError):
            owner.normalize(json.dumps(answer(phrase)), packet(phrase))


def test_new_format_is_explicit_and_old_schemas_stay_exact():
    old = deepcopy(packet())
    old.pop("requested_detail_gap_policy")
    for name, schema in [
        (owner.SCHEMA_NAME, owner.output_schema()),
        (owner.FINITE_SCHEMA_NAME, owner.finite_output_schema(old)),
    ]:
        fmt = {"type": "json_schema", "name": name, "schema": schema, "strict": True}
        owner.validate_writer_format(fmt, old)
        with pytest.raises(ValueError):
            owner.validate_writer_format(fmt, packet())
    assert "requested_detail_gaps" not in owner.output_schema()["properties"]
    schema = owner.finite_output_schema(packet(), requested_detail_gaps=True)
    assert "requested_detail_gaps" in schema["required"]
    fmt = {
        "type": "json_schema",
        "name": owner.GAP_SCHEMA_NAME,
        "schema": schema,
        "strict": True,
    }
    owner.validate_writer_format(fmt, packet())
    with pytest.raises(ValueError):
        owner.validate_writer_format(fmt, old)
    with pytest.raises(ValueError):
        owner.normalize(json.dumps(answer()), old)
    with pytest.raises(ValueError):
        owner.normalize(
            json.dumps(answer()), {**packet(), "requested_detail_gap_policy": "world"}
        )


def test_never_served_v3_is_retired_without_an_adapter():
    fmt = {
        "type": "json_schema",
        "name": "build_cited_source_answer_v3",
        "schema": owner.finite_output_schema(packet(), requested_detail_gaps=True),
        "strict": True,
    }
    with pytest.raises(ValueError, match="unknown output schema"):
        owner.validate_writer_format(fmt, packet())
    with pytest.raises(ValueError, match="Unknown requested-detail"):
        owner.normalize(
            json.dumps(answer()),
            {
                **packet(),
                "requested_detail_gap_policy": "question_spans_selected_excerpts_v1",
            },
        )
    raw = answer()
    raw["requested_detail_gaps"] = [
        {"question_span_start": 12, "question_span_end": 16}
    ]
    with pytest.raises(ValueError):
        owner.normalize(json.dumps(raw), packet())


class GapWriter(WriterWire):
    async def handle_async_request(self, request):
        response = await super().handle_async_request(request)
        wire = json.loads(request.content)
        question = json.loads(wire["input"])["user_question"]
        assert wire["text"]["format"]["name"] == owner.GAP_SCHEMA_NAME
        value = response.json()
        content = value["output"][0]["content"][0]
        raw = json.loads(content["text"])
        assert "the toll" in question
        raw["requested_detail_gaps"] = [{"question_phrase": "the toll"}]
        raw["limitations"] = ["missing_requested_details", "partial_retrieval"]
        content["text"] = json.dumps(raw)
        return httpx.Response(200, request=request, json=value)


def test_sdk_app_gap_proof_reconstruction_and_reopen(
    build_case, monkeypatch, tmp_path, application_state_dsn
):
    case, _ = ordinary_case(build_case, monkeypatch)
    source, request, bootstrap = case
    request = request.model_copy(
        update={"message": "What did Frank say, and what is the toll?"}
    )
    case = (source, request, bootstrap)
    original = AgentConversationService.complete_turn
    checked = []

    def guarded(service, result):
        assert isinstance(result, ledger.CitedSourceTurnResult)
        turn = service.list_turns(result.world_id, result.conversation_id)[0]
        with psycopg.connect(application_state_dsn) as conn:
            trace = conn.execute(
                "SELECT payload FROM agent.turn_context_trace WHERE turn_id=%s AND attempt=%s",
                (turn.turn_id, turn.attempt),
            ).fetchone()[0]
        owner.validate_completion_proof(result, turn, trace)
        fmt = json.loads(result.writer_request_json)
        auth = next(
            e
            for e in turn.graph_context_execution.events
            if getattr(e, "provider_attempt_id", None)
            == result.producing_provider_attempt_id
        )
        with pytest.raises(ValueError, match="exact original turn"):
            owner.reconstruct(
                result.raw_provider_output_json,
                {**json.loads(fmt["input"]), "user_question": "foreign"},
                turn,
                auth,
            )
        forged = result.completion.model_copy(deep=True)
        forged.answer_segments[1].text = "No exemptions exist in the World."
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
        checked.append(True)
        return original(service, result)

    monkeypatch.setattr(AgentConversationService, "complete_turn", guarded)
    writer = GapWriter()
    response = execute(
        case,
        tmp_path,
        BuildJevHarness(
            decision_transport=DecisionWire(),
            writer_transport=writer,
            accounting=counter(),
        ),
    )
    assert checked == [True] and len(writer.calls) == 1
    assert "Frank believes" in response.answer.text
    assert (
        "The selected source excerpts do not establish: “the toll”."
        in response.answer.text
    )
    service = AgentConversationService()
    turn = service.list_turns(
        "elderwyld", service.get_world_pointer("elderwyld").active_conversation_id
    )[0]
    assert turn.status == "completed"
    assert {c.segment_index for c in turn.completion.source_citations} == {0}
    assert turn.completion.answer_segments[1].kind == "connective"
    assert (
        ledger.BuildGraphCompletionV2.model_validate(
            turn.completion.model_dump(mode="json", by_alias=True)
        )
        == turn.completion
    )


def test_new_format_reserves_completion_capacity_for_host_messages():
    raw = answer()
    raw["answer_segments"] *= 109
    phrases = [f"item{i:02d}" for i in range(16)]
    raw["requested_detail_gaps"] = [{"question_phrase": phrase} for phrase in phrases]
    question = " ".join(phrases)
    raw["limitations"].append("unresolved_conflict")
    assert (
        len(owner.normalize(json.dumps(raw), packet(question))["answer_segments"])
        == 128
    )
    raw["answer_segments"].append(raw["answer_segments"][0])
    with pytest.raises(ValueError):
        owner.normalize(json.dumps(raw), packet(question))
