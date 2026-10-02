#!/usr/bin/env python3
"""Offline-capable harness for paired synthetic Hermes Graph crawl turns."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import random
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from apps.live_control_server.services.agent_graph_policy import (  # noqa: E402
    resolve_agent_graph_openai_inference,
)  # noqa: E402
from apps.live_control_server.services.hermes_graph_agent import (  # noqa: E402
    _build_ephemeral_system_prompt,
    run_hermes_graph_agent_turn,
)  # noqa: E402
from apps.live_control_server.services.hermes_graph_agent_contract import (  # noqa: E402
    HermesGraphAgentTurnRequest,
)  # noqa: E402
from graph_memory.hermes_graph_plugin import (  # noqa: E402
    HermesGraphScope,
    default_graph_only_capability_policy,
)  # noqa: E402
from apps.live_control_server.services.hermes_graph_interaction_tools import (  # noqa: E402
    hermes_model_visible_tool_definitions,
)  # noqa: E402
from graph_memory.interaction.expansion_executor import ExpandGraphRetrievalRequest  # noqa: E402

HERE = Path(__file__).resolve().parent
CASES_PATH = HERE / "graph_crawl_cases.json"
MODEL_REQUEST_KEYS = frozenset(
    ExpandGraphRetrievalRequest.model_json_schema(by_alias=True, mode="validation")[
        "properties"
    ]
)
INJECTED_SCOPE_KEYS = frozenset(
    {"worldId", "campaignId", "scopeMode", "focus", "admissibility", "revisionPin"}
)
INSTRUCTION = "When the initial Graph result leaves a requested relationship unsupported or ambiguous, make up to two bounded follow-up Graph reads: use `object` on an accepted candidate only if needed to resolve its identity, then `neighborhood` with an accepted node target and depth 1 or 2. Stop when the path is supported; if the bounded reads leave no path or multiple candidates, state that clearly without inferring a connection."


def sha(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def load_cases() -> list[dict[str, Any]]:
    payload = json.loads(CASES_PATH.read_text(encoding="utf-8"))
    cases = payload.get("cases")
    if (
        payload.get("schema") != "hermes_synthetic_graph_crawl_cases_v1"
        or len(cases or []) != 6
    ):
        raise ValueError("expected six hermes_synthetic_graph_crawl_cases_v1 cases")
    if len({case.get("case_id") for case in cases}) != 6:
        raise ValueError("case IDs must be unique")
    if sum(case["candidate_mode"] == "supplied" for case in cases) != 3:
        raise ValueError("expected three supplied and three discovered cases")
    return cases


def model_visible_tool_contract() -> dict[str, dict[str, Any]]:
    defs = hermes_model_visible_tool_definitions()
    by_name = {item["function"]["name"]: item["function"] for item in defs}
    expand = by_name.get("expand_graph_retrieval")
    if not expand:
        raise RuntimeError("model-visible expand_graph_retrieval tool missing")
    props = expand["parameters"]["properties"]
    if "targets" not in props or "depth" not in props or "operation" not in props:
        raise RuntimeError(
            "model-visible request schema does not expose targets/depth/operation"
        )
    if "seedNodeIds" in props or "maxDepth" in props:
        raise RuntimeError("executor-internal field leaked into model-visible schema")
    return by_name


def build_question(case: dict[str, Any], arm: str) -> str:
    question = case["question"]
    return question if arm == "control" else question + "\n\n" + INSTRUCTION


def build_context(case: dict[str, Any]) -> str | None:
    candidates = case["candidates"]
    if not candidates:
        return None
    return (
        "Synthetic candidate IDs accepted for lookup (no relationships provided): "
        + "; ".join(f"{c['label']} [{c['kind']}, {c['id']}]" for c in candidates)
    )


class StatefulFakeDispatcher:
    """Model-facing schema validator and per-turn deterministic synthetic Graph."""

    def __init__(self, case: dict[str, Any]):
        self.case = case
        self.accepted = {item["id"] for item in case["candidates"]}
        self.search_done = False
        self.reads: list[dict[str, Any]] = []
        self.edges_returned: list[str] = []

    def execute(self, tool_name: str, arguments: Any, *, root: Any = None) -> str:
        del root
        args = dict(arguments or {})
        if tool_name != "expand_graph_retrieval":
            return self._record_error(tool_name, args, "unsupported_synthetic_tool")
        unexpected = set(args) - MODEL_REQUEST_KEYS - INJECTED_SCOPE_KEYS
        if unexpected:
            return self._record_error(tool_name, args, "unexpected_request_fields")
        wire_args = {
            key: value for key, value in args.items() if key in MODEL_REQUEST_KEYS
        }
        try:
            validated = ExpandGraphRetrievalRequest.model_validate(wire_args)
        except Exception:
            return self._record_error(tool_name, args, "invalid_model_visible_request")
        args = validated.model_dump(by_alias=True, exclude_none=True)
        op = args.get("operation")
        targets = args.get("targets", [])
        depth = args.get("depth")
        row: dict[str, Any] = {
            "tool_name": tool_name,
            "operation": op,
            "targets": targets,
            "depth": depth,
        }
        self.reads.append(row)
        if op not in {"search", "object", "neighborhood"}:
            return self._error(row, "unsupported_operation")
        if not isinstance(targets, list) or any(
            not isinstance(t, dict)
            or set(t) != {"kind", "id"}
            or t.get("kind") != "node"
            or not isinstance(t.get("id"), str)
            for t in targets
        ):
            return self._error(row, "invalid_targets_schema")
        ids = [t["id"] for t in targets]
        if op == "search":
            if any(node_id not in self.accepted for node_id in ids):
                return self._error(row, "search_targets_must_be_accepted")
            candidates = self.case["search_candidates"] if not self.search_done else []
            self.search_done = True
            self.accepted.update(item["id"] for item in candidates)
            result = self._payload(op, candidates, [], [], "partial")
        elif op == "object":
            if len(ids) != 1 or ids[0] not in self.accepted:
                return self._error(row, "object_requires_one_accepted_target")
            attrs = [
                {"subjectNodeId": ids[0], **item}
                for item in self.case["identity_attributes"].get(ids[0], [])
            ]
            nodes = [self._node(ids[0])]
            result = self._payload(op, nodes, [], attrs, "enough")
        else:
            if (
                not ids
                or len(ids) > 8
                or any(i not in self.accepted for i in ids)
                or depth not in (1, 2)
            ):
                return self._error(
                    row, "neighborhood_requires_accepted_targets_and_depth_1_or_2"
                )
            returned_nodes, returned_edges = self._reachable(ids, depth)
            self.edges_returned.extend(e["id"] for e in returned_edges)
            result = self._payload(
                op,
                returned_nodes,
                returned_edges,
                [],
                "enough" if returned_edges else "partial",
            )
        row.update(
            {
                "result_status": "ok",
                "outcome": result["outcome"],
                "returned_node_ids": result["matchedNodeIds"],
                "returned_edge_ids": [e["edgeId"] for e in result["relationships"]],
                "returned_attributes": result["attributes"],
            }
        )
        return json.dumps(result, ensure_ascii=False)

    def _record_error(self, tool: str, args: dict[str, Any], code: str) -> str:
        row = {
            "tool_name": tool,
            "operation": args.get("operation"),
            "targets": args.get("targets"),
            "depth": args.get("depth"),
        }
        self.reads.append(row)
        return self._error(row, code)

    def _error(self, row: dict[str, Any], code: str) -> str:
        row.update({"result_status": "error", "error_code": code})
        return json.dumps(
            {
                "schema": "dmb_world_graph_retrieval_error_v1",
                "code": code,
                "message": "Synthetic request rejected by fixture contract.",
                "statusCode": 422,
                "diagnostics": [],
            }
        )

    def _node(self, node_id: str) -> dict[str, Any]:
        return next(node for node in self.case["nodes"] if node["id"] == node_id)

    def _reachable(
        self, seeds: list[str], depth: int
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        seen = set(seeds)
        frontier = set(seeds)
        edges: list[dict[str, Any]] = []
        for _ in range(depth):
            next_frontier: set[str] = set()
            for edge in self.case["edges"]:
                if edge["source"] in frontier and edge["id"] not in {
                    e["id"] for e in edges
                }:
                    edges.append(edge)
                    next_frontier.add(edge["target"])
            seen.update(next_frontier)
            frontier = next_frontier
        nodes = [
            self._node(node_id)
            for node_id in seen
            if any(n["id"] == node_id for n in self.case["nodes"])
        ]
        return nodes, edges

    @staticmethod
    def _payload(
        op: str,
        nodes: list[dict[str, Any]],
        edges: list[dict[str, Any]],
        attrs: list[dict[str, Any]],
        outcome: str,
    ) -> dict[str, Any]:
        return {
            "schema": "dmb_world_graph_retrieval_result_v1",
            "operation": op,
            "outcome": outcome,
            "matchedNodeIds": [n["id"] for n in nodes],
            "nodes": [
                {"nodeId": n["id"], "label": n["label"], "kind": n["kind"]}
                for n in nodes
            ],
            "relationships": [
                {
                    "edgeId": e["id"],
                    "sourceNodeId": e["source"],
                    "targetNodeId": e["target"],
                    "predicate": e["predicate"],
                    "label": e["label"],
                }
                for e in edges
            ],
            "attributes": [
                {
                    "subjectNodeId": a["subjectNodeId"],
                    "predicate": a["predicate"],
                    "textValue": a["value"],
                }
                for a in attrs
            ],
            "sourceAnchors": [],
            "coverage": {},
            "diagnostics": [],
        }


def hard_gates(
    case: dict[str, Any],
    answer: str | None,
    status: str,
    dispatcher: StatefulFakeDispatcher,
) -> dict[str, Any]:
    text = (answer or "").casefold()
    errors = [r for r in dispatcher.reads if r.get("result_status") == "error"]
    required_ids = case["expected_edge_ids"]
    returned = set(dispatcher.edges_returned)
    asserted_edges_covered = all(edge_id in returned for edge_id in required_ids)
    identity_ok = (
        not case.get("required_identity_value")
        or case["required_identity_value"] in text
    )
    if case.get("must_abstain"):
        if case.get("abstention_reason") == "ambiguous":
            abstention_ok = any(
                s in text
                for s in (
                    "which tavi",
                    "which of the two",
                    "can't identify which",
                    "cannot identify which",
                    "can't tell which",
                    "cannot tell which",
                    "can't determine which",
                    "cannot determine which",
                    "no further details to distinguish",
                    "records do not distinguish",
                    "records don't distinguish",
                    "unable to distinguish",
                    "cannot tell",
                    "can't tell",
                    "unclear",
                )
            )
        else:
            abstention_ok = any(
                s in text
                for s in (
                    "no path",
                    "not found",
                    "no connection",
                    "not connected",
                    "couldn't find",
                    "could not find",
                    "no relationship",
                    "does not establish a connection",
                    "doesn't establish a connection",
                    "did not establish a connection",
                    "records do not show",
                    "records don't show",
                )
            )
            abstention_ok = abstention_ok and any(
                s in text
                for s in (
                    "bounded lookup",
                    "the lookup",
                    "this lookup",
                    "these results",
                    "retrieved records",
                    "available records",
                    "this search",
                    "in the graph results",
                )
            )
    else:
        abstention_ok = True
    mentions_expected = all(
        any(
            tok in text
            for tok in (
                edge["label"].casefold(),
                edge["predicate"].replace("_", " ").casefold(),
            )
        )
        for edge in case["edges"]
        if edge["id"] in required_ids
    )
    successful_no_path_neighborhood = any(
        read.get("operation") == "neighborhood"
        and read.get("result_status") == "ok"
        and not read.get("returned_edge_ids")
        for read in dispatcher.reads
    )
    successful_ambiguous_search = any(
        read.get("operation") == "search"
        and read.get("result_status") == "ok"
        and len(read.get("returned_node_ids", [])) > 1
        for read in dispatcher.reads
    )
    if case.get("abstention_reason") == "no_path":
        abstention_ok = abstention_ok and successful_no_path_neighborhood
    no_global_absence_claim = (
        not any(
            s in text
            for s in (
                "does not exist",
                "never existed",
                "no connection exists",
                "there is no connection",
            )
        )
        if case.get("must_abstain")
        else True
    )
    gates = {
        "turn_status_ok": status == "ok",
        "nonempty_answer": bool(text.strip()),
        "no_failed_graph_operations": not errors,
        "all_expected_edges_returned_before_answer": asserted_edges_covered,
        "expected_chain_named_in_answer": mentions_expected if required_ids else True,
        "identity_disambiguation_resolved": identity_ok,
        "required_abstention_explicit": abstention_ok,
        "no_unbounded_absence_claim": no_global_absence_claim,
    }
    gates["traversal_success"] = not errors and (
        (bool(required_ids) and asserted_edges_covered)
        or (
            case.get("abstention_reason") == "no_path"
            and successful_no_path_neighborhood
        )
        or (
            case.get("abstention_reason") == "ambiguous" and successful_ambiguous_search
        )
    )
    gates["successful_no_path_neighborhood"] = (
        case.get("abstention_reason") != "no_path" or successful_no_path_neighborhood
    )
    gates["answer_gate_pass"] = all(
        v for k, v in gates.items() if k not in {"traversal_success"}
    )
    return gates


def safe_call(call: dict[str, Any]) -> dict[str, Any]:
    usage = call.get("usage") if isinstance(call.get("usage"), dict) else {}
    cost = call.get("cost") if isinstance(call.get("cost"), dict) else {}
    return {
        k: call.get(k)
        for k in (
            "status",
            "provider",
            "requested_model",
            "response_model",
            "duration_ms",
        )
        if k in call
    } | {
        "usage": {
            k: usage[k]
            for k in usage
            if k
            in {"input_tokens", "output_tokens", "total_tokens", "cached_input_tokens"}
        },
        "cost": {
            k: cost[k]
            for k in cost
            if k in {"status", "usd", "currency", "pricing_table_matched"}
        },
    }


def build_request(
    case: dict[str, Any],
    arm: str,
    policy: Any,
    scope: HermesGraphScope,
    *,
    session_id: str,
    retrieval_session_id: str,
) -> HermesGraphAgentTurnRequest:
    return HermesGraphAgentTurnRequest(
        question=build_question(case, arm),
        world_id=scope.world_id,
        campaign_id=scope.campaign_id,
        scope_mode=scope.scope_mode,
        revision_pin=scope.revision_pin,
        session_id=session_id,
        retrieval_session_id=retrieval_session_id,
        root=Path("/tmp"),
        surface_context_block=build_context(case),
        capability_policy=policy,
    )


def normalized_system_prompt_sha256(system: str, retrieval_session_id: str) -> str:
    encoded_id = json.dumps(retrieval_session_id, ensure_ascii=False)
    if system.count(encoded_id) != 1:
        raise ValueError(
            "fresh retrievalSessionId must occur exactly once in system prompt"
        )
    normalized = system.replace(encoded_id, json.dumps("<fresh-retrieval-session>"), 1)
    return sha(normalized)


def write_checkpoint(path: Path, record: dict[str, Any]) -> None:
    record["checkpoint_sha256"] = pilot_rows_sha256(record.get("cases", []))
    temporary = path.with_name(path.name + ".checkpoint.tmp")
    temporary.write_text(
        json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    temporary.replace(path)


def run_arm(
    case: dict[str, Any],
    arm: str,
    model: str,
    request: HermesGraphAgentTurnRequest,
    system: str,
    dispatcher: StatefulFakeDispatcher,
    checkpoint_raw: Callable[[dict[str, Any]], None],
) -> dict[str, Any]:
    import graph_memory.hermes_graph_plugin as graph_plugin

    prior = graph_plugin.execute_hermes_graph_interaction_tool_json
    graph_plugin.execute_hermes_graph_interaction_tool_json = dispatcher.execute
    started = time.perf_counter()
    try:
        result = run_hermes_graph_agent_turn(request)
    finally:
        graph_plugin.execute_hermes_graph_interaction_tool_json = prior
    wall_ms = round((time.perf_counter() - started) * 1000, 1)
    calls = [safe_call(dict(item)) for item in result.model_calls]
    raw = {
        "arm": arm,
        "answer": result.final_response,
        "status": result.status,
        "error_code": result.error_code,
        "wall_ms": wall_ms,
        "system_prompt_sha256": sha(system),
        "normalized_system_prompt_sha256": normalized_system_prompt_sha256(
            system, request.retrieval_session_id
        ),
        "question_sha256": sha(request.question),
        "model_calls": calls,
        "model_call_count": len(calls),
        "tool_events": [
            {
                "tool_name": event.tool_name,
                "state": event.state,
                "duration_ms": event.duration_ms,
                "outcome": event.outcome,
                "matched_node_ids": event.matched_node_ids,
                "relationship_ids": event.relationship_ids,
            }
            for event in result.tool_events
        ],
        "fake_trace": dispatcher.reads,
    }
    checkpoint_raw(raw)
    raw["gates"] = hard_gates(
        case, result.final_response, str(result.status), dispatcher
    )
    return raw


def blinded_packet(
    cases: list[dict[str, Any]], results: list[dict[str, Any]], seed: int = 47029
) -> dict[str, Any]:
    rng = random.Random(seed)
    mapped = {item["case_id"]: item for item in results}
    packet = []
    for case in cases:
        result = mapped[case["case_id"]]
        edge_by_id = {edge["id"]: edge for edge in case["edges"]}
        node_by_id = {node["id"]: node for node in case["nodes"]}
        blinded_outputs = []
        for arm in ("control", "treatment"):
            raw = result["arms"][arm]
            seen_edges = {
                edge_id
                for read in raw.get("fake_trace", [])
                for edge_id in read.get("returned_edge_ids", [])
            }
            seen_nodes = {
                node_id
                for read in raw.get("fake_trace", [])
                for node_id in read.get("returned_node_ids", [])
            }
            seen_attributes = [
                attribute
                for read in raw.get("fake_trace", [])
                for attribute in read.get("returned_attributes", [])
            ]
            facts = {
                "nodes": [
                    node_by_id[node_id]
                    for node_id in sorted(seen_nodes)
                    if node_id in node_by_id
                ],
                "relationships": [
                    edge_by_id[edge_id]
                    for edge_id in sorted(seen_edges)
                    if edge_id in edge_by_id
                ],
                "identity_attributes": seen_attributes,
            }
            blinded_outputs.append({"answer": raw["answer"], "evidence_seen": facts})
        rng.shuffle(blinded_outputs)
        key = {
            "supported_relationships": [
                edge_by_id[edge_id] for edge_id in case["expected_edge_ids"]
            ],
            "expected_abstention": case.get("abstention_reason"),
            "required_identity_value": case.get("required_identity_value"),
        }
        packet.append(
            {
                "case_id": case["case_id"],
                "question": case["question"],
                "shared_candidate_context": build_context(case),
                "answer_A": blinded_outputs[0]["answer"],
                "answer_A_evidence_seen": blinded_outputs[0]["evidence_seen"],
                "answer_A_sha256": sha(blinded_outputs[0]["answer"] or ""),
                "answer_B": blinded_outputs[1]["answer"],
                "answer_B_evidence_seen": blinded_outputs[1]["evidence_seen"],
                "answer_B_sha256": sha(blinded_outputs[1]["answer"] or ""),
                "expected_answer_key": key,
                "human_score": "pending",
            }
        )
    return {
        "schema": "hermes_graph_crawl_blinded_packet_v1",
        "randomization_seed": seed,
        "items": packet,
    }


def map_blinded_answer_hashes(
    raw_cases: list[dict[str, Any]], blinded_items: list[dict[str, Any]]
) -> dict[str, dict[str, str]]:
    """Join locked A/B answers to raw arms by exact unchanged-answer SHA-256."""
    raw_by_case = {case["case_id"]: case for case in raw_cases}
    if len(raw_by_case) != len(raw_cases):
        raise ValueError("raw case IDs must be unique")
    mapped: dict[str, dict[str, str]] = {}
    for item in blinded_items:
        case_id = item["case_id"]
        if case_id in mapped or case_id not in raw_by_case:
            raise ValueError("blind packet case IDs must map uniquely to raw cases")
        raw_arms = raw_by_case[case_id]["arms"]
        row: dict[str, str] = {}
        for label in ("A", "B"):
            answer_hash = item[f"answer_{label}_sha256"]
            matches = [
                arm
                for arm, result in raw_arms.items()
                if hashlib.sha256(result["answer"].encode("utf-8")).hexdigest()
                == answer_hash
            ]
            if len(matches) != 1 or matches[0] in row.values():
                raise ValueError(
                    f"blind answer {case_id}/{label} must match exactly one unique raw arm"
                )
            row[label] = matches[0]
        mapped[case_id] = row
    if set(mapped) != set(raw_by_case):
        raise ValueError("blind packet must include every raw case exactly once")
    return mapped


def pilot_rows_sha256(rows: list[dict[str, Any]]) -> str:
    return sha(json.dumps(rows, sort_keys=True, separators=(",", ":")))


def load_resume_record(
    path: Path,
    *,
    provider: str,
    model: str,
    fixture_sha: str,
    instruction_sha: str,
    cases: list[dict[str, Any]],
    prime_approval_reference: str | None,
    requested_stop_after: int,
) -> dict[str, Any]:
    record = json.loads(path.read_text(encoding="utf-8"))
    if record.get("schema") != "hermes_synthetic_graph_crawl_pairs_v1":
        raise ValueError("resume artifact schema mismatch")
    if record.get("provider") != provider or record.get("model") != model:
        raise ValueError("resume provider/model mismatch; refusing a mixed cohort")
    if (
        record.get("fixture_sha256") != fixture_sha
        or record.get("instruction_sha256") != instruction_sha
    ):
        raise ValueError("resume fixture/instruction mismatch; refusing a mixed cohort")
    rows = record.get("cases", [])
    status = record.get("cohort_status")
    max_rows = (
        2 if status in {"pilot_in_progress", "pilot_pending_prime_checkin"} else 6
    )
    expected_ids = [case["case_id"] for case in cases[: len(rows)]]
    if (
        not rows
        or len(rows) > max_rows
        or [row.get("case_id") for row in rows] != expected_ids
    ):
        raise ValueError(
            "resume artifact has an invalid case prefix for its recorded phase"
        )
    if status == "pilot_in_progress":
        if requested_stop_after != 2:
            raise ValueError(
                "in-progress pilot can resume only through its first two cases"
            )
        if (
            len(rows) > 2
            or record.get("continuation_approval_reference")
            or prime_approval_reference
        ):
            raise ValueError("in-progress pilot state is malformed")
    elif status == "pilot_pending_prime_checkin":
        if requested_stop_after != 6:
            raise ValueError("pending pilot may continue only after PRIME approval")
        if len(rows) != 2 or record.get("pilot_cases_sha256") != pilot_rows_sha256(
            rows
        ):
            raise ValueError("pending pilot hash/state mismatch")
        if any(set(row.get("arms", {})) != {"control", "treatment"} for row in rows):
            raise ValueError("pending pilot requires both arms in each paired case")
        if not prime_approval_reference:
            raise ValueError(
                "continuing beyond the pilot requires PRIME approval reference"
            )
    elif status == "continuation_in_progress":
        if requested_stop_after != 6:
            raise ValueError(
                "approved continuation must resume through the six-case cohort"
            )
        if (
            len(rows) < 2
            or not prime_approval_reference
            or record.get("continuation_approval_reference") != prime_approval_reference
        ):
            raise ValueError(
                "continuation resume requires its exact recorded PRIME approval reference"
            )
        if record.get("pilot_cases_sha256") != pilot_rows_sha256(rows[:2]):
            raise ValueError("immutable pilot rows changed during continuation")
    else:
        raise ValueError("resume artifact is not an authorized incomplete cohort")
    for row in rows:
        if not isinstance(row.get("arms"), dict) or not set(row["arms"]).issubset(
            {"control", "treatment"}
        ):
            raise ValueError("resume arm checkpoint malformed")
        if row.get("arm_order") not in (
            ["control", "treatment"],
            ["treatment", "control"],
        ):
            raise ValueError("resume arm order malformed")
    if record.get("checkpoint_sha256") != pilot_rows_sha256(rows):
        raise ValueError(
            "resume checkpoint rows changed; refusing to discard or rerun evidence"
        )
    return record


def validate_fresh_output(path: Path, *, resume: bool) -> None:
    if not resume and path.exists():
        raise ValueError("refusing to overwrite an existing cohort artifact")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stop-after", type=int, default=2, choices=(2, 6))
    parser.add_argument("--output", type=Path)
    parser.add_argument("--blind-output", type=Path)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--prime-approval-reference")
    args = parser.parse_args()
    if args.resume and (args.stop_after not in {2, 6} or args.output is None):
        raise SystemExit("--resume requires an existing --output pilot path")
    if args.stop_after == 6 and not args.resume:
        raise SystemExit(
            "the remaining four cases require --resume after PRIME's pilot check-in"
        )
    if args.resume and not args.output.resolve().is_relative_to(Path("/tmp")):
        raise SystemExit(
            "resuming the cohort must keep the cumulative raw artifact under /tmp"
        )
    if args.stop_after == 2 and (
        args.output is None or not args.output.resolve().is_relative_to(Path("/tmp"))
    ):
        raise SystemExit("the two-pair pilot must write to an explicit /tmp path")
    if not args.resume and args.output:
        try:
            validate_fresh_output(args.output, resume=False)
        except ValueError as exc:
            raise SystemExit(str(exc)) from exc

    cases = load_cases()
    model_visible_tool_contract()
    if not os.environ.get("OPENAI_API_KEY"):
        raise SystemExit("OPENAI_API_KEY required; its value is never emitted")
    provider, model, base_url = resolve_agent_graph_openai_inference(
        require_api_key=True
    )
    if provider != "openai-api" or model.casefold() != "gpt-6-luna":
        raise SystemExit(
            f"policy-resolved model mismatch: provider={provider!r}, model={model!r}; no provider calls made"
        )
    scope = HermesGraphScope(
        world_id="synthetic:hermes-crawl",
        campaign_id="synthetic:crawl",
        scope_mode="campaign",
        focus={"kind": "none"},
        admissibility="gm",
        revision_pin="rev:synthetic-crawl-1",
    )
    policy = default_graph_only_capability_policy(scope)
    fixture_sha = sha(CASES_PATH.read_text(encoding="utf-8"))
    instruction_sha = sha(INSTRUCTION)
    if args.resume:
        try:
            record = load_resume_record(
                args.output,
                provider=provider,
                model=model,
                fixture_sha=fixture_sha,
                instruction_sha=instruction_sha,
                cases=cases,
                prime_approval_reference=args.prime_approval_reference,
                requested_stop_after=args.stop_after,
            )
        except (ValueError, OSError, json.JSONDecodeError) as exc:
            raise SystemExit(str(exc)) from exc
        run = record["cases"]
    else:
        run = []
        record = {
            "schema": "hermes_synthetic_graph_crawl_pairs_v1",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "source": "fully synthetic; no user corpus, private data, live Graph, or DB",
            "provider": provider,
            "model": model,
            "api_base_url": base_url,
            "fixture_sha256": fixture_sha,
            "instruction_sha256": instruction_sha,
            "randomization_seed": 91073,
            "blind_randomization_seed": 47029,
            "instruction": INSTRUCTION,
            "cases": run,
            "limits": [
                "Six synthetic pairs are exploratory only.",
                "Fake proves behavior against a deterministic in-process state machine, not native Graph retrieval or source authority.",
                "Operation choice is measured only over this permitted fake response path; model/server process and session admission remain outside the evidence.",
                "Non-streaming TTFT is unknown.",
            ],
        }
    out = args.output or (
        HERE
        / "artifacts"
        / f"graph-crawl-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.json"
    )
    if args.stop_after == 6:
        record["cohort_status"] = "continuation_in_progress"
        record["continuation_approval_reference"] = args.prime_approval_reference
        record.setdefault(
            "continuation_started_at", datetime.now(timezone.utc).isoformat()
        )
    else:
        record["cohort_status"] = "pilot_in_progress"
    write_checkpoint(out, record)

    for index, case in enumerate(cases[: args.stop_after]):
        existing = next((row for row in run if row["case_id"] == case["case_id"]), None)
        if existing is None:
            order = ["control", "treatment"]
            random.Random(91073 + index).shuffle(order)
            existing = {
                "case_id": case["case_id"],
                "candidate_mode": case["candidate_mode"],
                "arm_order": order,
                "arms": {},
            }
            run.append(existing)
            record["cases"] = run
            write_checkpoint(out, record)
        arm_inputs = {}
        for arm in existing["arm_order"]:
            session_id = f"crawl-{case['case_id']}-{arm}-{uuid.uuid4()}"
            retrieval_session_id = f"retrieval-{uuid.uuid4()}"
            request = build_request(
                case,
                arm,
                policy,
                scope,
                session_id=session_id,
                retrieval_session_id=retrieval_session_id,
            )
            system = _build_ephemeral_system_prompt(
                policy, request, retrieval_session_packet=None
            )
            normalized_sha = normalized_system_prompt_sha256(
                system, retrieval_session_id
            )
            arm_inputs[arm] = (request, system, normalized_sha)
        if arm_inputs["control"][2] != arm_inputs["treatment"][2]:
            raise RuntimeError(
                f"normalized system prompt parity failed before provider: {case['case_id']}"
            )
        for saved in existing["arms"].values():
            if "gates" not in saved:
                restored = StatefulFakeDispatcher(case)
                restored.reads = saved.get("fake_trace", [])
                restored.edges_returned = [
                    edge_id
                    for read in restored.reads
                    for edge_id in read.get("returned_edge_ids", [])
                ]
                saved["gates"] = hard_gates(
                    case, saved.get("answer"), str(saved.get("status")), restored
                )
                record["cases"] = run
                write_checkpoint(out, record)
        for arm in existing["arm_order"]:
            if arm in existing["arms"]:
                continue
            request, system, _ = arm_inputs[arm]

            def checkpoint_raw(raw: dict[str, Any]) -> None:
                existing["arms"][arm] = raw
                record["cases"] = run
                record["checkpoint_completed_at"] = datetime.now(
                    timezone.utc
                ).isoformat()
                write_checkpoint(out, record)

            result = run_arm(
                case,
                arm,
                model,
                request,
                system,
                StatefulFakeDispatcher(case),
                checkpoint_raw,
            )
            existing["arms"][arm] = result
            record["cases"] = run
            write_checkpoint(out, record)
        if (
            len(existing["arms"]) == 2
            and existing["arms"]["control"]["normalized_system_prompt_sha256"]
            != existing["arms"]["treatment"]["normalized_system_prompt_sha256"]
        ):
            raise RuntimeError(
                f"normalized system prompt parity failed after provider: {case['case_id']}"
            )

    record["cases"] = run
    record["blind_packet"] = blinded_packet(cases[: len(run)], run)
    record["provider"] = provider
    record["model"] = model
    record["api_base_url"] = base_url
    record["updated_at"] = datetime.now(timezone.utc).isoformat()
    if args.stop_after == 2:
        record["cohort_status"] = "pilot_pending_prime_checkin"
        record["pilot_cases_sha256"] = pilot_rows_sha256(run)
    else:
        record["cohort_status"] = "complete"
    write_checkpoint(out, record)
    if args.blind_output:
        args.blind_output.parent.mkdir(parents=True, exist_ok=True)
        args.blind_output.write_text(
            json.dumps(record["blind_packet"], ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    print(
        json.dumps(
            {
                "output": str(out),
                "provider": provider,
                "model": model,
                "cases": [
                    {
                        "id": row["case_id"],
                        "control_status": row["arms"]["control"]["status"],
                        "treatment_status": row["arms"]["treatment"]["status"],
                        "control_ops": [
                            r.get("operation")
                            for r in row["arms"]["control"]["fake_trace"]
                        ],
                        "treatment_ops": [
                            r.get("operation")
                            for r in row["arms"]["treatment"]["fake_trace"]
                        ],
                    }
                    for row in run
                ],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
