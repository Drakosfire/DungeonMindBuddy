"""CUTOVER successor: seal Captain and Thrin alias assertion package.

Diagnostic only. Reconstructs the two remaining source-grounded current-node
aliases as revision-bound DungeonMind-compatible alias assertion rows.
Authorizes classification only from a complete current package proof.
Does not mutate Eldyrwild.
"""

from __future__ import annotations

import json
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
from apps.live_control_server.integrations.dungeonmind_kernel.alias_assertion_package_conformance_v1 import (
    AliasAssertionPackageConformanceError,
    prove_alias_assertion_package_v1,
)
from apps.live_control_server.integrations.dungeonmind_kernel.identity_lifecycle_history_conformance_v1 import (
    IdentityLifecycleHistoryConformanceError,
    prove_alias_remove_survivor_lineage,
    prove_identity_lifecycle_history_through_alias_remove,
    prove_identity_lifecycle_history_v1,
)
from apps.live_control_server.integrations.dungeonmind_kernel.relationship_effective_conformance_v1 import (
    analyze_relationship_effective_conformance_v1,
)
from apps.live_control_server.integrations.dungeonmind_kernel.whole_world_conformance import (
    BlockerClass,
    enumerate_durable_element_ids,
    snapshot_world_graph_tree_digest,
)
from apps.live_control_server.integrations.dungeonmind_kernel.whole_world_conformance_v4 import (
    CURRENT_V5_TARGET,
    LEGACY_ALIAS_ASSERTION_POLICY,
    LEGACY_SOURCE_HISTORY_POLICY,
    alias_assertion_policy_from_proof,
    source_history_policy_from_identity_lifecycle_proof,
)
from graph_memory.world_supergraph.contribution_store import load_contribution_record
from apps.live_control_server.services import (
    eldyrwild_relationship_node_kind_source_repair as repair_service,
)
from apps.live_control_server.services.cutover_identity_lifecycle_history_after_571 import (
    CANONICAL_GRAPH_PAYLOAD_SHA256 as HISTORICAL_575_PAYLOAD_SHA256,
    CANONICAL_REVISION_ID as HISTORICAL_575_REVISION_ID,
    FIXTURE_RELPATH as HISTORICAL_575_FIXTURE_RELPATH,
    LOCKED_FIXTURE_SHA256 as HISTORICAL_575_FIXTURE_SHA256,
    _attribute_assertion_ids,
    _blocker_count,
    _blocker_row,
    _proof_payload,
    _store_identity_snapshot,
)
from apps.live_control_server.services.cutover_whole_world_reanchor import (
    CANONICAL_RESIDUAL_EDGE_IDS,
    CHANGED_KIND_PATHS,
    EXPECTED_CANONICAL_RELATIONSHIP_INVENTORY,
    EXPECTED_MIGRATION_RELATIONSHIP_INVENTORY,
    MIGRATION_RESIDUAL_EDGE_IDS,
    _json_bytes,
    _next_slice_recommendation,
    _normalized_blockers_for_view,
    _projection_diff,
    _raw_blocker_classes,
    _relationship_inventory_from_effective,
    _sha256_bytes,
    snapshot_source_authority_inventory,
)
from apps.live_control_server.services.cutover_whole_world_repin_after_dm30 import (
    DUNGEONMIND_DEPENDENCY_REF,
    CutoverWholeWorldRepinAfterDm30Error,
    _copy_manifest,
    _git_head,
    _is_descendant,
    _verify_contract_pins,
)


CUTOVER_SCHEMA = "dmb_cutover_alias_assertion_package_after_shadow_alias_remove_v1"
DISPATCH_BASE_SHA = "17a58740502e99d592f05ba9a10f1d8401e09581"
WORLD_ID = "eldyrwild"
CANONICAL_REVISION_ID = "rev:0c644e56b45bcaac709012206e3e41c2"
CANONICAL_GRAPH_PAYLOAD_SHA256 = (
    "0640d7ef8ce152ee4f656959e0e9a6c9c2fdf5ecc8bd721729b3019170d677f2"
)
FIXTURE_RELPATH = (
    "tests/fixtures/dungeonmind_kernel/"
    "eldyrwild_cutover_alias_assertion_package_after_shadow_alias_remove_v1.json"
)
LOCKED_FIXTURE_SHA256 = (
    "84a9fb095feeff42e038ebfdd99db5735c3b7badc557c45c31d30a9f38ff1411"
)
CAPTAIN_BLOCKER_ID = "node:node:captain-lysandra-ironveil:field:aliases"
THRIN_BLOCKER_ID = "node:node:thrin-branchborn:field:aliases"

