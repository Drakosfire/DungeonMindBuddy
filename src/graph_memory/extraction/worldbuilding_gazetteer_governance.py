"""Add an explicit, source-backed city governance edge when endpoints are certain."""

from __future__ import annotations

import re
from copy import deepcopy
from dataclasses import replace
from typing import Any

from .extraction_profile import register_extraction_profile
from .worldbuilding_gazetteer_role_citations import _affirmed_role_occurrence
from .worldbuilding_gazetteer_scenario_scope import (
    GAZETTEER_PREPARED_SCENARIO_PROFILE,
    _heading,
    _ordered_rows,
    compile_gazetteer_scenario_scope,
)


PROFILE_VERSION = "1.9"
PROFILE = f"worldbuilding_gazetteer_v1@{PROFILE_VERSION}"
_CITY_GOVERNANCE = re.compile(
    r"\bcity[\s-]+state\s+(?:is\s+)?governed\s+by\s+(?:a|the)\s+council\b",
    re.IGNORECASE,
)
_CITY_TITLE = re.compile(r"^(?:the\s+)?city\s+of\s+(.+)$", re.IGNORECASE)


def _normalized_label(value: Any) -> str:
    return re.sub(r"[^a-z0-9]+", " ", str(value or "").casefold()).strip()


def _physical_source_lines(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Expand indexed spans to physical lines without losing their source IDs."""
    physical = []
    for row in _ordered_rows(rows):
        start = row["line_start"]
        end = row["line_end"]
        lines = row["text"].splitlines()
        if len(lines) != end - start + 1:
            raise ValueError("source span text does not match its physical line range")
        for offset, text in enumerate(lines):
            physical.append({
                **row,
                "line_start": start + offset,
                "line_end": start + offset,
                "text": text,
            })
    return physical


def _document_city_title(
    rows: list[dict[str, Any]],
) -> tuple[str, dict[str, Any]] | None:
    lines = _physical_source_lines(rows)
    frontmatter_titles = []
    frontmatter_open = bool(
        lines and lines[0].get("line_start") == 1 and lines[0]["text"].strip() == "---"
    )
    if frontmatter_open:
        frontmatter_closed = False
        for row in lines[1:]:
            text = row["text"].strip()
            if text == "---":
                frontmatter_closed = True
                break
            match = re.fullmatch(r"title\s*:\s*(.*?)\s*", text, re.IGNORECASE)
            if match:
                value = match.group(1).strip()
                if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
                    value = value[1:-1]
                frontmatter_titles.append((value, row))
        if not frontmatter_closed:
            return None
        if len(frontmatter_titles) == 1:
            title, row = frontmatter_titles[0]
            title_match = _CITY_TITLE.fullmatch(title.strip())
            return (title_match.group(1).strip(), row) if title_match else None
        if len(frontmatter_titles) > 1:
            return None

    titles = []
    for row in lines:
        heading = _heading(row["text"])
        if heading is None or heading[0] != 1:
            continue
        match = _CITY_TITLE.fullmatch(heading[1].rstrip(":").strip())
        if match:
            titles.append((match.group(1).strip(), row))
    return titles[0] if len(titles) == 1 else None


def _affirmed_city_governance(text: str) -> bool:
    # Preserve shared and introductory qualifiers using the reviewed claim rules.
    return any(
        _affirmed_role_occurrence(text, match.group(0))
        for match in _CITY_GOVERNANCE.finditer(text)
    )


def _governance_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    lines = _physical_source_lines(rows)
    in_governance = False
    governance_level: int | None = None
    matches = []
    for row in lines:
        heading = _heading(row["text"])
        if heading is not None:
            level, title = heading
            normalized_title = title.rstrip(":").strip().casefold()
            if in_governance and governance_level is not None and level <= governance_level:
                in_governance = False
                governance_level = None
            if normalized_title == "governance" and level >= 2:
                in_governance = True
                governance_level = level
            continue
        if in_governance and _affirmed_city_governance(row["text"]):
            matches.append(row)
    return matches


def _matching_city_nodes(nodes: list[dict[str, Any]], city_name: str) -> list[dict[str, Any]]:
    target = _normalized_label(city_name)
    return [
        node for node in nodes
        if node.get("node_type") == "location"
        and _normalized_label(node.get("label")) in {
            target,
            f"city of {target}",
            f"the city of {target}",
        }
    ]


def _matching_council_nodes(
    nodes: list[dict[str, Any]], city_name: str,
) -> list[dict[str, Any]]:
    city = _normalized_label(city_name)
    accepted_labels = {
        f"{city} city council",
        f"city council of {city}",
        f"{city} council",
        f"council of {city}",
    }
    return [
        node for node in nodes
        if node.get("node_type") in {"organization", "faction"}
        and _normalized_label(node.get("label")) in accepted_labels
    ]


def _openable_source_evidence(
    node: dict[str, Any], *, span_ref: str, source_text: str,
) -> dict[str, Any] | None:
    refs = node.get("evidence_refs")
    if not isinstance(refs, list):
        return None
    for ref in refs:
        if not isinstance(ref, dict) or ref.get("source_span_ref_id") != span_ref:
            continue
        quotes = ref.get("anchor_quotes")
        if (
            isinstance(quotes, list)
            and source_text in quotes
            and ref.get("source_artifact_id")
            and ref.get("source_ref_id")
            and ref.get("source_anchor_id")
            and ref.get("evidence_role") == "source_evidence"
            and ref.get("can_open_source") is True
        ):
            return ref
    return None


def _title_context_evidence(
    title_row: dict[str, Any], *, source_template: dict[str, Any],
) -> dict[str, Any] | None:
    """Materialize a source anchor for the title line from the registered source."""
    from .category_candidate_graph_extractor import materialize_promote_evidence_ref

    evidence = materialize_promote_evidence_ref(
        {
            "source_span_ref_id": title_row["source_span_ref_id"],
            "anchor_quotes": [title_row["text"]],
        },
        source_artifact_id=str(source_template.get("source_artifact_id") or ""),
        source_ref_id=str(source_template.get("source_ref_id") or ""),
    )
    if (
        evidence is None
        or evidence.get("can_open_source") is not True
        or not evidence.get("source_anchor_id")
    ):
        return None
    return evidence


def _append_evidence_once(node: dict[str, Any], evidence: dict[str, Any]) -> bool:
    refs = node.get("evidence_refs")
    if not isinstance(refs, list):
        return False
    span_ref = evidence.get("source_span_ref_id")
    if any(
        isinstance(ref, dict) and ref.get("source_span_ref_id") == span_ref
        for ref in refs
    ):
        return False
    refs.append(deepcopy(evidence))
    return True


def _apply_governance_relation(
    graph: dict[str, Any], rows: list[dict[str, Any]],
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Add only the uniquely name-bound relation explicitly stated by the source.

    Both endpoint candidates must already exist and carry the same openable exact
    Governance passage. This postprocessor never invents nodes or repairs an
    ambiguous or reversed model edge.
    """
    result = deepcopy(graph)
    nodes = result.get("nodes")
    edges = result.get("edges")
    if not isinstance(nodes, list) or not isinstance(edges, list):
        raise ValueError("candidate graph nodes and edges must be lists")
    if any(not isinstance(node, dict) for node in nodes):
        raise ValueError("candidate graph nodes must be objects")
    if any(not isinstance(edge, dict) for edge in edges):
        raise ValueError("candidate graph edges must be objects")

    statements = _governance_rows(_ordered_rows(rows))
    if not statements:
        return result, {"profile": PROFILE, "status": "not_applicable"}
    if len(statements) != 1:
        return result, {
            "profile": PROFILE,
            "status": "skipped",
            "reason": "multiple_governance_statements",
        }
    city_title = _document_city_title(rows)
    if city_title is None:
        return result, {
            "profile": PROFILE,
            "status": "skipped",
            "reason": "city_title_unresolved",
        }
    city_name, title_row = city_title
    city_nodes = _matching_city_nodes(nodes, city_name)
    council_nodes = _matching_council_nodes(nodes, city_name)
    if len(city_nodes) != 1 or len(council_nodes) != 1:
        return result, {
            "profile": PROFILE,
            "status": "skipped",
            "reason": "governance_endpoints_not_unique",
            "city_node_count": len(city_nodes),
            "council_node_count": len(council_nodes),
        }

    statement = statements[0]
    span_ref = statement["source_span_ref_id"]
    city = city_nodes[0]
    council = council_nodes[0]
    city_ref = _openable_source_evidence(
        city, span_ref=span_ref, source_text=statement["text"]
    )
    council_ref = _openable_source_evidence(
        council, span_ref=span_ref, source_text=statement["text"]
    )
    if city_ref is None or council_ref is None:
        return result, {
            "profile": PROFILE,
            "status": "skipped",
            "reason": "endpoint_missing_openable_governance_evidence",
            "source_span_ref_id": span_ref,
        }
    if (
        city_ref.get("source_artifact_id") != council_ref.get("source_artifact_id")
        or city_ref.get("source_ref_id") != council_ref.get("source_ref_id")
    ):
        return result, {
            "profile": PROFILE,
            "status": "skipped",
            "reason": "endpoint_source_binding_mismatch",
            "source_span_ref_id": span_ref,
        }
    title_ref = _title_context_evidence(title_row, source_template=city_ref)
    if title_ref is None:
        return result, {
            "profile": PROFILE,
            "status": "skipped",
            "reason": "city_title_has_no_openable_source_anchor",
            "source_span_ref_id": span_ref,
        }

    council_id = str(council.get("node_id") or "").strip()
    city_id = str(city.get("node_id") or "").strip()
    if not council_id or not city_id or council_id == city_id:
        return result, {
            "profile": PROFILE,
            "status": "skipped",
            "reason": "invalid_governance_endpoints",
            "source_span_ref_id": span_ref,
        }
    if (
        not isinstance(city.get("semantic_state"), dict)
        or city.get("semantic_state") != council.get("semantic_state")
    ):
        return result, {
            "profile": PROFILE,
            "status": "skipped",
            "reason": "governance_endpoint_state_mismatch",
            "source_span_ref_id": span_ref,
        }

    exact = [
        edge for edge in edges
        if edge.get("relationship_type") == "governs"
        and edge.get("from_node_id") == council_id
        and edge.get("to_node_id") == city_id
    ]
    reversed_edges = [
        edge for edge in edges
        if edge.get("relationship_type") == "governs"
        and edge.get("from_node_id") == city_id
        and edge.get("to_node_id") == council_id
    ]
    if reversed_edges or len(exact) > 1:
        return result, {
            "profile": PROFILE,
            "status": "skipped",
            "reason": "conflicting_or_duplicate_governance_edge",
            "source_span_ref_id": span_ref,
        }
    if exact and not isinstance(exact[0].get("evidence_refs"), list):
        return result, {
            "profile": PROFILE,
            "status": "skipped",
            "reason": "existing_governance_edge_has_invalid_evidence",
            "source_span_ref_id": span_ref,
        }

    edge_id = f"edge:{council_id}:governs:{city_id}"
    id_collision = next(
        (edge for edge in edges if edge.get("edge_id") == edge_id and edge not in exact),
        None,
    )
    if id_collision is not None:
        return result, {
            "profile": PROFILE,
            "status": "skipped",
            "reason": "governance_edge_id_collision",
            "source_span_ref_id": span_ref,
        }

    attached_city_title = _append_evidence_once(city, title_ref)
    attached_council_title = _append_evidence_once(council, title_ref)

    if exact:
        edge = exact[0]
        attached_governance_evidence = _append_evidence_once(edge, city_ref)
        attached_title_evidence = _append_evidence_once(edge, title_ref)
        status = (
            "evidence_attached"
            if attached_city_title or attached_council_title
            or attached_governance_evidence or attached_title_evidence
            else "already_present"
        )
        edge_id = str(edge.get("edge_id") or edge_id)
    else:
        semantic_state = council.get("semantic_state")
        if not isinstance(semantic_state, dict):
            return result, {
                "profile": PROFILE,
                "status": "skipped",
                "reason": "council_semantic_state_missing",
                "source_span_ref_id": span_ref,
            }
        edges.append({
            "edge_id": edge_id,
            "from_node_id": council_id,
            "to_node_id": city_id,
            "label": "governs",
            "relationship_type": "governs",
            "semantic_state": deepcopy(semantic_state),
            "evidence_refs": [deepcopy(city_ref), deepcopy(title_ref)],
            "proposed_action": "create",
            "confidence": "high",
            "warnings": [],
        })
        status = "added"

    return result, {
        "profile": PROFILE,
        "status": status,
        "edge_id": edge_id,
        "from_node_id": council_id,
        "to_node_id": city_id,
        "source_span_ref_id": span_ref,
        "title_span_ref_id": title_ref["source_span_ref_id"],
    }


def compile_gazetteer_governance_relations(
    graph: dict[str, Any], rows: list[dict[str, Any]],
) -> tuple[dict[str, Any], dict[str, Any]]:
    result, diagnostics = compile_gazetteer_scenario_scope(graph, rows)
    result, governance_diagnostics = _apply_governance_relation(result, rows)
    diagnostics["source_grounded_governance"] = governance_diagnostics
    return result, diagnostics


GAZETTEER_GOVERNANCE_PROFILE = register_extraction_profile(replace(
    GAZETTEER_PREPARED_SCENARIO_PROFILE,
    profile_version=PROFILE_VERSION,
    source_section_retainer=compile_gazetteer_governance_relations,
))
