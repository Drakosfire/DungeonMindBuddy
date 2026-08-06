"""Kernel World Graph projection (PR007A)."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from pydantic import ValidationError

from graph_memory.evidence.assertion_support import DurableAssertionSupport
from graph_memory.kernel.contribution_models import (
    GraphContribution,
    GraphContributionAssertion,
)
from graph_memory.kernel.contributions import (
    compute_assertion_id,
    explicit_assertion_evidence_ref_ids,
    explicit_assertion_source_artifact_ids,
    semantic_assertion_value,
)
from graph_memory.kernel.temporal import (
    TemporalScopeValidationError,
    temporal_core_semantic_payload,
)
from graph_memory.kernel.world_graph import (
    WorldGraphIntegrityError,
    WorldGraphNotFoundError,
    WorldGraphValidationError,
    load_world_graph_revision,
    open_world_graph_head,
)
from graph_memory.projection.node_view import (
    GraphProjectionAdjacencyCandidate,
    GraphProjectionEvidenceBadge,
    GraphProjectionNodeView,
    GraphProjectionSuggestedExpansion,
    GraphProjectionTextHighlightSpan,
)
from graph_memory.projection.recap_projection import (
    _resolve_evidence_source_excerpt,
    build_focus_overlay,
    build_node_view,
)
from graph_memory.projection.world_projection import (
    PROJECTION_RESPONSE_SCHEMA,
    SEARCH_MAX_ATTRIBUTES,
    SEARCH_MAX_EVIDENCE,
    SEARCH_MAX_NODES,
    SEARCH_MAX_RELATIONSHIPS,
    SEARCH_MAX_SOURCE_ARTIFACTS,
    WorldGraphDirectionError,
    WorldGraphProjection,
    WorldGraphProjectionAdjacencyCandidate,
    WorldGraphProjectionAttributeView,
    WorldGraphProjectionDiagnostic,
    WorldGraphProjectionEvidenceBadge,
    WorldGraphProjectionEvidenceView,
    WorldGraphProjectionFocus,
    WorldGraphProjectionNodeView,
    WorldGraphProjectionRelationshipView,
    WorldGraphProjectionRequest,
    WorldGraphProjectionSnapshot,
    WorldGraphProjectionSourceArtifactView,
    WorldGraphProjectionSuggestedExpansion,
    WorldGraphProjectionSummary,
    WorldGraphProjectionTextHighlightSpan,
    WorldGraphProjectionTrustBoundary,
    WorldGraphQueryContext,
    derive_attribute_text_value,
    normalize_world_graph_relationship_direction,
    rank_search_node_matches,
)
from graph_memory.union_supergraph.model import UnionSupergraphEdge, UnionSupergraphNode, UnionSupergraphStore
from graph_memory.union_supergraph.statblock_binding import (
    ExternalResourceV1,
    ThreatStatblockBindingV1,
    parse_external_resource_assertion,
    parse_threat_statblock_binding_assertion,
)
from graph_memory.union_supergraph.projection_identity import (
    UnionProjectionIdentityContext,
    build_union_projection_identity_context,
    is_projectable_union_edge,
    is_projectable_union_node,
    projectable_node_ids,
)
from graph_memory.world_supergraph import paths as world_paths
from graph_memory.world_supergraph.contribution_store import load_contribution_record
from graph_memory.world_supergraph.model import WorldGraphHead, WorldGraphRevision
from graph_memory.world_supergraph.storage import (
    compute_revision_id,
    load_world_graph_revision_manifest,
    sha256_hex,
)

# Late-bound import helpers for OPT01 resident runtime (same package; avoid cycle
# at module import of public re-exports). Functions are imported where used.

_UNSUPPORTED_ASSERTION_MEMORY_STATE = "unsupported_assertion"

_TRUST_CANNOT = [
    "Evidence locators and source spans are metadata only; this projection does not verify them.",
    "Source artifact text is not read or opened by this projection.",
    "Projection includes world-universal objects (campaign_scope null) plus objects scoped to the requested campaign_id; other campaign-scoped chronology is excluded.",
]
_TRUST_CAN_HEAD = [
    "Revision pin identity matches the requested world graph revision.",
    "Selected revision payload is the immutable store bytes for that revision.",
    "Attribute views are reconstructed from revision-bound assertion support and contributions.",
]


class WorldGraphProjectionError(Exception):
    """Stable projection failure with API-safe code and diagnostics."""

    def __init__(
        self,
        message: str,
        *,
        code: str,
        status_code: int,
        diagnostics: list[WorldGraphProjectionDiagnostic] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.status_code = status_code
        self.diagnostics = list(diagnostics or [])


def resolve_projection_admissibility(policy: str) -> str:
    if policy != "gm":
        raise WorldGraphProjectionError(
            f"Unsupported projection admissibility policy: {policy!r}",
            code="unsupported_admissibility",
            status_code=422,
            diagnostics=[
                WorldGraphProjectionDiagnostic(
                    code="unsupported_admissibility",
                    message="Only gm admissibility is supported in PR007A.",
                    severity="error",
                )
            ],
        )
    return "gm"


def _diagnostic(code: str, message: str, *, severity: str = "error") -> WorldGraphProjectionDiagnostic:
    return WorldGraphProjectionDiagnostic(code=code, message=message, severity=severity)


def _parse_support(raw: dict[str, Any]) -> DurableAssertionSupport:
    return DurableAssertionSupport.model_validate(raw)


def _generated_fallback_evidence_id(contribution_id: str, graph_object_id: str) -> str:
    return f"evidence:{contribution_id}:{graph_object_id}"


def _materialized_evidence_ref_ids(
    store: UnionSupergraphStore,
    graph_object_id: str | None,
) -> list[str] | None:
    if graph_object_id is None:
        return None
    if graph_object_id in store.nodes:
        return list(store.nodes[graph_object_id].evidence_ref_ids)
    if graph_object_id in store.edges:
        return list(store.edges[graph_object_id].evidence_ref_ids)
    return None


def _assertion_has_explicit_evidence(
    assertion: GraphContributionAssertion,
) -> bool:
    return bool(explicit_assertion_evidence_ref_ids(assertion))


def _integrity_error(message: str, *, detail: str) -> WorldGraphProjectionError:
    return WorldGraphProjectionError(
        message,
        code="projection_integrity_error",
        status_code=409,
        diagnostics=[_diagnostic("revision_integrity_error", detail)],
    )


def _temporal_core_semantic_for_fingerprint(
    temporal_scope: dict[str, Any] | None,
) -> dict[str, Any] | None:
    """Projection-safe temporal core payload; malformed V1 → integrity 409."""
    try:
        return temporal_core_semantic_payload(temporal_scope)
    except TemporalScopeValidationError as exc:
        detail = "; ".join(exc.diagnostics) if exc.diagnostics else str(exc)
        raise WorldGraphProjectionError(
            "Malformed durable temporal_scope envelope.",
            code="projection_integrity_error",
            status_code=409,
            diagnostics=[
                _diagnostic(
                    "malformed_temporal_envelope",
                    detail,
                )
            ],
        ) from exc


def _read_revision_graph_canonical(
    root: Path,
    world_id: str,
    revision_id: str,
) -> str:
    """Return the immutable on-disk graph payload text for a revision.

    Publish writes ``canonicalize_graph_payload(...)`` bytes and stores that
    digest in the revision manifest. Integrity checks must hash those bytes —
    never a post-parse ``dump_union_supergraph_store`` round-trip, which drifts
    when the UnionSupergraphStore model gains defaults or drops unknown keys.
    """
    path = world_paths.graph_payload_path(root, world_id, revision_id)
    return path.read_text(encoding="utf-8")


def _verify_revision_payload_hash(
    manifest_graph_payload_sha256: str,
    *,
    canonical_graph_json: str,
) -> None:
    payload_sha = sha256_hex(canonical_graph_json)
    if payload_sha != manifest_graph_payload_sha256:
        raise _integrity_error(
            "Revision payload hash does not match manifest graph_payload_sha256.",
            detail=(
                "graph_payload_sha256 mismatch between revision manifest "
                "and loaded graph"
            ),
        )


def _verify_revision_identity(
    manifest: WorldGraphRevision,
    *,
    world_id: str,
    revision_id: str,
    canonical_graph_json: str,
) -> None:
    if manifest.world_id != world_id:
        raise _integrity_error(
            "Revision manifest world_id does not match requested world.",
            detail=(
                f"manifest world_id={manifest.world_id!r} "
                f"requested world_id={world_id!r}"
            ),
        )
    if manifest.revision_id != revision_id:
        raise _integrity_error(
            "Revision manifest revision_id does not match selected revision.",
            detail=(
                f"manifest revision_id={manifest.revision_id!r} "
                f"selected revision_id={revision_id!r}"
            ),
        )
    expected_payload_path = world_paths.relative_graph_payload_path(revision_id)
    if manifest.graph_payload_path != expected_payload_path:
        raise _integrity_error(
            "Revision manifest graph_payload_path does not match expected layout.",
            detail=(
                f"manifest graph_payload_path={manifest.graph_payload_path!r} "
                f"expected={expected_payload_path!r}"
            ),
        )
    try:
        payload = json.loads(canonical_graph_json)
    except json.JSONDecodeError as exc:
        raise _integrity_error(
            "Revision graph payload is malformed.",
            detail=f"revision graph payload JSON decode failed: {exc}",
        ) from exc
    if not isinstance(payload, dict):
        raise _integrity_error(
            "Revision graph payload is malformed.",
            detail="revision graph payload root must be a JSON object",
        )
    expected_schema = str(payload.get("schema") or "")
    if manifest.graph_schema != expected_schema:
        raise _integrity_error(
            "Revision manifest graph_schema does not match loaded graph payload.",
            detail=(
                f"manifest graph_schema={manifest.graph_schema!r} "
                f"payload schema={expected_schema!r}"
            ),
        )
    recomputed_revision_id = compute_revision_id(
        world_id=manifest.world_id,
        parent_revision_id=manifest.parent_revision_id,
        operation_ids=manifest.operation_ids,
        canonical_graph_json=canonical_graph_json,
    )
    if recomputed_revision_id != revision_id:
        raise _integrity_error(
            "Revision identity does not match content-addressed revision id.",
            detail=(
                f"recomputed revision_id={recomputed_revision_id!r} "
                f"selected revision_id={revision_id!r}"
            ),
        )


def _load_revision_store_with_integrity(
    root: Path,
    world_id: str,
    revision_id: str,
    *,
    not_found_code: str,
    not_found_message: str,
    not_found_as_integrity_error: bool = False,
) -> tuple[str, UnionSupergraphStore]:
    def _not_found(exc: WorldGraphNotFoundError) -> WorldGraphProjectionError:
        if not_found_as_integrity_error:
            return _integrity_error(
                not_found_message,
                detail=f"revision not found: {exc}",
            )
        return WorldGraphProjectionError(
            not_found_message,
            code=not_found_code,
            status_code=404,
            diagnostics=[_diagnostic(not_found_code, str(exc))],
        )

    try:
        manifest = load_world_graph_revision_manifest(root, world_id, revision_id)
    except WorldGraphNotFoundError as exc:
        raise _not_found(exc) from exc
    except (ValidationError, json.JSONDecodeError, TypeError) as exc:
        raise _integrity_error(
            f"Revision {revision_id!r} manifest is malformed.",
            detail=f"revision manifest validation failed: {exc}",
        ) from exc
    except (WorldGraphValidationError, WorldGraphIntegrityError) as exc:
        raise _integrity_error(
            f"Revision {revision_id!r} failed integrity checks.",
            detail=str(exc),
        ) from exc
    except (FileNotFoundError, OSError) as exc:
        raise _integrity_error(
            f"Revision {revision_id!r} could not be loaded.",
            detail=f"revision manifest load failed: {exc}",
        ) from exc

    try:
        store = load_world_graph_revision(root, world_id, revision_id)
    except WorldGraphNotFoundError as exc:
        raise _not_found(exc) from exc
    except (ValidationError, json.JSONDecodeError, TypeError) as exc:
        raise _integrity_error(
            f"Revision {revision_id!r} graph payload is malformed.",
            detail=f"revision graph payload validation failed: {exc}",
        ) from exc
    except (WorldGraphValidationError, WorldGraphIntegrityError) as exc:
        raise _integrity_error(
            f"Revision {revision_id!r} failed integrity checks.",
            detail=str(exc),
        ) from exc
    except (FileNotFoundError, OSError) as exc:
        raise _integrity_error(
            f"Revision {revision_id!r} could not be loaded.",
            detail=f"revision graph payload load failed: {exc}",
        ) from exc

    try:
        canonical_graph_json = _read_revision_graph_canonical(root, world_id, revision_id)
        _verify_revision_payload_hash(
            manifest.graph_payload_sha256,
            canonical_graph_json=canonical_graph_json,
        )
        _verify_revision_identity(
            manifest,
            world_id=world_id,
            revision_id=revision_id,
            canonical_graph_json=canonical_graph_json,
        )
    except WorldGraphProjectionError:
        raise
    except Exception as exc:
        raise _integrity_error(
            f"Revision {revision_id!r} failed payload integrity verification.",
            detail=f"revision payload hash verification failed: {exc}",
        ) from exc

    return revision_id, store


def load_world_graph_revision_with_integrity(
    root: Path,
    world_id: str,
    revision_id: str,
) -> UnionSupergraphStore:
    """Load exactly one immutable world graph revision with integrity attestation.

    Verifies the on-disk manifest, graph payload hash, graph schema, and
    recomputed content-addressed revision id before returning the store.
    """
    try:
        world_paths.assert_safe_revision_id(revision_id)
    except ValueError as exc:
        raise WorldGraphProjectionError(
            f"Revision id is invalid: {revision_id!r}",
            code="invalid_request",
            status_code=422,
            diagnostics=[_diagnostic("invalid_revision_id", str(exc))],
        ) from exc
    _revision_id, store = _load_revision_store_with_integrity(
        root,
        world_id,
        revision_id,
        not_found_code="revision_not_found",
        not_found_message=f"Revision not found: {revision_id!r}",
    )
    del _revision_id
    return store


def _memory_state(graph_object: UnionSupergraphNode | UnionSupergraphEdge) -> str | None:
    memory_state = graph_object.state.get("memory_state")
    return memory_state if isinstance(memory_state, str) else None


def _is_unsupported_graph_object(graph_object: UnionSupergraphNode | UnionSupergraphEdge) -> bool:
    return _memory_state(graph_object) == _UNSUPPORTED_ASSERTION_MEMORY_STATE


def _canonicalize_json_value(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def _assertion_semantic_fingerprint(assertion: GraphContributionAssertion) -> tuple[Any, ...]:
    return (
        assertion.assertion_kind,
        assertion.subject_node_id,
        assertion.target_node_id,
        assertion.predicate,
        assertion.label,
        _canonicalize_json_value(semantic_assertion_value(assertion.value)),
        assertion.epistemic_kind,
        assertion.visibility,
        assertion.campaign_scope,
        _canonicalize_json_value(assertion.temporal_scope),
    )


def _node_core_semantic_fingerprint(
    assertion: GraphContributionAssertion,
) -> tuple[Any, ...]:
    """Fingerprint correction-sensitive node semantics, excluding aliases.

    Node aliases are additive: independently accepted node assertions may
    provide distinct spellings for the same node without being contradictory.
    All remaining semantic fields still must agree; a label/kind/role
    correction must supersede the older contribution rather than coexist.

    Temporal source/observation stamps (legacy ``session_id`` or V1
    ``source_time``) are excluded via ``_temporal_core_semantic_for_fingerprint``;
    occurrence and valid time remain correction-sensitive. Malformed
    schema-tagged V1 envelopes raise ``WorldGraphProjectionError`` (409).
    """
    value = dict(semantic_assertion_value(assertion.value))
    value.pop("aliases", None)
    return (
        assertion.assertion_kind,
        assertion.subject_node_id,
        assertion.target_node_id,
        assertion.predicate,
        assertion.label,
        _canonicalize_json_value(value),
        assertion.epistemic_kind,
        assertion.visibility,
        assertion.campaign_scope,
        _canonicalize_json_value(
            _temporal_core_semantic_for_fingerprint(assertion.temporal_scope)
        ),
    )


def _edge_core_semantic_fingerprint(
    assertion: GraphContributionAssertion,
) -> tuple[Any, ...]:
    """Fingerprint correction-sensitive edge semantics, excluding session stamps.

    ``value.session_ids`` and temporal source/observation stamps (legacy
    ``temporal_scope.session_id`` or V1 ``source_time``) are additive
    observation provenance for the same edge (e.g. standing party membership
    re-attested on a later session promote). They must not fail projection when
    endpoints, predicate, label, and other core semantics agree. Other
    ``temporal_scope`` qualifiers (e.g. ``as_of``) and V1 occurrence/valid time
    still participate in the fingerprint via
    ``_temporal_core_semantic_for_fingerprint``. Malformed schema-tagged V1
    envelopes raise ``WorldGraphProjectionError`` (409).
    """
    value = dict(semantic_assertion_value(assertion.value))
    value.pop("session_ids", None)
    return (
        assertion.assertion_kind,
        assertion.subject_node_id,
        assertion.target_node_id,
        assertion.predicate,
        assertion.label,
        _canonicalize_json_value(value),
        assertion.epistemic_kind,
        assertion.visibility,
        assertion.campaign_scope,
        _canonicalize_json_value(
            _temporal_core_semantic_for_fingerprint(assertion.temporal_scope)
        ),
    )


def _assert_active_node_assertions_agree(
    assertions: list[GraphContributionAssertion],
    *,
    node_id: str,
) -> None:
    fingerprints = {
        assertion.assertion_id: _node_core_semantic_fingerprint(assertion)
        for assertion in assertions
    }
    if len(set(fingerprints.values())) <= 1:
        return
    raise _integrity_error(
        "Active node assertions disagree on correction-sensitive semantics.",
        detail=f"node_id={node_id!r} assertion_fingerprints={fingerprints!r}",
    )


def _assert_active_edge_assertions_agree(
    assertions: list[GraphContributionAssertion],
    *,
    graph_object_id: str,
) -> None:
    fingerprints = {_edge_core_semantic_fingerprint(assertion) for assertion in assertions}
    if len(fingerprints) > 1:
        raise _integrity_error(
            "Active edge assertions disagree on semantic fields.",
            detail=(
                f"graph_object_id={graph_object_id!r} "
                f"active_assertion_ids={sorted(assertion.assertion_id for assertion in assertions)!r}"
            ),
        )


def _validate_assertion_identity(
    assertion: GraphContributionAssertion,
    *,
    contribution_id: str,
    context: str,
) -> None:
    if assertion.contribution_id != contribution_id:
        raise _integrity_error(
            "Contribution assertion does not belong to its containing contribution.",
            detail=(
                f"{context} assertion contribution_id={assertion.contribution_id!r} "
                f"expected={contribution_id!r}"
            ),
        )
    computed_assertion_id = compute_assertion_id(
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
    if assertion.assertion_id != computed_assertion_id:
        raise _integrity_error(
            "Contribution assertion id does not match its semantic content.",
            detail=(
                f"{context} assertion_id={assertion.assertion_id!r} "
                f"computed={computed_assertion_id!r}"
            ),
        )


def _load_validated_contribution_from_disk(
    root: Path,
    world_id: str,
    contribution_id: str,
) -> GraphContribution:
    """Durable contribution load used by resident cold admission / scrub."""
    try:
        contribution = load_contribution_record(root, world_id, contribution_id)
    except (FileNotFoundError, OSError, ValueError, ValidationError, json.JSONDecodeError) as exc:
        raise _integrity_error(
            f"Contribution record {contribution_id!r} could not be loaded.",
            detail=f"contribution load failed for {contribution_id!r}: {exc}",
        ) from exc
    if contribution.contribution_id != contribution_id:
        raise _integrity_error(
            "Contribution record id does not match the revision support reference.",
            detail=(
                f"loaded contribution_id={contribution.contribution_id!r} "
                f"expected={contribution_id!r}"
            ),
        )
    if contribution.world_id != world_id:
        raise _integrity_error(
            "Contribution record world_id does not match the selected world.",
            detail=(
                f"loaded world_id={contribution.world_id!r} "
                f"expected={world_id!r}"
            ),
        )
    for collection_name in (
        "candidate_assertions",
        "accepted_assertions",
        "rejected_assertions",
    ):
        for assertion in getattr(contribution, collection_name):
            _validate_assertion_identity(
                assertion,
                contribution_id=contribution_id,
                context=collection_name,
            )
    return contribution


def _load_validated_contribution(
    root: Path,
    world_id: str,
    contribution_id: str,
) -> GraphContribution:
    """Resolve a contribution from the active resident, else durable storage.

    Warm projection binds a resident via ``set_active_resident`` and must not
    reread contribution files. Cold admission / scrub call this without a
    resident binding and use the durable path.
    """
    from graph_memory.kernel.world_read_runtime import get_active_resident

    resident = get_active_resident()
    if resident is not None:
        contribution = resident.contributions.get(contribution_id)
        if contribution is None:
            raise _integrity_error(
                f"Contribution record {contribution_id!r} could not be loaded.",
                detail=(
                    f"contribution {contribution_id!r} missing from resident "
                    f"generation={resident.generation}"
                ),
            )
        return contribution
    return _load_validated_contribution_from_disk(root, world_id, contribution_id)


def _load_head_with_integrity(
    root: Path,
    world_id: str,
) -> tuple[WorldGraphHead, UnionSupergraphStore]:
    """Load the world graph head and verify its target revision actually exists.

    A well-formed ``head.json`` that points at a revision id which is missing
    or fails integrity is head *corruption*, not "world not bootstrapped yet"
    — every caller (pinned and unpinned requests alike) trusts
    ``head.head_revision_id`` in response metadata (``headRevisionId``,
    ``isHead``), so it must be verified here rather than left unchecked.
    """
    try:
        head = open_world_graph_head(root, world_id)
    except WorldGraphNotFoundError as exc:
        raise WorldGraphProjectionError(
            f"World graph unavailable for world_id={world_id!r}",
            code="world_graph_unavailable",
            status_code=404,
            diagnostics=[_diagnostic("world_graph_unavailable", str(exc))],
        ) from exc
    except (ValidationError, json.JSONDecodeError, TypeError, ValueError, OSError) as exc:
        raise _integrity_error(
            "World graph head is malformed.",
            detail=f"head validation failed: {exc}",
        ) from exc
    if head.world_id != world_id:
        raise _integrity_error(
            "World graph head world_id does not match requested world.",
            detail=f"head world_id={head.world_id!r} requested={world_id!r}",
        )
    try:
        world_paths.assert_safe_revision_id(head.head_revision_id)
    except ValueError as exc:
        raise _integrity_error(
            "World graph head references an unsafe revision id.",
            detail=f"head revision id validation failed: {exc}",
        ) from exc
    _, store = _load_revision_store_with_integrity(
        root,
        world_id,
        head.head_revision_id,
        not_found_code="projection_integrity_error",
        not_found_message=(
            f"World graph head references a revision that does not exist: "
            f"{head.head_revision_id!r}"
        ),
        not_found_as_integrity_error=True,
    )
    return head, store


def _load_revision_context(
    root: Path,
    request: WorldGraphProjectionRequest,
) -> tuple[str, str, UnionSupergraphStore]:
    world_id = request.world_id
    if request.revision_pin:
        try:
            world_paths.assert_safe_revision_id(request.revision_pin)
        except ValueError as exc:
            raise WorldGraphProjectionError(
                f"Revision pin is invalid: {request.revision_pin!r}",
                code="invalid_request",
                status_code=422,
                diagnostics=[_diagnostic("invalid_revision_pin", str(exc))],
            ) from exc
    # Caller-controlled pin syntax must win error precedence over storage
    # state. A malformed request remains invalid even when the world is
    # absent or its head is corrupt.
    head, head_store = _load_head_with_integrity(root, world_id)

    if request.revision_pin:
        revision_id, store = _load_revision_store_with_integrity(
            root,
            world_id,
            request.revision_pin,
            not_found_code="revision_not_found",
            not_found_message=f"Revision pin not found: {request.revision_pin!r}",
        )
        return revision_id, head.head_revision_id, store

    return head.head_revision_id, head.head_revision_id, head_store


def _assert_campaign_scope(request: WorldGraphProjectionRequest, store: UnionSupergraphStore) -> None:
    """Require a non-empty request campaign; do not bind to store.campaign_id.

    Model B: the durable store is world-owned. Tenancy is assertion/object
    ``campaign_scope`` (null = world-universal). The store may retain a legacy
    ``campaign_id`` label from bootstrap; it is not a projection hard gate.
    """
    del store  # legacy store.campaign_id is intentionally unused
    _assert_request_campaign_policy(request)


def _assert_request_campaign_policy(request: WorldGraphProjectionRequest) -> None:
    """Request-only campaign/scope checks that must precede durable reads."""
    campaign_id = (request.campaign_id or "").strip()
    if not campaign_id:
        raise WorldGraphProjectionError(
            "Requested campaign_id must be a non-empty campaign scope.",
            code="invalid_request",
            status_code=400,
            diagnostics=[
                _diagnostic(
                    "invalid_request",
                    "request campaign_id is missing or blank",
                )
            ],
        )
    scope_mode = getattr(request, "scope_mode", "campaign") or "campaign"
    if scope_mode not in {"campaign", "world"}:
        raise WorldGraphProjectionError(
            f"Unsupported scope_mode: {scope_mode!r}",
            code="invalid_request",
            status_code=400,
            diagnostics=[
                _diagnostic(
                    "invalid_request",
                    "scope_mode must be 'campaign' or 'world'",
                )
            ],
        )


def validate_projection_request_policy(
    request: WorldGraphProjectionRequest,
) -> WorldGraphProjectionRequest:
    """Revalidate request-only policy before any world storage access."""
    try:
        validated = WorldGraphProjectionRequest.model_validate(
            request.model_dump(mode="json")
        )
    except Exception as exc:
        raise WorldGraphProjectionError(
            "Projection request is invalid.",
            code="invalid_request",
            status_code=422,
            diagnostics=[_diagnostic("invalid_request", str(exc))],
        ) from exc
    resolve_projection_admissibility(validated.admissibility)
    _assert_request_campaign_policy(validated)
    return validated


def _effective_focus_campaign_id(
    focus: WorldGraphProjectionFocus,
    *,
    request_campaign_id: str,
) -> str | None:
    """Campaign that qualifies session focus (falls back to request campaign)."""
    if focus.kind != "session":
        return None
    explicit = (focus.campaign_id or "").strip()
    if explicit:
        return explicit
    return (request_campaign_id or "").strip() or None


def _evidence_campaign_id(
    store: UnionSupergraphStore,
    evidence_ref_id: str,
) -> str | None:
    evidence = store.evidence.get(evidence_ref_id)
    if evidence is None:
        return None
    artifact = store.source_artifacts.get(evidence.source_artifact_id)
    if artifact is None:
        return None
    campaign = (artifact.campaign_id or "").strip()
    return campaign or None


def _evidence_matches_focus(
    store: UnionSupergraphStore,
    evidence_ref_id: str,
    *,
    focus_session_id: str | None,
    focus_campaign_id: str | None,
) -> bool:
    """True when evidence session+campaign match the qualified temporal focus."""
    if not focus_session_id:
        return False
    evidence = store.evidence.get(evidence_ref_id)
    if evidence is None or evidence.session_id != focus_session_id:
        return False
    if not focus_campaign_id:
        return True
    evidence_campaign = _evidence_campaign_id(store, evidence_ref_id)
    # Missing artifact campaign stays non-matching under qualified focus so
    # bare session-N cannot silently cross campaigns.
    return evidence_campaign == focus_campaign_id


def _relationship_matches_focus(
    store: UnionSupergraphStore,
    relationship: WorldGraphProjectionRelationshipView,
    *,
    focus_session_id: str | None,
    focus_campaign_id: str | None,
) -> bool:
    if not focus_session_id or focus_session_id not in relationship.session_ids:
        # Fall back to evidence-level campaign+session match.
        return any(
            _evidence_matches_focus(
                store,
                evidence_ref_id,
                focus_session_id=focus_session_id,
                focus_campaign_id=focus_campaign_id,
            )
            for evidence_ref_id in relationship.evidence_ref_ids
        )
    if not focus_campaign_id:
        return True
    if relationship.campaign_scope is None:
        # World-owned edge: only focus-anchored when evidence proves campaign.
        return any(
            _evidence_matches_focus(
                store,
                evidence_ref_id,
                focus_session_id=focus_session_id,
                focus_campaign_id=focus_campaign_id,
            )
            for evidence_ref_id in relationship.evidence_ref_ids
        )
    scope = str(relationship.campaign_scope).strip()
    if not scope:
        raise WorldGraphProjectionError(
            "Blank campaign_scope is invalid; only JSON null is world-universal.",
            code="invalid_campaign_scope",
            status_code=409,
            diagnostics=[
                _diagnostic(
                    "invalid_campaign_scope",
                    "relationship campaign_scope is blank",
                )
            ],
        )
    return scope == focus_campaign_id


def _campaign_scope_is_visible(
    campaign_scope: str | None,
    *,
    request_campaign_id: str,
    scope_mode: str = "campaign",
) -> bool:
    """Visibility lens independent of temporal focus.

    - ``campaign``: world-universal (null) or matching request campaign.
    - ``world``: every non-blank campaign scope in the same world store.
    Blank strings are never world-universal in either mode.
    """
    if campaign_scope is None:
        return True
    scope = str(campaign_scope).strip()
    if not scope:
        raise WorldGraphProjectionError(
            "Blank campaign_scope is invalid; only JSON null is world-universal.",
            code="invalid_campaign_scope",
            status_code=409,
            diagnostics=[
                _diagnostic(
                    "invalid_campaign_scope",
                    "blank campaign_scope cannot be treated as world-universal",
                )
            ],
        )
    if scope_mode == "world":
        return True
    return scope == request_campaign_id


def _object_campaign_scope(state: Mapping[str, Any] | None) -> str | None:
    if not isinstance(state, Mapping):
        return None
    value = state.get("campaign_scope")
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        raise WorldGraphProjectionError(
            "Blank campaign_scope is invalid; only JSON null is world-universal.",
            code="invalid_campaign_scope",
            status_code=409,
            diagnostics=[
                _diagnostic(
                    "invalid_campaign_scope",
                    "stored object campaign_scope is blank",
                )
            ],
        )
    return text


@dataclass(frozen=True)
class ValidatedSupportAuthority:
    """Cold-admission proof for one active support's projection authority."""

    representative: GraphContributionAssertion
    evidence_ref_ids: tuple[str, ...]
    source_artifact_ids: tuple[str, ...]


