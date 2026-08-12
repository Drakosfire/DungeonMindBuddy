"""Non-publishing Eldyrwild deferred node-kind/source repair authority.

This authority is deliberately a read-only successor to the post-#563
relationship semantic closure.  It proves a typed in-memory overlay containing
four in-place kind repairs and three dual-sense aspect splits.  It never calls a
Kernel publish seam and never rewrites the base graph payload.

The manifest digest is self-excluding: ``canonical_payload_sha256`` is set to
the empty string while the remaining manifest is canonicalized with sorted
keys, compact separators, UTF-8, and no trailing newline.  The resulting
digest is then stored in the field.  ``LOCKED_MANIFEST_SHA256`` is the sha256 of
the deterministic pretty-printed manifest bytes on disk.
"""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from pathlib import Path
from typing import Any, Literal, Mapping, Sequence

from pydantic import BaseModel, ConfigDict, Field

import graph_memory.kernel as kernel
from apps.live_control_server.config import live_world_graph_root, repo_root, world_graph_root
from apps.live_control_server.integrations.dungeonmind_kernel.relationship_effective_conformance_v1 import (
    analyze_relationship_effective_conformance_v1,
)
from apps.live_control_server.integrations.dungeonmind_kernel.relationship_residual_adjudication import (
    RelationshipResidualAdjudicationError,
    resolve_evidence_excerpt,
    verify_excerpt_against_seal,
)
from apps.live_control_server.integrations.dungeonmind_kernel.whole_world_conformance_v4 import (
    PredicateDisposition,
    _classify_edge_predicate_v4,
    _current_relationship_edges,
)
from apps.live_control_server.services import eldyrwild_relationship_semantic_closure as closure_service
from dungeonmind_dnd.application.world_object_vocabulary import (
    load_builtin_world_object_v4_vocabulary,
)
from graph_memory.union_supergraph.model import (
    UnionSupergraphEdge,
    UnionSupergraphStore,
)
from graph_memory.world_supergraph.errors import WorldGraphNotFoundError


REPAIR_SCHEMA = "dmb_eldyrwild_relationship_node_kind_source_repair_v1"
REPAIR_ID = "eldyrwild-relationship-node-kind-source-repair-v1"
WORLD_ID = "eldyrwild"

MERGE_SHA_CONTEXT = "0479d50d048a88b92b9d200dbf3cbbc93d295ba2"
BASE_REVISION_ID = "rev:5a7c13ae45c49a65b402920499be72ed"
BASE_GRAPH_PAYLOAD_SHA256 = (
    "2632870ef70638969503de788cfdec97acd490875deff3e2630ac91dc96fe974"
)
PREDECESSOR_CLOSURE_ID = "eldyrwild-relationship-semantic-closure-v1"
PREDECESSOR_CLOSURE_MANIFEST_SHA256 = (
    "3d5da9b19b74a28d4930132e281c0e41197d3ea1493c5a202ba1ef6c6ffbfb25"
)

EXPECTED_BASE_INVENTORY = {
    "semantic": 323,
    "represented": 314,
    "residual": 9,
    "uses_statblock_mechanics": 3,
}
EXPECTED_PROJECTED_INVENTORY = {
    "semantic": 323,
    "represented": 323,
    "residual": 0,
    "uses_statblock_mechanics": 3,
}

DEFERRED_RESIDUAL_EDGE_IDS = frozenset(
    {
        "edge:combat_shatter_mages_tower_spider:located_in:item_shatter_mages_tower",
        "edge:loc:central-office:located_in:node:meat_distribution_network_session9:site-of",
        "edge:loc:packing-loading-area:part_of:node:meat_distribution_network_session9",
        "edge:loc:stone_bridge:contains:mystery_stone_bridge_river_name",
        "edge:node:headmaster_tinkerbright:leads:loc:wizard_college",
        "edge:node:hempholm_townsfolk:participates_in:node:hempholm_folk_revelry",
        "edge:node:torrin_flamescale:serves:loc:guilds:represents",
        "edge:node:torvak_hempdealer_crew:member_of:item:torvak-hemp-caravan",
        "edge:pc:caelynn:participates_in:node:hempholm_folk_revelry",
    }
)

MANIFEST_RELPATH = (
    "graph_data/approved_graph_corrections/eldyrwild/"
    "relationship-node-kind-source-repair-v1/manifest.json"
)

LOCKED_MANIFEST_SHA256 = (
    "9e382c85e575d5f3ba8ad328a52a3dc0156bc821c620e82fe67c16a908c2495e"
)


class RelationshipNodeKindSourceRepairError(RuntimeError):
    """Fail-closed repair authority error."""

    def __init__(self, message: str, *, code: str, status_code: int = 400) -> None:
        super().__init__(message)
        self.code = code
        self.status_code = status_code


class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


RepairEligibility = Literal["eligible", "ineligible", "integrity_failure"]


class RelationshipNodeKindSourceRepairStatus(_Model):
    schema_: str = Field(default=REPAIR_SCHEMA + "_status", alias="schema")
    world_id: str = WORLD_ID
    repair_id: str = REPAIR_ID
    head_revision_id: str | None = None
    eligibility: RepairEligibility
    reason: str | None = None
    diagnostics: list[str] = Field(default_factory=list)
    base_inventory: dict[str, int] | None = None
    residual_edge_ids: list[str] = Field(default_factory=list)


