"""Session-25 descendant residual adjudication authority (U₇).

Seals source-grounded judgments for the seven post-A residual edges that first
appear at S25. Historical A findings remain untouched; this module never appends
to ``ELDYRWILD_RESIDUAL_FINDINGS``.
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from apps.live_control_server.integrations.dungeonmind_kernel.relationship_residual_adjudication import (
    ELDYRWILD_CAMPAIGN_ID,
    ELDYRWILD_WORLD_ID,
    AdjudicationFinding,
    ReasonCode,
    _compound,
    _identity,
    _source,
    resolve_evidence_excerpt,
    verify_excerpt_against_seal,
)
from apps.live_control_server.integrations.dungeonmind_kernel.whole_world_conformance import (
    _load_exact_buddy_revision,
    snapshot_world_graph_tree_digest,
)

DESCENDANT_RESIDUAL_ADJUDICATION_SCHEMA_V1 = (
    "dmb_dungeonmind_relationship_descendant_residual_adjudication_v1"
)
DESCENDANT_RESIDUAL_SOURCE_SEALS_SCHEMA_V1 = (
    "dmb_dungeonmind_relationship_descendant_residual_source_seals_v1"
)

S25_REVISION_ID = "rev:df92031efcd379b9c52e0df2e3ff7217"
S25_PAYLOAD_SHA256 = (
    "5361c9734c84702a5ac6b012c1b5470c5991f3d31bb836721375fbab3727c71f"
)
S25_PARENT_REVISION_ID = "rev:3413bf6f5044cf2680233f5e37c90dcf"
S25_INTRODUCING_CONTRIBUTION_ID = "contribution:a4231edb9a228963"
S25_SOURCE_ARTIFACT_ID = "artifact:recap:longmont-c2:session-25:fd38b5915b32"
S25_SOURCE_ARTIFACT_CONTENT_SHA256 = (
    "fd38b5915b32beb77142c0334c578e7ff0d46ef6d91deb545801761508d26d0d"
)

EXPECTED_DESCENDANT_RESIDUAL_COUNT = 7

DEFAULT_DESCENDANT_SOURCE_SEALS_PATH = (
    Path(__file__).resolve().parents[4]
    / "tests"
    / "fixtures"
    / "dungeonmind_kernel"
    / "eldyrwild_relationship_descendant_residual_source_seals_v1.json"
)

U1 = (
    "edge:faction:town-guards-mireward-gate:reports_threat_in:"
    "mystery:session25:west-wall-screaming-and-dark-shapes-below"
)
U2 = "edge:item:crossbow_bolt_light_source:controls_comms_with:loc:north-road"
U3 = (
    "edge:node:hesta-bramblewood:governs:"
    "organization:merchant-s-crossroads-apothecary"
)
U4 = (
    "edge:node:orik:participates_in:"
    "organization:warehouse-gate-sheltering-group"
)
U5 = (
    "edge:node:thrin-branchborn:caused_by:"
    "mystery:session25:thrin-ambush-by-hybrid-creatures"
)
U6 = (
    "edge:organization:merchant-s-crossroads-apothecary:same_as:"
    "loc:crooked-retort"
)
U7 = "edge:pc:ephanna:hires:node:thrin-branchborn"

EXACT_U7_EDGE_IDS: tuple[str, ...] = (U1, U2, U3, U4, U5, U6, U7)


class RelationshipDescendantResidualAdjudicationError(RuntimeError):
    """Raised when S25 descendant adjudication authority fails closed."""


def _counter_rows(counter: Counter[str]) -> list[dict[str, Any]]:
    return [{"key": key, "count": count} for key, count in sorted(counter.items())]


ELDYRWILD_DESCENDANT_RESIDUAL_FINDINGS: dict[str, AdjudicationFinding] = {
    U1: _compound(
        rationale=(
            "Session-25 recap collapses observation/reporting, threat "
            "identification, and west-wall spatial context into "
            "`reports_threat_in`; follow A-era compound precedent for this "
            "predicate family."
        ),
    ),
    U2: _source(
        rationale=(
            "Stafl casts Light on a crossbow bolt and illuminates part of the "
            "north road; the durable `controls_comms_with` claim is a "
            "predicate misapplication."
        ),
        reason=ReasonCode.PREDICATE_MISAPPLIED,
    ),
    U3: _source(
        rationale=(
            "Hesta answers the apothecary door, holds potions, and agrees to "
            "brew more; the source does not establish organizational "
            "`governs` authority."
        ),
        reason=ReasonCode.PREDICATE_MISAPPLIED,
    ),
    U4: _source(
        rationale=(
            "Orik helps coordinate refugee sheltering and leaves to find help; "
            "the source does not establish membership/`participates_in` an "
            "organization identified as warehouse-gate-sheltering-group."
        ),
        reason=ReasonCode.PREDICATE_MISAPPLIED,
    ),
    U5: _source(
        rationale=(
            "Thrin is ambushed and dragged; durable "
            "`Thrin --caused_by--> ambush` contradicts source direction/"
            "meaning and requires authored correction rather than auto-reverse."
        ),
        reason=ReasonCode.DIRECTION_CONTRADICTION,
    ),
    U6: _identity(
        rationale=(
            "The recap identifies the Merchant's Crossroads apothecary as the "
            "Crooked Retort — two graph identities for one place/business, not "
            "a durable `same_as` semantic relationship."
        ),
    ),
    U7: _source(
        rationale=(
            "Ephanna entrusts Thrin to scout and remain hidden; the source "
            "supports assignment/request, not employment/`hires`."
        ),
        reason=ReasonCode.PREDICATE_MISAPPLIED,
    ),
}


@dataclass(frozen=True)
class DescendantResidualAdjudicationRecordV1:
    edge_id: str
    disposition: str
    reason_code: str
    responsible_repo: str
    next_action: str
    requires_source_mutation: bool
    rationale: str
    primary_evidence_ref_id: str
    source_artifact_id: str
    source_span_ref_id: str
    excerpt_sha256: str


@dataclass(frozen=True)
class DescendantResidualAdjudicationReportV1:
    schema_version: str
    world_id: str
    campaign_id: str
    anchor_revision_id: str
    anchor_graph_payload_sha256: str
    adjudicated_count: int
    by_disposition: list[dict[str, Any]]
    by_responsible_repo: list[dict[str, Any]]
    by_next_action: list[dict[str, Any]]
    records: list[DescendantResidualAdjudicationRecordV1]
    world_graph_digest_before: str | None = None
    world_graph_digest_after: str | None = None


def load_descendant_residual_source_seals(
    path: Path | None = None,
) -> dict[str, dict[str, Any]]:
    seals_path = path or DEFAULT_DESCENDANT_SOURCE_SEALS_PATH
    payload = json.loads(seals_path.read_text(encoding="utf-8"))
    if payload.get("schema") != DESCENDANT_RESIDUAL_SOURCE_SEALS_SCHEMA_V1:
        raise RelationshipDescendantResidualAdjudicationError(
            f"unexpected descendant source seals schema: {payload.get('schema')!r}"
        )
    if payload.get("world_id") != ELDYRWILD_WORLD_ID:
        raise RelationshipDescendantResidualAdjudicationError(
            f"descendant seals world_id mismatch: {payload.get('world_id')!r}"
        )
    if payload.get("campaign_id") != ELDYRWILD_CAMPAIGN_ID:
        raise RelationshipDescendantResidualAdjudicationError(
            f"descendant seals campaign_id mismatch: {payload.get('campaign_id')!r}"
        )
    if payload.get("anchor_revision_id") != S25_REVISION_ID:
        raise RelationshipDescendantResidualAdjudicationError(
            "descendant seals anchor_revision_id mismatch: "
            f"{payload.get('anchor_revision_id')!r}"
        )
    if payload.get("anchor_graph_payload_sha256") != S25_PAYLOAD_SHA256:
        raise RelationshipDescendantResidualAdjudicationError(
            "descendant seals anchor_graph_payload_sha256 mismatch: "
            f"{payload.get('anchor_graph_payload_sha256')!r}"
        )
    seals = payload.get("seals") or []
    sealed_count = payload.get("sealed_count")
    if sealed_count != EXPECTED_DESCENDANT_RESIDUAL_COUNT:
        raise RelationshipDescendantResidualAdjudicationError(
            f"descendant sealed_count {sealed_count} != "
            f"{EXPECTED_DESCENDANT_RESIDUAL_COUNT}"
        )
    if len(seals) != EXPECTED_DESCENDANT_RESIDUAL_COUNT:
        raise RelationshipDescendantResidualAdjudicationError(
            f"descendant seals length {len(seals)} != "
            f"{EXPECTED_DESCENDANT_RESIDUAL_COUNT}"
        )
    by_edge = {row["edge_id"]: row for row in seals}
    if len(by_edge) != len(seals):
        raise RelationshipDescendantResidualAdjudicationError(
            "duplicate edge_id in descendant source seals"
        )
    if set(by_edge) != set(EXACT_U7_EDGE_IDS):
        raise RelationshipDescendantResidualAdjudicationError(
            "descendant seals must cover exact U₇: "
            f"missing={sorted(set(EXACT_U7_EDGE_IDS) - set(by_edge))} "
            f"extra={sorted(set(by_edge) - set(EXACT_U7_EDGE_IDS))}"
        )
    return by_edge


def _assert_findings_exact(
    findings: Mapping[str, AdjudicationFinding],
) -> None:
    if len(findings) != EXPECTED_DESCENDANT_RESIDUAL_COUNT:
        raise RelationshipDescendantResidualAdjudicationError(
            f"descendant findings count {len(findings)} != "
            f"{EXPECTED_DESCENDANT_RESIDUAL_COUNT}"
        )
    if set(findings) != set(EXACT_U7_EDGE_IDS):
        raise RelationshipDescendantResidualAdjudicationError(
            "descendant findings must cover exact U₇: "
            f"missing={sorted(set(EXACT_U7_EDGE_IDS) - set(findings))} "
            f"extra={sorted(set(findings) - set(EXACT_U7_EDGE_IDS))}"
        )


def _support_for_edge(store: Any, edge_id: str) -> dict[str, Any]:
    for value in store.assertion_support.values():
        row = value.model_dump() if hasattr(value, "model_dump") else dict(value)
        if (
            row.get("graph_object_id") == edge_id
            and row.get("assertion_kind") == "edge"
        ):
            return row
    raise RelationshipDescendantResidualAdjudicationError(
        f"missing edge assertion support for {edge_id}"
    )


def analyze_eldyrwild_descendant_residual_adjudication_v1(
    *,
    root: Path,
    world_id: str = ELDYRWILD_WORLD_ID,
    revision_id: str = S25_REVISION_ID,
    findings: Mapping[str, AdjudicationFinding] | None = None,
    source_seals_path: Path | None = None,
    verify_excerpts: bool = True,
) -> DescendantResidualAdjudicationReportV1:
    """Analyze the sealed S25 descendant residual package at its anchor."""
    findings_map = dict(findings or ELDYRWILD_DESCENDANT_RESIDUAL_FINDINGS)
    _assert_findings_exact(findings_map)
    seals_by_edge = load_descendant_residual_source_seals(source_seals_path)

    if world_id != ELDYRWILD_WORLD_ID:
        raise RelationshipDescendantResidualAdjudicationError(
            f"descendant adjudication world mismatch: {world_id!r}"
        )
    if revision_id != S25_REVISION_ID:
        raise RelationshipDescendantResidualAdjudicationError(
            "descendant adjudication analyzer is pinned to S25 anchor "
            f"{S25_REVISION_ID}; got {revision_id!r}"
        )

    digest_before = snapshot_world_graph_tree_digest(root, world_id)
    manifest, store = _load_exact_buddy_revision(
        root=root, world_id=world_id, revision_id=revision_id
    )
    payload_sha = getattr(manifest, "graph_payload_sha256", None)
    if payload_sha != S25_PAYLOAD_SHA256:
        raise RelationshipDescendantResidualAdjudicationError(
            f"S25 payload sha mismatch: {payload_sha} != {S25_PAYLOAD_SHA256}"
        )
    parent_id = getattr(manifest, "parent_revision_id", None)
    if parent_id != S25_PARENT_REVISION_ID:
        raise RelationshipDescendantResidualAdjudicationError(
            f"S25 parent mismatch: {parent_id} != {S25_PARENT_REVISION_ID}"
        )

    records: list[DescendantResidualAdjudicationRecordV1] = []
    by_disp: Counter[str] = Counter()
    by_repo: Counter[str] = Counter()
    by_action: Counter[str] = Counter()

    for edge_id in EXACT_U7_EDGE_IDS:
        finding = findings_map[edge_id]
        seal = seals_by_edge[edge_id]
        edge = store.edges.get(edge_id)
        if edge is None:
            raise RelationshipDescendantResidualAdjudicationError(
                f"U₇ edge missing at S25: {edge_id}"
            )
        support = _support_for_edge(store, edge_id)
        if support.get("introduced_by_contribution_id") != S25_INTRODUCING_CONTRIBUTION_ID:
            raise RelationshipDescendantResidualAdjudicationError(
                f"U₇ edge {edge_id} introduced_by mismatch: "
                f"{support.get('introduced_by_contribution_id')}"
            )
        if seal.get("source_artifact_id") != S25_SOURCE_ARTIFACT_ID:
            raise RelationshipDescendantResidualAdjudicationError(
                f"seal source_artifact_id mismatch for {edge_id}"
            )
        if seal.get("artifact_content_sha256") != S25_SOURCE_ARTIFACT_CONTENT_SHA256:
            raise RelationshipDescendantResidualAdjudicationError(
                f"seal artifact_content_sha256 mismatch for {edge_id}"
            )
        if verify_excerpts:
            primary_id = seal["primary_evidence_ref_id"]
            live = resolve_evidence_excerpt(
                store,
                edge_id=edge_id,
                evidence_ref_id=primary_id,
                world_graph_root=root,
            )
            verify_excerpt_against_seal(live, seal, edge_id=edge_id)

        by_disp[finding.disposition.value] += 1
        by_repo[finding.responsible_repo.value] += 1
        by_action[finding.next_action.value] += 1
        records.append(
            DescendantResidualAdjudicationRecordV1(
                edge_id=edge_id,
                disposition=finding.disposition.value,
                reason_code=finding.reason_code.value,
                responsible_repo=finding.responsible_repo.value,
                next_action=finding.next_action.value,
                requires_source_mutation=finding.requires_source_mutation,
                rationale=finding.rationale,
                primary_evidence_ref_id=str(seal["primary_evidence_ref_id"]),
                source_artifact_id=str(seal["source_artifact_id"]),
                source_span_ref_id=str(seal["source_span_ref_id"]),
                excerpt_sha256=str(seal["excerpt_sha256"]),
            )
        )

    digest_after = snapshot_world_graph_tree_digest(root, world_id)
    if digest_after != digest_before:
        raise RelationshipDescendantResidualAdjudicationError(
            "descendant adjudication analysis mutated world-graph tree digest"
        )

    return DescendantResidualAdjudicationReportV1(
        schema_version=DESCENDANT_RESIDUAL_ADJUDICATION_SCHEMA_V1,
        world_id=world_id,
        campaign_id=ELDYRWILD_CAMPAIGN_ID,
        anchor_revision_id=S25_REVISION_ID,
        anchor_graph_payload_sha256=S25_PAYLOAD_SHA256,
        adjudicated_count=len(records),
        by_disposition=_counter_rows(by_disp),
        by_responsible_repo=_counter_rows(by_repo),
        by_next_action=_counter_rows(by_action),
        records=records,
        world_graph_digest_before=digest_before,
        world_graph_digest_after=digest_after,
    )


def compact_descendant_residual_adjudication_report_v1(
    report: DescendantResidualAdjudicationReportV1,
) -> dict[str, Any]:
    return {
        "schema": report.schema_version,
        "world_id": report.world_id,
        "campaign_id": report.campaign_id,
        "anchor_revision_id": report.anchor_revision_id,
        "anchor_graph_payload_sha256": report.anchor_graph_payload_sha256,
        "adjudicated_count": report.adjudicated_count,
        "by_disposition": report.by_disposition,
        "by_responsible_repo": report.by_responsible_repo,
        "by_next_action": report.by_next_action,
        "records": [
            {
                "edge_id": row.edge_id,
                "disposition": row.disposition,
                "reason_code": row.reason_code,
                "responsible_repo": row.responsible_repo,
                "next_action": row.next_action,
                "requires_source_mutation": row.requires_source_mutation,
                "rationale": row.rationale,
                "primary_evidence_ref_id": row.primary_evidence_ref_id,
                "source_artifact_id": row.source_artifact_id,
                "source_span_ref_id": row.source_span_ref_id,
                "excerpt_sha256": row.excerpt_sha256,
            }
            for row in report.records
        ],
    }


def descendant_residual_fixture_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()
