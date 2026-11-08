"""Ordinary capture contracts and offline reports; no provider or database calls."""
from copy import deepcopy
from hashlib import sha256
import json
from types import SimpleNamespace
from uuid import uuid4

import pytest

from evals.buddy_benchmark import workflow as w
from evals.buddy_benchmark.artifacts import immutable_save, row_inventory


def put(path, value):
    path.write_text(json.dumps(value))
    return {"path": str(path), "sha256": sha256(path.read_bytes()).hexdigest()}


@pytest.fixture
def retained(tmp_path):
    turn, attempt, evidence = str(uuid4()), str(uuid4()), str(uuid4())
    request = {"message": "Explain the route.", "turn_id": "client-turn", "client_thread_id": "client",
        "surface": {"instance_id": "surface"}, "owner_scope": {"kind": "world", "world_id": "world"}}
    put(tmp_path / "request.json", request)
    put(tmp_path / "answer-http.json", {"http_status": 200, "elapsed_ms": 20,
        "body": {"turn_id": "client-turn", "client_thread_id": "client", "answer": {"text": "A supported route."}}})
    put(tmp_path / "history-after.json", {"http_status": 200, "body": {"world_id": "world", "conversation_id": "conversation", "turns": [{
        "turn_id": turn, "user_text": request["message"], "assistant_text": "A supported route.",
        "provenance": {"world_id": "world", "surface_instance_id": "surface"},
        "lifecycle_status": "completed"}]}})
    prompt = tmp_path / (evidence + ".json")
    prompt.write_bytes(b'{"ordinary":"request"}')
    call = dict(kind="provider_call", provider_attempt_id=attempt, provider="openai",
        model="fixed", outcome="response_received", input_tokens=10, output_tokens=2)
    trace = {"http_status": 200, "body": {"world_id": "world", "turn_id": turn, "attempts": [{
        "turn_id": turn, "world_id": "world", "conversation_id": "conversation", "observations": [call, deepcopy(call),
        {"kind": "prompt_reference", "evidence_id": evidence,
         "payload_sha256": sha256(prompt.read_bytes()).hexdigest(),
         "payload_utf8_bytes": len(prompt.read_bytes())}]}]}}
    put(tmp_path / "context-trace.json", trace)
    case = {"id": "any-question", "question": request["message"],
        "capture_dir": str(tmp_path), "prompt_dir": str(tmp_path)}
    manifest = tmp_path / "manifest.json"
    put(manifest, {"schema": "dmb_ordinary_benchmark_v1", "cases": [case]})
    return tmp_path, case, manifest


def test_offline_report_deduplicates_attempts_without_claiming_semantic_pass(retained, monkeypatch):
    root, _, manifest = retained
    monkeypatch.setattr(w, "capture", lambda *a: pytest.fail("offline dispatch"))
    result = w.report(manifest)["cases"][0]
    assert result["delivery"]["status"] == "pass"
    assert result["operation"]["provider_attempts"] == 1
    assert result["operation"]["input_tokens"] == 10
    assert result["operation"]["billed_cost_usd"] is None
    assert all(x["status"] == "unknown" for x in result["boundaries"].values())


@pytest.mark.parametrize("status", [409, 503])
def test_operational_failure_is_preserved(retained, status):
    root, _, manifest = retained
    put(root / "answer-http.json", {"http_status": status, "body": {"detail": "failure"}})
    result = w.report(manifest)["cases"][0]
    assert result["delivery"] == {"status": "fail", "http_status": status, "lifecycle_status": "completed"}


@pytest.mark.parametrize("mutation", ["wrong_turn", "duplicate_question", "wrong_question", "changed_prompt", "conflicting_usage"])
def test_report_rejects_misbound_or_tampered_evidence(retained, mutation):
    root, _, manifest = retained
    history = json.loads((root / "history-after.json").read_text())
    trace = json.loads((root / "context-trace.json").read_text())
    if mutation == "wrong_turn":
        trace["body"]["turn_id"] = str(uuid4())
    elif mutation == "duplicate_question":
        history["body"]["turns"] *= 2
    elif mutation == "wrong_question":
        put(root / "request.json", {"message": "Another question"})
    elif mutation == "changed_prompt":
        trace["body"]["attempts"][0]["observations"][-1]["payload_sha256"] = "0" * 64
    else:
        trace["body"]["attempts"][0]["observations"][1]["input_tokens"] = 11
    put(root / "history-after.json", history)
    put(root / "context-trace.json", trace)
    with pytest.raises(ValueError):
        w.report(manifest)


