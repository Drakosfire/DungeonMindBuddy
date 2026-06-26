"""Category-decomposed graph extraction study (S22 proving slice).

Decomposes node discovery into explicit category passes (actors, locations,
collectives, objects, threads/phenomena, beats), then a durable-edge pass and
deterministic assembly into the live-extractor envelope. Party-member anchors
come from ``PartyContext`` — not from model discovery.
"""
from __future__ import annotations

import json
import re
import time
from datetime import date
from pathlib import Path
from typing import Any, Mapping, Sequence

from evals.graph_memory_layer import live_recap_ingest_run_bundle as ingest_bundle
from evals.graph_memory_layer.live_extractor_prompt_harness import (
    source_packet_rows,
    verify_run_bundle_and_source,
)
from evals.graph_memory_layer.live_vs_gold_compare import compare_parts, parts_from_raw_graph
from evals.graph_memory_layer.reconcile_live_candidate import (
    ENVELOPE_SCHEMA,
    ENVELOPE_VERSION,
    DEFAULT_SEMANTIC_STATE,
    validate_live_candidate_output,
)
from evals.graph_memory_layer.session_22_candidate_graph_gold_fixture import (
    GOLD_FIXTURE_ID as S22_GOLD_FIXTURE_ID,
    load_gold_candidate_graph_dict,
)
from evals.graph_memory_layer.session_22_recap_ingest_fixture import (
    NORMALIZED_RECAP_REL,
    load_manifest as load_s22_recap_manifest,
    load_source_span_seed_refs as load_s22_source_span_seed_refs,
    normalized_recap_path,
)
from src.graph_memory import identity_resolution as ir
from src.graph_memory.party_context import build_party_context

STUDY_SCHEMA = "dmb_category_graph_model_study_v0"
STUDY_VERSION = "0.1"
ARTIFACTS_REL = "evals/graph_memory_layer/artifacts/category_graph_model_study"
DEFAULT_MODELS = ("gpt-5.4", "gpt-5.4-mini", "gpt-5.3-codex")
S22_COMPARISON_ID = "graph-memory:category-graph-study:session-22:v0"

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

BEAT_PASS_NAME = "beat_pass"
EDGE_PASS_NAME = "edge_pass"


def _prompt_key(pass_name: str) -> str:
    return f"{pass_name}.md"

EVIDENCE_RULE = (
    "Every positive object MUST include evidence_refs as an array of objects with ONLY: "
    '{"source_span_ref_id": "<spref from source packet>"}. '
    "Do not invent anchor ids or line numbers."
)


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _slug_model(model_id: str) -> str:
    return re.sub(r"[^a-zA-Z0-9]+", "-", model_id.strip()).strip("-").lower()


def artifacts_dir_for_today() -> Path:
    return repo_root() / ARTIFACTS_REL / date.today().isoformat()


def s22_run_bundle_dir() -> Path:
    return repo_root() / "evals/graph_memory_layer/runs/live_recap_ingest/session_22_category_study"


def ensure_s22_run_bundle(*, allow_overwrite: bool = False) -> Path:
    """Build or refresh the S22 recap ingest run bundle from the normalized corpus recap."""
    out = s22_run_bundle_dir()
    manifest = load_s22_recap_manifest()
    recap_path = normalized_recap_path(manifest)
    rel_recap = NORMALIZED_RECAP_REL
    if out.is_dir() and any(out.iterdir()) and not allow_overwrite:
        return out
    bundle = ingest_bundle.build_bundle(
        campaign_id="longmont-c2",
        session_id="session-22",
        input_path=recap_path,
        source_label="Session 22 — Mireward Road and Lysandro",
        run_id="graph-memory:live-recap-ingest:session-22:category-study-v0",
        input_path_record=rel_recap,
        allow_corpus_input=True,
    )
    ingest_bundle.write_run_bundle(
        bundle,
        out,
        allow_overwrite=allow_overwrite,
        allow_example_output=False,
    )
    return out


def verified_s22_source() -> dict[str, Any]:
    bundle_dir = ensure_s22_run_bundle()
    recap = normalized_recap_path()
    return verify_run_bundle_and_source(bundle_dir, recap)


