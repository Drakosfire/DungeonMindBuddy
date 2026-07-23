from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from graph_memory.anchor_quotes import (
    anchor_quote_matches_to_dicts,
    find_anchor_quote_matches,
    normalize_for_match,
)

PREVIEW_UNION_SCHEMA = "dmb_union_supergraph_store_v0"
PREVIEW_UNION_VERSION = "0.1"


@dataclass(frozen=True)
class CandidateGraphInput:
    path: Path
    session_id: str | None = None
    recap_path: Path | None = None
    recap_text: str | None = None


def build_preview_union_supergraph(
    inputs: list[CandidateGraphInput],
    *,
    focus_session_id: str,
    graph_id: str = "longmont-c2:preview-union-supergraph",
) -> dict[str, Any]:
    """Build a preview-only union-supergraph read model from candidate graphs."""

    nodes: dict[str, dict[str, Any]] = {}
    edges: dict[str, dict[str, Any]] = {}
    evidence: dict[str, dict[str, Any]] = {}
    source_artifacts: dict[str, dict[str, Any]] = {}
    aliases: dict[str, str] = {}

    for graph_input in inputs:
        graph = _load_candidate_graph(graph_input.path)
        session_id = graph_input.session_id or str(graph.get("session_id") or "")
        campaign_id = str(graph.get("campaign_id") or "longmont-c2")
        source_artifact_id = _source_artifact_id(graph, session_id)
        source_artifacts[source_artifact_id] = {
            "source_artifact_id": source_artifact_id,
            "source_domain": "recap",
            "campaign_id": campaign_id,
            "session_id": session_id,
            "uri": graph_input.path.as_posix(),
        }
        if graph_input.recap_path is not None:
            source_artifacts[source_artifact_id]["recap_path"] = graph_input.recap_path.as_posix()
        paragraph_lookup = _paragraph_lookup(
            graph_input.recap_path,
            session_id=session_id,
            recap_text=graph_input.recap_text,
        )
        node_id_map = {
            str(node["node_id"]): _global_node_id(node)
            for node in graph.get("nodes", [])
            if node.get("node_id")
        }

        for candidate_node in graph.get("nodes", []):
            global_node_id = node_id_map.get(str(candidate_node.get("node_id")))
            if not global_node_id:
                continue
            node = nodes.setdefault(
                global_node_id,
                _new_union_node(candidate_node, global_node_id),
            )
            _extend_unique(node["source_domains"], "recap")
            _extend_unique(node["aliases"], str(candidate_node.get("label") or ""))
            for ref in candidate_node.get("evidence_refs", []):
                evidence_id = _add_evidence(
                    evidence,
                    ref,
                    object_id=global_node_id,
                    session_id=session_id,
                    source_artifact_id=source_artifact_id,
                    source_domain="recap",
                    paragraph_lookup=paragraph_lookup,
                    label=str(candidate_node.get("label") or ""),
                )
                _extend_unique(node["evidence_ref_ids"], evidence_id)
            corpus_ref = candidate_node.get("corpus_ref")
            if isinstance(corpus_ref, Mapping) and corpus_ref.get("resolution") == "resolved":
                worldbuilding_evidence_id = _add_worldbuilding_evidence(
                    evidence,
                    source_artifacts,
                    campaign_id=campaign_id,
                    global_node_id=global_node_id,
                    corpus_ref=corpus_ref,
                )
                _extend_unique(node["evidence_ref_ids"], worldbuilding_evidence_id)
                _extend_unique(node["source_domains"], "worldbuilding")
            if node["aliases"]:
                aliases[_alias_key(node["label"])] = global_node_id
                for alias in node["aliases"]:
                    aliases[_alias_key(alias)] = global_node_id

        for candidate_edge in graph.get("edges", []):
            source_node_id = node_id_map.get(str(candidate_edge.get("from_node_id")))
            target_node_id = node_id_map.get(str(candidate_edge.get("to_node_id")))
            if not source_node_id or not target_node_id:
                continue
            edge_id = _global_edge_id(candidate_edge, source_node_id, target_node_id, session_id)
            edge = edges.setdefault(
                edge_id,
                {
                    "edge_id": edge_id,
                    "source_node_id": source_node_id,
                    "target_node_id": target_node_id,
                    "predicate": str(
                        candidate_edge.get("relationship_type")
                        or candidate_edge.get("label")
                        or "related"
                    ),
                    "label": str(candidate_edge.get("label") or "related"),
                    "direction": "outbound",
                    "source_domains": ["recap"],
                    "session_ids": [],
                    "evidence_ref_ids": [],
                    "state": _preview_state(),
                },
            )
            _extend_unique(edge["session_ids"], session_id)
            for ref in candidate_edge.get("evidence_refs", []):
                evidence_id = _add_evidence(
                    evidence,
                    ref,
                    object_id=edge_id,
                    session_id=session_id,
                    source_artifact_id=source_artifact_id,
                    source_domain="recap",
                    paragraph_lookup=paragraph_lookup,
                    label=str(candidate_edge.get("label") or ""),
                )
                _extend_unique(edge["evidence_ref_ids"], evidence_id)

    adjacency = _build_adjacency(edges, focus_session_id=focus_session_id)
    for node_id in nodes:
        adjacency.setdefault(node_id, [])

    return {
        "schema": PREVIEW_UNION_SCHEMA,
        "version": PREVIEW_UNION_VERSION,
        "campaign_id": "longmont-c2",
        "graph_id": graph_id,
        "graph_domains": ["campaign", "preview"],
        "source_domains": ["recap", "worldbuilding"],
        "focus_session_id": focus_session_id,
        "nodes": dict(sorted(nodes.items())),
        "edges": dict(sorted(edges.items())),
        "evidence": dict(sorted(evidence.items())),
        "source_artifacts": dict(sorted(source_artifacts.items())),
        "aliases": dict(sorted((k, v) for k, v in aliases.items() if k)),
        "adjacency": {key: value for key, value in sorted(adjacency.items())},
        "diagnostics": {
            "canon_promotion": False,
            "approved_memory_write": False,
            "corpus_mutation": False,
            "production_retrieval": False,
            "preview_import": True,
        },
    }


