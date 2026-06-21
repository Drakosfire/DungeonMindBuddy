from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from src.graph_memory.ontology_ir import GraphBundle
from src.graph_memory.session_memory_materialize import (
    CREATED_BY,
    SCHEMA_VERSION,
    TAXONOMY_REGISTRY_VERSION,
    load_session_memory_jsonl,
    materialize_session_memory_jsonl,
    materialize_session_memory_records,
    materialize_validate_and_report_session_memory,
    session_memory_coverage,
)
from src.graph_memory.validation_rules import load_taxonomy_registry, validate_bundle_against_taxonomy

REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_PATH = REPO_ROOT / "evals" / "graph_memory_layer" / "examples" / "session_memory_sentence_units_minimal.jsonl"
TAXONOMY_REGISTRY_PATH = REPO_ROOT / "evals" / "graph_memory_layer" / "taxonomy_registry.json"
GATE_MANIFEST_PATH = REPO_ROOT / "evals" / "graph_memory_layer" / "real_structure_materialization_gate.json"
SOURCE_PATH = REPO_ROOT / "src" / "graph_memory" / "session_memory_materialize.py"

REAL_CAMPAIGN_TERMS = {
    "Mirathorn", "Bonogo", "Baergrom", "Ephanna", "Caelynn", "Stafl", "Karsemine", "Draven",
    "Stonebridge", "Stone Bridge", "Rivers Edge", "River's Edge", "Mireward", "Hester", "Glowkindle", "Grishna",
}
FORBIDDEN_IMPORT_SNIPPETS = {
    "src.agent.session_memory_query", "src.agent.planner_retrieval_router", "src.live_play.manifest_context_query",
    "src.session_memory.capture", "src.session_memory.breadcrumb_normalize", "src.corpus.session_recap_paths",
    "scripts.materialize_session_memory", "openai", "anthropic",
}


def _bundle() -> GraphBundle:
    return materialize_session_memory_records(load_session_memory_jsonl(FIXTURE_PATH))


def test_synthetic_fixture_exists_has_two_records_and_no_real_campaign_names() -> None:
    assert FIXTURE_PATH.is_file()
    text = FIXTURE_PATH.read_text(encoding="utf-8")
    assert len([line for line in text.splitlines() if line.strip()]) == 2
    for term in REAL_CAMPAIGN_TERMS:
        assert term not in text


def test_loader_parses_records_and_limit() -> None:
    records = load_session_memory_jsonl(FIXTURE_PATH)
    assert len(records) == 2
    assert records[0].campaign_id == "synthetic-campaign"
    assert records[0].routes[0].normalized_route == "Synthetic Campaign/Locations/synthetic_place/"
    assert len(load_session_memory_jsonl(FIXTURE_PATH, limit=1)) == 1


def test_loader_rejects_malformed_jsonl(tmp_path: Path) -> None:
    path = tmp_path / "bad.jsonl"
    path.write_text("{not json}\n", encoding="utf-8")
    with pytest.raises(ValueError, match="malformed JSONL"):
        load_session_memory_jsonl(path)


def test_loader_rejects_wrong_schema(tmp_path: Path) -> None:
    path = tmp_path / "wrong.jsonl"
    path.write_text('{"schema":"wrong","campaign_id":"synthetic","session_number":0,"source_recap_path":"x.md","unit_id":"u1","line_start":1,"line_end":1,"lexical_plain":"text"}\n', encoding="utf-8")
    with pytest.raises(ValueError, match="unsupported schema"):
        load_session_memory_jsonl(path)


