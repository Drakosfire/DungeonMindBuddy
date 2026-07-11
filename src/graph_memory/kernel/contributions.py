"""GraphContribution factory and deterministic ID helpers (PR005)."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any

from graph_memory.kernel.contribution_models import (
    ContributionIdentityMention,
    ContributionSourceKind,
    GraphContribution,
    GraphContributionAssertion,
)

PROVENANCE_ONLY_ASSERTION_VALUE_KEYS = frozenset(
    {
        "source_domain",
        "source_domains",
        "source_artifact_id",
        "source_artifacts",
        "source_revision_id",
        "evidence",
        "evidence_ref_ids",
    }
)


def _utc_now_iso() -> str:
    return (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def _canonical_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def compute_contribution_id(
    *,
    world_id: str,
    source_kind: ContributionSourceKind,
    source_artifact_id: str | None,
    source_revision_id: str | None,
    extraction_profile: str | None,
    authored_by: str | None,
    supersedes_contribution_id: str | None = None,
) -> str:
    payload = {
        "world_id": world_id,
        "source_kind": source_kind,
        "source_artifact_id": source_artifact_id,
        "source_revision_id": source_revision_id,
        "extraction_profile": extraction_profile,
        "authored_by": authored_by,
        "supersedes_contribution_id": supersedes_contribution_id,
    }
    digest = hashlib.sha256(_canonical_json(payload).encode("utf-8")).hexdigest()[:16]
    return f"contribution:{digest}"


def compute_assertion_id(
    *,
    assertion_kind: str,
    subject_node_id: str | None,
    target_node_id: str | None,
    predicate: str | None,
    label: str | None,
    value: dict[str, Any] | None,
    campaign_scope: str | None,
    temporal_scope: dict[str, Any] | None,
    epistemic_kind: str | None,
    visibility: str | None,
) -> str:
    payload = {
        "assertion_kind": assertion_kind,
        "subject_node_id": subject_node_id,
        "target_node_id": target_node_id,
        "predicate": predicate,
        "label": label,
        "value": semantic_assertion_value(value),
        "campaign_scope": campaign_scope,
        "temporal_scope": temporal_scope,
        "epistemic_kind": epistemic_kind,
        "visibility": visibility,
    }
    digest = hashlib.sha256(_canonical_json(payload).encode("utf-8")).hexdigest()[:16]
    return f"assertion:{digest}"


def semantic_assertion_value(value: dict[str, Any] | None) -> dict[str, Any]:
    """Return the shallow semantic portion of an assertion value."""
    return {
        key: item
        for key, item in dict(value or {}).items()
        if key not in PROVENANCE_ONLY_ASSERTION_VALUE_KEYS
    }


def _canonicalize_assertion_identity(
    assertion: GraphContributionAssertion,
) -> tuple[GraphContributionAssertion, tuple[str, str] | None]:
    current_id = compute_assertion_id(
        assertion_kind=assertion.assertion_kind,
        subject_node_id=assertion.subject_node_id,
        target_node_id=assertion.target_node_id,
        predicate=assertion.predicate,
        label=assertion.label,
        value=assertion.value,
        campaign_scope=assertion.campaign_scope,
        temporal_scope=assertion.temporal_scope,
        epistemic_kind=assertion.epistemic_kind,
        visibility=assertion.visibility,
    )
    if assertion.assertion_id == current_id:
        return assertion, None
    return assertion.model_copy(update={"assertion_id": current_id}), (
        assertion.assertion_id,
        current_id,
    )


def _canonicalize_graph_contribution_assertions(
    contribution: GraphContribution,
) -> tuple[GraphContribution, list[tuple[str, str]]]:
    """Return an immutable contribution copy using current assertion IDs."""
    rekeys: list[tuple[str, str]] = []

    def canonicalize(
        assertions: list[GraphContributionAssertion],
    ) -> list[GraphContributionAssertion]:
        canonical: list[GraphContributionAssertion] = []
        for assertion in assertions:
            updated, rekey = _canonicalize_assertion_identity(assertion)
            canonical.append(updated)
            if rekey is not None:
                rekeys.append(rekey)
        return canonical

    return (
        contribution.model_copy(
            update={
                "candidate_assertions": canonicalize(contribution.candidate_assertions),
                "accepted_assertions": canonicalize(contribution.accepted_assertions),
                "rejected_assertions": canonicalize(contribution.rejected_assertions),
            }
        ),
        rekeys,
    )


def _with_contribution_id(
    assertions: list[GraphContributionAssertion],
    contribution_id: str,
) -> list[GraphContributionAssertion]:
    updated: list[GraphContributionAssertion] = []
    for assertion in assertions:
        if assertion.contribution_id and assertion.contribution_id != contribution_id:
            # Placeholder contribution_id is rewritten to the computed id.
            if not assertion.contribution_id.startswith("contribution:"):
                updated.append(
                    assertion.model_copy(update={"contribution_id": contribution_id})
                )
            else:
                updated.append(
                    assertion.model_copy(update={"contribution_id": contribution_id})
                )
        else:
            updated.append(
                assertion.model_copy(update={"contribution_id": contribution_id})
            )
    return updated


def create_graph_contribution(
    *,
    world_id: str,
    source_kind: ContributionSourceKind,
    source_artifact_id: str | None = None,
    source_revision_id: str | None = None,
    extraction_profile: str | None = None,
    campaign_scope: str | None = None,
    candidate_assertions: list[GraphContributionAssertion] | None = None,
    accepted_assertions: list[GraphContributionAssertion] | None = None,
    rejected_assertions: list[GraphContributionAssertion] | None = None,
    unresolved_mentions: list[ContributionIdentityMention] | None = None,
    identity_decision_ids: list[str] | None = None,
    authored_by: str | None = None,
    supersedes_contribution_id: str | None = None,
    produced_at: str | None = None,
    diagnostics: list[str] | None = None,
) -> GraphContribution:
    """Build a GraphContribution with a deterministic contribution_id.

    ``produced_at`` is metadata only and does not affect identity.
    """
    if not world_id.strip():
        raise ValueError("world_id must be non-empty")

    contribution_id = compute_contribution_id(
        world_id=world_id,
        source_kind=source_kind,
        source_artifact_id=source_artifact_id,
        source_revision_id=source_revision_id,
        extraction_profile=extraction_profile,
        authored_by=authored_by,
        supersedes_contribution_id=supersedes_contribution_id,
    )

    candidates = _with_contribution_id(
        list(candidate_assertions or []), contribution_id
    )
    accepted = _with_contribution_id(list(accepted_assertions or []), contribution_id)
    rejected = _with_contribution_id(list(rejected_assertions or []), contribution_id)

    contribution = GraphContribution(
        contribution_id=contribution_id,
        world_id=world_id,
        source_kind=source_kind,
        source_artifact_id=source_artifact_id,
        source_revision_id=source_revision_id,
        extraction_profile=extraction_profile,
        produced_at=produced_at or _utc_now_iso(),
        campaign_scope=campaign_scope,
        status="active",
        supersedes_contribution_id=supersedes_contribution_id,
        candidate_assertions=candidates,
        accepted_assertions=accepted,
        rejected_assertions=rejected,
        unresolved_mentions=list(unresolved_mentions or []),
        identity_decision_ids=list(identity_decision_ids or []),
        authored_by=authored_by,
        diagnostics=list(diagnostics or []),
    )
    canonical, rekeys = _canonicalize_graph_contribution_assertions(contribution)
    if not rekeys:
        return canonical
    return canonical.model_copy(
        update={
            "diagnostics": [
                *canonical.diagnostics,
                *[
                    f"assertion_identity_rekeyed:{old_id}->{new_id}"
                    for old_id, new_id in rekeys
                ],
            ]
        }
    )


def build_assertion(
    *,
    assertion_kind: str,
    acceptance_state: str,
    contribution_id: str = "contribution:pending",
    subject_node_id: str | None = None,
    target_node_id: str | None = None,
    predicate: str | None = None,
    label: str | None = None,
    value: dict[str, Any] | None = None,
    evidence_ref_ids: list[str] | None = None,
    source_artifact_id: str | None = None,
    source_revision_id: str | None = None,
    campaign_scope: str | None = None,
    temporal_scope: dict[str, Any] | None = None,
    visibility: str | None = None,
    epistemic_kind: str | None = None,
    identity_resolution_outcome: str | None = None,
    assertion_id: str | None = None,
) -> GraphContributionAssertion:
    """Helper to build an assertion with a deterministic assertion_id."""
    value_map = dict(value or {})
    computed_id = assertion_id or compute_assertion_id(
        assertion_kind=assertion_kind,
        subject_node_id=subject_node_id,
        target_node_id=target_node_id,
        predicate=predicate,
        label=label,
        value=value_map,
        campaign_scope=campaign_scope,
        temporal_scope=temporal_scope,
        epistemic_kind=epistemic_kind,
        visibility=visibility,
    )
    return GraphContributionAssertion(
        assertion_id=computed_id,
        assertion_kind=assertion_kind,  # type: ignore[arg-type]
        subject_node_id=subject_node_id,
        target_node_id=target_node_id,
        predicate=predicate,
        label=label,
        value=value_map,
        evidence_ref_ids=list(evidence_ref_ids or []),
        source_artifact_id=source_artifact_id,
        source_revision_id=source_revision_id,
        campaign_scope=campaign_scope,
        temporal_scope=temporal_scope,
        visibility=visibility,
        epistemic_kind=epistemic_kind,
        acceptance_state=acceptance_state,  # type: ignore[arg-type]
        identity_resolution_outcome=identity_resolution_outcome,
        contribution_id=contribution_id,
    )
