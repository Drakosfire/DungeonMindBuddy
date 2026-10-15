"""Search pointers retain native evidence qualification without minting claims."""
from dataclasses import replace
import hashlib
import json
from types import SimpleNamespace

import pytest
from dungeonmind.application.world_graph_retrieval import (
    GraphSearchResult, ReviewedSourceObservationMatch, RetrievalCoverage,
)
from dungeonmind.contracts.projection_v2 import ScopeModeV2
from dungeonmind.contracts.vocabulary import Visibility
from pydantic import ValidationError

from apps.live_control_server.integrations.dungeonmind import world_graph_reads as direct
from apps.live_control_server.services.hermes_graph_interaction_tools import (
    execute_hermes_graph_interaction_tool_json, hermes_graph_interaction_tool_definitions,
)
from graph_memory.interaction import expansion_executor as executor
from graph_memory.interaction.authority_classifier import claims_from_retrieval_result
from graph_memory.interaction.session import GraphRetrievalSession, SessionSnapshot
from graph_memory.interaction.session_store import clear_sessions, create_session
from graph_memory.retrieval.models import (
    RETRIEVAL_SEARCH_REQUEST_SCHEMA, WorldGraphRetrievalResult,
    WorldGraphSearchRequest,
)

TEXT = "The keeper believes the visitors may be cult scouts; this is unconfirmed."


def _match(text=TEXT, start=0, end=None):
    end = len(text) if end is None else end
    return ReviewedSourceObservationMatch(
        assertion_id="assertion:reviewed", subject_object_id="npc:keeper",
        observation_kind="worldbuilding_observation", text_excerpt=text[start:end],
        excerpt_start=start, excerpt_end=end, text_length=len(text),
        text_sha256=hashlib.sha256(text.encode()).hexdigest(), entity_kind="npc",
        review_id="review:1", contribution_id="contribution:1",
        publication_revision_id="rev:published", source_artifact_id="artifact:1",
        source_revision_id="source-revision:1", evidence_ref_ids=("evidence:1",),
        campaign_scope=None, visibility=Visibility.GM, epistemic_kind="belief",
        temporal_scope={"as_of": "source"},
    )


def _native(matches):
    return GraphSearchResult(
        snapshot=SimpleNamespace(world_id="world:test", campaign_id=None,
            revision_id="rev:published", head_revision_id="rev:published", is_head=True,
            admissibility="gm", scope_mode=ScopeModeV2.WORLD_CROSS_CAMPAIGN),
        referents=(), matched_object_ids=("npc:keeper",),
        match_reasons={"npc:keeper": ("reviewed_source_observation_terms",)},
        objects=(SimpleNamespace(object_id="npc:keeper",label="Keeper",kind="npc",
            aliases=(),summary=None,evidence_ref_ids=()),),
        relationships=(), property_assertions=(), anchors=(), coverage=RetrievalCoverage(),
        reviewed_source_observation_matches=tuple(matches),
    )


def _request():
    return WorldGraphSearchRequest.model_validate({
        "schema":RETRIEVAL_SEARCH_REQUEST_SCHEMA, "worldId":"world:test",
        "campaignId":"", "scopeMode":"world", "revisionPin":"rev:published",
        "queryText":"cult scouts",
    })


def test_native_adapter_serialized_harness_preserves_qualified_discovery(monkeypatch):
    native = _native([_match()])
    projected = direct._search_result_view(native,request=_request())
    monkeypatch.setattr(executor.retrieval_service,"search_campaign_graph",lambda req: projected)
    clear_sessions()
    try:
        session=create_session(GraphRetrievalSession(
            snapshot=SessionSnapshot(world_id="world:test",campaign_id="",
                revision_id="rev:published",scope_mode="world"),question="cult scouts"))
        raw=execute_hermes_graph_interaction_tool_json("expand_graph_retrieval",{
            "retrievalSessionId":session.id,"operation":"search","queryText":"cult scouts"})
        wire=json.loads(raw)
        row=wire["reviewedSourceObservationMatches"][0]
        assert row == projected.model_dump(mode="json",by_alias=True)["reviewedSourceObservationMatches"][0]
        assert row["textExcerpt"] == TEXT
        assert row["epistemicKind"] == "belief"
        assert row["temporalScope"] == {"as_of":"source"}
        assert row["assertionId"] == "assertion:reviewed"
        assert row["subjectNodeId"] == "npc:keeper"
        assert row["reviewId"] == "review:1"
        assert row["publicationRevisionId"] == "rev:published"
        assert row["sourceRevisionId"] == "source-revision:1"
        assert row["evidenceRefIds"] == ["evidence:1"]
        assert wire["nodes"][0]["summary"] is None
        assert wire["attributes"] == []
        assert [c["claim_kind"] for c in wire["claimLedger"]] == ["identity"]
        assert session.claim_by_id("assertion:reviewed") is None
    finally:
        clear_sessions()


