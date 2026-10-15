"""Keep explicitly prepared Mirathorn scenes out of durable setting facts."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
from typing import Any

from .extraction_profile import register_extraction_profile
from .worldbuilding_gazetteer_role_citations import (
    GAZETTEER_ROLE_CITATION_PROFILE,
    compile_gazetteer_role_citations,
)
from .worldbuilding_source_sections import SourceSectionRetentionError


PROFILE_ID = "worldbuilding_gazetteer_v1"
PROFILE_VERSION = "1.8"
PROFILE = f"{PROFILE_ID}@{PROFILE_VERSION}"
_PROFILE_WARNING = f"source_support_policy:{PROFILE}"


def _heading(text: str) -> tuple[int, str] | None:
    stripped = text.strip()
    level = 0
    for char in stripped:
        if char != "#":
            break
        level += 1
    if not level or level > 6 or len(stripped) <= level or stripped[level] != " ":
        return None
    return level, stripped[level + 1:].strip().rstrip("#").strip()


def _ordered_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    previous_end = 0
    refs: set[str] = set()
    for row in rows:
        if not isinstance(row, dict):
            raise SourceSectionRetentionError("invalid source span row")
        start = row.get("line_start")
        end = row.get("line_end")
        span_ref = row.get("source_span_ref_id")
        text = row.get("text")
        if (
            isinstance(start, bool) or not isinstance(start, int)
            or isinstance(end, bool) or not isinstance(end, int)
            or start <= previous_end or end < start
            or not isinstance(span_ref, str) or not span_ref or span_ref in refs
            or not isinstance(text, str)
        ):
            raise SourceSectionRetentionError("invalid source span ordering or identity")
        previous_end = end
        refs.add(span_ref)
    return rows


def _physical_source_lines(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Expand grouped source spans while retaining their original identities."""
    physical = []
    for row in _ordered_rows(rows):
        start = row["line_start"]
        end = row["line_end"]
        lines = row["text"].splitlines()
        if len(lines) != end - start + 1:
            raise SourceSectionRetentionError(
                "source span text does not match its physical line range"
            )
        for offset, text in enumerate(lines):
            physical.append({
                **row,
                "line_start": start + offset,
                "line_end": start + offset,
                "text": text,
            })
    return physical


def _section_refs(
    rows: list[dict[str, Any]], *, title: str, heading_level: int,
    stop_levels: set[int], optional: bool = False,
) -> dict[str, Any] | None:
    physical_rows = _physical_source_lines(rows)
    matches = [
        index for index, row in enumerate(physical_rows)
        if (_heading(row["text"]) == (heading_level, title))
    ]
    if not matches and optional:
        return None
    if len(matches) != 1:
        raise SourceSectionRetentionError(
            f"expected one {title!r} source heading; found {len(matches)}"
        )
    start_index = matches[0]
    start_line = physical_rows[start_index]["line_start"]
    next_heading = next((
        row for row in physical_rows[start_index + 1:]
        if (parsed := _heading(row["text"])) is not None
        and parsed[0] in stop_levels
    ), None)
    end_line = next_heading["line_start"] - 1 if next_heading else rows[-1]["line_end"]
    refs = []
    for row in _ordered_rows(rows):
        overlaps = row["line_start"] <= end_line and row["line_end"] >= start_line
        if not overlaps:
            continue
        if row["line_start"] < start_line or row["line_end"] > end_line:
            raise SourceSectionRetentionError(
                f"source span crosses the boundary of {title!r}"
            )
        refs.append(row["source_span_ref_id"])
    return {
        "heading": title,
        "start_line": start_line,
        "end_line": end_line,
        "source_span_ref_ids": refs,
    }


