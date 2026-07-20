"""Tests for sealed promote proposal digest and verification."""

from __future__ import annotations

import pytest

from graph_memory.extract_promote_proposal import (
    SLICE_SELECTOR_DELIMITER,
    PromoteProposalError,
    build_contribution_effect_slice,
    compute_proposal_digest,
    contribution_meta_from_contribution,
    contribution_slice_id_for,
    contribution_slices_from_effect,
    parse_slice_qualified_selector,
    resolve_slice_qualified_selection,
    seal_multi_contribution_promote_proposal,
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
        campaign_scope="longmont-c2",
        authored_by="tester",
        candidate_assertions=[_assertion()],
    )


def _sealed_package(**overrides):
    contribution = _contribution()
    package = seal_promote_proposal(
        world_id="eldyrwild",
        parent_revision_id="rev:parent",
        source_revision_id="sha256:abc",
        source_artifact_id="artifact:a",
        verified_source_uri="/tmp/source.md",
        candidate_preview_id="preview:test",
        candidate_schema="dmb_candidate_graph_preview_v0",
        candidate_version="0.1",
        contribution_meta=contribution_meta_from_contribution(contribution),
        accepted_proposals=[_assertion()],
        rejected_assertions=[],
        unresolved_mentions=[],
        node_id_map={"obj_session22_vial": "obj:vial"},
        identity_outcome_snapshot={"obj_session22_vial": "created_new"},
        prepared_by="gm@test",
        proposal_id="proposal:test-1",
    )
    package.update(overrides)
    return package


def test_seal_requires_prepared_by() -> None:
    contribution = _contribution()
    with pytest.raises(PromoteProposalError, match="prepared_by"):
        seal_promote_proposal(
            world_id="eldyrwild",
            parent_revision_id="rev:parent",
            source_revision_id="sha256:abc",
            source_artifact_id="artifact:a",
            verified_source_uri="/tmp/source.md",
            candidate_preview_id="preview:test",
            candidate_schema="dmb_candidate_graph_preview_v0",
            candidate_version="0.1",
            contribution_meta=contribution_meta_from_contribution(contribution),
            accepted_proposals=[_assertion()],
            rejected_assertions=[],
            unresolved_mentions=[],
            node_id_map={},
            identity_outcome_snapshot={},
            prepared_by="",
        )


def test_seal_requires_verified_source_uri() -> None:
    contribution = _contribution()
    with pytest.raises(PromoteProposalError, match="verified_source_uri"):
        seal_promote_proposal(
            world_id="eldyrwild",
            parent_revision_id="rev:parent",
            source_revision_id="sha256:abc",
            source_artifact_id="artifact:a",
            verified_source_uri="",
            candidate_preview_id="preview:test",
            candidate_schema="dmb_candidate_graph_preview_v0",
            candidate_version="0.1",
            contribution_meta=contribution_meta_from_contribution(contribution),
            accepted_proposals=[_assertion()],
            rejected_assertions=[],
            unresolved_mentions=[],
            node_id_map={},
            identity_outcome_snapshot={},
            prepared_by="gm@test",
        )


def test_verify_rejects_modified_effect() -> None:
    package = _sealed_package()
    package["effect"]["accepted_proposals"][0]["label"] = "tampered"
    with pytest.raises(PromoteProposalError, match="proposal_digest mismatch"):
        verify_promote_proposal(package, confirming_principal="gm@confirm")


def test_verify_rejects_tampered_contribution_meta() -> None:
    package = _sealed_package()
    package["effect"]["contribution_meta"]["authored_by"] = "attacker"
    with pytest.raises(PromoteProposalError, match="proposal_digest mismatch"):
        verify_promote_proposal(package, confirming_principal="gm@confirm")


def test_verify_rejects_tampered_verified_source_uri() -> None:
    package = _sealed_package()
    package["effect"]["verified_source_uri"] = "/tmp/other.md"
    with pytest.raises(PromoteProposalError, match="proposal_digest mismatch"):
        verify_promote_proposal(package, confirming_principal="gm@confirm")