def _source_packet_md(rows: Sequence[Mapping[str, Any]]) -> str:
    parts: list[str] = []
    for r in rows:
        parts.append(
            f"### {r['source_span_ref_id']} / {r['source_unit_id']} / lines {r['line_start']}-{r['line_end']}\n\n"
            f"```text\n{r['text']}\n```"
        )
    return "\n\n".join(parts)


def _party_anchors_block(session: int) -> str:
    ctx = build_party_context(session)
    lines = [
        "## Party anchors (deterministic — do not re-extract as session-novel nodes)",
        f"Party names: {', '.join(ctx.party_names) or 'none'}",
        "",
    ]
    for m in ctx.members:
        lines.append(
            f"- {m.kind} `{m.slug}`: {m.display_name} | hub={m.hub_rel_path} | corpus_ref={json.dumps(m.corpus_ref())}"
        )
    return "\n".join(lines)


def render_category_pass_prompts(verified: Mapping[str, Any], session: int = 22) -> dict[str, str]:
    rows = list(source_packet_rows(verified))
    src = _source_packet_md(rows)
    anchors = _party_anchors_block(session)
    safety = (
        "Return ONLY valid JSON. Preview-only graph memory extraction. "
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
        prompts[f"{pass_name}.md"] = (
            f"# Category Graph Study — {pass_name}\n\n{safety}\n\n{anchors}\n\n"
            f"## Task\n\n{instruction}\n\n"
            f"Default node_type for this pass: `{default_type}`.\n\n"
            f"Return JSON with key `observation_nodes` (array). Each node: "
            f"`node_id`, `label`, `node_type`, `description`, `importance` (high|medium|low), `evidence_refs`.\n"
            f"{EVIDENCE_RULE}{extra}\n\n## Source Packet\n\n{src}\n"
        )
    prompts[f"{BEAT_PASS_NAME}.md"] = (
        f"# Category Graph Study — {BEAT_PASS_NAME}\n\n{safety}\n\n"
        "## Task\n\nExtract source-local beats (scenes, topic shifts, durable claims). "
        "Return JSON with key `observation_beats` (array). Each beat: "
        "`beat_id`, `order` (positive int), `title`, `summary`, `involved_node_ids` (may be empty), `evidence_refs`.\n"
        f"{EVIDENCE_RULE}\n\n## Source Packet\n\n{src}\n"
    )
    prompts[f"{EDGE_PASS_NAME}.md"] = (
        f"# Category Graph Study — {EDGE_PASS_NAME}\n\n{safety}\n\n"
        "## Task\n\nUsing ONLY the consolidated node list supplied below, propose durable relationship edges. "
        "Do NOT create new nodes. Return JSON with key `observation_edges` (array). "
        "Each edge: `edge_id`, `from_node_id`, `to_node_id`, `label`, `relationship_type`, `evidence_refs`.\n"
        f"{EVIDENCE_RULE}\n\n## Consolidated nodes\n\n"
        "(injected at runtime)\n"
    )
    return prompts


def parse_json_object(text: str) -> dict[str, Any]:
    raw = (text or "").strip()
    if raw.startswith("```"):
        raw = re.sub(r"^```(?:json)?\s*", "", raw, count=1)
        raw = re.sub(r"\s*```\s*$", "", raw.strip())
    return json.loads(raw)


def usage_from_response(response: Any) -> dict[str, int]:
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


def call_json_pass(
    client: Any,
    model_id: str,
    *,
    instructions: str,
    user_content: str,
) -> dict[str, Any]:
    from src.agent.planner_pricing import usage_cost_usd

    t0 = time.perf_counter()
    response = client.responses.create(
        model=model_id.strip(),
        instructions=instructions,
        input=[{"type": "message", "role": "user", "content": user_content}],
    )
    elapsed_ms = round((time.perf_counter() - t0) * 1000.0, 2)
    raw_text = (getattr(response, "output_text", None) or "").strip()
    usage = usage_from_response(response)
    cost_info = usage_cost_usd(
        model_id=model_id.strip(),
        input_tokens=usage["input_tokens"],
        output_tokens=usage["output_tokens"],
        cached_tokens=usage["cached_tokens"],
    )
    parsed = parse_json_object(raw_text) if raw_text else {}
    return {
        "parsed": parsed,
        "raw_text": raw_text,
        "usage": usage,
        "cost_usd": float(cost_info.get("total_usd") or 0.0),
        "cost_info": cost_info,
        "elapsed_ms": elapsed_ms,
        "response_id": str(getattr(response, "id", "") or ""),
    }


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


def _normalize_evidence_refs(refs: Any, allowed_span_refs: set[str] | None = None) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    if not isinstance(refs, list):
        return out
    for ref in refs:
        if isinstance(ref, Mapping) and ref.get("source_span_ref_id"):
            spref = str(ref["source_span_ref_id"])
            if allowed_span_refs is not None:
                canonical = _canonical_spref(spref, allowed_span_refs)
                if canonical:
                    out.append({"source_span_ref_id": canonical})
            else:
                out.append({"source_span_ref_id": spref})
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
    return {
        "edge_id": str(raw.get("edge_id") or "edge:unknown"),
        "from_node_id": str(raw.get("from_node_id") or ""),
        "to_node_id": str(raw.get("to_node_id") or ""),
        "label": str(raw.get("label") or ""),
        "relationship_type": str(raw.get("relationship_type") or "associated_with"),
        "semantic_state": dict(DEFAULT_SEMANTIC_STATE),
        "evidence_refs": _normalize_evidence_refs(raw.get("evidence_refs")),
        "proposed_action": "create",
        "confidence": str(raw.get("confidence") or "medium"),
        "warnings": list(raw.get("warnings") or []),
    }


def _normalize_disposition(raw: Mapping[str, Any], prefix: str) -> dict[str, Any]:
    return {
        "item_id": str(raw.get("item_id") or f"{prefix}:unknown"),
        "label": str(raw.get("label") or ""),
        "reason": str(raw.get("reason") or ""),
        "evidence_refs": _normalize_evidence_refs(raw.get("evidence_refs")),
        "warnings": list(raw.get("warnings") or []),
        **({"suggested_next_step": str(raw.get("suggested_next_step"))} if raw.get("suggested_next_step") else {}),
    }


def consolidate_category_outputs(
    pass_outputs: Mapping[str, Mapping[str, Any]],
    *,
    session: int = 22,
) -> dict[str, Any]:
    """Merge category pass JSON into graph parts + consolidation diagnostics."""
    party_ctx = build_party_context(session)
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
    edge_dedup = ir.dedup_edges(edges, deduped_nodes)

    diagnostics = {
        "per_pass_counts": per_pass_counts,
        "nodes_before_dedup": nodes_before_dedup,
        "party_companion_slugs": [m.slug for m in party_ctx.companions()],
        "merged_nodes": node_dedup["merged"],
        "merged_edges": edge_dedup["merged"],
        "dropped_edges_missing_endpoints": dropped_edges,
        "party_anchor_hub_paths": sorted(party_ctx.anchor_hub_paths()),
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


def repair_edge_evidence_refs(parts: Mapping[str, Any], allowed_span_refs: set[str]) -> dict[str, int]:
    """When edge sprefs are hallucinated, inherit one valid ref from an endpoint node."""
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


def sanitize_parts(parts: Mapping[str, Any], allowed_span_refs: set[str]) -> tuple[dict[str, Any], dict[str, Any]]:
    """Drop unknown evidence refs; remove objects with no valid evidence after filtering."""
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
            if key in ("nodes", "edges", "beats") and not refs:
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
    campaign_id: str = "longmont-c2",
    session_id: str = "session-22",
    source_artifact_id: str = "source-artifact:session-22-normalized-recap",
) -> dict[str, Any]:
    graph = {
        "schema": "dmb_candidate_graph_preview_v0",
        "version": "0.1",
        "preview_id": f"candidate-preview:{campaign_id}:{session_id}:category-study",
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
            "preview_only": True,
            "extraction_performed": False,
            "llm_used": False,
            "runtime_connected": False,
            "plan_connected": False,
            "agent_interaction_connected": False,
            "corpus_scanned": False,
            "corpus_mutated": False,
            "facts_promoted": False,
            "canon_promoted": False,
            "unresolved_evidence_refs": 0,
            "missing_evidence_objects": 0,
            "warning_count": len(consolidated.get("consolidation_diagnostics", {}).get("merged_nodes", [])),
        },
    }
    return {
        "schema": ENVELOPE_SCHEMA,
        "version": ENVELOPE_VERSION,
        "candidate_graph": graph,
        "review_sidecar": {"high_risk_claims": [], "notes": ["assembled deterministically from category passes"]},
    }