def test_native_excerpt_offsets_and_full_digest_survive_without_reconstruction():
    text="Ω prefix " + TEXT + " trailing text"
    row=_match(text,start=9,end=9+len(TEXT))
    result=direct._search_result_view(_native([row]),request=_request())
    mapped=result.reviewed_source_observation_matches[0]
    assert mapped.text_excerpt == text[mapped.excerpt_start:mapped.excerpt_end]
    assert mapped.excerpt_start > 0 and mapped.excerpt_end < mapped.text_length
    assert mapped.text_sha256 == hashlib.sha256(text.encode()).hexdigest()
    assert mapped.text_length == len(text)


def test_excluded_native_observation_is_not_reconstructed_from_identity():
    result=direct._search_result_view(_native([]),request=_request())
    assert result.matched_node_ids == ["npc:keeper"]
    assert result.reviewed_source_observation_matches == []
    assert result.nodes[0].summary is None


def test_default_empty_and_pointer_only_response_never_creates_claim():
    result=WorldGraphRetrievalResult(operation="search",outcome="empty")
    wire=result.model_dump(mode="json",by_alias=True)
    assert wire["reviewedSourceObservationMatches"] == []
    result=direct._search_result_view(_native([_match()]),request=_request())
    assert all(c.claim_id != "assertion:reviewed" for c in claims_from_retrieval_result(
        result.model_dump(mode="json",by_alias=True),revision_id="rev:published"))


@pytest.mark.parametrize("change",[{"excerpt_end":999},{"text_excerpt":"x"}])
def test_invalid_native_excerpt_extent_fails_instead_of_silent_clipping(change):
    row=replace(_match(),**change)
    with pytest.raises(ValidationError):
        direct._search_result_view(_native([row]),request=_request())


def test_tool_guidance_requires_object_and_source_read_for_discovery_pointers():
    definition=hermes_graph_interaction_tool_definitions()[0]["function"]["description"]
    assert "reviewedSourceObservationMatches" in definition
    assert "belief and conditional language" in definition
    assert "supporting source" in definition
    assert "does not establish council membership" in definition


def test_native_anchor_identity_stays_joined_to_discovery_assertion():
    anchor=SimpleNamespace(anchor_id="dm-source-anchor:v1:test",evidence_ref_id="evidence:1",
        source_artifact_id="artifact:1",source_revision_id="source-revision:1",
        source_span_ref_id="span:1",locator_identity="span:1",can_open_source=True,
        supporting_object_ids=("npc:keeper",),supporting_assertion_ids=("assertion:reviewed",),
        evidence=SimpleNamespace(source_domain="worldbuilding"),artifact=SimpleNamespace(uri="repo://source.md"))
    native=replace(_native([_match()]),anchors=(anchor,))
    projected=direct._search_result_view(native,request=_request())
    pointer=projected.reviewed_source_observation_matches[0]
    mapped=projected.source_anchors[0]
    assert mapped.anchor_id == "source-anchor:v1:test"
    assert mapped.readable and mapped.locator_kind == "source_span"
    assert mapped.supporting_assertion_ids == [pointer.assertion_id]
    assert mapped.supporting_graph_object_ids == [pointer.subject_node_id]
    assert mapped.evidence_ref_id in pointer.evidence_ref_ids
    assert mapped.source_artifact_id == pointer.source_artifact_id
    assert mapped.source_span_ref_id == "span:1"
