from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
REGISTRY_PATH = REPO_ROOT / "evals" / "graph_memory_layer" / "taxonomy_registry.json"
REQUIRED_VOCABULARIES = {
    "source_kind", "source_layer", "entity_kind", "route_kind", "evidence_role",
    "authority_state", "visibility_state", "truth_state", "lifecycle_state",
    "relationship_predicate_family", "planning_lane", "retrieval_lane",
    "graph_candidate_state", "promotion_state", "validation_severity",
}
REQUIRED_TERM_FIELDS = {
    "id", "label", "description", "allowed_usage", "disallowed_usage",
    "examples", "allowed_graph_record_states",
}
LIST_FIELDS = {"allowed_usage", "disallowed_usage", "examples", "allowed_graph_record_states"}
REQUIRED_SAFETY_TERMS = {
    "source_evidence", "diagnostic_only", "played_truth", "gm_prep", "rumor",
    "candidate", "derived_summary", "validated", "rejected", "deprecated",
    "conflicted", "private_gm", "player_visible",
}


def load_registry() -> dict[str, Any]:
    with REGISTRY_PATH.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    assert isinstance(data, dict)
    return data


def test_taxonomy_registry_file_exists() -> None:
    assert REGISTRY_PATH.is_file()


def test_taxonomy_registry_validator_exits_zero() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "evals.graph_memory_layer.validate_taxonomy_registry"],
        cwd=REPO_ROOT,
        check=False,
        text=True,
        capture_output=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "- taxonomy registry: ready" in result.stdout


def test_required_vocabularies_exist() -> None:
    vocabularies = load_registry()["vocabularies"]
    assert REQUIRED_VOCABULARIES <= set(vocabularies)


def test_vocabulary_ids_are_unique() -> None:
    vocabularies = load_registry()["vocabularies"].values()
    ids = [vocabulary["id"] for vocabulary in vocabularies]
    assert len(ids) == len(set(ids))


def test_term_ids_are_unique_within_each_vocabulary() -> None:
    for vocabulary in load_registry()["vocabularies"].values():
        ids = [term["id"] for term in vocabulary["terms"]]
        assert len(ids) == len(set(ids)), vocabulary["id"]


def test_every_term_has_required_fields() -> None:
    for vocabulary in load_registry()["vocabularies"].values():
        for term in vocabulary["terms"]:
            assert REQUIRED_TERM_FIELDS <= set(term), (vocabulary["id"], term.get("id"))


def test_term_list_fields_are_lists() -> None:
    for vocabulary in load_registry()["vocabularies"].values():
        for term in vocabulary["terms"]:
            for field in LIST_FIELDS:
                assert isinstance(term[field], list), (vocabulary["id"], term["id"], field)


def test_required_safety_terms_exist_somewhere() -> None:
    seen = {
        term["id"]
        for vocabulary in load_registry()["vocabularies"].values()
        for term in vocabulary["terms"]
    }
    assert REQUIRED_SAFETY_TERMS <= seen


def test_no_blank_term_id_label_or_description() -> None:
    for vocabulary in load_registry()["vocabularies"].values():
        for term in vocabulary["terms"]:
            assert term["id"].strip()
            assert term["label"].strip()
            assert term["description"].strip()
