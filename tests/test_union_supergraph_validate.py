"""Structural vs fixture validation for union supergraph payloads (PR006D)."""

from __future__ import annotations

import copy

import pytest

from graph_memory.union_supergraph.load import DEFAULT_FIXTURE_PATH, load_union_supergraph_payload
from graph_memory.union_supergraph.validate import (
    UnionSupergraphValidationError,
    validate_union_supergraph_fixture,
    validate_union_supergraph_store_payload,
)


@pytest.fixture
def fixture() -> dict:
    return load_union_supergraph_payload(DEFAULT_FIXTURE_PATH)


def test_empty_structural_baseline_passes() -> None:
    payload = {
        "schema": "dmb_union_supergraph_store_v0",
        "version": "0.1",
        "campaign_id": "longmont-c2",
        "focus_session_id": "session-23",
        "nodes": {},
        "edges": {},
        "evidence": {},
        "source_artifacts": {},
        "aliases": {},
        "assertion_support": {},
        "adjacency": {},
        "identity_decisions": [],
        "identity_redirects": [],
        "identity_merge_records": [],
        "diagnostics": {
            "canon_promotion": False,
            "approved_memory_write": False,
            "corpus_mutation": False,
            "production_retrieval": False,
        },
    }
    report = validate_union_supergraph_store_payload(payload)
    assert report["valid"] is True
    assert report["node_count"] == 0


def test_empty_payload_fails_fixture_acceptance() -> None:
    payload = {
        "schema": "dmb_union_supergraph_store_v0",
        "version": "0.1",
        "campaign_id": "longmont-c2",
        "focus_session_id": "session-23",
        "nodes": {},
        "edges": {},
        "evidence": {},
        "source_artifacts": {},
        "aliases": {},
        "assertion_support": {},
        "adjacency": {},
        "identity_decisions": [],
        "identity_redirects": [],
        "identity_merge_records": [],
        "diagnostics": {
            "canon_promotion": False,
            "approved_memory_write": False,
            "corpus_mutation": False,
            "production_retrieval": False,
        },
    }
    with pytest.raises(
        UnionSupergraphValidationError,
        match="at least one node must have multiple source domains",
    ):
        validate_union_supergraph_fixture(payload)


def test_fixture_passes_structural_and_fixture_validation(fixture: dict) -> None:
    structural = validate_union_supergraph_store_payload(fixture)
    fixture_report = validate_union_supergraph_fixture(fixture)
    assert structural["valid"] is True
    assert fixture_report["valid"] is True


def test_structural_pass_does_not_require_richness(fixture: dict) -> None:
    payload = copy.deepcopy(fixture)
    payload["nodes"] = {}
    payload["edges"] = {}
    payload["evidence"] = {}
    payload["source_artifacts"] = {}
    payload["aliases"] = {}
    payload["assertion_support"] = {}
    payload["adjacency"] = {}
    report = validate_union_supergraph_store_payload(payload)
    assert report["node_count"] == 0


def test_assertion_support_requires_typed_fields_and_refs() -> None:
    payload = {
        "schema": "dmb_union_supergraph_store_v0",
        "version": "0.1",
        "campaign_id": "longmont-c2",
        "focus_session_id": "session-23",
        "nodes": {},
        "edges": {},
        "evidence": {},
        "source_artifacts": {},
        "aliases": {},
        "assertion_support": {
            "assertion:1": {
                "assertion_id": "assertion:1",
                "active_contribution_ids": ["contribution:1"],
                "superseded_contribution_ids": [],
                "retracted_contribution_ids": [],
                "evidence_ref_ids": ["missing-evidence"],
                "source_artifact_ids": [],
                "support_state": "supported",
                "introduced_by_contribution_id": "contribution:1",
                "assertion_kind": "attribute",
                "graph_object_id": None,
            }
        },
        "adjacency": {},
        "identity_decisions": [],
        "identity_redirects": [],
        "identity_merge_records": [],
        "diagnostics": {
            "canon_promotion": False,
            "approved_memory_write": False,
            "corpus_mutation": False,
            "production_retrieval": False,
        },
    }
    with pytest.raises(UnionSupergraphValidationError, match="evidence_ref_id"):
        validate_union_supergraph_store_payload(payload)


def test_assertion_support_key_must_equal_assertion_id() -> None:
    payload = {
        "schema": "dmb_union_supergraph_store_v0",
        "version": "0.1",
        "campaign_id": "longmont-c2",
        "focus_session_id": "session-23",
        "nodes": {},
        "edges": {},
        "evidence": {},
        "source_artifacts": {},
        "aliases": {},
        "assertion_support": {
            "support:mismatched": {
                "assertion_id": "assertion:1",
                "active_contribution_ids": ["contribution:1"],
                "superseded_contribution_ids": [],
                "retracted_contribution_ids": [],
                "evidence_ref_ids": [],
                "source_artifact_ids": [],
                "support_state": "supported",
                "introduced_by_contribution_id": "contribution:1",
                "assertion_kind": "attribute",
                "graph_object_id": None,
            }
        },
        "adjacency": {},
        "identity_decisions": [],
        "identity_redirects": [],
        "identity_merge_records": [],
        "diagnostics": {
            "canon_promotion": False,
            "approved_memory_write": False,
            "corpus_mutation": False,
            "production_retrieval": False,
        },
    }
    with pytest.raises(UnionSupergraphValidationError, match="must equal assertion_id"):
        validate_union_supergraph_store_payload(payload)
