"""Typed Core observations preserve their kind and authority in Buddy claims."""

from dataclasses import replace

import pytest
from pydantic import ValidationError

from apps.live_control_server.integrations.dungeonmind import (
    world_graph_reads as direct,
)
from graph_memory.interaction.answer_validator import validate_structured_answer
from graph_memory.interaction.authority_classifier import claims_from_retrieval_result
from graph_memory.interaction.claims import GraphClaim
from graph_memory.interaction.session import GraphRetrievalSession, SessionSnapshot
from tests.test_reviewed_source_observation_consumer import _anchor, _observation


def packet(kind="worldbuilding_observation", count=6):
    observations = []
    anchors = []
    for i in range(count):
        assertion = f"assertion:section:{i}"
        evidence = f"evidence:section:{i}"
        native = replace(
            _observation(),
            assertion_id=assertion,
            observation_kind=kind,
            evidence_ref_ids=(evidence,),
            text=f"Section {i}: some communities believe goats float; Example: a cloak {i}.",
        )
        view = direct._reviewed_source_observation_view(native)
        observations.append(view.model_dump(mode="json", by_alias=True))
        anchor = _anchor().model_copy(
            update={
                "anchor_id": f"anchor:section:{i}",
                "evidence_ref_id": evidence,
                "supporting_assertion_ids": [assertion],
            }
        )
        anchors.append(anchor.model_dump(mode="json", by_alias=True))
    return {"reviewedSourceObservations": observations, "sourceAnchors": anchors}


@pytest.mark.parametrize("kind", ["worldbuilding_observation", "session_observation"])
def test_actual_core_typed_facet_reaches_claims_and_session_roundtrip(kind):
    payload = packet(kind)
    claims = claims_from_retrieval_result(payload, revision_id="rev:published")
    assert len(claims) == len({c.claim_id for c in claims}) == 6
    assert all(c.predicate == c.observation_kind == kind for c in claims)
    assert all(
        c.review_id == "review:1" and c.contribution_id == "contribution:1"
        for c in claims
    )
    assert all(c.source_revision_id == "source-revision:2" for c in claims)
    assert all(c.support.source_anchor_ids for c in claims)
    session = GraphRetrievalSession(
        snapshot=SessionSnapshot(
            world_id="world:test",
            campaign_id="campaign:one",
            revision_id="rev:published",
        ),
        question="How do the goats work?",
        claims=claims,
    )
    restored = GraphRetrievalSession.model_validate(
        session.model_dump(mode="json", by_alias=True)
    )
    assert restored.claims == claims
    answer = validate_structured_answer(
        restored, None, model_prose=claims[0].value_text
    )
    assert {r.object_id for r in answer.graph_references} == {
        c.claim_id for c in claims
    }


def test_unknown_kind_is_excluded_even_with_matching_anchor():
    payload = packet(count=1)
    payload["reviewedSourceObservations"][0]["observationKind"] = "invented_observation"
    assert claims_from_retrieval_result(payload, revision_id="rev:published") == []


@pytest.mark.parametrize("field", ["reviewId", "contributionId", "sourceRevisionId"])
def test_missing_review_or_source_identity_is_rejected(field):
    payload = packet(count=1)
    payload["reviewedSourceObservations"][0][field] = None
    with pytest.raises(ValidationError):
        claims_from_retrieval_result(payload, revision_id="rev:published")


def test_missing_and_partial_evidence_anchor_support_are_excluded():
    payload = packet(count=1)
    payload["sourceAnchors"] = []
    assert claims_from_retrieval_result(payload, revision_id="rev:published") == []
    payload = packet(count=1)
    payload["reviewedSourceObservations"][0]["evidenceRefIds"].append(
        "evidence:unanchored"
    )
    assert claims_from_retrieval_result(payload, revision_id="rev:published") == []


def test_claim_wire_cannot_admit_unknown_reviewed_kind():
    claim = claims_from_retrieval_result(packet(count=1), revision_id="rev:published")[
        0
    ]
    with pytest.raises(ValidationError):
        GraphClaim.model_validate(
            {**claim.model_dump(), "observation_kind": "invented_observation"}
        )
