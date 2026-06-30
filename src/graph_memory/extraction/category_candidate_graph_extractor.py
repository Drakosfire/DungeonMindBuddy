"""Category-decomposed graph extraction for runtime recap graph ingest."""
from __future__ import annotations

import json
import logging
import os
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping, Protocol, Sequence

from src.bootstrap_env import load_dungeonmindbuddy_dotenv
from src.graph_memory import identity_resolution as ir
from src.graph_memory.anchor_quotes import coerce_anchor_quotes
from src.graph_memory.predicate_catalog import (
    prompt_markdown as predicate_catalog_prompt_markdown,
    predicate_family_for_type,
    validate_edge_predicate,
)
from src.graph_memory.party_context import (
    PartyContext,
    build_party_context_for_campaign,
)
from src.graph_memory.vocabulary.edge_context import render_edge_vocabulary_context
from src.graph_memory.vocabulary.model import ContextVocabularyPacket
from src.graph_memory.session_graph_context import (
    build_session_graph_context,
    merge_party_anchor_nodes,
    merge_party_collective,
    party_anchors_markdown,
)

logger = logging.getLogger(__name__)

BEAT_PASS_NAME = "beat_pass"
EDGE_PASS_NAME = "edge_pass"

NODE_EXTRACTION_PASSES: tuple[tuple[str, str, str], ...] = (
    (
        "actor_pass",
        "character",
        "Extract named NON-PARTY NPCs, characters, and creatures only. "
        "Do NOT extract player characters or traveling companion NPCs — those are supplied as party anchors.",
    ),
    (
        "location_pass",
        "location",
        "Extract regions, towns, cities, roads, routes, sublocations, and named travel zones only.",
    ),
    (
        "collective_pass",
        "faction",
        "Extract factions, councils, guards, mercenary groups, organizations, and parties (as collectives) only. "
        "Use node_type faction, organization, or group as appropriate.",
    ),
    (
        "object_pass",
        "item",
        "Extract notable items, devices, artifacts, and objects only — not table-mechanics noise.",
    ),
    (
        "thread_pass",
        "mystery",
        "Extract mysteries, clues, warnings, events, unresolved phenomena, and threads. "
        "Also emit ignored_items and deferred_items when appropriate.",
    ),
)

ALL_PASS_NAMES: tuple[str, ...] = tuple(p[0] for p in NODE_EXTRACTION_PASSES) + (
    BEAT_PASS_NAME,
    EDGE_PASS_NAME,
)

PASS_PROGRESS_LABELS: dict[str, str] = {
    "actor_pass": "Extracting actors and NPCs",
    "location_pass": "Extracting locations",
    "collective_pass": "Extracting factions and collectives",
    "object_pass": "Extracting notable objects",
    "thread_pass": "Extracting mysteries and threads",
    "beat_pass": "Extracting session beats",
    "edge_pass": "Extracting relationship edges",
}

EVIDENCE_RULE = (
    "Every positive object MUST include evidence_refs as an array of objects with: "
    '{"source_span_ref_id": "<span id from source packet>", '
    '"anchor_quotes": ["<verbatim phrase copied from that paragraph>"]}. '
    "anchor_quotes must be literal substrings from the cited paragraph text block — "
    "not summaries, not your own node labels, not regex, not invented snippets. "
    "Copy exact words from the source packet."
)

DEFAULT_SEMANTIC_STATE = {
    "lifecycle": "candidate",
    "canon_status": "preview_only",
    "memory_status": "uncommitted",
}

ENVELOPE_SCHEMA = "dmb_live_extractor_candidate_envelope_v0"
ENVELOPE_VERSION = "0.1"
CANDIDATE_GRAPH_SCHEMA = "dmb_candidate_graph_preview_v0"
CANDIDATE_GRAPH_VERSION = "0.1"

PREVIEW_DIAGNOSTICS = {
    "preview_only": True,
    "canon_promotion": False,
    "approved_memory_write": False,
    "corpus_mutation": False,
    "production_retrieval": False,
}


class CategoryGraphExtractionError(RuntimeError):
    def __init__(
        self,
        message: str,
        *,
        pass_name: str | None = None,
        raw_model_response: str | None = None,
    ):
        super().__init__(message)
        self.pass_name = pass_name
        self.raw_model_response = raw_model_response


class CategoryGraphPassClient(Protocol):
    def run_pass(
        self,
        pass_name: str,
        *,
        model_id: str,
        instructions: str,
        user_content: str,
    ) -> dict[str, Any]: ...


@dataclass(frozen=True)
class CategoryGraphExtractionOptions:
    campaign_id: str
    session_id: str
    session_number: int
    source_span_index: Mapping[str, Any]
    model_id: str | None = None
    enable_edge_vocabulary_packet: bool = False
    edge_vocabulary_packet: ContextVocabularyPacket | None = None