def test_verify_rejects_contribution_candidate_envelope() -> None:
    package = _sealed_package()
    package["contribution_candidate"] = _contribution().model_dump(mode="json")
    with pytest.raises(PromoteProposalError, match="contribution_candidate"):
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
    assert verified["verified_source_uri"] == "/tmp/source.md"
    assert verified["contribution_meta"]["authored_by"] == "tester"
    # Digest is stable for same effect body.
    again = compute_proposal_digest(package["effect"])
    assert again == package["proposal_digest"]
    # Default single-contribution seal stays on v2 flat effect shape.
    assert package["proposal_version"] == 2
    assert "contributions" not in package["effect"]


def _standing_contribution():
    return create_graph_contribution(
        world_id="eldyrwild",
        source_kind="standing_context",
        source_artifact_id="artifact:party-registry:longmont-c1",
        source_revision_id="sha256:registry",
        extraction_profile="party_registry_standing",
        campaign_scope="longmont-c1",
        authored_by="tester",
        candidate_assertions=[
            build_assertion(
                assertion_kind="node",
                acceptance_state="accepted",
                subject_node_id="node:heroes-party",
                label="Heroes / party",
                value={
                    "kind": "group",
                    "role": "party",
                    "aliases": ["Heroes / party"],
                    "source_domains": ["party_registry"],
                    "canon_state": "canonical",
                    "approval_state": "accepted",
                },
                evidence_ref_ids=["evidence:registry:standing"],
                source_artifact_id="artifact:party-registry:longmont-c1",
                source_revision_id="sha256:registry",
                campaign_scope="longmont-c1",
                epistemic_kind="source_derived_candidate",
                visibility="gm",
                identity_resolution_outcome="created_new",
            )
        ],
    )


def test_v3_multi_contribution_seal_and_v2_backcompat() -> None:
    standing = _standing_contribution()
    recap = _contribution()
    standing_slice = build_contribution_effect_slice(
        source_revision_id="sha256:registry",
        source_artifact_id="artifact:party-registry:longmont-c1",
        verified_source_uri="repo://corpus/_party_registry.json",
        candidate_preview_id="preview:standing",
        candidate_schema="dmb_candidate_graph_preview_v0",
        candidate_version="0.1",
        contribution_meta=contribution_meta_from_contribution(standing),
        accepted_proposals=list(standing.candidate_assertions),
        rejected_assertions=[],
        unresolved_mentions=[],
        node_id_map={},
        identity_outcome_snapshot={},
    )
    recap_slice = build_contribution_effect_slice(
        source_revision_id="sha256:abc",
        source_artifact_id="artifact:a",
        verified_source_uri="/tmp/source.md",
        candidate_preview_id="preview:recap",
        candidate_schema="dmb_candidate_graph_preview_v0",
        candidate_version="0.1",
        contribution_meta=contribution_meta_from_contribution(recap),
        accepted_proposals=[_assertion()],
        rejected_assertions=[],
        unresolved_mentions=[],
        node_id_map={"obj_session22_vial": "obj:vial"},
        identity_outcome_snapshot={"obj_session22_vial": "created_new"},
    )
    package = seal_multi_contribution_promote_proposal(
        world_id="eldyrwild",
        parent_revision_id="rev:parent",
        contribution_slices=[standing_slice, recap_slice],
        prepared_by="gm@test",
        proposal_id="proposal:v3-dual",
    )
    assert package["proposal_version"] == 3
    slices = contribution_slices_from_effect(package["effect"])
    assert len(slices) == 2
    kinds = [s["contribution_meta"]["source_kind"] for s in slices]
    assert kinds == ["standing_context", "source_extraction"]
    verified = verify_promote_proposal(
        package,
        confirming_principal="gm@confirm",
        expected_parent_revision_id="rev:parent",
    )
    assert verified["proposal_digest"] == package["proposal_digest"]
    assert verified["verified_source_uri"] == "/tmp/source.md"

    # v2 packages still verify via one-element normalization.
    v2 = _sealed_package()
    assert v2["proposal_version"] == 2
    v2_verified = verify_promote_proposal(
        v2,
        confirming_principal="gm@confirm",
        expected_parent_revision_id="rev:parent",
    )
    assert len(contribution_slices_from_effect(v2["effect"])) == 1
    assert v2_verified["contribution_meta"]["source_kind"] == "source_extraction"