CutoverDisposition = Literal["CUTOVER_READY", "CUTOVER_NOT_READY"]
Eligibility = Literal["eligible", "ineligible", "integrity_failure"]


class CutoverAliasAssertionPackageAfterShadowAliasRemoveError(RuntimeError):
    """Fail-closed current identity-lifecycle successor error."""

    def __init__(self, message: str, *, code: str) -> None:
        super().__init__(message)
        self.code = code


class CutoverAliasAssertionPackageAfterShadowAliasRemoveStatusV1(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_: str = Field(default=CUTOVER_SCHEMA + "_status", alias="schema")
    world_id: str = WORLD_ID
    canonical_revision_id: str = CANONICAL_REVISION_ID
    eligibility: Eligibility
    reason: str | None = None
    diagnostics: list[str] = Field(default_factory=list)
    canonical_graph_payload_sha256: str | None = None


class CutoverAliasAssertionPackageAfterShadowAliasRemoveReportV1(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_: str = Field(default=CUTOVER_SCHEMA, alias="schema")
    world_id: str = WORLD_ID
    buddy_dispatch_base_sha: str
    canonical_revision_id: str
    canonical_graph_payload_sha256: str
    dungeonmind_dependency_ref: str
    pre_policy_attribute_assertion_ids: list[str]
    merge_only_diagnostic: dict[str, Any]
    merge_only_policy_refused: bool
    current_lifecycle_proof: dict[str, Any]
    alias_remove_lineage: dict[str, Any]
    source_history_policy: dict[str, Any]
    pre_package_evidence_provenance_ids: list[str]
    alias_package_proof: dict[str, Any]
    alias_assertion_policy: dict[str, Any]
    policy: dict[str, Any]
    post_policy_blockers: list[dict[str, Any]]
    attribute_assertion_count: int | None
    evidence_provenance: dict[str, Any]
    identity_history_count: int | None
    contribution_history_count: int | None
    relationship_invariants: dict[str, Any]
    historical_575: dict[str, Any]
    mutation_proof: dict[str, Any]
    captain_thrin_package_implemented: bool
    cutover_disposition: CutoverDisposition
    next_slice_recommendation: dict[str, Any]
    diagnostics: list[str] = Field(default_factory=list)


class CutoverAliasAssertionPackageAfterShadowAliasRemoveBuildResultV1(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_: str = Field(default=CUTOVER_SCHEMA + "_build_result", alias="schema")
    world_id: str = WORLD_ID
    fixture_path: str
    fixture_sha256: str
    report: CutoverAliasAssertionPackageAfterShadowAliasRemoveReportV1
    diagnostics: list[str] = Field(default_factory=list)


class CutoverAliasAssertionPackageAfterShadowAliasRemoveVerifyResultV1(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_: str = Field(default=CUTOVER_SCHEMA + "_verify_result", alias="schema")
    world_id: str = WORLD_ID
    verified: bool
    fixture_path: str
    fixture_sha256: str | None = None
    diagnostics: list[str] = Field(default_factory=list)


def _fail(message: str, code: str) -> CutoverAliasAssertionPackageAfterShadowAliasRemoveError:
    return CutoverAliasAssertionPackageAfterShadowAliasRemoveError(message, code=code)


def _root(root: Path | None) -> Path:
    return Path(root).resolve() if root is not None else world_graph_root()


def _repo(repo: Path | None) -> Path:
    return Path(repo).resolve() if repo is not None else repo_root()


def _fixture_path(repo: Path) -> Path:
    return repo / FIXTURE_RELPATH


def _report_bytes(report: CutoverAliasAssertionPackageAfterShadowAliasRemoveReportV1) -> bytes:
    return _json_bytes(report.model_dump(mode="json", by_alias=True))


def _alias_snapshot(store: Any) -> dict[str, list[str]]:
    return {
        node_id: list(getattr(node, "aliases", None) or [])
        for node_id, node in sorted((getattr(store, "nodes", None) or {}).items())
    }


def _assertion_support_digest(store: Any) -> str:
    return _sha256_bytes(
        _json_bytes(_dump_jsonable(getattr(store, "assertion_support", None) or {}))
    )


def _dump_jsonable(value: Any) -> Any:
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json", by_alias=True)
    if isinstance(value, dict):
        return {str(key): _dump_jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_dump_jsonable(item) for item in value]
    return value


def _contribution_history_digest(store: Any) -> str:
    """Digest the loaded store's actual contribution-history fields.

    ``UnionSupergraphStore`` has no ``contributions`` collection. Durable
    contribution-bearing state is the source-payload map, replay manifest,
    and initialization contribution ids/digests.
    """
    replay = getattr(store, "contribution_replay_manifest", None) or []
    payload = {
        "contribution_source_payload_sha256": dict(
            getattr(store, "contribution_source_payload_sha256", None) or {}
        ),
        "contribution_replay_manifest": _dump_jsonable(list(replay)),
        "initialization_contribution_ids": list(
            getattr(store, "initialization_contribution_ids", None) or []
        ),
        "initialization_plan_digest": getattr(store, "initialization_plan_digest", None),
        "initialization_attestation_digest": getattr(
            store, "initialization_attestation_digest", None
        ),
    }
    return _sha256_bytes(_json_bytes(payload))


def _loaded_store_digest(store: Any) -> str:
    """Deterministic semantic digest of the loaded UnionSupergraphStore."""
    if not hasattr(store, "model_dump"):
        raise _fail("loaded store is not dumpable", "store_digest_failed")
    return _sha256_bytes(_json_bytes(store.model_dump(mode="json", by_alias=True)))


def _pins_or_fail(report: Any) -> None:
    try:
        _verify_contract_pins(report)
    except CutoverWholeWorldRepinAfterDm30Error as exc:
        raise _fail(str(exc), getattr(exc, "code", "contract_pin_mismatch")) from exc


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


def _blocker_examples(blockers: list[dict[str, Any]], blocker_class: str) -> list[str]:
    row = _blocker_row(blockers, blocker_class)
    if row is None:
        return []
    return [str(item) for item in list(row.get("examples") or [])]


def _historical_575(root: Path, repo: Path) -> dict[str, Any]:
    path = repo / HISTORICAL_575_FIXTURE_RELPATH
    raw = path.read_bytes() if path.is_file() else b""
    digest = _sha256_bytes(raw) if raw else None
    historical_proof: dict[str, Any] | None = None
    historical_error: str | None = None
    try:
        manifest, store = whole_world_v4._load_exact_buddy_revision(
            root=root,
            world_id=WORLD_ID,
            revision_id=HISTORICAL_575_REVISION_ID,
        )
        if manifest.graph_payload_sha256 != HISTORICAL_575_PAYLOAD_SHA256:
            raise _fail(
                "historical #575 payload pin mismatch",
                "historical_575_payload_mismatch",
            )
        proof = prove_identity_lifecycle_history_v1(
            store,
            world_id=WORLD_ID,
            canonical_revision_id=HISTORICAL_575_REVISION_ID,
            canonical_graph_payload_sha256=HISTORICAL_575_PAYLOAD_SHA256,
        )
        historical_proof = {
            "passed": proof.passed,
            "reconstructable_count": proof.reconstructable_count,
            "unresolved_count": len(proof.unresolved_element_ids),
            "candidate_count": len(proof.element_ids),
            "field_counts": proof.field_counts,
        }
        if not proof.passed:
            historical_error = "historical merge-only proof did not pass"
    except Exception as exc:
        historical_error = f"{type(exc).__name__}:{exc}"
    return {
        "fixture_path": HISTORICAL_575_FIXTURE_RELPATH,
        "fixture_present": path.is_file(),
        "fixture_sha256": digest,
        "fixture_digest_matches_locked": digest == HISTORICAL_575_FIXTURE_SHA256,
        "historical_revision_id": HISTORICAL_575_REVISION_ID,
        "merge_only_proof": historical_proof,
        "error": historical_error,
    }


def compose_cutover_alias_assertion_package_after_shadow_alias_remove(
    root: Path | None = None,
    repo: Path | None = None,
) -> CutoverAliasAssertionPackageAfterShadowAliasRemoveReportV1:
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

    head_before, manifest, store, tree_before = _open_current_canonical(world_root)
    source_before = snapshot_source_authority_inventory(world_root)
    identity_before = _store_identity_snapshot(store)
    aliases_before = _alias_snapshot(store)
    support_before = _assertion_support_digest(store)
    contributions_before = _contribution_history_digest(store)
    loaded_store_before = _loaded_store_digest(store)

    legacy_classified: list[Any] = []
    legacy_v5 = whole_world_v5._analyze_loaded_buddy_world_store_v5(
        root=world_root,
        world_id=WORLD_ID,
        revision_id=CANONICAL_REVISION_ID,
        manifest=manifest,
        store=store,
        classified_out=legacy_classified,
        source_history_policy=LEGACY_SOURCE_HISTORY_POLICY,
    )
    _pins_or_fail(legacy_v5)
    attribute_ids = _attribute_assertion_ids(legacy_classified)

    try:
        merge_only = prove_identity_lifecycle_history_v1(
            store,
            world_id=WORLD_ID,
            canonical_revision_id=CANONICAL_REVISION_ID,
            canonical_graph_payload_sha256=CANONICAL_GRAPH_PAYLOAD_SHA256,
        )
    except IdentityLifecycleHistoryConformanceError as exc:
        raise _fail(str(exc), exc.code) from exc
    merge_only_refused = False
    try:
        source_history_policy_from_identity_lifecycle_proof(merge_only)
    except ValueError:
        merge_only_refused = True
    if not merge_only_refused:
        raise _fail(
            "merge-only partial proof must not mint source-history policy",
            "stale_partial_policy",
        )

    try:
        current_proof = prove_identity_lifecycle_history_through_alias_remove(
            store,
            world_id=WORLD_ID,
            canonical_revision_id=CANONICAL_REVISION_ID,
            canonical_graph_payload_sha256=CANONICAL_GRAPH_PAYLOAD_SHA256,
        )
    except IdentityLifecycleHistoryConformanceError as exc:
        raise _fail(str(exc), exc.code) from exc
    if not current_proof.passed or current_proof.unresolved_element_ids:
        raise _fail(
            f"current lifecycle proof unresolved: {current_proof.unresolved_element_ids}",
            "identity_lifecycle_proof_failed",
        )
    if set(attribute_ids) != set(current_proof.element_ids):
        raise _fail(
            "ATTRIBUTE_ASSERTION IDs != current lifecycle proof IDs",
            "attribute_identity_set_mismatch",
        )
    if current_proof.reconstructable_count != len(current_proof.element_ids):
        raise _fail(
            "current reconstructable_count drifted from candidate count",
            "identity_lifecycle_proof_failed",
        )

    policy = source_history_policy_from_identity_lifecycle_proof(current_proof)

    lineage_rows: list[dict[str, Any]] = []
    for row in current_proof.rows:
        if row.decision_kind != "alias_remove" or row.field != "last_identity_decision_id":
            continue
        lineage = prove_alias_remove_survivor_lineage(store, row.node_id)
        if (
            not lineage.reconstructable
            or lineage.current is None
            or lineage.causal_merge is None
        ):
            raise _fail(
                f"alias_remove lineage missing for {row.node_id}",
                "alias_remove_lineage_missing",
            )
        lineage_rows.append(
            {
                "node_id": row.node_id,
                "alias_remove_decision_id": lineage.current.decision_id,
                "causal_merge_decision_id": lineage.causal_merge.decision_id,
                "alias": lineage.current.alias,
                "ordering": "durable_decision_list_position",
            }
        )

    current_classified: list[Any] = []
    current_v5 = whole_world_v5._analyze_loaded_buddy_world_store_v5(
        root=world_root,
        world_id=WORLD_ID,
        revision_id=CANONICAL_REVISION_ID,
        manifest=_copy_manifest(manifest),
        store=store,
        classified_out=current_classified,
        source_history_policy=policy,
        alias_assertion_policy=LEGACY_ALIAS_ASSERTION_POLICY,
    )
    _pins_or_fail(current_v5)

    pre_package_ep_ids = sorted(
        item.element_id
        for item in current_classified
        if item.blocker_class == BlockerClass.EVIDENCE_PROVENANCE
        and str(item.element_id).endswith(":field:aliases")
    )
    expected_ep_ids = [CAPTAIN_BLOCKER_ID, THRIN_BLOCKER_ID]
    if pre_package_ep_ids != expected_ep_ids:
        raise _fail(
            f"pre-package alias EP inventory drifted: {pre_package_ep_ids}",
            "alias_ep_inventory_mismatch",
        )

    def _load_contribution(contribution_id: str) -> Any:
        return load_contribution_record(world_root, WORLD_ID, contribution_id)

    try:
        alias_proof = prove_alias_assertion_package_v1(
            store,
            world_id=WORLD_ID,
            canonical_revision_id=CANONICAL_REVISION_ID,
            canonical_graph_payload_sha256=CANONICAL_GRAPH_PAYLOAD_SHA256,
            contribution_loader=_load_contribution,
        )
    except AliasAssertionPackageConformanceError as exc:
        raise _fail(str(exc), exc.code) from exc
    if not alias_proof.passed or alias_proof.residuals:
        raise _fail(
            f"alias package proof failed: residuals={alias_proof.residual_count}",
            "alias_package_proof_failed",
        )
    if list(alias_proof.blocker_element_ids) != pre_package_ep_ids:
        raise _fail(
            "alias package blocker IDs != current EP alias inventory",
            "alias_package_blocker_mismatch",
        )
    if set(alias_proof.covered_blocker_element_ids) != set(pre_package_ep_ids):
        raise _fail(
            "alias package did not cover current EP alias inventory",
            "alias_package_incomplete",
        )

    alias_policy = alias_assertion_policy_from_proof(alias_proof)

    packaged_classified: list[Any] = []
    packaged_v5 = whole_world_v5._analyze_loaded_buddy_world_store_v5(
        root=world_root,
        world_id=WORLD_ID,
        revision_id=CANONICAL_REVISION_ID,
        manifest=_copy_manifest(manifest),
        store=store,
        classified_out=packaged_classified,
        source_history_policy=policy,
        alias_assertion_policy=alias_policy,
    )
    _pins_or_fail(packaged_v5)

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
    if set(canonical_relationship["residual_edge_ids"]) != CANONICAL_RESIDUAL_EDGE_IDS:
        raise _fail("canonical effective residual set mismatch", "canonical_residual_mismatch")

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
    if set(migration_relationship["residual_edge_ids"]) != MIGRATION_RESIDUAL_EDGE_IDS:
        raise _fail("migration overlay residual set mismatch", "migration_residual_mismatch")

    overlay_classified: list[Any] = []
    overlay_v5 = whole_world_v5._analyze_loaded_buddy_world_store_v5(
        root=world_root,
        world_id=WORLD_ID,
        revision_id=CANONICAL_REVISION_ID,
        manifest=_copy_manifest(manifest),
        store=overlay_store,
        classified_out=overlay_classified,
        source_history_policy=policy,
        alias_assertion_policy=alias_policy,
    )
    _pins_or_fail(overlay_v5)

    canonical_classes = set(_raw_blocker_classes(packaged_v5)) | {
        BlockerClass.RELATIONSHIP_PREDICATE.value
    }
    migration_classes = set(_raw_blocker_classes(overlay_v5)) | {
        BlockerClass.RELATIONSHIP_PREDICATE.value
    }
    migration_blockers = _normalized_blockers_for_view(
        overlay_v5,
        residual_edge_ids=migration_relationship["residual_edge_ids"],
        projection=True,
        canonical_classes=canonical_classes,
        migration_classes=migration_classes,
    )
    attribute_count = _blocker_count(migration_blockers, BlockerClass.ATTRIBUTE_ASSERTION.value)
    if attribute_count is None:
        attribute_count = 0
    evidence_examples = _blocker_examples(
        migration_blockers, BlockerClass.EVIDENCE_PROVENANCE.value
    )
    evidence_count = _blocker_count(migration_blockers, BlockerClass.EVIDENCE_PROVENANCE.value)
    identity_count = _blocker_count(migration_blockers, BlockerClass.IDENTITY_HISTORY.value)
    contribution_count = _blocker_count(
        migration_blockers, BlockerClass.CONTRIBUTION_HISTORY.value
    )

    if attribute_count not in (None, 0):
        raise _fail(
            f"ATTRIBUTE_ASSERTION reappeared after alias packaging: {attribute_count}",
            "attribute_assertion_reappeared",
        )
    if evidence_count not in (None, 0):
        raise _fail(
            f"EVIDENCE_PROVENANCE residual after alias packaging: {evidence_count}",
            "alias_package_ep_residual",
        )

    historical = _historical_575(world_root, repository)
    if not historical["fixture_digest_matches_locked"]:
        raise _fail(
            "historical #575 fixture digest mismatch",
            "historical_575_fixture_mismatch",
        )
    historical_proof = historical.get("merge_only_proof") or {}
    if historical_proof.get("passed") is not True:
        raise _fail(
            f"historical #575 merge-only world did not reproduce: {historical.get('error')}",
            "historical_575_proof_failed",
        )

    head_after = kernel.open_world_graph_head(world_root, WORLD_ID)
    tree_after = snapshot_world_graph_tree_digest(world_root, WORLD_ID)
    source_after = snapshot_source_authority_inventory(world_root)
    identity_after = _store_identity_snapshot(store)
    aliases_after = _alias_snapshot(store)
    support_after = _assertion_support_digest(store)
    contributions_after = _contribution_history_digest(store)
    loaded_store_after = _loaded_store_digest(store)
    if head_after.head_revision_id != head_before.head_revision_id:
        raise _fail("canonical head changed during diagnostic", "world_graph_mutated")
    if tree_after != tree_before:
        raise _fail("World Graph tree digest changed during diagnostic", "world_graph_mutated")
    if source_after != source_before:
        raise _fail("source authority changed during diagnostic", "world_graph_mutated")
    if identity_after != identity_before:
        raise _fail("identity ledger changed during diagnostic", "world_graph_mutated")
    if aliases_after != aliases_before:
        raise _fail("node aliases changed during diagnostic", "world_graph_mutated")
    if support_after != support_before:
        raise _fail("assertion support changed during diagnostic", "world_graph_mutated")
    if contributions_after != contributions_before:
        raise _fail("contribution history changed during diagnostic", "world_graph_mutated")
    if loaded_store_after != loaded_store_before:
        raise _fail("loaded store changed during diagnostic", "world_graph_mutated")

    recommendation = _next_slice_recommendation(migration_blockers)
    diagnostics = [
        "non_publishing",
        "merge_only_policy_refused",
        "current_lifecycle_proof_passed",
        "captain_thrin_package_implemented",
        "alias_assertion_policy_revision_bound",
    ]

    return CutoverAliasAssertionPackageAfterShadowAliasRemoveReportV1(
        buddy_dispatch_base_sha=DISPATCH_BASE_SHA,
        canonical_revision_id=manifest.revision_id,
        canonical_graph_payload_sha256=manifest.graph_payload_sha256,
        dungeonmind_dependency_ref=DUNGEONMIND_DEPENDENCY_REF,
        pre_policy_attribute_assertion_ids=attribute_ids,
        merge_only_diagnostic={
            "passed": merge_only.passed,
            "candidate_count": len(merge_only.element_ids),
            "reconstructable_count": merge_only.reconstructable_count,
            "unresolved_count": len(merge_only.unresolved_element_ids),
            "unresolved_element_ids": merge_only.unresolved_element_ids,
            "field_counts": merge_only.field_counts,
        },
        merge_only_policy_refused=True,
        current_lifecycle_proof=_proof_payload(current_proof),
        alias_remove_lineage={
            "survivor_count": len(lineage_rows),
            "rows": lineage_rows,
            "ordering": "durable_decision_list_position",
            "invalidating_split_unmerge": False,
        },
        source_history_policy={
            "policy_id": policy.policy_id,
            "proven_element_count": len(policy.proven_node_state_history_element_ids),
            "source": "source_history_policy_from_identity_lifecycle_proof",
            "same_store_world_id": WORLD_ID,
            "same_store_revision_id": CANONICAL_REVISION_ID,
            "same_store_payload_sha256": CANONICAL_GRAPH_PAYLOAD_SHA256,
        },
        pre_package_evidence_provenance_ids=pre_package_ep_ids,
        alias_package_proof={
            "passed": alias_proof.passed,
            "residuals": [],
            "blocker_element_ids": list(alias_proof.blocker_element_ids),
            "covered_blocker_element_ids": list(alias_proof.covered_blocker_element_ids),
            "package_row_count": len(alias_proof.package_rows),
            "package_rows": [
                row.model_dump(mode="json") for row in alias_proof.package_rows
            ],
        },
        alias_assertion_policy={
            "policy_id": alias_policy.policy_id,
            "world_id": alias_policy.world_id,
            "canonical_revision_id": alias_policy.canonical_revision_id,
            "canonical_graph_payload_sha256": alias_policy.canonical_graph_payload_sha256,
            "package_proof_sha256": alias_policy.package_proof_sha256,
            "proven_alias_blocker_element_ids": sorted(
                alias_policy.proven_alias_blocker_element_ids
            ),
        },
        policy={
            "policy_id": alias_policy.policy_id,
            "proven_element_count": len(alias_policy.proven_alias_blocker_element_ids),
            "source": "alias_assertion_policy_from_proof",
        },
        post_policy_blockers=migration_blockers,
        attribute_assertion_count=attribute_count if attribute_count is not None else 0,
        evidence_provenance={
            "count": evidence_count if evidence_count is not None else 0,
            "examples": evidence_examples,
        },
        identity_history_count=identity_count,
        contribution_history_count=contribution_count,
        relationship_invariants={
            "canonical": {
                **{
                    key: canonical_relationship[key]
                    for key in EXPECTED_CANONICAL_RELATIONSHIP_INVENTORY
                },
                "residual_edge_ids": sorted(canonical_relationship["residual_edge_ids"]),
            },
            "migration": {
                **{
                    key: migration_relationship[key]
                    for key in EXPECTED_MIGRATION_RELATIONSHIP_INVENTORY
                },
                "residual_edge_ids": sorted(migration_relationship["residual_edge_ids"]),
            },
        },
        historical_575=historical,
        mutation_proof={
            "head_before": head_before.head_revision_id,
            "head_after": head_after.head_revision_id,
            "tree_digest_unchanged": tree_before == tree_after,
            "payload_unchanged": manifest.graph_payload_sha256
            == CANONICAL_GRAPH_PAYLOAD_SHA256,
            "identity_ledger_unchanged": True,
            "aliases_unchanged": True,
            "assertion_support_unchanged": True,
            "source_authority_unchanged": True,
            "contributions_unchanged": True,
            "loaded_store_unchanged": True,
        },
        captain_thrin_package_implemented=True,
        cutover_disposition="CUTOVER_NOT_READY",
        next_slice_recommendation=recommendation,
        diagnostics=diagnostics,
    )


def get_cutover_alias_assertion_package_after_shadow_alias_remove_status(
    root: Path | None = None,
    repo: Path | None = None,
) -> CutoverAliasAssertionPackageAfterShadowAliasRemoveStatusV1:
    try:
        report = compose_cutover_alias_assertion_package_after_shadow_alias_remove(root, repo)
    except CutoverAliasAssertionPackageAfterShadowAliasRemoveError as exc:
        eligibility: Eligibility = (
            "integrity_failure" if exc.code.endswith("mutated") else "ineligible"
        )
        return CutoverAliasAssertionPackageAfterShadowAliasRemoveStatusV1(
            eligibility=eligibility,
            reason=str(exc),
            diagnostics=[exc.code],
        )
    return CutoverAliasAssertionPackageAfterShadowAliasRemoveStatusV1(
        eligibility="eligible",
        canonical_graph_payload_sha256=report.canonical_graph_payload_sha256,
        diagnostics=list(report.diagnostics),
    )


def build_cutover_alias_assertion_package_after_shadow_alias_remove(
    *,
    root: Path | None = None,
    repo: Path | None = None,
    allow_live_world: bool = False,
) -> CutoverAliasAssertionPackageAfterShadowAliasRemoveBuildResultV1:
    del allow_live_world
    repository = _repo(repo)
    report = compose_cutover_alias_assertion_package_after_shadow_alias_remove(root, repository)
    path = _fixture_path(repository)
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = _report_bytes(report)
    path.write_bytes(raw)
    fixture_sha = _sha256_bytes(raw)
    locked = LOCKED_FIXTURE_SHA256.strip()
    diagnostics = list(report.diagnostics)
    if locked and fixture_sha != locked:
        raise _fail("sealed fixture digest mismatch", "fixture_digest_mismatch")
    if not locked:
        diagnostics.append("first_seal_unlocked")
    diagnostics.append("sealed")
    return CutoverAliasAssertionPackageAfterShadowAliasRemoveBuildResultV1(
        fixture_path=str(path),
        fixture_sha256=fixture_sha,
        report=report,
        diagnostics=diagnostics,
    )


def verify_cutover_alias_assertion_package_after_shadow_alias_remove(
    *,
    root: Path | None = None,
    repo: Path | None = None,
) -> CutoverAliasAssertionPackageAfterShadowAliasRemoveVerifyResultV1:
    world_root = _root(root)
    repository = _repo(repo)
    path = _fixture_path(repository)
    if not path.is_file():
        return CutoverAliasAssertionPackageAfterShadowAliasRemoveVerifyResultV1(
            verified=False,
            fixture_path=str(path),
            diagnostics=["fixture_missing"],
        )
    raw = path.read_bytes()
    fixture_sha = _sha256_bytes(raw)
    locked = LOCKED_FIXTURE_SHA256.strip()
    diagnostics: list[str] = []
    if locked and fixture_sha != locked:
        return CutoverAliasAssertionPackageAfterShadowAliasRemoveVerifyResultV1(
            verified=False,
            fixture_path=str(path),
            fixture_sha256=fixture_sha,
            diagnostics=["fixture_digest_mismatch"],
        )
    if not locked:
        diagnostics.append("first_seal_unlocked")
    try:
        stored = CutoverAliasAssertionPackageAfterShadowAliasRemoveReportV1.model_validate(
            json.loads(raw)
        )
        reproduced = compose_cutover_alias_assertion_package_after_shadow_alias_remove(
            world_root, repository
        )
        if _report_bytes(stored) != _report_bytes(reproduced):
            return CutoverAliasAssertionPackageAfterShadowAliasRemoveVerifyResultV1(
                verified=False,
                fixture_path=str(path),
                fixture_sha256=fixture_sha,
                diagnostics=[*diagnostics, "fixture_bytes_not_deterministic"],
            )
    except (
        CutoverAliasAssertionPackageAfterShadowAliasRemoveError,
        OSError,
        ValueError,
        TypeError,
    ) as exc:
        return CutoverAliasAssertionPackageAfterShadowAliasRemoveVerifyResultV1(
            verified=False,
            fixture_path=str(path),
            fixture_sha256=fixture_sha,
            diagnostics=[*diagnostics, type(exc).__name__ + ":" + str(exc)],
        )
    return CutoverAliasAssertionPackageAfterShadowAliasRemoveVerifyResultV1(
        verified=True,
        fixture_path=str(path),
        fixture_sha256=fixture_sha,
        diagnostics=[*diagnostics, "verified", "non_publishing"],
    )
