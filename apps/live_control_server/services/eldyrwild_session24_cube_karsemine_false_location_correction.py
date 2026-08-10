"""Governed one-off apply for Session-24 cube→Karsemine false-location correction.

Loads exactly one checked-in GraphContribution (contradiction without replacement),
proves eligible-parent preconditions against adjudication/continuity/source-seal
authority, and delegates publication to
``graph_memory.kernel.contradict_edge_assertion_support``.

Callers cannot inject a different correction artifact, target IDs, or
replacement semantics.
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
    analyze_relationship_adjudication_continuity_v1,
    prove_revision_is_anchor_or_descendant_v1,
)
from apps.live_control_server.integrations.dungeonmind_kernel.relationship_effective_conformance_v1 import (
    analyze_relationship_effective_conformance_v1,
)
from apps.live_control_server.integrations.dungeonmind_kernel.relationship_residual_adjudication import (
    ELDYRWILD_REVISION_ID,
    ELDYRWILD_WORLD_ID,
)
from graph_memory.kernel.contribution_models import GraphContribution
from graph_memory.world_supergraph.contribution_store import load_contribution_record
from graph_memory.world_supergraph.errors import WorldGraphNotFoundError

APPROVED_CORRECTION_RELPATH = (
    "graph_data/approved_graph_corrections/eldyrwild/"
    "session24-cube-karsemine-false-location-v1.json"
)
SOURCE_SEAL_RELPATH = (
    "tests/fixtures/dungeonmind_kernel/"
    "eldyrwild_relationship_residual_source_seals_v1.json"
)

WORLD_ID = ELDYRWILD_WORLD_ID
CAMPAIGN_ID = "longmont-c2"
ANCHOR_REVISION_ID = ELDYRWILD_REVISION_ID
R_CURRENT_REVISION_ID = "rev:b90646fb5b135988bd7842cde858c96e"

TARGET_EDGE_ID = "edge:item-001:located_in:pc:karsemine"
TARGET_SOURCE_NODE_ID = "item-001"
TARGET_TARGET_NODE_ID = "pc:karsemine"
TARGET_PREDICATE = "located_in"
TARGET_ASSERTION_ID = "assertion:d27dd4e9041147bc"

# Historical adjudication candidates; live A(X) must be a non-empty subset.
HISTORICAL_ADJUDICATED_SUPPORT_IDS = frozenset(
    {
        "contribution:fe483d91c47590a1",
        "contribution:a01be11c6967afd9",
    }
)

# Exact live A(X) sealed into C at BUILD capture (subset of historical).
LOCKED_TARGET_CONTRIBUTION_IDS = frozenset({"contribution:fe483d91c47590a1"})

LOCKED_CORRECTION_CONTRIBUTION_ID = "contribution:6c13bc0f8edf4377"
LOCKED_CORRECTION_SOURCE_PAYLOAD_SHA256 = (
    "b48de88cad19a21360c103d86edd3de17818249c72f6146daf7e04e076747e6d"
)
LOCKED_CORRECTION_RAW_ARTIFACT_SHA256 = (
    "a06a12f75c0d1ca1e8659aa0ad5fbfa01214c6b3b7d8db6638d7706f634da159"
)
LOCKED_SOURCE_ARTIFACT_ID = (
    "graph-native:eldyrwild-correction:session24-cube-karsemine-false-location-v1"
)
LOCKED_SOURCE_REVISION_ID = (
    "correction:eldyrwild:session24-cube-karsemine-false-location-v1"
)

LOCKED_EVIDENCE_REF_ID = (
    "evidence:artifact:recap:longmont-c2:session-24:session-24:recap:paragraph:002"
)
LOCKED_SOURCE_ARTIFACT_URI_ID = "artifact:recap:longmont-c2:session-24"
LOCKED_ARTIFACT_CONTENT_SHA256 = (
    "603c1590da3aca71d90c8b69abed59368219d5dc1e3d1adf83db1bf854b5cc95"
)
LOCKED_SOURCE_SPAN_REF_ID = "session-24:recap:paragraph:002"
LOCKED_EXCERPT_SHA256 = (
    "5b3f91b9addeb2e140b72678de5660871cad2832a198c3990080f4213a17a609"
)

EligibilityState = Literal[
    "eligible", "already_applied", "ineligible", "integrity_failure"
]


class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class Session24CubeKarsemineFalseLocationCorrectionStatus(_Model):
    schema_: str = Field(
        default=(
            "dmb_eldyrwild_session24_cube_karsemine_false_location_correction_status_v1"
        ),
        alias="schema",
    )
    world_id: str
    campaign_id: str
    head_revision_id: str | None = None
    eligibility: EligibilityState
    reason: str | None = None
    target_edge_id: str = TARGET_EDGE_ID
    target_assertion_id: str = TARGET_ASSERTION_ID
    locked_target_contribution_ids: list[str] = Field(
        default_factory=lambda: sorted(LOCKED_TARGET_CONTRIBUTION_IDS)
    )
    correction_contribution_id: str = LOCKED_CORRECTION_CONTRIBUTION_ID
    correction_source_payload_sha256: str = LOCKED_CORRECTION_SOURCE_PAYLOAD_SHA256
    correction_raw_artifact_sha256: str = LOCKED_CORRECTION_RAW_ARTIFACT_SHA256
    continuity_state: str | None = None
    source_grounding_verified: bool | None = None
    durable_shape_verified: bool | None = None
    diagnostics: list[str] = Field(default_factory=list)


class Session24CubeKarsemineFalseLocationCorrectionResult(_Model):
    schema_: str = Field(
        default=(
            "dmb_eldyrwild_session24_cube_karsemine_false_location_correction_result_v1"
        ),
        alias="schema",
    )
    world_id: str
    expected_parent_revision_id: str
    parent_revision_id: str | None = None
    revision_id: str | None = None
    published: bool
    eligibility: EligibilityState | None = None
    correction_contribution_id: str = LOCKED_CORRECTION_CONTRIBUTION_ID
    failure_code: str | None = None
    failure_message: str | None = None
    diagnostics: list[str] = Field(default_factory=list)
    kernel_result: dict[str, Any] | None = None


class Session24CubeKarsemineFalseLocationCorrectionError(Exception):
    def __init__(self, message: str, *, code: str, status_code: int = 400) -> None:
        super().__init__(message)
        self.code = code
        self.status_code = status_code


def _correction_path(repo: Path | None = None) -> Path:
    return (repo or repo_root()).resolve() / APPROVED_CORRECTION_RELPATH


def _source_seal_path(repo: Path | None = None) -> Path:
    return (repo or repo_root()).resolve() / SOURCE_SEAL_RELPATH


def _resolve_root(root: Path | None) -> Path:
    return (root or world_graph_root()).resolve()


def _is_canonical_live_root(resolved: Path) -> bool:
    return resolved == live_world_graph_root().resolve()


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _status(
    *,
    eligibility: EligibilityState,
    reason: str | None,
    diagnostics: list[str],
    head_revision_id: str | None = None,
    continuity_state: str | None = None,
    source_grounding_verified: bool | None = None,
    durable_shape_verified: bool | None = None,
) -> Session24CubeKarsemineFalseLocationCorrectionStatus:
    return Session24CubeKarsemineFalseLocationCorrectionStatus(
        world_id=WORLD_ID,
        campaign_id=CAMPAIGN_ID,
        head_revision_id=head_revision_id,
        eligibility=eligibility,
        reason=reason,
        continuity_state=continuity_state,
        source_grounding_verified=source_grounding_verified,
        durable_shape_verified=durable_shape_verified,
        diagnostics=diagnostics,
    )


def load_approved_session24_cube_karsemine_false_location_correction(
    *,
    repo: Path | None = None,
) -> GraphContribution:
    """Load and seal-check the locked approved contradiction contribution."""
    path = _correction_path(repo)
    if not path.is_file():
        raise Session24CubeKarsemineFalseLocationCorrectionError(
            f"approved correction artifact missing: {path}",
            code="correction_artifact_missing",
            status_code=500,
        )
    raw = path.read_bytes()
    raw_sha = _sha256_bytes(raw)
    try:
        payload = json.loads(raw.decode("utf-8"))
        contribution = GraphContribution.model_validate(payload)
    except Exception as exc:  # noqa: BLE001 - surface as integrity failure
        raise Session24CubeKarsemineFalseLocationCorrectionError(
            f"approved correction artifact failed to validate: {exc}",
            code="correction_artifact_invalid",
            status_code=500,
        ) from exc

    digest = kernel.compute_contribution_source_payload_sha256(contribution)
    errors: list[str] = []
    if raw_sha != LOCKED_CORRECTION_RAW_ARTIFACT_SHA256:
        errors.append("raw artifact sha256 mismatch vs locked authority")
    if contribution.contribution_id != LOCKED_CORRECTION_CONTRIBUTION_ID:
        errors.append("contribution_id mismatch vs locked authority")
    if digest != LOCKED_CORRECTION_SOURCE_PAYLOAD_SHA256:
        errors.append("source-payload digest mismatch vs locked authority")
    if contribution.world_id != WORLD_ID:
        errors.append("world_id mismatch")
    if contribution.source_kind != "graph_review_authored_assertion":
        errors.append("source_kind mismatch")
    if contribution.authored_by != "gm":
        errors.append("authored_by mismatch")
    if contribution.source_artifact_id != LOCKED_SOURCE_ARTIFACT_ID:
        errors.append("source_artifact_id mismatch")
    if contribution.source_revision_id != LOCKED_SOURCE_REVISION_ID:
        errors.append("source_revision_id mismatch")
    if contribution.campaign_scope != CAMPAIGN_ID:
        errors.append("campaign_scope mismatch")
    if contribution.accepted_assertions:
        errors.append("contradiction must not carry accepted assertions")
    if contribution.candidate_assertions or contribution.rejected_assertions:
        errors.append("correction must not carry candidate/rejected assertions")
    if contribution.unresolved_mentions or contribution.identity_decision_ids:
        errors.append("correction must not carry unresolved/identity extras")
    if contribution.supersedes_contribution_id is not None:
        errors.append("correction must not supersede a contribution")
    if not contribution.assertion_corrections:
        errors.append("assertion_corrections must be non-empty")
    else:
        declared: list[str] = []
        for link in contribution.assertion_corrections:
            if link.correction_kind != "contradicts":
                errors.append("every correction_kind must be contradicts")
            if link.replacement_assertion_id is not None:
                errors.append("replacement_assertion_id must be null")
            if link.target_assertion_id != TARGET_ASSERTION_ID:
                errors.append("target_assertion_id mismatch")
            declared.append(link.target_contribution_id)
        if len(declared) != len(set(declared)):
            errors.append("duplicate target_contribution_id links")
        if set(declared) != LOCKED_TARGET_CONTRIBUTION_IDS:
            errors.append("declared target contribution IDs mismatch locked A(X)")
    if errors:
        raise Session24CubeKarsemineFalseLocationCorrectionError(
            "approved correction artifact integrity failure: " + "; ".join(errors),
            code="integrity_failure",
            status_code=400,
        )
    return contribution


def _verify_source_seals(*, repo: Path | None = None) -> tuple[bool, list[str]]:
    path = _source_seal_path(repo)
    if not path.is_file():
        return False, ["source_seal_fixture_missing"]
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return False, ["source_seal_fixture_unreadable"]
    rows = payload.get("seals") or payload.get("rows") or payload
    if isinstance(payload, dict) and "edges" in payload:
        rows = payload["edges"]
    if not isinstance(rows, list):
        # Fixture shape: top-level list or {seals: [...]}
        if isinstance(payload, dict):
            for key in ("source_seals", "residual_source_seals", "items"):
                if isinstance(payload.get(key), list):
                    rows = payload[key]
                    break
        if not isinstance(rows, list):
            return False, ["source_seal_fixture_shape"]
    row = next(
        (
            r
            for r in rows
            if isinstance(r, dict) and r.get("edge_id") == TARGET_EDGE_ID
        ),
        None,
    )
    if row is None:
        return False, ["source_seal_row_missing"]
    diagnostics: list[str] = []
    checks = [
        ("primary_evidence_ref_id", LOCKED_EVIDENCE_REF_ID),
        ("source_artifact_id", LOCKED_SOURCE_ARTIFACT_URI_ID),
        ("artifact_content_sha256", LOCKED_ARTIFACT_CONTENT_SHA256),
        ("source_span_ref_id", LOCKED_SOURCE_SPAN_REF_ID),
        ("excerpt_sha256", LOCKED_EXCERPT_SHA256),
    ]
    for key, expected in checks:
        if row.get(key) != expected:
            diagnostics.append(f"source_seal_mismatch:{key}")
    return (not diagnostics), diagnostics or ["source_seals_verified"]


def _support_shape_suggests_applied(store: Any) -> bool:
    support = store.assertion_support.get(TARGET_ASSERTION_ID)
    if not isinstance(support, dict):
        return False
    if support.get("support_state") != "contradicted":
        return False
    if list(support.get("active_contribution_ids") or []):
        return False
    contradicted = set(support.get("contradicted_contribution_ids") or [])
    if not LOCKED_TARGET_CONTRIBUTION_IDS.issubset(contradicted):
        return False
    edge = store.edges.get(TARGET_EDGE_ID)
    if edge is None:
        return False
    return (
        edge.source_node_id == TARGET_SOURCE_NODE_ID
        and edge.target_node_id == TARGET_TARGET_NODE_ID
        and edge.predicate == TARGET_PREDICATE
    )


def _manifest_entry(store: Any, contribution_id: str) -> Any | None:
    for entry in store.contribution_replay_manifest or []:
        cid = getattr(entry, "contribution_id", None)
        if cid is None and isinstance(entry, dict):
            cid = entry.get("contribution_id")
        if cid == contribution_id:
            return entry
    return None


def _revision_bound_correction_authority(
    *,
    root: Path,
    store: Any,
) -> tuple[bool, list[str]]:
    """Exact revision-bound + mutable-ledger proof that C is active authority."""
    diagnostics: list[str] = []
    digests = store.contribution_source_payload_sha256 or {}
    bound = digests.get(LOCKED_CORRECTION_CONTRIBUTION_ID)
    if bound != LOCKED_CORRECTION_SOURCE_PAYLOAD_SHA256:
        diagnostics.append("revision_digest_mismatch_or_missing")
        return False, diagnostics

    entry = _manifest_entry(store, LOCKED_CORRECTION_CONTRIBUTION_ID)
    if entry is None:
        diagnostics.append("replay_manifest_missing_C")
        return False, diagnostics
    status = getattr(entry, "status", None)
    if status is None and isinstance(entry, dict):
        status = entry.get("status")
    digest = getattr(entry, "source_payload_sha256", None)
    if digest is None and isinstance(entry, dict):
        digest = entry.get("source_payload_sha256")
    if status != "active":
        diagnostics.append("replay_manifest_C_not_active")
        return False, diagnostics
    if digest != LOCKED_CORRECTION_SOURCE_PAYLOAD_SHA256:
        diagnostics.append("replay_manifest_C_digest_mismatch")
        return False, diagnostics

    try:
        ledger = load_contribution_record(
            root, WORLD_ID, LOCKED_CORRECTION_CONTRIBUTION_ID
        )
    except FileNotFoundError:
        diagnostics.append("mutable_C_ledger_missing")
        return False, diagnostics
    if ledger.contribution_id != LOCKED_CORRECTION_CONTRIBUTION_ID:
        diagnostics.append("mutable_C_id_mismatch")
        return False, diagnostics
    ledger_digest = kernel.compute_contribution_source_payload_sha256(ledger)
    if ledger_digest != LOCKED_CORRECTION_SOURCE_PAYLOAD_SHA256:
        diagnostics.append("mutable_C_digest_mismatch")
        return False, diagnostics
    if ledger.status != "active":
        diagnostics.append("mutable_C_not_active")
        return False, diagnostics

    if not _support_shape_suggests_applied(store):
        diagnostics.append("support_shape_incomplete")
        return False, diagnostics

    return True, ["revision_bound_C_authority"]


def _classify_applied_state(
    *,
    root: Path,
    store: Any,
    head_revision_id: str,
) -> Session24CubeKarsemineFalseLocationCorrectionStatus | None:
    authority_ok, auth_diag = _revision_bound_correction_authority(
        root=root, store=store
    )
    if authority_ok:
        return _status(
            eligibility="already_applied",
            reason="exact approved correction already revision-bound on head",
            diagnostics=["already_applied", *auth_diag],
            head_revision_id=head_revision_id,
        )

    shape = _support_shape_suggests_applied(store)
    digests = store.contribution_source_payload_sha256 or {}
    bound = digests.get(LOCKED_CORRECTION_CONTRIBUTION_ID)
    if shape or bound is not None:
        return _status(
            eligibility="integrity_failure",
            reason=(
                "correction-shaped support or C digest present without exact "
                "revision-bound C authority"
            ),
            diagnostics=["integrity_failure", *auth_diag],
            head_revision_id=head_revision_id,
        )
    return None


def _preflight(
    *,
    root: Path,
    contribution: GraphContribution,
    expected_parent_revision_id: str | None,
    repo: Path | None = None,
) -> Session24CubeKarsemineFalseLocationCorrectionStatus:
    try:
        head, _revision, store = kernel.open_current_world_graph(root, WORLD_ID)
    except WorldGraphNotFoundError as exc:
        return _status(
            eligibility="ineligible",
            reason=f"world missing: {exc}",
            diagnostics=["world_missing"],
        )

    head_revision_id = head.head_revision_id
    if not head_revision_id:
        return _status(
            eligibility="ineligible",
            reason="Eldyrwild head revision is blank",
            diagnostics=["blank_head"],
        )

    # Exact-head fence before already_applied so stale expected parents cannot
    # masquerade as successful retries.
    if expected_parent_revision_id and expected_parent_revision_id != head_revision_id:
        return _status(
            eligibility="ineligible",
            reason=(
                f"expected parent {expected_parent_revision_id!r} is stale; "
                f"current head is {head_revision_id!r}"
            ),
            diagnostics=["stale_expected_parent"],
            head_revision_id=head_revision_id,
        )

    applied = _classify_applied_state(
        root=root, store=store, head_revision_id=head_revision_id
    )
    if applied is not None:
        return applied

    parent_for_proof = expected_parent_revision_id or head_revision_id

    seals_ok, seal_diag = _verify_source_seals(repo=repo)
    if not seals_ok:
        return _status(
            eligibility="integrity_failure",
            reason="source seal authority mismatch for target edge",
            diagnostics=["integrity_failure", *seal_diag],
            head_revision_id=head_revision_id,
        )

    ok, diagnostic, detail = prove_revision_is_anchor_or_descendant_v1(
        root=root,
        world_id=WORLD_ID,
        requested_revision_id=parent_for_proof,
        anchor_revision_id=ANCHOR_REVISION_ID,
        anchor_world_id=WORLD_ID,
    )
    if not ok:
        return _status(
            eligibility="ineligible",
            reason=detail or "parent is not adjudication anchor or descendant",
            diagnostics=[
                "ancestry_unproven",
                *([str(diagnostic)] if diagnostic else []),
            ],
            head_revision_id=head_revision_id,
        )

    r_ok, r_diag, r_detail = prove_revision_is_anchor_or_descendant_v1(
        root=root,
        world_id=WORLD_ID,
        requested_revision_id=parent_for_proof,
        anchor_revision_id=R_CURRENT_REVISION_ID,
        anchor_world_id=WORLD_ID,
    )
    if not r_ok:
        return _status(
            eligibility="ineligible",
            reason=r_detail
            or "parent is not R_current or a proven descendant of R_current",
            diagnostics=[
                "r_current_ancestry_unproven",
                *([str(r_diag)] if r_diag else []),
            ],
            head_revision_id=head_revision_id,
        )

    continuity = analyze_relationship_adjudication_continuity_v1(
        root=root,
        world_id=WORLD_ID,
        revision_id=parent_for_proof,
    )
    row = next(
        (r for r in continuity.rows if r.edge_id == TARGET_EDGE_ID),
        None,
    )
    if row is None:
        return _status(
            eligibility="ineligible",
            reason="target edge missing from continuity report",
            diagnostics=["continuity_row_missing"],
            head_revision_id=head_revision_id,
        )
    if row.continuity_state not in {"ANCHOR", "CARRIED_FORWARD"}:
        return _status(
            eligibility="ineligible",
            reason=(
                f"target continuity_state is {row.continuity_state!r}, "
                "expected ANCHOR or CARRIED_FORWARD"
            ),
            diagnostics=["continuity_inactive", row.continuity_state],
            head_revision_id=head_revision_id,
            continuity_state=row.continuity_state,
            source_grounding_verified=row.source_grounding_verified,
            durable_shape_verified=row.durable_shape_verified,
        )
    if not row.source_grounding_verified or not row.durable_shape_verified:
        return _status(
            eligibility="ineligible",
            reason="target source grounding or durable shape not verified",
            diagnostics=["continuity_unverified"],
            head_revision_id=head_revision_id,
            continuity_state=row.continuity_state,
            source_grounding_verified=row.source_grounding_verified,
            durable_shape_verified=row.durable_shape_verified,
        )

    support = store.assertion_support.get(TARGET_ASSERTION_ID)
    if not isinstance(support, dict) or support.get("support_state") != "supported":
        return _status(
            eligibility="ineligible",
            reason="target assertion support is not currently supported",
            diagnostics=["target_support_not_supported"],
            head_revision_id=head_revision_id,
            continuity_state=row.continuity_state,
            source_grounding_verified=True,
            durable_shape_verified=True,
        )
    if support.get("assertion_kind") != "edge":
        return _status(
            eligibility="ineligible",
            reason="target assertion_kind is not edge",
            diagnostics=["target_not_edge_assertion"],
            head_revision_id=head_revision_id,
            continuity_state=row.continuity_state,
            source_grounding_verified=True,
            durable_shape_verified=True,
        )
    if support.get("graph_object_id") != TARGET_EDGE_ID:
        return _status(
            eligibility="ineligible",
            reason="target assertion graph_object_id drifted from X",
            diagnostics=["target_graph_object_drift"],
            head_revision_id=head_revision_id,
            continuity_state=row.continuity_state,
            source_grounding_verified=True,
            durable_shape_verified=True,
        )

    active_ids = set(support.get("active_contribution_ids") or [])
    if not active_ids:
        return _status(
            eligibility="ineligible",
            reason="target assertion has no active supporting contributions",
            diagnostics=["target_support_empty"],
            head_revision_id=head_revision_id,
            continuity_state=row.continuity_state,
            source_grounding_verified=True,
            durable_shape_verified=True,
        )
    if not active_ids.issubset(HISTORICAL_ADJUDICATED_SUPPORT_IDS):
        return _status(
            eligibility="ineligible",
            reason=(
                "active support includes contribution IDs outside the historically "
                "adjudicated set; requires re-adjudication"
            ),
            diagnostics=["active_support_outside_historical"],
            head_revision_id=head_revision_id,
            continuity_state=row.continuity_state,
            source_grounding_verified=True,
            durable_shape_verified=True,
        )
    if active_ids != LOCKED_TARGET_CONTRIBUTION_IDS:
        return _status(
            eligibility="ineligible",
            reason=(
                "active support set does not exactly match locked A(X) sealed into C; "
                f"got {sorted(active_ids)!r}"
            ),
            diagnostics=["active_support_mismatch_locked_c"],
            head_revision_id=head_revision_id,
            continuity_state=row.continuity_state,
            source_grounding_verified=True,
            durable_shape_verified=True,
        )

    for cid in sorted(LOCKED_TARGET_CONTRIBUTION_IDS):
        try:
            target_contribution = load_contribution_record(root, WORLD_ID, cid)
        except FileNotFoundError:
            return _status(
                eligibility="ineligible",
                reason=f"target contribution missing: {cid}",
                diagnostics=["target_contribution_missing", cid],
                head_revision_id=head_revision_id,
                continuity_state=row.continuity_state,
                source_grounding_verified=True,
                durable_shape_verified=True,
            )
        if target_contribution.status != "active":
            return _status(
                eligibility="ineligible",
                reason=(
                    f"target contribution {cid} status is "
                    f"{target_contribution.status!r}, expected active"
                ),
                diagnostics=["target_contribution_inactive", cid],
                head_revision_id=head_revision_id,
                continuity_state=row.continuity_state,
                source_grounding_verified=True,
                durable_shape_verified=True,
            )
        target_assertion = next(
            (
                a
                for a in target_contribution.accepted_assertions
                if a.assertion_id == TARGET_ASSERTION_ID
            ),
            None,
        )
        if target_assertion is None or target_assertion.assertion_kind != "edge":
            return _status(
                eligibility="ineligible",
                reason=(
                    f"target contribution {cid} missing accepted edge assertion "
                    f"{TARGET_ASSERTION_ID}"
                ),
                diagnostics=["target_assertion_missing", cid],
                head_revision_id=head_revision_id,
                continuity_state=row.continuity_state,
                source_grounding_verified=True,
                durable_shape_verified=True,
            )

    live_edge = store.edges.get(TARGET_EDGE_ID)
    if live_edge is None:
        return _status(
            eligibility="ineligible",
            reason=f"live defective edge missing: {TARGET_EDGE_ID}",
            diagnostics=["live_edge_missing"],
            head_revision_id=head_revision_id,
            continuity_state=row.continuity_state,
            source_grounding_verified=True,
            durable_shape_verified=True,
        )
    if (
        live_edge.source_node_id != TARGET_SOURCE_NODE_ID
        or live_edge.target_node_id != TARGET_TARGET_NODE_ID
        or live_edge.predicate != TARGET_PREDICATE
    ):
        return _status(
            eligibility="ineligible",
            reason=(
                "live defective edge shape drifted: "
                f"{live_edge.source_node_id} --{live_edge.predicate}--> "
                f"{live_edge.target_node_id}"
            ),
            diagnostics=["live_edge_shape_drift"],
            head_revision_id=head_revision_id,
            continuity_state=row.continuity_state,
            source_grounding_verified=True,
            durable_shape_verified=True,
        )

    eff = analyze_relationship_effective_conformance_v1(
        root=root,
        world_id=WORLD_ID,
        revision_id=parent_for_proof,
    )
    if TARGET_EDGE_ID not in eff.remaining_residual_edge_ids:
        return _status(
            eligibility="ineligible",
            reason="target edge is not in the parent's effective residual set",
            diagnostics=["target_not_effective_residual"],
            head_revision_id=head_revision_id,
            continuity_state=row.continuity_state,
            source_grounding_verified=True,
            durable_shape_verified=True,
        )

    _ = contribution  # seal-checked; Kernel revalidates on apply
    return _status(
        eligibility="eligible",
        reason=(
            "parent is eligible for the locked Session-24 cube→Karsemine "
            "false-location contradiction"
        ),
        diagnostics=["eligible", *seal_diag],
        head_revision_id=head_revision_id,
        continuity_state=row.continuity_state,
        source_grounding_verified=True,
        durable_shape_verified=True,
    )


def get_session24_cube_karsemine_false_location_correction_status(
    *,
    root: Path | None = None,
    expected_parent_revision_id: str | None = None,
    repo: Path | None = None,
) -> Session24CubeKarsemineFalseLocationCorrectionStatus:
    """Read-only eligibility/status against the locked correction artifact."""
    try:
        contribution = load_approved_session24_cube_karsemine_false_location_correction(
            repo=repo
        )
    except Session24CubeKarsemineFalseLocationCorrectionError as exc:
        if exc.code in {
            "integrity_failure",
            "correction_artifact_invalid",
            "correction_artifact_missing",
            "correction_artifact_tampered",
        }:
            return _status(
                eligibility="integrity_failure",
                reason=str(exc),
                diagnostics=["integrity_failure", exc.code],
            )
        raise
    return _preflight(
        root=_resolve_root(root),
        contribution=contribution,
        expected_parent_revision_id=expected_parent_revision_id,
        repo=repo,
    )


def apply_session24_cube_karsemine_false_location_correction(
    *,
    expected_parent_revision_id: str,
    root: Path | None = None,
    repo: Path | None = None,
    allow_live_world: bool = False,
) -> Session24CubeKarsemineFalseLocationCorrectionResult:
    """Apply the locked contradiction to an exact eligible Eldyrwild parent."""
    if not expected_parent_revision_id or not expected_parent_revision_id.strip():
        raise Session24CubeKarsemineFalseLocationCorrectionError(
            "expected_parent_revision_id is required",
            code="expected_parent_required",
        )
    expected = expected_parent_revision_id.strip()
    world_root = _resolve_root(root)
    if _is_canonical_live_root(world_root) and not allow_live_world:
        raise Session24CubeKarsemineFalseLocationCorrectionError(
            "canonical live world root requires allow_live_world=True",
            code="live_world_opt_in_required",
        )

    contribution = load_approved_session24_cube_karsemine_false_location_correction(
        repo=repo
    )

    try:
        head_probe, _, _ = kernel.open_current_world_graph(world_root, WORLD_ID)
    except WorldGraphNotFoundError as exc:
        raise Session24CubeKarsemineFalseLocationCorrectionError(
            f"world missing: {exc}",
            code="ineligible_parent",
        ) from exc
    if head_probe.head_revision_id != expected:
        raise Session24CubeKarsemineFalseLocationCorrectionError(
            (
                f"expected parent {expected!r} is stale; "
                f"current head is {head_probe.head_revision_id!r}"
            ),
            code="stale_expected_parent",
        )

    status = _preflight(
        root=world_root,
        contribution=contribution,
        expected_parent_revision_id=expected,
        repo=repo,
    )
    if status.eligibility == "already_applied":
        return Session24CubeKarsemineFalseLocationCorrectionResult(
            world_id=WORLD_ID,
            expected_parent_revision_id=expected,
            parent_revision_id=expected,
            revision_id=status.head_revision_id,
            published=False,
            eligibility="already_applied",
            diagnostics=[*status.diagnostics, "already_applied_noop"],
        )
    if status.eligibility == "integrity_failure":
        raise Session24CubeKarsemineFalseLocationCorrectionError(
            status.reason or "integrity failure",
            code="integrity_failure",
        )
    if status.eligibility != "eligible":
        raise Session24CubeKarsemineFalseLocationCorrectionError(
            status.reason
            or "parent is ineligible for Session-24 cube→Karsemine correction",
            code="ineligible_parent",
        )

    head_now, _, _ = kernel.open_current_world_graph(world_root, WORLD_ID)
    if head_now.head_revision_id != expected:
        raise Session24CubeKarsemineFalseLocationCorrectionError(
            (
                f"expected parent {expected!r} is stale; "
                f"current head is {head_now.head_revision_id!r}"
            ),
            code="stale_expected_parent",
        )

    try:
        merge = kernel.contradict_edge_assertion_support(
            world_root,
            world_id=WORLD_ID,
            contribution=contribution,
            expected_parent_revision_id=expected,
        )
    except ValueError as exc:
        raise Session24CubeKarsemineFalseLocationCorrectionError(
            str(exc),
            code="kernel_rejected",
        ) from exc

    return Session24CubeKarsemineFalseLocationCorrectionResult(
        world_id=WORLD_ID,
        expected_parent_revision_id=expected,
        parent_revision_id=merge.parent_revision_id,
        revision_id=merge.revision_id or status.head_revision_id,
        published=bool(merge.published),
        eligibility=status.eligibility,
        failure_code=merge.failure_code,
        failure_message=merge.failure_message,
        diagnostics=[*status.diagnostics, *list(merge.diagnostics or [])],
        kernel_result=merge.model_dump(mode="json", by_alias=True),
    )
