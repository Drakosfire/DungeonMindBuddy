"""Deterministic live extractor output reconciliation (spref -> canonical IR)."""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Mapping

from evals.graph_memory_layer.session_23_candidate_graph_gold_fixture import (
    SOURCE_ARTIFACT_ID as DEFAULT_SOURCE_ARTIFACT_ID,
    SOURCE_REF_ID as DEFAULT_SOURCE_REF_ID,
)
from evals.graph_memory_layer.session_23_recap_ingest_fixture import (
    build_source_span_artifacts as default_build_source_span_artifacts,
)
from src.graph_memory.candidate_graph_preview import (
    CANDIDATE_GRAPH_PREVIEW_SCHEMA,
    CANDIDATE_GRAPH_PREVIEW_VERSION,
    NODE_TYPES,
    candidate_graph_preview_from_dict,
    validate_candidate_graph_preview,
)
from src.graph_memory.anchor_quotes import (
    anchor_quote_matches_to_dicts,
    coerce_anchor_quotes,
    find_anchor_quote_matches,
    quote_found_in_paragraph,
)
from src.graph_memory.source_span import SourceSpanRef, resolve_many_source_span_refs

ENVELOPE_SCHEMA = "dmb_live_extractor_candidate_envelope_v0"
ENVELOPE_VERSION = "0.1"

LEGACY_SECTION_MAP = {
    "candidate_nodes": "nodes",
    "candidate_edges": "edges",
    "session_beats": "beats",
    "unnamed_important_concepts": "nodes",
}

LEGACY_ID_KEYS = {
    "nodes": ("node_id", "candidate_id"),
    "edges": ("edge_id", "candidate_id"),
    "beats": ("beat_id", "candidate_id"),
    "proposed_writes": ("write_id", "candidate_id"),
    "ignored_items": ("item_id", "candidate_id"),
    "deferred_items": ("item_id", "candidate_id"),
}

SEMANTIC_KEYS = ("canon_state", "lifecycle_state", "evidence_role", "authority_state", "visibility_state")
NODE_KEYS = ("node_id", "label", "node_type", "description", "importance", "semantic_state", "evidence_refs", "proposed_action", "confidence", "warnings", "corpus_ref")
EDGE_KEYS = ("edge_id", "from_node_id", "to_node_id", "label", "relationship_type", "semantic_state", "evidence_refs", "proposed_action", "confidence", "warnings")


NODE_TYPE_ALIASES = {
    "person": "character",
    "npc": "character",
    "pc": "character",
    "place": "location",
    "site": "location",
    "org": "faction",
    "organization": "faction",
    "group_of_people": "group",
    "concept": "unknown_important",
    "entity": "unknown_important",
}


def _coerce_node_type(value: str | None) -> str:
    raw = (value or "unknown_important").strip()
    if raw in NODE_TYPES:
        return raw
    return NODE_TYPE_ALIASES.get(raw.lower(), "unknown_important")


def _coerce_semantic_fields(obj: dict[str, Any]) -> dict[str, Any]:
    state = dict(obj.get("semantic_state") or {})
    for key in SEMANTIC_KEYS:
        if key in obj and key not in state:
            state[key] = obj[key]
        if key in obj:
            obj.pop(key, None)
    obj["semantic_state"] = _normalize_semantic_state({"semantic_state": state})
    return obj


def _pick_keys(obj: Mapping[str, Any], keys: tuple[str, ...]) -> dict[str, Any]:
    out = {k: obj[k] for k in keys if k in obj}
    if "warnings" in keys and "warnings" not in out:
        out["warnings"] = list(obj.get("warnings") or obj.get("risk_flags") or [])
    return out


DEFAULT_SEMANTIC_STATE = {
    "canon_state": "candidate_extraction",
    "lifecycle_state": "candidate",
    "evidence_role": "source_evidence",
    "authority_state": "system_derived",
    "visibility_state": "gm_private",
}

FORBIDDEN_OUTPUT_TOKENS = (
    "approved_memory",
    "committed graph",
    "canon promotion",
    "fact promotion",
    "write_execution_result",
    "query_result",
    "runtime_payload",
    "/plan payload",
    "Agent Interaction payload",
    "corpus mutation",
)


