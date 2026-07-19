"""Deterministic known-entity mention matcher.

Longest-match-first, word-boundary, Unicode-normalized. Ambiguous surfaces that
resolve to multiple entities are fail-closed (recorded, not matched).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from src.graph_memory.extraction.known_entity_mention_schema import (
    KnownEntityMention,
    KnownEntityMentionSidecar,
)
from src.graph_memory.extraction.known_entity_registry import (
    KnownEntity,
    KnownEntityRegistry,
    normalize_match_surface,
)


@dataclass(frozen=True)
class _TermIndexEntry:
    surface: str
    normalized: str
    entity: KnownEntity
    match_method: str
    pattern: re.Pattern[str]


def _word_boundary_pattern(surface: str) -> re.Pattern[str]:
    # Match the original surface with flexible punctuation/spacing vs word chars.
    # Use the literal surface for span extraction; IGNORECASE for Latin case folds.
    escaped = re.escape(surface)
    return re.compile(rf"(?<![\w]){escaped}(?![\w])", re.IGNORECASE | re.UNICODE)


def build_term_index(entities: Sequence[KnownEntity]) -> list[_TermIndexEntry]:
    entries: list[_TermIndexEntry] = []
    for entity in entities:
        for surface, method in entity.match_terms:
            normalized = normalize_match_surface(surface)
            if not normalized:
                continue
            entries.append(
                _TermIndexEntry(
                    surface=surface,
                    normalized=normalized,
                    entity=entity,
                    match_method=method,
                    pattern=_word_boundary_pattern(surface),
                )
            )
    # Longest normalized surface first; stable by slug
    entries.sort(key=lambda e: (-len(e.normalized), e.entity.slug, e.surface))
    return entries


def _ambiguous_normalized_terms(entries: Sequence[_TermIndexEntry]) -> set[str]:
    owners: dict[str, set[str]] = {}
    for entry in entries:
        owners.setdefault(entry.normalized, set()).add(entry.entity.slug)
    return {norm for norm, slugs in owners.items() if len(slugs) > 1}


def match_text_mentions(
    text: str,
    *,
    source_span_ref_id: str,
    term_index: Sequence[_TermIndexEntry],
    ambiguous_norms: set[str],
) -> tuple[list[KnownEntityMention], list[str]]:
    if not text:
        return [], []
    occupied: list[tuple[int, int]] = []
    mentions: list[KnownEntityMention] = []
    ambiguous_hits: list[str] = []

    for entry in term_index:
        if entry.normalized in ambiguous_norms:
            # Still detect so we can report the surface, but never emit a mention.
            for match in entry.pattern.finditer(text):
                surface = match.group(0)
                if surface not in ambiguous_hits:
                    ambiguous_hits.append(surface)
            continue
        for match in entry.pattern.finditer(text):
            start, end = match.span()
            if any(start < used_end and end > used_start for used_start, used_end in occupied):
                continue
            occupied.append((start, end))
            mentions.append(
                KnownEntityMention(
                    source_span_ref_id=source_span_ref_id,
                    start_offset=start,
                    end_offset=end,
                    surface_text=match.group(0),
                    canonical_entity_id=entry.entity.canonical_entity_id,
                    entity_slug=entry.entity.slug,
                    entity_kind=entry.entity.kind,
                    match_method=entry.match_method,
                    display_name=entry.entity.display_name,
                )
            )

    mentions.sort(key=lambda m: (m.start_offset, -m.end_offset))
    return mentions, ambiguous_hits


def match_known_entities_in_spans(
    spans: Sequence[Mapping[str, Any]],
    registry: KnownEntityRegistry,
    *,
    session_id: str | None = None,
) -> KnownEntityMentionSidecar:
    """Match registry entities against paragraph (or text-bearing) spans."""
    term_index = build_term_index(registry.entities)
    ambiguous_norms = _ambiguous_normalized_terms(term_index)

    all_mentions: list[KnownEntityMention] = []
    ambiguous_surfaces: list[str] = []
    scanned = 0
    for span in spans:
        if not isinstance(span, Mapping):
            continue
        kind = span.get("kind")
        if kind == "full_text":
            continue
        text = str(span.get("text") or span.get("text_excerpt") or "")
        if not text.strip():
            continue
        spref = span.get("source_span_ref_id") or span.get("span_id")
        if not isinstance(spref, str) or not spref.strip():
            continue
        scanned += 1
        hits, amb = match_text_mentions(
            text,
            source_span_ref_id=spref.strip(),
            term_index=term_index,
            ambiguous_norms=ambiguous_norms,
        )
        all_mentions.extend(hits)
        for surface in amb:
            if surface not in ambiguous_surfaces:
                ambiguous_surfaces.append(surface)

    return KnownEntityMentionSidecar(
        campaign_id=registry.campaign_id,
        session_id=session_id or f"session-{registry.session_key}",
        registry_relpath=registry.registry_relpath,
        roster_session_key=registry.roster_session_key,
        roster_carry_forward=registry.roster_carry_forward,
        mentions=tuple(all_mentions),
        ambiguous_surfaces=tuple(ambiguous_surfaces),
        diagnostics={
            "spans_scanned": scanned,
            "mention_count": len(all_mentions),
            "entity_count": len(registry.entities),
            "ambiguous_term_count": len(ambiguous_norms),
            "registry_warnings": list(registry.warnings),
        },
    )


def render_known_entity_ledger_markdown(
    sidecar: KnownEntityMentionSidecar,
    *,
    registry: KnownEntityRegistry | None = None,
) -> str:
    """Compact identity ledger for LLM prompts (not a full registry dump)."""
    lines = [
        "## Known entity mentions (deterministic — do not recreate these as nodes)",
        "Use the canonical_entity_id values below when proposing edges, beats, or observations.",
        "Do NOT emit observation_nodes for these entities. Enrich via edges/evidence only.",
        "",
    ]
    if not sidecar.mentions:
        if registry and registry.entities:
            lines.append(
                "_Registry members are configured for this session, but none were "
                "mentioned in the source spans. Do not invent their presence._"
            )
            lines.append("")
            lines.append("Registered (unmentioned) entities:")
            for entity in registry.entities:
                lines.append(
                    f"- {entity.kind} `{entity.canonical_entity_id}` "
                    f"({entity.display_name} / {entity.slug})"
                )
        else:
            lines.append("_No known-entity mentions detected in this source packet._")
        if sidecar.ambiguous_surfaces:
            lines.append("")
            lines.append(
                "Ambiguous surfaces (ignored): "
                + ", ".join(repr(s) for s in sidecar.ambiguous_surfaces)
            )
        return "\n".join(lines)

    by_entity: dict[str, list[KnownEntityMention]] = {}
    for mention in sidecar.mentions:
        by_entity.setdefault(mention.canonical_entity_id, []).append(mention)

    for entity_id, mentions in sorted(by_entity.items(), key=lambda item: item[0]):
        head = mentions[0]
        surfaces = sorted({m.surface_text for m in mentions})
        span_ids = sorted({m.source_span_ref_id for m in mentions})
        lines.append(
            f"- {head.entity_kind} `{entity_id}` "
            f"({head.display_name} / {head.entity_slug}): "
            f"surfaces={surfaces!r}; spans={span_ids}"
        )

    if sidecar.ambiguous_surfaces:
        lines.append("")
        lines.append(
            "Ambiguous surfaces (ignored): "
            + ", ".join(repr(s) for s in sidecar.ambiguous_surfaces)
        )
    return "\n".join(lines)


def filter_observation_nodes_dropping_known_entities(
    nodes: Sequence[Mapping[str, Any]],
    *,
    known_ids: set[str],
    known_slugs: set[str],
    known_labels_norm: set[str],
) -> tuple[list[dict[str, Any]], list[str]]:
    """Drop LLM-emitted nodes that collide with known registry entities."""
    kept: list[dict[str, Any]] = []
    dropped: list[str] = []
    for raw in nodes:
        if not isinstance(raw, Mapping):
            continue
        node = dict(raw)
        node_id = str(node.get("node_id") or "").strip()
        label = str(node.get("label") or "").strip()
        corpus_ref = node.get("corpus_ref") if isinstance(node.get("corpus_ref"), Mapping) else {}
        ref_id = str(corpus_ref.get("ref_id") or "").strip() if corpus_ref else ""
        label_norm = normalize_match_surface(label)
        if (
            node_id in known_ids
            or ref_id in known_slugs
            or (label_norm and label_norm in known_labels_norm)
            or any(slug.replace("_", "-") in node_id for slug in known_slugs)
        ):
            dropped.append(node_id or label or "<unknown>")
            continue
        kept.append(node)
    return kept, dropped


def attach_mention_evidence_to_anchors(
    nodes: list[dict[str, Any]],
    sidecar: KnownEntityMentionSidecar,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Attach span evidence_refs onto known anchor nodes that were mentioned."""
    by_id = {str(n.get("node_id")): n for n in nodes if isinstance(n, dict)}
    attached = 0
    for mention in sidecar.mentions:
        node = by_id.get(mention.canonical_entity_id)
        if node is None:
            continue
        refs = list(node.get("evidence_refs") or [])
        already = {
            str(r.get("source_span_ref_id"))
            for r in refs
            if isinstance(r, Mapping)
        }
        if mention.source_span_ref_id in already:
            continue
        refs.append(
            {
                "source_span_ref_id": mention.source_span_ref_id,
                "anchor_quotes": [mention.surface_text],
            }
        )
        node["evidence_refs"] = refs
        warnings = [w for w in (node.get("warnings") or []) if w != "context_anchor_no_session_evidence"]
        if "known_entity_mention_evidence" not in warnings:
            warnings.append("known_entity_mention_evidence")
        node["warnings"] = warnings
        attached += 1
    return nodes, {"mention_evidence_attachments": attached}


