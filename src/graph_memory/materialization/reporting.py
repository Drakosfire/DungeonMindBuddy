"""Materialization report builder (PR006)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any


def _utc_now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def build_materialization_report(
    *,
    world_id: str,
    campaign_scope: str,
    manifest_sha256: str,
    bundle_sha256: str,
    inventory: dict[str, Any],
    bundle_sources: list[dict[str, Any]] | None = None,
    head_revision_id: str | None,
    parent_revision_id: str | None,
    baseline_revision_id: str | None,
    node_count: int,
    edge_count: int,
    evidence_ref_count: int,
    accepted_assertion_count: int,
    assertions_with_source_artifact_count: int,
    assertions_with_evidence_count: int,
    produced_contribution_count: int,
    merged_contribution_count: int,
    contribution_count: int,
    active_contribution_count: int,
    superseded_contribution_count: int,
    retracted_contribution_count: int,
    duplicate_graph_state_created: bool,
    world_integrity_valid: bool,
    contribution_integrity_valid: bool,
    rebuild_equivalent_to_head: bool,
    accepted_source_domain_counts: dict[str, int],
    requested_source_domain_counts: dict[str, int],
    identity_diagnostics: dict[str, Any],
    required_hubs_present: list[str],
    empty_skipped_sources: list[dict[str, Any]],
    failed_required_sources: list[dict[str, Any]],
    accepted_recap_count: int,
    retained_preview_paths: list[str],
) -> dict[str, Any]:
    requested = list(inventory.get("requested") or [])
    sources = bundle_sources or []
    bundle_accepted_count = sum(1 for entry in sources if entry.get("status") == "accepted")
    bundle_skipped_count = sum(1 for entry in sources if entry.get("status") == "skipped")
    return {
        "schema": "dmb_world_materialization_report_v1",
        "version": "1.0",
        "world_id": world_id,
        "campaign_scope": campaign_scope,
        "manifest_sha256": manifest_sha256,
        "bundle_sha256": bundle_sha256,
        "head_revision_id": head_revision_id,
        "parent_revision_id": parent_revision_id,
        "baseline_revision_id": baseline_revision_id,
        "requested_source_count": len(requested),
        "bundle_accepted_count": bundle_accepted_count,
        "bundle_skipped_count": bundle_skipped_count,
        "accepted_source_count": bundle_accepted_count,
        "skipped_source_count": bundle_skipped_count,
        "empty_skipped_sources": empty_skipped_sources,
        "failed_required_sources": failed_required_sources,
        "produced_contribution_count": produced_contribution_count,
        "merged_contribution_count": merged_contribution_count,
        "source_inventory": inventory.get("source_items") or [],
        "accepted_source_domain_counts": accepted_source_domain_counts,
        "requested_source_domain_counts": requested_source_domain_counts,
        "source_domain_counts": accepted_source_domain_counts,
        "counts_by_source_domain": accepted_source_domain_counts,
        "node_count": node_count,
        "edge_count": edge_count,
        "evidence_ref_count": evidence_ref_count,
        "accepted_assertion_count": accepted_assertion_count,
        "assertions_with_source_artifact_count": assertions_with_source_artifact_count,
        "assertions_with_evidence_count": assertions_with_evidence_count,
        "unresolved_identity_count": int(
            identity_diagnostics.get("unresolved_mention_count") or 0
        ),
        "provisional_identity_count": int(
            identity_diagnostics.get("provisional_identity_count") or 0
        ),
        "ambiguous_identity_count": int(
            identity_diagnostics.get("ambiguous_identity_count") or 0
        ),
        "blocked_collision_count": int(
            identity_diagnostics.get("blocked_collision_count") or 0
        ),
        "rejected_assertion_count": int(
            identity_diagnostics.get("rejected_assertion_count") or 0
        ),
        "resolved_existing_count": int(
            identity_diagnostics.get("resolved_existing_count") or 0
        ),
        "contribution_count": contribution_count,
        "active_contribution_count": active_contribution_count,
        "superseded_contribution_count": superseded_contribution_count,
        "retracted_contribution_count": retracted_contribution_count,
        "duplicate_graph_state_created": duplicate_graph_state_created,
        "world_integrity_valid": world_integrity_valid,
        "contribution_integrity_valid": contribution_integrity_valid,
        "rebuild_equivalent_to_head": rebuild_equivalent_to_head,
        "requested_recap_count": len(inventory.get("recap_session_numbers") or []),
        "accepted_recap_count": accepted_recap_count,
        "identity_diagnostics": identity_diagnostics,
        "required_hubs_present": required_hubs_present,
        "inventory": {
            "requested": requested,
            "accepted": list(inventory.get("accepted") or []),
            "skipped": list(inventory.get("skipped") or []),
            "failed_required": failed_required_sources,
            "authored_absent_reportable": list(
                inventory.get("authored_absent_reportable") or []
            ),
        },
        "unsupported_projection_requirements": [
            "revision-pinned Projection Engine (PR007)",
            "Plan latest-ingest / preview selection migration (PR008)",
            "focus-session overlay semantics beyond read-model baseline",
            "production retrieval over graph head without projection contract",
        ],
        "plan_can_trust": [
            "Persistent eldyrwild world graph head exists for longmont-c2",
            "Session 1–23 recap sources inventoried with sha256 provenance",
            "Mirathorn and Mireward location nodes present in merged head",
            "Six C2 PC hub nodes present with worldbuilding domain mapping",
            "Empty Kernel baseline + rebuild equivalence for contribution ledger",
            "Every accepted assertion carries source_artifact_id + source_revision_id",
            "Merged head has no fixture:// provenance URIs",
        ],
        "plan_cannot_trust": [
            "Revision-pinned projection slices (PR007 not landed)",
            "Latest-ingest preview graph selection (PR008 not landed)",
            "Graph Review preview union as durable authority",
            "Autonomous agent writes without governed confirm path (PR011)",
        ],
        "retained_preview_paths": retained_preview_paths,
        "generated_at": _utc_now_iso(),
    }
