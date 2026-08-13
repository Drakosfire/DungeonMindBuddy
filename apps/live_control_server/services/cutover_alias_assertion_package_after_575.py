"""CUTOVER successor: reconstruct source-grounded aliases and STOP on identity-derived residuals.

Non-publishing measurement after PR #575 / dispatch base PR #576. Packages the two
current-node source-grounded alias blockers as diagnostic rows. The six
identity-merge shadow aliases remain EVIDENCE_PROVENANCE residuals. This slice
does not seal a partial 8→N package or reclassify those residuals as history.
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
    IDENTITY_DERIVED_REASON,
    AliasAssertionPackageConformanceError,
    prove_alias_assertion_package_v1,
)
from apps.live_control_server.integrations.dungeonmind_kernel.identity_lifecycle_history_conformance_v1 import (
    EXPECTED_ELDRYWILD_FIELD_COUNTS,
    IdentityLifecycleHistoryConformanceError,
    prove_identity_lifecycle_history_v1,
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
    source_history_policy_from_identity_lifecycle_proof,
)
from apps.live_control_server.services import (
    eldyrwild_relationship_node_kind_source_repair as repair_service,
)
from apps.live_control_server.services.cutover_identity_lifecycle_history_after_571 import (
    EXPECTED_CONTRIBUTION_HISTORY_COUNT,
    EXPECTED_IDENTITY_HISTORY_COUNT,
    FIXTURE_RELPATH as PREDECESSOR_FIXTURE_RELPATH,
    LOCKED_FIXTURE_SHA256 as PREDECESSOR_FIXTURE_SHA256,
    _blocker_delta,
    _blocker_row,
    _store_identity_snapshot,
    verify_cutover_identity_lifecycle_history_after_571,
)
from apps.live_control_server.services.cutover_whole_world_reanchor import (
    CANONICAL_RESIDUAL_EDGE_IDS,
    CHANGED_KIND_PATHS,
    EXPECTED_CANONICAL_RELATIONSHIP_INVENTORY,
    EXPECTED_MIGRATION_RELATIONSHIP_INVENTORY,
    MIGRATION_NEWLY_REPRESENTED_EDGE_IDS,
    MIGRATION_RESIDUAL_EDGE_IDS,
    _next_slice_recommendation,
    _normalized_blockers_for_view,
    _projection_diff,
    _raw_blocker_classes,
    _relationship_inventory_from_effective,
    _relationship_inventory_from_repair_proof,
    _sha256_bytes,
    snapshot_source_authority_inventory,
)
from apps.live_control_server.services.cutover_whole_world_repin_after_dm30 import (
    CANONICAL_GRAPH_PAYLOAD_SHA256,
    CANONICAL_REVISION_ID,
    DUNGEONMIND_DEPENDENCY_REF,
    WORLD_ID,
    _classified_index,
    _contract_pins,
    _copy_manifest,
    _git_head,
    _is_descendant,
    _open_exact_canonical,
    _semantic_key,
    _verify_contract_pins,
    _verify_repair_authority,
    _view,
)
from graph_memory.world_supergraph.contribution_store import load_contribution_record


CUTOVER_SCHEMA = "dmb_cutover_alias_assertion_package_after_575_v1"
BUDDY_BASE_SHA = "fda746b99a8a9830280bf1beac126a8221ddedfc"
LOCKED_REPAIR_MANIFEST_SHA256 = (
    "96cc26fc6e99448e8fba5cd6982070c1e29bb058f2b1e8a4ac291f8a0a083247"
)
FIXTURE_RELPATH = (
    "tests/fixtures/dungeonmind_kernel/"
    "eldyrwild_cutover_alias_assertion_package_after_575_v1.json"
)

EXPECTED_EVIDENCE_PROVENANCE_COUNT = 8
EXPECTED_PACKAGED_ALIAS_COUNT = 2
EXPECTED_IDENTITY_DERIVED_ALIAS_COUNT = 6
EXPECTED_PACKAGED_ALIAS_IDS = frozenset(
    {
        "node:node:captain-lysandra-ironveil:field:aliases",
        "node:node:thrin-branchborn:field:aliases",
    }
)
EXPECTED_IDENTITY_DERIVED_ALIAS_IDS = frozenset(
    {
        "node:item_foot_of_statue:field:aliases",
        "node:loc:chilled_warehouse:field:aliases",
        "node:loc:crooked-retort:field:aliases",
        "node:loc:the-council:field:aliases",
        "node:loc:underground-entrance:field:aliases",
        "node:obj:session9:scroll_abyssal:field:aliases",
    }
)
EXPECTED_FIELD_COUNTS = dict(EXPECTED_ELDRYWILD_FIELD_COUNTS)

CutoverDisposition = Literal["CUTOVER_READY", "CUTOVER_NOT_READY"]
Eligibility = Literal["eligible", "ineligible", "integrity_failure"]


class CutoverAliasAssertionPackageAfter575Error(RuntimeError):
    """Fail-closed CUTOVER alias-package successor error."""

    def __init__(self, message: str, *, code: str) -> None:
        super().__init__(message)
        self.code = code


class CutoverAliasAssertionPackageAfter575StatusV1(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_: str = Field(default=CUTOVER_SCHEMA + "_status", alias="schema")
    world_id: str = WORLD_ID
    canonical_revision_id: str = CANONICAL_REVISION_ID
    eligibility: Eligibility
    reason: str | None = None
    diagnostics: list[str] = Field(default_factory=list)
    canonical_graph_payload_sha256: str | None = None
    repair_manifest_sha256: str | None = None
    predecessor_fixture_sha256: str | None = None
    adoption_seam: DurableAdoptionSeamStatusReport | None = None


class CutoverAliasAssertionPackageAfter575ReportV1(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_: str = Field(default=CUTOVER_SCHEMA, alias="schema")
    world_id: str = WORLD_ID
    buddy_repository_base_sha: str
    canonical_revision_id: str
    canonical_graph_payload_sha256: str
    dungeonmind_dependency_ref: str
    dungeonmind_contract_pins: dict[str, str]
    repair_authority: dict[str, Any]
    predecessor: dict[str, Any]
    alias_assertion_proof: dict[str, Any]
    canonical_view: dict[str, Any]
    migration_projection: dict[str, Any]
    classification_delta: dict[str, Any]
    blocker_delta: dict[str, Any]
    relationship_invariants: dict[str, Any]
    adoption_seam: DurableAdoptionSeamStatusReport
    mutation_proof: dict[str, Any]
    cutover_disposition: CutoverDisposition
    next_slice_recommendation: dict[str, Any]
    diagnostics: list[str] = Field(default_factory=list)


class CutoverAliasAssertionPackageAfter575BuildResultV1(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_: str = Field(default=CUTOVER_SCHEMA + "_build_result", alias="schema")
    world_id: str = WORLD_ID
    fixture_path: str
    fixture_sha256: str
    report: CutoverAliasAssertionPackageAfter575ReportV1
    diagnostics: list[str] = Field(default_factory=list)


class CutoverAliasAssertionPackageAfter575VerifyResultV1(BaseModel):
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


def _predecessor_fixture_path(repo: Path | None = None) -> Path:
    return _repo(repo) / PREDECESSOR_FIXTURE_RELPATH


def _fail(message: str, code: str) -> CutoverAliasAssertionPackageAfter575Error:
    return CutoverAliasAssertionPackageAfter575Error(message, code=code)


def _evidence_provenance_ids(elements: list[Any]) -> list[str]:
    ids: list[str] = []
    seen: set[str] = set()
    for element in elements:
        blocker = element.blocker_class
        value = None if blocker is None else blocker.value
        if value != BlockerClass.EVIDENCE_PROVENANCE.value:
            continue
        if element.element_id in seen:
            raise _fail(
                f"duplicate EVIDENCE_PROVENANCE element {element.element_id!r}",
                "evidence_provenance_duplicate",
            )
        seen.add(element.element_id)
        ids.append(element.element_id)
    return sorted(ids)


def _prove_predecessor(root: Path, repo: Path) -> dict[str, Any]:
    path = _predecessor_fixture_path(repo)
    if not path.is_file():
        raise _fail("PR #575 predecessor fixture is missing", "predecessor_fixture_missing")
    before = path.read_bytes()
    sha = _sha256_bytes(before)
    if sha != PREDECESSOR_FIXTURE_SHA256:
        raise _fail(
            "PR #575 predecessor fixture digest mismatch",
            "predecessor_fixture_digest_mismatch",
        )
    verified = verify_cutover_identity_lifecycle_history_after_571(root=root, repo=repo)
    if not verified.verified:
        raise _fail("PR #575 predecessor verifier did not pass", "predecessor_verify_failed")
    after = path.read_bytes()
    if after != before:
        raise _fail("predecessor fixture bytes changed during verify", "predecessor_fixture_mutated")
    return {
        "fixture_path": PREDECESSOR_FIXTURE_RELPATH,
        "fixture_sha256": sha,
        "verified": True,
        "bytes_unchanged": True,
    }


def build_alias_classification_delta(
    *,
    view: str,
    previous_elements: list[Any],
    current_elements: list[Any],
) -> dict[str, Any]:
    previous_index = _classified_index(previous_elements)
    current_index = _classified_index(current_elements)
    if set(previous_index) != set(current_index):
        missing = sorted(set(previous_index) - set(current_index))
        added = sorted(set(current_index) - set(previous_index))
        raise _fail(
            f"{view} classified element id set drifted (missing={missing[:5]}, added={added[:5]})",
            "classified_element_id_set_drift",
        )
    transitions: list[dict[str, Any]] = []
    for element_id in sorted(previous_index):
        previous = previous_index[element_id]
        current = current_index[element_id]
        if _semantic_key(previous) == _semantic_key(current):
            continue
        raise _fail(
            f"{view} unexpected classified-element transition {element_id}",
            "classification_delta_mismatch",
        )
    return {
        "count": 0,
        "packaged_count": 0,
        "identity_derived_count": EXPECTED_IDENTITY_DERIVED_ALIAS_COUNT,
        "element_ids": [],
        "transitions": transitions,
        "lossless": True,
    }


def _compose_report(
    root: Path, repo: Path
) -> CutoverAliasAssertionPackageAfter575ReportV1:
    repository_head = _git_head(repo)
    if not _is_descendant(repo, BUDDY_BASE_SHA):
        raise _fail(
            f"Buddy HEAD {repository_head} does not descend from {BUDDY_BASE_SHA}",
            "buddy_base_mismatch",
        )
    if CURRENT_V5_TARGET.dungeonmind_dependency_ref != DUNGEONMIND_DEPENDENCY_REF:
        raise _fail("DungeonMind dependency pin mismatch", "dependency_pin_mismatch")

    predecessor = _prove_predecessor(root, repo)
    head_before, manifest, base_store, tree_before = _open_exact_canonical(root)
    source_before = snapshot_source_authority_inventory(root)
    identity_before = _store_identity_snapshot(base_store)
    alias_before = _sha256_bytes(
        json.dumps(
            {node_id: list(node.aliases or []) for node_id, node in sorted(base_store.nodes.items())},
            sort_keys=True,
        ).encode("utf-8")
    )
    predecessor_before = _sha256_bytes(_predecessor_fixture_path(repo).read_bytes())
    repair_path = repo / repair_service.MANIFEST_RELPATH
    repair_before = _sha256_bytes(repair_path.read_bytes()) if repair_path.is_file() else None

    try:
        identity_proof = prove_identity_lifecycle_history_v1(
            base_store,
            world_id=WORLD_ID,
            canonical_revision_id=CANONICAL_REVISION_ID,
            canonical_graph_payload_sha256=CANONICAL_GRAPH_PAYLOAD_SHA256,
            expected_field_counts=EXPECTED_FIELD_COUNTS,
        )
    except IdentityLifecycleHistoryConformanceError as exc:
        raise _fail(str(exc), exc.code) from exc
    if not identity_proof.passed:
        raise _fail("identity-lifecycle proof required for post-575 baseline", "identity_lifecycle_proof_failed")
    identity_policy = source_history_policy_from_identity_lifecycle_proof(identity_proof)

    predecessor_classified: list[Any] = []
    predecessor_v5 = whole_world_v5._analyze_loaded_buddy_world_store_v5(
        root=root,
        world_id=WORLD_ID,
        revision_id=CANONICAL_REVISION_ID,
        manifest=manifest,
        store=base_store,
        classified_out=predecessor_classified,
        source_history_policy=identity_policy,
    )
    _verify_contract_pins(predecessor_v5)
    evidence_ids = _evidence_provenance_ids(predecessor_classified)
    if len(evidence_ids) != EXPECTED_EVIDENCE_PROVENANCE_COUNT:
        raise _fail(
            f"post-575 EVIDENCE_PROVENANCE inventory drifted: {len(evidence_ids)} != "
            f"{EXPECTED_EVIDENCE_PROVENANCE_COUNT}",
            "stale_evidence_provenance_inventory",
        )

    def _load_contribution(contribution_id: str):
        return load_contribution_record(root, WORLD_ID, contribution_id)

    try:
        proof = prove_alias_assertion_package_v1(
            base_store,
            world_id=WORLD_ID,
            canonical_revision_id=CANONICAL_REVISION_ID,
            canonical_graph_payload_sha256=CANONICAL_GRAPH_PAYLOAD_SHA256,
            contribution_loader=_load_contribution,
            expected_blocker_element_ids=evidence_ids,
        )
    except AliasAssertionPackageConformanceError as exc:
        raise _fail(str(exc), exc.code) from exc
    if proof.passed or proof.residual_count == 0:
        raise _fail(
            "alias-package proof cannot pass while identity-derived residuals remain STOPs",
            "identity_derived_alias_requires_identity_replay",
        )
    if set(proof.blocker_element_ids) != set(evidence_ids):
        raise _fail(
            "alias-package blocker IDs drifted from EVIDENCE_PROVENANCE inventory",
            "alias_blocker_set_mismatch",
        )
    if set(proof.covered_blocker_element_ids) != EXPECTED_PACKAGED_ALIAS_IDS:
        raise _fail("packaged alias IDs drifted", "alias_package_proof_failed")
    residual_ids = {row.blocker_element_id for row in proof.residuals}
    if residual_ids != EXPECTED_IDENTITY_DERIVED_ALIAS_IDS:
        raise _fail(
            f"identity-derived residual IDs drifted: {sorted(residual_ids)}",
            "identity_derived_alias_requires_identity_replay",
        )
    if any(row.reason_code != IDENTITY_DERIVED_REASON for row in proof.residuals):
        raise _fail(
            "alias residuals include a non-identity-derived reason",
            "alias_package_proof_failed",
        )
    if len(residual_ids) != EXPECTED_IDENTITY_DERIVED_ALIAS_COUNT:
        raise _fail("identity-derived alias count drifted", "alias_package_proof_failed")

    canonical_classified: list[Any] = []
    canonical_v5 = whole_world_v5._analyze_loaded_buddy_world_store_v5(
        root=root,
        world_id=WORLD_ID,
        revision_id=CANONICAL_REVISION_ID,
        manifest=_copy_manifest(manifest),
        store=base_store,
        classified_out=canonical_classified,
        source_history_policy=identity_policy,
    )
    _verify_contract_pins(canonical_v5)

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

    repair_pin, repair_proof = _verify_repair_authority(root, repo)
    overlay_store = repair_service._overlay_store(base_store)
    if enumerate_durable_element_ids(base_store) != enumerate_durable_element_ids(overlay_store):
        raise _fail("migration overlay changed durable element IDs", "durable_id_set_changed")
    changed_paths = _projection_diff(base_store, overlay_store)
    if set(changed_paths) != set(CHANGED_KIND_PATHS) or len(changed_paths) != len(CHANGED_KIND_PATHS):
        raise _fail(
            f"migration projection changed unexpected paths: {changed_paths}",
            "projection_diff_mismatch",
        )

    overlay_proof = prove_alias_assertion_package_v1(
        overlay_store,
        world_id=WORLD_ID,
        canonical_revision_id=CANONICAL_REVISION_ID,
        canonical_graph_payload_sha256=CANONICAL_GRAPH_PAYLOAD_SHA256,
        contribution_loader=_load_contribution,
        expected_blocker_element_ids=evidence_ids,
    )
    if overlay_proof.model_dump(mode="json", by_alias=True) != proof.model_dump(
        mode="json", by_alias=True
    ):
        raise _fail("#566 overlay changed the alias-package proof", "alias_package_projection_drift")

    predecessor_migration_classified: list[Any] = []
    predecessor_overlay_v5 = whole_world_v5._analyze_loaded_buddy_world_store_v5(
        root=root,
        world_id=WORLD_ID,
        revision_id=CANONICAL_REVISION_ID,
        manifest=_copy_manifest(manifest),
        store=overlay_store,
        classified_out=predecessor_migration_classified,
        source_history_policy=identity_policy,
    )
    if set(_evidence_provenance_ids(predecessor_migration_classified)) != set(evidence_ids):
        raise _fail(
            "migration EVIDENCE_PROVENANCE IDs drifted from canonical",
            "alias_blocker_set_mismatch",
        )

    migration_classified: list[Any] = []
    overlay_v5 = whole_world_v5._analyze_loaded_buddy_world_store_v5(
        root=root,
        world_id=WORLD_ID,
        revision_id=CANONICAL_REVISION_ID,
        manifest=_copy_manifest(manifest),
        store=overlay_store,
        classified_out=migration_classified,
        source_history_policy=identity_policy,
    )
    if overlay_v5.unaccounted_durable_elements != 0:
        raise _fail("migration overlay has unaccounted durable elements", "overlay_unaccounted")

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
    predecessor_canonical_classes = set(_raw_blocker_classes(predecessor_v5)) | {
        BlockerClass.RELATIONSHIP_PREDICATE.value
    }
    predecessor_migration_classes = set(_raw_blocker_classes(predecessor_overlay_v5)) | {
        BlockerClass.RELATIONSHIP_PREDICATE.value
    }
    predecessor_canonical_blockers = _normalized_blockers_for_view(
        predecessor_v5,
        residual_edge_ids=canonical_relationship["residual_edge_ids"],
        projection=False,
        canonical_classes=predecessor_canonical_classes,
        migration_classes=predecessor_migration_classes,
    )
    predecessor_migration_blockers = _normalized_blockers_for_view(
        predecessor_overlay_v5,
        residual_edge_ids=migration_relationship["residual_edge_ids"],
        projection=True,
        canonical_classes=predecessor_canonical_classes,
        migration_classes=predecessor_migration_classes,
    )
    canonical_classes = set(_raw_blocker_classes(canonical_v5)) | {
        BlockerClass.RELATIONSHIP_PREDICATE.value
    }
    migration_classes = set(_raw_blocker_classes(overlay_v5)) | {
        BlockerClass.RELATIONSHIP_PREDICATE.value
    }
    canonical_blockers = _normalized_blockers_for_view(
        canonical_v5,
        residual_edge_ids=canonical_relationship["residual_edge_ids"],
        projection=False,
        canonical_classes=canonical_classes,
        migration_classes=migration_classes,
    )
    migration_blockers = _normalized_blockers_for_view(
        overlay_v5,
        residual_edge_ids=migration_relationship["residual_edge_ids"],
        projection=True,
        canonical_classes=canonical_classes,
        migration_classes=migration_classes,
    )

    for view_name, blockers in (("canonical", canonical_blockers), ("migration", migration_blockers)):
        evidence = _blocker_row(blockers, BlockerClass.EVIDENCE_PROVENANCE.value)
        if evidence is None or evidence["count"] != EXPECTED_EVIDENCE_PROVENANCE_COUNT:
            raise _fail(
                f"EVIDENCE_PROVENANCE drifted after residual STOP in {view_name}",
                "evidence_provenance_not_cleared",
            )
        if any(row["blocker_class"] == BlockerClass.ATTRIBUTE_ASSERTION.value for row in blockers):
            raise _fail(f"ATTRIBUTE_ASSERTION reappeared in {view_name}", "attribute_assertion_reintroduced")
        identity = _blocker_row(blockers, BlockerClass.IDENTITY_HISTORY.value)
        if identity is None or identity["count"] != EXPECTED_IDENTITY_HISTORY_COUNT:
            raise _fail(f"{view_name} IDENTITY_HISTORY drifted", "identity_history_weakened")
        contribution = _blocker_row(blockers, BlockerClass.CONTRIBUTION_HISTORY.value)
        if contribution is None or contribution["count"] != EXPECTED_CONTRIBUTION_HISTORY_COUNT:
            raise _fail(
                f"{view_name} CONTRIBUTION_HISTORY drifted",
                "contribution_history_identity_shadow_leak",
            )

    canonical_delta = build_alias_classification_delta(
        view="canonical",
        previous_elements=predecessor_classified,
        current_elements=canonical_classified,
    )
    migration_delta = build_alias_classification_delta(
        view="migration",
        previous_elements=predecessor_migration_classified,
        current_elements=migration_classified,
    )
    if canonical_delta["element_ids"] != migration_delta["element_ids"]:
        raise _fail(
            "canonical/migration classification element IDs drifted",
            "classification_delta_mismatch",
        )
    classification_delta = {
        "count": canonical_delta["count"],
        "packaged_count": canonical_delta["packaged_count"],
        "identity_derived_count": canonical_delta["identity_derived_count"],
        "element_ids": canonical_delta["element_ids"],
        "transitions": canonical_delta["transitions"],
        "migration_transitions": migration_delta["transitions"],
        "lossless": True,
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
    blocker_delta = {
        "canonical": _blocker_delta(
            previous_blockers=predecessor_canonical_blockers,
            current_blockers=canonical_blockers,
        ),
        "migration": _blocker_delta(
            previous_blockers=predecessor_migration_blockers,
            current_blockers=migration_blockers,
        ),
    }
    if BlockerClass.EVIDENCE_PROVENANCE.value in blocker_delta["migration"]["cleared_blocker_classes"]:
        raise _fail(
            "blocker_delta cleared EVIDENCE_PROVENANCE despite identity-derived residuals",
            "blocker_delta_incomplete",
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

    head_after = kernel.open_world_graph_head(root, WORLD_ID)
    tree_after = snapshot_world_graph_tree_digest(root, WORLD_ID)
    source_after = snapshot_source_authority_inventory(root)
    identity_after = _store_identity_snapshot(base_store)
    alias_after = _sha256_bytes(
        json.dumps(
            {node_id: list(node.aliases or []) for node_id, node in sorted(base_store.nodes.items())},
            sort_keys=True,
        ).encode("utf-8")
    )
    predecessor_after = _sha256_bytes(_predecessor_fixture_path(repo).read_bytes())
    repair_after = _sha256_bytes(repair_path.read_bytes()) if repair_path.is_file() else None
    if head_after.head_revision_id != head_before.head_revision_id or tree_after != tree_before:
        raise _fail("CUTOVER analysis mutated the World Graph", "world_graph_mutated")
    if source_after != source_before:
        raise _fail("CUTOVER analysis mutated source/provenance authority families", "source_authority_mutated")
    if identity_after != identity_before:
        raise _fail("CUTOVER analysis mutated identity authority", "identity_authority_mutated")
    if alias_after != alias_before:
        raise _fail("CUTOVER analysis mutated node aliases", "node_aliases_mutated")
    if predecessor_after != predecessor_before:
        raise _fail("CUTOVER analysis mutated the PR #575 fixture", "predecessor_fixture_mutated")
    if repair_after != repair_before:
        raise _fail("CUTOVER analysis mutated the #566 repair manifest", "repair_manifest_mutated")

    mutation_proof = {
        "head_revision_id": {
            "before": head_before.head_revision_id,
            "after": head_after.head_revision_id,
        },
        "graph_tree_digest": {"before": tree_before, "after": tree_after},
        "source_authority": {"before": source_before, "after": source_after},
        "identity_authority": {"before": identity_before, "after": identity_after},
        "node_aliases": {"before": alias_before, "after": alias_after},
        "predecessor_fixture_sha256": {"before": predecessor_before, "after": predecessor_after},
        "repair_manifest_sha256": {"before": repair_before, "after": repair_after},
        "unchanged": True,
    }
    relationship_invariants = {
        "canonical": {
            **EXPECTED_CANONICAL_RELATIONSHIP_INVENTORY,
            "residual_edge_ids": sorted(CANONICAL_RESIDUAL_EDGE_IDS),
        },
        "migration": {
            **EXPECTED_MIGRATION_RELATIONSHIP_INVENTORY,
            "residual_edge_ids": sorted(MIGRATION_RESIDUAL_EDGE_IDS),
            "newly_represented_edge_ids": sorted(MIGRATION_NEWLY_REPRESENTED_EDGE_IDS),
        },
    }
    diagnostics = [
        "non_publishing",
        "predecessor:PR575",
        "dispatch_base:PR576",
        "alias_package_policy:legacy",
        "identity_derived_aliases_remain_residuals",
        "partial_package_not_sealed",
        "node_aliases_unchanged",
        "next_slice_derived_from_normalized_blocker_stages",
    ]
    report = CutoverAliasAssertionPackageAfter575ReportV1(
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
        },
        predecessor=predecessor,
        alias_assertion_proof=proof.model_dump(mode="json", by_alias=True),
        canonical_view=canonical_view,
        migration_projection=migration_view,
        classification_delta=classification_delta,
        blocker_delta=blocker_delta,
        relationship_invariants=relationship_invariants,
        adoption_seam=adoption_seam,
        mutation_proof=mutation_proof,
        cutover_disposition=disposition,
        next_slice_recommendation=recommendation,
        diagnostics=diagnostics,
    )
    _assert_report_invariants(report)
    return report


def _assert_report_invariants(report: CutoverAliasAssertionPackageAfter575ReportV1) -> None:
    if report.canonical_revision_id != CANONICAL_REVISION_ID:
        raise _fail("report revision pin mismatch", "report_pin_mismatch")
    if report.canonical_graph_payload_sha256 != CANONICAL_GRAPH_PAYLOAD_SHA256:
        raise _fail("report payload pin mismatch", "report_pin_mismatch")
    if report.cutover_disposition != "CUTOVER_NOT_READY":
        raise _fail("CUTOVER disposition must remain NOT_READY", "cutover_ready_regression")
    proof = report.alias_assertion_proof
    residual_ids = {row["blocker_element_id"] for row in proof.get("residuals", [])}
    if proof.get("passed") is True or residual_ids != EXPECTED_IDENTITY_DERIVED_ALIAS_IDS:
        raise _fail(
            "report alias-package proof is not the identity-derived residual STOP",
            "identity_derived_alias_requires_identity_replay",
        )
    if set(proof.get("covered_blocker_element_ids", [])) != EXPECTED_PACKAGED_ALIAS_IDS:
        raise _fail("report packaged alias IDs drifted", "alias_package_proof_failed")
    delta = report.classification_delta
    if not delta.get("lossless") or delta.get("count") != 0:
        raise _fail(
            "classification_delta must be empty while identity-derived residuals remain STOPs",
            "classification_delta_mismatch",
        )
    for view_name in ("canonical_view", "migration_projection"):
        view = getattr(report, view_name)
        evidence = _blocker_row(view["blockers"], BlockerClass.EVIDENCE_PROVENANCE.value)
        if evidence is None or evidence["count"] != EXPECTED_EVIDENCE_PROVENANCE_COUNT:
            raise _fail(
                f"{view_name} EVIDENCE_PROVENANCE drifted",
                "evidence_provenance_not_cleared",
            )
        contribution = _blocker_row(view["blockers"], BlockerClass.CONTRIBUTION_HISTORY.value)
        if contribution is None or contribution["count"] != EXPECTED_CONTRIBUTION_HISTORY_COUNT:
            raise _fail(f"{view_name} CONTRIBUTION_HISTORY drifted", "contribution_history_identity_shadow_leak")
        identity = _blocker_row(view["blockers"], BlockerClass.IDENTITY_HISTORY.value)
        if identity is None or identity["count"] != EXPECTED_IDENTITY_HISTORY_COUNT:
            raise _fail(f"{view_name} IDENTITY_HISTORY drifted", "identity_history_weakened")
    for delta_view in ("canonical", "migration"):
        changed = {row["blocker_class"] for row in report.blocker_delta[delta_view]["rows"]}
        if BlockerClass.CONTRIBUTION_HISTORY.value in changed:
            raise _fail(
                f"{delta_view} blocker_delta recorded CONTRIBUTION_HISTORY change",
                "contribution_history_identity_shadow_leak",
            )
        if BlockerClass.IDENTITY_HISTORY.value in changed:
            raise _fail(
                f"{delta_view} blocker_delta recorded IDENTITY_HISTORY change",
                "identity_history_weakened",
            )
    if not report.mutation_proof.get("unchanged"):
        raise _fail("mutation proof is not unchanged", "world_graph_mutated")


def get_cutover_alias_assertion_package_after_575_status(
    root: Path | None = None,
    *,
    repo: Path | None = None,
) -> CutoverAliasAssertionPackageAfter575StatusV1:
    world_root = _root(root)
    repository = _repo(repo)
    diagnostics: list[str] = []
    try:
        if not _is_descendant(repository, BUDDY_BASE_SHA):
            diagnostics.append("buddy_base_mismatch")
        predecessor_path = _predecessor_fixture_path(repository)
        predecessor_sha = (
            _sha256_bytes(predecessor_path.read_bytes()) if predecessor_path.is_file() else None
        )
        if predecessor_sha != PREDECESSOR_FIXTURE_SHA256:
            diagnostics.append("predecessor_fixture_digest_mismatch")
        graph_manifest = kernel.load_world_graph_revision_manifest(
            world_root, WORLD_ID, CANONICAL_REVISION_ID
        )
        payload_sha = graph_manifest.graph_payload_sha256
        if graph_manifest.revision_id != CANONICAL_REVISION_ID:
            diagnostics.append("canonical_revision_mismatch")
        if payload_sha != CANONICAL_GRAPH_PAYLOAD_SHA256:
            diagnostics.append("canonical_payload_mismatch")
        adoption_seam = whole_world_v4.inspect_dungeonmind_durable_adoption_seam()
        eligibility: Eligibility = "eligible" if not diagnostics else "ineligible"
        return CutoverAliasAssertionPackageAfter575StatusV1(
            eligibility=eligibility,
            reason=None if eligibility == "eligible" else "stale_input",
            diagnostics=diagnostics,
            canonical_graph_payload_sha256=payload_sha,
            predecessor_fixture_sha256=predecessor_sha,
            adoption_seam=adoption_seam,
        )
    except Exception as exc:  # noqa: BLE001 — status must fail closed, not raise
        diagnostics.append(type(exc).__name__)
        return CutoverAliasAssertionPackageAfter575StatusV1(
            eligibility="integrity_failure",
            reason=str(exc),
            diagnostics=diagnostics,
        )


def build_cutover_alias_assertion_package_after_575(
    *,
    root: Path | None = None,
    repo: Path | None = None,
    allow_live_world: bool = False,
) -> CutoverAliasAssertionPackageAfter575BuildResultV1:
    del allow_live_world
    world_root = _root(root)
    repository = _repo(repo)
    _compose_report(world_root, repository)
    path = _fixture_path(repository)
    if path.is_file():
        raise _fail(
            "partial alias-package fixture must not exist while identity-derived residuals remain",
            "identity_derived_alias_requires_identity_replay",
        )
    raise _fail(
        "six identity-derived alias residuals remain; do not seal a partial 8→N package",
        "identity_derived_alias_requires_identity_replay",
    )


def verify_cutover_alias_assertion_package_after_575(
    *,
    root: Path | None = None,
    repo: Path | None = None,
) -> CutoverAliasAssertionPackageAfter575VerifyResultV1:
    world_root = _root(root)
    repository = _repo(repo)
    path = _fixture_path(repository)
    if path.is_file():
        return CutoverAliasAssertionPackageAfter575VerifyResultV1(
            verified=False,
            fixture_path=str(path),
            diagnostics=["partial_alias_package_fixture_must_not_exist"],
        )
    try:
        reproduced = _compose_report(world_root, repository)
        _assert_report_invariants(reproduced)
    except (
        CutoverAliasAssertionPackageAfter575Error,
        OSError,
        ValueError,
        TypeError,
    ) as exc:
        return CutoverAliasAssertionPackageAfter575VerifyResultV1(
            verified=False,
            fixture_path=str(path),
            diagnostics=[type(exc).__name__ + ":" + str(exc)],
        )
    return CutoverAliasAssertionPackageAfter575VerifyResultV1(
        verified=True,
        fixture_path=str(path),
        diagnostics=["residual_stop_verified"],
    )