def _load_candidate_graph(path: Path) -> dict[str, Any]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if raw.get("candidate_graph"):
        return dict(raw["candidate_graph"])
    return dict(raw)


def _source_artifact_id(graph: Mapping[str, Any], session_id: str) -> str:
    source_artifact_ids = graph.get("source_artifact_ids") or []
    if source_artifact_ids:
        return str(source_artifact_ids[0])
    return f"source-artifact:{session_id}:candidate-graph"


def _new_union_node(candidate_node: Mapping[str, Any], global_node_id: str) -> dict[str, Any]:
    kind = _node_kind(candidate_node)
    label = str(candidate_node.get("label") or global_node_id)
    return {
        "node_id": global_node_id,
        "label": label,
        "kind": kind,
        "role": kind,
        "description": candidate_node.get("description"),
        "aliases": [label],
        "source_domains": [],
        "evidence_ref_ids": [],
        "state": _preview_state(),
    }


def _node_kind(candidate_node: Mapping[str, Any]) -> str:
    node_type = str(candidate_node.get("node_type") or "unknown").strip()
    if node_type == "character":
        corpus_ref = candidate_node.get("corpus_ref")
        if isinstance(corpus_ref, Mapping) and corpus_ref.get("type") == "pc":
            return "pc"
        return "character"
    if node_type == "mystery":
        return "thread"
    return node_type


def _global_node_id(candidate_node: Mapping[str, Any]) -> str:
    kind = _node_kind(candidate_node)
    label = str(candidate_node.get("label") or candidate_node.get("node_id") or "node")
    return f"{kind}_{_slug(label)}"


def _global_edge_id(
    candidate_edge: Mapping[str, Any],
    source_node_id: str,
    target_node_id: str,
    session_id: str,
) -> str:
    predicate = _slug(
        str(
            candidate_edge.get("relationship_type")
            or candidate_edge.get("label")
            or "related"
        )
    )
    raw_edge_id = _slug(str(candidate_edge.get("edge_id") or "edge"))
    return f"edge:{session_id}:{source_node_id}:{predicate}:{target_node_id}:{raw_edge_id}"


