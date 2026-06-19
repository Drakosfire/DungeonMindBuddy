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
    "examples", "allowed_graph_record_states", "admissibility_notes",
}
ALLOWED_GRAPH_RECORD_STATES = {"baseline", "candidate", "validated", "promoted", "rejected", "deprecated", "archived"}
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


def test_allowed_graph_record_states_use_known_values() -> None:
    for vocabulary in load_registry()["vocabularies"].values():
        for term in vocabulary["terms"]:
            assert set(term["allowed_graph_record_states"]) <= ALLOWED_GRAPH_RECORD_STATES


def find_term(term_id: str) -> dict[str, Any]:
    for vocabulary in load_registry()["vocabularies"].values():
        for term in vocabulary["terms"]:
            if term["id"] == term_id:
                return term
    raise AssertionError(f"missing term {term_id}")


def semantic_text(term: dict[str, Any]) -> str:
    parts: list[str] = [term["description"], term["admissibility_notes"]]
    parts.extend(term["allowed_usage"])
    parts.extend(term["disallowed_usage"])
    return " ".join(parts).lower()


def test_evidence_role_guardrails_are_explicit() -> None:
    for term_id in {"diagnostic_only", "derived_summary", "routing_hint", "not_admissible"}:
        text = semantic_text(find_term(term_id))
        assert "not source evidence" in text or "not admit" in text or "not admissible" in text
        assert "promoted" not in find_term(term_id)["allowed_graph_record_states"]


def test_authority_state_guardrails_do_not_imply_source_truth() -> None:
    for term_id in {"llm_inferred", "rumor", "gm_prep", "unknown", "contradicted"}:
        text = semantic_text(find_term(term_id))
        assert "do not" in text or "not source" in text or "not imply" in text
        assert "promoted" not in find_term(term_id)["allowed_graph_record_states"]


def test_visibility_terms_preserve_boundaries() -> None:
    assert "player" in semantic_text(find_term("player_visible"))
    assert "gm" in semantic_text(find_term("private_gm"))
    assert "spoiler" in semantic_text(find_term("spoiler_sensitive"))
    assert "internal" in semantic_text(find_term("internal_diagnostic"))


def test_no_blank_term_id_label_description_or_admissibility_notes() -> None:
    for vocabulary in load_registry()["vocabularies"].values():
        for term in vocabulary["terms"]:
            assert term["id"].strip()
            assert term["label"].strip()
            assert term["description"].strip()
            assert term["admissibility_notes"].strip()
