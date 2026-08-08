"""Claimed-PC / companion fill experiment (preview-only).

Hypothesis: deterministic mention claims already own party node identity; an LLM
fill pass told those IDs are owned/authored can complete session descriptions and
action evidence better than leaving ``Deterministic party context anchor`` stubs.

Does not mutate corpus or production extraction profiles.
"""

from __future__ import annotations

import json
import re
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

from src.graph_memory.extraction.category_candidate_graph_extractor import (
    OpenAICategoryGraphPassClient,
    _source_packet_md,
    resolve_category_graph_model,
    source_packet_rows_from_span_index,
)
from src.graph_memory.extraction.party_claimed_fill import (
    CLAIMABLE_KINDS,
    PASS_NAME,
    STUB_DESCRIPTION,
    ClaimedEntity,
    ClaimPacket,
    party_claimed_fill_json_schema as _prod_fill_schema,
)
from src.graph_memory.extraction.recap_extraction_profile import EVIDENCE_RULE


def pc_claimed_fill_json_schema() -> dict[str, Any]:
    """Ablation schema: production filled_nodes + optional participation_edges."""
    base = _prod_fill_schema()
    evidence_ref = base["properties"]["filled_nodes"]["items"]["properties"]["evidence_refs"][
        "items"
    ]
    participation_edge = {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "edge_id": {"type": "string"},
            "from_node_id": {"type": "string"},
            "to_node_id": {"type": "string"},
            "predicate": {"type": "string"},
            "description": {"type": ["string", "null"]},
            "evidence_refs": {
                "type": "array",
                "items": evidence_ref,
            },
        },
        "required": [
            "edge_id",
            "from_node_id",
            "to_node_id",
            "predicate",
            "description",
            "evidence_refs",
        ],
    }
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "filled_nodes": base["properties"]["filled_nodes"],
            "participation_edges": {
                "type": "array",
                "items": participation_edge,
            },
        },
        "required": ["filled_nodes", "participation_edges"],
    }


def pc_claimed_fill_text_format(*, strict: bool = True) -> dict[str, Any]:
    return {
        "format": {
            "type": "json_schema",
            "name": "pc_claimed_fill_pass_v0",
            "strict": strict,
            "schema": pc_claimed_fill_json_schema(),
        }
    }


@dataclass
class FillScore:
    claimed_count: int
    filled_count: int
    missing_claim_ids: list[str]
    invented_node_ids: list[str]
    stub_description_count: int
    session_description_count: int
    name_only_evidence_refs: int
    action_evidence_refs: int
    ungrounded_quotes: int
    grounded_quotes: int
    participation_edge_count: int
    invalid_participation_edges: list[str]
    verdict: str
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "claimed_count": self.claimed_count,
            "filled_count": self.filled_count,
            "missing_claim_ids": self.missing_claim_ids,
            "invented_node_ids": self.invented_node_ids,
            "stub_description_count": self.stub_description_count,
            "session_description_count": self.session_description_count,
            "name_only_evidence_refs": self.name_only_evidence_refs,
            "action_evidence_refs": self.action_evidence_refs,
            "ungrounded_quotes": self.ungrounded_quotes,
            "grounded_quotes": self.grounded_quotes,
            "participation_edge_count": self.participation_edge_count,
            "invalid_participation_edges": self.invalid_participation_edges,
            "verdict": self.verdict,
            "notes": self.notes,
        }


def _norm_name(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", value.casefold())


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
    for node_id, rows in sorted(by_id.items()):
        first = rows[0]
        spans = tuple(
            dict.fromkeys(
                str(r.get("source_span_ref_id") or "").strip()
                for r in rows
                if str(r.get("source_span_ref_id") or "").strip()
            )
        )
        surfaces = tuple(
            dict.fromkeys(
                str(r.get("surface_text") or "").strip()
                for r in rows
                if str(r.get("surface_text") or "").strip()
            )
        )
        claims.append(
            ClaimedEntity(
                node_id=node_id,
                label=str(first.get("display_name") or node_id),
                entity_kind=str(first.get("entity_kind") or ""),
                entity_slug=str(first.get("entity_slug") or ""),
                mention_count=len(rows),
                source_span_ref_ids=spans,
                surface_texts=surfaces,
            )
        )
    return claims


def build_claim_packet(
    *,
    mentions_payload: Mapping[str, Any],
    candidate_graph: Mapping[str, Any],
    span_index: Mapping[str, Any],
    source_text: str,
) -> ClaimPacket:
    claims = build_claims_from_mentions(mentions_payload)
    claimed_span_ids = {span for c in claims for span in c.source_span_ref_ids}
    all_rows = source_packet_rows_from_span_index(span_index, source_text=source_text)
    # Prefer claimed spans; fall back to full packet if empty.
    source_rows = [r for r in all_rows if r["source_span_ref_id"] in claimed_span_ids]
    if not source_rows:
        source_rows = list(all_rows)

    baseline_nodes_by_id: dict[str, dict[str, Any]] = {}
    for raw in candidate_graph.get("nodes") or []:
        if isinstance(raw, Mapping) and str(raw.get("node_id") or "").strip():
            baseline_nodes_by_id[str(raw["node_id"])] = dict(raw)

    claimed_ids = {c.node_id for c in claims}
    allowed_targets: list[str] = []
    for node_id, node in baseline_nodes_by_id.items():
        if node_id in claimed_ids:
            continue
        if node.get("context_anchor") is True or str(node.get("proposed_action") or "") == "anchor":
            continue
        allowed_targets.append(node_id)
    allowed_targets.sort()

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
            f"slug={claim.entity_slug!r} mentions={claim.mention_count} "
            f"surfaces=[{surfaces}] spans=[{spans}]"
        )
    return "\n".join(lines)