def test_semantic_partial_requires_exact_pinned_review(retained):
    root, case, manifest = retained
    review = put(root / "review.json", {"composition": "missing intermediate junction"})
    history = json.loads((root / "history-after.json").read_text())["body"]
    capture = {"world_id": "world", "conversation_id": "conversation", "turn_id": history["turns"][0]["turn_id"],
        **{name+"_sha256": sha256((root / (name+".json")).read_bytes()).hexdigest()
            for name in ("request", "answer-http", "history-after", "context-trace")}}
    adopted = {"schema": "dmb_ordinary_benchmark_assessment_v1", "reviewer": "independent",
        "capture": capture, "boundaries": {"composition": {"status": "partial", "evidence": [{"artifact": review,
        "pointer": "/composition", "expected": "missing intermediate junction"}]}}}
    case["assessment"] = put(root / "adoption.json", adopted)
    put(manifest, {"schema": "dmb_ordinary_benchmark_v1", "cases": [case]})
    result = w.report(manifest)["cases"][0]
    assert result["boundaries"]["composition"]["status"] == "partial"
    put(root / "review.json", {"composition": "pass"})
    with pytest.raises(ValueError, match="pin mismatch"):
        w.report(manifest)


class Client:
    def __init__(self, question, *, fail_cas=False):
        self.posts = []
        self.question, self.fail_cas = question, fail_cas
        self.turn = str(uuid4())
    def response(self, body, status=200):
        return SimpleNamespace(status_code=status, json=lambda: body, content=json.dumps(body).encode())
    def get(self, route, **kwargs):
        if "context-trace" in route:
            assert self.turn in route
            return self.response({"turn_id": self.turn, "attempts": []})
        turns = [{"turn_id": self.turn, "user_text": self.question}] if kwargs else []
        return self.response({"pointer_revision": 3, "active_conversation_id": "prior", "turns": turns})
    def post(self, route, *, json):
        self.posts.append((route, json))
        return self.response({}, 409 if self.fail_cas else 200)


def template():
    return {"schema": "dmb_agent_turn_request_v1", "surface": {"surface_id": "plan"},
        "owner_scope": {"kind": "world", "world_id": "world"},
        "primary_work": {"kind": "plan", "object_id": "neutral"}, "graph_request": {"mode": "none"}}


def test_capture_uses_fresh_cas_question_only_and_durable_identity(tmp_path):
    case = {"id": "generic", "question": "Explain the route.", "gold_answer": "DO NOT SEND",
        "assessments": {"composition": "DO NOT SEND"}}
    client = Client(case["question"])
    w.capture_case(client, "world", template(), case, tmp_path)
    assert client.posts[0][1]["expected_pointer_revision"] == 3
    request = client.posts[1][1]
    assert request["message"] == case["question"]
    assert "DO NOT SEND" not in json.dumps(request)
    assert request["turn_id"] != client.turn
    assert json.loads((tmp_path / "history-after.json").read_text())["body"]["turns"][0]["turn_id"] == client.turn


def test_failed_cas_never_dispatches_question(tmp_path):
    client = Client("Explain the route.", fail_cas=True)
    with pytest.raises(ValueError, match="CAS failed"):
        w.capture_case(client, "world", template(), {"question": client.question}, tmp_path)
    assert len(client.posts) == 1


def test_checkpoint_replacement_is_not_a_resume(tmp_path):
    immutable_save(tmp_path, "dispatch", {"state": "dispatching"})
    immutable_save(tmp_path, "dispatch", {"state": "dispatching"})
    with pytest.raises(ValueError, match="collision"):
        immutable_save(tmp_path, "dispatch", {"state": "retry"})


@pytest.mark.parametrize("field,value", [
    ("gold_answer", "answer"), ("plan_requested_operation", "discuss"),
    ("graph_selection", {"subject_id": "hint"}), ("plan_authoring_capture", {}),
])
def test_hints_and_operation_overrides_fail_before_any_route(tmp_path, field, value):
    client = Client("Explain the route.")
    with pytest.raises(ValueError, match="template contains"):
        w.capture_case(client, "world", template() | {field: value}, {"question": client.question}, tmp_path)
    assert not client.posts


def test_non_json_failure_response_bytes_are_retained(tmp_path):
    client = Client("Explain the route.")
    original = client.post
    def post(route, **kwargs):
        if route.endswith("/turn"):
            return SimpleNamespace(status_code=503, content=b"upstream failure", json=lambda: json.loads("not json"))
        return original(route, **kwargs)
    client.post = post
    w.capture_case(client, "world", template(), {"question": client.question}, tmp_path)
    result = json.loads((tmp_path / "answer-http.json").read_text())
    assert result["http_status"] == 503 and result["body"] is None
    assert bytes.fromhex(result["raw_body_hex"]) == b"upstream failure"


