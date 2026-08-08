"""Party claimed-fill: enrich PC/companion anchors with session-grounded prose.

Deterministic mention matching owns party identity; this pass completes
description / evidence / session_actions on those owned IDs only. Does not
emit participation edges (kept experimental) and does not invent new party IDs.
"""

from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from src.graph_memory.extraction.recap_extraction_profile import EVIDENCE_RULE

STUB_DESCRIPTION = "Deterministic party context anchor"
CLAIMABLE_KINDS = frozenset({"pc", "companion"})
PASS_NAME = "pc_claimed_fill_pass"
PASS_PROGRESS_LABEL = "Filling claimed party nodes"


def party_claimed_fill_json_schema() -> dict[str, Any]:
    """Production fill schema: filled_nodes only (no participation edges)."""
    evidence_ref = {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "source_span_ref_id": {"type": "string"},
            "anchor_quotes": {
                "type": "array",
                "items": {"type": "string"},
            },
        },
        "required": ["source_span_ref_id", "anchor_quotes"],
    }
    filled_node = {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "node_id": {"type": "string"},
            "label": {"type": "string"},
            "node_type": {"type": "string"},
            "description": {"type": "string"},
            "importance": {
                "type": "string",
                "enum": ["high", "medium", "low"],
            },
            "evidence_refs": {
                "type": "array",
                "items": evidence_ref,
            },
            "session_actions": {
                "type": "array",
                "items": {"type": "string"},
            },
        },
        "required": [
            "node_id",
            "label",
            "node_type",
            "description",
            "importance",
            "evidence_refs",
            "session_actions",
        ],
    }
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "filled_nodes": {
                "type": "array",
                "items": filled_node,
            },
        },
        "required": ["filled_nodes"],
    }


def party_claimed_fill_text_format(*, strict: bool = True) -> dict[str, Any]:
    return {
        "format": {
            "type": "json_schema",
            "name": "pc_claimed_fill_pass_v1",
            "strict": strict,
            "schema": party_claimed_fill_json_schema(),
        }
    }


@dataclass(frozen=True)
class ClaimedEntity:
    node_id: str
    label: str
    entity_kind: str
    entity_slug: str
    mention_count: int
    source_span_ref_ids: tuple[str, ...]
    surface_texts: tuple[str, ...]


@dataclass
class ClaimPacket:
    claims: list[ClaimedEntity]
    source_rows: list[dict[str, Any]]
    allowed_target_node_ids: list[str]
    baseline_nodes_by_id: dict[str, dict[str, Any]]


def build_claims_from_mentions(
    mentions_payload: Mapping[str, Any],
    *,
    kinds: frozenset[str] = CLAIMABLE_KINDS,
) -> list[ClaimedEntity]:
    by_id: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for raw in mentions_payload.get("mentions") or []:
        if not isinstance(raw, Mapping):
            continue
        kind = str(raw.get("entity_kind") or "").strip()
        if kind not in kinds:
            continue
        node_id = str(raw.get("canonical_entity_id") or "").strip()
        if not node_id:
            continue
        by_id[node_id].append(raw)

    claims: list[ClaimedEntity] = []
    for node_id in sorted(by_id):
        rows = by_id[node_id]
        head = rows[0]
        spans = tuple(
            sorted(
                {
                    str(r.get("source_span_ref_id") or "").strip()
                    for r in rows
                    if str(r.get("source_span_ref_id") or "").strip()
                }
            )
        )
        surfaces = tuple(
            sorted(
                {
                    str(r.get("surface_text") or "").strip()
                    for r in rows
                    if str(r.get("surface_text") or "").strip()
                }
            )
        )
        claims.append(
            ClaimedEntity(
                node_id=node_id,
                label=str(head.get("display_name") or head.get("entity_slug") or node_id),
                entity_kind=str(head.get("entity_kind") or ""),
                entity_slug=str(head.get("entity_slug") or ""),
                mention_count=len(rows),
                source_span_ref_ids=spans,
                surface_texts=surfaces,
            )
        )
    return claims


def build_claim_packet(
    *,
    mentions_payload: Mapping[str, Any],
    span_index: Mapping[str, Any],
    source_text: str | None,
    candidate_nodes: Sequence[Mapping[str, Any]],
    source_packet_rows_from_span_index: Any,
) -> ClaimPacket:
    """Build claim packet; ``source_packet_rows_from_span_index`` injected to avoid cycles."""
    claims = build_claims_from_mentions(mentions_payload)
    claimed_span_ids = {span for c in claims for span in c.source_span_ref_ids}
    all_rows = source_packet_rows_from_span_index(span_index, source_text=source_text)
    source_rows = [r for r in all_rows if r["source_span_ref_id"] in claimed_span_ids]
    if not source_rows:
        source_rows = list(all_rows)

    baseline_nodes_by_id: dict[str, dict[str, Any]] = {}
    for raw in candidate_nodes:
        if isinstance(raw, Mapping) and str(raw.get("node_id") or "").strip():
            baseline_nodes_by_id[str(raw["node_id"])] = dict(raw)

    allowed_targets = sorted(
        nid
        for nid in baseline_nodes_by_id
        if nid not in {c.node_id for c in claims}
    )
    return ClaimPacket(
        claims=claims,
        source_rows=source_rows,
        allowed_target_node_ids=allowed_targets,
        baseline_nodes_by_id=baseline_nodes_by_id,
    )


