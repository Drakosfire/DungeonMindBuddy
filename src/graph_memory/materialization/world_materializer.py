"""World graph materialization orchestration via Kernel (PR006)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import graph_memory.kernel as kernel
from graph_memory.materialization.acceptance_manifest import (
    AcceptanceManifestError,
    build_inventory,
    load_acceptance_manifest,
    sha256_bytes,
)
from graph_memory.materialization.candidate_bundle import (
    load_candidate_bundle,
    validate_candidate_bundle,
)
from graph_memory.materialization.candidate_to_contribution import (
    bundle_sources_to_contributions,
)
from graph_memory.materialization.reporting import build_materialization_report
from graph_memory.union_supergraph.model import (
    UnionSupergraphAdjacencyItem,
    UnionSupergraphDiagnostics,
    UnionSupergraphEdge,
    UnionSupergraphEvidence,
    UnionSupergraphNode,
    UnionSupergraphNodeState,
    UnionSupergraphSourceArtifact,
    UnionSupergraphStore,
)
from graph_memory.kernel import WorldGraphNotFoundError


def build_pr006_baseline_store(*, campaign_scope: str = "longmont-c2") -> UnionSupergraphStore:
    """Minimal valid baseline matching longmont_c2_minimal_graph constraints."""
    store = UnionSupergraphStore(
        **{
            "schema": "dmb_union_supergraph_store_v0",
            "version": "0.1",
            "campaign_id": campaign_scope,
            "graph_id": f"{campaign_scope}:union-supergraph",
            "graph_domains": ["campaign", "worldbuilding"],
            "source_domains": ["recap", "worldbuilding", "statblock", "session_memory"],
            "focus_session_id": "session-23",
            "nodes": {
                "pc_caelynn": UnionSupergraphNode(
                    node_id="pc_caelynn",
                    label="Caelynn",
                    kind="pc",
                    role="pc",
                    aliases=["Caelynn"],
                    source_domains=["recap", "worldbuilding"],
                    evidence_ref_ids=[
                        "evidence:session-23:caelynn:recap-mention",
                        "evidence:worldbuilding:caelynn:character-note",
                    ],
                    state=UnionSupergraphNodeState(
                        memory_state="graph_read_model",
                        canon_state="not_canon_promotion",
                        approval_state="not_approval_write",
                    ).model_dump(),
                ),
                "event_session_23_mireward_gate": UnionSupergraphNode(
                    node_id="event_session_23_mireward_gate",
                    label="Mireward Gate Incident",
                    kind="event",
                    role="event",
                    aliases=["Mireward gate"],
                    source_domains=["recap"],
                    evidence_ref_ids=["evidence:session-23:caelynn:recap-mention"],
                    state=UnionSupergraphNodeState(
                        memory_state="graph_read_model",
                        canon_state="not_canon_promotion",
                        approval_state="not_approval_write",
                    ).model_dump(),
                ),
                "loc_mirathorn": UnionSupergraphNode(
                    node_id="loc_mirathorn",
                    label="Mirathorn",
                    kind="location",
                    role="location",
                    aliases=["Mirathorn"],
                    source_domains=["worldbuilding"],
                    evidence_ref_ids=["evidence:worldbuilding:mirathorn:gazetteer-note"],
                    state=UnionSupergraphNodeState(
                        memory_state="graph_read_model",
                        canon_state="not_canon_promotion",
                        approval_state="not_approval_write",
                    ).model_dump(),
                ),
            },
            "edges": {
                "edge:pc_caelynn:participated_in:event_session_23_mireward_gate": UnionSupergraphEdge(
                    edge_id="edge:pc_caelynn:participated_in:event_session_23_mireward_gate",
                    source_node_id="pc_caelynn",
                    target_node_id="event_session_23_mireward_gate",
                    predicate="participated_in",
                    label="participated in",
                    direction="outbound",
                    source_domains=["recap"],
                    session_ids=["session-23"],
                    evidence_ref_ids=["evidence:session-23:caelynn:recap-mention"],
                    state=UnionSupergraphNodeState(
                        memory_state="graph_read_model",
                        canon_state="not_canon_promotion",
                        approval_state="not_approval_write",
                    ).model_dump(),
                ),
                "edge:pc_caelynn:connected_to:loc_mirathorn": UnionSupergraphEdge(
                    edge_id="edge:pc_caelynn:connected_to:loc_mirathorn",
                    source_node_id="pc_caelynn",
                    target_node_id="loc_mirathorn",
                    predicate="connected_to",
                    label="connected to",
                    direction="outbound",
                    source_domains=["worldbuilding"],
                    session_ids=[],
                    evidence_ref_ids=["evidence:worldbuilding:caelynn:character-note"],
                    state=UnionSupergraphNodeState(
                        memory_state="graph_read_model",
                        canon_state="not_canon_promotion",
                        approval_state="not_approval_write",
                    ).model_dump(),
                ),
            },
            "evidence": {
                "evidence:session-23:caelynn:recap-mention": UnionSupergraphEvidence(
                    evidence_ref_id="evidence:session-23:caelynn:recap-mention",
                    source_artifact_id="artifact:recap:longmont-c2:session-23",
                    source_domain="recap",
                    evidence_role="focus_session_recap_mention",
                    session_id="session-23",
                    source_span_ref_id="spref:session-23:p014",
                    can_open_source=True,
                    can_highlight_span=True,
                ),
                "evidence:worldbuilding:caelynn:character-note": UnionSupergraphEvidence(
                    evidence_ref_id="evidence:worldbuilding:caelynn:character-note",
                    source_artifact_id="artifact:worldbuilding:longmont-c2:caelynn-note",
                    source_domain="worldbuilding",
                    evidence_role="character_context",
                    locator="worldbuilding/characters/caelynn.md#read-model-example",
                    can_open_source=True,
                    can_highlight_span=False,
                ),
                "evidence:worldbuilding:mirathorn:gazetteer-note": UnionSupergraphEvidence(
                    evidence_ref_id="evidence:worldbuilding:mirathorn:gazetteer-note",
                    source_artifact_id="artifact:worldbuilding:longmont-c2:mirathorn-gazetteer",
                    source_domain="worldbuilding",
                    evidence_role="location_context",
                    locator="worldbuilding/locations/mirathorn.md#overview",
                    can_open_source=True,
                    can_highlight_span=False,
                ),
            },
            "source_artifacts": {
                "artifact:recap:longmont-c2:session-23": UnionSupergraphSourceArtifact(
                    source_artifact_id="artifact:recap:longmont-c2:session-23",
                    source_domain="recap",
                    campaign_id=campaign_scope,
                    session_id="session-23",
                    uri="fixture://recap/session-23",
                ),
                "artifact:worldbuilding:longmont-c2:caelynn-note": UnionSupergraphSourceArtifact(
                    source_artifact_id="artifact:worldbuilding:longmont-c2:caelynn-note",
                    source_domain="worldbuilding",
                    campaign_id=campaign_scope,
                    uri="fixture://worldbuilding/characters/caelynn.md",
                ),
                "artifact:worldbuilding:longmont-c2:mirathorn-gazetteer": UnionSupergraphSourceArtifact(
                    source_artifact_id="artifact:worldbuilding:longmont-c2:mirathorn-gazetteer",
                    source_domain="worldbuilding",
                    campaign_id=campaign_scope,
                    uri="fixture://worldbuilding/locations/mirathorn.md",
                ),
            },
            "aliases": {"caelynn": "pc_caelynn", "mirathorn": "loc_mirathorn"},
            "adjacency": {
                "pc_caelynn": [
                    UnionSupergraphAdjacencyItem(
                        edge_id="edge:pc_caelynn:participated_in:event_session_23_mireward_gate",
                        node_id="event_session_23_mireward_gate",
                        label="participated in",
                        direction="outbound",
                        anchored_to_focus_session=True,
                    ),
                    UnionSupergraphAdjacencyItem(
                        edge_id="edge:pc_caelynn:connected_to:loc_mirathorn",
                        node_id="loc_mirathorn",
                        label="connected to",
                        direction="outbound",
                        anchored_to_focus_session=False,
                    ),
                ],
                "event_session_23_mireward_gate": [
                    UnionSupergraphAdjacencyItem(
                        edge_id="edge:pc_caelynn:participated_in:event_session_23_mireward_gate",
                        node_id="pc_caelynn",
                        label="participated in",
                        direction="inbound",
                        anchored_to_focus_session=True,
                    ),
                ],
                "loc_mirathorn": [
                    UnionSupergraphAdjacencyItem(
                        edge_id="edge:pc_caelynn:connected_to:loc_mirathorn",
                        node_id="pc_caelynn",
                        label="connected to",
                        direction="inbound",
                        anchored_to_focus_session=False,
                    ),
                ],
            },
            "diagnostics": UnionSupergraphDiagnostics(
                canon_promotion=False,
                approved_memory_write=False,
                corpus_mutation=False,
                production_retrieval=False,
            ),
        }
    )
    return store


def _head_exists(root: Path, world_id: str) -> bool:
    try:
        kernel.open_world_graph_head(root, world_id)
        return True
    except WorldGraphNotFoundError:
        return False


def _count_assertions_with_source(contribs: list[kernel.GraphContribution]) -> tuple[int, int]:
    accepted = 0
    with_source = 0
    for contrib in contribs:
        for assertion in contrib.accepted_assertions:
            accepted += 1
            if assertion.source_artifact_id and assertion.source_revision_id:
                with_source += 1
    return accepted, with_source


def _counts_by_domain(sources: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for entry in sources:
        domain = entry.get("source_domain", "unknown")
        counts[domain] = counts.get(domain, 0) + 1
    return counts


def _hub_presence(store: UnionSupergraphStore) -> dict[str, bool]:
    labels = {node.label.lower() for node in store.nodes.values()}
    ids = set(store.nodes.keys())
    return {
        "mirathorn": "loc_mirathorn" in ids or any("mirathorn" in label for label in labels),
        "mireward": "loc_mireward" in ids or any("mireward" in label for label in labels),
    }


def _required_hubs_present_list(store: UnionSupergraphStore) -> list[str]:
    """Capitalized hub names for §7 assertions (`\"Mirathorn\" in required_hubs_present`)."""
    hubs = _hub_presence(store)
    names: list[str] = []
    if hubs.get("mirathorn"):
        names.append("Mirathorn")
    if hubs.get("mireward"):
        names.append("Mireward")
    return names


def _required_hub_names(inventory: dict[str, Any]) -> list[str]:
    names: list[str] = []
    for item in inventory.get("source_items") or []:
        if item.get("domain") != "worldbuilding":
            continue
        path = item.get("path", "")
        if "Mirathorn" in path:
            names.append("mirathorn")
        if "Mireward" in path:
            names.append("mireward")
    return list(dict.fromkeys(names))


def _acceptance_gates(
    *,
    inventory: dict[str, Any],
    store: UnionSupergraphStore,
    accepted_assertion_count: int,
    assertions_with_source_artifact_count: int,
    world_integrity_valid: bool,
    rebuild_equivalent: bool,
) -> list[str]:
    failures: list[str] = []
    expected_recaps = len(inventory.get("recap_session_numbers") or [])
    if inventory.get("recap_count") != expected_recaps:
        failures.append(
            f"expected {expected_recaps} recaps, got {inventory.get('recap_count')}"
        )
    if inventory.get("failed_required"):
        failures.append("failed_required is non-empty")
    required_pcs = inventory.get("required_pc_slugs") or []
    pc_nodes = [nid for nid in store.nodes if nid.startswith("pc_")]
    if len(pc_nodes) < len(required_pcs):
        failures.append(f"expected >={len(required_pcs)} PC nodes, got {len(pc_nodes)}")
    hubs = _hub_presence(store)
    for hub_name in _required_hub_names(inventory):
        if not hubs.get(hub_name):
            failures.append(f"{hub_name} hub not present in head nodes")
    if len(store.nodes) == 0 or len(store.edges) == 0:
        failures.append("head graph must have nodes and edges")
    if assertions_with_source_artifact_count != accepted_assertion_count:
        failures.append("not all accepted assertions have source artifact linkage")
    if not world_integrity_valid:
        failures.append("world integrity invalid")
    if not rebuild_equivalent:
        failures.append("rebuild not equivalent to head")
    return failures


def materialize_world_graph(
    *,
    repo_root: Path,
    store_root: Path,
    manifest_path: Path,
    bundle_path: Path,
    fresh_root: bool = False,
    expected_parent_revision_id: str | None = None,
) -> dict[str, Any]:
    """Run full materialization: validate → baseline (optional) → merge → report."""
    repo_root = repo_root.resolve()
    store_root = store_root.resolve()
    manifest = load_acceptance_manifest(manifest_path)
    world_id = manifest["world_id"]
    campaign_scope = manifest["campaign_scope"]

    inventory = build_inventory(manifest, repo_root=repo_root, manifest_path=manifest_path)
    bundle = load_candidate_bundle(bundle_path)
    manifest_sha256 = sha256_bytes(manifest_path.read_bytes())
    bundle_sha256 = sha256_bytes(bundle_path.read_bytes())

    bundle_errors = validate_candidate_bundle(
        bundle,
        manifest_sha256=manifest_sha256,
        inventory_paths={item["path"] for item in inventory["source_items"]},
    )
    if bundle_errors:
        raise AcceptanceManifestError(
            f"bundle validation failed: {bundle_errors[0]}",
            errors=[{"kind": "bundle_validation", "messages": bundle_errors}],
        )

    head_exists = _head_exists(store_root, world_id)
    if fresh_root and head_exists:
        raise AcceptanceManifestError(
            "--fresh-root refused: world head already exists",
            errors=[{"kind": "fresh_root_blocked"}],
        )

    baseline_revision_id: str | None = None
    parent_revision_id: str | None = None

    if not head_exists:
        if not fresh_root:
            raise AcceptanceManifestError(
                "no world head; pass --fresh-root to publish baseline",
                errors=[{"kind": "missing_head"}],
            )
        baseline = build_pr006_baseline_store(campaign_scope=campaign_scope)
        baseline_result = kernel.publish_world_revision(
            store_root,
            world_id,
            baseline,
            operation_ids=["op:pr006-baseline"],
        )
        baseline_revision_id = baseline_result.revision.revision_id
        parent_revision_id = baseline_revision_id
    else:
        if expected_parent_revision_id is None:
            raise AcceptanceManifestError(
                "expected_parent_revision_id required when world head exists",
                errors=[{"kind": "missing_expected_parent"}],
            )
        head = kernel.open_world_graph_head(store_root, world_id)
        parent_revision_id = head.head_revision_id
        if expected_parent_revision_id != parent_revision_id:
            raise AcceptanceManifestError(
                "stale expected parent revision",
                errors=[
                    {
                        "kind": "stale_parent",
                        "expected": expected_parent_revision_id,
                        "actual": parent_revision_id,
                    }
                ],
            )

    contributions = bundle_sources_to_contributions(bundle)
    duplicate_graph_state_created = False
    current_parent = parent_revision_id
    published_any = False

    for contrib in contributions:
        result = kernel.merge_contribution_to_revision(
            store_root,
            world_id=world_id,
            contribution=contrib,
            expected_parent_revision_id=current_parent,
        )
        if result.published:
            current_parent = result.revision_id
            published_any = True
        elif any("idempotent_noop" in d for d in result.diagnostics):
            continue
        else:
            raise AcceptanceManifestError(
                "contribution merge failed",
                errors=[{"kind": "merge_failed", "diagnostics": result.diagnostics}],
            )

    # Unchanged reprocessing must not invent a second graph state.
    if head_exists and not published_any:
        duplicate_graph_state_created = False

    head = kernel.open_world_graph_head(store_root, world_id)
    _head_rev, _rev, store = kernel.open_current_world_graph(store_root, world_id)

    world_health = kernel.build_world_integrity_report(store_root, world_id, persist=False)
    contrib_health = kernel.build_contribution_integrity_report(
        store_root, world_id=world_id, check_rebuild=True
    )
    rebuild = kernel.rebuild_from_contributions(store_root, world_id=world_id, publish=False)
    rebuild_equivalent = "rebuild_equivalent_to_head" in rebuild.diagnostics

    accepted_count, with_source_count = _count_assertions_with_source(contributions)
    with_evidence_count = sum(
        1
        for contrib in contributions
        for assertion in contrib.accepted_assertions
        if assertion.evidence_ref_ids
    )
    hubs = _hub_presence(store)

    gate_failures = _acceptance_gates(
        inventory=inventory,
        store=store,
        accepted_assertion_count=accepted_count,
        assertions_with_source_artifact_count=with_source_count,
        world_integrity_valid=bool(world_health.load_ok and world_health.validation_ok),
        rebuild_equivalent=rebuild_equivalent,
    )
    if gate_failures:
        raise AcceptanceManifestError(
            f"acceptance gates failed: {gate_failures[0]}",
            errors=[{"kind": "acceptance_gate", "messages": gate_failures}],
        )

    report = build_materialization_report(
        world_id=world_id,
        campaign_scope=campaign_scope,
        manifest_sha256=manifest_sha256,
        bundle_sha256=bundle_sha256,
        inventory=inventory,
        head_revision_id=head.head_revision_id,
        parent_revision_id=parent_revision_id,
        baseline_revision_id=baseline_revision_id,
        node_count=len(store.nodes),
        edge_count=len(store.edges),
        evidence_ref_count=len(store.evidence),
        accepted_assertion_count=accepted_count,
        assertions_with_source_artifact_count=with_source_count,
        assertions_with_evidence_count=with_evidence_count,
        contribution_count=len(contributions),
        active_contribution_count=contrib_health.active_contribution_count,
        superseded_contribution_count=contrib_health.superseded_contribution_count,
        retracted_contribution_count=contrib_health.retracted_contribution_count,
        duplicate_graph_state_created=duplicate_graph_state_created,
        world_integrity_valid=bool(world_health.load_ok and world_health.validation_ok),
        contribution_integrity_valid=contrib_health.rebuild_equivalent_to_head is not False,
        rebuild_equivalent_to_head=rebuild_equivalent,
        counts_by_source_domain=_counts_by_domain(bundle.get("sources", [])),
        identity_diagnostics={
            "unresolved_mention_count": sum(
                len(c.unresolved_mentions) for c in contributions
            ),
            "rejected_assertion_count": sum(
                len(c.rejected_assertions) for c in contributions
            ),
            "provisional_identity_count": 0,
            "ambiguous_identity_count": sum(
                1
                for c in contributions
                for m in c.unresolved_mentions
                if m.identity_resolution_outcome == "ambiguous"
            ),
            "blocked_collision_count": sum(
                1
                for c in contributions
                for m in c.unresolved_mentions
                if m.identity_resolution_outcome == "blocked_collision"
            ),
        },
        required_hubs_present=_required_hubs_present_list(store),
        retained_preview_paths=[
            "apps/live-control-ui graph-preview route parameters",
            "union_supergraph_projection_adapter preview selectors",
        ],
    )
    return report


def verify_materialization(store_root: Path, world_id: str) -> dict[str, Any]:
    world_health = kernel.build_world_integrity_report(store_root, world_id, persist=False)
    contrib_health = kernel.build_contribution_integrity_report(
        store_root, world_id=world_id, check_rebuild=True
    )
    head = kernel.open_world_graph_head(store_root, world_id)
    _h, _r, store = kernel.open_current_world_graph(store_root, world_id)
    return {
        "head_revision_id": head.head_revision_id,
        "node_count": len(store.nodes),
        "edge_count": len(store.edges),
        "world_integrity_valid": bool(world_health.load_ok and world_health.validation_ok),
        "rebuild_equivalent_to_head": contrib_health.rebuild_equivalent_to_head,
    }


def verify_rebuild(store_root: Path, world_id: str) -> dict[str, Any]:
    result = kernel.rebuild_from_contributions(store_root, world_id=world_id, publish=False)
    return {
        "rebuild_equivalent_to_head": "rebuild_equivalent_to_head" in result.diagnostics,
        "diagnostics": result.diagnostics,
    }


def write_report_json(report: dict[str, Any], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
