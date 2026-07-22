"""Session-6 shape: duplicate Lysandra extract ids must not refuse merge."""

from __future__ import annotations

from pathlib import Path

import graph_memory.kernel as kernel
from graph_memory.candidate_graph_preview import (
    CANDIDATE_GRAPH_PREVIEW_SCHEMA,
    CANDIDATE_GRAPH_PREVIEW_VERSION,
    candidate_graph_preview_from_dict,
)
from graph_memory.extract_identity_gate import (
    _collapse_duplicate_extract_nodes,
    build_accepted_contribution_from_proposals,
    gate_candidate_graph_against_head,
)
from graph_memory.union_supergraph.load import (
    DEFAULT_FIXTURE_PATH,
    load_union_supergraph_store,
)


WORLD_ID = "eldyrwild"
CAMPAIGN_ID = "longmont-c1"


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
        "source_artifact_id": "artifact:recap:longmont-c1:session-6",
        "source_anchor_id": f"anchor:{suffix}",
        "label": "span",
        "evidence_role": "source_evidence",
        "can_open_source": True,
        "can_highlight_span": True,
        "source_span_ref_id": f"session-6:recap:paragraph:{suffix}",
        "anchor_quotes": ["Captain Lysandra Ironveil"],
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


def _seed_lysandra_world(root: Path) -> None:
    fixture_store = load_union_supergraph_store(DEFAULT_FIXTURE_PATH)
    kernel.publish_world_revision(
        root,
        WORLD_ID,
        fixture_store,
        operation_ids=["op:baseline-seed"],
    )
    contribution = kernel.create_graph_contribution(
        world_id=WORLD_ID,
        source_kind="manual_import",
        source_artifact_id="artifact:seed:lysandra",
        source_revision_id="rev:seed-lysandra",
        campaign_scope="longmont-c2",
        authored_by="test",
        accepted_assertions=[
            kernel.build_assertion(
                assertion_kind="node",
                subject_node_id="npc_lysandra",
                label="Lysandra",
                value={
                    "kind": "npc",
                    "role": "npc",
                    "aliases": ["Lysandra"],
                    "summary": "Allied tactical leader.",
                    "canon_state": "canonical",
                    "source_domains": ["manual_seed"],
                },
                acceptance_state="accepted",
                identity_resolution_outcome="created_new",
                campaign_scope="longmont-c2",
                epistemic_kind="fact",
                visibility="gm",
            )
        ],
    )
    merged = kernel.merge_contribution_to_revision(
        root, world_id=WORLD_ID, contribution=contribution
    )
    assert merged.published is True


def test_collapse_duplicate_extract_nodes_prefers_actor() -> None:
    preview = candidate_graph_preview_from_dict(
        {
            "schema": CANDIDATE_GRAPH_PREVIEW_SCHEMA,
            "version": CANDIDATE_GRAPH_PREVIEW_VERSION,
            "preview_id": "preview:lysandra-dup",
            "session_id": "session-6",
            "campaign_id": CAMPAIGN_ID,
            "source_artifact_ids": ["artifact:recap:longmont-c1:session-6"],
            "status": "preview",
            "nodes": [
                _node(
                    "node:captain_lysandra_ironveil",
                    "Captain Lysandra Ironveil",
                    "organization",
                    "006",
                    "Mis-typed collective",
                ),
                _node(
                    "node:captain_lysandra_ironveil",
                    "Captain Lysandra Ironveil",
                    "character",
                    "006",
                    "Captain of the guards",
                ),
            ],
            "edges": [],
            "beats": [],
            "proposed_writes": [],
            "ignored_items": [],
            "deferred_items": [],
            "diagnostics": _diagnostics(),
        }
    )
    kept, dropped = _collapse_duplicate_extract_nodes(preview.nodes)
    assert len(kept) == 1
    assert kept[0].node_type == "character"
    assert len(dropped) == 1
    assert dropped[0].node_type == "organization"


