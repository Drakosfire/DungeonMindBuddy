"""Post-DM#30 CUTOVER whole-world re-pin.

Diagnostic/compositional successor to the #568 re-anchor. Re-analyzes the same
Eldyrwild canonical revision and #566 four-kind migration overlay against
DungeonMind world-object-v5 / world-property-v3, proves historical #568
reproduction, and seals a new deterministic fixture. Does not mutate World Graph
or source authority.
"""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Literal

import graph_memory.kernel as kernel
from pydantic import BaseModel, ConfigDict, Field

from apps.live_control_server.config import repo_root, world_graph_root
from apps.live_control_server.integrations.dungeonmind_kernel import (
    whole_world_conformance_v4 as whole_world_v4,
)
from apps.live_control_server.integrations.dungeonmind_kernel import (
    whole_world_conformance_v5 as whole_world_v5,
)
from apps.live_control_server.integrations.dungeonmind_kernel.relationship_effective_conformance_v1 import (
    analyze_relationship_effective_conformance_v1,
)
from apps.live_control_server.integrations.dungeonmind_kernel.whole_world_conformance import (
    BlockerClass,
    DurableAdoptionSeamStatusReport,
    enumerate_durable_element_ids,
    snapshot_world_graph_tree_digest,
)
from apps.live_control_server.integrations.dungeonmind_kernel.whole_world_conformance_v4 import (
    CURRENT_V5_TARGET,
    HISTORICAL_V4_TARGET,
)
from apps.live_control_server.services import (
    eldyrwild_relationship_node_kind_source_repair as repair_service,
)
from apps.live_control_server.services.cutover_whole_world_reanchor import (
    CANONICAL_RESIDUAL_EDGE_IDS,
    CHANGED_KIND_PATHS,
    EXPECTED_CANONICAL_RELATIONSHIP_INVENTORY,
    EXPECTED_MIGRATION_RELATIONSHIP_INVENTORY,
    MIGRATION_NEWLY_REPRESENTED_EDGE_IDS,
    MIGRATION_RESIDUAL_EDGE_IDS,
    _blocker_carry_forward,
    _json_bytes,
    _next_slice_recommendation,
    _non_relationship_inventory,
    _normalized_blockers_for_view,
    _projection_delta,
    _projection_diff,
    _raw_blocker_classes,
    _relationship_inventory_from_effective,
    _relationship_inventory_from_repair_proof,
    _sha256_bytes,
    snapshot_source_authority_inventory,
    verify_cutover_whole_world_reanchor,
)


CUTOVER_SCHEMA = "dmb_cutover_whole_world_repin_after_dm30_v1"
WORLD_ID = "eldyrwild"
CANONICAL_REVISION_ID = "rev:5a7c13ae45c49a65b402920499be72ed"
CANONICAL_GRAPH_PAYLOAD_SHA256 = (
    "2632870ef70638969503de788cfdec97acd490875deff3e2630ac91dc96fe974"
)
BUDDY_BASE_SHA = "e5aaaf1d3d1e1e9f8c07a62383770dfd8326f259"
LOCKED_REPAIR_MANIFEST_SHA256 = (
    "96cc26fc6e99448e8fba5cd6982070c1e29bb058f2b1e8a4ac291f8a0a083247"
)
DUNGEONMIND_DEPENDENCY_REF = "be76acc997c5fbcb8ceaa090969ec051afa6051d"
HISTORICAL_DUNGEONMIND_DEPENDENCY_REF = (
    "2e4fdc51f91c5c2a428500f7c2ece0d6742d04b4"
)
HISTORICAL_FIXTURE_RELPATH = (
    "tests/fixtures/dungeonmind_kernel/"
    "eldyrwild_cutover_reanchor_after_566_v1.json"
)
HISTORICAL_FIXTURE_SHA256 = (
    "6c978f89527ccd82e9bad32eac70a5386a5d714e80f7e426f574d7dbc0e43cbf"
)
FIXTURE_RELPATH = (
    "tests/fixtures/dungeonmind_kernel/"
    "eldyrwild_cutover_repin_after_dm30_v1.json"
)
# Empty until first seal; nonempty enforces exact match thereafter.
LOCKED_FIXTURE_SHA256 = (
    "cf44b403b2686bc4cfbdee4d3a96252b3d4f1c071384f8a95dc2ebb1937e1b13"
)

CutoverDisposition = Literal["CUTOVER_READY", "CUTOVER_NOT_READY"]
Eligibility = Literal["eligible", "ineligible", "integrity_failure"]


class CutoverWholeWorldRepinAfterDm30Error(RuntimeError):
    """Fail-closed CUTOVER re-pin error."""

    def __init__(self, message: str, *, code: str) -> None:
        super().__init__(message)
        self.code = code


