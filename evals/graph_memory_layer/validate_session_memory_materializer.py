from __future__ import annotations

import sys
from pathlib import Path

from src.graph_memory.session_memory_materialize import (
    ADMITTED_SOURCE_FAMILY,
    load_session_memory_jsonl,
    materialize_validate_and_report_session_memory,
    session_memory_coverage,
    validate_session_memory_gate,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURE_PATH = REPO_ROOT / "evals" / "graph_memory_layer" / "examples" / "session_memory_sentence_units_minimal.jsonl"
TAXONOMY_REGISTRY_PATH = REPO_ROOT / "evals" / "graph_memory_layer" / "taxonomy_registry.json"
GATE_MANIFEST_PATH = REPO_ROOT / "evals" / "graph_memory_layer" / "real_structure_materialization_gate.json"
BLOCKING_SEVERITIES = {"error", "fatal"}


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> int:
    print("Graph Memory session-memory sentence-unit materializer validation")
    manifest = validate_session_memory_gate(GATE_MANIFEST_PATH)
    _require(manifest["gate_decision"]["admitted_source_family"] == ADMITTED_SOURCE_FAMILY, "wrong admitted source family")
    print("- real-structure gate: ready")
    _require(TAXONOMY_REGISTRY_PATH.is_file(), "taxonomy registry missing")
    print("- taxonomy registry: found")
    _require(FIXTURE_PATH.is_file(), "session-memory fixture missing")
    print("- session-memory fixture: found")
    records = load_session_memory_jsonl(FIXTURE_PATH)
    _require(len(records) == 2, "fixture must load exactly two records")
    print("- records loaded: 2")
    bundle, report, _summaries, issues = materialize_validate_and_report_session_memory(
        FIXTURE_PATH,
        TAXONOMY_REGISTRY_PATH,
        gate_manifest_path=GATE_MANIFEST_PATH,
    )
    print("- graph bundle: materialized")
    _require(len(bundle.nodes) == 3, "expected 3 nodes")
    _require(len(bundle.edges) == 2, "expected 2 edges")
    print("- nodes: 3")
    print("- edges: 2")
    _require(sum(1 for node in bundle.nodes if node.kind.term == "source_document") == 1, "expected one source document")
    _require(sum(1 for node in bundle.nodes if node.kind.term == "source_unit") == 2, "expected two source units")
    _require(all(edge.predicate_family.term == "source_derivation" for edge in bundle.edges), "expected only source_derivation edges")
    _require(all(record.lifecycle_state and record.lifecycle_state.term == "candidate" for record in [*bundle.nodes, *bundle.edges]), "all records must be candidate")
    _require(all(record.visibility_state and record.visibility_state.term == "internal_diagnostic" for record in [*bundle.nodes, *bundle.edges]), "all records must be internal diagnostic")
    _require(all(record.provenance for record in [*bundle.nodes, *bundle.edges]), "provenance missing")
    print("- provenance refs: present")
    _require(all(any(prov.source_refs for prov in record.provenance) for record in [*bundle.nodes, *bundle.edges]), "source refs missing")
    print("- source refs: present")
    forbidden_node_kinds = {"route", "alias"}
    _require(not any(node.kind.term in forbidden_node_kinds for node in bundle.nodes), "forbidden route/alias node emitted")
    _require(not any(edge.predicate_family.term != "source_derivation" for edge in bundle.edges), "forbidden edge emitted")
    _require(not any(issue.severity in BLOCKING_SEVERITIES for issue in issues), "blocking validation issues found")
    print("- validation issues: no blocking issues")
    coverage = session_memory_coverage(records)
    _require(coverage.total_route_mentions == 1 and report.node_count == 3, "route coverage/report count missing")
    print("- session-memory materializer: ready")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (AssertionError, ValueError) as exc:
        print(f"- session-memory materializer: blocked ({exc})")
        sys.exit(1)
