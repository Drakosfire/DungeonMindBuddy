"""Owning-boundary contract tests for immutable candidate admission."""

from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

import pytest

from apps.live_control_server.models.candidate_graph_admission import (
    CandidateAdmissionIntegrityError,
)
from apps.live_control_server.models.world_graph_mutation_context import (
    WorldGraphMutationContext,
)
from apps.live_control_server.services.candidate_graph_admission import (
    canonical_candidate_digest,
    confirm_candidate_graph_admission,
    prepare_candidate_graph_admission,
)
from graph_memory.candidate_graph_preview import (
    CANDIDATE_GRAPH_PREVIEW_SCHEMA,
    CANDIDATE_GRAPH_PREVIEW_VERSION,
)

_PR715_WITNESSES = (
    Path(__file__).parent
    / "fixtures/candidate_admission/pr715_failure_witnesses.json"
)


def _semantic() -> dict:
    return {
        "canon_state": "played_canon",
        "lifecycle_state": "candidate",
        "evidence_role": "source_evidence",
        "authority_state": "system_derived",
        "visibility_state": "gm_private",
    }


def _evidence(item: str) -> dict:
    return {
        "source_ref_id": f"ref:{item}",
        "source_artifact_id": "artifact:recap:longmont-c2:session-9",
        "evidence_role": "source_evidence",
        "can_open_source": True,
        "can_highlight_span": True,
        "source_span_ref_id": f"session-9:recap:paragraph:{item}",
    }


def _node(node_id: str, node_type: str) -> dict:
    return {
        "node_id": node_id,
        "label": node_id.rsplit(":", 1)[-1].replace("-", " ").title(),
        "node_type": node_type,
        "description": "Candidate admission witness.",
        "importance": "medium",
        "semantic_state": _semantic(),
        "evidence_refs": [_evidence(node_id)],
        "proposed_action": "create",
        "confidence": "medium",
        "warnings": [],
    }


def _candidate(*, unsupported: bool = False) -> dict:
    nodes = [_node("candidate:brin", "character")]
    edges: list[dict] = []
    if unsupported:
        nodes.append(_node("candidate:medical-wing", "sublocation"))
        edges.append(
            {
                "edge_id": "candidate:edge:brin-medical-wing",
                "from_node_id": "candidate:brin",
                "to_node_id": "candidate:medical-wing",
                "relationship_type": "located_at",
                "label": "located at",
                "semantic_state": _semantic(),
                "evidence_refs": [_evidence("edge")],
                "proposed_action": "create",
                "confidence": "medium",
                "warnings": [],
            }
        )
    return {
        "schema": CANDIDATE_GRAPH_PREVIEW_SCHEMA,
        "version": CANDIDATE_GRAPH_PREVIEW_VERSION,
        "preview_id": "preview:c2-s9-admission-witness",
        "campaign_id": "longmont-c2",
        "session_id": "session-9",
        "source_artifact_ids": ["artifact:recap:longmont-c2:session-9"],
        "status": "preview",
        "nodes": nodes,
        "edges": edges,
        "beats": [],
        "proposed_writes": [],
        "ignored_items": [],
        "deferred_items": [],
        "diagnostics": {
            "preview_only": True,
            "extraction_performed": False,
            "llm_used": False,
            "runtime_connected": False,
            "plan_connected": False,
            "agent_interaction_connected": False,
            "corpus_scanned": False,
            "corpus_mutated": False,
            "facts_promoted": False,
            "canon_promoted": False,
            "unresolved_evidence_refs": 0,
            "missing_evidence_objects": 0,
            "warning_count": 0,
        },
    }


def _prepare(tmp_path, candidate: dict):
    source = tmp_path / "session-9.md"
    source.write_text("Brin visits the Medical Wing.\n", encoding="utf-8")
    revision = f"sha256:{hashlib.sha256(source.read_bytes()).hexdigest()}"
    context = WorldGraphMutationContext(
        world_id="eldyrwild",
        revision_id="rev:d0",
        head_revision_id="rev:d0",
        objects={},
    )
    return prepare_candidate_graph_admission(
        candidate_graph=candidate,
        source_uri=str(source),
        source_revision_id=revision,
        prepared_by="gm@test",
        world_id="eldyrwild",
        source_artifact_id="artifact:recap:longmont-c2:session-9",
        campaign_scope="longmont-c2",
        candidate_graph_path=str(tmp_path / "candidate_graph.json"),
        repo_root=tmp_path,
        mutation_context=context,
    )