def _contribution_from_map(
    contributions: Mapping[str, GraphContribution],
    contribution_id: str,
    *,
    assertion_id: str,
) -> GraphContribution:
    contribution = contributions.get(contribution_id)
    if contribution is None:
        raise _integrity_error(
            f"Contribution record {contribution_id!r} could not be loaded.",
            detail=(
                f"assertion_id={assertion_id!r} contribution_id={contribution_id!r} "
                "missing from support-authority contribution set"
            ),
        )
    return contribution


def _collect_assertion_provenance_from_contribution_map(
    store: UnionSupergraphStore,
    support: DurableAssertionSupport,
    contributions: Mapping[str, GraphContribution],
    *,
    graph_object_id: str | None = None,
    materialized_evidence_ref_ids: list[str] | None = None,
) -> tuple[list[str], list[str]]:
    evidence_ids: set[str] = set()
    artifact_ids: set[str] = set()
    resolved_graph_object_id = graph_object_id or support.graph_object_id
    materialized_refs = (
        materialized_evidence_ref_ids
        if materialized_evidence_ref_ids is not None
        else _materialized_evidence_ref_ids(store, resolved_graph_object_id)
    )
    active_contribution_ids = set(support.active_contribution_ids)
    if set(support.per_contribution_evidence_ref_ids) != active_contribution_ids:
        raise _integrity_error(
            "Contribution evidence lineage keys do not match active support.",
            detail=(
                f"assertion_id={support.assertion_id!r} "
                f"active_contributions={sorted(active_contribution_ids)!r} "
                "per_contribution_evidence_ref_ids="
                f"{sorted(support.per_contribution_evidence_ref_ids)!r}"
            ),
        )
    if set(support.per_contribution_source_artifact_ids) != active_contribution_ids:
        raise _integrity_error(
            "Contribution source-artifact lineage keys do not match active support.",
            detail=(
                f"assertion_id={support.assertion_id!r} "
                f"active_contributions={sorted(active_contribution_ids)!r} "
                "per_contribution_source_artifact_ids="
                f"{sorted(support.per_contribution_source_artifact_ids)!r}"
            ),
        )
    for contribution_id in support.active_contribution_ids:
        contribution = _contribution_from_map(
            contributions,
            contribution_id,
            assertion_id=support.assertion_id,
        )
        matched_candidate: GraphContributionAssertion | None = None
        for candidate in contribution.accepted_assertions:
            if candidate.assertion_id != support.assertion_id:
                continue
            matched_candidate = candidate
            break
        if matched_candidate is None:
            raise _integrity_error(
                "Active contribution does not contain the supported assertion.",
                detail=(
                    f"assertion_id={support.assertion_id!r} "
                    f"contribution_id={contribution_id!r}"
                ),
            )
        explicit_evidence_ids = set(explicit_assertion_evidence_ref_ids(matched_candidate))
        explicit_artifact_ids = set(explicit_assertion_source_artifact_ids(matched_candidate))
        recorded_evidence_ids = set(
            support.per_contribution_evidence_ref_ids[contribution_id]
        )
        if explicit_evidence_ids != recorded_evidence_ids:
            raise _integrity_error(
                "Contribution evidence lineage does not match revision support record.",
                detail=(
                    f"assertion_id={support.assertion_id!r} contribution_id={contribution_id!r} "
                    f"loaded_evidence={sorted(explicit_evidence_ids)!r} "
                    f"recorded_evidence={sorted(recorded_evidence_ids)!r}"
                ),
            )
        recorded_artifact_ids = set(
            support.per_contribution_source_artifact_ids[contribution_id]
        )
        if explicit_artifact_ids != recorded_artifact_ids:
            raise _integrity_error(
                "Contribution source artifact lineage does not match revision support record.",
                detail=(
                    f"assertion_id={support.assertion_id!r} contribution_id={contribution_id!r} "
                    f"loaded_artifacts={sorted(explicit_artifact_ids)!r} "
                    f"recorded_artifacts={sorted(recorded_artifact_ids)!r}"
                ),
            )
        evidence_ids.update(explicit_evidence_ids)
        artifact_ids.update(explicit_artifact_ids)
        if (
            matched_candidate is not None
            and not _assertion_has_explicit_evidence(matched_candidate)
            and matched_candidate.assertion_kind in {"node", "edge"}
            and resolved_graph_object_id is not None
            and materialized_refs is not None
        ):
            fallback_id = _generated_fallback_evidence_id(
                contribution_id,
                resolved_graph_object_id,
            )
            if fallback_id in materialized_refs and fallback_id in store.evidence:
                evidence_ids.add(fallback_id)
    for evidence_ref_id in sorted(evidence_ids):
        if evidence_ref_id not in store.evidence:
            raise WorldGraphProjectionError(
                f"Unresolved evidence reference {evidence_ref_id!r}",
                code="projection_integrity_error",
                status_code=409,
                diagnostics=[
                    _diagnostic(
                        "unresolved_evidence_ref",
                        f"Evidence {evidence_ref_id!r} missing from revision store.",
                    )
                ],
            )
        artifact_ids.add(store.evidence[evidence_ref_id].source_artifact_id)
    for source_artifact_id in sorted(artifact_ids):
        if source_artifact_id not in store.source_artifacts:
            raise WorldGraphProjectionError(
                f"Unresolved source artifact {source_artifact_id!r}",
                code="projection_integrity_error",
                status_code=409,
                diagnostics=[
                    _diagnostic(
                        "unresolved_source_artifact",
                        (
                            f"Source artifact {source_artifact_id!r} "
                            "missing from revision store."
                        ),
                    )
                ],
            )
    return sorted(evidence_ids), sorted(artifact_ids)


