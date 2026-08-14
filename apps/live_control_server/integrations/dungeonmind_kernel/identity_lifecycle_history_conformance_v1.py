"""Prove Buddy identity-lifecycle shadow fields are reconstructable history.

Diagnostic only. Does not mutate World Graph identity decisions, redirects,
merge records, or node state. Does not invent DungeonMind property terms.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from graph_memory.kernel.identity_models import IdentityDecisionRecord


IDENTITY_LIFECYCLE_HISTORY_SCHEMA = "dmb_identity_lifecycle_history_conformance_v1"
CANDIDATE_SHADOW_FIELDS: tuple[str, ...] = (
    "identity_state",
    "merged_into",
    "last_identity_decision_id",
)
EXPECTED_ELDRYWILD_FIELD_COUNTS: dict[str, int] = {
    "identity_state": 7,
    "merged_into": 7,
    "last_identity_decision_id": 14,
}
SUPPORTED_DECISION_KIND = "merge"
ALIAS_REMOVE_DECISION_KIND = "alias_remove"
SUPPORTED_IDENTITY_STATE = "survivor"
MERGED_AWAY_STATE = "merged_away"
CANONICAL_SURVIVOR_STATE = "canonical"
STATE_MUTATING_DECISION_KINDS = frozenset(
    {"merge", "split", "unmerge", "alias_remove"}
)
INVALIDATING_BETWEEN_DECISION_KINDS = frozenset({"split", "unmerge"})
PROVEN_HISTORY_NOTE = (
    "validated identity lifecycle shadow; durable authority is the "
    "identity decision/redirect history, not a world-property assertion"
)

LifecycleRole = Literal["merge_source", "merge_survivor"]
CandidateField = Literal[
    "identity_state",
    "merged_into",
    "last_identity_decision_id",
]


class IdentityLifecycleHistoryConformanceError(RuntimeError):
    """Fail-closed identity-lifecycle proof error."""

    def __init__(self, message: str, *, code: str) -> None:
        super().__init__(message)
        self.code = code


class IdentityLifecycleShadowRowV1(BaseModel):
    model_config = ConfigDict(extra="forbid")

    element_id: str
    node_id: str
    field: CandidateField
    stored_value: Any
    decision_id: str
    decision_kind: str
    decision_status: str
    subject_node_id: str | None
    target_node_id: str | None
    redirect_id: str | None
    redirect_status: str | None
    lifecycle_role: LifecycleRole | None
    reconstructable: bool
    rationale: str


class IdentityLifecycleHistoryConformanceV1(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_: Literal["dmb_identity_lifecycle_history_conformance_v1"] = Field(
        default=IDENTITY_LIFECYCLE_HISTORY_SCHEMA,
        alias="schema",
    )
    world_id: str
    canonical_revision_id: str
    canonical_graph_payload_sha256: str
    rows: list[IdentityLifecycleShadowRowV1]
    field_counts: dict[str, int]
    element_ids: list[str]
    reconstructable_count: int
    unresolved_element_ids: list[str]
    passed: bool


def _fail(message: str, code: str) -> IdentityLifecycleHistoryConformanceError:
    return IdentityLifecycleHistoryConformanceError(message, code=code)


def identity_lifecycle_element_id(node_id: str, field: str) -> str:
    return f"node:{node_id}:state:{field}"


def _node_state(node: Any) -> dict[str, Any]:
    state = getattr(node, "state", None)
    if state is None and isinstance(node, dict):
        state = node.get("state")
    return dict(state or {})


def _redirect_attr(redirect: Any, name: str) -> Any:
    if hasattr(redirect, name):
        return getattr(redirect, name)
    if isinstance(redirect, dict):
        return redirect.get(name)
    return None


@dataclass(frozen=True, slots=True)
class IdentityDecisionLedger:
    """Durable identity-decision list with id and append-position indexes."""

    ordered: tuple[IdentityDecisionRecord, ...]
    by_id: dict[str, IdentityDecisionRecord]
    position: dict[str, int]


@dataclass(frozen=True, slots=True)
class AliasRemoveSurvivorLineage:
    """Internal causal merge + current alias_remove proof for one survivor."""

    reconstructable: bool
    rationale: str
    current: IdentityDecisionRecord | None = None
    causal_merge: IdentityDecisionRecord | None = None


def _load_identity_decision_ledger(store: Any) -> IdentityDecisionLedger:
    ordered: list[IdentityDecisionRecord] = []
    by_id: dict[str, IdentityDecisionRecord] = {}
    position: dict[str, int] = {}
    raw_decisions = list(getattr(store, "identity_decisions", None) or [])
    for index, raw in enumerate(raw_decisions):
        try:
            decision = IdentityDecisionRecord.model_validate(raw)
        except Exception as exc:
            raise _fail(
                f"identity decision record is not valid: {exc}",
                "identity_decision_invalid",
            ) from exc
        if decision.decision_id in by_id:
            raise _fail(
                f"duplicate identity decision_id {decision.decision_id!r}",
                "duplicate_decision_id",
            )
        ordered.append(decision)
        by_id[decision.decision_id] = decision
        position[decision.decision_id] = index
    return IdentityDecisionLedger(
        ordered=tuple(ordered),
        by_id=by_id,
        position=position,
    )


def _index_identity_decisions(store: Any) -> dict[str, IdentityDecisionRecord]:
    return _load_identity_decision_ledger(store).by_id


def _active_redirects_from(store: Any, node_id: str) -> list[Any]:
    matches: list[Any] = []
    for redirect in list(getattr(store, "identity_redirects", None) or []):
        if _redirect_attr(redirect, "status") != "active":
            continue
        if _redirect_attr(redirect, "from_node_id") == node_id:
            matches.append(redirect)
    return matches


def collect_identity_lifecycle_candidates(store: Any) -> list[tuple[str, str, str, Any]]:
    """Return (element_id, node_id, field, stored_value) for candidate shadow fields."""
    nodes = getattr(store, "nodes", None) or {}
    rows: list[tuple[str, str, str, Any]] = []
    for node_id, node in nodes.items():
        state = _node_state(node)
        for field in CANDIDATE_SHADOW_FIELDS:
            if field not in state:
                continue
            rows.append(
                (
                    identity_lifecycle_element_id(node_id, field),
                    node_id,
                    field,
                    state[field],
                )
            )
    rows.sort(key=lambda item: item[0])
    return rows


def _field_counts(candidates: list[tuple[str, str, str, Any]]) -> dict[str, int]:
    counts = Counter(field for _, _, field, _ in candidates)
    return {field: int(counts.get(field, 0)) for field in CANDIDATE_SHADOW_FIELDS}


def _node_named_by_decision(node_id: str, decision: IdentityDecisionRecord) -> bool:
    affected = list(decision.affected_node_ids or [])
    return node_id in {
        decision.subject_node_id,
        decision.target_node_id,
        *affected,
    }


def _lifecycle_role_for_merge(
    node_id: str,
    decision: IdentityDecisionRecord,
) -> LifecycleRole | None:
    if decision.subject_node_id == node_id:
        return "merge_source"
    if decision.target_node_id == node_id:
        return "merge_survivor"
    return None


def _unresolved_row(
    *,
    element_id: str,
    node_id: str,
    field: str,
    stored_value: Any,
    rationale: str,
    decision: IdentityDecisionRecord | None = None,
    redirect: Any | None = None,
    lifecycle_role: LifecycleRole | None = None,
) -> IdentityLifecycleShadowRowV1:
    return IdentityLifecycleShadowRowV1(
        element_id=element_id,
        node_id=node_id,
        field=field,  # type: ignore[arg-type]
        stored_value=stored_value,
        decision_id="" if decision is None else decision.decision_id,
        decision_kind="" if decision is None else decision.decision_kind,
        decision_status="" if decision is None else decision.status,
        subject_node_id=None if decision is None else decision.subject_node_id,
        target_node_id=None if decision is None else decision.target_node_id,
        redirect_id=None if redirect is None else _redirect_attr(redirect, "redirect_id"),
        redirect_status=None if redirect is None else _redirect_attr(redirect, "status"),
        lifecycle_role=lifecycle_role,
        reconstructable=False,
        rationale=rationale,
    )


def _prove_last_identity_decision_id(
    *,
    store: Any,
    node_id: str,
    stored_value: Any,
    decisions: dict[str, IdentityDecisionRecord],
) -> IdentityLifecycleShadowRowV1:
    element_id = identity_lifecycle_element_id(node_id, "last_identity_decision_id")
    if not isinstance(stored_value, str) or not stored_value.strip():
        return _unresolved_row(
            element_id=element_id,
            node_id=node_id,
            field="last_identity_decision_id",
            stored_value=stored_value,
            rationale="last_identity_decision_id is not a nonblank string",
        )
    decision = decisions.get(stored_value)
    if decision is None:
        return _unresolved_row(
            element_id=element_id,
            node_id=node_id,
            field="last_identity_decision_id",
            stored_value=stored_value,
            rationale=f"dangling last_identity_decision_id {stored_value!r}",
        )
    if decision.decision_kind != SUPPORTED_DECISION_KIND:
        return _unresolved_row(
            element_id=element_id,
            node_id=node_id,
            field="last_identity_decision_id",
            stored_value=stored_value,
            decision=decision,
            rationale=(
                f"decision kind {decision.decision_kind!r} is not covered by the "
                "merge-shadow proof"
            ),
        )
    if decision.status != "active":
        return _unresolved_row(
            element_id=element_id,
            node_id=node_id,
            field="last_identity_decision_id",
            stored_value=stored_value,
            decision=decision,
            rationale=f"identity decision status {decision.status!r} is not active",
        )
    if not _node_named_by_decision(node_id, decision):
        return _unresolved_row(
            element_id=element_id,
            node_id=node_id,
            field="last_identity_decision_id",
            stored_value=stored_value,
            decision=decision,
            rationale="node is not subject, target, or affected by the pointed decision",
        )
    role = _lifecycle_role_for_merge(node_id, decision)
    if role is None:
        return _unresolved_row(
            element_id=element_id,
            node_id=node_id,
            field="last_identity_decision_id",
            stored_value=stored_value,
            decision=decision,
            rationale="node is not the merge subject or target",
        )
    state = _node_state(store.nodes[node_id])
    redirect = None
    if role == "merge_source":
        active = _active_redirects_from(store, node_id)
        if len(active) != 1:
            return _unresolved_row(
                element_id=element_id,
                node_id=node_id,
                field="last_identity_decision_id",
                stored_value=stored_value,
                decision=decision,
                lifecycle_role=role,
                rationale=(
                    "merge source does not have exactly one active identity redirect"
                ),
            )
        redirect = active[0]
        expected_target = decision.target_node_id
        if _redirect_attr(redirect, "to_node_id") != expected_target:
            return _unresolved_row(
                element_id=element_id,
                node_id=node_id,
                field="last_identity_decision_id",
                stored_value=stored_value,
                decision=decision,
                redirect=redirect,
                lifecycle_role=role,
                rationale="active redirect target disagrees with merge decision target",
            )
        reconstructed = decision.decision_id
        if stored_value != reconstructed:
            return _unresolved_row(
                element_id=element_id,
                node_id=node_id,
                field="last_identity_decision_id",
                stored_value=stored_value,
                decision=decision,
                redirect=redirect,
                lifecycle_role=role,
                rationale="stored last_identity_decision_id is not the merge that produced the shadow",
            )
        if state.get("memory_state") != MERGED_AWAY_STATE:
            return _unresolved_row(
                element_id=element_id,
                node_id=node_id,
                field="last_identity_decision_id",
                stored_value=stored_value,
                decision=decision,
                redirect=redirect,
                lifecycle_role=role,
                rationale="merge source memory_state is not merged_away",
            )
        if state.get("identity_canon_state") != MERGED_AWAY_STATE:
            return _unresolved_row(
                element_id=element_id,
                node_id=node_id,
                field="last_identity_decision_id",
                stored_value=stored_value,
                decision=decision,
                redirect=redirect,
                lifecycle_role=role,
                rationale="merge source identity_canon_state is not merged_away",
            )
        rationale = (
            "reconstructable merge-source last_identity_decision_id from durable "
            "merge decision and active redirect"
        )
    else:
        reconstructed = decision.decision_id
        if stored_value != reconstructed:
            return _unresolved_row(
                element_id=element_id,
                node_id=node_id,
                field="last_identity_decision_id",
                stored_value=stored_value,
                decision=decision,
                lifecycle_role=role,
                rationale="stored last_identity_decision_id is not the merge that produced the shadow",
            )
        if state.get("identity_canon_state") != CANONICAL_SURVIVOR_STATE:
            return _unresolved_row(
                element_id=element_id,
                node_id=node_id,
                field="last_identity_decision_id",
                stored_value=stored_value,
                decision=decision,
                lifecycle_role=role,
                rationale="merge survivor identity_canon_state is not canonical",
            )
        rationale = (
            "reconstructable merge-survivor last_identity_decision_id from durable "
            "merge decision target"
        )
    return IdentityLifecycleShadowRowV1(
        element_id=element_id,
        node_id=node_id,
        field="last_identity_decision_id",
        stored_value=stored_value,
        decision_id=decision.decision_id,
        decision_kind=decision.decision_kind,
        decision_status=decision.status,
        subject_node_id=decision.subject_node_id,
        target_node_id=decision.target_node_id,
        redirect_id=None if redirect is None else _redirect_attr(redirect, "redirect_id"),
        redirect_status=None if redirect is None else _redirect_attr(redirect, "status"),
        lifecycle_role=role,
        reconstructable=True,
        rationale=rationale,
    )


def _prove_merged_into(
    *,
    store: Any,
    node_id: str,
    stored_value: Any,
    decisions: dict[str, IdentityDecisionRecord],
) -> IdentityLifecycleShadowRowV1:
    element_id = identity_lifecycle_element_id(node_id, "merged_into")
    nodes = getattr(store, "nodes", None) or {}
    if not isinstance(stored_value, str) or not stored_value.strip():
        return _unresolved_row(
            element_id=element_id,
            node_id=node_id,
            field="merged_into",
            stored_value=stored_value,
            rationale="merged_into is not a nonblank node id",
        )
    if stored_value not in nodes:
        return _unresolved_row(
            element_id=element_id,
            node_id=node_id,
            field="merged_into",
            stored_value=stored_value,
            rationale=f"dangling merged_into target {stored_value!r}",
        )
    state = _node_state(nodes[node_id])
    pointer = state.get("last_identity_decision_id")
    if not isinstance(pointer, str) or not pointer.strip():
        return _unresolved_row(
            element_id=element_id,
            node_id=node_id,
            field="merged_into",
            stored_value=stored_value,
            rationale="merged_into node has no resolvable last_identity_decision_id",
        )
    decision = decisions.get(pointer)
    if decision is None:
        return _unresolved_row(
            element_id=element_id,
            node_id=node_id,
            field="merged_into",
            stored_value=stored_value,
            rationale=f"dangling last_identity_decision_id {pointer!r} on merged_into node",
        )
    if decision.decision_kind != SUPPORTED_DECISION_KIND:
        return _unresolved_row(
            element_id=element_id,
            node_id=node_id,
            field="merged_into",
            stored_value=stored_value,
            decision=decision,
            rationale=(
                f"decision kind {decision.decision_kind!r} is not covered by the "
                "merge-shadow proof"
            ),
        )
    if decision.subject_node_id != node_id or decision.target_node_id != stored_value:
        return _unresolved_row(
            element_id=element_id,
            node_id=node_id,
            field="merged_into",
            stored_value=stored_value,
            decision=decision,
            lifecycle_role="merge_source",
            rationale="merged_into disagrees with merge decision subject/target",
        )
    active = _active_redirects_from(store, node_id)
    if len(active) > 1:
        return _unresolved_row(
            element_id=element_id,
            node_id=node_id,
            field="merged_into",
            stored_value=stored_value,
            decision=decision,
            lifecycle_role="merge_source",
            rationale="multiple conflicting active redirects from merged-away source",
        )
    if len(active) != 1:
        return _unresolved_row(
            element_id=element_id,
            node_id=node_id,
            field="merged_into",
            stored_value=stored_value,
            decision=decision,
            lifecycle_role="merge_source",
            rationale="merged_into source has no current active identity redirect",
        )
    redirect = active[0]
    if (
        _redirect_attr(redirect, "from_node_id") != node_id
        or _redirect_attr(redirect, "to_node_id") != stored_value
    ):
        return _unresolved_row(
            element_id=element_id,
            node_id=node_id,
            field="merged_into",
            stored_value=stored_value,
            decision=decision,
            redirect=redirect,
            lifecycle_role="merge_source",
            rationale="merged_into disagrees with active redirect authority",
        )
    if state.get("memory_state") != MERGED_AWAY_STATE:
        return _unresolved_row(
            element_id=element_id,
            node_id=node_id,
            field="merged_into",
            stored_value=stored_value,
            decision=decision,
            redirect=redirect,
            lifecycle_role="merge_source",
            rationale="merged-away source memory_state is not merged_away",
        )
    if state.get("identity_canon_state") != MERGED_AWAY_STATE:
        return _unresolved_row(
            element_id=element_id,
            node_id=node_id,
            field="merged_into",
            stored_value=stored_value,
            decision=decision,
            redirect=redirect,
            lifecycle_role="merge_source",
            rationale="merged-away source identity_canon_state is not merged_away",
        )
    reconstructed = decision.target_node_id
    if stored_value != reconstructed or stored_value != _redirect_attr(redirect, "to_node_id"):
        return _unresolved_row(
            element_id=element_id,
            node_id=node_id,
            field="merged_into",
            stored_value=stored_value,
            decision=decision,
            redirect=redirect,
            lifecycle_role="merge_source",
            rationale="stored merged_into is not reconstructable from decision/redirect target",
        )
    return IdentityLifecycleShadowRowV1(
        element_id=element_id,
        node_id=node_id,
        field="merged_into",
        stored_value=stored_value,
        decision_id=decision.decision_id,
        decision_kind=decision.decision_kind,
        decision_status=decision.status,
        subject_node_id=decision.subject_node_id,
        target_node_id=decision.target_node_id,
        redirect_id=_redirect_attr(redirect, "redirect_id"),
        redirect_status=_redirect_attr(redirect, "status"),
        lifecycle_role="merge_source",
        reconstructable=True,
        rationale=(
            "reconstructable merged_into from merge decision target and active redirect"
        ),
    )


def _prove_identity_state(
    *,
    store: Any,
    node_id: str,
    stored_value: Any,
    decisions: dict[str, IdentityDecisionRecord],
) -> IdentityLifecycleShadowRowV1:
    element_id = identity_lifecycle_element_id(node_id, "identity_state")
    if stored_value != SUPPORTED_IDENTITY_STATE:
        return _unresolved_row(
            element_id=element_id,
            node_id=node_id,
            field="identity_state",
            stored_value=stored_value,
            rationale=(
                f"identity_state {stored_value!r} is not proven by the current "
                "merge-survivor lifecycle semantics"
            ),
        )
    state = _node_state(store.nodes[node_id])
    pointer = state.get("last_identity_decision_id")
    if not isinstance(pointer, str) or not pointer.strip():
        return _unresolved_row(
            element_id=element_id,
            node_id=node_id,
            field="identity_state",
            stored_value=stored_value,
            rationale="identity_state node has no resolvable last_identity_decision_id",
        )
    decision = decisions.get(pointer)
    if decision is None:
        return _unresolved_row(
            element_id=element_id,
            node_id=node_id,
            field="identity_state",
            stored_value=stored_value,
            rationale=f"dangling last_identity_decision_id {pointer!r} on identity_state node",
        )
    if decision.decision_kind != SUPPORTED_DECISION_KIND:
        return _unresolved_row(
            element_id=element_id,
            node_id=node_id,
            field="identity_state",
            stored_value=stored_value,
            decision=decision,
            rationale=(
                f"decision kind {decision.decision_kind!r} is not covered by the "
                "merge-shadow proof"
            ),
        )
    if decision.target_node_id != node_id:
        return _unresolved_row(
            element_id=element_id,
            node_id=node_id,
            field="identity_state",
            stored_value=stored_value,
            decision=decision,
            rationale="identity_state node is not the surviving target of the merge decision",
        )
    if state.get("identity_canon_state") != CANONICAL_SURVIVOR_STATE:
        return _unresolved_row(
            element_id=element_id,
            node_id=node_id,
            field="identity_state",
            stored_value=stored_value,
            decision=decision,
            lifecycle_role="merge_survivor",
            rationale="survivor identity_canon_state is not canonical",
        )
    reconstructed = SUPPORTED_IDENTITY_STATE
    if stored_value != reconstructed:
        return _unresolved_row(
            element_id=element_id,
            node_id=node_id,
            field="identity_state",
            stored_value=stored_value,
            decision=decision,
            lifecycle_role="merge_survivor",
            rationale="stored identity_state is not the role implied by the proven merge",
        )
    return IdentityLifecycleShadowRowV1(
        element_id=element_id,
        node_id=node_id,
        field="identity_state",
        stored_value=stored_value,
        decision_id=decision.decision_id,
        decision_kind=decision.decision_kind,
        decision_status=decision.status,
        subject_node_id=decision.subject_node_id,
        target_node_id=decision.target_node_id,
        redirect_id=None,
        redirect_status=None,
        lifecycle_role="merge_survivor",
        reconstructable=True,
        rationale=(
            "reconstructable identity_state=survivor from merge decision target "
            "and canonical identity_canon_state"
        ),
    )


def prove_identity_lifecycle_history_v1(
    store: Any,
    *,
    world_id: str,
    canonical_revision_id: str,
    canonical_graph_payload_sha256: str,
    expected_field_counts: dict[str, int] | None = None,
) -> IdentityLifecycleHistoryConformanceV1:
    """Prove candidate identity-lifecycle shadow fields from the loaded store."""
    decisions = _index_identity_decisions(store)
    candidates = collect_identity_lifecycle_candidates(store)
    field_counts = _field_counts(candidates)
    if expected_field_counts is not None and field_counts != dict(expected_field_counts):
        raise _fail(
            (
                "identity lifecycle field-family inventory drifted: "
                f"observed={field_counts} expected={dict(expected_field_counts)}"
            ),
            "stale_identity_shadow_inventory",
        )

    rows: list[IdentityLifecycleShadowRowV1] = []
    for element_id, node_id, field, stored_value in candidates:
        if field == "last_identity_decision_id":
            row = _prove_last_identity_decision_id(
                store=store,
                node_id=node_id,
                stored_value=stored_value,
                decisions=decisions,
            )
        elif field == "merged_into":
            row = _prove_merged_into(
                store=store,
                node_id=node_id,
                stored_value=stored_value,
                decisions=decisions,
            )
        else:
            row = _prove_identity_state(
                store=store,
                node_id=node_id,
                stored_value=stored_value,
                decisions=decisions,
            )
        if row.element_id != element_id:
            raise _fail(
                f"proof row element_id drifted {row.element_id!r} != {element_id!r}",
                "identity_lifecycle_element_id_mismatch",
            )
        rows.append(row)

    unresolved = [row.element_id for row in rows if not row.reconstructable]
    element_ids = [row.element_id for row in rows]
    reconstructable_count = sum(1 for row in rows if row.reconstructable)
    passed = not unresolved and reconstructable_count == len(rows)
    return IdentityLifecycleHistoryConformanceV1(
        world_id=world_id,
        canonical_revision_id=canonical_revision_id,
        canonical_graph_payload_sha256=canonical_graph_payload_sha256,
        rows=rows,
        field_counts=field_counts,
        element_ids=element_ids,
        reconstructable_count=reconstructable_count,
        unresolved_element_ids=unresolved,
        passed=passed,
    )


def _decision_affects_node(decision: IdentityDecisionRecord, node_id: str) -> bool:
    return node_id in {
        decision.subject_node_id,
        decision.target_node_id,
        *(decision.affected_node_ids or []),
    }


def _alias_listed_on_merge(alias: str, merge: IdentityDecisionRecord) -> bool:
    side_effects = merge.merge_side_effects
    if side_effects is None:
        return False
    wanted = alias.casefold()
    return any(
        str(item).casefold() == wanted for item in side_effects.aliases_added_to_target
    )


def _unresolved_lineage(rationale: str) -> AliasRemoveSurvivorLineage:
    return AliasRemoveSurvivorLineage(reconstructable=False, rationale=rationale)


def prove_alias_remove_survivor_lineage(
    store: Any,
    node_id: str,
    *,
    ledger: IdentityDecisionLedger | None = None,
) -> AliasRemoveSurvivorLineage:
    """Prove one survivor's current alias_remove pointer from ordered merge history."""
    loaded = ledger if ledger is not None else _load_identity_decision_ledger(store)
    nodes = getattr(store, "nodes", None) or {}
    if node_id not in nodes:
        return _unresolved_lineage(f"unknown survivor node {node_id!r}")
    state = _node_state(nodes[node_id])
    pointer = state.get("last_identity_decision_id")
    if not isinstance(pointer, str) or not pointer.strip():
        return _unresolved_lineage(
            "survivor last_identity_decision_id is not a nonblank string"
        )
    current = loaded.by_id.get(pointer)
    if current is None:
        return _unresolved_lineage(f"dangling last_identity_decision_id {pointer!r}")
    if current.decision_kind != ALIAS_REMOVE_DECISION_KIND:
        return _unresolved_lineage(
            f"decision kind {current.decision_kind!r} is not alias_remove"
        )
    if current.status != "active":
        return _unresolved_lineage(
            f"identity decision status {current.status!r} is not active"
        )
    if current.subject_node_id != node_id:
        return _unresolved_lineage("alias_remove subject is not the current node")
    if node_id not in list(current.affected_node_ids or []):
        return _unresolved_lineage("current node is not in alias_remove affected_node_ids")
    if current.target_node_id is not None:
        return _unresolved_lineage("alias_remove target_node_id must be None")
    if not isinstance(current.alias, str) or not current.alias.strip():
        return _unresolved_lineage("alias_remove alias is not a nonblank string")
    if pointer != current.decision_id:
        return _unresolved_lineage(
            "stored last_identity_decision_id is not the alias_remove decision id"
        )

    remove_pos = loaded.position[current.decision_id]
    earlier_target_merges = [
        decision
        for decision in loaded.ordered
        if loaded.position[decision.decision_id] < remove_pos
        and decision.status == "active"
        and decision.decision_kind == SUPPORTED_DECISION_KIND
        and decision.target_node_id == current.subject_node_id
    ]
    if any(merge.merge_side_effects is None for merge in earlier_target_merges):
        return _unresolved_lineage(
            "earlier merge into this survivor is missing merge_side_effects"
        )
    causal = [
        merge
        for merge in earlier_target_merges
        if _alias_listed_on_merge(current.alias, merge)
    ]
    if not causal:
        return _unresolved_lineage(
            "alias_remove has no earlier causal merge that added that alias"
        )
    if len(causal) != 1:
        return _unresolved_lineage(
            "alias_remove has multiple earlier causal merges for that alias"
        )
    merge = causal[0]
    merge_pos = loaded.position[merge.decision_id]
    if merge_pos >= remove_pos:
        return _unresolved_lineage(
            "causal merge is not earlier than alias_remove in durable decision order"
        )

    source_id = merge.subject_node_id
    if not isinstance(source_id, str) or source_id not in nodes:
        return _unresolved_lineage("causal merge source node does not exist")
    source_state = _node_state(nodes[source_id])
    if source_state.get("memory_state") != MERGED_AWAY_STATE:
        return _unresolved_lineage("causal merge source memory_state is not merged_away")
    if source_state.get("identity_canon_state") != MERGED_AWAY_STATE:
        return _unresolved_lineage(
            "causal merge source identity_canon_state is not merged_away"
        )
    if source_state.get("merged_into") != node_id:
        return _unresolved_lineage("causal merge source merged_into is not the survivor")
    if source_state.get("last_identity_decision_id") != merge.decision_id:
        return _unresolved_lineage(
            "causal merge source last_identity_decision_id is not the proving merge"
        )
    active = _active_redirects_from(store, source_id)
    if len(active) != 1:
        return _unresolved_lineage(
            "causal merge source does not have exactly one active identity redirect"
        )
    redirect = active[0]
    if _redirect_attr(redirect, "to_node_id") != node_id:
        return _unresolved_lineage(
            "causal merge source redirect does not point at the survivor"
        )

    if state.get("identity_canon_state") != CANONICAL_SURVIVOR_STATE:
        return _unresolved_lineage("survivor identity_canon_state is not canonical")
    if state.get("identity_state") != SUPPORTED_IDENTITY_STATE:
        return _unresolved_lineage("survivor identity_state is not survivor")

    for decision in loaded.ordered:
        pos = loaded.position[decision.decision_id]
        if not (merge_pos < pos < remove_pos):
            continue
        if decision.status != "active":
            continue
        if decision.decision_kind not in INVALIDATING_BETWEEN_DECISION_KINDS:
            continue
        if _decision_affects_node(decision, node_id):
            return _unresolved_lineage(
                f"invalidating {decision.decision_kind} {decision.decision_id} "
                "between causal merge and alias_remove"
            )

    for decision in loaded.ordered:
        pos = loaded.position[decision.decision_id]
        if pos <= remove_pos:
            continue
        if decision.status != "active":
            continue
        if decision.decision_kind not in STATE_MUTATING_DECISION_KINDS:
            continue
        if _decision_affects_node(decision, node_id):
            return _unresolved_lineage(
                "last_identity_decision_id is stale; later "
                f"{decision.decision_kind} {decision.decision_id} affects the survivor"
            )

    return AliasRemoveSurvivorLineage(
        reconstructable=True,
        rationale=(
            f"validated alias_remove {current.decision_id} against earlier causal "
            f"merge {merge.decision_id} using durable decision-list order"
        ),
        current=current,
        causal_merge=merge,
    )