def render_owned_claims_markdown(claims: Sequence[ClaimedEntity]) -> str:
    lines = [
        "## Owned / authored claims (DO NOT invent new party IDs)",
        "",
        "These node identities are already claimed by deterministic matching.",
        "Complete each claimed node. Do not emit any other party PC/companion node_id.",
        "",
    ]
    for claim in claims:
        spans = ", ".join(f"`{s}`" for s in claim.source_span_ref_ids) or "(none)"
        surfaces = ", ".join(repr(s) for s in claim.surface_texts) or "(none)"
        lines.append(
            f"- **{claim.entity_kind}** `{claim.node_id}` label={claim.label!r} "
            f"surfaces=[{surfaces}] spans=[{spans}] mentions={claim.mention_count}"
        )
    return "\n".join(lines)


def _source_packet_md(source_rows: Sequence[Mapping[str, Any]]) -> str:
    blocks: list[str] = []
    for row in source_rows:
        spref = row.get("source_span_ref_id")
        text = str(row.get("text") or "")
        blocks.append(f"### `{spref}`\n\n{text}")
    return "\n\n".join(blocks) if blocks else "_No source spans._"


def render_fill_prompt(packet: ClaimPacket) -> str:
    claims_md = render_owned_claims_markdown(packet.claims)
    src = _source_packet_md(packet.source_rows)
    return (
        "# Claimed Party Node Fill Pass\n\n"
        "Preview-only graph memory enrichment. Forbidden: approve memory, commit graph "
        "records, promote canon, execute writes.\n\n"
        f"{claims_md}\n\n"
        "## Task\n\n"
        "For EACH owned claim above, emit one `filled_nodes` entry with the SAME `node_id` "
        "and `label`. Write a session-grounded `description` of what this character did or "
        "experienced in THIS recap (not a roster stub). Include `session_actions` as short "
        "bullet-like phrases grounded in the source. Prefer action/state quotes in "
        "`evidence_refs.anchor_quotes` — not bare name-only quotes when richer text exists.\n\n"
        "Do NOT invent new party node IDs. Do NOT emit edges in this pass.\n\n"
        f"{EVIDENCE_RULE}\n\n"
        "## Source Packet (claimed spans)\n\n"
        f"{src}\n"
    )


def apply_fill_to_nodes(
    nodes: Sequence[Mapping[str, Any]],
    *,
    parsed: Mapping[str, Any],
    claimed_ids: set[str],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Enrich matching nodes in-place-copied list; ignore unknown / invented IDs."""
    out = [dict(n) for n in nodes if isinstance(n, Mapping)]
    by_id = {
        str(n.get("node_id")): n
        for n in out
        if str(n.get("node_id") or "").strip()
    }
    applied = 0
    skipped_missing_anchor = 0
    skipped_invented = 0
    for raw in parsed.get("filled_nodes") or []:
        if not isinstance(raw, Mapping):
            continue
        node_id = str(raw.get("node_id") or "").strip()
        if not node_id:
            continue
        if node_id not in claimed_ids:
            skipped_invented += 1
            continue
        if node_id not in by_id:
            skipped_missing_anchor += 1
            continue
        node = by_id[node_id]
        node["description"] = str(raw.get("description") or node.get("description") or "")
        node["importance"] = str(raw.get("importance") or node.get("importance") or "high")
        if raw.get("evidence_refs"):
            node["evidence_refs"] = list(raw["evidence_refs"])
        warnings = [
            w
            for w in (node.get("warnings") or [])
            if w != "context_anchor_no_session_evidence"
        ]
        if "pc_claimed_fill" not in warnings:
            warnings.append("pc_claimed_fill")
        node["warnings"] = warnings
        node["session_actions"] = list(raw.get("session_actions") or [])
        node["enriched_by"] = PASS_NAME
        applied += 1
    diag = {
        "enabled": True,
        "claimed_count": len(claimed_ids),
        "filled_offered": len(
            [n for n in (parsed.get("filled_nodes") or []) if isinstance(n, Mapping)]
        ),
        "filled_applied": applied,
        "skipped_missing_anchor": skipped_missing_anchor,
        "skipped_invented": skipped_invented,
        "pass_id": PASS_NAME,
    }
    return out, diag


def apply_fill_to_parts(
    parts: Mapping[str, Any],
    *,
    parsed: Mapping[str, Any],
    claimed_ids: set[str],
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Enrich ``parts['nodes']``; leave edges/beats untouched."""
    out = dict(parts)
    nodes, diag = apply_fill_to_nodes(
        list(parts.get("nodes") or []),
        parsed=parsed,
        claimed_ids=claimed_ids,
    )
    out["nodes"] = nodes
    return out, diag


# Keep a deep-copy graph helper for the eval harness / artifacts.
def apply_fill_to_candidate_graph(
    candidate_graph: Mapping[str, Any],
    *,
    parsed: Mapping[str, Any],
    claimed_ids: set[str],
) -> dict[str, Any]:
    out = json.loads(json.dumps(candidate_graph))
    nodes, diag = apply_fill_to_nodes(
        list(out.get("nodes") or []),
        parsed=parsed,
        claimed_ids=claimed_ids,
    )
    out["nodes"] = nodes
    diagnostics = dict(out.get("diagnostics") or {})
    diagnostics["pc_claimed_fill"] = diag
    out["diagnostics"] = diagnostics
    return out
