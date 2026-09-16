"""Exact durable edge-id continuity against sealed parent relationships."""

from __future__ import annotations

import hashlib
from pathlib import Path

from apps.live_control_server.models.world_graph_mutation_context import (
    MutationObject,
    MutationRelationship,
    WorldGraphMutationContext,
    classify_edge_against_parent,
    durable_relationship_id,
)
from graph_memory.candidate_graph_preview import (
    CANDIDATE_GRAPH_PREVIEW_SCHEMA,
    CANDIDATE_GRAPH_PREVIEW_VERSION,
    candidate_graph_preview_from_dict,
)
from graph_memory.extract_identity_gate import gate_candidate_graph_against_head


def _context(
    *,
    objects: list[MutationObject],
    relationships: list[MutationRelationship] | None = None,
) -> WorldGraphMutationContext:
    return WorldGraphMutationContext(
        world_id="dogfood-world",
        revision_id="rev:parent",
        head_revision_id="rev:parent",
        objects={obj.object_id: obj for obj in objects},
        relationships={
            rel.relationship_id: rel for rel in (relationships or [])
        },
    )


def test_durable_relationship_id_matches_write_path_form() -> None:
    assert (
        durable_relationship_id(
            source_object_id="node:torbin",
            buddy_predicate="located_in",
            target_object_id="loc:hempholm",
        )
        == "edge:node:torbin:located_in:loc:hempholm"
    )


def test_compatible_occupied_edge_confirms_existing() -> None:
    """Dogfood witness: parent already holds dnd5e:located_in Torbin→Hempholm."""
    rid = "edge:node:torbin:located_in:loc:hempholm"
    context = _context(
        objects=[
            MutationObject(object_id="node:torbin", label="Torbin", kind="npc"),
            MutationObject(object_id="loc:hempholm", label="Hempholm", kind="location"),
        ],
        relationships=[
            MutationRelationship(
                relationship_id=rid,
                source_object_id="node:torbin",
                target_object_id="loc:hempholm",
                predicate="dnd5e:located_in",
            )
        ],
    )
    assert (
        classify_edge_against_parent(
            context,
            relationship_id=rid,
            source_object_id="node:torbin",
            target_object_id="loc:hempholm",
            buddy_predicate="located_in",
        )
        == "resolved_existing"
    )


def test_free_edge_id_is_created_new() -> None:
    context = _context(
        objects=[
            MutationObject(object_id="node:torbin", label="Torbin", kind="npc"),
            MutationObject(object_id="loc:hempholm", label="Hempholm", kind="location"),
        ]
    )
    assert (
        classify_edge_against_parent(
            context,
            relationship_id="edge:node:torbin:located_in:loc:hempholm",
            source_object_id="node:torbin",
            target_object_id="loc:hempholm",
            buddy_predicate="located_in",
        )
        == "created_new"
    )


def test_incompatible_endpoints_block_create_into_occupied_id() -> None:
    rid = "edge:node:torbin:located_in:loc:hempholm"
    context = _context(
        objects=[
            MutationObject(object_id="node:torbin", label="Torbin", kind="npc"),
            MutationObject(object_id="loc:hempholm", label="Hempholm", kind="location"),
            MutationObject(object_id="loc:other", label="Other", kind="location"),
        ],
        relationships=[
            MutationRelationship(
                relationship_id=rid,
                source_object_id="node:torbin",
                target_object_id="loc:hempholm",
                predicate="dnd5e:located_in",
            )
        ],
    )
    assert (
        classify_edge_against_parent(
            context,
            relationship_id=rid,
            source_object_id="node:torbin",
            target_object_id="loc:other",
            buddy_predicate="located_in",
        )
        == "blocked_collision"
    )


def test_incompatible_predicate_block_create_into_occupied_id() -> None:
    rid = "edge:node:torbin:located_in:loc:hempholm"
    context = _context(
        objects=[
            MutationObject(object_id="node:torbin", label="Torbin", kind="npc"),
            MutationObject(object_id="loc:hempholm", label="Hempholm", kind="location"),
        ],
        relationships=[
            MutationRelationship(
                relationship_id=rid,
                source_object_id="node:torbin",
                target_object_id="loc:hempholm",
                predicate="dnd5e:allied_with",
            )
        ],
    )
    assert (
        classify_edge_against_parent(
            context,
            relationship_id=rid,
            source_object_id="node:torbin",
            target_object_id="loc:hempholm",
            buddy_predicate="located_in",
        )
        == "blocked_collision"
    )


