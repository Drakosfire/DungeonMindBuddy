"""CUTOVER successor: classify proven identity-lifecycle shadow as history.

Non-publishing measurement after PR #571. Proves the 28 ATTRIBUTE_ASSERTION
paths are reconstructable identity-lifecycle shadow, classifies only those
proven paths as SOURCE_MIGRATION_HISTORY, and preserves IDENTITY_HISTORY.
Does not mutate World Graph or source authority.
"""

from __future__ import annotations

import json
import os
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
from apps.live_control_server.integrations.dungeonmind_kernel.identity_lifecycle_history_conformance_v1 import (
    EXPECTED_ELDRYWILD_FIELD_COUNTS,
    IdentityLifecycleHistoryConformanceError,
    IdentityLifecycleHistoryConformanceV1,
    prove_identity_lifecycle_history_v1,
)
from apps.live_control_server.integrations.dungeonmind_kernel.relationship_effective_conformance_v1 import (
    analyze_relationship_effective_conformance_v1,
)
from apps.live_control_server.integrations.dungeonmind_kernel.whole_world_conformance import (
    BlockerClass,
    DurableAdoptionSeamStatusReport,
    SemanticClassification,
    enumerate_durable_element_ids,
    snapshot_world_graph_tree_digest,
)
from apps.live_control_server.integrations.dungeonmind_kernel.whole_world_conformance_v4 import (
    CURRENT_V5_TARGET,
    LEGACY_SOURCE_HISTORY_POLICY,
    source_history_policy_from_identity_lifecycle_proof,
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
    _json_bytes,
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
    EXPECTED_CLASSIFIED_TRANSITION_ELEMENT_IDS,
    FIXTURE_RELPATH as PREDECESSOR_FIXTURE_RELPATH,
    LOCKED_FIXTURE_SHA256 as PREDECESSOR_FIXTURE_SHA256,
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
    verify_cutover_whole_world_repin_after_dm30,
)


CUTOVER_SCHEMA = "dmb_cutover_identity_lifecycle_history_after_571_v1"
BUDDY_BASE_SHA = "9d5efb7eaa92a4890bd49db45130e5843777c8b9"
LOCKED_REPAIR_MANIFEST_SHA256 = (
    "96cc26fc6e99448e8fba5cd6982070c1e29bb058f2b1e8a4ac291f8a0a083247"
)
FIXTURE_RELPATH = (
    "tests/fixtures/dungeonmind_kernel/"
    "eldyrwild_cutover_identity_lifecycle_history_after_571_v1.json"
)
# Empty until first seal; nonempty enforces exact match thereafter.
LOCKED_FIXTURE_SHA256 = (
    "1a2cd8f9c47b223d4623fccbe1c988dd8d3eb1c8796078a32a32720f51ef000b"
)

EXPECTED_ATTRIBUTE_ASSERTION_COUNT = 28
EXPECTED_IDENTITY_HISTORY_COUNT = 14
EXPECTED_CONTRIBUTION_HISTORY_COUNT = 5285
EXPECTED_EVIDENCE_PROVENANCE_COUNT = 8
EXPECTED_FIELD_COUNTS = dict(EXPECTED_ELDRYWILD_FIELD_COUNTS)

CutoverDisposition = Literal["CUTOVER_READY", "CUTOVER_NOT_READY"]
Eligibility = Literal["eligible", "ineligible", "integrity_failure"]


class CutoverIdentityLifecycleHistoryAfter571Error(RuntimeError):
    """Fail-closed CUTOVER identity-lifecycle successor error."""

    def __init__(self, message: str, *, code: str) -> None:
        super().__init__(message)
        self.code = code


class CutoverIdentityLifecycleHistoryAfter571StatusV1(BaseModel):
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


class CutoverIdentityLifecycleHistoryAfter571ReportV1(BaseModel):
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
    identity_lifecycle_proof: dict[str, Any]
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