def _colliding_slices() -> list[dict]:
    """Two independently-sourced slices that assert the identical node fact.

    ``compute_assertion_id`` hashes only semantic fields (kind/subject/value/
    scope/...), never provenance (evidence_ref_ids, source_artifact_id), so a
    standing_context registry slice and a recap source_extraction slice that
    both re-assert the same durable fact legitimately produce the SAME
    ``assertion_id`` — this is the exact P1 collision the review flagged.
    """
    shared_kwargs = dict(
        assertion_kind="node",
        acceptance_state="accepted",
        subject_node_id="node:heroes-party",
        label="Heroes / party",
        value={
            "kind": "group",
            "role": "party",
            "aliases": ["Heroes / party"],
            "source_domains": ["party_registry"],
            "canon_state": "canonical",
            "approval_state": "accepted",
        },
        campaign_scope="longmont-c1",
        epistemic_kind="source_derived_candidate",
        visibility="gm",
        identity_resolution_outcome="created_new",
    )
    standing_assertion = build_assertion(
        **shared_kwargs,
        evidence_ref_ids=["evidence:registry:standing"],
        source_artifact_id="artifact:party-registry:longmont-c1",
        source_revision_id="sha256:registry",
    )
    recap_assertion = build_assertion(
        **shared_kwargs,
        evidence_ref_ids=["evidence:recap:session22"],
        source_artifact_id="artifact:a",
        source_revision_id="sha256:abc",
    )
    assert standing_assertion.assertion_id == recap_assertion.assertion_id

    standing_contribution = create_graph_contribution(
        world_id="eldyrwild",
        source_kind="standing_context",
        source_artifact_id="artifact:party-registry:longmont-c1",
        source_revision_id="sha256:registry",
        extraction_profile="party_registry_standing",
        campaign_scope="longmont-c1",
        authored_by="tester",
        candidate_assertions=[standing_assertion],
    )
    recap_contribution = create_graph_contribution(
        world_id="eldyrwild",
        source_kind="source_extraction",
        source_artifact_id="artifact:a",
        source_revision_id="sha256:abc",
        extraction_profile="current_default",
        campaign_scope="longmont-c1",
        authored_by="tester",
        candidate_assertions=[recap_assertion],
    )
    standing_slice = build_contribution_effect_slice(
        source_revision_id="sha256:registry",
        source_artifact_id="artifact:party-registry:longmont-c1",
        verified_source_uri="repo://corpus/_party_registry.json",
        candidate_preview_id="preview:standing",
        candidate_schema="dmb_candidate_graph_preview_v0",
        candidate_version="0.1",
        contribution_meta=contribution_meta_from_contribution(standing_contribution),
        accepted_proposals=[standing_assertion],
        rejected_assertions=[],
        unresolved_mentions=[],
        node_id_map={},
        identity_outcome_snapshot={},
    )
    recap_slice = build_contribution_effect_slice(
        source_revision_id="sha256:abc",
        source_artifact_id="artifact:a",
        verified_source_uri="/tmp/source.md",
        candidate_preview_id="preview:recap",
        candidate_schema="dmb_candidate_graph_preview_v0",
        candidate_version="0.1",
        contribution_meta=contribution_meta_from_contribution(recap_contribution),
        accepted_proposals=[recap_assertion],
        rejected_assertions=[],
        unresolved_mentions=[],
        node_id_map={},
        identity_outcome_snapshot={},
    )
    return [standing_slice, recap_slice]


def test_parse_slice_qualified_selector_roundtrip_and_malformed() -> None:
    assert parse_slice_qualified_selector("assertion:abc") == (None, "assertion:abc")
    slice_id, assertion_id = parse_slice_qualified_selector(
        f"0:standing_context{SLICE_SELECTOR_DELIMITER}assertion:abc"
    )
    assert slice_id == "0:standing_context"
    assert assertion_id == "assertion:abc"
    with pytest.raises(PromoteProposalError, match="malformed"):
        parse_slice_qualified_selector(f"0:standing_context{SLICE_SELECTOR_DELIMITER}")


