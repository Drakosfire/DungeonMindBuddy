# ruff: noqa: F811
"""Real Plan writer/APP acceptance with source-only objects, no external inference."""

import asyncio
import json
import pytest
from application_state.agent_conversation import AgentConversationService
from application_state.agent_conversation import types as t
from application_state.agent_conversation.rules_authority_policy import rules_capability
from apps.live_control_server.services.plan_jev_driver import PlanJevDriver
from apps.live_control_server.services.plan_jev_rules_runtime import PlanRulesRuntime
from apps.live_control_server.services.plan_jev_writer import PlanJevWriter
from graph_memory.interaction.session import GraphReferent
from tests.test_plan_jev_dispatch import plan_adapter  # noqa: F401
from tests.test_plan_jev_driver import Decisions, fixture_reads
from tests.test_plan_jev_writer import WriterWire


def stage(adapter):
    adapter.bootstrap.retrieval_session.referents = [
        GraphReferent(id="pond", label="Park pond")
    ]
    fixture_reads(adapter, anchors=2, node_only=True)
    rules = PlanRulesRuntime(adapter, rules_capability(graph=True))
    driver = PlanJevDriver(adapter)
    proof = asyncio.run(
        driver.run(transport=Decisions(), api_key="synthetic-not-secret")
    )
    writer = PlanJevWriter(adapter, proof, rules)
    assert writer.projection.frame["graph_records"] == []
    assert len(writer.projection.frame["opened_passages"]) == 2
    return writer


def answer(writer):
    return {
        "schema": "dmb_surface_evidence_answer_v1",
        "limitations": [], "requested_detail_gaps": [],
        "answer_segments": [
            {
                "kind": "source_passage_claim",
                "text": "The Synthetic park journal describes the walkway.",
                "passage_handles": [
                    p["passage_handle"]
                    for p in writer.projection.frame["opened_passages"]
                ],
            }
        ],
    }


def test_actual_plan_source_only_writer_persists_exact_receipts_and_reopens(
    plan_adapter,
    monkeypatch,
):
    writer = stage(plan_adapter)
    wire = WriterWire(plan_adapter, json.dumps(answer(writer)))
    completed = asyncio.run(writer.run(transport=wire, api_key="synthetic-not-secret"))
    assert completed.status == "completed" and len(wire.calls) == 1
    instructions=json.loads(wire.calls[0].content)["instructions"]
    from application_state.agent_conversation.surface_source_answer import SOURCE_ATTRIBUTION_INSTRUCTIONS
    assert instructions.count(SOURCE_ATTRIBUTION_INSTRUCTIONS) == 1
    assert "Use source names in prose" not in instructions
    assert "dmb_surface_evidence_answer_v1" in instructions
    assert "passage_handles" in instructions
    assert "authored_quote" in instructions

    assert isinstance(completed.completion, t.SurfaceEvidenceCompletionV1)
    assert (
        completed.completion.surface_id == "plan"
        and completed.completion.citation_map is None
    )
    assert len(completed.completion.source_citations) == 2
    assert all(
        c.source_name == "Synthetic park journal"
        for c in completed.completion.source_citations
    )
    reopened = AgentConversationService().inspect_turn(
        world_id=completed.world_id, turn_id=completed.turn_id
    )
    assert (
        reopened.completion == completed.completion
        and reopened.assistant_text == completed.assistant_text
    )
    assert len(wire.calls) == 1
    from apps.live_control_server.integrations.dungeonmind import (
        world_graph_reads as direct,
    )
    from apps.live_control_server.services.agent_source_passages import (
        open_source_passage,
    )
    from graph_memory.retrieval.models import WorldGraphSourceAnchorReadResult

    citation = completed.completion.source_citations[0]
    r = citation.receipt
    passage = next(
        p["text"]
        for p in writer.projection.frame["opened_passages"]
        if p["line_start"] == r.line_start
        and __import__("hashlib").sha256(p["text"].encode()).hexdigest()
        == r.content_sha256
    )
    authority = completed.graph_context_receipt.graph_authority
    result = WorldGraphSourceAnchorReadResult.model_validate(
        {
            "outcome": "enough",
            "snapshot": {
                "worldId": authority.native_world_id,
                "campaignId": "",
                "scopeMode": "world",
                "focus": {"kind": "none", "sessionId": None},
                "admissibility": "gm",
                "revisionId": authority.graph_revision,
                "headRevisionId": "newer-head",
                "isHead": False,
            },
            "anchorId": r.anchor_id,
            "evidenceRefId": r.evidence_ref_id,
            "sourceArtifactId": r.source_artifact_id,
            "content": passage,
            "contentSha256": "a" * 64,
            "lineStart": r.line_start,
            "lineEnd": r.line_end,
            "truncated": False,
        }
    )
    opened = direct.ResolvedSourceAnchorReadV2(
        result=result,
        source_revision_id=r.source_revision_id,
        source_revision_sha256="a" * 64,
        evidence_ref_id=r.evidence_ref_id,
        source_artifact_id=r.source_artifact_id,
        source_span_ref_id="span-one",
        locator_kind="source_span",
        locator_identity="span-one",
        graph_revision=authority.graph_revision,
    )
    calls = []
    monkeypatch.setattr(direct, "direct_services_from_config", lambda *_a: object())

    def read(_services, request, **_kwargs):
        calls.append(request)
        return opened

    monkeypatch.setattr(direct, "read_source_anchor_direct_v2", read)
    response = open_source_passage(
        world_id=completed.world_id, turn_id=completed.turn_id, citation_index=0
    )
    assert response.content == passage and response.citation == citation
    assert response.citation.source_name == "Synthetic park journal"
    assert calls[0].revision_pin == authority.graph_revision


@pytest.mark.parametrize(
    "mutation",
    [
        "unknown_handle",
        "metadata",
        "graph_claim",
        "duplicate_handle",
        "changed_producing_input",
    ],
)
def test_invalid_source_only_provider_reply_never_persists_completion(
    plan_adapter, mutation
):
    writer = stage(plan_adapter)
    candidate = answer(writer)
    segment = candidate["answer_segments"][0]
    if mutation == "unknown_handle":
        segment["passage_handles"] = ["unknown"]
    elif mutation == "metadata":
        segment["source_artifact_id"] = "forged"
    elif mutation == "graph_claim":
        segment.update(
            kind="graph_claim",
            claim_id="claim:1",
            target_kind="assertion",
            target_id="invented",
        )
    elif mutation == "duplicate_handle":
        segment["passage_handles"] *= 2
    else:
        # A real final frame must still match admission; changed body loses its receipt binding.
        writer.proof["source_names"] = {
            key: "Changed source" for key in writer.proof["source_names"]
        }
    wire = WriterWire(plan_adapter, json.dumps(candidate))
    with pytest.raises(Exception):
        asyncio.run(writer.run(transport=wire, api_key="synthetic-not-secret"))
    turn = AgentConversationService().inspect_turn(
        world_id=plan_adapter.world_id, turn_id=plan_adapter.turn.turn_id
    )
    assert turn.completion is None
