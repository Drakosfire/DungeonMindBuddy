"""Revision-bound dual-sense relationship decomposition package v1.

Diagnostic / materialization-plan only. Projected aspects are package values,
not Buddy graph identities. This module does not mutate World Graph nodes,
edges, kinds, or source authority, and it does not feed the package into
whole-world classification.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from dataclasses import field as dataclass_field
from hashlib import sha256
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from apps.live_control_server.integrations.dungeonmind_kernel.whole_world_conformance import (
    _predicate_allowed_endpoints,
)
from apps.live_control_server.integrations.dungeonmind_kernel.whole_world_conformance_v4 import (
    WholeWorldTargetContract,
    resolve_buddy_predicate_mapping_v4,
)


DECOMPOSITION_SCHEMA = "dmb_relationship_dual_sense_decomposition_v1"
PACKAGE_ID = "relationship-dual-sense-decomposition-v1"
AssignedEndpoint = Literal["source", "target"]
_BINDING_TOKEN = object()
_PREDECESSOR_TOKEN = object()

# Package-defined semantic roles for predecessor candidate kinds.
# This is not an edge/node allowlist.
_ASPECT_KEY_BY_CANDIDATE_KIND: Mapping[str, str] = {
    "faction": "organization",
    "location": "site",
    "event": "event",
}


class RelationshipDualSenseDecompositionError(RuntimeError):
    """Fail-closed dual-sense decomposition error."""

    def __init__(self, message: str, *, code: str) -> None:
        super().__init__(message)
        self.code = code


def _fail(message: str, code: str) -> RelationshipDualSenseDecompositionError:
    return RelationshipDualSenseDecompositionError(message, code=code)


def _jsonable(value: Any) -> Any:
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json", by_alias=True)
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if hasattr(value, "__dict__"):
        return {
            key: _jsonable(item)
            for key, item in vars(value).items()
            if not str(key).startswith("_")
        }
    return str(value)


def _canonical_json(payload: Any) -> str:
    return json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def store_semantic_sha256(store: Any) -> str:
    """Digest an in-memory store after an integrity-attested revision load.

    This is not the on-disk graph payload hash.
    """
    encoded = _canonical_json({"store": _jsonable(store)})
    return sha256(encoded.encode("utf-8")).hexdigest()


def sha256_bytes(raw: bytes) -> str:
    return sha256(raw).hexdigest()


@dataclass(frozen=True, slots=True)
class DecompositionRevisionBinding:
    """Integrity-attested world/revision/payload binding for one loaded store."""

    world_id: str
    canonical_revision_id: str
    canonical_graph_payload_sha256: str
    store_semantic_sha256: str
    _token: object = dataclass_field(repr=False, compare=False)

    def __post_init__(self) -> None:
        if self._token is not _BINDING_TOKEN:
            raise TypeError(
                "DecompositionRevisionBinding is not a public constructor; "
                "use decomposition_binding_from_attested_revision"
            )


def decomposition_binding_from_attested_revision(
    *,
    root: Path,
    world_id: str,
    revision_id: str,
    expected_world_id: str,
    expected_revision_id: str,
    expected_graph_payload_sha256: str,
    store: Any,
) -> DecompositionRevisionBinding:
    """Mint package pins only from an integrity-verified revision load."""
    from apps.live_control_server.integrations.dungeonmind_kernel.whole_world_conformance import (
        WholeWorldConformanceError,
        _load_exact_buddy_revision,
    )

    if not isinstance(root, Path):
        raise _fail(
            "decomposition binding requires a world-graph root for integrity load",
            "decomposition_binding_unattested",
        )
    if not world_id or not revision_id:
        raise _fail(
            "decomposition binding requires an integrity-loaded world/revision",
            "decomposition_binding_unattested",
        )
    if not expected_world_id or not expected_revision_id or not expected_graph_payload_sha256:
        raise _fail(
            "decomposition binding expected pins must be nonblank",
            "decomposition_binding_unattested",
        )
    try:
        manifest, loaded_store = _load_exact_buddy_revision(
            root=root,
            world_id=world_id,
            revision_id=revision_id,
        )
    except WholeWorldConformanceError as exc:
        raise _fail(
            f"decomposition binding requires an integrity-attested revision: {exc}",
            "decomposition_binding_unattested",
        ) from exc

    attested_world = str(getattr(manifest, "world_id", "") or "")
    attested_revision = str(getattr(manifest, "revision_id", "") or "")
    attested_payload = str(getattr(manifest, "graph_payload_sha256", "") or "")
    if not attested_world or not attested_revision or not attested_payload:
        raise _fail(
            "decomposition binding requires attested world/revision/payload pins",
            "decomposition_binding_unattested",
        )
    if attested_world != world_id or attested_revision != revision_id:
        raise _fail(
            "integrity-loaded revision does not match requested world/revision",
            "decomposition_binding_pin_mismatch",
        )
    if (
        attested_world != expected_world_id
        or attested_revision != expected_revision_id
        or attested_payload != expected_graph_payload_sha256
    ):
        raise _fail(
            "decomposition expected pins do not match integrity-attested revision",
            "decomposition_binding_pin_mismatch",
        )
    loaded_digest = store_semantic_sha256(loaded_store)
    if store_semantic_sha256(store) != loaded_digest:
        raise _fail(
            "decomposition store does not belong to the integrity-attested revision",
            "decomposition_store_revision_mismatch",
        )
    return DecompositionRevisionBinding(
        world_id=attested_world,
        canonical_revision_id=attested_revision,
        canonical_graph_payload_sha256=attested_payload,
        store_semantic_sha256=loaded_digest,
        _token=_BINDING_TOKEN,
    )


@dataclass(frozen=True, slots=True)
class DualSenseStopRow:
    node_id: str
    stored_buddy_kind: str
    candidate_kind: str
    deferred_edge_ids: tuple[str, ...]
    retained_edge_ids: tuple[str, ...]
    kind_only_insufficient: bool
    stop_note: str
    source_rationales: Mapping[str, str]


@dataclass(frozen=True, slots=True)
class VerifiedPredecessorAuthority:
    """STOP rows minted only from the sealed predecessor repair loader."""

    manifest_sha256: str
    schema: str
    repair_id: str
    world_id: str
    remaining_residual_edge_ids: tuple[str, ...]
    stops: tuple[DualSenseStopRow, ...]
    _token: object = dataclass_field(repr=False, compare=False)

    def __post_init__(self) -> None:
        if self._token is not _PREDECESSOR_TOKEN:
            raise TypeError(
                "VerifiedPredecessorAuthority is not a public constructor; "
                "use predecessor_authority_from_sealed_repair"
            )


def predecessor_authority_from_locked_bytes(
    raw: bytes,
    *,
    expected_sha256: str,
) -> VerifiedPredecessorAuthority:
    """Refuse caller-minted STOP authority.

    Pairing proposed bytes with a digest computed from those same bytes is not
    a trust boundary. Use predecessor_authority_from_sealed_repair.
    """
    del raw, expected_sha256
    raise _fail(
        "VerifiedPredecessorAuthority cannot be minted from caller-supplied "
        "bytes and digest; use predecessor_authority_from_sealed_repair",
        "predecessor_authority_unattested",
    )


def _predecessor_from_verified_payload(
    payload: dict[str, Any],
    *,
    digest: str,
) -> VerifiedPredecessorAuthority:
    schema = str(payload.get("schema") or "")
    repair_id = str(payload.get("repair_id") or "")
    world_id = str(payload.get("world_id") or "")
    if not schema or not repair_id or not world_id:
        raise _fail("predecessor repair identity fields missing", "predecessor_invalid")
    remaining = payload.get("expected_remaining_residual_edge_ids")
    stops_raw = payload.get("deferred_dual_sense_stops")
    if not isinstance(remaining, list) or not remaining:
        raise _fail("predecessor remaining residual set missing", "predecessor_invalid")
    if not isinstance(stops_raw, list) or not stops_raw:
        raise _fail("predecessor dual-sense STOP rows missing", "predecessor_invalid")
    remaining_ids = tuple(sorted(str(item) for item in remaining))
    if len(set(remaining_ids)) != len(remaining_ids):
        raise _fail("predecessor remaining residual set has duplicates", "predecessor_invalid")
    stops: list[DualSenseStopRow] = []
    deferred_union: set[str] = set()
    seen_nodes: set[str] = set()
    for row in stops_raw:
        if not isinstance(row, dict):
            raise _fail("predecessor STOP row is not an object", "predecessor_invalid")
        node_id = str(row.get("node_id") or "")
        stored_kind = str(row.get("current_kind") or "")
        if not node_id or not stored_kind:
            raise _fail("predecessor STOP row missing node identity", "predecessor_invalid")
        if node_id in seen_nodes:
            raise _fail(f"duplicate predecessor STOP node {node_id}", "predecessor_invalid")
        seen_nodes.add(node_id)
        deferred = tuple(str(item) for item in (row.get("deferred_edge_ids") or []))
        retained = tuple(str(item) for item in (row.get("retained_effective_edge_ids") or []))
        if not deferred:
            raise _fail(f"predecessor STOP {node_id} has no deferred edges", "predecessor_invalid")
        if set(deferred) & set(retained):
            raise _fail(
                f"predecessor STOP {node_id} overlaps deferred and retained edges",
                "predecessor_invalid",
            )
        overlap = deferred_union.intersection(deferred)
        if overlap:
            raise _fail(
                f"predecessor STOP deferred edges collide: {sorted(overlap)}",
                "predecessor_invalid",
            )
        deferred_union.update(deferred)
        stop_basis = row.get("stop_basis") or {}
        if not isinstance(stop_basis, dict):
            raise _fail(f"predecessor STOP {node_id} stop_basis missing", "predecessor_invalid")
        candidate_kind = str(stop_basis.get("candidate_kind") or "")
        if not candidate_kind:
            raise _fail(f"predecessor STOP {node_id} missing candidate kind", "predecessor_invalid")
        if stop_basis.get("kind_only_insufficient") is not True:
            raise _fail(
                f"predecessor STOP {node_id} is not a kind-only-insufficient dual-sense row",
                "predecessor_invalid",
            )
        rationales_raw = stop_basis.get("source_rationales") or {}
        if not isinstance(rationales_raw, dict):
            raise _fail(f"predecessor STOP {node_id} rationales missing", "predecessor_invalid")
        rationales = {str(key): str(value) for key, value in rationales_raw.items()}
        stops.append(
            DualSenseStopRow(
                node_id=node_id,
                stored_buddy_kind=stored_kind,
                candidate_kind=candidate_kind,
                deferred_edge_ids=deferred,
                retained_edge_ids=retained,
                kind_only_insufficient=True,
                stop_note=str(stop_basis.get("note") or ""),
                source_rationales=rationales,
            )
        )
    if deferred_union != set(remaining_ids):
        raise _fail(
            "predecessor STOP deferred edges != remaining residual set",
            "predecessor_invalid",
        )
    ordered_stops = tuple(sorted(stops, key=lambda item: item.node_id))
    return VerifiedPredecessorAuthority(
        manifest_sha256=digest,
        schema=schema,
        repair_id=repair_id,
        world_id=world_id,
        remaining_residual_edge_ids=remaining_ids,
        stops=ordered_stops,
        _token=_PREDECESSOR_TOKEN,
    )


def predecessor_authority_from_sealed_repair(
    *,
    repo: Path,
) -> VerifiedPredecessorAuthority:
    """Mint STOP authority only by consuming the locked predecessor loader.

    The caller supplies a repository path. The locked digest is owned by
    ``eldyrwild_relationship_node_kind_source_repair``, not by this caller.
    """
    from apps.live_control_server.services.eldyrwild_relationship_node_kind_source_repair import (
        LOCKED_MANIFEST_SHA256,
        RelationshipNodeKindSourceRepairError,
        _load_repair_manifest,
        _manifest_path,
        _sha256_bytes,
    )

    if not isinstance(repo, Path):
        raise _fail(
            "predecessor authority requires the sealed repair repository path",
            "predecessor_authority_unattested",
        )
    try:
        payload = _load_repair_manifest(repo=repo)
    except RelationshipNodeKindSourceRepairError as exc:
        if exc.code == "manifest_tampered":
            mapped = "predecessor_manifest_tampered"
        elif exc.code == "manifest_invalid":
            mapped = "predecessor_invalid"
        else:
            mapped = "predecessor_authority_unattested"
        raise _fail(str(exc), mapped) from exc
    digest = _sha256_bytes(_manifest_path(repo).read_bytes())
    if digest != LOCKED_MANIFEST_SHA256:
        raise _fail(
            "sealed predecessor digest drifted after loader verification",
            "predecessor_manifest_tampered",
        )
    if not isinstance(payload, dict):
        raise _fail("predecessor repair payload must be an object", "predecessor_invalid")
    return _predecessor_from_verified_payload(payload, digest=digest)


class AspectRefV1(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_node_id: str
    aspect_key: str
    projected_dm_kind: str


class DecompositionRowV1(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_node_id: str
    stored_buddy_kind: str
    aspect_key: str
    projected_dm_kind: str
    deferred_edge_ids: list[str]
    retained_edge_ids: list[str]
    predecessor_stop_authority_ref: str
    predecessor_repair_manifest_sha256: str
    kind_only_insufficient: bool
    stop_note: str


class EndpointAssignmentV1(BaseModel):
    model_config = ConfigDict(extra="forbid")

    edge_id: str
    buddy_predicate: str
    source_node_id: str
    target_node_id: str
    assigned_endpoint: AssignedEndpoint
    aspect_ref: AspectRefV1
    predecessor_stop_authority_ref: str
    predecessor_repair_manifest_sha256: str
    rationale: str


class EndpointAdmissionV1(BaseModel):
    model_config = ConfigDict(extra="forbid")

    edge_id: str
    admitted: bool
    dm_predicate: str | None = None
    source_dm_kind: str | None = None
    target_dm_kind: str | None = None
    note: str


class PackageProjectionV1(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_: str = Field(
        default=DECOMPOSITION_SCHEMA + "_package_projection",
        alias="schema",
    )
    passed: bool
    assigned_admissions: list[EndpointAdmissionV1]
    retained_admissions: list[EndpointAdmissionV1]
    retained_regressions: list[str]
    uncovered_current_residual_edge_ids: list[str]
    extra_package_edge_assignments: list[str]
    dungeonmind_target_id: str
    dungeonmind_dependency_ref: str
    world_object_revision_label: str


class DualSenseDecompositionPackageV1(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_: str = Field(default=DECOMPOSITION_SCHEMA, alias="schema")
    package_id: str = PACKAGE_ID
    world_id: str
    canonical_revision_id: str
    canonical_graph_payload_sha256: str
    store_semantic_sha256: str
    dungeonmind_target_id: str
    dungeonmind_dependency_ref: str
    world_object_revision_label: str
    predecessor_repair_id: str
    predecessor_repair_manifest_sha256: str
    decomposition_rows: list[DecompositionRowV1]
    endpoint_assignments: list[EndpointAssignmentV1]
    package_projection: PackageProjectionV1
    canonical_payload_sha256: str = ""


class DualSenseDecompositionProofV1(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_: str = Field(default=DECOMPOSITION_SCHEMA + "_proof", alias="schema")
    passed: bool
    package: DualSenseDecompositionPackageV1
    package_sha256: str
    diagnostics: list[str] = Field(default_factory=list)


def _require_binding_store(store: Any, binding: DecompositionRevisionBinding) -> None:
    if store_semantic_sha256(store) != binding.store_semantic_sha256:
        raise _fail(
            "prove store does not match integrity-attested decomposition binding",
            "decomposition_store_revision_mismatch",
        )


def _edges(store: Any) -> dict[str, Any]:
    raw = getattr(store, "edges", None)
    if isinstance(raw, dict):
        return dict(raw)
    raise _fail("store.edges must be a mapping", "store_shape_invalid")


def _nodes(store: Any) -> Mapping[str, Any]:
    raw = getattr(store, "nodes", None)
    if isinstance(raw, dict):
        return raw
    raise _fail("store.nodes must be a mapping", "store_shape_invalid")


def _node_kind(store: Any, node_id: str) -> str:
    node = _nodes(store).get(node_id)
    if node is None:
        raise _fail(f"missing node {node_id}", "source_node_missing")
    kind = str(getattr(node, "kind", "") or "")
    if not kind:
        raise _fail(f"node {node_id} has empty kind", "stored_kind_missing")
    return kind


def _dm_kind_for(buddy_kind: str, *, target: WholeWorldTargetContract) -> str:
    mapped = target.buddy_to_dm_kind.get(buddy_kind)
    if not mapped:
        raise _fail(
            f"target {target.target_id} has no Buddy→DM kind for {buddy_kind!r}",
            "projected_kind_not_in_target",
        )
    return mapped


def admit_edge_under_dm_kinds(
    edge: Any,
    *,
    source_dm_kind: str,
    target_dm_kind: str,
    target: WholeWorldTargetContract,
) -> EndpointAdmissionV1:
    """Evaluate one edge against explicit pinned target endpoint constraints."""
    predicate = str(getattr(edge, "predicate", "") or "")
    edge_id = str(getattr(edge, "edge_id", "") or "")
    mapping = resolve_buddy_predicate_mapping_v4(predicate)
    if mapping is None:
        return EndpointAdmissionV1(
            edge_id=edge_id,
            admitted=False,
            note=f"predicate {predicate!r} has no explicit DM adapter",
        )
    dm_predicate, reverse_endpoints = mapping
    vocabulary = target.world_object_loader()
    allowed = _predicate_allowed_endpoints(dm_predicate, vocabulary)
    if allowed is None:
        return EndpointAdmissionV1(
            edge_id=edge_id,
            admitted=False,
            dm_predicate=dm_predicate,
            source_dm_kind=source_dm_kind,
            target_dm_kind=target_dm_kind,
            note=(
                f"{target.world_object_revision_label} vocabulary missing "
                f"predicate {dm_predicate}"
            ),
        )
    subject_kinds, object_kinds = allowed
    admit_src, admit_tgt = (
        (target_dm_kind, source_dm_kind) if reverse_endpoints else (source_dm_kind, target_dm_kind)
    )
    admitted = admit_src in subject_kinds and admit_tgt in object_kinds
    note = (
        f"{predicate}→{dm_predicate} endpoint kinds {admit_src}/{admit_tgt} "
        + ("admitted" if admitted else "not admitted")
        + (" [reverse_endpoints]" if reverse_endpoints else "")
    )
    return EndpointAdmissionV1(
        edge_id=edge_id,
        admitted=admitted,
        dm_predicate=dm_predicate,
        source_dm_kind=admit_src,
        target_dm_kind=admit_tgt,
        note=note,
    )


def _assigned_endpoint(edge: Any, source_node_id: str) -> AssignedEndpoint:
    if str(getattr(edge, "source_node_id", "") or "") == source_node_id:
        return "source"
    if str(getattr(edge, "target_node_id", "") or "") == source_node_id:
        return "target"
    raise _fail(
        f"edge {getattr(edge, 'edge_id', '')} does not touch {source_node_id}",
        "assignment_endpoint_missing",
    )


def _aspect_for_stop(
    stop: DualSenseStopRow,
    *,
    target: WholeWorldTargetContract,
) -> tuple[str, str]:
    aspect_key = _ASPECT_KEY_BY_CANDIDATE_KIND.get(stop.candidate_kind)
    if not aspect_key:
        raise _fail(
            f"no package aspect key for candidate kind {stop.candidate_kind!r}",
            "aspect_key_unknown",
        )
    projected = _dm_kind_for(stop.candidate_kind, target=target)
    return aspect_key, projected


def derive_dual_sense_decomposition_package_v1(
    store: Any,
    *,
    binding: DecompositionRevisionBinding,
    predecessor: VerifiedPredecessorAuthority,
    current_residual_edge_ids: set[str] | frozenset[str],
    target: WholeWorldTargetContract,
) -> DualSenseDecompositionPackageV1:
    _require_binding_store(store, binding)
    if predecessor.world_id != binding.world_id:
        raise _fail(
            "predecessor world_id does not match attested revision binding",
            "decomposition_world_mismatch",
        )
    current_ids = tuple(sorted(str(item) for item in current_residual_edge_ids))
    if current_ids != predecessor.remaining_residual_edge_ids:
        raise _fail(
            "current residual set != predecessor remaining dual-sense STOP edges",
            "current_residual_set_mismatch",
        )
    edges = _edges(store)
    rows: list[DecompositionRowV1] = []
    assignments: list[EndpointAssignmentV1] = []
    assigned_ids: list[str] = []
    for stop in predecessor.stops:
        stored_kind = _node_kind(store, stop.node_id)
        if stored_kind != stop.stored_buddy_kind:
            raise _fail(
                f"stored kind for {stop.node_id} is {stored_kind!r}, "
                f"predecessor has {stop.stored_buddy_kind!r}",
                "stored_kind_drift",
            )
        _dm_kind_for(stored_kind, target=target)
        aspect_key, projected = _aspect_for_stop(stop, target=target)
        authority_ref = f"{predecessor.repair_id}:{stop.node_id}"
        rows.append(
            DecompositionRowV1(
                source_node_id=stop.node_id,
                stored_buddy_kind=stored_kind,
                aspect_key=aspect_key,
                projected_dm_kind=projected,
                deferred_edge_ids=list(stop.deferred_edge_ids),
                retained_edge_ids=list(stop.retained_edge_ids),
                predecessor_stop_authority_ref=authority_ref,
                predecessor_repair_manifest_sha256=predecessor.manifest_sha256,
                kind_only_insufficient=True,
                stop_note=stop.stop_note,
            )
        )
        aspect_ref = AspectRefV1(
            source_node_id=stop.node_id,
            aspect_key=aspect_key,
            projected_dm_kind=projected,
        )
        for edge_id in stop.deferred_edge_ids:
            edge = edges.get(edge_id)
            if edge is None:
                raise _fail(f"deferred edge missing from store: {edge_id}", "deferred_edge_missing")
            if str(getattr(edge, "edge_id", "") or "") != edge_id:
                raise _fail(f"store edge id drift for {edge_id}", "edge_shape_drift")
            endpoint = _assigned_endpoint(edge, stop.node_id)
            opposite = (
                str(getattr(edge, "target_node_id", "") or "")
                if endpoint == "source"
                else str(getattr(edge, "source_node_id", "") or "")
            )
            if not opposite:
                raise _fail(f"edge {edge_id} missing opposite endpoint", "edge_shape_drift")
            rationale = stop.source_rationales.get(edge_id) or stop.stop_note
            if not rationale:
                raise _fail(f"missing source rationale for {edge_id}", "assignment_rationale_missing")
            assignments.append(
                EndpointAssignmentV1(
                    edge_id=edge_id,
                    buddy_predicate=str(getattr(edge, "predicate", "") or ""),
                    source_node_id=str(getattr(edge, "source_node_id", "") or ""),
                    target_node_id=str(getattr(edge, "target_node_id", "") or ""),
                    assigned_endpoint=endpoint,
                    aspect_ref=aspect_ref,
                    predecessor_stop_authority_ref=authority_ref,
                    predecessor_repair_manifest_sha256=predecessor.manifest_sha256,
                    rationale=rationale,
                )
            )
            assigned_ids.append(edge_id)
        for retained_id in stop.retained_edge_ids:
            retained = edges.get(retained_id)
            if retained is None:
                raise _fail(
                    f"retained edge missing from store: {retained_id}",
                    "retained_edge_missing",
                )
    if len(assigned_ids) != len(set(assigned_ids)):
        raise _fail("duplicate endpoint assignments", "duplicate_assignment")
    if tuple(sorted(assigned_ids)) != predecessor.remaining_residual_edge_ids:
        raise _fail(
            "derived assignments != exact current residual set",
            "assignment_set_mismatch",
        )
    if len(rows) != len(predecessor.stops):
        raise _fail("decomposition row count drifted from predecessor STOPs", "row_count_mismatch")
    package = DualSenseDecompositionPackageV1(
        world_id=binding.world_id,
        canonical_revision_id=binding.canonical_revision_id,
        canonical_graph_payload_sha256=binding.canonical_graph_payload_sha256,
        store_semantic_sha256=binding.store_semantic_sha256,
        dungeonmind_target_id=target.target_id,
        dungeonmind_dependency_ref=target.dungeonmind_dependency_ref,
        world_object_revision_label=target.world_object_revision_label,
        predecessor_repair_id=predecessor.repair_id,
        predecessor_repair_manifest_sha256=predecessor.manifest_sha256,
        decomposition_rows=rows,
        endpoint_assignments=sorted(assignments, key=lambda item: item.edge_id),
        package_projection=PackageProjectionV1(
            passed=False,
            assigned_admissions=[],
            retained_admissions=[],
            retained_regressions=["pending"],
            uncovered_current_residual_edge_ids=[],
            extra_package_edge_assignments=[],
            dungeonmind_target_id=target.target_id,
            dungeonmind_dependency_ref=target.dungeonmind_dependency_ref,
            world_object_revision_label=target.world_object_revision_label,
        ),
    )
    projection = evaluate_package_projection_v1(
        store,
        package=package,
        binding=binding,
        current_residual_edge_ids=set(current_ids),
        target=target,
    )
    if not projection.passed:
        raise _fail(
            "package projection failed: "
            f"regressions={projection.retained_regressions} "
            f"uncovered={projection.uncovered_current_residual_edge_ids} "
            f"extra={projection.extra_package_edge_assignments}",
            "package_projection_failed",
        )
    return package.model_copy(update={"package_projection": projection})


def evaluate_package_projection_v1(
    store: Any,
    *,
    package: DualSenseDecompositionPackageV1,
    binding: DecompositionRevisionBinding,
    current_residual_edge_ids: set[str],
    target: WholeWorldTargetContract,
) -> PackageProjectionV1:
    """Validate assigned edges under projected aspects and retained stored senses."""
    if (
        binding.world_id != package.world_id
        or binding.canonical_revision_id != package.canonical_revision_id
        or binding.canonical_graph_payload_sha256 != package.canonical_graph_payload_sha256
        or binding.store_semantic_sha256 != package.store_semantic_sha256
    ):
        raise _fail(
            "package projection binding does not match package world/revision/payload/store pins",
            "decomposition_binding_pin_mismatch",
        )
    if store_semantic_sha256(store) != binding.store_semantic_sha256:
        raise _fail(
            "package projection store does not match attested decomposition binding",
            "decomposition_store_revision_mismatch",
        )
    if target.target_id != package.dungeonmind_target_id:
        raise _fail(
            "package projection target_id does not match package binding",
            "decomposition_target_mismatch",
        )
    if target.dungeonmind_dependency_ref != package.dungeonmind_dependency_ref:
        raise _fail(
            "package projection DungeonMind pin does not match package binding",
            "decomposition_target_mismatch",
        )
    if target.world_object_revision_label != package.world_object_revision_label:
        raise _fail(
            "package projection vocabulary revision label does not match package binding",
            "decomposition_target_mismatch",
        )
    edges = _edges(store)
    assignment_ids = [row.edge_id for row in package.endpoint_assignments]
    if len(assignment_ids) != len(set(assignment_ids)):
        raise _fail("package assigns one edge twice", "duplicate_assignment")
    extra = sorted(set(assignment_ids) - set(current_residual_edge_ids))
    uncovered = sorted(set(current_residual_edge_ids) - set(assignment_ids))
    assigned_admissions: list[EndpointAdmissionV1] = []
    for assignment in package.endpoint_assignments:
        edge = edges.get(assignment.edge_id)
        if edge is None:
            raise _fail(
                f"assigned edge missing from store: {assignment.edge_id}",
                "deferred_edge_missing",
            )
        if (
            str(getattr(edge, "predicate", "") or "") != assignment.buddy_predicate
            or str(getattr(edge, "source_node_id", "") or "") != assignment.source_node_id
            or str(getattr(edge, "target_node_id", "") or "") != assignment.target_node_id
        ):
            raise _fail(
                f"assignment {assignment.edge_id} would change Buddy edge shape",
                "edge_shape_mutation",
            )
        source_kind = _node_kind(store, assignment.source_node_id)
        target_kind = _node_kind(store, assignment.target_node_id)
        source_dm = _dm_kind_for(source_kind, target=target)
        target_dm = _dm_kind_for(target_kind, target=target)
        projected = assignment.aspect_ref.projected_dm_kind
        if assignment.assigned_endpoint == "source":
            if assignment.aspect_ref.source_node_id != assignment.source_node_id:
                raise _fail(
                    f"{assignment.edge_id} aspect is not the assigned source endpoint",
                    "aspect_endpoint_mismatch",
                )
            source_dm = projected
        else:
            if assignment.aspect_ref.source_node_id != assignment.target_node_id:
                raise _fail(
                    f"{assignment.edge_id} aspect is not the assigned target endpoint",
                    "aspect_endpoint_mismatch",
                )
            target_dm = projected
        assigned_admissions.append(
            admit_edge_under_dm_kinds(
                edge,
                source_dm_kind=source_dm,
                target_dm_kind=target_dm,
                target=target,
            )
        )
    retained_admissions: list[EndpointAdmissionV1] = []
    retained_regressions: list[str] = []
    seen_retained: set[str] = set()
    for row in package.decomposition_rows:
        stored_dm = _dm_kind_for(row.stored_buddy_kind, target=target)
        for edge_id in row.retained_edge_ids:
            if edge_id in seen_retained:
                raise _fail(f"retained edge assigned twice: {edge_id}", "duplicate_assignment")
            seen_retained.add(edge_id)
            if edge_id in assignment_ids:
                raise _fail(
                    f"retained edge {edge_id} also has an aspect assignment",
                    "retained_edge_assigned",
                )
            edge = edges.get(edge_id)
            if edge is None:
                raise _fail(f"retained edge missing from store: {edge_id}", "retained_edge_missing")
            source_kind = _node_kind(store, str(getattr(edge, "source_node_id", "") or ""))
            target_kind = _node_kind(store, str(getattr(edge, "target_node_id", "") or ""))
            source_dm = _dm_kind_for(source_kind, target=target)
            target_dm = _dm_kind_for(target_kind, target=target)
            if str(getattr(edge, "source_node_id", "") or "") == row.source_node_id:
                source_dm = stored_dm
            if str(getattr(edge, "target_node_id", "") or "") == row.source_node_id:
                target_dm = stored_dm
            admission = admit_edge_under_dm_kinds(
                edge,
                source_dm_kind=source_dm,
                target_dm_kind=target_dm,
                target=target,
            )
            retained_admissions.append(admission)
            if not admission.admitted:
                retained_regressions.append(edge_id)
    assigned_failed = [row.edge_id for row in assigned_admissions if not row.admitted]
    passed = (
        not extra
        and not uncovered
        and not retained_regressions
        and not assigned_failed
        and all(row.admitted for row in assigned_admissions)
    )
    return PackageProjectionV1(
        passed=passed,
        assigned_admissions=sorted(assigned_admissions, key=lambda item: item.edge_id),
        retained_admissions=sorted(retained_admissions, key=lambda item: item.edge_id),
        retained_regressions=sorted(retained_regressions),
        uncovered_current_residual_edge_ids=uncovered,
        extra_package_edge_assignments=extra,
        dungeonmind_target_id=target.target_id,
        dungeonmind_dependency_ref=target.dungeonmind_dependency_ref,
        world_object_revision_label=target.world_object_revision_label,
    )


def evaluate_global_aspect_substitution_v1(
    store: Any,
    *,
    package: DualSenseDecompositionPackageV1,
    source_node_id: str,
    target: WholeWorldTargetContract,
) -> list[str]:
    """Apply one projected aspect to every edge of a source identity.

    Used to prove that a global kind substitution regresses retained senses.
    """
    row = next(
        (item for item in package.decomposition_rows if item.source_node_id == source_node_id),
        None,
    )
    if row is None:
        raise _fail(f"no decomposition row for {source_node_id}", "source_node_missing")
    projected = row.projected_dm_kind
    edges = _edges(store)
    regressions: list[str] = []
    for edge_id in row.retained_edge_ids:
        edge = edges[edge_id]
        source_kind = _node_kind(store, str(getattr(edge, "source_node_id", "") or ""))
        target_kind = _node_kind(store, str(getattr(edge, "target_node_id", "") or ""))
        source_dm = _dm_kind_for(source_kind, target=target)
        target_dm = _dm_kind_for(target_kind, target=target)
        if str(getattr(edge, "source_node_id", "") or "") == source_node_id:
            source_dm = projected
        if str(getattr(edge, "target_node_id", "") or "") == source_node_id:
            target_dm = projected
        admission = admit_edge_under_dm_kinds(
            edge,
            source_dm_kind=source_dm,
            target_dm_kind=target_dm,
            target=target,
        )
        if not admission.admitted:
            regressions.append(edge_id)
    return sorted(regressions)


def package_canonical_bytes(package: DualSenseDecompositionPackageV1) -> bytes:
    payload = package.model_dump(mode="json", by_alias=True)
    payload["canonical_payload_sha256"] = ""
    digest = sha256(_canonical_json(payload).encode("utf-8")).hexdigest()
    payload["canonical_payload_sha256"] = digest
    text = json.dumps(payload, ensure_ascii=False, indent=1, sort_keys=True) + "\n"
    return text.encode("utf-8")


def package_from_canonical_bytes(raw: bytes) -> DualSenseDecompositionPackageV1:
    payload = json.loads(raw.decode("utf-8"))
    package = DualSenseDecompositionPackageV1.model_validate(payload)
    reproduced = package_canonical_bytes(package)
    if reproduced != raw:
        raise _fail("package bytes are not canonical", "package_bytes_not_canonical")
    return DualSenseDecompositionPackageV1.model_validate(json.loads(reproduced.decode("utf-8")))


def prove_relationship_dual_sense_decomposition_v1(
    store: Any,
    *,
    binding: DecompositionRevisionBinding,
    predecessor: VerifiedPredecessorAuthority,
    current_residual_edge_ids: set[str] | frozenset[str],
    target: WholeWorldTargetContract,
) -> DualSenseDecompositionProofV1:
    package = derive_dual_sense_decomposition_package_v1(
        store,
        binding=binding,
        predecessor=predecessor,
        current_residual_edge_ids=current_residual_edge_ids,
        target=target,
    )
    raw = package_canonical_bytes(package)
    sealed = DualSenseDecompositionPackageV1.model_validate(json.loads(raw.decode("utf-8")))
    if not sealed.package_projection.passed:
        raise _fail("sealed package projection is not passed", "package_projection_failed")
    if any(
        str(getattr(row.aspect_ref, "source_node_id", "")).startswith("node:aspect:")
        or "synthetic" in row.aspect_ref.source_node_id
        for row in sealed.endpoint_assignments
    ):
        raise _fail("package created a synthetic Buddy node id", "synthetic_node_id")
    return DualSenseDecompositionProofV1(
        passed=True,
        package=sealed,
        package_sha256=sha256_bytes(raw),
        diagnostics=["package_projection_passed", "no_synthetic_buddy_node_ids"],
    )
