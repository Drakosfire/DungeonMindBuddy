"""Composed Eldyrwild adjudication authority (historical A + S25 descendant).

Keeps the public A continuity analyzer semantically untouched and constructs an
additive multi-authority view that callers can use without silently widening
``anchor_finding_count`` from 59 to 66 under the old single-anchor schema.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from apps.live_control_server.integrations.dungeonmind_kernel.relationship_adjudication_continuity_v1 import (
    RelationshipAdjudicationContinuityReportV1,
    RelationshipAdjudicationContinuityRowV1,
    _analyze_relationship_adjudication_continuity_with_authorities,
    analyze_relationship_adjudication_continuity_v1,
)
from apps.live_control_server.integrations.dungeonmind_kernel.relationship_descendant_residual_adjudication_v1 import (
    ELDYRWILD_DESCENDANT_RESIDUAL_FINDINGS,
    EXACT_U7_EDGE_IDS,
    S25_PAYLOAD_SHA256,
    S25_REVISION_ID,
    load_descendant_residual_source_seals,
)
from apps.live_control_server.integrations.dungeonmind_kernel.relationship_residual_adjudication import (
    ELDYRWILD_CAMPAIGN_ID,
    ELDYRWILD_PAYLOAD_SHA256,
    ELDYRWILD_RESIDUAL_FINDINGS,
    ELDYRWILD_REVISION_ID,
    ELDYRWILD_WORLD_ID,
    AdjudicationFinding,
    load_residual_source_seals,
)

RELATIONSHIP_ADJUDICATION_AUTHORITY_SCHEMA_V1 = (
    "dmb_dungeonmind_relationship_adjudication_authority_v1"
)

HISTORICAL_A_AUTHORITY_ID = "eldyrwild-historical-a"
SESSION25_DESCENDANT_AUTHORITY_ID = "eldyrwild-session25-descendant"

_ACTIVE_CONTINUITY = frozenset({"ANCHOR", "CARRIED_FORWARD"})


class RelationshipAdjudicationAuthorityError(RuntimeError):
    """Raised when multi-authority composition fails closed."""


@dataclass(frozen=True)
class RelationshipAdjudicationAuthorityRowV1:
    edge_id: str
    authority_id: str
    anchor_revision_id: str
    anchor_graph_payload_sha256: str
    requested_revision_id: str
    continuity_state: str
    source_grounding_verified: bool
    durable_shape_verified: bool
    disposition: str
    responsible_repo: str
    next_action: str
    reason_code: str | None = None
    diagnostic: str | None = None
    diagnostic_detail: str | None = None


@dataclass(frozen=True)
class RelationshipAdjudicationAuthorityReportV1:
    schema_version: str
    world_id: str
    campaign_id: str
    requested_revision_id: str
    requested_graph_payload_sha256: str | None
    historical_a: RelationshipAdjudicationContinuityReportV1
    session25_descendant: RelationshipAdjudicationContinuityReportV1
    rows: list[RelationshipAdjudicationAuthorityRowV1]
    historical_a_row_count: int
    session25_descendant_row_count: int
    composed_row_count: int


def _row_from_continuity(
    *,
    authority_id: str,
    continuity: RelationshipAdjudicationContinuityReportV1,
    row: RelationshipAdjudicationContinuityRowV1,
) -> RelationshipAdjudicationAuthorityRowV1:
    return RelationshipAdjudicationAuthorityRowV1(
        edge_id=row.edge_id,
        authority_id=authority_id,
        anchor_revision_id=continuity.anchor_revision_id,
        anchor_graph_payload_sha256=continuity.anchor_graph_payload_sha256,
        requested_revision_id=continuity.requested_revision_id,
        continuity_state=row.continuity_state,
        source_grounding_verified=row.source_grounding_verified,
        durable_shape_verified=row.durable_shape_verified,
        disposition=row.original_disposition,
        responsible_repo=row.original_responsible_repo,
        next_action=row.original_next_action,
        diagnostic=row.diagnostic,
        diagnostic_detail=row.diagnostic_detail,
    )


def analyze_session25_descendant_continuity_v1(
    *,
    root: Path,
    world_id: str,
    revision_id: str,
    findings: Mapping[str, AdjudicationFinding] | None = None,
    seals_by_edge: Mapping[str, Mapping[str, Any]] | None = None,
    verify_excerpt: bool = True,
) -> RelationshipAdjudicationContinuityReportV1:
    """Continuity for the S25 descendant authority only (anchor = S25)."""
    findings_map = dict(findings or ELDYRWILD_DESCENDANT_RESIDUAL_FINDINGS)
    if set(findings_map) != set(EXACT_U7_EDGE_IDS):
        raise RelationshipAdjudicationAuthorityError(
            "S25 continuity findings must equal exact U₇"
        )
    seals = dict(seals_by_edge or load_descendant_residual_source_seals())
    if set(seals) != set(EXACT_U7_EDGE_IDS):
        raise RelationshipAdjudicationAuthorityError(
            "S25 continuity seals must equal exact U₇"
        )
    return _analyze_relationship_adjudication_continuity_with_authorities(
        root=root,
        world_id=world_id,
        revision_id=revision_id,
        findings=findings_map,
        seals_by_edge=seals,
        anchor_world_id=ELDYRWILD_WORLD_ID,
        anchor_revision_id=S25_REVISION_ID,
        anchor_payload_sha256=S25_PAYLOAD_SHA256,
        campaign_id=ELDYRWILD_CAMPAIGN_ID,
        verify_excerpt=verify_excerpt,
    )


def analyze_composed_relationship_adjudication_authority_v1(
    *,
    root: Path,
    world_id: str,
    revision_id: str,
    historical_a: RelationshipAdjudicationContinuityReportV1 | None = None,
    session25_descendant: RelationshipAdjudicationContinuityReportV1 | None = None,
    verify_excerpt: bool = True,
) -> RelationshipAdjudicationAuthorityReportV1:
    """Compose immutable A continuity with S25 descendant continuity."""
    if world_id != ELDYRWILD_WORLD_ID:
        raise RelationshipAdjudicationAuthorityError(
            f"composed authority world mismatch: {world_id!r}"
        )

    a_report = historical_a or analyze_relationship_adjudication_continuity_v1(
        root=root,
        world_id=world_id,
        revision_id=revision_id,
    )
    if a_report.anchor_revision_id != ELDYRWILD_REVISION_ID:
        raise RelationshipAdjudicationAuthorityError(
            "historical A continuity anchor drifted: "
            f"{a_report.anchor_revision_id!r}"
        )
    if a_report.anchor_finding_count != 59:
        raise RelationshipAdjudicationAuthorityError(
            "historical A continuity must keep anchor_finding_count=59; got "
            f"{a_report.anchor_finding_count}"
        )
    if a_report.anchor_graph_payload_sha256 != ELDYRWILD_PAYLOAD_SHA256:
        raise RelationshipAdjudicationAuthorityError(
            "historical A continuity payload pin drifted"
        )

    s25_report = session25_descendant or analyze_session25_descendant_continuity_v1(
        root=root,
        world_id=world_id,
        revision_id=revision_id,
        verify_excerpt=verify_excerpt,
    )
    if s25_report.anchor_revision_id != S25_REVISION_ID:
        raise RelationshipAdjudicationAuthorityError(
            "S25 continuity must remain anchored at S25; got "
            f"{s25_report.anchor_revision_id!r}"
        )
    if s25_report.anchor_finding_count != 7:
        raise RelationshipAdjudicationAuthorityError(
            f"S25 continuity finding count {s25_report.anchor_finding_count} != 7"
        )
    if s25_report.anchor_graph_payload_sha256 != S25_PAYLOAD_SHA256:
        raise RelationshipAdjudicationAuthorityError(
            "S25 continuity payload pin drifted"
        )

    a_ids = {row.edge_id for row in a_report.rows}
    s25_ids = {row.edge_id for row in s25_report.rows}
    if a_ids & s25_ids:
        raise RelationshipAdjudicationAuthorityError(
            "A and S25 authorities must be disjoint; overlap="
            f"{sorted(a_ids & s25_ids)}"
        )
    if s25_ids != set(EXACT_U7_EDGE_IDS):
        raise RelationshipAdjudicationAuthorityError(
            "S25 authority rows must equal exact U₇"
        )

    rows = [
        _row_from_continuity(
            authority_id=HISTORICAL_A_AUTHORITY_ID,
            continuity=a_report,
            row=row,
        )
        for row in a_report.rows
    ]
    rows.extend(
        _row_from_continuity(
            authority_id=SESSION25_DESCENDANT_AUTHORITY_ID,
            continuity=s25_report,
            row=row,
        )
        for row in s25_report.rows
    )
    rows.sort(key=lambda row: (row.authority_id, row.edge_id))

    # Reject silent re-labeling of all composed rows under one foreign anchor.
    for row in rows:
        if row.authority_id == HISTORICAL_A_AUTHORITY_ID:
            if row.anchor_revision_id != ELDYRWILD_REVISION_ID:
                raise RelationshipAdjudicationAuthorityError(
                    "historical-A row lost A anchor identity"
                )
        elif row.authority_id == SESSION25_DESCENDANT_AUTHORITY_ID:
            if row.anchor_revision_id != S25_REVISION_ID:
                raise RelationshipAdjudicationAuthorityError(
                    "S25 row lost S25 anchor identity"
                )
        else:
            raise RelationshipAdjudicationAuthorityError(
                f"unknown authority_id: {row.authority_id!r}"
            )

    requested_payload = (
        a_report.requested_graph_payload_sha256
        or s25_report.requested_graph_payload_sha256
    )
    return RelationshipAdjudicationAuthorityReportV1(
        schema_version=RELATIONSHIP_ADJUDICATION_AUTHORITY_SCHEMA_V1,
        world_id=world_id,
        campaign_id=ELDYRWILD_CAMPAIGN_ID,
        requested_revision_id=revision_id,
        requested_graph_payload_sha256=requested_payload,
        historical_a=a_report,
        session25_descendant=s25_report,
        rows=rows,
        historical_a_row_count=len(a_report.rows),
        session25_descendant_row_count=len(s25_report.rows),
        composed_row_count=len(rows),
    )


def composed_active_findings_by_edge(
    composed: RelationshipAdjudicationAuthorityReportV1,
) -> dict[str, AdjudicationFinding]:
    """Active composed findings keyed by edge_id for effective ownership."""
    a_findings = ELDYRWILD_RESIDUAL_FINDINGS
    s25_findings = ELDYRWILD_DESCENDANT_RESIDUAL_FINDINGS
    out: dict[str, AdjudicationFinding] = {}
    for row in composed.rows:
        if row.continuity_state not in _ACTIVE_CONTINUITY:
            continue
        if row.authority_id == HISTORICAL_A_AUTHORITY_ID:
            finding = a_findings.get(row.edge_id)
        elif row.authority_id == SESSION25_DESCENDANT_AUTHORITY_ID:
            finding = s25_findings.get(row.edge_id)
        else:
            raise RelationshipAdjudicationAuthorityError(
                f"unknown authority_id while resolving findings: {row.authority_id}"
            )
        if finding is None:
            raise RelationshipAdjudicationAuthorityError(
                f"active composed row lacks finding: {row.edge_id}"
            )
        out[row.edge_id] = finding
    return out


def composed_rows_by_edge(
    composed: RelationshipAdjudicationAuthorityReportV1,
) -> dict[str, RelationshipAdjudicationAuthorityRowV1]:
    return {row.edge_id: row for row in composed.rows}


def reject_naive_union_into_historical_a_anchor(
    *,
    root: Path,
    world_id: str,
    revision_id: str,
) -> None:
    """Adversarial helper: unioning U₇ into A-anchored continuity must fail.

    U₇ edges do not exist at A, so expected-shape construction fails closed.
    """
    seals_a = load_residual_source_seals()
    seals_s25 = load_descendant_residual_source_seals()
    union_findings = {
        **ELDYRWILD_RESIDUAL_FINDINGS,
        **ELDYRWILD_DESCENDANT_RESIDUAL_FINDINGS,
    }
    union_seals = {**seals_a, **seals_s25}
    try:
        _analyze_relationship_adjudication_continuity_with_authorities(
            root=root,
            world_id=world_id,
            revision_id=revision_id,
            findings=union_findings,
            seals_by_edge=union_seals,
            anchor_world_id=ELDYRWILD_WORLD_ID,
            anchor_revision_id=ELDYRWILD_REVISION_ID,
            anchor_payload_sha256=ELDYRWILD_PAYLOAD_SHA256,
            campaign_id=ELDYRWILD_CAMPAIGN_ID,
            verify_excerpt=False,
        )
    except Exception as exc:  # noqa: BLE001 - fail-closed proof
        raise RelationshipAdjudicationAuthorityError(
            "naive A∪U₇ union under A anchor failed closed as required"
        ) from exc
    raise RelationshipAdjudicationAuthorityError(
        "naive A∪U₇ union under A anchor unexpectedly succeeded"
    )
