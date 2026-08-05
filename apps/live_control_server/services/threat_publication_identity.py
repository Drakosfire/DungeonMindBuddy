"""SBW09b: Threat publication identity-resolution orchestration.

Storage:
    out/threat_publication_identity/<draft_id>/<operation_id>/ledger.json
    out/threat_publication_identity/<draft_id>/<operation_id>/.identity.lock

Lock order:
    identity-resolution lock -> SBW09a publication lock -> World Graph projection

No graph, ThreatDraft, accepted-mechanics, or DungeonMind mutation occurs here.
"""
from __future__ import annotations

import fcntl
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Iterator, Literal

import graph_memory.kernel as kernel
from apps.live_control_server.config import world_graph_root
from apps.live_control_server.models.statblock_mechanics_acceptance import AcceptedMechanicsRefV1
from apps.live_control_server.models.threat_draft import require_draft_id
from apps.live_control_server.models.threat_publication import (
    OperationState,
    ThreatPublicationOperationV1,
    ThreatPublicationResultLabel,
    validate_publication_operation_id,
)
from apps.live_control_server.services.threat_publication_operations import (
    PublicationOperationOutcome,
    refresh_publication_operation,
    read_publication_operation,
)
from apps.live_control_server.models.threat_publication_identity import (
    LEDGER_SCHEMA,
    MATCHING_PROFILE_V1,
    MAX_RESOLUTIONS_PER_OPERATION,
    MAX_TOTAL_CANDIDATES,
    SUGGESTED_ADVISORY_CANDIDATES,
    CreateThreatIdentityResolutionRequestV1,
    PrepareThreatIdentityCandidatesRequestV1,
    ThreatIdentityCandidateSetV1,
    ThreatIdentityCandidateV1,
    ThreatPublicationIdentityLedgerV1,
    ThreatPublicationIdentityResolutionV1,
    ThreatPublicationIdentityResponseV1,
    ThreatPublicationIdentityResultLabel,
    candidate_set_digest_for_set,
    derive_created_node_id,
    normalize_exact_collision_text,
    resolution_request_digest,
    source_name_from_snapshot,
    validate_resolution_id,
)
from apps.live_control_server.services.world_graph_projection import (
    WorldGraphProjectionServiceError,
    project_world_graph,
)
from graph_memory.projection.world_projection import (
    PROJECTION_REQUEST_SCHEMA,
    WorldGraphProjection,
    WorldGraphProjectionAttributeView,
    WorldGraphProjectionNodeView,
    WorldGraphProjectionRelationshipView,
    WorldGraphProjectionRequest,
    WorldGraphProjectionSnapshot,
    WorldGraphProjectionSummary,
    WorldGraphProjectionTrustBoundary,
    rank_search_node_matches,
)
from graph_memory.union_supergraph.statblock_binding import ThreatStatblockBindingV1
from src.live_play.live_store import load_json, write_json

DEFAULT_IDENTITY_REL = "out/threat_publication_identity"
LEDGER_NAME = "ledger.json"
LOCK_NAME = ".identity.lock"


@dataclass(frozen=True)
class IdentityResolutionOutcome:
    response: ThreatPublicationIdentityResponseV1
    created: bool = False


class ThreatPublicationIdentityStorageError(Exception):
    def __init__(self, message: str, *, kind: Literal["unavailable", "integrity"]) -> None:
        super().__init__(message)
        self.kind = kind


_DECISION_LABELS: dict[str, ThreatPublicationIdentityResultLabel] = {
    "create_new": "publication_identity_created_new",
    "connect_existing": "publication_identity_connected_existing",
    "refuse": "publication_identity_refused",
}

_PREDECESSOR_LABEL_MAP: dict[
    ThreatPublicationResultLabel, ThreatPublicationIdentityResultLabel
] = {
    "publication_not_found": "publication_identity_not_found",
    "publication_storage_unavailable": "publication_identity_storage_unavailable",
    "publication_draft_unavailable": "publication_identity_storage_unavailable",
    "publication_integrity_failure": "publication_identity_integrity_failure",
    "publication_graph_unavailable": "publication_identity_graph_unavailable",
}


def _identity_label_from_predecessor(
    predecessor_label: ThreatPublicationResultLabel,
) -> ThreatPublicationIdentityResultLabel:
    mapped = _PREDECESSOR_LABEL_MAP.get(predecessor_label)
    if mapped is not None:
        return mapped
    return "publication_identity_operation_not_ready"


def _outcome_from_predecessor_failure(
    draft_id: str,
    operation_id: str,
    predecessor: PublicationOperationOutcome,
) -> IdentityResolutionOutcome:
    label = _identity_label_from_predecessor(predecessor.response.result_label)
    op = predecessor.response.operation
    predecessor_usable: bool | None = None
    if op is not None and op.state in ("stale", "cancelled", "superseded"):
        predecessor_usable = False
    return IdentityResolutionOutcome(
        _response(
            draft_id,
            operation_id,
            label,
            predecessor_state=op.state if op is not None else None,
            predecessor_usable=predecessor_usable,
            message=predecessor.response.message or predecessor.response.result_label,
        ),
        created=False,
    )


