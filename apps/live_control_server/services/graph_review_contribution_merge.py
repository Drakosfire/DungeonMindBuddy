"""Graph Review → durable contribution merge seam (PR005).

Converts Graph Review authored object assertions into ``GraphContribution``
records and publishes them through ``merge_contribution_to_revision``.

This is the service-level write path that keeps Graph Review authoring on the
same Kernel merge semantics as extraction contributions. Overlay/preview paths
remain available until PR006–PR008 migrate surfaces fully.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import graph_memory.kernel as kernel
from apps.live_control_server.models.graph_authoring_overlay import (
    AuthoredGraphObjectAssertion,
)


def authored_object_assertion_to_kernel_assertion(
    assertion: AuthoredGraphObjectAssertion,
    *,
    source_artifact_id: str,
    source_revision_id: str,
    campaign_scope: str | None = None,
) -> kernel.GraphContributionAssertion:
    """Map one Graph Review object assertion into a Kernel contribution assertion."""
    ref = assertion.object_ref
    node_id = (
        (ref.node_id or "").strip()
        or (ref.authored_node_id or "").strip()
        or (ref.local_proposal_id or "").strip()
    )
    if not node_id:
        raise ValueError(
            f"authored assertion {assertion.assertion_id!r} has no resolvable node id"
        )

    kind = (ref.kind or "npc").strip() or "npc"
    role = (ref.role or kind).strip() or kind
    label = (ref.label or node_id).strip() or node_id
    aliases = list(assertion.aliases) if assertion.aliases else [label]

    visibility = "gm"
    if assertion.visibility is not None:
        raw = str(assertion.visibility.visibility)
        visibility = "gm" if raw in {"gm_private", "gm"} else raw

    return kernel.build_assertion(
        assertion_kind="node",
        acceptance_state="accepted",
        subject_node_id=node_id,
        label=label,
        value={
            "kind": kind,
            "role": role,
            "source_domains": ["manual_seed"],
            "aliases": aliases,
            "summary": assertion.summary,
        },
        source_artifact_id=source_artifact_id,
        source_revision_id=source_revision_id,
        campaign_scope=campaign_scope or assertion.campaign_id,
        epistemic_kind="fact",
        visibility=visibility,
        identity_resolution_outcome="created_new",
    )


def merge_graph_review_authored_assertions(
    root: Path,
    *,
    world_id: str,
    source_artifact_id: str,
    source_revision_id: str,
    authored_by: str,
    assertions: list[AuthoredGraphObjectAssertion],
    campaign_scope: str | None = None,
    expected_parent_revision_id: str | None = None,
) -> kernel.ContributionMergeResult:
    """Create a graph_review_authored_assertion contribution and merge it via Kernel."""
    if not assertions:
        raise ValueError("assertions must be non-empty")

    accepted = [
        authored_object_assertion_to_kernel_assertion(
            item,
            source_artifact_id=source_artifact_id,
            source_revision_id=source_revision_id,
            campaign_scope=campaign_scope,
        )
        for item in assertions
    ]
    contribution = kernel.create_graph_contribution(
        world_id=world_id,
        source_kind="graph_review_authored_assertion",
        source_artifact_id=source_artifact_id,
        source_revision_id=source_revision_id,
        extraction_profile=None,
        campaign_scope=campaign_scope,
        authored_by=authored_by,
        accepted_assertions=accepted,
    )
    return kernel.merge_contribution_to_revision(
        root,
        world_id=world_id,
        contribution=contribution,
        expected_parent_revision_id=expected_parent_revision_id,
    )


def merge_graph_review_authored_assertions_from_payloads(
    root: Path,
    *,
    world_id: str,
    source_artifact_id: str,
    source_revision_id: str,
    authored_by: str,
    assertion_payloads: list[dict[str, Any]],
    campaign_scope: str | None = None,
    expected_parent_revision_id: str | None = None,
) -> kernel.ContributionMergeResult:
    """Validate overlay payloads then merge through the durable contribution seam."""
    assertions = [
        AuthoredGraphObjectAssertion.model_validate(payload)
        for payload in assertion_payloads
    ]
    return merge_graph_review_authored_assertions(
        root,
        world_id=world_id,
        source_artifact_id=source_artifact_id,
        source_revision_id=source_revision_id,
        authored_by=authored_by,
        assertions=assertions,
        campaign_scope=campaign_scope,
        expected_parent_revision_id=expected_parent_revision_id,
    )
