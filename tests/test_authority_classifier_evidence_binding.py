"""Exact relationship-evidence binding at the retrieval claim boundary."""

from __future__ import annotations

import pytest

from graph_memory.interaction.authority_classifier import claims_from_retrieval_result


def test_accepted_relationship_binds_only_exact_same_revision_evidence() -> None:
    claims = claims_from_retrieval_result(
        {
            "relationships": [{
                "edgeId": "rel:one", "sourceNodeId": "node:a",
                "targetNodeId": "node:b", "predicate": "guards",
                "evidenceRefIds": ["ev:one"],
            }],
            "sourceAnchors": [
                {"anchorId": "anchor:opaque", "revisionId": "rev:one",
                 "evidenceRefId": "ev:one", "readable": False,
                 "opened": True, "supportingGraphObjectIds": []},
                {"anchorId": "anchor:unrelated", "revisionId": "rev:one",
                 "evidenceRefId": "ev:other", "readable": True,
                 "supportingGraphObjectIds": ["rel:one"]},
                {"anchorId": "anchor:foreign-revision", "revisionId": "rev:other",
                 "evidenceRefId": "ev:one", "readable": True},
            ],
        },
        revision_id="rev:one",
    )

    assert len(claims) == 1
    claim = claims[0]
    assert claim.claim_id == "rel:one"
    assert claim.evidence_ref_ids == ["ev:one"]
    assert claim.may_state_as_campaign_fact()
    assert claim.support.state == "source_anchor_unreadable"
    assert claim.support.source_anchor_ids == ["anchor:opaque"]
    assert claim.support.unreadable_anchor_ids == ["anchor:opaque"]
    assert claim.support.source_read_ids == []


@pytest.mark.parametrize(
    ("evidence_ids", "anchor_evidence", "anchor_revision"),
    [
        ([], "ev:one", "rev:one"),
        (["ev:foreign"], "ev:one", "rev:one"),
        (["ev:one"], "ev:other", "rev:one"),
        (["ev:one"], "ev:one", "rev:foreign"),
        (["ev:one", " "], "ev:one", "rev:one"),
    ],
)
def test_relationship_evidence_binding_fails_closed(
    evidence_ids: list[str], anchor_evidence: str, anchor_revision: str,
) -> None:
    claims = claims_from_retrieval_result(
        {
            "relationships": [{"edgeId": "rel:one", "evidenceRefIds": evidence_ids}],
            "sourceAnchors": [{
                "anchorId": "anchor:one", "revisionId": anchor_revision,
                "evidenceRefId": anchor_evidence, "readable": True,
                "supportingGraphObjectIds": ["rel:one"],
            }],
        },
        revision_id="rev:one",
    )
    assert claims[0].support.state == "graph_accepted"
    assert claims[0].support.source_anchor_ids == []
    assert claims[0].support.source_read_ids == []


def test_relationship_binding_does_not_promote_nonfact_or_candidate() -> None:
    claims = claims_from_retrieval_result(
        {
            "nodes": [{"nodeId": "node:candidate", "label": "Candidate"}],
            "attributes": [{
                "assertionId": "assertion:rejected", "subjectNodeId": "node:candidate",
                "supportState": "disputed", "evidenceRefIds": ["ev:one"],
            }],
            "sourceAnchors": [{
                "anchorId": "anchor:one", "revisionId": "rev:one",
                "evidenceRefId": "ev:one", "readable": False,
            }],
        },
        revision_id="rev:one",
    )
    assert not any(claim.claim_kind == "relationship" for claim in claims)
    assert next(c for c in claims if c.claim_kind == "attribute").may_state_as_campaign_fact() is False


@pytest.mark.parametrize("readable", [True, False])
def test_initial_attribute_exposes_exact_canonical_evidence_without_opening_source(readable):
    packet = {
        "attributes": [{"assertionId": "asrt:stacey-species", "predicate": "species",
                        "textValue": "Stacey is a half-elf.", "evidenceRefIds": ["ev:stacey-species"]}],
        "sourceAnchors": [
            {"anchorId": "source-anchor:v1:opaque", "revisionId": "rev:one",
             "evidenceRefId": "ev:stacey-species", "readable": readable, "opened": True,
             "supportingAssertionIds": ["asrt:stacey-species"]},
            {"anchorId": "wrong-revision", "revisionId": "rev:other",
             "evidenceRefId": "ev:stacey-species", "supportingAssertionIds": ["asrt:stacey-species"]},
            {"anchorId": "wrong-assertion", "revisionId": "rev:one",
             "evidenceRefId": "ev:stacey-species", "supportingAssertionIds": ["asrt:other"]},
            {"anchorId": "wrong-evidence", "revisionId": "rev:one",
             "evidenceRefId": "ev:other", "supportingAssertionIds": ["asrt:stacey-species"]},
        ],
    }
    claim = claims_from_retrieval_result(
        packet, revision_id="rev:one", include_attribute_evidence_refs=True,
    )[0]
    assert claim.evidence_ref_ids == ["ev:stacey-species"]
    assert claim.support.source_anchor_ids == ["source-anchor:v1:opaque"]
    assert claim.support.source_read_ids == []
    assert claim.support.state != "source_opened"
    assert claim.model_dump(mode="json")["evidence_ref_ids"] == ["ev:stacey-species"]
    # The explicit opt-in preserves frozen v1 and all unrelated consumers.
    legacy = claims_from_retrieval_result(packet, revision_id="rev:one")[0]
    assert "evidence_ref_ids" not in legacy.model_dump(mode="json")