class CutoverIdentityLifecycleHistoryAfter571BuildResultV1(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_: str = Field(default=CUTOVER_SCHEMA + "_build_result", alias="schema")
    world_id: str = WORLD_ID
    fixture_path: str
    fixture_sha256: str
    report: CutoverIdentityLifecycleHistoryAfter571ReportV1
    diagnostics: list[str] = Field(default_factory=list)


class CutoverIdentityLifecycleHistoryAfter571VerifyResultV1(BaseModel):
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


def _fail(message: str, code: str) -> CutoverIdentityLifecycleHistoryAfter571Error:
    return CutoverIdentityLifecycleHistoryAfter571Error(message, code=code)


def _canonical_json_sha(payload: Any) -> str:
    raw = (
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True, default=str)
        + "\n"
    ).encode("utf-8")
    return _sha256_bytes(raw)


def _store_identity_snapshot(store: Any) -> dict[str, str]:
    return {
        "identity_decisions": _canonical_json_sha(list(store.identity_decisions)),
        "identity_redirects": _canonical_json_sha(
            [item.model_dump(mode="json") for item in store.identity_redirects]
        ),
        "identity_merge_records": _canonical_json_sha(
            [item.model_dump(mode="json") for item in store.identity_merge_records]
        ),
        "node_state": _canonical_json_sha(
            {
                node_id: dict(node.state)
                for node_id, node in sorted(store.nodes.items())
            }
        ),
    }


def _blocker_count(blockers: list[dict[str, Any]], blocker_class: str) -> int | None:
    for row in blockers:
        if row["blocker_class"] == blocker_class:
            return int(row["count"])
    return None


def _blocker_row(blockers: list[dict[str, Any]], blocker_class: str) -> dict[str, Any] | None:
    for row in blockers:
        if row["blocker_class"] == blocker_class:
            return row
    return None


def _attribute_assertion_ids(elements: list[Any]) -> list[str]:
    ids: list[str] = []
    seen: set[str] = set()
    for element in elements:
        blocker = element.blocker_class
        value = None if blocker is None else blocker.value
        if value != BlockerClass.ATTRIBUTE_ASSERTION.value:
            continue
        if element.element_id in seen:
            raise _fail(
                f"duplicate ATTRIBUTE_ASSERTION element {element.element_id!r}",
                "attribute_assertion_duplicate",
            )
        seen.add(element.element_id)
        ids.append(element.element_id)
    return sorted(ids)


def _prove_predecessor(root: Path, repo: Path) -> dict[str, Any]:
    path = _predecessor_fixture_path(repo)
    if not path.is_file():
        raise _fail("PR #571 predecessor fixture is missing", "predecessor_fixture_missing")
    before = path.read_bytes()
    sha = _sha256_bytes(before)
    if sha != PREDECESSOR_FIXTURE_SHA256:
        raise _fail(
            "PR #571 predecessor fixture digest mismatch",
            "predecessor_fixture_digest_mismatch",
        )
    verified = verify_cutover_whole_world_repin_after_dm30(root=root, repo=repo)
    if not verified.verified:
        raise _fail("PR #571 predecessor verifier did not pass", "predecessor_verify_failed")
    payload = json.loads(before.decode("utf-8"))
    migration_blockers = payload["migration_projection"]["blockers"]
    attribute_count = _blocker_count(
        migration_blockers, BlockerClass.ATTRIBUTE_ASSERTION.value
    )
    if attribute_count != EXPECTED_ATTRIBUTE_ASSERTION_COUNT:
        raise _fail(
            f"predecessor ATTRIBUTE_ASSERTION count {attribute_count} != "
            f"{EXPECTED_ATTRIBUTE_ASSERTION_COUNT}",
            "predecessor_attribute_count_mismatch",
        )
    classified = payload["target_contract_delta"]["classified_element_transitions"]
    sealed = classified.get("sealed_element_ids")
    if set(sealed) != set(EXPECTED_CLASSIFIED_TRANSITION_ELEMENT_IDS):
        raise _fail(
            "predecessor thread classified-element transitions drifted",
            "predecessor_thread_transition_mismatch",
        )
    after = path.read_bytes()
    if after != before:
        raise _fail("predecessor fixture bytes changed during verify", "predecessor_fixture_mutated")
    return {
        "fixture_path": PREDECESSOR_FIXTURE_RELPATH,
        "fixture_sha256": sha,
        "verified": True,
        "attribute_assertion_count": attribute_count,
        "thread_classified_element_ids": sorted(EXPECTED_CLASSIFIED_TRANSITION_ELEMENT_IDS),
        "bytes_unchanged": True,
    }


