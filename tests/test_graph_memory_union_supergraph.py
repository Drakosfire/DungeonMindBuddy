from __future__ import annotations

import copy
import os
import subprocess
import sys
from pathlib import Path

import pytest

from graph_memory.union_supergraph.report import build_report
from graph_memory.union_supergraph.validate import (
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


def test_unknown_declared_source_domain_fails(fixture: dict) -> None:
    payload = copy.deepcopy(fixture)
    payload["source_domains"].append("dream_pickle")
    assert_invalid(payload, "unknown source_domain dream_pickle")


def test_missing_focus_session_id_fails(fixture: dict) -> None:
    payload = copy.deepcopy(fixture)
    payload.pop("focus_session_id")
    assert_invalid(payload, "focus_session_id is required")


def test_focus_session_id_mismatch_fails(fixture: dict) -> None:
    payload = copy.deepcopy(fixture)
    payload["focus_session_id"] = "session-99"
    assert_invalid(payload, "does not include focus_session_id session-99")


def test_focus_anchored_adjacency_on_non_focus_edge_fails(fixture: dict) -> None:
    payload = copy.deepcopy(fixture)
    payload["adjacency"]["pc_caelynn"][1]["anchored_to_focus_session"] = True
    assert_invalid(payload, "focus-anchored but edge")


def test_non_focus_adjacency_on_focus_edge_fails(fixture: dict) -> None:
    payload = copy.deepcopy(fixture)
    payload["adjacency"]["pc_caelynn"][0]["anchored_to_focus_session"] = False
    assert_invalid(payload, "is non-focus but edge")


def test_unsafe_diagnostics_fail(fixture: dict) -> None:
    payload = copy.deepcopy(fixture)
    payload["diagnostics"]["corpus_mutation"] = True
    assert_invalid(payload, "diagnostics.corpus_mutation")


def test_report_cli_prints_counts_and_readiness() -> None:
    src_path = str(Path(__file__).resolve().parents[1] / "src")
    env = {
        **os.environ,
        "PYTHONPATH": os.pathsep.join(filter(None, [src_path, os.environ.get("PYTHONPATH")])),
    }
    completed = subprocess.run(
        [sys.executable, "-m", "graph_memory.union_supergraph.report"],
        env=env,
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