def test_timeout_is_retained_as_unknown_without_redispatch(tmp_path):
    client = Client("Explain the route.")
    original = client.post
    def post(route, **kwargs):
        if route.endswith("/turn"):
            client.posts.append((route, kwargs["json"]))
            raise TimeoutError("private transport details")
        return original(route, **kwargs)
    client.post = post
    with pytest.raises(TimeoutError):
        w.capture_case(client, "world", template(), {"question": client.question}, tmp_path)
    terminal = json.loads((tmp_path / "terminal.json").read_text())
    assert terminal["status"] == "outcome_unknown"
    assert len(client.posts) == 2
    assert "private transport details" not in (tmp_path / "terminal.json").read_text()
    assert (tmp_path / "history-after.json").exists()


def test_free_manifest_grade_is_not_a_review(retained):
    root, case, manifest = retained
    case["assessments"] = {"composition": {"status": "pass"}}
    put(manifest, {"schema": "dmb_ordinary_benchmark_v1", "cases": [case]})
    with pytest.raises(ValueError, match="canonical assessment"):
        w.report(manifest)


def test_shared_inventory_preserves_explicit_historical_routing_keys():
    from contextlib import contextmanager
    class Cursor:
        def __init__(self, rows):
            self.rows = rows
        def fetchall(self):
            return self.rows
    class Connection:
        def execute(self, query):
            if "information_schema.tables" in str(query):
                return Cursor([{"table_schema": "agent", "table_name": "turn"}])
            return Cursor([{"body": '{"world_id":"w","operation_id":"op","turn_id":"t"}'}])
    @contextmanager
    def readonly(_):
        yield Connection()
    old = row_inventory("unused", readonly=readonly)
    new = row_inventory("unused", readonly=readonly, keys=("world_id", "operation_id", "turn_id"))
    assert old["agent.turn"][0]["sha256"] == new["agent.turn"][0]["sha256"]
    assert "operation_id" not in old["agent.turn"][0]["keys"]
    assert new["agent.turn"][0]["keys"]["operation_id"] == "op"


def test_completed_or_uncertain_case_is_never_redispatched(tmp_path):
    client = Client("Explain the route.")
    immutable_save(tmp_path, "dispatch", {"state": "dispatching"})
    with pytest.raises(ValueError, match="do not redispatch"):
        w.capture_case(client, "world", template(), {"question": client.question}, tmp_path)
    assert not client.posts


def test_offline_mode_has_no_live_imports(retained, monkeypatch):
    import builtins
    _, _, manifest = retained
    original = builtins.__import__
    def guarded(name, *args, **kwargs):
        if name.split(".")[0] in {"apps", "fastapi", "psycopg", "generationengine", "openai"}:
            pytest.fail("live import from offline report: " + name)
        return original(name, *args, **kwargs)
    monkeypatch.setattr(builtins, "__import__", guarded)
    assert w.report(manifest)["cases"][0]["delivery"]["status"] == "pass"


@pytest.mark.parametrize("field", ["world_id", "conversation_id"])
def test_same_question_wrong_context_is_rejected(retained, field):
    root, _, manifest = retained
    trace = json.loads((root / "context-trace.json").read_text())
    trace["body"]["attempts"][0][field] = "foreign"
    put(root / "context-trace.json", trace)
    with pytest.raises(ValueError):
        w.report(manifest)


def test_runtime_source_and_actual_dependency_bytes_are_required(tmp_path, monkeypatch):
    import importlib
    import subprocess
    from pathlib import Path
    module = tmp_path / "dependency.py"
    module.write_text("fixed dependency")
    source = Path(w.__file__).resolve()
    relative = "evals/buddy_benchmark/workflow.py"
    source_pin = put(tmp_path / "tree.json", {relative: sha256(source.read_bytes()).hexdigest()})
    dependency = put(tmp_path / "dependency.json", {"dependency.py": sha256(module.read_bytes()).hexdigest()})
    # Inventory only the declared package directory, not the test evidence files.
    package = tmp_path / "package"
    package.mkdir()
    installed = package / "dependency.py"
    installed.write_bytes(module.read_bytes())
    monkeypatch.setattr(subprocess, "check_output", lambda *a, **kw: (relative + "\0").encode())
    monkeypatch.setattr(importlib, "import_module", lambda name: SimpleNamespace(__file__=str(installed)))
    spec = {"source_tree": source_pin, "dependencies": dict.fromkeys(
        ("generationengine", "openai", "dungeonmind", "worldkeeper"), dependency)}
    w.verify_runtime(spec, tmp_path)
    installed.write_text("changed import")
    with pytest.raises(ValueError, match="dependency differs"):
        w.verify_runtime(spec, tmp_path)


