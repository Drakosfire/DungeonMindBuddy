"""Parameterized ordinary turns and provider-free retained-run reporting.

Run with ``python -m evals.buddy_benchmark.workflow --help``. Gold and semantic
reviews belong to reporting only, never to the ordinary capture request.
``writer-prepare`` and ``writer-capture`` isolate retained composition inputs;
their results are provider-only diagnostics, never ordinary delivery or QA grades.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
import os
from pathlib import Path
import secrets
import time
from uuid import NAMESPACE_URL, UUID, uuid4, uuid5

from .artifacts import immutable_save


def read_pin(pin, base):
    path = Path(pin["path"])
    path = path if path.is_absolute() else base / path
    data = path.read_bytes()
    if sha256(data).hexdigest() != pin["sha256"]:
        raise ValueError("Evidence pin mismatch: " + str(path))
    return data


def load_manifest(path, *, schema="dmb_ordinary_benchmark_v1", expected_sha256=None):
    path = Path(path).resolve()
    if expected_sha256 is None:
        data = path.read_bytes()
    else:
        data = read_pin({"path": str(path), "sha256": expected_sha256}, path.parent)
    if schema == "dmb_ordinary_benchmark_v1":
        manifest = json.loads(data)
    else:
        from application_state.agent_conversation.source_writer_output import strict_json
        manifest = strict_json(data.decode("utf-8"))
    if manifest.get("schema") != schema:
        raise ValueError("Unknown ordinary benchmark manifest")
    cases = manifest["cases"]
    ids = [case["id"] for case in cases]
    if not cases or len(ids) != len(set(ids)) or any(
        not value or not value.replace("-", "").replace("_", "").isalnum()
        for value in ids
    ):
        raise ValueError("Cases require unique safe identifiers")
    for case in cases:
        if not isinstance(case["question"], str) or not case["question"].strip():
            raise ValueError("Case question required")
    for pin in manifest.get("pins", []):
        read_pin(pin, path.parent)
    return manifest, path.parent


def _wrapped(path):
    value = json.loads(path.read_text())
    if not isinstance(value.get("http_status"), int) or "body" not in value:
        raise ValueError("Invalid retained HTTP envelope: " + str(path))
    return value


def _pointer(value, pointer):
    if not pointer.startswith("/"):
        raise ValueError("Review evidence needs an explicit JSON pointer")
    for key in pointer[1:].split("/"):
        key = key.replace("~1", "/").replace("~0", "~")
        value = value[int(key)] if isinstance(value, list) else value[key]
    return value


def validate_template(template, world, *, context_only=False, build_sequence=False):
    allowed = {"schema", "client_thread_id", "turn_id", "surface", "owner_scope",
        "primary_work", "client_work_state", "graph_request", "graph_selection", "plan_context_policy"}
    if build_sequence:
        allowed = (allowed - {"plan_context_policy"}) | {"build_authored_references"}
        surface = template.get("surface", {})
        work = template.get("primary_work", {})
        graph = template.get("graph_request", {})
        if (context_only or set(template) - allowed
                or template.get("schema") != "dmb_agent_turn_request_v1"
                or template.get("owner_scope") != {"kind": "world", "world_id": world}
                or template.get("client_work_state") != "saved_clean"
                or surface.get("surface_id") != "build" or work.get("kind") != "build"
                or not work.get("object_id") or surface.get("instance_id") != work["object_id"]
                or work.get("expected_revision") is None or not work.get("expected_content_sha256")
                or template.get("graph_selection") is not None
                or graph.get("mode") != "world" or graph.get("world_id") != world):
            raise ValueError("Build sequence requires a pinned saved page and ordinary World scope")
        return
    if (set(template) - allowed or template.get("schema") != "dmb_agent_turn_request_v1"
        or template.get("graph_selection") is not None
        or template.get("graph_request") != {"mode": "none"}
        or template.get("surface", {}).get("surface_id") != "plan"
        or template.get("owner_scope") != {"kind": "world", "world_id": world}
        or template.get("primary_work", {}).get("kind") != "plan"):
        raise ValueError("Ordinary capture template contains hints or an operation override")
    if context_only and template.get("plan_context_policy") != {
            "schema": "dmb_plan_context_policy_v2", "policy": "auto_plan_world",
            "graph_source": "reviewed_native_graph"}:
        raise ValueError("Context capture requires the explicit shared native Plan route")


def _request_turns(history, request, world, *, browser_plan=False):
    turns = [turn for turn in history["turns"] if turn["user_text"] == request["message"]]
    if browser_plan or request["surface"].get("surface_id") == "build":
        key = str(uuid5(NAMESPACE_URL, f"dmb-agent-turn:{world}:{request['turn_id']}"))
        turns = [turn for turn in turns if turn.get("idempotency_key") == key]
    return turns


def report_case(case, base):
    """Facts from retained receipts; semantic grades only from pinned reviews."""
    directory = Path(case["capture_dir"])
    directory = directory if directory.is_absolute() else base / directory
    boundary = case.get("capture_boundary", "response")
    if boundary in {"image_preview", "play_choice"}:
        result = directory / "fixture-result.json"
        if not result.is_file():
            return {"case_id": case["id"], "capture_boundary": boundary,
                    "delivery": {"status": "unknown"}}
        raw = result.read_bytes()
        observation = json.loads(raw)
        return {"case_id": case["id"], "capture_boundary": boundary,
                "delivery": {"status": "pass" if observation["status"] == "observed" else "fail"},
                "owner_observation": observation,
                "evidence": {"path": str(result), "sha256": sha256(raw).hexdigest()}}
    if boundary not in {"response", "context_ready", "writer_transport"}:
        raise ValueError("Unknown capture boundary")
    context_only = boundary != "response"
    detailed_trace = case.get("detailed_trace", False)
    if type(detailed_trace) is not bool or (detailed_trace and not context_only):
        raise ValueError("Invalid detailed trace mode")
    names = ("request", "history-after", "context-trace") + (
        ("context-ready", "context-request", "context-stop") if context_only else ("answer-http",))
    detail_path = directory / "detailed-host-trace.json"
    if not detailed_trace and detail_path.exists():
        raise ValueError("Detailed host trace differs from the requested mode")
    if detailed_trace:
        names += ("detailed-host-trace",)
    paths = {name: directory / (name + ".json") for name in names}
    if context_only and (directory / "answer-http.json").exists():
        paths["answer-http"] = directory / "answer-http.json"
    if not context_only:
        for name in ("saved-citation-reopen", "native-citation-reopen"):
            citation_path = directory / (name + ".json")
            if citation_path.is_file():
                paths[name] = citation_path
    for surface in ("build", "plan"):
        wire_name = surface + "-wire-response"
        wire_path = directory / (wire_name + ".json")
        if not context_only and wire_path.is_file():
            paths[wire_name] = wire_path
            if "answer-http" in paths and not paths["answer-http"].is_file():
                del paths["answer-http"]
    missing = [name for name, path in paths.items() if not path.exists()]
    if missing:
        failure_status = None
        if {"plan-wire-response", "answer-http", "request"} <= paths.keys() and all(
                paths[name].is_file() for name in ("plan-wire-response", "answer-http", "request")):
            wire_failure = json.loads(paths["plan-wire-response"].read_bytes())
            raw_failure = bytes.fromhex(wire_failure["raw_body_hex"])
            response = _wrapped(paths["answer-http"])
            request = json.loads(paths["request"].read_bytes())
            if (request["surface"]["surface_id"] != "plan" or request["message"] != case["question"]
                    or sha256(raw_failure).hexdigest() != wire_failure["raw_body_sha256"]):
                raise ValueError("Incomplete Plan wire capture differs from its retained request or hash")
            if (wire_failure["transport_complete"] and response["http_status"] >= 400
                    and wire_failure["status"] == response["http_status"]
                    and json.loads(raw_failure) == response["body"]):
                failure_status = response["http_status"]
        if case.get("assessment") is not None:
            raise ValueError("Reviewed capture evidence is missing")
        return {"case_id": case["id"], "question": case["question"],
        "capture_status": "incomplete" if (directory / "dispatch.json").exists() else "not_started", "missing_artifacts": missing,
            "delivery": ({"status": "fail", "http_status": failure_status} if failure_status is not None
                         else {"status": "not_requested" if context_only else "unknown"}),
            "operation": {"provider_attempts": None, "billed_cost_usd": None},
            "boundaries": {name: {"status": "unknown"} for name in (
                "ingestion_publication", "retrieval", "composition", "citations")}}
    documents = {name: json.loads(path.read_text()) for name, path in paths.items()}
    request = documents["request"]
    if request.get("message") != case["question"]:
        raise ValueError("Retained request belongs to another question")
    history = _wrapped(paths["history-after"])
    trace = _wrapped(paths["context-trace"])
    answer = _wrapped(paths["answer-http"]) if "answer-http" in paths else {"http_status": None, "body": None}
    if (history["http_status"] != 200 or trace["http_status"] != 200
        or not isinstance(history["body"], dict) or not isinstance(trace["body"], dict)):
        if case.get("assessment") is not None:
            raise ValueError("Reviewed capture observations changed")
        return {"case_id": case["id"], "question": case["question"], "capture_status": "incomplete",
            "observation_status": {"history": history["http_status"], "trace": trace["http_status"]},
            "delivery": {"status": "not_requested" if context_only else "fail" if answer["http_status"] != 200 else "unknown",
                "http_status": answer["http_status"]},
            "operation": {"provider_attempts": None, "billed_cost_usd": None},
            "boundaries": {name: {"status": "unknown"} for name in (
                "ingestion_publication", "retrieval", "composition", "citations")}}
    turns = _request_turns(history["body"], request, history["body"]["world_id"],
                           browser_plan="plan-wire-response" in paths)
    if len(turns) != 1:
        raise ValueError("Ambiguous retained question/turn correlation")
    turn = turns[0]
    world = history["body"]["world_id"]
    conversation = history["body"]["conversation_id"]
    if (request["owner_scope"] != {"kind": "world", "world_id": world}
        or trace["body"]["world_id"] != world
        or turn["provenance"]["world_id"] != world
        or turn["provenance"]["surface_instance_id"] != request["surface"]["instance_id"]):
        raise ValueError("Request/history world or surface correlation differs")
    if trace["body"]["turn_id"] != turn["turn_id"]:
        raise ValueError("Context trace belongs to another durable turn")
    attempts = trace["body"]["attempts"]
    calls, failures, prompt_count, prompt_witnesses = {}, [], 0, []
    for attempt in attempts:
        if (attempt["turn_id"] != turn["turn_id"] or attempt["world_id"] != world
            or attempt["conversation_id"] != conversation):
            raise ValueError("Trace attempt belongs to another durable turn")
        for event in attempt["observations"]:
            if event["kind"] == "provider_call":
                call = calls.setdefault(event["provider_attempt_id"], {
                    "provider": event["provider"], "model": event["model"],
                    "outcomes": [], "input_tokens": None, "output_tokens": None})
                if (call["provider"], call["model"]) != (event["provider"], event["model"]):
                    raise ValueError("Provider attempt identity changed")
                call["outcomes"].append(event["outcome"])
                for key in ("input_tokens", "output_tokens"):
                    if event.get(key) is not None:
                        if call[key] not in (None, event[key]):
                            raise ValueError("Conflicting attempt accounting")
                        call[key] = event[key]
            elif event["kind"] == "failure":
                failures.append({"phase": event["phase"], "code": event["code"]})
            elif event["kind"] == "prompt_reference":
                root = Path(case["prompt_dir"])
                root = root if root.is_absolute() else base / root
                identity = event["evidence_id"]
                # UUID validation prevents traversal through retained references.
                from uuid import UUID
                UUID(identity)
                data = (root / (identity + ".json")).read_bytes()
                if len(data) != event["payload_utf8_bytes"] or sha256(data).hexdigest() != event["payload_sha256"]:
                    raise ValueError("Prepared prompt witness mismatch")
                prompt_count += 1
                prompt_witnesses.append(event)
    context_packet = None
    if context_only:
        from .context_capture import summarize_host_trace, validate_context_packet
        context_packet = validate_context_packet(
            documents["context-ready"], documents["context-request"], documents["context-stop"],
            writer_transport=boundary == "writer_transport")
        detail = (summarize_host_trace(documents["detailed-host-trace"],
                   documents["context-ready"], documents["context-stop"]) if detailed_trace else None)
        captured = context_packet["turn"]
        authorization = context_packet["authorization"]
        if ((str(captured.turn_id), str(captured.conversation_id), captured.world_id, captured.user_text)
                != (turn["turn_id"], conversation, world, case["question"])):
            raise ValueError("Captured context belongs to another ordinary turn")
        if len([p for p in prompt_witnesses
                if p.get("provider_attempt_id") == str(authorization.provider_attempt_id)
                and p["payload_sha256"] == authorization.envelope_sha256]) != 1:
            raise ValueError("Context capture has no unique admitted prompt witness")
    wire = None
    for surface in ("build", "plan"):
        candidate = documents.get(surface + "-wire-response")
        if candidate is None:
            continue
        if request["surface"]["surface_id"] != surface:
            raise ValueError("Browser wire capture belongs to another surface")
        wire = candidate
        raw_wire = bytes.fromhex(wire["raw_body_hex"])
        if sha256(raw_wire).hexdigest() != wire["raw_body_sha256"]:
            raise ValueError("Browser wire response bytes differ from their recorded hash")
    answer_body = answer["body"] if isinstance(answer["body"], dict) else {}
    delivery_status = "unknown"
    response_completion = (answer_body.get("knowledge_context") or {}).get("completion") or {}
    durable_completion = (turn.get("knowledge_context") or {}).get("completion") or {}
    collaboration = response_completion.get("collaboration")
    structured_delivery = (isinstance(collaboration, dict) and bool(collaboration.get("kind"))
                           and collaboration == durable_completion.get("collaboration"))
    plan_proposal = answer_body.get("plan_proposal")
    if isinstance(plan_proposal, dict) and plan_proposal == turn.get("plan_proposal"):
        from application_state.agent_conversation.plan_authoring import PlanAuthoredProposalV1

        proposal = PlanAuthoredProposalV1.model_validate(plan_proposal)
        structured_delivery |= (request["surface"]["surface_id"] == "plan"
                                and str(proposal.origin.turn_id) == turn["turn_id"]
                                and str(proposal.origin.conversation_id) == conversation)
    prose_delivery = (bool(turn.get("assistant_text"))
                      and answer_body.get("answer", {}).get("text") == turn["assistant_text"])
    delivered = (answer["http_status"] == 200 and turn["lifecycle_status"] == "completed"
                 and (prose_delivery or structured_delivery))
    if "answer-http" in paths:
        delivery_status = "pass" if delivered else "fail"
    elif wire is not None and wire.get("client_disconnect_ms") is not None:
        delivery_status = "disconnected"
    if answer["http_status"] == 200 and answer_body and (answer_body["turn_id"] != request["turn_id"]
        or answer_body["client_thread_id"] != request["client_thread_id"]):
        raise ValueError("HTTP response belongs to another client request")
    # A canonical adopted review owns dispositions. A manifest cannot assign a
    # grade to an arbitrary text pointer or silently reuse another run's review.
    if "assessments" in case:
        raise ValueError("Use a capture-bound canonical assessment, not manifest grades")
    assessment = None
    if case.get("assessment") is not None:
        assessment = json.loads(read_pin(case["assessment"], base))
        expected_binding = {"world_id": world, "conversation_id": conversation,
            "turn_id": turn["turn_id"], **{name + "_sha256": sha256(path.read_bytes()).hexdigest()
                for name, path in paths.items()}}
        if (assessment.get("schema") != "dmb_ordinary_benchmark_assessment_v1"
            or not assessment.get("reviewer") or assessment.get("capture") != expected_binding):
            raise ValueError("Assessment belongs to another capture")
    boundaries = {}
    for name in ("ingestion_publication", "retrieval", "composition", "citations"):
        judgment = assessment.get("boundaries", {}).get(name) if assessment is not None else None
        boundaries[name] = {"status": "unknown"}
        if judgment is not None:
            if judgment["status"] not in {"pass", "partial", "fail", "not_reached", "unknown"}:
                raise ValueError("Unknown semantic disposition")
            if not judgment.get("evidence"):
                raise ValueError("Semantic disposition requires review evidence")
            for evidence in judgment["evidence"]:
                doc = json.loads(read_pin(evidence["artifact"], base))
                if _pointer(doc, evidence["pointer"]) != evidence["expected"]:
                    raise ValueError("Assessment evidence binding differs")
            boundaries[name] = {**judgment, "basis": "capture-bound adopted review, not an automatic grade",
                "assessment": case["assessment"]}
    if context_only:
        if assessment is not None and "composition" in assessment.get("boundaries", {}):
            raise ValueError("Context-only capture cannot use response composition grades")
        boundaries["composition"] = {"status": "not_reached", "reason": "No response requested"}
        writer_attempt = str(context_packet["authorization"].provider_attempt_id)
        controller_calls = {identity: call for identity, call in calls.items() if identity != writer_attempt}
        def controller_total(key):
            return sum(c[key] for c in controller_calls.values()) if controller_calls and all(
                c[key] is not None for c in controller_calls.values()) else None
        return {"case_id": case["id"], "question": case["question"], "capture_status": "complete",
            "capture_boundary": boundary, "durable_turn_id": turn["turn_id"], "boundaries": boundaries,
            "context": {"status": "captured", "accepted_to_ready_ms": context_packet["elapsed_ms"],
                "request_to_ready_ms": context_packet["request_to_ready_ms"],
                "request_to_transport_ms": context_packet["request_to_transport_ms"],
                "detailed_host_trace": detail,
                "request_timing_basis": ("Same-process monotonic clock from ordinary request dispatch to post-authorization context-ready; includes bootstrap, excludes capture installation, artifact IO and cleanup"
                    if context_packet["request_to_ready_ms"] is not None else "Unknown: historical request-start tick was not retained"),
                "prepared_request_bytes": context_packet["prepared_bytes"],
                "host_spans": documents["context-ready"].get("host_spans"),
                "host_span_limits": "Existing pre-stop spans; cumulative/nested durations overlap and are not additive. Open phases are unfinished, not zero-cost.",
                "timing_basis": "APP accepted_at to UTC observed immediately after real input authorization; same-host wallclock correlation, not nanosecond accuracy; excludes artifact IO and cleanup",
                "input_accounting": {"kind": authorization.input_accounting_kind,
                    "amount": authorization.input_tokens, "estimator": authorization.input_estimator}},
            "delivery": {"status": "not_requested", "http_status": answer["http_status"],
                "lifecycle_status": turn["lifecycle_status"]},
            "operation": {"elapsed_ms": context_packet["elapsed_ms"], "provider_attempts": len(controller_calls),
                "writer_requests_sent": 0, "writer_output": "not_requested", "input_tokens": controller_total("input_tokens"),
                "output_tokens": controller_total("output_tokens"), "billed_cost_usd": None,
                "cost_status": "unknown", "attempts": controller_calls},
            "failures": failures, "verified_prompt_witnesses": prompt_count,
            "artifacts": {name: {"path": str(path), "sha256": sha256(path.read_bytes()).hexdigest()}
                for name, path in paths.items()}}
    owner_observation = None
    for name in ("lore-confirmation-result", "terminal-build-failure"):
        owner_path = directory / (name + ".json")
        if owner_path.is_file():
            paths[name] = owner_path
            owner_observation = json.loads(owner_path.read_bytes())
    elapsed = answer.get("elapsed_ms")
    if elapsed is None and (directory / "terminal.json").exists():
        elapsed = json.loads((directory / "terminal.json").read_text())["elapsed_seconds"] * 1000
    def total(key):
        return sum(c[key] for c in calls.values()) if calls and all(c[key] is not None for c in calls.values()) else None
    return {"case_id": case["id"], "question": case["question"], "capture_status": "complete",
        "durable_turn_id": turn["turn_id"], "boundaries": boundaries,
        **({"owner_observation": owner_observation} if owner_observation is not None else {}),
        "delivery": {"status": delivery_status, "http_status": answer["http_status"],
            "lifecycle_status": turn["lifecycle_status"]},
        "operation": {"elapsed_ms": elapsed, "provider_attempts": len(calls),
            "input_tokens": total("input_tokens"), "output_tokens": total("output_tokens"),
            "billed_cost_usd": None, "cost_status": "unknown", "attempts": calls},
        "failures": failures, "verified_prompt_witnesses": prompt_count,
        "artifacts": {name: {"path": str(path), "sha256": sha256(path.read_bytes()).hexdigest()}
            for name, path in paths.items()}}


def report(manifest_path, *, oracle=None, citation_readback=None):
    manifest, base = load_manifest(manifest_path)
    rows = [report_case(case, base) for case in manifest["cases"]]
    if (oracle is None) != (citation_readback is None):
        raise ValueError("Oracle scoring requires both Gold and citation readback")
    analytics = {}
    if oracle is not None:
        from .retrieval_oracle import score
        analytics["retrieval_analytics"] = score(oracle, citation_readback, manifest, base)
    return {**analytics, "schema": "dmb_ordinary_benchmark_report_v1", "cases": rows,
        "limits": ["Semantic dispositions are pinned reviewer judgments, not inferred from HTTP success.",
            "No new calls or database access. Historical failures remain failures.",
            "Billing and missing measurements remain unknown; no estimated price is billed cost."]}


def reopen_saved_citations(client, turn_route, completion):
    """Reopen delivered saved sections through their ordinary turn owner."""
    from httpx import RequestError

    results = []
    for citation in completion.get("saved_source_citations") or []:
        index = citation["segment_index"]
        if type(index) is not int or not 0 <= index < len(completion["answer_segments"]):
            raise ValueError("Saved citation has no corresponding answer segment")
        claim = completion["answer_segments"][index].get("text", "").strip().strip('“”"')
        for value in citation["section_event_ids"]:
            event_id = str(UUID(value))
            try:
                response = client.get(f"{turn_route}/saved-sections/{index}/{event_id}")
            except RequestError as error:
                results.append({"segment_index": index, "section_event_id": event_id,
                                "http_status": None, "transport_error": type(error).__name__,
                                "claim_exact_substring_of_reopened_text": None})
                continue
            evidence = response_envelope(response)
            body = evidence["body"]
            results.append({
                "segment_index": index,
                "section_event_id": event_id,
                **evidence,
                "claim_exact_substring_of_reopened_text": (
                    bool(claim) and claim in body.get("content", "")
                    if response.status_code == 200 and isinstance(body, dict) else None
                ),
            })
    return {"scope": "saved_authored_sections", "citations": results}


def retain_citation_readbacks(client, directory, route, world, turn_id, answer):
    """Retain owner readbacks for source citations delivered on an ordinary turn."""
    turn_route = f"{route}/turns/{turn_id}"
    completions = [(answer.get(key) or {}).get("completion") or {}
                   for key in ("knowledge_context", "plan_context")]
    saved = next((c for c in completions if c.get("saved_source_citations")), None)
    if saved is not None:
        immutable_save(directory, "saved-citation-reopen",
                       reopen_saved_citations(client, turn_route, saved))
    native = next((c for c in completions if c.get("native_body_citations")), None)
    if native is not None:
        immutable_save(directory, "native-citation-reopen",
                       reopen_native_body_citations(client, turn_route, world, turn_id, native))


def reopen_native_body_citations(client, turn_route, world, turn_id, completion):
    """Verify exact native excerpt bytes and the original delivered citation."""
    from httpx import RequestError

    results = []
    for index, citation in enumerate(completion["native_body_citations"]):
        observed_digest = None
        binding_matches = None
        expected_digest = citation["excerpt_sha256"]
        try:
            response = client.get(f"{turn_route}/native-body-excerpts/{index}")
        except RequestError as error:
            evidence = {"http_status": None, "transport_error": type(error).__name__}
        else:
            evidence = response_envelope(response)
            body = evidence["body"]
            if response.status_code == 200 and isinstance(body, dict):
                content = body.get("content")
                if isinstance(content, str):
                    observed_digest = sha256(content.encode()).hexdigest()
                binding_matches = (
                    set(body) == {"schema", "world_id", "turn_id", "citation_index", "citation", "content", "display_label"}
                    and body["schema"] == "dmb_agent_native_body_excerpt_read_v2"
                    and isinstance(content, str) and bool(content)
                    and (body["display_label"] is None or
                         isinstance(body["display_label"], str) and bool(body["display_label"].strip()))
                    and body.get("world_id") == world
                    and body.get("turn_id") == turn_id
                    and type(body.get("citation_index")) is int
                    and body["citation_index"] == index
                    and body.get("citation") == citation
                )
        results.append({
            "citation_index": index,
            **evidence,
            "expected_excerpt_sha256": expected_digest,
            "observed_excerpt_sha256": observed_digest,
            "binding_matches": binding_matches,
            "exact_reopen": binding_matches is True and observed_digest == expected_digest,
        })
    return {"scope": "native_body_excerpts", "citations": results}


def require_pinned_history(history, expected, *, allow_interrupted=False):
    """Reject nonterminal, stale, or extra turns in a restored conversation."""
    observed = []
    for turn in history["turns"]:
        status = turn["lifecycle_status"]
        if status != "completed" and not (allow_interrupted and status == "interrupted"):
            raise ValueError("Active conversation differs from the pinned conversation history")
        answer = turn["assistant_text"]
        if status == "completed" and not isinstance(answer, str):
            raise ValueError("Active conversation differs from the pinned conversation history")
        row = {
            "turn_id": turn["turn_id"], "sequence": turn["sequence"],
            "user_text_sha256": sha256(turn["user_text"].encode("utf-8")).hexdigest(),
            "assistant_text_sha256": sha256(answer.encode("utf-8")).hexdigest() if answer is not None else None,
        }
        if status != "completed":
            row["lifecycle_status"] = status
        observed.append(row)
    observed.sort(key=lambda turn: turn["sequence"])
    if (history["active_conversation_id"] != expected["conversation_id"]
            or history.get("next_before_sequence") is not None
            or not observed or observed != expected["prior_turns"]):
        raise ValueError("Active conversation differs from the pinned conversation history")


def capture_lore_confirmation(client, directory, route, world, conversation, turn, completion, foreign):
    """Exercise revision-bound review, confirmation and exact receipt recovery."""
    from application_state.agent_conversation import AgentConversationService
    from application_state.agent_conversation.rules_authority_types import canonical_sha256
    from application_state.content.pages import committed_page

    def snapshot(label):
        response = client.get("/api/live/workspace-documents",
                              params={"world_id": world, "kind": "worldbuilding_source"})
        evidence = response_envelope(response)
        immutable_save(directory, label, evidence)
        response.raise_for_status()
        return {row["document_id"]: row for row in evidence["body"]["records"]}

    def post(label, action, command):
        response = client.post(f"{route}/lore-pages/{action}", json=command)
        evidence = response_envelope(response)
        immutable_save(directory, label, evidence)
        return evidence

    if foreign == conversation:
        raise ValueError("Foreign lore confirmation requires a different conversation")
    if (completion.get("collaboration") or {}).get("kind") != "lore_page":
        immutable_save(directory, "lore-confirmation-result", {"status": "unavailable", "reason": "no_lore_review"})
        return
    other = AgentConversationService().get_conversation(world, UUID(foreign))
    if other.status != "archived":
        raise ValueError("Foreign lore confirmation requires a retained archived conversation")
    immutable_save(directory, "lore-foreign-binding", {"conversation_id": foreign, "status": other.status})
    command = {"conversation_id": conversation, "turn_id": turn, "review_sha256": canonical_sha256(completion)}
    immutable_save(directory, "lore-confirmation-request", command)
    before = snapshot("lore-pages-before")
    wrong_digest = "0" * 64 if command["review_sha256"] != "0" * 64 else "1" * 64
    rejected = []
    for label, override, expected in (
        ("lore-wrong-digest", {"review_sha256": wrong_digest}, 409),
        ("lore-foreign-conversation", {"conversation_id": foreign}, 404),
        ("lore-before-review", {}, 409),
    ):
        response = post(label, "confirm", {**command, **override})
        unchanged = snapshot(label + "-pages") == before
        rejected.append(response["http_status"] == expected and unchanged)
        if not rejected[-1]:
            immutable_save(directory, "lore-confirmation-result", {
                "status": "incomplete", "reason": label, "protected_pages_unchanged": unchanged,
            })
            return
    review = post("lore-present-review", "review", command)
    if (review["http_status"] != 200 or review["body"].get("review_sha256") != command["review_sha256"]
            or snapshot("lore-after-review-pages") != before):
        immutable_save(directory, "lore-confirmation-result", {"status": "incomplete", "reason": "review_not_bound"})
        return
    confirmation = post("lore-confirm", "confirm", command)
    if confirmation["http_status"] != 200:
        immutable_save(directory, "lore-confirmation-result", {"status": "incomplete", "reason": "confirmation_failed"})
        return
    receipt = confirmation["body"]
    document = str(UUID(receipt["document_id"]))
    after = snapshot("lore-after-confirm-pages")
    if (set(after) != set(before) | {document} or document in before
            or any(after[item] != row for item, row in before.items())):
        immutable_save(directory, "lore-confirmation-result", {"status": "incomplete", "reason": "unexpected_page_effect"})
        return
    reopened = response_envelope(client.get(f"/api/live/workspace-documents/{document}/snapshot",
                                            params={"view": "committed"}))
    immutable_save(directory, "lore-committed-reopen", reopened)
    body = reopened["body"] if isinstance(reopened["body"], dict) else {}
    owned_page = committed_page(document, world_id=world)
    revision = owned_page.revision
    if revision is not None:
        immutable_save(directory, "lore-owner-revision", revision.model_dump(mode="json"))
    expected_links = [f"{route}/turns/{turn}/native-body-excerpts/{index}"
                      for index in range(len(completion.get("native_body_citations") or []))]
    citations = json.loads((directory / "native-citation-reopen.json").read_bytes()) if expected_links else {}
    replay = post("lore-confirm-retry", "confirm", command)
    after_retry = snapshot("lore-after-retry-pages")
    checks = {
        "invalid_confirmations_no_effect": all(rejected),
        "one_new_page": True,
        "receipt_bound_to_review": receipt.get("review_sha256") == command["review_sha256"],
        "reopened_exact_revision": (revision is not None and str(revision.work_revision_id) == receipt.get("revision_id")
            and body.get("content_sha256") == revision.content_sha256 and body.get("markdown") == revision.markdown
            and owned_page.page.title == completion["collaboration"]["destination"]["title"]),
        "reopened_committed_page": (reopened["http_status"] == 200 and body.get("record") == after[document]
            and body["record"].get("world_id") == world and body["record"].get("content_status") == "committed"
            and isinstance(body.get("markdown"), str) and body["markdown"] == body.get("committed_markdown")),
        "reopened_own_turn_links": bool(expected_links) and all(
            link in body.get("markdown", "") for link in expected_links),
        "exact_citations_reopened": bool(expected_links) and len(citations.get("citations", [])) == len(expected_links)
            and all(item["exact_reopen"] for item in citations["citations"]),
        "same_receipt_no_second_page": (replay["http_status"] == 200 and replay["body"] == receipt
            and after_retry == after),
    }
    immutable_save(directory, "lore-confirmation-result", {
        "status": "observed" if all(checks.values()) else "incomplete", "checks": checks,
    })


def capture_case(client, world, template, case, directory, *, context_only=False, writer_transport=False, detailed_trace=False,
                 build_thread_id=None, expected_conversation_id=None, build_editor_snapshot=None, pinned_history=None):
    """The single ordinary route sequence, shared by all question fixtures."""
    build_sequence = build_thread_id is not None
    validate_template(template, world, context_only=context_only, build_sequence=build_sequence)
    if build_editor_snapshot is not None:
        from application_state.agent_conversation.build_draft_context import (
            BuildDraftContextRequestV1, BuildDraftSnapshotV1,
        )
        snapshot = BuildDraftSnapshotV1.model_validate(build_editor_snapshot)
        work = template["primary_work"]
        if (not build_sequence or snapshot.world_id != world
                or str(snapshot.document_id) != work["object_id"]
                or snapshot.registry_revision != work["expected_revision"]
                or snapshot.content_sha256 != work["expected_content_sha256"]
                or snapshot.draft_sha256 != snapshot.content_sha256
                or sha256(snapshot.draft_markdown.encode()).hexdigest() != snapshot.content_sha256):
            raise ValueError("Build benchmark editor snapshot must match the exact saved page")
    if directory.exists() and any(directory.iterdir()):
        raise ValueError("Case output already exists; do not redispatch")
    route = "/api/live/agent/worlds/" + world + "/conversation"
    def save(name, response):
        envelope = response_envelope(response)
        immutable_save(directory, name, envelope)
        body = envelope["body"]
        return body
    before = save("history-before", client.get(route))
    if pinned_history is not None:
        if not build_sequence or expected_conversation_id is not None:
            raise ValueError("Pinned Build history must start the ordinary sequence")
        require_pinned_history(before, pinned_history, allow_interrupted=True)
        expected_conversation_id = before["active_conversation_id"]
    if expected_conversation_id is None:
        command = {"schema": "dmb_agent_new_conversation_v1", "command_id": str(uuid4()),
            "expected_pointer_revision": before["pointer_revision"],
            "expected_active_conversation_id": before["active_conversation_id"]}
        immutable_save(directory, "new-conversation-request", command)
        response = client.post(route + "/new", json=command)
        created = save("new-conversation-response", response)
        if response.status_code != 200:
            raise ValueError("New conversation CAS failed; no question dispatched")
        fresh = save("fresh-history", client.get(route))
        if fresh["turns"]:
            raise ValueError("Ordinary benchmark requires a fresh conversation")
        if build_sequence and (
            not created.get("active_conversation_id")
            or fresh["active_conversation_id"] != created["active_conversation_id"]
        ):
            raise ValueError("Build conversation changed after creation; no turn dispatched")
    else:
        fresh = before
        if fresh["active_conversation_id"] != expected_conversation_id:
            raise ValueError("Build conversation changed; no turn dispatched")
    request = json.loads(json.dumps(template))
    request.update(client_thread_id=build_thread_id or str(uuid4()), turn_id=str(uuid4()), message=case["question"])
    if build_sequence and expected_conversation_id is not None and pinned_history is None:
        request.pop("build_authored_references", None)
    if not build_sequence:
        request["surface"]["instance_id"] = request["client_thread_id"]
    if build_editor_snapshot is not None:
        request["build_draft_context"] = BuildDraftContextRequestV1(
            snapshot=snapshot, conversation_id=fresh["active_conversation_id"],
            expected_pointer_revision=fresh["pointer_revision"],
        ).model_dump(mode="json", by_alias=True)
    immutable_save(directory, "request", request)
    immutable_save(directory, "dispatch", {"state": "dispatching", "automatic_restart": False})
    started = time.monotonic()
    error, known_response = None, False
    from contextlib import nullcontext
    from .context_capture import ContextCapture
    context_stop = ContextCapture(directory, writer_transport=writer_transport, detailed_trace=detailed_trace) if context_only else None
    try:
        with context_stop.install() if context_stop is not None else nullcontext():
            if context_stop is not None:
                context_stop.request_started_monotonic_ns = time.monotonic_ns()
            response = client.post("/api/live/agent/turn", json=request)
        immutable_save(directory, "answer-http", {**response_envelope(response),
            "elapsed_ms": (time.monotonic() - started) * 1000})
        known_response = True
    except Exception as exc:
        error = exc
    finally:
        try:
            history = save("history-after", client.get(route, params={"include_turn_correlation": "true"}))
            if build_sequence and history["active_conversation_id"] != fresh["active_conversation_id"]:
                raise ValueError("Build conversation changed after dispatch")
            prior_ids = {turn["turn_id"] for turn in fresh["turns"]}
            turns = [t for t in _request_turns(history, request, world) if t["turn_id"] not in prior_ids]
            if len(turns) != 1:
                raise ValueError("Question has no unique durable turn; do not redispatch")
            durable = turns[0]
            trace_response = client.get(route + "/turns/" + durable["turn_id"] + "/context-trace")
            trace = save("context-trace", trace_response)
            if build_sequence and known_response and response.status_code == 200:
                delivered = response.json()
                if (durable.get("lifecycle_status") != "completed"
                        or delivered.get("turn_id") != request["turn_id"]
                        or delivered.get("client_thread_id") != request["client_thread_id"]
                        or delivered.get("answer", {}).get("text") != durable.get("assistant_text")
                        or trace_response.status_code != 200 or not isinstance(trace, dict)
                        or trace.get("world_id") != world or trace.get("turn_id") != durable["turn_id"]):
                    raise ValueError("Build turn delivery or trace could not be verified")
            if not context_only and known_response and response.status_code == 200:
                retain_citation_readbacks(client, directory, route, world, durable["turn_id"], response.json())
                if case.get("lore_confirmation") is not None:
                    completion = response.json()["knowledge_context"]["completion"]
                    capture_lore_confirmation(client, directory, route, world, fresh["active_conversation_id"],
                                              durable["turn_id"], completion, case["lore_confirmation"]["foreign_conversation_id"])

            if context_stop is not None:
                from application_state.agent_conversation import AgentConversationService
                observed = AgentConversationService().inspect_turn(world_id=world, turn_id=UUID(turns[0]["turn_id"]))
                context_stop.finalize(observed)
        except Exception as exc:
            error = error or exc
        immutable_save(directory, "terminal", {"status": "observed" if known_response else "outcome_unknown",
            "error_type": type(error).__name__ if error else None,
            "elapsed_seconds": time.monotonic() - started, "automatic_restart": False})
    if error:
        raise error
    return response


def response_envelope(response):
    """Retain exact HTTP bytes even when the response is not JSON."""
    raw = response.content
    try:
        body = response.json()
    except ValueError:
        body = None
    return {"http_status": response.status_code, "body": body,
        "raw_body_hex": raw.hex(), "raw_body_sha256": sha256(raw).hexdigest()}


def verify_runtime(spec, base):
    """Pin the executing checkout and dependency files, not a decorative label."""
    import subprocess
    from importlib import import_module
    root = Path(__file__).resolve().parents[2]
    files = subprocess.check_output(["git", "ls-files", "-z"], cwd=root).decode().split("\0")
    actual = {name: sha256((root / name).read_bytes()).hexdigest() for name in files if name}
    if "evals/buddy_benchmark/workflow.py" not in actual or actual != json.loads(read_pin(spec["source_tree"], base)):
        raise ValueError("Executing runtime source differs from pinned tree")
    if not {"generationengine", "openai", "dungeonmind", "worldkeeper"} <= set(spec["dependencies"]):
        raise ValueError("Runtime requires engine, writer and authority dependency pins")
    for name, pin in spec["dependencies"].items():
        module = import_module(name)
        directory = Path(module.__file__).resolve().parent
        inventory = {str(f.relative_to(directory)): sha256(f.read_bytes()).hexdigest()
            for f in directory.rglob("*") if f.is_file() and "__pycache__" not in f.parts and f.suffix != ".pyc"}
        if inventory != json.loads(read_pin(pin, base)):
            raise ValueError("Executing dependency differs: " + name)


def verify_capture_environment(expected):
    if os.environ.get("DMB_AGENT_GRAPH_LOCAL_PROFILE") or any(os.environ.get(k) != v for k,v in expected.items()):
        raise ValueError("Runtime qualification changed; no question dispatched")


class BuildSequenceStopped(ValueError):
    """An observed failed turn prevented dependent turns from dispatching."""


def capture(manifest_path, output, *, context_only=False, writer_transport=False, detailed_trace=False,
            browser_case=None, cohort_manifest_sha256=None, clone_app=False, cohort_app=None, build_fixture=False, live_build=False, live_plan=False):
    """Explicit live entry point; never invoked by offline reporting."""
    if live_plan and (not clone_app or browser_case is None or build_fixture or live_build
                      or context_only or writer_transport or detailed_trace):
        raise ValueError("Live Plan browser capture requires its own App clone and selected case in response mode")
    manifest, base = load_manifest(manifest_path, expected_sha256=cohort_manifest_sha256)
    if any("lore_confirmation" in case for case in manifest["cases"]) and (
            manifest.get("conversation_mode") != "build_sequence" or browser_case is not None
            or context_only or writer_transport or detailed_trace or (not clone_app and cohort_app is None)):
        raise ValueError("Lore confirmation requires ordinary Build capture on an owned App clone")
    if "build_history" in manifest and (
            manifest.get("conversation_mode") != "build_sequence"
            or browser_case is not None or context_only or writer_transport or detailed_trace
            or (not clone_app and cohort_app is None)):
        raise ValueError("Pinned Build history requires ordinary response capture on an owned App clone")
    if manifest.get("browser_capture", {}).get("image_preview") is True and (
            not live_build or browser_case is None or (not clone_app and cohort_app is None)):
        raise ValueError("Image preview requires a selected live Build case and an owned App clone")
    if "play_choice" in manifest.get("browser_capture", {}) and (
            browser_case is None or (not clone_app and cohort_app is None)):
        raise ValueError("Play Choice requires a selected browser case and an owned App clone")
    options = dict(context_only=context_only, writer_transport=writer_transport,
                   detailed_trace=detailed_trace, browser_case=browser_case,
                   cohort_member=cohort_manifest_sha256 is not None, build_fixture=build_fixture, live_build=live_build, live_plan=live_plan)
    if cohort_app is not None:
        if cohort_manifest_sha256 is None or clone_app:
            raise ValueError("Shared App override requires a pinned cohort member")
        manifest["isolation"]["app"] = cohort_app
    if not clone_app:
        return _capture(manifest, base, output, **options)

    from urllib.parse import urlsplit
    from unittest.mock import patch
    from .disposable_database import disposable_benchmark_database

    env = "DUNGEONBUDDY_APPLICATION_STATE_DATABASE_URL"
    url = urlsplit(os.environ[env])
    app = manifest["isolation"]["app"]
    native = manifest["isolation"]["native"]
    if (url.hostname, url.port, url.path[1:]) != (app["host"], app["port"], app["database"]):
        raise ValueError("App source differs from the pinned benchmark fixture")
    if (app["system_identifier"], app["oid"]) == (native["system_identifier"], native["oid"]):
        raise ValueError("App source must be distinct from the read-only Core database")
    with disposable_benchmark_database(url._replace(path="/postgres").geturl(), app) as clone:
        manifest["isolation"]["app"] = clone
        with patch.dict(os.environ, {env: url._replace(path="/" + clone["database"]).geturl()}):
            from application_state.cli import upgrade_to_head

            upgrade_to_head()
            return _capture(manifest, base, output, **options)


def _capture(manifest, base, output, *, context_only, writer_transport, detailed_trace,
             browser_case, cohort_member, build_fixture, live_build, live_plan=False):
    if os.environ.get("DMB_AGENT_GRAPH_LOCAL_PROFILE"):
        raise ValueError("Capture cannot use a hidden local profile")
    if not manifest.get("pins"):
        raise ValueError("Capture requires pinned runtime/source evidence")
    verify_runtime(manifest["runtime"], base)
    template = manifest["request_template"]
    mode = manifest.get("conversation_mode", "fresh_per_case")
    if mode not in {"fresh_per_case", "build_sequence"}:
        raise ValueError("Unknown benchmark conversation mode")
    build_sequence = mode == "build_sequence"
    for case in manifest["cases"]:
        if "lore_confirmation" not in case:
            continue
        confirmation = case["lore_confirmation"]
        if (not build_sequence or browser_case is not None or context_only or writer_transport or detailed_trace
                or not isinstance(confirmation, dict) or set(confirmation) != {"foreign_conversation_id"}
                or str(UUID(confirmation["foreign_conversation_id"])) != confirmation["foreign_conversation_id"]):
            raise ValueError("Lore confirmation requires a pinned foreign conversation and ordinary Build response")
    build_history = None
    if "build_history" in manifest:
        if not build_sequence or browser_case is not None or context_only or writer_transport or detailed_trace:
            raise ValueError("Pinned Build history requires an ordinary Build response sequence")
        build_history = json.loads(read_pin(manifest["build_history"], base))
    validate_template(template, manifest["world"], context_only=context_only, build_sequence=build_sequence)
    browser = None
    if browser_case is not None:
        plan_replay = (context_only and writer_transport and not build_sequence
                       and template["surface"]["surface_id"] == "plan" and not build_fixture and not live_plan)
        build_preflight = (build_fixture and not context_only and not writer_transport and build_sequence
                           and template["surface"]["surface_id"] == "build")
        plan_placement = (live_plan and not context_only and not writer_transport and not build_sequence
                          and template["surface"]["surface_id"] == "plan")
        play_choice = ("play_choice" in manifest.get("browser_capture", {}) and not any(
            (build_fixture, live_build, live_plan, context_only, writer_transport, detailed_trace, build_sequence)))
        if not (plan_replay or build_preflight or plan_placement or play_choice):
            raise ValueError("Browser capture requires Plan replay or Build selection preflight")
        selected = next((case for case in manifest["cases"] if case["id"] == browser_case), None)
        if selected is None:
            raise ValueError("Browser case is absent from the manifest")
        manifest["cases"] = [selected]
        from . import browser_capture as browser
        browser_inputs = browser.browser_inputs(manifest, base, build_fixture=build_fixture, live_plan=live_plan)
    editor_snapshot = None
    if "build_editor_snapshot" in manifest:
        if not build_sequence:
            raise ValueError("Editor snapshots require a Build sequence")
        editor_snapshot = json.loads(read_pin(manifest["build_editor_snapshot"], base))
        if not isinstance(editor_snapshot, dict):
            raise ValueError("Build editor snapshot pin must contain a snapshot object")
    output = Path(output).resolve()
    output.mkdir(mode=0o700, parents=True, exist_ok=False)
    # The application must be configured against explicitly qualified test state.
    from urllib.parse import urlparse
    dsns = {}
    for role, env in (("app", "DUNGEONBUDDY_APPLICATION_STATE_DATABASE_URL"),
                      ("native", "DUNGEONMIND_WORLD_GRAPH_AUTHORITY_DATABASE_URL")):
        dsn = os.environ[env]
        expected = manifest["isolation"][role]
        parsed = urlparse(dsn)
        if (parsed.hostname, parsed.port, parsed.path[1:]) != (
            expected["host"], expected["port"], expected["database"]):
            raise ValueError("Isolated database configuration differs")
        if parsed.hostname not in {"127.0.0.1", "localhost", "::1"}:
            raise ValueError("Ordinary benchmark requires isolated local state")
        dsns[env] = dsn
        import psycopg
        with psycopg.connect(dsn, options="-c default_transaction_read_only=on") as conn:
            actual = conn.execute("SELECT current_database(), (SELECT oid::text FROM pg_database WHERE datname=current_database()), system_identifier::text FROM pg_control_system()").fetchone()
            if actual != (expected["database"], expected["oid"], expected["system_identifier"]):
                raise ValueError("Isolated database identity differs")
    from contextlib import contextmanager
    from psycopg.rows import dict_row
    from .artifacts import row_inventory
    @contextmanager
    def readonly(dsn):
        with psycopg.connect(dsn, options="-c default_transaction_read_only=on", row_factory=dict_row) as conn:
            yield conn
    native_dsn = dsns["DUNGEONMIND_WORLD_GRAPH_AUTHORITY_DATABASE_URL"]
    from .cohort_capture import require_read_only_core
    require_read_only_core(native_dsn)
    if not cohort_member:
        native_before = row_inventory(native_dsn, readonly=readonly)
        expected_native = json.loads(read_pin(manifest["isolation"]["native"]["inventory"], base))
        if native_before != expected_native:
            raise ValueError("Native corpus differs from pinned inventory")
        immutable_save(output, "native-before", native_before)
    token = secrets.token_urlsafe(32)
    owned_env = dict(dsns, DMB_AGENT_GRAPH_LOCAL_OPERATOR_TOKEN=token,
        DMB_AGENT_GRAPH_SESSION_STORE=str(output / "isolated-session.json"),
        DMB_ARTIFACT_DATA_ROOT=str(output / "runtime-artifacts"))
    os.environ.update(owned_env)
    (output / "runtime-artifacts").mkdir(mode=0o700)
    from fastapi.testclient import TestClient
    retained = dict(manifest)
    if editor_snapshot is not None:
        pin = manifest["build_editor_snapshot"]
        retained["build_editor_snapshot"] = dict(pin, path=str((base / pin["path"]).resolve()))
    retained["cases"] = []
    for case in manifest["cases"]:
        # A new capture never inherits an old semantic assessment.
        current = {key: value for key, value in case.items() if key not in {"assessment", "assessments", "detailed_trace"}}
        if "play_choice" in manifest.get("browser_capture", {}):
            current["capture_boundary"] = "play_choice"
        elif manifest.get("browser_capture", {}).get("image_preview") is True:
            current["capture_boundary"] = "image_preview"
        elif context_only:
            current["capture_boundary"] = "writer_transport" if writer_transport else "context_ready"
            current["detailed_trace"] = detailed_trace
        elif current.get("capture_boundary", "response") != "response":
            raise ValueError("Context capture requires the explicit capture-context mode")
        retained["cases"].append(dict(current, capture_dir=str((output / case["id"]).resolve()),
            prompt_dir=str((output / "runtime-artifacts/out/agent_request_evidence").resolve())))
    # Preserve relative input pins/review bindings by resolving them before moving
    # the manifest. Requests were constructed exclusively from template/question.
    def absolute_pins(value):
        if isinstance(value, dict):
            if "path" in value and "sha256" in value:
                path = Path(value["path"])
                value["path"] = str(path if path.is_absolute() else (base / path).resolve())
            for child in value.values():
                absolute_pins(child)
        elif isinstance(value, list):
            for child in value:
                absolute_pins(child)
    absolute_pins(retained)
    immutable_save(output, "capture-manifest", retained)
    from apps.live_control_server import main as application
    if Path(application.__file__).resolve() != Path(__file__).resolve().parents[2] / "apps/live_control_server/main.py":
        raise ValueError("Application import differs from qualified source")
    try:
        if browser is not None:
            browser.browser_capture(application.create_app(), manifest, selected, output, token,
                                    browser_inputs, owned_env, detail=detailed_trace, build_fixture=build_fixture, live_build=live_build, live_plan=live_plan)
            return
        with TestClient(application.create_app(), client=("127.0.0.1", 43021),
            headers={"Authorization": "Bearer " + token}, raise_server_exceptions=False) as client:
            if client.get("/health/ready").status_code != 200:
                raise ValueError("Runtime qualification changed; no question dispatched")
            verify_capture_environment(owned_env)
            from apps.live_control_server.services.plan_jev_dispatch import request_budget
            if request_budget() != manifest["provider_policy"]:
                raise ValueError("Effective ordinary provider policy differs")
            conversation_id = None
            build_thread_id = str(uuid4()) if build_sequence else None
            for index, case in enumerate(manifest["cases"]):
                verify_capture_environment(owned_env)
                directory = output / case["id"]
                response = capture_case(client, manifest["world"], template, case, directory,
                    context_only=context_only, writer_transport=writer_transport, detailed_trace=detailed_trace, build_thread_id=build_thread_id,
                    expected_conversation_id=conversation_id, build_editor_snapshot=editor_snapshot,
                    pinned_history=build_history if index == 0 else None)
                if build_sequence:
                    if response.status_code != 200:
                        raise BuildSequenceStopped("Build turn failed; later turns not dispatched")
                    conversation_id = _wrapped(directory / "history-after.json")["body"]["active_conversation_id"]
    finally:
        if not cohort_member:
            native_after = row_inventory(native_dsn, readonly=readonly)
            immutable_save(output, "native-after", native_after)
        if not build_fixture or live_build:
            immutable_save(output, "report", report(output / "capture-manifest.json"))
        if not cohort_member and native_before != native_after:
            raise ValueError("Native authority changed during ordinary capture")


def _writer_replay_request(case, source, source_base, summary, *, case_base):
    """Join retained witnesses, never manufacture an APP writer authorization."""
    from application_state.agent_conversation.source_writer_output import strict_json
    from application_state.agent_conversation.native_evidence_view import semantic_frame_in_request
    from application_state.agent_conversation.types import canonical_sha256
    import jsonschema

    if set(case) != {"id", "question", "writer_attempt_id", "ledger"}:
        raise ValueError("Replay case requires its exact retained writer and ledger")
    identity = str(UUID(case["writer_attempt_id"]))
    if case["question"] != source["question"] or summary["delivery"]["status"] != "pass":
        raise ValueError("Replay requires the same completed ordinary question")
    directory = Path(source["capture_dir"])
    directory = directory if directory.is_absolute() else source_base / directory
    surface = json.loads((directory / "request.json").read_text())["surface"].get("surface_id")
    replay_contracts = {
        "plan": ("plan_context", "native_writer_authorized_v1"),
        "build": ("knowledge_context", "native_build_writer_authorized_v2"),
    }
    if surface not in replay_contracts:
        raise ValueError("Replay requires a supported retained ordinary writer")
    context_key, writer_kind = replay_contracts[surface]
    trace = _wrapped(directory / "context-trace.json")["body"]
    history = _wrapped(directory / "history-after.json")["body"]
    witnesses = [(attempt, event) for attempt in trace["attempts"] for event in attempt["observations"]
        if event["kind"] == "prompt_reference" and event.get("provider_attempt_id") == identity]
    if len(witnesses) != 1:
        raise ValueError("Replay needs one exact writer prompt witness")
    trace_attempt, witness = witnesses[0]
    if (witness.get("provider"), witness.get("api_mode"), witness.get("serializer_version")) != (
            "openai", "responses", "openai-sdk-json-v1"):
        raise ValueError("Replay witness is not a native answer writer")
    evidence = str(UUID(witness["evidence_id"]))
    root = Path(source["prompt_dir"])
    path = (root if root.is_absolute() else source_base / root) / (evidence + ".json")
    pin = {"path": str(path.resolve()), "sha256": witness["payload_sha256"]}
    raw = read_pin(pin, source_base)
    if len(raw) != witness["payload_utf8_bytes"]:
        raise ValueError("Replay witness size differs")
    body = strict_json(raw.decode())
    ledger = strict_json(read_pin(case["ledger"], case_base).decode())
    events = ledger["graph_context_execution"]["events"]
    writers = [e for e in events if e["kind"] in {"native_writer_authorized_v1", "native_build_writer_authorized_v2"}]
    completions = [e for e in events if e["kind"] == "completion_binding"]
    frame = semantic_frame_in_request(body, legacy_schemas=())
    if (ledger["turn_id"] != summary["durable_turn_id"] or ledger["status"] != "completed"
            or ledger["conversation_id"] != history["conversation_id"]
            or len(writers) != 1 or len(completions) != 1 or frame is None):
        raise ValueError("Replay requires its completed native writer binding")
    writer = writers[0]
    if writer["kind"] != writer_kind:
        raise ValueError("Replay writer authorization belongs to a different surface")
    turn = next(t for t in history["turns"] if t["turn_id"] == ledger["turn_id"])
    completion = turn[context_key]["completion"]
    receipt = turn[context_key]["receipt"]
    delivered_context = _wrapped(directory / "answer-http.json")["body"].get(context_key)
    if ((writer["provider_attempt_id"], writer["provider"], writer["api_mode"], writer["serializer_version"])
            != (identity, "openai", "responses", "openai-sdk-json-v1")
            or ledger["attempt"] != trace_attempt["attempt"]
            or ledger["graph_context_receipt"] != receipt
            or ledger["graph_context_execution"]["context_receipt_sha256"] != receipt["context_receipt_sha256"]
            or completion["context_receipt_sha256"] != receipt["context_receipt_sha256"]
            or completion["producing_provider_attempt_id"] != identity
            or not isinstance(delivered_context, dict)
            or delivered_context.get("completion") != completion or delivered_context.get("receipt") != receipt
            or completions[0]["provider_attempt_id"] != identity
            or completions[0]["completion_sha256"] != canonical_sha256(completion)
            or writer["envelope_sha256"] != pin["sha256"]
            or writer["frame_sha256"] != canonical_sha256(frame)
            or frame["user_question"] != case["question"]
            or (writer["model"], witness["model"]) != (body["model"], body["model"])):
        raise ValueError("Replay writer request, frame or attempt binding differs")
    attempt = summary["operation"]["attempts"].get(identity)
    if (not attempt or (attempt["provider"], attempt["model"]) != ("openai", body["model"])
            or "authorized" not in attempt["outcomes"] or "response_received" not in attempt["outcomes"]):
        raise ValueError("Replay writer has no actual retained dispatch")
    required = {"model", "input", "instructions", "tools", "stream", "text", "reasoning", "service_tier"}
    if (not required <= set(body) or set(body) - required - {"max_output_tokens"}
            or body["tools"] != [] or body["stream"] is not False or body["service_tier"] != "fast"
            or not isinstance(body["instructions"], str) or not body["instructions"].strip()
            or not isinstance(body["input"], list) or not body["input"]
            or any(not isinstance(row, dict) or set(row) != {"role", "content"}
                or row["role"] != "user" or not isinstance(row["content"], str) for row in body["input"])
            or set(body["reasoning"]) != {"effort"}
            or set(body["text"]) != {"format"}
            or set(body["text"]["format"]) != {"type", "name", "schema", "strict"}
            or body["text"]["format"]["type"] != "json_schema"
            or body["text"]["format"]["name"] not in (
                "surface_native_evidence_selectors_v1", "surface_native_evidence_selectors_v2")
            or body["text"]["format"]["strict"] is not True):
        raise ValueError("Unsupported retained native writer packet")
    pending = [body["text"]["format"]["schema"]]
    while pending:
        value = pending.pop()
        if isinstance(value, dict):
            if (set(value) & {"$id", "$schema", "$dynamicRef", "$recursiveRef"}
                    or "$ref" in value and (not isinstance(value["$ref"], str) or not value["$ref"].startswith("#/"))):
                raise ValueError("Replay output schema must use only local native references")
            pending.extend(value.values())
        elif isinstance(value, list):
            pending.extend(value)
    jsonschema.Draft202012Validator.check_schema(body["text"]["format"]["schema"])
    return body, pin, {"turn_id": ledger["turn_id"], "conversation_id": ledger["conversation_id"],
        "world_id": history["world_id"], "writer_attempt_id": identity, "frame_sha256": writer["frame_sha256"]}


async def _writer_replay_call(packet, directory=None, *, transport=None, expected_wire=None):
    """Same provider/SDK as production; a missing directory is a denied offline preflight."""
    import httpx
    import jsonschema
    from generationengine import GenerationClient, TextRequest
    from generationengine.text_dispatch import TextDispatchGate
    from apps.live_control_server.services.plan_jev_writer import PlanWriterProvider
    from application_state.agent_conversation.source_writer_output import strict_json

    prepared_wire, outcomes = [], []
    async def authorize(prepared):
        if ((prepared.provider, prepared.api_mode, prepared.model, prepared.method, prepared.url)
                != ("openai", "responses", packet["model"], "POST", "https://api.openai.com/v1/responses")
                or len(prepared.body) != prepared.body_size
                or sha256(prepared.body).hexdigest() != prepared.body_sha256
                or strict_json(prepared.body.decode()) != packet
                or expected_wire is not None and expected_wire != {
                    "sha256": prepared.body_sha256, "size": prepared.body_size}):
            raise ValueError("Replay actual SDK wire differs from its frozen packet")
        prepared_wire.append({"sha256": prepared.body_sha256, "size": prepared.body_size})
        if directory is not None:
            immutable_save(directory, "wire-request", {"provider_attempt_id": prepared.attempt_id,
                "body": prepared.body.decode(), **prepared_wire[-1]})
        return directory is not None
    async def record(event):
        outcomes.append(event.outcome)
        if directory is not None:
            immutable_save(directory, "dispatch-" + event.outcome, {
                "provider_attempt_id": event.request.attempt_id, "outcome": event.outcome,
                "http_status": event.http_status, "request_sha256": event.request.body_sha256})
        return True
    def offline(_request):
        raise AssertionError("Offline writer preparation must not reach HTTP transport")
    provider = PlanWriterProvider(dispatch_gate=TextDispatchGate(authorize, record),
        **({"api_key": "offline-writer-preparation", "transport": httpx.MockTransport(offline)}
           if directory is None else {"transport": transport}))
    client = GenerationClient(text_providers={"openai": provider})
    started = time.perf_counter()
    try:
        result = await client.generate_structured(TextRequest(provider="openai", model=packet["model"],
            user_prompt=json.dumps(packet["input"], ensure_ascii=False), system_prompt=packet["instructions"],
            reasoning_effort=packet["reasoning"]["effort"], temperature=None,
            max_output_tokens=packet.get("max_output_tokens"), json_schema=packet["text"]["format"]["schema"],
            schema_name=packet["text"]["format"]["name"], max_conformance_retries=0, max_transport_retries=0))
        raw = provider.consume_completed_text(provider.actual_response, packet["model"])
        jsonschema.validate(strict_json(raw), packet["text"]["format"]["schema"])
        observation = result.observation.model_dump(mode="json")
        immutable_save(directory, "result", {"status": "diagnostic_complete", "raw_text": raw,
            "observation": observation, "elapsed_seconds": time.perf_counter()-started,
            "billed_cost_usd": observation.get("cost_usd") if observation.get("cost_status") == "reported" else None,
            "cost_status": observation.get("cost_status", "unavailable"),
            "semantic_acceptance": "unknown", "ordinary_delivery": "not_exercised"})
    except BaseException as exc:
        if directory is None:
            if not isinstance(exc, Exception):
                raise
            if len(prepared_wire) != 1 or outcomes != ["known_not_sent"]:
                raise ValueError("Offline SDK preparation failed before its exact denied dispatch") from exc
            return prepared_wire[0]
        immutable_save(directory, "failure", {"status": "diagnostic_failed", "exception_type": type(exc).__name__,
            "dispatch_outcomes": outcomes, "elapsed_seconds": time.perf_counter()-started,
            "observation": (exc.observation.model_dump(mode="json")
                if getattr(exc, "observation", None) is not None else None),
            "ordinary_delivery": "not_exercised", "automatic_resume": False})
        raise
    finally:
        if directory is not None and provider.actual_response is not None:
            immutable_save(directory, "sdk-response", provider.actual_response.model_dump(mode="json"))
        await client.aclose()


def _present_replay_body_paragraphs(packet):
    """Change only the presentation of already admitted native body text."""
    import re
    from application_state.agent_conversation.native_evidence_view import is_semantic_frame
    from application_state.agent_conversation.source_writer_output import strict_json

    for message in packet["input"]:
        try:
            frame = strict_json(message["content"])
        except ValueError:
            continue
        if not is_semantic_frame(frame):
            continue
        excerpts = frame["native_body_evidence"].get("excerpts")
        if not excerpts:
            break
        for excerpt in excerpts:
            original = excerpt["text"]
            paragraphs = re.findall(r".+?(?:\n[ \t]*\n+|\Z)", original, re.DOTALL)
            if not paragraphs or "".join(paragraphs) != original:
                raise ValueError("Replay paragraphs must preserve the exact admitted text")
            excerpt["text"] = paragraphs
        message["content"] = json.dumps(frame, ensure_ascii=False, separators=(",", ":"))
        return
    raise ValueError("Paragraph presentation requires retained native body excerpts")


def _writer_replay_plan(specification):
    import asyncio
    from copy import deepcopy
    spec, base = load_manifest(specification, schema="dmb_writer_replay_spec_v1")
    if set(spec) - {"schema", "cases", "runtime", "source_manifest", "instructions", "pins", "body_layout"}:
        raise ValueError("Unknown writer replay specification fields")
    if "body_layout" in spec and (spec["body_layout"] != "paragraphs" or spec.get("instructions") is not None):
        raise ValueError("Paragraph presentation must be the only replay change")
    verify_runtime(spec["runtime"], base)
    source_pin = spec["source_manifest"]
    read_pin(source_pin, base)
    source_path = Path(source_pin["path"])
    source_path = source_path if source_path.is_absolute() else base / source_path
    sources, source_base = load_manifest(source_path)
    summaries = {c["case_id"]: c for c in report(source_path)["cases"]}
    source_cases = {c["id"]: c for c in sources["cases"]}
    override = read_pin(spec["instructions"], base).decode() if spec.get("instructions") is not None else None
    if override is not None and not override.strip():
        raise ValueError("Empty shared replay instructions")
    cases = []
    for case in spec["cases"]:
        if case["id"] not in source_cases:
            raise ValueError("Replay case is not in its retained cohort")
        original, pin, binding = _writer_replay_request(case, source_cases[case["id"]], source_base,
            summaries[case["id"]], case_base=base)
        packet = deepcopy(original)
        if override is not None:
            packet["instructions"] = override
        if "body_layout" in spec:
            _present_replay_body_paragraphs(packet)
        wire = asyncio.run(_writer_replay_call(packet))
        cases.append({"id": case["id"], "question": case["question"], "source_request": pin,
            "binding": binding, "request_json": json.dumps(packet, ensure_ascii=False), "prepared_wire": wire,
            "original_instructions_sha256": sha256(original["instructions"].encode()).hexdigest()})
    path = Path(specification).resolve()
    return {"schema": "dmb_writer_replay_plan_v1", "specification": {"path": str(path), "sha256": sha256(path.read_bytes()).hexdigest()},
        "cases": cases, "scope": "provider_only_diagnostic; not APP authorization, citation acceptance or ordinary delivery"}


def writer_prepare(specification, output):
    plan = _writer_replay_plan(specification)
    immutable_save(Path(output).resolve(), "plan", plan)
    return plan


def writer_capture(plan_path, output, *, transport=None):
    import asyncio
    from application_state.agent_conversation.source_writer_output import strict_json
    plan_path = Path(plan_path).resolve()
    directory = Path(output).resolve()
    if directory.exists():
        raise FileExistsError("Writer replay output already exists; no resume or replacement")
    plan = strict_json(plan_path.read_text())
    pin = plan["specification"]
    read_pin(pin, plan_path.parent)
    source = Path(pin["path"])
    expected = _writer_replay_plan(source if source.is_absolute() else plan_path.parent / source)
    if plan != expected:
        raise ValueError("Prepared writer replay plan changed")
    directory.mkdir(mode=0o700, parents=True, exist_ok=False)
    immutable_save(directory, "plan", plan)
    completed = []
    for index, case in enumerate(plan["cases"]):
        target = directory / case["id"]
        immutable_save(target, "request", case)
        try:
            from application_state.agent_conversation.native_evidence_view import (
                semantic_frame_in_request, world_context_representation)
            packet = strict_json(case["request_json"])
            frame = semantic_frame_in_request(packet, legacy_schemas=())
            if frame is not None and world_context_representation(frame) == "historical":
                raise ValueError("Historical World host envelope is read-only; cannot dispatch replay")
            asyncio.run(_writer_replay_call(packet, target,
                transport=transport, expected_wire=case["prepared_wire"]))
        except BaseException:
            immutable_save(directory, "cohort", {"status": "stopped", "completed_cases": completed,
                "failed_case": case["id"], "unattempted_cases": [c["id"] for c in plan["cases"][index+1:]],
                "automatic_resume": False, "ordinary_delivery": "not_exercised"})
            raise
        completed.append(case["id"])
    immutable_save(directory, "cohort", {"status": "diagnostic_complete", "completed_cases": completed,
        "ordinary_delivery": "not_exercised", "semantic_acceptance": "unknown"})


def native_claim_property_orders(schema):
    """Ordered native claim fields; arrays survive canonical artifact storage."""
    selectors = {"native_statement_report": "statement_handles",
        "native_body_claim": "excerpt_handles", "native_assertion_claim": "assertion_handles"}
    rows = []
    def visit(value, path):
        if isinstance(value, dict):
            props = value.get("properties", {})
            kind = props.get("kind", {}).get("const")
            if kind in selectors and "text" in props and selectors[kind] in props:
                rows.append({"path": path, "kind": kind, "selector": selectors[kind],
                    "fields": list(props)})
            for key, child in value.items():
                visit(child, [*path, key])
        elif isinstance(value, list):
            for index, child in enumerate(value):
                visit(child, [*path, index])
    visit(schema, [])
    return rows


def citation_first_schema(schema):
    """Reorder native claim properties only; preserve every schema constraint."""
    from copy import deepcopy
    result = deepcopy(schema)
    rows = native_claim_property_orders(result)
    if not rows:
        raise ValueError("Citation-first requires native claim variants")
    for row in rows:
        node = result
        for key in row["path"]:
            node = node[key]
        props = node["properties"]
        node["properties"] = {**{key: value for key, value in props.items() if key != "text"},
            "text": props["text"]}
    if result != schema:
        raise ValueError("Citation-first changed schema constraints")
    return result


def verify_citation_first_wire(raw, expected_schema):
    """Inspect final SDK bytes, not a key-sorted request artifact."""
    from generationengine.utils.schema_utils import make_schema_strict
    body = json.loads(raw)
    fmt = body.get("response_format", {})
    contract = fmt.get("json_schema", {})
    expected = make_schema_strict(expected_schema)
    actual = contract.get("schema")
    rows = native_claim_property_orders(actual)
    if (fmt.get("type") != "json_schema" or contract.get("strict") is not True
            or actual != expected or rows != native_claim_property_orders(expected)
            or not rows or any(row["fields"].index(row["selector"]) > row["fields"].index("text")
                for row in rows)):
        raise ValueError("Citation-first schema order did not reach provider wire")
    return rows


def context_tasting(manifest_path, output, *, transport=None):
    """Provider-only comparison; never resume a product turn or retrieve evidence."""
    import asyncio
    from generationengine import GenerationClient, TextRequest
    from application_state.agent_conversation.native_evidence_view import semantic_frame_in_request
    from application_state.agent_conversation.types import canonical_sha256

    path = Path(manifest_path).resolve()
    spec = json.loads(path.read_text())
    required = {"schema", "source_request", "context_ready", "models"}
    if not required <= set(spec) or set(spec) - required - {"endpoint_catalog", "presentation", "instructions", "prompt_components", "qualification_review", "assessment", "schema_order"} or spec["schema"] != "dmb_context_tasting_v1":
        raise ValueError("Unknown context tasting specification")
    envelope = json.loads(read_pin(spec["source_request"], path.parent))
    ready = json.loads(read_pin(spec["context_ready"], path.parent))
    raw = bytes.fromhex(envelope["body_hex"])
    if (sha256(raw).hexdigest() != envelope["body_sha256"]
            or len(raw) != envelope["body_size"] or ready["frame_sha256"] is None):
        raise ValueError("Frozen writer request integrity differs")
    packet = json.loads(raw)
    frame = semantic_frame_in_request(packet, legacy_schemas=())
    if frame is None or canonical_sha256(frame) != ready["frame_sha256"]:
        raise ValueError("Frozen writer context-ready frame differs")
    if packet["tools"] != [] or not packet["instructions"] or not packet["input"]:
        raise ValueError("Tasting requires a tool-free retained writer packet")
    if any(set(row) != {"role", "content"} or row["role"] != "user"
           or not isinstance(row["content"], str) for row in packet["input"]):
        raise ValueError("Tasting adapter requires ordered user text messages")
    instructions = packet["instructions"]
    prompt_components = None
    if spec.get("instructions") is not None:
        instructions = read_pin(spec["instructions"], path.parent).decode("utf-8")
        if not instructions.strip() or spec.get("prompt_components") is None:
            raise ValueError("Prompt experiment requires nonblank instructions and versioned component manifest")
    if spec.get("prompt_components") is not None:
        prompt_components = json.loads(read_pin(spec["prompt_components"], path.parent))
        components = prompt_components.get("components", [])
        if (set(prompt_components) != {"contract", "components", "instructions_sha256"}
                or not isinstance(prompt_components["contract"], str) or not prompt_components["contract"].strip()
                or not isinstance(components, list) or not components
                or any(not isinstance(c, dict) or set(c) != {"name", "version", "text", "sha256"}
                    or any(not isinstance(c[k], str) or not c[k].strip() for k in ("name", "version", "text", "sha256"))
                    for c in components)):
            raise ValueError("Invalid versioned prompt component manifest")
        if len({c["name"] for c in components}) != len(components):
            raise ValueError("Prompt component names must be unique")
        if (any(c["sha256"] != sha256(c["text"].encode()).hexdigest() for c in components)
                or "\n\n".join(c["text"] for c in components) != instructions):
            raise ValueError("Prompt component texts or hashes differ from compiled instructions")
        if prompt_components.get("instructions_sha256") != sha256(instructions.encode()).hexdigest():
            raise ValueError("Prompt components differ from actual instructions")
    presentation = spec.get("presentation", "retained_json")
    if presentation not in {"retained_json", "flat_native_assertions_v2"}:
        raise ValueError("Unknown evidence presentation")
    input_contents = [row["content"] for row in packet["input"]]
    flat = None
    qualification_repair = None
    if presentation == "flat_native_assertions_v2" or spec.get("qualification_review") is not None:
        from application_state.agent_conversation.native_evidence_presentation import (
            flat_native_evidence, reviewed_qualification_frame)
        positions = []
        for index, content in enumerate(input_contents):
            try:
                if json.loads(content) == frame:
                    positions.append(index)
            except json.JSONDecodeError:
                continue
        if len(positions) != 1:
            raise ValueError("Presentation requires one exact retained semantic frame")
        presented_frame = frame
        if spec.get("qualification_review") is not None:
            review = json.loads(read_pin(spec["qualification_review"], path.parent))
            presented_frame, binding = reviewed_qualification_frame(frame, review)
            qualification_repair = {"review": review, "binding": binding, "presented_frame": presented_frame}
        if presentation == "flat_native_assertions_v2":
            text, proof = flat_native_evidence(presented_frame)
            flat = {"text": text, "readback_proof": proof}
        else:
            text = json.dumps(presented_frame, ensure_ascii=False, separators=(",", ":"), allow_nan=False)
        input_contents[positions[0]] = text
    assessment = None
    output_schema = packet["text"]["format"]["schema"]
    schema_name = packet["text"]["format"]["name"]
    schema_order = spec.get("schema_order", "retained")
    if schema_order not in {"retained", "citation_first"}:
        raise ValueError("Unknown schema order experiment")
    if schema_order == "citation_first":
        output_schema = citation_first_schema(output_schema)
    judge_role = prompt_components is not None and prompt_components['contract'] == 'buddy_writer_judge_v1'
    if (spec.get('assessment') is not None) != judge_role:
        raise ValueError('Judge inputs require an explicit versioned judge role; never ordinary writer inputs')
    if judge_role:
        if schema_order != "retained":
            raise ValueError("Schema order experiments require writer inputs")
        from .writer_assessment import validate_judge_inputs
        pins = spec['assessment']
        if not isinstance(pins, dict) or set(pins) != {'candidates', 'reference', 'schema'}:
            raise ValueError('Invalid pinned judge task')
        assessment = {key: json.loads(read_pin(pin, path.parent)) for key, pin in pins.items()}
        validate_judge_inputs(assessment['candidates'], assessment['reference'], assessment['schema'],
                              answer_schema=output_schema)
        output_schema, schema_name = assessment['schema'], 'writer_quality_assessment_v1'
        input_contents += ['REFERENCE CRITERIA\n' + json.dumps(assessment['reference'], ensure_ascii=False),
                           'CANDIDATE REPLIES TO ASSESS\n' + json.dumps(assessment['candidates'], ensure_ascii=False)]
    models = spec["models"]
    if not models or len(models) != len(set(models)) or any(not isinstance(m, str) or "/" not in m for m in models):
        raise ValueError("Tasting requires distinct explicit OpenRouter model identifiers")
    routes = {}
    if spec.get("endpoint_catalog") is not None:
        catalog = json.loads(read_pin(spec["endpoint_catalog"], path.parent))
        for model in models:
            entry = catalog.get(model, {}).get("data", {})
            if entry.get("id") != model:
                raise ValueError("Endpoint catalog model binding differs")
            routes[model] = sorted({endpoint["tag"] for endpoint in entry.get("endpoints", [])
                if isinstance(endpoint.get("tag"), str) and endpoint["tag"]
                and {"structured_outputs", "response_format"} <= set(endpoint.get("supported_parameters") or [])
                and (packet["reasoning"]["effort"] is None or "reasoning" in (endpoint.get("supported_parameters") or []))})
    directory = Path(output).resolve()
    if directory.exists():
        raise FileExistsError("Tasting output exists; no automatic replay")
    directory.mkdir(parents=True, mode=0o700)
    immutable_save(directory, "specification", spec)
    immutable_save(directory, "frozen-packet", packet)
    if assessment is not None:
        immutable_save(directory, "assessment-task", assessment)
    if qualification_repair is not None:
        immutable_save(directory, "qualification-review", qualification_repair)
    if prompt_components is not None:
        immutable_save(directory, "prompt-components", prompt_components)
    if flat is not None:
        immutable_save(directory, "flat-presentation", flat)
    secrets.SystemRandom().shuffle(models)
    mapping = {chr(65+i): model for i, model in enumerate(models)}
    immutable_save(directory, "identity-key", mapping)
    # GE's public request has one user string. Preserve raw ordered content,
    # rather than JSON-escaping the original message array inside user content.
    shared = dict(provider="openrouter", user_prompt="\n\n".join(input_contents),
        system_prompt=instructions, temperature=None,
        json_schema=output_schema, schema_name=schema_name,
        reasoning_effort=packet["reasoning"]["effort"],
        max_output_tokens=packet.get("max_output_tokens"), max_conformance_retries=0, max_transport_retries=0)
    immutable_save(directory, "shared-request", shared)

    async def run():
        semaphore = asyncio.Semaphore(2)
        async def one(label, model):
            async with semaphore:
                target = directory / label
                if model in routes and not routes[model]:
                    immutable_save(target, "excluded", {"reason": "No declared native structured-output endpoint with requested parameters", "provider_attempt_count": 0})
                    return {"label": label, "status": "excluded"}
                immutable_save(target, "request", {**shared, "model": model})
                started = time.perf_counter()
                if schema_order == "citation_first" or transport is not None:
                    import httpx
                    from openai import AsyncOpenAI
                    from generationengine.providers.openrouter_text import OpenRouterTextProvider, OPENROUTER_BASE_URL
                    wire_count = 0
                    async def retain_wire(request):
                        nonlocal wire_count
                        wire_count += 1
                        raw = request.content
                        orders = (verify_citation_first_wire(raw, output_schema)
                            if schema_order == "citation_first" else [])
                        immutable_save(target, "provider-wire-" + str(wire_count), {
                            "body_hex": raw.hex(), "body_sha256": sha256(raw).hexdigest(),
                            "body_size": len(raw), "claim_property_orders": orders,
                            "citation_first_verified": schema_order == "citation_first"})
                    api_key = os.environ.get("OPENROUTER_API_KEY")
                    if not api_key:
                        if transport is None:
                            raise ValueError("OPENROUTER_API_KEY is required for tasting")
                        api_key = "offline-test"
                    sdk = AsyncOpenAI(api_key=api_key, base_url=OPENROUTER_BASE_URL, max_retries=0,
                        http_client=httpx.AsyncClient(transport=transport, event_hooks={"request": [retain_wire]}))
                    client = GenerationClient(text_providers={"openrouter": OpenRouterTextProvider(client=sdk)})
                else:
                    client = GenerationClient()
                async def retain_attempt(event):
                    immutable_save(target, "attempt-" + str(event.ordinal), event.model_dump(mode="json"))
                try:
                    parameters = dict(shared)
                    if model in routes:
                        from generationengine.types import ProviderRoute
                        parameters["provider_route"] = ProviderRoute(order=tuple(routes[model]),
                            allow_fallbacks=False, require_parameters=True)
                        immutable_save(target, "route", parameters["provider_route"].model_dump(mode="json"))
                    result = await client.generate_structured(TextRequest(model=model, **parameters),
                        on_attempt_completed=retain_attempt)
                    immutable_save(target, "result", {"text": result.text, "parsed": result.parsed,
                        "observation": result.observation.model_dump(mode="json"),
                        "elapsed_seconds": time.perf_counter()-started})
                    return {"label": label, "status": "returned"}
                except Exception as exc:
                    observation = getattr(exc, "observation", None)
                    immutable_save(target, "failure", {"exception_type": type(exc).__name__,
                        "message": str(exc), "elapsed_seconds": time.perf_counter()-started,
                        "observation": observation.model_dump(mode="json") if observation is not None else None})
                    return {"label": label, "status": "failed"}
                finally:
                    await client.aclose()
        return await asyncio.gather(*(one(label, model) for label, model in mapping.items()))
    immutable_save(directory, "cohort", {"results": asyncio.run(run()),
        "scope": "provider_only; no retrieval, APP delivery or local hardware measurement"})
    blind = []
    for label in mapping:
        result_path = directory / label / "result.json"
        if result_path.exists():
            result = json.loads(result_path.read_text())
            blind.append({"label": label, "text": result["text"], "parsed": result["parsed"]})
        else:
            blind.append({"label": label, "status": "excluded" if (directory / label / "excluded.json").exists() else "failed"})
    immutable_save(directory, "blind-answers", blind)


def _action_operation_metrics(capture, expected_turn_id):
    body = capture["body"]
    trace = body["answer"]["trace"]
    if (
        not isinstance(expected_turn_id, str)
        or not expected_turn_id
        or trace["schema"] != "dmb_agent_turn_trace_v1"
        or body["turn_id"] != expected_turn_id
        or trace["turn_id"] != expected_turn_id
    ):
        raise ValueError("AW trace does not match the expected turn")
    return {
        "elapsed_ms": trace["elapsed_ms"],
        "model_tokens": trace["usage"]["total_tokens"],
        "model_calls": trace["usage"]["model_call_count"],
        "usage_status": trace["usage"]["status"],
        "usage_reported_call_count": trace["usage"]["usage_reported_call_count"],
        "reported_cost_usd": trace["cost"]["usd"],
        "cost_status": trace["cost"]["status"],
        "operator_interventions": None,
        "stages": [
            {"name": span["name"], "duration_ms": span["duration_ms"], "status": span["status"]}
            for span in trace["spans"] if span["kind"] == "phase"
        ],
    }


def retained_action_report(ledger, base):
    """Join reviewed case judgments to independently pinned ordinary turn measurements."""
    rows = []
    by_action = {}
    seen_turns = set()
    seen_cases = set()
    for case in ledger["cases"]:
        case_id = case["id"]
        tiers = by_action.setdefault(case["action"], {})
        tier = str(case["tier"])
        if case_id in seen_cases or tier in tiers:
            raise ValueError("Duplicate action case or tier")
        seen_cases.add(case_id)
        row = {key: case.get(key) for key in (
            "id", "action", "tier", "specification", "run_status", "unrun_reason",
            "review_note", "qualification_required", "fixture_limitation",
            "expected_actions_observed", "required_retrieval_missed", "exact_reopen",
            "unnecessary_retrieval", "unnecessary_jev_source_opens",
            "zero_new_retrieval_disposition")}
        row["reviewed_outcome"] = case.get("outcome", "unrun")
        row["turns"] = []
        if case["run_status"] == "executed":
            for variant in case.get("variants", [case]):
                answer = json.loads(read_pin(variant["answer"], base))
                trace = json.loads(read_pin(variant["trace"], base))["body"]
                directory = (base / variant["answer"]["path"]).parent
                request_path = directory / "request.json"
                history_path = directory / "history-after.json"
                request = json.loads(request_path.read_bytes())
                history = _wrapped(history_path)["body"]
                turns = _request_turns(history, request, trace["world_id"])
                if [t["turn_id"] for t in turns] != [trace["turn_id"]]:
                    raise ValueError("Request and history do not identify this durable trace")
                if answer["http_status"] == 200 and answer["body"]["turn_id"] != request["turn_id"]:
                    raise ValueError("Answer belongs to another client request")
                turn_id = trace["turn_id"]
                if not turn_id or turn_id in seen_turns:
                    raise ValueError("Missing or duplicate retained turn")
                seen_turns.add(turn_id)
                operation = None
                if answer["body"].get("answer", {}).get("trace"):
                    if answer["body"]["conversation"]["conversation_id"] != trace["attempts"][0]["conversation_id"]:
                        raise ValueError("Answer and durable trace belong to different conversations")
                    operation = _action_operation_metrics(answer, answer["body"]["turn_id"])
                attempts = trace["attempts"]
                if any((a["turn_id"], a["world_id"], a["conversation_id"]) !=
                       (turn_id, history["world_id"], history["conversation_id"]) for a in attempts):
                    raise ValueError("Trace attempt belongs to another turn")
                row["turns"].append({
                    "id": variant.get("case_id", case_id), "turn_id": turn_id,
                    "answer": variant["answer"], "trace": variant["trace"],
                    "correlation_sidecars": {
                        "status": "observed_not_pinned_by_ledger",
                        "request_sha256": sha256(request_path.read_bytes()).hexdigest(),
                        "history_sha256": sha256(history_path.read_bytes()).hexdigest(),
                    },
                    "reviewed_source_open_count": variant.get("recorded_source_open_count"),
                    "discovery_measurement": variant.get("host_graph_discovery_measurement"),
                    "http_status": answer["http_status"], "http_elapsed_ms": answer["elapsed_ms"],
                    "ledger_elapsed_ms": variant.get("latency_ms"), "operation": operation,
                    "attempts": [{
                        "attempt": a["attempt"], "capture_status": a["capture_status"],
                        "recorded_retrieved_decisions": sum(
                            x["kind"] == "context_decision" and x["action"] == "retrieved"
                            for x in a["observations"]),
                        "recorded_expanded_decisions": sum(
                            x["kind"] == "context_decision" and x["action"] == "expanded"
                            for x in a["observations"]),
                        "recorded_discovery_hops": len(a["native_discovery_replay"]["hops"])
                            if a.get("native_discovery_replay") is not None else None,
                    } for a in attempts],
                })
        tiers[tier] = {key: row[key] for key in (
            "id", "reviewed_outcome", "unnecessary_retrieval", "unnecessary_jev_source_opens")}
        rows.append(row)
    source_open_reviews = [row["unnecessary_jev_source_opens"] for row in rows
                           if row["unnecessary_jev_source_opens"] is not None]
    zero_retrieval_reviews = [row["zero_new_retrieval_disposition"] for row in rows
                              if row["zero_new_retrieval_disposition"] is not None]
    return {
        "schema": "dmb_retained_action_report_v1",
        "build": ledger["product_build_executed"],
        "cases": rows,
        "by_action_tier": by_action,
        "retrieval_review_counts": {
            "jev_source_opens": {
                "case_rows_assessed": len(source_open_reviews),
                "case_rows_unnecessary": source_open_reviews.count(True),
                "historical_aggregate": ledger.get("retrieval_counts"),
            },
            "zero_new_retrieval": {
                "case_rows_audited": len(zero_retrieval_reviews),
                "case_rows_failed": sum(value.startswith("fail:") for value in zero_retrieval_reviews),
                "case_rows_unverified": sum(
                    value.startswith("unverified:") for value in zero_retrieval_reviews),
            },
        },
    }


def action_report(manifest_path):
    """Score retained action observations without starting an ordinary turn."""
    from .action_assessment import (
        assess_blocked_action,
        assess_confirmed_action,
        assess_conversation_only,
    )

    assess = {
        "conversation_only": assess_conversation_only,
        "confirmed_action": assess_confirmed_action,
        "blocked_action": assess_blocked_action,
    }

    path = Path(manifest_path)
    manifest = json.loads(path.read_text())
    if manifest.get("schema") == "dmb_right_action_baseline_status_v1":
        return retained_action_report(manifest, path.parent)
    if manifest.get("schema") != "dmb_aw_assessment_v1":
        raise ValueError("Unknown AW assessment manifest")
    cases = manifest["cases"]
    ids = [case["id"] for case in cases]
    if not ids or len(ids) != len(set(ids)):
        raise ValueError("AW assessment requires unique case IDs")
    results = []
    for case in cases:
        observation = json.loads(read_pin(case["observation"], path.parent))
        assessment = assess[case.get("kind", "conversation_only")](**observation)
        row = {"id": case["id"], "observation": case["observation"], **assessment}
        if "turn_capture" in case:
            pin = case["turn_capture"]
            capture = json.loads(read_pin(pin, path.parent))
            row["turn_capture"] = pin
            row["operation"] = _action_operation_metrics(capture, case.get("turn_id"))
        results.append(row)
    return {"schema": "dmb_aw_assessment_report_v1", "cases": results}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("report", "action-report", "capture", "capture-context",
        "capture-context-cohort", "capture-cohort", "writer-prepare", "writer-capture", "context-tasting", "trace-report"))
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--workers", type=int, default=2)
    parser.add_argument("--live-plan", action="store_true", help="Capture ordinary Plan delivery with an editor placement")
    parser.add_argument("--live-build", action="store_true", help="Forward a validated Build editor request to ordinary Buddy")
    parser.add_argument("--build-fixture", action="store_true", help="Capture a Build editor selection before model dispatch")
    parser.add_argument("--oracle", help="Private Gold JSON for offline report mode")
    parser.add_argument("--citation-readback", help="Retained excerpt citation readback JSONL")
    parser.add_argument("--writer-transport", action="store_true",
                        help="Capture the serialized writer request at a local transport sink")
    parser.add_argument("--browser-cohort", action="store_true",
                        help="Capture ordinary browser Send to the local writer transport sink for each cohort member")
    parser.add_argument("--detailed-trace", action="store_true", help="Retain individual host timing intervals")
    parser.add_argument("--trace-input", type=Path, help="Retained detailed capture directory")
    parser.add_argument("--case", help="Manifest case ID for trace-report or isolated browser capture")
    parser.add_argument("--clone-app", action="store_true",
                        help="Own and drop a temporary clone of the pinned local App fixture")
    args = parser.parse_args(argv)
    browser_cohort = args.mode == "capture-context-cohort" and args.browser_cohort
    if args.browser_cohort and not browser_cohort:
        parser.error("--browser-cohort requires capture-context-cohort")
    if args.detailed_trace and args.mode != "capture-context" and not browser_cohort:
        parser.error("--detailed-trace requires capture-context or a browser cohort")
    if args.writer_transport and args.mode != "capture-context":
        parser.error("--writer-transport requires capture-context")
    if args.clone_app and args.mode not in {"capture", "capture-context", "capture-context-cohort", "capture-cohort"}:
        parser.error("--clone-app requires a capture command")
    if args.mode != "report" and (args.oracle or args.citation_readback):
        parser.error("Oracle and citation readback are available only in report mode")
    if args.mode == "trace-report":
        if args.trace_input is None or args.case is None:
            parser.error("trace-report requires --trace-input and --case")
        manifest, _ = load_manifest(args.manifest)
        case = next((case for case in manifest["cases"] if case["id"] == args.case), None)
        if case is None:
            parser.error("trace-report case is absent from the manifest")
        from .trace_report import write_report
        write_report(args.trace_input, args.case, Path(args.output), world=manifest["world"], question=case["question"])
        return
    if args.trace_input is not None:
        parser.error("--trace-input requires trace-report")
    if args.live_plan and (args.mode != "capture" or args.case is None or not args.clone_app or args.build_fixture):
        parser.error("--live-plan requires capture, --case and --clone-app")
    if args.live_build and not args.build_fixture:
        parser.error("--live-build requires --build-fixture")
    if args.build_fixture and (args.mode != "capture" or args.case is None or not args.clone_app):
        parser.error("--build-fixture requires capture, --case and --clone-app")
    if args.case is not None and not (args.mode == "capture-context" and args.writer_transport or args.mode == "capture" and (args.build_fixture or args.live_plan)):
        parser.error("--case requires trace-report, Build fixture, or capture-context --writer-transport")
    if args.mode == "report":
        immutable_save(Path(args.output), "report", report(args.manifest, oracle=args.oracle, citation_readback=args.citation_readback))
    elif args.mode == "action-report":
        immutable_save(Path(args.output), "action-report", action_report(args.manifest))
    elif args.mode == "capture":
        options = {"browser_case": args.case, "build_fixture": True, "live_build": args.live_build} if args.build_fixture else {}
        if args.live_plan:
            options = {"browser_case": args.case, "live_plan": True}
        capture(args.manifest, args.output, clone_app=args.clone_app, **options)
    elif args.mode == "capture-context":
        options = {"browser_case": args.case} if args.case is not None else {}
        if args.clone_app:
            options["clone_app"] = True
        capture(args.manifest, args.output, context_only=True, writer_transport=args.writer_transport,
                detailed_trace=args.detailed_trace, **options)
    elif args.mode in {"capture-context-cohort", "capture-cohort"}:
        from .cohort_capture import capture_cohort
        capture_cohort(args.manifest, args.output, workers=args.workers,
                       browser=browser_cohort, detailed_trace=args.detailed_trace, clone_app=args.clone_app,
                       context_only=args.mode == "capture-context-cohort")
    elif args.mode == "writer-prepare":
        writer_prepare(args.manifest, args.output)
    elif args.mode == "context-tasting":
        context_tasting(args.manifest, args.output)
    else:
        writer_capture(args.manifest, args.output)


if __name__ == "__main__":
    main()