def render_fill_prompt(packet: ClaimPacket) -> str:
    claims_md = render_owned_claims_markdown(packet.claims)
    src = _source_packet_md(packet.source_rows)
    targets = "\n".join(f"- `{nid}`" for nid in packet.allowed_target_node_ids[:80])
    if len(packet.allowed_target_node_ids) > 80:
        targets += f"\n- … ({len(packet.allowed_target_node_ids) - 80} more omitted)"
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
        "Also emit `participation_edges` linking claimed nodes to non-party observation "
        "nodes from the allowed target list when the recap supports it (participates_in, "
        "located_at, allied_with, opposed_by, etc.). Every edge endpoint must be either a "
        "claimed node_id or an allowed target id.\n\n"
        f"{EVIDENCE_RULE}\n\n"
        "## Allowed non-party target node_ids\n\n"
        f"{targets or '_none_'}\n\n"
        "## Source Packet (claimed spans)\n\n"
        f"{src}\n"
    )


def _quote_is_name_only(quote: str, surfaces: Sequence[str], label: str) -> bool:
    qn = _norm_name(quote)
    if not qn:
        return True
    candidates = [_norm_name(s) for s in surfaces] + [_norm_name(label)]
    if label.split():
        candidates.append(_norm_name(label.split()[0]))
    return qn in {c for c in candidates if c}


def _span_text_by_id(source_rows: Sequence[Mapping[str, Any]]) -> dict[str, str]:
    return {
        str(r["source_span_ref_id"]): str(r.get("text") or "")
        for r in source_rows
        if str(r.get("source_span_ref_id") or "").strip()
    }