def _resolve_assertion_from_support_map(
    store: UnionSupergraphStore,
    support: DurableAssertionSupport,
    contributions: Mapping[str, GraphContribution],
) -> tuple[GraphContributionAssertion, tuple[str, ...], tuple[str, ...]]:
    """Validate one active support against an in-memory contribution map."""
    assertions_by_contribution: dict[str, GraphContributionAssertion] = {}
    fingerprints: dict[str, tuple[Any, ...]] = {}

    for contribution_id in support.active_contribution_ids:
        contribution = _contribution_from_map(
            contributions,
            contribution_id,
            assertion_id=support.assertion_id,
        )

        matched: GraphContributionAssertion | None = None
        for candidate in contribution.accepted_assertions:
            if candidate.assertion_id == support.assertion_id:
                matched = candidate
                break
        if matched is None:
            raise _integrity_error(
                f"Assertion {support.assertion_id!r} not found in active contribution.",
                detail=(
                    f"assertion_id={support.assertion_id!r} "
                    f"contribution_id={contribution_id!r}"
                ),
            )
        _validate_assertion_identity(
            matched,
            contribution_id=contribution_id,
            context="matched accepted assertion",
        )
        assertions_by_contribution[contribution_id] = matched
        fingerprints[contribution_id] = _assertion_semantic_fingerprint(matched)

    unique_fingerprints = {fingerprint for fingerprint in fingerprints.values()}
    if len(unique_fingerprints) > 1:
        raise WorldGraphProjectionError(
            f"Assertion {support.assertion_id!r} has semantically divergent active copies.",
            code="projection_integrity_error",
            status_code=409,
            diagnostics=[
                _diagnostic(
                    "semantic_assertion_divergence",
                    (
                        f"Active contributions disagree on semantic fields for "
                        f"assertion {support.assertion_id!r}."
                    ),
                )
            ],
        )

    representative_contribution_id = min(assertions_by_contribution)
    assertion = assertions_by_contribution[representative_contribution_id]

    expected_graph_object_id = support.graph_object_id
    if expected_graph_object_id is not None:
        actual = assertion.subject_node_id or assertion.target_node_id
        if assertion.assertion_kind == "edge":
            value = dict(assertion.value)
            actual = str(value.get("edge_id") or actual or "")
        if actual != expected_graph_object_id:
            raise WorldGraphProjectionError(
                "Assertion graph_object_id does not match contribution payload.",
                code="projection_integrity_error",
                status_code=409,
                diagnostics=[
                    _diagnostic(
                        "graph_object_id_mismatch",
                        (
                            f"support graph_object_id={expected_graph_object_id!r} "
                            f"assertion object={actual!r}"
                        ),
                    )
                ],
            )

    evidence_ref_ids, source_artifact_ids = _collect_assertion_provenance_from_contribution_map(
        store,
        support,
        contributions,
        graph_object_id=support.graph_object_id,
    )
    return assertion, tuple(evidence_ref_ids), tuple(source_artifact_ids)


