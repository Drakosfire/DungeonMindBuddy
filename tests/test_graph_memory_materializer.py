from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from src.graph_memory.materialize import materialize_fixture_file
from src.graph_memory.ontology_ir import GraphBundle
from src.graph_memory.validation_rules import load_taxonomy_registry, validate_bundle_against_taxonomy

REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_PATH = REPO_ROOT / "evals" / "graph_memory_layer" / "examples" / "materializer_input_minimal.json"
TAXONOMY_REGISTRY_PATH = REPO_ROOT / "evals" / "graph_memory_layer" / "taxonomy_registry.json"
MATERIALIZER_SOURCE_PATH = REPO_ROOT / "src" / "graph_memory" / "materialize.py"

REAL_CAMPAIGN_TERMS = {
    "Mirathorn", "Bonogo", "Baergrom", "Ephanna", "Caelynn", "Stafl",
    "Karsemine", "Draven", "Stonebridge", "Rivers Edge", "Mireward", "Hester",
}
FORBIDDEN_IMPORT_SNIPPETS = {
    "src.agent.session_memory_query",
    "src.agent.planner_retrieval_router",
    "src.live_play.manifest_context_query",
    "src.session_memory.capture",
    "src.session_memory.breadcrumb_normalize",
    "openai",
    "anthropic",
}


def bundle() -> GraphBundle:
    return materialize_fixture_file(FIXTURE_PATH)


def test_materializer_input_fixture_exists() -> None:
    assert FIXTURE_PATH.is_file()
    with FIXTURE_PATH.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    assert "source_documents" in data
    assert "nodes" not in data
    assert "edges" not in data


def test_materializer_cli_exits_zero() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "evals.graph_memory_layer.validate_materializer"],
        cwd=REPO_ROOT,
        check=False,
        text=True,
        capture_output=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "- materializer: ready" in result.stdout


def test_materializer_returns_graph_bundle_with_expected_versions() -> None:
    materialized = bundle()
    assert isinstance(materialized, GraphBundle)
    assert materialized.schema_version == "0.1"
    assert materialized.taxonomy_registry_version == "0.1"


def test_expected_nodes_and_edge_exist_with_valid_endpoints() -> None:
    materialized = bundle()
    node_ids = {node.node_id for node in materialized.nodes}
    edge_ids = {edge.edge_id for edge in materialized.edges}
    assert "example:source:document:alpha" in node_ids
    assert "example:source-unit:alpha-1" in node_ids
    assert "example:relationship:document-contains-unit" in edge_ids
    for edge in materialized.edges:
        assert edge.subject_id in node_ids
        assert edge.object_id in node_ids


def test_validation_rules_pass_without_error_or_fatal() -> None:
    result = validate_bundle_against_taxonomy(bundle(), load_taxonomy_registry(TAXONOMY_REGISTRY_PATH))
    assert not [issue for issue in result.issues if issue.severity in {"error", "fatal"}]


def test_materialized_provenance_is_diagnostic_and_records_are_not_promoted() -> None:
    materialized = bundle()
    for record in [*materialized.nodes, *materialized.edges]:
        assert record.lifecycle_state is not None
        assert record.lifecycle_state.term == "candidate"
        assert record.provenance
        for provenance in record.provenance:
            assert provenance.evidence_role.term == "diagnostic_only"
            assert provenance.visibility_state is not None
            assert provenance.visibility_state.term == "internal_diagnostic"
            assert provenance.source_refs


def test_materialized_example_contains_no_real_campaign_names() -> None:
    text = FIXTURE_PATH.read_text(encoding="utf-8")
    for term in REAL_CAMPAIGN_TERMS:
        assert term not in text


def test_materializer_does_not_import_production_retrieval_or_llm_modules() -> None:
    source = MATERIALIZER_SOURCE_PATH.read_text(encoding="utf-8")
    for snippet in FORBIDDEN_IMPORT_SNIPPETS:
        assert snippet not in source
