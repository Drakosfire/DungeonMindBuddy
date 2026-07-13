from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from graph_memory.evidence.assertion_support import DurableAssertionSupport
from graph_memory.evidence.source_domain import KNOWN_SOURCE_DOMAINS
from graph_memory.union_supergraph.load import (
    DEFAULT_FIXTURE_PATH,
    load_union_supergraph_payload,
    parse_union_supergraph_store,
)
from graph_memory.union_supergraph.redirects import (
    identity_redirect_dicts_from_fixture,
    validate_identity_redirects,
)

REQUIRED_MAPS = (
    "nodes",
    "edges",
    "evidence",
    "source_artifacts",
    "adjacency",
)
OPTIONAL_EMPTY_MAPS = ("aliases", "assertion_support")
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
    return load_union_supergraph_payload(path)


def _require(condition: bool, errors: list[str], message: str) -> None:
    if not condition:
        errors.append(message)


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _raise_if_errors(errors: list[str], *, label: str) -> None:
    if errors:
        raise UnionSupergraphValidationError(
            f"{label}:\n- " + "\n- ".join(errors)
        )


def _structural_report(fixture: dict[str, Any]) -> dict[str, Any]:
    nodes = fixture.get("nodes") if isinstance(fixture.get("nodes"), dict) else {}
    edges = fixture.get("edges") if isinstance(fixture.get("edges"), dict) else {}
    evidence = (
        fixture.get("evidence") if isinstance(fixture.get("evidence"), dict) else {}
    )
    artifacts = (
        fixture.get("source_artifacts")
        if isinstance(fixture.get("source_artifacts"), dict)
        else {}
    )
    focus_session_ids = sorted(
        {item.get("session_id") for item in evidence.values() if item.get("session_id")}
    )
    return {
        "valid": True,
        "schema": fixture.get("schema"),
        "campaign_id": fixture.get("campaign_id"),
        "node_count": len(nodes),
        "edge_count": len(edges),
        "evidence_count": len(evidence),
        "source_artifact_count": len(artifacts),
        "multi_domain_node_count": sum(
            1
            for node in nodes.values()
            if len(_as_list(node.get("source_domains"))) > 1
        ),
        "focus_session_ids": focus_session_ids,
    }