def test_digest_covers_complete_candidate_before_qualification(tmp_path) -> None:
    candidate = _candidate(unsupported=True)
    frozen = copy.deepcopy(candidate)
    result = _prepare(tmp_path, candidate)

    binding = result.review_package["effect"]["candidate_admission"]
    assert candidate == frozen
    assert binding["candidate_digest"] == canonical_candidate_digest(candidate)
    assert binding["exact_candidate_counts"] == {
        "nodes": 2,
        "edges": 1,
        "beats": 0,
        "proposed_writes": 0,
    }
    assert {
        (item["item_id"], item["reason"])
        for item in binding["dispositions"]
    } == {
        ("candidate:medical-wing", "unsupported_node_type"),
        ("candidate:edge:brin-medical-wing", "endpoint_not_admitted"),
    }
    assert result.accepted_proposals_count >= 1


@pytest.mark.parametrize(
    ("duplicate_id", "node_types"),
    [
        (entry["node_id"], entry["node_types"])
        for witness in json.loads(_PR715_WITNESSES.read_text())["witnesses"]
        for entry in witness["duplicate_nodes"]
    ],
)
def test_duplicate_node_ids_are_candidate_integrity_failures(
    tmp_path, duplicate_id: str, node_types: list[str]
) -> None:
    candidate = _candidate()
    candidate["nodes"] = [
        _node(duplicate_id, node_type) for node_type in node_types
    ]
    with pytest.raises(CandidateAdmissionIntegrityError) as excinfo:
        _prepare(tmp_path, candidate)
    assert [item.code for item in excinfo.value.diagnostics] == ["duplicate_node_id"]
    assert excinfo.value.diagnostics[0].object_id == duplicate_id


def test_pr715_s9_sublocation_witness_is_explicit_rejection(tmp_path) -> None:
    evidence = json.loads(_PR715_WITNESSES.read_text())
    s9 = next(item for item in evidence["witnesses"] if item["session_id"] == "session-9")
    medical_wing = s9["unsupported_nodes"][0]
    candidate = _candidate()
    candidate["nodes"].append(
        _node(medical_wing["node_id"], medical_wing["node_type"])
    )
    result = _prepare(tmp_path, candidate)
    assert result.review_package["effect"]["candidate_admission"]["dispositions"] == [
        {
            "item_id": "candidate:medical-wing",
            "item_kind": "node",
            "outcome": "rejected",
            "reason": "unsupported_node_type",
            "depends_on": [],
        }
    ]


def test_candidate_drift_blocks_governed_confirm(tmp_path) -> None:
    candidate = _candidate()
    result = _prepare(tmp_path, candidate)
    changed = copy.deepcopy(candidate)
    changed["nodes"][0]["description"] = "Drifted after prepare."
    called = False

    def _governed_confirm():
        nonlocal called
        called = True
        return "rev:d1"

    with pytest.raises(CandidateAdmissionIntegrityError) as excinfo:
        confirm_candidate_graph_admission(
            review_package=result.review_package,
            candidate_graph=changed,
            governed_confirm=_governed_confirm,
        )
    assert excinfo.value.diagnostics[0].code == "candidate_digest_mismatch"
    assert called is False


def test_unmapped_predicate_is_explicit_admission_rejection(tmp_path) -> None:
    candidate = _candidate()
    candidate["nodes"].append(_node("candidate:orik", "character"))
    candidate["edges"] = [
        {
            "edge_id": "candidate:edge:unknown",
            "from_node_id": "candidate:brin",
            "to_node_id": "candidate:orik",
            "relationship_type": "invented_relation",
            "label": "invented relation",
            "semantic_state": _semantic(),
            "evidence_refs": [_evidence("unknown-edge")],
            "proposed_action": "create",
            "confidence": "medium",
            "warnings": [],
        }
    ]
    result = _prepare(tmp_path, candidate)
    dispositions = result.review_package["effect"]["candidate_admission"][
        "dispositions"
    ]
    assert dispositions == [
        {
            "item_id": "candidate:edge:unknown",
            "item_kind": "edge",
            "outcome": "rejected",
            "reason": "unmapped_predicate",
            "depends_on": [],
        }
    ]


def test_exact_candidate_confirm_invokes_existing_write_once(tmp_path) -> None:
    candidate = _candidate()
    result = _prepare(tmp_path, candidate)
    calls = 0

    def _governed_confirm():
        nonlocal calls
        calls += 1
        return "rev:d1"

    assert confirm_candidate_graph_admission(
        review_package=result.review_package,
        candidate_graph=candidate,
        governed_confirm=_governed_confirm,
    ) == "rev:d1"
    assert calls == 1