class RelationshipNodeKindSourceRepairProof(_Model):
    schema_: str = Field(default=REPAIR_SCHEMA + "_proof", alias="schema")
    world_id: str = WORLD_ID
    repair_id: str = REPAIR_ID
    base_revision_id: str
    base_graph_payload_sha256: str
    passed: bool
    all_deferred_edges_admitted: bool
    zero_regressions: bool
    base_inventory: dict[str, int]
    projected_inventory: dict[str, int]
    deferred_edge_proofs: list[dict[str, Any]] = Field(default_factory=list)
    regression_edge_ids: list[str] = Field(default_factory=list)
    diagnostics: list[str] = Field(default_factory=list)


class RelationshipNodeKindSourceRepairBuildResult(_Model):
    schema_: str = Field(default=REPAIR_SCHEMA + "_build_result", alias="schema")
    world_id: str = WORLD_ID
    repair_id: str = REPAIR_ID
    manifest_path: str
    manifest_sha256: str
    canonical_payload_sha256: str
    proof: RelationshipNodeKindSourceRepairProof
    diagnostics: list[str] = Field(default_factory=list)


class RelationshipNodeKindSourceRepairPin(_Model):
    schema_: str = Field(default=REPAIR_SCHEMA + "_pin", alias="schema")
    world_id: str = WORLD_ID
    repair_id: str = REPAIR_ID
    base_revision_id: str
    base_graph_payload_sha256: str
    canonical_payload_sha256: str
    manifest_sha256: str
    projected_inventory: dict[str, int]
    diagnostics: list[str] = Field(default_factory=list)


KIND_REPAIR_SPECS: tuple[dict[str, Any], ...] = (
    {
        "node_id": "item_shatter_mages_tower",
        "current_kind": "item",
        "corrected_kind": "location",
        "affected_deferred_edge_ids": (
            "edge:combat_shatter_mages_tower_spider:located_in:item_shatter_mages_tower",
        ),
        "note": (
            "The sealed recap calls this a tower and the deferred located_in "
            "edge needs a location endpoint; this is uniquely source-required "
            "by adapter admission and source; adapter admission must not widen "
            "located_in to item."
        ),
    },
    {
        "node_id": "item:torvak-hemp-caravan",
        "current_kind": "item",
        "corrected_kind": "group",
        "affected_deferred_edge_ids": (
            "edge:node:torvak_hempdealer_crew:member_of:item:torvak-hemp-caravan",
        ),
        "note": (
            "The sealed recap describes a caravan with a crew; member_of "
            "already admits group/faction/party and does not admit item; "
            "adapter admission and source uniquely require group."
        ),
    },
    {
        "node_id": "loc:guilds",
        "current_kind": "location",
        "corrected_kind": "faction",
        "affected_deferred_edge_ids": (
            "edge:node:torrin_flamescale:serves:loc:guilds:represents",
        ),
        "note": (
            "The sealed source identifies the Guilds as Torrin's represented "
            "collective; adapter admission and source uniquely require faction, "
            "without widening serves to location."
        ),
    },
    {
        "node_id": "mystery_stone_bridge_river_name",
        "current_kind": "mystery",
        "corrected_kind": "location",
        "affected_deferred_edge_ids": (
            "edge:loc:stone_bridge:contains:mystery_stone_bridge_river_name",
        ),
        "note": (
            "The sealed recap describes the river by Stone Bridge; contains "
            "requires a location endpoint by adapter admission and source, and "
            "must not be widened to mystery."
        ),
    },
)

ASPECT_SPLIT_SPECS: tuple[dict[str, Any], ...] = (
    {
        "source_node_id": "loc:wizard_college",
        "source_retained_kind": "location",
        "aspect_node_id": "faction:wizard_college",
        "aspect_kind": "faction",
        "aspect_label": "Wizard's College (organization)",
        "edges_rewired_to_aspect": (
            "edge:node:headmaster_tinkerbright:leads:loc:wizard_college",
        ),
        "edges_retained_on_source": (
            "edge:node:thalia:travels_to:loc:wizard_college",
            "edge:node:torbin:travels_to:loc:wizard_college",
            "edge:loc:wizard_college:within:node:city_mirathorn",
        ),
        "split_basis": (
            "The sealed source gives the same node two senses: the physical "
            "college location and its organized collective led by the headmaster. "
            "Kernel split_identity is insufficient because it preserves the "
            "source kind and does not rewire selected deferred edges."
        ),
    },
    {
        "source_node_id": "node:hempholm_folk_revelry",
        "source_retained_kind": "group",
        "aspect_node_id": "event:hempholm_folk_revelry",
        "aspect_kind": "event",
        "aspect_label": "Hempholm folk revelry",
        "edges_rewired_to_aspect": (
            "edge:node:hempholm_townsfolk:participates_in:node:hempholm_folk_revelry",
            "edge:pc:caelynn:participates_in:node:hempholm_folk_revelry",
        ),
        "edges_retained_on_source": (
            "edge:node:hempholm_folk_revelry:within:loc:hempholm",
        ),
        "split_basis": (
            "The sealed source describes a revelry event attended by townsfolk "
            "and Caelynn while the original node label/kind is the revelers "
            "group. Preserve the group identity and introduce an event aspect."
        ),
    },
    {
        "source_node_id": "node:meat_distribution_network_session9",
        "source_retained_kind": "party",
        "aspect_node_id": "loc:meat_distribution_site_session9",
        "aspect_kind": "location",
        "aspect_label": "Meat Distribution Site",
        "edges_rewired_to_aspect": (
            "edge:loc:central-office:located_in:node:meat_distribution_network_session9:site-of",
            "edge:loc:packing-loading-area:part_of:node:meat_distribution_network_session9",
        ),
        "edges_retained_on_source": (
            "edge:node:captain_blart:leads:node:meat_distribution_network_session9:coordinates",
            "edge:node:lyra:leads:node:meat_distribution_network_session9",
        ),
        "split_basis": (
            "The sealed source describes both the meat distribution project as "
            "a party/collective led by Blart and Lyra and its physical site. "
            "Preserve the party source and introduce a location aspect."
        ),
    },
)