def test_belongs_to_repeat_confirms_after_reverse_endpoint_publication() -> None:
    """Review Cycle 1: belongs_to publishes as reversed dnd5e:owns.

    Candidate A belongs_to B seals durable id edge:A:belongs_to:B, but the write
    qualifier stores parent endpoints as B→A with predicate dnd5e:owns. A later
    identical candidate must confirm existing, not false-collide.
    """
    member = "node:torbin"
    group = "node:city_council"
    rid = durable_relationship_id(
        source_object_id=member,
        buddy_predicate="belongs_to",
        target_object_id=group,
    )
    assert rid == "edge:node:torbin:belongs_to:node:city_council"
    context = _context(
        objects=[
            MutationObject(object_id=member, label="Torbin", kind="npc"),
            MutationObject(object_id=group, label="City Council", kind="party"),
        ],
        relationships=[
            MutationRelationship(
                relationship_id=rid,
                # Published orientation after reverse_endpoints=True.
                source_object_id=group,
                target_object_id=member,
                predicate="dnd5e:owns",
            )
        ],
    )
    assert (
        classify_edge_against_parent(
            context,
            relationship_id=rid,
            source_object_id=member,
            target_object_id=group,
            buddy_predicate="belongs_to",
        )
        == "resolved_existing"
    )


def test_belongs_to_still_blocks_when_published_endpoints_disagree() -> None:
    member = "node:torbin"
    group = "node:city_council"
    other = "node:other_guild"
    rid = durable_relationship_id(
        source_object_id=member,
        buddy_predicate="belongs_to",
        target_object_id=group,
    )
    context = _context(
        objects=[
            MutationObject(object_id=member, label="Torbin", kind="npc"),
            MutationObject(object_id=group, label="City Council", kind="party"),
            MutationObject(object_id=other, label="Other Guild", kind="party"),
        ],
        relationships=[
            MutationRelationship(
                relationship_id=rid,
                source_object_id=other,
                target_object_id=member,
                predicate="dnd5e:owns",
            )
        ],
    )
    assert (
        classify_edge_against_parent(
            context,
            relationship_id=rid,
            source_object_id=member,
            target_object_id=group,
            buddy_predicate="belongs_to",
        )
        == "blocked_collision"
    )


def _preview_node(
    artifact_id: str,
    *,
    node_id: str,
    label: str,
    node_type: str,
) -> dict[str, object]:
    return {
        "node_id": node_id,
        "label": label,
        "node_type": node_type,
        "description": f"{label}.",
        "importance": "low",
        "aliases": [],
        "semantic_state": {
            "canon_state": "played_canon",
            "lifecycle_state": "candidate",
            "evidence_role": "source_evidence",
            "authority_state": "system_derived",
            "visibility_state": "gm_private",
        },
        "evidence_refs": [
            {
                "source_ref_id": f"ref:{node_id}",
                "source_artifact_id": artifact_id,
                "source_anchor_id": f"anchor:{node_id}",
                "label": "span",
                "evidence_role": "source_evidence",
                "can_open_source": True,
                "can_highlight_span": True,
                "source_span_ref_id": f"{artifact_id}:span:{node_id}",
                "anchor_quotes": [label],
            }
        ],
        "proposed_action": "create",
        "confidence": "medium",
        "warnings": [],
    }


def _preview_edge(
    artifact_id: str,
    *,
    edge_id: str,
    from_node_id: str,
    to_node_id: str,
    relationship_type: str,
) -> dict[str, object]:
    return {
        "edge_id": edge_id,
        "from_node_id": from_node_id,
        "to_node_id": to_node_id,
        "label": relationship_type,
        "relationship_type": relationship_type,
        "semantic_state": {
            "canon_state": "played_canon",
            "lifecycle_state": "candidate",
            "evidence_role": "source_evidence",
            "authority_state": "system_derived",
            "visibility_state": "gm_private",
        },
        "evidence_refs": [
            {
                "source_ref_id": f"ref:{edge_id}",
                "source_artifact_id": artifact_id,
                "source_anchor_id": f"anchor:{edge_id}",
                "label": "span",
                "evidence_role": "source_evidence",
                "can_open_source": True,
                "can_highlight_span": True,
                "source_span_ref_id": f"{artifact_id}:span:{edge_id}",
                "anchor_quotes": [relationship_type],
            }
        ],
        "proposed_action": "create",
        "confidence": "medium",
        "warnings": [],
    }


