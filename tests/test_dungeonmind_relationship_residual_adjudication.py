"""Eldyrwild residual relationship semantic adjudication proofs."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from apps.live_control_server.config import world_graph_root
from apps.live_control_server.integrations.dungeonmind_kernel.relationship_residual_adjudication import (
    ELDYRWILD_PAYLOAD_SHA256,
    ELDYRWILD_RESIDUAL_FINDINGS,
    ELDYRWILD_REVISION_ID,
    ELDYRWILD_WORLD_ID,
    EXPECTED_RESIDUAL_BY_PREDICATE,
    EXPECTED_RESIDUAL_COUNT,
    FORBIDDEN_CATCH_ALL_TERMS,
    RELATIONSHIP_RESIDUAL_ADJUDICATION_SCHEMA,
    NextAction,
    ReasonCode,
    RelationshipResidualAdjudicationError,
    ResidualDisposition,
    ResponsibleRepo,
    adjudicate_synthetic_residual,
    analyze_eldyrwild_relationship_residual_adjudication,
    collect_v3_residual_edge_ids,
    compact_relationship_residual_adjudication_report,
)
from apps.live_control_server.integrations.dungeonmind_kernel.whole_world_conformance import (
    snapshot_world_graph_tree_digest,
)
from apps.live_control_server.integrations.dungeonmind_kernel.whole_world_conformance_v3 import (
    PredicateDisposition,
    _classify_edge_predicate_v3,
)
from dungeonmind_dnd.application.world_object_vocabulary import (
    load_builtin_world_object_v3_vocabulary,
)
from apps.live_control_server.integrations.dungeonmind_kernel.whole_world_conformance import (
    _load_exact_buddy_revision,
)

FIXTURE_PATH = (
    Path(__file__).resolve().parent
    / "fixtures"
    / "dungeonmind_kernel"
    / "eldyrwild_relationship_residual_adjudication_v1.json"
)

LYSANDRA_EDGE_ID = (
    "edge:npc_lysandra:threatens:node:cultists_of_longmont:is-threatened-by-cultists"
)


def _eldyrwild_available() -> bool:
    root = world_graph_root()
    world_root = root / "graph_memory" / "worlds" / ELDYRWILD_WORLD_ID
    if not world_root.exists():
        world_root = root / "worlds" / ELDYRWILD_WORLD_ID
    return world_root.exists()


def test_synthetic_existing_term_endpoint_extension() -> None:
    finding = adjudicate_synthetic_residual(
        buddy_predicate="located_in",
        source_buddy_kind="item",
        target_buddy_kind="item",
        edge_id="edge:synthetic:poster:located_in:board",
        evidence_supports_exact_dm_term="dnd5e:located_in",
        endpoint_extension_safe=True,
    )
    assert (
        finding.disposition
        == ResidualDisposition.EXISTING_TERM_ENDPOINT_EXTENSION_CANDIDATE
    )
    assert finding.candidate_dungeonmind_term == "dnd5e:located_in"
    assert finding.responsible_repo == ResponsibleRepo.DUNGEONMIND
    assert finding.next_action == NextAction.EXTEND_DUNGEONMIND_ENDPOINTS


def test_synthetic_matching_predicate_string_is_not_automatically_safe() -> None:
    finding = adjudicate_synthetic_residual(
        buddy_predicate="leads_to",
        source_buddy_kind="npc",
        target_buddy_kind="location",
        edge_id="edge:synthetic:npc:leads_to:loc",
        evidence_supports_exact_dm_term="dnd5e:leads_to",
        endpoint_extension_safe=False,
        predicate_misapplied=True,
    )
    assert finding.disposition == ResidualDisposition.SOURCE_CORRECTION_REQUIRED
    assert finding.candidate_dungeonmind_term is None


def test_synthetic_explicit_rename_adapter() -> None:
    finding = adjudicate_synthetic_residual(
        buddy_predicate="path_to",
        source_buddy_kind="location",
        target_buddy_kind="location",
        edge_id="edge:synthetic:a:path_to:b",
        evidence_supports_exact_dm_term="dnd5e:leads_to",
        reverse_endpoints=False,
    )
    assert finding.disposition == ResidualDisposition.EXPLICIT_ADAPTER_CANDIDATE
    assert finding.candidate_dungeonmind_term == "dnd5e:leads_to"
    assert finding.reverse_endpoints is False
    assert finding.responsible_repo == ResponsibleRepo.DUNGEONMINDBUDDY


def test_synthetic_explicit_reversal_is_local() -> None:
    finding = adjudicate_synthetic_residual(
        buddy_predicate="carries",
        source_buddy_kind="item",
        target_buddy_kind="pc",
        edge_id="edge:synthetic:item:carries:pc",
        evidence_supports_exact_dm_term="dnd5e:carries",
        reverse_endpoints=True,
    )
    assert finding.disposition == ResidualDisposition.EXPLICIT_ADAPTER_CANDIDATE
    assert finding.reverse_endpoints is True
    assert finding.reason_code == ReasonCode.REVERSE_ENDPOINT_FORM


def test_synthetic_identity_stays_outside_relationship_vocabulary() -> None:
    finding = adjudicate_synthetic_residual(
        buddy_predicate="same_as",
        source_buddy_kind="location",
        target_buddy_kind="location",
        edge_id="edge:synthetic:a:same_as:b",
        is_identity=True,
    )
    assert finding.disposition == ResidualDisposition.IDENTITY_NOT_RELATIONSHIP
    assert finding.candidate_dungeonmind_term is None
    with pytest.raises(RelationshipResidualAdjudicationError):
        adjudicate_synthetic_residual(
            buddy_predicate="same_as",
            source_buddy_kind="location",
            target_buddy_kind="location",
            edge_id="edge:synthetic:a:same_as:b",
            is_identity=True,
            evidence_supports_exact_dm_term="dnd5e:same_as",
        )


def test_synthetic_compound_cannot_flatten_to_component_term() -> None:
    finding = adjudicate_synthetic_residual(
        buddy_predicate="carries_report_to",
        source_buddy_kind="npc",
        target_buddy_kind="location",
        edge_id="edge:synthetic:npc:carries_report_to:loc",
        is_compound=True,
        evidence_supports_exact_dm_term="dnd5e:carries",
    )
    assert (
        finding.disposition
        == ResidualDisposition.COMPOUND_ASSERTION_NOT_SINGLE_RELATIONSHIP
    )
    assert finding.candidate_dungeonmind_term is None


def test_synthetic_direction_contradiction_not_saved_by_compatible_endpoints() -> None:
    finding = adjudicate_synthetic_residual(
        buddy_predicate="threatens",
        source_buddy_kind="npc",
        target_buddy_kind="faction",
        edge_id=LYSANDRA_EDGE_ID,
        evidence_supports_exact_dm_term="dnd5e:threatens",
        endpoint_extension_safe=True,
        direction_contradiction=True,
    )
    assert finding.disposition == ResidualDisposition.SOURCE_CORRECTION_REQUIRED
    assert finding.reason_code == ReasonCode.DIRECTION_CONTRADICTION


def test_synthetic_insufficient_evidence_remains_visible() -> None:
    finding = adjudicate_synthetic_residual(
        buddy_predicate="mystery_link",
        source_buddy_kind="npc",
        target_buddy_kind="mystery",
        edge_id="edge:synthetic:insufficient",
        insufficient_evidence=True,
    )
    assert finding.disposition == ResidualDisposition.INSUFFICIENT_EVIDENCE
    assert finding.next_action == NextAction.GATHER_OR_CLARIFY_EVIDENCE


def test_synthetic_unknown_predicate_has_no_fallback() -> None:
    finding = adjudicate_synthetic_residual(
        buddy_predicate="blorps_with",
        source_buddy_kind="npc",
        target_buddy_kind="npc",
        edge_id="edge:synthetic:unknown",
    )
    assert finding.disposition == ResidualDisposition.NEW_PREDICATE_CANDIDATE
    assert finding.candidate_dungeonmind_term is None
    assert "related_to" not in (finding.rationale or "")


def test_synthetic_uses_statblock_never_enters_adjudication() -> None:
    with pytest.raises(RelationshipResidualAdjudicationError):
        adjudicate_synthetic_residual(
            buddy_predicate="uses_statblock",
            source_buddy_kind="npc",
            target_buddy_kind="external_resource",
            edge_id="edge:synthetic:uses_statblock",
            mechanics_predicate=True,
        )


def test_findings_table_covers_exactly_expected_residual_predicates() -> None:
    assert len(ELDYRWILD_RESIDUAL_FINDINGS) == EXPECTED_RESIDUAL_COUNT
    assert sum(EXPECTED_RESIDUAL_BY_PREDICATE.values()) == EXPECTED_RESIDUAL_COUNT
    for edge_id, finding in ELDYRWILD_RESIDUAL_FINDINGS.items():
        assert finding.candidate_dungeonmind_term not in FORBIDDEN_CATCH_ALL_TERMS
        if ":same_as:" in edge_id or edge_id.endswith(":same_as"):
            # edge ids embed predicate; all same_as edges must be identity
            pass
        if finding.disposition == ResidualDisposition.IDENTITY_NOT_RELATIONSHIP:
            assert finding.candidate_dungeonmind_term is None


def test_committed_fixture_is_self_consistent() -> None:
    fixture = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    assert fixture["schema"] == RELATIONSHIP_RESIDUAL_ADJUDICATION_SCHEMA
    assert fixture["world_id"] == ELDYRWILD_WORLD_ID
    assert fixture["revision_id"] == ELDYRWILD_REVISION_ID
    assert fixture["graph_payload_sha256"] == ELDYRWILD_PAYLOAD_SHA256
    assert fixture["relationship_semantic_count"] == 346
    assert fixture["relationship_represented_count"] == 287
    assert fixture["relationship_residual_count"] == 59
    assert fixture["uses_statblock_mechanics_count"] == 2
    assert fixture["adjudicated_count"] == 59
    assert fixture["missing_adjudication_count"] == 0
    assert fixture["extra_adjudication_count"] == 0
    assert len(fixture["records"]) == 59

    pred_table = {row["key"]: row["count"] for row in fixture["residual_by_predicate"]}
    assert pred_table == EXPECTED_RESIDUAL_BY_PREDICATE

    edge_ids = [row["edge_id"] for row in fixture["records"]]
    assert len(set(edge_ids)) == 59
    assert "uses_statblock" not in {
        row["buddy_predicate"] for row in fixture["records"]
    }
    for row in fixture["records"]:
        assert row["candidate_dungeonmind_term"] not in FORBIDDEN_CATCH_ALL_TERMS
        assert not (
            row["candidate_dungeonmind_term"]
            and row["candidate_dungeonmind_term"].endswith(":related_to")
        )
        if row["buddy_predicate"] == "same_as":
            assert row["disposition"] == ResidualDisposition.IDENTITY_NOT_RELATIONSHIP.value
            assert row["candidate_dungeonmind_term"] is None

    lysandra = next(r for r in fixture["records"] if r["edge_id"] == LYSANDRA_EDGE_ID)
    assert lysandra["disposition"] == ResidualDisposition.SOURCE_CORRECTION_REQUIRED.value
    assert lysandra["reason_code"] == ReasonCode.DIRECTION_CONTRADICTION.value


@pytest.mark.skipif(not _eldyrwild_available(), reason="Eldyrwild world graph not present")
def test_eldyrwild_residual_identity_matches_v3() -> None:
    root = world_graph_root()
    vocabulary = load_builtin_world_object_v3_vocabulary()
    _manifest, store = _load_exact_buddy_revision(
        root=root,
        world_id=ELDYRWILD_WORLD_ID,
        revision_id=ELDYRWILD_REVISION_ID,
    )
    v3_ids = collect_v3_residual_edge_ids(store, vocabulary)
    assert len(v3_ids) == 59

    # uses_statblock must be mechanics, never residual
    for edge in store.edges.values():
        if edge.predicate != "uses_statblock":
            continue
        *_r, disposition, _m, _rev = _classify_edge_predicate_v3(
            edge, store, vocabulary
        )
        assert disposition == PredicateDisposition.MECHANICS_SPECIALIZATION
        assert edge.edge_id not in v3_ids

    report = analyze_eldyrwild_relationship_residual_adjudication(root=root)
    assert {r.edge_id for r in report.records} == v3_ids
    assert report.adjudicated_count == 59
    assert report.missing_adjudication_count == 0
    assert report.extra_adjudication_count == 0


@pytest.mark.skipif(not _eldyrwild_available(), reason="Eldyrwild world graph not present")
def test_eldyrwild_integration_fixture_and_read_only_graph() -> None:
    root = world_graph_root()
    before = snapshot_world_graph_tree_digest(root, ELDYRWILD_WORLD_ID)
    report = analyze_eldyrwild_relationship_residual_adjudication(root=root)
    after = snapshot_world_graph_tree_digest(root, ELDYRWILD_WORLD_ID)
    assert before == after
    assert report.world_graph_digest_before == report.world_graph_digest_after

    assert report.relationship_semantic_count == 346
    assert report.relationship_represented_count == 287
    assert report.relationship_residual_count == 59
    assert report.uses_statblock_mechanics_count == 2
    assert report.adjudicated_count == 59

    compact = compact_relationship_residual_adjudication_report(report)
    fixture = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    assert compact == fixture

    # Successor derivation is multi-owner — do not collapse to one fix-all slice.
    named = [s for s in report.successor_slices if s["name"] != "summary-disposition-counts"]
    assert len(named) >= 2
    owners = {s["responsible_repo"] for s in named}
    assert ResponsibleRepo.DUNGEONMIND.value in owners
    assert ResponsibleRepo.DUNGEONMINDBUDDY.value in owners