def _repo(repo: Path | None) -> Path:
    return (repo or repo_root()).resolve()


def _root(root: Path | None) -> Path:
    return (root or world_graph_root()).resolve()


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha256_text(value: str) -> str:
    return _sha256_bytes(value.encode("utf-8"))


def _json_bytes(payload: Mapping[str, Any], *, pretty: bool) -> bytes:
    if pretty:
        text = json.dumps(payload, ensure_ascii=False, indent=1, sort_keys=True) + "\n"
    else:
        text = json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
    return text.encode("utf-8")


def _canonical_payload_sha256(payload: Mapping[str, Any]) -> str:
    body = dict(payload)
    body["canonical_payload_sha256"] = ""
    return _sha256_bytes(_json_bytes(body, pretty=False))


def _manifest_path(repo: Path | None = None) -> Path:
    return _repo(repo) / MANIFEST_RELPATH


def _is_live_root(root: Path) -> bool:
    return root.resolve() == live_world_graph_root().resolve()


def _fail(message: str, code: str) -> RelationshipNodeKindSourceRepairError:
    return RelationshipNodeKindSourceRepairError(message, code=code)


def _load_repair_manifest(repo: Path | None = None) -> dict[str, Any]:
    path = _manifest_path(repo)
    if not path.is_file():
        raise _fail(f"repair manifest missing: {MANIFEST_RELPATH}", "manifest_missing")
    raw = path.read_bytes()
    digest = _sha256_bytes(raw)
    if digest != LOCKED_MANIFEST_SHA256:
        raise _fail(
            f"repair manifest sha256 {digest} != locked {LOCKED_MANIFEST_SHA256}",
            "manifest_tampered",
        )
    try:
        payload = json.loads(raw.decode("utf-8"))
    except json.JSONDecodeError as exc:
        raise _fail(f"repair manifest is not JSON: {exc}", "manifest_invalid") from exc
    _validate_manifest_payload(payload)
    return payload


def _validate_manifest_payload(payload: Mapping[str, Any]) -> None:
    if payload.get("schema") != REPAIR_SCHEMA:
        raise _fail("repair manifest schema mismatch", "manifest_invalid")
    if payload.get("repair_id") != REPAIR_ID or payload.get("world_id") != WORLD_ID:
        raise _fail("repair manifest identity mismatch", "manifest_invalid")
    for field, expected in (
        ("base_revision_id", BASE_REVISION_ID),
        ("base_graph_payload_sha256", BASE_GRAPH_PAYLOAD_SHA256),
        ("predecessor_closure_id", PREDECESSOR_CLOSURE_ID),
        ("predecessor_closure_manifest_sha256", PREDECESSOR_CLOSURE_MANIFEST_SHA256),
        ("expected_base_inventory", EXPECTED_BASE_INVENTORY),
        ("expected_projected_inventory", EXPECTED_PROJECTED_INVENTORY),
    ):
        if payload.get(field) != expected:
            raise _fail(f"repair manifest {field} mismatch", "manifest_invalid")
    if payload.get("expected_deferred_residual_edge_ids") != sorted(
        DEFERRED_RESIDUAL_EDGE_IDS
    ):
        raise _fail("repair manifest deferred residual set mismatch", "manifest_invalid")
    canonical = payload.get("canonical_payload_sha256")
    if not isinstance(canonical, str) or canonical != _canonical_payload_sha256(payload):
        raise _fail("repair manifest canonical digest mismatch", "manifest_invalid")
    repairs = payload.get("kind_repairs")
    splits = payload.get("aspect_splits")
    if not isinstance(repairs, list) or [r.get("node_id") for r in repairs] != sorted(
        r.get("node_id") for r in repairs
    ):
        raise _fail("repair manifest kind repair order mismatch", "manifest_invalid")
    if not isinstance(splits, list) or [
        s.get("source_node_id") for s in splits
    ] != sorted(s.get("source_node_id") for s in splits):
        raise _fail("repair manifest aspect split order mismatch", "manifest_invalid")
    if len(repairs) != len(KIND_REPAIR_SPECS) or len(splits) != len(ASPECT_SPLIT_SPECS):
        raise _fail("repair manifest repair counts mismatch", "manifest_invalid")


def _load_predecessor_manifest(repo: Path) -> dict[str, Any]:
    try:
        return closure_service._load_manifest(repo=repo)
    except Exception as exc:  # noqa: BLE001
        raise _fail(f"predecessor closure unavailable: {exc}", "predecessor_invalid") from exc


def _deferred_units(repo: Path) -> list[dict[str, Any]]:
    predecessor = _load_predecessor_manifest(repo)
    units = [
        unit
        for unit in predecessor.get("units", [])
        if unit.get("deferred") is True
    ]
    if {unit.get("edge_id") for unit in units} != set(DEFERRED_RESIDUAL_EDGE_IDS):
        raise _fail("predecessor deferred edge coverage drift", "predecessor_invalid")
    if len(units) != 9:
        raise _fail("predecessor deferred unit count drift", "predecessor_invalid")
    return sorted(units, key=lambda unit: unit["edge_id"])


