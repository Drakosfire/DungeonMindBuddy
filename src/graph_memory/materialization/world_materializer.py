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
    resolve_contribution_identities,
)
from graph_memory.materialization.reporting import build_materialization_report
from graph_memory.union_supergraph.model import (
    UnionSupergraphDiagnostics,
    UnionSupergraphStore,
)


def _focus_session_id(inventory: dict[str, Any]) -> str:
    sessions = inventory.get("recap_session_numbers") or []
    if not sessions:
        return "session-23"
    return f"session-{max(sessions)}"


def _empty_union_store(*, campaign_scope: str, focus_session_id: str) -> UnionSupergraphStore:
    """Structural empty store: no corpus assertions (nodes/edges/evidence)."""
    return UnionSupergraphStore(
        **{
            "schema": "dmb_union_supergraph_store_v0",
            "version": "0.1",
            "campaign_id": campaign_scope,
            "graph_id": f"{campaign_scope}:union-supergraph",
            "graph_domains": ["campaign", "worldbuilding"],
            "source_domains": ["recap", "worldbuilding", "statblock", "session_memory", "npc_note"],
            "focus_session_id": focus_session_id,
            "nodes": {},
            "edges": {},
            "evidence": {},
            "source_artifacts": {},
            "aliases": {},
            "adjacency": {},
            "assertion_support": {},
            "diagnostics": UnionSupergraphDiagnostics(
                canon_promotion=False,
                approved_memory_write=False,
                corpus_mutation=False,
                production_retrieval=False,
            ),
        }
    )