def score_fill(
    *,
    packet: ClaimPacket,
    parsed: Mapping[str, Any],
) -> FillScore:
    claimed_ids = {c.node_id for c in packet.claims}
    claims_by_id = {c.node_id: c for c in packet.claims}
    filled_nodes = [
        n for n in (parsed.get("filled_nodes") or []) if isinstance(n, Mapping)
    ]
    filled_ids = {
        str(n.get("node_id") or "").strip()
        for n in filled_nodes
        if str(n.get("node_id") or "").strip()
    }
    missing = sorted(claimed_ids - filled_ids)
    invented = sorted(filled_ids - claimed_ids)

    span_text = _span_text_by_id(packet.source_rows)
    stub_desc = 0
    session_desc = 0
    name_only = 0
    action_ev = 0
    grounded = 0
    ungrounded = 0

    for node in filled_nodes:
        node_id = str(node.get("node_id") or "").strip()
        claim = claims_by_id.get(node_id)
        label = str(node.get("label") or (claim.label if claim else ""))
        surfaces = claim.surface_texts if claim else ()
        desc = str(node.get("description") or "").strip()
        if not desc or desc == STUB_DESCRIPTION or desc.casefold().startswith("deterministic party"):
            stub_desc += 1
        else:
            session_desc += 1
        for ref in node.get("evidence_refs") or []:
            if not isinstance(ref, Mapping):
                continue
            spref = str(ref.get("source_span_ref_id") or "").strip()
            body = span_text.get(spref, "")
            for quote in ref.get("anchor_quotes") or []:
                q = str(quote or "")
                if not q:
                    continue
                if body and q in body:
                    grounded += 1
                else:
                    ungrounded += 1
                if _quote_is_name_only(q, surfaces, label):
                    name_only += 1
                else:
                    action_ev += 1

    edges = [
        e for e in (parsed.get("participation_edges") or []) if isinstance(e, Mapping)
    ]
    allowed = set(packet.allowed_target_node_ids) | claimed_ids
    invalid_edges: list[str] = []
    for edge in edges:
        endpoints = {
            str(edge.get("from_node_id") or "").strip(),
            str(edge.get("to_node_id") or "").strip(),
        }
        edge_id = str(edge.get("edge_id") or "<unknown>")
        if not endpoints.issubset(allowed):
            invalid_edges.append(edge_id)
            continue
        if not endpoints.intersection(claimed_ids):
            invalid_edges.append(edge_id)

    notes: list[str] = []
    # Succeed if: all claims filled, no invented IDs, majority session descriptions,
    # action evidence present, grounding mostly holds.
    success_gates = [
        not missing,
        not invented,
        session_desc >= max(1, len(claimed_ids) - 1),
        action_ev >= max(1, len(claimed_ids)),
        ungrounded <= max(2, grounded // 5) if (grounded + ungrounded) else False,
    ]
    if all(success_gates):
        verdict = "PASS"
        notes.append("Claimed fill meets coverage, non-invention, session-body, and grounding gates.")
    elif session_desc >= len(claimed_ids) // 2 and not invented:
        verdict = "PARTIAL"
        notes.append("Useful enrichment landed, but one or more gates failed.")
    else:
        verdict = "FAIL"
        notes.append("Fill did not beat stub baseline on core gates.")

    if missing:
        notes.append(f"missing claims: {missing}")
    if invented:
        notes.append(f"invented ids: {invented}")
    if invalid_edges:
        notes.append(f"invalid edges: {invalid_edges}")

    return FillScore(
        claimed_count=len(claimed_ids),
        filled_count=len(filled_ids & claimed_ids),
        missing_claim_ids=missing,
        invented_node_ids=invented,
        stub_description_count=stub_desc,
        session_description_count=session_desc,
        name_only_evidence_refs=name_only,
        action_evidence_refs=action_ev,
        ungrounded_quotes=ungrounded,
        grounded_quotes=grounded,
        participation_edge_count=len(edges),
        invalid_participation_edges=invalid_edges,
        verdict=verdict,
        notes=notes,
    )


def score_baseline_stubs(packet: ClaimPacket) -> dict[str, Any]:
    stub = 0
    present = 0
    name_only = 0
    action_ev = 0
    for claim in packet.claims:
        node = packet.baseline_nodes_by_id.get(claim.node_id)
        if node is None:
            continue
        present += 1
        desc = str(node.get("description") or "")
        if desc == STUB_DESCRIPTION:
            stub += 1
        for ref in node.get("evidence_refs") or []:
            if not isinstance(ref, Mapping):
                continue
            for quote in ref.get("anchor_quotes") or []:
                if _quote_is_name_only(str(quote or ""), claim.surface_texts, claim.label):
                    name_only += 1
                else:
                    action_ev += 1
    return {
        "claimed_count": len(packet.claims),
        "present_in_candidate": present,
        "stub_description_count": stub,
        "session_description_count": present - stub,
        "name_only_evidence_refs": name_only,
        "action_evidence_refs": action_ev,
        "note": "Baseline party anchors exist but carry stub descriptions + name-surface evidence.",
    }


def apply_fill_to_candidate_graph(
    candidate_graph: Mapping[str, Any],
    *,
    parsed: Mapping[str, Any],
    claimed_ids: set[str],
) -> dict[str, Any]:
    """Return a copy of candidate_graph with claimed nodes enriched (experiment artifact)."""
    out = json.loads(json.dumps(candidate_graph))
    by_id = {
        str(n.get("node_id")): n
        for n in (out.get("nodes") or [])
        if isinstance(n, dict) and str(n.get("node_id") or "").strip()
    }
    for raw in parsed.get("filled_nodes") or []:
        if not isinstance(raw, Mapping):
            continue
        node_id = str(raw.get("node_id") or "").strip()
        if node_id not in claimed_ids or node_id not in by_id:
            continue
        node = by_id[node_id]
        node["description"] = str(raw.get("description") or node.get("description") or "")
        node["importance"] = str(raw.get("importance") or node.get("importance") or "high")
        if raw.get("evidence_refs"):
            node["evidence_refs"] = list(raw["evidence_refs"])
        warnings = [w for w in (node.get("warnings") or []) if w != "context_anchor_no_session_evidence"]
        if "pc_claimed_fill" not in warnings:
            warnings.append("pc_claimed_fill")
        node["warnings"] = warnings
        node["session_actions"] = list(raw.get("session_actions") or [])
        node["enriched_by"] = PASS_NAME

    edges = list(out.get("edges") or [])
    for raw in parsed.get("participation_edges") or []:
        if not isinstance(raw, Mapping):
            continue
        edge = dict(raw)
        edge.setdefault("confidence", "medium")
        edge.setdefault("proposed_action", "create")
        edge["enriched_by"] = PASS_NAME
        edges.append(edge)
    out["edges"] = edges
    diagnostics = dict(out.get("diagnostics") or {})
    diagnostics["pc_claimed_fill"] = {
        "filled_nodes": len(parsed.get("filled_nodes") or []),
        "participation_edges": len(parsed.get("participation_edges") or []),
    }
    out["diagnostics"] = diagnostics
    return out


class PcClaimedFillPassClient(OpenAICategoryGraphPassClient):
    """Same Responses client, but uses the claimed-fill schema."""

    def run_pass(
        self,
        pass_name: str,
        *,
        model_id: str,
        instructions: str,
        user_content: str,
        pass_spec: Any = None,
    ) -> dict[str, Any]:
        # Reimplement create kwargs with custom text format rather than category schemas.
        import os
        import time

        from openai import OpenAI

        from src.agent.planner_pricing import usage_cost_usd
        from src.bootstrap_env import load_dungeonmindbuddy_dotenv
        from src.graph_memory.extraction.category_candidate_graph_extractor import (
            CategoryGraphExtractionError,
            _usage_from_response,
            parse_json_object,
        )

        load_dungeonmindbuddy_dotenv()
        if not os.environ.get("OPENAI_API_KEY"):
            raise CategoryGraphExtractionError(
                "OPENAI_API_KEY is not configured; cannot run claimed fill experiment."
            )
        openai_kwargs: dict[str, Any] = {}
        if self._max_retries is not None:
            openai_kwargs["max_retries"] = self._max_retries
        client = OpenAI(**openai_kwargs)
        create_kwargs: dict[str, Any] = {
            "model": model_id.strip(),
            "instructions": instructions,
            "input": [{"type": "message", "role": "user", "content": user_content}],
            "text": pc_claimed_fill_text_format(),
        }
        if self._reasoning_effort is not None:
            create_kwargs["reasoning"] = {"effort": self._reasoning_effort}
        t0 = time.perf_counter()
        response = client.responses.create(**create_kwargs)
        elapsed_ms = round((time.perf_counter() - t0) * 1000.0, 2)
        refusal = getattr(response, "refusal", None)
        if refusal:
            raise CategoryGraphExtractionError(f"model refused {pass_name}: {refusal}", pass_name=pass_name)
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
        result: dict[str, Any] = {
            "parsed": parsed,
            "raw_text": raw_text,
            "usage": usage,
            "cost_usd": float(cost_info.get("total_usd") or 0.0),
            "cost_info": cost_info,
            "elapsed_ms": elapsed_ms,
            "response_id": str(getattr(response, "id", "") or ""),
        }
        if self._reasoning_effort is not None:
            result["reasoning_effort"] = self._reasoning_effort
        return result


def load_baseline_run(run_dir: Path) -> dict[str, Any]:
    run_dir = run_dir.resolve()
    return {
        "run_dir": run_dir,
        "candidate_graph": json.loads((run_dir / "candidate_graph.json").read_text(encoding="utf-8")),
        "known_entity_mentions": json.loads(
            (run_dir / "known_entity_mentions.json").read_text(encoding="utf-8")
        ),
        "source_span_index": json.loads(
            (run_dir / "source_span_index.json").read_text(encoding="utf-8")
        ),
        "source_text": (run_dir / "normalized_recap_source.md").read_text(encoding="utf-8"),
        "manifest": json.loads(
            (run_dir / "graph_ingest_run_manifest.json").read_text(encoding="utf-8")
        ),
    }


def rebuild_known_entity_mentions(
    *,
    campaign_id: str,
    session_number: int,
    session_id: str,
    span_index: Mapping[str, Any],
    source_text: str,
) -> dict[str, Any]:
    """Rebuild mention sidecar from current party/known-entity registry."""
    from src.graph_memory.extraction.known_entity_mention_matcher import (
        match_known_entities_in_spans,
    )
    from src.graph_memory.extraction.known_entity_registry import (
        build_known_entity_registry,
    )
    from src.graph_memory.party_context import build_party_context_for_campaign

    party_ctx = build_party_context_for_campaign(campaign_id, session_number)
    registry = build_known_entity_registry(
        campaign_id, session_number, party_ctx=party_ctx
    )
    source_rows = source_packet_rows_from_span_index(span_index, source_text=source_text)
    sidecar = match_known_entities_in_spans(
        source_rows,
        registry,
        session_id=session_id,
    )
    return sidecar.to_dict()


def score_open_extract_against_claims(
    *,
    claims: Sequence[ClaimedEntity],
    observation_nodes: Sequence[Mapping[str, Any]],
    source_rows: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Score free actor extraction against the deterministic party claim set."""
    span_text = _span_text_by_id(source_rows)
    claim_by_norm = {_norm_name(c.label): c for c in claims}
    for claim in claims:
        for surface in claim.surface_texts:
            claim_by_norm.setdefault(_norm_name(surface), claim)
        if claim.label.split():
            claim_by_norm.setdefault(_norm_name(claim.label.split()[0]), claim)

    matched: dict[str, list[dict[str, Any]]] = defaultdict(list)
    unmatched: list[dict[str, Any]] = []
    grounded = 0
    ungrounded = 0
    name_only = 0
    action_ev = 0
    session_desc = 0
    stub_desc = 0

    for raw in observation_nodes:
        if not isinstance(raw, Mapping):
            continue
        node = dict(raw)
        label = str(node.get("label") or "").strip()
        norm = _norm_name(label)
        claim = claim_by_norm.get(norm)
        if claim is None and label.split():
            claim = claim_by_norm.get(_norm_name(label.split()[0]))
        desc = str(node.get("description") or "").strip()
        if not desc or desc == STUB_DESCRIPTION:
            stub_desc += 1
        else:
            session_desc += 1
        surfaces = claim.surface_texts if claim else ((label,) if label else ())
        for ref in node.get("evidence_refs") or []:
            if not isinstance(ref, Mapping):
                continue
            body = span_text.get(str(ref.get("source_span_ref_id") or "").strip(), "")
            for quote in ref.get("anchor_quotes") or []:
                q = str(quote or "")
                if not q:
                    continue
                if body and q in body:
                    grounded += 1
                else:
                    ungrounded += 1
                if _quote_is_name_only(q, surfaces, label):
                    name_only += 1
                else:
                    action_ev += 1
        row = {
            "node_id": str(node.get("node_id") or ""),
            "label": label,
            "description": desc,
            "matched_claim_id": claim.node_id if claim else None,
        }
        if claim is None:
            unmatched.append(row)
        else:
            matched[claim.node_id].append(row)

    covered = sorted(matched.keys())
    missing = sorted({c.node_id for c in claims} - set(covered))
    duplicate_claim_hits = {
        claim_id: len(nodes)
        for claim_id, nodes in matched.items()
        if len(nodes) > 1
    }
    # Open extract "beats" claimed-fill identity story only if it covers the roster
    # with session bodies and few duplicates. Still weaker than owned IDs.
    verdict = "FAIL"
    if not missing and session_desc >= len(claims) and not duplicate_claim_hits:
        verdict = "PASS"
    elif len(covered) >= max(1, len(claims) // 2) and session_desc > 0:
        verdict = "PARTIAL"

    return {
        "claimed_count": len(claims),
        "observation_node_count": len(list(observation_nodes)),
        "roster_covered_count": len(covered),
        "roster_covered_ids": covered,
        "missing_claim_ids": missing,
        "duplicate_claim_hits": duplicate_claim_hits,
        "unmatched_nodes": unmatched,
        "session_description_count": session_desc,
        "stub_description_count": stub_desc,
        "name_only_evidence_refs": name_only,
        "action_evidence_refs": action_ev,
        "grounded_quotes": grounded,
        "ungrounded_quotes": ungrounded,
        "invented_or_non_roster_count": len(unmatched),
        "verdict": verdict,
        "notes": [
            "Open extract matched to roster by label/surface normalization — IDs are not owned.",
            f"missing={missing}" if missing else "full roster label coverage",
            f"duplicates={duplicate_claim_hits}" if duplicate_claim_hits else "no duplicate roster hits",
        ],
    }


def render_open_pc_extract_prompt(
    *,
    source_rows: Sequence[Mapping[str, Any]],
    roster_labels: Sequence[str],
) -> str:
    src = _source_packet_md(source_rows)
    roster = "\n".join(f"- {label}" for label in roster_labels) or "_unknown_"
    return (
        "# Open Party Character Extraction (ablation)\n\n"
        "Preview-only. Forbidden: approve memory, commit graph records, promote canon.\n\n"
        "## Task\n\n"
        "Extract named characters who appear in this recap, INCLUDING player characters "
        "and traveling companions. Do NOT skip the party roster. Prefer one node per "
        "distinct person. Include session-grounded descriptions and action evidence.\n\n"
        "Known party roster labels (for recall — still ground in the source):\n"
        f"{roster}\n\n"
        "Return JSON with key `observation_nodes`. Each node: `node_id`, `label`, "
        "`node_type`, `description`, `importance` (high|medium|low), `evidence_refs`.\n"
        f"{EVIDENCE_RULE}\n\n"
        "## Source Packet\n\n"
        f"{src}\n"
    )


def run_open_pc_extract_experiment(
    *,
    run_dir: Path,
    out_dir: Path | None = None,
    model_id: str | None = None,
    reasoning_effort: str | None = None,
    rebuild_mentions: bool = False,
    campaign_id: str | None = None,
    session_number: int | None = None,
) -> dict[str, Any]:
    """Ablation: free PC/companion extraction vs deterministic claim set."""
    loaded = load_baseline_run(run_dir)
    mentions = loaded["known_entity_mentions"]
    manifest = loaded["manifest"]
    camp = campaign_id or str(manifest.get("campaign_id") or "longmont-c2")
    sess_id = str(manifest.get("session_id") or "session-unknown")
    sess_num = session_number
    if sess_num is None:
        digits = "".join(ch for ch in sess_id if ch.isdigit())
        sess_num = int(digits) if digits else None

    if rebuild_mentions or not (mentions.get("mentions") or []):
        if sess_num is None:
            raise ValueError("session_number required to rebuild mentions")
        mentions = rebuild_known_entity_mentions(
            campaign_id=camp,
            session_number=sess_num,
            session_id=sess_id,
            span_index=loaded["source_span_index"],
            source_text=loaded["source_text"],
        )

    packet = build_claim_packet(
        mentions_payload=mentions,
        candidate_graph=loaded["candidate_graph"],
        span_index=loaded["source_span_index"],
        source_text=loaded["source_text"],
    )
    # Open extract gets the full source packet, not only claimed spans.
    all_rows = source_packet_rows_from_span_index(
        loaded["source_span_index"], source_text=loaded["source_text"]
    )
    prompt = render_open_pc_extract_prompt(
        source_rows=all_rows,
        roster_labels=[c.label for c in packet.claims],
    )

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    resolved_model = resolve_category_graph_model(model_id)
    model_tag = resolved_model.replace("/", "_")
    out = out_dir or (
        Path("out/graph_memory/experiments/pc_open_extract")
        / sess_id
        / f"{stamp}_{model_tag}"
    )
    out.mkdir(parents=True, exist_ok=True)
    (out / "owned_claims.json").write_text(
        json.dumps(
            [
                {
                    "node_id": c.node_id,
                    "label": c.label,
                    "entity_kind": c.entity_kind,
                    "mention_count": c.mention_count,
                }
                for c in packet.claims
            ],
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    (out / "open_extract_prompt.md").write_text(prompt, encoding="utf-8")
    if rebuild_mentions or mentions is not loaded["known_entity_mentions"]:
        (out / "rebuilt_known_entity_mentions.json").write_text(
            json.dumps(mentions, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    client = OpenAICategoryGraphPassClient(reasoning_effort=reasoning_effort)
    result = client.run_pass(
        "actor_pass",
        model_id=resolved_model,
        instructions=(
            "Extract characters including player characters and companions. "
            "Ground every quote in the source packet."
        ),
        user_content=prompt,
    )
    parsed = result.get("parsed") or {}
    nodes = [
        n for n in (parsed.get("observation_nodes") or []) if isinstance(n, Mapping)
    ]
    score = score_open_extract_against_claims(
        claims=packet.claims,
        observation_nodes=nodes,
        source_rows=all_rows,
    )
    # Also score whatever party-ish nodes already exist in the ingested candidate.
    historical = [
        n
        for n in (loaded["candidate_graph"].get("nodes") or [])
        if isinstance(n, Mapping)
        and _norm_name(str(n.get("label") or ""))
        in {
            _norm_name(c.label)
            for c in packet.claims
        }.union({_norm_name(s) for c in packet.claims for s in c.surface_texts})
    ]
    historical_score = score_open_extract_against_claims(
        claims=packet.claims,
        observation_nodes=historical,
        source_rows=all_rows,
    )

    report = {
        "status": "complete",
        "arm": "open_pc_extract",
        "verdict": score["verdict"],
        "model_id": resolved_model,
        "reasoning_effort": reasoning_effort,
        "baseline_run_dir": str(loaded["run_dir"]),
        "out_dir": str(out),
        "cost_usd": result.get("cost_usd"),
        "elapsed_ms": result.get("elapsed_ms"),
        "open_extract_score": score,
        "historical_ingest_partyish_score": historical_score,
        "observation_nodes": nodes,
    }
    (out / "open_extract_raw.json").write_text(
        json.dumps(
            {
                "parsed": parsed,
                "usage": result.get("usage"),
                "cost_usd": result.get("cost_usd"),
                "elapsed_ms": result.get("elapsed_ms"),
                "response_id": result.get("response_id"),
                "model_id": resolved_model,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    (out / "experiment_report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return report


def run_experiment(
    *,
    run_dir: Path,
    out_dir: Path | None = None,
    model_id: str | None = None,
    reasoning_effort: str | None = None,
    client: Any | None = None,
    dry_run_prompt_only: bool = False,
    rebuild_mentions: bool = False,
    campaign_id: str | None = None,
    session_number: int | None = None,
) -> dict[str, Any]:
    loaded = load_baseline_run(run_dir)
    mentions = loaded["known_entity_mentions"]
    manifest = loaded["manifest"]
    camp = campaign_id or str(manifest.get("campaign_id") or "longmont-c2")
    sess_id = str(manifest.get("session_id") or "session-unknown")
    sess_num = session_number
    if sess_num is None:
        digits = "".join(ch for ch in sess_id if ch.isdigit())
        sess_num = int(digits) if digits else None
    rebuilt = False
    if rebuild_mentions or not (mentions.get("mentions") or []):
        if sess_num is None:
            raise ValueError("session_number required to rebuild mentions")
        mentions = rebuild_known_entity_mentions(
            campaign_id=camp,
            session_number=sess_num,
            session_id=sess_id,
            span_index=loaded["source_span_index"],
            source_text=loaded["source_text"],
        )
        rebuilt = True

    packet = build_claim_packet(
        mentions_payload=mentions,
        candidate_graph=loaded["candidate_graph"],
        span_index=loaded["source_span_index"],
        source_text=loaded["source_text"],
    )
    prompt = render_fill_prompt(packet)
    baseline_score = score_baseline_stubs(packet)
    # When stubs are absent (e.g. Session 24 open-extract history), also score
    # party-ish ingested nodes by label as a second baseline.
    historical_partyish = [
        n
        for n in (loaded["candidate_graph"].get("nodes") or [])
        if isinstance(n, Mapping)
        and _norm_name(str(n.get("label") or ""))
        in {_norm_name(c.label) for c in packet.claims}.union(
            {_norm_name(s) for c in packet.claims for s in c.surface_texts}
        )
    ]
    historical_score = score_open_extract_against_claims(
        claims=packet.claims,
        observation_nodes=historical_partyish,
        source_rows=packet.source_rows,
    )
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    resolved_model_early = resolve_category_graph_model(model_id)
    model_tag = resolved_model_early.replace("/", "_")
    out = out_dir or (
        Path("out/graph_memory/experiments/pc_claimed_fill")
        / sess_id
        / f"{stamp}_{model_tag}"
    )
    out.mkdir(parents=True, exist_ok=True)
    if rebuilt:
        (out / "rebuilt_known_entity_mentions.json").write_text(
            json.dumps(mentions, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    (out / "owned_claims.json").write_text(
        json.dumps(
            [
                {
                    "node_id": c.node_id,
                    "label": c.label,
                    "entity_kind": c.entity_kind,
                    "entity_slug": c.entity_slug,
                    "mention_count": c.mention_count,
                    "source_span_ref_ids": list(c.source_span_ref_ids),
                    "surface_texts": list(c.surface_texts),
                }
                for c in packet.claims
            ],
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    (out / "fill_prompt.md").write_text(prompt, encoding="utf-8")
    (out / "baseline_score.json").write_text(
        json.dumps(
            {
                "stub_baseline": baseline_score,
                "historical_partyish_open_extract": historical_score,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    if dry_run_prompt_only:
        report = {
            "status": "prompt_only",
            "baseline_score": baseline_score,
            "historical_partyish_open_extract": historical_score,
            "claimed_count": len(packet.claims),
            "out_dir": str(out),
            "model_id": resolved_model_early,
        }
        (out / "experiment_report.json").write_text(
            json.dumps(report, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        return report

    resolved_model = resolved_model_early
    active_client = client or PcClaimedFillPassClient(reasoning_effort=reasoning_effort)
    result = active_client.run_pass(
        PASS_NAME,
        model_id=resolved_model,
        instructions=(
            "You enrich owned party graph nodes. Never invent new party node IDs. "
            "Ground every quote in the provided source packet paragraphs."
        ),
        user_content=prompt,
    )
    parsed = result.get("parsed") or {}
    fill_score = score_fill(packet=packet, parsed=parsed)
    enriched = apply_fill_to_candidate_graph(
        loaded["candidate_graph"],
        parsed=parsed,
        claimed_ids={c.node_id for c in packet.claims},
    )

    (out / "fill_raw.json").write_text(
        json.dumps(
            {
                "parsed": parsed,
                "usage": result.get("usage"),
                "cost_usd": result.get("cost_usd"),
                "elapsed_ms": result.get("elapsed_ms"),
                "response_id": result.get("response_id"),
                "model_id": resolved_model,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    (out / "fill_score.json").write_text(
        json.dumps(fill_score.to_dict(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (out / "candidate_graph_enriched.json").write_text(
        json.dumps(enriched, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    # Compact qualitative table for the report.
    comparisons: list[dict[str, Any]] = []
    filled_by_id = {
        str(n.get("node_id")): n
        for n in (parsed.get("filled_nodes") or [])
        if isinstance(n, Mapping)
    }
    for claim in packet.claims:
        base = packet.baseline_nodes_by_id.get(claim.node_id) or {}
        filled = filled_by_id.get(claim.node_id) or {}
        comparisons.append(
            {
                "node_id": claim.node_id,
                "label": claim.label,
                "mention_count": claim.mention_count,
                "baseline_description": base.get("description"),
                "filled_description": filled.get("description"),
                "session_actions": filled.get("session_actions") or [],
                "filled_evidence_ref_count": len(filled.get("evidence_refs") or []),
            }
        )

    report = {
        "status": "complete",
        "arm": "claimed_fill",
        "verdict": fill_score.verdict,
        "model_id": resolved_model,
        "reasoning_effort": reasoning_effort,
        "baseline_run_dir": str(loaded["run_dir"]),
        "out_dir": str(out),
        "cost_usd": result.get("cost_usd"),
        "elapsed_ms": result.get("elapsed_ms"),
        "baseline_score": baseline_score,
        "historical_partyish_open_extract": historical_score,
        "fill_score": fill_score.to_dict(),
        "comparisons": comparisons,
        "notes": fill_score.notes,
        "mentions_rebuilt": rebuilt,
    }
    (out / "experiment_report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (out / "experiment_report.md").write_text(
        _render_markdown_report(report),
        encoding="utf-8",
    )
    return report


def _render_markdown_report(report: Mapping[str, Any]) -> str:
    baseline = report.get("baseline_score") or {}
    fill = report.get("fill_score") or {}
    lines = [
        f"# PC claimed-fill experiment — {report.get('verdict')}",
        "",
        f"- baseline run: `{report.get('baseline_run_dir')}`",
        f"- model: `{report.get('model_id')}`",
        f"- cost_usd: {report.get('cost_usd')}",
        f"- elapsed_ms: {report.get('elapsed_ms')}",
        "",
        "## Baseline (stubs)",
        "",
        f"- claimed: {baseline.get('claimed_count')}",
        f"- stub descriptions: {baseline.get('stub_description_count')}",
        f"- session descriptions: {baseline.get('session_description_count')}",
        f"- name-only evidence refs: {baseline.get('name_only_evidence_refs')}",
        f"- action evidence refs: {baseline.get('action_evidence_refs')}",
        "",
        "## Fill",
        "",
        f"- filled: {fill.get('filled_count')} / {fill.get('claimed_count')}",
        f"- session descriptions: {fill.get('session_description_count')}",
        f"- stub descriptions: {fill.get('stub_description_count')}",
        f"- action evidence refs: {fill.get('action_evidence_refs')}",
        f"- name-only evidence refs: {fill.get('name_only_evidence_refs')}",
        f"- grounded quotes: {fill.get('grounded_quotes')}",
        f"- ungrounded quotes: {fill.get('ungrounded_quotes')}",
        f"- participation edges: {fill.get('participation_edge_count')}",
        "",
        "## Notes",
        "",
    ]
    for note in report.get("notes") or []:
        lines.append(f"- {note}")
    lines.extend(["", "## Per-node comparisons", ""])
    for row in report.get("comparisons") or []:
        lines.append(f"### {row.get('label')} (`{row.get('node_id')}`)")
        lines.append("")
        lines.append(f"- mentions: {row.get('mention_count')}")
        lines.append(f"- baseline: {row.get('baseline_description')!r}")
        lines.append(f"- filled: {row.get('filled_description')!r}")
        actions = row.get("session_actions") or []
        if actions:
            lines.append("- actions:")
            for action in actions:
                lines.append(f"  - {action}")
        lines.append("")
    return "\n".join(lines)