def _unit_by_edge(units: Sequence[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {unit["edge_id"]: unit for unit in units}


def _support_authority_diagnostics(
    *, root: Path, store: UnionSupergraphStore, unit: dict[str, Any]
) -> list[str]:
    diagnostics: list[str] = []
    for contribution_id in unit.get("target_contribution_ids") or []:
        locked = (unit.get("target_source_payload_sha256") or {}).get(contribution_id)
        if not locked:
            diagnostics.append(f"target_source_digest_missing:{contribution_id}")
            continue
        ok, details = closure_service._verify_locked_target_source_contribution_authority(
            root=root,
            store=store,
            contribution_id=contribution_id,
            locked_source_payload_sha256=locked,
            target_assertion_id=unit.get("target_assertion_id"),
        )
        if not ok:
            diagnostics.extend(details)
    return diagnostics


def _seal_diagnostics(
    *, root: Path, store: UnionSupergraphStore, unit: dict[str, Any]
) -> list[str]:
    seal = unit.get("seal") or {}
    evidence_id = seal.get("primary_evidence_ref_id")
    if not evidence_id:
        return [f"source_seal_missing_primary_evidence:{unit.get('edge_id')}"]
    try:
        live = resolve_evidence_excerpt(
            store,
            edge_id=unit["edge_id"],
            evidence_ref_id=evidence_id,
            world_graph_root=root,
        )
        verify_excerpt_against_seal(live, seal, edge_id=unit["edge_id"])
    except (RelationshipResidualAdjudicationError, OSError) as exc:
        return [f"source_seal_failed:{unit.get('edge_id')}:{exc}"]
    return []


def _verify_deferred_authority(
    *, root: Path, store: UnionSupergraphStore, units: Sequence[dict[str, Any]]
) -> list[str]:
    diagnostics: list[str] = []
    for unit in units:
        diagnostics.extend(_seal_diagnostics(root=root, store=store, unit=unit))
        diagnostics.extend(_support_authority_diagnostics(root=root, store=store, unit=unit))
    return diagnostics


def _base_report(root: Path):
    try:
        return analyze_relationship_effective_conformance_v1(
            root=root,
            world_id=WORLD_ID,
            revision_id=BASE_REVISION_ID,
        )
    except Exception as exc:  # noqa: BLE001
        raise _fail(f"base conformance analysis failed: {exc}", "base_analysis_failed") from exc


def _open_exact_base(root: Path) -> tuple[Any, Any, UnionSupergraphStore]:
    try:
        head, revision, store = kernel.open_current_world_graph(root, WORLD_ID)
    except WorldGraphNotFoundError as exc:
        raise _fail(f"world graph missing: {WORLD_ID}", "world_missing") from exc
    if head.head_revision_id != BASE_REVISION_ID:
        raise _fail(
            f"stale head {head.head_revision_id!r} != exact base {BASE_REVISION_ID!r}",
            "stale_base",
        )
    if revision.revision_id != BASE_REVISION_ID:
        raise _fail("opened revision is not exact base", "stale_base")
    manifest = kernel.load_world_graph_revision_manifest(root, WORLD_ID, BASE_REVISION_ID)
    payload_sha = getattr(manifest, "graph_payload_sha256", None)
    if payload_sha != BASE_GRAPH_PAYLOAD_SHA256:
        raise _fail(
            f"base graph payload sha {payload_sha} != {BASE_GRAPH_PAYLOAD_SHA256}",
            "base_payload_mismatch",
        )
    return head, revision, store


def _inventory_from_report(report: Any) -> dict[str, int]:
    return {
        "semantic": report.relationship_semantic_count,
        "represented": report.relationship_effectively_represented_count,
        "residual": report.relationship_effective_residual_count,
        "uses_statblock_mechanics": report.uses_statblock_mechanics_count,
    }


def _base_gate(root: Path) -> tuple[Any, UnionSupergraphStore, dict[str, int], list[str]]:
    _head, _revision, store = _open_exact_base(root)
    report = _base_report(root)
    inventory = _inventory_from_report(report)
    diagnostics: list[str] = []
    if inventory != EXPECTED_BASE_INVENTORY:
        diagnostics.append(f"base_inventory_mismatch:{inventory}")
    if set(report.remaining_residual_edge_ids) != set(DEFERRED_RESIDUAL_EDGE_IDS):
        diagnostics.append(
            "base_residual_set_mismatch:"
            + json.dumps(sorted(report.remaining_residual_edge_ids))
        )
    return report, store, inventory, diagnostics


def _edge_proof(
    edge: UnionSupergraphEdge,
    store: UnionSupergraphStore,
    vocabulary: Any,
) -> dict[str, Any]:
    result = _classify_edge_predicate_v4(
        edge,
        store,
        vocabulary,
        adjudication_domain=True,
    )
    classification, blocker, note, disposition, mapped, reverse = result
    source = store.nodes.get(edge.source_node_id)
    target = store.nodes.get(edge.target_node_id)
    return {
        "edge_id": edge.edge_id,
        "source_node_id": edge.source_node_id,
        "target_node_id": edge.target_node_id,
        "predicate": edge.predicate,
        "source_kind": source.kind if source else None,
        "target_kind": target.kind if target else None,
        "classification": getattr(classification, "value", str(classification)),
        "blocker": getattr(blocker, "value", str(blocker)) if blocker else None,
        "disposition": getattr(disposition, "value", str(disposition)),
        "mapped_dm_term": mapped,
        "reverse_endpoints": reverse,
        "note": note,
    }


def _overlay_store(
    store: UnionSupergraphStore,
    *,
    kind_repairs: Sequence[Mapping[str, Any]] = KIND_REPAIR_SPECS,
    aspect_splits: Sequence[Mapping[str, Any]] = ASPECT_SPLIT_SPECS,
) -> UnionSupergraphStore:
    _validate_aspect_split_specs(store, aspect_splits)
    nodes = dict(store.nodes)
    edges = dict(store.edges)

    for repair in sorted(kind_repairs, key=lambda item: str(item["node_id"])):
        node_id = str(repair["node_id"])
        node = nodes.get(node_id)
        if node is None:
            raise _fail(f"kind repair node missing: {node_id}", "repair_target_missing")
        if node.kind != repair["current_kind"]:
            raise _fail(
                f"kind repair current kind drift for {node_id}: "
                f"{node.kind} != {repair['current_kind']}",
                "kind_source_drift",
            )
        nodes[node_id] = node.model_copy(update={"kind": repair["corrected_kind"]})

    for split in sorted(aspect_splits, key=lambda item: str(item["source_node_id"])):
        source_id = str(split["source_node_id"])
        source = nodes.get(source_id)
        if source is None:
            raise _fail(f"aspect source missing: {source_id}", "repair_target_missing")
        aspect_id = str(split["aspect_node_id"])
        aspect = source.model_copy(
            update={
                "node_id": aspect_id,
                "label": split["aspect_label"],
                "kind": split["aspect_kind"],
                "role": split["aspect_kind"],
                "state": {
                    **dict(source.state or {}),
                    "aspect_of_node_id": source_id,
                    "aspect_state": "non_publishing_repair_overlay",
                },
            }
        )
        nodes[aspect_id] = aspect
        for edge_id in split["edges_rewired_to_aspect"]:
            edge = edges.get(edge_id)
            if edge is None:
                raise _fail(f"aspect edge missing: {edge_id}", "repair_target_missing")
            if edge.target_node_id != source_id:
                raise _fail(
                    f"aspect edge {edge_id} does not target {source_id}",
                    "aspect_edge_shape_drift",
                )
            edges[edge_id] = edge.model_copy(update={"target_node_id": aspect_id})

    return store.model_copy(update={"nodes": nodes, "edges": edges})


def _validate_aspect_split_specs(
    store: UnionSupergraphStore,
    specs: Sequence[Mapping[str, Any]],
) -> None:
    source_ids: set[str] = set()
    aspect_ids: set[str] = set()
    rewired_ids: set[str] = set()
    for split in specs:
        source_id = str(split["source_node_id"])
        aspect_id = str(split["aspect_node_id"])
        if source_id in source_ids or aspect_id in aspect_ids:
            raise _fail(
                f"conflicting aspect split for source/aspect {source_id}/{aspect_id}",
                "aspect_split_conflict",
            )
        source_ids.add(source_id)
        aspect_ids.add(aspect_id)
        if aspect_id in store.nodes:
            raise _fail(f"aspect node already exists: {aspect_id}", "aspect_split_conflict")
        source = store.nodes.get(source_id)
        if source is None:
            raise _fail(f"aspect source missing: {source_id}", "repair_target_missing")
        if source.kind != split["source_retained_kind"]:
            raise _fail(
                f"aspect source kind drift for {source_id}: "
                f"{source.kind} != {split['source_retained_kind']}",
                "kind_source_drift",
            )
        local_rewired = set(split["edges_rewired_to_aspect"])
        if rewired_ids & local_rewired:
            raise _fail("aspect split edge overlap", "aspect_split_conflict")
        rewired_ids.update(local_rewired)
        for edge_id in local_rewired:
            edge = store.edges.get(edge_id)
            if edge is None or edge.target_node_id != source_id:
                raise _fail(
                    f"aspect deferred edge shape drift: {edge_id}",
                    "aspect_edge_shape_drift",
                )
        retained = set(split["edges_retained_on_source"])
        if local_rewired & retained:
            raise _fail(
                f"edge cannot be both rewired and retained: {source_id}",
                "aspect_split_conflict",
            )
        for edge_id in retained:
            edge = store.edges.get(edge_id)
            if edge is None or edge.source_node_id != source_id and edge.target_node_id != source_id:
                raise _fail(
                    f"aspect retained edge shape drift: {edge_id}",
                    "aspect_edge_shape_drift",
                )


def _source_authority_fields(units: Sequence[dict[str, Any]]) -> dict[str, Any]:
    contribution_digests: dict[str, str] = {}
    for unit in units:
        for contribution_id, digest in (unit.get("target_source_payload_sha256") or {}).items():
            prior = contribution_digests.get(contribution_id)
            if prior is not None and prior != digest:
                raise _fail(
                    f"contribution digest conflict: {contribution_id}",
                    "source_authority_conflict",
                )
            contribution_digests[contribution_id] = digest
    return {
        "source_contribution_ids": sorted(contribution_digests),
        "source_contribution_payload_sha256": dict(
            sorted(contribution_digests.items())
        ),
    }


def _seal_fields(units: Sequence[dict[str, Any]]) -> dict[str, Any]:
    seals = [dict(unit["seal"]) for unit in units]
    seals.sort(key=lambda seal: seal["edge_id"])
    return {
        "source_artifact_ids": sorted(
            {seal["source_artifact_id"] for seal in seals}
        ),
        "source_seals": seals,
    }


def _basis_fields(units: Sequence[dict[str, Any]], note: str) -> dict[str, Any]:
    return {
        "closure_unit_ids": sorted(unit["unit_id"] for unit in units),
        "seal_excerpt_refs": [
            {
                "edge_id": unit["edge_id"],
                "primary_evidence_ref_id": unit["seal"]["primary_evidence_ref_id"],
                "source_span_ref_id": unit["seal"]["source_span_ref_id"],
                "excerpt_sha256": unit["seal"]["excerpt_sha256"],
            }
            for unit in sorted(units, key=lambda row: row["edge_id"])
        ],
        "note": note,
        "source_rationales": {
            unit["edge_id"]: unit.get("rationale", "")
            for unit in sorted(units, key=lambda row: row["edge_id"])
        },
    }


def _make_repair_entries(
    *,
    base_store: UnionSupergraphStore,
    overlay: UnionSupergraphStore,
    units: Sequence[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    by_edge = _unit_by_edge(units)
    vocabulary = load_builtin_world_object_v4_vocabulary()
    kind_entries: list[dict[str, Any]] = []
    for spec in KIND_REPAIR_SPECS:
        selected = [by_edge[edge_id] for edge_id in spec["affected_deferred_edge_ids"]]
        before = [
            _edge_proof(base_store.edges[edge_id], base_store, vocabulary)
            for edge_id in spec["affected_deferred_edge_ids"]
        ]
        after = [
            _edge_proof(overlay.edges[edge_id], overlay, vocabulary)
            for edge_id in spec["affected_deferred_edge_ids"]
        ]
        authority = _source_authority_fields(selected)
        kind_entries.append(
            {
                "node_id": spec["node_id"],
                "current_kind": spec["current_kind"],
                "corrected_kind": spec["corrected_kind"],
                "affected_deferred_edge_ids": sorted(spec["affected_deferred_edge_ids"]),
                **authority,
                **_seal_fields(selected),
                "kind_basis": _basis_fields(selected, spec["note"]),
                "admissibility_before": before,
                "admissibility_after": after,
            }
        )

    split_entries: list[dict[str, Any]] = []
    for spec in ASPECT_SPLIT_SPECS:
        affected = [
            by_edge[edge_id]
            for edge_id in spec["edges_rewired_to_aspect"]
        ]
        proof_edge_ids = list(spec["edges_rewired_to_aspect"]) + list(
            spec["edges_retained_on_source"]
        )
        before = [
            _edge_proof(base_store.edges[edge_id], base_store, vocabulary)
            for edge_id in proof_edge_ids
        ]
        after = [
            _edge_proof(overlay.edges[edge_id], overlay, vocabulary)
            for edge_id in proof_edge_ids
        ]
        split_entries.append(
            {
                "source_node_id": spec["source_node_id"],
                "source_retained_kind": spec["source_retained_kind"],
                "aspect_node_id": spec["aspect_node_id"],
                "aspect_kind": spec["aspect_kind"],
                "aspect_label": spec["aspect_label"],
                "edges_rewired_to_aspect": sorted(spec["edges_rewired_to_aspect"]),
                "edges_retained_on_source": sorted(spec["edges_retained_on_source"]),
                **_source_authority_fields(affected),
                **_seal_fields(affected),
                "split_basis": {
                    "note": spec["split_basis"],
                    "conflict": "dual_sense_source_identity",
                    "kernel_split_identity_insufficient": True,
                    "closure_unit_ids": sorted(unit["unit_id"] for unit in affected),
                },
                "admissibility_before": before,
                "admissibility_after": after,
            }
        )
    return (
        sorted(kind_entries, key=lambda entry: entry["node_id"]),
        sorted(split_entries, key=lambda entry: entry["source_node_id"]),
    )


def _validate_repair_entries(
    *,
    payload: Mapping[str, Any],
    base_store: UnionSupergraphStore,
    overlay: UnionSupergraphStore,
) -> None:
    expected_kind_specs = {spec["node_id"]: spec for spec in KIND_REPAIR_SPECS}
    for entry in payload["kind_repairs"]:
        spec = expected_kind_specs.get(entry["node_id"])
        if spec is None:
            raise _fail("unexpected kind repair entry", "manifest_invalid")
        if entry["current_kind"] != spec["current_kind"] or entry["corrected_kind"] != spec["corrected_kind"]:
            raise _fail(f"kind repair semantics drift: {entry['node_id']}", "manifest_invalid")
        for proof in entry["admissibility_after"]:
            if proof["disposition"] != PredicateDisposition.EXISTING_EXPLICIT_ADAPTER.value:
                raise _fail(
                    f"kind repair edge not admitted: {proof['edge_id']}",
                    "repair_proof_failed",
                )

    expected_split_specs = {
        spec["source_node_id"]: spec for spec in ASPECT_SPLIT_SPECS
    }
    for entry in payload["aspect_splits"]:
        spec = expected_split_specs.get(entry["source_node_id"])
        if spec is None:
            raise _fail("unexpected aspect split entry", "manifest_invalid")
        if entry["aspect_node_id"] != spec["aspect_node_id"] or entry["aspect_kind"] != spec["aspect_kind"]:
            raise _fail(
                f"aspect split semantics drift: {entry['source_node_id']}",
                "manifest_invalid",
            )
        for proof in entry["admissibility_after"]:
            if proof["edge_id"] in spec["edges_rewired_to_aspect"] and (
                proof["disposition"] != PredicateDisposition.EXISTING_EXPLICIT_ADAPTER.value
            ):
                raise _fail(
                    f"aspect deferred edge not admitted: {proof['edge_id']}",
                    "repair_proof_failed",
                )


def _build_manifest_payload(
    *,
    root: Path,
    repo: Path,
    base_store: UnionSupergraphStore,
    base_inventory: dict[str, int],
) -> tuple[dict[str, Any], RelationshipNodeKindSourceRepairProof]:
    units = _deferred_units(repo)
    authority_diags = _verify_deferred_authority(
        root=root,
        store=base_store,
        units=units,
    )
    if authority_diags:
        raise _fail(
            "deferred source authority failed: " + "; ".join(authority_diags[:10]),
            "source_authority_failed",
        )
    overlay = _overlay_store(base_store)
    kind_entries, split_entries = _make_repair_entries(
        base_store=base_store,
        overlay=overlay,
        units=units,
    )
    payload: dict[str, Any] = {
        "schema": REPAIR_SCHEMA,
        "repair_id": REPAIR_ID,
        "world_id": WORLD_ID,
        "merge_sha_context": MERGE_SHA_CONTEXT,
        "base_revision_id": BASE_REVISION_ID,
        "base_graph_payload_sha256": BASE_GRAPH_PAYLOAD_SHA256,
        "predecessor_closure_id": PREDECESSOR_CLOSURE_ID,
        "predecessor_closure_manifest_sha256": PREDECESSOR_CLOSURE_MANIFEST_SHA256,
        "expected_base_inventory": dict(EXPECTED_BASE_INVENTORY),
        "expected_deferred_residual_edge_ids": sorted(DEFERRED_RESIDUAL_EDGE_IDS),
        "expected_projected_inventory": dict(EXPECTED_PROJECTED_INVENTORY),
        "kind_repairs": kind_entries,
        "aspect_splits": split_entries,
        "canonical_payload_sha256": "",
    }
    payload["canonical_payload_sha256"] = _canonical_payload_sha256(payload)
    proof = _prove_overlay(
        base_store=base_store,
        overlay=overlay,
        base_inventory=base_inventory,
    )
    if not proof.passed:
        raise _fail(
            "isolated repair proof failed: " + "; ".join(proof.diagnostics[:10]),
            "repair_proof_failed",
        )
    _validate_repair_entries(
        payload=payload,
        base_store=base_store,
        overlay=overlay,
    )
    return payload, proof


def _prove_overlay(
    *,
    base_store: UnionSupergraphStore,
    overlay: UnionSupergraphStore,
    base_inventory: dict[str, int],
) -> RelationshipNodeKindSourceRepairProof:
    vocabulary = load_builtin_world_object_v4_vocabulary()
    deferred_proofs: list[dict[str, Any]] = []
    for edge_id in sorted(DEFERRED_RESIDUAL_EDGE_IDS):
        proof = _edge_proof(overlay.edges[edge_id], overlay, vocabulary)
        proof["base"] = _edge_proof(base_store.edges[edge_id], base_store, vocabulary)
        deferred_proofs.append(proof)
    admitted = all(
        proof["disposition"] == PredicateDisposition.EXISTING_EXPLICIT_ADAPTER.value
        for proof in deferred_proofs
    )

    touched_sources = {
        spec["node_id"] for spec in KIND_REPAIR_SPECS
    } | {spec["source_node_id"] for spec in ASPECT_SPLIT_SPECS}
    rewired = {
        edge_id
        for spec in ASPECT_SPLIT_SPECS
        for edge_id in spec["edges_rewired_to_aspect"]
    }
    regressions: list[str] = []
    for edge in _current_relationship_edges(base_store):
        if edge.edge_id in DEFERRED_RESIDUAL_EDGE_IDS or edge.edge_id in rewired:
            continue
        if edge.source_node_id not in touched_sources and edge.target_node_id not in touched_sources:
            continue
        before = _edge_proof(edge, base_store, vocabulary)
        if before["disposition"] != PredicateDisposition.EXISTING_EXPLICIT_ADAPTER.value:
            continue
        after = _edge_proof(overlay.edges[edge.edge_id], overlay, vocabulary)
        if after["disposition"] != PredicateDisposition.EXISTING_EXPLICIT_ADAPTER.value:
            regressions.append(edge.edge_id)

    projected = {
        "semantic": base_inventory["semantic"],
        "represented": base_inventory["represented"] + len(DEFERRED_RESIDUAL_EDGE_IDS),
        "residual": base_inventory["residual"] - len(DEFERRED_RESIDUAL_EDGE_IDS),
        "uses_statblock_mechanics": base_inventory["uses_statblock_mechanics"],
    }
    diagnostics: list[str] = []
    if base_inventory != EXPECTED_BASE_INVENTORY:
        diagnostics.append(f"base_inventory_mismatch:{base_inventory}")
    if not admitted:
        diagnostics.append("deferred_edge_not_admitted")
    if regressions:
        diagnostics.append("non_deferred_regressions:" + ",".join(sorted(regressions)))
    if projected != EXPECTED_PROJECTED_INVENTORY:
        diagnostics.append(f"projected_inventory_mismatch:{projected}")
    return RelationshipNodeKindSourceRepairProof(
        base_revision_id=BASE_REVISION_ID,
        base_graph_payload_sha256=BASE_GRAPH_PAYLOAD_SHA256,
        passed=not diagnostics,
        all_deferred_edges_admitted=admitted,
        zero_regressions=not regressions,
        base_inventory=base_inventory,
        projected_inventory=projected,
        deferred_edge_proofs=deferred_proofs,
        regression_edge_ids=sorted(regressions),
        diagnostics=diagnostics,
    )


def get_relationship_node_kind_source_repair_status(
    root: Path | None = None,
    *,
    repo: Path | None = None,
) -> RelationshipNodeKindSourceRepairStatus:
    """Return eligibility against the exact pinned base, without mutation."""
    world_root = _root(root)
    try:
        _load_repair_manifest(repo=repo)
    except RelationshipNodeKindSourceRepairError as exc:
        return RelationshipNodeKindSourceRepairStatus(
            eligibility="integrity_failure",
            reason=str(exc),
            diagnostics=[exc.code],
        )
    try:
        _head, _store_revision, store = _open_exact_base(world_root)
        report = _base_report(world_root)
        inventory = _inventory_from_report(report)
        residuals = sorted(report.remaining_residual_edge_ids)
    except RelationshipNodeKindSourceRepairError as exc:
        return RelationshipNodeKindSourceRepairStatus(
            head_revision_id=None,
            eligibility="ineligible",
            reason=str(exc),
            diagnostics=[exc.code],
        )
    diagnostics: list[str] = []
    if inventory != EXPECTED_BASE_INVENTORY:
        diagnostics.append(f"base_inventory_mismatch:{inventory}")
    if set(residuals) != set(DEFERRED_RESIDUAL_EDGE_IDS):
        diagnostics.append("residual_set_mismatch")
    if diagnostics:
        return RelationshipNodeKindSourceRepairStatus(
            head_revision_id=BASE_REVISION_ID,
            eligibility="ineligible",
            reason="exact base inventory or residual pins do not hold",
            diagnostics=diagnostics,
            base_inventory=inventory,
            residual_edge_ids=residuals,
        )
    return RelationshipNodeKindSourceRepairStatus(
        head_revision_id=BASE_REVISION_ID,
        eligibility="eligible",
        reason="exact post-#563 base and residual pins hold",
        diagnostics=["status_ok"],
        base_inventory=inventory,
        residual_edge_ids=residuals,
    )


def build_relationship_node_kind_source_repair(
    *,
    root: Path | None = None,
    repo: Path | None = None,
    allow_live_world: bool = False,
) -> RelationshipNodeKindSourceRepairBuildResult:
    """Derive and atomically write the non-publishing repair manifest.

    ``allow_live_world`` is intentionally only a guard observation.  Even when
    the configured root is live, this function has no graph write path; the
    only durable write is the allowlisted repository manifest.
    """
    del allow_live_world
    world_root = _root(root)
    repository = _repo(repo)
    _head, _revision, store = _open_exact_base(world_root)
    report, _store, inventory, diagnostics = _base_gate(world_root)
    if diagnostics:
        raise _fail("; ".join(diagnostics), "base_ineligible")
    payload, proof = _build_manifest_payload(
        root=world_root,
        repo=repository,
        base_store=store,
        base_inventory=inventory,
    )
    path = _manifest_path(repository)
    raw = _json_bytes(payload, pretty=True)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            temp_path = Path(handle.name)
            handle.write(raw)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_path, path)
    except OSError as exc:
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)
        raise _fail(f"atomic manifest write failed: {exc}", "manifest_write_failed") from exc
    manifest_digest = _sha256_bytes(raw)
    return RelationshipNodeKindSourceRepairBuildResult(
        manifest_path=str(path),
        manifest_sha256=manifest_digest,
        canonical_payload_sha256=payload["canonical_payload_sha256"],
        proof=proof,
        diagnostics=["non_publishing", "manifest_written_atomically"],
    )


def verify_relationship_node_kind_source_repair(
    *,
    root: Path | None = None,
    repo: Path | None = None,
) -> RelationshipNodeKindSourceRepairPin | None:
    """Verify the locked manifest and its isolated proof; return a pin or None."""
    try:
        payload = _load_repair_manifest(repo=repo)
        world_root = _root(root)
        _head, _revision, store = _open_exact_base(world_root)
        report, _store, inventory, diagnostics = _base_gate(world_root)
        if diagnostics:
            return None
        units = _deferred_units(_repo(repo))
        if _verify_deferred_authority(root=world_root, store=store, units=units):
            return None
        overlay = _overlay_store(store)
        proof = _prove_overlay(
            base_store=store,
            overlay=overlay,
            base_inventory=inventory,
        )
        if not proof.passed:
            return None
        _validate_repair_entries(payload=payload, base_store=store, overlay=overlay)
        manifest_raw = _manifest_path(repo).read_bytes()
        return RelationshipNodeKindSourceRepairPin(
            base_revision_id=BASE_REVISION_ID,
            base_graph_payload_sha256=BASE_GRAPH_PAYLOAD_SHA256,
            canonical_payload_sha256=payload["canonical_payload_sha256"],
            manifest_sha256=_sha256_bytes(manifest_raw),
            projected_inventory=proof.projected_inventory,
            diagnostics=["repair_verified", "non_publishing", "exact_base"],
        )
    except (
        RelationshipNodeKindSourceRepairError,
        RelationshipResidualAdjudicationError,
        OSError,
        ValueError,
        KeyError,
    ):
        return None


def prove_isolated_repair_effect(
    root: Path | None = None,
    *,
    repo: Path | None = None,
) -> RelationshipNodeKindSourceRepairProof:
    """Prove the repair using only an in-memory overlay on the exact base store."""
    world_root = _root(root)
    repository = _repo(repo)
    _head, _revision, store = _open_exact_base(world_root)
    report, _base_store, inventory, diagnostics = _base_gate(world_root)
    if diagnostics:
        raise _fail("; ".join(diagnostics), "base_ineligible")
    units = _deferred_units(repository)
    authority_diags = _verify_deferred_authority(
        root=world_root,
        store=store,
        units=units,
    )
    if authority_diags:
        raise _fail("; ".join(authority_diags[:10]), "source_authority_failed")
    overlay = _overlay_store(store)
    proof = _prove_overlay(
        base_store=store,
        overlay=overlay,
        base_inventory=inventory,
    )
    if report.source_graph_payload_sha256 != BASE_GRAPH_PAYLOAD_SHA256:
        raise _fail("base report payload pin drift", "base_payload_mismatch")
    return proof