def build_active_support_authority_index(
    store: UnionSupergraphStore,
    contributions: Mapping[str, GraphContribution],
) -> dict[str, ValidatedSupportAuthority]:
    """Fail-closed cold-admission/scrub proof for every active support."""
    authority: dict[str, ValidatedSupportAuthority] = {}
    for raw_support in store.assertion_support.values():
        support = _parse_support(raw_support)
        if support.support_state != "supported" or not support.active_contribution_ids:
            continue
        representative, evidence_ref_ids, source_artifact_ids = (
            _resolve_assertion_from_support_map(store, support, contributions)
        )
        authority[support.assertion_id] = ValidatedSupportAuthority(
            representative=representative,
            evidence_ref_ids=evidence_ref_ids,
            source_artifact_ids=source_artifact_ids,
        )
    return authority


def _collect_assertion_provenance_from_contributions(
    root: Path,
    world_id: str,
    store: UnionSupergraphStore,
    support: DurableAssertionSupport,
    *,
    graph_object_id: str | None = None,
    materialized_evidence_ref_ids: list[str] | None = None,
) -> tuple[list[str], list[str]]:
    from graph_memory.kernel.world_read_runtime import get_active_resident

    resident = get_active_resident()
    if resident is not None:
        authority = resident.support_authority_by_assertion_id.get(support.assertion_id)
        if authority is not None:
            return list(authority.evidence_ref_ids), list(authority.source_artifact_ids)

    contributions = {
        contribution_id: _load_validated_contribution(root, world_id, contribution_id)
        for contribution_id in support.active_contribution_ids
    }
    return _collect_assertion_provenance_from_contribution_map(
        store,
        support,
        contributions,
        graph_object_id=graph_object_id,
        materialized_evidence_ref_ids=materialized_evidence_ref_ids,
    )


def _resolve_assertion_from_support(
    root: Path,
    world_id: str,
    store: UnionSupergraphStore,
    support: DurableAssertionSupport,
) -> GraphContributionAssertion:
    from graph_memory.kernel.world_read_runtime import get_active_resident

    resident = get_active_resident()
    if resident is not None:
        authority = resident.support_authority_by_assertion_id.get(support.assertion_id)
        if authority is not None:
            return authority.representative
        if support.support_state == "supported" and support.active_contribution_ids:
            raise _integrity_error(
                "Active support missing from resident authority index.",
                detail=(
                    f"assertion_id={support.assertion_id!r} "
                    f"generation={resident.generation}"
                ),
            )

    contributions = {
        contribution_id: _load_validated_contribution(root, world_id, contribution_id)
        for contribution_id in support.active_contribution_ids
    }
    assertion, _evidence_ref_ids, _source_artifact_ids = _resolve_assertion_from_support_map(
        store,
        support,
        contributions,
    )
    return assertion


def _supports_for_graph_object(
    store: UnionSupergraphStore,
    graph_object_id: str,
) -> list[DurableAssertionSupport]:
    supports: list[DurableAssertionSupport] = []
    for raw_support in store.assertion_support.values():
        support = _parse_support(raw_support)
        if support.graph_object_id == graph_object_id:
            supports.append(support)
    return supports


def _edge_state_field(edge_state: dict[str, Any], key: str) -> str | None:
    value = edge_state.get(key)
    return str(value) if value is not None else None


def _build_evidence_badge_from_store(
    store: UnionSupergraphStore,
    evidence_ref_id: str,
    focus_session_id: str | None,
    *,
    focus_campaign_id: str | None = None,
) -> GraphProjectionEvidenceBadge:
    evidence = store.evidence[evidence_ref_id]
    evidence_extra = evidence.model_extra or {}
    stored_label = evidence_extra.get("label")
    if isinstance(stored_label, str) and stored_label.strip():
        badge_label = stored_label.strip()
    else:
        badge_label = evidence.evidence_role.replace("_", " ")
    return GraphProjectionEvidenceBadge(
        evidence_ref_id=evidence.evidence_ref_id,
        source_artifact_id=evidence.source_artifact_id,
        source_domain=str(evidence.source_domain),
        evidence_role=evidence.evidence_role,
        is_focus_session_evidence=_evidence_matches_focus(
            store,
            evidence_ref_id,
            focus_session_id=focus_session_id,
            focus_campaign_id=focus_campaign_id,
        ),
        can_open_source=evidence.can_open_source,
        can_highlight_span=evidence.can_highlight_span,
        label=badge_label,
        session_id=evidence.session_id,
        source_span_ref_id=evidence.source_span_ref_id,
    )


def _union_session_ids_from_active_edge_assertions(
    active_assertions: list[GraphContributionAssertion],
) -> list[str] | None:
    """Union ``value.session_ids`` across active edge supports when the key is present.

    Returns ``None`` when no active assertion declares ``session_ids`` (caller
    keeps store-edge fallback). An explicit empty list from a sole active
    support still returns ``[]`` so supersession can clear the projected list.
    """
    session_ids: list[str] = []
    key_present = False
    for assertion in active_assertions:
        assertion_value = dict(assertion.value)
        if "session_ids" not in assertion_value:
            continue
        key_present = True
        nested = assertion_value.get("session_ids")
        if not isinstance(nested, list):
            continue
        for item in nested:
            session_id = str(item)
            if session_id not in session_ids:
                session_ids.append(session_id)
    return session_ids if key_present else None


def _aggregate_active_edge_support(
    root: Path,
    world_id: str,
    store: UnionSupergraphStore,
    edge_id: str,
    edge: UnionSupergraphEdge,
    active_supports: list[DurableAssertionSupport],
) -> tuple[
    list[str],
    list[str],
    list[str],
    GraphContributionAssertion | None,
    list[str] | None,
]:
    evidence_ids: set[str] = set()
    artifact_ids: set[str] = set()
    active_contribution_ids: set[str] = set()
    materialized_refs = list(edge.evidence_ref_ids)
    representative_assertion: GraphContributionAssertion | None = None
    active_assertions: list[GraphContributionAssertion] = []
    for support in active_supports:
        assertion = _resolve_assertion_from_support(root, world_id, store, support)
        active_assertions.append(assertion)
        if representative_assertion is None:
            representative_assertion = assertion
        active_contribution_ids.update(support.active_contribution_ids)
        support_evidence, support_artifacts = _collect_assertion_provenance_from_contributions(
            root,
            world_id,
            store,
            support,
            graph_object_id=edge_id,
            materialized_evidence_ref_ids=materialized_refs,
        )
        evidence_ids.update(support_evidence)
        artifact_ids.update(support_artifacts)
    _assert_active_edge_assertions_agree(
        active_assertions,
        graph_object_id=edge_id,
    )
    return (
        sorted(active_contribution_ids),
        sorted(evidence_ids),
        sorted(artifact_ids),
        representative_assertion,
        _union_session_ids_from_active_edge_assertions(active_assertions),
    )


def _convert_highlight_span(
    span: GraphProjectionTextHighlightSpan,
) -> WorldGraphProjectionTextHighlightSpan:
    return WorldGraphProjectionTextHighlightSpan(start=span.start, end=span.end)


def _convert_evidence_badge(
    badge: GraphProjectionEvidenceBadge,
) -> WorldGraphProjectionEvidenceBadge:
    return WorldGraphProjectionEvidenceBadge(
        evidence_ref_id=badge.evidence_ref_id,
        source_artifact_id=badge.source_artifact_id,
        source_domain=badge.source_domain,
        evidence_role=badge.evidence_role,
        is_focus_session_evidence=badge.is_focus_session_evidence,
        can_open_source=badge.can_open_source,
        can_highlight_span=badge.can_highlight_span,
        label=badge.label,
        session_id=badge.session_id,
        source_span_ref_id=badge.source_span_ref_id,
    )


def _convert_adjacency_candidate(
    candidate: GraphProjectionAdjacencyCandidate,
) -> WorldGraphProjectionAdjacencyCandidate:
    try:
        direction = normalize_world_graph_relationship_direction(candidate.direction)
    except WorldGraphDirectionError as exc:
        raise WorldGraphProjectionError(
            str(exc),
            code="unsupported_relationship_direction",
            status_code=422,
            diagnostics=[
                _diagnostic("unsupported_relationship_direction", str(exc)),
            ],
        ) from exc
    return WorldGraphProjectionAdjacencyCandidate(
        edge_id=candidate.edge_id,
        node_id=candidate.node_id,
        label=candidate.label,
        kind=candidate.kind,
        predicate=candidate.predicate,
        direction=direction,
        anchored_to_focus_session=candidate.anchored_to_focus_session,
        source_domains=list(candidate.source_domains),
        evidence_ref_ids=list(candidate.evidence_ref_ids),
        edge_label=candidate.edge_label,
        session_ids=list(candidate.session_ids),
        campaign_scope=candidate.campaign_scope,
        related_summary=candidate.related_summary,
        source_excerpt=candidate.source_excerpt,
        source_excerpt_is_full_paragraph=candidate.source_excerpt_is_full_paragraph,
        source_excerpt_highlight_spans=[
            _convert_highlight_span(span)
            for span in candidate.source_excerpt_highlight_spans
        ],
    )


def _convert_suggested_expansion(
    expansion: GraphProjectionSuggestedExpansion,
) -> WorldGraphProjectionSuggestedExpansion:
    base = _convert_adjacency_candidate(expansion)
    return WorldGraphProjectionSuggestedExpansion(
        **base.model_dump(),
        rank=expansion.rank,
        rank_reason=expansion.rank_reason,
    )