def _row_from_alias_remove_lineage(
    *,
    field: CandidateField,
    node_id: str,
    stored_value: Any,
    lineage: AliasRemoveSurvivorLineage,
) -> IdentityLifecycleShadowRowV1:
    element_id = identity_lifecycle_element_id(node_id, field)
    if not lineage.reconstructable or lineage.current is None or lineage.causal_merge is None:
        return _unresolved_row(
            element_id=element_id,
            node_id=node_id,
            field=field,
            stored_value=stored_value,
            rationale=lineage.rationale,
            decision=lineage.current,
            lifecycle_role="merge_survivor",
        )
    current = lineage.current
    if field == "last_identity_decision_id":
        rationale = (
            "reconstructable merge-survivor last_identity_decision_id from later "
            f"alias_remove {current.decision_id} whose alias was introduced by "
            f"earlier merge {lineage.causal_merge.decision_id}"
        )
    else:
        rationale = (
            "reconstructable identity_state=survivor from causal merge "
            f"{lineage.causal_merge.decision_id} plus later alias_remove "
            f"{current.decision_id}"
        )
    return IdentityLifecycleShadowRowV1(
        element_id=element_id,
        node_id=node_id,
        field=field,
        stored_value=stored_value,
        decision_id=current.decision_id,
        decision_kind=current.decision_kind,
        decision_status=current.status,
        subject_node_id=current.subject_node_id,
        target_node_id=current.target_node_id,
        redirect_id=None,
        redirect_status=None,
        lifecycle_role="merge_survivor",
        reconstructable=True,
        rationale=rationale,
    )