def _utc_now_iso() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def identity_root(repo_root: Path) -> Path:
    return repo_root / DEFAULT_IDENTITY_REL


def _storage_unavailable() -> ThreatPublicationIdentityStorageError:
    return ThreatPublicationIdentityStorageError(
        "identity ledger storage unavailable", kind="unavailable"
    )


def _integrity_failure(message: str) -> ThreatPublicationIdentityStorageError:
    return ThreatPublicationIdentityStorageError(message, kind="integrity")


def _operation_directory(root: Path, draft_id: str, operation_id: str) -> Path:
    safe_draft = require_draft_id(draft_id)
    safe_op = validate_publication_operation_id(operation_id)
    store_root = identity_root(root).resolve()
    directory = (store_root / safe_draft / safe_op).resolve()
    expected_parent = (store_root / safe_draft).resolve()
    if directory.parent != expected_parent or not str(directory).startswith(str(store_root)):
        raise _integrity_failure("identity path escape")
    return directory


def _ledger_path(root: Path, draft_id: str, operation_id: str) -> Path:
    return _operation_directory(root, draft_id, operation_id) / LEDGER_NAME


@contextmanager
def _identity_lock(root: Path, draft_id: str, operation_id: str) -> Iterator[None]:
    directory = _operation_directory(root, draft_id, operation_id)
    try:
        directory.mkdir(parents=True, exist_ok=True)
        lock_path = directory / LOCK_NAME
        lock_file = open(lock_path, "a+", encoding="utf-8")
    except OSError:
        raise _storage_unavailable() from None
    try:
        try:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
        except OSError:
            raise _storage_unavailable() from None
        try:
            yield
        finally:
            try:
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
            except OSError:
                pass
    finally:
        lock_file.close()


def _empty_ledger(
    draft_id: str,
    operation_id: str,
    *,
    source_digest: str,
    expected_parent_revision_id: str,
) -> ThreatPublicationIdentityLedgerV1:
    return ThreatPublicationIdentityLedgerV1(
        draft_id=draft_id,
        operation_id=operation_id,
        source_digest=source_digest,
        expected_parent_revision_id=expected_parent_revision_id,
        active_resolution_id=None,
        resolutions=[],
    )


def _load_ledger_unlocked(
    root: Path, draft_id: str, operation_id: str
) -> ThreatPublicationIdentityLedgerV1 | None:
    path = _ledger_path(root, draft_id, operation_id)
    if not path.is_file():
        return None
    try:
        payload = load_json(path)
    except OSError:
        raise _storage_unavailable() from None
    except Exception:
        raise _integrity_failure("corrupt identity ledger") from None
    if not isinstance(payload, dict):
        raise _integrity_failure("corrupt identity ledger")
    if payload.get("schema") != LEDGER_SCHEMA:
        raise _integrity_failure("corrupt identity ledger")
    try:
        ledger = ThreatPublicationIdentityLedgerV1.model_validate(payload)
    except Exception:
        raise _integrity_failure("corrupt identity ledger") from None
    if ledger.draft_id != require_draft_id(draft_id):
        raise _integrity_failure("identity ledger identity mismatch")
    if ledger.operation_id != validate_publication_operation_id(operation_id):
        raise _integrity_failure("identity ledger identity mismatch")
    return ledger


def _save_ledger_unlocked(root: Path, ledger: ThreatPublicationIdentityLedgerV1) -> None:
    path = _ledger_path(root, ledger.draft_id, ledger.operation_id)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        write_json(path, ledger.model_dump(mode="json", by_alias=True))
    except OSError:
        raise _storage_unavailable() from None


def _revalidate_ledger(ledger: ThreatPublicationIdentityLedgerV1) -> ThreatPublicationIdentityLedgerV1:
    return ThreatPublicationIdentityLedgerV1.model_validate(
        ledger.model_dump(mode="json", by_alias=True)
    )


def _response(
    draft_id: str,
    operation_id: str,
    result_label: ThreatPublicationIdentityResultLabel,
    *,
    candidate_set: ThreatIdentityCandidateSetV1 | None = None,
    resolution: ThreatPublicationIdentityResolutionV1 | None = None,
    predecessor_state: OperationState | None = None,
    predecessor_usable: bool | None = None,
    message: str | None = None,
) -> ThreatPublicationIdentityResponseV1:
    return ThreatPublicationIdentityResponseV1(
        draft_id=draft_id,
        operation_id=operation_id,
        result_label=result_label,
        candidate_set=candidate_set,
        resolution=resolution,
        predecessor_state=predecessor_state,
        predecessor_usable=predecessor_usable,
        message=message,
    )


def _outcome_from_storage_error(
    draft_id: str, operation_id: str, exc: ThreatPublicationIdentityStorageError
) -> IdentityResolutionOutcome:
    label: ThreatPublicationIdentityResultLabel = (
        "publication_identity_integrity_failure"
        if exc.kind == "integrity"
        else "publication_identity_storage_unavailable"
    )
    return IdentityResolutionOutcome(
        _response(draft_id, operation_id, label, message=str(exc)), created=False
    )


