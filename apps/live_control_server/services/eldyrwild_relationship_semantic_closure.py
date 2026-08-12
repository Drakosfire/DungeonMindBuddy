"""Governed apply for the Eldyrwild relationship semantic closure program.

Loads the locked 55-row closure manifest (46 mutable + 9 deferred kind-repair
units with empty operations), proves whole-ledger preflight against the exact
Q4 base revision, and applies mutable closure operations in ``operation_plan``
order through existing Kernel seams:

* ``contradict_edge_assertion_support`` for contradiction-only units and for
  the compound/identity edge contradictions;
* ``correct_edge_assertion_support`` for the two governed replacements;
* ``merge_contribution_to_revision`` for the one compound decomposition atomic;
* ``merge_identity`` + ``publish_world_revision`` for the seven durable
  identity migrations (decision payloads are synced to the durable
  ``identity_decisions/`` ledger on publish).

Deferred ``deferred_buddy_kind_repair`` units are never contradicted or mutated;
they remain residual (residual=9) at the governed exit.

Callers cannot inject different artifacts, unit/op order, targets, or semantics:
the manifest bytes are sha256-locked here and child artifacts are verified
against the manifest before any mutation. Apply is operation-plan prefix-safe:
an already applied op prefix is skipped, a non-prefix applied set is refused.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

import graph_memory.kernel as kernel
from apps.live_control_server.config import (
    live_world_graph_root,
    repo_root,
    world_graph_root,
)
from apps.live_control_server.integrations.dungeonmind_kernel.relationship_adjudication_continuity_v1 import (
    prove_revision_is_anchor_or_descendant_v1,
)
from apps.live_control_server.integrations.dungeonmind_kernel.relationship_effective_conformance_v1 import (
    analyze_relationship_effective_conformance_v1,
)
from apps.live_control_server.integrations.dungeonmind_kernel.relationship_residual_adjudication import (
    RelationshipResidualAdjudicationError,
    resolve_evidence_excerpt,
    verify_excerpt_against_seal,
)
from graph_memory.kernel.contribution_models import GraphContribution
from graph_memory.kernel.identity_decisions import (
    compute_identity_decision_id,
    merge_identity,
)
from graph_memory.world_supergraph.contribution_store import (
    load_contribution_index,
    load_contribution_record,
)
from graph_memory.world_supergraph.errors import WorldGraphNotFoundError
from graph_memory.world_supergraph.identity_decision_store import (
    load_identity_decision_index,
    load_identity_decision_record,
)

CLOSURE_ID = "eldyrwild-relationship-semantic-closure-v1"
WORLD_ID = "eldyrwild"
AUTHORED_BY = "gm"

# Exact Q4 base (post-C4 live exit, PR #559).
BASE_REVISION_ID = "rev:3759d8d6a02f09306397918234a2ded2"
BASE_PARENT_REVISION_ID = "rev:ba3abde1bfc3659795bcd77bb55eb9f7"

CLOSURE_DIR_RELPATH = (
    "graph_data/approved_graph_corrections/eldyrwild/relationship-semantic-closure-v1"
)
MANIFEST_RELPATH = f"{CLOSURE_DIR_RELPATH}/manifest.json"
LOCKED_MANIFEST_SHA256 = (
    "3d5da9b19b74a28d4930132e281c0e41197d3ea1493c5a202ba1ef6c6ffbfb25"
)

EXPECTED_BASE_INVENTORY = {
    "semantic": 366,
    "represented": 311,
    "residual": 55,
    "uses_statblock_mechanics": 3,
    "unadjudicated": 0,
    "dungeonmind_owned": 0,
    "buddy_owned": 55,
}
EXPECTED_FINAL_INVENTORY = {
    "semantic": 323,
    "represented": 314,
    "residual": 9,
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

MUTABLE_UNIT_COUNT = 46
DEFERRED_UNIT_COUNT = 9
TOTAL_UNIT_COUNT = 55
OPERATION_PLAN_COUNT = 54

ADJUDICATION_FIXTURES = {
    "A": "tests/fixtures/dungeonmind_kernel/eldyrwild_relationship_residual_adjudication_v1.json",
    "S25": "tests/fixtures/dungeonmind_kernel/eldyrwild_relationship_descendant_residual_adjudication_v1.json",
}
SEAL_FIXTURES = {
    "A": "tests/fixtures/dungeonmind_kernel/eldyrwild_relationship_residual_source_seals_v1.json",
    "S25": "tests/fixtures/dungeonmind_kernel/eldyrwild_relationship_descendant_residual_source_seals_v1.json",
}

ClosureEligibility = Literal[
    "eligible", "partially_applied", "already_applied", "ineligible", "integrity_failure"
]
OpState = Literal["applied", "pending", "integrity_failure"]


class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class ClosureUnitState(_Model):
    unit_id: str
    ordinal: int
    edge_id: str
    closure_kind: str
    deferred: bool = False
    applied: bool
    applied_operations: list[str] = Field(default_factory=list)
    pending_operations: list[str] = Field(default_factory=list)
    integrity_failure: bool = False


class RelationshipSemanticClosureStatus(_Model):
    schema_: str = Field(
        default="dmb_eldyrwild_relationship_semantic_closure_status_v1",
        alias="schema",
    )
    world_id: str = WORLD_ID
    closure_id: str = CLOSURE_ID
    head_revision_id: str | None = None
    base_revision_id: str = BASE_REVISION_ID
    eligibility: ClosureEligibility
    reason: str | None = None
    unit_count: int = 0
    mutable_unit_count: int = 0
    deferred_unit_count: int = 0
    applied_unit_count: int = 0
    next_pending_unit_id: str | None = None
    units: list[ClosureUnitState] = Field(default_factory=list)
    diagnostics: list[str] = Field(default_factory=list)


class RelationshipSemanticClosureResult(_Model):
    schema_: str = Field(
        default="dmb_eldyrwild_relationship_semantic_closure_result_v1",
        alias="schema",
    )
    world_id: str = WORLD_ID
    closure_id: str = CLOSURE_ID
    expected_base_revision_id: str
    final_revision_id: str | None = None
    published_revision_ids: list[str] = Field(default_factory=list)
    applied_unit_ids: list[str] = Field(default_factory=list)
    already_applied_unit_ids: list[str] = Field(default_factory=list)
    deferred_unit_ids: list[str] = Field(default_factory=list)
    failed_unit_id: str | None = None
    failure_code: str | None = None
    failure_message: str | None = None
    final_inventory: dict[str, int] | None = None
    verify_passed: bool = False
    diagnostics: list[str] = Field(default_factory=list)


class RelationshipSemanticClosurePin(_Model):
    schema_: str = Field(
        default="dmb_eldyrwild_relationship_semantic_closure_pin_v1",
        alias="schema",
    )
    world_id: str = WORLD_ID
    closure_id: str = CLOSURE_ID
    base_revision_id: str = BASE_REVISION_ID
    final_revision_id: str
    final_graph_payload_sha256: str
    final_inventory: dict[str, int]
    residual_edge_ids: list[str] = Field(default_factory=list)
    diagnostics: list[str] = Field(default_factory=list)


class RelationshipSemanticClosureError(Exception):
    def __init__(self, message: str, *, code: str, status_code: int = 400) -> None:
        super().__init__(message)
        self.code = code
        self.status_code = status_code


# ---------------------------------------------------------------------------
# Artifact loading + integrity
# ---------------------------------------------------------------------------


def _repo(repo: Path | None) -> Path:
    return (repo or repo_root()).resolve()


def _resolve_root(root: Path | None) -> Path:
    return (root or world_graph_root()).resolve()


def _is_canonical_live_root(resolved: Path) -> bool:
    return resolved == live_world_graph_root().resolve()


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _load_manifest(repo: Path | None = None) -> dict[str, Any]:
    base = _repo(repo)
    manifest_path = base / MANIFEST_RELPATH
    if not manifest_path.is_file():
        raise RelationshipSemanticClosureError(
            f"closure manifest missing: {MANIFEST_RELPATH}",
            code="closure_manifest_missing",
            status_code=404,
        )
    raw = manifest_path.read_text(encoding="utf-8")
    digest = _sha256_text(raw)
    if digest != LOCKED_MANIFEST_SHA256:
        raise RelationshipSemanticClosureError(
            f"closure manifest sha256 {digest} != locked {LOCKED_MANIFEST_SHA256}",
            code="closure_manifest_tampered",
        )
    manifest = json.loads(raw)
    if manifest.get("schema") != "dmb_eldyrwild_relationship_semantic_closure_manifest_v1":
        raise RelationshipSemanticClosureError(
            "closure manifest schema mismatch", code="closure_manifest_invalid"
        )
    if manifest.get("closure_id") != CLOSURE_ID:
        raise RelationshipSemanticClosureError(
            "closure manifest id mismatch", code="closure_manifest_invalid"
        )
    if manifest.get("base_revision_id") != BASE_REVISION_ID:
        raise RelationshipSemanticClosureError(
            "closure manifest base revision mismatch", code="closure_manifest_invalid"
        )
    if manifest.get("expected_base_inventory") != EXPECTED_BASE_INVENTORY:
        raise RelationshipSemanticClosureError(
            "closure manifest base inventory mismatch", code="closure_manifest_invalid"
        )
    if manifest.get("expected_final_inventory") != EXPECTED_FINAL_INVENTORY:
        raise RelationshipSemanticClosureError(
            "closure manifest final inventory mismatch", code="closure_manifest_invalid"
        )
    deferred_ids = frozenset(manifest.get("deferred_residual_edge_ids") or [])
    if deferred_ids != DEFERRED_RESIDUAL_EDGE_IDS:
        raise RelationshipSemanticClosureError(
            "closure manifest deferred residual edge set mismatch",
            code="closure_manifest_invalid",
        )
    units = manifest.get("units") or []
    if len(units) != TOTAL_UNIT_COUNT or manifest.get("unit_order") != [
        u["unit_id"] for u in units
    ]:
        raise RelationshipSemanticClosureError(
            "closure manifest unit order mismatch", code="closure_manifest_invalid"
        )
    mutable = [u for u in units if not u.get("deferred")]
    deferred = [u for u in units if u.get("deferred")]
    if len(mutable) != MUTABLE_UNIT_COUNT or len(deferred) != DEFERRED_UNIT_COUNT:
        raise RelationshipSemanticClosureError(
            "closure manifest mutable/deferred unit counts mismatch",
            code="closure_manifest_invalid",
        )
    for unit in deferred:
        if unit.get("operations"):
            raise RelationshipSemanticClosureError(
                f"deferred unit {unit['unit_id']} must have empty operations",
                code="closure_manifest_invalid",
            )
        if unit.get("closure_kind") != "deferred_buddy_kind_repair":
            raise RelationshipSemanticClosureError(
                f"deferred unit {unit['unit_id']} has unexpected closure_kind",
                code="closure_manifest_invalid",
            )
    plan = manifest.get("operation_plan") or []
    if len(plan) != OPERATION_PLAN_COUNT:
        raise RelationshipSemanticClosureError(
            "closure manifest operation_plan length mismatch",
            code="closure_manifest_invalid",
        )

    for name, info in (manifest.get("artifacts") or {}).items():
        child_path = base / CLOSURE_DIR_RELPATH / info["path"]
        if not child_path.is_file():
            raise RelationshipSemanticClosureError(
                f"closure child artifact missing: {info['path']}",
                code="closure_artifact_missing",
                status_code=404,
            )
        child_raw = child_path.read_text(encoding="utf-8")
        child_digest = _sha256_text(child_raw)
        if child_digest != info["sha256"]:
            raise RelationshipSemanticClosureError(
                f"closure child artifact {info['path']} sha256 {child_digest} "
                f"!= manifest {info['sha256']}",
                code="closure_artifact_tampered",
            )
        child = json.loads(child_raw)
        if child.get("closure_id") != CLOSURE_ID:
            raise RelationshipSemanticClosureError(
                f"closure child artifact {info['path']} closure_id mismatch",
                code="closure_artifact_invalid",
            )
        info["_payload"] = child
    return manifest


def _unit_contribution(manifest: dict[str, Any], contribution_id: str) -> GraphContribution:
    for info in (manifest.get("artifacts") or {}).values():
        payload = info.get("_payload") or {}
        for entry in payload.get("entries") or []:
            contribs = entry.get("contributions") or {}
            if contribution_id in contribs:
                raw = dict(contribs[contribution_id])
                # Artifacts may embed the locked digest alongside the contribution
                # body; GraphContribution forbids that auxiliary field.
                raw.pop("source_payload_sha256", None)
                return GraphContribution.model_validate(raw)
    raise RelationshipSemanticClosureError(
        f"contribution {contribution_id} not found in closure artifacts",
        code="closure_artifact_invalid",
    )


def _units_by_id(manifest: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {u["unit_id"]: u for u in manifest["units"]}


def _plan_unit_op(
    manifest: dict[str, Any], plan_op: dict[str, Any]
) -> tuple[dict[str, Any], dict[str, Any]]:
    unit = _units_by_id(manifest)[plan_op["unit_id"]]
    op = unit["operations"][plan_op["unit_op_index"]]
    return unit, op


# ---------------------------------------------------------------------------
# Gold-standard authority helpers (mirrored from C4 session25 service)
# ---------------------------------------------------------------------------


def _support_row(store: Any, assertion_id: str) -> dict[str, Any] | None:
    support = store.assertion_support or {}
    row = support.get(assertion_id)
    if row is None:
        return None
    if isinstance(row, dict):
        return row
    return row.model_dump(mode="json")


def _support_record_as_dict(record: Any) -> dict[str, Any] | None:
    if isinstance(record, dict):
        return record
    if hasattr(record, "model_dump"):
        dumped = record.model_dump()
        return dumped if isinstance(dumped, dict) else None
    return None


def _active_edge_assertion_ids(store: Any, edge_id: str) -> set[str]:
    """Assertion IDs that currently keep ``edge_id`` supported in the Kernel."""
    active: set[str] = set()
    for assertion_id, raw in (store.assertion_support or {}).items():
        support = _support_record_as_dict(raw)
        if support is None:
            continue
        if support.get("graph_object_id") != edge_id:
            continue
        if support.get("assertion_kind") != "edge":
            continue
        if support.get("support_state") != "supported":
            continue
        if not list(support.get("active_contribution_ids") or []):
            continue
        resolved_id = support.get("assertion_id") or assertion_id
        if isinstance(resolved_id, str) and resolved_id:
            active.add(resolved_id)
    return active


def _manifest_entry(store: Any, contribution_id: str) -> Any | None:
    for entry in store.contribution_replay_manifest or []:
        cid = getattr(entry, "contribution_id", None)
        if cid is None and isinstance(entry, dict):
            cid = entry.get("contribution_id")
        if cid == contribution_id:
            return entry
    return None


def _entry_status_digest(entry: Any) -> tuple[str | None, str | None]:
    status = getattr(entry, "status", None)
    if status is None and isinstance(entry, dict):
        status = entry.get("status")
    digest = getattr(entry, "source_payload_sha256", None)
    if digest is None and isinstance(entry, dict):
        digest = entry.get("source_payload_sha256")
    return status, digest


def _accepted_edge_ids(contribution: GraphContribution) -> list[str]:
    edge_ids: list[str] = []
    for assertion in contribution.accepted_assertions:
        if assertion.assertion_kind != "edge":
            continue
        value = assertion.value
        if isinstance(value, dict):
            edge_id = value.get("edge_id")
            if isinstance(edge_id, str) and edge_id:
                edge_ids.append(edge_id)
    return edge_ids


def _revision_bound_contribution_authority(
    *,
    root: Path,
    store: Any,
    contribution_id: str,
    locked_source_payload_sha256: str,
) -> tuple[bool, list[str]]:
    """Digest VALUE equality + active replay + mutable ledger + index coherence."""
    diagnostics: list[str] = []
    digests = store.contribution_source_payload_sha256 or {}
    bound = digests.get(contribution_id)
    if bound != locked_source_payload_sha256:
        diagnostics.append(f"revision_digest_mismatch_or_missing:{contribution_id}")
        return False, diagnostics

    entry = _manifest_entry(store, contribution_id)
    if entry is None:
        diagnostics.append(f"replay_manifest_missing:{contribution_id}")
        return False, diagnostics
    status, digest = _entry_status_digest(entry)
    if status != "active":
        diagnostics.append(f"replay_manifest_not_active:{contribution_id}")
        return False, diagnostics
    if digest != locked_source_payload_sha256:
        diagnostics.append(f"replay_manifest_digest_mismatch:{contribution_id}")
        return False, diagnostics

    try:
        ledger = load_contribution_record(root, WORLD_ID, contribution_id)
    except FileNotFoundError:
        diagnostics.append(f"mutable_ledger_missing:{contribution_id}")
        return False, diagnostics
    if ledger.contribution_id != contribution_id:
        diagnostics.append(f"mutable_id_mismatch:{contribution_id}")
        return False, diagnostics
    ledger_digest = kernel.compute_contribution_source_payload_sha256(ledger)
    if ledger_digest != locked_source_payload_sha256:
        diagnostics.append(f"mutable_digest_mismatch:{contribution_id}")
        return False, diagnostics
    if ledger.status != "active":
        diagnostics.append(f"mutable_not_active:{contribution_id}")
        return False, diagnostics

    index = load_contribution_index(root, WORLD_ID)
    all_ids = set(index.all_contribution_ids)
    active_ids = set(index.active_contribution_ids)
    superseded_ids = set(index.superseded_contribution_ids)
    retracted_ids = set(index.retracted_contribution_ids)
    failed_ids = set(index.failed_contribution_ids)
    if contribution_id not in all_ids:
        diagnostics.append(f"index_missing_from_all:{contribution_id}")
    if contribution_id not in active_ids:
        diagnostics.append(f"index_not_active:{contribution_id}")
    if contribution_id in superseded_ids:
        diagnostics.append(f"index_superseded:{contribution_id}")
    if contribution_id in retracted_ids:
        diagnostics.append(f"index_retracted:{contribution_id}")
    if contribution_id in failed_ids:
        diagnostics.append(f"index_failed:{contribution_id}")
    if any(
        d.startswith("index_") and d.endswith(f":{contribution_id}") for d in diagnostics
    ):
        return False, diagnostics

    return True, [f"revision_bound_authority:{contribution_id}"]


def _verify_locked_target_source_contribution_authority(
    *,
    root: Path,
    store: Any,
    contribution_id: str,
    locked_source_payload_sha256: str,
    target_assertion_id: str | None = None,
) -> tuple[bool, list[str]]:
    """Seal an original target contribution against revision + mutable authority."""
    ok, diagnostics = _revision_bound_contribution_authority(
        root=root,
        store=store,
        contribution_id=contribution_id,
        locked_source_payload_sha256=locked_source_payload_sha256,
    )
    if not ok:
        return False, [f"target_source_{d}" for d in diagnostics]

    if target_assertion_id is not None:
        try:
            ledger = load_contribution_record(root, WORLD_ID, contribution_id)
        except FileNotFoundError:
            return False, [f"target_source_mutable_ledger_missing:{contribution_id}"]
        target_assertion = next(
            (
                a
                for a in ledger.accepted_assertions
                if a.assertion_id == target_assertion_id
            ),
            None,
        )
        if target_assertion is None or target_assertion.assertion_kind != "edge":
            return False, [f"target_source_assertion_missing:{contribution_id}"]

    return True, [f"target_source_authority_sealed:{contribution_id}"]


def _contradict_support_shape_suggests_applied(
    store: Any, unit: dict[str, Any]
) -> bool:
    row = _support_row(store, unit["target_assertion_id"])
    if row is None:
        return False
    if row.get("support_state") != "contradicted":
        return False
    if list(row.get("active_contribution_ids") or []):
        return False
    contradicted = set(row.get("contradicted_contribution_ids") or [])
    targets = set(unit.get("target_contribution_ids") or [])
    if not targets.issubset(contradicted):
        return False
    if _active_edge_assertion_ids(store, unit["edge_id"]):
        return False
    return True


def _replacement_edges_current(
    store: Any, manifest: dict[str, Any], contribution_id: str
) -> bool:
    contribution = _unit_contribution(manifest, contribution_id)
    edge_ids = _accepted_edge_ids(contribution)
    if not edge_ids:
        return False
    for edge_id in edge_ids:
        if not _active_edge_assertion_ids(store, edge_id):
            return False
    return True


def _merge_additive_shape_suggests_applied(
    store: Any, manifest: dict[str, Any], contribution_id: str
) -> bool:
    entry = _manifest_entry(store, contribution_id)
    if entry is None:
        return False
    status, _digest = _entry_status_digest(entry)
    if status != "active":
        return False
    return _replacement_edges_current(store, manifest, contribution_id)


def _identity_redirect_active(store: Any, source_node_id: str, target_node_id: str) -> bool:
    from graph_memory.union_supergraph.redirects import resolve_union_node_id

    try:
        return (
            resolve_union_node_id(source_node_id, store.identity_redirects or [])
            == target_node_id
        )
    except Exception:
        return False


def _identity_merge_authority(
    *,
    root: Path,
    store: Any,
    op: dict[str, Any],
) -> tuple[bool, list[str]]:
    diagnostics: list[str] = []
    source = store.nodes.get(op["source_node_id"])
    if source is None:
        diagnostics.append(f"identity_source_missing:{op['source_node_id']}")
        return False, diagnostics
    state = dict(source.state or {})
    if state.get("merged_into") != op["target_node_id"]:
        diagnostics.append(f"identity_merged_into_mismatch:{op['source_node_id']}")
        return False, diagnostics

    expected = op["expected_decision_id"]
    try:
        record = load_identity_decision_record(root, WORLD_ID, expected)
    except FileNotFoundError:
        diagnostics.append(f"identity_durable_ledger_missing:{expected}")
        return False, diagnostics
    if record.status != "active":
        diagnostics.append(f"identity_durable_ledger_inactive:{expected}")
        return False, diagnostics
    if record.decision_id != expected:
        diagnostics.append(f"identity_durable_ledger_id_mismatch:{expected}")
        return False, diagnostics

    if not _identity_redirect_active(store, op["source_node_id"], op["target_node_id"]):
        diagnostics.append(f"identity_redirect_missing:{op['source_node_id']}")
        return False, diagnostics

    index = load_identity_decision_index(root, WORLD_ID)
    if expected not in set(index.all_decision_ids):
        diagnostics.append(f"identity_decision_index_missing:{expected}")
        return False, diagnostics

    return True, [f"identity_merge_authority:{expected}"]


def _identity_merge_shape_suggests_applied(store: Any, op: dict[str, Any]) -> bool:
    source = store.nodes.get(op["source_node_id"])
    if source is not None:
        state = dict(source.state or {})
        if state.get("merged_into") == op["target_node_id"]:
            return True
    expected = op.get("expected_decision_id")
    for raw in store.identity_decisions or []:
        decision_id = raw.get("decision_id") if isinstance(raw, dict) else raw.decision_id
        if decision_id == expected:
            return True
    return False


def _contribution_digest_key_present(store: Any, contribution_id: str) -> bool:
    digests = store.contribution_source_payload_sha256 or {}
    return contribution_id in digests


def _classify_op(
    *,
    root: Path,
    store: Any,
    unit: dict[str, Any],
    op: dict[str, Any],
    manifest: dict[str, Any],
) -> tuple[OpState, list[str]]:
    kind = op["op"]
    if kind in {"contradict", "correct", "merge_additive"}:
        cid = op["contribution_id"]
        locked = op.get("source_payload_sha256")
        if not locked:
            return "integrity_failure", [f"op_missing_locked_digest:{cid}"]
        authority_ok, auth_diag = _revision_bound_contribution_authority(
            root=root,
            store=store,
            contribution_id=cid,
            locked_source_payload_sha256=locked,
        )
        if kind in {"contradict", "correct"}:
            shape = _contradict_support_shape_suggests_applied(store, unit)
            if kind == "correct":
                shape = shape and _replacement_edges_current(store, manifest, cid)
        else:
            shape = _merge_additive_shape_suggests_applied(store, manifest, cid)

        if authority_ok and shape:
            return "applied", auth_diag
        if shape or _contribution_digest_key_present(store, cid) or authority_ok:
            return "integrity_failure", [
                f"op_integrity_failure:{unit['unit_id']}:{kind}",
                *auth_diag,
            ]
        return "pending", []

    if kind == "identity_merge":
        authority_ok, auth_diag = _identity_merge_authority(root=root, store=store, op=op)
        shape = _identity_merge_shape_suggests_applied(store, op)
        if authority_ok:
            return "applied", auth_diag
        if shape:
            return "integrity_failure", [
                f"op_integrity_failure:{unit['unit_id']}:identity_merge",
                *auth_diag,
            ]
        return "pending", []

    raise RelationshipSemanticClosureError(
        f"unknown closure op {kind!r}", code="closure_manifest_invalid"
    )


def _op_applied(
    store: Any,
    unit: dict[str, Any],
    op: dict[str, Any],
    *,
    root: Path | None = None,
    manifest: dict[str, Any] | None = None,
) -> bool:
    """True only when the op is applied under gold-standard authority detectors.

    When ``root``/``manifest`` are omitted (legacy call sites), falls back to a
    fail-closed False unless a temporary root/manifest can be supplied via the
    store-bound closure apply path (which always passes them).
    """
    if root is None or manifest is None:
        # Narrow legacy helper: contribution digest key alone is NOT applied.
        kind = op["op"]
        if kind in {"contradict", "correct"}:
            if not _contribution_digest_key_present(store, op["contribution_id"]):
                return False
            return False
        if kind == "merge_additive":
            return False
        if kind == "identity_merge":
            return False
        return False
    state, _diag = _classify_op(
        root=root, store=store, unit=unit, op=op, manifest=manifest
    )
    return state == "applied"


def _op_label(op: dict[str, Any], index: int) -> str:
    return f"{op['op']}#{index}"


def _unit_states(
    *,
    root: Path,
    store: Any,
    manifest: dict[str, Any],
) -> list[ClosureUnitState]:
    states: list[ClosureUnitState] = []
    for unit in manifest["units"]:
        if unit.get("deferred"):
            states.append(
                ClosureUnitState(
                    unit_id=unit["unit_id"],
                    ordinal=unit["ordinal"],
                    edge_id=unit["edge_id"],
                    closure_kind=unit["closure_kind"],
                    deferred=True,
                    applied=False,
                    applied_operations=[],
                    pending_operations=[],
                    integrity_failure=False,
                )
            )
            continue
        applied_ops: list[str] = []
        pending_ops: list[str] = []
        integrity = False
        for index, op in enumerate(unit["operations"]):
            label = _op_label(op, index)
            state, _diag = _classify_op(
                root=root, store=store, unit=unit, op=op, manifest=manifest
            )
            if state == "applied":
                applied_ops.append(label)
            elif state == "pending":
                pending_ops.append(label)
            else:
                integrity = True
                pending_ops.append(label)
        states.append(
            ClosureUnitState(
                unit_id=unit["unit_id"],
                ordinal=unit["ordinal"],
                edge_id=unit["edge_id"],
                closure_kind=unit["closure_kind"],
                deferred=False,
                applied=not pending_ops and not integrity,
                applied_operations=applied_ops,
                pending_operations=pending_ops,
                integrity_failure=integrity,
            )
        )
    return states


def _operation_plan_states(
    *,
    root: Path,
    store: Any,
    manifest: dict[str, Any],
) -> list[tuple[dict[str, Any], OpState, list[str]]]:
    results: list[tuple[dict[str, Any], OpState, list[str]]] = []
    for plan_op in manifest.get("operation_plan") or []:
        unit, op = _plan_unit_op(manifest, plan_op)
        state, diag = _classify_op(
            root=root, store=store, unit=unit, op=op, manifest=manifest
        )
        results.append((plan_op, state, diag))
    return results


def _assert_operation_plan_prefix(
    plan_states: list[tuple[dict[str, Any], OpState, list[str]]],
) -> list[str]:
    diagnostics: list[str] = []
    if any(state == "integrity_failure" for _op, state, _d in plan_states):
        diagnostics.append("op_authority_integrity_failure")
        for plan_op, state, diag in plan_states:
            if state == "integrity_failure":
                diagnostics.extend(diag)
                diagnostics.append(
                    f"integrity_op:{plan_op['unit_id']}:{plan_op['op']}#{plan_op['op_ordinal']}"
                )
    applied_flags = [state == "applied" for _op, state, _d in plan_states]
    first_pending = next(
        (i for i, flag in enumerate(applied_flags) if not flag), len(applied_flags)
    )
    if any(applied_flags[first_pending:]):
        diagnostics.append("applied_ops_not_a_prefix")
    return diagnostics


# ---------------------------------------------------------------------------
# Preflight — whole ledger, resume-aware
# ---------------------------------------------------------------------------


def _verify_fixture_rows(manifest: dict[str, Any], repo: Path | None) -> list[str]:
    """Cross-check manifest-embedded adjudication rows + seals against fixtures."""
    diagnostics: list[str] = []
    adjudication_rows: dict[str, tuple[str, dict[str, Any]]] = {}
    seal_rows: dict[str, tuple[str, dict[str, Any]]] = {}
    for authority, relpath in ADJUDICATION_FIXTURES.items():
        path = _repo(repo) / relpath
        if not path.is_file():
            raise RelationshipSemanticClosureError(
                f"adjudication fixture missing: {relpath}",
                code="adjudication_fixture_missing",
                status_code=404,
            )
        payload = json.loads(path.read_text(encoding="utf-8"))
        for record in payload.get("records") or []:
            adjudication_rows[record["edge_id"]] = (authority, record)
    for authority, relpath in SEAL_FIXTURES.items():
        path = _repo(repo) / relpath
        if not path.is_file():
            raise RelationshipSemanticClosureError(
                f"source seal fixture missing: {relpath}",
                code="source_seal_fixture_missing",
                status_code=404,
            )
        payload = json.loads(path.read_text(encoding="utf-8"))
        for seal in payload.get("seals") or []:
            seal_rows[seal["edge_id"]] = (authority, seal)

    for unit in manifest["units"]:
        edge_id = unit["edge_id"]
        adj = adjudication_rows.get(edge_id)
        if adj is None:
            diagnostics.append(f"adjudication_row_missing:{edge_id}")
            continue
        authority, record = adj
        if authority != unit["authority"]:
            diagnostics.append(f"adjudication_authority_mismatch:{edge_id}")
        for key in ("disposition", "reason_code", "rationale", "next_action"):
            if record.get(key) != unit.get(key):
                diagnostics.append(f"adjudication_{key}_mismatch:{edge_id}")
        seal_entry = seal_rows.get(edge_id)
        if seal_entry is None:
            diagnostics.append(f"source_seal_row_missing:{edge_id}")
            continue
        seal_authority, seal = seal_entry
        if seal_authority != unit["authority"]:
            diagnostics.append(f"source_seal_authority_mismatch:{edge_id}")
        embedded = unit.get("seal") or {}
        for key in (
            "source_artifact_id",
            "artifact_content_sha256",
            "source_span_ref_id",
            "primary_evidence_ref_id",
            "excerpt_sha256",
            "artifact_uri",
        ):
            if key in seal and seal.get(key) != embedded.get(key):
                diagnostics.append(f"source_seal_mismatch:{edge_id}:{key}")
    return diagnostics


def _verify_live_source_seal(
    *,
    store: Any,
    root: Path,
    unit: dict[str, Any],
) -> list[str]:
    diagnostics: list[str] = []
    seal = unit.get("seal") or {}
    edge_id = unit["edge_id"]
    evidence_ref_id = seal.get("primary_evidence_ref_id")
    if not evidence_ref_id:
        diagnostics.append(f"live_seal_missing_primary_evidence:{edge_id}")
        return diagnostics
    try:
        live = resolve_evidence_excerpt(
            store,
            edge_id=edge_id,
            evidence_ref_id=evidence_ref_id,
            world_graph_root=root,
        )
        verify_excerpt_against_seal(live, seal, edge_id=edge_id)
    except RelationshipResidualAdjudicationError as exc:
        diagnostics.append(f"live_seal_failed:{edge_id}:{exc}")
    return diagnostics


def _verify_unit_target_source_seals(
    *,
    root: Path,
    store: Any,
    unit: dict[str, Any],
) -> list[str]:
    diagnostics: list[str] = []
    locked_map = unit.get("target_source_payload_sha256") or {}
    for contribution_id in unit.get("target_contribution_ids") or []:
        locked = locked_map.get(contribution_id)
        if not locked:
            diagnostics.append(f"target_source_digest_missing:{contribution_id}")
            continue
        ok, diag = _verify_locked_target_source_contribution_authority(
            root=root,
            store=store,
            contribution_id=contribution_id,
            locked_source_payload_sha256=locked,
            target_assertion_id=unit.get("target_assertion_id"),
        )
        if not ok:
            diagnostics.extend(diag)
    return diagnostics


def _expected_operation_authority_ids(manifest: dict[str, Any]) -> list[str]:
    """Locked per-op authority IDs in operation_plan order.

    Contribution ops use the locked contribution_id; identity ops use the
    locked identity-decision id. Each closure publish records exactly one of
    these as the revision ``operation_ids`` entry.
    """
    ids: list[str] = []
    for plan_op in manifest.get("operation_plan") or []:
        if plan_op["op"] == "identity_merge":
            ids.append(plan_op["expected_decision_id"])
        else:
            ids.append(plan_op["contribution_id"])
    return ids


def _prove_closure_operation_chain(
    *,
    root: Path,
    head_revision_id: str,
    manifest: dict[str, Any],
    expected_operation_count: int | None = None,
) -> tuple[bool, list[str]]:
    """Bind the post-Q₄ parent chain to an exact ``operation_plan`` prefix.

    Walks ``head → … → Q₄`` and requires:
    * exact descendant revision count == ``expected_operation_count``;
    * each revision carries exactly one ``operation_id``;
    * forward operation IDs match the locked authority IDs for ops ``1..k``.

    ``expected_operation_count`` defaults to the full plan (54) for finalizer use.
    Resume/preflight passes the currently applied op count so a foreign revision
    interleaved into a partial prefix fails closed before further mutation.
    """
    expected_all = _expected_operation_authority_ids(manifest)
    if len(expected_all) != OPERATION_PLAN_COUNT:
        return False, [
            f"closure_chain_expected_length_mismatch:{len(expected_all)}"
        ]
    k = (
        OPERATION_PLAN_COUNT
        if expected_operation_count is None
        else expected_operation_count
    )
    if k < 0 or k > OPERATION_PLAN_COUNT:
        return False, [f"closure_chain_prefix_out_of_range:{k}"]
    expected = expected_all[:k]

    if k == 0:
        if head_revision_id != BASE_REVISION_ID:
            return False, [
                "closure_chain_prefix_not_q4:"
                f"expected {BASE_REVISION_ID} head {head_revision_id}"
            ]
        return True, ["closure_operation_chain_prefix_exact:0"]

    newest_first_op_ids: list[str] = []
    current = head_revision_id
    seen: set[str] = set()
    while current != BASE_REVISION_ID:
        if current in seen:
            return False, [f"closure_chain_cycle:{current}"]
        seen.add(current)
        if len(newest_first_op_ids) > k:
            return False, [
                f"closure_chain_too_long:{len(newest_first_op_ids)}>{k}"
            ]
        try:
            rev = kernel.load_world_graph_revision_manifest(
                root, WORLD_ID, current
            )
        except WorldGraphNotFoundError:
            return False, [f"closure_chain_revision_missing:{current}"]
        if rev.parent_revision_id is None:
            return False, [f"closure_chain_broke_before_q4:{current}"]
        if len(rev.operation_ids) != 1:
            return False, [
                f"closure_chain_operation_arity:{current}:{len(rev.operation_ids)}"
            ]
        newest_first_op_ids.append(rev.operation_ids[0])
        current = rev.parent_revision_id

    forward = list(reversed(newest_first_op_ids))
    if len(forward) != k:
        return False, [f"closure_chain_length_mismatch:{len(forward)}!={k}"]
    if forward != expected:
        return False, ["closure_chain_operation_ids_mismatch"]
    diag = (
        "closure_operation_chain_exact"
        if k == OPERATION_PLAN_COUNT
        else f"closure_operation_chain_prefix_exact:{k}"
    )
    return True, [diag]


def _preflight(
    *,
    root: Path,
    manifest: dict[str, Any],
    expected_base_revision_id: str,
    repo: Path | None,
) -> list[str]:
    """Fail-closed whole-ledger verification. Returns diagnostics (empty = clean).

    Resume-aware: applied ops must form an exact ``operation_plan`` prefix, and
    the Q₄→head revision chain must be exactly that applied prefix (no foreign
    interleaved revisions) before any further mutation.
    Deferred units are never mutated; they remain residual and seal-verified.
    """
    diagnostics: list[str] = []

    try:
        head = kernel.open_world_graph_head(root, WORLD_ID)
    except WorldGraphNotFoundError:
        return [f"world_missing:{WORLD_ID}"]

    _h, _r, store = kernel.open_current_world_graph(root, WORLD_ID)
    plan_states = _operation_plan_states(root=root, store=store, manifest=manifest)
    diagnostics.extend(_assert_operation_plan_prefix(plan_states))

    applied_op_count = sum(1 for _op, state, _d in plan_states if state == "applied")
    states = _unit_states(root=root, store=store, manifest=manifest)
    if any(s.integrity_failure for s in states):
        diagnostics.append("unit_op_integrity_failure")

    # Bind head ancestry to the exact applied operation_plan prefix before any
    # resumed mutation. k=0 ⇒ head must be exact Q₄.
    chain_ok, chain_diags = _prove_closure_operation_chain(
        root=root,
        head_revision_id=head.head_revision_id or "",
        manifest=manifest,
        expected_operation_count=applied_op_count,
    )
    if not chain_ok:
        diagnostics.extend(chain_diags)
        if applied_op_count == 0 and head.head_revision_id != expected_base_revision_id:
            diagnostics.append(
                "stale_base:"
                f"expected {expected_base_revision_id} head {head.head_revision_id}"
            )
        # Chain ownership failed — refuse before further seal/mutation work.
        return diagnostics

    if applied_op_count == 0:
        eff = analyze_relationship_effective_conformance_v1(
            root=root, world_id=WORLD_ID, revision_id=expected_base_revision_id
        )
        inventory = {
            "semantic": eff.relationship_semantic_count,
            "represented": eff.relationship_effectively_represented_count,
            "residual": eff.relationship_effective_residual_count,
            "uses_statblock_mechanics": eff.uses_statblock_mechanics_count,
            "unadjudicated": eff.unadjudicated_remaining_count,
            "dungeonmind_owned": eff.dungeonmind_owned_remaining_count,
            "buddy_owned": eff.dungeonmindbuddy_owned_remaining_count,
        }
        if inventory != EXPECTED_BASE_INVENTORY:
            diagnostics.append(f"base_inventory_mismatch:{inventory}")
        residual_set = set(eff.remaining_residual_edge_ids)
    else:
        residual_set = None

    diagnostics.extend(_verify_fixture_rows(manifest, repo))

    seen_edges: set[str] = set()
    for unit, state in zip(manifest["units"], states, strict=True):
        edge_id = unit["edge_id"]
        if edge_id in seen_edges:
            diagnostics.append(f"duplicate_unit_edge:{edge_id}")
        seen_edges.add(edge_id)

        # Live source seals for every unit (including deferred).
        diagnostics.extend(
            _verify_live_source_seal(store=store, root=root, unit=unit)
        )
        # Original target-contribution authority stays sealed for the whole
        # prefix-resume program — including already-applied mutable units.
        diagnostics.extend(
            _verify_unit_target_source_seals(root=root, store=store, unit=unit)
        )

        if unit.get("deferred"):
            # Deferred residuals must remain supported residual edges.
            if residual_set is not None and edge_id not in residual_set:
                diagnostics.append(f"deferred_edge_not_residual:{edge_id}")
            row = _support_row(store, unit["target_assertion_id"])
            if row is None or row.get("support_state") != "supported":
                diagnostics.append(f"deferred_assertion_not_supported:{edge_id}")
            if not _active_edge_assertion_ids(store, edge_id):
                diagnostics.append(f"deferred_edge_not_current:{edge_id}")
            continue

        if state.applied:
            continue

        # Pending mutable units: edge still residual at base; pending-op checks.
        if residual_set is not None and edge_id not in residual_set:
            diagnostics.append(f"unit_edge_not_residual:{edge_id}")
        edge = store.edges.get(edge_id)
        if edge is None:
            diagnostics.append(f"unit_edge_missing:{edge_id}")
            continue
        shape = unit["edge_shape"]
        if (
            edge.source_node_id != shape["source"]
            or edge.target_node_id != shape["target"]
            or edge.predicate != shape["predicate"]
        ):
            diagnostics.append(f"unit_edge_shape_drift:{edge_id}")

        row = _support_row(store, unit["target_assertion_id"])
        if row is None:
            diagnostics.append(f"unit_assertion_support_missing:{edge_id}")
            continue
        if row.get("graph_object_id") != edge_id:
            diagnostics.append(f"unit_assertion_edge_mismatch:{edge_id}")
        if row.get("assertion_kind") != "edge":
            diagnostics.append(f"unit_assertion_not_edge:{edge_id}")

        for index, op in enumerate(unit["operations"]):
            label = _op_label(op, index)
            if label in state.applied_operations:
                continue
            if op["op"] in {"contradict", "correct"}:
                # Only require still-supported shape when no prior op of this unit applied.
                if not state.applied_operations:
                    if row is not None and row.get("support_state") != "supported":
                        diagnostics.append(f"unit_assertion_not_supported:{edge_id}")
                    active = sorted((row or {}).get("active_contribution_ids") or [])
                    if active != sorted(unit["target_contribution_ids"]):
                        diagnostics.append(
                            f"unit_active_support_mismatch:{edge_id}:{active}"
                        )
                contribution = _unit_contribution(manifest, op["contribution_id"])
                digest = kernel.compute_contribution_source_payload_sha256(contribution)
                if digest != op.get("source_payload_sha256"):
                    diagnostics.append(
                        f"unit_contribution_digest_mismatch:{op['contribution_id']}"
                    )
            elif op["op"] == "merge_additive":
                contribution = _unit_contribution(manifest, op["contribution_id"])
                digest = kernel.compute_contribution_source_payload_sha256(contribution)
                if digest != op.get("source_payload_sha256"):
                    diagnostics.append(
                        f"unit_contribution_digest_mismatch:{op['contribution_id']}"
                    )
            elif op["op"] == "identity_merge":
                for node_key in ("source_node_id", "target_node_id"):
                    if op[node_key] not in store.nodes:
                        diagnostics.append(
                            f"unit_identity_node_missing:{edge_id}:{op[node_key]}"
                        )
                recomputed = compute_identity_decision_id(
                    world_id=WORLD_ID,
                    decision_kind="merge",
                    subject_node_id=op["source_node_id"],
                    target_node_id=op["target_node_id"],
                    alias=None,
                    source_candidate_id=None,
                    reason=op["merge_reason"],
                )
                if recomputed != op["expected_decision_id"]:
                    diagnostics.append(f"unit_identity_decision_mismatch:{edge_id}")
            else:
                diagnostics.append(f"unit_unknown_op:{edge_id}:{op['op']}")

    return diagnostics


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def get_relationship_semantic_closure_status(
    *,
    root: Path | None = None,
    expected_base_revision_id: str | None = None,
    repo: Path | None = None,
) -> RelationshipSemanticClosureStatus:
    """Read-only closure status against the locked manifest."""
    manifest = _load_manifest(repo=repo)
    world_root = _resolve_root(root)
    expected = (expected_base_revision_id or BASE_REVISION_ID).strip()

    try:
        _h, _r, store = kernel.open_current_world_graph(world_root, WORLD_ID)
    except WorldGraphNotFoundError:
        return RelationshipSemanticClosureStatus(
            eligibility="ineligible",
            reason="world graph missing",
            head_revision_id=None,
            diagnostics=["world_missing"],
        )

    states = _unit_states(root=world_root, store=store, manifest=manifest)
    plan_states = _operation_plan_states(
        root=world_root, store=store, manifest=manifest
    )
    prefix_diags = _assert_operation_plan_prefix(plan_states)

    mutable_states = [s for s in states if not s.deferred]
    deferred_states = [s for s in states if s.deferred]
    fully_applied = [s for s in mutable_states if s.applied]
    pending = [s for s in mutable_states if not s.applied]
    applied_op_count = sum(1 for _op, state, _d in plan_states if state == "applied")

    chain_ok, chain_diags = _prove_closure_operation_chain(
        root=world_root,
        head_revision_id=_h.head_revision_id or "",
        manifest=manifest,
        expected_operation_count=applied_op_count,
    )

    if prefix_diags or any(s.integrity_failure for s in states):
        eligibility: ClosureEligibility = "integrity_failure"
        reason = "applied ops are not an authority-safe operation_plan prefix"
        diagnostics = ["integrity_failure", *prefix_diags, *chain_diags]
    elif not chain_ok:
        if applied_op_count == 0 and _h.head_revision_id != expected:
            eligibility = "ineligible"
            reason = (
                f"head {_h.head_revision_id!r} is not the exact closure base "
                f"{expected!r} and no closure op is applied"
            )
            diagnostics = ["stale_base", *chain_diags]
        else:
            eligibility = "integrity_failure"
            reason = (
                "Q4→head revision chain is not the exact applied operation_plan "
                f"prefix ({applied_op_count} ops)"
            )
            diagnostics = ["integrity_failure", *chain_diags]
    elif not pending:
        eligibility = "already_applied"
        reason = (
            f"all {MUTABLE_UNIT_COUNT} mutable closure units are applied at head; "
            f"{DEFERRED_UNIT_COUNT} deferred kind-repair residuals remain open"
        )
        diagnostics = ["status_ok", "already_applied", *chain_diags]
    elif applied_op_count > 0 or fully_applied:
        eligibility = "partially_applied"
        reason = (
            f"{len(fully_applied)} mutable units fully applied, "
            f"{len(pending)} pending "
            f"({applied_op_count}/{OPERATION_PLAN_COUNT} ops applied)"
        )
        diagnostics = ["status_ok", "partially_applied", *chain_diags]
    elif _h.head_revision_id != expected:
        eligibility = "ineligible"
        reason = (
            f"head {_h.head_revision_id!r} is not the exact closure base "
            f"{expected!r} and no closure op is applied"
        )
        diagnostics = ["stale_base", *chain_diags]
    else:
        eligibility = "eligible"
        reason = (
            "head is the exact closure base; no mutable unit applied yet; "
            f"{DEFERRED_UNIT_COUNT} deferred residuals will remain open"
        )
        diagnostics = ["status_ok", *chain_diags]

    return RelationshipSemanticClosureStatus(
        head_revision_id=_h.head_revision_id,
        eligibility=eligibility,
        reason=reason,
        unit_count=len(states),
        mutable_unit_count=len(mutable_states),
        deferred_unit_count=len(deferred_states),
        applied_unit_count=len(fully_applied),
        next_pending_unit_id=pending[0].unit_id if pending else None,
        units=states,
        diagnostics=diagnostics,
    )


def apply_relationship_semantic_closure(
    *,
    expected_base_revision_id: str,
    root: Path | None = None,
    repo: Path | None = None,
    allow_live_world: bool = False,
) -> RelationshipSemanticClosureResult:
    """Apply the mutable closure program in operation_plan order (prefix-safe)."""
    if not expected_base_revision_id or not expected_base_revision_id.strip():
        raise RelationshipSemanticClosureError(
            "expected_base_revision_id is required", code="expected_base_required"
        )
    expected = expected_base_revision_id.strip()
    if expected != BASE_REVISION_ID:
        raise RelationshipSemanticClosureError(
            f"closure base must be exact Q4 {BASE_REVISION_ID!r}; got {expected!r}",
            code="base_mismatch",
        )
    world_root = _resolve_root(root)
    if _is_canonical_live_root(world_root) and not allow_live_world:
        raise RelationshipSemanticClosureError(
            "canonical live world root requires allow_live_world=True",
            code="live_world_opt_in_required",
        )

    manifest = _load_manifest(repo=repo)
    deferred_unit_ids = [
        u["unit_id"] for u in manifest["units"] if u.get("deferred")
    ]

    preflight_diags = _preflight(
        root=world_root,
        manifest=manifest,
        expected_base_revision_id=expected,
        repo=repo,
    )
    if preflight_diags:
        raise RelationshipSemanticClosureError(
            "closure preflight failed: " + "; ".join(preflight_diags[:10]),
            code="preflight_failed",
        )

    published: list[str] = []
    applied_units: list[str] = []
    already_applied: list[str] = []
    diagnostics: list[str] = []

    for unit in manifest["units"]:
        if unit.get("deferred"):
            diagnostics.append(f"unit_deferred_skipped:{unit['unit_id']}")
            continue

        _h, _r, store = kernel.open_current_world_graph(world_root, WORLD_ID)
        if all(
            _op_applied(store, unit, op, root=world_root, manifest=manifest)
            for op in unit["operations"]
        ):
            already_applied.append(unit["unit_id"])
            diagnostics.append(f"unit_already_applied:{unit['unit_id']}")
            continue

        try:
            for index, op in enumerate(unit["operations"]):
                # Intra-unit prefix: refuse op N if any earlier op is not applied.
                for earlier_index, earlier_op in enumerate(unit["operations"][:index]):
                    _h, _r, store = kernel.open_current_world_graph(
                        world_root, WORLD_ID
                    )
                    if not _op_applied(
                        store, unit, earlier_op, root=world_root, manifest=manifest
                    ):
                        raise RelationshipSemanticClosureError(
                            f"applied_ops_not_a_prefix at {unit['unit_id']} "
                            f"op#{index} while op#{earlier_index} pending",
                            code="applied_ops_not_a_prefix",
                        )

                head_now = kernel.open_world_graph_head(world_root, WORLD_ID)
                parent = head_now.head_revision_id
                _h, _r, store = kernel.open_current_world_graph(world_root, WORLD_ID)
                if _op_applied(store, unit, op, root=world_root, manifest=manifest):
                    diagnostics.append(
                        f"op_already_applied:{unit['unit_id']}:{op['op']}"
                    )
                    continue
                if op["op"] == "contradict":
                    contribution = _unit_contribution(manifest, op["contribution_id"])
                    locked = op.get("source_payload_sha256")
                    digest = kernel.compute_contribution_source_payload_sha256(
                        contribution
                    )
                    if locked and digest != locked:
                        raise RelationshipSemanticClosureError(
                            f"contribution digest drift for {op['contribution_id']}",
                            code="contribution_digest_drift",
                        )
                    merge = kernel.contradict_edge_assertion_support(
                        world_root,
                        world_id=WORLD_ID,
                        contribution=contribution,
                        expected_parent_revision_id=parent,
                    )
                elif op["op"] == "correct":
                    contribution = _unit_contribution(manifest, op["contribution_id"])
                    locked = op.get("source_payload_sha256")
                    digest = kernel.compute_contribution_source_payload_sha256(
                        contribution
                    )
                    if locked and digest != locked:
                        raise RelationshipSemanticClosureError(
                            f"contribution digest drift for {op['contribution_id']}",
                            code="contribution_digest_drift",
                        )
                    merge = kernel.correct_edge_assertion_support(
                        world_root,
                        world_id=WORLD_ID,
                        contribution=contribution,
                        expected_parent_revision_id=parent,
                    )
                elif op["op"] == "merge_additive":
                    contribution = _unit_contribution(manifest, op["contribution_id"])
                    locked = op.get("source_payload_sha256")
                    digest = kernel.compute_contribution_source_payload_sha256(
                        contribution
                    )
                    if locked and digest != locked:
                        raise RelationshipSemanticClosureError(
                            f"contribution digest drift for {op['contribution_id']}",
                            code="contribution_digest_drift",
                        )
                    merge = kernel.merge_contribution_to_revision(
                        world_root,
                        world_id=WORLD_ID,
                        contribution=contribution,
                        expected_parent_revision_id=parent,
                    )
                elif op["op"] == "identity_merge":
                    updated, decision = merge_identity(
                        store,
                        world_id=WORLD_ID,
                        source_node_id=op["source_node_id"],
                        target_node_id=op["target_node_id"],
                        actor=AUTHORED_BY,
                        reason=op["merge_reason"],
                    )
                    if decision.decision_id != op["expected_decision_id"]:
                        raise RelationshipSemanticClosureError(
                            f"identity decision drift for {unit['unit_id']}: "
                            f"{decision.decision_id} != {op['expected_decision_id']}",
                            code="identity_decision_drift",
                        )
                    publish = kernel.publish_world_revision(
                        world_root,
                        WORLD_ID,
                        updated,
                        operation_ids=[decision.decision_id],
                        expected_parent_revision_id=parent,
                    )
                    published.append(publish.revision.revision_id)
                    diagnostics.append(
                        f"identity_merged:{unit['unit_id']}:{decision.decision_id}"
                    )
                    continue
                else:  # pragma: no cover - manifest verified at load
                    raise RelationshipSemanticClosureError(
                        f"unknown closure op {op['op']!r}",
                        code="closure_manifest_invalid",
                    )
                if merge.failure_code:
                    raise RelationshipSemanticClosureError(
                        f"kernel op failed for {unit['unit_id']}:{op['op']}: "
                        f"{merge.failure_code} {merge.failure_message}",
                        code="kernel_op_failed",
                    )
                if merge.published and merge.revision_id:
                    published.append(merge.revision_id)
                diagnostics.append(f"op_applied:{unit['unit_id']}:{op['op']}")
        except (ValueError, RelationshipSemanticClosureError) as exc:
            code = (
                exc.code
                if isinstance(exc, RelationshipSemanticClosureError)
                else "kernel_rejected"
            )
            return RelationshipSemanticClosureResult(
                expected_base_revision_id=expected,
                final_revision_id=kernel.open_world_graph_head(
                    world_root, WORLD_ID
                ).head_revision_id,
                published_revision_ids=published,
                applied_unit_ids=applied_units,
                already_applied_unit_ids=already_applied,
                deferred_unit_ids=deferred_unit_ids,
                failed_unit_id=unit["unit_id"],
                failure_code=code,
                failure_message=str(exc),
                diagnostics=diagnostics,
            )
        applied_units.append(unit["unit_id"])

    final_head = kernel.open_world_graph_head(world_root, WORLD_ID).head_revision_id
    pin = verify_relationship_semantic_closure(root=world_root, repo=repo)
    return RelationshipSemanticClosureResult(
        expected_base_revision_id=expected,
        final_revision_id=final_head,
        published_revision_ids=published,
        applied_unit_ids=applied_units,
        already_applied_unit_ids=already_applied,
        deferred_unit_ids=deferred_unit_ids,
        final_inventory=pin.final_inventory if pin else None,
        verify_passed=pin is not None,
        diagnostics=[
            *diagnostics,
            "closure_applied" if pin else "closure_verify_failed",
        ],
    )


def verify_relationship_semantic_closure(
    *,
    root: Path | None = None,
    repo: Path | None = None,
) -> RelationshipSemanticClosurePin | None:
    """Verify the post-closure head; return the pin when the governed exit holds."""
    manifest = _load_manifest(repo=repo)
    world_root = _resolve_root(root)
    diagnostics: list[str] = []
    try:
        head = kernel.open_world_graph_head(world_root, WORLD_ID)
    except WorldGraphNotFoundError:
        return None

    head_revision_id = head.head_revision_id
    if not head_revision_id:
        return None

    ancestry_ok, ancestry_diag, ancestry_detail = prove_revision_is_anchor_or_descendant_v1(
        root=world_root,
        world_id=WORLD_ID,
        requested_revision_id=head_revision_id,
        anchor_revision_id=BASE_REVISION_ID,
        anchor_world_id=WORLD_ID,
    )
    if not ancestry_ok:
        return None
    diagnostics.append("q4_ancestry_proven")
    if ancestry_diag:
        diagnostics.append(str(ancestry_diag))
    if ancestry_detail:
        diagnostics.append(str(ancestry_detail))

    chain_ok, chain_diags = _prove_closure_operation_chain(
        root=world_root,
        head_revision_id=head_revision_id,
        manifest=manifest,
    )
    if not chain_ok:
        return None
    diagnostics.extend(chain_diags)

    try:
        pinned = kernel.rebuild_from_contributions(
            world_root,
            world_id=WORLD_ID,
            compare_revision_id=head_revision_id,
            publish=False,
        )
        pinned_diag = list(getattr(pinned, "diagnostics", []) or [])
        if "rebuild_equivalent_to_pinned_revision" not in pinned_diag:
            return None
        diagnostics.append("rebuild_equivalent_to_pinned_revision")

        unpinned = kernel.rebuild_from_contributions(
            world_root,
            world_id=WORLD_ID,
            publish=False,
        )
        unpinned_diag = list(getattr(unpinned, "diagnostics", []) or [])
        if not (
            "rebuild_equivalent_to_head" in unpinned_diag
            or "rebuild_equivalent_to_published_head" in unpinned_diag
        ):
            return None
        diagnostics.append(
            "rebuild_equivalent_to_head"
            if "rebuild_equivalent_to_head" in unpinned_diag
            else "rebuild_equivalent_to_published_head"
        )
    except (ValueError, RuntimeError):
        return None

    eff = analyze_relationship_effective_conformance_v1(
        root=world_root, world_id=WORLD_ID, revision_id=head_revision_id
    )
    inventory = {
        "semantic": eff.relationship_semantic_count,
        "represented": eff.relationship_effectively_represented_count,
        "residual": eff.relationship_effective_residual_count,
        "uses_statblock_mechanics": eff.uses_statblock_mechanics_count,
    }
    if inventory != EXPECTED_FINAL_INVENTORY:
        return None
    remaining = set(eff.remaining_residual_edge_ids)
    if remaining != DEFERRED_RESIDUAL_EDGE_IDS:
        return None
    diagnostics.append("final_inventory_matches")
    diagnostics.append("deferred_residuals_exact")

    _h, _r, store = kernel.open_current_world_graph(world_root, WORLD_ID)
    plan_states = _operation_plan_states(
        root=world_root, store=store, manifest=manifest
    )
    if any(state != "applied" for _op, state, _d in plan_states):
        return None
    diagnostics.append("all_mutable_ops_applied")

    for unit in manifest["units"]:
        seal_diags = _verify_live_source_seal(
            store=store, root=world_root, unit=unit
        )
        if seal_diags:
            return None
        target_diags = _verify_unit_target_source_seals(
            root=world_root, store=store, unit=unit
        )
        if target_diags:
            return None
        if not unit.get("deferred"):
            continue
        edge_id = unit["edge_id"]
        if edge_id not in remaining:
            return None
        row = _support_row(store, unit["target_assertion_id"])
        if row is None or row.get("support_state") != "supported":
            return None
        if not _active_edge_assertion_ids(store, edge_id):
            return None
    diagnostics.append("all_units_live_source_sealed")
    diagnostics.append("all_units_target_source_sealed")
    diagnostics.append("deferred_units_still_supported_residual")

    # Every closure contribution in the operation_plan is revision-bound.
    for plan_op in manifest.get("operation_plan") or []:
        if plan_op["op"] == "identity_merge":
            expected = plan_op["expected_decision_id"]
            try:
                record = load_identity_decision_record(
                    world_root, WORLD_ID, expected
                )
            except FileNotFoundError:
                return None
            if record.status != "active":
                return None
            continue
        cid = plan_op["contribution_id"]
        locked = plan_op["source_payload_sha256"]
        ok, _diag = _revision_bound_contribution_authority(
            root=world_root,
            store=store,
            contribution_id=cid,
            locked_source_payload_sha256=locked,
        )
        if not ok:
            return None
    diagnostics.append("closure_contributions_revision_bound")
    diagnostics.append("identity_decisions_durable_active")
    diagnostics.append("closure_verified")

    return RelationshipSemanticClosurePin(
        final_revision_id=head_revision_id,
        final_graph_payload_sha256=eff.source_graph_payload_sha256,
        final_inventory=inventory,
        residual_edge_ids=sorted(DEFERRED_RESIDUAL_EDGE_IDS),
        diagnostics=diagnostics,
    )


def finalize_relationship_semantic_closure(
    *,
    root: Path | None = None,
    repo: Path | None = None,
    allow_live_world: bool = False,
) -> RelationshipSemanticClosurePin:
    """§18 finalizer: refuse unless verify proves the governed residual=9 exit."""
    world_root = _resolve_root(root)
    if _is_canonical_live_root(world_root) and not allow_live_world:
        raise RelationshipSemanticClosureError(
            "canonical live world root requires allow_live_world=True",
            code="live_world_opt_in_required",
        )
    pin = verify_relationship_semantic_closure(root=world_root, repo=repo)
    if pin is None:
        raise RelationshipSemanticClosureError(
            "closure finalization refused: head does not verify as a complete "
            "closure exit (inventory 323/314/9/3 with deferred residuals intact, "
            "exact Q4→head operation_plan chain, and rebuild equivalence)",
            code="finalize_refused",
        )
    return pin