def _local_graph_fingerprint(store: UnionSupergraphStore) -> str:
    """Idempotency fingerprint from a publicly loaded store (no private Kernel imports)."""
    payload = store.model_dump(mode="json", by_alias=True)
    focused = {
        "nodes": payload.get("nodes", {}),
        "edges": payload.get("edges", {}),
        "aliases": payload.get("aliases", {}),
        "assertion_support": payload.get("assertion_support", {}),
        "evidence": payload.get("evidence", {}),
        "source_artifacts": payload.get("source_artifacts", {}),
    }
    return json.dumps(focused, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _head_exists(root: Path, world_id: str) -> bool:
    try:
        kernel.open_world_graph_head(root, world_id)
        return True
    except kernel.WorldGraphNotFoundError:
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


def _counts_by_domain(
    sources: list[dict[str, Any]],
    *,
    status: str | None = None,
) -> dict[str, int]:
    counts: dict[str, int] = {}
    for entry in sources:
        if status is not None and entry.get("status") != status:
            continue
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
        if item.get("domain") != "worldbuilding" or not item.get("required"):
            continue
        path = item.get("path", "")
        if path.endswith("/Mirathorn/README.md"):
            names.append("mirathorn")
        if path.endswith("/Mireward/README.md"):
            names.append("mireward")
    return list(dict.fromkeys(names))


def _store_has_fixture_uris(store: UnionSupergraphStore) -> list[str]:
    bad: list[str] = []
    for artifact in store.source_artifacts.values():
        uri = str(artifact.uri or "")
        if uri.startswith("fixture://"):
            bad.append(uri)
    for evidence in store.evidence.values():
        for field in ("uri", "locator", "source_locator"):
            value = getattr(evidence, field, None)
            if isinstance(value, str) and value.startswith("fixture://"):
                bad.append(value)
    return bad


def _accepted_recap_count(bundle: dict[str, Any]) -> int:
    return sum(
        1
        for entry in bundle.get("sources", [])
        if entry.get("source_domain") == "recap"
        and entry.get("status") == "accepted"
        and _graph_has_content(entry.get("candidate_graph") or {})
    )


def _graph_has_content(graph: dict[str, Any]) -> bool:
    return bool(graph.get("nodes")) and bool(graph.get("evidence_refs"))


def _bundle_failed_required(bundle: dict[str, Any]) -> list[dict[str, Any]]:
    """Any ``required=True`` source that is not accepted fails — no silent reclassification."""
    failures: list[dict[str, Any]] = []
    for entry in bundle.get("sources", []):
        if not entry.get("required"):
            continue
        if entry.get("status") == "accepted":
            continue
        failures.append(
            {
                "kind": "required_source_not_accepted",
                "path": entry.get("source_uri"),
                "domain": entry.get("source_domain"),
                "status": entry.get("status"),
                "skip_reason": entry.get("skip_reason"),
            }
        )
    return failures


def _acceptance_gates(
    *,
    inventory: dict[str, Any],
    bundle: dict[str, Any],
    store: UnionSupergraphStore,
    accepted_assertion_count: int,
    assertions_with_source_artifact_count: int,
    merged_contribution_count: int,
    world_integrity_valid: bool,
    rebuild_equivalent: bool,
) -> list[str]:
    failures: list[str] = []
    expected_recaps = len(inventory.get("recap_session_numbers") or [])
    recap_accepted = _accepted_recap_count(bundle)
    if recap_accepted != expected_recaps:
        failures.append(f"expected {expected_recaps} accepted recaps, got {recap_accepted}")
    failed_required = _bundle_failed_required(bundle)
    if failed_required:
        failures.append("failed_required_sources is non-empty")
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
    if merged_contribution_count < recap_accepted:
        failures.append("not all accepted sources produced merged contributions")
    fixture_uris = _store_has_fixture_uris(store)
    if fixture_uris:
        failures.append(f"store contains fixture URIs: {fixture_uris[:3]}")
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
    """Run full materialization: empty baseline → Kernel merge per contribution → report."""
    repo_root = repo_root.resolve()
    store_root = store_root.resolve()
    manifest = load_acceptance_manifest(manifest_path)
    world_id = manifest["world_id"]
    campaign_scope = manifest["campaign_scope"]

    inventory = build_inventory(manifest, repo_root=repo_root, manifest_path=manifest_path)
    bundle = load_candidate_bundle(bundle_path)
    manifest_sha256 = sha256_bytes(manifest_path.read_bytes())
    bundle_sha256 = sha256_bytes(bundle_path.read_bytes())
    focus_session_id = _focus_session_id(inventory)

    bundle_errors = validate_candidate_bundle(
        bundle,
        manifest_sha256=manifest_sha256,
        inventory=inventory,
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

    contributions = bundle_sources_to_contributions(bundle, world_id=world_id)
    baseline_revision_id: str | None = None
    parent_revision_id: str | None = None
    duplicate_graph_state_created = False
    contrib_count_before = 0
    head_before = None
    fp_before = ""

    if not head_exists:
        if not fresh_root:
            raise AcceptanceManifestError(
                "no world head; pass --fresh-root to publish baseline",
                errors=[{"kind": "missing_head"}],
            )
        empty_baseline = _empty_union_store(
            campaign_scope=campaign_scope,
            focus_session_id=focus_session_id,
        )
        try:
            baseline_result = kernel.publish_world_revision(
                store_root,
                world_id,
                empty_baseline,
                operation_ids=["op:pr006-empty-baseline"],
            )
        except kernel.WorldGraphValidationError as exc:
            raise AcceptanceManifestError(
                f"empty baseline failed publish validation: {exc}",
                errors=[{"kind": "publish_validation", "message": str(exc)}],
            ) from exc
        baseline_revision_id = baseline_result.revision.revision_id
        parent_revision_id = baseline_revision_id
        current_parent = baseline_revision_id
        _hb, _rb, baseline_store = kernel.open_current_world_graph(store_root, world_id)
        if baseline_store.nodes or baseline_store.edges or baseline_store.evidence:
            raise AcceptanceManifestError(
                "empty baseline must contain no corpus assertions",
                errors=[{"kind": "baseline_not_empty"}],
            )
    else:
        if expected_parent_revision_id is None:
            raise AcceptanceManifestError(
                "expected_parent_revision_id required when world head exists",
                errors=[{"kind": "missing_expected_parent"}],
            )
        head_before = kernel.open_world_graph_head(store_root, world_id)
        _h, _r, store_before = kernel.open_current_world_graph(store_root, world_id)
        fp_before = _local_graph_fingerprint(store_before)
        contrib_health_before = kernel.build_contribution_integrity_report(
            store_root, world_id=world_id, check_rebuild=False
        )
        contrib_count_before = contrib_health_before.active_contribution_count
        parent_revision_id = head_before.head_revision_id
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
        current_parent = parent_revision_id

    merged_contribution_count = 0
    resolved_existing_count = 0
    resolved_contributions: list[kernel.GraphContribution] = []
    _h0, _r0, working_store = kernel.open_current_world_graph(store_root, world_id)
    for contrib in contributions:
        resolved = resolve_contribution_identities(
            contrib,
            working_store,
            world_id=world_id,
        )
        resolved_contributions.append(resolved)
        resolved_existing_count += sum(
            1
            for assertion in resolved.accepted_assertions
            if assertion.identity_resolution_outcome == "resolved_existing"
        )
        result = kernel.merge_contribution_to_revision(
            store_root,
            world_id=world_id,
            contribution=resolved,
            expected_parent_revision_id=current_parent,
        )
        if result.published:
            current_parent = result.revision_id
            merged_contribution_count += 1
            _h, _r, working_store = kernel.open_current_world_graph(store_root, world_id)
        elif any("idempotent_noop" in d for d in result.diagnostics):
            merged_contribution_count += 1
            continue
        else:
            raise AcceptanceManifestError(
                "contribution merge failed",
                errors=[{"kind": "merge_failed", "diagnostics": result.diagnostics}],
            )

    if head_exists:
        head_after = kernel.open_world_graph_head(store_root, world_id)
        _h2, _r2, store_after = kernel.open_current_world_graph(store_root, world_id)
        fp_after = _local_graph_fingerprint(store_after)
        contrib_health_after = kernel.build_contribution_integrity_report(
            store_root, world_id=world_id, check_rebuild=False
        )
        contrib_count_after = contrib_health_after.active_contribution_count
        duplicate_graph_state_created = (
            head_after.head_revision_id != head_before.head_revision_id
            or fp_after != fp_before
            or contrib_count_after != contrib_count_before
        )
        if duplicate_graph_state_created:
            raise AcceptanceManifestError(
                "idempotent replay changed graph state",
                errors=[
                    {
                        "kind": "duplicate_graph_state",
                        "head_before": head_before.head_revision_id,
                        "head_after": head_after.head_revision_id,
                        "fp_changed": fp_after != fp_before,
                        "contrib_count_before": contrib_count_before,
                        "contrib_count_after": contrib_count_after,
                    }
                ],
            )

    head = kernel.open_world_graph_head(store_root, world_id)
    _head_rev, _rev, store = kernel.open_current_world_graph(store_root, world_id)

    world_health = kernel.build_world_integrity_report(store_root, world_id, persist=False)
    contrib_health = kernel.build_contribution_integrity_report(
        store_root, world_id=world_id, check_rebuild=True
    )
    rebuild = kernel.rebuild_from_contributions(store_root, world_id=world_id, publish=False)
    rebuild_equivalent = "rebuild_equivalent_to_head" in rebuild.diagnostics

    accepted_count, with_source_count = _count_assertions_with_source(resolved_contributions)
    with_evidence_count = sum(
        1
        for contrib in resolved_contributions
        for assertion in contrib.accepted_assertions
        if assertion.evidence_ref_ids
    )

    bundle_sources = bundle.get("sources", [])
    empty_skipped = [
        {"uri": entry["source_uri"], "skip_reason": entry.get("skip_reason")}
        for entry in bundle_sources
        if entry.get("status") == "skipped"
    ]
    failed_required_sources = _bundle_failed_required(bundle)

    gate_failures = _acceptance_gates(
        inventory=inventory,
        bundle=bundle,
        store=store,
        accepted_assertion_count=accepted_count,
        assertions_with_source_artifact_count=with_source_count,
        merged_contribution_count=merged_contribution_count,
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
        bundle_sources=bundle_sources,
        head_revision_id=head.head_revision_id,
        parent_revision_id=parent_revision_id,
        baseline_revision_id=baseline_revision_id,
        node_count=len(store.nodes),
        edge_count=len(store.edges),
        evidence_ref_count=len(store.evidence),
        accepted_assertion_count=accepted_count,
        assertions_with_source_artifact_count=with_source_count,
        assertions_with_evidence_count=with_evidence_count,
        produced_contribution_count=len(resolved_contributions),
        merged_contribution_count=merged_contribution_count,
        contribution_count=len(resolved_contributions),
        active_contribution_count=contrib_health.active_contribution_count,
        superseded_contribution_count=contrib_health.superseded_contribution_count,
        retracted_contribution_count=contrib_health.retracted_contribution_count,
        duplicate_graph_state_created=duplicate_graph_state_created,
        world_integrity_valid=bool(world_health.load_ok and world_health.validation_ok),
        contribution_integrity_valid=contrib_health.rebuild_equivalent_to_head is not False,
        rebuild_equivalent_to_head=rebuild_equivalent,
        accepted_source_domain_counts=_counts_by_domain(bundle_sources, status="accepted"),
        requested_source_domain_counts=_counts_by_domain(bundle_sources),
        identity_diagnostics={
            "unresolved_mention_count": sum(
                len(c.unresolved_mentions) for c in resolved_contributions
            ),
            "rejected_assertion_count": sum(
                len(c.rejected_assertions) for c in resolved_contributions
            ),
            "provisional_identity_count": 0,
            "ambiguous_identity_count": sum(
                1
                for c in resolved_contributions
                for m in c.unresolved_mentions
                if m.identity_resolution_outcome == "ambiguous"
            ),
            "blocked_collision_count": sum(
                1
                for c in resolved_contributions
                for m in c.unresolved_mentions
                if m.identity_resolution_outcome == "blocked_collision"
            ),
            "resolved_existing_count": resolved_existing_count,
        },
        required_hubs_present=_required_hubs_present_list(store),
        empty_skipped_sources=empty_skipped,
        failed_required_sources=failed_required_sources,
        accepted_recap_count=_accepted_recap_count(bundle),
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
        "fixture_uri_count": len(_store_has_fixture_uris(store)),
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
