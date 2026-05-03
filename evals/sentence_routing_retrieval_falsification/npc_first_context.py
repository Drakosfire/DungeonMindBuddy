"""NPC-first attachment context for Stage B1 (experimental).

Builds ``npc_attachment_context_v1`` sidecars from Stage A event records (line-anchored)
and optional timeline-pass gold (NPC append vs skip). Injects structured fields under
``sentence_unit.routing_context.npc_first_context`` only for units whose recap line span
overlaps an event anchor — PCs are never listed here.
"""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Any, Literal

SCHEMA_NPC_ATTACHMENT_CONTEXT_V1 = "npc_attachment_context_v1"

NpcAttachmentDisposition = Literal["append", "skip_incidental", "unknown"]

DEFAULT_PC_ROUTING_INSTRUCTION = (
    "Do not route to NPC hubs; use NPC names only as context anchors when they explain PC roles "
    "or are the searchable object of a PC action, discovery, relationship, or report."
)


def normalize_eldyrwild_recap_suffix(path: str) -> str:
    """Strip optional ``corpus/eldyrwild-markdown/`` prefix for path equality."""
    p = path.replace("\\", "/").strip()
    prefix = "corpus/eldyrwild-markdown/"
    if p.startswith(prefix):
        return p[len(prefix) :]
    return p


def ranges_overlap_1based(a_start: int, a_end: int, b_start: int, b_end: int) -> bool:
    """Inclusive line ranges overlap."""
    return max(a_start, b_start) <= min(a_end, b_end)


def manifest_pc_slugs_from_hub_manifest(manifest_jsonable: list[dict[str, Any]]) -> set[str]:
    out: set[str] = set()
    for m in manifest_jsonable:
        if not isinstance(m, dict):
            continue
        if str(m.get("subject_class") or "").strip().lower() != "pc":
            continue
        slug = str(m.get("slug") or "").strip()
        if slug:
            out.add(slug)
    return out


def npc_slugs_from_event(ev: dict[str, Any], manifest_pc_slugs: set[str]) -> list[str]:
    """Collect NPC-ish slugs from an event (participants + referenced_slugs minus manifest PCs)."""
    raw: set[str] = set()
    for key in ("participants", "referenced_slugs"):
        for x in ev.get(key) or []:
            s = str(x).strip()
            if s:
                raw.add(s)
    npc = sorted(s for s in raw if s not in manifest_pc_slugs)
    return npc


def load_npc_timeline_alignment_sets(timeline_grading: dict[str, Any]) -> tuple[set[str], set[str]]:
    """From timeline-pass ``grading``, return (npc_append_slugs, npc_skip_slugs) for NPC hubs only."""

    def _is_npc_hub_row(row: dict[str, Any]) -> bool:
        rel = str(row.get("timeline_relative_path") or "").replace("\\", "/")
        return "/NPCs/" in rel

    appends: set[str] = set()
    for row in timeline_grading.get("expected_appends") or []:
        if isinstance(row, dict) and _is_npc_hub_row(row):
            slug = str(row.get("npc_slug") or "").strip()
            if slug:
                appends.add(slug)
    skips: set[str] = set()
    for row in timeline_grading.get("expected_skips") or []:
        if isinstance(row, dict) and _is_npc_hub_row(row):
            slug = str(row.get("npc_slug") or "").strip()
            if slug:
                skips.add(slug)
    return appends, skips


def disposition_for_slug(
    slug: str,
    *,
    append_slugs: set[str],
    skip_slugs: set[str],
) -> NpcAttachmentDisposition:
    if slug in append_slugs:
        return "append"
    if slug in skip_slugs:
        return "skip_incidental"
    return "unknown"