def test_identity_gate_omits_compatible_existing_edge(
    tmp_path: Path,
) -> None:
    rid = "edge:node:torbin:located_in:loc:hempholm"
    context = _context(
        objects=[
            MutationObject(object_id="node:torbin", label="Torbin", kind="npc"),
            MutationObject(object_id="loc:hempholm", label="Hempholm", kind="location"),
        ],
        relationships=[
            MutationRelationship(
                relationship_id=rid,
                source_object_id="node:torbin",
                target_object_id="loc:hempholm",
                predicate="dnd5e:located_in",
            )
        ],
    )
    source = tmp_path / "recap.md"
    source.write_text("Torbin is in Hempholm.\n")
    source_revision = "sha256:" + hashlib.sha256(source.read_bytes()).hexdigest()
    artifact_id = "artifact:recap:dogfood:edge-continuity"
    graph = {
        "schema": CANDIDATE_GRAPH_PREVIEW_SCHEMA,
        "version": CANDIDATE_GRAPH_PREVIEW_VERSION,
        "preview_id": "preview:edge-continuity",
        "session_id": "session-6",
        "campaign_id": "longmont-c1",
        "source_artifact_ids": [artifact_id],
        "status": "preview",
        "nodes": [
            _preview_node(
                artifact_id,
                node_id="node:torbin",
                label="Torbin",
                node_type="npc",
            ),
            _preview_node(
                artifact_id,
                node_id="loc:hempholm",
                label="Hempholm",
                node_type="location",
            ),
        ],
        "edges": [
            _preview_edge(
                artifact_id,
                edge_id="candidate:edge:torbin-hempholm",
                from_node_id="node:torbin",
                to_node_id="loc:hempholm",
                relationship_type="located_in",
            )
        ],
        "beats": [],
        "proposed_writes": [],
        "ignored_items": [],
        "deferred_items": [],
        "diagnostics": {
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
        },
    }
    gate = gate_candidate_graph_against_head(
        candidate_graph_preview_from_dict(graph),
        mutation_context=context,
        world_id=context.world_id,
        source_artifact_id=artifact_id,
        source_revision_id=source_revision,
        source_uri=str(source),
        source_kind="source_extraction",
        source_domain="recap",
        campaign_scope="longmont-c1",
    )
    edge_assertions = [
        a for a in gate.accepted_proposals if a.assertion_kind == "edge"
    ]
    assert edge_assertions == []
    assert gate.identity_outcome_snapshot.get(rid) == "resolved_existing"
    assert any(
        d.startswith(f"confirm_existing_edge:{rid}") for d in gate.diagnostics
    )


def test_identity_gate_omits_belongs_to_after_reverse_endpoint_publication(
    tmp_path: Path,
) -> None:
    member = "node:torbin"
    group = "node:city_council"
    rid = durable_relationship_id(
        source_object_id=member,
        buddy_predicate="belongs_to",
        target_object_id=group,
    )
    context = _context(
        objects=[
            MutationObject(object_id=member, label="Torbin", kind="npc"),
            MutationObject(object_id=group, label="City Council", kind="party"),
        ],
        relationships=[
            MutationRelationship(
                relationship_id=rid,
                source_object_id=group,
                target_object_id=member,
                predicate="dnd5e:owns",
            )
        ],
    )
    source = tmp_path / "recap.md"
    source.write_text("Torbin belongs to the city council.\n")
    source_revision = "sha256:" + hashlib.sha256(source.read_bytes()).hexdigest()
    artifact_id = "artifact:recap:dogfood:belongs-to-continuity"
    graph = {
        "schema": CANDIDATE_GRAPH_PREVIEW_SCHEMA,
        "version": CANDIDATE_GRAPH_PREVIEW_VERSION,
        "preview_id": "preview:belongs-to-continuity",
        "session_id": "session-6",
        "campaign_id": "longmont-c1",
        "source_artifact_ids": [artifact_id],
        "status": "preview",
        "nodes": [
            _preview_node(
                artifact_id,
                node_id=member,
                label="Torbin",
                node_type="npc",
            ),
            _preview_node(
                artifact_id,
                node_id=group,
                label="City Council",
                node_type="party",
            ),
        ],
        "edges": [
            _preview_edge(
                artifact_id,
                edge_id="candidate:edge:torbin-belongs-council",
                from_node_id=member,
                to_node_id=group,
                relationship_type="belongs_to",
            )
        ],
        "beats": [],
        "proposed_writes": [],
        "ignored_items": [],
        "deferred_items": [],
        "diagnostics": {
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
        },
    }
    gate = gate_candidate_graph_against_head(
        candidate_graph_preview_from_dict(graph),
        mutation_context=context,
        world_id=context.world_id,
        source_artifact_id=artifact_id,
        source_revision_id=source_revision,
        source_uri=str(source),
        source_kind="source_extraction",
        source_domain="recap",
        campaign_scope="longmont-c1",
    )
    assert all(a.assertion_kind != "edge" for a in gate.accepted_proposals)
    assert gate.identity_outcome_snapshot.get(rid) == "resolved_existing"
    assert any(d.startswith(f"confirm_existing_edge:{rid}") for d in gate.diagnostics)


