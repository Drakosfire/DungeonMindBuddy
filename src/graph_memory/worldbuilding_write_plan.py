"""Deterministic, inert write plans for reviewed worldbuilding candidates.

This module deliberately stops before every durable graph operation.  It reads
one pinned World Graph revision, validates explicit dispositions for the exact
candidate graph, and returns a response-carried effect for a later capability
to confirm.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

import graph_memory.kernel as kernel
from graph_memory.candidate_graph_preview import (
    CandidateEdge,
    CandidateGraphPreview,
    CandidateNode,
)
from graph_memory.candidate_graph_to_contribution import (
    CandidateGraphMappingError,
    kernel_kind_for_node_type,
    map_candidate_edge_to_assertion,
    map_candidate_node_to_assertion,
    map_connect_existing_support_assertions,
    require_single_verified_source_artifact,
)
from graph_memory.candidate_semantic_promote_matrix import (
    CandidateSemanticPromoteError,
    map_reviewed_worldbuilding_semantics_to_kernel,
    semantic_diagnostics,
)
from graph_memory.extraction.worldbuilding_extraction_profile import (
    WORLDBUILDING_PROFILE_ID,
    WORLDBUILDING_PROFILE_VERSION,
)
from graph_memory.kernel.contribution_models import (
    ContributionIdentityMention,
    GraphContribution,
    GraphContributionAssertion,
)
from graph_memory.kernel.contributions import build_assertion, create_graph_contribution
from graph_memory.union_supergraph.model import (
    UnionSupergraphNode,
    UnionSupergraphStore,
)
from graph_memory.union_supergraph.redirects import active_identity_redirect_map


WORLD_BUILDING_WRITE_PLAN_SCHEMA = "dmb_worldbuilding_write_plan_v1"
WORLD_BUILDING_WRITE_PLAN_VERSION = 1
WORLD_BUILDING_WRITE_PLAN_AUTHORED_BY = "live_control:worldbuilding_write_plan"
WORLD_BUILDING_WRITE_PLAN_SOURCE_KIND = "source_extraction"
WORLDBUILDING_EXTRACTION_PROFILE = (
    f"{WORLDBUILDING_PROFILE_ID}@{WORLDBUILDING_PROFILE_VERSION}"
)
_FIXED_PRODUCED_AT = "1970-01-01T00:00:00Z"

_NODE_DECISIONS = frozenset({"create_new", "bind_existing", "reject", "defer"})
_EDGE_DECISIONS = frozenset({"accept", "reject", "defer"})
WORLDBUILDING_BIND_SUPPORT_PREDICATE = "worldbuilding_observation"
_WORLDBUILDING_CONFIRMABLE_REASON = (
    "BLD-10a prepares an inert write plan; graph confirmation is not implemented."
)
_MISSING = object()


class WorldbuildingWritePlanError(ValueError):
    """Stable fail-closed error raised while constructing a write plan."""

    def __init__(
        self,
        message: str,
        *,
        code: str = "invalid_disposition_set",
        status_code: int = 422,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.status_code = status_code


@dataclass(frozen=True)
class WorldbuildingDispositionInput:
    assertion_id: str
    decision: str
    target_node_id: str | None = None


@dataclass(frozen=True)
class WorldbuildingWritePlanVerificationContext:
    """Server-resolved identity inputs for rebuild verification.

    Response-carried envelope fields are compared to this context; they must
    never be fed back as rebuild authority.
    """

    world_id: str
    parent_revision_id: str
    run_id: str
    source_artifact_id: str
    source_revision_id: str
    source_uri: str
    extraction_profile: str
    campaign_scope: str | None


@dataclass(frozen=True)
class WorldbuildingWritePlan:
    """The authority fields of one response-carried inert plan."""

    plan_id: str
    plan_digest: str
    decision_digest: str
    world_id: str
    parent_revision_id: str
    run_id: str
    source_artifact_id: str
    source_revision_id: str
    extraction_profile: str
    candidate_preview_id: str
    candidate_schema: str
    candidate_version: str
    effect: dict[str, Any]
    summary: dict[str, int]
    diagnostics: list[str]


def _canonical_json(payload: object) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _digest(payload: object) -> str:
    return f"sha256:{hashlib.sha256(_canonical_json(payload).encode('utf-8')).hexdigest()}"


def _camel_key(name: str) -> str:
    parts = name.split("_")
    return parts[0] + "".join(part[:1].upper() + part[1:] for part in parts[1:])


def _field(
    payload: Mapping[str, Any],
    name: str,
    *,
    optional: bool = False,
) -> Any:
    keys = tuple(
        dict.fromkeys(
            ("schema", "schema_") if name == "schema" else (name, _camel_key(name))
        )
    )
    present = [key for key in keys if key in payload]
    if len(present) > 1:
        raise WorldbuildingWritePlanError(
            f"plan contains duplicate aliases for {name}",
            code="plan_verification_failed",
        )
    if not present:
        if optional:
            return _MISSING
        raise WorldbuildingWritePlanError(
            f"plan is missing {name}",
            code="plan_verification_failed",
        )
    return payload[present[0]]


def _canonical_fields(
    payload: Any,
    names: Sequence[str],
    *,
    context: str,
) -> dict[str, Any]:
    if not isinstance(payload, Mapping):
        raise WorldbuildingWritePlanError(
            f"{context} must be an object",
            code="plan_verification_failed",
        )
    result: dict[str, Any] = {}
    for name in names:
        try:
            result[name] = _field(payload, name)
        except WorldbuildingWritePlanError as exc:
            raise WorldbuildingWritePlanError(
                f"{context}: {exc}",
                code="plan_verification_failed",
            ) from exc
    recognized = {
        key
        for name in names
        for key in ((("schema", "schema_") if name == "schema" else (name, _camel_key(name))))
    }
    unknown = sorted(set(payload) - recognized)
    if unknown:
        raise WorldbuildingWritePlanError(
            f"{context} contains unsupported fields: {unknown!r}",
            code="plan_verification_failed",
        )
    return result


def _require_string(value: Any, *, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise WorldbuildingWritePlanError(
            f"{field} must be a non-blank string",
            code="plan_verification_failed",
        )
    return value


def _canonical_assertion_list(value: Any, *, field: str) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        raise WorldbuildingWritePlanError(
            f"{field} must be a list",
            code="plan_verification_failed",
        )
    result: list[dict[str, Any]] = []
    for index, item in enumerate(value):
        if not isinstance(item, Mapping):
            raise WorldbuildingWritePlanError(
                f"{field}[{index}] must be an object",
                code="plan_verification_failed",
            )
        try:
            assertion = GraphContributionAssertion.model_validate(item)
        except Exception as exc:  # noqa: BLE001 — verifier fails closed
            raise WorldbuildingWritePlanError(
                f"{field}[{index}] is not a valid GraphContributionAssertion",
                code="plan_verification_failed",
            ) from exc
        result.append(assertion.model_dump(mode="json"))
    return result


def _canonical_mention_list(value: Any, *, field: str) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        raise WorldbuildingWritePlanError(
            f"{field} must be a list",
            code="plan_verification_failed",
        )
    result: list[dict[str, Any]] = []
    for index, item in enumerate(value):
        if not isinstance(item, Mapping):
            raise WorldbuildingWritePlanError(
                f"{field}[{index}] must be an object",
                code="plan_verification_failed",
            )
        try:
            mention = ContributionIdentityMention.model_validate(item)
        except Exception as exc:  # noqa: BLE001 — verifier fails closed
            raise WorldbuildingWritePlanError(
                f"{field}[{index}] is not a valid ContributionIdentityMention",
                code="plan_verification_failed",
            ) from exc
        result.append(mention.model_dump(mode="json"))
    return result


def _canonical_string_list(value: Any, *, field: str) -> list[str]:
    if not isinstance(value, list) or any(
        not isinstance(item, str) or not item.strip() for item in value
    ):
        raise WorldbuildingWritePlanError(
            f"{field} must be a list of non-blank strings",
            code="plan_verification_failed",
        )
    return list(value)


def _canonical_string_map(value: Any, *, field: str) -> dict[str, str]:
    if not isinstance(value, Mapping):
        raise WorldbuildingWritePlanError(
            f"{field} must be an object",
            code="plan_verification_failed",
        )
    result: dict[str, str] = {}
    for key, item in value.items():
        if (
            not isinstance(key, str)
            or not key.strip()
            or not isinstance(item, str)
            or not item.strip()
        ):
            raise WorldbuildingWritePlanError(
                f"{field} must contain non-blank string keys and values",
                code="plan_verification_failed",
            )
        result[key] = item
    return result


def _canonical_candidate_effect_map(value: Any) -> dict[str, list[str]]:
    if not isinstance(value, Mapping):
        raise WorldbuildingWritePlanError(
            "effect.candidate_effect_map must be an object",
            code="plan_verification_failed",
        )
    result: dict[str, list[str]] = {}
    for key, item in value.items():
        if not isinstance(key, str) or not key.strip():
            raise WorldbuildingWritePlanError(
                "effect.candidate_effect_map keys must be non-blank strings",
                code="plan_verification_failed",
            )
        if not isinstance(item, list):
            raise WorldbuildingWritePlanError(
                f"effect.candidate_effect_map[{key!r}] must be a list",
                code="plan_verification_failed",
            )
        assertion_ids: list[str] = []
        for index, assertion_id in enumerate(item):
            if not isinstance(assertion_id, str) or not assertion_id.strip():
                raise WorldbuildingWritePlanError(
                    f"effect.candidate_effect_map[{key!r}][{index}] must be "
                    "a non-blank string",
                    code="plan_verification_failed",
                )
            assertion_ids.append(assertion_id)
        if len(set(assertion_ids)) != len(assertion_ids):
            raise WorldbuildingWritePlanError(
                f"effect.candidate_effect_map[{key!r}] has duplicate assertion IDs",
                code="plan_verification_failed",
            )
        result[key] = assertion_ids
    return dict(sorted(result.items()))


def _canonical_decision_snapshot(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        raise WorldbuildingWritePlanError(
            "effect.decision_snapshot must be a list",
            code="plan_verification_failed",
        )
    result: list[dict[str, Any]] = []
    for index, item in enumerate(value):
        canonical = _canonical_fields(
            item,
            ("assertion_id", "candidate_kind", "decision", "target_node_id"),
            context=f"effect.decision_snapshot[{index}]",
        )
        assertion_id = _require_string(
            canonical["assertion_id"],
            field=f"effect.decision_snapshot[{index}].assertion_id",
        )
        candidate_kind = _require_string(
            canonical["candidate_kind"],
            field=f"effect.decision_snapshot[{index}].candidate_kind",
        )
        decision = _require_string(
            canonical["decision"],
            field=f"effect.decision_snapshot[{index}].decision",
        )
        target = canonical["target_node_id"]
        if target is not None and (
            not isinstance(target, str) or not target.strip()
        ):
            raise WorldbuildingWritePlanError(
                f"effect.decision_snapshot[{index}].target_node_id must be null "
                "or a non-blank string",
                code="plan_verification_failed",
            )
        if candidate_kind == "node":
            allowed = _NODE_DECISIONS
        elif candidate_kind == "edge":
            allowed = _EDGE_DECISIONS
        else:
            raise WorldbuildingWritePlanError(
                f"unsupported candidate_kind {candidate_kind!r}",
                code="plan_verification_failed",
            )
        if decision not in allowed:
            raise WorldbuildingWritePlanError(
                f"decision {decision!r} is invalid for {candidate_kind}",
                code="plan_verification_failed",
            )
        if (decision == "bind_existing") != (target is not None):
            raise WorldbuildingWritePlanError(
                f"target_node_id does not match {decision!r}",
                code="plan_verification_failed",
            )
        result.append(
            {
                "assertion_id": assertion_id,
                "candidate_kind": candidate_kind,
                "decision": decision,
                "target_node_id": target,
            }
        )
    if len({item["assertion_id"] for item in result}) != len(result):
        raise WorldbuildingWritePlanError(
            "effect.decision_snapshot contains duplicate assertion IDs",
            code="plan_verification_failed",
        )
    if result != sorted(
        result,
        key=lambda item: (
            0 if item["candidate_kind"] == "node" else 1,
            item["assertion_id"],
        ),
    ):
        raise WorldbuildingWritePlanError(
            "effect.decision_snapshot is not canonically ordered",
            code="plan_verification_failed",
        )
    return result


def _canonical_effect(effect: Any) -> dict[str, Any]:
    canonical = _canonical_fields(
        effect,
        (
            "contribution_meta",
            "accepted_proposals",
            "rejected_assertions",
            "unresolved_mentions",
            "deferred_candidate_ids",
            "node_id_map",
            "identity_outcome_snapshot",
            "candidate_effect_map",
            "decision_snapshot",
        ),
        context="effect",
    )
    meta = _canonical_fields(
        canonical["contribution_meta"],
        (
            "source_kind",
            "source_artifact_id",
            "source_revision_id",
            "extraction_profile",
            "campaign_scope",
            "authored_by",
        ),
        context="effect.contribution_meta",
    )
    if meta["campaign_scope"] is not None and (
        not isinstance(meta["campaign_scope"], str)
        or not meta["campaign_scope"].strip()
    ):
        raise WorldbuildingWritePlanError(
            "effect.contribution_meta.campaign_scope must be null or non-blank",
            code="plan_verification_failed",
        )
    return {
        "contribution_meta": meta,
        "accepted_proposals": _canonical_assertion_list(
            canonical["accepted_proposals"],
            field="effect.accepted_proposals",
        ),
        "rejected_assertions": _canonical_assertion_list(
            canonical["rejected_assertions"],
            field="effect.rejected_assertions",
        ),
        "unresolved_mentions": _canonical_mention_list(
            canonical["unresolved_mentions"],
            field="effect.unresolved_mentions",
        ),
        "deferred_candidate_ids": _canonical_string_list(
            canonical["deferred_candidate_ids"],
            field="effect.deferred_candidate_ids",
        ),
        "node_id_map": _canonical_string_map(
            canonical["node_id_map"],
            field="effect.node_id_map",
        ),
        "identity_outcome_snapshot": _canonical_string_map(
            canonical["identity_outcome_snapshot"],
            field="effect.identity_outcome_snapshot",
        ),
        "candidate_effect_map": _canonical_candidate_effect_map(
            canonical["candidate_effect_map"]
        ),
        "decision_snapshot": _canonical_decision_snapshot(
            canonical["decision_snapshot"]
        ),
    }


def _nonblank(value: str | None, *, field: str) -> str:
    text = str(value or "").strip()
    if not text:
        raise WorldbuildingWritePlanError(
            f"{field} is required",
            code="invalid_request",
        )
    return text


def _disposition_input(raw: WorldbuildingDispositionInput | Mapping[str, Any]) -> WorldbuildingDispositionInput:
    if isinstance(raw, WorldbuildingDispositionInput):
        item = raw
    else:
        item = WorldbuildingDispositionInput(
            assertion_id=str(raw.get("assertion_id", raw.get("assertionId", ""))),
            decision=str(raw.get("decision", "")),
            target_node_id=(
                raw.get("target_node_id")
                if "target_node_id" in raw
                else raw.get("targetNodeId")
            ),
        )
    assertion_id = _nonblank(item.assertion_id, field="assertion_id")
    decision = str(item.decision or "").strip()
    target = item.target_node_id
    target = None if target is None else _nonblank(str(target), field="target_node_id")
    if decision == "bind_existing" and target is None:
        raise WorldbuildingWritePlanError(
            f"disposition {assertion_id!r} requires target_node_id for bind_existing",
            code="invalid_disposition",
        )
    if decision != "bind_existing" and target is not None:
        raise WorldbuildingWritePlanError(
            f"disposition {assertion_id!r} must not include target_node_id for {decision!r}",
            code="invalid_disposition",
        )
    return WorldbuildingDispositionInput(assertion_id, decision, target)


def _candidate_kind_map(
    preview: CandidateGraphPreview,
) -> tuple[dict[str, CandidateNode], dict[str, CandidateEdge]]:
    nodes = {node.node_id: node for node in preview.nodes}
    edges = {edge.edge_id: edge for edge in preview.edges}
    if len(nodes) != len(preview.nodes) or len(edges) != len(preview.edges):
        raise WorldbuildingWritePlanError(
            "candidate graph contains duplicate node or edge IDs",
            code="invalid_disposition_set",
        )
    overlap = set(nodes) & set(edges)
    if overlap:
        raise WorldbuildingWritePlanError(
            f"candidate graph reuses IDs across node and edge kinds: {sorted(overlap)}",
            code="invalid_disposition_set",
        )
    return nodes, edges


def _validate_dispositions(
    preview: CandidateGraphPreview,
    dispositions: Sequence[WorldbuildingDispositionInput | Mapping[str, Any]],
) -> tuple[
    dict[str, tuple[str, str | None]],
    list[dict[str, Any]],
    dict[str, CandidateNode],
    dict[str, CandidateEdge],
]:
    nodes, edges = _candidate_kind_map(preview)
    by_id: dict[str, tuple[str, str | None]] = {}
    for raw in dispositions:
        item = _disposition_input(raw)
        if item.assertion_id in by_id:
            raise WorldbuildingWritePlanError(
                f"duplicate disposition for assertion_id {item.assertion_id!r}",
                code="invalid_disposition_set",
            )
        if item.assertion_id in nodes:
            candidate_kind = "node"
            allowed = _NODE_DECISIONS
        elif item.assertion_id in edges:
            candidate_kind = "edge"
            allowed = _EDGE_DECISIONS
        else:
            raise WorldbuildingWritePlanError(
                f"unknown candidate assertion_id {item.assertion_id!r}",
                code="invalid_disposition_set",
            )
        if item.decision not in allowed:
            raise WorldbuildingWritePlanError(
                f"{candidate_kind} {item.assertion_id!r} does not permit "
                f"decision {item.decision!r}",
                code="invalid_disposition",
            )
        by_id[item.assertion_id] = (item.decision, item.target_node_id)

    expected = set(nodes) | set(edges)
    supplied = set(by_id)
    if supplied != expected:
        missing = sorted(expected - supplied)
        unknown = sorted(supplied - expected)
        raise WorldbuildingWritePlanError(
            f"disposition set must cover every candidate exactly once; "
            f"missing={missing!r} unknown={unknown!r}",
            code="invalid_disposition_set",
        )

    snapshot = [
        {
            "assertion_id": assertion_id,
            "candidate_kind": candidate_kind,
            "decision": by_id[assertion_id][0],
            "target_node_id": by_id[assertion_id][1],
        }
        for candidate_kind, candidates in (("node", nodes), ("edge", edges))
        for assertion_id in sorted(candidates)
    ]
    return by_id, snapshot, nodes, edges


def _candidate_kernel_kind(node: CandidateNode) -> str:
    return kernel_kind_for_node_type(node.node_type)


def _identity_canon_state(node: UnionSupergraphNode) -> str:
    return str(
        node.state.get("identity_canon_state")
        or node.state.get("canon_state")
        or ""
    ).strip()


def _assert_create_new_id_is_free(
    store: UnionSupergraphStore,
    node_id: str,
) -> None:
    redirects = active_identity_redirect_map(store.identity_redirects)
    if node_id in store.nodes or node_id in redirects:
        raise WorldbuildingWritePlanError(
            f"create_new node ID {node_id!r} already exists in the pinned parent",
            code="new_node_id_conflict",
            status_code=409,
        )
    if any(
        node_id in {redirect.from_node_id, redirect.to_node_id}
        for redirect in store.identity_redirects
    ):
        raise WorldbuildingWritePlanError(
            f"create_new node ID {node_id!r} conflicts with identity history",
            code="new_node_id_conflict",
            status_code=409,
        )


def _resolve_bind_target(
    store: UnionSupergraphStore,
    node: CandidateNode,
    target_node_id: str,
) -> UnionSupergraphNode:
    target = store.nodes.get(target_node_id)
    if target is None:
        raise WorldbuildingWritePlanError(
            f"bind_existing target {target_node_id!r} is not in the pinned parent",
            code="bind_target_missing",
            status_code=409,
        )
    redirects = active_identity_redirect_map(store.identity_redirects)
    canon = _identity_canon_state(target)
    memory = str(target.state.get("memory_state") or "").strip()
    if target_node_id in redirects:
        canonical_id = redirects[target_node_id].to_node_id
        raise WorldbuildingWritePlanError(
            f"bind_existing target {target_node_id!r} is a redirected source; "
            f"canonical target is {canonical_id!r}",
            code="bind_target_not_canonical",
            status_code=409,
        )
    if (
        memory in {"merged_away", "rejected"}
        or canon in {"merged_away", "rejected", "noncanonical_provisional"}
        or canon != "canonical"
    ):
        raise WorldbuildingWritePlanError(
            f"bind_existing target {target_node_id!r} is not an active canonical node",
            code="bind_target_not_canonical",
            status_code=409,
        )
    raw_type = (node.node_type or "").strip().lower()
    if raw_type in {"character", "pc", "npc"}:
        allowed_target_kinds = {"pc", "npc"}
    elif raw_type in {"collective", "organization", "party", "faction", "group"}:
        allowed_target_kinds = {"party", "faction"}
    else:
        allowed_target_kinds = {_candidate_kernel_kind(node)}
    target_kind = target.kind.strip().lower()
    if target_kind not in allowed_target_kinds:
        raise WorldbuildingWritePlanError(
            f"bind_existing target {target_node_id!r} kind {target.kind!r} "
            f"does not match candidate kind {_candidate_kernel_kind(node)!r}",
            code="bind_target_kind_mismatch",
            status_code=422,
        )
    return target


def _mapping_error(exc: Exception) -> WorldbuildingWritePlanError:
    return WorldbuildingWritePlanError(
        str(exc),
        code="mapping_error",
        status_code=422,
    )


def _map_node(
    node: CandidateNode,
    *,
    source_revision_id: str,
    source_artifact_id: str,
    campaign_scope: str | None,
    source_uri: str,
    acceptance_state: str,
    identity_resolution_outcome: str,
    subject_node_id: str | None = None,
) -> GraphContributionAssertion:
    try:
        return map_candidate_node_to_assertion(
            node,
            source_revision_id=source_revision_id,
            verified_source_artifact_id=source_artifact_id,
            campaign_scope=campaign_scope,
            campaign_id=campaign_scope,
            source_domain="worldbuilding",
            session_id=None,
            source_uri=source_uri,
            acceptance_state=acceptance_state,
            identity_resolution_outcome=identity_resolution_outcome,
            kind_override=_candidate_kernel_kind(node),
            subject_node_id_override=subject_node_id,
            semantic_mapper=map_reviewed_worldbuilding_semantics_to_kernel,
        )
    except (CandidateGraphMappingError, CandidateSemanticPromoteError) as exc:
        raise _mapping_error(exc) from exc


def _map_edge(
    edge: CandidateEdge,
    *,
    source_revision_id: str,
    source_artifact_id: str,
    campaign_scope: str | None,
    source_uri: str,
    acceptance_state: str,
    identity_resolution_outcome: str,
    node_id_map: Mapping[str, str] | None = None,
) -> GraphContributionAssertion:
    try:
        assertion = map_candidate_edge_to_assertion(
            edge,
            source_revision_id=source_revision_id,
            verified_source_artifact_id=source_artifact_id,
            campaign_scope=campaign_scope,
            campaign_id=campaign_scope,
            source_domain="worldbuilding",
            session_id=None,
            source_uri=source_uri,
            acceptance_state=acceptance_state,
            identity_resolution_outcome=identity_resolution_outcome,
            node_id_map=node_id_map,
            semantic_mapper=map_reviewed_worldbuilding_semantics_to_kernel,
        )
    except (CandidateGraphMappingError, CandidateSemanticPromoteError) as exc:
        raise _mapping_error(exc) from exc
    value = dict(assertion.value or {})
    value["extract_edge_id"] = edge.edge_id
    return build_assertion(
        assertion_kind=assertion.assertion_kind,
        acceptance_state=assertion.acceptance_state,
        subject_node_id=assertion.subject_node_id,
        target_node_id=assertion.target_node_id,
        predicate=assertion.predicate,
        label=assertion.label,
        value=value,
        evidence_ref_ids=list(assertion.evidence_ref_ids),
        source_artifact_id=assertion.source_artifact_id,
        source_revision_id=assertion.source_revision_id,
        campaign_scope=assertion.campaign_scope,
        temporal_scope=assertion.temporal_scope,
        visibility=assertion.visibility,
        epistemic_kind=assertion.epistemic_kind,
        identity_resolution_outcome=assertion.identity_resolution_outcome,
    )


def _deferred_node_mention(
    node: CandidateNode,
    assertion: GraphContributionAssertion,
) -> ContributionIdentityMention:
    return ContributionIdentityMention(
        mention_id=node.node_id,
        label=(node.label or node.node_id).strip(),
        object_kind=_candidate_kernel_kind(node),
        aliases=[str(alias).strip() for alias in node.aliases if str(alias).strip()],
        evidence_ref_ids=list(assertion.evidence_ref_ids),
        identity_resolution_outcome="deferred_by_operator",
        diagnostics=["operator_disposition:defer"],
        candidate_node_ids=[],
    )


def _load_pinned_parent(
    *,
    world_root: Path,
    world_id: str,
    expected_parent_revision_id: str,
) -> tuple[str, UnionSupergraphStore]:
    expected = _nonblank(
        expected_parent_revision_id, field="expected_parent_revision_id"
    )
    try:
        head, _revision, _current = kernel.open_current_world_graph(world_root, world_id)
    except (kernel.WorldGraphNotFoundError, ValueError) as exc:
        raise WorldbuildingWritePlanError(
            "The World Graph is not initialized.",
            code="world_not_initialized",
            status_code=409,
        ) from exc
    if head.head_revision_id != expected:
        raise WorldbuildingWritePlanError(
            "expected parent revision is not the current World Graph head",
            code="stale_parent_revision",
            status_code=409,
        )
    try:
        return expected, kernel.load_world_graph_revision(
            world_root, world_id, expected
        )
    except (kernel.WorldGraphNotFoundError, ValueError) as exc:
        raise WorldbuildingWritePlanError(
            "The expected World Graph revision is not readable.",
            code="world_not_initialized",
            status_code=409,
        ) from exc


def build_worldbuilding_write_plan(
    *,
    preview: CandidateGraphPreview,
    world_root: Path,
    world_id: str,
    expected_parent_revision_id: str,
    run_id: str,
    source_artifact_id: str,
    source_revision_id: str,
    source_uri: str,
    extraction_profile: str,
    campaign_scope: str | None,
    dispositions: Sequence[WorldbuildingDispositionInput | Mapping[str, Any]],
    self_verify: bool = True,
) -> WorldbuildingWritePlan:
    """Build one deterministic inert plan without any graph mutation."""
    world = _nonblank(world_id, field="world_id")
    run = _nonblank(run_id, field="run_id")
    artifact = _nonblank(source_artifact_id, field="source_artifact_id")
    revision = _nonblank(source_revision_id, field="source_revision_id")
    uri = _nonblank(source_uri, field="source_uri")
    profile = _nonblank(extraction_profile, field="extraction_profile")
    if profile != WORLDBUILDING_EXTRACTION_PROFILE:
        raise WorldbuildingWritePlanError(
            "worldbuilding write plans require the exact BLD-08 extraction profile",
            code="unsupported_worldbuilding_profile",
        )
    if preview.session_id not in (None, ""):
        raise WorldbuildingWritePlanError(
            "worldbuilding candidate must keep session_id null",
            code="run_scope_mismatch",
        )
    parent, store = _load_pinned_parent(
        world_root=world_root,
        world_id=world,
        expected_parent_revision_id=expected_parent_revision_id,
    )
    disposition_map, decision_snapshot, nodes, edges = _validate_dispositions(
        preview, dispositions
    )
    try:
        require_single_verified_source_artifact(
            preview=preview,
            verified_artifact_id=artifact,
            nodes=list(nodes.values()),
            edges=list(edges.values()),
        )
    except CandidateGraphMappingError as exc:
        raise _mapping_error(exc) from exc

    accepted: list[GraphContributionAssertion] = []
    rejected: list[GraphContributionAssertion] = []
    unresolved: list[ContributionIdentityMention] = []
    node_id_map: dict[str, str] = {}
    identity_snapshot: dict[str, str] = {}
    candidate_effect_map: dict[str, list[str]] = {}
    deferred_ids: list[str] = []
    diagnostics: list[str] = []

    for node_id in sorted(nodes):
        node = nodes[node_id]
        decision, target = disposition_map[node_id]
        diagnostics.extend(semantic_diagnostics(node))
        if decision == "create_new":
            _assert_create_new_id_is_free(store, node_id)
            assertion = _map_node(
                node,
                source_revision_id=revision,
                source_artifact_id=artifact,
                campaign_scope=campaign_scope,
                source_uri=uri,
                acceptance_state="accepted",
                identity_resolution_outcome="created_new",
            )
            accepted.append(assertion)
            candidate_effect_map[node_id] = [assertion.assertion_id]
            node_id_map[node_id] = node_id
            identity_snapshot[node_id] = "created_new"
        elif decision == "bind_existing":
            assert target is not None
            target_node = _resolve_bind_target(store, node, target)
            # Validate the reviewed semantic tuple even though connect-existing
            # intentionally emits support-only assertions, never a competing node.
            try:
                map_reviewed_worldbuilding_semantics_to_kernel(
                    object_id=node.node_id,
                    semantic=node.semantic_state,
                    proposed_action=node.proposed_action,
                    confidence=node.confidence,
                    warnings=node.warnings,
                    acceptance_state="accepted",
                )
            except CandidateSemanticPromoteError as exc:
                raise _mapping_error(exc) from exc
            try:
                support, alias_diagnostics = map_connect_existing_support_assertions(
                    node,
                    durable_node_id=target_node.node_id,
                    source_revision_id=revision,
                    verified_source_artifact_id=artifact,
                    campaign_scope=campaign_scope,
                    campaign_id=campaign_scope,
                    source_domain="worldbuilding",
                    session_id=None,
                    source_uri=uri,
                    acceptance_state="accepted",
                    identity_resolution_outcome="human_override",
                    alias_owners=dict(store.aliases),
                    kind_override=_candidate_kernel_kind(node),
                    predicate=WORLDBUILDING_BIND_SUPPORT_PREDICATE,
                )
            except CandidateGraphMappingError as exc:
                raise _mapping_error(exc) from exc
            accepted.extend(support)
            candidate_effect_map[node_id] = [
                item.assertion_id for item in support
            ]
            diagnostics.extend(alias_diagnostics)
            node_id_map[node_id] = target_node.node_id
            identity_snapshot[node_id] = "human_override"
        elif decision == "reject":
            assertion = _map_node(
                node,
                source_revision_id=revision,
                source_artifact_id=artifact,
                campaign_scope=campaign_scope,
                source_uri=uri,
                acceptance_state="rejected",
                identity_resolution_outcome="rejected_by_operator",
            )
            rejected.append(assertion)
            candidate_effect_map[node_id] = [assertion.assertion_id]
            identity_snapshot[node_id] = "rejected_by_operator"
        else:
            deferred = _map_node(
                node,
                source_revision_id=revision,
                source_artifact_id=artifact,
                campaign_scope=campaign_scope,
                source_uri=uri,
                acceptance_state="rejected",
                identity_resolution_outcome="deferred_by_operator",
            )
            unresolved.append(_deferred_node_mention(node, deferred))
            deferred_ids.append(node_id)
            candidate_effect_map[node_id] = []
            identity_snapshot[node_id] = "deferred_by_operator"

    for edge_id in sorted(edges):
        edge = edges[edge_id]
        decision, _target = disposition_map[edge_id]
        diagnostics.extend(semantic_diagnostics(edge))
        if decision == "accept":
            from_decision = disposition_map.get(edge.from_node_id)
            to_decision = disposition_map.get(edge.to_node_id)
            if (
                from_decision is None
                or to_decision is None
                or from_decision[0] not in {"create_new", "bind_existing"}
                or to_decision[0] not in {"create_new", "bind_existing"}
                or edge.from_node_id not in node_id_map
                or edge.to_node_id not in node_id_map
            ):
                raise WorldbuildingWritePlanError(
                    f"accepted edge {edge.edge_id!r} has an unresolved endpoint",
                    code="edge_endpoint_unresolved",
                )
            assertion = _map_edge(
                edge,
                source_revision_id=revision,
                source_artifact_id=artifact,
                campaign_scope=campaign_scope,
                source_uri=uri,
                acceptance_state="accepted",
                identity_resolution_outcome="accepted_by_operator",
                node_id_map=node_id_map,
            )
            accepted.append(assertion)
            candidate_effect_map[edge_id] = [assertion.assertion_id]
            identity_snapshot[edge_id] = "accepted_by_operator"
        elif decision == "reject":
            assertion = _map_edge(
                edge,
                source_revision_id=revision,
                source_artifact_id=artifact,
                campaign_scope=campaign_scope,
                source_uri=uri,
                acceptance_state="rejected",
                identity_resolution_outcome="rejected_by_operator",
            )
            rejected.append(assertion)
            candidate_effect_map[edge_id] = [assertion.assertion_id]
            identity_snapshot[edge_id] = "rejected_by_operator"
        else:
            # Validate edge-native evidence and reviewed semantics, but do not
            # turn a deferred relationship into an unresolved node mention.
            _map_edge(
                edge,
                source_revision_id=revision,
                source_artifact_id=artifact,
                campaign_scope=campaign_scope,
                source_uri=uri,
                acceptance_state="rejected",
                identity_resolution_outcome="deferred_by_operator",
            )
            deferred_ids.append(edge_id)
            candidate_effect_map[edge_id] = []
            identity_snapshot[edge_id] = "deferred_by_operator"

    decision_digest = _digest(decision_snapshot)
    contribution: GraphContribution = create_graph_contribution(
        world_id=world,
        source_kind=WORLD_BUILDING_WRITE_PLAN_SOURCE_KIND,  # type: ignore[arg-type]
        source_artifact_id=artifact,
        source_revision_id=revision,
        extraction_profile=profile,
        campaign_scope=campaign_scope,
        accepted_assertions=accepted,
        rejected_assertions=rejected,
        unresolved_mentions=unresolved,
        authored_by=WORLD_BUILDING_WRITE_PLAN_AUTHORED_BY,
        proposal_digest=decision_digest,
        produced_at=_FIXED_PRODUCED_AT,
        diagnostics=[],
    )
    effect: dict[str, Any] = {
        "contribution_meta": {
            "source_kind": WORLD_BUILDING_WRITE_PLAN_SOURCE_KIND,
            "source_artifact_id": artifact,
            "source_revision_id": revision,
            "extraction_profile": profile,
            "campaign_scope": campaign_scope,
            "authored_by": WORLD_BUILDING_WRITE_PLAN_AUTHORED_BY,
        },
        "accepted_proposals": [
            assertion.model_dump(mode="json")
            for assertion in contribution.accepted_assertions
        ],
        "rejected_assertions": [
            assertion.model_dump(mode="json")
            for assertion in contribution.rejected_assertions
        ],
        "unresolved_mentions": [
            mention.model_dump(mode="json")
            for mention in contribution.unresolved_mentions
        ],
        "deferred_candidate_ids": sorted(deferred_ids),
        "node_id_map": dict(sorted(node_id_map.items())),
        "identity_outcome_snapshot": dict(sorted(identity_snapshot.items())),
        "candidate_effect_map": {
            candidate_id: list(assertion_ids)
            for candidate_id, assertion_ids in sorted(candidate_effect_map.items())
        },
        "decision_snapshot": decision_snapshot,
    }
    plan_identity = {
        "world_id": world,
        "parent_revision_id": parent,
        "run_id": run,
        "source_domain": "worldbuilding",
        "source_artifact_id": artifact,
        "source_revision_id": revision,
        "extraction_profile": profile,
        "candidate_preview_id": preview.preview_id,
        "candidate_schema": preview.schema,
        "candidate_version": preview.version,
        "decision_snapshot": decision_snapshot,
        "effect": effect,
    }
    plan_digest = _digest(plan_identity)
    plan_id = f"worldbuilding-write-plan:{plan_digest.removeprefix('sha256:')[:24]}"
    summary = {
        "create_new_node_count": sum(
            disposition_map[node_id][0] == "create_new" for node_id in nodes
        ),
        "bind_existing_node_count": sum(
            disposition_map[node_id][0] == "bind_existing" for node_id in nodes
        ),
        "accepted_edge_count": sum(
            disposition_map[edge_id][0] == "accept" for edge_id in edges
        ),
        "rejected_candidate_count": sum(
            disposition_map[assertion_id][0] == "reject"
            for assertion_id in set(nodes) | set(edges)
        ),
        "deferred_candidate_count": len(deferred_ids),
        "accepted_assertion_count": len(contribution.accepted_assertions),
    }
    plan = WorldbuildingWritePlan(
        plan_id=plan_id,
        plan_digest=plan_digest,
        decision_digest=decision_digest,
        world_id=world,
        parent_revision_id=parent,
        run_id=run,
        source_artifact_id=artifact,
        source_revision_id=revision,
        extraction_profile=profile,
        candidate_preview_id=preview.preview_id,
        candidate_schema=preview.schema,
        candidate_version=preview.version,
        effect=effect,
        summary=summary,
        diagnostics=sorted(set(diagnostics)),
    )
    if self_verify:
        verify_worldbuilding_write_plan(
            _plan_mapping(plan),
            preview=preview,
            world_root=world_root,
            context=WorldbuildingWritePlanVerificationContext(
                world_id=world,
                parent_revision_id=parent,
                run_id=run,
                source_artifact_id=artifact,
                source_revision_id=revision,
                source_uri=uri,
                extraction_profile=profile,
                campaign_scope=campaign_scope,
            ),
        )
    return plan


def _plan_mapping(plan: WorldbuildingWritePlan) -> dict[str, Any]:
    return {
        "schema": WORLD_BUILDING_WRITE_PLAN_SCHEMA,
        "version": WORLD_BUILDING_WRITE_PLAN_VERSION,
        "plan_id": plan.plan_id,
        "plan_digest": plan.plan_digest,
        "decision_digest": plan.decision_digest,
        "world_id": plan.world_id,
        "parent_revision_id": plan.parent_revision_id,
        "run_id": plan.run_id,
        "source_domain": "worldbuilding",
        "source_artifact_id": plan.source_artifact_id,
        "source_revision_id": plan.source_revision_id,
        "extraction_profile": plan.extraction_profile,
        "candidate_preview_id": plan.candidate_preview_id,
        "candidate_schema": plan.candidate_schema,
        "candidate_version": plan.candidate_version,
        "effect": plan.effect,
        "summary": plan.summary,
        "diagnostics": plan.diagnostics,
        "confirmable": False,
        "confirmable_reason": _WORLDBUILDING_CONFIRMABLE_REASON,
    }


def _normalize_optional_campaign(value: Any) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise WorldbuildingWritePlanError(
            "campaign_scope must be null or a string",
            code="plan_verification_failed",
        )
    text = value.strip()
    return text or None


def verify_worldbuilding_write_plan(
    plan: Mapping[str, Any],
    *,
    preview: CandidateGraphPreview,
    world_root: Path,
    context: WorldbuildingWritePlanVerificationContext,
) -> dict[str, Any]:
    """Verify a response-carried plan by rebuilding from trusted context.

    Envelope identity is compared to the server-resolved context first. The
    builder is then re-run only from that context plus the sealed dispositions
    and exact candidate preview.
    """
    try:
        if not isinstance(plan, Mapping):
            raise WorldbuildingWritePlanError(
                "worldbuilding write plan must be an object",
                code="plan_verification_failed",
            )
        if not isinstance(preview, CandidateGraphPreview):
            raise WorldbuildingWritePlanError(
                "worldbuilding write plan verification requires the exact candidate preview",
                code="plan_verification_failed",
            )
        if not isinstance(context, WorldbuildingWritePlanVerificationContext):
            raise WorldbuildingWritePlanError(
                "worldbuilding write plan verification requires a trusted context",
                code="plan_verification_failed",
            )
        schema = _field(plan, "schema")
        if schema != WORLD_BUILDING_WRITE_PLAN_SCHEMA:
            raise WorldbuildingWritePlanError(
                f"unsupported plan schema: {schema!r}",
                code="plan_verification_failed",
            )
        version = _field(plan, "version")
        if type(version) is not int or version != WORLD_BUILDING_WRITE_PLAN_VERSION:
            raise WorldbuildingWritePlanError(
                f"unsupported plan version: {version!r}",
                code="plan_verification_failed",
            )
        confirmable = _field(plan, "confirmable", optional=True)
        if confirmable is not _MISSING and confirmable is not False:
            raise WorldbuildingWritePlanError(
                "worldbuilding write plan must not be confirmable",
                code="plan_verification_failed",
            )
        top_fields = {
            name: _require_string(_field(plan, name), field=name)
            for name in (
                "plan_id",
                "plan_digest",
                "decision_digest",
                "world_id",
                "parent_revision_id",
                "run_id",
                "source_domain",
                "source_artifact_id",
                "source_revision_id",
                "extraction_profile",
                "candidate_preview_id",
                "candidate_schema",
                "candidate_version",
            )
        }
        if top_fields["source_domain"] != "worldbuilding":
            raise WorldbuildingWritePlanError(
                "plan source_domain must be worldbuilding",
                code="plan_verification_failed",
            )
        if top_fields["extraction_profile"] != WORLDBUILDING_EXTRACTION_PROFILE:
            raise WorldbuildingWritePlanError(
                "plan extraction_profile is not the BLD-08 profile",
                code="plan_verification_failed",
            )
        if context.extraction_profile != WORLDBUILDING_EXTRACTION_PROFILE:
            raise WorldbuildingWritePlanError(
                "verification context extraction_profile is not the BLD-08 profile",
                code="plan_verification_failed",
            )
        identity_pairs = (
            ("world_id", top_fields["world_id"], context.world_id),
            (
                "parent_revision_id",
                top_fields["parent_revision_id"],
                context.parent_revision_id,
            ),
            ("run_id", top_fields["run_id"], context.run_id),
            (
                "source_artifact_id",
                top_fields["source_artifact_id"],
                context.source_artifact_id,
            ),
            (
                "source_revision_id",
                top_fields["source_revision_id"],
                context.source_revision_id,
            ),
            (
                "extraction_profile",
                top_fields["extraction_profile"],
                context.extraction_profile,
            ),
        )
        for field_name, carried, trusted in identity_pairs:
            if carried != trusted:
                raise WorldbuildingWritePlanError(
                    f"plan {field_name} disagrees with trusted verification context",
                    code="plan_verification_failed",
                )
        if (
            preview.preview_id != top_fields["candidate_preview_id"]
            or preview.schema != top_fields["candidate_schema"]
            or preview.version != top_fields["candidate_version"]
        ):
            raise WorldbuildingWritePlanError(
                "candidate preview identity disagrees with plan envelope",
                code="plan_verification_failed",
            )
        preview_campaign = _normalize_optional_campaign(preview.campaign_id)
        if preview_campaign != context.campaign_scope:
            raise WorldbuildingWritePlanError(
                "candidate preview campaign_id disagrees with trusted context",
                code="plan_verification_failed",
            )
        preview_artifacts = {
            str(item).strip()
            for item in (preview.source_artifact_ids or ())
            if str(item).strip()
        }
        if preview_artifacts != {context.source_artifact_id}:
            raise WorldbuildingWritePlanError(
                "candidate preview source_artifact_ids disagree with trusted context",
                code="plan_verification_failed",
            )
        effect = _canonical_effect(_field(plan, "effect"))
        meta = effect["contribution_meta"]
        if meta["extraction_profile"] != context.extraction_profile:
            raise WorldbuildingWritePlanError(
                "effect extraction_profile disagrees with trusted context",
                code="plan_verification_failed",
            )
        if meta["source_artifact_id"] != context.source_artifact_id:
            raise WorldbuildingWritePlanError(
                "effect contribution source_artifact_id disagrees with trusted context",
                code="plan_verification_failed",
            )
        if meta["source_revision_id"] != context.source_revision_id:
            raise WorldbuildingWritePlanError(
                "effect contribution source_revision_id disagrees with trusted context",
                code="plan_verification_failed",
            )
        if meta["campaign_scope"] != context.campaign_scope:
            raise WorldbuildingWritePlanError(
                "effect contribution campaign_scope disagrees with trusted context",
                code="plan_verification_failed",
            )
        dispositions = [
            WorldbuildingDispositionInput(
                assertion_id=item["assertion_id"],
                decision=item["decision"],
                target_node_id=item["target_node_id"],
            )
            for item in effect["decision_snapshot"]
        ]
        try:
            expected = build_worldbuilding_write_plan(
                preview=preview,
                world_root=world_root,
                world_id=context.world_id,
                expected_parent_revision_id=context.parent_revision_id,
                run_id=context.run_id,
                source_artifact_id=context.source_artifact_id,
                source_revision_id=context.source_revision_id,
                source_uri=context.source_uri,
                extraction_profile=context.extraction_profile,
                campaign_scope=context.campaign_scope,
                dispositions=dispositions,
                self_verify=False,
            )
        except WorldbuildingWritePlanError as exc:
            raise WorldbuildingWritePlanError(
                f"plan does not rebuild from pinned inputs: {exc}",
                code="plan_verification_failed",
            ) from exc
        expected_effect = _canonical_effect(expected.effect)
        if (
            expected.decision_digest != top_fields["decision_digest"]
            or expected.plan_digest != top_fields["plan_digest"]
            or expected.plan_id != top_fields["plan_id"]
            or expected_effect != effect
        ):
            raise WorldbuildingWritePlanError(
                "response-carried plan does not match rebuilt authority effect",
                code="plan_verification_failed",
            )
        return {
            **top_fields,
            "schema": schema,
            "version": version,
            "effect": effect,
        }
    except WorldbuildingWritePlanError as exc:
        if exc.code == "plan_verification_failed":
            raise
        raise WorldbuildingWritePlanError(
            str(exc),
            code="plan_verification_failed",
        ) from exc
    except Exception as exc:  # noqa: BLE001 — verification fails closed
        raise WorldbuildingWritePlanError(
            "worldbuilding write plan verification failed",
            code="plan_verification_failed",
        ) from exc


__all__ = [
    "WORLD_BUILDING_WRITE_PLAN_AUTHORED_BY",
    "WORLD_BUILDING_WRITE_PLAN_SCHEMA",
    "WORLD_BUILDING_WRITE_PLAN_SOURCE_KIND",
    "WORLD_BUILDING_WRITE_PLAN_VERSION",
    "WORLDBUILDING_BIND_SUPPORT_PREDICATE",
    "WORLDBUILDING_EXTRACTION_PROFILE",
    "WorldbuildingDispositionInput",
    "WorldbuildingWritePlan",
    "WorldbuildingWritePlanError",
    "WorldbuildingWritePlanVerificationContext",
    "build_worldbuilding_write_plan",
    "verify_worldbuilding_write_plan",
]