class CutoverWholeWorldRepinAfterDm30StatusV1(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_: str = Field(default=CUTOVER_SCHEMA + "_status", alias="schema")
    world_id: str = WORLD_ID
    canonical_revision_id: str = CANONICAL_REVISION_ID
    eligibility: Eligibility
    reason: str | None = None
    diagnostics: list[str] = Field(default_factory=list)
    canonical_graph_payload_sha256: str | None = None
    repair_manifest_sha256: str | None = None
    adoption_seam: DurableAdoptionSeamStatusReport | None = None


class CutoverWholeWorldRepinAfterDm30ReportV1(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_: str = Field(default=CUTOVER_SCHEMA, alias="schema")
    world_id: str = WORLD_ID
    buddy_repository_base_sha: str
    canonical_revision_id: str
    canonical_graph_payload_sha256: str
    dungeonmind_dependency_ref: str
    dungeonmind_contract_pins: dict[str, str]
    repair_authority: dict[str, Any]
    canonical_view: dict[str, Any]
    migration_projection: dict[str, Any]
    projection_delta: dict[str, Any]
    blocker_carry_forward: dict[str, Any]
    target_contract_delta: dict[str, Any]
    historical_reproduction: dict[str, Any]
    adoption_seam: DurableAdoptionSeamStatusReport
    cutover_disposition: CutoverDisposition
    next_slice_recommendation: dict[str, Any]
    diagnostics: list[str] = Field(default_factory=list)


class CutoverWholeWorldRepinAfterDm30BuildResultV1(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_: str = Field(default=CUTOVER_SCHEMA + "_build_result", alias="schema")
    world_id: str = WORLD_ID
    fixture_path: str
    fixture_sha256: str
    report: CutoverWholeWorldRepinAfterDm30ReportV1
    diagnostics: list[str] = Field(default_factory=list)


class CutoverWholeWorldRepinAfterDm30VerifyResultV1(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_: str = Field(default=CUTOVER_SCHEMA + "_verify_result", alias="schema")
    world_id: str = WORLD_ID
    verified: bool
    fixture_path: str
    fixture_sha256: str | None = None
    diagnostics: list[str] = Field(default_factory=list)


def _repo(repo: Path | None) -> Path:
    return (repo or repo_root()).resolve()


def _root(root: Path | None) -> Path:
    return (root or world_graph_root()).resolve()


def _fixture_path(repo: Path | None = None) -> Path:
    return _repo(repo) / FIXTURE_RELPATH


def _historical_fixture_path(repo: Path | None = None) -> Path:
    return _repo(repo) / HISTORICAL_FIXTURE_RELPATH


def _fail(message: str, code: str) -> CutoverWholeWorldRepinAfterDm30Error:
    return CutoverWholeWorldRepinAfterDm30Error(message, code=code)


def _git_head(repo: Path) -> str:
    try:
        result = subprocess.run(
            ["git", "-C", str(repo), "rev-parse", "--verify", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        raise _fail(f"could not inspect Buddy repository HEAD: {exc}", "buddy_git_unavailable")
    return result.stdout.strip()


def _is_descendant(repo: Path, ancestor: str) -> bool:
    try:
        result = subprocess.run(
            ["git", "-C", str(repo), "merge-base", "--is-ancestor", ancestor, "HEAD"],
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError:
        return False
    return result.returncode == 0


def _contract_pins() -> dict[str, str]:
    return {
        "graph_schema": "dm_union_graph_v5",
        "world_object_vocabulary": "world-object-v5",
        "world_object_vocabulary_sha256": (
            "f9fd5420e0ab3849224e0d58cf83dd432ca2e5da22ce661b25654406ec9c60d8"
        ),
        "world_property_vocabulary": "world-property-v3",
        "world_property_vocabulary_sha256": (
            "aa94df78c10a913e7ca6774198f080131f8f447c90cc917b9b840ed88bd856e4"
        ),
        "semantic_profile": "dnd5e-profile-v3",
        "semantic_profile_descriptor_sha256": (
            "2199e8fb96e917c22718e6aec59cbbf55a37ee81575e1bcf16ce13fae0393496"
        ),
        "source_artifact_contract": "dm_source_artifact_v2",
        "evidence_contract": "dm_evidence_ref_v2",
        "knowledge_assertion_metadata": "dm_knowledge_assertion_metadata_v1",
    }


def _historical_contract_pins() -> dict[str, str]:
    return {
        "graph_schema": "dm_union_graph_v5",
        "world_object_vocabulary": "world-object-v4",
        "world_object_vocabulary_sha256": (
            "552c59a3fa9a20e437294d1a77974c05e37b69ec95e5ea03337a7d010e4d287b"
        ),
        "world_property_vocabulary": "world-property-v2",
        "world_property_vocabulary_sha256": (
            "8ad4c223e83ce48cf5cd33a33e10f5be5d48a80ad742784d7c561470b450ab73"
        ),
        "semantic_profile": "dnd5e-profile-v3",
        "semantic_profile_descriptor_sha256": (
            "2199e8fb96e917c22718e6aec59cbbf55a37ee81575e1bcf16ce13fae0393496"
        ),
        "source_artifact_contract": "dm_source_artifact_v2",
        "evidence_contract": "dm_evidence_ref_v2",
        "knowledge_assertion_metadata": "dm_knowledge_assertion_metadata_v1",
    }


def _verify_contract_pins(report: Any) -> None:
    expected = _contract_pins()
    observed = {
        "graph_schema": report.target_graph_schema,
        "world_object_vocabulary": report.world_object_vocabulary_revision,
        "world_object_vocabulary_sha256": report.world_object_vocabulary_sha256,
        "world_property_vocabulary": report.world_property_vocabulary_revision,
        "world_property_vocabulary_sha256": report.world_property_vocabulary_sha256,
        "semantic_profile": report.semantic_profile_revision,
        "semantic_profile_descriptor_sha256": report.semantic_profile_descriptor_sha256,
        "source_artifact_contract": report.source_artifact_schema,
        "evidence_contract": report.evidence_schema,
        "knowledge_assertion_metadata": report.assertion_metadata_schema,
    }
    if observed != expected:
        raise _fail(
            "DungeonMind contract pins differ from the locked CUTOVER v5 contract",
            "contract_pin_mismatch",
        )
    if report.dungeonmind_dependency_ref != DUNGEONMIND_DEPENDENCY_REF:
        raise _fail("DungeonMind dependency pin mismatch", "dependency_pin_mismatch")


def _verify_historical_contract_pins(report: Any) -> None:
    expected = _historical_contract_pins()
    observed = {
        "graph_schema": report.target_graph_schema,
        "world_object_vocabulary": report.world_object_vocabulary_revision,
        "world_object_vocabulary_sha256": report.world_object_vocabulary_sha256,
        "world_property_vocabulary": report.world_property_vocabulary_revision,
        "world_property_vocabulary_sha256": report.world_property_vocabulary_sha256,
        "semantic_profile": report.semantic_profile_revision,
        "semantic_profile_descriptor_sha256": report.semantic_profile_descriptor_sha256,
        "source_artifact_contract": report.source_artifact_schema,
        "evidence_contract": report.evidence_schema,
        "knowledge_assertion_metadata": report.assertion_metadata_schema,
    }
    if observed != expected:
        raise _fail(
            "Historical DungeonMind v4 contract pins drifted under CURRENT dependency",
            "historical_contract_pin_mismatch",
        )
    if report.dungeonmind_dependency_ref != HISTORICAL_DUNGEONMIND_DEPENDENCY_REF:
        raise _fail(
            "Historical DungeonMind dependency pin mismatch",
            "historical_dependency_pin_mismatch",
        )


def _open_exact_canonical(
    root: Path,
) -> tuple[Any, Any, Any, str]:
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
    tree_digest = snapshot_world_graph_tree_digest(root, WORLD_ID)
    return head, manifest, store, tree_digest


def _verify_repair_authority(root: Path, repo: Path) -> tuple[Any, Any]:
    manifest_path = repo / repair_service.MANIFEST_RELPATH
    if not manifest_path.is_file():
        raise _fail("PR #566 repair manifest is missing", "repair_manifest_missing")
    manifest_sha = _sha256_bytes(manifest_path.read_bytes())
    if manifest_sha != LOCKED_REPAIR_MANIFEST_SHA256:
        raise _fail("PR #566 repair manifest digest mismatch", "repair_manifest_mismatch")
    pin = repair_service.verify_relationship_node_kind_source_repair(
        root=root,
        repo=repo,
    )
    if pin is None or pin.manifest_sha256 != LOCKED_REPAIR_MANIFEST_SHA256:
        raise _fail("PR #566 locked repair authority did not verify", "repair_verify_failed")
    proof = repair_service.prove_isolated_repair_effect(root=root, repo=repo)
    if not proof.passed or proof.projected_inventory != EXPECTED_MIGRATION_RELATIONSHIP_INVENTORY:
        raise _fail("PR #566 owning repair proof did not verify", "repair_proof_failed")
    migration_relationship = _relationship_inventory_from_repair_proof(proof)
    if set(migration_relationship["residual_edge_ids"]) != MIGRATION_RESIDUAL_EDGE_IDS:
        raise _fail("PR #566 proof residual set did not verify", "repair_proof_failed")
    if (
        set(migration_relationship["newly_represented_edge_ids"])
        != MIGRATION_NEWLY_REPRESENTED_EDGE_IDS
    ):
        raise _fail("PR #566 proof represented set did not verify", "repair_proof_failed")
    return pin, proof


def _copy_manifest(manifest: Any) -> Any:
    if hasattr(manifest, "model_copy"):
        return manifest.model_copy(deep=True)
    raise _fail("canonical manifest is not copyable", "manifest_copy_failed")


def _whole_world_digest(report: Any, *, target: Literal["v4", "v5"]) -> str:
    if target == "v5":
        compact = whole_world_v5.compact_whole_world_conformance_report_v5(report)
    else:
        compact = whole_world_v4.compact_whole_world_conformance_report_v4(report)
    return _sha256_bytes(_json_bytes(compact))


def _view(
    *,
    whole_world_report: Any,
    relationship_inventory: dict[str, Any],
    blockers: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "whole_world_report_digest": _whole_world_digest(whole_world_report, target="v5"),
        "durable_inventory": _non_relationship_inventory(whole_world_report),
        "relationship_inventory": relationship_inventory,
        "relationship_residual_edge_ids": relationship_inventory["residual_edge_ids"],
        "blockers": blockers,
        "unaccounted_durable_elements": whole_world_report.unaccounted_durable_elements,
    }


def _blocker_ledger_map(blockers: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {
        blocker["blocker_class"]: {
            "count": blocker["count"],
            "examples": list(blocker.get("examples", [])),
            "blocking_stage": blocker.get("blocking_stage"),
            "ownership_scope": blocker.get("ownership_scope"),
            "responsible_repo": blocker.get("responsible_repo"),
        }
        for blocker in blockers
    }


def _compare_blocker_ledgers(
    *,
    view: str,
    previous_blockers: list[dict[str, Any]],
    current_blockers: list[dict[str, Any]],
) -> tuple[list[str], list[dict[str, Any]]]:
    previous_map = _blocker_ledger_map(previous_blockers)
    current_map = _blocker_ledger_map(current_blockers)
    cleared = sorted(set(previous_map) - set(current_map))
    changed: list[dict[str, Any]] = []
    for blocker_class in sorted(set(previous_map) & set(current_map)):
        if previous_map[blocker_class] == current_map[blocker_class]:
            continue
        prev = previous_map[blocker_class]
        curr = current_map[blocker_class]
        representative = sorted(
            set(prev.get("examples", [])) | set(curr.get("examples", []))
        )[:10]
        note = (
            "Remeasured under CURRENT_V5_TARGET after DungeonMind PR #30; "
            "counts are analyzer outputs, not carried forward from #568."
        )
        if (
            blocker_class == BlockerClass.ATTRIBUTE_ASSERTION.value
            and prev.get("count") == 29
            and curr.get("count") == 28
        ):
            # Same node that cleared WORLD_OBJECT_KIND; role was blocked only
            # because the kind was unmapped under historical v4.
            thread_role_id = (
                "node:mystery:session25:light-and-sound-as-search-tools-"
                "during-night-response:field:role"
            )
            representative = [thread_role_id, *representative][:10]
            note = (
                "ATTRIBUTE_ASSERTION 29→28 because Buddy role on kind 'thread' "
                f"({thread_role_id}) becomes representable once PR #30 maps "
                "thread→dnd5e:thread and world-property-v3 admits dnd5e:role "
                "on that subject kind."
            )
        changed.append(
            {
                "view": view,
                "blocker_class": blocker_class,
                "previous": prev,
                "current": curr,
                "representative_durable_ids": representative,
                "note": note,
            }
        )
    for blocker_class in cleared:
        prev = previous_map[blocker_class]
        changed.append(
            {
                "view": view,
                "blocker_class": blocker_class,
                "previous": prev,
                "current": None,
                "representative_durable_ids": list(prev.get("examples", []))[:10],
                "note": (
                    "Cleared under CURRENT_V5_TARGET (DungeonMind PR #30 "
                    "world-object-v5 / world-property-v3)."
                ),
            }
        )
    for blocker_class in sorted(set(current_map) - set(previous_map)):
        curr = current_map[blocker_class]
        changed.append(
            {
                "view": view,
                "blocker_class": blocker_class,
                "previous": None,
                "current": curr,
                "representative_durable_ids": list(curr.get("examples", []))[:10],
                "note": "Newly present under CURRENT_V5_TARGET relative to historical v4.",
            }
        )
    return cleared, changed


def _build_target_contract_delta(
    *,
    historical_canonical: Any,
    historical_migration: Any,
    current_canonical: Any,
    current_migration: Any,
    historical_canonical_blockers: list[dict[str, Any]],
    historical_migration_blockers: list[dict[str, Any]],
    current_canonical_blockers: list[dict[str, Any]],
    current_migration_blockers: list[dict[str, Any]],
) -> dict[str, Any]:
    cleared_canonical, changed_canonical = _compare_blocker_ledgers(
        view="canonical",
        previous_blockers=historical_canonical_blockers,
        current_blockers=current_canonical_blockers,
    )
    cleared_migration, changed_migration = _compare_blocker_ledgers(
        view="migration",
        previous_blockers=historical_migration_blockers,
        current_blockers=current_migration_blockers,
    )
    historical_kind = set(HISTORICAL_V4_TARGET.buddy_to_dm_kind)
    current_kind = set(CURRENT_V5_TARGET.buddy_to_dm_kind)
    kind_delta = {
        key: CURRENT_V5_TARGET.buddy_to_dm_kind[key]
        for key in sorted(current_kind - historical_kind)
    }
    if kind_delta != {"thread": "dnd5e:thread"}:
        raise _fail(
            f"unexpected Buddy→DM kind map delta: {kind_delta}",
            "kind_map_delta_mismatch",
        )
    if historical_kind - current_kind:
        raise _fail(
            "historical Buddy→DM kinds missing from CURRENT_V5_TARGET",
            "kind_map_delta_mismatch",
        )
    return {
        "previous": {
            "dungeonmind_dependency_ref": HISTORICAL_DUNGEONMIND_DEPENDENCY_REF,
            "world_object_revision": "world-object-v4",
            "world_object_sha256": (
                "552c59a3fa9a20e437294d1a77974c05e37b69ec95e5ea03337a7d010e4d287b"
            ),
            "world_property_revision": "world-property-v2",
            "world_property_sha256": (
                "8ad4c223e83ce48cf5cd33a33e10f5be5d48a80ad742784d7c561470b450ab73"
            ),
            "target_id": HISTORICAL_V4_TARGET.target_id,
        },
        "current": {
            "dungeonmind_dependency_ref": DUNGEONMIND_DEPENDENCY_REF,
            "world_object_revision": "world-object-v5",
            "world_object_sha256": (
                "f9fd5420e0ab3849224e0d58cf83dd432ca2e5da22ce661b25654406ec9c60d8"
            ),
            "world_property_revision": "world-property-v3",
            "world_property_sha256": (
                "aa94df78c10a913e7ca6774198f080131f8f447c90cc917b9b840ed88bd856e4"
            ),
            "target_id": CURRENT_V5_TARGET.target_id,
        },
        "source_kind_mapping_delta": kind_delta,
        "historical_whole_world_digests": {
            "canonical": _whole_world_digest(historical_canonical, target="v4"),
            "migration": _whole_world_digest(historical_migration, target="v4"),
        },
        "current_whole_world_digests": {
            "canonical": _whole_world_digest(current_canonical, target="v5"),
            "migration": _whole_world_digest(current_migration, target="v5"),
        },
        "cleared_blocker_classes": sorted(set(cleared_canonical) | set(cleared_migration)),
        "changed_blockers": changed_canonical + changed_migration,
    }


def _prove_historical_reproduction(root: Path, repo: Path) -> dict[str, Any]:
    historical_path = _historical_fixture_path(repo)
    if not historical_path.is_file():
        raise _fail("historical #568 fixture is missing", "historical_fixture_missing")
    historical_sha = _sha256_bytes(historical_path.read_bytes())
    if historical_sha != HISTORICAL_FIXTURE_SHA256:
        raise _fail(
            "historical #568 fixture digest mismatch",
            "historical_fixture_digest_mismatch",
        )
    verified = verify_cutover_whole_world_reanchor(root=root, repo=repo)
    if not verified.verified or verified.fixture_sha256 != HISTORICAL_FIXTURE_SHA256:
        raise _fail(
            "historical #568 CUTOVER fixture did not reproduce under CURRENT dependency",
            "historical_reproduction_failed",
        )
    return {
        "verified": True,
        "historical_fixture_relpath": HISTORICAL_FIXTURE_RELPATH,
        "historical_fixture_sha256": HISTORICAL_FIXTURE_SHA256,
        "historical_dungeonmind_dependency_ref": HISTORICAL_DUNGEONMIND_DEPENDENCY_REF,
        "analyzer_path": (
            "whole_world_v4._analyze_loaded_buddy_world_store_v4 "
            "(default HISTORICAL_V4_TARGET)"
        ),
        "note": (
            "Historical #568 verifier reproduced under the installed DungeonMind "
            "dependency because PR #30 preserves explicit historical v4/v2 loaders."
        ),
        "verify_diagnostics": list(verified.diagnostics),
    }


def _compose_report(root: Path, repo: Path) -> CutoverWholeWorldRepinAfterDm30ReportV1:
    repository_head = _git_head(repo)
    if not _is_descendant(repo, BUDDY_BASE_SHA):
        raise _fail(
            f"Buddy HEAD {repository_head} does not descend from {BUDDY_BASE_SHA}",
            "buddy_base_mismatch",
        )

    historical_reproduction = _prove_historical_reproduction(root, repo)

    head_before, manifest, base_store, tree_before = _open_exact_canonical(root)
    source_before = snapshot_source_authority_inventory(root)

    # CURRENT v5/v3 analysis (canonical + migration overlay).
    canonical_v5 = whole_world_v5._analyze_loaded_buddy_world_store_v5(
        root=root,
        world_id=WORLD_ID,
        revision_id=CANONICAL_REVISION_ID,
        manifest=manifest,
        store=base_store,
    )
    _verify_contract_pins(canonical_v5)

    # Historical v4/v2 analysis on the same loaded stores (target delta + reproduction).
    historical_canonical_v4 = whole_world_v4._analyze_loaded_buddy_world_store_v4(
        root=root,
        world_id=WORLD_ID,
        revision_id=CANONICAL_REVISION_ID,
        manifest=_copy_manifest(manifest),
        store=base_store,
    )
    _verify_historical_contract_pins(historical_canonical_v4)

    canonical_effective = analyze_relationship_effective_conformance_v1(
        root=root,
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
    if set(canonical_relationship["residual_edge_ids"]) != CANONICAL_RESIDUAL_EDGE_IDS:
        raise _fail("canonical effective residual set mismatch", "canonical_residual_mismatch")

    repair_pin, repair_proof = _verify_repair_authority(root, repo)
    overlay_store = repair_service._overlay_store(base_store)
    if enumerate_durable_element_ids(base_store) != enumerate_durable_element_ids(
        overlay_store
    ):
        raise _fail("migration overlay changed durable element IDs", "durable_id_set_changed")
    changed_paths = _projection_diff(base_store, overlay_store)
    if set(changed_paths) != set(CHANGED_KIND_PATHS) or len(changed_paths) != len(
        CHANGED_KIND_PATHS
    ):
        raise _fail(
            f"migration projection changed unexpected paths: {changed_paths}",
            "projection_diff_mismatch",
        )
    changed_paths = list(CHANGED_KIND_PATHS)
    if any("thread" in path for path in changed_paths):
        raise _fail(
            "migration projection must not change thread source kinds",
            "projection_diff_mismatch",
        )

    overlay_v5 = whole_world_v5._analyze_loaded_buddy_world_store_v5(
        root=root,
        world_id=WORLD_ID,
        revision_id=CANONICAL_REVISION_ID,
        manifest=_copy_manifest(manifest),
        store=overlay_store,
    )
    if overlay_v5.unaccounted_durable_elements != 0:
        raise _fail("migration overlay has unaccounted durable elements", "overlay_unaccounted")
    historical_overlay_v4 = whole_world_v4._analyze_loaded_buddy_world_store_v4(
        root=root,
        world_id=WORLD_ID,
        revision_id=CANONICAL_REVISION_ID,
        manifest=_copy_manifest(manifest),
        store=overlay_store,
    )
    _verify_historical_contract_pins(historical_overlay_v4)

    migration_relationship = _relationship_inventory_from_repair_proof(repair_proof)
    if {
        key: migration_relationship[key]
        for key in EXPECTED_MIGRATION_RELATIONSHIP_INVENTORY
    } != EXPECTED_MIGRATION_RELATIONSHIP_INVENTORY:
        raise _fail(
            "migration proof relationship inventory mismatch",
            "migration_relationship_mismatch",
        )
    if set(migration_relationship["residual_edge_ids"]) != MIGRATION_RESIDUAL_EDGE_IDS:
        raise _fail("migration proof residual set mismatch", "migration_residual_mismatch")

    adoption_seam = whole_world_v4.inspect_dungeonmind_durable_adoption_seam()

    canonical_classes_v5 = set(_raw_blocker_classes(canonical_v5)) | {
        BlockerClass.RELATIONSHIP_PREDICATE.value
    }
    migration_classes_v5 = set(_raw_blocker_classes(overlay_v5)) | {
        BlockerClass.RELATIONSHIP_PREDICATE.value
    }
    canonical_blockers = _normalized_blockers_for_view(
        canonical_v5,
        residual_edge_ids=canonical_relationship["residual_edge_ids"],
        projection=False,
        canonical_classes=canonical_classes_v5,
        migration_classes=migration_classes_v5,
    )
    migration_blockers = _normalized_blockers_for_view(
        overlay_v5,
        residual_edge_ids=migration_relationship["residual_edge_ids"],
        projection=True,
        canonical_classes=canonical_classes_v5,
        migration_classes=migration_classes_v5,
    )

    historical_canonical_classes = set(_raw_blocker_classes(historical_canonical_v4)) | {
        BlockerClass.RELATIONSHIP_PREDICATE.value
    }
    historical_migration_classes = set(_raw_blocker_classes(historical_overlay_v4)) | {
        BlockerClass.RELATIONSHIP_PREDICATE.value
    }
    historical_canonical_blockers = _normalized_blockers_for_view(
        historical_canonical_v4,
        residual_edge_ids=canonical_relationship["residual_edge_ids"],
        projection=False,
        canonical_classes=historical_canonical_classes,
        migration_classes=historical_migration_classes,
    )
    historical_migration_blockers = _normalized_blockers_for_view(
        historical_overlay_v4,
        residual_edge_ids=migration_relationship["residual_edge_ids"],
        projection=True,
        canonical_classes=historical_canonical_classes,
        migration_classes=historical_migration_classes,
    )

    # Fail closed if WORLD_OBJECT_KIND remains under v5 (PR #30 must clear thread).
    for view_name, blockers in (
        ("canonical", canonical_blockers),
        ("migration", migration_blockers),
    ):
        if any(
            row["blocker_class"] == BlockerClass.WORLD_OBJECT_KIND.value for row in blockers
        ):
            raise _fail(
                f"WORLD_OBJECT_KIND remains under CURRENT_V5_TARGET in {view_name}",
                "world_object_kind_not_cleared",
            )
    if not any(
        row["blocker_class"] == BlockerClass.WORLD_OBJECT_KIND.value
        for row in historical_migration_blockers
    ):
        raise _fail(
            "historical v4 migration ledger lost WORLD_OBJECT_KIND (unexpected)",
            "historical_world_object_kind_missing",
        )

    carry_forward = _blocker_carry_forward(
        canonical_report=canonical_v5,
        migration_report=overlay_v5,
        canonical_blockers=canonical_blockers,
        migration_blockers=migration_blockers,
    )
    # Note text still mentions raw RELATIONSHIP_PREDICATE replacement; keep shape.
    carry_forward = {
        **carry_forward,
        "note": (
            "Raw whole-world RELATIONSHIP_PREDICATE rows are replaced by the owning "
            "effective relationship residual ledger; all other whole-world blockers "
            "are carried under CURRENT_V5_TARGET."
        ),
    }
    canonical_view = _view(
        whole_world_report=canonical_v5,
        relationship_inventory=canonical_relationship,
        blockers=canonical_blockers,
    )
    migration_view = _view(
        whole_world_report=overlay_v5,
        relationship_inventory=migration_relationship,
        blockers=migration_blockers,
    )
    projection_delta = _projection_delta(
        canonical_view,
        migration_view,
        changed_paths,
    )
    target_contract_delta = _build_target_contract_delta(
        historical_canonical=historical_canonical_v4,
        historical_migration=historical_overlay_v4,
        current_canonical=canonical_v5,
        current_migration=overlay_v5,
        historical_canonical_blockers=historical_canonical_blockers,
        historical_migration_blockers=historical_migration_blockers,
        current_canonical_blockers=canonical_blockers,
        current_migration_blockers=migration_blockers,
    )
    if BlockerClass.WORLD_OBJECT_KIND.value not in target_contract_delta[
        "cleared_blocker_classes"
    ]:
        raise _fail(
            "target_contract_delta did not record WORLD_OBJECT_KIND clearance",
            "target_delta_incomplete",
        )

    recommendation = _next_slice_recommendation(migration_view["blockers"])
    package_construction_remains = any(
        row.get("blocking_stage") == "adoption_package_construction"
        for row in migration_view["blockers"]
    )
    if package_construction_remains and recommendation.get("case") == "CASE_B":
        raise _fail(
            "selector returned CASE_B while package-construction blockers remain",
            "recommendation_stage_violation",
        )

    disposition: CutoverDisposition = (
        "CUTOVER_READY" if not migration_view["blockers"] else "CUTOVER_NOT_READY"
    )
    diagnostics = [
        "non_publishing",
        "canonical_relationship_authority:effective_conformance",
        "migration_relationship_authority:prove_isolated_repair_effect",
        "overlay_manifest_payload_sha_reflects_canonical_pin_for_domain_matching",
        "raw_whole_world_relationship_predicate_blockers_replaced_by_owning_ledgers",
        "next_slice_derived_from_normalized_blocker_stages",
        "current_target:CURRENT_V5_TARGET",
        "historical_target:HISTORICAL_V4_TARGET",
        "historical_568_reproduction_verified",
        "world_object_kind_cleared_under_v5",
    ]
    report = CutoverWholeWorldRepinAfterDm30ReportV1(
        buddy_repository_base_sha=BUDDY_BASE_SHA,
        canonical_revision_id=manifest.revision_id,
        canonical_graph_payload_sha256=manifest.graph_payload_sha256,
        dungeonmind_dependency_ref=DUNGEONMIND_DEPENDENCY_REF,
        dungeonmind_contract_pins=_contract_pins(),
        repair_authority={
            "repair_id": repair_service.REPAIR_ID,
            "manifest_sha256": repair_pin.manifest_sha256,
            "verified": True,
            "changed_node_kind_paths": list(CHANGED_KIND_PATHS),
            "proof": {
                "passed": repair_proof.passed,
                "projected_inventory": dict(repair_proof.projected_inventory),
                "zero_regressions": repair_proof.zero_regressions,
                "diagnostics": list(repair_proof.diagnostics),
            },
        },
        canonical_view=canonical_view,
        migration_projection=migration_view,
        projection_delta=projection_delta,
        blocker_carry_forward=carry_forward,
        target_contract_delta=target_contract_delta,
        historical_reproduction=historical_reproduction,
        adoption_seam=adoption_seam,
        cutover_disposition=disposition,
        next_slice_recommendation=recommendation,
        diagnostics=diagnostics,
    )
    _assert_report_invariants(report)

    head_after = kernel.open_world_graph_head(root, WORLD_ID)
    tree_after = snapshot_world_graph_tree_digest(root, WORLD_ID)
    source_after = snapshot_source_authority_inventory(root)
    if head_after.head_revision_id != head_before.head_revision_id or tree_after != tree_before:
        raise _fail("CUTOVER analysis mutated the World Graph", "world_graph_mutated")
    if source_after != source_before:
        raise _fail(
            "CUTOVER analysis mutated source/provenance authority families",
            "source_authority_mutated",
        )
    return report


def _assert_report_invariants(report: CutoverWholeWorldRepinAfterDm30ReportV1) -> None:
    if report.canonical_revision_id != CANONICAL_REVISION_ID:
        raise _fail("report revision pin mismatch", "report_pin_mismatch")
    if report.canonical_graph_payload_sha256 != CANONICAL_GRAPH_PAYLOAD_SHA256:
        raise _fail("report payload pin mismatch", "report_pin_mismatch")
    if report.repair_authority["manifest_sha256"] != LOCKED_REPAIR_MANIFEST_SHA256:
        raise _fail("report repair manifest pin mismatch", "report_repair_pin_mismatch")
    if report.repair_authority["changed_node_kind_paths"] != list(CHANGED_KIND_PATHS):
        raise _fail("report kind path projection mismatch", "report_projection_mismatch")
    for view_name in ("canonical_view", "migration_projection"):
        view = getattr(report, view_name)
        if view["unaccounted_durable_elements"] != 0:
            raise _fail(f"{view_name} is not fully accounted", "unaccounted_durable_elements")
        if any(
            row["blocker_class"] == BlockerClass.WORLD_OBJECT_KIND.value
            for row in view["blockers"]
        ):
            raise _fail(
                f"{view_name} still contains WORLD_OBJECT_KIND",
                "world_object_kind_not_cleared",
            )
    if report.canonical_view["relationship_inventory"] != {
        **EXPECTED_CANONICAL_RELATIONSHIP_INVENTORY,
        "residual_edge_ids": sorted(CANONICAL_RESIDUAL_EDGE_IDS),
        "newly_represented_edge_ids": report.canonical_view["relationship_inventory"][
            "newly_represented_edge_ids"
        ],
        "residual_disposition_inventory": report.canonical_view[
            "relationship_inventory"
        ]["residual_disposition_inventory"],
        "authority": "dmb_dungeonmind_relationship_effective_conformance_v1",
    }:
        raise _fail("canonical relationship report shape drifted", "report_relationship_mismatch")
    migration = report.migration_projection["relationship_inventory"]
    if {
        key: migration[key] for key in EXPECTED_MIGRATION_RELATIONSHIP_INVENTORY
    } != EXPECTED_MIGRATION_RELATIONSHIP_INVENTORY:
        raise _fail("migration relationship report shape drifted", "report_relationship_mismatch")
    if migration["residual_edge_ids"] != sorted(MIGRATION_RESIDUAL_EDGE_IDS):
        raise _fail("migration residual report shape drifted", "report_relationship_mismatch")
    if report.projection_delta["changed_durable_paths"] != list(CHANGED_KIND_PATHS):
        raise _fail("projection delta path drifted", "report_projection_mismatch")
    if report.target_contract_delta["source_kind_mapping_delta"] != {
        "thread": "dnd5e:thread"
    }:
        raise _fail("kind mapping delta drifted", "kind_map_delta_mismatch")
    if not report.historical_reproduction.get("verified"):
        raise _fail("historical reproduction flag missing", "historical_reproduction_failed")
    if "aspect" in json.dumps(report.model_dump(mode="json", by_alias=True)).lower():
        raise _fail("report contains forbidden aspect identity materialization", "aspect_materialization")


def _report_bytes(report: CutoverWholeWorldRepinAfterDm30ReportV1) -> bytes:
    return _json_bytes(report.model_dump(mode="json", by_alias=True))


def get_cutover_whole_world_repin_after_dm30_status(
    root: Path | None = None,
    *,
    repo: Path | None = None,
) -> CutoverWholeWorldRepinAfterDm30StatusV1:
    world_root = _root(root)
    repository = _repo(repo)
    diagnostics: list[str] = []
    try:
        head = _git_head(repository)
        if not _is_descendant(repository, BUDDY_BASE_SHA):
            diagnostics.append("buddy_base_mismatch")
        manifest_path = repository / repair_service.MANIFEST_RELPATH
        manifest_sha = (
            _sha256_bytes(manifest_path.read_bytes()) if manifest_path.is_file() else None
        )
        if manifest_sha != LOCKED_REPAIR_MANIFEST_SHA256:
            diagnostics.append("repair_manifest_mismatch")
        current_dep = (
            getattr(whole_world_v4, "_DUNGEONMIND_DEPENDENCY_REF_V5", None)
            or CURRENT_V5_TARGET.dungeonmind_dependency_ref
        )
        if current_dep != DUNGEONMIND_DEPENDENCY_REF:
            diagnostics.append("dependency_pin_mismatch")
        historical_path = _historical_fixture_path(repository)
        if not historical_path.is_file():
            diagnostics.append("historical_fixture_missing")
        elif _sha256_bytes(historical_path.read_bytes()) != HISTORICAL_FIXTURE_SHA256:
            diagnostics.append("historical_fixture_digest_mismatch")
        graph_manifest = kernel.load_world_graph_revision_manifest(
            world_root,
            WORLD_ID,
            CANONICAL_REVISION_ID,
        )
        if graph_manifest.graph_payload_sha256 != CANONICAL_GRAPH_PAYLOAD_SHA256:
            diagnostics.append("canonical_payload_mismatch")
        head_revision = kernel.open_world_graph_head(world_root, WORLD_ID).head_revision_id
        if head_revision != CANONICAL_REVISION_ID:
            diagnostics.append("stale_canonical_head")
        repair_pin = repair_service.verify_relationship_node_kind_source_repair(
            root=world_root,
            repo=repository,
        )
        if repair_pin is None:
            diagnostics.append("repair_verify_failed")
        seam = whole_world_v4.inspect_dungeonmind_durable_adoption_seam()
        if diagnostics:
            return CutoverWholeWorldRepinAfterDm30StatusV1(
                eligibility="ineligible",
                reason="exact CUTOVER re-pin activation pins do not hold",
                diagnostics=diagnostics,
                canonical_graph_payload_sha256=getattr(
                    graph_manifest, "graph_payload_sha256", None
                ),
                repair_manifest_sha256=manifest_sha,
                adoption_seam=seam,
            )
        return CutoverWholeWorldRepinAfterDm30StatusV1(
            eligibility="eligible",
            reason="exact post-DM#30 CUTOVER re-pin activation pins hold",
            diagnostics=["status_ok", "buddy_head_observed:" + head, *diagnostics],
            canonical_graph_payload_sha256=graph_manifest.graph_payload_sha256,
            repair_manifest_sha256=manifest_sha,
            adoption_seam=seam,
        )
    except Exception as exc:  # noqa: BLE001
        diagnostics.append(type(exc).__name__ + ":" + str(exc))
        return CutoverWholeWorldRepinAfterDm30StatusV1(
            eligibility="integrity_failure",
            reason="CUTOVER re-pin activation diagnostics failed closed",
            diagnostics=diagnostics,
        )


def build_cutover_whole_world_repin_after_dm30(
    *,
    root: Path | None = None,
    repo: Path | None = None,
    allow_live_world: bool = False,
) -> CutoverWholeWorldRepinAfterDm30BuildResultV1:
    """Build the deterministic repository fixture without mutating the graph."""
    del allow_live_world
    world_root = _root(root)
    repository = _repo(repo)
    # Never touch the historical #568 fixture path.
    historical_path = _historical_fixture_path(repository)
    historical_before = (
        _sha256_bytes(historical_path.read_bytes()) if historical_path.is_file() else None
    )

    report = _compose_report(world_root, repository)
    raw = _report_bytes(report)
    fixture_sha = _sha256_bytes(raw)
    locked = LOCKED_FIXTURE_SHA256.strip()
    if locked and fixture_sha != locked:
        raise _fail(
            "generated CUTOVER re-pin fixture digest does not match locked digest",
            "fixture_digest_mismatch",
        )
    path = _fixture_path(repository)
    diagnostics = ["non_publishing"]
    if path.is_file():
        existing_sha = _sha256_bytes(path.read_bytes())
        if existing_sha != fixture_sha:
            raise _fail(
                "existing CUTOVER re-pin fixture differs from generated bytes; refuse overwrite",
                "locked_fixture_overwrite_refused",
            )
        if historical_path.is_file() and historical_before is not None:
            if _sha256_bytes(historical_path.read_bytes()) != historical_before:
                raise _fail(
                    "build mutated historical #568 fixture",
                    "historical_fixture_mutated",
                )
        if not locked:
            diagnostics.extend(["already_built", "first_seal_unlocked"])
        else:
            diagnostics.append("already_built")
        return CutoverWholeWorldRepinAfterDm30BuildResultV1(
            fixture_path=str(path),
            fixture_sha256=fixture_sha,
            report=report,
            diagnostics=diagnostics,
        )

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
        raise _fail(
            f"atomic CUTOVER re-pin fixture write failed: {exc}",
            "fixture_write_failed",
        ) from exc

    if historical_path.is_file() and historical_before is not None:
        if _sha256_bytes(historical_path.read_bytes()) != historical_before:
            raise _fail(
                "build mutated historical #568 fixture",
                "historical_fixture_mutated",
            )

    if not locked:
        diagnostics.extend(["fixture_written_atomically", "first_seal_unlocked"])
    else:
        diagnostics.extend(["fixture_written_atomically", "first_seal"])
    return CutoverWholeWorldRepinAfterDm30BuildResultV1(
        fixture_path=str(path),
        fixture_sha256=fixture_sha,
        report=report,
        diagnostics=diagnostics,
    )


def verify_cutover_whole_world_repin_after_dm30(
    *,
    root: Path | None = None,
    repo: Path | None = None,
) -> CutoverWholeWorldRepinAfterDm30VerifyResultV1:
    """Reload the fixture and independently reproduce its report bytes."""
    world_root = _root(root)
    repository = _repo(repo)
    path = _fixture_path(repository)
    if not path.is_file():
        return CutoverWholeWorldRepinAfterDm30VerifyResultV1(
            verified=False,
            fixture_path=str(path),
            diagnostics=["fixture_missing"],
        )
    raw = path.read_bytes()
    fixture_sha = _sha256_bytes(raw)
    locked = LOCKED_FIXTURE_SHA256.strip()
    diagnostics: list[str] = []
    if locked:
        if fixture_sha != locked:
            return CutoverWholeWorldRepinAfterDm30VerifyResultV1(
                verified=False,
                fixture_path=str(path),
                fixture_sha256=fixture_sha,
                diagnostics=["fixture_digest_mismatch"],
            )
    else:
        diagnostics.append("first_seal_unlocked")
    try:
        stored = CutoverWholeWorldRepinAfterDm30ReportV1.model_validate(json.loads(raw))
        reproduced = _compose_report(world_root, repository)
        if _report_bytes(stored) != _report_bytes(reproduced):
            return CutoverWholeWorldRepinAfterDm30VerifyResultV1(
                verified=False,
                fixture_path=str(path),
                fixture_sha256=fixture_sha,
                diagnostics=[*diagnostics, "fixture_bytes_not_deterministic"],
            )
        _assert_report_invariants(reproduced)
    except (CutoverWholeWorldRepinAfterDm30Error, OSError, ValueError, TypeError) as exc:
        return CutoverWholeWorldRepinAfterDm30VerifyResultV1(
            verified=False,
            fixture_path=str(path),
            fixture_sha256=fixture_sha,
            diagnostics=[*diagnostics, type(exc).__name__ + ":" + str(exc)],
        )
    return CutoverWholeWorldRepinAfterDm30VerifyResultV1(
        verified=True,
        fixture_path=str(path),
        fixture_sha256=fixture_sha,
        diagnostics=[*diagnostics, "verified", "non_publishing"],
    )
