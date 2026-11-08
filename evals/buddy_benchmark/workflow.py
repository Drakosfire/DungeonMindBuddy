"""Parameterized ordinary turns and provider-free retained-run reporting.

Run with ``python -m evals.buddy_benchmark.workflow --help``. Gold and semantic
reviews belong to reporting only, never to the ordinary capture request.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
import os
from pathlib import Path
import secrets
import time
from uuid import uuid4

from .artifacts import immutable_save


def read_pin(pin, base):
    path = Path(pin["path"])
    path = path if path.is_absolute() else base / path
    data = path.read_bytes()
    if sha256(data).hexdigest() != pin["sha256"]:
        raise ValueError("Evidence pin mismatch: " + str(path))
    return data


def load_manifest(path):
    path = Path(path).resolve()
    manifest = json.loads(path.read_text())
    if manifest.get("schema") != "dmb_ordinary_benchmark_v1":
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


def validate_template(template, world):
    allowed = {"schema", "client_thread_id", "turn_id", "surface", "owner_scope",
        "primary_work", "client_work_state", "graph_request", "graph_selection", "plan_context_policy"}
    if (set(template) - allowed or template.get("schema") != "dmb_agent_turn_request_v1"
        or template.get("graph_selection") is not None
        or template.get("graph_request") != {"mode": "none"}
        or template.get("surface", {}).get("surface_id") != "plan"
        or template.get("owner_scope") != {"kind": "world", "world_id": world}
        or template.get("primary_work", {}).get("kind") != "plan"):
        raise ValueError("Ordinary capture template contains hints or an operation override")


def report_case(case, base):
    """Facts from retained receipts; semantic grades only from pinned reviews."""
    directory = Path(case["capture_dir"])
    directory = directory if directory.is_absolute() else base / directory
    paths = {name: directory / (name + ".json") for name in (
        "request", "answer-http", "history-after", "context-trace")}
    missing = [name for name, path in paths.items() if not path.exists()]
    if missing:
        if case.get("assessment") is not None:
            raise ValueError("Reviewed capture evidence is missing")
        return {"case_id": case["id"], "question": case["question"],
        "capture_status": "incomplete" if (directory / "dispatch.json").exists() else "not_started", "missing_artifacts": missing,
            "delivery": {"status": "unknown"},
            "operation": {"provider_attempts": None, "billed_cost_usd": None},
            "boundaries": {name: {"status": "unknown"} for name in (
                "ingestion_publication", "retrieval", "composition", "citations")}}
    documents = {name: json.loads(path.read_text()) for name, path in paths.items()}
    request = documents["request"]
    if request.get("message") != case["question"]:
        raise ValueError("Retained request belongs to another question")
    history = _wrapped(paths["history-after"])
    trace = _wrapped(paths["context-trace"])
    answer = _wrapped(paths["answer-http"])
    if (history["http_status"] != 200 or trace["http_status"] != 200
        or not isinstance(history["body"], dict) or not isinstance(trace["body"], dict)):
        if case.get("assessment") is not None:
            raise ValueError("Reviewed capture observations changed")
        return {"case_id": case["id"], "question": case["question"], "capture_status": "incomplete",
            "observation_status": {"history": history["http_status"], "trace": trace["http_status"]},
            "delivery": {"status": "fail" if answer["http_status"] != 200 else "unknown",
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
    calls, failures, prompt_count = {}, [], 0
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


def capture_case(client, world, template, case, directory):
    """The single ordinary route sequence, shared by all question fixtures."""
    validate_template(template, world)
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
    try:
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
        except Exception as exc:
            error = error or exc
        immutable_save(directory, "terminal", {"status": "observed" if known_response else "outcome_unknown",
            "error_type": type(error).__name__ if error else None,
            "elapsed_seconds": time.monotonic() - started, "automatic_restart": False})
    if error:
        raise error


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


def capture(manifest_path, output):
    """Explicit live entry point; never invoked by offline reporting."""
    manifest, base = load_manifest(manifest_path)
    if os.environ.get("DMB_AGENT_GRAPH_LOCAL_PROFILE"):
        raise ValueError("Capture cannot use a hidden local profile")
    if not manifest.get("pins"):
        raise ValueError("Capture requires pinned runtime/source evidence")
    verify_runtime(manifest["runtime"], base)
    template = manifest["request_template"]
    validate_template(template, manifest["world"])
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
                capture_case(client, manifest["world"], template, case, output / case["id"])
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


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("report", "capture"))
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args(argv)
    if args.mode == "report":
        immutable_save(Path(args.output), "report", report(args.manifest))
    else:
        capture(args.manifest, args.output)


if __name__ == "__main__":
    main()