def _binding_matches_accepted_ref(
    binding: ThreatStatblockBindingV1, accepted: AcceptedMechanicsRefV1
) -> bool:
    locator = accepted.to_mechanics_locator()
    return (
        binding.provider == locator.provider
        and binding.statblock_id == locator.statblock_id
        and binding.revision_id == locator.revision_id
        and binding.contract == locator.contract
        and binding.contract_version == locator.contract_version
        and binding.definition_digest == locator.definition_digest
    )


def _bindings_for_node(
    node_id: str,
    relationships: list[WorldGraphProjectionRelationshipView],
    accepted_ref: AcceptedMechanicsRefV1,
) -> tuple[list[str], bool]:
    binding_ids: list[str] = []
    has_exact = False
    for rel in relationships:
        binding = rel.threat_statblock_binding
        if binding is None:
            continue
        if rel.source_node_id != node_id and rel.target_node_id != node_id:
            continue
        binding_ids.append(binding.binding_id)
        if _binding_matches_accepted_ref(binding, accepted_ref):
            has_exact = True
    return sorted(set(binding_ids)), has_exact


def _is_exact_name_collision(source_name: str, node: WorldGraphProjectionNodeView) -> bool:
    normalized_source = normalize_exact_collision_text(source_name)
    labels = [node.label, *node.aliases]
    return any(normalize_exact_collision_text(label) == normalized_source for label in labels)


def _threat_nodes(projection: WorldGraphProjection) -> list[WorldGraphProjectionNodeView]:
    return [node for node in projection.nodes if node.kind.casefold() == "threat"]


def _candidate_from_node(
    node: WorldGraphProjectionNodeView,
    *,
    relationships: list[WorldGraphProjectionRelationshipView],
    accepted_ref: AcceptedMechanicsRefV1,
    match_score: int,
    match_reasons: list[str],
    exact_name_collision: bool,
) -> ThreatIdentityCandidateV1:
    binding_ids, has_exact_binding = _bindings_for_node(
        node.node_id, relationships, accepted_ref
    )
    return ThreatIdentityCandidateV1(
        node_id=node.node_id,
        label=node.label,
        kind=node.kind,
        role=node.role,
        aliases=sorted(node.aliases),
        campaign_scope=node.campaign_scope,
        summary=node.summary,
        source_domains=sorted(node.source_domains),
        binding_ids=binding_ids,
        has_exact_accepted_binding=has_exact_binding,
        match_score=match_score,
        match_reasons=sorted(match_reasons),
        exact_name_collision=exact_name_collision,
    )


def _has_identity_surface_match(match_reasons: list[str]) -> bool:
    """True when a candidate matched on node identity surfaces (id/label/alias).

    Attribute-/kind-/summary-only hits are too loose for connect-or-create:
    place tokens in a draft name (e.g. "Mireward Latchling") otherwise surface
    unrelated Mireward-linked threats as false positives.
    """
    for reason in match_reasons:
        if reason in {
            "exact_node_id",
            "exact_label",
            "exact_alias",
            "label_phrase",
            "alias_phrase",
        }:
            return True
        if reason.startswith("token:") and (
            reason.endswith(":node_id")
            or reason.endswith(":label")
            or reason.endswith(":alias")
        ):
            return True
    return False


def _compose_candidate_set(
    *,
    draft_id: str,
    operation_id: str,
    source_digest: str,
    expected_parent_revision_id: str,
    source_name: str,
    candidate_query: str,
    projection: WorldGraphProjection,
    accepted_ref: AcceptedMechanicsRefV1,
) -> tuple[ThreatIdentityCandidateSetV1 | None, ThreatPublicationIdentityResultLabel | None, str | None]:
    threats = _threat_nodes(projection)
    eligible_count = len(threats)
    collision_nodes = [
        node for node in threats if _is_exact_name_collision(source_name, node)
    ]
    exact_collision_count = len(collision_nodes)

    if exact_collision_count > MAX_TOTAL_CANDIDATES:
        return (
            None,
            "publication_identity_candidate_overflow",
            "exact-name collisions exceed the maximum candidate bound",
        )

    ranked, match_reasons = rank_search_node_matches(
        threats, projection.attributes, candidate_query
    )
    ranked_non_collision: list[tuple[WorldGraphProjectionNodeView, int]] = []
    collision_ids = {node.node_id for node in collision_nodes}
    for node, score in ranked:
        if node.node_id in collision_ids:
            continue
        # Drop attribute/context-only advisory hits (place-name leakage).
        if not _has_identity_surface_match(match_reasons.get(node.node_id, [])):
            continue
        ranked_non_collision.append((node, score))

    remaining_slots = MAX_TOTAL_CANDIDATES - exact_collision_count
    advisory_limit = min(SUGGESTED_ADVISORY_CANDIDATES, remaining_slots)
    advisory_non_collision = ranked_non_collision[:advisory_limit]
    truncated = len(ranked_non_collision) > advisory_limit

    score_by_id = {node.node_id: score for node, score in ranked}
    candidates: list[ThreatIdentityCandidateV1] = []
    for node in sorted(collision_nodes, key=lambda item: item.node_id):
        candidates.append(
            _candidate_from_node(
                node,
                relationships=projection.relationships,
                accepted_ref=accepted_ref,
                match_score=score_by_id.get(node.node_id, 0),
                match_reasons=match_reasons.get(node.node_id, []),
                exact_name_collision=True,
            )
        )

    for node, score in advisory_non_collision:
        candidates.append(
            _candidate_from_node(
                node,
                relationships=projection.relationships,
                accepted_ref=accepted_ref,
                match_score=score,
                match_reasons=match_reasons.get(node.node_id, []),
                exact_name_collision=False,
            )
        )
    rebuilt = candidates

    candidate_set_without_digest = ThreatIdentityCandidateSetV1.model_construct(
        schema_name="dmb_threat_identity_candidate_set_v1",
        draft_id=draft_id,
        operation_id=operation_id,
        source_digest=source_digest,
        expected_parent_revision_id=expected_parent_revision_id,
        matching_profile=MATCHING_PROFILE_V1,
        candidate_query=candidate_query,
        eligible_threat_count=eligible_count,
        exact_collision_count=exact_collision_count,
        truncated=truncated,
        candidates=rebuilt,
        candidate_set_digest="sha256:" + "0" * 64,
    )
    digest = candidate_set_digest_for_set(candidate_set_without_digest)
    candidate_set = candidate_set_without_digest.model_copy(update={"candidate_set_digest": digest})
    ThreatIdentityCandidateSetV1.model_validate(candidate_set.model_dump(mode="json", by_alias=True))
    return candidate_set, None, None