def build_npc_attachment_context_sidecar(
    *,
    scenario_id: str,
    units_json: list[dict[str, Any]],
    parsed_events: list[dict[str, Any]],
    manifest_jsonable: list[dict[str, Any]],
    timeline_grading: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Map overlapping event anchors → unit_ids; attach NPC slugs + per-slug disposition."""
    manifest_pc_slugs = manifest_pc_slugs_from_hub_manifest(manifest_jsonable)
    append_slugs: set[str] = set()
    skip_slugs: set[str] = set()
    if isinstance(timeline_grading, dict) and timeline_grading:
        append_slugs, skip_slugs = load_npc_timeline_alignment_sets(timeline_grading)

    unit_to_slugs: dict[str, set[str]] = defaultdict(set)

    for ev in parsed_events:
        if not isinstance(ev, dict):
            continue
        npc_list = npc_slugs_from_event(ev, manifest_pc_slugs)
        if not npc_list:
            continue
        for anchor in ev.get("source_anchors") or []:
            if not isinstance(anchor, dict):
                continue
            path_a = normalize_eldyrwild_recap_suffix(str(anchor.get("path") or ""))
            try:
                ls = int(anchor.get("line_start") or 0)
                le = int(anchor.get("line_end") or 0)
            except (TypeError, ValueError):
                continue
            if ls < 1 or le < 1:
                continue
            for u in units_json:
                if not isinstance(u, dict):
                    continue
                uid = str(u.get("unit_id") or "").strip()
                if not uid:
                    continue
                path_u = normalize_eldyrwild_recap_suffix(str(u.get("path") or ""))
                if path_a != path_u:
                    continue
                try:
                    us = int(u.get("line_start") or 0)
                    ue = int(u.get("line_end") or us)
                except (TypeError, ValueError):
                    continue
                if ranges_overlap_1based(ls, le, us, ue):
                    unit_to_slugs[uid].update(npc_list)

    by_unit_id: dict[str, Any] = {}
    for uid, slugs in sorted(unit_to_slugs.items()):
        slug_list = sorted(slugs)
        per_npc: dict[str, str] = {}
        for s in slug_list:
            per_npc[s] = disposition_for_slug(s, append_slugs=append_slugs, skip_slugs=skip_slugs)
        if all(per_npc[s] in ("append", "skip_incidental") for s in slug_list):
            summary = "npc_timeline_disposition_known"
        elif any(per_npc[s] == "unknown" for s in slug_list):
            summary = "npc_timeline_disposition_partial_or_unknown"
        else:
            summary = "npc_mentions_only"
        by_unit_id[uid] = {
            "npc_slugs": slug_list,
            "per_npc_attachment": per_npc,
            "npc_attachment_summary": summary,
            "pc_routing_instruction": DEFAULT_PC_ROUTING_INSTRUCTION,
        }

    return {
        "schema": SCHEMA_NPC_ATTACHMENT_CONTEXT_V1,
        "scenario_id": scenario_id,
        "by_unit_id": by_unit_id,
        "meta": {
            "event_count": len(parsed_events),
            "units_with_overlapping_npc_evidence": len(by_unit_id),
            "timeline_gold_loaded": bool(timeline_grading),
        },
    }


def enrich_sentence_units_with_npc_attachment_context(
    units_json: list[dict[str, Any]],
    sidecar: dict[str, Any],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Deep-merge ``by_unit_id`` entries into each unit's ``routing_context.npc_first_context``."""
    by_unit = sidecar.get("by_unit_id") if isinstance(sidecar, dict) else None
    if not isinstance(by_unit, dict):
        by_unit = {}

    out: list[dict[str, Any]] = []
    stats = {
        "units_total": len(units_json),
        "units_enriched": 0,
        "units_with_npc_slugs": 0,
    }
    for u in units_json:
        if not isinstance(u, dict):
            continue
        uid = str(u.get("unit_id") or "").strip()
        ctx = by_unit.get(uid) if uid else None
        if not isinstance(ctx, dict) or not ctx:
            out.append(json.loads(json.dumps(u)))
            continue
        nu = json.loads(json.dumps(u))
        base_rc = nu.get("routing_context")
        npc_blob = {k: v for k, v in ctx.items()}
        if isinstance(base_rc, dict):
            merged_rc = {**base_rc, "npc_first_context": npc_blob}
        else:
            merged_rc = {"npc_first_context": npc_blob}
        nu["routing_context"] = merged_rc
        out.append(nu)
        stats["units_enriched"] += 1
        if ctx.get("npc_slugs"):
            stats["units_with_npc_slugs"] += 1

    return out, stats


def load_npc_attachment_context_sidecar(path: Path) -> dict[str, Any]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("npc_first_context JSON must be an object")
    if raw.get("schema") != SCHEMA_NPC_ATTACHMENT_CONTEXT_V1:
        raise ValueError(
            f"expected schema {SCHEMA_NPC_ATTACHMENT_CONTEXT_V1!r}, got {raw.get('schema')!r}"
        )
    return raw


def build_minimal_session_events_scenario(raw_sentence: dict[str, Any]) -> dict[str, Any]:
    """Shrink-wrap sentence-routing scenario input for ``run_session_events_extraction``."""
    inp = dict(raw_sentence.get("input") or {})
    rel_full = str(inp.get("recap_relative_path") or "").strip()
    prefix = "corpus/eldyrwild-markdown/"
    if rel_full.startswith(prefix):
        recap_for_stage_a = rel_full[len(prefix) :]
    else:
        recap_for_stage_a = rel_full
    manifest = list(inp.get("hub_manifest") or [])
    pc_slugs = sorted(
        str(m.get("slug"))
        for m in manifest
        if isinstance(m, dict) and str(m.get("subject_class") or "").strip().lower() == "pc"
        if str(m.get("slug") or "").strip()
    )
    um = (
        f"Read the recap at `{recap_for_stage_a}` and extract meaningful scene-scale events as "
        "structured event_records. Anchor each event with recap_evidence_span / source_anchors "
        "to recap line ranges. "
        "Use underscore slugs in participants[] and referenced_slugs[] when they match characters "
        "in the recap. "
        f"Known manifest PC slugs (use verbatim when they participate): {', '.join(pc_slugs)}. "
        "Include relevant NPCs and referenced figures as slugs when supported by the recap text."
    )
    sid = str(raw_sentence.get("scenario_id") or "sentence_routing")
    return {
        "schema": "session_events_extraction_v1",
        "scenario_id": f"{sid}_npc_first_stage_a",
        "input": {
            "recap_relative_path": recap_for_stage_a,
            "user_message": um,
        },
        "grading": {},
    }


def default_eldyrwild_corpus_root(repo_root: Path) -> Path:
    return (repo_root / "corpus" / "eldyrwild-markdown").resolve()
