from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from src.graph_memory.ontology_ir import GraphBundle, OntologyIRValidationError, TaxonomyRef, validate_scalar_properties


REPO_ROOT = Path(__file__).resolve().parents[1]
EXAMPLE_BUNDLE_PATH = REPO_ROOT / "evals" / "graph_memory_layer" / "examples" / "ontology_ir_minimal_bundle.json"
FORBIDDEN_EXAMPLE_TERMS = {
    "Mirathorn",
    "Bonogo",
    "Baergrom",
    "Ephanna",
    "Caelynn",
    "Stafl",
    "Karsemine",
    "Draven",
    "Stonebridge",
    "Rivers Edge",
    "Mireward",
}


def load_example_dict() -> dict[str, object]:
    with EXAMPLE_BUNDLE_PATH.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    assert isinstance(data, dict)
    return data


def test_example_bundle_exists() -> None:
    assert EXAMPLE_BUNDLE_PATH.is_file()


def test_ontology_ir_validator_exits_zero() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "evals.graph_memory_layer.validate_ontology_ir"],
        cwd=REPO_ROOT,
        check=False,
        text=True,
        capture_output=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "- ontology IR: ready" in result.stdout


def test_graph_bundle_loads_from_example_dict() -> None:
    bundle = GraphBundle.from_dict(load_example_dict())
    assert bundle.bundle_id == "example:ontology-ir:minimal"
    assert bundle.schema_version == "0.1"
    assert bundle.taxonomy_registry_version == "0.1"


def test_node_ids_are_unique() -> None:
    bundle = GraphBundle.from_dict(load_example_dict())
    node_ids = [node.node_id for node in bundle.nodes]
    assert len(node_ids) == len(set(node_ids))


def test_edge_ids_are_unique() -> None:
    bundle = GraphBundle.from_dict(load_example_dict())
    edge_ids = [edge.edge_id for edge in bundle.edges]
    assert len(edge_ids) == len(set(edge_ids))


def test_edge_endpoints_refer_to_bundle_nodes() -> None:
    bundle = GraphBundle.from_dict(load_example_dict())
    node_ids = {node.node_id for node in bundle.nodes}
    for edge in bundle.edges:
        assert edge.subject_id in node_ids
        assert edge.object_id in node_ids


def test_taxonomy_refs_require_nonblank_vocabulary_and_term() -> None:
    with pytest.raises(OntologyIRValidationError):
        TaxonomyRef(vocabulary="", term="candidate")
    with pytest.raises(OntologyIRValidationError):
        TaxonomyRef(vocabulary="lifecycle_state", term=" ")


def test_scalar_properties_only() -> None:
    assert validate_scalar_properties({"text": "ok", "count": 1, "flag": True, "empty": None})
    with pytest.raises(OntologyIRValidationError):
        validate_scalar_properties({"nested": {"not": "allowed"}})
    with pytest.raises(OntologyIRValidationError):
        validate_scalar_properties({"items": ["not", "allowed"]})


def test_synthetic_example_contains_no_real_campaign_names() -> None:
    example_text = EXAMPLE_BUNDLE_PATH.read_text(encoding="utf-8")
    for forbidden_term in FORBIDDEN_EXAMPLE_TERMS:
        assert forbidden_term not in example_text