@dataclass(frozen=True)
class CategoryGraphExtractionResult:
    candidate_graph: dict[str, Any]
    envelope: dict[str, Any]
    pass_outputs: dict[str, dict[str, Any]]
    pass_telemetry: dict[str, Any]
    consolidation_diagnostics: dict[str, Any]
    model_id: str
    total_cost_usd: float
    diagnostics: dict[str, Any] = field(default_factory=dict)


def _policy_paths() -> list[Path]:
    here = Path(__file__).resolve()
    return [
        here.parents[2] / "MODEL_POLICY.json",
        here.parents[3] / "MODEL_POLICY.json",
    ]


def resolve_category_graph_model(model_id: str | None) -> str:
    if model_id and model_id.strip():
        return model_id.strip()
    for policy_path in _policy_paths():
        if policy_path.exists():
            policy = json.loads(policy_path.read_text(encoding="utf-8"))
            role = policy.get("actions", {}).get(
                "graph_memory_category_extraction", "fast_smart_mini"
            )
            resolved = policy.get("models", {}).get(role)
            if isinstance(resolved, str) and resolved.strip():
                return resolved.strip()
    return "gpt-5.4-mini"


def source_packet_rows_from_span_index(span_index: Mapping[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for span in span_index.get("spans") or []:
        if not isinstance(span, Mapping):
            continue
        if span.get("kind") not in {"paragraph", None}:
            if span.get("kind") == "full_text":
                continue
        spref = span.get("source_span_ref_id") or span.get("span_id")
        if not isinstance(spref, str) or not spref.strip():
            continue
        text = str(span.get("text") or span.get("text_excerpt") or "").strip()
        if not text and span.get("kind") == "full_text":
            continue
        if span.get("kind") == "full_text":
            continue
        rows.append(
            {
                "source_span_ref_id": spref,
                "source_unit_id": str(span.get("span_id") or spref),
                "line_start": int(span.get("line_start") or 1),
                "line_end": int(span.get("line_end") or 1),
                "text": text,
            }
        )
    return rows


def _prompt_key(pass_name: str) -> str:
    return f"{pass_name}.md"


def _source_packet_md(rows: Sequence[dict[str, Any]]) -> str:
    parts: list[str] = []
    for row in rows:
        parts.append(
            f"### {row['source_span_ref_id']} / {row['source_unit_id']} / "
            f"lines {row['line_start']}-{row['line_end']}\n\n"
            f"```text\n{row['text']}\n```"
        )
    return "\n\n".join(parts)


def _party_anchors_block(party_ctx: PartyContext) -> str:
    return party_anchors_markdown(party_ctx)


def render_category_pass_prompts(
    source_rows: Sequence[dict[str, Any]],
    *,
    party_ctx: PartyContext,
) -> dict[str, str]:
    src = _source_packet_md(source_rows)
    anchors = _party_anchors_block(party_ctx)
    safety = (
        "Preview-only graph memory extraction. "
        "Forbidden: approve memory, commit graph records, promote canon, execute writes."
    )
    prompts: dict[str, str] = {}
    for pass_name, default_type, instruction in NODE_EXTRACTION_PASSES:
        extra = ""
        if pass_name == "thread_pass":
            extra = (
                "\n\nAlso include JSON keys `ignored_items` and `deferred_items` (arrays, may be empty). "
                "Each item: `item_id`, `label`, `reason`, `evidence_refs`; deferred may include `suggested_next_step`."
            )
        prompts[_prompt_key(pass_name)] = (
            f"# Category Graph Extraction — {pass_name}\n\n{safety}\n\n{anchors}\n\n"
            f"## Task\n\n{instruction}\n\n"
            f"Default node_type for this pass: `{default_type}`.\n\n"
            f"Return JSON with key `observation_nodes` (array). Each node: "
            f"`node_id`, `label`, `node_type`, `description`, `importance` (high|medium|low), `evidence_refs`.\n"
            f"{EVIDENCE_RULE}{extra}\n\n## Source Packet\n\n{src}\n"
        )
    prompts[_prompt_key(BEAT_PASS_NAME)] = (
        f"# Category Graph Extraction — {BEAT_PASS_NAME}\n\n{safety}\n\n"
        "## Task\n\nExtract source-local beats (scenes, topic shifts, durable claims). "
        "Return JSON with key `observation_beats` (array). Each beat: "
        "`beat_id`, `order` (positive int), `title`, `summary`, `involved_node_ids` (may be empty), `evidence_refs`.\n"
        f"{EVIDENCE_RULE}\n\n## Source Packet\n\n{src}\n"
    )
    predicate_catalog = predicate_catalog_prompt_markdown()
    prompts[_prompt_key(EDGE_PASS_NAME)] = (
        f"# Category Graph Extraction — {EDGE_PASS_NAME}\n\n{safety}\n\n"
        "## Task\n\nUsing ONLY the Source Packet and consolidated node list supplied below, propose durable relationship edges. "
        "Do NOT create new nodes. Use exact `node_id` values from the consolidated nodes. "
        "For a session-sized graph, expect roughly 10-30 durable edges when evidence supports them; "
        "do not stop after the first few obvious edges.\n\n"
        "## Relationship extraction sweep\n\n"
        "Review the source and nodes systematically before returning JSON:\n"
        "- Location containment: emit `located_in`, `part_of`, `within`, or related location predicates for gates, walls, roads, inns, rooms, settlements, and regions.\n"
        "- Authority and command: emit `governs`, `leads`, `commands`, or `reports_to` for mayors, commanders, leaders, and organized refugee groups.\n"
        "- Threat and displacement: emit `threatens`, `besieges`, `attacks`, or `displaced_from` for attackers, fleeing groups, sieges, and evacuation pressure.\n"
        "- Knowledge and reports: emit `knows_about`, `aware_of`, or `reports_threat_in` for explicit knowledge, messages, warnings, and learned weaknesses.\n"
        "- Composition and participation: emit `part_of`, `member_of`, or `participates_in` for waves, groups, encounters, and participants.\n\n"
        "Prefer specific supported predicates over generic `associated_with` / `linked_to`. "
        "Omit an edge only when no catalog predicate is supported by a source quote or one endpoint cannot be bound to a listed node.\n\n"
        "Return JSON with key `observation_edges` (array). "
        "Each edge: `edge_id`, `from_node_id`, `to_node_id`, `label`, `relationship_type`, "
        "`predicate_family`, `evidence_refs`.\n"
        f"{predicate_catalog}\n\n"
        f"{EVIDENCE_RULE}\n\n## Source Packet\n\n{src}\n\n## Consolidated nodes\n\n"
        "(injected at runtime)\n"
    )
    return prompts


def parse_json_object(text: str) -> dict[str, Any]:
    raw = (text or "").strip()
    if raw.startswith("```"):
        raw = re.sub(r"^```(?:json)?\s*", "", raw, count=1)
        raw = re.sub(r"\s*```\s*$", "", raw.strip())
    parsed = json.loads(raw)
    if not isinstance(parsed, dict):
        raise CategoryGraphExtractionError("model output must be a JSON object")
    return parsed


def _usage_from_response(response: Any) -> dict[str, int]:
    usage = getattr(response, "usage", None)
    cached = 0
    if usage is not None:
        details = getattr(usage, "input_tokens_details", None)
        if details is not None:
            cached = int(getattr(details, "cached_tokens", 0) or 0)
        return {
            "input_tokens": int(getattr(usage, "input_tokens", 0) or 0),
            "output_tokens": int(getattr(usage, "output_tokens", 0) or 0),
            "cached_tokens": cached,
        }
    return {"input_tokens": 0, "output_tokens": 0, "cached_tokens": 0}


def _canonical_spref(value: str, allowed_span_refs: set[str]) -> str | None:
    raw = (value or "").strip()
    if not raw:
        return None
    candidates = [raw]
    if not raw.startswith("spref:"):
        candidates.append(f"spref:{raw}")
    for cand in candidates:
        if cand in allowed_span_refs:
            return cand
    return None


def _normalize_evidence_refs(
    refs: Any,
    allowed_span_refs: set[str] | None = None,
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    if not isinstance(refs, list):
        return out
    for ref in refs:
        if isinstance(ref, Mapping) and ref.get("source_span_ref_id"):
            spref = str(ref["source_span_ref_id"])
            if allowed_span_refs is not None:
                canonical = _canonical_spref(spref, allowed_span_refs)
                if not canonical and spref in allowed_span_refs:
                    canonical = spref
                if not canonical:
                    for cand in (spref, f"spref:{spref}"):
                        if cand in allowed_span_refs:
                            canonical = cand
                            break
                if canonical:
                    entry: dict[str, Any] = {"source_span_ref_id": canonical}
                    quotes = coerce_anchor_quotes(ref.get("anchor_quotes"))
                    if quotes:
                        entry["anchor_quotes"] = quotes
                    out.append(entry)
            else:
                entry = {"source_span_ref_id": spref}
                quotes = coerce_anchor_quotes(ref.get("anchor_quotes"))
                if quotes:
                    entry["anchor_quotes"] = quotes
                out.append(entry)
    return out


def _normalize_node(raw: Mapping[str, Any], default_type: str) -> dict[str, Any]:
    node_id = str(raw.get("node_id") or "").strip() or f"node:{ir.normalize_label(str(raw.get('label', 'unknown')))}"
    return {
        "node_id": node_id,
        "label": str(raw.get("label") or "").strip() or node_id,
        "node_type": str(raw.get("node_type") or default_type),
        "description": str(raw.get("description") or "").strip() or None,
        "importance": str(raw.get("importance") or "medium"),
        "semantic_state": dict(DEFAULT_SEMANTIC_STATE),
        "evidence_refs": _normalize_evidence_refs(raw.get("evidence_refs")),
        "proposed_action": "create",
        "confidence": str(raw.get("confidence") or "medium"),
        "warnings": list(raw.get("warnings") or []),
        "corpus_ref": raw.get("corpus_ref"),
    }


def _normalize_beat(raw: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "beat_id": str(raw.get("beat_id") or "beat:unknown"),
        "order": int(raw.get("order") or 1),
        "title": str(raw.get("title") or ""),
        "summary": str(raw.get("summary") or ""),
        "involved_node_ids": [str(x) for x in (raw.get("involved_node_ids") or [])],
        "evidence_refs": _normalize_evidence_refs(raw.get("evidence_refs")),
        "proposed_action": "create",
        "warnings": list(raw.get("warnings") or []),
    }


def _normalize_edge(raw: Mapping[str, Any]) -> dict[str, Any]:
    relationship_type = str(raw.get("relationship_type") or "").strip().lower()
    predicate_family = str(raw.get("predicate_family") or "").strip()
    if relationship_type and not predicate_family:
        predicate_family = predicate_family_for_type(relationship_type)

    warnings = [str(w) for w in (raw.get("warnings") or [])]
    for code in validate_edge_predicate(relationship_type, predicate_family):
        marker = f"predicate_validation:{code}"
        if marker not in warnings:
            warnings.append(marker)

    return {
        "edge_id": str(raw.get("edge_id") or "edge:unknown"),
        "from_node_id": str(raw.get("from_node_id") or ""),
        "to_node_id": str(raw.get("to_node_id") or ""),
        "label": str(raw.get("label") or ""),
        "relationship_type": relationship_type,
        "predicate_family": predicate_family,
        "semantic_state": dict(DEFAULT_SEMANTIC_STATE),
        "evidence_refs": _normalize_evidence_refs(raw.get("evidence_refs")),
        "proposed_action": "create",
        "confidence": str(raw.get("confidence") or "medium"),
        "warnings": warnings,
    }


def _normalize_disposition(raw: Mapping[str, Any], prefix: str) -> dict[str, Any]:
    out: dict[str, Any] = {
        "item_id": str(raw.get("item_id") or f"{prefix}:unknown"),
        "label": str(raw.get("label") or ""),
        "reason": str(raw.get("reason") or ""),
        "evidence_refs": _normalize_evidence_refs(raw.get("evidence_refs")),
        "warnings": list(raw.get("warnings") or []),
    }
    if raw.get("suggested_next_step"):
        out["suggested_next_step"] = str(raw.get("suggested_next_step"))
    return out


def consolidate_category_outputs(
    pass_outputs: Mapping[str, Mapping[str, Any]],
    *,
    campaign_id: str,
    session: int,
) -> dict[str, Any]:
    party_ctx = build_party_context_for_campaign(campaign_id, session)
    per_pass_counts: dict[str, int] = {}
    nodes: list[dict[str, Any]] = []
    beats: list[dict[str, Any]] = []
    ignored: list[dict[str, Any]] = []
    deferred: list[dict[str, Any]] = []

    for pass_name, default_type, _ in NODE_EXTRACTION_PASSES:
        payload = pass_outputs.get(pass_name, {})
        raw_nodes = payload.get("observation_nodes") or []
        per_pass_counts[pass_name] = len(raw_nodes)
        for raw in raw_nodes:
            if isinstance(raw, Mapping):
                nodes.append(_normalize_node(raw, default_type))
        if pass_name == "thread_pass":
            for raw in payload.get("ignored_items") or []:
                if isinstance(raw, Mapping):
                    ignored.append(_normalize_disposition(raw, "ignored"))
            for raw in payload.get("deferred_items") or []:
                if isinstance(raw, Mapping):
                    deferred.append(_normalize_disposition(raw, "deferred"))

    beat_payload = pass_outputs.get(BEAT_PASS_NAME, {})
    raw_beats = beat_payload.get("observation_beats") or []
    per_pass_counts[BEAT_PASS_NAME] = len(raw_beats)
    for raw in raw_beats:
        if isinstance(raw, Mapping):
            beats.append(_normalize_beat(raw))

    nodes_before_dedup = len(nodes)
    node_dedup = ir.dedup_nodes(nodes)
    deduped_nodes = list(node_dedup["kept"])
    deduped_nodes, anchor_merge_diag = merge_party_anchor_nodes(
        deduped_nodes,
        party_ctx,
        default_semantic_state=DEFAULT_SEMANTIC_STATE,
    )
    # One observation pass per node type means a single proper noun can surface
    # as both a place and a polity (e.g. "Mireward Reach" as location AND
    # organization). dedup_nodes keys on (type_class, label) and keeps both,
    # which makes endpoint binding ambiguous downstream. Collapse exact-label
    # collisions across type classes into one canonical node and remap edges.
    cross_class = ir.reconcile_cross_class_label_collisions(deduped_nodes)
    deduped_nodes = list(cross_class["kept"])
    cross_class_remap: dict[str, str] = cross_class["remap"]

    edge_payload = pass_outputs.get(EDGE_PASS_NAME, {})
    raw_edges = edge_payload.get("observation_edges") or []
    per_pass_counts[EDGE_PASS_NAME] = len(raw_edges)
    node_ids = {n["node_id"] for n in deduped_nodes}
    edges: list[dict[str, Any]] = []
    dropped_edges: list[dict[str, str]] = []
    for raw in raw_edges:
        if not isinstance(raw, Mapping):
            continue
        edge = _normalize_edge(raw)
        edge["from_node_id"] = cross_class_remap.get(edge["from_node_id"], edge["from_node_id"])
        edge["to_node_id"] = cross_class_remap.get(edge["to_node_id"], edge["to_node_id"])
        if edge["from_node_id"] in node_ids and edge["to_node_id"] in node_ids:
            edges.append(edge)
        else:
            dropped_edges.append(
                {
                    "edge_id": edge["edge_id"],
                    "from_node_id": edge["from_node_id"],
                    "to_node_id": edge["to_node_id"],
                }
            )
    deduped_nodes, edges, party_collective_diag = merge_party_collective(
        deduped_nodes,
        edges,
        party_ctx,
        default_semantic_state=DEFAULT_SEMANTIC_STATE,
    )
    edge_dedup = ir.dedup_edges(edges, deduped_nodes)
    edge_predicate_issues = [
        {
            "edge_id": edge["edge_id"],
            "relationship_type": edge.get("relationship_type"),
            "predicate_family": edge.get("predicate_family"),
            "issues": [
                w.removeprefix("predicate_validation:")
                for w in edge.get("warnings", [])
                if str(w).startswith("predicate_validation:")
            ],
        }
        for edge in edges
        if any(str(w).startswith("predicate_validation:") for w in edge.get("warnings", []))
    ]

    session_ctx = build_session_graph_context(campaign_id, session)
    diagnostics = {
        "per_pass_counts": per_pass_counts,
        "nodes_before_dedup": nodes_before_dedup,
        "party_companion_slugs": [m.slug for m in party_ctx.companions()],
        "merged_nodes": node_dedup["merged"],
        "cross_class_merged_nodes": cross_class["merged"],
        "cross_class_blocked_nodes": cross_class.get("blocked", []),
        "merged_edges": edge_dedup["merged"],
        "dropped_edges_missing_endpoints": dropped_edges,
        "edge_predicate_issues": edge_predicate_issues,
        "party_anchor_hub_paths": sorted(party_ctx.anchor_hub_paths()),
        "inserted_party_anchor_slugs": anchor_merge_diag.get("inserted_party_anchor_slugs", []),
        "party_collective_inserted": party_collective_diag.get("party_collective_inserted", False),
        "party_membership_edge_slugs": party_collective_diag.get("party_membership_edge_slugs", []),
        "registry_relpath": session_ctx.registry_relpath,
        "session_graph_context_warnings": list(session_ctx.warnings),
    }
    return {
        "nodes": deduped_nodes,
        "edges": list(edge_dedup["kept"]),
        "beats": beats,
        "ignored_items": ignored,
        "deferred_items": deferred,
        "proposed_writes": [],
        "consolidation_diagnostics": diagnostics,
    }


def repair_edge_evidence_refs(
    parts: Mapping[str, Any],
    allowed_span_refs: set[str],
) -> dict[str, int]:
    node_refs: dict[str, list[dict[str, str]]] = {}
    for node in parts.get("nodes") or []:
        if isinstance(node, Mapping):
            refs = _normalize_evidence_refs(node.get("evidence_refs"), allowed_span_refs)
            if refs:
                node_refs[str(node.get("node_id") or "")] = refs

    repaired = 0
    for edge in parts.get("edges") or []:
        if not isinstance(edge, Mapping):
            continue
        refs = _normalize_evidence_refs(edge.get("evidence_refs"), allowed_span_refs)
        if refs:
            edge["evidence_refs"] = refs
            continue
        from_id = str(edge.get("from_node_id") or "")
        to_id = str(edge.get("to_node_id") or "")
        inherited = node_refs.get(from_id) or node_refs.get(to_id)
        if inherited:
            edge["evidence_refs"] = list(inherited[:1])
            repaired += 1
    return {"repaired_edge_evidence_refs": repaired}


def sanitize_parts(
    parts: Mapping[str, Any],
    allowed_span_refs: set[str],
) -> tuple[dict[str, Any], dict[str, Any]]:
    dropped: dict[str, list[str]] = {}
    out: dict[str, Any] = {}

    def filter_refs(refs: Any) -> list[dict[str, str]]:
        return _normalize_evidence_refs(refs, allowed_span_refs)

    for key in ("nodes", "edges", "beats", "ignored_items", "deferred_items", "proposed_writes"):
        kept: list[Any] = []
        dropped_ids: list[str] = []
        for obj in parts.get(key) or []:
            if not isinstance(obj, Mapping):
                continue
            refs = filter_refs(obj.get("evidence_refs"))
            is_context_anchor = bool(obj.get("context_anchor"))
            has_resolved_corpus = (
                isinstance(obj.get("corpus_ref"), Mapping)
                and obj.get("corpus_ref", {}).get("resolution") == "resolved"
            )
            if (
                key in ("nodes", "edges", "beats")
                and not refs
                and not is_context_anchor
                and not (key == "nodes" and has_resolved_corpus)
            ):
                id_key = next(
                    (k for k in ("node_id", "edge_id", "beat_id", "write_id", "item_id") if k in obj),
                    "id",
                )
                dropped_ids.append(str(obj.get(id_key, "")))
                continue
            clone = dict(obj)
            clone["evidence_refs"] = refs
            kept.append(clone)
        out[key] = kept
        if dropped_ids:
            dropped[key] = dropped_ids
    return out, {"dropped_no_valid_evidence": dropped}


def assemble_envelope(
    consolidated: Mapping[str, Any],
    *,
    campaign_id: str,
    session_id: str,
    source_artifact_id: str,
    model_id: str,
) -> dict[str, Any]:
    graph = {
        "schema": CANDIDATE_GRAPH_SCHEMA,
        "version": CANDIDATE_GRAPH_VERSION,
        "preview_id": f"candidate-preview:{campaign_id}:{session_id}:category",
        "campaign_id": campaign_id,
        "session_id": session_id,
        "source_artifact_ids": [source_artifact_id],
        "status": "preview",
        "nodes": list(consolidated.get("nodes") or []),
        "edges": list(consolidated.get("edges") or []),
        "beats": list(consolidated.get("beats") or []),
        "proposed_writes": list(consolidated.get("proposed_writes") or []),
        "ignored_items": list(consolidated.get("ignored_items") or []),
        "deferred_items": list(consolidated.get("deferred_items") or []),
        "diagnostics": {
            **PREVIEW_DIAGNOSTICS,
            "extraction_performed": True,
            "llm_used": True,
            "runtime_connected": True,
            "extraction_mode": "category_decomposed",
            "model_id": model_id,
            "warning_count": len(
                consolidated.get("consolidation_diagnostics", {}).get("merged_nodes", [])
            ),
        },
    }
    return {
        "schema": ENVELOPE_SCHEMA,
        "version": ENVELOPE_VERSION,
        "candidate_graph": graph,
        "review_sidecar": {
            "high_risk_claims": [],
            "notes": ["assembled deterministically from category passes"],
        },
    }


def edge_vocabulary_ablation_diagnostics(options: CategoryGraphExtractionOptions) -> dict[str, Any]:
    if not options.enable_edge_vocabulary_packet or options.edge_vocabulary_packet is None:
        return {"enabled": False}
    return render_edge_vocabulary_context(options.edge_vocabulary_packet).diagnostics


def build_edge_pass_prompt(
    edge_prompt_template: str,
    nodes: Sequence[Mapping[str, Any]],
    *,
    options: CategoryGraphExtractionOptions,
) -> tuple[str, dict[str, Any]]:
    nodes_json = json.dumps([_edge_prompt_node_summary(n) for n in nodes], indent=2)
    prompt = edge_prompt_template.replace("(injected at runtime)", nodes_json)
    diagnostics = {"enabled": False}
    if options.enable_edge_vocabulary_packet and options.edge_vocabulary_packet is not None:
        edge_vocab_context = render_edge_vocabulary_context(options.edge_vocabulary_packet)
        prompt = f"{prompt}\n\n{edge_vocab_context.context_text}\n"
        diagnostics = edge_vocab_context.diagnostics
    return prompt, diagnostics


def _edge_prompt_node_summary(node: Mapping[str, Any]) -> dict[str, Any]:
    """Compact node payload for edge extraction.

    Edges need more than labels: descriptions and node evidence help the model
    bind endpoints and copy valid quotes without seeing the full candidate graph
    shape. Keep the payload bounded and review-friendly.
    """
    summary: dict[str, Any] = {
        "node_id": node.get("node_id"),
        "label": node.get("label"),
        "node_type": node.get("node_type"),
    }
    description = str(node.get("description") or "").strip()
    if description:
        summary["description"] = description
    evidence_refs = node.get("evidence_refs")
    if evidence_refs:
        summary["evidence_refs"] = evidence_refs
    if node.get("context_anchor"):
        summary["context_anchor"] = True
    return summary


def canonical_graph_for_runner(envelope: Mapping[str, Any]) -> dict[str, Any]:
    """Return candidate graph payload suitable for graph_preview_runner artifacts."""
    graph = dict(envelope.get("candidate_graph") or envelope)
    graph.setdefault("diagnostics", {})
    diag = dict(graph["diagnostics"])
    diag.update(PREVIEW_DIAGNOSTICS)
    graph["diagnostics"] = diag
    return graph


class OpenAICategoryGraphPassClient:
    def run_pass(
        self,
        pass_name: str,
        *,
        model_id: str,
        instructions: str,
        user_content: str,
    ) -> dict[str, Any]:
        from src.graph_memory.extraction.category_candidate_graph_schema import (
            category_pass_text_format,
        )

        load_dungeonmindbuddy_dotenv()
        if not os.environ.get("OPENAI_API_KEY"):
            raise CategoryGraphExtractionError(
                "OPENAI_API_KEY is not configured; supply candidate_graph_path or disable graph extraction."
            )
        from openai import OpenAI

        from src.agent.planner_pricing import usage_cost_usd

        client = OpenAI()
        t0 = time.perf_counter()
        response = client.responses.create(
            model=model_id.strip(),
            instructions=instructions,
            input=[{"type": "message", "role": "user", "content": user_content}],
            text=category_pass_text_format(pass_name),
        )
        elapsed_ms = round((time.perf_counter() - t0) * 1000.0, 2)
        refusal = getattr(response, "refusal", None)
        if refusal:
            raise CategoryGraphExtractionError(
                f"model refused {pass_name}: {refusal}",
                pass_name=pass_name,
            )
        if getattr(response, "status", None) == "incomplete":
            raw = getattr(response, "output_text", None) or response.model_dump_json()
            raise CategoryGraphExtractionError(
                f"model response incomplete for {pass_name}",
                pass_name=pass_name,
                raw_model_response=str(raw),
            )
        raw_text = (getattr(response, "output_text", None) or "").strip()
        usage = _usage_from_response(response)
        cost_info = usage_cost_usd(
            model_id=model_id.strip(),
            input_tokens=usage["input_tokens"],
            output_tokens=usage["output_tokens"],
            cached_tokens=usage["cached_tokens"],
        )
        try:
            parsed = parse_json_object(raw_text) if raw_text else {}
        except json.JSONDecodeError as exc:
            raise CategoryGraphExtractionError(
                f"{pass_name} returned invalid JSON: {exc.msg}",
                pass_name=pass_name,
                raw_model_response=raw_text,
            ) from exc
        return {
            "parsed": parsed,
            "raw_text": raw_text,
            "usage": usage,
            "cost_usd": float(cost_info.get("total_usd") or 0.0),
            "cost_info": cost_info,
            "elapsed_ms": elapsed_ms,
            "response_id": str(getattr(response, "id", "") or ""),
        }


class FixtureCategoryGraphPassClient:
    """Deterministic pass outputs for tests (pass_name -> parsed JSON)."""

    def __init__(self, pass_outputs: Mapping[str, Mapping[str, Any]]):
        self._pass_outputs = {k: dict(v) for k, v in pass_outputs.items()}

    def run_pass(
        self,
        pass_name: str,
        *,
        model_id: str,
        instructions: str,
        user_content: str,
    ) -> dict[str, Any]:
        return {
            "parsed": dict(self._pass_outputs.get(pass_name, {})),
            "raw_text": json.dumps(self._pass_outputs.get(pass_name, {})),
            "usage": {"input_tokens": 0, "output_tokens": 0, "cached_tokens": 0},
            "cost_usd": 0.0,
            "cost_info": {},
            "elapsed_ms": 0.0,
            "response_id": f"fixture-{pass_name}",
        }


def run_category_pipeline(
    client: CategoryGraphPassClient,
    options: CategoryGraphExtractionOptions,
    *,
    progress_callback: Any | None = None,
) -> CategoryGraphExtractionResult:
    model_id = resolve_category_graph_model(options.model_id)
    source_rows = source_packet_rows_from_span_index(options.source_span_index)
    allowed_span_refs = {r["source_span_ref_id"] for r in source_rows}
    for span in options.source_span_index.get("spans") or []:
        if isinstance(span, Mapping):
            for key in ("source_span_ref_id", "span_id"):
                val = span.get(key)
                if isinstance(val, str):
                    allowed_span_refs.add(val)

    party_ctx = build_party_context_for_campaign(
        options.campaign_id, options.session_number
    )
    prompts = render_category_pass_prompts(source_rows, party_ctx=party_ctx)
    pass_outputs: dict[str, dict[str, Any]] = {}
    pass_telemetry: dict[str, Any] = {}
    total_cost = 0.0
    system = "Category-decomposed graph memory extraction."

    def _notify(pass_name: str, state: str) -> None:
        if progress_callback is not None:
            progress_callback(pass_name, state)

    for pass_name, _default_type, _instruction in NODE_EXTRACTION_PASSES:
        _notify(pass_name, "running")
        result = client.run_pass(
            pass_name,
            model_id=model_id,
            instructions=system,
            user_content=prompts[_prompt_key(pass_name)],
        )
        pass_outputs[pass_name] = result["parsed"]
        pass_telemetry[pass_name] = {
            "cost_usd": result["cost_usd"],
            "usage": result["usage"],
            "elapsed_ms": result["elapsed_ms"],
            "response_id": result["response_id"],
            "progress_label": PASS_PROGRESS_LABELS.get(pass_name, pass_name),
        }
        total_cost += result["cost_usd"]
        _notify(pass_name, "complete")

    _notify(BEAT_PASS_NAME, "running")
    beat_result = client.run_pass(
        BEAT_PASS_NAME,
        model_id=model_id,
        instructions=system,
        user_content=prompts[_prompt_key(BEAT_PASS_NAME)],
    )
    pass_outputs[BEAT_PASS_NAME] = beat_result["parsed"]
    pass_telemetry[BEAT_PASS_NAME] = {
        "cost_usd": beat_result["cost_usd"],
        "usage": beat_result["usage"],
        "elapsed_ms": beat_result["elapsed_ms"],
        "response_id": beat_result["response_id"],
        "progress_label": PASS_PROGRESS_LABELS[BEAT_PASS_NAME],
    }
    total_cost += beat_result["cost_usd"]
    _notify(BEAT_PASS_NAME, "complete")

    consolidated = consolidate_category_outputs(
        pass_outputs,
        campaign_id=options.campaign_id,
        session=options.session_number,
    )
    edge_prompt, edge_vocabulary_diag = build_edge_pass_prompt(
        prompts[_prompt_key(EDGE_PASS_NAME)],
        consolidated["nodes"],
        options=options,
    )
    _notify(EDGE_PASS_NAME, "running")
    edge_result = client.run_pass(
        EDGE_PASS_NAME,
        model_id=model_id,
        instructions=system,
        user_content=edge_prompt,
    )
    pass_outputs[EDGE_PASS_NAME] = edge_result["parsed"]
    pass_telemetry[EDGE_PASS_NAME] = {
        "cost_usd": edge_result["cost_usd"],
        "usage": edge_result["usage"],
        "elapsed_ms": edge_result["elapsed_ms"],
        "response_id": edge_result["response_id"],
        "progress_label": PASS_PROGRESS_LABELS[EDGE_PASS_NAME],
    }
    total_cost += edge_result["cost_usd"]
    _notify(EDGE_PASS_NAME, "complete")

    consolidated = consolidate_category_outputs(
        pass_outputs,
        campaign_id=options.campaign_id,
        session=options.session_number,
    )
    repair_diag = repair_edge_evidence_refs(consolidated, allowed_span_refs)
    sanitized, sanitize_diag = sanitize_parts(consolidated, allowed_span_refs)
    merged_diag = {
        **consolidated["consolidation_diagnostics"],
        **repair_diag,
        **sanitize_diag,
    }
    source_artifact_id = f"artifact:recap:{options.campaign_id}:{options.session_id}"
    envelope = assemble_envelope(
        sanitized,
        campaign_id=options.campaign_id,
        session_id=options.session_id,
        source_artifact_id=source_artifact_id,
        model_id=model_id,
    )
    candidate_graph = canonical_graph_for_runner(envelope)
    return CategoryGraphExtractionResult(
        candidate_graph=candidate_graph,
        envelope=envelope,
        pass_outputs=pass_outputs,
        pass_telemetry=pass_telemetry,
        consolidation_diagnostics=merged_diag,
        model_id=model_id,
        total_cost_usd=round(total_cost, 6),
        diagnostics={
            "extraction_mode": "category_decomposed",
            "model_id": model_id,
            "edge_vocabulary_ablation": edge_vocabulary_diag,
            **PREVIEW_DIAGNOSTICS,
        },
    )


def extract_category_candidate_graph(
    options: CategoryGraphExtractionOptions,
    *,
    client: CategoryGraphPassClient | None = None,
    progress_callback: Any | None = None,
) -> CategoryGraphExtractionResult:
    model_client = client or OpenAICategoryGraphPassClient()
    return run_category_pipeline(
        model_client, options, progress_callback=progress_callback
    )
