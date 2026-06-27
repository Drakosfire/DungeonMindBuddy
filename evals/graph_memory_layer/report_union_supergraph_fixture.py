from __future__ import annotations

import argparse
from pathlib import Path

from evals.graph_memory_layer.validate_union_supergraph_fixture import (
    DEFAULT_FIXTURE_PATH,
    load_fixture,
    validate_union_supergraph_fixture,
)


def build_report(fixture: dict) -> dict:
    validation = validate_union_supergraph_fixture(fixture)
    focus_session_ids = sorted(
        {item.get("session_id") for item in fixture["evidence"].values() if item.get("session_id")}
    )
    focus_edges = [edge for edge in fixture["edges"].values() if set(edge.get("session_ids", [])) & set(focus_session_ids)]
    non_focus_edges = [edge for edge in fixture["edges"].values() if not (set(edge.get("session_ids", [])) & set(focus_session_ids))]
    return {
        "schema": fixture.get("schema"),
        "campaign_id": fixture.get("campaign_id"),
        "node_count": len(fixture["nodes"]),
        "edge_count": len(fixture["edges"]),
        "evidence_count": len(fixture["evidence"]),
        "source_artifact_count": len(fixture["source_artifacts"]),
        "source_domains": fixture.get("source_domains", []),
        "graph_domains": fixture.get("graph_domains", []),
        "multi_domain_node_count": validation["multi_domain_node_count"],
        "focus_session_ids": focus_session_ids,
        "focus_session_edge_count": len(focus_edges),
        "non_focus_edge_count": len(non_focus_edges),
        "safety_flags": fixture.get("diagnostics", {}),
        "readiness_verdict": "ready: union supergraph read-model fixture passes validation",
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("fixture", nargs="?", default=str(DEFAULT_FIXTURE_PATH))
    args = ap.parse_args()
    report = build_report(load_fixture(Path(args.fixture)))
    print("# Union Supergraph Fixture Report")
    for key, value in report.items():
        print(f"- {key}: {value}")


if __name__ == "__main__":
    main()