def validate_union_supergraph_store_payload(fixture: dict[str, Any]) -> dict[str, Any]:
    """Validate structural coherence of a World Supergraph store payload.

    Permits an empty technical baseline (no nodes/edges/evidence). Does not
    require representative multi-source / focus-session fixture richness.
    """
    errors: list[str] = []
    _require(bool(fixture.get("schema")), errors, "top-level schema is required")
    _require(bool(fixture.get("version")), errors, "top-level version is required")
    _require(
        bool(fixture.get("campaign_id")), errors, "top-level campaign_id is required"
    )
    for key in REQUIRED_MAPS:
        _require(
            isinstance(fixture.get(key), dict), errors, f"top-level {key} must be a map"
        )
    for key in OPTIONAL_EMPTY_MAPS:
        value = fixture.get(key)
        if value is not None:
            _require(
                isinstance(value, dict),
                errors,
                f"top-level {key} must be a map",
            )

    nodes = fixture.get("nodes") if isinstance(fixture.get("nodes"), dict) else {}
    edges = fixture.get("edges") if isinstance(fixture.get("edges"), dict) else {}
    evidence = (
        fixture.get("evidence") if isinstance(fixture.get("evidence"), dict) else {}
    )
    artifacts = (
        fixture.get("source_artifacts")
        if isinstance(fixture.get("source_artifacts"), dict)
        else {}
    )
    aliases = fixture.get("aliases") if isinstance(fixture.get("aliases"), dict) else {}
    assertion_support = (
        fixture.get("assertion_support")
        if isinstance(fixture.get("assertion_support"), dict)
        else {}
    )
    adjacency = (
        fixture.get("adjacency") if isinstance(fixture.get("adjacency"), dict) else {}
    )
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
        _require(
            isinstance(node, dict),
            errors,
            f"node {node_id} must be an object",
        )
        if not isinstance(node, dict):
            continue
        _require(
            node.get("node_id") == node_id,
            errors,
            f"node {node_id} must have matching node_id",
        )
        for field in (
            "label",
            "kind",
            "role",
            "aliases",
            "source_domains",
            "evidence_ref_ids",
            "state",
        ):
            _require(field in node, errors, f"node {node_id} missing {field}")
        for domain in _as_list(node.get("source_domains")):
            _require(
                domain in known_domains,
                errors,
                f"node {node_id} has unknown source_domain {domain}",
            )
        for ref in _as_list(node.get("evidence_ref_ids")):
            _require(
                ref in evidence,
                errors,
                f"node {node_id} evidence_ref_id {ref} does not resolve",
            )

    for edge_id, edge in edges.items():
        _require(
            isinstance(edge, dict),
            errors,
            f"edge {edge_id} must be an object",
        )
        if not isinstance(edge, dict):
            continue
        _require(
            edge.get("edge_id") == edge_id,
            errors,
            f"edge {edge_id} must have matching edge_id",
        )
        for field in (
            "source_node_id",
            "target_node_id",
            "predicate",
            "label",
            "direction",
            "source_domains",
            "session_ids",
            "evidence_ref_ids",
            "state",
        ):
            _require(field in edge, errors, f"edge {edge_id} missing {field}")
        _require(
            edge.get("source_node_id") in nodes,
            errors,
            f"edge {edge_id} source_node_id {edge.get('source_node_id')} does not resolve",
        )
        _require(
            edge.get("target_node_id") in nodes,
            errors,
            f"edge {edge_id} target_node_id {edge.get('target_node_id')} does not resolve",
        )
        for domain in _as_list(edge.get("source_domains")):
            _require(
                domain in known_domains,
                errors,
                f"edge {edge_id} has unknown source_domain {domain}",
            )
        for ref in _as_list(edge.get("evidence_ref_ids")):
            _require(
                ref in evidence,
                errors,
                f"edge {edge_id} evidence_ref_id {ref} does not resolve",
            )

    for ref_id, item in evidence.items():
        _require(
            isinstance(item, dict),
            errors,
            f"evidence {ref_id} must be an object",
        )
        if not isinstance(item, dict):
            continue
        _require(
            item.get("evidence_ref_id") == ref_id,
            errors,
            f"evidence {ref_id} must have matching evidence_ref_id",
        )
        for field in (
            "source_artifact_id",
            "source_domain",
            "evidence_role",
            "can_open_source",
            "can_highlight_span",
        ):
            _require(field in item, errors, f"evidence {ref_id} missing {field}")
        _require(
            item.get("source_artifact_id") in artifacts,
            errors,
            f"evidence {ref_id} source_artifact_id {item.get('source_artifact_id')} does not resolve",
        )
        _require(
            item.get("source_domain") in known_domains,
            errors,
            f"evidence {ref_id} has unknown source_domain {item.get('source_domain')}",
        )
        if item.get("source_domain") == "recap" or item.get("session_id"):
            _require(
                bool(item.get("session_id")),
                errors,
                f"session evidence {ref_id} requires session_id",
            )
            _require(
                bool(item.get("source_span_ref_id")),
                errors,
                f"session evidence {ref_id} requires source_span_ref_id",
            )
        else:
            _require(
                any(item.get(field) for field in LOCATOR_FIELDS),
                errors,
                f"non-recap evidence {ref_id} requires a source locator",
            )

    for artifact_id, artifact in artifacts.items():
        _require(
            isinstance(artifact, dict),
            errors,
            f"source_artifact {artifact_id} must be an object",
        )
        if not isinstance(artifact, dict):
            continue
        _require(
            artifact.get("source_artifact_id") == artifact_id,
            errors,
            f"source_artifact {artifact_id} must have matching source_artifact_id",
        )
        for field in ("source_domain", "campaign_id", "uri"):
            _require(
                field in artifact,
                errors,
                f"source_artifact {artifact_id} missing {field}",
            )
        _require(
            artifact.get("source_domain") in known_domains,
            errors,
            f"source_artifact {artifact_id} has unknown source_domain {artifact.get('source_domain')}",
        )

    for alias, node_id in aliases.items():
        _require(
            isinstance(alias, str) and alias.strip(),
            errors,
            f"alias key {alias!r} must be a non-empty string",
        )
        _require(
            node_id in nodes,
            errors,
            f"alias {alias!r} points to missing node {node_id!r}",
        )

    for support_id, support in assertion_support.items():
        _require(
            isinstance(support, dict),
            errors,
            f"assertion_support {support_id} must be an object",
        )
        if not isinstance(support, dict):
            continue
        try:
            typed = DurableAssertionSupport.model_validate(support)
        except ValidationError as exc:
            errors.append(f"assertion_support {support_id} is invalid: {exc}")
            continue
        _require(
            typed.assertion_id == support_id,
            errors,
            f"assertion_support key {support_id} must equal assertion_id "
            f"{typed.assertion_id!r}",
        )
        for evidence_id in typed.evidence_ref_ids:
            _require(
                evidence_id in evidence,
                errors,
                f"assertion_support {support_id} evidence_ref_id "
                f"{evidence_id!r} does not resolve",
            )
        for artifact_id in typed.source_artifact_ids:
            _require(
                artifact_id in artifacts,
                errors,
                f"assertion_support {support_id} source_artifact_id "
                f"{artifact_id!r} does not resolve",
            )
        active_contribution_ids = set(typed.active_contribution_ids)
        _require(
            set(typed.per_contribution_evidence_ref_ids) == active_contribution_ids,
            errors,
            f"assertion_support {support_id} evidence lineage keys must "
            "exactly match active_contribution_ids",
        )
        _require(
            set(typed.per_contribution_source_artifact_ids)
            == active_contribution_ids,
            errors,
            f"assertion_support {support_id} source-artifact lineage keys "
            "must exactly match active_contribution_ids",
        )
        for contribution_id, evidence_ids in typed.per_contribution_evidence_ref_ids.items():
            _require(
                isinstance(contribution_id, str) and contribution_id.strip(),
                errors,
                f"assertion_support {support_id} has empty evidence lineage contribution id",
            )
            for evidence_id in evidence_ids:
                _require(
                    evidence_id in evidence,
                    errors,
                    f"assertion_support {support_id} contribution {contribution_id!r} "
                    f"evidence_ref_id {evidence_id!r} does not resolve",
                )
        for contribution_id, artifact_ids in typed.per_contribution_source_artifact_ids.items():
            _require(
                isinstance(contribution_id, str) and contribution_id.strip(),
                errors,
                f"assertion_support {support_id} has empty source lineage contribution id",
            )
            for artifact_id in artifact_ids:
                _require(
                    artifact_id in artifacts,
                    errors,
                    f"assertion_support {support_id} contribution {contribution_id!r} "
                    f"source_artifact_id {artifact_id!r} does not resolve",
                )
        if typed.graph_object_id is not None:
            _require(
                typed.graph_object_id in nodes or typed.graph_object_id in edges,
                errors,
                f"assertion_support {support_id} graph_object_id "
                f"{typed.graph_object_id!r} does not resolve",
            )
        for contribution_id in (
            *typed.active_contribution_ids,
            *typed.superseded_contribution_ids,
            *typed.retracted_contribution_ids,
            *(
                [typed.introduced_by_contribution_id]
                if typed.introduced_by_contribution_id
                else []
            ),
        ):
            _require(
                isinstance(contribution_id, str) and contribution_id.strip(),
                errors,
                f"assertion_support {support_id} has empty contribution id",
            )

    for node_id, items in adjacency.items():
        _require(node_id in nodes, errors, f"adjacency node {node_id} does not resolve")
        _require(isinstance(items, list), errors, f"adjacency {node_id} must be a list")
        for i, item in enumerate(_as_list(items)):
            _require(
                isinstance(item, dict),
                errors,
                f"adjacency {node_id}[{i}] must be an object",
            )
            if not isinstance(item, dict):
                continue
            edge_id = item.get("edge_id")
            target_id = item.get("node_id")
            _require(
                edge_id in edges,
                errors,
                f"adjacency {node_id}[{i}] edge_id {edge_id} does not resolve",
            )
            _require(
                target_id in nodes,
                errors,
                f"adjacency {node_id}[{i}] node_id {target_id} does not resolve",
            )
            _require(
                "anchored_to_focus_session" in item,
                errors,
                f"adjacency {node_id}[{i}] missing anchored_to_focus_session",
            )
            edge = edges.get(edge_id, {}) if isinstance(edges.get(edge_id), dict) else {}
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

    diagnostics = fixture.get("diagnostics")
    _require(isinstance(diagnostics, dict), errors, "diagnostics must be a map")
    if isinstance(diagnostics, dict):
        for flag in UNSAFE_DIAGNOSTICS:
            _require(
                diagnostics.get(flag) is False,
                errors,
                f"diagnostics.{flag} must be false",
            )

    redirect_payloads = identity_redirect_dicts_from_fixture(fixture)
    if redirect_payloads:
        try:
            store = parse_union_supergraph_store(fixture)
        except Exception as exc:  # pragma: no cover - parse errors surface elsewhere
            errors.append(f"identity_redirects present but store parse failed: {exc}")
        else:
            for message in validate_identity_redirects(store.identity_redirects):
                errors.append(message)

    _raise_if_errors(errors, label="Union supergraph store validation failed")
    return _structural_report(fixture)


