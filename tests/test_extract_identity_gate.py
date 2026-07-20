"""Tests for head-pinned extract identity gate."""

from __future__ import annotations

import dataclasses
from pathlib import Path

import pytest

import graph_memory.kernel as kernel
from graph_memory.candidate_graph_preview import (
    CANDIDATE_GRAPH_PREVIEW_SCHEMA,
    CANDIDATE_GRAPH_PREVIEW_VERSION,
    candidate_graph_preview_from_dict,
)
from graph_memory.candidate_graph_to_contribution import CandidateGraphMappingError
from graph_memory.contribution_bundles import load_contribution_bundle
from graph_memory.extract_identity_gate import (
    build_accepted_contribution_from_multi_slice_proposals,
    build_accepted_contribution_from_proposals,
    gate_candidate_graph_against_head,
)
from graph_memory.kernel.world_initialization import initialize_world_from_contributions
from graph_memory.kernel.world_initialization_models import (
    PLAN_SCHEMA,
    WorldInitializationApprovalAttestation,
    WorldInitializationContribution,
    WorldInitializationPlan,
)
from graph_memory.projection.world_projection import (
    PROJECTION_REQUEST_SCHEMA,
    WorldGraphProjectionFocus,
    WorldGraphProjectionRequest,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
BUNDLE_PATH = (
    REPO_ROOT
    / "graph_data/approved_contribution_bundles/eldyrwild-longmont-c2-initial-v1"
)
BUNDLE_DIGEST = (
    "5f8288d3052a9e59192884f2c35a13d51f665095d84cca2081a56638108d3fa5"
)
BUNDLE_ID = "eldyrwild-longmont-c2-initial-v1"
WORLD_ID = "eldyrwild"
CAMPAIGN_ID = "longmont-c2"
FOCUS_SESSION_ID = "session-23"
APPROVED_MERGE_SHA = "65ae001e0852d827ecd680200a965a576c705b1d"
ACTOR = "gm"
ORDERED_CONTRIBUTION_IDS = [
    "contribution:82f23934d8eaca8a",
    "contribution:43782369bd717d32",
    "contribution:33d7cdb0ff623f28",
    "contribution:c086a0b72324ff16",
    "contribution:1227841724520c18",
    "contribution:022187fdefdf4557",
]


@pytest.fixture
def loaded_bundle():
    return load_contribution_bundle(BUNDLE_PATH)


def _plan(bundle) -> WorldInitializationPlan:
    by_id = {item.contribution_id: item for item in bundle.contributions}
    return WorldInitializationPlan(
        schema=PLAN_SCHEMA,
        world_id=WORLD_ID,
        campaign_id=CAMPAIGN_ID,
        focus_session_id=FOCUS_SESSION_ID,
        ordered_contributions=[
            WorldInitializationContribution(
                contribution_id=contribution_id,
                payload_sha256=kernel.compute_contribution_payload_sha256(
                    by_id[contribution_id]
                ),
            )
            for contribution_id in ORDERED_CONTRIBUTION_IDS
        ],
        approval_attestation=WorldInitializationApprovalAttestation(
            bundle_id=BUNDLE_ID,
            bundle_digest=BUNDLE_DIGEST,
            approved_bundle_merge_sha=APPROVED_MERGE_SHA,
        ),
    )


def _initialize(root: Path, bundle):
    return initialize_world_from_contributions(
        root,
        plan=_plan(bundle),
        contributions=list(bundle.contributions),
        actor=ACTOR,
    )


def _semantic() -> dict:
    return {
        "canon_state": "played_canon",
        "lifecycle_state": "candidate",
        "evidence_role": "source_evidence",
        "authority_state": "system_derived",
        "visibility_state": "gm_private",
    }


def _evidence(suffix: str) -> dict:
    return {
        "source_ref_id": f"ref:{suffix}",
        "source_artifact_id": "artifact:recap:longmont-c2:session-22",
        "source_anchor_id": f"anchor:{suffix}",
        "label": "span",
        "evidence_role": "source_evidence",
        "can_open_source": True,
        "can_highlight_span": True,
        "source_span_ref_id": f"session-22:recap:paragraph:{suffix}",
        "anchor_quotes": ["quote"],
    }


def _diagnostics() -> dict:
    return {
        "preview_only": True,
        "extraction_performed": False,
        "llm_used": False,
        "runtime_connected": False,
        "plan_connected": False,
        "agent_interaction_connected": False,
        "corpus_scanned": False,
        "corpus_mutated": False,
        "facts_promoted": False,
        "canon_promoted": False,
        "unresolved_evidence_refs": 0,
        "missing_evidence_objects": 0,
        "warning_count": 0,
    }


def _node(node_id: str, label: str, node_type: str, suffix: str, description: str) -> dict:
    return {
        "node_id": node_id,
        "label": label,
        "node_type": node_type,
        "description": description,
        "importance": "medium",
        "semantic_state": _semantic(),
        "evidence_refs": [_evidence(suffix)],
        "proposed_action": "create",
        "confidence": "medium",
        "warnings": [],
    }


def _candidate_graph() -> dict:
    return {
        "schema": CANDIDATE_GRAPH_PREVIEW_SCHEMA,
        "version": CANDIDATE_GRAPH_PREVIEW_VERSION,
        "preview_id": "preview:test-identity-gate",
        "session_id": "session-22",
        "campaign_id": "longmont-c2",
        "source_artifact_ids": ["artifact:recap:longmont-c2:session-22"],
        "status": "preview",
        "nodes": [
            _node("node:caelynn", "Caelynn", "character", "001", "PC"),
            _node("loc_mireward", "Mireward", "location", "002", "Town"),
            _node("obj_session22_vial", "vial", "item", "006", "Puddle sample vial"),
            _node("mystery_puddles", "Magic puddles", "mystery", "007", "Delayed reflections"),
        ],
        "edges": [
            {
                "edge_id": "e33",
                "from_node_id": "obj_session22_vial",
                "to_node_id": "mystery_puddles",
                "relationship_type": "linked_to",
                "label": "linked to",
                "semantic_state": _semantic(),
                "evidence_refs": [_evidence("007")],
                "proposed_action": "create",
                "confidence": "medium",
                "warnings": [],
            }
        ],
        "beats": [],
        "proposed_writes": [],
        "ignored_items": [],
        "deferred_items": [],
        "diagnostics": _diagnostics(),
    }


def test_identity_gate_attaches_existing_and_creates_new(
    tmp_path: Path, loaded_bundle
) -> None:
    _initialize(tmp_path, loaded_bundle)
    preview = candidate_graph_preview_from_dict(_candidate_graph())
    gate = gate_candidate_graph_against_head(
        preview,
        root=tmp_path,
        world_id=WORLD_ID,
        source_revision_id="sha256:testdigest001",
    )
    assert gate.parent_revision_id.startswith("rev:")
    assert gate.node_id_map["node:caelynn"] == "pc:caelynn"
    assert gate.node_id_map["loc_mireward"] == "location:mireward"
    assert gate.node_id_map["obj_session22_vial"]
    assert gate.node_id_map["mystery_puddles"]
    assert gate.identity_outcome_snapshot["node:caelynn"] == "resolved_existing"

    outcomes = {
        a.subject_node_id: a.identity_resolution_outcome
        for a in gate.accepted_proposals
        if a.assertion_kind == "node"
    }
    # resolved_existing connects map durable ids but do not emit competing node asserts
    assert "pc:caelynn" not in outcomes
    assert "location:mireward" not in outcomes
    assert outcomes[gate.node_id_map["obj_session22_vial"]] == "created_new"
    assert any(
        d.startswith("connect_existing_support_only:node:caelynn->pc:caelynn")
        for d in gate.diagnostics
    )

    # Support-only assertions replace the skipped node assert: an attribute
    # observation (non-destructive) for the durable resolved-existing node.
    caelynn_attributes = [
        a
        for a in gate.accepted_proposals
        if a.assertion_kind == "attribute" and a.subject_node_id == "pc:caelynn"
    ]
    assert len(caelynn_attributes) == 1
    assert caelynn_attributes[0].identity_resolution_outcome == "resolved_existing"
    assert caelynn_attributes[0].value.get("evidence")
    assert caelynn_attributes[0].value.get("source_artifacts")
    assert not any(
        a.subject_node_id == "pc:caelynn" and a.assertion_kind == "alias"
        for a in gate.accepted_proposals
    )

    edge_proposals = [
        a for a in gate.accepted_proposals if a.assertion_kind == "edge"
    ]
    assert len(edge_proposals) == 1
    assert edge_proposals[0].subject_node_id == gate.node_id_map["obj_session22_vial"]
    assert edge_proposals[0].target_node_id == gate.node_id_map["mystery_puddles"]
    assert gate.scorer_report["matched"]
    assert "unresolved_ambiguity" in gate.scorer_report


def test_ambiguous_identity_parks_unresolved(tmp_path: Path, loaded_bundle) -> None:
    _initialize(tmp_path, loaded_bundle)
    graph = {
        "schema": CANDIDATE_GRAPH_PREVIEW_SCHEMA,
        "version": CANDIDATE_GRAPH_PREVIEW_VERSION,
        "preview_id": "preview:test-collision",
        "session_id": "session-22",
        "campaign_id": "longmont-c2",
        "source_artifact_ids": ["artifact:recap:longmont-c2:session-22"],
        "status": "preview",
        "nodes": [
            _node("item_named_caelynn", "Caelynn", "item", "001", "Wrong kind"),
        ],
        "edges": [],
        "beats": [],
        "proposed_writes": [],
        "ignored_items": [],
        "deferred_items": [],
        "diagnostics": _diagnostics(),
    }
    gate = gate_candidate_graph_against_head(
        candidate_graph_preview_from_dict(graph),
        root=tmp_path,
        world_id=WORLD_ID,
        source_revision_id="sha256:testdigest002",
    )
    assert gate.accepted_proposals == []
    assert len(gate.unresolved_mentions) == 1
    assert gate.unresolved_mentions[0].identity_resolution_outcome == "blocked_collision"
    assert "item_named_caelynn" not in gate.node_id_map


def test_partial_edge_selection_rejected(tmp_path: Path, loaded_bundle) -> None:
    _initialize(tmp_path, loaded_bundle)
    gate = gate_candidate_graph_against_head(
        candidate_graph_preview_from_dict(_candidate_graph()),
        root=tmp_path,
        world_id=WORLD_ID,
        source_revision_id="sha256:testdigest004",
        node_ids=["obj_session22_vial", "mystery_puddles"],
    )
    edge = next(a for a in gate.accepted_proposals if a.assertion_kind == "edge")
    vial = next(
        a
        for a in gate.accepted_proposals
        if a.assertion_kind == "node"
        and a.subject_node_id == gate.node_id_map["obj_session22_vial"]
    )
    with pytest.raises(CandidateGraphMappingError, match="target endpoint"):
        build_accepted_contribution_from_proposals(
            gate,
            root=tmp_path,
            accepted_assertion_ids=[vial.assertion_id, edge.assertion_id],
            proposal_digest="digest-a",
        )


def test_edge_only_second_artifact_rejected_by_identity_gate(
    tmp_path: Path, loaded_bundle
) -> None:
    """Node evidence A + edge evidence B must not bypass the single-artifact gate.

    Regression: gate called candidate_graph_to_contribution(include_edges=False)
    then mapped edges without re-checking artifacts.
    """
    _initialize(tmp_path, loaded_bundle)
    payload = _candidate_graph()
    art_a = "artifact:recap:longmont-c2:session-22"
    art_b = "artifact:recap:longmont-c2:session-22-alt"
    # Top-level and node evidence stay on A; only the edge points at B.
    payload["source_artifact_ids"] = [art_a]
    for node in payload["nodes"]:
        for ref in node["evidence_refs"]:
            ref["source_artifact_id"] = art_a
    for edge in payload["edges"]:
        for ref in edge["evidence_refs"]:
            ref["source_artifact_id"] = art_b
    with pytest.raises(CandidateGraphMappingError, match="multi-artifact"):
        gate_candidate_graph_against_head(
            candidate_graph_preview_from_dict(payload),
            root=tmp_path,
            world_id=WORLD_ID,
            source_revision_id="sha256:testdigest-edge-artifact",
            source_artifact_id=art_a,
            node_ids=["obj_session22_vial", "mystery_puddles"],
            include_edges=True,
        )


def test_different_selections_produce_different_contribution_ids(
    tmp_path: Path, loaded_bundle
) -> None:
    _initialize(tmp_path, loaded_bundle)
    gate = gate_candidate_graph_against_head(
        candidate_graph_preview_from_dict(_candidate_graph()),
        root=tmp_path,
        world_id=WORLD_ID,
        source_revision_id="sha256:testdigest005",
        node_ids=["obj_session22_vial", "mystery_puddles"],
        include_edges=False,
    )
    nodes = [a for a in gate.accepted_proposals if a.assertion_kind == "node"]
    assert len(nodes) == 2
    # Same proposal digest — selection_digest must still distinguish subsets.
    same_digest = "digest-same-proposal"
    a_only = build_accepted_contribution_from_proposals(
        gate,
        root=tmp_path,
        accepted_assertion_ids=[nodes[0].assertion_id],
        proposal_digest=same_digest,
    )
    both = build_accepted_contribution_from_proposals(
        gate,
        root=tmp_path,
        accepted_assertion_ids=[nodes[0].assertion_id, nodes[1].assertion_id],
        proposal_digest=same_digest,
    )
    assert a_only.contribution_id != both.contribution_id
    assert any(d.startswith("selection_digest:") for d in a_only.diagnostics)


def test_build_accepted_contribution_and_merge(
    tmp_path: Path, loaded_bundle
) -> None:
    init = _initialize(tmp_path, loaded_bundle)
    parent = init.current_head_revision_id or init.initial_head_revision_id
    assert parent is not None
    gate = gate_candidate_graph_against_head(
        candidate_graph_preview_from_dict(_candidate_graph()),
        root=tmp_path,
        world_id=WORLD_ID,
        source_revision_id="sha256:testdigest003",
        node_ids=["obj_session22_vial", "mystery_puddles"],
    )
    contribution = build_accepted_contribution_from_proposals(
        gate,
        root=tmp_path,
        proposal_digest="digest-merge-test",
    )
    assert contribution.accepted_assertions
    assert all(a.acceptance_state == "accepted" for a in contribution.accepted_assertions)
    result = kernel.merge_contribution_to_revision(
        tmp_path,
        world_id=WORLD_ID,
        contribution=contribution,
        expected_parent_revision_id=parent,
    )
    assert result.published is True
    assert result.revision_id != parent
    rebuild = kernel.rebuild_from_contributions(tmp_path, world_id=WORLD_ID, publish=False)
    assert "rebuild_equivalent_to_head" in rebuild.diagnostics
    store = kernel.open_current_world_graph(tmp_path, WORLD_ID)[2]
    vial_id = gate.node_id_map["obj_session22_vial"]
    mystery_id = gate.node_id_map["mystery_puddles"]
    assert vial_id in store.nodes
    assert mystery_id in store.nodes
    assert "pc:caelynn" in store.nodes


def _projection_request(*, revision_pin: str | None = None) -> WorldGraphProjectionRequest:
    return WorldGraphProjectionRequest(
        schema=PROJECTION_REQUEST_SCHEMA,
        world_id=WORLD_ID,
        campaign_id=CAMPAIGN_ID,
        focus=WorldGraphProjectionFocus(kind="none"),
        admissibility="gm",
        revision_pin=revision_pin,
    )


def test_connect_existing_alias_and_support_survive_publish_and_projection(
    tmp_path: Path, loaded_bundle
) -> None:
    init = _initialize(tmp_path, loaded_bundle)
    parent = init.current_head_revision_id or init.initial_head_revision_id
    assert parent is not None

    graph = _candidate_graph()
    graph["nodes"] = [
        {
            **_node("node:caelynn", "Caelynn", "character", "001", "PC"),
            "aliases": ["Caellynn"],
        }
    ]
    graph["edges"] = []
    gate = gate_candidate_graph_against_head(
        candidate_graph_preview_from_dict(graph),
        root=tmp_path,
        world_id=WORLD_ID,
        source_revision_id="sha256:testdigest-alias-publish",
        node_ids=["node:caelynn"],
        include_edges=False,
    )
    alias_proposals = [
        a
        for a in gate.accepted_proposals
        if a.assertion_kind == "alias" and a.subject_node_id == "pc:caelynn"
    ]
    assert len(alias_proposals) == 1
    assert alias_proposals[0].label == "Caellynn"

    attribute_proposals = [
        a
        for a in gate.accepted_proposals
        if a.assertion_kind == "attribute" and a.subject_node_id == "pc:caelynn"
    ]
    assert len(attribute_proposals) == 1
    assert attribute_proposals[0].value.get("evidence")

    contribution = build_accepted_contribution_from_proposals(
        gate,
        root=tmp_path,
        proposal_digest="digest-alias-publish",
    )
    merged = kernel.merge_contribution_to_revision(
        tmp_path,
        world_id=WORLD_ID,
        contribution=contribution,
        expected_parent_revision_id=parent,
    )
    assert merged.published is True
    published_revision_id = merged.revision_id

    projection = kernel.project_world_graph(
        tmp_path,
        _projection_request(revision_pin=published_revision_id),
    )
    assert projection.snapshot.revision_id == published_revision_id
    caelynn = next(node for node in projection.nodes if node.node_id == "pc:caelynn")
    assert "Caellynn" in caelynn.aliases

    published_attributes = [
        item
        for item in projection.attributes
        if item.subject_node_id == "pc:caelynn"
        and item.predicate == "session_observation"
    ]
    assert published_attributes
    assert published_attributes[0].value.get("evidence")
    assert published_attributes[0].evidence_ref_ids or published_attributes[0].source_artifact_ids


def test_connect_existing_mireward_alias_blocks_collision(
    tmp_path: Path, loaded_bundle
) -> None:
    """Foreign-owned cross-kind alias in IdentityCandidate fails closed at resolve."""
    _initialize(tmp_path, loaded_bundle)
    graph = _candidate_graph()
    graph["nodes"] = [
        {
            **_node("node:caelynn", "Caelynn", "character", "001", "PC"),
            "aliases": ["Mireward"],
        }
    ]
    graph["edges"] = []
    gate = gate_candidate_graph_against_head(
        candidate_graph_preview_from_dict(graph),
        root=tmp_path,
        world_id=WORLD_ID,
        source_revision_id="sha256:testdigest-mireward-collision",
        node_ids=["node:caelynn"],
        include_edges=False,
    )
    assert gate.identity_outcome_snapshot["node:caelynn"] == "blocked_collision"
    assert gate.accepted_proposals == []
    assert len(gate.unresolved_mentions) == 1
    assert not any(
        a.assertion_kind == "alias" and a.label == "Mireward"
        for a in gate.accepted_proposals
    )

SLICE_TWO_ARTIFACT_ID = "artifact:recap:longmont-c2:session-22-slice-two"


def _second_candidate_graph() -> dict:
    """A disjoint candidate graph standing in for a second contribution slice."""
    graph = {
        "schema": CANDIDATE_GRAPH_PREVIEW_SCHEMA,
        "version": CANDIDATE_GRAPH_PREVIEW_VERSION,
        "preview_id": "preview:test-identity-gate-slice-two",
        "session_id": "session-22",
        "campaign_id": "longmont-c2",
        "source_artifact_ids": [SLICE_TWO_ARTIFACT_ID],
        "status": "preview",
        "nodes": [
            _node(
                "node:whisper-charm",
                "Whisper charm",
                "item",
                "101",
                "A second-slice standing-context item",
            ),
            _node(
                "node:charm-origin",
                "Charm's origin",
                "mystery",
                "102",
                "Where the charm came from",
            ),
        ],
        "edges": [
            {
                "edge_id": "e-slice-two",
                "from_node_id": "node:whisper-charm",
                "to_node_id": "node:charm-origin",
                "relationship_type": "linked_to",
                "label": "linked to",
                "semantic_state": _semantic(),
                "evidence_refs": [_evidence("102")],
                "proposed_action": "create",
                "confidence": "medium",
                "warnings": [],
            }
        ],
        "beats": [],
        "proposed_writes": [],
        "ignored_items": [],
        "deferred_items": [],
        "diagnostics": _diagnostics(),
    }
    # Slice B is a disjoint source artifact from slice A's recap; re-point
    # every evidence ref at the slice-two artifact so the single-artifact
    # gate accepts it.
    for node in graph["nodes"]:
        for ref in node["evidence_refs"]:
            ref["source_artifact_id"] = SLICE_TWO_ARTIFACT_ID
    for edge in graph["edges"]:
        for ref in edge["evidence_refs"]:
            ref["source_artifact_id"] = SLICE_TWO_ARTIFACT_ID
    return graph


def _gated_slice_pair(tmp_path: Path):
    """Two independently-gated slices against the same pinned parent head."""
    gate_a = gate_candidate_graph_against_head(
        candidate_graph_preview_from_dict(_candidate_graph()),
        root=tmp_path,
        world_id=WORLD_ID,
        source_revision_id="sha256:testdigest-multislice-a",
        source_uri="/tmp/slice-a-source.md",
        node_ids=["obj_session22_vial", "mystery_puddles"],
    )
    gate_b = gate_candidate_graph_against_head(
        candidate_graph_preview_from_dict(_second_candidate_graph()),
        root=tmp_path,
        world_id=WORLD_ID,
        source_revision_id="sha256:testdigest-multislice-b",
        source_uri="/tmp/slice-b-source.md",
        source_artifact_id=SLICE_TWO_ARTIFACT_ID,
    )
    return gate_a, gate_b


def _multi_slice_args(*entries):
    """Attach sealed contribution_slice_id coordinates for multi-slice builds."""
    out = []
    for index, entry in enumerate(entries):
        if len(entry) == 3:
            out.append(entry)
            continue
        gate, ids = entry
        kind = gate.contribution.source_kind or "source_extraction"
        out.append((gate, ids, f"{index}:{kind}"))
    return out


def test_multi_slice_contribution_unions_selected_slices_atomically(
    tmp_path: Path, loaded_bundle
) -> None:
    init = _initialize(tmp_path, loaded_bundle)
    parent = init.current_head_revision_id or init.initial_head_revision_id
    gate_a, gate_b = _gated_slice_pair(tmp_path)
    assert gate_a.parent_revision_id == parent
    assert gate_b.parent_revision_id == parent

    contribution = build_accepted_contribution_from_multi_slice_proposals(
        _multi_slice_args((gate_a, None), (gate_b, None)),
        root=tmp_path,
        proposal_digest="digest-multislice",
    )
    accepted_subjects = {
        a.subject_node_id for a in contribution.accepted_assertions if a.assertion_kind == "node"
    }
    assert gate_a.node_id_map["obj_session22_vial"] in accepted_subjects
    assert gate_b.node_id_map["node:whisper-charm"] in accepted_subjects
    assert any(d.startswith("contribution_slices_merged:2") for d in contribution.diagnostics)

    # ONE kernel merge call publishes both slices' assertions together —
    # the head advances exactly once for the whole multi-slice selection.
    result = kernel.merge_contribution_to_revision(
        tmp_path,
        world_id=WORLD_ID,
        contribution=contribution,
        expected_parent_revision_id=parent,
    )
    assert result.published is True
    store = kernel.open_current_world_graph(tmp_path, WORLD_ID)[2]
    assert gate_a.node_id_map["obj_session22_vial"] in store.nodes
    assert gate_b.node_id_map["node:whisper-charm"] in store.nodes


def test_multi_slice_contribution_rejects_bad_edge_before_any_merge(
    tmp_path: Path, loaded_bundle
) -> None:
    """Atomicity (P0): an unresolvable endpoint in ANY slice must raise before
    ``kernel.merge_contribution_to_revision`` is ever called, so the head
    cannot advance partially for the other, otherwise-valid slice.
    """
    init = _initialize(tmp_path, loaded_bundle)
    parent = init.current_head_revision_id or init.initial_head_revision_id
    gate_a, gate_b = _gated_slice_pair(tmp_path)

    # Select only the vial node from slice A's edge (drop its edge partner),
    # so the edge assertion in slice A cannot resolve its target endpoint
    # against either slice's selected subjects or the pinned parent.
    vial = next(
        a
        for a in gate_a.accepted_proposals
        if a.assertion_kind == "node"
        and a.subject_node_id == gate_a.node_id_map["obj_session22_vial"]
    )
    edge_a = next(a for a in gate_a.accepted_proposals if a.assertion_kind == "edge")

    head_before = kernel.open_current_world_graph(tmp_path, WORLD_ID)[0]
    assert head_before.head_revision_id == parent

    with pytest.raises(CandidateGraphMappingError, match="target endpoint"):
        build_accepted_contribution_from_multi_slice_proposals(
            _multi_slice_args(
                (gate_a, [vial.assertion_id, edge_a.assertion_id]),
                (gate_b, None),
            ),
            root=tmp_path,
            proposal_digest="digest-multislice-bad-edge",
        )

    # No mutation of any kind happened — the head is exactly where it was.
    head_after = kernel.open_current_world_graph(tmp_path, WORLD_ID)[0]
    assert head_after.head_revision_id == parent


def test_multi_slice_contribution_retry_after_failure_succeeds(
    tmp_path: Path, loaded_bundle
) -> None:
    """Retry-safe (P0): after a raised build failure, a corrected retry with
    the same gates/parent must succeed with no leftover state from the
    failed attempt.
    """
    init = _initialize(tmp_path, loaded_bundle)
    parent = init.current_head_revision_id or init.initial_head_revision_id
    gate_a, gate_b = _gated_slice_pair(tmp_path)

    vial = next(
        a
        for a in gate_a.accepted_proposals
        if a.assertion_kind == "node"
        and a.subject_node_id == gate_a.node_id_map["obj_session22_vial"]
    )
    edge_a = next(a for a in gate_a.accepted_proposals if a.assertion_kind == "edge")

    with pytest.raises(CandidateGraphMappingError):
        build_accepted_contribution_from_multi_slice_proposals(
            _multi_slice_args(
                (gate_a, [vial.assertion_id, edge_a.assertion_id]),
                (gate_b, None),
            ),
            root=tmp_path,
            proposal_digest="digest-multislice-retry",
        )

    # Retry with the full slice A selection (both endpoints present) succeeds.
    contribution = build_accepted_contribution_from_multi_slice_proposals(
        _multi_slice_args((gate_a, None), (gate_b, None)),
        root=tmp_path,
        proposal_digest="digest-multislice-retry",
    )
    result = kernel.merge_contribution_to_revision(
        tmp_path,
        world_id=WORLD_ID,
        contribution=contribution,
        expected_parent_revision_id=parent,
    )
    assert result.published is True


def test_multi_slice_contribution_requires_shared_parent_and_world(
    tmp_path: Path, loaded_bundle
) -> None:
    _initialize(tmp_path, loaded_bundle)
    gate_a, gate_b = _gated_slice_pair(tmp_path)
    mismatched_b = dataclasses.replace(gate_b, parent_revision_id="rev:other-parent")
    with pytest.raises(CandidateGraphMappingError, match="shared parent"):
        build_accepted_contribution_from_multi_slice_proposals(
            _multi_slice_args((gate_a, None), (mismatched_b, None)),
            root=tmp_path,
            proposal_digest="digest-multislice-mismatch",
        )


def test_multi_slice_contribution_unions_cross_slice_assertion_provenance(
    tmp_path: Path, loaded_bundle
) -> None:
    """Selecting both colliding assertions unions evidence; digests differ."""
    _initialize(tmp_path, loaded_bundle)
    gate_a, gate_b = _gated_slice_pair(tmp_path)
    vial = next(
        a
        for a in gate_a.accepted_proposals
        if a.assertion_kind == "node"
        and a.subject_node_id == gate_a.node_id_map["obj_session22_vial"]
    )
    recap_only_vial = vial.model_copy(
        update={
            "evidence_ref_ids": ["evidence:recap:vial"],
            "source_artifact_id": "artifact:recap-slice",
            "source_revision_id": "sha256:recap-slice",
        }
    )
    standing_vial = vial.model_copy(
        update={
            "evidence_ref_ids": ["evidence:standing:vial"],
            "source_artifact_id": "artifact:standing-slice",
            "source_revision_id": "sha256:standing-slice",
        }
    )
    assert standing_vial.assertion_id == recap_only_vial.assertion_id

    gate_standing = dataclasses.replace(
        gate_a,
        accepted_proposals=[standing_vial],
        contribution=gate_a.contribution.model_copy(
            update={"source_kind": "standing_context"}
        ),
    )
    gate_recap = dataclasses.replace(
        gate_b,
        accepted_proposals=[*gate_b.accepted_proposals, recap_only_vial],
    )

    both = build_accepted_contribution_from_multi_slice_proposals(
        _multi_slice_args((gate_standing, None), (gate_recap, None)),
        root=tmp_path,
        proposal_digest="digest-multislice-both",
    )
    matching = [
        a for a in both.accepted_assertions if a.assertion_id == vial.assertion_id
    ]
    assert len(matching) == 1
    assert set(matching[0].evidence_ref_ids) >= {
        "evidence:standing:vial",
        "evidence:recap:vial",
    }
    assert any(
        d.startswith(f"cross_slice_assertion_provenance_unioned:{vial.assertion_id}")
        for d in both.diagnostics
    )

    recap_only = build_accepted_contribution_from_multi_slice_proposals(
        [
            (
                gate_recap,
                [recap_only_vial.assertion_id],
                "1:source_extraction",
            )
        ],
        root=tmp_path,
        proposal_digest="digest-multislice-recap-only",
    )
    # selection_digest enters contribution_id — both-slices vs recap-only must
    # not collapse to the same durable contribution identity.
    assert both.contribution_id != recap_only.contribution_id
    both_digest = next(
        d.split(":", 1)[1]
        for d in both.diagnostics
        if d.startswith("selection_digest:")
    )
    recap_digest = next(
        d.split(":", 1)[1]
        for d in recap_only.diagnostics
        if d.startswith("selection_digest:")
    )
    assert both_digest != recap_digest
    assert "evidence:standing:vial" not in recap_only.accepted_assertions[0].evidence_ref_ids


def test_multi_slice_orders_earlier_edge_after_later_slice_node(
    tmp_path: Path, loaded_bundle
) -> None:
    """Edge in slice 0 targeting a node created only in slice 1 must reorder."""
    from graph_memory.kernel.contributions import build_assertion

    init = _initialize(tmp_path, loaded_bundle)
    parent = init.current_head_revision_id or init.initial_head_revision_id
    gate_a, gate_b = _gated_slice_pair(tmp_path)

    later_node = next(
        a
        for a in gate_b.accepted_proposals
        if a.assertion_kind == "node"
        and a.subject_node_id == gate_b.node_id_map["node:whisper-charm"]
    )
    vial = next(
        a
        for a in gate_a.accepted_proposals
        if a.assertion_kind == "node"
        and a.subject_node_id == gate_a.node_id_map["obj_session22_vial"]
    )
    early_edge = build_assertion(
        assertion_kind="edge",
        acceptance_state="accepted",
        subject_node_id=vial.subject_node_id,
        target_node_id=later_node.subject_node_id,
        predicate="related_to",
        label="cross-slice order probe",
        value={"source_domains": ["manual_seed"]},
        evidence_ref_ids=[],
        source_artifact_id="artifact:order-probe",
        source_revision_id="sha256:order-probe",
        campaign_scope="longmont-c1",
        epistemic_kind="source_derived_candidate",
        visibility="gm",
        identity_resolution_outcome="created_new",
    )
    gate_early = dataclasses.replace(
        gate_a,
        accepted_proposals=[vial, early_edge],
    )
    gate_later = dataclasses.replace(
        gate_b,
        accepted_proposals=[later_node],
    )

    contribution = build_accepted_contribution_from_multi_slice_proposals(
        _multi_slice_args((gate_early, None), (gate_later, None)),
        root=tmp_path,
        proposal_digest="digest-edge-order",
    )
    kinds = [a.assertion_kind for a in contribution.accepted_assertions]
    assert kinds.index("edge") > max(i for i, k in enumerate(kinds) if k == "node")

    result = kernel.merge_contribution_to_revision(
        tmp_path,
        world_id=WORLD_ID,
        contribution=contribution,
        expected_parent_revision_id=parent,
    )
    assert result.published is True


def test_multi_slice_contribution_deduplicates_identical_cross_slice_assertion(
    tmp_path: Path, loaded_bundle
) -> None:
    """Legacy name retained: collision keeps one body and unions provenance."""
    _initialize(tmp_path, loaded_bundle)
    gate_a, gate_b = _gated_slice_pair(tmp_path)
    vial = next(
        a
        for a in gate_a.accepted_proposals
        if a.assertion_kind == "node"
        and a.subject_node_id == gate_a.node_id_map["obj_session22_vial"]
    )
    # Force a cross-slice collision by re-asserting the exact same accepted
    # proposal object as if slice B had also carried it (content-hashed ids
    # are identical for identical semantic content regardless of source).
    gate_b_with_duplicate = dataclasses.replace(
        gate_b, accepted_proposals=[*gate_b.accepted_proposals, vial]
    )
    contribution = build_accepted_contribution_from_multi_slice_proposals(
        _multi_slice_args((gate_a, None), (gate_b_with_duplicate, None)),
        root=tmp_path,
        proposal_digest="digest-multislice-dup",
    )
    matching = [a for a in contribution.accepted_assertions if a.assertion_id == vial.assertion_id]
    assert len(matching) == 1
    assert any(
        d.startswith(f"cross_slice_assertion_provenance_unioned:{vial.assertion_id}")
        for d in contribution.diagnostics
    )
