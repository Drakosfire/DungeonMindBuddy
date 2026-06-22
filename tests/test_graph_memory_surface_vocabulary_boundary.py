from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = REPO_ROOT / "evals" / "graph_memory_layer" / "surface_vocabulary_boundary.json"
REPORT_PATH = REPO_ROOT / "Docs" / "Reports" / "GRAPH-MEMORY-SURFACE-VOCABULARY-BOUNDARY.md"


def _manifest() -> dict[str, Any]:
    with MANIFEST_PATH.open(encoding="utf-8") as handle:
        data = json.load(handle)
    assert isinstance(data, dict)
    return data


def _ids(items: list[Any]) -> set[str]:
    ids: set[str] = set()
    for item in items:
        if isinstance(item, str):
            ids.add(item)
        elif isinstance(item, dict):
            ids.add(item["id"])
    return ids


def test_surface_vocabulary_boundary_manifest_exists() -> None:
    assert MANIFEST_PATH.is_file()


def test_surface_vocabulary_boundary_validator_exits_zero() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "evals.graph_memory_layer.validate_surface_vocabulary_boundary"],
        cwd=REPO_ROOT,
        check=False,
        text=True,
        capture_output=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "- surface vocabulary boundary: ready" in result.stdout


def test_surface_vocabulary_boundary_decision() -> None:
    assert _manifest()["decision"] == "share_semantic_envelope_preserve_surface_vocabulary"


def test_shared_semantic_envelope_includes_source_provenance_lifecycle_and_evidence() -> None:
    shared = _ids(_manifest()["shared_semantic_envelope"])
    assert {"source_artifact", "source_anchor", "source_unit", "source_ref"}.issubset(shared)
    assert {"provenance", "lifecycle_state", "evidence_role", "authority_state", "visibility_state"}.issubset(shared)


def test_ontology_owned_vocabulary_includes_lifecycle_evidence_source_and_entity_terms() -> None:
    ontology = set(_manifest()["ontology_owned_terms"])
    assert {"lifecycle_state", "evidence_role", "source_kind", "source_layer", "entity_kind"}.issubset(ontology)


def test_surface_owned_vocabulary_includes_chip_projection_and_tool_terms() -> None:
    surface = set(_manifest()["surface_owned_terms"])
    assert {"npc_chip", "location_chip", "reference_chip"}.issubset(surface)
    assert {"statblock_projection", "roll_table_projection", "projection_card"}.issubset(surface)
    assert {"tool_workflow", "edit_unlock"}.issubset(surface)


def test_contested_terms_include_statblock_summary_and_route() -> None:
    contested = _ids(_manifest()["contested_terms"])
    assert {"statblock", "summary", "route"}.issubset(contested)


def test_forbidden_collapses_include_summary_as_evidence_and_lifecycle_as_known_fact() -> None:
    forbidden = _ids(_manifest()["forbidden_collapses"])
    assert {"summary_as_source_evidence", "lifecycle_as_known_fact"}.issubset(forbidden)
    assert {"ui_ref_type_as_taxonomy_owner", "surface_projection_as_corpus_truth"}.issubset(forbidden)


def test_future_payload_required_fields_include_semantic_envelope_fields() -> None:
    fields = set(_manifest()["future_payload_required_fields"])
    assert {"adapter_key", "ref_id", "label"}.issubset(fields)
    assert {"source_anchor", "evidence_role", "authority_state", "visibility_state", "lifecycle_state", "provenance"}.issubset(fields)


def test_surface_vocabulary_boundary_report_exists() -> None:
    assert REPORT_PATH.is_file()


def test_report_includes_arguments_for_and_against_forcing_shared_vocabulary() -> None:
    report = REPORT_PATH.read_text(encoding="utf-8")
    assert "Arguments for forcing one shared vocabulary" in report
    assert "prevents lifecycle drift" in report
    assert "prevents evidence-role drift" in report
    assert "Arguments against forcing one shared vocabulary" in report
    assert "UI vocabulary is product-facing and task-shaped" in report
    assert "one UI term may map to multiple ontology concepts" in report


def test_report_includes_share_semantics_not_surface_labels() -> None:
    report = REPORT_PATH.read_text(encoding="utf-8").lower()
    assert "share semantics, not surface labels" in report