class ReconcileError(ValueError):
    pass


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _assert(cond: bool, msg: str) -> None:
    if not cond:
        raise ReconcileError(msg)


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_span_index(run_bundle: Path) -> dict[str, Any]:
    base = run_bundle if run_bundle.is_absolute() else repo_root() / run_bundle
    return _load_json(base / "source_span_index.json")


def _recap_text_for_run_bundle(run_bundle: Path) -> str:
    base = run_bundle if run_bundle.is_absolute() else repo_root() / run_bundle
    manifest = _load_json(base / "run_manifest.json")
    input_rel = str(manifest["source"]["input_path_record"])
    recap_path = Path(input_rel)
    if not recap_path.is_absolute():
        recap_path = repo_root() / recap_path
    return recap_path.read_text(encoding="utf-8")


def _paragraph_text_for_span(recap_text: str, span: Mapping[str, Any]) -> str:
    lines = recap_text.splitlines()
    start = int(span["line_start"])
    end = int(span["line_end"])
    return "\n".join(lines[start - 1 : end])


def _resolve_anchor_quotes_for_ref(
    ref: Mapping[str, Any],
    *,
    paragraph_text: str,
    entity_label: str | None,
) -> tuple[list[str], list[dict[str, Any]]]:
    """Validate model-provided quotes in paragraph; optional label fallback when omitted."""
    quotes = coerce_anchor_quotes(ref.get("anchor_quotes"))
    if quotes:
        for q in quotes:
            if not quote_found_in_paragraph(paragraph_text, q):
                _assert(False, f"invalid_anchor_quote:not_in_paragraph:{q[:96]}")
        matches = find_anchor_quote_matches(paragraph_text, quotes)
        return quotes, anchor_quote_matches_to_dicts(matches)
    if entity_label and quote_found_in_paragraph(paragraph_text, entity_label):
        matches = find_anchor_quote_matches(paragraph_text, [entity_label])
        return [], anchor_quote_matches_to_dicts(matches)
    return [], []


def _source_context_for_bundle(run_bundle: Path) -> tuple[str, str, Any]:
    """Resolve canonical source_ref / artifact ids and span artifacts for a run bundle session."""
    base = run_bundle if run_bundle.is_absolute() else repo_root() / run_bundle
    manifest = _load_json(base / "run_manifest.json")
    session_id = str(manifest.get("session_id") or "")
    if session_id == "session-22":
        from evals.graph_memory_layer.session_22_candidate_graph_gold_fixture import (
            SOURCE_ARTIFACT_ID,
            SOURCE_REF_ID,
        )
        from evals.graph_memory_layer.session_22_recap_ingest_fixture import build_source_span_artifacts

        return SOURCE_REF_ID, SOURCE_ARTIFACT_ID, build_source_span_artifacts
    return DEFAULT_SOURCE_REF_ID, DEFAULT_SOURCE_ARTIFACT_ID, default_build_source_span_artifacts


