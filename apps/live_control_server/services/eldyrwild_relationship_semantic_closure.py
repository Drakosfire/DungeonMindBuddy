"""Governed apply for the Eldyrwild relationship semantic closure program.

Loads the locked 55-row closure manifest (plus its four hash-sealed child
artifacts), proves whole-ledger preflight against the exact Q4 base revision,
and applies closure units in manifest order through existing Kernel seams:

* ``contradict_edge_assertion_support`` for contradiction-only units and for
  the compound/identity edge contradictions;
* ``correct_edge_assertion_support`` for the two governed replacements;
* ``merge_contribution_to_revision`` for the one compound decomposition atomic;
* ``merge_identity`` + ``publish_world_revision`` for the seven durable
  identity migrations (decision payloads are synced to the durable
  ``identity_decisions/`` ledger on publish).

Callers cannot inject different artifacts, unit order, targets, or semantics:
the manifest bytes are sha256-locked here and child artifacts are verified
against the manifest before any mutation. Apply is prefix-safe: an already
applied prefix is skipped, a non-prefix applied set is refused.
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
from apps.live_control_server.integrations.dungeonmind_kernel.relationship_effective_conformance_v1 import (
    analyze_relationship_effective_conformance_v1,
)
from graph_memory.kernel.contribution_models import GraphContribution
from graph_memory.kernel.identity_decisions import (
    compute_identity_decision_id,
    merge_identity,
)
from graph_memory.world_supergraph.contribution_store import (
    load_contribution_record,
)
from graph_memory.world_supergraph.errors import WorldGraphNotFoundError

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
    "ff52a6ddbd55f3339d89dd26aa286107eb3f473f184072a0c5182dfe25822423"
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
    "semantic": 314,
    "represented": 314,
    "residual": 0,
    "uses_statblock_mechanics": 3,
}

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


class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class ClosureUnitState(_Model):
    unit_id: str
    ordinal: int
    edge_id: str
    closure_kind: str
    applied: bool
    applied_operations: list[str] = Field(default_factory=list)
    pending_operations: list[str] = Field(default_factory=list)


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
    units = manifest.get("units") or []
    if len(units) != 55 or manifest.get("unit_order") != [u["unit_id"] for u in units]:
        raise RelationshipSemanticClosureError(
            "closure manifest unit order mismatch", code="closure_manifest_invalid"
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
                return GraphContribution.model_validate(contribs[contribution_id])
    raise RelationshipSemanticClosureError(
        f"contribution {contribution_id} not found in closure artifacts",
        code="closure_artifact_invalid",
    )


# ---------------------------------------------------------------------------
# Per-operation applied detection (prefix-safe resume)
# ---------------------------------------------------------------------------


def _support_row(store: Any, assertion_id: str) -> dict[str, Any] | None:
    support = store.assertion_support or {}
    row = support.get(assertion_id)
    if row is None:
        return None
    if isinstance(row, dict):
        return row
    return row.model_dump(mode="json")


def _correction_op_applied(
    store: Any, unit: dict[str, Any], contribution_id: str
) -> bool:
    bound = set((store.contribution_source_payload_sha256 or {}).keys())
    if contribution_id not in bound:
        return False
    row = _support_row(store, unit["target_assertion_id"])
    if row is None:
        return False
    return row.get("support_state") == "contradicted"


def _additive_op_applied(store: Any, contribution_id: str) -> bool:
    bound = set((store.contribution_source_payload_sha256 or {}).keys())
    if contribution_id not in bound:
        return False
    manifest = store.contribution_replay_manifest or []
    for entry in manifest:
        if isinstance(entry, dict):
            entry_id = entry.get("contribution_id")
            entry_status = entry.get("status")
        else:
            entry_id = entry.contribution_id
            entry_status = entry.status
        if entry_id == contribution_id:
            return entry_status == "active"
    return True


def _identity_merge_op_applied(store: Any, op: dict[str, Any]) -> bool:
    source = store.nodes.get(op["source_node_id"])
    if source is None:
        return False
    state = dict(source.state or {})
    if state.get("merged_into") != op["target_node_id"]:
        return False
    decisions = store.identity_decisions or []
    expected = op["expected_decision_id"]
    for raw in decisions:
        decision_id = raw.get("decision_id") if isinstance(raw, dict) else raw.decision_id
        if decision_id == expected:
            return True
    return False


def _op_applied(store: Any, unit: dict[str, Any], op: dict[str, Any]) -> bool:
    kind = op["op"]
    if kind in {"contradict", "correct"}:
        return _correction_op_applied(store, unit, op["contribution_id"])
    if kind == "merge_additive":
        return _additive_op_applied(store, op["contribution_id"])
    if kind == "identity_merge":
        return _identity_merge_op_applied(store, op)
    raise RelationshipSemanticClosureError(
        f"unknown closure op {kind!r}", code="closure_manifest_invalid"
    )


def _unit_states(store: Any, manifest: dict[str, Any]) -> list[ClosureUnitState]:
    states: list[ClosureUnitState] = []
    for unit in manifest["units"]:
        applied_ops: list[str] = []
        pending_ops: list[str] = []
        for index, op in enumerate(unit["operations"]):
            label = f"{op['op']}#{index}"
            if _op_applied(store, unit, op):
                applied_ops.append(label)
            else:
                pending_ops.append(label)
        states.append(
            ClosureUnitState(
                unit_id=unit["unit_id"],
                ordinal=unit["ordinal"],
                edge_id=unit["edge_id"],
                closure_kind=unit["closure_kind"],
                applied=not pending_ops,
                applied_operations=applied_ops,
                pending_operations=pending_ops,
            )
        )
    return states


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


def _preflight(
    *,
    root: Path,
    manifest: dict[str, Any],
    expected_base_revision_id: str,
    repo: Path | None,
) -> list[str]:
    """Fail-closed whole-ledger verification. Returns diagnostics (empty = clean).

    Resume-aware: units already applied at head are exempt from live-state
    checks; the applied set must form an exact manifest-order prefix.
    """
    diagnostics: list[str] = []

    try:
        head = kernel.open_world_graph_head(root, WORLD_ID)
    except WorldGraphNotFoundError:
        return [f"world_missing:{WORLD_ID}"]

    _h, _r, store = kernel.open_current_world_graph(root, WORLD_ID)
    states = _unit_states(store, manifest)
    applied_flags = [s.applied for s in states]
    applied_count = sum(applied_flags)
    first_pending = next(
        (i for i, flag in enumerate(applied_flags) if not flag), len(applied_flags)
    )
    if any(applied_flags[first_pending:]):
        diagnostics.append("applied_units_not_a_prefix")

    if applied_count == 0:
        if head.head_revision_id != expected_base_revision_id:
            diagnostics.append(
                "stale_base:"
                f"expected {expected_base_revision_id} head {head.head_revision_id}"
            )
            return diagnostics
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
        if state.applied:
            continue

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

        # Per-op live checks only for ops still pending.
        for index, op in enumerate(unit["operations"]):
            label = f"{op['op']}#{index}"
            if label in state.applied_operations:
                continue
            if op["op"] in {"contradict", "correct"}:
                if row is not None and row.get("support_state") != "supported":
                    diagnostics.append(f"unit_assertion_not_supported:{edge_id}")
                active = sorted((row or {}).get("active_contribution_ids") or [])
                if active != sorted(unit["target_contribution_ids"]):
                    diagnostics.append(
                        f"unit_active_support_mismatch:{edge_id}:{active}"
                    )
                for contribution_id in unit["target_contribution_ids"]:
                    try:
                        contribution = load_contribution_record(
                            root, WORLD_ID, contribution_id
                        )
                    except FileNotFoundError:
                        diagnostics.append(
                            f"unit_target_contribution_missing:{contribution_id}"
                        )
                        continue
                    if not any(
                        a.assertion_id == unit["target_assertion_id"]
                        for a in contribution.accepted_assertions
                    ):
                        diagnostics.append(
                            f"unit_target_contribution_lacks_assertion:{contribution_id}"
                        )
                _unit_contribution(manifest, op["contribution_id"])
            elif op["op"] == "merge_additive":
                _unit_contribution(manifest, op["contribution_id"])
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

    states = _unit_states(store, manifest)
    applied = [s for s in states if s.applied]
    pending = [s for s in states if not s.applied]

    if not pending:
        eligibility: ClosureEligibility = "already_applied"
        reason = "all 55 closure units are applied at head"
    elif applied:
        eligibility = "partially_applied"
        reason = f"{len(applied)} units applied, {len(pending)} pending"
    elif _h.head_revision_id != expected:
        eligibility = "ineligible"
        reason = (
            f"head {_h.head_revision_id!r} is not the exact closure base "
            f"{expected!r} and no closure unit is applied"
        )
    else:
        eligibility = "eligible"
        reason = "head is the exact closure base; no unit applied yet"

    return RelationshipSemanticClosureStatus(
        head_revision_id=_h.head_revision_id,
        eligibility=eligibility,
        reason=reason,
        unit_count=len(states),
        applied_unit_count=len(applied),
        next_pending_unit_id=pending[0].unit_id if pending else None,
        units=states,
        diagnostics=["status_ok"],
    )


def apply_relationship_semantic_closure(
    *,
    expected_base_revision_id: str,
    root: Path | None = None,
    repo: Path | None = None,
    allow_live_world: bool = False,
) -> RelationshipSemanticClosureResult:
    """Apply the 55-unit closure program in manifest order (prefix-safe)."""
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
        _h, _r, store = kernel.open_current_world_graph(world_root, WORLD_ID)
        if all(_op_applied(store, unit, op) for op in unit["operations"]):
            already_applied.append(unit["unit_id"])
            diagnostics.append(f"unit_already_applied:{unit['unit_id']}")
            continue
        try:
            for op in unit["operations"]:
                head_now = kernel.open_world_graph_head(world_root, WORLD_ID)
                parent = head_now.head_revision_id
                _h, _r, store = kernel.open_current_world_graph(world_root, WORLD_ID)
                if _op_applied(store, unit, op):
                    diagnostics.append(f"op_already_applied:{unit['unit_id']}:{op['op']}")
                    continue
                if op["op"] == "contradict":
                    contribution = _unit_contribution(manifest, op["contribution_id"])
                    merge = kernel.contradict_edge_assertion_support(
                        world_root,
                        world_id=WORLD_ID,
                        contribution=contribution,
                        expected_parent_revision_id=parent,
                    )
                elif op["op"] == "correct":
                    contribution = _unit_contribution(manifest, op["contribution_id"])
                    merge = kernel.correct_edge_assertion_support(
                        world_root,
                        world_id=WORLD_ID,
                        contribution=contribution,
                        expected_parent_revision_id=parent,
                    )
                elif op["op"] == "merge_additive":
                    contribution = _unit_contribution(manifest, op["contribution_id"])
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
    """Verify the post-closure head inventory; return the pin when clean."""
    manifest = _load_manifest(repo=repo)
    world_root = _resolve_root(root)
    try:
        head = kernel.open_world_graph_head(world_root, WORLD_ID)
    except WorldGraphNotFoundError:
        return None
    eff = analyze_relationship_effective_conformance_v1(
        root=world_root, world_id=WORLD_ID, revision_id=head.head_revision_id
    )
    inventory = {
        "semantic": eff.relationship_semantic_count,
        "represented": eff.relationship_effectively_represented_count,
        "residual": eff.relationship_effective_residual_count,
        "uses_statblock_mechanics": eff.uses_statblock_mechanics_count,
    }
    if inventory != EXPECTED_FINAL_INVENTORY:
        return None
    _h, _r, store = kernel.open_current_world_graph(world_root, WORLD_ID)
    states = _unit_states(store, manifest)
    if not all(s.applied for s in states):
        return None
    return RelationshipSemanticClosurePin(
        final_revision_id=head.head_revision_id,
        final_graph_payload_sha256=eff.source_graph_payload_sha256,
        final_inventory=inventory,
        residual_edge_ids=list(eff.remaining_residual_edge_ids),
        diagnostics=["closure_verified"],
    )


def finalize_relationship_semantic_closure(
    *,
    root: Path | None = None,
    repo: Path | None = None,
    allow_live_world: bool = False,
) -> RelationshipSemanticClosurePin:
    """§18 finalizer: refuse nonzero residual; emit the live pin."""
    world_root = _resolve_root(root)
    if _is_canonical_live_root(world_root) and not allow_live_world:
        raise RelationshipSemanticClosureError(
            "canonical live world root requires allow_live_world=True",
            code="live_world_opt_in_required",
        )
    pin = verify_relationship_semantic_closure(root=world_root, repo=repo)
    if pin is None:
        raise RelationshipSemanticClosureError(
            "closure finalization refused: head does not verify as a complete, "
            "zero-residual closure exit",
            code="finalize_refused",
        )
    return pin