def test_resolve_slice_qualified_selection_bare_id_unique_across_slices() -> None:
    standing = _standing_contribution()
    recap = _contribution()
    standing_slice = build_contribution_effect_slice(
        source_revision_id="sha256:registry",
        source_artifact_id="artifact:party-registry:longmont-c1",
        verified_source_uri="repo://corpus/_party_registry.json",
        candidate_preview_id="preview:standing",
        candidate_schema="dmb_candidate_graph_preview_v0",
        candidate_version="0.1",
        contribution_meta=contribution_meta_from_contribution(standing),
        accepted_proposals=list(standing.candidate_assertions),
        rejected_assertions=[],
        unresolved_mentions=[],
        node_id_map={},
        identity_outcome_snapshot={},
    )
    recap_slice = build_contribution_effect_slice(
        source_revision_id="sha256:abc",
        source_artifact_id="artifact:a",
        verified_source_uri="/tmp/source.md",
        candidate_preview_id="preview:recap",
        candidate_schema="dmb_candidate_graph_preview_v0",
        candidate_version="0.1",
        contribution_meta=contribution_meta_from_contribution(recap),
        accepted_proposals=[_assertion()],
        rejected_assertions=[],
        unresolved_mentions=[],
        node_id_map={},
        identity_outcome_snapshot={},
    )
    slices = [standing_slice, recap_slice]
    recap_assertion_id = recap_slice["accepted_proposals"][0]["assertion_id"]
    resolved = resolve_slice_qualified_selection(slices, [recap_assertion_id])
    recap_slice_id = contribution_slice_id_for(1, recap_slice)
    assert resolved == {recap_slice_id: {recap_assertion_id}}


def test_resolve_slice_qualified_selection_ambiguous_bare_id_raises() -> None:
    slices = _colliding_slices()
    shared_id = slices[0]["accepted_proposals"][0]["assertion_id"]
    with pytest.raises(PromoteProposalError, match="ambiguous"):
        resolve_slice_qualified_selection(slices, [shared_id])


def test_resolve_slice_qualified_selection_qualified_selector_disambiguates() -> None:
    slices = _colliding_slices()
    shared_id = slices[0]["accepted_proposals"][0]["assertion_id"]
    standing_slice_id = contribution_slice_id_for(0, slices[0])
    recap_slice_id = contribution_slice_id_for(1, slices[1])
    assert standing_slice_id != recap_slice_id

    only_standing = resolve_slice_qualified_selection(
        slices, [f"{standing_slice_id}{SLICE_SELECTOR_DELIMITER}{shared_id}"]
    )
    assert only_standing == {standing_slice_id: {shared_id}}

    only_recap = resolve_slice_qualified_selection(
        slices, [f"{recap_slice_id}{SLICE_SELECTOR_DELIMITER}{shared_id}"]
    )
    assert only_recap == {recap_slice_id: {shared_id}}

    both = resolve_slice_qualified_selection(
        slices,
        [
            f"{standing_slice_id}{SLICE_SELECTOR_DELIMITER}{shared_id}",
            f"{recap_slice_id}{SLICE_SELECTOR_DELIMITER}{shared_id}",
        ],
    )
    assert both == {standing_slice_id: {shared_id}, recap_slice_id: {shared_id}}


def test_resolve_slice_qualified_selection_unknown_qualified_slice_raises() -> None:
    slices = _colliding_slices()
    shared_id = slices[0]["accepted_proposals"][0]["assertion_id"]
    with pytest.raises(PromoteProposalError, match="not in sealed contribution slices"):
        resolve_slice_qualified_selection(
            slices, [f"9:unknown{SLICE_SELECTOR_DELIMITER}{shared_id}"]
        )


def test_verify_promote_proposal_with_qualified_selector_on_multi_slice_package() -> None:
    slices = _colliding_slices()
    package = seal_multi_contribution_promote_proposal(
        world_id="eldyrwild",
        parent_revision_id="rev:parent",
        contribution_slices=slices,
        prepared_by="gm@test",
        proposal_id="proposal:collision-1",
    )
    shared_id = slices[0]["accepted_proposals"][0]["assertion_id"]
    standing_slice_id = contribution_slice_id_for(0, slices[0])
    verified = verify_promote_proposal(
        package,
        confirming_principal="gm@confirm",
        expected_parent_revision_id="rev:parent",
        selected_assertion_ids=[
            f"{standing_slice_id}{SLICE_SELECTOR_DELIMITER}{shared_id}"
        ],
    )
    assert verified["resolved_selection"] == {standing_slice_id: {shared_id}}

    # A bare (unqualified) selector is refused for this package since both
    # slices carry the identical assertion_id.
    with pytest.raises(PromoteProposalError, match="ambiguous"):
        verify_promote_proposal(
            package,
            confirming_principal="gm@confirm",
            expected_parent_revision_id="rev:parent",
            selected_assertion_ids=[shared_id],
        )
