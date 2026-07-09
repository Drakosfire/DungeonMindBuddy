"""Guardrails for authored identity merge assertions."""

from __future__ import annotations

from typing import TYPE_CHECKING

from apps.live_control_server.models.graph_authoring_overlay import (
    AuthoredGraphAssertion,
    AuthoredGraphMergeObjectsAssertion,
    _object_ref_identity_key,
)

if TYPE_CHECKING:
    from apps.live_control_server.services.graph_object_authoring_prepare import (
        GraphAuthoringDiagnostic,
    )


def merge_assertion_cluster_keys(assertion: AuthoredGraphMergeObjectsAssertion) -> frozenset[str]:
    keys = {_object_ref_identity_key(assertion.survivor_object_ref)}
    for ref in assertion.merged_object_refs:
        keys.add(_object_ref_identity_key(ref))
    return frozenset(keys)


def merge_assertions_share_cluster(
    left: AuthoredGraphMergeObjectsAssertion,
    right: AuthoredGraphMergeObjectsAssertion,
) -> bool:
    return bool(merge_assertion_cluster_keys(left) & merge_assertion_cluster_keys(right))


def merge_assertions_conflict(
    left: AuthoredGraphMergeObjectsAssertion,
    right: AuthoredGraphMergeObjectsAssertion,
) -> bool:
    if left.assertion_id == right.assertion_id:
        return False
    if not merge_assertions_share_cluster(left, right):
        return False
    left_survivor = _object_ref_identity_key(left.survivor_object_ref)
    right_survivor = _object_ref_identity_key(right.survivor_object_ref)
    if left_survivor == right_survivor:
        return False
    if merge_assertion_supersedes_existing(proposed=left, existing=right):
        return False
    if merge_assertion_supersedes_existing(proposed=right, existing=left):
        return False
    return True


def merge_assertion_supersedes_existing(
    *,
    proposed: AuthoredGraphMergeObjectsAssertion,
    existing: AuthoredGraphMergeObjectsAssertion,
) -> bool:
    """True when a new merge intentionally replaces an older survivor choice."""
    if proposed.assertion_id == existing.assertion_id:
        return False
    if not merge_assertions_share_cluster(proposed, existing):
        return False
    proposed_survivor = _object_ref_identity_key(proposed.survivor_object_ref)
    existing_survivor = _object_ref_identity_key(existing.survivor_object_ref)
    if proposed_survivor == existing_survivor:
        return False
    proposed_merged_keys = merge_assertion_cluster_keys(proposed) - {proposed_survivor}
    existing_merged_keys = merge_assertion_cluster_keys(existing) - {existing_survivor}
    if proposed_survivor in existing_merged_keys:
        return False
    return existing_survivor in proposed_merged_keys


def find_superseded_merge_assertion_ids(
    proposed_assertions: list[AuthoredGraphAssertion],
    *,
    existing_assertions: list[AuthoredGraphAssertion],
) -> set[str]:
    return {
        superseded_assertion_id
        for superseded_assertion_id, _ in find_superseded_merge_assertion_pairs(
            proposed_assertions,
            existing_assertions=existing_assertions,
        )
    }


def find_superseded_merge_assertion_pairs(
    proposed_assertions: list[AuthoredGraphAssertion],
    *,
    existing_assertions: list[AuthoredGraphAssertion],
) -> list[tuple[str, str]]:
    """Return (superseded, superseding) assertion IDs for corrected merges."""
    proposed_merges = _active_merge_assertions(proposed_assertions)
    existing_merges = _active_merge_assertions(existing_assertions)
    pairs: set[tuple[str, str]] = set()
    for proposed in proposed_merges:
        for existing in existing_merges:
            if merge_assertion_supersedes_existing(proposed=proposed, existing=existing):
                pairs.add((existing.assertion_id, proposed.assertion_id))
    return sorted(pairs)


def _active_merge_assertions(
    assertions: list[AuthoredGraphAssertion],
) -> list[AuthoredGraphMergeObjectsAssertion]:
    return [
        assertion
        for assertion in assertions
        if assertion.assertion_kind == "merge_objects"
        and assertion.status == "authored"
        and isinstance(assertion, AuthoredGraphMergeObjectsAssertion)
    ]


def _conflict_message(
    proposed: AuthoredGraphMergeObjectsAssertion,
    existing: AuthoredGraphMergeObjectsAssertion,
) -> str:
    proposed_survivor = proposed.survivor_object_ref.node_id or proposed.survivor_object_ref.label
    existing_survivor = existing.survivor_object_ref.node_id or existing.survivor_object_ref.label
    return (
        f"Identity merge conflicts with existing assertion {existing.assertion_id}: "
        f"both touch the same record cluster but choose different survivors "
        f"({proposed_survivor!r} vs {existing_survivor!r}). "
        "Include the prior survivor as a duplicate to correct it, or revoke/supersede "
        "the existing merge before committing a different survivor."
    )


def detect_merge_assertion_conflicts(
    proposed_assertions: list[AuthoredGraphAssertion],
    *,
    existing_assertions: list[AuthoredGraphAssertion],
    local_proposal_id_by_assertion_id: dict[str, str] | None = None,
) -> list[GraphAuthoringDiagnostic]:
    """Return blocking diagnostics when merge assertions fight over the same identity cluster."""
    from apps.live_control_server.services.graph_object_authoring_prepare import (
        GraphAuthoringDiagnostic,
    )

    proposal_ids = local_proposal_id_by_assertion_id or {}
    proposed_merges = _active_merge_assertions(proposed_assertions)
    existing_merges = _active_merge_assertions(existing_assertions)
    diagnostics: list[GraphAuthoringDiagnostic] = []

    for proposed in proposed_merges:
        for existing in existing_merges:
            if not merge_assertions_conflict(proposed, existing):
                continue
            diagnostics.append(
                GraphAuthoringDiagnostic(
                    code="merge_assertion_conflicts_with_existing",
                    message=_conflict_message(proposed, existing),
                    local_proposal_id=proposal_ids.get(proposed.assertion_id),
                    severity="error",
                )
            )

    for index, left in enumerate(proposed_merges):
        for right in proposed_merges[index + 1 :]:
            if not merge_assertions_conflict(left, right):
                continue
            diagnostics.append(
                GraphAuthoringDiagnostic(
                    code="merge_assertion_conflicts_in_batch",
                    message=_conflict_message(left, right),
                    local_proposal_id=proposal_ids.get(left.assertion_id),
                    severity="error",
                )
            )

    return diagnostics
