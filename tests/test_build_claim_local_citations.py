"""Producer instructions and existing mixed-lane SDK/APP citation boundaries.

These checks do not establish semantic entailment. Real frozen-input contrasts
and ordinary citation inspection remain separate evidence.
"""

import json
from types import SimpleNamespace
from uuid import UUID

import httpx
import pytest

from application_state.agent_conversation import source_quote_binding as quotes
from application_state.agent_conversation import types as t
from application_state.agent_conversation.build_draft_answer import source_claim_limitations
from application_state.agent_conversation.build_draft_context import resolve_body_aliases
from tests.test_build_related_pages import PagesWriter, completed
from tests.test_build_related_pages import build_case as _build_case


@pytest.fixture
def build_case(tmp_path, monkeypatch, application_state_dsn):
    return _build_case.__wrapped__(tmp_path, monkeypatch, application_state_dsn)


@pytest.fixture
def mixed_answer(build_case, monkeypatch, tmp_path):
    original = PagesWriter.handle_async_request

    async def respond(self, request):
        response = await original(self, request)
        wire = json.loads(request.content)
        packet = resolve_body_aliases(json.loads(wire["input"]))
        passage = packet["opened_passages"][0]
        section = packet["artifact_under_edit"]["sections"][0]
        # Each part states only its own witness, with the original lane/selector.
        native = passage["text"].strip().splitlines()[0]
        saved = section["text"].strip().splitlines()[0]
        raw = {
            "answer_context_status": "source_grounded_partial",
            "answer_segments": [
                {"kind": "source_passage_claim", "text": native,
                 "passage_handles": [passage["handle"]], "supporting_quotes": [native]},
                {"kind": "saved_source_claim", "text": saved,
                 "section_read_ids": [section["read_id"]], "supporting_quotes": [saved]},
            ],
            "limitations": sorted(source_claim_limitations(packet)),
            "requested_detail_gaps": [],
            "collaboration": None,
        }
        self.raw_output = raw
        payload = response.json()
        payload["output"][0]["content"][0]["text"] = json.dumps(raw)
        return httpx.Response(200, request=request, json=payload)

    monkeypatch.setattr(PagesWriter, "handle_async_request", respond)
    return completed.__wrapped__(
        build_case, monkeypatch, tmp_path, SimpleNamespace(param="answer_from_sources")
    )


def test_actual_writer_keeps_independently_supported_parts_in_their_original_lanes(mixed_answer):
    turn, service, _, _, _, transport, _ = mixed_answer
    assert len(transport.calls) == 1
    wire = json.loads(transport.calls[0].content)
    packet = resolve_body_aliases(json.loads(wire["input"]))
    assert "Split answer portions that require different supporting evidence" in wire["instructions"]
    assert "A quote supporting one clause does not support neighboring clauses" in wire["instructions"]
    assert "use it in its own segment; do not omit that portion or invent an evidence gap" in wire["instructions"]
    assert quotes.enabled(packet)
    assert wire["model"] == "gpt-6.1-sol"
    assert wire["reasoning"] == {"effort": "low"}
    assert turn.graph_context_execution.policy.provider_roles.writer.model == wire["model"]
    assert turn.graph_context_execution.policy.provider_roles.controller.model == "jev-1.14.0"
    native, saved = turn.completion.answer_segments
    assert native.kind == "source_passage_claim" and saved.kind == "saved_source_claim"
    assert saved.content_sha256 == turn.graph_context_receipt.source_basis.content_sha256
    execution = turn.graph_context_execution
    read = next(e for e in execution.events if isinstance(e, t.ValidatedBuildSectionReadV1)
                and e.read_id == UUID(packet["artifact_under_edit"]["sections"][0]["read_id"]))
    (binding,) = [b for e in execution.events if isinstance(e, t.BuildSectionAnswerBindingV1)
                  for b in e.bindings]
    assert binding.segment_index == 1 and binding.section_event_ids == [read.event_id]
    assert turn.completion.source_citations
    assert all(c.segment_index == 0 for c in turn.completion.source_citations)
    assert "supporting_quotes" not in turn.completion.model_dump_json()
    retained = next(value for value in service.list_turns(turn.world_id, turn.conversation_id)
                    if value.turn_id == turn.turn_id)
    assert retained.completion == turn.completion