def _project_exact_parent(
    operation: ThreatPublicationOperationV1,
    *,
    world_root: Path | None = None,
) -> WorldGraphProjection:
    snapshot = operation.source_snapshot
    request = WorldGraphProjectionRequest(
        schema=PROJECTION_REQUEST_SCHEMA,
        world_id=snapshot.world_id,
        campaign_id=snapshot.campaign_id,
        admissibility="gm",
        revision_pin=operation.expected_parent_revision_id,
        scope_mode="campaign",
    )
    return project_world_graph(request, root=world_root)


def _validate_pinned_projection(
    projection: WorldGraphProjection, expected_parent_revision_id: str
) -> str | None:
    snap = projection.snapshot
    if (
        snap.revision_id != expected_parent_revision_id
        or snap.head_revision_id != expected_parent_revision_id
        or not snap.is_head
    ):
        return "pinned projection is not the exact expected parent head"
    return None


def _exact_revision_contains_node_id(
    operation: ThreatPublicationOperationV1,
    node_id: str,
    *,
    world_root: Path | None,
) -> bool:
    """Check global node-ID occupancy in the immutable expected-parent revision.

    Candidate projection is intentionally campaign-visible and projectable, so it
    is insufficient for the create-new collision boundary. This read uses only
    the public Kernel exact-revision loader and never follows the mutable head.
    """
    graph_root = (world_root if world_root is not None else world_graph_root()).resolve()
    try:
        store = kernel.load_world_graph_revision_with_integrity(
            graph_root,
            operation.source_snapshot.world_id,
            operation.expected_parent_revision_id,
        )
    except kernel.WorldGraphProjectionError as exc:
        if exc.code == "projection_integrity_error":
            raise WorldGraphProjectionServiceError(
                "exact expected-parent World Graph revision failed integrity validation",
                code="projection_integrity_error",
                status_code=500,
            ) from exc
        raise WorldGraphProjectionServiceError(
            "exact expected-parent World Graph revision is unavailable",
            code="projection_revision_unavailable",
            status_code=503,
        ) from exc
    return node_id in store.nodes


def _validate_resolution_against_operation(
    resolution: ThreatPublicationIdentityResolutionV1,
    operation: ThreatPublicationOperationV1,
    *,
    draft_id: str,
) -> str | None:
    if resolution.draft_id != draft_id:
        return "resolution draft_id does not match operation"
    if resolution.operation_id != operation.operation_id:
        return "resolution operation_id does not match operation"
    if resolution.source_digest != operation.source_digest:
        return "resolution source_digest does not match operation"
    if resolution.expected_parent_revision_id != operation.expected_parent_revision_id:
        return "resolution expected_parent_revision_id does not match operation"
    candidate_set = resolution.candidate_set
    if candidate_set.draft_id != draft_id:
        return "candidate_set draft_id does not match operation"
    if candidate_set.operation_id != operation.operation_id:
        return "candidate_set operation_id does not match operation"
    if candidate_set.source_digest != operation.source_digest:
        return "candidate_set source_digest does not match operation"
    if candidate_set.expected_parent_revision_id != operation.expected_parent_revision_id:
        return "candidate_set expected_parent_revision_id does not match operation"
    if resolution.decision == "create_new":
        if resolution.created_node_id is None:
            return "create_new requires created_node_id"
        expected_id = derive_created_node_id(
            world_id=operation.source_snapshot.world_id,
            campaign_id=operation.source_snapshot.campaign_id,
            draft_id=draft_id,
            operation_id=operation.operation_id,
        )
        if resolution.created_node_id != expected_id:
            return "created_node_id does not match server-derived formula"
    elif resolution.decision == "connect_existing":
        if resolution.selected_target is None:
            return "connect_existing requires selected_target"
        candidate_by_id = {c.node_id: c for c in candidate_set.candidates}
        snapshotted = candidate_by_id.get(resolution.selected_target.node_id)
        if snapshotted is None:
            return "selected_target is not an exact candidate Threat"
        if snapshotted.kind.casefold() != "threat":
            return "selected_target must be a Threat candidate"
        if snapshotted.model_dump(mode="json", by_alias=True) != resolution.selected_target.model_dump(
            mode="json", by_alias=True
        ):
            return "selected_target does not match snapshotted candidate"
    return None


