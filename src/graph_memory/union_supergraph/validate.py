from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

DEFAULT_FIXTURE_PATH = (
    Path(__file__).resolve().parents[3]
    / "tests/fixtures/graph_memory/union_supergraph/longmont_c2_minimal_graph.json"
)
KNOWN_SOURCE_DOMAINS = {
    "recap",
    "statblock",
    "worldbuilding",
    "npc_note",
    "location_note",
    "faction_note",
    "item_note",
    "session_memory",
    "manual_seed",
    "future_artifact",
}
REQUIRED_MAPS = ("nodes", "edges", "evidence", "source_artifacts", "adjacency")
UNSAFE_DIAGNOSTICS = (
    "canon_promotion",
    "approved_memory_write",
    "corpus_mutation",
    "production_retrieval",
)
LOCATOR_FIELDS = ("source_span_ref_id", "locator", "uri", "source_locator", "line_ref")


class UnionSupergraphValidationError(ValueError):
    pass


def load_fixture(path: Path = DEFAULT_FIXTURE_PATH) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _require(condition: bool, errors: list[str], message: str) -> None:
    if not condition:
        errors.append(message)


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def validate_union_supergraph_fixture(fixture: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    _require(bool(fixture.get("schema")), errors, "top-level schema is required")
    _require(bool(fixture.get("version")), errors, "top-level version is required")
    _require(bool(fixture.get("campaign_id")), errors, "top-level campaign_id is required")
    for key in REQUIRED_MAPS:
        _require(isinstance(fixture.get(key), dict), errors, f"top-level {key} must be a map")

    nodes = fixture.get("nodes") if isinstance(fixture.get("nodes"), dict) else {}
    edges = fixture.get("edges") if isinstance(fixture.get("edges"), dict) else {}
    evidence = fixture.get("evidence") if isinstance(fixture.get("evidence"), dict) else {}
    artifacts = fixture.get("source_artifacts") if isinstance(fixture.get("source_artifacts"), dict) else {}
    adjacency = fixture.get("adjacency") if isinstance(fixture.get("adjacency"), dict) else {}
    declared_domains = set(_as_list(fixture.get("source_domains")))
    for domain in declared_domains:
        _require(
            domain in KNOWN_SOURCE_DOMAINS,
            errors,
            f"top-level source_domains contains unknown source_domain {domain}",
        )
    known_domains = KNOWN_SOURCE_DOMAINS
    focus_session_id = fixture.get("focus_session_id")
    _require(bool(focus_session_id), errors, "top-level focus_session_id is required")

    for node_id, node in nodes.items():
        _require(node.get("node_id") == node_id, errors, f"node {node_id} must have matching node_id")
        for field in ("label", "kind", "role", "aliases", "source_domains", "evidence_ref_ids", "state"):
            _require(field in node, errors, f"node {node_id} missing {field}")
        for domain in _as_list(node.get("source_domains")):
            _require(domain in known_domains, errors, f"node {node_id} has unknown source_domain {domain}")
        for ref in _as_list(node.get("evidence_ref_ids")):
            _require(ref in evidence, errors, f"node {node_id} evidence_ref_id {ref} does not resolve")

    for edge_id, edge in edges.items():
        _require(edge.get("edge_id") == edge_id, errors, f"edge {edge_id} must have matching edge_id")
        for field in ("source_node_id", "target_node_id", "predicate", "label", "direction", "source_domains", "session_ids", "evidence_ref_ids", "state"):
            _require(field in edge, errors, f"edge {edge_id} missing {field}")
        _require(edge.get("source_node_id") in nodes, errors, f"edge {edge_id} source_node_id {edge.get('source_node_id')} does not resolve")
        _require(edge.get("target_node_id") in nodes, errors, f"edge {edge_id} target_node_id {edge.get('target_node_id')} does not resolve")
        for domain in _as_list(edge.get("source_domains")):
            _require(domain in known_domains, errors, f"edge {edge_id} has unknown source_domain {domain}")
        for ref in _as_list(edge.get("evidence_ref_ids")):
            _require(ref in evidence, errors, f"edge {edge_id} evidence_ref_id {ref} does not resolve")

    for ref_id, item in evidence.items():
        _require(item.get("evidence_ref_id") == ref_id, errors, f"evidence {ref_id} must have matching evidence_ref_id")
        for field in ("source_artifact_id", "source_domain", "evidence_role", "can_open_source", "can_highlight_span"):
            _require(field in item, errors, f"evidence {ref_id} missing {field}")
        _require(item.get("source_artifact_id") in artifacts, errors, f"evidence {ref_id} source_artifact_id {item.get('source_artifact_id')} does not resolve")
        _require(item.get("source_domain") in known_domains, errors, f"evidence {ref_id} has unknown source_domain {item.get('source_domain')}")
        if item.get("source_domain") == "recap" or item.get("session_id"):
            _require(bool(item.get("session_id")), errors, f"session evidence {ref_id} requires session_id")
            _require(bool(item.get("source_span_ref_id")), errors, f"session evidence {ref_id} requires source_span_ref_id")
        else:
            _require(any(item.get(field) for field in LOCATOR_FIELDS), errors, f"non-recap evidence {ref_id} requires a source locator")

    for artifact_id, artifact in artifacts.items():
        _require(artifact.get("source_artifact_id") == artifact_id, errors, f"source_artifact {artifact_id} must have matching source_artifact_id")
        for field in ("source_domain", "campaign_id", "uri"):
            _require(field in artifact, errors, f"source_artifact {artifact_id} missing {field}")
        _require(artifact.get("source_domain") in known_domains, errors, f"source_artifact {artifact_id} has unknown source_domain {artifact.get('source_domain')}")

    for node_id, items in adjacency.items():
        _require(node_id in nodes, errors, f"adjacency node {node_id} does not resolve")
        _require(isinstance(items, list), errors, f"adjacency {node_id} must be a list")
        for i, item in enumerate(_as_list(items)):
            edge_id = item.get("edge_id")
            target_id = item.get("node_id")
            _require(edge_id in edges, errors, f"adjacency {node_id}[{i}] edge_id {edge_id} does not resolve")
            _require(target_id in nodes, errors, f"adjacency {node_id}[{i}] node_id {target_id} does not resolve")
            _require("anchored_to_focus_session" in item, errors, f"adjacency {node_id}[{i}] missing anchored_to_focus_session")
            edge = edges.get(edge_id, {})
            edge_session_ids = set(_as_list(edge.get("session_ids")))
            if item.get("anchored_to_focus_session") is True:
                _require(
                    focus_session_id in edge_session_ids,
                    errors,
                    f"adjacency {node_id}[{i}] is focus-anchored but edge {edge_id} does not include focus_session_id {focus_session_id}",
                )
            if item.get("anchored_to_focus_session") is False:
                _require(
                    focus_session_id not in edge_session_ids,
                    errors,
                    f"adjacency {node_id}[{i}] is non-focus but edge {edge_id} includes focus_session_id {focus_session_id}",
                )

    _require(any(len(_as_list(node.get("source_domains"))) > 1 for node in nodes.values()), errors, "at least one node must have multiple source domains")
    _require(any(item.get("session_id") for item in evidence.values()), errors, "at least one evidence record must be session-focused")
    _require(
        any(item.get("session_id") == focus_session_id for item in evidence.values()),
        errors,
        f"at least one evidence record must match focus_session_id {focus_session_id}",
    )
    _require(
        any(focus_session_id in _as_list(edge.get("session_ids")) for edge in edges.values()),
        errors,
        f"at least one edge must include focus_session_id {focus_session_id}",
    )
    _require(
        any(item.get("source_domain") != "recap" or item.get("session_id") != focus_session_id for item in evidence.values()),
        errors,
        "at least one evidence record must be non-recap or non-focus-session",
    )
    adjacency_items = [item for items in adjacency.values() if isinstance(items, list) for item in items]
    _require(any(item.get("anchored_to_focus_session") is True for item in adjacency_items), errors, "at least one adjacency item must be focus-session anchored")
    _require(any(item.get("anchored_to_focus_session") is False for item in adjacency_items), errors, "at least one adjacency item must not be focus-session anchored")
    diagnostics = fixture.get("diagnostics")
    _require(isinstance(diagnostics, dict), errors, "diagnostics must be a map")
    if isinstance(diagnostics, dict):
        for flag in UNSAFE_DIAGNOSTICS:
            _require(diagnostics.get(flag) is False, errors, f"diagnostics.{flag} must be false")

    if errors:
        raise UnionSupergraphValidationError("Union supergraph fixture validation failed:\n- " + "\n- ".join(errors))

    focus_session_ids = sorted({item.get("session_id") for item in evidence.values() if item.get("session_id")})
    return {
        "valid": True,
        "schema": fixture.get("schema"),
        "campaign_id": fixture.get("campaign_id"),
        "node_count": len(nodes),
        "edge_count": len(edges),
        "evidence_count": len(evidence),
        "source_artifact_count": len(artifacts),
        "multi_domain_node_count": sum(1 for node in nodes.values() if len(_as_list(node.get("source_domains"))) > 1),
        "focus_session_ids": focus_session_ids,
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("fixture", nargs="?", default=str(DEFAULT_FIXTURE_PATH))
    args = ap.parse_args()
    result = validate_union_supergraph_fixture(load_fixture(Path(args.fixture)))
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