def test_exact_witness_membership_is_not_an_entailment_or_citation_repair_judge():
    packet = {
        quotes.KEY: quotes.CURRENT_POLICY,
        "connected_page_review_policy": "typed_connected_page_review_v1",
        "opened_passages": [{"handle": "biography", "text": "The keeper lost her daughter."}],
        "artifact_under_edit": {"sections": [{"read_id": "help", "text": "She helps after a DC 15 check."}]},
    }
    raw = {"answer_segments": [{
        "kind": "source_passage_claim",
        "text": "The keeper lost her daughter. She helps after a DC 15 check.",
        "passage_handles": ["biography"],
        "supporting_quotes": ["The keeper lost her daughter."],
    }]}
    projected = quotes.validate_and_project(raw, packet)
    assert projected["answer_segments"][0]["passage_handles"] == ["biography"]
    assert projected["answer_segments"][0]["text"] == raw["answer_segments"][0]["text"]
    # The producer violation stays observable; host code must not silently invent
    # a second selector, reinterpret the claim, or label this test semantic proof.
    assert raw["answer_segments"][0]["supporting_quotes"] == ["The keeper lost her daughter."]


def test_final_writer_allocation_is_shared_by_authorization_and_budget_only():
    from apps.live_control_server.services import build_jev_dispatch as controller
    from apps.live_control_server.services import build_jev_writer as writer

    budget = controller.request_budget()
    assert budget["model"] == "jev-1.14.0"
    assert budget["providerRoles"]["controller"]["model"] == "jev-1.14.0"
    assert budget["providerRoles"]["writer"] == {
        "provider": writer.PROVIDER, "model": "gpt-6.1-sol", "api_mode": writer.API_MODE,
    }
    role = writer.role_budget()
    assert role["model"] == "gpt-6.1-sol"
    assert role["context_limit_tokens"] == 128_000
    assert role["max_request_bytes"] == 128_000
    assert role["output_reserve_tokens"] == 4096


def test_historical_writer_budget_preserves_exact_allocation_without_rerouting():
    from apps.live_control_server.services import build_jev_writer as writer

    historical = {**writer.role_budget(), "model": "gpt-6-luna"}
    assert t.BuildWriterContextBudgetV1.model_validate(historical).model_dump(
        mode="json", by_alias=True
    ) == historical
    assert t.BuildWriterContextBudgetV1.model_validate(historical).identity() == (
        "openai", "gpt-6-luna", "responses"
    )


@pytest.mark.parametrize("completed", ["propose_build_insertion", "prepare_build_image"], indirect=True)
def test_authoring_producers_use_the_same_frozen_build_writer_role(completed):
    turn, _, _, _, _, transport, _ = completed
    (call,) = transport.calls
    wire = json.loads(call.content)
    assert wire["model"] == "gpt-6.1-sol"
    assert wire["model"] == turn.graph_context_execution.policy.provider_roles.writer.model
    assert wire["reasoning"] == {"effort": "low"}
    assert turn.status == "completed"


def test_mismatched_writer_model_is_not_a_fallback(mixed_answer):
    from apps.live_control_server.services import build_jev_writer as writer

    turn, _, _, _, _, transport, _ = mixed_answer
    wire = json.loads(transport.calls[0].content)
    with pytest.raises(ValueError, match="exact parent projection"):
        writer.validate_body(
            json.dumps({**wire, "model": "gpt-6-luna"}), transport.staged,
            budget=turn.graph_context_execution.policy.writer_context_budget.model_dump(
                mode="json", by_alias=True
            ),
        )
    assert len(transport.calls) == 1


def test_reader_fence_refuses_an_older_runtime(application_state_dsn, monkeypatch):
    from application_state import cli
    from application_state.errors import ApplicationStateMigrationError

    cli.assert_at_head(dsn=application_state_dsn)
    monkeypatch.setattr(cli, "_alembic_head", lambda: "20261028_0086")
    with pytest.raises(ApplicationStateMigrationError):
        cli.assert_at_head(dsn=application_state_dsn)