def _convert_node_view(
    view: GraphProjectionNodeView,
    *,
    label: str | None = None,
    kind: str | None = None,
    role: str | None = None,
    aliases: list[str] | None = None,
    source_domains: list[str] | None = None,
    summary: str | None = None,
    evidence_ref_ids: list[str],
    source_artifact_ids: list[str],
    adjacency: list[GraphProjectionAdjacencyCandidate] | None = None,
    suggested_expansions: list[GraphProjectionSuggestedExpansion] | None = None,
    evidence_badges: list[GraphProjectionEvidenceBadge] | None = None,
    anchored_to_focus_session: bool | None = None,
    campaign_scope: str | None = None,
    external_resource: ExternalResourceV1 | None = None,
) -> WorldGraphProjectionNodeView:
    return WorldGraphProjectionNodeView(
        node_id=view.node_id,
        label=label if label is not None else view.label,
        kind=kind if kind is not None else view.kind,
        role=role if role is not None else view.role,
        aliases=list(aliases if aliases is not None else view.aliases),
        source_domains=list(
            source_domains if source_domains is not None else view.source_domains
        ),
        summary=summary if summary is not None else view.summary,
        anchored_to_focus_session=(
            view.anchored_to_focus_session
            if anchored_to_focus_session is None
            else anchored_to_focus_session
        ),
        campaign_scope=campaign_scope,
        evidence_badges=[
            _convert_evidence_badge(badge)
            for badge in (evidence_badges if evidence_badges is not None else view.evidence_badges)
        ],
        adjacency=[
            _convert_adjacency_candidate(candidate)
            for candidate in (adjacency if adjacency is not None else view.adjacency)
        ],
        suggested_expansions=[
            _convert_suggested_expansion(expansion)
            for expansion in (
                suggested_expansions
                if suggested_expansions is not None
                else view.suggested_expansions
            )
        ],
        evidence_ref_ids=list(evidence_ref_ids),
        source_artifact_ids=list(source_artifact_ids),
        external_resource=external_resource,
    )


def _source_artifact_ids_for_evidence(
    store: UnionSupergraphStore,
    evidence_ref_ids: list[str],
) -> list[str]:
    artifact_ids = {
        store.evidence[evidence_ref_id].source_artifact_id
        for evidence_ref_id in evidence_ref_ids
        if evidence_ref_id in store.evidence
    }
    return sorted(artifact_ids)


def _source_domains_from_active_provenance(
    store: UnionSupergraphStore,
    evidence_ref_ids: list[str],
    source_artifact_ids: list[str],
) -> list[str]:
    domains = {
        str(store.evidence[evidence_ref_id].source_domain)
        for evidence_ref_id in evidence_ref_ids
        if evidence_ref_id in store.evidence
    }
    domains.update(
        str(store.source_artifacts[source_artifact_id].source_domain)
        for source_artifact_id in source_artifact_ids
        if source_artifact_id in store.source_artifacts
    )
    return sorted(domains)


def _edge_semantics_from_assertion(
    assertion: GraphContributionAssertion,
    *,
    fallback: UnionSupergraphEdge,
) -> tuple[str, str, str, str, str | None, str | None, str | None]:
    value = dict(assertion.value)
    return (
        assertion.subject_node_id or str(value.get("source_node_id") or fallback.source_node_id),
        assertion.target_node_id or str(value.get("target_node_id") or fallback.target_node_id),
        assertion.predicate or str(value.get("predicate") or fallback.predicate),
        str(value.get("direction") or fallback.direction or "outbound"),
        assertion.visibility,
        assertion.campaign_scope,
        assertion.epistemic_kind,
    )


def _assert_active_object_assertions_agree(
    assertions: list[GraphContributionAssertion],
    *,
    object_kind: str,
    graph_object_id: str,
) -> None:
    fingerprints = {_assertion_semantic_fingerprint(assertion) for assertion in assertions}
    if len(fingerprints) > 1:
        raise _integrity_error(
            f"Active {object_kind} assertions disagree on semantic fields.",
            detail=(
                f"graph_object_id={graph_object_id!r} "
                f"active_assertion_ids={sorted(assertion.assertion_id for assertion in assertions)!r}"
            ),
        )


def _build_attribute_views(
    root: Path,
    world_id: str,
    store: UnionSupergraphStore,
    *,
    request_campaign_id: str,
    scope_mode: str = "campaign",
) -> list[WorldGraphProjectionAttributeView]:
    attributes: list[WorldGraphProjectionAttributeView] = []
    for raw_support in store.assertion_support.values():
        support = _parse_support(raw_support)
        if support.assertion_kind != "attribute":
            continue
        if support.support_state != "supported" or not support.active_contribution_ids:
            continue
        assertion = _resolve_assertion_from_support(root, world_id, store, support)
        if not _campaign_scope_is_visible(
            assertion.campaign_scope,
            request_campaign_id=request_campaign_id,
            scope_mode=scope_mode,
        ):
            continue
        value = dict(assertion.value)
        evidence_ref_ids, source_artifact_ids = _collect_assertion_provenance_from_contributions(
            root,
            world_id,
            store,
            support,
            graph_object_id=support.graph_object_id,
        )
        attributes.append(
            WorldGraphProjectionAttributeView(
                assertion_id=assertion.assertion_id,
                subject_node_id=assertion.subject_node_id or "",
                predicate=assertion.predicate,
                label=assertion.label,
                value=value,
                text_value=derive_attribute_text_value(value),
                epistemic_kind=assertion.epistemic_kind,
                visibility=assertion.visibility,
                campaign_scope=assertion.campaign_scope,
                temporal_scope=assertion.temporal_scope,
                support_state=support.support_state,
                active_contribution_ids=list(support.active_contribution_ids),
                evidence_ref_ids=evidence_ref_ids,
                source_artifact_ids=source_artifact_ids,
            )
        )
    return sorted(attributes, key=lambda item: item.assertion_id)


def _build_relationship_views(
    root: Path,
    world_id: str,
    store: UnionSupergraphStore,
    *,
    request_campaign_id: str,
    scope_mode: str = "campaign",
) -> list[WorldGraphProjectionRelationshipView]:
    identity_context = _projection_identity_context(store)
    relationships: list[WorldGraphProjectionRelationshipView] = []
    for edge_id, edge in sorted(store.edges.items()):
        if not is_projectable_union_edge(edge, identity_context):
            continue
        if _is_unsupported_graph_object(edge):
            continue
        all_supports = _supports_for_graph_object(store, edge_id)
        active_supports = _active_supports_for_graph_object(store, edge_id)
        if all_supports and not active_supports:
            continue
        active_contribution_ids: list[str] = []
        evidence_ref_ids: list[str] = []
        source_artifact_ids: list[str] = []
        relationship_label = edge.label
        relationship_session_ids = list(edge.session_ids)
        source_node_id = edge.source_node_id
        target_node_id = edge.target_node_id
        predicate = edge.predicate
        direction = edge.direction
        visibility = _edge_state_field(edge.state or {}, "visibility")
        campaign_scope = _edge_state_field(edge.state or {}, "campaign_scope")
        epistemic_kind = _edge_state_field(edge.state or {}, "epistemic_kind")
        threat_statblock_binding: ThreatStatblockBindingV1 | None = None
        if active_supports:
            (
                active_contribution_ids,
                evidence_ref_ids,
                source_artifact_ids,
                representative_assertion,
                aggregated_session_ids,
            ) = _aggregate_active_edge_support(
                root,
                world_id,
                store,
                edge_id,
                edge,
                active_supports,
            )
            if aggregated_session_ids is not None:
                # Union across all active supports — do not replace with one
                # representative assertion's session list.
                relationship_session_ids = aggregated_session_ids
            if representative_assertion is not None:
                assertion_value = dict(representative_assertion.value)
                (
                    source_node_id,
                    target_node_id,
                    predicate,
                    direction,
                    visibility,
                    campaign_scope,
                    epistemic_kind,
                ) = _edge_semantics_from_assertion(
                    representative_assertion,
                    fallback=edge,
                )
                label_override = representative_assertion.label
                if label_override is None:
                    nested_label = assertion_value.get("label")
                    if isinstance(nested_label, str) and nested_label:
                        label_override = nested_label
                if label_override is not None:
                    relationship_label = label_override
                threat_statblock_binding = parse_threat_statblock_binding_assertion(
                    subject_node_id=representative_assertion.subject_node_id,
                    target_node_id=representative_assertion.target_node_id,
                    predicate=representative_assertion.predicate,
                    value=assertion_value,
                )
                if (
                    threat_statblock_binding is not None
                    and edge.threat_statblock_binding != threat_statblock_binding
                ):
                    raise _integrity_error(
                        "Stored statblock binding disagrees with active assertion authority.",
                        detail=f"edge_id={edge_id!r}",
                    )
        elif edge.evidence_ref_ids:
            evidence_ref_ids = list(edge.evidence_ref_ids)
            source_artifact_ids = _source_artifact_ids_for_evidence(store, evidence_ref_ids)
        if not active_supports:
            threat_statblock_binding = edge.threat_statblock_binding
        if not _campaign_scope_is_visible(
            campaign_scope,
            request_campaign_id=request_campaign_id,
            scope_mode=scope_mode,
        ):
            continue
        source_domains = _source_domains_from_active_provenance(
            store,
            evidence_ref_ids,
            source_artifact_ids,
        )
        try:
            normalized_direction = normalize_world_graph_relationship_direction(
                direction
            )
        except WorldGraphDirectionError as exc:
            raise WorldGraphProjectionError(
                str(exc),
                code="unsupported_relationship_direction",
                status_code=422,
                diagnostics=[
                    _diagnostic("unsupported_relationship_direction", str(exc)),
                ],
            ) from exc
        relationships.append(
            WorldGraphProjectionRelationshipView(
                edge_id=edge.edge_id,
                source_node_id=source_node_id,
                target_node_id=target_node_id,
                predicate=predicate,
                label=relationship_label,
                direction=normalized_direction,
                session_ids=relationship_session_ids,
                source_domains=source_domains,
                visibility=visibility,
                campaign_scope=campaign_scope,
                epistemic_kind=epistemic_kind,
                evidence_ref_ids=evidence_ref_ids,
                source_artifact_ids=source_artifact_ids,
                active_contribution_ids=active_contribution_ids,
                threat_statblock_binding=threat_statblock_binding,
            )
        )
    return relationships


def _active_supports_for_graph_object(
    store: UnionSupergraphStore,
    graph_object_id: str,
) -> list[DurableAssertionSupport]:
    from graph_memory.kernel.world_read_runtime import get_active_resident

    resident = get_active_resident()
    if resident is not None and resident.store is store:
        return list(resident.supports_by_graph_object.get(graph_object_id, ()))

    supports: list[DurableAssertionSupport] = []
    for raw_support in store.assertion_support.values():
        support = _parse_support(raw_support)
        if support.graph_object_id != graph_object_id:
            continue
        if support.support_state != "supported" or not support.active_contribution_ids:
            continue
        supports.append(support)
    return supports


def _projection_identity_context(store: UnionSupergraphStore) -> UnionProjectionIdentityContext:
    from graph_memory.kernel.world_read_runtime import get_active_resident

    resident = get_active_resident()
    if resident is not None and resident.store is store:
        return resident.identity_context
    return build_union_projection_identity_context(store)


def _node_evidence_from_projection_context(
    root: Path,
    world_id: str,
    store: UnionSupergraphStore,
    node_id: str,
    attributes: list[WorldGraphProjectionAttributeView],
    relationships: list[WorldGraphProjectionRelationshipView],
) -> tuple[list[str], list[str]]:
    evidence_ids: set[str] = set()
    artifact_ids: set[str] = set()
    for attribute in attributes:
        if attribute.subject_node_id == node_id:
            evidence_ids.update(attribute.evidence_ref_ids)
            artifact_ids.update(attribute.source_artifact_ids)
    for relationship in relationships:
        if node_id not in {relationship.source_node_id, relationship.target_node_id}:
            continue
        evidence_ids.update(relationship.evidence_ref_ids)
        artifact_ids.update(relationship.source_artifact_ids)
    for support in _active_supports_for_graph_object(store, node_id):
        support_evidence, support_artifacts = _collect_assertion_provenance_from_contributions(
            root,
            world_id,
            store,
            support,
            graph_object_id=node_id,
            materialized_evidence_ref_ids=_materialized_evidence_ref_ids(store, node_id),
        )
        evidence_ids.update(support_evidence)
        artifact_ids.update(support_artifacts)
    return sorted(evidence_ids), sorted(artifact_ids)


