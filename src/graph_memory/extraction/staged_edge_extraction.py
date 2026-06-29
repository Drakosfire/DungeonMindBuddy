"""Staged edge extraction experiment — relation observe → bind → normalize → assemble.

Experiment-only path: production one-shot ``edge_pass`` remains in
``category_candidate_graph_extractor.run_category_pipeline``.
"""
from __future__ import annotations

import json
import os
import re
import time
from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence

from src.bootstrap_env import load_dungeonmindbuddy_dotenv
from src.graph_memory import identity_resolution as ir
from src.graph_memory.extraction.category_candidate_graph_extractor import (
    CategoryGraphExtractionError,
    EVIDENCE_RULE,
    _edge_prompt_node_summary,
    _normalize_evidence_refs,
    _source_packet_md,
    parse_json_object,
)
from src.graph_memory.predicate_catalog import (
    exact_predicate_ids,
    predicate_family_for_type,
    prompt_markdown,
    validate_edge_predicate,
)

RELATION_OBSERVATION_PASS = "relation_observation_pass"
BINDING_SCORE_THRESHOLD = 0.55
AMBIGUOUS_SCORE_DELTA = 0.05

# Experiment-only token aliases for phrase→node binding (not gold/comparator).
_BINDING_TOKEN_ALIASES: dict[str, set[str]] = {
    "refugees": {"refugees", "survivor", "survivors"},
    "survivor": {"refugees", "survivor", "survivors"},
    "survivors": {"refugees", "survivor", "survivors"},
    "tripod": {"tripod", "tripods"},
    "tripods": {"tripod", "tripods"},
    "meatwings": {"meatwings", "meatwing", "flying"},
    "meatwing": {"meatwings", "meatwing", "flying"},
    "meat": {"meat", "meatwing", "meatwings", "monsters", "monster"},
    "monsters": {"meat", "monsters", "monster", "horde"},
    "monster": {"meat", "monsters", "monster", "horde"},
    "horde": {"horde", "monsters", "wave"},
    "wave": {"horde", "wave", "monsters"},
    "gate": {"gate", "gates"},
    "gates": {"gate", "gates"},
    "wall": {"wall", "walls"},
    "walls": {"wall", "walls"},
    "inn": {"inn", "bed", "room"},
    "bed": {"inn", "bed", "room"},
    "room": {"inn", "bed", "room"},
}

# Common phrase → catalog verb (longer phrases first at runtime).
RELATION_PHRASE_TO_PREDICATE: tuple[tuple[str, str], ...] = (
    ("displaced from", "displaced_from"),
    ("fleeing from", "displaced_from"),
    ("fled from", "displaced_from"),
    ("is mayor of", "governs"),
    ("mayor of", "governs"),
    ("governs", "governs"),
    ("commands", "commands"),
    ("leads", "leads"),
    ("located in", "located_in"),
    ("located at", "located_in"),
    ("part of", "part_of"),
    ("member of", "member_of"),
    ("threatens", "threatens"),
    ("besieges", "besieges"),
    ("attacks", "attacks"),
    ("knows about", "knows_about"),
    ("aware of", "aware_of"),
    ("parent of", "parent_of"),
    ("child of", "child_of"),
    ("carries", "carries"),
    ("reports threat", "reports_threat_in"),
    ("travels to", "travels_to"),
    ("routes to", "routes_to"),
    ("road to", "road_to"),
    ("north of", "north_of"),
    ("same as", "same_as"),
    ("associated with", "associated_with"),
    ("participates in", "participates_in"),
    ("present at", "present_at"),
    ("refers to", "refers_to"),
    ("contains", "contains"),
    ("within", "within"),
)


def relation_observation_json_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "relation_candidates": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "candidate_id": {"type": "string"},
                        "subject_phrase": {"type": "string"},
                        "raw_relation": {"type": "string"},
                        "object_phrase": {"type": "string"},
                        "source_span_ref_id": {"type": "string"},
                        "anchor_quotes": {
                            "type": "array",
                            "items": {"type": "string"},
                        },
                        "rationale": {"type": ["string", "null"]},
                    },
                    "required": [
                        "candidate_id",
                        "subject_phrase",
                        "raw_relation",
                        "object_phrase",
                        "source_span_ref_id",
                        "anchor_quotes",
                        "rationale",
                    ],
                },
            },
        },
        "required": ["relation_candidates"],
    }


def relation_observation_text_format(*, strict: bool = True) -> dict[str, Any]:
    return {
        "format": {
            "type": "json_schema",
            "name": "category_graph_relation_observation_pass",
            "strict": strict,
            "schema": relation_observation_json_schema(),
        }
    }