def _prove_last_identity_decision_id_through_alias_remove(
    *,
    store: Any,
    node_id: str,
    stored_value: Any,
    decisions: dict[str, IdentityDecisionRecord],
    ledger: IdentityDecisionLedger,
    lineage_cache: dict[str, AliasRemoveSurvivorLineage],
) -> IdentityLifecycleShadowRowV1:
    merge_row = _prove_last_identity_decision_id(
        store=store,
        node_id=node_id,
        stored_value=stored_value,
        decisions=decisions,
    )
    if merge_row.reconstructable:
        return merge_row
    decision = None if not isinstance(stored_value, str) else ledger.by_id.get(stored_value)
    if decision is None or decision.decision_kind != ALIAS_REMOVE_DECISION_KIND:
        return merge_row
    lineage = lineage_cache.setdefault(
        node_id,
        prove_alias_remove_survivor_lineage(store, node_id, ledger=ledger),
    )
    return _row_from_alias_remove_lineage(
        field="last_identity_decision_id",
        node_id=node_id,
        stored_value=stored_value,
        lineage=lineage,
    )


def _prove_identity_state_through_alias_remove(
    *,
    store: Any,
    node_id: str,
    stored_value: Any,
    decisions: dict[str, IdentityDecisionRecord],
    ledger: IdentityDecisionLedger,
    lineage_cache: dict[str, AliasRemoveSurvivorLineage],
) -> IdentityLifecycleShadowRowV1:
    merge_row = _prove_identity_state(
        store=store,
        node_id=node_id,
        stored_value=stored_value,
        decisions=decisions,
    )
    if merge_row.reconstructable:
        return merge_row
    state = _node_state((getattr(store, "nodes", None) or {}).get(node_id) or {})
    pointer = state.get("last_identity_decision_id")
    decision = None if not isinstance(pointer, str) else ledger.by_id.get(pointer)
    if decision is None or decision.decision_kind != ALIAS_REMOVE_DECISION_KIND:
        return merge_row
    lineage = lineage_cache.setdefault(
        node_id,
        prove_alias_remove_survivor_lineage(store, node_id, ledger=ledger),
    )
    return _row_from_alias_remove_lineage(
        field="identity_state",
        node_id=node_id,
        stored_value=stored_value,
        lineage=lineage,
    )