def _resolution_outcome_label(
    resolution: ThreatPublicationIdentityResolutionV1,
    *, superseded: bool = False
) -> ThreatPublicationIdentityResultLabel:
    if superseded:
        return "publication_identity_superseded"
    return _DECISION_LABELS[resolution.decision]


def _find_resolution(
    ledger: ThreatPublicationIdentityLedgerV1, resolution_id: str
) -> ThreatPublicationIdentityResolutionV1 | None:
    for resolution in ledger.resolutions:
        if resolution.resolution_id == resolution_id:
            return resolution
    return None


def _replace_resolution(
    ledger: ThreatPublicationIdentityLedgerV1,
    updated: ThreatPublicationIdentityResolutionV1,
) -> list[ThreatPublicationIdentityResolutionV1]:
    return [
        updated if item.resolution_id == updated.resolution_id else item
        for item in ledger.resolutions
    ]


def prepare_identity_candidates(
    root: Path,
    draft_id: str,
    operation_id: str,
    request: PrepareThreatIdentityCandidatesRequestV1,
    *,
    world_root: Path | None = None,
) -> IdentityResolutionOutcome:
    safe_draft = require_draft_id(draft_id)
    safe_op = validate_publication_operation_id(operation_id)

    refresh = refresh_publication_operation(root, safe_draft, safe_op)
    if refresh.response.result_label != "publication_ready" or refresh.response.operation is None:
        return _outcome_from_predecessor_failure(safe_draft, safe_op, refresh)

    operation = refresh.response.operation
    source_name = source_name_from_snapshot(operation.source_snapshot)
    candidate_query = request.query_text or source_name

    try:
        projection = _project_exact_parent(operation, world_root=world_root)
    except WorldGraphProjectionServiceError as exc:
        return IdentityResolutionOutcome(
            _response(
                safe_draft,
                safe_op,
                "publication_identity_graph_unavailable",
                message=str(exc),
            ),
            created=False,
        )

    projection_error = _validate_pinned_projection(
        projection, operation.expected_parent_revision_id
    )
    if projection_error is not None:
        return IdentityResolutionOutcome(
            _response(
                safe_draft,
                safe_op,
                "publication_identity_graph_unavailable",
                message=projection_error,
            ),
            created=False,
        )

    candidate_set, overflow_label, overflow_message = _compose_candidate_set(
        draft_id=safe_draft,
        operation_id=safe_op,
        source_digest=operation.source_digest,
        expected_parent_revision_id=operation.expected_parent_revision_id,
        source_name=source_name,
        candidate_query=candidate_query,
        projection=projection,
        accepted_ref=operation.source_snapshot.accepted_mechanics_ref,
    )
    if overflow_label is not None:
        return IdentityResolutionOutcome(
            _response(
                safe_draft,
                safe_op,
                overflow_label,
                message=overflow_message,
            ),
            created=False,
        )
    assert candidate_set is not None
    return IdentityResolutionOutcome(
        _response(
            safe_draft,
            safe_op,
            "publication_identity_candidates_ready",
            candidate_set=candidate_set,
            predecessor_state=operation.state,
            predecessor_usable=True,
        ),
        created=False,
    )


