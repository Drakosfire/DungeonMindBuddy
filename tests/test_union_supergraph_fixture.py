from __future__ import annotations

import copy
import subprocess
import sys

import pytest

from evals.graph_memory_layer.report_union_supergraph_fixture import build_report
from evals.graph_memory_layer.validate_union_supergraph_fixture import (
    DEFAULT_FIXTURE_PATH,
    UnionSupergraphValidationError,
    load_fixture,
    validate_union_supergraph_fixture,
)


@pytest.fixture
def fixture() -> dict:
    return load_fixture(DEFAULT_FIXTURE_PATH)


def assert_invalid(payload: dict, text: str) -> None:
    with pytest.raises(UnionSupergraphValidationError, match=text):
        validate_union_supergraph_fixture(payload)


def test_valid_fixture_passes(fixture: dict) -> None:
    result = validate_union_supergraph_fixture(fixture)
    assert result["valid"] is True
    assert result["schema"] == "dmb_union_supergraph_store_v0"
    assert result["multi_domain_node_count"] >= 1


def test_missing_node_evidence_ref_fails(fixture: dict) -> None:
    payload = copy.deepcopy(fixture)
    payload["nodes"]["pc_caelynn"]["evidence_ref_ids"].append("missing:evidence")
    assert_invalid(payload, "missing:evidence")


def test_edge_with_unknown_source_node_fails(fixture: dict) -> None:
    payload = copy.deepcopy(fixture)
    edge = payload["edges"]["edge:pc_caelynn:connected_to:loc_mirathorn"]
    edge["source_node_id"] = "missing_node"
    assert_invalid(payload, "source_node_id missing_node")


def test_edge_with_unknown_target_node_fails(fixture: dict) -> None:
    payload = copy.deepcopy(fixture)
    edge = payload["edges"]["edge:pc_caelynn:connected_to:loc_mirathorn"]
    edge["target_node_id"] = "missing_node"
    assert_invalid(payload, "target_node_id missing_node")


def test_edge_with_unknown_evidence_ref_fails(fixture: dict) -> None:
    payload = copy.deepcopy(fixture)
    edge = payload["edges"]["edge:pc_caelynn:connected_to:loc_mirathorn"]
    edge["evidence_ref_ids"] = ["missing:evidence"]
    assert_invalid(payload, "missing:evidence")


def test_evidence_with_unknown_source_artifact_fails(fixture: dict) -> None:
    payload = copy.deepcopy(fixture)
    payload["evidence"]["evidence:worldbuilding:caelynn:character-note"]["source_artifact_id"] = "missing:artifact"
    assert_invalid(payload, "missing:artifact")


def test_adjacency_with_unknown_node_fails(fixture: dict) -> None:
    payload = copy.deepcopy(fixture)
    payload["adjacency"]["missing_node"] = []
    assert_invalid(payload, "adjacency node missing_node")


def test_adjacency_with_unknown_edge_fails(fixture: dict) -> None:
    payload = copy.deepcopy(fixture)
    payload["adjacency"]["pc_caelynn"][0]["edge_id"] = "missing:edge"
    assert_invalid(payload, "missing:edge")


def test_fixture_without_multi_source_domain_node_fails(fixture: dict) -> None:
    payload = copy.deepcopy(fixture)
    for node in payload["nodes"].values():
        node["source_domains"] = node["source_domains"][:1]
    assert_invalid(payload, "multiple source domains")


def test_fixture_without_focus_session_evidence_fails(fixture: dict) -> None:
    payload = copy.deepcopy(fixture)
    for item in payload["evidence"].values():
        item.pop("session_id", None)
        item.pop("source_span_ref_id", None)
        item["source_domain"] = "worldbuilding"
        item["locator"] = item.get("locator", "fixture://locator")
    assert_invalid(payload, "session-focused")


def test_fixture_without_non_focus_or_non_recap_evidence_fails(fixture: dict) -> None:
    payload = copy.deepcopy(fixture)
    for item in payload["evidence"].values():
        item["source_domain"] = "recap"
        item["session_id"] = "session-23"
        item["source_span_ref_id"] = item.get("source_span_ref_id", "spref:session-23:p999")
    assert_invalid(payload, "non-recap or non-focus-session")


def test_unsafe_diagnostics_fail(fixture: dict) -> None:
    payload = copy.deepcopy(fixture)
    payload["diagnostics"]["corpus_mutation"] = True
    assert_invalid(payload, "diagnostics.corpus_mutation")


def test_report_cli_prints_counts_and_readiness() -> None:
    completed = subprocess.run(
        [sys.executable, "-m", "evals.graph_memory_layer.report_union_supergraph_fixture"],
        check=True,
        capture_output=True,
        text=True,
    )
    assert "node_count: 3" in completed.stdout
    assert "edge_count: 2" in completed.stdout
    assert "readiness_verdict: ready" in completed.stdout


def test_build_report_returns_summary(fixture: dict) -> None:
    report = build_report(fixture)
    assert report["source_artifact_count"] == 3
    assert report["focus_session_edge_count"] == 1
    assert report["non_focus_edge_count"] == 1
