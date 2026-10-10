"""Reviewed source evidence stays distinct through Buddy's two read surfaces."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch

from dungeonmind.application.world_graph_retrieval import ReviewedSourceObservation
from dungeonmind.contracts.vocabulary import Visibility

from apps.live_control_server.integrations.dungeonmind import world_graph_reads as direct
from apps.live_control_server.models.world_graph_object_projection import (
    SelectedObjectCompletenessView,
    WorldGraphObjectProjectionResult,
)
from apps.live_control_server.services.agent_world_graph_query_context import (
    AgentWorldGraphQueryContextRequest,
    render_world_graph_prompt_block,
    resolve_agent_world_graph_query_context,
)
from graph_memory.interaction.answer_validator import validate_structured_answer
from graph_memory.interaction.authority_classifier import claims_from_retrieval_result
from graph_memory.interaction.claims import GraphClaim
from graph_memory.interaction.expansion_executor import execute_expand_graph_retrieval
from graph_memory.interaction.session import GraphRetrievalSession, SessionSnapshot
from graph_memory.interaction.session_store import clear_sessions, create_session
from graph_memory.retrieval.models import (
    RETRIEVAL_OBJECT_REQUEST_SCHEMA,
    WorldGraphObjectRequest,
    WorldGraphRetrievalResult,
    WorldGraphSourceAnchor,
)


def _observation() -> ReviewedSourceObservation:
    return ReviewedSourceObservation(
        assertion_id="assertion:reviewed:1",
        subject_object_id="npc:keeper",
        observation_kind="session_observation",
        text="The keeper saw a blue lantern by the gate.",
        entity_kind="npc",
        review_id="review:1",
        contribution_id="contribution:1",
        publication_revision_id="rev:published",
        source_artifact_id="artifact:recap:2",
        source_revision_id="source-revision:2",
        evidence_ref_ids=("evidence:1",),
        campaign_scope="campaign:one",
        visibility=Visibility.GM,
        epistemic_kind="fact",
        temporal_scope=None,
    )


def _anchor() -> WorldGraphSourceAnchor:
    return WorldGraphSourceAnchor(
        anchor_id="anchor:1",
        revision_id="rev:published",
        evidence_ref_id="evidence:1",
        source_artifact_id="artifact:recap:2",
        source_domain="session_recap",
        supporting_assertion_ids=["assertion:reviewed:1"],
        readable=True,
        locator_kind="source_span",
    )


def test_pinned_native_observation_reaches_ordinary_harness_claim_and_event(monkeypatch):
    """The second native read uses the same pin; tool claims retain provenance."""
    bounded_snapshot = SimpleNamespace(
        revision_id="rev:published", head_revision_id="rev:published",
        is_head=True, projected_at=1,
    )
    complete_snapshot = SimpleNamespace(
        revision_id="rev:published", head_revision_id="rev:later",
        is_head=False, projected_at=2,
    )
    observed_requests = []

    class Retrieval:
        def get_object(self, request, *, object_id, bounds):
            observed_requests.append(("bounded", request.revision_pin, object_id, bounds))
            return SimpleNamespace(
                snapshot=bounded_snapshot, found=True,
                object=SimpleNamespace(object_id="npc:keeper"),
            )

        def get_complete_object(self, request, *, object_id):
            observed_requests.append(("complete", request.revision_pin, object_id))
            return SimpleNamespace(
                snapshot=complete_snapshot,
                found=True,
                object=SimpleNamespace(object_id="npc:keeper"),
                reviewed_source_observations=(_observation(),),
                anchors=(object(),),
                coverage=SimpleNamespace(gap_codes=(), missing_ids=()),
            )

    services = SimpleNamespace(
        binding=direct.DirectAuthorityBinding(
            world_id="world:test",
            dungeonmind_first_revision_id="rev:published",
            dungeonmind_head_revision_id="rev:published",
            legacy_buddy_revision_id=None,
            genesis="reviewed_world_initialization",
        ),
        retrieval=Retrieval(),
    )
    monkeypatch.setattr(
        direct,
        "_object_result_view",
        lambda _row, *, request: WorldGraphRetrievalResult(
            operation="object", outcome="enough", requested_node_id=request.node_id
        ),
    )
    monkeypatch.setattr(direct, "_source_anchor_views", lambda *_a, **_k: [_anchor()])
    request = WorldGraphObjectRequest.model_validate({
        "schema": RETRIEVAL_OBJECT_REQUEST_SCHEMA,
        "worldId": "world:test",
        "campaignId": "campaign:one",
        "revisionPin": "rev:published",
        "nodeId": "npc:keeper",
    })
    result, observations, gaps, missing = direct.get_object_with_reviewed_sources_direct(
        services, request
    )
    assert [kind for kind, *_ in observed_requests] == ["bounded", "complete"]
    assert {pin for _, pin, *_ in observed_requests} == {"rev:published"}
    assert observations[0].review_id == "review:1"
    assert result.attributes == []
    assert result.source_anchors[0].supporting_assertion_ids == ["assertion:reviewed:1"]
    assert gaps == missing == []

    clear_sessions()
    try:
        session = GraphRetrievalSession(
            snapshot=SessionSnapshot(
                world_id="world:test", campaign_id="campaign:one",
                revision_id="rev:published",
            ),
            question="What happened?",
            preflight_candidate_ids=["npc:keeper"],
        )
        create_session(session)
        with patch(
            "graph_memory.interaction.expansion_executor.retrieval_service.get_campaign_object_with_reviewed_sources",
            return_value=(result, observations, gaps, missing),
        ):
            tool = execute_expand_graph_retrieval({
                "schema": "dmb_expand_graph_retrieval_request_v1",
                "retrievalSessionId": session.id,
                "operation": "object",
                "targets": [{"kind": "node", "id": "npc:keeper"}],
            })
        assert tool["reviewedSourceObservations"][0]["publicationRevisionId"] == "rev:published"
        assert tool["reviewedSourceObservations"][0]["sourceRevisionId"] == "source-revision:2"
        claim = session.claim_by_id("assertion:reviewed:1")
        assert claim is not None
        assert claim.claim_kind == "source_observation"
        assert claim.review_id == "review:1"
        assert claim.contribution_id == "contribution:1"
        assert claim.support.source_anchor_ids == ["anchor:1"]
        assert session.operations[-1].added_claim_ids == ["assertion:reviewed:1"]
        replayed = GraphRetrievalSession.model_validate(
            session.model_dump(mode="json", by_alias=True)
        )
        assert replayed.claim_by_id("assertion:reviewed:1").review_id == "review:1"
        validated = validate_structured_answer(session, None, model_prose="A lantern was seen.")
        assert validated.graph_references[0].object_id == "assertion:reviewed:1"
        assert "reviewed source observation" in validated.support_claim_ledger_text
    finally:
        clear_sessions()


def test_selected_object_context_keeps_reviewed_observation_separate(monkeypatch):
    observation = direct._reviewed_source_observation_view(_observation())
    complete = WorldGraphObjectProjectionResult(
        found=True,
        completeness=SelectedObjectCompletenessView(status="complete"),
        requested_node_id="npc:keeper",
        resolved_node_id="npc:keeper",
        reviewed_source_observations=[observation],
        coverage_gap_codes=["missing_source_authority"],
        coverage_missing_ids=["source-revision:missing"],
    )
    monkeypatch.setattr(
        "apps.live_control_server.services.agent_world_graph_query_context.project_complete_world_object",
        lambda *_a, **_k: complete,
    )
    envelope = resolve_agent_world_graph_query_context(
        AgentWorldGraphQueryContextRequest.model_validate({
            "schema": "dmb_agent_world_graph_query_context_request_v1",
            "world_id": "world:test",
            "campaign_id": "campaign:one",
            "selected_node_id": "npc:keeper",
        }),
        outer_text="What happened?",
        outer_campaign_id="campaign:one",
    )
    assert envelope["attributes"] == []
    assert envelope["reviewed_source_observations"][0]["review_id"] == "review:1"
    assert envelope["reviewed_source_observation_coverage"]["missing_ids"] == [
        "source-revision:missing"
    ]
    prompt = render_world_graph_prompt_block(envelope)
    assert "The keeper saw a blue lantern" in prompt
    assert "missing_source_authority" in prompt


def test_observation_without_matching_evidence_anchor_is_not_a_claim():
    observation = direct._reviewed_source_observation_view(_observation())
    payload = {
        "reviewedSourceObservations": [observation.model_dump(mode="json", by_alias=True)],
        "sourceAnchors": [],
    }
    assert claims_from_retrieval_result(payload, revision_id="rev:published") == []


def test_legacy_claim_wire_shape_has_no_new_source_fields():
    claim = GraphClaim(
        claim_id="assertion:legacy", claim_kind="attribute", revision_id="rev:published",
        authority_class="gm_authored_accepted_assertion",
    )
    wire = claim.model_dump(mode="json", by_alias=True)
    assert "reviewId" not in wire
    assert "evidenceRefIds" not in wire
    assert "sourceAssertionId" not in wire


def test_missing_review_authority_is_reported_without_inventing_observation(monkeypatch):
    snapshot = SimpleNamespace(revision_id="rev:published")

    class Retrieval:
        def get_object(self, *_a, **_k):
            return SimpleNamespace(snapshot=snapshot, found=False, object=None)

        def get_complete_object(self, *_a, **_k):
            return SimpleNamespace(
                snapshot=snapshot, found=False, object=None,
                reviewed_source_observations=(), anchors=(),
                coverage=SimpleNamespace(
                    gap_codes=("review_authority_unavailable",),
                    missing_ids=("review:missing",),
                ),
            )

    services = SimpleNamespace(
        binding=direct.DirectAuthorityBinding(
            world_id="world:test",
            dungeonmind_first_revision_id="rev:published",
            dungeonmind_head_revision_id="rev:published",
            legacy_buddy_revision_id=None,
            genesis="reviewed_world_initialization",
        ),
        retrieval=Retrieval(),
    )
    monkeypatch.setattr(
        direct, "_object_result_view",
        lambda *_a, **_k: WorldGraphRetrievalResult(operation="object", outcome="empty"),
    )
    request = WorldGraphObjectRequest.model_validate({
        "schema": RETRIEVAL_OBJECT_REQUEST_SCHEMA,
        "worldId": "world:test",
        "campaignId": "campaign:one",
        "revisionPin": "rev:published",
        "nodeId": "npc:keeper",
    })
    result, observations, gaps, missing = direct.get_object_with_reviewed_sources_direct(
        services, request
    )
    assert observations == []
    assert gaps == ["review_authority_unavailable"]
    assert missing == ["review:missing"]
    assert result.diagnostics[0].code == "review_authority_unavailable"