def decide_identity_resolution(
    root: Path,
    draft_id: str,
    operation_id: str,
    request: CreateThreatIdentityResolutionRequestV1,
    *,
    world_root: Path | None = None,
) -> IdentityResolutionOutcome:
    safe_draft = require_draft_id(draft_id)
    safe_op = validate_publication_operation_id(operation_id)

    with _identity_lock(root, safe_draft, safe_op):
        try:
            existing_ledger = _load_ledger_unlocked(root, safe_draft, safe_op)
        except ThreatPublicationIdentityStorageError as exc:
            return _outcome_from_storage_error(safe_draft, safe_op, exc)

        if existing_ledger is not None:
            existing_resolution = _find_resolution(existing_ledger, request.resolution_id)
            if existing_resolution is not None:
                incoming_digest = resolution_request_digest(
                    safe_draft,
                    safe_op,
                    request,
                    created_node_id=existing_resolution.created_node_id,
                )
                if incoming_digest == existing_resolution.request_digest:
                    label = _resolution_outcome_label(existing_resolution)
                    return IdentityResolutionOutcome(
                        _response(
                            safe_draft,
                            safe_op,
                            label,
                            resolution=existing_resolution,
                            predecessor_usable=None,
                        ),
                        created=False,
                    )
                return IdentityResolutionOutcome(
                    _response(
                        safe_draft,
                        safe_op,
                        "publication_identity_input_conflict",
                        resolution=existing_resolution,
                        message="resolution_id reused with a changed request",
                    ),
                    created=False,
                )

            if (
                existing_ledger.active_resolution_id is not None
                and request.supersedes_resolution_id is None
            ):
                return IdentityResolutionOutcome(
                    _response(
                        safe_draft,
                        safe_op,
                        "publication_identity_busy",
                        message="active resolution exists; explicit supersession required",
                    ),
                    created=False,
                )
            if request.supersedes_resolution_id is not None:
                if request.supersedes_resolution_id != existing_ledger.active_resolution_id:
                    return IdentityResolutionOutcome(
                        _response(
                            safe_draft,
                            safe_op,
                            "publication_identity_input_conflict",
                            message="supersedes_resolution_id must name the current active resolution",
                        ),
                        created=False,
                    )
        elif request.supersedes_resolution_id is not None:
            return IdentityResolutionOutcome(
                _response(
                    safe_draft,
                    safe_op,
                    "publication_identity_input_conflict",
                    message="supersedes_resolution_id requires an active resolution",
                ),
                created=False,
            )

        refresh = refresh_publication_operation(root, safe_draft, safe_op)
        if refresh.response.result_label != "publication_ready" or refresh.response.operation is None:
            return _outcome_from_predecessor_failure(safe_draft, safe_op, refresh)
        operation = refresh.response.operation

        if existing_ledger is not None:
            if (
                existing_ledger.source_digest != operation.source_digest
                or existing_ledger.expected_parent_revision_id
                != operation.expected_parent_revision_id
            ):
                return IdentityResolutionOutcome(
                    _response(
                        safe_draft,
                        safe_op,
                        "publication_identity_integrity_failure",
                        message="identity ledger predecessor identity mismatch",
                    ),
                    created=False,
                )
            for resolution in existing_ledger.resolutions:
                validation_error = _validate_resolution_against_operation(
                    resolution, operation, draft_id=safe_draft
                )
                if validation_error is not None:
                    return IdentityResolutionOutcome(
                        _response(
                            safe_draft,
                            safe_op,
                            "publication_identity_integrity_failure",
                            message=validation_error,
                        ),
                        created=False,
                    )
            ledger = existing_ledger
        else:
            ledger = _empty_ledger(
                safe_draft,
                safe_op,
                source_digest=operation.source_digest,
                expected_parent_revision_id=operation.expected_parent_revision_id,
            )

        if len(ledger.resolutions) >= MAX_RESOLUTIONS_PER_OPERATION:
            return IdentityResolutionOutcome(
                _response(
                    safe_draft,
                    safe_op,
                    "publication_identity_history_full",
                    message="identity resolution history bound reached",
                ),
                created=False,
            )

        source_name = source_name_from_snapshot(operation.source_snapshot)
        if request.candidate_query != (request.candidate_query.strip()):
            return IdentityResolutionOutcome(
                _response(
                    safe_draft,
                    safe_op,
                    "publication_identity_input_conflict",
                    message="candidate_query must be trimmed",
                ),
                created=False,
            )
        candidate_query = request.candidate_query

        try:
            projection = _project_exact_parent(operation, world_root=world_root)
        except WorldGraphProjectionServiceError as exc:
            return IdentityResolutionOutcome(
                _response(
                    safe_draft,
                    safe_op,
                    "publication_identity_graph_unavailable",
                    message=str(exc),
                ),
                created=False,
            )

        projection_error = _validate_pinned_projection(
            projection, operation.expected_parent_revision_id
        )
        if projection_error is not None:
            return IdentityResolutionOutcome(
                _response(
                    safe_draft,
                    safe_op,
                    "publication_identity_graph_unavailable",
                    message=projection_error,
                ),
                created=False,
            )

        candidate_set, overflow_label, overflow_message = _compose_candidate_set(
            draft_id=safe_draft,
            operation_id=safe_op,
            source_digest=operation.source_digest,
            expected_parent_revision_id=operation.expected_parent_revision_id,
            source_name=source_name,
            candidate_query=candidate_query,
            projection=projection,
            accepted_ref=operation.source_snapshot.accepted_mechanics_ref,
        )
        if overflow_label is not None:
            return IdentityResolutionOutcome(
                _response(
                    safe_draft,
                    safe_op,
                    overflow_label,
                    message=overflow_message,
                ),
                created=False,
            )
        assert candidate_set is not None

        if candidate_set.candidate_set_digest != request.candidate_set_digest:
            return IdentityResolutionOutcome(
                _response(
                    safe_draft,
                    safe_op,
                    "publication_identity_candidate_set_changed",
                    message="candidate_set_digest does not match the recomputed candidate set",
                ),
                created=False,
            )

        candidate_by_id = {c.node_id: c for c in candidate_set.candidates}
        rejected = list(dict.fromkeys(request.rejected_candidate_node_ids))
        if len(rejected) != len(request.rejected_candidate_node_ids):
            return IdentityResolutionOutcome(
                _response(
                    safe_draft,
                    safe_op,
                    "publication_identity_input_conflict",
                    message="rejected_candidate_node_ids must be unique",
                ),
                created=False,
            )
        if not set(rejected).issubset(candidate_by_id):
            return IdentityResolutionOutcome(
                _response(
                    safe_draft,
                    safe_op,
                    "publication_identity_input_conflict",
                    message="rejected_candidate_node_ids must be members of the candidate set",
                ),
                created=False,
            )

        exact_collision_ids = [
            c.node_id for c in candidate_set.candidates if c.exact_name_collision
        ]
        selected_target: ThreatIdentityCandidateV1 | None = None
        created_node_id: str | None = None

        if request.decision == "create_new":
            if request.target_node_id is not None:
                return IdentityResolutionOutcome(
                    _response(
                        safe_draft,
                        safe_op,
                        "publication_identity_input_conflict",
                        message="create_new must not include target_node_id",
                    ),
                    created=False,
                )
            missing_rejections = [
                node_id for node_id in exact_collision_ids if node_id not in rejected
            ]
            if missing_rejections:
                return IdentityResolutionOutcome(
                    _response(
                        safe_draft,
                        safe_op,
                        "publication_identity_review_required",
                        message="every exact-name collision must be explicitly rejected",
                    ),
                    created=False,
                )
            created_node_id = derive_created_node_id(
                world_id=operation.source_snapshot.world_id,
                campaign_id=operation.source_snapshot.campaign_id,
                draft_id=safe_draft,
                operation_id=safe_op,
            )
            try:
                occupied = _exact_revision_contains_node_id(
                    operation,
                    created_node_id,
                    world_root=world_root,
                )
            except WorldGraphProjectionServiceError as exc:
                label: ThreatPublicationIdentityResultLabel = (
                    "publication_identity_integrity_failure"
                    if exc.code == "projection_integrity_error"
                    else "publication_identity_graph_unavailable"
                )
                return IdentityResolutionOutcome(
                    _response(
                        safe_draft,
                        safe_op,
                        label,
                        message=str(exc),
                    ),
                    created=False,
                )
            if occupied:
                return IdentityResolutionOutcome(
                    _response(
                        safe_draft,
                        safe_op,
                        "publication_identity_new_id_collision",
                        message="derived proposed Threat ID already exists at the exact parent",
                    ),
                    created=False,
                )
        elif request.decision == "connect_existing":
            if request.target_node_id is None:
                return IdentityResolutionOutcome(
                    _response(
                        safe_draft,
                        safe_op,
                        "publication_identity_input_conflict",
                        message="connect_existing requires target_node_id",
                    ),
                    created=False,
                )
            if request.target_node_id in rejected:
                return IdentityResolutionOutcome(
                    _response(
                        safe_draft,
                        safe_op,
                        "publication_identity_target_invalid",
                        message="connect target cannot be rejected",
                    ),
                    created=False,
                )
            selected = candidate_by_id.get(request.target_node_id)
            if selected is None:
                return IdentityResolutionOutcome(
                    _response(
                        safe_draft,
                        safe_op,
                        "publication_identity_target_not_found",
                        message="target_node_id is not a reviewed candidate",
                    ),
                    created=False,
                )
            if selected.kind.casefold() != "threat":
                return IdentityResolutionOutcome(
                    _response(
                        safe_draft,
                        safe_op,
                        "publication_identity_target_invalid",
                        message="connect target must be a Threat candidate",
                    ),
                    created=False,
                )
            selected_target = selected
        elif request.decision == "refuse":
            if request.target_node_id is not None:
                return IdentityResolutionOutcome(
                    _response(
                        safe_draft,
                        safe_op,
                        "publication_identity_input_conflict",
                        message="refuse must not include target_node_id",
                    ),
                    created=False,
                )

        now = _utc_now_iso()
        superseded_predecessor: ThreatPublicationIdentityResolutionV1 | None = None
        if request.supersedes_resolution_id is not None:
            superseded_predecessor = _find_resolution(ledger, request.supersedes_resolution_id)
            if superseded_predecessor is None or superseded_predecessor.state != "active":
                return IdentityResolutionOutcome(
                    _response(
                        safe_draft,
                        safe_op,
                        "publication_identity_input_conflict",
                        message="supersedes_resolution_id must name the current active resolution",
                    ),
                    created=False,
                )

        computed_digest = resolution_request_digest(
            safe_draft,
            safe_op,
            request,
            created_node_id=created_node_id,
        )
        new_resolution_unvalidated = ThreatPublicationIdentityResolutionV1.model_construct(
            resolution_id=request.resolution_id,
            draft_id=safe_draft,
            operation_id=safe_op,
            source_digest=operation.source_digest,
            expected_parent_revision_id=operation.expected_parent_revision_id,
            matching_profile=MATCHING_PROFILE_V1,
            candidate_query=candidate_query,
            candidate_set=candidate_set,
            candidate_set_digest=candidate_set.candidate_set_digest,
            request_digest=computed_digest,
            decision=request.decision,
            selected_target=selected_target,
            created_node_id=created_node_id,
            rejected_candidate_node_ids=rejected,
            actor=request.actor,
            reason=request.reason,
            state="active",
            supersedes_resolution_id=request.supersedes_resolution_id,
            superseded_by_resolution_id=None,
            created_at=now,
            updated_at=now,
        )
        new_resolution = ThreatPublicationIdentityResolutionV1.model_validate(
            new_resolution_unvalidated.model_dump(mode="json", by_alias=True)
        )

        resolutions = list(ledger.resolutions)
        if superseded_predecessor is not None:
            updated_predecessor = ThreatPublicationIdentityResolutionV1.model_validate(
                superseded_predecessor.model_copy(
                    update={
                        "state": "superseded",
                        "superseded_by_resolution_id": new_resolution.resolution_id,
                        "updated_at": now,
                    }
                ).model_dump(mode="json", by_alias=True)
            )
            resolutions = _replace_resolution(ledger, updated_predecessor)
            resolutions.append(new_resolution)
            result_label: ThreatPublicationIdentityResultLabel = "publication_identity_superseded"
        else:
            resolutions.append(new_resolution)
            result_label = _resolution_outcome_label(new_resolution)

        new_ledger = _revalidate_ledger(
            ledger.model_copy(
                update={
                    "active_resolution_id": new_resolution.resolution_id,
                    "resolutions": resolutions,
                }
            )
        )
        try:
            _save_ledger_unlocked(root, new_ledger)
        except ThreatPublicationIdentityStorageError as exc:
            return _outcome_from_storage_error(safe_draft, safe_op, exc)

        return IdentityResolutionOutcome(
            _response(
                safe_draft,
                safe_op,
                result_label,
                resolution=new_resolution,
                predecessor_state=operation.state,
                predecessor_usable=True,
            ),
            created=True,
        )


