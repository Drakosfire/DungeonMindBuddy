"""CUTOVER successor: seal dual-sense relationship decomposition package.

Diagnostic only. Derives a revision-bound, source-grounded materialization
plan for the exact five remaining relationship STOP edges. Does not mutate
Eldyrwild and does not claim durable DungeonMind materialization.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

import graph_memory.kernel as kernel
from apps.live_control_server.config import repo_root, world_graph_root
from apps.live_control_server.integrations.dungeonmind_kernel import (
    whole_world_conformance_v4 as whole_world_v4,
)
from apps.live_control_server.integrations.dungeonmind_kernel.relationship_dual_sense_decomposition_v1 import (
    DualSenseDecompositionPackageV1,
    RelationshipDualSenseDecompositionError,
    decomposition_binding_from_attested_revision,
    package_canonical_bytes,
    predecessor_authority_from_locked_bytes,
    prove_relationship_dual_sense_decomposition_v1,
    sha256_bytes,
)
from apps.live_control_server.integrations.dungeonmind_kernel.relationship_effective_conformance_v1 import (
    analyze_relationship_effective_conformance_v1,
)
from apps.live_control_server.integrations.dungeonmind_kernel.whole_world_conformance import (
    enumerate_durable_element_ids,
    snapshot_world_graph_tree_digest,
)
from apps.live_control_server.integrations.dungeonmind_kernel.whole_world_conformance_v4 import (
    CURRENT_V5_TARGET,
)
from apps.live_control_server.services import (
    eldyrwild_relationship_node_kind_source_repair as repair_service,
)
from apps.live_control_server.services.cutover_whole_world_reanchor import (
    CHANGED_KIND_PATHS,
    EXPECTED_CANONICAL_RELATIONSHIP_INVENTORY,
    EXPECTED_MIGRATION_RELATIONSHIP_INVENTORY,
    MIGRATION_RESIDUAL_EDGE_IDS,
    _json_bytes,
    _projection_diff,
    _relationship_inventory_from_effective,
    snapshot_source_authority_inventory,
)
from apps.live_control_server.services.cutover_whole_world_repin_after_dm30 import (
    DUNGEONMIND_DEPENDENCY_REF,
    _git_head,
    _is_descendant,
)


CUTOVER_SCHEMA = "dmb_cutover_relationship_dual_sense_decomposition_after_alias_package_v1"
DISPATCH_BASE_SHA = "cc5dc6ddba0750924a46cf13843498c124937e5f"
WORLD_ID = "eldyrwild"
CANONICAL_REVISION_ID = "rev:0c644e56b45bcaac709012206e3e41c2"
CANONICAL_GRAPH_PAYLOAD_SHA256 = (
    "0640d7ef8ce152ee4f656959e0e9a6c9c2fdf5ecc8bd721729b3019170d677f2"
)
MANIFEST_RELPATH = (
    "graph_data/approved_graph_corrections/eldyrwild/"
    "relationship-dual-sense-decomposition-v1/manifest.json"
)
LOCKED_PACKAGE_SHA256 = (
    "53986158ec9ad326481755f7baef9f425d973f34a65b789f96e92e3f55208ef8"
)
WIZARD_COLLEGE_NODE_ID = "loc:wizard_college"
MEAT_NETWORK_NODE_ID = "node:meat_distribution_network_session9"
REVELRY_NODE_ID = "node:hempholm_folk_revelry"
EXACT_SOURCE_NODE_IDS = (
    WIZARD_COLLEGE_NODE_ID,
    REVELRY_NODE_ID,
    MEAT_NETWORK_NODE_ID,
)

CutoverDisposition = Literal["CUTOVER_READY", "CUTOVER_NOT_READY"]
Eligibility = Literal["eligible", "ineligible", "integrity_failure"]
_INTEGRITY_CODES = frozenset(
    {
        "predecessor_manifest_tampered",
        "predecessor_authority_unattested",
        "predecessor_invalid",
        "canonical_revision_mismatch",
        "canonical_payload_mismatch",
        "stale_canonical_head",
        "decomposition_binding_unattested",
        "decomposition_binding_pin_mismatch",
        "decomposition_store_revision_mismatch",
        "dependency_pin_mismatch",
        "world_graph_mutated",
    }
)


class CutoverRelationshipDualSenseDecompositionError(RuntimeError):
    """Fail-closed current dual-sense decomposition successor error."""

    def __init__(self, message: str, *, code: str) -> None:
        super().__init__(message)
        self.code = code


class CutoverRelationshipDualSenseDecompositionStatusV1(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_: str = Field(default=CUTOVER_SCHEMA + "_status", alias="schema")
    world_id: str = WORLD_ID
    canonical_revision_id: str = CANONICAL_REVISION_ID
    eligibility: Eligibility
    reason: str | None = None
    diagnostics: list[str] = Field(default_factory=list)
    canonical_graph_payload_sha256: str | None = None


class CutoverRelationshipDualSenseDecompositionReportV1(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_: str = Field(default=CUTOVER_SCHEMA, alias="schema")
    world_id: str = WORLD_ID
    buddy_dispatch_base_sha: str
    canonical_revision_id: str
    canonical_graph_payload_sha256: str
    dungeonmind_dependency_ref: str
    predecessor_repair_manifest_sha256: str
    predecessor_repair_verified: bool
    decomposition_proof: dict[str, Any]
    package: dict[str, Any]
    package_projection: dict[str, Any]
    relationship_invariants: dict[str, Any]
    mutation_proof: dict[str, Any]
    cutover_disposition: CutoverDisposition
    next_slice_recommendation: dict[str, Any]
    diagnostics: list[str] = Field(default_factory=list)


class CutoverRelationshipDualSenseDecompositionBuildResultV1(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_: str = Field(default=CUTOVER_SCHEMA + "_build_result", alias="schema")
    world_id: str = WORLD_ID
    manifest_path: str
    package_sha256: str
    already_built: bool
    report: CutoverRelationshipDualSenseDecompositionReportV1
    diagnostics: list[str] = Field(default_factory=list)


class CutoverRelationshipDualSenseDecompositionVerifyResultV1(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_: str = Field(default=CUTOVER_SCHEMA + "_verify_result", alias="schema")
    world_id: str = WORLD_ID
    verified: bool
    manifest_path: str
    package_sha256: str | None = None
    diagnostics: list[str] = Field(default_factory=list)


def _fail(message: str, code: str) -> CutoverRelationshipDualSenseDecompositionError:
    return CutoverRelationshipDualSenseDecompositionError(message, code=code)


def _repo(repo: Path | None) -> Path:
    return (repo or repo_root()).resolve()


def _root(root: Path | None) -> Path:
    return (root or world_graph_root()).resolve()


def _manifest_path(repo: Path | None = None) -> Path:
    return _repo(repo) / MANIFEST_RELPATH


def _loaded_store_digest(store: Any) -> str:
    if not hasattr(store, "model_dump"):
        raise _fail("loaded store is not dumpable", "store_digest_failed")
    return sha256_bytes(_json_bytes(store.model_dump(mode="json", by_alias=True)))


def _open_current_canonical(root: Path) -> tuple[Any, Any, Any, str]:
    head = kernel.open_world_graph_head(root, WORLD_ID)
    if head.head_revision_id != CANONICAL_REVISION_ID:
        raise _fail(
            f"canonical head {head.head_revision_id!r} != {CANONICAL_REVISION_ID!r}",
            "stale_canonical_head",
        )
    manifest, store = whole_world_v4._load_exact_buddy_revision(
        root=root,
        world_id=WORLD_ID,
        revision_id=CANONICAL_REVISION_ID,
    )
    if manifest.revision_id != CANONICAL_REVISION_ID:
        raise _fail("canonical manifest revision pin mismatch", "canonical_revision_mismatch")
    if manifest.graph_payload_sha256 != CANONICAL_GRAPH_PAYLOAD_SHA256:
        raise _fail(
            "canonical graph payload pin mismatch",
            "canonical_payload_mismatch",
        )
    return head, manifest, store, snapshot_world_graph_tree_digest(root, WORLD_ID)


def _store_identity_snapshot(store: Any) -> dict[str, Any]:
    return {
        "node_ids": sorted(store.nodes),
        "edge_ids": sorted(store.edges),
        "node_kinds": {
            node_id: store.nodes[node_id].kind for node_id in sorted(store.nodes)
        },
    }


def compose_cutover_relationship_dual_sense_decomposition_after_alias_package(
    root: Path | None = None,
    repo: Path | None = None,
) -> CutoverRelationshipDualSenseDecompositionReportV1:
    world_root = _root(root)
    repository = _repo(repo)
    repository_head = _git_head(repository)
    if not _is_descendant(repository, DISPATCH_BASE_SHA):
        raise _fail(
            f"Buddy HEAD {repository_head} does not descend from {DISPATCH_BASE_SHA}",
            "buddy_base_mismatch",
        )
    if CURRENT_V5_TARGET.dungeonmind_dependency_ref != DUNGEONMIND_DEPENDENCY_REF:
        raise _fail("DungeonMind dependency pin mismatch", "dependency_pin_mismatch")
    if CURRENT_V5_TARGET.target_id != "current_v5":
        raise _fail("CURRENT_V5_TARGET was not selected explicitly", "dependency_pin_mismatch")

    head_before, _manifest, store, tree_before = _open_current_canonical(world_root)
    source_before = snapshot_source_authority_inventory(world_root)
    identity_before = _store_identity_snapshot(store)
    loaded_store_before = _loaded_store_digest(store)

    predecessor_path = repository / repair_service.MANIFEST_RELPATH
    predecessor_raw = predecessor_path.read_bytes()
    try:
        predecessor = predecessor_authority_from_locked_bytes(
            predecessor_raw,
            expected_sha256=repair_service.LOCKED_MANIFEST_SHA256,
        )
    except RelationshipDualSenseDecompositionError as exc:
        raise _fail(str(exc), exc.code) from exc
    if predecessor.repair_id != repair_service.REPAIR_ID:
        raise _fail("predecessor repair_id drift", "predecessor_invalid")
    if tuple(stop.node_id for stop in predecessor.stops) != EXACT_SOURCE_NODE_IDS:
        raise _fail(
            f"predecessor STOP node set drifted: {[s.node_id for s in predecessor.stops]}",
            "predecessor_invalid",
        )
    if set(predecessor.remaining_residual_edge_ids) != set(MIGRATION_RESIDUAL_EDGE_IDS):
        raise _fail(
            "predecessor remaining residuals != current migration residual pins",
            "current_residual_set_mismatch",
        )

    canonical_effective = analyze_relationship_effective_conformance_v1(
        root=world_root,
        world_id=WORLD_ID,
        revision_id=CANONICAL_REVISION_ID,
    )
    canonical_relationship = _relationship_inventory_from_effective(canonical_effective)
    if {
        key: canonical_relationship[key]
        for key in EXPECTED_CANONICAL_RELATIONSHIP_INVENTORY
    } != EXPECTED_CANONICAL_RELATIONSHIP_INVENTORY:
        raise _fail(
            "canonical effective relationship inventory mismatch",
            "canonical_relationship_mismatch",
        )

    overlay_store = repair_service._overlay_store(store)
    if enumerate_durable_element_ids(store) != enumerate_durable_element_ids(overlay_store):
        raise _fail("migration overlay changed durable element IDs", "durable_id_set_changed")
    changed_paths = _projection_diff(store, overlay_store)
    if set(changed_paths) != set(CHANGED_KIND_PATHS) or len(changed_paths) != len(
        CHANGED_KIND_PATHS
    ):
        raise _fail(
            f"migration projection changed unexpected paths: {changed_paths}",
            "projection_diff_mismatch",
        )
    overlay_effective = repair_service._effective_overlay_report(
        root=world_root,
        store=overlay_store,
    )
    migration_relationship = _relationship_inventory_from_effective(overlay_effective)
    if {
        key: migration_relationship[key]
        for key in EXPECTED_MIGRATION_RELATIONSHIP_INVENTORY
    } != EXPECTED_MIGRATION_RELATIONSHIP_INVENTORY:
        raise _fail(
            "migration overlay relationship inventory mismatch",
            "migration_relationship_mismatch",
        )
    current_residuals = set(migration_relationship["residual_edge_ids"])
    if current_residuals != set(MIGRATION_RESIDUAL_EDGE_IDS):
        raise _fail("migration overlay residual set mismatch", "migration_residual_mismatch")
    if current_residuals != set(predecessor.remaining_residual_edge_ids):
        raise _fail(
            "measured residuals != predecessor remaining STOP edges",
            "current_residual_set_mismatch",
        )

    try:
        binding = decomposition_binding_from_attested_revision(
            root=world_root,
            world_id=WORLD_ID,
            revision_id=CANONICAL_REVISION_ID,
            expected_world_id=WORLD_ID,
            expected_revision_id=CANONICAL_REVISION_ID,
            expected_graph_payload_sha256=CANONICAL_GRAPH_PAYLOAD_SHA256,
            store=store,
        )
        proof = prove_relationship_dual_sense_decomposition_v1(
            store,
            binding=binding,
            predecessor=predecessor,
            current_residual_edge_ids=current_residuals,
            target=CURRENT_V5_TARGET,
        )
    except RelationshipDualSenseDecompositionError as exc:
        raise _fail(str(exc), exc.code) from exc
    if not proof.passed:
        raise _fail("dual-sense decomposition proof failed", "package_projection_failed")
    package = proof.package
    if [row.source_node_id for row in package.decomposition_rows] != list(EXACT_SOURCE_NODE_IDS):
        raise _fail("package source identities drifted", "row_count_mismatch")
    if [row.edge_id for row in package.endpoint_assignments] != sorted(MIGRATION_RESIDUAL_EDGE_IDS):
        raise _fail("package assignments drifted from current five residuals", "assignment_set_mismatch")
    if package.package_projection.retained_regressions:
        raise _fail(
            f"retained-edge regressions: {package.package_projection.retained_regressions}",
            "package_projection_failed",
        )

    head_after = kernel.open_world_graph_head(world_root, WORLD_ID)
    tree_after = snapshot_world_graph_tree_digest(world_root, WORLD_ID)
    source_after = snapshot_source_authority_inventory(world_root)
    identity_after = _store_identity_snapshot(store)
    loaded_store_after = _loaded_store_digest(store)
    if head_after.head_revision_id != head_before.head_revision_id:
        raise _fail("canonical head changed during diagnostic", "world_graph_mutated")
    if tree_after != tree_before:
        raise _fail("World Graph tree digest changed during diagnostic", "world_graph_mutated")
    if source_after != source_before:
        raise _fail("source authority changed during diagnostic", "world_graph_mutated")
    if identity_after != identity_before:
        raise _fail("node identities/kinds changed during diagnostic", "world_graph_mutated")
    if loaded_store_after != loaded_store_before:
        raise _fail("loaded store changed during diagnostic", "world_graph_mutated")

    return CutoverRelationshipDualSenseDecompositionReportV1(
        buddy_dispatch_base_sha=DISPATCH_BASE_SHA,
        canonical_revision_id=CANONICAL_REVISION_ID,
        canonical_graph_payload_sha256=CANONICAL_GRAPH_PAYLOAD_SHA256,
        dungeonmind_dependency_ref=DUNGEONMIND_DEPENDENCY_REF,
        predecessor_repair_manifest_sha256=predecessor.manifest_sha256,
        predecessor_repair_verified=True,
        decomposition_proof={
            "passed": proof.passed,
            "package_sha256": proof.package_sha256,
            "diagnostics": list(proof.diagnostics),
            "row_count": len(package.decomposition_rows),
            "assignment_count": len(package.endpoint_assignments),
        },
        package=package.model_dump(mode="json", by_alias=True),
        package_projection=package.package_projection.model_dump(mode="json", by_alias=True),
        relationship_invariants={
            "canonical": canonical_relationship,
            "migration": migration_relationship,
            "authoritative_residual_edge_ids": sorted(MIGRATION_RESIDUAL_EDGE_IDS),
            "package_does_not_relabel_authoritative_state": True,
        },
        mutation_proof={
            "head_before": head_before.head_revision_id,
            "head_after": head_after.head_revision_id,
            "tree_before": tree_before,
            "tree_after": tree_after,
            "loaded_store_before": loaded_store_before,
            "loaded_store_after": loaded_store_after,
            "source_authority_before": source_before,
            "source_authority_after": source_after,
            "identity_before": identity_before,
            "identity_after": identity_after,
            "head_unchanged": True,
            "tree_unchanged": True,
            "loaded_store_unchanged": True,
            "source_authority_unchanged": True,
            "node_ids_unchanged": True,
            "node_kinds_unchanged": True,
            "edges_unchanged": True,
        },
        cutover_disposition="CUTOVER_NOT_READY",
        next_slice_recommendation={
            "owner": "DungeonMind",
            "capability": (
                "durable relationship-aspect materialization / "
                "adopt-existing-world of dmb_relationship_dual_sense_decomposition_v1"
            ),
            "case": "NOT_CASE_B",
            "reason": (
                "Buddy now has a lossless decomposition package; durable "
                "DungeonMind materialization still does not exist. The five "
                "relationship STOPs remain authoritative."
            ),
        },
        diagnostics=[
            "non_publishing",
            "package_projection_passed",
            "authoritative_migration_residuals_unchanged",
            "no_whole_world_classifier_override",
            "no_synthetic_buddy_node_ids",
        ],
    )


def get_cutover_relationship_dual_sense_decomposition_after_alias_package_status(
    root: Path | None = None,
    repo: Path | None = None,
) -> CutoverRelationshipDualSenseDecompositionStatusV1:
    try:
        report = compose_cutover_relationship_dual_sense_decomposition_after_alias_package(
            root, repo
        )
    except CutoverRelationshipDualSenseDecompositionError as exc:
        eligibility: Eligibility = (
            "integrity_failure" if exc.code in _INTEGRITY_CODES else "ineligible"
        )
        return CutoverRelationshipDualSenseDecompositionStatusV1(
            eligibility=eligibility,
            reason=str(exc),
            diagnostics=[exc.code],
        )
    return CutoverRelationshipDualSenseDecompositionStatusV1(
        eligibility="eligible",
        canonical_graph_payload_sha256=report.canonical_graph_payload_sha256,
        diagnostics=list(report.diagnostics),
    )


def build_cutover_relationship_dual_sense_decomposition_after_alias_package(
    *,
    root: Path | None = None,
    repo: Path | None = None,
    allow_live_world: bool = False,
) -> CutoverRelationshipDualSenseDecompositionBuildResultV1:
    del allow_live_world
    repository = _repo(repo)
    report = compose_cutover_relationship_dual_sense_decomposition_after_alias_package(
        root, repository
    )
    package = DualSenseDecompositionPackageV1.model_validate(report.package)
    raw = package_canonical_bytes(package)
    package_sha = sha256_bytes(raw)
    path = _manifest_path(repository)
    diagnostics = list(report.diagnostics)
    locked = LOCKED_PACKAGE_SHA256.strip()
    if locked and package_sha != locked:
        raise _fail("sealed package digest mismatch", "package_digest_mismatch")
    if not locked:
        diagnostics.append("first_seal_unlocked")
    if path.is_file():
        existing = path.read_bytes()
        if existing != raw:
            raise _fail(
                "existing decomposition manifest bytes differ; refuse overwrite",
                "package_overwrite_refused",
            )
        diagnostics.append("already_built")
        return CutoverRelationshipDualSenseDecompositionBuildResultV1(
            manifest_path=str(path),
            package_sha256=package_sha,
            already_built=True,
            report=report,
            diagnostics=diagnostics,
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(raw)
    diagnostics.append("sealed")
    return CutoverRelationshipDualSenseDecompositionBuildResultV1(
        manifest_path=str(path),
        package_sha256=package_sha,
        already_built=False,
        report=report,
        diagnostics=diagnostics,
    )


def verify_cutover_relationship_dual_sense_decomposition_after_alias_package(
    *,
    root: Path | None = None,
    repo: Path | None = None,
) -> CutoverRelationshipDualSenseDecompositionVerifyResultV1:
    world_root = _root(root)
    repository = _repo(repo)
    path = _manifest_path(repository)
    if not path.is_file():
        return CutoverRelationshipDualSenseDecompositionVerifyResultV1(
            verified=False,
            manifest_path=str(path),
            diagnostics=["manifest_missing"],
        )
    raw = path.read_bytes()
    package_sha = sha256_bytes(raw)
    locked = LOCKED_PACKAGE_SHA256.strip()
    diagnostics: list[str] = []
    if locked and package_sha != locked:
        return CutoverRelationshipDualSenseDecompositionVerifyResultV1(
            verified=False,
            manifest_path=str(path),
            package_sha256=package_sha,
            diagnostics=["package_digest_mismatch"],
        )
    if not locked:
        diagnostics.append("first_seal_unlocked")
    try:
        stored = DualSenseDecompositionPackageV1.model_validate(json.loads(raw))
        reproduced_report = (
            compose_cutover_relationship_dual_sense_decomposition_after_alias_package(
                world_root, repository
            )
        )
        reproduced = DualSenseDecompositionPackageV1.model_validate(
            reproduced_report.package
        )
        if package_canonical_bytes(stored) != package_canonical_bytes(reproduced):
            return CutoverRelationshipDualSenseDecompositionVerifyResultV1(
                verified=False,
                manifest_path=str(path),
                package_sha256=package_sha,
                diagnostics=[*diagnostics, "package_bytes_not_deterministic"],
            )
    except (CutoverRelationshipDualSenseDecompositionError, ValueError, json.JSONDecodeError) as exc:
        return CutoverRelationshipDualSenseDecompositionVerifyResultV1(
            verified=False,
            manifest_path=str(path),
            package_sha256=package_sha,
            diagnostics=[*diagnostics, f"verify_failed:{type(exc).__name__}"],
        )
    return CutoverRelationshipDualSenseDecompositionVerifyResultV1(
        verified=True,
        manifest_path=str(path),
        package_sha256=package_sha,
        diagnostics=[*diagnostics, "verified"],
    )
