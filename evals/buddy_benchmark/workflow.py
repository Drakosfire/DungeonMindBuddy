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
from uuid import UUID, uuid4

from .artifacts import immutable_save


def read_pin(pin, base):
    path = Path(pin["path"])
    path = path if path.is_absolute() else base / path
    data = path.read_bytes()
    if sha256(data).hexdigest() != pin["sha256"]:
        raise ValueError("Evidence pin mismatch: " + str(path))
    return data


def load_manifest(path, *, schema="dmb_ordinary_benchmark_v1"):
    path = Path(path).resolve()
    if schema == "dmb_ordinary_benchmark_v1":
        manifest = json.loads(path.read_text())
    else:
        from application_state.agent_conversation.source_writer_output import strict_json
        manifest = strict_json(path.read_text())
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


def validate_template(template, world, *, context_only=False):
    allowed = {"schema", "client_thread_id", "turn_id", "surface", "owner_scope",
        "primary_work", "client_work_state", "graph_request", "graph_selection", "plan_context_policy"}
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


def report_case(case, base):
    """Facts from retained receipts; semantic grades only from pinned reviews."""
    directory = Path(case["capture_dir"])
    directory = directory if directory.is_absolute() else base / directory
    boundary = case.get("capture_boundary", "response")
    if boundary not in {"response", "context_ready"}:
        raise ValueError("Unknown capture boundary")
    context_only = boundary == "context_ready"
    names = ("request", "history-after", "context-trace") + (
        ("context-ready", "context-request", "context-stop") if context_only else ("answer-http",))
    paths = {name: directory / (name + ".json") for name in names}
    if context_only and (directory / "answer-http.json").exists():
        paths["answer-http"] = directory / "answer-http.json"
    missing = [name for name, path in paths.items() if not path.exists()]
    if missing:
        if case.get("assessment") is not None:
            raise ValueError("Reviewed capture evidence is missing")
        return {"case_id": case["id"], "question": case["question"],
        "capture_status": "incomplete" if (directory / "dispatch.json").exists() else "not_started", "missing_artifacts": missing,
            "delivery": {"status": "not_requested" if context_only else "unknown"},
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
    turns = [t for t in history["body"]["turns"] if t["user_text"] == case["question"]]
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
        from .context_capture import validate_context_packet
        context_packet = validate_context_packet(documents["context-ready"], documents["context-request"], documents["context-stop"])
        captured = context_packet["turn"]
        authorization = context_packet["authorization"]
        if ((str(captured.turn_id), str(captured.conversation_id), captured.world_id, captured.user_text)
                != (turn["turn_id"], conversation, world, case["question"])):
            raise ValueError("Captured context belongs to another ordinary turn")
        if len([p for p in prompt_witnesses
                if p.get("provider_attempt_id") == str(authorization.provider_attempt_id)
                and p["payload_sha256"] == authorization.envelope_sha256]) != 1:
            raise ValueError("Context capture has no unique admitted prompt witness")
    answer_body = answer["body"] if isinstance(answer["body"], dict) else {}
    delivered = (answer["http_status"] == 200 and turn["lifecycle_status"] == "completed"
        and bool(turn.get("assistant_text"))
        and answer_body.get("answer", {}).get("text") == turn["assistant_text"])
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
            "capture_boundary": "context_ready", "durable_turn_id": turn["turn_id"], "boundaries": boundaries,
            "context": {"status": "captured", "accepted_to_ready_ms": context_packet["elapsed_ms"],
                "request_to_ready_ms": context_packet["request_to_ready_ms"],
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
    elapsed = answer.get("elapsed_ms")
    if elapsed is None and (directory / "terminal.json").exists():
        elapsed = json.loads((directory / "terminal.json").read_text())["elapsed_seconds"] * 1000
    def total(key):
        return sum(c[key] for c in calls.values()) if calls and all(c[key] is not None for c in calls.values()) else None
    return {"case_id": case["id"], "question": case["question"], "capture_status": "complete",
        "durable_turn_id": turn["turn_id"], "boundaries": boundaries,
        "delivery": {"status": "pass" if delivered else "fail", "http_status": answer["http_status"],
            "lifecycle_status": turn["lifecycle_status"]},
        "operation": {"elapsed_ms": elapsed, "provider_attempts": len(calls),
            "input_tokens": total("input_tokens"), "output_tokens": total("output_tokens"),
            "billed_cost_usd": None, "cost_status": "unknown", "attempts": calls},
        "failures": failures, "verified_prompt_witnesses": prompt_count,
        "artifacts": {name: {"path": str(path), "sha256": sha256(path.read_bytes()).hexdigest()}
            for name, path in paths.items()}}


def report(manifest_path):
    manifest, base = load_manifest(manifest_path)
    rows = [report_case(case, base) for case in manifest["cases"]]
    return {"schema": "dmb_ordinary_benchmark_report_v1", "cases": rows,
        "limits": ["Semantic dispositions are pinned reviewer judgments, not inferred from HTTP success.",
            "No new calls or database access. Historical failures remain failures.",
            "Billing and missing measurements remain unknown; no estimated price is billed cost."]}


def capture_case(client, world, template, case, directory, *, context_only=False):
    """The single ordinary route sequence, shared by all question fixtures."""
    validate_template(template, world, context_only=context_only)
    if directory.exists() and any(directory.iterdir()):
        raise ValueError("Case output already exists; do not redispatch")
    route = "/api/live/agent/worlds/" + world + "/conversation"
    def save(name, response):
        envelope = response_envelope(response)
        immutable_save(directory, name, envelope)
        body = envelope["body"]
        return body
    before = save("history-before", client.get(route))
    command = {"schema": "dmb_agent_new_conversation_v1", "command_id": str(uuid4()),
        "expected_pointer_revision": before["pointer_revision"],
        "expected_active_conversation_id": before["active_conversation_id"]}
    immutable_save(directory, "new-conversation-request", command)
    response = client.post(route + "/new", json=command)
    save("new-conversation-response", response)
    if response.status_code != 200:
        raise ValueError("New conversation CAS failed; no question dispatched")
    fresh = save("fresh-history", client.get(route))
    if fresh["turns"]:
        raise ValueError("Ordinary benchmark requires a fresh conversation")
    request = json.loads(json.dumps(template))
    request.update(client_thread_id=str(uuid4()), turn_id=str(uuid4()), message=case["question"])
    request["surface"]["instance_id"] = request["client_thread_id"]
    immutable_save(directory, "request", request)
    immutable_save(directory, "dispatch", {"state": "dispatching", "automatic_restart": False})
    started = time.monotonic()
    error, known_response = None, False
    from contextlib import nullcontext
    from .context_capture import ContextCapture
    context_stop = ContextCapture(directory) if context_only else None
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
            turns = [t for t in history["turns"] if t["user_text"] == case["question"]]
            if len(turns) != 1:
                raise ValueError("Question has no unique durable turn; do not redispatch")
            save("context-trace", client.get(route + "/turns/" + turns[0]["turn_id"] + "/context-trace"))
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


def capture(manifest_path, output, *, context_only=False):
    """Explicit live entry point; never invoked by offline reporting."""
    manifest, base = load_manifest(manifest_path)
    if os.environ.get("DMB_AGENT_GRAPH_LOCAL_PROFILE"):
        raise ValueError("Capture cannot use a hidden local profile")
    if not manifest.get("pins"):
        raise ValueError("Capture requires pinned runtime/source evidence")
    verify_runtime(manifest["runtime"], base)
    template = manifest["request_template"]
    validate_template(template, manifest["world"], context_only=context_only)
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
    retained["cases"] = []
    for case in manifest["cases"]:
        # A new capture never inherits an old semantic assessment.
        current = {key: value for key, value in case.items() if key not in {"assessment", "assessments"}}
        if context_only:
            current["capture_boundary"] = "context_ready"
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
        with TestClient(application.create_app(), client=("127.0.0.1", 43021),
            headers={"Authorization": "Bearer " + token}, raise_server_exceptions=False) as client:
            if client.get("/health/ready").status_code != 200:
                raise ValueError("Runtime qualification changed; no question dispatched")
            verify_capture_environment(owned_env)
            from apps.live_control_server.services.plan_jev_dispatch import request_budget
            if request_budget() != manifest["provider_policy"]:
                raise ValueError("Effective ordinary provider policy differs")
            for case in manifest["cases"]:
                verify_capture_environment(owned_env)
                capture_case(client, manifest["world"], template, case, output / case["id"], context_only=context_only)
                checkpoint = row_inventory(native_dsn, readonly=readonly)
                immutable_save(output, "native-after-" + case["id"], checkpoint)
                if checkpoint != native_before:
                    raise ValueError("Native authority changed; later questions not dispatched")
    finally:
        native_after = row_inventory(native_dsn, readonly=readonly)
        immutable_save(output, "native-after", native_after)
        immutable_save(output, "report", report(output / "capture-manifest.json"))
        if native_before != native_after:
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
    if json.loads((directory / "request.json").read_text())["surface"].get("surface_id") != "plan":
        raise ValueError("Replay currently supports retained ordinary Plan writers only")
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
    turn = next(t for t in history["turns"] if t["turn_id"] == ledger["turn_id"])
    completion = turn["plan_context"]["completion"]
    receipt = turn["plan_context"]["receipt"]
    delivered_context = _wrapped(directory / "answer-http.json")["body"].get("plan_context")
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
            or body["text"]["format"]["name"] != "surface_native_evidence_selectors_v1"
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


def _writer_replay_plan(specification):
    import asyncio
    from copy import deepcopy
    spec, base = load_manifest(specification, schema="dmb_writer_replay_spec_v1")
    if set(spec) - {"schema", "cases", "runtime", "source_manifest", "instructions", "pins"}:
        raise ValueError("Unknown writer replay specification fields")
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


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("report", "capture", "capture-context", "writer-prepare", "writer-capture"))
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args(argv)
    if args.mode == "report":
        immutable_save(Path(args.output), "report", report(args.manifest))
    elif args.mode == "capture":
        capture(args.manifest, args.output)
    elif args.mode == "capture-context":
        capture(args.manifest, args.output, context_only=True)
    elif args.mode == "writer-prepare":
        writer_prepare(args.manifest, args.output)
    else:
        writer_capture(args.manifest, args.output)


if __name__ == "__main__":
    main()