def read_identity_resolution(
    root: Path, draft_id: str, operation_id: str, resolution_id: str
) -> IdentityResolutionOutcome:
    safe_draft = require_draft_id(draft_id)
    safe_op = validate_publication_operation_id(operation_id)
    safe_resolution = validate_resolution_id(resolution_id)

    with _identity_lock(root, safe_draft, safe_op):
        try:
            ledger = _load_ledger_unlocked(root, safe_draft, safe_op)
        except ThreatPublicationIdentityStorageError as exc:
            return _outcome_from_storage_error(safe_draft, safe_op, exc)

        if ledger is None:
            return IdentityResolutionOutcome(
                _response(
                    safe_draft,
                    safe_op,
                    "publication_identity_not_found",
                    message="identity ledger not found",
                ),
                created=False,
            )

        resolution = _find_resolution(ledger, safe_resolution)
        if resolution is None:
            return IdentityResolutionOutcome(
                _response(
                    safe_draft,
                    safe_op,
                    "publication_identity_not_found",
                    message="identity resolution not found",
                ),
                created=False,
            )

        predecessor = read_publication_operation(root, safe_draft, safe_op)
        predecessor_op = predecessor.response.operation
        if predecessor_op is None:
            outcome = _outcome_from_predecessor_failure(safe_draft, safe_op, predecessor)
            return IdentityResolutionOutcome(
                outcome.response.model_copy(update={"predecessor_usable": None}),
                created=False,
            )

        if (
            predecessor_op.source_digest != resolution.source_digest
            or predecessor_op.expected_parent_revision_id
            != resolution.expected_parent_revision_id
        ):
            return IdentityResolutionOutcome(
                _response(
                    safe_draft,
                    safe_op,
                    "publication_identity_integrity_failure",
                    message="predecessor identity mismatch with persisted resolution",
                ),
                created=False,
            )

        validation_error = _validate_resolution_against_operation(
            resolution, predecessor_op, draft_id=safe_draft
        )
        if validation_error is not None:
            return IdentityResolutionOutcome(
                _response(
                    safe_draft,
                    safe_op,
                    "publication_identity_integrity_failure",
                    message=validation_error,
                ),
                created=False,
            )

        predecessor_state = predecessor_op.state
        label = _resolution_outcome_label(
            resolution, superseded=resolution.state == "superseded"
        )
        return IdentityResolutionOutcome(
            _response(
                safe_draft,
                safe_op,
                label,
                resolution=resolution,
                predecessor_state=predecessor_state,
                predecessor_usable=None,
            ),
            created=False,
        )