def _preview_state() -> dict[str, Any]:
    return {
        "memory_state": "preview_import",
        "canon_state": "not_canon_promotion",
        "approval_state": "needs_review",
    }


def _add_worldbuilding_evidence(
    evidence: dict[str, dict[str, Any]],
    source_artifacts: dict[str, dict[str, Any]],
    *,
    campaign_id: str,
    global_node_id: str,
    corpus_ref: Mapping[str, Any],
) -> str:
    artifact_id = f"artifact:worldbuilding:{campaign_id}:{_slug(str(corpus_ref.get('ref_id') or global_node_id))}"
    source_artifacts.setdefault(
        artifact_id,
        {
            "source_artifact_id": artifact_id,
            "source_domain": "worldbuilding",
            "campaign_id": campaign_id,
            "uri": str(corpus_ref.get("hub_path") or f"fixture://corpus-ref/{global_node_id}"),
        },
    )
    evidence_id = f"evidence:worldbuilding:{global_node_id}:corpus-ref"
    evidence.setdefault(
        evidence_id,
        {
            "evidence_ref_id": evidence_id,
            "source_artifact_id": artifact_id,
            "source_domain": "worldbuilding",
            "evidence_role": "corpus_ref_context",
            "locator": str(corpus_ref.get("hub_path") or f"fixture://corpus-ref/{global_node_id}"),
            "can_open_source": True,
            "can_highlight_span": False,
        },
    )
    return evidence_id


def _add_evidence(
    evidence: dict[str, dict[str, Any]],
    ref: Any,
    *,
    object_id: str,
    session_id: str,
    source_artifact_id: str,
    source_domain: str,
    paragraph_lookup: Mapping[str, str],
    label: str,
) -> str:
    ref_map = ref if isinstance(ref, Mapping) else {}
    span_ref_id = str(
        ref_map.get("source_span_ref_id")
        or ref_map.get("span_id")
        or ref_map.get("source_anchor_id")
        or f"spref:{session_id}:unknown"
    )
    evidence_id = f"evidence:{session_id}:{_slug(object_id)}:{_slug(span_ref_id)}"
    item = evidence.setdefault(
        evidence_id,
        {
            "evidence_ref_id": evidence_id,
            "source_artifact_id": str(ref_map.get("source_artifact_id") or source_artifact_id),
            "source_domain": source_domain,
            "evidence_role": str(ref_map.get("evidence_role") or "source_evidence"),
            "session_id": session_id,
            "source_span_ref_id": span_ref_id,
            "can_open_source": bool(ref_map.get("can_open_source", True)),
            "can_highlight_span": bool(ref_map.get("can_highlight_span", True)),
            "label": ref_map.get("text_excerpt") or ref_map.get("label") or label,
        },
    )
    paragraph = paragraph_lookup.get(span_ref_id)
    repaired_quotes, match_dicts = _repair_anchor_quotes(
        paragraph,
        [str(q) for q in ref_map.get("anchor_quotes", []) if str(q).strip()],
    )
    if repaired_quotes:
        item["anchor_quotes"] = repaired_quotes
    if match_dicts:
        item["anchor_quote_matches"] = match_dicts
    return evidence_id


def _repair_anchor_quotes(
    paragraph: str | None,
    quotes: list[str],
) -> tuple[list[str], list[dict[str, Any]]]:
    if not paragraph or not quotes:
        return [], []
    accepted: list[str] = []
    repairs: list[dict[str, str]] = []
    for quote in quotes:
        matches = find_anchor_quote_matches(paragraph, [quote])
        if matches:
            accepted.append(quote)
            continue
        repaired = _repair_quote_by_ordered_tokens(paragraph, quote)
        if repaired:
            accepted.append(repaired)
            repairs.append({"from": quote, "to": repaired})
    match_dicts = anchor_quote_matches_to_dicts(find_anchor_quote_matches(paragraph, accepted))
    if repairs:
        for match in match_dicts:
            for repair in repairs:
                if match["quote"] == repair["to"]:
                    match["repaired_from"] = repair["from"]
    return accepted, match_dicts