def prove_identity_lifecycle_history_through_alias_remove(
    store: Any,
    *,
    world_id: str,
    canonical_revision_id: str,
    canonical_graph_payload_sha256: str,
    expected_field_counts: dict[str, int] | None = None,
) -> IdentityLifecycleHistoryConformanceV1:
    """Prove identity-lifecycle shadow including ordered merge then alias_remove."""
    ledger = _load_identity_decision_ledger(store)
    decisions = ledger.by_id
    candidates = collect_identity_lifecycle_candidates(store)
    field_counts = _field_counts(candidates)
    if expected_field_counts is not None and field_counts != dict(expected_field_counts):
        raise _fail(
            (
                "identity lifecycle field-family inventory drifted: "
                f"observed={field_counts} expected={dict(expected_field_counts)}"
            ),
            "stale_identity_shadow_inventory",
        )

    lineage_cache: dict[str, AliasRemoveSurvivorLineage] = {}
    rows: list[IdentityLifecycleShadowRowV1] = []
    for element_id, node_id, field, stored_value in candidates:
        if field == "last_identity_decision_id":
            row = _prove_last_identity_decision_id_through_alias_remove(
                store=store,
                node_id=node_id,
                stored_value=stored_value,
                decisions=decisions,
                ledger=ledger,
                lineage_cache=lineage_cache,
            )
        elif field == "merged_into":
            row = _prove_merged_into(
                store=store,
                node_id=node_id,
                stored_value=stored_value,
                decisions=decisions,
            )
        else:
            row = _prove_identity_state_through_alias_remove(
                store=store,
                node_id=node_id,
                stored_value=stored_value,
                decisions=decisions,
                ledger=ledger,
                lineage_cache=lineage_cache,
            )
        if row.element_id != element_id:
            raise _fail(
                f"proof row element_id drifted {row.element_id!r} != {element_id!r}",
                "identity_lifecycle_element_id_mismatch",
            )
        rows.append(row)

    unresolved = [row.element_id for row in rows if not row.reconstructable]
    element_ids = [row.element_id for row in rows]
    reconstructable_count = sum(1 for row in rows if row.reconstructable)
    passed = not unresolved and reconstructable_count == len(rows)
    return IdentityLifecycleHistoryConformanceV1(
        world_id=world_id,
        canonical_revision_id=canonical_revision_id,
        canonical_graph_payload_sha256=canonical_graph_payload_sha256,
        rows=rows,
        field_counts=field_counts,
        element_ids=element_ids,
        reconstructable_count=reconstructable_count,
        unresolved_element_ids=unresolved,
        passed=passed,
    )
