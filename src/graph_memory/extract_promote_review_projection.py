"""Game-facing review projection for extract → World Graph promote.

The sealed ``reviewPackage`` remains confirmation authority. This module emits a
typed presentation model so UI clients never parse Kernel proposal internals.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

from graph_memory.extract_identity_gate import IdentityGateResult
from graph_memory.kernel.contribution_models import (
    ContributionIdentityMention,
    GraphContributionAssertion,
)

ReviewItemKind = Literal["object", "relationship", "attribute", "alias"]
ReviewItemAction = Literal["create", "connect_existing", "update"]


@dataclass(frozen=True)
class PromoteReviewItem:
    assertion_id: str
    kind: ReviewItemKind
    label: str
    action: ReviewItemAction
    identity_outcome: str
    summary: str
    evidence_summary: str | None = None
    warnings: list[str] = field(default_factory=list)
    selectable: bool = False
    selected_by_default: bool = False
    # Assertion IDs that must remain selected when this item is selected
    # (e.g. newly created endpoint nodes required by a relationship).
    depends_on_assertion_ids: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class PromoteReviewSummary:
    new_object_count: int = 0
    connect_existing_count: int = 0
    relationship_count: int = 0
    unresolved_mention_count: int = 0
    rejected_assertion_count: int = 0


def project_promote_review(
    gate: IdentityGateResult,
) -> tuple[list[PromoteReviewItem], PromoteReviewSummary]:
    """Project an identity-gate result into UI review items + summary counts."""
    items: list[PromoteReviewItem] = []
    new_objects = 0
    connect_existing = 0
    relationships = 0

    label_by_node_id = _label_map_from_accepted(gate.accepted_proposals)
    create_node_assertion_ids = _create_node_assertion_ids(gate.accepted_proposals)

    for assertion in gate.accepted_proposals:
        item = _item_from_accepted_assertion(
            assertion,
            identity_outcome_snapshot=gate.identity_outcome_snapshot,
            node_id_map=gate.node_id_map,
            label_by_node_id=label_by_node_id,
            create_node_assertion_ids=create_node_assertion_ids,
        )
        items.append(item)
        if item.kind == "relationship":
            relationships += 1
        elif item.action == "create":
            new_objects += 1
        elif item.action == "connect_existing":
            connect_existing += 1

    for mention in gate.unresolved_mentions:
        items.append(_item_from_unresolved_mention(mention))

    for assertion in gate.rejected_assertions:
        items.append(
            _item_from_rejected_assertion(
                assertion,
                label_by_node_id=label_by_node_id,
            )
        )

    summary = PromoteReviewSummary(
        new_object_count=new_objects,
        connect_existing_count=connect_existing,
        relationship_count=relationships,
        unresolved_mention_count=len(gate.unresolved_mentions),
        rejected_assertion_count=len(gate.rejected_assertions),
    )
    return items, summary


def project_promote_review_as_dicts(
    gate: IdentityGateResult,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    items, summary = project_promote_review(gate)
    return (
        [_item_to_dict(item) for item in items],
        {
            "new_object_count": summary.new_object_count,
            "connect_existing_count": summary.connect_existing_count,
            "relationship_count": summary.relationship_count,
            "unresolved_mention_count": summary.unresolved_mention_count,
            "rejected_assertion_count": summary.rejected_assertion_count,
        },
    )


def _item_to_dict(item: PromoteReviewItem) -> dict[str, Any]:
    return {
        "assertion_id": item.assertion_id,
        "kind": item.kind,
        "label": item.label,
        "action": item.action,
        "identity_outcome": item.identity_outcome,
        "summary": item.summary,
        "evidence_summary": item.evidence_summary,
        "warnings": list(item.warnings),
        "selectable": item.selectable,
        "selected_by_default": item.selected_by_default,
        "depends_on_assertion_ids": list(item.depends_on_assertion_ids),
    }


def _kind_from_assertion(assertion: GraphContributionAssertion) -> ReviewItemKind:
    mapping: dict[str, ReviewItemKind] = {
        "node": "object",
        "edge": "relationship",
        "attribute": "attribute",
        "alias": "alias",
        "evidence_ref": "attribute",
    }
    return mapping.get(str(assertion.assertion_kind), "object")


def _action_from_outcome(outcome: str) -> ReviewItemAction:
    text = (outcome or "").strip()
    if text in {"created_new", "provisional_new"}:
        return "create"
    if text in {"resolved_existing", "human_override"}:
        return "connect_existing"
    return "update"


def _evidence_summary(assertion: GraphContributionAssertion) -> str | None:
    refs = [str(r).strip() for r in (assertion.evidence_ref_ids or []) if str(r).strip()]
    if refs:
        return f"{len(refs)} evidence ref{'s' if len(refs) != 1 else ''}"
    artifact = (assertion.source_artifact_id or "").strip()
    if artifact:
        return f"source {artifact}"
    return None


def _label_map_from_accepted(
    assertions: list[GraphContributionAssertion],
) -> dict[str, str]:
    labels: dict[str, str] = {}
    for assertion in assertions:
        if assertion.assertion_kind != "node":
            continue
        subject = (assertion.subject_node_id or "").strip()
        if not subject:
            continue
        label = (assertion.label or "").strip() or subject
        labels[subject] = label
    return labels


def _create_node_assertion_ids(
    assertions: list[GraphContributionAssertion],
) -> dict[str, str]:
    """Map newly created node subject IDs → their accepted assertion IDs."""
    create_ids: dict[str, str] = {}
    for assertion in assertions:
        if assertion.assertion_kind != "node":
            continue
        subject = (assertion.subject_node_id or "").strip()
        if not subject:
            continue
        outcome = (assertion.identity_resolution_outcome or "").strip()
        if outcome in {"created_new", "provisional_new"}:
            create_ids[subject] = assertion.assertion_id
    return create_ids


def _depends_on_for_edge(
    assertion: GraphContributionAssertion,
    *,
    create_node_assertion_ids: dict[str, str],
) -> list[str]:
    deps: list[str] = []
    for endpoint in (
        (assertion.subject_node_id or "").strip(),
        (assertion.target_node_id or "").strip(),
    ):
        dep = create_node_assertion_ids.get(endpoint)
        if dep and dep not in deps:
            deps.append(dep)
    return deps


def _relationship_endpoint_label(
    node_id: str | None,
    *,
    label_by_node_id: dict[str, str],
) -> str:
    text = (node_id or "").strip()
    if not text:
        return "?"
    return label_by_node_id.get(text, text)


def _relationship_display(
    assertion: GraphContributionAssertion,
    *,
    label_by_node_id: dict[str, str],
) -> str:
    """Always identify both endpoints; never rely on predicate-only edge.label."""
    predicate = (
        (assertion.predicate or "").strip()
        or (assertion.label or "").strip()
        or "related_to"
    )
    left = _relationship_endpoint_label(
        assertion.subject_node_id, label_by_node_id=label_by_node_id
    )
    right = _relationship_endpoint_label(
        assertion.target_node_id, label_by_node_id=label_by_node_id
    )
    return f"{left} —{predicate}→ {right}"


def _label_for_assertion(
    assertion: GraphContributionAssertion,
    *,
    label_by_node_id: dict[str, str] | None = None,
) -> str:
    if assertion.assertion_kind == "edge":
        return _relationship_display(
            assertion, label_by_node_id=label_by_node_id or {}
        )
    if (assertion.label or "").strip():
        return str(assertion.label).strip()
    subject = (assertion.subject_node_id or "").strip()
    if subject:
        return subject
    return assertion.assertion_id


def _summary_for_accepted(
    assertion: GraphContributionAssertion,
    *,
    action: ReviewItemAction,
    identity_outcome: str,
    node_id_map: dict[str, str],
    label_by_node_id: dict[str, str],
) -> str:
    kind = _kind_from_assertion(assertion)
    if kind == "relationship":
        return f"Add relationship: {_relationship_display(assertion, label_by_node_id=label_by_node_id)}"
    label = _label_for_assertion(assertion, label_by_node_id=label_by_node_id)
    if action == "create":
        return f"Create new {kind}: {label}"
    if action == "connect_existing":
        extract_id = (assertion.subject_node_id or "").strip()
        # Prefer mapped durable id when the gate recorded one.
        durable = None
        for extract, mapped in node_id_map.items():
            if mapped == extract_id or extract == extract_id:
                durable = mapped
                break
        if durable and durable != label:
            return f"Connect existing {kind}: {label} → {durable}"
        return f"Connect existing {kind}: {label}"
    return f"Update {kind}: {label} ({identity_outcome or 'update'})"


def _item_from_accepted_assertion(
    assertion: GraphContributionAssertion,
    *,
    identity_outcome_snapshot: dict[str, str],
    node_id_map: dict[str, str],
    label_by_node_id: dict[str, str],
    create_node_assertion_ids: dict[str, str],
) -> PromoteReviewItem:
    subject = (assertion.subject_node_id or "").strip()
    outcome = (
        (assertion.identity_resolution_outcome or "").strip()
        or identity_outcome_snapshot.get(subject, "")
        or "created_new"
    )
    action = _action_from_outcome(outcome)
    kind = _kind_from_assertion(assertion)
    depends_on: list[str] = []
    # Edges rarely carry identity outcomes; treat as create relationship.
    if kind == "relationship" and action == "update" and not (
        assertion.identity_resolution_outcome or ""
    ).strip():
        action = "create"
        outcome = outcome or "created_new"
    if kind == "relationship":
        depends_on = _depends_on_for_edge(
            assertion, create_node_assertion_ids=create_node_assertion_ids
        )
    return PromoteReviewItem(
        assertion_id=assertion.assertion_id,
        kind=kind,
        label=_label_for_assertion(assertion, label_by_node_id=label_by_node_id),
        action=action,
        identity_outcome=outcome,
        summary=_summary_for_accepted(
            assertion,
            action=action,
            identity_outcome=outcome,
            node_id_map=node_id_map,
            label_by_node_id=label_by_node_id,
        ),
        evidence_summary=_evidence_summary(assertion),
        warnings=[],
        selectable=True,
        selected_by_default=True,
        depends_on_assertion_ids=depends_on,
    )


def _item_from_unresolved_mention(
    mention: ContributionIdentityMention,
) -> PromoteReviewItem:
    outcome = (mention.identity_resolution_outcome or "ambiguous").strip()
    warnings = list(mention.diagnostics or [])
    return PromoteReviewItem(
        assertion_id=f"unresolved:{mention.mention_id}",
        kind="object",
        label=(mention.label or mention.mention_id).strip(),
        action="update",
        identity_outcome=outcome,
        summary=(
            f"Unresolved mention: {(mention.label or mention.mention_id).strip()} "
            f"({outcome})"
        ),
        evidence_summary=(
            f"{len(mention.evidence_ref_ids)} evidence refs"
            if mention.evidence_ref_ids
            else None
        ),
        warnings=warnings,
        selectable=False,
        selected_by_default=False,
    )


def _item_from_rejected_assertion(
    assertion: GraphContributionAssertion,
    *,
    label_by_node_id: dict[str, str],
) -> PromoteReviewItem:
    outcome = (assertion.identity_resolution_outcome or "rejected").strip()
    label = _label_for_assertion(assertion, label_by_node_id=label_by_node_id)
    return PromoteReviewItem(
        assertion_id=f"rejected:{assertion.assertion_id}",
        kind=_kind_from_assertion(assertion),
        label=label,
        action="update",
        identity_outcome=outcome,
        summary=f"Rejected: {label} ({outcome})",
        evidence_summary=_evidence_summary(assertion),
        warnings=[],
        selectable=False,
        selected_by_default=False,
    )


__all__ = [
    "PromoteReviewItem",
    "PromoteReviewSummary",
    "project_promote_review",
    "project_promote_review_as_dicts",
]