def s22_spref_line_map() -> dict[str, tuple[int, int]]:
    """spref -> (line_start, line_end) from the S22 run-bundle span index."""
    index = json.loads((s22_run_bundle_dir() / "source_span_index.json").read_text(encoding="utf-8"))
    out: dict[str, tuple[int, int]] = {}
    for sp in index.get("spans", []):
        out[sp["source_span_ref_id"]] = (int(sp["line_start"]), int(sp["line_end"]))
    return out


def s22_anchor_line_map() -> dict[str, tuple[int, int]]:
    """curated source_anchor_id -> (line_start, line_end) from the S22 seed refs."""
    seed = load_s22_source_span_seed_refs()
    out: dict[str, tuple[int, int]] = {}
    for sr in seed.get("source_span_refs", []):
        anchor = sr.get("source_anchor_id")
        if anchor:
            out[str(anchor)] = (int(sr["start_line"]), int(sr["end_line"]))
    return out


def _annotate_line_spans(
    parts: Mapping[str, Any],
    spref_map: Mapping[str, tuple[int, int]],
    anchor_map: Mapping[str, tuple[int, int]],
) -> dict[str, Any]:
    """Attach resolved ``source_line_start/end`` to every evidence ref.

    Resolution is addressing-scheme-agnostic: a ref may cite a paragraph
    ``source_span_ref_id`` (autonomous extractor) or a curated
    ``source_anchor_id`` (gold). Either resolves to the same line range, which
    is what ``identity_resolution`` uses as the same-source rescue signal.
    """
    out: dict[str, Any] = {}
    for key, seq in parts.items():
        new_seq = []
        for obj in seq or []:
            clone = dict(obj)
            refs = []
            for ref in clone.get("evidence_refs") or []:
                ref = dict(ref)
                span = None
                spref = ref.get("source_span_ref_id")
                anchor = ref.get("source_anchor_id")
                if spref and spref in spref_map:
                    span = spref_map[spref]
                elif anchor and anchor in anchor_map:
                    span = anchor_map[anchor]
                if span is not None:
                    ref["source_line_start"], ref["source_line_end"] = span
                refs.append(ref)
            clone["evidence_refs"] = refs
            new_seq.append(clone)
        out[key] = new_seq
    return out