def test_identity_gate_rejects_incompatible_occupied_edge(
    tmp_path: Path,
) -> None:
    rid = "edge:node:torbin:located_in:loc:hempholm"
    context = _context(
        objects=[
            MutationObject(object_id="node:torbin", label="Torbin", kind="npc"),
            MutationObject(object_id="loc:hempholm", label="Hempholm", kind="location"),
            MutationObject(object_id="loc:other", label="Other", kind="location"),
        ],
        relationships=[
            MutationRelationship(
                relationship_id=rid,
                source_object_id="node:torbin",
                target_object_id="loc:hempholm",
                predicate="dnd5e:located_in",
            )
        ],
    )
    source = tmp_path / "recap.md"
    source.write_text("Torbin relocates.\n")
    source_revision = "sha256:" + hashlib.sha256(source.read_bytes()).hexdigest()
    artifact_id = "artifact:recap:dogfood:edge-collision"
    graph = {
        "schema": CANDIDATE_GRAPH_PREVIEW_SCHEMA,
        "version": CANDIDATE_GRAPH_PREVIEW_VERSION,
        "preview_id": "preview:edge-collision",
        "session_id": "session-6",
        "campaign_id": "longmont-c1",
        "source_artifact_ids": [artifact_id],
        "status": "preview",
        "nodes": [
            _preview_node(
                artifact_id,
                node_id="node:torbin",
                label="Torbin",
                node_type="npc",
            ),
            _preview_node(
                artifact_id,
                node_id="loc:other",
                label="Other",
                node_type="location",
            ),
        ],
        "edges": [
            _preview_edge(
                artifact_id,
                edge_id="candidate:edge:torbin-other",
                from_node_id="node:torbin",
                to_node_id="loc:other",
                relationship_type="located_in",
            )
        ],
        "beats": [],
        "proposed_writes": [],
        "ignored_items": [],
        "deferred_items": [],
        "diagnostics": {
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
        },
    }
    # Force the durable id to collide while endpoints differ: the write path
    # always derives edge:{subject}:{predicate}:{target}, so an incompatible
    # collision requires the candidate endpoints to produce that same id while
    # disagreeing with the parent — which is impossible for same predicate.
    # Cover the gate by classifying a crafted conflicting id via parent facts
    # that share the computed durable id for these endpoints but disagree.
    # Here endpoints differ, so durable id differs → created_new unless we
    # occupy that computed id with incompatible parent facts.
    conflicting_id = durable_relationship_id(
        source_object_id="node:torbin",
        buddy_predicate="located_in",
        target_object_id="loc:other",
    )
    context = _context(
        objects=list(context.objects.values()),
        relationships=[
            MutationRelationship(
                relationship_id=conflicting_id,
                source_object_id="node:torbin",
                target_object_id="loc:hempholm",
                predicate="dnd5e:located_in",
            )
        ],
    )
    gate = gate_candidate_graph_against_head(
        candidate_graph_preview_from_dict(graph),
        mutation_context=context,
        world_id=context.world_id,
        source_artifact_id=artifact_id,
        source_revision_id=source_revision,
        source_uri=str(source),
        source_kind="source_extraction",
        source_domain="recap",
        campaign_scope="longmont-c1",
    )
    assert all(a.assertion_kind != "edge" for a in gate.accepted_proposals)
    rejected_edges = [
        a for a in gate.rejected_assertions if a.assertion_kind == "edge"
    ]
    assert len(rejected_edges) == 1
    assert rejected_edges[0].identity_resolution_outcome == "blocked_collision"
    assert gate.identity_outcome_snapshot.get(conflicting_id) == "blocked_collision"