def _active_node_aliases(
    root: Path,
    world_id: str,
    store: UnionSupergraphStore,
    node_id: str,
    identity_context: UnionProjectionIdentityContext,
    base_aliases: list[str],
) -> list[str]:
    """Reconstruct a node's aliases from every authority that can contribute one.

    Aliases are additive by design (an alias, once valid, does not stop being
    valid the way a corrected label/kind/role does), but they must still
    disappear if the assertion that introduced them is retracted. So this
    unions three distinct sources rather than trusting the materialized
    ``UnionSupergraphNode.aliases`` field, which accumulates forever and never
    removes an alias on retraction:
      * the active node assertion's own declared aliases (``base_aliases``);
      * active dedicated ``alias``-kind assertions, which do disappear when
        retracted since they are looked up via active assertion support;
      * identity-survivor aliases inherited from nodes merged away during
        identity reconciliation, which is a durable one-time structural fact
        (not something with its own retractable assertion support record).
    """
    aliases = list(dict.fromkeys(base_aliases))
    alias_supports = [
        support
        for support in _active_supports_for_graph_object(store, node_id)
        if support.assertion_kind == "alias"
    ]
    for support in alias_supports:
        assertion = _resolve_assertion_from_support(root, world_id, store, support)
        value = dict(assertion.value)
        alias = assertion.label or str(value.get("alias") or "")
        if alias and alias not in aliases:
            aliases.append(alias)
    for record in identity_context.merge_records_by_survivor.get(node_id, ()):
        for merged_away_id in record.merged_away_node_ids:
            merged_node = store.nodes.get(merged_away_id)
            if merged_node is None:
                continue
            if merged_node.label and merged_node.label not in aliases:
                aliases.append(merged_node.label)
            for alias in merged_node.aliases:
                if alias not in aliases:
                    aliases.append(alias)
    return aliases


def _active_node_campaign_scope(
    root: Path,
    world_id: str,
    store: UnionSupergraphStore,
    node_id: str,
    fallback_node: UnionSupergraphNode,
) -> str | None:
    """Prefer active node-assertion campaign_scope over stale materialized state."""
    node_supports = [
        support
        for support in _active_supports_for_graph_object(store, node_id)
        if support.assertion_kind == "node"
    ]
    if node_supports:
        assertions = [
            _resolve_assertion_from_support(root, world_id, store, support)
            for support in node_supports
        ]
        _assert_active_node_assertions_agree(assertions, node_id=node_id)
        representative = min(assertions, key=lambda assertion: assertion.assertion_id)
        return representative.campaign_scope
    return _object_campaign_scope(
        fallback_node.state if isinstance(fallback_node.state, Mapping) else None
    )


def _union_node_description_summary(node: UnionSupergraphNode) -> str | None:
    description = (node.model_extra or {}).get("description")
    if isinstance(description, str) and description.strip():
        return description.strip()
    return None


def _assertion_value_summary(value: Mapping[str, Any] | None) -> str | None:
    raw = dict(value or {}).get("summary")
    if isinstance(raw, str) and raw.strip():
        return raw.strip()
    return None


def _active_node_semantics(
    root: Path,
    world_id: str,
    store: UnionSupergraphStore,
    node_id: str,
    fallback: UnionSupergraphNode,
    identity_context: UnionProjectionIdentityContext,
) -> tuple[str, str, str, list[str], str | None]:
    node_supports = [
        support
        for support in _active_supports_for_graph_object(store, node_id)
        if support.assertion_kind == "node"
    ]
    if not node_supports:
        aliases = _active_node_aliases(
            root, world_id, store, node_id, identity_context, list(fallback.aliases)
        )
        return (
            fallback.label,
            fallback.kind,
            fallback.role,
            aliases,
            _union_node_description_summary(fallback),
        )
    assertions = [
        _resolve_assertion_from_support(root, world_id, store, support)
        for support in node_supports
    ]
    _assert_active_node_assertions_agree(assertions, node_id=node_id)
    representative = min(assertions, key=lambda assertion: assertion.assertion_id)
    value = dict(representative.value)
    label = representative.label or str(value.get("label") or fallback.label)
    kind = str(value.get("kind") or fallback.kind)
    role = str(value.get("role") or kind)
    summary = _assertion_value_summary(value) or _union_node_description_summary(fallback)
    base_aliases = [
        alias
        for assertion in assertions
        for alias in list(dict(assertion.value).get("aliases") or [])
    ]
    if not base_aliases:
        base_aliases = [label]
    aliases = _active_node_aliases(
        root, world_id, store, node_id, identity_context, base_aliases
    )
    return label, kind, role, aliases, summary


def _active_external_resource(
    root: Path,
    world_id: str,
    store: UnionSupergraphStore,
    node_id: str,
    fallback: UnionSupergraphNode,
) -> ExternalResourceV1 | None:
    supports = [
        support
        for support in _active_supports_for_graph_object(store, node_id)
        if support.assertion_kind == "node"
    ]
    if not supports:
        return fallback.external_resource
    resources: list[ExternalResourceV1] = []
    for support in supports:
        assertion = _resolve_assertion_from_support(root, world_id, store, support)
        resource = parse_external_resource_assertion(
            subject_node_id=assertion.subject_node_id,
            value=dict(assertion.value),
        )
        if resource is not None:
            resources.append(resource)
    if not resources:
        return None
    if any(resource != resources[0] for resource in resources[1:]):
        raise _integrity_error(
            "Active external-resource assertions disagree.",
            detail=f"node_id={node_id!r}",
        )
    if fallback.external_resource != resources[0]:
        raise _integrity_error(
            "Stored external-resource state disagrees with active assertion authority.",
            detail=f"node_id={node_id!r}",
        )
    return resources[0]


def _endpoint_relative_direction(
    relationship: WorldGraphProjectionRelationshipView,
    source_node_id: str,
) -> str:
    """Direction of ``relationship`` as seen from ``source_node_id``'s own node card.

    Node-card direction is endpoint-relative, not a copy of the edge's single
    global ``direction`` value: the same edge must read "outbound" on its
    source node's card and "inbound" on its target node's card (matching the
    convention ``rebuild_adjacency`` already establishes for
    ``store.adjacency``). A correction that swaps an edge's source/target
    changes which endpoint gets which label, so this is derived from the
    (possibly corrected) relationship endpoints rather than cached.
    """
    if relationship.source_node_id == source_node_id:
        return "outbound"
    if relationship.target_node_id == source_node_id:
        return "inbound"
    return relationship.direction or ""


def _resolve_repo_uri_file(uri: str, world_root: Path) -> Path | None:
    """Resolve a ``repo://…`` artifact URI to an on-disk file under the repo.

    ``world_root`` is typically ``<repo>/out`` (``world_graph_root()``). Artifact
    URIs are repo-relative (``repo://out/graph_memory/runs/…``), so resolution
    tries ``world_root.parent / <rel>`` first, then paths under ``world_root``.
    """
    if not isinstance(uri, str) or not uri.startswith("repo://"):
        return None
    rel = uri[len("repo://") :].lstrip("/")
    if not rel or ".." in Path(rel).parts:
        return None
    world_root = world_root.resolve()
    repo_root = world_root.parent
    candidates = [
        (repo_root / rel).resolve(),
        (world_root / rel).resolve(),
    ]
    rel_path = Path(rel)
    if rel_path.parts and rel_path.parts[0] == world_root.name:
        candidates.insert(1, (world_root.joinpath(*rel_path.parts[1:])).resolve())
    for path in candidates:
        try:
            path.relative_to(repo_root)
        except ValueError:
            continue
        if path.is_file():
            return path
    return None


