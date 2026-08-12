"""Post-#566 CUTOVER whole-world re-anchor.

This module is diagnostic and compositional.  It reads the exact canonical
Eldyrwild revision, verifies the sealed PR #566 migration authority, analyzes a
four-kind in-memory overlay, and writes only the deterministic report fixture.
It has no World Graph publication path and does not create identities or
resolve the five dual-sense residual edges.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Literal, Mapping

import graph_memory.kernel as kernel
from pydantic import BaseModel, ConfigDict, Field

from apps.live_control_server.config import repo_root, world_graph_root
from apps.live_control_server.integrations.dungeonmind_kernel import (
    whole_world_conformance_v4 as whole_world_v4,
)
from apps.live_control_server.integrations.dungeonmind_kernel.relationship_effective_conformance_v1 import (
    analyze_relationship_effective_conformance_v1,
)
from apps.live_control_server.integrations.dungeonmind_kernel.whole_world_conformance import (
    AdoptionBlocker,
    BlockerClass,
    DurableAdoptionSeamStatusReport,
    enumerate_durable_element_ids,
    snapshot_world_graph_tree_digest,
)
from apps.live_control_server.services import (
    eldyrwild_relationship_node_kind_source_repair as repair_service,
)


CUTOVER_SCHEMA = "dmb_cutover_whole_world_reanchor_v1"
WORLD_ID = "eldyrwild"
CANONICAL_REVISION_ID = "rev:5a7c13ae45c49a65b402920499be72ed"
CANONICAL_GRAPH_PAYLOAD_SHA256 = (
    "2632870ef70638969503de788cfdec97acd490875deff3e2630ac91dc96fe974"
)
BUDDY_BASE_SHA = "9f08d72462f87b39073920f7726aa8f3e392ef08"
LOCKED_REPAIR_MANIFEST_SHA256 = (
    "96cc26fc6e99448e8fba5cd6982070c1e29bb058f2b1e8a4ac291f8a0a083247"
)
DUNGEONMIND_DEPENDENCY_REF = "2e4fdc51f91c5c2a428500f7c2ece0d6742d04b4"

EXPECTED_CANONICAL_RELATIONSHIP_INVENTORY = {
    "semantic": 323,
    "represented": 314,
    "residual": 9,
    "uses_statblock_mechanics": 3,
}
EXPECTED_MIGRATION_RELATIONSHIP_INVENTORY = {
    "semantic": 323,
    "represented": 318,
    "residual": 5,
    "uses_statblock_mechanics": 3,
}

CANONICAL_RESIDUAL_EDGE_IDS = frozenset(
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
MIGRATION_RESIDUAL_EDGE_IDS = frozenset(
    repair_service.STAGE_B_REMAINING_RESIDUAL_EDGE_IDS
)
MIGRATION_NEWLY_REPRESENTED_EDGE_IDS = frozenset(
    {
        "edge:combat_shatter_mages_tower_spider:located_in:item_shatter_mages_tower",
        "edge:loc:stone_bridge:contains:mystery_stone_bridge_river_name",
        "edge:node:torrin_flamescale:serves:loc:guilds:represents",
        "edge:node:torvak_hempdealer_crew:member_of:item:torvak-hemp-caravan",
    }
)
CHANGED_KIND_PATHS = (
    "nodes[item_shatter_mages_tower].kind",
    "nodes[mystery_stone_bridge_river_name].kind",
    "nodes[loc:guilds].kind",
    "nodes[item:torvak-hemp-caravan].kind",
)

FIXTURE_RELPATH = (
    "tests/fixtures/dungeonmind_kernel/"
    "eldyrwild_cutover_reanchor_after_566_v1.json"
)
LOCKED_FIXTURE_SHA256 = (
    "6c978f89527ccd82e9bad32eac70a5386a5d714e80f7e426f574d7dbc0e43cbf"
)

# Named source/provenance families for T14 no-mutation proofs. Assertion support,
# evidence, and source artifacts live inside revision/contribution payloads, so the
# revisions + contributions digests cover those durable records without a second tree.
_SOURCE_AUTHORITY_RELATIVE_PATHS: tuple[tuple[str, str], ...] = (
    ("head", "head.json"),
    ("contribution_index", "contribution_index.json"),
    ("contributions", "contributions"),
    ("contribution_rebuild", "contribution_rebuild"),
    ("identity_decision_index", "identity_decision_index.json"),
    ("identity_decisions", "identity_decisions"),
    ("initialization", "initialization"),
    ("revisions", "revisions"),
)

CutoverDisposition = Literal["CUTOVER_READY", "CUTOVER_NOT_READY"]
Eligibility = Literal["eligible", "ineligible", "integrity_failure"]


class CutoverWholeWorldReanchorError(RuntimeError):
    """Fail-closed CUTOVER report error."""

    def __init__(self, message: str, *, code: str) -> None:
        super().__init__(message)
        self.code = code


class CutoverWholeWorldReanchorStatusV1(BaseModel):
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


class CutoverWholeWorldReanchorReportV1(BaseModel):
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
    adoption_seam: DurableAdoptionSeamStatusReport
    cutover_disposition: CutoverDisposition
    next_slice_recommendation: dict[str, Any]
    diagnostics: list[str] = Field(default_factory=list)


class CutoverWholeWorldReanchorBuildResultV1(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_: str = Field(default=CUTOVER_SCHEMA + "_build_result", alias="schema")
    world_id: str = WORLD_ID
    fixture_path: str
    fixture_sha256: str
    report: CutoverWholeWorldReanchorReportV1
    diagnostics: list[str] = Field(default_factory=list)


class CutoverWholeWorldReanchorVerifyResultV1(BaseModel):
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


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _digest_path(path: Path) -> str:
    digest = hashlib.sha256()
    if path.is_file():
        digest.update(path.read_bytes())
        return digest.hexdigest()
    if not path.is_dir():
        digest.update(b"missing")
        return digest.hexdigest()
    for child in sorted(p for p in path.rglob("*") if p.is_file()):
        rel = child.relative_to(path).as_posix().encode("utf-8")
        digest.update(rel)
        digest.update(b"\0")
        digest.update(child.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def snapshot_source_authority_inventory(root: Path, world_id: str = WORLD_ID) -> dict[str, str]:
    """Per-family digests for contribution/identity/revision source authority (T14)."""
    world_root = (root / "graph_memory" / "worlds" / world_id).resolve()
    return {
        name: _digest_path(world_root / relative)
        for name, relative in _SOURCE_AUTHORITY_RELATIVE_PATHS
    }


def _json_bytes(payload: Mapping[str, Any]) -> bytes:
    return (
        json.dumps(
            payload,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n"
    ).encode("utf-8")


def _fail(message: str, code: str) -> CutoverWholeWorldReanchorError:
    return CutoverWholeWorldReanchorError(message, code=code)


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
            "DungeonMind contract pins differ from the locked CUTOVER contract",
            "contract_pin_mismatch",
        )
    if report.dungeonmind_dependency_ref != DUNGEONMIND_DEPENDENCY_REF:
        raise _fail("DungeonMind dependency pin mismatch", "dependency_pin_mismatch")


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


def _projection_diff(base_store: Any, overlay_store: Any) -> list[str]:
    base = base_store.model_dump(mode="python", by_alias=True)
    overlay = overlay_store.model_dump(mode="python", by_alias=True)
    changes: list[str] = []

    def visit(left: Any, right: Any, path: str) -> None:
        if isinstance(left, dict) and isinstance(right, dict):
            for key in sorted(set(left) | set(right), key=str):
                if path == "nodes":
                    child = f"nodes[{key}]"
                else:
                    child = f"{path}.{key}" if path else str(key)
                if key not in left or key not in right:
                    changes.append(child)
                else:
                    visit(left[key], right[key], child)
            return
        if isinstance(left, list) and isinstance(right, list):
            if left != right:
                changes.append(path)
            return
        if left != right:
            changes.append(path)

    visit(base, overlay, "")
    return sorted(changes)


PresenceScope = Literal["canonical_only", "projection_only", "both"]
BlockingStage = Literal[
    "adoption_package_construction",
    "durable_adoption",
    "shadow_parity",
    "authority_promotion",
]
OwnershipScope = Literal["singular", "cross_repository"]

# CUTOVER-normalized blocking stage for each whole-world blocker class.
# Dual-sense RELATIONSHIP_PREDICATE is handled specially in _relationship_blocker.
_BLOCKING_STAGE_BY_CLASS: dict[str, BlockingStage] = {
    BlockerClass.WORLD_OBJECT_KIND.value: "adoption_package_construction",
    BlockerClass.ATTRIBUTE_ASSERTION.value: "adoption_package_construction",
    BlockerClass.EVIDENCE_PROVENANCE.value: "adoption_package_construction",
    BlockerClass.SOURCE_INTEGRITY.value: "adoption_package_construction",
    BlockerClass.CAMPAIGN_SCOPE.value: "adoption_package_construction",
    BlockerClass.VISIBILITY_ADMISSIBILITY.value: "adoption_package_construction",
    BlockerClass.EPISTEMIC_STATE.value: "adoption_package_construction",
    BlockerClass.FICTIONAL_TIME.value: "adoption_package_construction",
    BlockerClass.MECHANICS_ATTACHMENT.value: "adoption_package_construction",
    BlockerClass.DUNGEONMIND_PROFILE.value: "adoption_package_construction",
    BlockerClass.DUNGEONMIND_GRAPH_SCHEMA.value: "adoption_package_construction",
    BlockerClass.RELATIONSHIP_PREDICATE.value: "adoption_package_construction",
    BlockerClass.IDENTITY_HISTORY.value: "durable_adoption",
    BlockerClass.CONTRIBUTION_HISTORY.value: "durable_adoption",
    BlockerClass.DURABLE_ADOPTION_BOUNDARY.value: "durable_adoption",
    BlockerClass.POSTGRES_ADOPTION.value: "durable_adoption",
}

_CASE_A_PRIORITY: tuple[str, ...] = (
    BlockerClass.WORLD_OBJECT_KIND.value,
    BlockerClass.DUNGEONMIND_PROFILE.value,
    BlockerClass.DUNGEONMIND_GRAPH_SCHEMA.value,
    BlockerClass.ATTRIBUTE_ASSERTION.value,
    BlockerClass.EVIDENCE_PROVENANCE.value,
    BlockerClass.CAMPAIGN_SCOPE.value,
    BlockerClass.EPISTEMIC_STATE.value,
    BlockerClass.FICTIONAL_TIME.value,
    BlockerClass.VISIBILITY_ADMISSIBILITY.value,
    BlockerClass.MECHANICS_ATTACHMENT.value,
    BlockerClass.RELATIONSHIP_PREDICATE.value,
)


def _presence_scope(
    blocker_class: str,
    *,
    canonical_classes: set[str],
    migration_classes: set[str],
) -> PresenceScope:
    in_canonical = blocker_class in canonical_classes
    in_migration = blocker_class in migration_classes
    if in_canonical and in_migration:
        return "both"
    if in_canonical:
        return "canonical_only"
    return "projection_only"


def _relationship_blocker(
    *,
    residual_edge_ids: list[str],
    projection: bool,
    presence_scope: PresenceScope,
) -> dict[str, Any]:
    if projection:
        return {
            "blocker_class": BlockerClass.RELATIONSHIP_PREDICATE.value,
            "count": len(residual_edge_ids),
            "examples": residual_edge_ids[:10],
            "presence_scope": presence_scope,
            "blocking_stage": "adoption_package_construction",
            "ownership_scope": "cross_repository",
            "responsible_repo": None,
            "ownership_note": (
                "Each dual-sense STOP needs a Buddy source identity/decomposition "
                "decision and a DungeonMind adoption/materialization capability; "
                "this report does not collapse either owner."
            ),
            "smallest_next_change": (
                "Keep the five dual-sense edges as an explicit migration decision "
                "set that still blocks adoption-package construction until a pinned "
                "contract can carry unresolved identity/decomposition semantics "
                "losslessly; do not schedule live Buddy repair or Case B adoption "
                "from this row alone."
            ),
            "ledger_disposition": "replaced_by_effective_relationship",
            "relationship_authority": "eldyrwild-relationship-node-kind-source-repair-v1",
        }
    return {
        "blocker_class": BlockerClass.RELATIONSHIP_PREDICATE.value,
        "count": len(residual_edge_ids),
        "examples": residual_edge_ids[:10],
        "presence_scope": presence_scope,
        "blocking_stage": "adoption_package_construction",
        "ownership_scope": "singular",
        "responsible_repo": "DungeonMindBuddy",
        "ownership_note": "Canonical residual truth is the Buddy source-repair authority.",
        "smallest_next_change": (
            "Keep the nine canonical residuals source-sealed; use only the "
            "verified four-kind migration projection and do not publish it here."
        ),
        "ledger_disposition": "replaced_by_effective_relationship",
        "relationship_authority": "dmb_dungeonmind_relationship_effective_conformance_v1",
    }


def _normalize_whole_world_blocker(
    blocker: AdoptionBlocker,
    *,
    presence_scope: PresenceScope,
) -> dict[str, Any]:
    blocker_class = blocker.blocker_class.value
    stage = _BLOCKING_STAGE_BY_CLASS.get(blocker_class, "adoption_package_construction")
    return {
        "blocker_class": blocker_class,
        "count": blocker.count,
        "examples": list(blocker.examples),
        "presence_scope": presence_scope,
        "blocking_stage": stage,
        "ownership_scope": "singular",
        "responsible_repo": blocker.responsible_repo,
        "ownership_note": None,
        "smallest_next_change": blocker.smallest_next_change,
        "ledger_disposition": "carried",
    }


def _sort_blockers(blockers: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(
        blockers,
        key=lambda blocker: (
            blocker["blocker_class"],
            blocker.get("responsible_repo") or "",
            blocker.get("blocking_stage") or "",
            json.dumps(blocker.get("examples", []), sort_keys=True),
        ),
    )


def _normalized_blockers_for_view(
    whole_world_report: Any,
    *,
    residual_edge_ids: list[str],
    projection: bool,
    canonical_classes: set[str],
    migration_classes: set[str],
) -> list[dict[str, Any]]:
    blockers: list[dict[str, Any]] = []
    for blocker in whole_world_report.blockers:
        if blocker.blocker_class == BlockerClass.RELATIONSHIP_PREDICATE:
            continue
        blocker_class = blocker.blocker_class.value
        blockers.append(
            _normalize_whole_world_blocker(
                blocker,
                presence_scope=_presence_scope(
                    blocker_class,
                    canonical_classes=canonical_classes,
                    migration_classes=migration_classes,
                ),
            )
        )
    blockers.append(
        _relationship_blocker(
            residual_edge_ids=residual_edge_ids,
            projection=projection,
            presence_scope=_presence_scope(
                BlockerClass.RELATIONSHIP_PREDICATE.value,
                canonical_classes=canonical_classes,
                migration_classes=migration_classes,
            ),
        )
    )
    return _sort_blockers(blockers)


def _raw_blocker_classes(whole_world_report: Any) -> set[str]:
    return {blocker.blocker_class.value for blocker in whole_world_report.blockers}


def _blocker_carry_forward(
    *,
    canonical_report: Any,
    migration_report: Any,
    canonical_blockers: list[dict[str, Any]],
    migration_blockers: list[dict[str, Any]],
) -> dict[str, Any]:
    """T11: every original whole-world blocker survives or is explicitly replaced."""

    def _rows(report: Any, ledger: list[dict[str, Any]], view: str) -> list[dict[str, Any]]:
        ledger_by_class = {row["blocker_class"]: row for row in ledger}
        rows: list[dict[str, Any]] = []
        for blocker in report.blockers:
            blocker_class = blocker.blocker_class.value
            if blocker_class == BlockerClass.RELATIONSHIP_PREDICATE.value:
                replacement = ledger_by_class.get(blocker_class)
                rows.append(
                    {
                        "view": view,
                        "original_blocker_class": blocker_class,
                        "original_count": blocker.count,
                        "disposition": "replaced_by_effective_relationship",
                        "cutover_blocker_class": blocker_class,
                        "cutover_count": None
                        if replacement is None
                        else replacement["count"],
                    }
                )
                continue
            carried = ledger_by_class.get(blocker_class)
            if carried is None:
                raise _fail(
                    f"whole-world blocker {blocker_class} missing from {view} CUTOVER ledger",
                    "blocker_carry_forward_loss",
                )
            rows.append(
                {
                    "view": view,
                    "original_blocker_class": blocker_class,
                    "original_count": blocker.count,
                    "disposition": "carried",
                    "cutover_blocker_class": carried["blocker_class"],
                    "cutover_count": carried["count"],
                }
            )
        return rows

    rows = _rows(canonical_report, canonical_blockers, "canonical") + _rows(
        migration_report, migration_blockers, "migration"
    )
    return {
        "lossless": True,
        "rows": rows,
        "non_blocking_operational_classifications": [],
        "note": (
            "Raw v4 RELATIONSHIP_PREDICATE rows are replaced by the owning effective "
            "relationship residual ledger; all other whole-world blockers are carried."
        ),
    }


def _non_relationship_inventory(whole_world_report: Any) -> dict[str, Any]:
    return {
        "inventory": dict(whole_world_report.inventory),
        "kind_inventory": [
            row.model_dump(mode="json") for row in whole_world_report.kind_inventory
        ],
        "predicate_inventory": [
            row.model_dump(mode="json") for row in whole_world_report.predicate_inventory
        ],
        "state_family_inventory": [
            row.model_dump(mode="json")
            for row in whole_world_report.state_family_inventory
        ],
        "artifact_source_domain_inventory": [
            row.model_dump(mode="json")
            for row in whole_world_report.artifact_source_domain_inventory
        ],
        "evidence_source_domain_inventory": [
            row.model_dump(mode="json")
            for row in whole_world_report.evidence_source_domain_inventory
        ],
        "property_gap_inventory": [
            row.model_dump(mode="json")
            for row in whole_world_report.property_gap_inventory
        ],
        "classification_inventory": [
            row.model_dump(mode="json")
            for row in whole_world_report.classification_inventory
        ],
    }


def _relationship_inventory_from_effective(report: Any) -> dict[str, Any]:
    return {
        "semantic": report.relationship_semantic_count,
        "represented": report.relationship_effectively_represented_count,
        "residual": report.relationship_effective_residual_count,
        "uses_statblock_mechanics": report.uses_statblock_mechanics_count,
        "residual_edge_ids": sorted(report.remaining_residual_edge_ids),
        "newly_represented_edge_ids": sorted(
            report.newly_represented_by_continuity_edge_ids
        ),
        "residual_disposition_inventory": [
            row.model_dump(mode="json")
            for row in report.remaining_residual_disposition_inventory
        ],
        "authority": "dmb_dungeonmind_relationship_effective_conformance_v1",
    }


def _relationship_inventory_from_repair_proof(proof: Any) -> dict[str, Any]:
    residual_edge_ids = sorted(
        edge_id
        for stop in proof.dual_sense_stop_proofs
        for edge_id in stop["deferred_edge_ids"]
    )
    newly_represented_edge_ids = sorted(
        edge["edge_id"]
        for edge in proof.deferred_edge_proofs
        if edge["disposition"]
        == repair_service.PredicateDisposition.EXISTING_EXPLICIT_ADAPTER.value
    )
    return {
        **dict(proof.projected_inventory),
        "residual_edge_ids": residual_edge_ids,
        "newly_represented_edge_ids": newly_represented_edge_ids,
        "residual_disposition_inventory": [
            {
                "key": "DUAL_SENSE_MIGRATION_STOP",
                "count": proof.projected_inventory["residual"],
            }
        ],
        "authority": "eldyrwild-relationship-node-kind-source-repair-v1",
        "proof_diagnostics": list(proof.diagnostics),
    }


def _view(
    *,
    whole_world_report: Any,
    relationship_inventory: dict[str, Any],
    blockers: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "whole_world_report_digest": _sha256_bytes(
            _json_bytes(
                whole_world_v4.compact_whole_world_conformance_report_v4(
                    whole_world_report
                )
            )
        ),
        "durable_inventory": _non_relationship_inventory(whole_world_report),
        "relationship_inventory": relationship_inventory,
        "relationship_residual_edge_ids": relationship_inventory["residual_edge_ids"],
        "blockers": blockers,
        "unaccounted_durable_elements": whole_world_report.unaccounted_durable_elements,
    }


def _blocker_map(blockers: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {blocker["blocker_class"]: blocker for blocker in blockers}


def _projection_delta(
    canonical: dict[str, Any],
    migration: dict[str, Any],
    changed_paths: list[str],
) -> dict[str, Any]:
    canonical_map = _blocker_map(canonical["blockers"])
    migration_map = _blocker_map(migration["blockers"])
    added = sorted(set(migration_map) - set(canonical_map))
    cleared = sorted(set(canonical_map) - set(migration_map))
    changed = [
        {
            "blocker_class": key,
            "canonical": canonical_map[key],
            "migration": migration_map[key],
        }
        for key in sorted(set(canonical_map) & set(migration_map))
        if canonical_map[key] != migration_map[key]
    ]
    return {
        "changed_node_ids": sorted(
            {
                "item_shatter_mages_tower",
                "mystery_stone_bridge_river_name",
                "loc:guilds",
                "item:torvak-hemp-caravan",
            }
        ),
        "changed_durable_paths": changed_paths,
        "newly_represented_relationship_edge_ids": migration[
            "relationship_inventory"
        ]["newly_represented_edge_ids"],
        "remaining_relationship_edge_ids": migration["relationship_residual_edge_ids"],
        "added_blockers": added,
        "cleared_blockers": cleared,
        "changed_blockers": changed,
    }


def _package_construction_blockers(
    blockers: list[dict[str, Any]],
    *,
    responsible_repo: str | None = None,
    ownership_scope: OwnershipScope | None = "singular",
) -> list[dict[str, Any]]:
    rows = [
        blocker
        for blocker in blockers
        if blocker.get("blocking_stage") == "adoption_package_construction"
    ]
    if ownership_scope is not None:
        rows = [blocker for blocker in rows if blocker.get("ownership_scope") == ownership_scope]
    if responsible_repo is None:
        return rows
    return [blocker for blocker in rows if blocker.get("responsible_repo") == responsible_repo]


def _any_package_construction_blockers(blockers: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        blocker
        for blocker in blockers
        if blocker.get("blocking_stage") == "adoption_package_construction"
    ]


def _pick_case_a_gap(blockers: list[dict[str, Any]]) -> dict[str, Any]:
    by_class = {blocker["blocker_class"]: blocker for blocker in blockers}
    for blocker_class in _CASE_A_PRIORITY:
        if blocker_class in by_class:
            return by_class[blocker_class]
    return sorted(blockers, key=lambda row: row["blocker_class"])[0]


def _next_slice_recommendation(blockers: list[dict[str, Any]]) -> dict[str, Any]:
    """Derive Case A/B/C/D from normalized blocker stage/ownership — never hardcode Case B."""

    source_integrity = [
        blocker
        for blocker in blockers
        if blocker["blocker_class"] == BlockerClass.SOURCE_INTEGRITY.value
        and blocker.get("blocking_stage") == "adoption_package_construction"
    ]
    if source_integrity:
        return {
            "case": "CASE_C",
            "repository": "DungeonMindBuddy",
            "change": "Resolve the exact source/provenance integrity blocker in the ledger.",
            "basis_blocker_classes": [BlockerClass.SOURCE_INTEGRITY.value],
            "basis_blocking_stages": ["adoption_package_construction"],
            "nonclaim": "Do not reopen broad relationship cleanup.",
        }

    dm_package = _package_construction_blockers(
        blockers, responsible_repo="DungeonMind"
    )
    if dm_package:
        primary = _pick_case_a_gap(dm_package)
        change = primary["smallest_next_change"]
        if primary["blocker_class"] == BlockerClass.WORLD_OBJECT_KIND.value:
            change = (
                "Admit Buddy kind 'thread' into world-object vocabulary, or publish "
                "an explicit Buddy→DM kind adapter with ADR "
                f"(example: {primary['examples'][0]})."
            )
        return {
            "case": "CASE_A",
            "repository": "DungeonMind",
            "change": change,
            "basis_blocker_classes": [primary["blocker_class"]],
            "basis_blocking_stages": ["adoption_package_construction"],
            "basis_examples": list(primary.get("examples", [])[:5]),
            "deferred_durable_adoption_gates": sorted(
                {
                    blocker["blocker_class"]
                    for blocker in blockers
                    if blocker.get("blocking_stage") == "durable_adoption"
                }
            ),
            "cross_repository_package_construction": sorted(
                {
                    blocker["blocker_class"]
                    for blocker in blockers
                    if blocker.get("ownership_scope") == "cross_repository"
                    and blocker.get("blocking_stage") == "adoption_package_construction"
                }
            ),
            "nonclaim": (
                "Case A does not authorize adopting an existing world while semantic "
                "package-construction gaps remain; dual-sense STOPs still block "
                "adoption-package construction and stay undecided."
            ),
        }

    buddy_package = _package_construction_blockers(
        blockers, responsible_repo="DungeonMindBuddy"
    )
    if buddy_package:
        primary = sorted(buddy_package, key=lambda row: row["blocker_class"])[0]
        return {
            "case": "CASE_C",
            "repository": "DungeonMindBuddy",
            "change": primary["smallest_next_change"],
            "basis_blocker_classes": [primary["blocker_class"]],
            "basis_blocking_stages": ["adoption_package_construction"],
            "basis_examples": list(primary.get("examples", [])[:5]),
            "cross_repository_package_construction": sorted(
                {
                    blocker["blocker_class"]
                    for blocker in blockers
                    if blocker.get("ownership_scope") == "cross_repository"
                    and blocker.get("blocking_stage") == "adoption_package_construction"
                }
            ),
            "nonclaim": "Do not reopen broad relationship cleanup.",
        }

    cross_repo_package = _package_construction_blockers(
        blockers, ownership_scope="cross_repository"
    )
    if cross_repo_package:
        primary = sorted(cross_repo_package, key=lambda row: row["blocker_class"])[0]
        return {
            "case": "CASE_A",
            "repository": None,
            "change": primary["smallest_next_change"],
            "basis_blocker_classes": [primary["blocker_class"]],
            "basis_blocking_stages": ["adoption_package_construction"],
            "basis_examples": list(primary.get("examples", [])[:5]),
            "basis_ownership_scope": "cross_repository",
            "deferred_durable_adoption_gates": sorted(
                {
                    blocker["blocker_class"]
                    for blocker in blockers
                    if blocker.get("blocking_stage") == "durable_adoption"
                }
            ),
            "nonclaim": (
                "Cross-repository package-construction blockers keep the semantic "
                "target inexpressible; Case B adoption-seam work is not authorized."
            ),
        }

    remaining_package = _any_package_construction_blockers(blockers)
    if remaining_package:
        primary = sorted(remaining_package, key=lambda row: row["blocker_class"])[0]
        return {
            "case": "CASE_A",
            "repository": primary.get("responsible_repo"),
            "change": primary["smallest_next_change"],
            "basis_blocker_classes": [primary["blocker_class"]],
            "basis_blocking_stages": ["adoption_package_construction"],
            "basis_examples": list(primary.get("examples", [])[:5]),
            "nonclaim": (
                "Adoption-package construction is not clear; Case B is not authorized."
            ),
        }

    durable_gates = [
        blocker
        for blocker in blockers
        if blocker.get("blocking_stage") == "durable_adoption"
        and blocker.get("ownership_scope") == "singular"
        and blocker.get("responsible_repo") == "DungeonMind"
    ]
    adoption_boundary = any(
        blocker["blocker_class"] == BlockerClass.DURABLE_ADOPTION_BOUNDARY.value
        for blocker in durable_gates
    )
    if adoption_boundary:
        return {
            "case": "CASE_B",
            "repository": "DungeonMind",
            "change": "Add governed existing-world adoption transaction",
            "basis_blocker_classes": sorted(
                {blocker["blocker_class"] for blocker in durable_gates}
            ),
            "basis_blocking_stages": ["durable_adoption"],
            "nonclaim": (
                "Case B is valid only because adoption-package construction is already "
                "expressible; this report still does not claim CUTOVER completion."
            ),
        }

    if not blockers:
        return {
            "case": "CASE_D",
            "repository": "DungeonMindBuddy",
            "change": (
                "Dispatch a separate shadow-adoption/readiness proof; "
                "do not switch product authority here."
            ),
            "basis_blocker_classes": [],
            "basis_blocking_stages": [],
            "nonclaim": "No adoption blockers remain in this ledger.",
        }

    return {
        "case": "CASE_A",
        "repository": "DungeonMind",
        "change": "Dispatch the narrowest remaining contract gap from the ledger.",
        "basis_blocker_classes": sorted({blocker["blocker_class"] for blocker in blockers}),
        "basis_blocking_stages": sorted(
            {
                blocker.get("blocking_stage") or "adoption_package_construction"
                for blocker in blockers
            }
        ),
        "nonclaim": "Do not claim CUTOVER readiness from relationship counts.",
    }


def _compose_report(root: Path, repo: Path) -> CutoverWholeWorldReanchorReportV1:
    repository_head = _git_head(repo)
    if not _is_descendant(repo, BUDDY_BASE_SHA):
        raise _fail(
            f"Buddy HEAD {repository_head} does not descend from {BUDDY_BASE_SHA}",
            "buddy_base_mismatch",
        )

    head_before, manifest, base_store, tree_before = _open_exact_canonical(root)
    source_before = snapshot_source_authority_inventory(root)
    canonical_v4 = whole_world_v4._analyze_loaded_buddy_world_store_v4(
        root=root,
        world_id=WORLD_ID,
        revision_id=CANONICAL_REVISION_ID,
        manifest=manifest,
        store=base_store,
    )
    _verify_contract_pins(canonical_v4)
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
        raise _fail("canonical effective relationship inventory mismatch", "canonical_relationship_mismatch")
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
    overlay_v4 = whole_world_v4._analyze_loaded_buddy_world_store_v4(
        root=root,
        world_id=WORLD_ID,
        revision_id=CANONICAL_REVISION_ID,
        manifest=_copy_manifest(manifest),
        store=overlay_store,
    )
    if overlay_v4.unaccounted_durable_elements != 0:
        raise _fail("migration overlay has unaccounted durable elements", "overlay_unaccounted")
    migration_relationship = _relationship_inventory_from_repair_proof(repair_proof)
    if {
        key: migration_relationship[key]
        for key in EXPECTED_MIGRATION_RELATIONSHIP_INVENTORY
    } != EXPECTED_MIGRATION_RELATIONSHIP_INVENTORY:
        raise _fail("migration proof relationship inventory mismatch", "migration_relationship_mismatch")
    if set(migration_relationship["residual_edge_ids"]) != MIGRATION_RESIDUAL_EDGE_IDS:
        raise _fail("migration proof residual set mismatch", "migration_residual_mismatch")

    adoption_seam = whole_world_v4.inspect_dungeonmind_durable_adoption_seam()
    canonical_classes = _raw_blocker_classes(canonical_v4)
    migration_classes = _raw_blocker_classes(overlay_v4)
    # Effective relationship residual always contributes RELATIONSHIP_PREDICATE.
    canonical_classes = set(canonical_classes) | {
        BlockerClass.RELATIONSHIP_PREDICATE.value
    }
    migration_classes = set(migration_classes) | {
        BlockerClass.RELATIONSHIP_PREDICATE.value
    }
    canonical_blockers = _normalized_blockers_for_view(
        canonical_v4,
        residual_edge_ids=canonical_relationship["residual_edge_ids"],
        projection=False,
        canonical_classes=canonical_classes,
        migration_classes=migration_classes,
    )
    migration_blockers = _normalized_blockers_for_view(
        overlay_v4,
        residual_edge_ids=migration_relationship["residual_edge_ids"],
        projection=True,
        canonical_classes=canonical_classes,
        migration_classes=migration_classes,
    )
    carry_forward = _blocker_carry_forward(
        canonical_report=canonical_v4,
        migration_report=overlay_v4,
        canonical_blockers=canonical_blockers,
        migration_blockers=migration_blockers,
    )
    canonical_view = _view(
        whole_world_report=canonical_v4,
        relationship_inventory=canonical_relationship,
        blockers=canonical_blockers,
    )
    migration_view = _view(
        whole_world_report=overlay_v4,
        relationship_inventory=migration_relationship,
        blockers=migration_blockers,
    )
    projection_delta = _projection_delta(
        canonical_view,
        migration_view,
        changed_paths,
    )
    diagnostics = [
        "non_publishing",
        "canonical_relationship_authority:effective_conformance",
        "migration_relationship_authority:prove_isolated_repair_effect",
        "overlay_manifest_payload_sha_reflects_canonical_pin_for_domain_matching",
        "raw_v4_relationship_predicate_blockers_replaced_by_owning_ledgers",
        "next_slice_derived_from_normalized_blocker_stages",
        "historical_effective_conformance_suite_superseded_by_cutover_owned_proofs",
    ]
    report = CutoverWholeWorldReanchorReportV1(
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
        adoption_seam=adoption_seam,
        cutover_disposition="CUTOVER_NOT_READY",
        next_slice_recommendation=_next_slice_recommendation(migration_view["blockers"]),
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


def _assert_report_invariants(report: CutoverWholeWorldReanchorReportV1) -> None:
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
    if "aspect" in json.dumps(report.model_dump(mode="json", by_alias=True)).lower():
        raise _fail("report contains forbidden aspect identity materialization", "aspect_materialization")


def _report_bytes(report: CutoverWholeWorldReanchorReportV1) -> bytes:
    return _json_bytes(report.model_dump(mode="json", by_alias=True))


def get_cutover_whole_world_reanchor_status(
    root: Path | None = None,
    *,
    repo: Path | None = None,
) -> CutoverWholeWorldReanchorStatusV1:
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
        if whole_world_v4._DUNGEONMIND_DEPENDENCY_REF_V4 != DUNGEONMIND_DEPENDENCY_REF:
            diagnostics.append("dependency_pin_mismatch")
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
            return CutoverWholeWorldReanchorStatusV1(
                eligibility="ineligible",
                reason="exact CUTOVER activation pins do not hold",
                diagnostics=diagnostics,
                canonical_graph_payload_sha256=getattr(
                    graph_manifest, "graph_payload_sha256", None
                ),
                repair_manifest_sha256=manifest_sha,
                adoption_seam=seam,
            )
        return CutoverWholeWorldReanchorStatusV1(
            eligibility="eligible",
            reason="exact post-#566 CUTOVER activation pins hold",
            diagnostics=["status_ok", "buddy_head_observed:" + head, *diagnostics],
            canonical_graph_payload_sha256=graph_manifest.graph_payload_sha256,
            repair_manifest_sha256=manifest_sha,
            adoption_seam=seam,
        )
    except Exception as exc:  # noqa: BLE001
        diagnostics.append(type(exc).__name__ + ":" + str(exc))
        return CutoverWholeWorldReanchorStatusV1(
            eligibility="integrity_failure",
            reason="CUTOVER activation diagnostics failed closed",
            diagnostics=diagnostics,
        )


def build_cutover_whole_world_reanchor(
    *,
    root: Path | None = None,
    repo: Path | None = None,
    allow_live_world: bool = False,
) -> CutoverWholeWorldReanchorBuildResultV1:
    """Build the deterministic repository fixture without mutating the graph."""
    del allow_live_world
    world_root = _root(root)
    repository = _repo(repo)
    report = _compose_report(world_root, repository)
    raw = _report_bytes(report)
    fixture_sha = _sha256_bytes(raw)
    if fixture_sha != LOCKED_FIXTURE_SHA256:
        raise _fail(
            "generated CUTOVER fixture digest does not match locked v1 digest",
            "fixture_digest_mismatch",
        )
    path = _fixture_path(repository)
    if path.is_file():
        existing_sha = _sha256_bytes(path.read_bytes())
        if existing_sha != fixture_sha:
            raise _fail(
                "existing CUTOVER v1 fixture differs from locked generated bytes",
                "locked_fixture_overwrite_refused",
            )
        return CutoverWholeWorldReanchorBuildResultV1(
            fixture_path=str(path),
            fixture_sha256=fixture_sha,
            report=report,
            diagnostics=["non_publishing", "already_built"],
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
        raise _fail(f"atomic CUTOVER fixture write failed: {exc}", "fixture_write_failed") from exc
    return CutoverWholeWorldReanchorBuildResultV1(
        fixture_path=str(path),
        fixture_sha256=fixture_sha,
        report=report,
        diagnostics=["non_publishing", "fixture_written_atomically", "first_seal"],
    )


def verify_cutover_whole_world_reanchor(
    *,
    root: Path | None = None,
    repo: Path | None = None,
) -> CutoverWholeWorldReanchorVerifyResultV1:
    """Reload the locked fixture and independently reproduce its report bytes."""
    world_root = _root(root)
    repository = _repo(repo)
    path = _fixture_path(repository)
    if not path.is_file():
        return CutoverWholeWorldReanchorVerifyResultV1(
            verified=False,
            fixture_path=str(path),
            diagnostics=["fixture_missing"],
        )
    raw = path.read_bytes()
    fixture_sha = _sha256_bytes(raw)
    if fixture_sha != LOCKED_FIXTURE_SHA256:
        return CutoverWholeWorldReanchorVerifyResultV1(
            verified=False,
            fixture_path=str(path),
            fixture_sha256=fixture_sha,
            diagnostics=["fixture_digest_mismatch"],
        )
    try:
        stored = CutoverWholeWorldReanchorReportV1.model_validate(json.loads(raw))
        reproduced = _compose_report(world_root, repository)
        if _report_bytes(stored) != _report_bytes(reproduced):
            return CutoverWholeWorldReanchorVerifyResultV1(
                verified=False,
                fixture_path=str(path),
                fixture_sha256=fixture_sha,
                diagnostics=["fixture_bytes_not_deterministic"],
            )
        _assert_report_invariants(reproduced)
    except (CutoverWholeWorldReanchorError, OSError, ValueError, TypeError) as exc:
        return CutoverWholeWorldReanchorVerifyResultV1(
            verified=False,
            fixture_path=str(path),
            fixture_sha256=fixture_sha,
            diagnostics=[type(exc).__name__ + ":" + str(exc)],
        )
    return CutoverWholeWorldReanchorVerifyResultV1(
        verified=True,
        fixture_path=str(path),
        fixture_sha256=fixture_sha,
        diagnostics=["verified", "non_publishing"],
    )

