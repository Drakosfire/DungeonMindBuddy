#!/usr/bin/env python3
"""Deterministic dogfood gate for Hermes Graph retrieval session.

Does not require a live Hermes model. Exercises:
  1) digest completeness (Tripod contribution)
  2) preflight → GraphRetrievalSession claim ledger
  3) expand_graph_retrieval (search / object)
  4) structured answer validation (graph-grounded without unread source cites)

Usage:
  PYTHONPATH=src:. python scripts/hermes_graph_dogfood_gate.py
  PYTHONPATH=src:. python scripts/hermes_graph_dogfood_gate.py --root out
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
_SRC = REPO_ROOT / "src"
for _path in (str(REPO_ROOT), str(_SRC)):
    if _path not in sys.path:
        sys.path.insert(0, _path)

from graph_memory.interaction.answer_validator import validate_structured_answer  # noqa: E402
from graph_memory.interaction.digest_audit import (  # noqa: E402
    TRIPOD_CONTRIBUTION_ID,
    audit_contribution_source_digests,
)
from graph_memory.interaction.expansion_executor import (  # noqa: E402
    execute_expand_graph_retrieval,
)
from graph_memory.interaction.initial_resolve import create_session_from_preflight  # noqa: E402
from graph_memory.interaction.session_store import clear_sessions  # noqa: E402
from graph_memory.world_supergraph.storage import load_current_world_graph  # noqa: E402


def _preflight_envelope(*, root: Path, question: str) -> dict:
    head, revision, store = load_current_world_graph(root, "eldyrwild")
    revision_id = (
        getattr(store, "revision_id", None)
        or getattr(revision, "revision_id", None)
        or head.head_revision_id
    )
    # Prefer Tripod durable id if present in the head store.
    store_nodes = getattr(store, "nodes", {}) or {}
    if not isinstance(store_nodes, dict):
        store_nodes = {}
    nodes = list(store_nodes)
    campaign_id = str(getattr(store, "campaign_id", None) or "longmont-c2")
    tripod_candidates = [
        nid
        for nid in nodes
        if "tripod" in str(nid).lower()
    ]
    session_seeds = [
        nid
        for nid in nodes
        if "session-" in str(nid).lower() or str(nid).startswith("event:")
    ]
    matched = tripod_candidates[:3] or session_seeds[:3] or list(nodes)[:3]
    return {
        "schema": "dmb_agent_world_graph_query_context_v1",
        "status": "ready",
        "world_id": "eldyrwild",
        "campaign_id": campaign_id,
        "revision_id": revision_id,
        "head_revision_id": head.head_revision_id,
        "is_head": True,
        "focus": {"kind": "session", "session_id": "session-21"},
        "admissibility": "gm",
        "query_text": question,
        "matched_node_ids": matched,
        "nodes": [{"node_id": nid, "label": nid} for nid in matched],
        "relationships": [],
        "attributes": [],
        "projection_truncated": False,
        "diagnostics": [],
        "warning_codes": [],
        "trust_boundary": {
            "graph_role": "structured_campaign_memory_and_navigation",
            "citation_authority": "corpus_source_evidence",
            "graph_citations_permitted": False,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=REPO_ROOT / "out")
    parser.add_argument(
        "--question",
        default="What happened last session involving Tripod?",
    )
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    root = args.root.expanduser().resolve()

    clear_sessions()
    report: dict = {"ok": True, "checks": {}}

    digests = audit_contribution_source_digests(
        root,
        world_id="eldyrwild",
        highlight_contribution_ids=[TRIPOD_CONTRIBUTION_ID],
    )
    report["checks"]["digest_complete"] = digests["complete"]
    report["checks"]["tripod_digest"] = digests["highlighted"].get(TRIPOD_CONTRIBUTION_ID)
    if not digests["complete"]:
        report["ok"] = False

    envelope = _preflight_envelope(root=root, question=args.question)
    session = create_session_from_preflight(envelope, question=args.question)
    report["checks"]["session_id"] = session.id
    report["checks"]["revision_id"] = session.snapshot.revision_id
    report["checks"]["claim_count"] = len(session.claims)
    report["checks"]["factual_claim_count"] = sum(
        1 for c in session.claims if c.may_state_as_campaign_fact()
    )
    if report["checks"]["factual_claim_count"] < 1:
        report["ok"] = False

    expand = execute_expand_graph_retrieval(
        {
            "schema": "dmb_expand_graph_retrieval_request_v1",
            "retrieval_session_id": session.id,
            "operation": "search",
            "query_text": args.question,
            "targets": [
                {"kind": "node", "id": nid}
                for nid in session.preflight_candidate_ids[:3]
            ],
        },
        root=root,
    )
    report["checks"]["expand_schema"] = expand.get("schema")
    report["checks"]["expand_outcome"] = expand.get("outcome")
    if expand.get("schema") == "dmb_world_graph_retrieval_error_v1":
        # Object expand is a softer fallback for sparse search support.
        expand = execute_expand_graph_retrieval(
            {
                "schema": "dmb_expand_graph_retrieval_request_v1",
                "retrieval_session_id": session.id,
                "operation": "object",
                "targets": [
                    {"kind": "node", "id": nid}
                    for nid in session.preflight_candidate_ids[:1]
                ],
            },
            root=root,
        )
        report["checks"]["expand_fallback"] = expand.get("operation") or "object"
        report["checks"]["expand_schema"] = expand.get("schema")
        report["checks"]["expand_outcome"] = expand.get("outcome")

    from graph_memory.interaction.session_store import get_session

    session = get_session(session.id) or session
    validated = validate_structured_answer(
        session,
        None,
        model_prose="Tripod remains an active threat near the focus session.",
    )
    report["checks"]["outcome"] = validated.outcome
    report["checks"]["accepted_claim_ids"] = validated.accepted_claim_ids
    report["checks"]["graph_reference_count"] = len(validated.graph_references)
    report["checks"]["source_citation_count"] = len(validated.source_citations)
    if validated.outcome in {"abstained", "execution_error", "unsupported"}:
        report["ok"] = False
    if validated.source_citations:
        # Dogfood gate: unread anchors must not invent source citations.
        report["ok"] = False
        report["checks"]["source_citation_violation"] = True

    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(f"ok={report['ok']}")
        for key, value in report["checks"].items():
            print(f"{key}={json.dumps(value, sort_keys=True)}")

    clear_sessions()
    return 0 if report["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