def compare_to_s22_gold(envelope: Mapping[str, Any], *, session: int = 22) -> dict[str, Any]:
    gold = load_gold_candidate_graph_dict()
    cand_graph = envelope.get("candidate_graph") or envelope
    spref_map = s22_spref_line_map()
    anchor_map = s22_anchor_line_map()
    cand_parts = _annotate_line_spans(parts_from_raw_graph(cand_graph), spref_map, anchor_map)
    gold_parts = _annotate_line_spans(parts_from_raw_graph(gold), spref_map, anchor_map)

    # Seed deterministic party-companion nodes (Thrin, Lysandra) so standing
    # companions count as present: they are real graph entities supplied from
    # party context, not session-novel extractions the model must rediscover.
    # They dedup-match gold by resolved corpus_ref hub_path.
    party_ctx = build_party_context(session)
    existing_keys = {ir.canonical_node_key(n) for n in cand_parts.get("nodes", [])}
    for member in party_ctx.companions():
        seed = member.seed_node()
        if ir.canonical_node_key(seed) not in existing_keys:
            cand_parts["nodes"].append(seed)

    return compare_parts(
        cand_parts,
        gold_parts,
        gold_fixture_id=S22_GOLD_FIXTURE_ID,
        report_id=S22_COMPARISON_ID,
    )