def validate_union_supergraph_fixture(fixture: dict[str, Any]) -> dict[str, Any]:
    """Structural validation plus representative-fixture acceptance requirements."""
    report = validate_union_supergraph_store_payload(fixture)
    errors: list[str] = []

    nodes = fixture.get("nodes") if isinstance(fixture.get("nodes"), dict) else {}
    edges = fixture.get("edges") if isinstance(fixture.get("edges"), dict) else {}
    evidence = (
        fixture.get("evidence") if isinstance(fixture.get("evidence"), dict) else {}
    )
    adjacency = (
        fixture.get("adjacency") if isinstance(fixture.get("adjacency"), dict) else {}
    )
    focus_session_id = fixture.get("focus_session_id")

    _require(
        any(len(_as_list(node.get("source_domains"))) > 1 for node in nodes.values()),
        errors,
        "at least one node must have multiple source domains",
    )
    _require(
        any(item.get("session_id") for item in evidence.values()),
        errors,
        "at least one evidence record must be session-focused",
    )
    _require(
        any(item.get("session_id") == focus_session_id for item in evidence.values()),
        errors,
        f"at least one evidence record must match focus_session_id {focus_session_id}",
    )
    _require(
        any(
            focus_session_id in _as_list(edge.get("session_ids"))
            for edge in edges.values()
        ),
        errors,
        f"at least one edge must include focus_session_id {focus_session_id}",
    )
    _require(
        any(
            item.get("source_domain") != "recap"
            or item.get("session_id") != focus_session_id
            for item in evidence.values()
        ),
        errors,
        "at least one evidence record must be non-recap or non-focus-session",
    )
    adjacency_items = [
        item
        for items in adjacency.values()
        if isinstance(items, list)
        for item in items
    ]
    _require(
        any(item.get("anchored_to_focus_session") is True for item in adjacency_items),
        errors,
        "at least one adjacency item must be focus-session anchored",
    )
    _require(
        any(item.get("anchored_to_focus_session") is False for item in adjacency_items),
        errors,
        "at least one adjacency item must not be focus-session anchored",
    )

    _raise_if_errors(errors, label="Union supergraph fixture validation failed")
    return report


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("fixture", nargs="?", default=str(DEFAULT_FIXTURE_PATH))
    args = ap.parse_args()
    result = validate_union_supergraph_fixture(load_fixture(Path(args.fixture)))
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
