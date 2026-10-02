#!/usr/bin/env python3
"""Run synthetic direct-fact and two-hop Graph questions through Hermes + fake reads."""

from __future__ import annotations
import hashlib
import json
import os
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
from apps.live_control_server.services.agent_graph_policy import (  # noqa: E402
    resolve_agent_graph_openai_inference,
)
from apps.live_control_server.services.hermes_graph_agent import (  # noqa: E402
    run_hermes_graph_agent_turn,
)
from apps.live_control_server.services.hermes_graph_agent_contract import (  # noqa: E402
    HermesGraphAgentTurnRequest,
)
from graph_memory.hermes_graph_plugin import (  # noqa: E402
    HermesGraphScope,
    default_graph_only_capability_policy,
)

HERE = Path(__file__).resolve().parent
WORKER_HOME = Path(
    os.environ.get(
        "DMB_HERMES_GRAPH_AGENT_WORKER_HOME", "/tmp/hermes-tuning-worker-home"
    )
)
(WORKER_HOME / "logs").mkdir(parents=True, exist_ok=True)
os.environ.setdefault("DMB_HERMES_GRAPH_AGENT_WORKER_HOME", str(WORKER_HOME))
CASES = [
    {
        "id": "synthetic-direct-neras-role-v1",
        "question": "What role does Nera have in Alderwatch?",
    },
    {
        "id": "synthetic-two-hop-nera-quarry-v1",
        "question": "How is Nera connected to the Old Quarry? State the relationship chain and what remains unverified.",
    },
]