def span_ref_lookup(span_index: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    return {sp["source_span_ref_id"]: sp for sp in span_index.get("spans", [])}


def extract_envelope(raw: Mapping[str, Any]) -> tuple[Mapping[str, Any], Mapping[str, Any]]:
    if raw.get("schema") == ENVELOPE_SCHEMA and "candidate_graph" in raw:
        sidecar = raw.get("review_sidecar") or {}
        return raw["candidate_graph"], sidecar
    if raw.get("schema") == CANDIDATE_GRAPH_PREVIEW_SCHEMA:
        return raw, {}
    # legacy flat sections
    return raw, {"high_risk_claims": raw.get("high_risk_claims", []), "notes": []}


def _object_id(obj: Mapping[str, Any], section: str) -> str:
    keys = LEGACY_ID_KEYS.get(section, ("candidate_id", "id"))
    for key in keys:
        if obj.get(key):
            return str(obj[key])
    return "<unknown>"


def _normalize_semantic_state(obj: Mapping[str, Any]) -> dict[str, Any]:
    if isinstance(obj.get("semantic_state"), Mapping):
        state = dict(obj["semantic_state"])
        for key, default in DEFAULT_SEMANTIC_STATE.items():
            state.setdefault(key, default)
        return state
    return dict(DEFAULT_SEMANTIC_STATE)


def _upgrade_node(obj: Mapping[str, Any], *, unnamed: bool = False) -> dict[str, Any]:
    node_id = obj.get("node_id") or obj.get("candidate_id") or obj.get("id")
    label = obj.get("label") or obj.get("summary") or str(node_id)
    node_type = obj.get("node_type") or obj.get("candidate_type") or ("unknown_important" if unnamed else "character")
    out: dict[str, Any] = {
        "node_id": node_id,
        "label": label,
        "node_type": node_type,
        "description": obj.get("description") or obj.get("summary"),
        "importance": obj.get("importance") or "medium",
        "semantic_state": _normalize_semantic_state(obj),
        "evidence_refs": list(obj.get("evidence_refs") or []),
        "proposed_action": obj.get("proposed_action") or "create",
        "confidence": obj.get("confidence") or "medium",
        "warnings": list(obj.get("warnings") or obj.get("risk_flags") or []),
    }
    return out


def _upgrade_edge(obj: Mapping[str, Any]) -> dict[str, Any]:
    edge_id = obj.get("edge_id") or obj.get("candidate_id") or obj.get("id")
    return {
        "edge_id": edge_id,
        "from_node_id": obj.get("from_node_id") or obj.get("from_candidate_id"),
        "to_node_id": obj.get("to_node_id") or obj.get("to_candidate_id"),
        "label": obj.get("label") or obj.get("summary") or str(edge_id),
        "relationship_type": obj.get("relationship_type") or obj.get("candidate_type") or "related",
        "semantic_state": _normalize_semantic_state(obj),
        "evidence_refs": list(obj.get("evidence_refs") or []),
        "proposed_action": obj.get("proposed_action") or "create",
        "confidence": obj.get("confidence") or "medium",
        "warnings": list(obj.get("warnings") or obj.get("risk_flags") or []),
    }


def _upgrade_beat(obj: Mapping[str, Any], order: int) -> dict[str, Any]:
    beat_id = obj.get("beat_id") or obj.get("candidate_id") or obj.get("id") or f"beat:{order}"
    return {
        "beat_id": beat_id,
        "order": int(obj.get("order") or order),
        "title": obj.get("title") or obj.get("label") or str(beat_id),
        "summary": obj.get("summary") or obj.get("label") or "",
        "involved_node_ids": list(obj.get("involved_node_ids") or obj.get("involved_candidate_ids") or []),
        "evidence_refs": list(obj.get("evidence_refs") or []),
        "unresolved_thread_node_ids": list(obj.get("unresolved_thread_node_ids") or []),
        "proposed_action": obj.get("proposed_action") or "create",
        "warnings": list(obj.get("warnings") or []),
    }


def _upgrade_write(obj: Mapping[str, Any]) -> dict[str, Any]:
    write_id = obj.get("write_id") or obj.get("candidate_id") or obj.get("id")
    return {
        "write_id": write_id,
        "write_type": obj.get("write_type") or "create_node",
        "target_id": obj.get("target_id") or obj.get("target_candidate_id") or "",
        "label": obj.get("label") or obj.get("summary") or str(write_id),
        "reason": obj.get("reason") or obj.get("summary") or "",
        "evidence_refs": list(obj.get("evidence_refs") or []),
        "status": "pending",
    }


def _upgrade_item(obj: Mapping[str, Any], section: str) -> dict[str, Any]:
    item_id = obj.get("item_id") or obj.get("candidate_id") or obj.get("id")
    return {
        "item_id": item_id,
        "label": obj.get("label") or obj.get("summary") or str(item_id),
        "reason": obj.get("reason") or obj.get("summary") or "",
        "evidence_refs": list(obj.get("evidence_refs") or []),
        "warnings": list(obj.get("warnings") or []),
        **({"suggested_next_step": obj.get("suggested_next_step")} if section == "deferred_items" and obj.get("suggested_next_step") else {}),
    }


def migrate_legacy_to_candidate_graph(raw: Mapping[str, Any]) -> dict[str, Any]:
    if raw.get("schema") == CANDIDATE_GRAPH_PREVIEW_SCHEMA:
        return dict(raw)
    nodes = [n for n in raw.get("nodes", [])]
    edges = [e for e in raw.get("edges", [])]
    beats = [b for b in raw.get("beats", [])]
    if "candidate_nodes" in raw:
        nodes.extend(_upgrade_node(o) for o in raw.get("candidate_nodes", []))
    if "unnamed_important_concepts" in raw:
        nodes.extend(_upgrade_node(o, unnamed=True) for o in raw.get("unnamed_important_concepts", []))
    if "candidate_edges" in raw:
        edges.extend(_upgrade_edge(o) for o in raw.get("candidate_edges", []))
    if "session_beats" in raw:
        beats.extend(_upgrade_beat(o, i + 1) for i, o in enumerate(raw.get("session_beats", [])))
    proposed = [_upgrade_write(w) for w in raw.get("proposed_writes", [])]
    ignored = [_upgrade_item(o, "ignored_items") for o in raw.get("ignored_items", [])]
    deferred = [_upgrade_item(o, "deferred_items") for o in raw.get("deferred_items", [])]
    diagnostics = raw.get("diagnostics") if isinstance(raw.get("diagnostics"), Mapping) else {}
    if not diagnostics:
        diagnostics = {
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
            "warning_count": 0,
        }
    return {
        "schema": CANDIDATE_GRAPH_PREVIEW_SCHEMA,
        "version": CANDIDATE_GRAPH_PREVIEW_VERSION,
        "preview_id": raw.get("preview_id") or "candidate-preview:longmont-c2:session-23:live-extractor",
        "campaign_id": raw.get("campaign_id") or "longmont-c2",
        "session_id": raw.get("session_id") or "session-23",
        "source_artifact_ids": list(raw.get("source_artifact_ids") or [DEFAULT_SOURCE_ARTIFACT_ID]),
        "status": "preview",
        "nodes": nodes,
        "edges": edges,
        "beats": beats,
        "proposed_writes": proposed,
        "ignored_items": ignored,
        "deferred_items": deferred,
        "diagnostics": diagnostics,
    }


def _normalize_spref(value: str, span_lookup: Mapping[str, Mapping[str, Any]]) -> str:
    raw = value.strip()
    if raw in span_lookup:
        return raw
    candidates = [raw]
    if not raw.startswith("spref:"):
        candidates.append(f"spref:{raw}")
    if not raw.startswith("spref:") and re.match(r"session-\d+:", raw):
        candidates.append(f"spref:{raw}")
    for cand in candidates:
        if cand in span_lookup:
            return cand
    return raw


def _spref_from_ref(ref: Any, span_lookup: Mapping[str, Mapping[str, Any]] | None = None) -> str | None:
    if isinstance(ref, str):
        value = ref.strip()
    elif isinstance(ref, Mapping) and ref.get("source_span_ref_id"):
        value = str(ref["source_span_ref_id"]).strip()
    else:
        return None
    if span_lookup is not None:
        return _normalize_spref(value, span_lookup)
    return value


def upgrade_evidence_ref(
    ref: Any,
    *,
    span_lookup: Mapping[str, Mapping[str, Any]],
    resolved: Mapping[tuple[str, int, int], Any],
    label: str | None = None,
    source_ref_id: str = DEFAULT_SOURCE_REF_ID,
    source_artifact_id: str = DEFAULT_SOURCE_ARTIFACT_ID,
    recap_text: str | None = None,
) -> dict[str, Any]:
    spref = _spref_from_ref(ref, span_lookup)
    if spref and spref in span_lookup:
        sp = span_lookup[spref]
        key = (source_ref_id, sp["line_start"], sp["line_end"])
        resolved_ev = resolved.get(key)
        out = {
            "source_ref_id": source_ref_id,
            "source_artifact_id": source_artifact_id,
            "source_span_ref_id": spref,
            "label": label or spref,
            "evidence_role": "source_evidence",
            "can_open_source": bool(resolved_ev and resolved_ev.can_open_source),
            "can_highlight_span": bool(resolved_ev and resolved_ev.can_highlight_span),
        }
        if resolved_ev and resolved_ev.source_anchor_id:
            out["source_anchor_id"] = resolved_ev.source_anchor_id
        if recap_text:
            paragraph = _paragraph_text_for_span(recap_text, sp)
            if isinstance(ref, Mapping):
                anchor_quotes, match_dicts = _resolve_anchor_quotes_for_ref(
                    ref,
                    paragraph_text=paragraph,
                    entity_label=label,
                )
                if anchor_quotes:
                    out["anchor_quotes"] = anchor_quotes
                if match_dicts:
                    out["anchor_quote_matches"] = match_dicts
        elif isinstance(ref, Mapping) and coerce_anchor_quotes(ref.get("anchor_quotes")):
            _assert(False, "invalid_anchor_quote:no_paragraph_text")
        return out
    if isinstance(ref, Mapping) and ref.get("source_ref_id") and ref.get("source_artifact_id"):
        return dict(ref)
    _assert(False, f"unknown_or_incomplete_evidence_ref:{spref or ref}")


def _resolve_span_map(
    span_lookup: Mapping[str, Mapping[str, Any]],
    *,
    source_ref_id: str = DEFAULT_SOURCE_REF_ID,
    source_artifact_id: str = DEFAULT_SOURCE_ARTIFACT_ID,
    build_source_span_artifacts: Any = default_build_source_span_artifacts,
) -> dict[tuple[str, int, int], Any]:
    refs = []
    for sp in span_lookup.values():
        refs.append(
            SourceSpanRef(
                source_ref_id=source_ref_id,
                source_artifact_id=source_artifact_id,
                start_line=sp["line_start"],
                end_line=sp["line_end"],
                label=sp.get("source_span_ref_id"),
                evidence_role="source_evidence",
            )
        )
    text, structured = build_source_span_artifacts()
    resolved_list = resolve_many_source_span_refs(
        refs,
        text_artifacts=text,
        structured_artifacts=structured,
        snippet_max_chars=240,
        context_lines=0,
    )
    out: dict[tuple[str, int, int], Any] = {}
    for sp, ev in zip(span_lookup.values(), resolved_list):
        out[(source_ref_id, sp["line_start"], sp["line_end"])] = ev
    return out


def reconcile_candidate_graph(
    graph: Mapping[str, Any],
    *,
    run_bundle: Path,
    allowed_span_refs: set[str] | None = None,
) -> dict[str, Any]:
    migrated = migrate_legacy_to_candidate_graph(graph)
    span_lookup = span_ref_lookup(load_span_index(run_bundle))
    source_ref_id, source_artifact_id, build_artifacts = _source_context_for_bundle(run_bundle)
    if allowed_span_refs is not None:
        for spref in allowed_span_refs:
            _assert(spref in span_lookup, f"unknown_source_span_ref:{spref}")
    resolved_map = _resolve_span_map(
        span_lookup,
        source_ref_id=source_ref_id,
        source_artifact_id=source_artifact_id,
        build_source_span_artifacts=build_artifacts,
    )
    recap_text = _recap_text_for_run_bundle(run_bundle)

    def upgrade_refs(refs: list[Any], label: str | None = None) -> list[dict[str, Any]]:
        out = []
        for ref in refs or []:
            spref = _spref_from_ref(ref, span_lookup)
            if allowed_span_refs is not None and spref:
                norm = _normalize_spref(spref, span_lookup) if spref not in allowed_span_refs else spref
                _assert(norm in allowed_span_refs, f"unknown_source_span_ref:{spref}")
            out.append(
                upgrade_evidence_ref(
                    ref,
                    span_lookup=span_lookup,
                    resolved=resolved_map,
                    label=label,
                    source_ref_id=source_ref_id,
                    source_artifact_id=source_artifact_id,
                    recap_text=recap_text,
                )
            )
        return out

    result = json.loads(json.dumps(migrated))
    for i, node in enumerate(result.get("nodes", [])):
        cleaned = _pick_keys(_coerce_semantic_fields(dict(node)), NODE_KEYS)
        cleaned["node_type"] = _coerce_node_type(cleaned.get("node_type"))
        cleaned["evidence_refs"] = upgrade_refs(cleaned.get("evidence_refs"), cleaned.get("label"))
        result["nodes"][i] = cleaned
    for i, edge in enumerate(result.get("edges", [])):
        cleaned = _pick_keys(_coerce_semantic_fields(dict(edge)), EDGE_KEYS)
        cleaned["evidence_refs"] = upgrade_refs(cleaned.get("evidence_refs"), cleaned.get("label"))
        result["edges"][i] = cleaned
    for i, beat in enumerate(result.get("beats", [])):
        beat["order"] = beat.get("order") or i + 1
        beat["evidence_refs"] = upgrade_refs(beat.get("evidence_refs"), beat.get("title"))
    for write in result.get("proposed_writes", []):
        write["status"] = "pending"
        write["evidence_refs"] = upgrade_refs(write.get("evidence_refs"), write.get("label"))
    for item in result.get("ignored_items", []):
        item["evidence_refs"] = upgrade_refs(item.get("evidence_refs"), item.get("label"))
    for item in result.get("deferred_items", []):
        item["evidence_refs"] = upgrade_refs(item.get("evidence_refs"), item.get("label"))
    return result


def validate_review_sidecar(sidecar: Mapping[str, Any], allowed_span_refs: set[str] | None = None, span_lookup: Mapping[str, Mapping[str, Any]] | None = None) -> None:
    claims = sidecar.get("high_risk_claims") or []
    _assert(isinstance(claims, list), "high_risk_claims_not_list")
    for claim in claims:
        _assert(isinstance(claim, Mapping), "high_risk_claim_not_object")
        for key in ("risk_type", "unsafe_interpretation", "safe_interpretation"):
            _assert(claim.get(key), f"missing_high_risk_field:{key}")
        refs = claim.get("evidence_refs") or []
        _assert(refs, "high_risk_missing_evidence")
        if allowed_span_refs is not None:
            for ref in refs:
                spref = _spref_from_ref(ref, span_lookup) if span_lookup else _spref_from_ref(ref)
                if spref:
                    _assert(spref in allowed_span_refs, f"unknown_source_span_ref:{spref}")


def validate_live_candidate_output(
    raw: Mapping[str, Any],
    *,
    run_bundle: Path,
    allowed_span_refs: set[str] | None = None,
) -> dict[str, Any]:
    text = json.dumps(raw, sort_keys=True)
    for tok in FORBIDDEN_OUTPUT_TOKENS:
        _assert(tok not in text, f"forbidden_candidate_output:{tok}")
    graph_raw, sidecar = extract_envelope(raw)
    span_lookup = span_ref_lookup(load_span_index(run_bundle))
    validate_review_sidecar(sidecar, allowed_span_refs, span_lookup)
    reconciled = reconcile_candidate_graph(graph_raw, run_bundle=run_bundle, allowed_span_refs=allowed_span_refs)
    preview = candidate_graph_preview_from_dict(reconciled)
    validation = validate_candidate_graph_preview(preview)
    _assert(not validation.issues, f"canonical_ir_issues:{validation.issues}")
    counts = {
        "nodes": len(preview.nodes),
        "edges": len(preview.edges),
        "beats": len(preview.beats),
        "proposed_writes": len(preview.proposed_writes),
        "ignored_items": len(preview.ignored_items),
        "deferred_items": len(preview.deferred_items),
        "high_risk_claims": len(sidecar.get("high_risk_claims") or []),
    }
    return {
        "schema": ENVELOPE_SCHEMA,
        "version": ENVELOPE_VERSION,
        "preview_only": True,
        "canonical_ir_valid": True,
        "candidate_class_counts": counts,
        "evidence_ref_count": validation.evidence_ref_count,
        "resolvable_evidence_ref_count": validation.resolvable_evidence_ref_count,
        "benchmark_comparison_ready": True,
        "reconciled_candidate_graph": reconciled,
        "review_sidecar": sidecar,
    }
