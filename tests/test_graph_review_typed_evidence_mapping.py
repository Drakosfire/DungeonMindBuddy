"""Fresh Graph Review keeps a typed readable span through the Core V3 mapper."""

import pytest

from apps.live_control_server.integrations.dungeonmind.contribution_mapping import (
    ContributionMappingError,
    GRAPH_REVIEW_EVIDENCE_ID_MARK,
    map_graph_review_contribution_v3,
)
from apps.live_control_server.services.graph_object_authoring_prepare import (
    VerifiedGraphReviewSpan,
    build_assertions_from_proposals,
    translate_assertions_to_contribution,
)
from tests.test_graph_object_authoring_prepare import prepare_request


def test_graph_review_v3_evidence_preserves_per_assertion_span_and_domain() -> None:
    assertions, diagnostics = build_assertions_from_proposals(prepare_request())
    assert not diagnostics
    verified = {
        assertion.assertion_id: VerifiedGraphReviewSpan(
            assertion_id=assertion.assertion_id,
            evidence_ref_id=f"grauth-ev:source:{assertion.assertion_id}",
            source_artifact_id="source",
            source_revision_id="sha256:" + "a" * 64,
            source_domain="session_recap",
            source_span_ref_id="source:paragraph:1",
            source_content_sha256="a" * 64,
            span_content_sha256="b" * 64,
            span_index_sha256=None,
            visibility_state="internal",
        )
        for assertion in assertions
    }
    contribution = translate_assertions_to_contribution(
        world_id="longmont-c1",
        campaign_id="longmont-c1",
        actor="test-actor",
        source_artifact_id="source",
        source_revision_id="sha256:" + "a" * 64,
        assertions=assertions,
        verified_spans=verified,
    )
    mapped = map_graph_review_contribution_v3(
        type("Store", (), {"evidence": {}})(),
        contribution,
        {("source", "sha256:" + "a" * 64): "dm-revision"},
    )
    assert mapped.schema_version == "dm_graph_contribution_v3"
    assert len(mapped.assertions) == 1
    evidence = mapped.assertions[0].evidence_refs[0]
    assert GRAPH_REVIEW_EVIDENCE_ID_MARK in evidence.evidence_ref_id
    assert evidence.source_domain.value == "session_recap"
    assert evidence.source_span_ref_id == "source:paragraph:1"
    assert evidence.source_revision_id == "dm-revision"
    assert evidence.can_open_source is True
    assert evidence.can_highlight_span is True


def test_graph_review_v3_rejects_unverified_evidence_row() -> None:
    assertions, _ = build_assertions_from_proposals(prepare_request())
    verified = {
        item.assertion_id: VerifiedGraphReviewSpan(
            assertion_id=item.assertion_id,
            evidence_ref_id=f"grauth-ev:source:{item.assertion_id}",
            source_artifact_id="source",
            source_revision_id="sha256:" + "a" * 64,
            source_domain="worldbuilding",
            source_span_ref_id="source:span:1",
            source_content_sha256="a" * 64,
            span_content_sha256="b" * 64,
            span_index_sha256="c" * 64,
            visibility_state="internal",
        )
        for item in assertions
    }
    contribution = translate_assertions_to_contribution(
        world_id="longmont-c1",
        campaign_id="longmont-c1",
        actor="test-actor",
        source_artifact_id="source",
        source_revision_id="sha256:" + "a" * 64,
        assertions=assertions,
        verified_spans=verified,
    )
    accepted = contribution.accepted_assertions[0]
    invalid = accepted.model_copy(update={
        "value": {
            **accepted.value,
            "evidence": [{**accepted.value["evidence"][0], "span_index_sha256": "bad"}],
        }
    })
    contribution = contribution.model_copy(update={"accepted_assertions": [invalid]})
    with pytest.raises(ContributionMappingError) as exc:
        map_graph_review_contribution_v3(
            type("Store", (), {"evidence": {}})(),
            contribution,
            {("source", "sha256:" + "a" * 64): "dm-revision"},
        )
    assert exc.value.code == "evidence_span_mismatch"