@pytest.mark.parametrize("field", ["DMB_ARTIFACT_DATA_ROOT", "DMB_AGENT_GRAPH_SESSION_STORE",
    "DMB_AGENT_GRAPH_LOCAL_OPERATOR_TOKEN", "DUNGEONBUDDY_APPLICATION_STATE_DATABASE_URL"])
def test_startup_drift_is_rejected_before_dispatch(monkeypatch, field):
    monkeypatch.delenv("DMB_AGENT_GRAPH_LOCAL_PROFILE", raising=False)
    monkeypatch.setenv(field, "isolated")
    w.verify_capture_environment({field: "isolated"})
    monkeypatch.setenv(field, "redirected")
    with pytest.raises(ValueError, match="qualification changed"):
        w.verify_capture_environment({field: "isolated"})


def test_hidden_profile_cannot_redirect_capture(monkeypatch):
    monkeypatch.setenv("DMB_AGENT_GRAPH_LOCAL_PROFILE", "hidden")
    with pytest.raises(ValueError, match="qualification changed"):
        w.verify_capture_environment({})


@pytest.mark.parametrize("bad_observation", ["history-after", "context-trace"])
def test_observation_failure_has_explicit_partial_report(retained, bad_observation):
    root, _, manifest = retained
    put(root / (bad_observation + ".json"), {"http_status": 404, "body": None})
    row = w.report(manifest)["cases"][0]
    assert row["capture_status"] == "incomplete"
    assert row["delivery"]["status"] == "unknown"
    assert all(x["status"] == "unknown" for x in row["boundaries"].values())


def test_relative_capture_output_qualifies_absolute_owned_paths(tmp_path, monkeypatch):
    import os
    from pathlib import Path
    import sys
    from types import ModuleType
    import psycopg
    from evals.buddy_benchmark import artifacts
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("DMB_AGENT_GRAPH_LOCAL_PROFILE", raising=False)
    monkeypatch.setattr(w, "verify_runtime", lambda *args: None)
    monkeypatch.setattr(artifacts, "row_inventory", lambda *args, **kwargs: {})
    native = put(tmp_path / "native.json", {})
    isolation = {}
    for role, env in [("app", "DUNGEONBUDDY_APPLICATION_STATE_DATABASE_URL"),
                      ("native", "DUNGEONMIND_WORLD_GRAPH_AUTHORITY_DATABASE_URL")]:
        isolation[role] = dict(host="127.0.0.1", port=55447, database=role, oid="1", system_identifier="2")
        monkeypatch.setenv(env, "postgresql://127.0.0.1:55447/" + role)
    isolation["native"]["inventory"] = native
    class Connection:
        def __init__(self, database):
            self.database = database
        def __enter__(self):
            return self
        def __exit__(self, *args):
            return False
        def execute(self, query):
            return SimpleNamespace(fetchone=lambda: (self.database, "1", "2"))
    monkeypatch.setattr(psycopg, "connect", lambda dsn, **kw: Connection(dsn.rsplit("/", 1)[1]))
    package = ModuleType("apps.live_control_server")
    package.main = SimpleNamespace(__file__=str(Path(w.__file__).resolve().parents[2] / "apps/live_control_server/main.py"), create_app=lambda: None)
    monkeypatch.setitem(sys.modules, "apps.live_control_server", package)
    fastapi = ModuleType("fastapi.testclient")
    def stop_before_startup(*args, **kwargs):
        for key in ("DMB_ARTIFACT_DATA_ROOT", "DMB_AGENT_GRAPH_SESSION_STORE"):
            assert Path(os.environ[key]).is_absolute()
        raise RuntimeError("inert startup stop")
    fastapi.TestClient = stop_before_startup
    monkeypatch.setitem(sys.modules, "fastapi.testclient", fastapi)
    manifest = tmp_path / "capture.json"
    put(manifest, {"schema": "dmb_ordinary_benchmark_v1", "world": "world",
        "cases": [{"id": "generic", "question": "Explain."}], "pins": [native],
        "runtime": {}, "isolation": isolation, "request_template": template()})
    with pytest.raises(RuntimeError, match="inert startup stop"):
        w.capture(manifest, "relative-output")
    assert (tmp_path / "relative-output/capture-manifest.json").exists()
    report = json.loads((tmp_path / "relative-output/report.json").read_text())
    assert report["cases"][0]["capture_status"] == "not_started"