def _load_source_span_paragraph_text_index(index_path: Path) -> dict[str, str]:
    """Load span_id → full paragraph text from an ingest ``source_span_index.json``."""
    try:
        payload = json.loads(index_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    spans = payload.get("spans")
    if not isinstance(spans, list):
        return {}
    paragraph_text_by_span_id: dict[str, str] = {}
    for span in spans:
        if not isinstance(span, dict):
            continue
        if span.get("kind") != "paragraph":
            continue
        span_id = span.get("span_id") or span.get("source_span_ref_id")
        # Prefer full ``text`` over truncated ``text_excerpt`` (240-char preview).
        text = span.get("text") or span.get("text_excerpt")
        if isinstance(span_id, str) and isinstance(text, str) and text.strip():
            paragraph_text_by_span_id.setdefault(span_id, text)
    return paragraph_text_by_span_id


def _paragraph_text_by_span_id_from_source_artifacts(
    root: Path,
    store: UnionSupergraphStore,
) -> dict[str, str]:
    """Build span_id → paragraph text from source-artifact ingest run indexes.

    World-graph evidence points at ``source_span_ref_id`` values but does not
    embed paragraph prose. Ingest runs keep that prose in sibling
    ``source_span_index.json`` files next to the artifact's ``normalized_recap``.
    """
    from graph_memory.kernel.world_read_runtime import get_active_resident

    resident = get_active_resident()
    if resident is not None and resident.store is store:
        return dict(resident.source_span_paragraph_text)

    paragraph_text_by_span_id: dict[str, str] = {}
    for artifact in store.source_artifacts.values():
        uri = getattr(artifact, "uri", None)
        if not isinstance(uri, str) or not uri.strip():
            continue
        artifact_path = _resolve_repo_uri_file(uri, root)
        if artifact_path is None:
            continue
        index_path = artifact_path.parent / "source_span_index.json"
        if not index_path.is_file():
            continue
        for span_id, text in _load_source_span_paragraph_text_index(index_path).items():
            paragraph_text_by_span_id.setdefault(span_id, text)
    return paragraph_text_by_span_id


def _adjacency_campaign_scope(
    relationship: WorldGraphProjectionRelationshipView,
    *,
    store: UnionSupergraphStore,
    related_node_id: str,
) -> str | None:
    """Prefer edge tenancy; fall back to related-node scope for world-universal edges."""
    if relationship.campaign_scope is not None:
        text = str(relationship.campaign_scope).strip()
        return text or None
    related = store.nodes.get(related_node_id)
    if related is None:
        return None
    return _object_campaign_scope(
        related.state if isinstance(related.state, Mapping) else None
    )


def _normalized_adjacency_candidate(
    candidate: GraphProjectionAdjacencyCandidate,
    relationship: WorldGraphProjectionRelationshipView,
    *,
    store: UnionSupergraphStore,
    source_node_id: str,
    node_metadata: dict[str, tuple[str, str, str, list[str], str | None]],
    focus_session_id: str | None,
    focus_campaign_id: str | None = None,
    paragraph_text_by_span_id: Mapping[str, str] | None = None,
) -> GraphProjectionAdjacencyCandidate:
    related_node_id = (
        relationship.target_node_id
        if relationship.source_node_id == source_node_id
        else relationship.source_node_id
    )
    related_label, related_kind, _related_role, _related_aliases, related_summary = (
        node_metadata.get(
            related_node_id,
            (candidate.label, candidate.kind, "", [], candidate.related_summary),
        )
    )
    source_excerpt = candidate.source_excerpt
    source_excerpt_is_full_paragraph = candidate.source_excerpt_is_full_paragraph
    source_excerpt_highlight_spans = list(candidate.source_excerpt_highlight_spans)
    if not (isinstance(source_excerpt, str) and source_excerpt.strip()):
        resolved = _resolve_evidence_source_excerpt(
            store,
            relationship.evidence_ref_ids,
            paragraph_text_by_span_id=paragraph_text_by_span_id,
        )
        source_excerpt = resolved.text
        source_excerpt_is_full_paragraph = resolved.is_full_paragraph
        source_excerpt_highlight_spans = list(resolved.highlight_spans)
    return GraphProjectionAdjacencyCandidate(
        edge_id=relationship.edge_id,
        node_id=related_node_id,
        label=related_label,
        kind=related_kind,
        predicate=relationship.predicate,
        direction=_endpoint_relative_direction(relationship, source_node_id),
        anchored_to_focus_session=_relationship_matches_focus(
            store,
            relationship,
            focus_session_id=focus_session_id,
            focus_campaign_id=focus_campaign_id,
        ),
        source_domains=list(relationship.source_domains),
        evidence_ref_ids=list(relationship.evidence_ref_ids),
        edge_label=relationship.label,
        session_ids=list(relationship.session_ids),
        campaign_scope=_adjacency_campaign_scope(
            relationship,
            store=store,
            related_node_id=related_node_id,
        ),
        related_summary=related_summary if related_summary is not None else candidate.related_summary,
        source_excerpt=source_excerpt,
        source_excerpt_is_full_paragraph=source_excerpt_is_full_paragraph,
        source_excerpt_highlight_spans=source_excerpt_highlight_spans,
    )


def _build_node_views(
    root: Path,
    world_id: str,
    store: UnionSupergraphStore,
    focus: WorldGraphProjectionFocus,
    attributes: list[WorldGraphProjectionAttributeView],
    relationships: list[WorldGraphProjectionRelationshipView],
    *,
    request_campaign_id: str,
    scope_mode: str = "campaign",
) -> list[WorldGraphProjectionNodeView]:
    identity_context = _projection_identity_context(store)
    focus_session_id = focus.session_id if focus.kind == "session" else None
    focus_campaign_id = _effective_focus_campaign_id(
        focus, request_campaign_id=request_campaign_id
    )
    focus_evidence_ids = {
        evidence_ref_id
        for evidence_ref_id in store.evidence
        if _evidence_matches_focus(
            store,
            evidence_ref_id,
            focus_session_id=focus_session_id,
            focus_campaign_id=focus_campaign_id,
        )
    }
    node_metadata = {
        node_id: _active_node_semantics(
            root, world_id, store, node_id, node, identity_context
        )
        for node_id, node in store.nodes.items()
        if not _is_unsupported_graph_object(node)
    }
    paragraph_text_by_span_id = _paragraph_text_by_span_id_from_source_artifacts(
        root, store
    )
    nodes: list[WorldGraphProjectionNodeView] = []
    for node_id in sorted(projectable_node_ids(store, identity_context)):
        node = store.nodes[node_id]
        if not is_projectable_union_node(node, identity_context):
            continue
        if _is_unsupported_graph_object(node):
            continue
        node_campaign_scope = _active_node_campaign_scope(
            root, world_id, store, node_id, node
        )
        if not _campaign_scope_is_visible(
            node_campaign_scope,
            request_campaign_id=request_campaign_id,
            scope_mode=scope_mode,
        ):
            continue
        view = build_node_view(
            store,
            node_id,
            focus_session_id=focus_session_id,
            identity_context=identity_context,
        )
        relationships_by_edge_id = {
            relationship.edge_id: relationship
            for relationship in relationships
            if node_id in {relationship.source_node_id, relationship.target_node_id}
        }

        def _normalize(
            candidate: GraphProjectionAdjacencyCandidate,
        ) -> GraphProjectionAdjacencyCandidate:
            return _normalized_adjacency_candidate(
                candidate,
                relationships_by_edge_id[candidate.edge_id],
                store=store,
                source_node_id=node_id,
                node_metadata=node_metadata,
                focus_session_id=focus_session_id,
                focus_campaign_id=focus_campaign_id,
                paragraph_text_by_span_id=paragraph_text_by_span_id,
            )

        def _synthesize(edge_id: str) -> GraphProjectionAdjacencyCandidate:
            relationship = relationships_by_edge_id[edge_id]
            related_node_id = (
                relationship.target_node_id
                if relationship.source_node_id == node_id
                else relationship.source_node_id
            )
            placeholder = GraphProjectionAdjacencyCandidate(
                edge_id=edge_id,
                node_id=related_node_id,
                label=node_metadata.get(
                    related_node_id, (related_node_id, "unknown", "", [], None)
                )[0],
                kind=node_metadata.get(related_node_id, ("", "unknown", "", [], None))[1],
                predicate=relationship.predicate,
                direction="",
            )
            return _normalize(placeholder)

        # Preserve the original view's ordering (and, for suggested_expansions,
        # its established focus-first rank/rank_reason) rather than
        # regenerating from scratch — only normalize the correction-sensitive
        # fields (direction, evidence, labels) on each still-active entry, and
        # append genuinely new relationships absent from the source node view.
        filtered_adjacency: list[GraphProjectionAdjacencyCandidate] = []
        seen_adjacency_edge_ids: set[str] = set()
        for candidate in view.adjacency:
            if candidate.edge_id not in relationships_by_edge_id:
                continue
            filtered_adjacency.append(_normalize(candidate))
            seen_adjacency_edge_ids.add(candidate.edge_id)
        for edge_id in relationships_by_edge_id:
            if edge_id in seen_adjacency_edge_ids:
                continue
            filtered_adjacency.append(_synthesize(edge_id))
            seen_adjacency_edge_ids.add(edge_id)

        filtered_expansions: list[GraphProjectionSuggestedExpansion] = []
        seen_expansion_edge_ids: set[str] = set()
        for expansion in view.suggested_expansions:
            if expansion.edge_id not in relationships_by_edge_id:
                continue
            normalized = _normalize(expansion)
            filtered_expansions.append(
                GraphProjectionSuggestedExpansion(
                    **normalized.model_dump(),
                    rank=expansion.rank,
                    rank_reason=expansion.rank_reason,
                )
            )
            seen_expansion_edge_ids.add(expansion.edge_id)
        next_rank = max((expansion.rank for expansion in filtered_expansions), default=0) + 1
        adjacency_by_edge_id = {
            candidate.edge_id: candidate for candidate in filtered_adjacency
        }
        for edge_id in relationships_by_edge_id:
            if edge_id in seen_expansion_edge_ids:
                continue
            filtered_expansions.append(
                GraphProjectionSuggestedExpansion(
                    **adjacency_by_edge_id[edge_id].model_dump(),
                    rank=next_rank,
                    rank_reason="active relationship",
                )
            )
            next_rank += 1
        evidence_ref_ids, source_artifact_ids = _node_evidence_from_projection_context(
            root,
            world_id,
            store,
            node_id,
            attributes,
            relationships,
        )
        active_evidence_ids = set(evidence_ref_ids)
        badge_by_id = {
            evidence_ref_id: _build_evidence_badge_from_store(
                store,
                evidence_ref_id,
                focus_session_id,
                focus_campaign_id=focus_campaign_id,
            )
            for evidence_ref_id in evidence_ref_ids
            if evidence_ref_id in store.evidence
        }
        filtered_badges = [
            badge_by_id[evidence_ref_id]
            for evidence_ref_id in evidence_ref_ids
            if evidence_ref_id in badge_by_id
        ]
        anchored_to_focus_session = bool(active_evidence_ids.intersection(focus_evidence_ids)) or any(
            candidate.anchored_to_focus_session for candidate in filtered_adjacency
        )
        nodes.append(
            _convert_node_view(
                view,
                label=node_metadata[node_id][0],
                kind=node_metadata[node_id][1],
                role=node_metadata[node_id][2],
                aliases=node_metadata[node_id][3],
                summary=node_metadata[node_id][4],
                source_domains=_source_domains_from_active_provenance(
                    store,
                    evidence_ref_ids,
                    source_artifact_ids,
                ),
                evidence_ref_ids=evidence_ref_ids,
                source_artifact_ids=source_artifact_ids,
                adjacency=filtered_adjacency,
                suggested_expansions=filtered_expansions,
                evidence_badges=filtered_badges,
                anchored_to_focus_session=anchored_to_focus_session,
                campaign_scope=node_campaign_scope,
                external_resource=_active_external_resource(
                    root,
                    world_id,
                    store,
                    node_id,
                    node,
                ),
            )
        )
    return nodes


def _count_omitted_unsupported_objects(store: UnionSupergraphStore) -> tuple[int, int]:
    identity_context = _projection_identity_context(store)
    omitted_nodes = sum(
        1
        for node in store.nodes.values()
        if is_projectable_union_node(node, identity_context)
        and _is_unsupported_graph_object(node)
    )
    omitted_edges = sum(
        1
        for edge in store.edges.values()
        if is_projectable_union_edge(edge, identity_context)
        and _is_unsupported_graph_object(edge)
    )
    return omitted_nodes, omitted_edges


def _collect_projection_provenance_ids(
    nodes: list[WorldGraphProjectionNodeView],
    attributes: list[WorldGraphProjectionAttributeView],
    relationships: list[WorldGraphProjectionRelationshipView],
) -> list[str]:
    evidence_ids: set[str] = set()
    for node in nodes:
        evidence_ids.update(node.evidence_ref_ids)
    for attribute in attributes:
        evidence_ids.update(attribute.evidence_ref_ids)
    for relationship in relationships:
        evidence_ids.update(relationship.evidence_ref_ids)
    return sorted(evidence_ids)


def _collect_projection_source_artifact_ids(
    store: UnionSupergraphStore,
    nodes: list[WorldGraphProjectionNodeView],
    attributes: list[WorldGraphProjectionAttributeView],
    relationships: list[WorldGraphProjectionRelationshipView],
    evidence_ids: list[str],
) -> list[str]:
    artifact_ids: set[str] = set()
    for node in nodes:
        artifact_ids.update(node.source_artifact_ids)
    for attribute in attributes:
        artifact_ids.update(attribute.source_artifact_ids)
    for relationship in relationships:
        artifact_ids.update(relationship.source_artifact_ids)
    for evidence_id in evidence_ids:
        evidence = store.evidence.get(evidence_id)
        if evidence is not None:
            artifact_ids.add(evidence.source_artifact_id)
    for source_artifact_id in sorted(artifact_ids):
        if source_artifact_id not in store.source_artifacts:
            raise WorldGraphProjectionError(
                f"Unresolved source artifact {source_artifact_id!r}",
                code="projection_integrity_error",
                status_code=409,
                diagnostics=[
                    _diagnostic(
                        "unresolved_source_artifact",
                        (
                            f"Source artifact {source_artifact_id!r} "
                            "missing from revision store."
                        ),
                    )
                ],
            )
    return sorted(artifact_ids)


def _build_evidence_views(
    store: UnionSupergraphStore,
    evidence_ids: list[str],
) -> list[WorldGraphProjectionEvidenceView]:
    evidence_views: list[WorldGraphProjectionEvidenceView] = []
    for evidence_id in evidence_ids:
        if evidence_id not in store.evidence:
            continue
        evidence = store.evidence[evidence_id]
        evidence_views.append(
            WorldGraphProjectionEvidenceView(
                evidence_ref_id=evidence.evidence_ref_id,
                source_artifact_id=evidence.source_artifact_id,
                source_domain=str(evidence.source_domain),
                session_id=evidence.session_id,
                campaign_id=_evidence_campaign_id(store, evidence_id),
                locator=evidence.locator,
                source_span_ref_id=evidence.source_span_ref_id,
            )
        )
    return evidence_views


def _build_source_artifact_views(
    store: UnionSupergraphStore,
    artifact_ids: list[str],
) -> list[WorldGraphProjectionSourceArtifactView]:
    artifacts: list[WorldGraphProjectionSourceArtifactView] = []
    for artifact_id in artifact_ids:
        if artifact_id not in store.source_artifacts:
            continue
        artifact = store.source_artifacts[artifact_id]
        artifact_extra = artifact.model_extra or {}
        artifacts.append(
            WorldGraphProjectionSourceArtifactView(
                source_artifact_id=artifact.source_artifact_id,
                source_domain=str(artifact.source_domain),
                uri=artifact.uri,
                campaign_id=artifact.campaign_id,
                session_id=(
                    str(artifact_extra["session_id"])
                    if artifact_extra.get("session_id") is not None
                    else None
                ),
            )
        )
    return artifacts


def build_projection_payload(
    *,
    request: WorldGraphProjectionRequest,
    revision_id: str,
    head_revision_id: str,
    store: UnionSupergraphStore,
    root: Path | None = None,
    world_id: str | None = None,
) -> WorldGraphProjection:
    resolve_projection_admissibility(request.admissibility)
    _assert_campaign_scope(request, store)

    resolved_world_id = world_id or request.world_id
    if root is None:
        raise WorldGraphProjectionError(
            "Internal projection build requires root for contribution reconstruction.",
            code="projection_internal_error",
            status_code=500,
        )

    try:
        attributes = _build_attribute_views(
            root,
            resolved_world_id,
            store,
            request_campaign_id=request.campaign_id,
            scope_mode=request.scope_mode,
        )
        relationships = _build_relationship_views(
            root,
            resolved_world_id,
            store,
            request_campaign_id=request.campaign_id,
            scope_mode=request.scope_mode,
        )
        nodes = _build_node_views(
            root,
            resolved_world_id,
            store,
            request.focus,
            attributes,
            relationships,
            request_campaign_id=request.campaign_id,
            scope_mode=request.scope_mode,
        )
        evidence_ids = _collect_projection_provenance_ids(
            nodes,
            attributes,
            relationships,
        )
        evidence = _build_evidence_views(store, evidence_ids)
        source_artifact_ids = _collect_projection_source_artifact_ids(
            store,
            nodes,
            attributes,
            relationships,
            evidence_ids,
        )
        source_artifacts = _build_source_artifact_views(store, source_artifact_ids)
    except WorldGraphProjectionError:
        raise
    except Exception as exc:
        raise WorldGraphProjectionError(
            "World graph projection failed while building payload.",
            code="projection_internal_error",
            status_code=500,
            diagnostics=[_diagnostic("projection_internal_error", str(exc))],
        ) from exc

    identity_context = _projection_identity_context(store)
    focus_session_id = request.focus.session_id if request.focus.kind == "session" else None
    focus_campaign_id = _effective_focus_campaign_id(
        request.focus, request_campaign_id=request.campaign_id
    )
    # Focus overlay remains session-biased; campaign qualification is applied
    # in node/adjacency ranking above. Overlay uses session_id for coarse set.
    overlay = build_focus_overlay(
        store,
        focus_session_id=focus_session_id,
        identity_context=identity_context,
    )
    diagnostics = [
        WorldGraphProjectionDiagnostic(
            code="focus_overlay_built",
            message=(
                f"Focused {len(overlay.focused_node_ids)} nodes for "
                f"focus={request.focus.kind} "
                f"focus_campaign={focus_campaign_id!r} "
                f"scope_mode={request.scope_mode}."
            ),
            severity="info",
        )
    ]
    omitted_nodes, omitted_edges = _count_omitted_unsupported_objects(store)
    if omitted_nodes or omitted_edges:
        diagnostics.append(
            WorldGraphProjectionDiagnostic(
                code="unsupported_objects_omitted",
                message=(
                    f"Omitted {omitted_nodes} unsupported node(s) and "
                    f"{omitted_edges} unsupported relationship(s)."
                ),
                severity="info",
            )
        )

    projection = WorldGraphProjection(
        schema=PROJECTION_RESPONSE_SCHEMA,
        snapshot=WorldGraphProjectionSnapshot(
            world_id=request.world_id,
            campaign_id=request.campaign_id,
            revision_id=revision_id,
            head_revision_id=head_revision_id,
            is_head=revision_id == head_revision_id,
            focus=request.focus,
            admissibility=request.admissibility,
            scope_mode=request.scope_mode,
        ),
        summary=WorldGraphProjectionSummary(
            node_count=len(nodes),
            relationship_count=len(relationships),
            attribute_count=len(attributes),
            evidence_count=len(evidence),
            source_artifact_count=len(source_artifacts),
            projection_truncated=False,
        ),
        nodes=nodes,
        relationships=relationships,
        attributes=attributes,
        evidence=evidence,
        source_artifacts=source_artifacts,
        trust_boundary=WorldGraphProjectionTrustBoundary(
            can_trust=list(_TRUST_CAN_HEAD),
            cannot_trust=list(_TRUST_CANNOT),
        ),
        diagnostics=diagnostics,
    )
    if request.query_text:
        projection = projection.model_copy(
            update={
                "query_context": search_world_graph_projection(
                    projection,
                    request.query_text,
                )
            }
        )
    return projection


def _assert_projection_read_context_matches_request(
    root: Path,
    request: WorldGraphProjectionRequest,
    context: Any,
) -> None:
    """Refuse mismatched resident contexts before building a projection payload."""
    from graph_memory.kernel.world_read_runtime import ProjectionReadContext

    if not isinstance(context, ProjectionReadContext):
        raise WorldGraphProjectionError(
            "Projection read context is invalid.",
            code="projection_internal_error",
            status_code=500,
            diagnostics=[_diagnostic("projection_internal_error", "invalid read context")],
        )

    resolved_root = str(root.resolve())
    selected = context.selected
    head = context.head
    mismatches: list[str] = []
    if selected.key.resolved_root != resolved_root or head.key.resolved_root != resolved_root:
        mismatches.append("resolved_root")
    if selected.key.world_id != request.world_id or head.key.world_id != request.world_id:
        mismatches.append("world_id")
    if context.selected_revision_id != selected.key.revision_id:
        mismatches.append("selected_revision_id")
    if context.head_revision_id != head.key.revision_id:
        mismatches.append("head_revision_id")
    if request.revision_pin:
        if context.selected_revision_id != request.revision_pin:
            mismatches.append("revision_pin")
    elif context.selected_revision_id != context.head_revision_id:
        mismatches.append("unpinned_selected_head")
    elif selected.key != head.key:
        mismatches.append("unpinned_resident_key")
    if mismatches:
        raise WorldGraphProjectionError(
            "Projection read context does not match the projection request.",
            code="projection_internal_error",
            status_code=500,
            diagnostics=[
                _diagnostic(
                    "projection_internal_error",
                    "context/request mismatch: " + ", ".join(mismatches),
                )
            ],
        )


def project_world_graph_from_context(
    root: Path,
    request: WorldGraphProjectionRequest,
    context: Any,
) -> WorldGraphProjection:
    """Build a projection from an already-resolved resident read context."""
    from graph_memory.kernel.world_read_runtime import (
        reset_active_resident,
        set_active_resident,
    )

    _assert_projection_read_context_matches_request(root, request, context)

    token = set_active_resident(context.selected)
    try:
        return build_projection_payload(
            request=request,
            revision_id=context.selected_revision_id,
            head_revision_id=context.head_revision_id,
            store=context.selected.store,
            root=root,
            world_id=request.world_id,
        )
    finally:
        reset_active_resident(token)


def project_world_graph(
    root: Path,
    request: WorldGraphProjectionRequest,
) -> WorldGraphProjection:
    from graph_memory.kernel.world_read_runtime import (
        begin_request_io,
        resolve_projection_read_context,
    )

    request = validate_projection_request_policy(request)
    begin_request_io()

    try:
        context = resolve_projection_read_context(root, request)
        return project_world_graph_from_context(root, request, context)
    except WorldGraphProjectionError:
        raise
    except Exception as exc:
        raise WorldGraphProjectionError(
            "World graph projection failed unexpectedly.",
            code="projection_internal_error",
            status_code=500,
            diagnostics=[_diagnostic("projection_internal_error", str(exc))],
        ) from exc


def search_world_graph_projection(
    projection: WorldGraphProjection,
    query_text: str,
) -> WorldGraphQueryContext:
    query = query_text.strip()
    if not query:
        return WorldGraphQueryContext(
            snapshot=projection.snapshot,
            revision_id=projection.snapshot.revision_id,
            query_text=query_text,
            diagnostics=[
                WorldGraphProjectionDiagnostic(
                    code="empty_query",
                    message="Search query is empty.",
                    severity="warning",
                )
            ],
        )

    ranked_nodes, match_reasons = rank_search_node_matches(
        projection.nodes,
        projection.attributes,
        query,
    )

    node_cap = SEARCH_MAX_NODES
    selected_nodes = [node for node, _score in ranked_nodes[:node_cap]]
    selected_node_ids = {node.node_id for node in selected_nodes}
    capped_matched_node_ids = [node.node_id for node in selected_nodes]

    selected_relationships = [
        relationship
        for relationship in projection.relationships
        if relationship.source_node_id in selected_node_ids
        or relationship.target_node_id in selected_node_ids
    ]
    relationship_truncated = len(selected_relationships) > SEARCH_MAX_RELATIONSHIPS
    selected_relationships = selected_relationships[:SEARCH_MAX_RELATIONSHIPS]

    selected_attributes = [
        attribute
        for attribute in projection.attributes
        if attribute.subject_node_id in selected_node_ids
    ]
    attribute_truncated = len(selected_attributes) > SEARCH_MAX_ATTRIBUTES
    selected_attributes = selected_attributes[:SEARCH_MAX_ATTRIBUTES]

    evidence_ids: set[str] = set()
    for node in selected_nodes:
        evidence_ids.update(node.evidence_ref_ids)
    evidence_ids.update(
        evidence_id
        for attribute in selected_attributes
        for evidence_id in attribute.evidence_ref_ids
    )
    evidence_ids.update(
        evidence_id
        for relationship in selected_relationships
        for evidence_id in relationship.evidence_ref_ids
    )
    selected_evidence = [
        item for item in projection.evidence if item.evidence_ref_id in evidence_ids
    ]
    evidence_truncated = len(selected_evidence) > SEARCH_MAX_EVIDENCE
    selected_evidence = selected_evidence[:SEARCH_MAX_EVIDENCE]

    artifact_ids: set[str] = set()
    for node in selected_nodes:
        artifact_ids.update(node.source_artifact_ids)
    for attribute in selected_attributes:
        artifact_ids.update(attribute.source_artifact_ids)
    for relationship in selected_relationships:
        artifact_ids.update(relationship.source_artifact_ids)
    for evidence in selected_evidence:
        artifact_ids.add(evidence.source_artifact_id)
    selected_artifacts = [
        item
        for item in projection.source_artifacts
        if item.source_artifact_id in artifact_ids
    ]
    artifact_truncated = len(selected_artifacts) > SEARCH_MAX_SOURCE_ARTIFACTS
    selected_artifacts = selected_artifacts[:SEARCH_MAX_SOURCE_ARTIFACTS]

    diagnostics: list[WorldGraphProjectionDiagnostic] = []
    if len(ranked_nodes) > node_cap:
        diagnostics.append(
            WorldGraphProjectionDiagnostic(
                code="search_truncated_nodes",
                message=f"Node matches truncated to {node_cap}.",
                severity="warning",
            )
        )
    if relationship_truncated:
        diagnostics.append(
            WorldGraphProjectionDiagnostic(
                code="search_truncated_relationships",
                message=f"Relationship matches truncated to {SEARCH_MAX_RELATIONSHIPS}.",
                severity="warning",
            )
        )
    if attribute_truncated:
        diagnostics.append(
            WorldGraphProjectionDiagnostic(
                code="search_truncated_attributes",
                message=f"Attribute matches truncated to {SEARCH_MAX_ATTRIBUTES}.",
                severity="warning",
            )
        )
    if evidence_truncated:
        diagnostics.append(
            WorldGraphProjectionDiagnostic(
                code="search_truncated_evidence",
                message=f"Evidence matches truncated to {SEARCH_MAX_EVIDENCE}.",
                severity="warning",
            )
        )
    if artifact_truncated:
        diagnostics.append(
            WorldGraphProjectionDiagnostic(
                code="search_truncated_source_artifacts",
                message=(
                    f"Source artifact matches truncated to {SEARCH_MAX_SOURCE_ARTIFACTS}."
                ),
                severity="warning",
            )
        )

    selected_match_reasons = {
        node_id: match_reasons[node_id]
        for node_id in capped_matched_node_ids
        if node_id in match_reasons
    }

    return WorldGraphQueryContext(
        snapshot=projection.snapshot,
        revision_id=projection.snapshot.revision_id,
        query_text=query_text,
        matched_node_ids=capped_matched_node_ids,
        match_reasons=selected_match_reasons,
        nodes=selected_nodes,
        relationships=selected_relationships,
        attributes=selected_attributes,
        evidence=selected_evidence,
        source_artifacts=selected_artifacts,
        diagnostics=diagnostics,
    )


__all__ = [
    "ValidatedSupportAuthority",
    "WorldGraphProjectionError",
    "build_active_support_authority_index",
    "build_projection_payload",
    "load_world_graph_revision_with_integrity",
    "project_world_graph",
    "project_world_graph_from_context",
    "resolve_projection_admissibility",
    "search_world_graph_projection",
    "validate_projection_request_policy",
]