def main() -> int:
    if not os.environ.get("OPENAI_API_KEY"):
        raise SystemExit("OPENAI_API_KEY is required; its value is never emitted")
    fixture = json.loads((HERE / "graph_fixture_result.json").read_text())
    import graph_memory.hermes_graph_plugin as graph_plugin

    real_execute = graph_plugin.execute_hermes_graph_interaction_tool_json
    active_case_reads = []
    active_case_id = ""

    def fake_execute(tool_name: str, arguments: Any, *, root: Any = None) -> str:
        del root
        args = dict(arguments or {})
        item = {
            "tool_name": tool_name,
            "operation": args.get("operation"),
            "query_text_sha256": hashlib.sha256(
                str(args.get("queryText", "")).encode()
            ).hexdigest()[:16],
            "seed_node_ids": args.get("seedNodeIds", []),
        }
        active_case_reads.append(item)

        def error_response(message: str) -> str:
            item.update(
                {
                    "result_status": "error",
                    "error_code": "invalid_request",
                    "status_code": 422,
                    "error_message": message,
                }
            )
            return json.dumps(
                {
                    "schema": "dmb_world_graph_retrieval_error_v1",
                    "code": "invalid_request",
                    "message": message,
                    "statusCode": 422,
                    "diagnostics": [],
                }
            )

        op = args.get("operation") or "search"
        if op == "neighborhood" and "person:nera" not in args.get("seedNodeIds", []):
            return error_response(
                "seedNodeIds must contain the accepted candidate person:nera"
            )
        if op == "object" and args.get("nodeId") != "person:nera":
            return error_response("nodeId must identify an accepted candidate")
        if op not in {"search", "neighborhood", "object"}:
            return error_response("unsupported synthetic operation")
        payload = dict(fixture)
        payload["operation"] = op
        if op in {"search", "object"}:
            payload["outcome"] = (
                "partial"
                if active_case_id == "synthetic-two-hop-nera-quarry-v1"
                else "enough"
            )
            payload["diagnostics"] = (
                [
                    {
                        "code": "coverage_gap",
                        "message": "Search did not return relationship coverage.",
                        "severity": "warning",
                    }
                ]
                if payload["outcome"] == "partial"
                else []
            )
            payload["matchedNodeIds"] = ["person:nera"]
            payload["nodes"] = fixture["nodes"][:1]
            payload["relationships"] = []
            payload["attributes"] = [
                item
                for item in fixture["attributes"]
                if item["subjectNodeId"] == "person:nera"
            ]
        elif op == "neighborhood":
            payload["outcome"] = "enough" if args.get("maxDepth", 1) == 2 else "partial"
            payload["matchedNodeIds"] = ["person:nera", "place:east-tower"]
            payload["nodes"] = fixture["nodes"][:2]
            payload["relationships"] = fixture["relationships"][:1]
            if args.get("maxDepth", 1) == 2:
                payload["matchedNodeIds"] = fixture["matchedNodeIds"]
                payload["nodes"] = fixture["nodes"]
                payload["relationships"] = fixture["relationships"]
        item.update(
            {
                "result_status": "ok",
                "outcome": payload.get("outcome"),
                "matched_node_ids": payload.get("matchedNodeIds", []),
                "relationship_ids": [
                    edge["edgeId"] for edge in payload.get("relationships", [])
                ],
            }
        )
        return json.dumps(payload, ensure_ascii=False)

    graph_plugin.execute_hermes_graph_interaction_tool_json = fake_execute
    provider, model, base_url = resolve_agent_graph_openai_inference(
        require_api_key=True
    )
    scope = HermesGraphScope(
        world_id="synthetic:alderwatch",
        campaign_id="synthetic:campaign",
        scope_mode="campaign",
        focus={"kind": "none"},
        admissibility="gm",
        revision_pin="rev:synthetic-1",
    )
    policy = default_graph_only_capability_policy(scope)
    records = []
    try:
        for case in CASES:
            active_case_id = case["id"]
            active_case_reads.clear()
            start = time.perf_counter()
            result = run_hermes_graph_agent_turn(
                HermesGraphAgentTurnRequest(
                    question=case["question"],
                    world_id=scope.world_id,
                    campaign_id=scope.campaign_id,
                    scope_mode="campaign",
                    revision_pin=scope.revision_pin,
                    session_id=f"synthetic-graph-{uuid.uuid4()}",
                    retrieval_session_id="synthetic-read-session",
                    root=Path("/tmp"),
                    surface_context_block=(
                        "Synthetic accepted retrieval candidate: Nera, node ID person:nera. "
                        "This candidate contains no relationship data."
                        if case["id"] == "synthetic-two-hop-nera-quarry-v1"
                        else None
                    ),
                    capability_policy=policy,
                ),
                on_model_call=lambda call: None,
            )
            wall_ms = (time.perf_counter() - start) * 1000
            # Events carry the structural trace for this turn. Fake reads are separately hash-only.
            events = [
                {
                    "tool_name": event.tool_name,
                    "state": event.state,
                    "duration_ms": event.duration_ms,
                    "outcome": event.outcome,
                    "matched_node_ids": event.matched_node_ids,
                    "relationship_ids": event.relationship_ids,
                    "source_anchor_ids": event.source_anchor_ids,
                }
                for event in result.tool_events
            ]
            records.append(
                {
                    "case_id": case["id"],
                    "question": case["question"],
                    "status": result.status,
                    "error_code": result.error_code,
                    "error_message": result.error_message,
                    "wall_ms": round(wall_ms, 1),
                    "response_model_calls": result.model_calls,
                    "tool_events": events,
                    "fake_graph_reads": list(active_case_reads),
                    "tool_read_count": sum(
                        1
                        for event in events
                        if event["tool_name"] == "expand_graph_retrieval"
                        and event["state"] == "completion"
                    ),
                    "answer": result.final_response,
                }
            )
    finally:
        graph_plugin.execute_hermes_graph_interaction_tool_json = real_execute
    output = HERE / "artifacts" / "synthetic-graph-cases.json"
    report = {
        "schema": "hermes_tuning_synthetic_graph_v1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "source": "fully synthetic Graph fixture; production retrieval dispatcher replaced in process",
        "provider": provider,
        "model": model,
        "api_base_url": base_url,
        "fixture_sha256": hashlib.sha256(
            (HERE / "graph_fixture_result.json").read_bytes()
        ).hexdigest(),
        "cases": records,
        "limit": "This measures tool choice against a deterministic fake Graph response; it does not prove native Graph retrieval, traversal, admission, or source authority.",
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(
        json.dumps(
            {
                "output": str(output),
                "model": model,
                "cases": [
                    {
                        "id": r["case_id"],
                        "status": r["status"],
                        "wall_ms": r["wall_ms"],
                        "model_call_count": len(r["response_model_calls"]),
                        "tool_read_count": r["tool_read_count"],
                        "tool_names": [
                            e["tool_name"]
                            for e in r["tool_events"]
                            if e["state"] == "completion"
                        ],
                    }
                    for r in records
                ],
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
