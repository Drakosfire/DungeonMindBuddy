"""Governed one-off apply for the Eldyrwild Lysandra threat-direction correction.

Loads exactly one checked-in GraphContribution, proves eligible-parent
preconditions against built-in adjudication/continuity authority, and delegates
publication to ``graph_memory.kernel.correct_edge_assertion_support``.

Callers cannot inject a different correction artifact, target IDs, or
replacement semantics.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

import graph_memory.kernel as kernel
from apps.live_control_server.config import repo_root, world_graph_root
from apps.live_control_server.integrations.dungeonmind_kernel.relationship_adjudication_continuity_v1 import (
    analyze_relationship_adjudication_continuity_v1,
    prove_revision_is_anchor_or_descendant_v1,
)
from apps.live_control_server.integrations.dungeonmind_kernel.relationship_residual_adjudication import (
    ELDYRWILD_REVISION_ID,
    ELDYRWILD_WORLD_ID,
)
from graph_memory.kernel.contribution_models import GraphContribution
from graph_memory.world_supergraph.contribution_store import load_contribution_record
from graph_memory.world_supergraph.errors import WorldGraphNotFoundError

APPROVED_CORRECTION_RELPATH = (
    "graph_data/approved_graph_corrections/eldyrwild/lysandra-threat-direction-v1.json"
)

WORLD_ID = ELDYRWILD_WORLD_ID
CAMPAIGN_ID = "longmont-c1"
ANCHOR_REVISION_ID = ELDYRWILD_REVISION_ID

TARGET_EDGE_ID = (
    "edge:npc_lysandra:threatens:node:cultists_of_longmont:is-threatened-by-cultists"
)
TARGET_SOURCE_NODE_ID = "npc_lysandra"
TARGET_TARGET_NODE_ID = "node:cultists_of_longmont"
TARGET_PREDICATE = "threatens"
TARGET_CONTRIBUTION_ID = "contribution:86ea8a3d97dd18cc"
TARGET_ASSERTION_ID = "assertion:1dc0fef6561c3282"

REPLACEMENT_EDGE_ID = "edge:node:cultists_of_longmont:threatens:npc_lysandra"
REPLACEMENT_SOURCE_NODE_ID = "node:cultists_of_longmont"
REPLACEMENT_TARGET_NODE_ID = "npc_lysandra"
REPLACEMENT_PREDICATE = "threatens"
REPLACEMENT_ASSERTION_ID = "assertion:3668ba31192a37ad"

LOCKED_CORRECTION_CONTRIBUTION_ID = "contribution:4c65f668dc95ef4f"
LOCKED_CORRECTION_SOURCE_PAYLOAD_SHA256 = (
    "754b5a6a1f91f1449b5d0ae44f92ede4ddc92851ae782c421f72eb3cbf817767"
)
LOCKED_SOURCE_ARTIFACT_ID = (
    "graph-native:eldyrwild-correction:lysandra-threat-direction-v1"
)
LOCKED_SOURCE_REVISION_ID = "correction:eldyrwild:lysandra-threat-direction-v1"

EligibilityState = Literal["eligible", "already_applied", "ineligible"]


class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class LysandraThreatDirectionCorrectionStatus(_Model):
    schema_: str = Field(
        default="dmb_eldyrwild_lysandra_threat_direction_correction_status_v1",
        alias="schema",
    )
    world_id: str
    campaign_id: str
    head_revision_id: str | None = None
    eligibility: EligibilityState
    reason: str | None = None
    target_edge_id: str = TARGET_EDGE_ID
    target_contribution_id: str = TARGET_CONTRIBUTION_ID
    target_assertion_id: str = TARGET_ASSERTION_ID
    replacement_edge_id: str = REPLACEMENT_EDGE_ID
    replacement_assertion_id: str = REPLACEMENT_ASSERTION_ID
    correction_contribution_id: str = LOCKED_CORRECTION_CONTRIBUTION_ID
    correction_source_payload_sha256: str = LOCKED_CORRECTION_SOURCE_PAYLOAD_SHA256
    continuity_state: str | None = None
    source_grounding_verified: bool | None = None
    durable_shape_verified: bool | None = None
    diagnostics: list[str] = Field(default_factory=list)


class LysandraThreatDirectionCorrectionResult(_Model):
    schema_: str = Field(
        default="dmb_eldyrwild_lysandra_threat_direction_correction_result_v1",
        alias="schema",
    )
    world_id: str
    expected_parent_revision_id: str
    parent_revision_id: str | None = None
    revision_id: str | None = None
    published: bool
    eligibility: EligibilityState | None = None
    correction_contribution_id: str = LOCKED_CORRECTION_CONTRIBUTION_ID
    replacement_assertion_id: str = REPLACEMENT_ASSERTION_ID
    failure_code: str | None = None
    failure_message: str | None = None
    diagnostics: list[str] = Field(default_factory=list)
    kernel_result: dict[str, Any] | None = None


class LysandraThreatDirectionCorrectionError(Exception):
    def __init__(self, message: str, *, code: str, status_code: int = 400) -> None:
        super().__init__(message)
        self.code = code
        self.status_code = status_code


def _correction_path(repo: Path | None = None) -> Path:
    return (repo or repo_root()).resolve() / APPROVED_CORRECTION_RELPATH


def _resolve_root(root: Path | None) -> Path:
    return (root or world_graph_root()).resolve()


def load_approved_lysandra_threat_direction_correction(
    *,
    repo: Path | None = None,
) -> GraphContribution:
    """Load and seal-check the locked approved correction contribution."""
    path = _correction_path(repo)
    if not path.is_file():
        raise LysandraThreatDirectionCorrectionError(
            f"approved correction artifact missing: {path}",
            code="correction_artifact_missing",
            status_code=500,
        )
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        contribution = GraphContribution.model_validate(payload)
    except Exception as exc:  # noqa: BLE001 - surface as integrity failure
        raise LysandraThreatDirectionCorrectionError(
            f"approved correction artifact failed to validate: {exc}",
            code="correction_artifact_invalid",
            status_code=500,
        ) from exc

    digest = kernel.compute_contribution_source_payload_sha256(contribution)
    errors: list[str] = []
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
    if len(contribution.assertion_corrections) != 1:
        errors.append("expected exactly one assertion_corrections entry")
    else:
        link = contribution.assertion_corrections[0]
        if link.target_contribution_id != TARGET_CONTRIBUTION_ID:
            errors.append("target_contribution_id mismatch")
        if link.target_assertion_id != TARGET_ASSERTION_ID:
            errors.append("target_assertion_id mismatch")
        if link.replacement_assertion_id != REPLACEMENT_ASSERTION_ID:
            errors.append("replacement_assertion_id mismatch")
    if len(contribution.accepted_assertions) != 1:
        errors.append("expected exactly one accepted assertion")
    else:
        replacement = contribution.accepted_assertions[0]
        if replacement.assertion_id != REPLACEMENT_ASSERTION_ID:
            errors.append("accepted replacement assertion_id mismatch")
        if replacement.assertion_kind != "edge":
            errors.append("replacement assertion_kind mismatch")
        if replacement.subject_node_id != REPLACEMENT_SOURCE_NODE_ID:
            errors.append("replacement subject_node_id mismatch")
        if replacement.target_node_id != REPLACEMENT_TARGET_NODE_ID:
            errors.append("replacement target_node_id mismatch")
        if replacement.predicate != REPLACEMENT_PREDICATE:
            errors.append("replacement predicate mismatch")
        value = replacement.value if isinstance(replacement.value, dict) else {}
        if value.get("edge_id") != REPLACEMENT_EDGE_ID:
            errors.append("replacement value.edge_id mismatch")
        if replacement.campaign_scope != CAMPAIGN_ID:
            errors.append("replacement campaign_scope mismatch")
        if replacement.visibility != "gm":
            errors.append("replacement visibility mismatch")
        if replacement.epistemic_kind != "source_derived_candidate":
            errors.append("replacement epistemic_kind mismatch")
        if replacement.temporal_scope != {"session_id": "session-8"}:
            errors.append("replacement temporal_scope mismatch")
    if contribution.candidate_assertions or contribution.rejected_assertions:
        errors.append("correction must not carry candidate/rejected assertions")
    if contribution.unresolved_mentions or contribution.identity_decision_ids:
        errors.append("correction must not carry unresolved/identity extras")
    if contribution.supersedes_contribution_id is not None:
        errors.append("correction must not supersede a contribution")
    if errors:
        raise LysandraThreatDirectionCorrectionError(
            "approved correction artifact integrity failure: " + "; ".join(errors),
            code="correction_artifact_tampered",
            status_code=400,
        )
    return contribution


def _already_applied(store: Any, contribution: GraphContribution) -> bool:
    support = store.assertion_support.get(TARGET_ASSERTION_ID)
    if not isinstance(support, dict):
        return False
    if support.get("support_state") != "contradicted":
        return False
    contradicted = set(support.get("contradicted_contribution_ids") or [])
    if TARGET_CONTRIBUTION_ID not in contradicted:
        return False
    replacement_support = store.assertion_support.get(REPLACEMENT_ASSERTION_ID)
    if not isinstance(replacement_support, dict):
        return False
    if replacement_support.get("support_state") != "supported":
        return False
    active = set(replacement_support.get("active_contribution_ids") or [])
    if contribution.contribution_id not in active:
        return False
    edge = store.edges.get(REPLACEMENT_EDGE_ID)
    if edge is None:
        return False
    return (
        edge.source_node_id == REPLACEMENT_SOURCE_NODE_ID
        and edge.target_node_id == REPLACEMENT_TARGET_NODE_ID
        and edge.predicate == REPLACEMENT_PREDICATE
    )


def _preflight(
    *,
    root: Path,
    contribution: GraphContribution,
    expected_parent_revision_id: str | None,
) -> LysandraThreatDirectionCorrectionStatus:
    diagnostics: list[str] = []
    try:
        head, _revision, store = kernel.open_current_world_graph(root, WORLD_ID)
    except WorldGraphNotFoundError as exc:
        return LysandraThreatDirectionCorrectionStatus(
            world_id=WORLD_ID,
            campaign_id=CAMPAIGN_ID,
            eligibility="ineligible",
            reason=f"world missing: {exc}",
            diagnostics=["world_missing"],
        )

    head_revision_id = head.head_revision_id
    if not head_revision_id:
        return LysandraThreatDirectionCorrectionStatus(
            world_id=WORLD_ID,
            campaign_id=CAMPAIGN_ID,
            eligibility="ineligible",
            reason="Eldyrwild head revision is blank",
            diagnostics=["blank_head"],
        )

    if _already_applied(store, contribution):
        return LysandraThreatDirectionCorrectionStatus(
            world_id=WORLD_ID,
            campaign_id=CAMPAIGN_ID,
            head_revision_id=head_revision_id,
            eligibility="already_applied",
            reason="exact approved correction already current on head",
            diagnostics=["already_applied"],
        )

    parent_for_proof = expected_parent_revision_id or head_revision_id
    if expected_parent_revision_id and expected_parent_revision_id != head_revision_id:
        return LysandraThreatDirectionCorrectionStatus(
            world_id=WORLD_ID,
            campaign_id=CAMPAIGN_ID,
            head_revision_id=head_revision_id,
            eligibility="ineligible",
            reason=(
                f"expected parent {expected_parent_revision_id!r} is stale; "
                f"current head is {head_revision_id!r}"
            ),
            diagnostics=["stale_expected_parent"],
        )

    ok, diagnostic, detail = prove_revision_is_anchor_or_descendant_v1(
        root=root,
        world_id=WORLD_ID,
        requested_revision_id=parent_for_proof,
        anchor_revision_id=ANCHOR_REVISION_ID,
        anchor_world_id=WORLD_ID,
    )
    if not ok:
        return LysandraThreatDirectionCorrectionStatus(
            world_id=WORLD_ID,
            campaign_id=CAMPAIGN_ID,
            head_revision_id=head_revision_id,
            eligibility="ineligible",
            reason=detail or "parent is not adjudication anchor or descendant",
            diagnostics=[
                "ancestry_unproven",
                *( [str(diagnostic)] if diagnostic else [] ),
            ],
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
        return LysandraThreatDirectionCorrectionStatus(
            world_id=WORLD_ID,
            campaign_id=CAMPAIGN_ID,
            head_revision_id=head_revision_id,
            eligibility="ineligible",
            reason="target edge missing from continuity report",
            diagnostics=["continuity_row_missing"],
        )
    if row.continuity_state not in {"ANCHOR", "CARRIED_FORWARD"}:
        return LysandraThreatDirectionCorrectionStatus(
            world_id=WORLD_ID,
            campaign_id=CAMPAIGN_ID,
            head_revision_id=head_revision_id,
            eligibility="ineligible",
            reason=(
                f"target continuity_state is {row.continuity_state!r}, "
                "expected ANCHOR or CARRIED_FORWARD"
            ),
            continuity_state=row.continuity_state,
            source_grounding_verified=row.source_grounding_verified,
            durable_shape_verified=row.durable_shape_verified,
            diagnostics=["continuity_inactive", row.continuity_state],
        )
    if not row.source_grounding_verified or not row.durable_shape_verified:
        return LysandraThreatDirectionCorrectionStatus(
            world_id=WORLD_ID,
            campaign_id=CAMPAIGN_ID,
            head_revision_id=head_revision_id,
            eligibility="ineligible",
            reason="target source grounding or durable shape not verified",
            continuity_state=row.continuity_state,
            source_grounding_verified=row.source_grounding_verified,
            durable_shape_verified=row.durable_shape_verified,
            diagnostics=["continuity_unverified"],
        )

    try:
        target_contribution = load_contribution_record(
            root, WORLD_ID, TARGET_CONTRIBUTION_ID
        )
    except FileNotFoundError:
        return LysandraThreatDirectionCorrectionStatus(
            world_id=WORLD_ID,
            campaign_id=CAMPAIGN_ID,
            head_revision_id=head_revision_id,
            eligibility="ineligible",
            reason=f"target contribution missing: {TARGET_CONTRIBUTION_ID}",
            continuity_state=row.continuity_state,
            source_grounding_verified=True,
            durable_shape_verified=True,
            diagnostics=["target_contribution_missing"],
        )
    if target_contribution.status != "active":
        return LysandraThreatDirectionCorrectionStatus(
            world_id=WORLD_ID,
            campaign_id=CAMPAIGN_ID,
            head_revision_id=head_revision_id,
            eligibility="ineligible",
            reason=(
                f"target contribution status is {target_contribution.status!r}, "
                "expected active"
            ),
            continuity_state=row.continuity_state,
            source_grounding_verified=True,
            durable_shape_verified=True,
            diagnostics=["target_contribution_inactive"],
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
        return LysandraThreatDirectionCorrectionStatus(
            world_id=WORLD_ID,
            campaign_id=CAMPAIGN_ID,
            head_revision_id=head_revision_id,
            eligibility="ineligible",
            reason="target assertion missing or not an accepted edge assertion",
            continuity_state=row.continuity_state,
            source_grounding_verified=True,
            durable_shape_verified=True,
            diagnostics=["target_assertion_missing"],
        )

    support = store.assertion_support.get(TARGET_ASSERTION_ID)
    if not isinstance(support, dict) or support.get("support_state") != "supported":
        return LysandraThreatDirectionCorrectionStatus(
            world_id=WORLD_ID,
            campaign_id=CAMPAIGN_ID,
            head_revision_id=head_revision_id,
            eligibility="ineligible",
            reason="target assertion support is not currently supported",
            continuity_state=row.continuity_state,
            source_grounding_verified=True,
            durable_shape_verified=True,
            diagnostics=["target_support_not_supported"],
        )
    active_ids = list(support.get("active_contribution_ids") or [])
    if active_ids != [TARGET_CONTRIBUTION_ID]:
        return LysandraThreatDirectionCorrectionStatus(
            world_id=WORLD_ID,
            campaign_id=CAMPAIGN_ID,
            head_revision_id=head_revision_id,
            eligibility="ineligible",
            reason=(
                "target assertion must have exactly one active supporting "
                f"contribution {TARGET_CONTRIBUTION_ID}; got {active_ids!r}"
            ),
            continuity_state=row.continuity_state,
            source_grounding_verified=True,
            durable_shape_verified=True,
            diagnostics=["target_support_not_sole"],
        )

    live_edge = store.edges.get(TARGET_EDGE_ID)
    if live_edge is None:
        return LysandraThreatDirectionCorrectionStatus(
            world_id=WORLD_ID,
            campaign_id=CAMPAIGN_ID,
            head_revision_id=head_revision_id,
            eligibility="ineligible",
            reason=f"live defective edge missing: {TARGET_EDGE_ID}",
            continuity_state=row.continuity_state,
            source_grounding_verified=True,
            durable_shape_verified=True,
            diagnostics=["live_edge_missing"],
        )
    if (
        live_edge.source_node_id != TARGET_SOURCE_NODE_ID
        or live_edge.target_node_id != TARGET_TARGET_NODE_ID
        or live_edge.predicate != TARGET_PREDICATE
    ):
        return LysandraThreatDirectionCorrectionStatus(
            world_id=WORLD_ID,
            campaign_id=CAMPAIGN_ID,
            head_revision_id=head_revision_id,
            eligibility="ineligible",
            reason=(
                "live defective edge shape drifted: "
                f"{live_edge.source_node_id} --{live_edge.predicate}--> "
                f"{live_edge.target_node_id}"
            ),
            continuity_state=row.continuity_state,
            source_grounding_verified=True,
            durable_shape_verified=True,
            diagnostics=["live_edge_shape_drift"],
        )

    existing_replacement = store.edges.get(REPLACEMENT_EDGE_ID)
    if existing_replacement is not None and (
        existing_replacement.source_node_id != REPLACEMENT_SOURCE_NODE_ID
        or existing_replacement.target_node_id != REPLACEMENT_TARGET_NODE_ID
        or existing_replacement.predicate != REPLACEMENT_PREDICATE
    ):
        return LysandraThreatDirectionCorrectionStatus(
            world_id=WORLD_ID,
            campaign_id=CAMPAIGN_ID,
            head_revision_id=head_revision_id,
            eligibility="ineligible",
            reason=(
                f"replacement edge id {REPLACEMENT_EDGE_ID} already exists with "
                "conflicting structural fingerprint"
            ),
            continuity_state=row.continuity_state,
            source_grounding_verified=True,
            durable_shape_verified=True,
            diagnostics=["replacement_edge_collision"],
        )

    if target_assertion.campaign_scope != contribution.accepted_assertions[0].campaign_scope:
        diagnostics.append("scope_campaign_mismatch")
    if target_assertion.visibility != contribution.accepted_assertions[0].visibility:
        diagnostics.append("scope_visibility_mismatch")
    if target_assertion.epistemic_kind != contribution.accepted_assertions[0].epistemic_kind:
        diagnostics.append("scope_epistemic_mismatch")
    if target_assertion.temporal_scope != contribution.accepted_assertions[0].temporal_scope:
        diagnostics.append("scope_temporal_mismatch")
    if any(d.startswith("scope_") for d in diagnostics):
        return LysandraThreatDirectionCorrectionStatus(
            world_id=WORLD_ID,
            campaign_id=CAMPAIGN_ID,
            head_revision_id=head_revision_id,
            eligibility="ineligible",
            reason="replacement scope fields do not match the exact target assertion",
            continuity_state=row.continuity_state,
            source_grounding_verified=True,
            durable_shape_verified=True,
            diagnostics=diagnostics,
        )

    return LysandraThreatDirectionCorrectionStatus(
        world_id=WORLD_ID,
        campaign_id=CAMPAIGN_ID,
        head_revision_id=head_revision_id,
        eligibility="eligible",
        reason="parent is eligible for the locked Lysandra threat-direction correction",
        continuity_state=row.continuity_state,
        source_grounding_verified=True,
        durable_shape_verified=True,
        diagnostics=["eligible", *diagnostics],
    )


def get_lysandra_threat_direction_correction_status(
    *,
    root: Path | None = None,
    expected_parent_revision_id: str | None = None,
    repo: Path | None = None,
) -> LysandraThreatDirectionCorrectionStatus:
    """Read-only eligibility/status against the locked correction artifact."""
    contribution = load_approved_lysandra_threat_direction_correction(repo=repo)
    return _preflight(
        root=_resolve_root(root),
        contribution=contribution,
        expected_parent_revision_id=expected_parent_revision_id,
    )


def apply_lysandra_threat_direction_correction(
    *,
    expected_parent_revision_id: str,
    root: Path | None = None,
    repo: Path | None = None,
) -> LysandraThreatDirectionCorrectionResult:
    """Apply the locked correction to an exact eligible Eldyrwild parent."""
    if not expected_parent_revision_id or not expected_parent_revision_id.strip():
        raise LysandraThreatDirectionCorrectionError(
            "expected_parent_revision_id is required",
            code="expected_parent_required",
        )
    expected = expected_parent_revision_id.strip()
    world_root = _resolve_root(root)
    contribution = load_approved_lysandra_threat_direction_correction(repo=repo)
    status = _preflight(
        root=world_root,
        contribution=contribution,
        expected_parent_revision_id=expected,
    )
    if status.eligibility not in {"eligible", "already_applied"}:
        raise LysandraThreatDirectionCorrectionError(
            status.reason or "parent is ineligible for Lysandra correction",
            code="ineligible_parent",
        )

    try:
        merge = kernel.correct_edge_assertion_support(
            world_root,
            world_id=WORLD_ID,
            contribution=contribution,
            expected_parent_revision_id=expected,
        )
    except ValueError as exc:
        raise LysandraThreatDirectionCorrectionError(
            str(exc),
            code="kernel_rejected",
        ) from exc

    return LysandraThreatDirectionCorrectionResult(
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