def prepared_scenario_sections(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Find bounded prepared-scene sections without swallowing intervening lore."""
    rows = _ordered_rows(rows)
    if not rows:
        return []
    sections = []
    plot_hooks = _section_refs(
        rows, title="Plot Hooks and Encounters", heading_level=4,
        stop_levels={1, 2}, optional=True,
    )
    if plot_hooks is not None:
        sections.append(plot_hooks)
    approach = _section_refs(
        rows, title="Approach to Mirathorn", heading_level=2,
        stop_levels={1}, optional=True,
    )
    if approach is not None:
        sections.append(approach)
    sections.sort(key=lambda item: item["start_line"])
    previous_end = 0
    for section in sections:
        if section["start_line"] <= previous_end:
            raise SourceSectionRetentionError("prepared-scenario source sections overlap")
        previous_end = section["end_line"]
    return sections


def _span_refs(item: dict[str, Any]) -> list[str | None]:
    evidence_refs = item.get("evidence_refs")
    if not isinstance(evidence_refs, list):
        return []
    return [
        ref.get("source_span_ref_id") if isinstance(ref, dict) else None
        for ref in evidence_refs
    ]


def _with_profile_warning(item: dict[str, Any]) -> None:
    warnings = item.get("warnings")
    if not isinstance(warnings, list):
        warnings = []
        item["warnings"] = warnings
    if _PROFILE_WARNING not in warnings:
        warnings.append(_PROFILE_WARNING)


def _defer(
    result: dict[str, Any], proposals: dict[str, dict[str, Any]], *,
    kind: str, item: dict[str, Any], reason: str, refs: list[str],
) -> None:
    item_id = f"deferred:prepared-scenario:{kind}:{item.get(kind + '_id')}"
    if item_id in proposals or any(
        existing.get("item_id") == item_id
        for existing in result.get("deferred_items", [])
        if isinstance(existing, dict)
    ):
        raise SourceSectionRetentionError("prepared-scenario disposition identity collision")
    proposal = deepcopy(item)
    _with_profile_warning(proposal)
    result.setdefault("deferred_items", []).append({
        "item_id": item_id,
        "label": item.get("label") or item.get(kind + "_id") or "",
        "reason": reason,
        "evidence_refs": [
            deepcopy(ref) for ref in item.get("evidence_refs", [])
            if isinstance(ref, dict)
            and ref.get("source_span_ref_id") in refs
        ],
        "warnings": [_PROFILE_WARNING],
        "suggested_next_step": (
            "Review this proposal as prepared-scene material; do not promote it "
            "as enduring World knowledge without separate source support."
        ),
    })
    proposals[item_id] = {"item_id": item_id, "kind": kind, "proposal": proposal}


def retain_durable_gazetteer_scope(
    graph: dict[str, Any], rows: list[dict[str, Any]],
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Defer scene-only proposals and clear contaminated prose from mixed nodes.

    Source passages remain in the immutable source index. A mixed node can remain
    only when a clean, source-backed edge independently establishes its identity;
    in that case its unsupported description and aliases are removed.
    """
    sections = prepared_scenario_sections(rows)
    section_by_ref = {
        span_ref: section["heading"]
        for section in sections
        for span_ref in section["source_span_ref_ids"]
    }
    all_source_refs = {row["source_span_ref_id"] for row in rows}
    result = deepcopy(graph)
    proposals: dict[str, dict[str, Any]] = {}
    if not sections:
        return result, {
            "profile": PROFILE,
            "status": "no_recognized_prepared_scenario_sections",
            "sections": [],
            "deferred_proposals": {},
            "deferred_node_ids": [],
            "deferred_edge_ids": [],
            "sanitized_node_ids": [],
        }

    nodes = result.get("nodes", [])
    edges = result.get("edges", [])
    if not isinstance(nodes, list) or not isinstance(edges, list):
        raise SourceSectionRetentionError("candidate graph nodes and edges must be lists")
    node_by_id = {
        node.get("node_id"): node for node in nodes if isinstance(node, dict)
    }
    if len(node_by_id) != len(nodes) or None in node_by_id:
        raise SourceSectionRetentionError("candidate graph node identities are invalid")

    scene_edge_ids: set[str] = set()
    durable_edge_ids: set[str] = set()
    for edge in edges:
        if not isinstance(edge, dict) or not edge.get("edge_id"):
            raise SourceSectionRetentionError("candidate graph edge identities are invalid")
        refs = _span_refs(edge)
        if any(ref in section_by_ref for ref in refs):
            scene_edge_ids.add(edge["edge_id"])
        elif refs and all(ref in all_source_refs for ref in refs):
            durable_edge_ids.add(edge["edge_id"])

    scene_node_ids: set[str] = set()
    affected_node_ids: set[str] = set()
    for node in nodes:
        refs = _span_refs(node)
        scene_refs = [ref for ref in refs if ref in section_by_ref]
        if not scene_refs:
            continue
        affected_node_ids.add(node["node_id"])
        if refs and all(ref in section_by_ref for ref in refs):
            scene_node_ids.add(node["node_id"])

    durable_incident_edges: dict[str, list[dict[str, Any]]] = {}
    for edge in edges:
        if edge.get("edge_id") not in durable_edge_ids:
            continue
        source_id = edge.get("from_node_id")
        target_id = edge.get("to_node_id")
        if source_id not in node_by_id or target_id not in node_by_id:
            continue
        if source_id in scene_node_ids or target_id in scene_node_ids:
            continue
        durable_incident_edges.setdefault(source_id, []).append(edge)
        durable_incident_edges.setdefault(target_id, []).append(edge)

    kept_nodes: list[dict[str, Any]] = []
    dropped_node_ids: set[str] = set()
    sanitized_nodes = []
    for node in nodes:
        node_id = node["node_id"]
        if node_id not in affected_node_ids:
            kept_nodes.append(node)
            continue
        incident = durable_incident_edges.get(node_id, [])
        if not incident:
            _defer(
                result, proposals, kind="node", item=node,
                reason="node_supported_only_by_prepared_scenario_material",
                refs=[ref for ref in _span_refs(node) if ref in section_by_ref],
            )
            dropped_node_ids.add(node_id)
            continue

        original = deepcopy(node)
        retained_evidence: dict[str, dict[str, Any]] = {}
        for edge in incident:
            for ref in edge.get("evidence_refs", []):
                if isinstance(ref, dict):
                    span_ref = ref.get("source_span_ref_id")
                    if span_ref in all_source_refs and span_ref not in section_by_ref:
                        retained_evidence.setdefault(span_ref, deepcopy(ref))
        node["description"] = ""
        node["evidence_refs"] = [retained_evidence[key] for key in sorted(retained_evidence)]
        if "aliases" in node:
            node["aliases"] = []
        if "corpus_ref" in node:
            node["corpus_ref"] = None
        _with_profile_warning(node)
        kept_nodes.append(node)
        item_id = f"deferred:prepared-scenario:sanitized-node:{node_id}"
        if item_id in proposals or any(
            existing.get("item_id") == item_id
            for existing in result.get("deferred_items", [])
            if isinstance(existing, dict)
        ):
            raise SourceSectionRetentionError("prepared-scenario disposition identity collision")
        proposals[item_id] = {
            "item_id": item_id,
            "kind": "node",
            "proposal": original,
            "decision": "identity_retained_description_and_aliases_cleared",
        }
        sanitized_nodes.append({
            "node_id": node_id,
            "removed_source_span_ref_ids": [
                ref for ref in _span_refs(original) if ref in section_by_ref
            ],
            "retained_edge_ids": sorted(edge["edge_id"] for edge in incident),
            "retained_evidence_span_ref_ids": sorted(retained_evidence),
            "description_cleared": True,
            "aliases_cleared": "aliases" in original,
        })

    kept_node_ids = {node["node_id"] for node in kept_nodes}
    kept_edges: list[dict[str, Any]] = []
    deferred_edge_ids: list[str] = []
    for edge in edges:
        edge_id = edge["edge_id"]
        scene_refs = [ref for ref in _span_refs(edge) if ref in section_by_ref]
        missing_endpoint = (
            edge.get("from_node_id") not in kept_node_ids
            or edge.get("to_node_id") not in kept_node_ids
        )
        if scene_refs or missing_endpoint:
            reason = (
                "relationship_supported_by_prepared_scenario_material"
                if scene_refs else "relationship_endpoint_deferred_with_prepared_scenario_node"
            )
            _defer(
                result, proposals, kind="edge", item=edge, reason=reason,
                refs=[ref for ref in _span_refs(edge) if isinstance(ref, str)],
            )
            deferred_edge_ids.append(edge_id)
            continue
        kept_edges.append(edge)

    result["nodes"] = kept_nodes
    result["edges"] = kept_edges
    deferred_node_ids = sorted(dropped_node_ids)
    return result, {
        "profile": PROFILE,
        "sections": sections,
        "deferred_node_ids": deferred_node_ids,
        "deferred_edge_ids": sorted(deferred_edge_ids),
        "sanitized_node_ids": sorted(item["node_id"] for item in sanitized_nodes),
        "sanitized_nodes": sanitized_nodes,
        "deferred_proposals": {key: proposals[key] for key in sorted(proposals)},
    }


def compile_gazetteer_scenario_scope(
    graph: dict[str, Any], rows: list[dict[str, Any]],
) -> tuple[dict[str, Any], dict[str, Any]]:
    result, diagnostics = compile_gazetteer_role_citations(graph, rows)
    result, scope_diagnostics = retain_durable_gazetteer_scope(result, rows)
    diagnostics["prepared_scenario_scope"] = scope_diagnostics
    for deferred in result.get("deferred_items", []):
        _with_profile_warning(deferred)
    livestock = diagnostics.get("livestock_semantic_hygiene")
    if isinstance(livestock, dict):
        livestock["profile"] = PROFILE
    return result, diagnostics


GAZETTEER_PREPARED_SCENARIO_PROFILE = register_extraction_profile(replace(
    GAZETTEER_ROLE_CITATION_PROFILE,
    profile_version=PROFILE_VERSION,
    source_section_retainer=compile_gazetteer_scenario_scope,
))
