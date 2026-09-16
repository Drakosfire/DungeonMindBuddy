"""Read-only ingested-object loadability probe for the accepted World.

Evaluation-only. Production code is not modified. This does not gate
admission; it classifies whether a candidate/payload object can be found
and opened through production product reads.

First sample: Campaign 2 Session 22 / loc:mireward.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence

import httpx

from graph_memory.anchor_quotes import find_anchor_quote_matches

from evals.graph_benchmark.run_current_corpus_question_gauntlet import (
    DATABASE_NAME,
    OUTER_CAMPAIGN_ID,
    PROJECT_ROOT,
    TERMINAL_HEAD,
    WORLD_ID,
    _post_json,
    collect_ids,
    resolve_ledger_session_row,
)

LOADABILITY_CAMPAIGN_ID = OUTER_CAMPAIGN_ID
LOADABILITY_SESSION_ID = "session-22"
CANDIDATE_NODE_ID = "loc:mireward"
PUBLISHED_OBJECT_ID = "node:location:mireward"
SEARCH_TEXT = "Mireward"
C2S22_REVISION = "rev:24268294e868b30034e247aa9e23087b"

_SAFE_ID_RE = re.compile(r"^[A-Za-z0-9:_-]+$")

LoadabilityStatus = str

STATUS_AUTHORITY_ABSENT = "authority_absent"
STATUS_CANDIDATE_NOT_ADMITTED = "candidate_not_admitted"
STATUS_PRODUCT_UNRESOLVED = "product_unresolved"
STATUS_EXCERPT_READY = "excerpt_ready"
STATUS_QUOTE_MISMATCH = "quote_mismatch"
STATUS_SOURCE_NOT_DURABLE = "source_not_durable"
STATUS_SPAN_UNRESOLVABLE = "span_unresolvable"
STATUS_UNREADABLE_ANCHOR = "unreadable_anchor"

_STATUS_PRIORITY = (
    STATUS_QUOTE_MISMATCH,
    STATUS_PRODUCT_UNRESOLVED,
    STATUS_UNREADABLE_ANCHOR,
    STATUS_SOURCE_NOT_DURABLE,
    STATUS_SPAN_UNRESOLVABLE,
    STATUS_CANDIDATE_NOT_ADMITTED,
    STATUS_AUTHORITY_ABSENT,
    STATUS_EXCERPT_READY,
)


def _require_safe_id(value: str, *, what: str) -> str:
    if not _SAFE_ID_RE.match(value):
        raise ValueError(f"refusing to interpolate unsafe {what}: {value!r}")
    return value


def build_loadability_search_request(
    *,
    query_text: str,
    revision_pin: str,
    campaign_id: str = LOADABILITY_CAMPAIGN_ID,
    scope_mode: str = "world",
    seed_node_ids: list[str] | None = None,
    focus_session_id: str | None = None,
) -> dict[str, Any]:
    return {
        "schema": "dmb_world_graph_search_request_v1",
        "worldId": WORLD_ID,
        "campaignId": campaign_id,
        "focus": _focus(focus_session_id, campaign_id),
        "admissibility": "gm",
        "revisionPin": revision_pin,
        "scopeMode": scope_mode,
        "queryText": query_text,
        "seedNodeIds": list(seed_node_ids or []),
        "bounds": {
            "maxNodes": 12,
            "maxRelationships": 24,
            "maxAttributes": 32,
            "maxSourceAnchors": 32,
        },
    }


def build_loadability_object_request(
    *,
    node_id: str,
    revision_pin: str,
    campaign_id: str = LOADABILITY_CAMPAIGN_ID,
    scope_mode: str = "world",
    focus_session_id: str | None = None,
) -> dict[str, Any]:
    return {
        "schema": "dmb_world_graph_object_request_v1",
        "worldId": WORLD_ID,
        "campaignId": campaign_id,
        "focus": _focus(focus_session_id, campaign_id),
        "admissibility": "gm",
        "revisionPin": revision_pin,
        "scopeMode": scope_mode,
        "nodeId": node_id,
        "bounds": {
            "maxNodes": 12,
            "maxRelationships": 24,
            "maxAttributes": 32,
            "maxSourceAnchors": 32,
        },
    }


def build_loadability_complete_object_request(
    *,
    node_id: str,
    revision_pin: str,
    campaign_id: str = LOADABILITY_CAMPAIGN_ID,
    focus_session_id: str | None = None,
    origin_surface: str = "ingest",
) -> dict[str, Any]:
    return {
        "schema": "dmb_world_graph_object_projection_request_v1",
        "worldId": WORLD_ID,
        "campaignId": campaign_id,
        "nodeId": node_id,
        "focus": _focus(focus_session_id, campaign_id),
        "admissibility": "gm",
        "revisionPin": revision_pin,
        "originSurface": origin_surface,
    }


def build_loadability_evidence_request(
    *,
    node_id: str,
    revision_pin: str,
    campaign_id: str = LOADABILITY_CAMPAIGN_ID,
    scope_mode: str = "world",
    focus_session_id: str | None = None,
) -> dict[str, Any]:
    return {
        "schema": "dmb_world_graph_evidence_request_v1",
        "worldId": WORLD_ID,
        "campaignId": campaign_id,
        "focus": _focus(focus_session_id, campaign_id),
        "admissibility": "gm",
        "revisionPin": revision_pin,
        "scopeMode": scope_mode,
        "target": {"kind": "node", "id": node_id},
        "bounds": {"maxSourceAnchors": 32},
    }


def _focus(session_id: str | None, campaign_id: str) -> dict[str, Any]:
    if session_id:
        return {
            "kind": "session",
            "sessionId": session_id,
            "campaignId": campaign_id,
        }
    return {"kind": "none", "sessionId": None, "campaignId": None}


def classify_loadability(
    *,
    candidate_present: bool,
    payload_present: bool,
    product_found: bool,
    provenance_statuses: Sequence[str] = (),
    quotes_checked: bool = False,
    quotes_all_matched: bool = False,
) -> LoadabilityStatus:
    """Classify one identity: candidate vs admitted payload vs product read."""
    if product_found:
        if quotes_checked and not quotes_all_matched:
            return STATUS_QUOTE_MISMATCH
        statuses = [s for s in provenance_statuses if s]
        if statuses and all(s == "excerpt_ready" for s in statuses):
            return STATUS_EXCERPT_READY
        if statuses and all(s == "source_not_durable" for s in statuses):
            return STATUS_SOURCE_NOT_DURABLE
        if statuses and all(s == "span_unresolvable" for s in statuses):
            return STATUS_SPAN_UNRESOLVABLE
        if any(s == "excerpt_ready" for s in statuses):
            return STATUS_EXCERPT_READY
        return STATUS_UNREADABLE_ANCHOR
    if payload_present:
        return STATUS_PRODUCT_UNRESOLVED
    if candidate_present:
        return STATUS_CANDIDATE_NOT_ADMITTED
    return STATUS_AUTHORITY_ABSENT


def evaluate_dogfood_readiness(
    *,
    harness_ready: bool,
    agent_smoke_ok: bool,
    loadability: dict[str, Any] | None,
    agent_full: int | None = None,
    agent_ran: bool = False,
    agent_tool_calls: int | None = None,
) -> dict[str, Any]:
    """Operator dogfood is the readiness gate.

    Structural oracle PASS does not make the World ready. If the GM cannot
    load admitted objects or get a usable Hermes answer, the product is
    not ready.
    """
    blockers: list[dict[str, str]] = []
    if not harness_ready:
        blockers.append(
            {
                "id": "historical_retrieval",
                "detail": (
                    "C1S10 retrieval smoke did not pin BENCHMARK_REVISION; "
                    "the operator cannot even query the historical World."
                ),
            }
        )
    if not agent_smoke_ok:
        blockers.append(
            {
                "id": "hermes_agent",
                "detail": (
                    "Hermes Agent smoke failed. The operator cannot ask the "
                    "accepted World a question and get a graph-backed answer."
                ),
            }
        )
    elif agent_ran and agent_full == 0:
        tool_note = (
            f" (tool_calls={agent_tool_calls})"
            if agent_tool_calls is not None
            else ""
        )
        blockers.append(
            {
                "id": "hermes_cannot_answer",
                "detail": (
                    "Hermes returned 0 FULL answers"
                    f"{tool_note}. HTTP 200 / hermes_graph_agent is not dogfood "
                    "if the operator cannot get a usable graph-backed answer."
                ),
            }
        )
    if loadability is None:
        blockers.append(
            {
                "id": "loadability_missing",
                "detail": "Ingested-object loadability was not probed.",
            }
        )
    elif not loadability.get("openable") or loadability.get("seed_status") != STATUS_EXCERPT_READY:
        seed_status = loadability.get("seed_status")
        remap = loadability.get("identity_remap") or {}
        blockers.append(
            {
                "id": "ingested_object_unreadable",
                "detail": (
                    "Admitted C2S22 Mireward is not loadable through product "
                    f"reads (seed_status={seed_status}; "
                    f"candidate={remap.get('from_candidate_id')}; "
                    f"published={remap.get('to_published_ids')})."
                ),
            }
        )
    return {
        "schema": "dmb_current_corpus_dogfood_readiness_v1",
        "rule": (
            "If the operator cannot dogfood the accepted World, it is not ready. "
            "Structural retrieval PASS is not product readiness."
        ),
        "dogfood_ready": not blockers,
        "blockers": blockers,
    }


def roll_up_seed_status(statuses: Sequence[str]) -> LoadabilityStatus:
    remaining = set(statuses)
    if not remaining:
        return STATUS_AUTHORITY_ABSENT
    for status in _STATUS_PRIORITY:
        if status in remaining:
            return status
    return next(iter(remaining))


def extract_candidate_node(
    candidate_path: Path,
    node_id: str,
) -> dict[str, Any]:
    payload = json.loads(candidate_path.read_text(encoding="utf-8"))
    nodes = payload.get("nodes") if isinstance(payload, dict) else None
    if not isinstance(nodes, list):
        raise RuntimeError(f"candidate missing nodes list: {candidate_path}")
    match = next(
        (
            node
            for node in nodes
            if isinstance(node, dict) and node.get("node_id") == node_id
        ),
        None,
    )
    if match is None:
        return {
            "present": False,
            "node_id": node_id,
            "label": None,
            "node_type": None,
            "evidence_ref_count": 0,
            "quotes": [],
        }
    quotes: list[dict[str, Any]] = []
    for index, evidence in enumerate(match.get("evidence_refs") or []):
        if not isinstance(evidence, dict):
            continue
        for quote_index, quote in enumerate(evidence.get("anchor_quotes") or []):
            if not isinstance(quote, str) or not quote.strip():
                continue
            quotes.append(
                {
                    "evidence_index": index,
                    "quote_index": quote_index,
                    "char_len": len(quote),
                    "text": quote,
                    "source_span_ref_id": evidence.get("source_span_ref_id"),
                    "source_artifact_id": evidence.get("source_artifact_id"),
                    "can_open_source": evidence.get("can_open_source"),
                    "can_highlight_span": evidence.get("can_highlight_span"),
                }
            )
    return {
        "present": True,
        "node_id": node_id,
        "label": match.get("label"),
        "node_type": match.get("node_type"),
        "proposed_action": match.get("proposed_action"),
        "evidence_ref_count": len(match.get("evidence_refs") or []),
        "quotes": quotes,
    }


def candidate_public_view(extracted: dict[str, Any]) -> dict[str, Any]:
    """Drop quote text before persisting artifacts."""
    quotes = [
        {
            "evidence_index": row["evidence_index"],
            "quote_index": row["quote_index"],
            "char_len": row["char_len"],
            "source_span_ref_id": row.get("source_span_ref_id"),
            "source_artifact_id": row.get("source_artifact_id"),
            "can_open_source": row.get("can_open_source"),
            "can_highlight_span": row.get("can_highlight_span"),
        }
        for row in extracted.get("quotes") or []
    ]
    return {
        "present": extracted.get("present"),
        "node_id": extracted.get("node_id"),
        "label": extracted.get("label"),
        "node_type": extracted.get("node_type"),
        "proposed_action": extracted.get("proposed_action"),
        "evidence_ref_count": extracted.get("evidence_ref_count"),
        "quote_count": len(quotes),
        "quotes": quotes,
    }


def lookup_payload_objects(
    *,
    revision_id: str,
    object_ids: Sequence[str],
    label_needle: str,
) -> list[dict[str, str]]:
    revision = _require_safe_id(revision_id, what="revision_id")
    world_id = _require_safe_id(WORLD_ID, what="world_id")
    safe_ids = [_require_safe_id(item, what="object_id") for item in object_ids]
    if not safe_ids:
        return []
    ids_sql = ", ".join(f"'{item}'" for item in safe_ids)
    needle = label_needle.replace("'", "''")
    sql = f"""
