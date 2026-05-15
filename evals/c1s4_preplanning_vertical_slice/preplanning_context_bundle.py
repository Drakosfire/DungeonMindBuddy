from __future__ import annotations

from typing import Any

from evals.c1s4_preplanning_vertical_slice.step0_kb_materialize import check_oracle_leakage


def build_preplanning_context_bundle(*, kb_id: str, campaign_id: str, allowed_sessions: list[int], heldout_sessions: list[int], query: str, retrieval_result: object, forbidden_oracle_relpaths: list[str], records_by_unit_id: dict[str, dict[str, Any]] | None = None, max_items: int = 8, max_snippet_chars: int = 500) -> dict[str, Any]:
    hits = retrieval_result.hits if hasattr(retrieval_result, "hits") else (retrieval_result.get("hits", []) if isinstance(retrieval_result, dict) else [])
    items: list[dict[str, Any]] = []
    records_by_unit_id = records_by_unit_id or {}
    for hit in hits[:max_items]:
        unit_id = str(hit.get("unit_id") or "")
        record = records_by_unit_id.get(unit_id, {})
        snippet_source = record or hit
        snippet = str(snippet_source.get("lexical_plain") or snippet_source.get("text") or hit.get("snippet") or "")[:max_snippet_chars]
        items.append(
            {
                "unit_id": hit.get("unit_id"),
                "session_number": hit.get("session_number", record.get("session_number")),
                "source_recap_path": hit.get("source_recap_path", record.get("source_recap_path")),
                "line_start": hit.get("line_start"),
                "line_end": hit.get("line_end"),
                "routes": hit.get("routes") or [],
                "why_matched": hit.get("why_matched") or [],
                "snippet": snippet,
            }
        )
    leakage = check_oracle_leakage(records_or_items=items, heldout_sessions=heldout_sessions, forbidden_oracle_relpaths=forbidden_oracle_relpaths)
    return {
        "schema": "dmb_preplanning_context_bundle_v1",
        "kb_id": kb_id,
        "campaign_id": campaign_id,
        "allowed_sessions": allowed_sessions,
        "heldout_sessions": heldout_sessions,
        "query": query,
        "retrieved_anchor_count": len(hits),
        "items": items,
        "oracle_leakage_check": leakage,
    }