def validate_known_entity_ir_assertions(
    *,
    nodes: Sequence[Mapping[str, Any]],
    edges: Sequence[Mapping[str, Any]],
    beats: Sequence[Mapping[str, Any]] = (),
    known_ids: set[str],
    known_slugs: set[str],
    known_labels_norm: set[str],
) -> dict[str, Any]:
    """Reject known-entity full node asserts; accept additive edges/beats with evidence.

    Known registry entities may appear as ``proposed_action=anchor`` context nodes.
    Full observation-node assertions for those IDs/labels are rejected. Edges and
    beats may reference known canonical IDs when they carry evidence_refs.
    """
    rejected_node_ids: list[str] = []
    accepted_known_edges: list[str] = []
    rejected_known_edges_missing_evidence: list[str] = []
    accepted_known_beats: list[str] = []
    rejected_known_beats_missing_evidence: list[str] = []

    def _collides(node: Mapping[str, Any]) -> bool:
        node_id = str(node.get("node_id") or "").strip()
        label = str(node.get("label") or "").strip()
        corpus_ref = node.get("corpus_ref") if isinstance(node.get("corpus_ref"), Mapping) else {}
        ref_id = str(corpus_ref.get("ref_id") or "").strip() if corpus_ref else ""
        label_norm = normalize_match_surface(label)
        return bool(
            node_id in known_ids
            or ref_id in known_slugs
            or (label_norm and label_norm in known_labels_norm)
            or any(slug.replace("_", "-") in node_id for slug in known_slugs)
        )

    for raw in nodes:
        if not isinstance(raw, Mapping):
            continue
        if raw.get("context_anchor") is True or str(raw.get("proposed_action") or "") == "anchor":
            continue
        if _collides(raw):
            rejected_node_ids.append(str(raw.get("node_id") or raw.get("label") or "<unknown>"))

    for raw in edges:
        if not isinstance(raw, Mapping):
            continue
        endpoints = {
            str(raw.get("from_node_id") or "").strip(),
            str(raw.get("to_node_id") or "").strip(),
        }
        if not endpoints.intersection(known_ids):
            continue
        edge_id = str(raw.get("edge_id") or "<unknown>")
        refs = raw.get("evidence_refs") or []
        if isinstance(refs, list) and any(isinstance(r, Mapping) for r in refs):
            accepted_known_edges.append(edge_id)
        else:
            rejected_known_edges_missing_evidence.append(edge_id)

    for raw in beats:
        if not isinstance(raw, Mapping):
            continue
        involved = [
            str(x).strip()
            for x in (raw.get("involved_node_ids") or [])
            if str(x).strip()
        ]
        if not known_ids.intersection(involved):
            continue
        beat_id = str(raw.get("beat_id") or "<unknown>")
        refs = raw.get("evidence_refs") or []
        if isinstance(refs, list) and any(isinstance(r, Mapping) for r in refs):
            accepted_known_beats.append(beat_id)
        else:
            rejected_known_beats_missing_evidence.append(beat_id)

    return {
        "rejected_known_entity_node_assertions": rejected_node_ids,
        "accepted_known_entity_edges": accepted_known_edges,
        "rejected_known_entity_edges_missing_evidence": rejected_known_edges_missing_evidence,
        "accepted_known_entity_beats": accepted_known_beats,
        "rejected_known_entity_beats_missing_evidence": rejected_known_beats_missing_evidence,
        "ok": not (
            rejected_node_ids
            or rejected_known_edges_missing_evidence
            or rejected_known_beats_missing_evidence
        ),
    }