def build_projection_fixture(
    *,
    revision_id: str,
    world_id: str = "world_1",
    campaign_id: str = "campaign_1",
    nodes: list[WorldGraphProjectionNodeView] | None = None,
    relationships: list[WorldGraphProjectionRelationshipView] | None = None,
    attributes: list[WorldGraphProjectionAttributeView] | None = None,
) -> WorldGraphProjection:
    """Test helper: minimal typed projection pinned to one revision head."""
    node_list = list(nodes or [])
    rel_list = list(relationships or [])
    attr_list = list(attributes or [])
    return WorldGraphProjection(
        schema="dmb_world_graph_projection_v1",
        snapshot=WorldGraphProjectionSnapshot(
            world_id=world_id,
            campaign_id=campaign_id,
            revision_id=revision_id,
            head_revision_id=revision_id,
            is_head=True,
            focus={"kind": "none"},
            admissibility="gm",
            scope_mode="campaign",
        ),
        summary=WorldGraphProjectionSummary(
            node_count=len(node_list),
            relationship_count=len(rel_list),
            attribute_count=len(attr_list),
            evidence_count=0,
            source_artifact_count=0,
        ),
        nodes=node_list,
        relationships=rel_list,
        attributes=attr_list,
        evidence=[],
        source_artifacts=[],
        trust_boundary=WorldGraphProjectionTrustBoundary(),
        diagnostics=[],
        query_context=None,
    )