SELECT obj->>'object_id', coalesce(obj->>'kind',''), coalesce(obj->>'label','')
FROM dungeonmind.graph_revisions r,
LATERAL jsonb_array_elements(r.graph_payload->'objects') obj
WHERE r.world_id = '{world_id}'
  AND r.revision_id = '{revision}'
  AND (
    obj->>'object_id' IN ({ids_sql})
    OR obj->>'label' ILIKE '%{needle}%'
  );
"""
    env = os.environ.copy()
    env.setdefault("PGPASSWORD", "dungeonmind-dev")
    out = subprocess.check_output(
        [
            "psql",
            "-h",
            "127.0.0.1",
            "-p",
            "54329",
            "-U",
            "dungeonmind",
            "-d",
            DATABASE_NAME,
            "-Atc",
            sql,
        ],
        env=env,
        text=True,
    ).strip()
    rows: list[dict[str, str]] = []
    if not out:
        return rows
    for line in out.splitlines():
        object_id, kind, label = (line.split("|") + ["", ""])[:3]
        rows.append({"object_id": object_id, "kind": kind, "label": label})
    return rows


def summarize_retrieval(status_code: int, body: Any) -> dict[str, Any]:
    payload = body if isinstance(body, dict) else {"non_object": True}
    ids = collect_ids(payload) if isinstance(body, dict) else {
        "node_ids": [],
        "relationship_ids": [],
        "attribute_ids": [],
        "source_anchor_ids": [],
    }
    snapshot = payload.get("snapshot") or {}
    if not snapshot and isinstance(payload.get("result"), dict):
        snapshot = payload["result"].get("snapshot") or {}
    coverage = payload.get("coverage") or {}
    return {
        "http_status": status_code,
        "outcome": payload.get("outcome"),
        "found": payload.get("found"),
        "requested_node_id": payload.get("requestedNodeId")
        or payload.get("requested_node_id"),
        "resolved_node_id": payload.get("resolvedNodeId")
        or payload.get("resolved_node_id"),
        "revision_id": (
            snapshot.get("revisionId") or snapshot.get("revision_id")
            if isinstance(snapshot, dict)
            else None
        ),
        "node_ids": ids["node_ids"],
        "source_anchor_ids": ids["source_anchor_ids"],
        "missing_seed_node_ids": coverage.get("missingSeedNodeIds")
        or coverage.get("missing_seed_node_ids")
        or [],
        "resolved_redirects": coverage.get("resolvedRedirects")
        or coverage.get("resolved_redirects")
        or {},
        "error_code": payload.get("code") or payload.get("error"),
    }


def summarize_complete_object(status_code: int, body: Any) -> dict[str, Any]:
    payload = body if isinstance(body, dict) else {}
    bindings = payload.get("sourceBindings") or payload.get("source_bindings") or []
    provenance: list[str] = []
    artifact_ids: list[str] = []
    session_ids: list[str] = []
    excerpts: list[str] = []
    for binding in bindings:
        if not isinstance(binding, dict):
            continue
        status = binding.get("provenanceStatus") or binding.get("provenance_status")
        if isinstance(status, str):
            provenance.append(status)
        artifact = binding.get("sourceArtifactId") or binding.get("source_artifact_id")
        if isinstance(artifact, str):
            artifact_ids.append(artifact)
        session_id = binding.get("sessionId") or binding.get("session_id")
        if isinstance(session_id, str):
            session_ids.append(session_id)
        excerpt = binding.get("excerpt")
        if isinstance(excerpt, str) and excerpt.strip():
            excerpts.append(excerpt)
    return {
        "http_status": status_code,
        "found": payload.get("found"),
        "requested_node_id": payload.get("requestedNodeId")
        or payload.get("requested_node_id"),
        "resolved_node_id": payload.get("resolvedNodeId")
        or payload.get("resolved_node_id"),
        "completeness": payload.get("completeness"),
        "assertion_count": len(payload.get("assertions") or []),
        "relationship_count": len(payload.get("relationships") or []),
        "provenance_statuses": provenance,
        "source_artifact_ids": sorted(set(artifact_ids)),
        "session_ids": sorted(set(session_ids)),
        "excerpt_count": len(excerpts),
        "excerpts": excerpts,
        "error_code": payload.get("code") or payload.get("error"),
    }


def match_quotes_against_excerpts(
    quotes: Sequence[dict[str, Any]],
    excerpts: Sequence[str],
) -> dict[str, Any]:
    if not quotes:
        return {
            "quotes_checked": False,
            "quotes_all_matched": False,
            "matched": [],
        }
    if not excerpts:
        return {
            "quotes_checked": False,
            "quotes_all_matched": False,
            "matched": [],
        }
    matched: list[dict[str, Any]] = []
    all_matched = True
    for quote in quotes:
        text = quote.get("text") or ""
        hits = False
        for excerpt in excerpts:
            if find_anchor_quote_matches(excerpt, [text]):
                hits = True
                break
        if not hits:
            all_matched = False
        matched.append(
            {
                "evidence_index": quote.get("evidence_index"),
                "quote_index": quote.get("quote_index"),
                "char_len": quote.get("char_len"),
                "matched": hits,
            }
        )
    return {
        "quotes_checked": True,
        "quotes_all_matched": all_matched,
        "matched": matched,
    }


def _product_found(complete_summaries: Sequence[dict[str, Any]], object_summaries: Sequence[dict[str, Any]]) -> bool:
    return any(row.get("found") is True for row in complete_summaries) or any(
        row.get("outcome") not in (None, "empty") and row.get("http_status") == 200
        and (row.get("node_ids") or row.get("found") is True)
        for row in object_summaries
    )


def probe_identity(
    client: httpx.Client,
    *,
    node_id: str,
    revision_pin: str,
    campaign_id: str,
    session_id: str,
    candidate_present: bool,
    payload_present: bool,
    candidate_quotes: Sequence[dict[str, Any]],
) -> dict[str, Any]:
    complete_none_status, complete_none_body = _post_json(
        client,
        "/api/live/world-graph/retrieval/complete-object",
        build_loadability_complete_object_request(
            node_id=node_id,
            revision_pin=revision_pin,
            campaign_id=campaign_id,
        ),
    )
    complete_session_status, complete_session_body = _post_json(
        client,
        "/api/live/world-graph/retrieval/complete-object",
        build_loadability_complete_object_request(
            node_id=node_id,
            revision_pin=revision_pin,
            campaign_id=campaign_id,
            focus_session_id=session_id,
        ),
    )
    object_status, object_body = _post_json(
        client,
        "/api/live/world-graph/retrieval/object",
        build_loadability_object_request(
            node_id=node_id,
            revision_pin=revision_pin,
            campaign_id=campaign_id,
            focus_session_id=session_id,
        ),
    )
    evidence_status, evidence_body = _post_json(
        client,
        "/api/live/world-graph/retrieval/evidence",
        build_loadability_evidence_request(
            node_id=node_id,
            revision_pin=revision_pin,
            campaign_id=campaign_id,
            focus_session_id=session_id,
        ),
    )

    complete_none = summarize_complete_object(complete_none_status, complete_none_body)
    complete_session = summarize_complete_object(
        complete_session_status, complete_session_body
    )
    object_summary = summarize_retrieval(object_status, object_body)
    evidence_summary = summarize_retrieval(evidence_status, evidence_body)

    excerpts = list(complete_none.get("excerpts") or []) + list(
        complete_session.get("excerpts") or []
    )
    quote_report = match_quotes_against_excerpts(candidate_quotes, excerpts)
    provenance = list(complete_none.get("provenance_statuses") or []) + list(
        complete_session.get("provenance_statuses") or []
    )
    found = _product_found(
        [complete_none, complete_session],
        [object_summary, evidence_summary],
    )
    status = classify_loadability(
        candidate_present=candidate_present,
        payload_present=payload_present,
        product_found=found,
        provenance_statuses=provenance,
        quotes_checked=quote_report["quotes_checked"],
        quotes_all_matched=quote_report["quotes_all_matched"],
    )
    complete_none.pop("excerpts", None)
    complete_session.pop("excerpts", None)
    return {
        "node_id": node_id,
        "candidate_present": candidate_present,
        "payload_present": payload_present,
        "product_found": found,
        "status": status,
        "quote_report": {
            "quotes_checked": quote_report["quotes_checked"],
            "quotes_all_matched": quote_report["quotes_all_matched"],
            "matched": quote_report["matched"],
        },
        "complete_object_focus_none": complete_none,
        "complete_object_focus_session": complete_session,
        "object": object_summary,
        "evidence": evidence_summary,
    }


def run_loadability_probe(
    client: httpx.Client,
    *,
    campaign_id: str = LOADABILITY_CAMPAIGN_ID,
    session_id: str = LOADABILITY_SESSION_ID,
    candidate_node_id: str = CANDIDATE_NODE_ID,
    search_text: str = SEARCH_TEXT,
    lookup_ids: Sequence[str] | None = None,
) -> dict[str, Any]:
    ids = list(lookup_ids or (candidate_node_id, PUBLISHED_OBJECT_ID))
    ledger_row = resolve_ledger_session_row(campaign_id, session_id)
    revision_pin = ledger_row["receipt_child_revision"]
    if revision_pin == TERMINAL_HEAD:
        raise RuntimeError(
            f"{campaign_id}/{session_id} unexpectedly equals terminal head"
        )
    if (
        campaign_id == LOADABILITY_CAMPAIGN_ID
        and session_id == LOADABILITY_SESSION_ID
        and revision_pin != C2S22_REVISION
    ):
        raise RuntimeError(
            f"C2S22 revision drifted: got {revision_pin}, expected {C2S22_REVISION}"
        )

    locator = ledger_row.get("candidate_locator")
    if not isinstance(locator, str) or not locator:
        raise RuntimeError("candidate_locator missing from ledger row")
    candidate_path = PROJECT_ROOT / locator
    extracted = extract_candidate_node(candidate_path, candidate_node_id)
    payload_rows = lookup_payload_objects(
        revision_id=revision_pin,
        object_ids=ids,
        label_needle=search_text,
    )
    payload_ids = {row["object_id"] for row in payload_rows}
    identity_remap = None
    if extracted["present"] and candidate_node_id not in payload_ids:
        published = sorted(
            item for item in payload_ids if item != candidate_node_id
        )
        if published:
            identity_remap = {
                "from_candidate_id": candidate_node_id,
                "to_published_ids": published,
            }

    search_world_status, search_world_body = _post_json(
        client,
        "/api/live/world-graph/retrieval/search",
        build_loadability_search_request(
            query_text=search_text,
            revision_pin=revision_pin,
            campaign_id=campaign_id,
            scope_mode="world",
            focus_session_id=session_id,
        ),
    )
    search_campaign_status, search_campaign_body = _post_json(
        client,
        "/api/live/world-graph/retrieval/search",
        build_loadability_search_request(
            query_text=search_text,
            revision_pin=revision_pin,
            campaign_id=campaign_id,
            scope_mode="campaign",
            focus_session_id=session_id,
        ),
    )

    identities = [
        probe_identity(
            client,
            node_id=node_id,
            revision_pin=revision_pin,
            campaign_id=campaign_id,
            session_id=session_id,
            candidate_present=extracted["present"] and node_id == candidate_node_id,
            payload_present=node_id in payload_ids,
            candidate_quotes=extracted.get("quotes") or [],
        )
        for node_id in ids
    ]
    seed_status = roll_up_seed_status(row["status"] for row in identities)
    return {
        "schema": "dmb_current_corpus_loadability_probe_v1",
        "probed_at": datetime.now(timezone.utc).isoformat(),
        "world_id": WORLD_ID,
        "campaign_id": campaign_id,
        "session_id": session_id,
        "revision_pin": revision_pin,
        "terminal_head": TERMINAL_HEAD,
        "search_text": search_text,
        "candidate": candidate_public_view(extracted),
        "payload_objects": payload_rows,
        "identity_remap": identity_remap,
        "search_world": summarize_retrieval(search_world_status, search_world_body),
        "search_campaign": summarize_retrieval(
            search_campaign_status, search_campaign_body
        ),
        "identities": identities,
        "seed_status": seed_status,
        "openable": seed_status == STATUS_EXCERPT_READY,
        "notes": [
            "Read-only evaluator probe; not an admission gate.",
            "Quote text and source excerpts are not persisted.",
        ],
    }