def _repair_quote_by_ordered_tokens(paragraph: str, quote: str) -> str | None:
    quote_tokens = _tokens_with_positions(quote)
    paragraph_tokens = _tokens_with_positions(paragraph)
    if len(quote_tokens) < 2 or not paragraph_tokens:
        return None
    quote_norms = [token for token, _, _ in quote_tokens]
    windows: list[tuple[int, int]] = []
    max_extra_tokens = 3
    max_window_chars = max(len(quote) + 32, int(len(quote) * 1.75))
    for start_index, (token, raw_start, _) in enumerate(paragraph_tokens):
        if token != quote_norms[0]:
            continue
        q_index = 1
        end_raw = paragraph_tokens[start_index][2]
        extras = 0
        for p_index in range(start_index + 1, len(paragraph_tokens)):
            p_token, _, p_end = paragraph_tokens[p_index]
            if q_index < len(quote_norms) and p_token == quote_norms[q_index]:
                q_index += 1
                end_raw = p_end
                if q_index == len(quote_norms):
                    break
            else:
                extras += 1
                if extras > max_extra_tokens:
                    break
        if q_index == len(quote_norms) and end_raw - raw_start <= max_window_chars:
            windows.append((raw_start, end_raw))
    if len(windows) != 1:
        return None
    start, end = windows[0]
    return paragraph[start:end]


def _tokens_with_positions(text: str) -> list[tuple[str, int, int]]:
    tokens: list[tuple[str, int, int]] = []
    for match in re.finditer(r"[\w']+", text, flags=re.UNICODE):
        token = normalize_for_match(match.group(0)).strip("'")
        if token:
            tokens.append((token, match.start(), match.end()))
    return tokens


def _paragraph_lookup(
    recap_path: Path | None,
    *,
    session_id: str,
    recap_text: str | None = None,
) -> dict[str, str]:
    if recap_text is not None:
        text = _strip_yaml_frontmatter(recap_text)
    elif recap_path is not None and recap_path.exists():
        text = _strip_yaml_frontmatter(recap_path.read_text(encoding="utf-8"))
    else:
        return {}
    paragraphs = [part.strip() for part in re.split(r"\n\s*\n", text) if part.strip()]
    lookup: dict[str, str] = {}
    for index, paragraph in enumerate(paragraphs, start=1):
        lookup[f"{session_id}:recap:paragraph:{index:03d}"] = paragraph
        lookup[f"spref:{session_id}:p{index:03d}"] = paragraph
        lookup[f"{session_id}:p{index:03d}"] = paragraph
    return lookup


def _strip_yaml_frontmatter(markdown: str) -> str:
    lines = markdown.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    if not lines or lines[0].strip() != "---":
        return markdown
    for index in range(1, len(lines)):
        if lines[index].strip() == "---":
            return "\n".join(lines[index + 1 :]).lstrip("\n")
    return markdown


def _build_adjacency(
    edges: Mapping[str, Mapping[str, Any]],
    *,
    focus_session_id: str,
) -> dict[str, list[dict[str, Any]]]:
    adjacency: dict[str, list[dict[str, Any]]] = {}
    for edge in edges.values():
        edge_id = str(edge["edge_id"])
        source_node_id = str(edge["source_node_id"])
        target_node_id = str(edge["target_node_id"])
        anchored = focus_session_id in set(edge.get("session_ids") or [])
        adjacency.setdefault(source_node_id, []).append(
            {
                "edge_id": edge_id,
                "node_id": target_node_id,
                "label": edge["label"],
                "direction": "outbound",
                "anchored_to_focus_session": anchored,
            }
        )
        adjacency.setdefault(target_node_id, []).append(
            {
                "edge_id": edge_id,
                "node_id": source_node_id,
                "label": edge["label"],
                "direction": "inbound",
                "anchored_to_focus_session": anchored,
            }
        )
    return adjacency


def _slug(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", normalize_for_match(value)).strip("_")
    return slug or "unknown"


def _alias_key(value: str) -> str:
    return normalize_for_match(value).strip()


def _extend_unique(items: list[str], value: str) -> None:
    if value and value not in items:
        items.append(value)