def test_materializer_returns_expected_graph_bundle_shape() -> None:
    bundle = _bundle()
    assert isinstance(bundle, GraphBundle)
    assert bundle.schema_version == SCHEMA_VERSION
    assert bundle.taxonomy_registry_version == TAXONOMY_REGISTRY_VERSION
    assert bundle.created_by == CREATED_BY
    assert len(bundle.nodes) == 3
    assert len(bundle.edges) == 2
    assert sum(1 for node in bundle.nodes if node.kind.term == "source_document") == 1
    assert sum(1 for node in bundle.nodes if node.kind.term == "source_unit") == 2
    node_ids = {node.node_id for node in bundle.nodes}
    assert all(edge.subject_id in node_ids and edge.object_id in node_ids for edge in bundle.edges)
    assert all(edge.predicate_family.term == "source_derivation" for edge in bundle.edges)


def test_materialized_records_are_candidate_internal_diagnostic_with_provenance_and_sources() -> None:
    bundle = _bundle()
    for record in [*bundle.nodes, *bundle.edges]:
        assert record.lifecycle_state and record.lifecycle_state.term == "candidate"
        assert record.visibility_state and record.visibility_state.term == "internal_diagnostic"
        assert record.provenance
        for provenance in record.provenance:
            assert provenance.evidence_role.term == "diagnostic_only"
            assert provenance.authority_state.term == "system_derived"
            assert provenance.source_refs
    assert not any(node.lifecycle_state and node.lifecycle_state.term == "promoted" for node in bundle.nodes)
    assert not any(edge.lifecycle_state and edge.lifecycle_state.term == "promoted" for edge in bundle.edges)


def test_no_entity_alias_route_or_inferred_relationship_records_emitted() -> None:
    bundle = _bundle()
    assert {node.kind.term for node in bundle.nodes} == {"source_document", "source_unit"}
    assert {edge.predicate_family.term for edge in bundle.edges} == {"source_derivation"}
    assert all(not node.aliases for node in bundle.nodes)


def test_validation_rules_pass_with_no_blocking_issues() -> None:
    bundle = _bundle()
    result = validate_bundle_against_taxonomy(bundle, load_taxonomy_registry(TAXONOMY_REGISTRY_PATH))
    assert not [issue for issue in result.issues if issue.severity in {"error", "fatal"}]


def test_validate_and_report_includes_route_coverage_counts() -> None:
    bundle, report, records, issues = materialize_validate_and_report_session_memory(FIXTURE_PATH, TAXONOMY_REGISTRY_PATH, gate_manifest_path=GATE_MANIFEST_PATH)
    coverage = session_memory_coverage(load_session_memory_jsonl(FIXTURE_PATH))
    assert bundle is not None and records
    assert report.node_count == 3
    assert coverage.input_record_count == 2
    assert coverage.records_with_routes == 1
    assert coverage.total_route_mentions == 1
    assert coverage.proposed_route_mentions == 1
    assert not [issue for issue in issues if issue.severity in {"error", "fatal"}]


def test_report_cli_exits_zero() -> None:
    result = subprocess.run([sys.executable, "-m", "evals.graph_memory_layer.report_session_memory_materializer"], cwd=REPO_ROOT, check=False, text=True, capture_output=True)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "## Session-Memory Coverage" in result.stdout
    assert "| Total route mentions | 1 |" in result.stdout


def test_validator_cli_exits_zero() -> None:
    result = subprocess.run([sys.executable, "-m", "evals.graph_memory_layer.validate_session_memory_materializer"], cwd=REPO_ROOT, check=False, text=True, capture_output=True)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "- session-memory materializer: ready" in result.stdout


def test_explicit_temporary_jsonl_path_can_be_materialized(tmp_path: Path) -> None:
    path = tmp_path / "explicit.jsonl"
    path.write_text(FIXTURE_PATH.read_text(encoding="utf-8"), encoding="utf-8")
    assert len(materialize_session_memory_jsonl(path).nodes) == 3


def test_materializer_source_does_not_import_forbidden_modules() -> None:
    source = SOURCE_PATH.read_text(encoding="utf-8")
    for snippet in FORBIDDEN_IMPORT_SNIPPETS:
        assert snippet not in source