def test_gate_attaches_creature_bubbles_when_extract_retargets_as_npc(
    tmp_path: Path,
) -> None:
    """S6 shape: existing creature node:bubbles must not get a competing npc assert."""
    fixture_store = load_union_supergraph_store(DEFAULT_FIXTURE_PATH)
    kernel.publish_world_revision(
        tmp_path,
        WORLD_ID,
        fixture_store,
        operation_ids=["op:baseline-seed"],
    )
    seed = kernel.create_graph_contribution(
        world_id=WORLD_ID,
        source_kind="manual_import",
        source_artifact_id="artifact:seed:bubbles",
        source_revision_id="rev:seed-bubbles",
        campaign_scope=CAMPAIGN_ID,
        authored_by="test",
        accepted_assertions=[
            kernel.build_assertion(
                assertion_kind="node",
                subject_node_id="node:bubbles",
                label="Bubbles the Float Goat",
                value={
                    "kind": "creature",
                    "role": "creature",
                    "aliases": ["Bubbles the Float Goat"],
                    "summary": "Float goat rescued during the flood.",
                    "canon_state": "canonical",
                    "source_domains": ["manual_seed"],
                },
                acceptance_state="accepted",
                identity_resolution_outcome="created_new",
                campaign_scope=CAMPAIGN_ID,
                epistemic_kind="fact",
                visibility="gm",
            )
        ],
    )
    assert kernel.merge_contribution_to_revision(
        tmp_path, world_id=WORLD_ID, contribution=seed
    ).published

    preview = candidate_graph_preview_from_dict(
        {
            "schema": CANDIDATE_GRAPH_PREVIEW_SCHEMA,
            "version": CANDIDATE_GRAPH_PREVIEW_VERSION,
            "preview_id": "preview:bubbles-retarget",
            "session_id": "session-6",
            "campaign_id": CAMPAIGN_ID,
            "source_artifact_ids": ["artifact:recap:longmont-c1:session-6"],
            "status": "preview",
            "nodes": [
                _node(
                    "node:bubbles",
                    "Bubbles",
                    "character",
                    "005",
                    "A named individual in Outtown",
                ),
            ],
            "edges": [],
            "beats": [],
            "proposed_writes": [],
            "ignored_items": [],
            "deferred_items": [],
            "diagnostics": _diagnostics(),
        }
    )
    gate = gate_candidate_graph_against_head(
        preview,
        root=tmp_path,
        world_id=WORLD_ID,
        source_revision_id="rev:s6-bubbles",
        campaign_scope=CAMPAIGN_ID,
        source_domain="recap",
        source_uri="normalized_recap_source.md",
    )
    assert gate.identity_outcome_snapshot["node:bubbles"] == "resolved_existing"
    assert gate.node_id_map["node:bubbles"] == "node:bubbles"
    assert not any(
        a.assertion_kind == "node" and a.subject_node_id == "node:bubbles"
        for a in gate.accepted_proposals
    )
    contribution = build_accepted_contribution_from_proposals(
        gate,
        root=tmp_path,
        accepted_assertion_ids=[a.assertion_id for a in gate.accepted_proposals],
    )
    merged = kernel.merge_contribution_to_revision(
        tmp_path, world_id=WORLD_ID, contribution=contribution
    )
    assert merged.published is True
    _head, _rev, store = kernel.open_current_world_graph(tmp_path, WORLD_ID)
    assert store.nodes["node:bubbles"].kind == "creature"


def test_gate_attaches_lysandra_and_drops_org_duplicate(tmp_path: Path) -> None:
    _seed_lysandra_world(tmp_path)

    preview = candidate_graph_preview_from_dict(
        {
            "schema": CANDIDATE_GRAPH_PREVIEW_SCHEMA,
            "version": CANDIDATE_GRAPH_PREVIEW_VERSION,
            "preview_id": "preview:lysandra-dup",
            "session_id": "session-6",
            "campaign_id": CAMPAIGN_ID,
            "source_artifact_ids": ["artifact:recap:longmont-c1:session-6"],
            "status": "preview",
            "nodes": [
                _node(
                    "node:captain_lysandra_ironveil",
                    "Captain Lysandra Ironveil",
                    "character",
                    "006",
                    "Captain of the guards",
                ),
                _node(
                    "node:captain_lysandra_ironveil",
                    "Captain Lysandra Ironveil",
                    "organization",
                    "006",
                    "Mis-typed collective",
                ),
                _node(
                    "loc:mirathorn_gate",
                    "Mirathorn gate",
                    "location",
                    "006",
                    "City gate",
                ),
            ],
            "edges": [
                {
                    "edge_id": "edge_session6_024",
                    "from_node_id": "node:captain_lysandra_ironveil",
                    "to_node_id": "loc:mirathorn_gate",
                    "relationship_type": "controls_comms_with",
                    "label": "may close gate",
                    "semantic_state": _semantic(),
                    "evidence_refs": [_evidence("006")],
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
    )

    gate = gate_candidate_graph_against_head(
        preview,
        root=tmp_path,
        world_id=WORLD_ID,
        source_revision_id="rev:s6-test",
        campaign_scope=CAMPAIGN_ID,
        source_domain="recap",
        source_uri="normalized_recap_source.md",
    )

    assert gate.identity_outcome_snapshot["node:captain_lysandra_ironveil"] == (
        "resolved_existing"
    )
    assert gate.node_id_map["node:captain_lysandra_ironveil"] == "npc_lysandra"
    assert any(
        "duplicate_extract_node_id_dropped:node:captain_lysandra_ironveil:organization"
        in d
        for d in gate.diagnostics
    )
    assert any(
        "connect_existing_support_only:node:captain_lysandra_ironveil->npc_lysandra" in d
        for d in gate.diagnostics
    )

    lysandra_nodes = [
        a
        for a in gate.accepted_proposals
        if a.assertion_kind == "node"
        and a.subject_node_id in {"npc_lysandra", "node:captain_lysandra_ironveil"}
    ]
    assert lysandra_nodes == []

    contribution = build_accepted_contribution_from_proposals(
        gate,
        root=tmp_path,
        accepted_assertion_ids=[a.assertion_id for a in gate.accepted_proposals],
    )
    merged = kernel.merge_contribution_to_revision(
        tmp_path, world_id=WORLD_ID, contribution=contribution
    )
    assert merged.published is True
    _head, _rev, store = kernel.open_current_world_graph(tmp_path, WORLD_ID)
    assert "npc_lysandra" in store.nodes
    assert "node:captain_lysandra_ironveil" not in store.nodes