def run_category_pipeline(
    client: Any,
    model_id: str,
    verified: Mapping[str, Any],
    *,
    session: int = 22,
) -> dict[str, Any]:
    prompts = render_category_pass_prompts(verified, session=session)
    pass_outputs: dict[str, dict[str, Any]] = {}
    pass_telemetry: dict[str, Any] = {}
    total_cost = 0.0

    system = "Category-decomposed graph memory extraction. Return strict JSON only."
    for pass_name, _default_type, _instruction in NODE_EXTRACTION_PASSES:
        result = call_json_pass(client, model_id, instructions=system, user_content=prompts[_prompt_key(pass_name)])
        pass_outputs[pass_name] = result["parsed"]
        pass_telemetry[pass_name] = {
            "cost_usd": result["cost_usd"],
            "usage": result["usage"],
            "elapsed_ms": result["elapsed_ms"],
            "response_id": result["response_id"],
        }
        total_cost += result["cost_usd"]

    beat_result = call_json_pass(client, model_id, instructions=system, user_content=prompts[_prompt_key(BEAT_PASS_NAME)])
    pass_outputs[BEAT_PASS_NAME] = beat_result["parsed"]
    pass_telemetry[BEAT_PASS_NAME] = {
        "cost_usd": beat_result["cost_usd"],
        "usage": beat_result["usage"],
        "elapsed_ms": beat_result["elapsed_ms"],
        "response_id": beat_result["response_id"],
    }
    total_cost += beat_result["cost_usd"]

    consolidated = consolidate_category_outputs(pass_outputs, session=session)
    nodes_json = json.dumps(
        [{"node_id": n["node_id"], "label": n["label"], "node_type": n["node_type"]} for n in consolidated["nodes"]],
        indent=2,
    )
    edge_prompt = prompts[_prompt_key(EDGE_PASS_NAME)].replace("(injected at runtime)", nodes_json)
    edge_result = call_json_pass(client, model_id, instructions=system, user_content=edge_prompt)
    pass_outputs[EDGE_PASS_NAME] = edge_result["parsed"]
    pass_telemetry[EDGE_PASS_NAME] = {
        "cost_usd": edge_result["cost_usd"],
        "usage": edge_result["usage"],
        "elapsed_ms": edge_result["elapsed_ms"],
        "response_id": edge_result["response_id"],
    }
    total_cost += edge_result["cost_usd"]

    consolidated = consolidate_category_outputs(pass_outputs, session=session)
    allowed = {r["source_span_ref_id"] for r in source_packet_rows(verified)}
    repair_diag = repair_edge_evidence_refs(consolidated, allowed)
    sanitized, sanitize_diag = sanitize_parts(consolidated, allowed)
    merged_diag = {
        **consolidated["consolidation_diagnostics"],
        **repair_diag,
        **sanitize_diag,
    }
    bundle = verified["bundle"]
    campaign_id = bundle["run_manifest"]["campaign_id"]
    session_id = bundle["run_manifest"]["session_id"]
    source_artifact_id = "source-artifact:session-22-normalized-recap"
    envelope = assemble_envelope(
        sanitized,
        campaign_id=campaign_id,
        session_id=session_id,
        source_artifact_id=source_artifact_id,
    )

    validation = validate_live_candidate_output(
        envelope,
        run_bundle=s22_run_bundle_dir(),
        allowed_span_refs=allowed,
    )
    comparison = compare_to_s22_gold(envelope)

    return {
        "schema": STUDY_SCHEMA,
        "version": STUDY_VERSION,
        "model_id": model_id,
        "session": session,
        "scenario_estimated_cost_usd": round(total_cost, 6),
        "pass_outputs": pass_outputs,
        "pass_telemetry": pass_telemetry,
        "consolidation_diagnostics": merged_diag,
        "candidate_output": envelope,
        "validation": validation,
        "comparison": comparison,
    }


def write_run_artifacts(result: Mapping[str, Any], out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "candidate_output.json").write_text(
        json.dumps(result["candidate_output"], indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    (out_dir / "pass_outputs.json").write_text(
        json.dumps(result["pass_outputs"], indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    (out_dir / "pass_telemetry.json").write_text(
        json.dumps(result["pass_telemetry"], indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    (out_dir / "consolidation_diagnostics.json").write_text(
        json.dumps(result["consolidation_diagnostics"], indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    (out_dir / "validation_report.json").write_text(
        json.dumps(result["validation"], indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    (out_dir / "comparison_report.json").write_text(
        json.dumps(result["comparison"], indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    summary = {
        "schema": STUDY_SCHEMA,
        "version": STUDY_VERSION,
        "model_id": result["model_id"],
        "session": result["session"],
        "scenario_estimated_cost_usd": result["scenario_estimated_cost_usd"],
        "scores": result["comparison"].get("scores"),
        "canonical_ir_valid": result["validation"].get("canonical_ir_valid"),
    }
    (out_dir / "run_summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    return out_dir
