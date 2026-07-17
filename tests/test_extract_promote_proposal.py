"""Tests for sealed promote proposal digest and verification."""

from __future__ import annotations

import pytest

from graph_memory.extract_promote_proposal import (
    PromoteProposalError,
    compute_proposal_digest,
    seal_promote_proposal,
    verify_promote_proposal,
)
from graph_memory.kernel.contributions import build_assertion, create_graph_contribution


def _assertion(*, label: str = "vial", outcome: str = "created_new"):
    return build_assertion(
        assertion_kind="node",
        acceptance_state="accepted",
        subject_node_id="obj:vial",
        label=label,
        value={
            "kind": "item",
            "role": "item",
            "aliases": [label],
            "source_domains": ["recap"],
            "canon_state": "canonical",
            "approval_state": "accepted",
        },
        evidence_ref_ids=["evidence:a:span"],
        source_artifact_id="artifact:a",
        source_revision_id="sha256:abc",
        campaign_scope="longmont-c2",
        epistemic_kind="source_derived_candidate",
        visibility="gm",
        identity_resolution_outcome=outcome,
    )


def _contribution():
    return create_graph_contribution(
        world_id="eldyrwild",
        source_kind="source_extraction",
        source_artifact_id="artifact:a",
        source_revision_id="sha256:abc",
        extraction_profile="current_default",
        authored_by="tester",
        candidate_assertions=[_assertion()],
    )


def _sealed_package(**overrides):
    assertion = _assertion()
    package = seal_promote_proposal(
        world_id="eldyrwild",
        parent_revision_id="rev:parent",
        source_revision_id="sha256:abc",
        source_artifact_id="artifact:a",
        candidate_preview_id="preview:test",
        candidate_schema="dmb_candidate_graph_preview_v0",
        candidate_version="0.1",
        accepted_proposals=[assertion],
        rejected_assertions=[],
        unresolved_mentions=[],
        node_id_map={"obj_session22_vial": "obj:vial"},
        identity_outcome_snapshot={"obj_session22_vial": "created_new"},
        prepared_by="gm@test",
        contribution_candidate=_contribution(),
        proposal_id="proposal:test-1",
    )
    package.update(overrides)
    return package


def test_seal_requires_prepared_by() -> None:
    with pytest.raises(PromoteProposalError, match="prepared_by"):
        seal_promote_proposal(
            world_id="eldyrwild",
            parent_revision_id="rev:parent",
            source_revision_id="sha256:abc",
            source_artifact_id="artifact:a",
            candidate_preview_id="preview:test",
            candidate_schema="dmb_candidate_graph_preview_v0",
            candidate_version="0.1",
            accepted_proposals=[_assertion()],
            rejected_assertions=[],
            unresolved_mentions=[],
            node_id_map={},
            identity_outcome_snapshot={},
            prepared_by="",
            contribution_candidate=_contribution(),
        )


def test_verify_rejects_modified_effect() -> None:
    package = _sealed_package()
    package["effect"]["accepted_proposals"][0]["label"] = "tampered"
    with pytest.raises(PromoteProposalError, match="proposal_digest mismatch"):
        verify_promote_proposal(package, confirming_principal="gm@confirm")


def test_verify_rejects_parent_mismatch() -> None:
    package = _sealed_package()
    with pytest.raises(PromoteProposalError, match="parent_revision_id mismatch"):
        verify_promote_proposal(
            package,
            confirming_principal="gm@confirm",
            expected_parent_revision_id="rev:other",
        )


def test_verify_rejects_missing_principal() -> None:
    package = _sealed_package()
    with pytest.raises(PromoteProposalError, match="confirming_principal"):
        verify_promote_proposal(package, confirming_principal="")


def test_verify_rejects_unknown_selection() -> None:
    package = _sealed_package()
    with pytest.raises(PromoteProposalError, match="not in sealed"):
        verify_promote_proposal(
            package,
            confirming_principal="gm@confirm",
            expected_parent_revision_id="rev:parent",
            selected_assertion_ids=["assertion:does-not-exist"],
        )


def test_verify_happy_path() -> None:
    package = _sealed_package()
    verified = verify_promote_proposal(
        package,
        confirming_principal="gm@confirm",
        expected_parent_revision_id="rev:parent",
    )
    assert verified["proposal_id"] == "proposal:test-1"
    assert verified["proposal_digest"] == package["proposal_digest"]
    assert verified["confirming_principal"] == "gm@confirm"
    # Digest is stable for same effect body.
    again = compute_proposal_digest(package["effect"])
    assert again == package["proposal_digest"]