def _proof_payload(proof: IdentityLifecycleHistoryConformanceV1) -> dict[str, Any]:
    return proof.model_dump(mode="json", by_alias=True)


def _explain_identity_transition(
    *,
    element_id: str,
    proof_by_id: dict[str, Any],
) -> str:
    row = proof_by_id.get(element_id)
    if row is None:
        return "unexpected classified-element transition without identity-lifecycle proof"
    return str(row.rationale)


def build_identity_classification_delta(
    *,
    view: str,
    previous_elements: list[Any],
    current_elements: list[Any],
    proof: IdentityLifecycleHistoryConformanceV1,
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
    proof_by_id = {row.element_id: row for row in proof.rows}
    expected_ids = set(proof.element_ids)
    transitions: list[dict[str, Any]] = []
    for element_id in sorted(previous_index):
        previous = previous_index[element_id]
        current = current_index[element_id]
        if _semantic_key(previous) == _semantic_key(current):
            continue
        transitions.append(
            {
                "view": view,
                "element_id": element_id,
                "element_family": current["element_family"],
                "previous": previous,
                "current": current,
                "explanation": _explain_identity_transition(
                    element_id=element_id,
                    proof_by_id=proof_by_id,
                ),
            }
        )
    observed = {row["element_id"] for row in transitions}
    if observed != expected_ids:
        raise _fail(
            f"{view} classification transitions {sorted(observed)} != proof {sorted(expected_ids)}",
            "classification_delta_mismatch",
        )
    if len(transitions) != EXPECTED_ATTRIBUTE_ASSERTION_COUNT:
        raise _fail(
            f"{view} classification transition count {len(transitions)} != "
            f"{EXPECTED_ATTRIBUTE_ASSERTION_COUNT}",
            "classification_delta_mismatch",
        )
    field_counts: dict[str, int] = {
        "identity_state": 0,
        "last_identity_decision_id": 0,
        "merged_into": 0,
    }
    for row in transitions:
        previous = row["previous"]
        current = row["current"]
        if previous["classification"] != SemanticClassification.DUNGEONMIND_SEMANTIC_CONTRACT_GAP.value:
            raise _fail(
                f"{view} {row['element_id']} previous classification is not contract gap",
                "classification_delta_mismatch",
            )
        if previous["blocker_class"] != BlockerClass.ATTRIBUTE_ASSERTION.value:
            raise _fail(
                f"{view} {row['element_id']} previous blocker is not ATTRIBUTE_ASSERTION",
                "classification_delta_mismatch",
            )
        if current["classification"] != SemanticClassification.SOURCE_MIGRATION_HISTORY.value:
            raise _fail(
                f"{view} {row['element_id']} current classification is not SOURCE_MIGRATION_HISTORY",
                "classification_delta_mismatch",
            )
        if current["blocker_class"] is not None:
            raise _fail(
                f"{view} {row['element_id']} current still carries a blocker",
                "classification_delta_mismatch",
            )
        field = row["element_id"].rsplit(":", 1)[-1]
        if field not in field_counts:
            raise _fail(
                f"{view} unexpected identity-lifecycle field {field!r}",
                "classification_delta_mismatch",
            )
        field_counts[field] += 1
    if field_counts != EXPECTED_FIELD_COUNTS:
        raise _fail(
            f"{view} classification field counts {field_counts} != {EXPECTED_FIELD_COUNTS}",
            "classification_delta_mismatch",
        )
    return {
        "count": len(transitions),
        "field_counts": field_counts,
        "element_ids": [row["element_id"] for row in transitions],
        "transitions": transitions,
        "lossless": True,
    }


def _blocker_delta(
    *,
    previous_blockers: list[dict[str, Any]],
    current_blockers: list[dict[str, Any]],
) -> dict[str, Any]:
    previous_map = {row["blocker_class"]: row for row in previous_blockers}
    current_map = {row["blocker_class"]: row for row in current_blockers}
    rows: list[dict[str, Any]] = []
    for blocker_class in sorted(set(previous_map) | set(current_map)):
        prev = previous_map.get(blocker_class)
        curr = current_map.get(blocker_class)
        prev_count = None if prev is None else prev["count"]
        curr_count = None if curr is None else curr["count"]
        if prev == curr:
            continue
        rows.append(
            {
                "blocker_class": blocker_class,
                "predecessor_count": prev_count,
                "successor_count": curr_count,
                "predecessor_stage": None if prev is None else prev.get("blocking_stage"),
                "successor_stage": None if curr is None else curr.get("blocking_stage"),
                "predecessor_owner": None if prev is None else prev.get("responsible_repo"),
                "successor_owner": None if curr is None else curr.get("responsible_repo"),
            }
        )
    return {"rows": rows, "cleared_blocker_classes": sorted(set(previous_map) - set(current_map))}


def _compose_report(
    root: Path, repo: Path
) -> CutoverIdentityLifecycleHistoryAfter571ReportV1:
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
    predecessor_before = _sha256_bytes(_predecessor_fixture_path(repo).read_bytes())
    repair_path = repo / repair_service.MANIFEST_RELPATH
    repair_before = _sha256_bytes(repair_path.read_bytes()) if repair_path.is_file() else None

    predecessor_classified: list[Any] = []
    predecessor_v5 = whole_world_v5._analyze_loaded_buddy_world_store_v5(
        root=root,
        world_id=WORLD_ID,
        revision_id=CANONICAL_REVISION_ID,
        manifest=manifest,
        store=base_store,
        classified_out=predecessor_classified,
        source_history_policy=LEGACY_SOURCE_HISTORY_POLICY,
    )
    _verify_contract_pins(predecessor_v5)
    attribute_ids = _attribute_assertion_ids(predecessor_classified)
    if len(attribute_ids) != EXPECTED_ATTRIBUTE_ASSERTION_COUNT:
        raise _fail(
            (
                "predecessor-compatible v5 ATTRIBUTE_ASSERTION inventory drifted: "
                f"{len(attribute_ids)} != {EXPECTED_ATTRIBUTE_ASSERTION_COUNT}"
            ),
            "stale_attribute_assertion_inventory",
        )

    try:
        proof = prove_identity_lifecycle_history_v1(
            base_store,
            world_id=WORLD_ID,
            canonical_revision_id=CANONICAL_REVISION_ID,
            canonical_graph_payload_sha256=CANONICAL_GRAPH_PAYLOAD_SHA256,
            expected_field_counts=EXPECTED_FIELD_COUNTS,
        )
    except IdentityLifecycleHistoryConformanceError as exc:
        raise _fail(str(exc), exc.code) from exc
    if not proof.passed:
        raise _fail(
            f"identity-lifecycle proof unresolved: {proof.unresolved_element_ids}",
            "identity_lifecycle_proof_failed",
        )
    if set(attribute_ids) != set(proof.element_ids):
        only_attr = sorted(set(attribute_ids) - set(proof.element_ids))
        only_proof = sorted(set(proof.element_ids) - set(attribute_ids))
        raise _fail(
            (
                "ATTRIBUTE_ASSERTION IDs != identity-lifecycle proof IDs "
                f"(only_attribute={only_attr[:8]}, only_proof={only_proof[:8]})"
            ),
            "attribute_identity_set_mismatch",
        )
    if len(proof.element_ids) != EXPECTED_ATTRIBUTE_ASSERTION_COUNT:
        raise _fail(
            "identity-lifecycle proof count drifted",
            "identity_lifecycle_proof_count_mismatch",
        )
    if proof.reconstructable_count != EXPECTED_ATTRIBUTE_ASSERTION_COUNT:
        raise _fail(
            "identity-lifecycle reconstructable_count drifted",
            "identity_lifecycle_proof_failed",
        )

    policy = source_history_policy_from_identity_lifecycle_proof(proof)

    canonical_classified: list[Any] = []
    canonical_v5 = whole_world_v5._analyze_loaded_buddy_world_store_v5(
        root=root,
        world_id=WORLD_ID,
        revision_id=CANONICAL_REVISION_ID,
        manifest=_copy_manifest(manifest),
        store=base_store,
        classified_out=canonical_classified,
        source_history_policy=policy,
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

    try:
        overlay_proof = prove_identity_lifecycle_history_v1(
            overlay_store,
            world_id=WORLD_ID,
            canonical_revision_id=CANONICAL_REVISION_ID,
            canonical_graph_payload_sha256=CANONICAL_GRAPH_PAYLOAD_SHA256,
            expected_field_counts=EXPECTED_FIELD_COUNTS,
        )
    except IdentityLifecycleHistoryConformanceError as exc:
        raise _fail(str(exc), exc.code) from exc
    if _proof_payload(overlay_proof) != _proof_payload(proof):
        raise _fail(
            "#566 overlay changed the identity-lifecycle proof",
            "identity_lifecycle_proof_projection_drift",
        )

    predecessor_migration_classified: list[Any] = []
    predecessor_overlay_v5 = whole_world_v5._analyze_loaded_buddy_world_store_v5(
        root=root,
        world_id=WORLD_ID,
        revision_id=CANONICAL_REVISION_ID,
        manifest=_copy_manifest(manifest),
        store=overlay_store,
        classified_out=predecessor_migration_classified,
        source_history_policy=LEGACY_SOURCE_HISTORY_POLICY,
    )
    migration_attribute_ids = _attribute_assertion_ids(predecessor_migration_classified)
    if set(migration_attribute_ids) != set(attribute_ids):
        raise _fail(
            "migration ATTRIBUTE_ASSERTION IDs drifted from canonical",
            "attribute_identity_set_mismatch",
        )

    migration_classified: list[Any] = []
    overlay_v5 = whole_world_v5._analyze_loaded_buddy_world_store_v5(
        root=root,
        world_id=WORLD_ID,
        revision_id=CANONICAL_REVISION_ID,
        manifest=_copy_manifest(manifest),
        store=overlay_store,
        classified_out=migration_classified,
        source_history_policy=policy,
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
        if any(row["blocker_class"] == BlockerClass.ATTRIBUTE_ASSERTION.value for row in blockers):
            raise _fail(
                f"ATTRIBUTE_ASSERTION remains after identity-history policy in {view_name}",
                "attribute_assertion_not_cleared",
            )
    identity_row = _blocker_row(migration_blockers, BlockerClass.IDENTITY_HISTORY.value)
    if identity_row is None or identity_row["count"] != EXPECTED_IDENTITY_HISTORY_COUNT:
        raise _fail(
            "IDENTITY_HISTORY count drifted after identity-lifecycle reclassification",
            "identity_history_weakened",
        )
    if identity_row["blocking_stage"] != "durable_adoption":
        raise _fail(
            "IDENTITY_HISTORY blocking_stage drifted",
            "identity_history_weakened",
        )
    for view_name, blockers, previous in (
        ("canonical", canonical_blockers, predecessor_canonical_blockers),
        ("migration", migration_blockers, predecessor_migration_blockers),
    ):
        contribution_row = _blocker_row(blockers, BlockerClass.CONTRIBUTION_HISTORY.value)
        predecessor_contribution = _blocker_row(
            previous, BlockerClass.CONTRIBUTION_HISTORY.value
        )
        if contribution_row is None or predecessor_contribution is None:
            raise _fail(
                f"{view_name} CONTRIBUTION_HISTORY missing after identity-lifecycle reclassification",
                "contribution_history_identity_shadow_leak",
            )
        if contribution_row["count"] != predecessor_contribution["count"]:
            raise _fail(
                f"{view_name} CONTRIBUTION_HISTORY absorbed identity-lifecycle shadow "
                f"({predecessor_contribution['count']} -> {contribution_row['count']})",
                "contribution_history_identity_shadow_leak",
            )
        if contribution_row["count"] != EXPECTED_CONTRIBUTION_HISTORY_COUNT:
            raise _fail(
                f"{view_name} CONTRIBUTION_HISTORY count drifted",
                "contribution_history_identity_shadow_leak",
            )
    evidence_count = _blocker_count(
        migration_blockers, BlockerClass.EVIDENCE_PROVENANCE.value
    )
    if evidence_count != EXPECTED_EVIDENCE_PROVENANCE_COUNT:
        raise _fail(
            "EVIDENCE_PROVENANCE count drifted",
            "evidence_provenance_drift",
        )

    canonical_delta = build_identity_classification_delta(
        view="canonical",
        previous_elements=predecessor_classified,
        current_elements=canonical_classified,
        proof=proof,
    )
    migration_delta = build_identity_classification_delta(
        view="migration",
        previous_elements=predecessor_migration_classified,
        current_elements=migration_classified,
        proof=proof,
    )
    if canonical_delta["element_ids"] != migration_delta["element_ids"]:
        raise _fail(
            "canonical/migration classification element IDs drifted",
            "classification_delta_mismatch",
        )
    classification_delta = {
        "count": canonical_delta["count"],
        "field_counts": canonical_delta["field_counts"],
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
    if BlockerClass.ATTRIBUTE_ASSERTION.value not in blocker_delta["migration"][
        "cleared_blocker_classes"
    ]:
        raise _fail(
            "blocker_delta did not record ATTRIBUTE_ASSERTION clearance",
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
    predecessor_after = _sha256_bytes(_predecessor_fixture_path(repo).read_bytes())
    repair_after = _sha256_bytes(repair_path.read_bytes()) if repair_path.is_file() else None
    if head_after.head_revision_id != head_before.head_revision_id or tree_after != tree_before:
        raise _fail("CUTOVER analysis mutated the World Graph", "world_graph_mutated")
    if source_after != source_before:
        raise _fail(
            "CUTOVER analysis mutated source/provenance authority families",
            "source_authority_mutated",
        )
    if identity_after != identity_before:
        raise _fail("CUTOVER analysis mutated identity authority", "identity_authority_mutated")
    if predecessor_after != predecessor_before:
        raise _fail("CUTOVER analysis mutated the PR #571 fixture", "predecessor_fixture_mutated")
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
        "predecessor_fixture_sha256": {
            "before": predecessor_before,
            "after": predecessor_after,
        },
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
        "predecessor:PR571",
        "identity_lifecycle_history_policy:explicit",
        "legacy_source_history_policy_preserved",
        "attribute_assertion_cleared_without_source_mutation",
        "identity_history_preserved",
        "contribution_history_excludes_identity_lifecycle_shadow",
        "next_slice_derived_from_normalized_blocker_stages",
    ]
    report = CutoverIdentityLifecycleHistoryAfter571ReportV1(
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
        identity_lifecycle_proof=_proof_payload(proof),
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


def _assert_report_invariants(
    report: CutoverIdentityLifecycleHistoryAfter571ReportV1,
) -> None:
    if report.canonical_revision_id != CANONICAL_REVISION_ID:
        raise _fail("report revision pin mismatch", "report_pin_mismatch")
    if report.canonical_graph_payload_sha256 != CANONICAL_GRAPH_PAYLOAD_SHA256:
        raise _fail("report payload pin mismatch", "report_pin_mismatch")
    if report.repair_authority["manifest_sha256"] != LOCKED_REPAIR_MANIFEST_SHA256:
        raise _fail("report repair manifest pin mismatch", "report_repair_pin_mismatch")
    if report.cutover_disposition != "CUTOVER_NOT_READY":
        raise _fail("CUTOVER disposition must remain NOT_READY", "cutover_ready_regression")
    proof = report.identity_lifecycle_proof
    if proof.get("passed") is not True:
        raise _fail("report identity-lifecycle proof is not passed", "identity_lifecycle_proof_failed")
    if proof.get("reconstructable_count") != EXPECTED_ATTRIBUTE_ASSERTION_COUNT:
        raise _fail("report reconstructable_count drifted", "identity_lifecycle_proof_failed")
    if proof.get("unresolved_element_ids") != []:
        raise _fail("report has unresolved identity-lifecycle IDs", "identity_lifecycle_proof_failed")
    delta = report.classification_delta
    if not delta.get("lossless") or delta.get("count") != EXPECTED_ATTRIBUTE_ASSERTION_COUNT:
        raise _fail("classification_delta is not the sealed 28-element set", "classification_delta_mismatch")
    if delta.get("element_ids") != proof.get("element_ids"):
        raise _fail(
            "classification_delta IDs drifted from identity-lifecycle proof",
            "classification_delta_mismatch",
        )
    for view_name in ("canonical_view", "migration_projection"):
        view = getattr(report, view_name)
        if view["unaccounted_durable_elements"] != 0:
            raise _fail(f"{view_name} is not fully accounted", "unaccounted_durable_elements")
        if any(
            row["blocker_class"] == BlockerClass.ATTRIBUTE_ASSERTION.value
            for row in view["blockers"]
        ):
            raise _fail(f"{view_name} still contains ATTRIBUTE_ASSERTION", "attribute_assertion_not_cleared")
        identity = _blocker_row(view["blockers"], BlockerClass.IDENTITY_HISTORY.value)
        if identity is None or identity["count"] != EXPECTED_IDENTITY_HISTORY_COUNT:
            raise _fail(f"{view_name} IDENTITY_HISTORY drifted", "identity_history_weakened")
        contribution = _blocker_row(view["blockers"], BlockerClass.CONTRIBUTION_HISTORY.value)
        if contribution is None or contribution["count"] != EXPECTED_CONTRIBUTION_HISTORY_COUNT:
            raise _fail(
                f"{view_name} CONTRIBUTION_HISTORY drifted",
                "contribution_history_identity_shadow_leak",
            )
    for delta_view in ("canonical", "migration"):
        changed = {
            row["blocker_class"] for row in report.blocker_delta[delta_view]["rows"]
        }
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
    if report.relationship_invariants["migration"]["residual_edge_ids"] != sorted(
        MIGRATION_RESIDUAL_EDGE_IDS
    ):
        raise _fail("migration residual IDs drifted", "report_relationship_mismatch")
    if not report.mutation_proof.get("unchanged"):
        raise _fail("mutation proof is not unchanged", "world_graph_mutated")
    if "aspect" in json.dumps(report.model_dump(mode="json", by_alias=True)).lower():
        raise _fail("report contains forbidden aspect identity materialization", "aspect_materialization")


def _report_bytes(report: CutoverIdentityLifecycleHistoryAfter571ReportV1) -> bytes:
    return _json_bytes(report.model_dump(mode="json", by_alias=True))


def get_cutover_identity_lifecycle_history_after_571_status(
    root: Path | None = None,
    *,
    repo: Path | None = None,
) -> CutoverIdentityLifecycleHistoryAfter571StatusV1:
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
        manifest_path = repository / repair_service.MANIFEST_RELPATH
        manifest_sha = (
            _sha256_bytes(manifest_path.read_bytes()) if manifest_path.is_file() else None
        )
        if manifest_sha != LOCKED_REPAIR_MANIFEST_SHA256:
            diagnostics.append("repair_manifest_mismatch")
        if CURRENT_V5_TARGET.dungeonmind_dependency_ref != DUNGEONMIND_DEPENDENCY_REF:
            diagnostics.append("dependency_pin_mismatch")
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
        return CutoverIdentityLifecycleHistoryAfter571StatusV1(
            eligibility=eligibility,
            reason=None if eligibility == "eligible" else "stale_input",
            diagnostics=diagnostics,
            canonical_graph_payload_sha256=payload_sha,
            repair_manifest_sha256=manifest_sha,
            predecessor_fixture_sha256=predecessor_sha,
            adoption_seam=adoption_seam,
        )
    except Exception as exc:  # noqa: BLE001 — status must fail closed, not raise
        diagnostics.append(type(exc).__name__)
        return CutoverIdentityLifecycleHistoryAfter571StatusV1(
            eligibility="integrity_failure",
            reason=str(exc),
            diagnostics=diagnostics,
        )


def build_cutover_identity_lifecycle_history_after_571(
    *,
    root: Path | None = None,
    repo: Path | None = None,
    allow_live_world: bool = False,
) -> CutoverIdentityLifecycleHistoryAfter571BuildResultV1:
    """Build the deterministic successor fixture without mutating the graph."""
    del allow_live_world
    world_root = _root(root)
    repository = _repo(repo)
    predecessor_path = _predecessor_fixture_path(repository)
    predecessor_before = (
        _sha256_bytes(predecessor_path.read_bytes()) if predecessor_path.is_file() else None
    )
    report = _compose_report(world_root, repository)
    raw = _report_bytes(report)
    fixture_sha = _sha256_bytes(raw)
    locked = LOCKED_FIXTURE_SHA256.strip()
    if locked and fixture_sha != locked:
        raise _fail(
            "generated identity-lifecycle CUTOVER fixture digest does not match locked digest",
            "fixture_digest_mismatch",
        )
    path = _fixture_path(repository)
    diagnostics = ["non_publishing"]
    if path.is_file():
        existing_sha = _sha256_bytes(path.read_bytes())
        if existing_sha != fixture_sha:
            raise _fail(
                "existing identity-lifecycle CUTOVER fixture differs from generated bytes; refuse overwrite",
                "locked_fixture_overwrite_refused",
            )
        if predecessor_path.is_file() and predecessor_before is not None:
            if _sha256_bytes(predecessor_path.read_bytes()) != predecessor_before:
                raise _fail(
                    "build mutated PR #571 predecessor fixture",
                    "predecessor_fixture_mutated",
                )
        if not locked:
            diagnostics.extend(["already_built", "first_seal_unlocked"])
        else:
            diagnostics.append("already_built")
        return CutoverIdentityLifecycleHistoryAfter571BuildResultV1(
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
            f"atomic identity-lifecycle CUTOVER fixture write failed: {exc}",
            "fixture_write_failed",
        ) from exc

    if predecessor_path.is_file() and predecessor_before is not None:
        if _sha256_bytes(predecessor_path.read_bytes()) != predecessor_before:
            raise _fail(
                "build mutated PR #571 predecessor fixture",
                "predecessor_fixture_mutated",
            )
    if not locked:
        diagnostics.append("first_seal_unlocked")
    diagnostics.append("sealed")
    return CutoverIdentityLifecycleHistoryAfter571BuildResultV1(
        fixture_path=str(path),
        fixture_sha256=fixture_sha,
        report=report,
        diagnostics=diagnostics,
    )


def verify_cutover_identity_lifecycle_history_after_571(
    *,
    root: Path | None = None,
    repo: Path | None = None,
) -> CutoverIdentityLifecycleHistoryAfter571VerifyResultV1:
    """Reload the fixture and independently reproduce its report bytes."""
    world_root = _root(root)
    repository = _repo(repo)
    path = _fixture_path(repository)
    if not path.is_file():
        return CutoverIdentityLifecycleHistoryAfter571VerifyResultV1(
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
            return CutoverIdentityLifecycleHistoryAfter571VerifyResultV1(
                verified=False,
                fixture_path=str(path),
                fixture_sha256=fixture_sha,
                diagnostics=["fixture_digest_mismatch"],
            )
    else:
        diagnostics.append("first_seal_unlocked")
    try:
        stored = CutoverIdentityLifecycleHistoryAfter571ReportV1.model_validate(
            json.loads(raw)
        )
        reproduced = _compose_report(world_root, repository)
        if _report_bytes(stored) != _report_bytes(reproduced):
            return CutoverIdentityLifecycleHistoryAfter571VerifyResultV1(
                verified=False,
                fixture_path=str(path),
                fixture_sha256=fixture_sha,
                diagnostics=[*diagnostics, "fixture_bytes_not_deterministic"],
            )
        _assert_report_invariants(reproduced)
    except (
        CutoverIdentityLifecycleHistoryAfter571Error,
        OSError,
        ValueError,
        TypeError,
    ) as exc:
        return CutoverIdentityLifecycleHistoryAfter571VerifyResultV1(
            verified=False,
            fixture_path=str(path),
            fixture_sha256=fixture_sha,
            diagnostics=[*diagnostics, type(exc).__name__ + ":" + str(exc)],
        )
    return CutoverIdentityLifecycleHistoryAfter571VerifyResultV1(
        verified=True,
        fixture_path=str(path),
        fixture_sha256=fixture_sha,
        diagnostics=[*diagnostics, "verified", "non_publishing"],
    )