def _beat_summaries(beats: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for beat in beats:
        out.append(
            {
                "beat_id": beat.get("beat_id"),
                "order": beat.get("order"),
                "title": beat.get("title"),
                "summary": beat.get("summary"),
                "involved_node_ids": list(beat.get("involved_node_ids") or []),
            }
        )
    return out


def build_graph_context_packet(
    *,
    source_rows: Sequence[dict[str, Any]],
    nodes: Sequence[Mapping[str, Any]],
    beats: Sequence[Mapping[str, Any]],
    ignored_items: Sequence[Mapping[str, Any]] | None = None,
    deferred_items: Sequence[Mapping[str, Any]] | None = None,
) -> str:
    """Markdown context for staged relation observation (runs last)."""
    node_summaries = [_edge_prompt_node_summary(n) for n in nodes]
    sections = [
        "## Graph context (constructed before edge closure)",
        "",
        "Use this packet to bind relation phrases to **exact** `node_id` values in later stages.",
        "Do NOT invent new nodes.",
        "",
        "### Consolidated nodes",
        "",
        "```json",
        json.dumps(node_summaries, indent=2),
        "```",
        "",
        "### Beat summaries",
        "",
        "```json",
        json.dumps(_beat_summaries(beats), indent=2),
        "```",
    ]
    if ignored_items:
        sections.extend(
            [
                "",
                "### Ignored items (may contain relation clues)",
                "",
                "```json",
                json.dumps(list(ignored_items), indent=2),
                "```",
            ]
        )
    if deferred_items:
        sections.extend(
            [
                "",
                "### Deferred items",
                "",
                "```json",
                json.dumps(list(deferred_items), indent=2),
                "```",
            ]
        )
    sections.extend(
        [
            "",
            "### Relation affordances (scan systematically)",
            "",
            "- location → location/region: `located_in`, `part_of`, `within`, directional predicates",
            "- character → group/organization: `leads`, `member_of`, `commands`, `governs`",
            "- group/creature → location: `threatens`, `attacks`, `besieges`, `located_in`, `travels_to`",
            "- group → group: `part_of`, `part_of_group`, `contains`",
            "- character → fact/creature: `knows_about`, `aware_of`",
            "- displacement: `displaced_from`, `travels_to`, `routes_to`",
            "",
            prompt_markdown(),
        ]
    )
    return "\n".join(sections)


def render_relation_observation_prompt(
    source_rows: Sequence[dict[str, Any]],
    *,
    nodes: Sequence[Mapping[str, Any]],
    beats: Sequence[Mapping[str, Any]],
    ignored_items: Sequence[Mapping[str, Any]] | None = None,
    deferred_items: Sequence[Mapping[str, Any]] | None = None,
) -> str:
    src = _source_packet_md(source_rows)
    context = build_graph_context_packet(
        source_rows=source_rows,
        nodes=nodes,
        beats=beats,
        ignored_items=ignored_items,
        deferred_items=deferred_items,
    )
    safety = (
        "Preview-only graph memory extraction. "
        "Forbidden: approve memory, commit graph records, promote canon, execute writes."
    )
    return (
        f"# Staged Edge Extraction — {RELATION_OBSERVATION_PASS}\n\n{safety}\n\n"
        "## Task\n\n"
        "Extract **phrase-level relation candidates** from the Source Packet. "
        "Each candidate names subject phrase, raw relation phrase, and object phrase "
        "exactly as supported by a source quote. Do NOT assign `node_id` values yet.\n\n"
        "Scan the full session for durable relationships: location containment, authority, "
        "displacement, threat, knowledge, group composition, and participation.\n\n"
        "Return JSON with key `relation_candidates` (array). Each item: "
        "`candidate_id`, `subject_phrase`, `raw_relation`, `object_phrase`, "
        "`source_span_ref_id`, `anchor_quotes`, `rationale` (nullable).\n\n"
        f"{EVIDENCE_RULE}\n\n"
        f"{context}\n\n"
        "## Source Packet\n\n"
        f"{src}\n"
    )


def normalize_relation_candidate(raw: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "candidate_id": str(raw.get("candidate_id") or "rc:unknown"),
        "subject_phrase": str(raw.get("subject_phrase") or "").strip(),
        "raw_relation": str(raw.get("raw_relation") or "").strip(),
        "object_phrase": str(raw.get("object_phrase") or "").strip(),
        "source_span_ref_id": str(raw.get("source_span_ref_id") or "").strip(),
        "anchor_quotes": [str(q) for q in (raw.get("anchor_quotes") or []) if str(q).strip()],
        "rationale": str(raw.get("rationale") or "").strip() or None,
    }


def _expanded_phrase_tokens(phrase: str) -> set[str]:
    tokens = ir.label_tokens(phrase)
    expanded: set[str] = set(tokens)
    for token in tokens:
        expanded |= _BINDING_TOKEN_ALIASES.get(token, {token})
    return expanded


def phrase_bind_score(phrase: str, label: str) -> float:
    base = ir.label_similarity(phrase, label)
    pt = _expanded_phrase_tokens(phrase)
    lt = ir.label_tokens(label)
    if not pt or not lt:
        return base
    # Avoid bare location labels (e.g. "Edge") winning multi-token group phrases.
    if len(pt) >= 2 and len(lt) == 1 and lt <= pt and len(pt - lt) >= 1:
        base = min(base, 0.5)
    if lt <= pt and len(lt) >= 2:
        return max(base, 0.85)
    inter = len(pt & lt)
    if inter == 0:
        return base
    alias_score = inter / len(pt | lt)
    return max(base, alias_score)


def _phrase_bind_candidates(
    phrase: str,
    nodes: Sequence[Mapping[str, Any]],
    *,
    top_k: int = 3,
) -> list[dict[str, Any]]:
    scored: list[tuple[float, Mapping[str, Any]]] = []
    for node in nodes:
        score = phrase_bind_score(phrase, str(node.get("label") or ""))
        if score <= 0:
            continue
        scored.append((score, node))
    scored.sort(key=lambda x: x[0], reverse=True)
    alts: list[dict[str, Any]] = []
    for score, node in scored[:top_k]:
        alts.append(
            {
                "node_id": node.get("node_id"),
                "label": node.get("label"),
                "node_type": node.get("node_type"),
                "score": round(score, 4),
            }
        )
    return alts


def bind_phrase_to_node(
    phrase: str,
    nodes: Sequence[Mapping[str, Any]],
    *,
    threshold: float = BINDING_SCORE_THRESHOLD,
) -> dict[str, Any]:
    alts = _phrase_bind_candidates(phrase, nodes)
    if not alts:
        return {
            "node_id": None,
            "score": 0.0,
            "binding_status": "unbound",
            "alternatives": [],
        }
    best = alts[0]
    status = "bound"
    if best["score"] < threshold:
        status = "below_threshold"
    elif len(alts) > 1 and (best["score"] - alts[1]["score"]) < AMBIGUOUS_SCORE_DELTA:
        status = "ambiguous"
    return {
        "node_id": best["node_id"] if status == "bound" else None,
        "score": best["score"],
        "binding_status": status,
        "alternatives": alts,
    }


def bind_relation_candidate(
    candidate: Mapping[str, Any],
    nodes: Sequence[Mapping[str, Any]],
    *,
    threshold: float = BINDING_SCORE_THRESHOLD,
) -> dict[str, Any]:
    subject = bind_phrase_to_node(
        str(candidate.get("subject_phrase") or ""),
        nodes,
        threshold=threshold,
    )
    obj = bind_phrase_to_node(
        str(candidate.get("object_phrase") or ""),
        nodes,
        threshold=threshold,
    )
    if subject["binding_status"] == "ambiguous" or obj["binding_status"] == "ambiguous":
        overall = "ambiguous"
    elif subject["binding_status"] in {"unbound", "below_threshold"}:
        overall = "unbound_subject"
    elif obj["binding_status"] in {"unbound", "below_threshold"}:
        overall = "unbound_object"
    else:
        overall = "bound"
    return {
        **dict(candidate),
        "from_node_id": subject["node_id"],
        "to_node_id": obj["node_id"],
        "subject_binding": subject,
        "object_binding": obj,
        "binding_status": overall,
    }


def normalize_raw_relation(raw_relation: str) -> dict[str, Any]:
    raw = (raw_relation or "").strip().lower()
    if not raw:
        return {
            "relationship_type": "",
            "predicate_family": "",
            "predicate_status": "missing_relation",
            "issues": ["missing_relation"],
        }
    catalog = set(exact_predicate_ids())
    if raw in catalog:
        fam = predicate_family_for_type(raw)
        return {
            "relationship_type": raw,
            "predicate_family": fam,
            "predicate_status": "ok",
            "issues": validate_edge_predicate(raw, fam),
        }
    normalized = re.sub(r"[^a-z0-9 ]+", " ", raw)
    normalized = " ".join(normalized.split())
    for phrase, verb in sorted(RELATION_PHRASE_TO_PREDICATE, key=lambda x: -len(x[0])):
        if phrase in normalized or phrase in raw:
            fam = predicate_family_for_type(verb)
            return {
                "relationship_type": verb,
                "predicate_family": fam,
                "predicate_status": "mapped_from_phrase",
                "issues": validate_edge_predicate(verb, fam),
            }
    for verb in catalog:
        if re.search(rf"\b{re.escape(verb.replace('_', ' '))}\b", normalized):
            fam = predicate_family_for_type(verb)
            return {
                "relationship_type": verb,
                "predicate_family": fam,
                "predicate_status": "mapped_from_token",
                "issues": validate_edge_predicate(verb, fam),
            }
        if verb in normalized.replace(" ", "_") or verb.replace("_", " ") in normalized:
            fam = predicate_family_for_type(verb)
            return {
                "relationship_type": verb,
                "predicate_family": fam,
                "predicate_status": "mapped_from_token",
                "issues": validate_edge_predicate(verb, fam),
            }
    return {
        "relationship_type": "",
        "predicate_family": "",
        "predicate_status": "unknown_predicate",
        "issues": ["unknown_predicate"],
    }


def normalize_bound_candidate(bound: Mapping[str, Any]) -> dict[str, Any]:
    pred = normalize_raw_relation(str(bound.get("raw_relation") or ""))
    issues = list(pred.get("issues") or [])
    if bound.get("binding_status") != "bound":
        issues.append(str(bound.get("binding_status")))
    return {
        **dict(bound),
        "relationship_type": pred["relationship_type"],
        "predicate_family": pred["predicate_family"],
        "predicate_status": pred["predicate_status"],
        "predicate_issues": issues,
    }


def assemble_staged_edges(
    normalized_candidates: Sequence[Mapping[str, Any]],
    *,
    allowed_span_refs: set[str] | None = None,
    node_ids: set[str] | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    edges: list[dict[str, Any]] = []
    dropped: list[dict[str, Any]] = []
    drop_counts: dict[str, int] = {}

    def _bump(reason: str) -> None:
        drop_counts[reason] = drop_counts.get(reason, 0) + 1

    for idx, cand in enumerate(normalized_candidates):
        cid = str(cand.get("candidate_id") or f"rc:{idx}")
        binding_status = str(cand.get("binding_status") or "")
        if binding_status != "bound":
            reason = binding_status or "unbound"
            _bump(reason)
            dropped.append({"candidate_id": cid, "reason": reason, "candidate": dict(cand)})
            continue
        rel = str(cand.get("relationship_type") or "")
        fam = str(cand.get("predicate_family") or "")
        issues = [str(i) for i in (cand.get("predicate_issues") or []) if str(i)]
        if not rel or "unknown_predicate" in issues or "missing_relation" in issues:
            _bump("unknown_predicate")
            dropped.append({"candidate_id": cid, "reason": "unknown_predicate", "candidate": dict(cand)})
            continue
        if fam and "relationship_family_mismatch" in issues:
            _bump("family_mismatch")
            dropped.append({"candidate_id": cid, "reason": "family_mismatch", "candidate": dict(cand)})
            continue
        from_id = str(cand.get("from_node_id") or "")
        to_id = str(cand.get("to_node_id") or "")
        if node_ids is not None and (from_id not in node_ids or to_id not in node_ids):
            _bump("endpoint_missing")
            dropped.append({"candidate_id": cid, "reason": "endpoint_missing", "candidate": dict(cand)})
            continue
        refs = _normalize_evidence_refs(
            [
                {
                    "source_span_ref_id": cand.get("source_span_ref_id"),
                    "anchor_quotes": cand.get("anchor_quotes") or [],
                }
            ],
            allowed_span_refs,
        )
        if not refs:
            _bump("missing_evidence")
            dropped.append({"candidate_id": cid, "reason": "missing_evidence", "candidate": dict(cand)})
            continue
        label = (
            f"{cand.get('subject_phrase')} {cand.get('raw_relation')} {cand.get('object_phrase')}"
        ).strip()
        edges.append(
            {
                "edge_id": f"edge:staged:{cid}",
                "from_node_id": from_id,
                "to_node_id": to_id,
                "label": label[:240],
                "relationship_type": rel,
                "predicate_family": fam or predicate_family_for_type(rel),
                "semantic_state": {
                    "lifecycle": "candidate",
                    "canon_status": "preview_only",
                    "memory_status": "uncommitted",
                },
                "evidence_refs": refs,
                "proposed_action": "create",
                "confidence": "medium",
                "warnings": [f"staged_edge:{cand.get('predicate_status')}"],
            }
        )
    return edges, {
        "assembled_edge_count": len(edges),
        "dropped_candidates": dropped,
        "drop_counts_by_reason": drop_counts,
    }


@dataclass
class StagedEdgeExtractionResult:
    edges: list[dict[str, Any]]
    relation_candidates: list[dict[str, Any]]
    bound_candidates: list[dict[str, Any]]
    normalized_candidates: list[dict[str, Any]]
    assembly_diagnostics: dict[str, Any]
    relation_observation_telemetry: dict[str, Any] = field(default_factory=dict)


def run_relation_observation_llm(
    *,
    model_id: str,
    user_content: str,
    instructions: str = "Staged graph edge relation observation.",
) -> dict[str, Any]:
    load_dungeonmindbuddy_dotenv()
    if not os.environ.get("OPENAI_API_KEY"):
        raise CategoryGraphExtractionError(
            "OPENAI_API_KEY is not configured for staged edge extraction."
        )
    from openai import OpenAI

    from src.agent.planner_pricing import usage_cost_usd
    from src.graph_memory.extraction.category_candidate_graph_extractor import (
        _usage_from_response,
    )

    client = OpenAI()
    t0 = time.perf_counter()
    response = client.responses.create(
        model=model_id.strip(),
        instructions=instructions,
        input=[{"type": "message", "role": "user", "content": user_content}],
        text=relation_observation_text_format(),
    )
    elapsed_ms = round((time.perf_counter() - t0) * 1000.0, 2)
    refusal = getattr(response, "refusal", None)
    if refusal:
        raise CategoryGraphExtractionError(
            f"model refused {RELATION_OBSERVATION_PASS}: {refusal}",
            pass_name=RELATION_OBSERVATION_PASS,
        )
    if getattr(response, "status", None) == "incomplete":
        raw = getattr(response, "output_text", None) or response.model_dump_json()
        raise CategoryGraphExtractionError(
            f"model response incomplete for {RELATION_OBSERVATION_PASS}",
            pass_name=RELATION_OBSERVATION_PASS,
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
    parsed = parse_json_object(raw_text) if raw_text else {}
    return {
        "parsed": parsed,
        "usage": usage,
        "cost_usd": float(cost_info.get("total_usd") or 0.0),
        "elapsed_ms": elapsed_ms,
        "response_id": str(getattr(response, "id", "") or ""),
    }


def run_staged_edge_extraction(
    *,
    model_id: str,
    source_rows: Sequence[dict[str, Any]],
    consolidated: Mapping[str, Any],
    allowed_span_refs: set[str] | None = None,
) -> StagedEdgeExtractionResult:
    """Run observe → bind → normalize → assemble on a consolidated graph snapshot."""
    nodes = list(consolidated.get("nodes") or [])
    beats = list(consolidated.get("beats") or [])
    ignored = list(consolidated.get("ignored_items") or [])
    deferred = list(consolidated.get("deferred_items") or [])
    node_ids = {str(n.get("node_id") or "") for n in nodes}

    prompt = render_relation_observation_prompt(
        source_rows,
        nodes=nodes,
        beats=beats,
        ignored_items=ignored,
        deferred_items=deferred,
    )
    llm = run_relation_observation_llm(model_id=model_id, user_content=prompt)
    raw_candidates = llm["parsed"].get("relation_candidates") or []
    relation_candidates = [
        normalize_relation_candidate(raw)
        for raw in raw_candidates
        if isinstance(raw, Mapping)
    ]
    bound_candidates = [bind_relation_candidate(c, nodes) for c in relation_candidates]
    normalized_candidates = [normalize_bound_candidate(b) for b in bound_candidates]
    edges, assembly_diag = assemble_staged_edges(
        normalized_candidates,
        allowed_span_refs=allowed_span_refs,
        node_ids=node_ids,
    )
    return StagedEdgeExtractionResult(
        edges=edges,
        relation_candidates=relation_candidates,
        bound_candidates=bound_candidates,
        normalized_candidates=normalized_candidates,
        assembly_diagnostics=assembly_diag,
        relation_observation_telemetry={
            "cost_usd": llm["cost_usd"],
            "usage": llm["usage"],
            "elapsed_ms": llm["elapsed_ms"],
            "response_id": llm["response_id"],
        },
    )
