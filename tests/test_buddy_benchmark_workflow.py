"""Ordinary capture contracts and offline reports; no provider or database calls."""
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import pytest

from evals.buddy_benchmark import workflow as w
from evals.buddy_benchmark.artifacts import immutable_save, row_inventory


@pytest.mark.parametrize('invalid', [None, 'writer_role', 'hidden_grades', 'schema', 'nested'])
def test_pinned_judge_role_and_native_contract_are_separate_from_writer_inputs(tmp_path, monkeypatch, invalid):
    import generationengine
    from application_state.agent_conversation import native_evidence_view, types
    from evals.buddy_benchmark.writer_assessment import quality_schema
    from tests.test_writer_assessment import native_answer_schema
    frame = {'user_question': 'A question'}
    monkeypatch.setattr(native_evidence_view, 'semantic_frame_in_request', lambda *a, **k: frame)
    packet = {'tools': [], 'instructions': 'Original writer.', 'input': [{'role': 'user', 'content': 'Evidence'}],
        'text': {'format': {'schema': native_answer_schema(), 'name': 'answer'}}, 'reasoning': {'effort': 'low'}}
    raw = json.dumps(packet).encode()
    text = 'Assess replies against supplied evidence; do not answer the campaign question.'
    instruction = tmp_path / 'instructions.txt'; instruction.write_text(text)
    components = {'contract': 'buddy_response_v1' if invalid == 'writer_role' else 'buddy_writer_judge_v1',
        'components': [{'name': 'judge_task', 'version': '1', 'text': text, 'sha256': sha256(text.encode()).hexdigest()}],
        'instructions_sha256': sha256(text.encode()).hexdigest()}
    candidates = [{'candidate_id': 'sample0', 'answer': {'answer_segments': [], 'limitations': [], 'requested_detail_gaps': []}}]
    if invalid == 'nested': candidates[0]['answer']['answer_segments'] = [{'text': 'A claim', 'expected_grades': {'grounding': 'pass'}}]
    reference = {'required_concepts': [{'id': 'concept0', 'description': 'A detail'}]}
    if invalid == 'hidden_grades': reference['expected_grades'] = {'sample0': 'pass'}
    schema = quality_schema(['sample0'], ['concept0'])
    if invalid == 'schema': schema['required'] = []
    spec = {'schema': 'dmb_context_tasting_v1', 'models': ['test/model'],
        'source_request': put(tmp_path / 'request.json', {'body_hex': raw.hex(), 'body_size': len(raw), 'body_sha256': sha256(raw).hexdigest()}),
        'context_ready': put(tmp_path / 'ready.json', {'frame_sha256': types.canonical_sha256(frame)}),
        'instructions': {'path': str(instruction), 'sha256': sha256(instruction.read_bytes()).hexdigest()},
        'prompt_components': put(tmp_path / 'components.json', components),
        'assessment': {k: put(tmp_path / (k+'.json'), v) for k,v in
            [('candidates', candidates), ('reference', reference), ('schema', schema)]}}
    manifest = tmp_path / 'manifest.json'; put(manifest, spec)
    seen = []
    class Client:
        async def generate_structured(self, request, **kwargs):
            seen.append(request)
            return SimpleNamespace(text='{}', parsed={}, observation=SimpleNamespace(model_dump=lambda **k: {}))
        async def aclose(self): pass
    monkeypatch.setattr(generationengine, 'GenerationClient', Client)
    output = tmp_path / 'output'
    if invalid:
        with pytest.raises(ValueError): w.context_tasting(manifest, output)
        assert not seen and not output.exists()
    else:
        w.context_tasting(manifest, output)
        assert seen[0].json_schema == schema
        assert seen[0].system_prompt == text
        assert 'REFERENCE CRITERIA' in seen[0].user_prompt and 'sample0' in seen[0].user_prompt
        assert 'expected_grades' not in seen[0].user_prompt and 'instructions_sha256' not in seen[0].user_prompt
        assert json.loads((output / 'frozen-packet.json').read_text()) == packet


@pytest.mark.parametrize("prompt_override,bad_manifest", [(False, None), (True, None), (True, "instructions"), (True, "component")])
def test_context_tasting_freezes_shared_input_and_retains_failures(tmp_path, monkeypatch, prompt_override, bad_manifest):
    import generationengine
    from application_state.agent_conversation import native_evidence_view, types
    frame = {"user_question": "A generic question"}
    monkeypatch.setattr(native_evidence_view, "semantic_frame_in_request", lambda *a, **k: frame)
    packet = {"tools": [], "instructions": "Same voice", "input": [{"role": "user", "content": "Evidence"}],
        "text": {"format": {"schema": {"type": "object"}, "name": "answer"}}, "reasoning": {"effort": "low"}}
    raw = json.dumps(packet).encode()
    request = put(tmp_path / "source.json", {"body_hex": raw.hex(), "body_sha256": sha256(raw).hexdigest(), "body_size": len(raw)})
    ready = put(tmp_path / "ready.json", {"frame_sha256": types.canonical_sha256(frame)})
    seen = []
    class Client:
        async def generate_structured(self, request, **kwargs):
            seen.append(request)
            if request.model == "test/failure":
                raise ValueError("retained failure")
            return SimpleNamespace(text='{}', parsed={}, observation=SimpleNamespace(model_dump=lambda **k: {"cost_status": "unavailable"}))
        async def aclose(self):
            pass
    monkeypatch.setattr(generationengine, "GenerationClient", Client)
    manifest = tmp_path / "manifest.json"
    specification = {"schema": "dmb_context_tasting_v1", "source_request": request, "context_ready": ready,
        "models": ["test/success", "test/failure"]}
    expected = "Same voice"
    if prompt_override:
        from application_state.agent_conversation.response_prompt import compose_response_prompt
        response = compose_response_prompt()
        expected = response.instructions
        instructions = tmp_path / "instructions.txt"
        instructions.write_text(expected)
        specification["instructions"] = {"path": str(instructions), "sha256": sha256(instructions.read_bytes()).hexdigest()}
        component_manifest = response.manifest()
        if bad_manifest == "instructions":
            component_manifest["instructions_sha256"] = "0" * 64
        elif bad_manifest == "component":
            component_manifest["components"][0]["sha256"] = "bogus"
        specification["prompt_components"] = put(tmp_path / "components.json", component_manifest)
    put(manifest, specification)
    output = tmp_path / "output"
    if bad_manifest:
        with pytest.raises(ValueError, match="Prompt component"):
            w.context_tasting(manifest, output)
        assert seen == [] and not output.exists()
        return
    w.context_tasting(manifest, output)
    assert len(seen) == 2

    assert {r.system_prompt for r in seen} == {expected}
    assert (output / "prompt-components.json").exists() == prompt_override
    assert all("instructions_sha256" not in r.system_prompt for r in seen)
    assert len({r.user_prompt for r in seen}) == 1
    assert seen[0].user_prompt == "Evidence"
    cohort = json.loads((output / "cohort.json").read_text())
    assert {r["status"] for r in cohort["results"]} == {"returned", "failed"}
    blind = (output / "blind-answers.json").read_text()
    assert "test/success" not in blind and "test/failure" not in blind
    assert "observation" not in blind
    with pytest.raises(FileExistsError):
        w.context_tasting(manifest, output)
    assert len(seen) == 2


@pytest.mark.parametrize("reviewed", [False, True, "pending"])
@pytest.mark.parametrize("presentation", ["flat_native_assertions_v2", "retained_json"])
def test_flat_tasting_changes_only_exact_evidence_frame(tmp_path, monkeypatch, reviewed, presentation):
    import generationengine
    from application_state.agent_conversation import native_evidence_view, types
    from application_state.agent_conversation.native_evidence_presentation import restore_flat_native_evidence
    frame = {"user_question": "Question", "native_assertions": {"assertions": [
        {"assertion_handle": "a0", "fact": "Exact fact"}], "qualifications": {"q0": {"standing": "provisional",
        "domain_metadata": [{"world_context": {"source_qualification": "Report only. host-binding"}}]}}}}
    packet = {"tools": [], "instructions": "Unchanged instructions", "input": [
        {"role": "user", "content": json.dumps(frame)}, {"role": "user", "content": "Return JSON."}],
        "text": {"format": {"schema": {"type": "object"}, "name": "answer"}}, "reasoning": {"effort": "low"}}
    raw = json.dumps(packet).encode()
    request = put(tmp_path / "request.json", {"body_hex": raw.hex(), "body_size": len(raw), "body_sha256": sha256(raw).hexdigest()})
    ready = put(tmp_path / "ready.json", {"frame_sha256": types.canonical_sha256(frame)})
    manifest = tmp_path / "manifest.json"
    specification = {"schema": "dmb_context_tasting_v1", "source_request": request, "context_ready": ready,
        "models": ["test/model"], "presentation": presentation}
    if reviewed:
        compact = lambda x: json.dumps(x, ensure_ascii=False, separators=(",", ":"), allow_nan=False)
        review = {"schema": "dmb_reviewed_qualification_parts_v1", "reviewer": "Independent reviewer",
            "source_frame_sha256": sha256(compact(frame).encode()).hexdigest(), "records": [
                {"qualification_handle": "q0", "domain_index": 0,
                 "original_sha256": sha256(b"Report only. host-binding").hexdigest(), "parts": [
                     {"role": "meaning", "text": "Report only. "},
                     {"role": "pending" if reviewed == "pending" else "host_audit", "text": "host-binding"}]}]}
        specification["qualification_review"] = put(tmp_path / "review.json", review)
    put(manifest, specification)
    monkeypatch.setattr(native_evidence_view, "semantic_frame_in_request", lambda *a, **k: frame)
    seen = []
    class Client:
        async def generate_structured(self, request, **kwargs):
            seen.append(request)
            return SimpleNamespace(text='{}', parsed={}, observation=SimpleNamespace(model_dump=lambda **k: {}))
        async def aclose(self):
            pass
    monkeypatch.setattr(generationengine, "GenerationClient", Client)
    output = tmp_path / "output"
    if reviewed == "pending":
        with pytest.raises(ValueError, match="Unresolved"):
            w.context_tasting(manifest, output)
        assert seen == [] and not output.exists()
        return
    w.context_tasting(manifest, output)
    expected = deepcopy(frame)
    if reviewed:
        expected["native_assertions"]["qualifications"]["q0"]["domain_metadata"][0]["world_context"]["source_qualification"] = "Report only. "
        assert json.loads((output / "frozen-packet.json").read_text()) == packet
        assert "host-binding" not in seen[0].user_prompt
        assert "source_frame_sha256" not in seen[0].user_prompt
    if presentation == "flat_native_assertions_v2":
        flat = json.loads((output / "flat-presentation.json").read_text())
        assert restore_flat_native_evidence(flat["text"], flat["readback_proof"]) == expected
        text = flat["text"]
    else:
        text = seen[0].user_prompt.removesuffix("\n\nReturn JSON.")
        assert json.loads(text) == expected
        assert not (output / "flat-presentation.json").exists()
    assert seen[0].system_prompt == packet["instructions"]
    assert seen[0].json_schema == packet["text"]["format"]["schema"]
    assert seen[0].user_prompt == text + "\n\nReturn JSON."
    assert "readback_proof" not in seen[0].user_prompt



@pytest.mark.parametrize("response_contract", [False, True, 'judge'])
def test_tasting_adapter_actual_sdk_wire_is_common_across_models(response_contract):
    import asyncio
    import httpx
    from openai import AsyncOpenAI
    from generationengine import GenerationClient, TextRequest
    from generationengine.providers.openrouter_text import OpenRouterTextProvider
    from application_state.agent_conversation.response_prompt import compose_response_prompt
    system = compose_response_prompt().instructions if response_contract else "Frozen voice"
    wires = []
    schema = {"type": "object", "properties": {}, "required": [], "additionalProperties": False}
    output = {}
    if response_contract == 'judge':
        from evals.buddy_benchmark.writer_assessment import AXES, quality_schema
        system = 'Assess the supplied replies, not the campaign question.'
        schema = quality_schema(['sample0'], ['concept0'])
        output = {'assessments': [{'candidate_id': 'sample0', 'covered_concepts': ['concept0'],
            'dimensions': {axis: {'judgment': 'pass', 'reason': 'Supported.',
                'segment_indices': [], 'support_handles': []} for axis in AXES}}]}
    def reply(request):
        wires.append(json.loads(request.content))
        return httpx.Response(200, json={"id": "offline-response", "object": "chat.completion",
            "created": 1, "model": wires[-1]["model"],
            "choices": [{"index": 0, "message": {"role": "assistant", "content": json.dumps(output)}, "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 2, "total_tokens": 12}})
    async def run():
        sdk = AsyncOpenAI(api_key="offline", base_url="https://openrouter.ai/api/v1",
            max_retries=0, http_client=httpx.AsyncClient(transport=httpx.MockTransport(reply)))
        client = GenerationClient(text_providers={"openrouter": OpenRouterTextProvider(client=sdk)})
        try:
            for model in ["test/one", "test/two"]:
                await client.generate_structured(TextRequest(provider="openrouter", model=model,
                    system_prompt=system, user_prompt="First context\n\nSecond context",
                    temperature=None, json_schema=schema, schema_name="answer",
                    max_conformance_retries=0, max_transport_retries=0))
        finally:
            await client.aclose()
    asyncio.run(run())
    assert len(wires) == 2
    assert wires[0]["messages"] == wires[1]["messages"] == [
        {"role": "system", "content": system},
        {"role": "user", "content": "First context\n\nSecond context"}]
    assert all(wire["response_format"] == {"type": "json_schema", "json_schema": {
        "name": "answer", "strict": True, "schema": schema}} for wire in wires)
    assert all(wire["provider"]["require_parameters"] is True for wire in wires)


def test_tasting_excludes_unsupported_endpoint_without_constructing_provider(tmp_path, monkeypatch):
    import generationengine
    from application_state.agent_conversation import native_evidence_view, types
    frame = {"user_question": "Generic"}
    monkeypatch.setattr(native_evidence_view, "semantic_frame_in_request", lambda *a, **k: frame)
    monkeypatch.setattr(generationengine, "GenerationClient", lambda: pytest.fail("Excluded endpoint dispatched"))
    packet = {"tools": [], "instructions": "Same voice", "input": [{"role": "user", "content": "Evidence"}],
        "reasoning": {"effort": "low"}, "text": {"format": {"schema": {"type": "object"}, "name": "answer"}}}
    raw = json.dumps(packet).encode()
    request = put(tmp_path / "request.json", {"body_hex": raw.hex(), "body_size": len(raw), "body_sha256": sha256(raw).hexdigest()})
    ready = put(tmp_path / "ready.json", {"frame_sha256": types.canonical_sha256(frame)})
    catalog = put(tmp_path / "catalog.json", {"fixture/model": {"data": {"id": "fixture/model", "endpoints": [
        {"tag": "unsupported", "supported_parameters": ["response_format", "reasoning"]}]}}})
    manifest = tmp_path / "manifest.json"
    put(manifest, {"schema": "dmb_context_tasting_v1", "models": ["fixture/model"],
        "source_request": request, "context_ready": ready, "endpoint_catalog": catalog})
    w.context_tasting(manifest, tmp_path / "output")
    assert json.loads((tmp_path / "output" / "cohort.json").read_text())["results"] == [{"label": "A", "status": "excluded"}]


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


def test_build_capture_preserves_page_thread_and_repeated_turns(tmp_path):
    request_template = template() | {
        "surface": {"surface_id": "build", "instance_id": "saved-page"},
        "primary_work": {"kind": "build", "object_id": "saved-page",
                         "expected_revision": 1, "expected_content_sha256": "a" * 64},
        "graph_request": {"mode": "world", "world_id": "world"},
        "client_work_state": "saved_clean",
        "build_authored_references": {"references": ["fixture"]},
    }

    class BuildClient(Client):
        conversation = "prev"
        turns = ()
        trace_status = 200

        def post(self, route, *, json):
            response = super().post(route, json=json)
            if route.endswith("/new"):
                self.conversation = "build-rehearsal"
                return self.response({"active_conversation_id": self.conversation})
            else:
                self.turn = str(uuid4())
                from apps.live_control_server.services.agent_turn_service import _turn_idempotency_key

                self.turns += ({"turn_id": self.turn, "user_text": json["message"],
                                "idempotency_key": str(_turn_idempotency_key("world", json["turn_id"])),
                                "lifecycle_status": "completed", "assistant_text": "Reply"},)
                return self.response({"turn_id": json["turn_id"],
                                      "client_thread_id": json["client_thread_id"],
                                      "answer": {"text": "Reply"}})
            return response

        def get(self, route, **kwargs):
            if "context-trace" in route:
                return self.response({"turn_id": self.turn, "world_id": "world"}, self.trace_status)
            return self.response({"pointer_revision": 3, "active_conversation_id": self.conversation,
                                  "turns": list(self.turns)})

    client = BuildClient("A repeated question")
    case = {"question": client.question, "gold_answer": "DO NOT SEND"}
    w.capture_case(client, "world", request_template, case, tmp_path / "first", build_thread_id="thread")
    w.capture_case(client, "world", request_template, case, tmp_path / "second",
                   build_thread_id="thread", expected_conversation_id=client.conversation)
    _, first, second = [body for _, body in client.posts]
    assert first["client_thread_id"] == second["client_thread_id"] == "thread"
    assert first["surface"] == second["surface"] == request_template["surface"]
    assert "build_authored_references" in first and "build_authored_references" not in second
    assert first["turn_id"] != second["turn_id"]
    assert "DO NOT SEND" not in json.dumps(client.posts)
    with pytest.raises(ValueError, match="conversation changed"):
        w.capture_case(client, "world", request_template, case, tmp_path / "drift",
                       build_thread_id="thread", expected_conversation_id="wrong")
    assert len(client.posts) == 3
    client.trace_status = 503
    with pytest.raises(ValueError, match="delivery or trace"):
        w.capture_case(client, "world", request_template, case, tmp_path / "trace-failure",
                       build_thread_id="thread", expected_conversation_id=client.conversation)
    assert json.loads((tmp_path / "trace-failure" / "context-trace.json").read_text())["http_status"] == 503



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

        def __enter__(self):
            return self

        def __exit__(self, *_):
            return False

        def execute(self, query):
            assert self.itersize == 1

        def __iter__(self):
            return iter(self.rows)

        def fetchall(self):
            assert not hasattr(self, "itersize"), "Do not buffer table bodies"
            return self.rows

    class Connection:
        def execute(self, query):
            if "information_schema.tables" in str(query):
                return Cursor([{"table_schema": "agent", "table_name": "turn"}])

        def cursor(self, *, name):
            assert name == "benchmark_inventory"
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
            if "transaction_read_only" in query:
                return SimpleNamespace(fetchone=lambda: ("on", True))
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


def test_capture_rejects_changed_editor_snapshot_before_startup(tmp_path, monkeypatch):
    monkeypatch.delenv("DMB_AGENT_GRAPH_LOCAL_PROFILE", raising=False)
    monkeypatch.setattr(w, "verify_runtime", lambda *args: None)
    snapshot = tmp_path / "editor.json"
    pin = put(snapshot, {"draft_markdown": "Saved text"})
    put(snapshot, {"draft_markdown": "Changed text"})
    manifest = tmp_path / "capture.json"
    put(manifest, {"schema": "dmb_ordinary_benchmark_v1", "world": "world",
        "cases": [{"id": "first", "question": "Discuss."}], "pins": [put(tmp_path / "runtime.json", {})],
        "runtime": {}, "conversation_mode": "build_sequence", "build_editor_snapshot": pin,
        "request_template": template() | {
            "surface": {"surface_id": "build", "instance_id": "page"},
            "primary_work": {"kind": "build", "object_id": "page",
                             "expected_revision": 1, "expected_content_sha256": "a" * 64},
            "graph_request": {"mode": "world", "world_id": "world"},
            "client_work_state": "saved_clean",
        }})
    output = tmp_path / "output"
    with pytest.raises(ValueError, match="(?i)pin|digest|sha256"):
        w.capture(manifest, output)
    assert not output.exists()


@pytest.fixture
def writer_replay(retained,monkeypatch):
    from application_state.agent_conversation.types import canonical_sha256
    root,case,source=retained
    request=json.loads((root/'request.json').read_text());request['surface']['surface_id']='plan';put(root/'request.json',request)
    trace=json.loads((root/'context-trace.json').read_text());attempt=trace['body']['attempts'][0];attempt['attempt']=1
    identity=attempt['observations'][0]['provider_attempt_id'];witness=attempt['observations'][-1]
    frame=dict(input_status='complete',user_question=case['question'],native_body_evidence={},native_statements={},native_assertions=None)
    packet=dict(model='fixed',instructions='Retained source instructions.',input=[dict(role='user',content=json.dumps(frame))],
        tools=[],stream=False,reasoning={'effort':'low'},service_tier='fast',text={'format':dict(
            type='json_schema',name='surface_native_evidence_selectors_v1',strict=True,
            schema={'type':'object','properties':{'answer':{'type':'string'}},'required':['answer'],'additionalProperties':False})})
    prompt=root/(witness['evidence_id']+'.json');prompt_pin=put(prompt,packet)
    witness.update(provider='openai',api_mode='responses',model='fixed',provider_attempt_id=identity,
        serializer_version='openai-sdk-json-v1',payload_sha256=prompt_pin['sha256'],payload_utf8_bytes=len(prompt.read_bytes()))
    attempt['observations'].insert(0,dict(attempt['observations'][0],outcome='authorized',input_tokens=None,output_tokens=None))
    put(root/'context-trace.json',trace)
    history=json.loads((root/'history-after.json').read_text())['body']
    receipt={'context_receipt_sha256':'c'*64}
    completion=dict(schema='synthetic_completion',producing_provider_attempt_id=identity,context_receipt_sha256='c'*64)
    history['turns'][0]['plan_context']=dict(completion=completion,receipt=receipt)
    put(root/'history-after.json',{'http_status':200,'body':history})
    answer=json.loads((root/'answer-http.json').read_text());answer['body']['plan_context']=deepcopy(history['turns'][0]['plan_context']);put(root/'answer-http.json',answer)
    ledger=dict(turn_id=history['turns'][0]['turn_id'],conversation_id=history['conversation_id'],status='completed',attempt=1,
        graph_context_receipt=receipt,graph_context_execution={'context_receipt_sha256':'c'*64,'events':[dict(kind='native_writer_authorized_v1',provider_attempt_id=identity,
            provider='openai',api_mode='responses',model='fixed',serializer_version='openai-sdk-json-v1',
            envelope_sha256=prompt_pin['sha256'],frame_sha256=canonical_sha256(frame)),
            dict(kind='completion_binding',provider_attempt_id=identity,completion_sha256=canonical_sha256(completion))]})
    ledger_path=root/'ledger.json';ledger_pin=put(ledger_path,ledger)
    spec=root/'replay.json';spec_doc=dict(schema='dmb_writer_replay_spec_v1',runtime={},source_manifest={
        'path':str(source),'sha256':sha256(source.read_bytes()).hexdigest()},cases=[dict(id=case['id'],
            question=case['question'],writer_attempt_id=identity,ledger=ledger_pin)])
    put(spec,spec_doc)
    monkeypatch.setattr(w,'verify_runtime',lambda *_:None)
    monkeypatch.setenv('OPENAI_API_KEY','test-key-not-real')
    return SimpleNamespace(root=root,spec=spec,document=spec_doc,packet=packet,ledger=ledger,
        ledger_path=ledger_path,trace=trace,identity=identity,source=source,case=case)


@pytest.mark.parametrize("matching_authorization", [True, False])
def test_writer_replay_accepts_only_matching_build_authorization(writer_replay, matching_authorization):
    replay = writer_replay
    request_path = replay.root / "request.json"
    request = json.loads(request_path.read_text())
    request["surface"]["surface_id"] = "build"
    put(request_path, request)
    for name in ("history-after", "answer-http"):
        path = replay.root / (name + ".json")
        wrapped = json.loads(path.read_text())
        owner = wrapped["body"]["turns"][0] if name == "history-after" else wrapped["body"]
        if name == "history-after":
            from apps.live_control_server.services.agent_turn_service import _turn_idempotency_key

            owner["idempotency_key"] = str(_turn_idempotency_key(
                wrapped["body"]["world_id"], request["turn_id"]))
        owner["knowledge_context"] = owner.pop("plan_context")
        put(path, wrapped)
    ledger = deepcopy(replay.ledger)
    if matching_authorization:
        ledger["graph_context_execution"]["events"][0]["kind"] = "native_build_writer_authorized_v2"
    case = replay.document["cases"][0] | {"ledger": put(replay.ledger_path, ledger)}
    summary = w.report_case(replay.case, replay.root)
    assert summary["delivery"]["status"] == "pass"
    if matching_authorization:
        packet, _, binding = w._writer_replay_request(case, replay.case, replay.root, summary, case_base=replay.root)
        assert packet == replay.packet
        assert binding["writer_attempt_id"] == replay.identity
    else:
        with pytest.raises(ValueError, match="different surface"):
            w._writer_replay_request(case, replay.case, replay.root, summary, case_base=replay.root)


def _writer_response(request,*,status='completed',text='{"answer":"Supported."}',refusal=False):
    import httpx
    return httpx.Response(200,request=request,json=dict(id='response-fixture',object='response',created_at=1,
        model='fixed',status=status,error=None,output=[dict(id='message-fixture',type='message',role='assistant',
            status='completed',content=[dict(type='refusal',refusal='Refused.') if refusal else
                dict(type='output_text',text=text,annotations=[])])],
        usage=dict(input_tokens=17,output_tokens=5,total_tokens=22)))


@pytest.mark.parametrize('format_version', [1, 2])
def test_writer_prepare_is_offline_and_override_only_changes_shared_instructions(writer_replay,tmp_path,monkeypatch,format_version):
    import psycopg
    r=writer_replay
    r.packet['text']['format']['name']=f'surface_native_evidence_selectors_v{format_version}'
    _repin_writer_packet(r,r.packet)
    monkeypatch.setattr(psycopg,'connect',lambda *a,**k:pytest.fail('Replay accessed database'))
    override=tmp_path/'instructions.txt';override.write_text('Shared alternative instructions, no new evidence.')
    r.document['instructions']={'path':str(override),'sha256':sha256(override.read_bytes()).hexdigest()};put(r.spec,r.document)
    plan=w.writer_prepare(r.spec,tmp_path/'prepared')
    assert json.loads(plan['cases'][0]['request_json'])==r.packet|{'instructions':override.read_text()}
    assert plan['cases'][0]['original_instructions_sha256']==sha256(r.packet['instructions'].encode()).hexdigest()
    assert plan['cases'][0]['prepared_wire']['size']>0
    assert 'not APP authorization' in plan['scope']
    assert not (tmp_path/'prepared/result.json').exists()


@pytest.mark.parametrize('mutation',['turn','attempt','envelope','frame','completion','completion_digest','receipt','ledger_attempt','witness','packet_field','tools','question','foreign_case','per_case_instructions'])
def test_writer_preflight_refuses_misbound_or_unsupported_case_before_dispatch(writer_replay,tmp_path,monkeypatch,mutation):
    r=writer_replay
    if mutation in {'turn','attempt','envelope','frame','completion','completion_digest','receipt','ledger_attempt'}:
        if mutation=='turn':r.ledger['turn_id']=str(uuid4())
        elif mutation=='completion':r.ledger['graph_context_execution']['events'][1]['provider_attempt_id']=str(uuid4())
        elif mutation=='completion_digest':r.ledger['graph_context_execution']['events'][1]['completion_sha256']='0'*64
        elif mutation=='receipt':r.ledger['graph_context_execution']['context_receipt_sha256']='0'*64
        elif mutation=='ledger_attempt':r.ledger['attempt']=2
        else:r.ledger['graph_context_execution']['events'][0][{'attempt':'provider_attempt_id','envelope':'envelope_sha256','frame':'frame_sha256'}[mutation]]='0'*64
        r.document['cases'][0]['ledger']=put(r.ledger_path,r.ledger)
    elif mutation=='witness':
        r.trace['body']['attempts'][0]['observations'][-1]['api_mode']='decision';put(r.root/'context-trace.json',r.trace)
    elif mutation in {'packet_field','tools'}:
        # Pins remain unchanged: changed source must be refused, never reinterpreted.
        path=next(r.root.glob('????????-????-????-????-????????????.json'))
        put(path,r.packet|({'temperature':0} if mutation=='packet_field' else {'tools':[{'type':'web_search'}]}))
    elif mutation=='question':r.document['cases'][0]['question']='Another question'
    elif mutation=='foreign_case':r.document['cases'][0]['id']='other'
    else:r.document['cases'][0]['instructions']='Question-specific rewrite'
    put(r.spec,r.document)
    with pytest.raises(ValueError):w.writer_prepare(r.spec,tmp_path/'prepared')
    assert not (tmp_path/'prepared').exists()


def test_writer_capture_uses_actual_sdk_gate_and_preserves_raw_diagnostic_only(writer_replay,tmp_path,monkeypatch):
    import httpx
    import psycopg
    monkeypatch.setattr(psycopg,'connect',lambda *a,**k:pytest.fail('Replay accessed database'))
    r=writer_replay;sent=[]
    def send(request):
        sent.append(request)
        assert str(request.url)=='https://api.openai.com/v1/responses'
        assert json.loads(request.content)==r.packet
        return _writer_response(request)
    w.writer_prepare(r.spec,tmp_path/'prepared')
    w.writer_capture(tmp_path/'prepared/plan.json',tmp_path/'capture',transport=httpx.MockTransport(send))
    assert len(sent)==1
    result=json.loads((tmp_path/'capture'/r.case['id']/'result.json').read_text())
    assert result['status']=='diagnostic_complete' and result['ordinary_delivery']=='not_exercised'
    assert result['semantic_acceptance']=='unknown' and result['billed_cost_usd'] is None
    wire=json.loads((tmp_path/'capture'/r.case['id']/'wire-request.json').read_text())
    assert wire['sha256']==sha256(sent[0].content).hexdigest()
    assert wire['provider_attempt_id']!=r.identity
    assert (tmp_path/'capture'/r.case['id']/'sdk-response.json').exists()
    with pytest.raises(FileExistsError):w.writer_capture(tmp_path/'prepared/plan.json',tmp_path/'capture',transport=httpx.MockTransport(send))
    assert len(sent)==1


def test_writer_paragraph_layout_changes_only_admitted_body_presentation(writer_replay, tmp_path):
    import httpx
    from application_state.agent_conversation.types import canonical_sha256

    replay = writer_replay
    body = "First café paragraph.\n\nSecond paragraph.\n"
    frame = json.loads(replay.packet["input"][0]["content"])
    frame["native_body_evidence"] = {"excerpts": [{"excerpt_handle": "body0", "text": body}]}
    replay.packet["input"][0]["content"] = json.dumps(frame)
    replay.ledger["graph_context_execution"]["events"][0]["frame_sha256"] = canonical_sha256(frame)
    _repin_writer_packet(replay, replay.packet)
    replay.document["body_layout"] = "paragraphs"
    put(replay.spec, replay.document)
    prepared = tmp_path / "prepared"
    plan = w.writer_prepare(replay.spec, prepared)
    candidate = json.loads(plan["cases"][0]["request_json"])
    candidate_frame = json.loads(candidate["input"][0]["content"])
    excerpt = candidate_frame["native_body_evidence"]["excerpts"][0]
    assert excerpt["text"] == ["First café paragraph.\n\n", "Second paragraph.\n"]
    excerpt["text"] = "".join(excerpt["text"])
    assert candidate_frame == frame
    assert candidate | {"input": replay.packet["input"]} == replay.packet

    def send(request):
        assert json.loads(request.content) == candidate
        return _writer_response(request)

    w.writer_capture(prepared / "plan.json", tmp_path / "capture", transport=httpx.MockTransport(send))


@pytest.mark.parametrize("layout,instructions", [("unknown", None), ("paragraphs", {})])
def test_writer_rejects_unrecognized_or_combined_paragraph_layout(writer_replay, tmp_path, layout, instructions):
    replay = writer_replay
    replay.document.update(body_layout=layout, instructions=instructions)
    put(replay.spec, replay.document)
    with pytest.raises(ValueError, match="only replay change"):
        w.writer_prepare(replay.spec, tmp_path / "prepared")


@pytest.mark.parametrize('status,text,refusal',[('incomplete','{"answer":"Partial"}',False),
    ('completed','{',False),('completed','{"wrong":1}',False),('completed','',True)])
def test_writer_capture_retains_actual_incomplete_invalid_or_refused_reply(writer_replay,tmp_path,status,text,refusal):
    import httpx
    r=writer_replay;sent=[]
    def send(request):
        sent.append(request);return _writer_response(request,status=status,text=text,refusal=refusal)
    w.writer_prepare(r.spec,tmp_path/'prepared')
    with pytest.raises(Exception):w.writer_capture(tmp_path/'prepared/plan.json',tmp_path/'capture',transport=httpx.MockTransport(send))
    target=tmp_path/'capture'/r.case['id']
    assert len(sent)==1 and (target/'sdk-response.json').exists() and (target/'failure.json').exists()
    assert not (target/'result.json').exists()


def test_writer_unknown_outcome_is_not_retried_or_resumed(writer_replay,tmp_path):
    import httpx
    r=writer_replay;sent=[]
    def send(request):
        sent.append(request);raise httpx.ReadError('Synthetic response loss',request=request)
    w.writer_prepare(r.spec,tmp_path/'prepared')
    with pytest.raises(Exception):w.writer_capture(tmp_path/'prepared/plan.json',tmp_path/'capture',transport=httpx.MockTransport(send))
    target=tmp_path/'capture'/r.case['id'];failure=json.loads((target/'failure.json').read_text())
    assert failure['dispatch_outcomes']==['sending','outcome_unknown'] and failure['automatic_resume'] is False
    assert len(sent)==1 and not (target/'sdk-response.json').exists()
    with pytest.raises(FileExistsError):w.writer_capture(tmp_path/'prepared/plan.json',tmp_path/'capture',transport=httpx.MockTransport(send))
    assert len(sent)==1


def test_writer_plan_tampering_and_late_case_failure_never_send(writer_replay,tmp_path):
    import httpx
    r=writer_replay;sent=[];transport=httpx.MockTransport(lambda q:sent.append(q) or _writer_response(q))
    w.writer_prepare(r.spec,tmp_path/'prepared')
    plan_path=tmp_path/'prepared/plan.json';plan=json.loads(plan_path.read_text());packet=json.loads(plan['cases'][0]['request_json']);packet['model']='another';plan['cases'][0]['request_json']=json.dumps(packet)
    put(plan_path,plan)
    with pytest.raises(ValueError,match='plan changed'):w.writer_capture(plan_path,tmp_path/'capture',transport=transport)
    r.document['cases'].append(dict(r.document['cases'][0],id='late-invalid'))
    put(r.spec,r.document)
    with pytest.raises(ValueError):w.writer_prepare(r.spec,tmp_path/'other')
    assert not sent and not (tmp_path/'capture').exists()


@pytest.mark.parametrize('change',['model','body','endpoint'])
def test_writer_offline_sdk_preparation_refuses_changed_actual_dispatch(writer_replay,tmp_path,monkeypatch,change):
    from apps.live_control_server.services.plan_jev_writer import PlanWriterProvider
    if change=='endpoint':
        real=PlanWriterProvider.__init__
        def altered(self,*a,**kw):
            real(self,*a,**kw);self._client.base_url='https://example.invalid/v1'
        monkeypatch.setattr(PlanWriterProvider,'__init__',altered)
    else:
        real=PlanWriterProvider._request_kwargs
        def altered(self,*a,**kw):
            body=real(self,*a,**kw);body['model' if change=='model' else 'instructions']='Changed';return body
        monkeypatch.setattr(PlanWriterProvider,'_request_kwargs',altered)
    with pytest.raises(ValueError,match='Offline SDK preparation failed'):
        w.writer_prepare(writer_replay.spec,tmp_path/'prepared')


def _repin_writer_packet(r,packet):
    witness=r.trace['body']['attempts'][0]['observations'][-1]
    pin=put(r.root/(witness['evidence_id']+'.json'),packet)
    witness.update(payload_sha256=pin['sha256'],payload_utf8_bytes=len((r.root/(witness['evidence_id']+'.json')).read_bytes()))
    put(r.root/'context-trace.json',r.trace)
    r.ledger['graph_context_execution']['events'][0]['envelope_sha256']=pin['sha256']
    r.document['cases'][0]['ledger']=put(r.ledger_path,r.ledger);put(r.spec,r.document)


@pytest.mark.parametrize('mutation',['extra','tools','stream','tier','schema_name','schema_ref','schema_id','schema_dynamic_ref'])
def test_writer_rejects_rebound_unsupported_packet_not_just_bad_pin(writer_replay,tmp_path,mutation):
    r=writer_replay;packet=deepcopy(r.packet)
    if mutation=='extra':packet['temperature']=0
    elif mutation=='tools':packet['tools']=[{'type':'web_search'}]
    elif mutation=='stream':packet['stream']=True
    elif mutation=='tier':packet['service_tier']='auto'
    elif mutation=='schema_name':packet['text']['format']['name']='surface_native_evidence_selectors_v3'
    else:
        packet['text']['format']['schema'][{'schema_ref':'$ref','schema_id':'$id','schema_dynamic_ref':'$dynamicRef'}[mutation]]='https://example.invalid/schema'
    _repin_writer_packet(r,packet)
    with pytest.raises(ValueError):w.writer_prepare(r.spec,tmp_path/'prepared')
    assert not (tmp_path/'prepared').exists()


def _second_writer_case(r):
    source=json.loads(r.source.read_text());source['cases'].append(dict(r.case,id='second'))
    r.document['source_manifest']=put(r.source,source)
    ledger=r.root/'second-ledger.json'
    r.document['cases'].append(dict(r.document['cases'][0],id='second',ledger=put(ledger,r.ledger)))
    put(r.spec,r.document)
    return ledger


def test_late_invalid_pinned_case_blocks_all_paid_dispatch(writer_replay,tmp_path):
    import httpx
    r=writer_replay;ledger=_second_writer_case(r);sent=[]
    w.writer_prepare(r.spec,tmp_path/'prepared')
    put(ledger,{'changed':'after preparation'})
    with pytest.raises(ValueError,match='pin mismatch'):
        w.writer_capture(tmp_path/'prepared/plan.json',tmp_path/'capture',transport=httpx.MockTransport(lambda req:sent.append(req)))
    assert not sent and not (tmp_path/'capture').exists()


def test_known_failure_records_cohort_stop_and_unattempted_cases(writer_replay,tmp_path):
    import httpx
    r=writer_replay;_second_writer_case(r);sent=[]
    w.writer_prepare(r.spec,tmp_path/'prepared')
    def send(req):
        sent.append(req);return _writer_response(req,text='{"wrong":1}')
    with pytest.raises(Exception):w.writer_capture(tmp_path/'prepared/plan.json',tmp_path/'capture',transport=httpx.MockTransport(send))
    cohort=json.loads((tmp_path/'capture/cohort.json').read_text())
    assert len(sent)==1 and cohort['failed_case']==r.case['id'] and cohort['unattempted_cases']==['second']
    assert cohort['automatic_resume'] is False and not (tmp_path/'capture/second').exists()


def test_interrupted_writer_retains_unknown_and_cannot_resume(writer_replay,tmp_path):
    import asyncio
    import httpx
    r=writer_replay;sent=[]
    w.writer_prepare(r.spec,tmp_path/'prepared')
    def send(req):
        sent.append(req);raise asyncio.CancelledError()
    with pytest.raises(asyncio.CancelledError):
        w.writer_capture(tmp_path/'prepared/plan.json',tmp_path/'capture',transport=httpx.MockTransport(send))
    failure=json.loads((tmp_path/'capture'/r.case['id']/'failure.json').read_text())
    assert failure['exception_type']=='CancelledError' and failure['dispatch_outcomes']==['sending','outcome_unknown']
    assert len(sent)==1 and json.loads((tmp_path/'capture/cohort.json').read_text())['status']=='stopped'
    with pytest.raises(FileExistsError):w.writer_capture(tmp_path/'prepared/plan.json',tmp_path/'capture',transport=httpx.MockTransport(send))
    assert len(sent)==1


def test_replay_spec_rejects_duplicate_json_fields(writer_replay,tmp_path):
    r=writer_replay
    r.spec.write_text(r.spec.read_text().replace('"runtime": {}','"runtime": {},"runtime": {}'))
    with pytest.raises(ValueError):w.writer_prepare(r.spec,tmp_path/'prepared')


def test_historical_world_envelope_is_readable_but_never_paid_replayed(writer_replay, tmp_path):
    import httpx
    from application_state.agent_conversation.types import canonical_sha256
    r = writer_replay
    frame = json.loads(r.packet['input'][0]['content'])
    frame['native_assertions'] = {'assertions': [{'assertion': {'metadata': {
        'domain_metadata': [{'schema': 'dungeonbuddy.domain_metadata:world_context_v1',
            'payload': {'source_qualification': 'Reported speech, not an observed fact.'}}]}}}]}
    r.packet['input'][0]['content'] = json.dumps(frame)
    witness = r.trace['body']['attempts'][0]['observations'][-1]
    prompt = r.root / (witness['evidence_id'] + '.json')
    packet_pin = put(prompt, r.packet)
    witness.update(payload_sha256=packet_pin['sha256'], payload_utf8_bytes=len(prompt.read_bytes()))
    put(r.root / 'context-trace.json', r.trace)
    r.ledger['graph_context_execution']['events'][0].update(
        envelope_sha256=packet_pin['sha256'], frame_sha256=canonical_sha256(frame))
    r.document['cases'][0]['ledger'] = put(r.ledger_path, r.ledger)
    put(r.spec, r.document)
    plan = w.writer_prepare(r.spec, tmp_path / 'prepared')
    assert json.loads(plan['cases'][0]['request_json']) == r.packet
    with pytest.raises(ValueError, match='Historical World host envelope'):
        w.writer_capture(tmp_path / 'prepared/plan.json', tmp_path / 'capture',
            transport=httpx.MockTransport(lambda _: pytest.fail('Historical prompt was dispatched')))
    cohort = json.loads((tmp_path / 'capture/cohort.json').read_text())
    assert cohort['status'] == 'stopped' and not cohort['automatic_resume']
    assert not (tmp_path / 'capture' / r.case['id'] / 'wire-request.json').exists()


def test_context_capture_cli_is_explicit_and_does_not_select_a_response_mode(monkeypatch):
    calls = []
    monkeypatch.setattr(w, 'capture', lambda *a, **kw: calls.append((a, kw)))
    w.main(['capture-context', '--manifest', 'pinned.json', '--output', 'isolated'])
    assert calls == [(('pinned.json', 'isolated'), {'context_only': True, 'writer_transport': False, 'detailed_trace': False})]
    w.main(['capture-context', '--manifest', 'pinned.json', '--output', 'isolated', '--writer-transport'])
    assert calls[-1] == (('pinned.json', 'isolated'), {'context_only': True, 'writer_transport': True, 'detailed_trace': False})


@pytest.mark.parametrize('policy', ['absent', None, {}, {'policy': 'auto_plan_world'}, {
    'schema': 'dmb_plan_context_policy_v2', 'policy': 'auto_plan_world', 'graph_source': 'legacy_graph'}])
def test_context_capture_rejects_routes_outside_its_guard_before_dispatch(tmp_path, policy):
    client = Client('Explain the route.')
    candidate = template()
    if policy != 'absent':
        candidate['plan_context_policy'] = policy
    with pytest.raises(ValueError, match='explicit shared native Plan route'):
        w.capture_case(client, 'world', candidate, {'question': client.question}, tmp_path, context_only=True)
    assert not client.posts and not list(tmp_path.iterdir())


def test_context_capture_accepts_only_the_supported_native_policy():
    w.validate_template(template() | {'plan_context_policy': {
        'schema': 'dmb_plan_context_policy_v2', 'policy': 'auto_plan_world',
        'graph_source': 'reviewed_native_graph'}}, 'world', context_only=True)


def test_context_report_does_not_relabel_old_response_as_context_success(retained):
    _, case, _ = retained
    result = w.report_case(case | {'capture_boundary': 'context_ready'}, Path('.'))
    assert result['capture_status'] == 'not_started'
    assert result['delivery']['status'] == 'not_requested'
    assert 'context-ready' in result['missing_artifacts']


def test_context_network_guard_is_below_sdk_preparation_and_restored(tmp_path, monkeypatch):
    import asyncio
    import httpx
    from apps.live_control_server.services.plan_jev_writer import PlanJevWriter
    from evals.buddy_benchmark.context_capture import ContextCapture, WriterIODenied
    sent = []
    async def direct_run(writer, *, transport=None, api_key=None):
        return await transport.handle_async_request(httpx.Request('POST', 'https://api.openai.com/v1/responses'))
    monkeypatch.setattr(PlanJevWriter, 'run', direct_run)
    original = PlanJevWriter.authorize
    stop = ContextCapture(tmp_path)
    supplied = httpx.MockTransport(lambda request: sent.append(request))
    with stop.install(), pytest.raises(WriterIODenied):
        asyncio.run(PlanJevWriter.run(SimpleNamespace(), transport=supplied))
    assert stop.guard_hits == 1 and not sent and not stop.stop_issued
    assert PlanJevWriter.run is direct_run and PlanJevWriter.authorize is original


def test_transport_capture_intercepts_exact_bytes_and_never_delegates(tmp_path, monkeypatch):
    import asyncio
    import httpx
    from apps.live_control_server.services.plan_jev_writer import PlanJevWriter
    from evals.buddy_benchmark.context_capture import ContextCapture, ContextReadyStop

    url = 'https://api.openai.com/v1/responses'
    body = b'{"input":"exact bytes"}'
    async def direct_run(writer, *, transport=None, api_key=None):
        await transport.handle_async_request(httpx.Request('POST', url, content=body))

    monkeypatch.setattr(PlanJevWriter, 'run', direct_run)
    stop = ContextCapture(tmp_path, writer_transport=True)
    stop.request = {'body_hex': body.hex()}
    delegated = []
    supplied = httpx.MockTransport(lambda request: delegated.append(request))
    with stop.install(), pytest.raises(ContextReadyStop):
        asyncio.run(PlanJevWriter.run(SimpleNamespace(), transport=supplied))
    assert stop.guard_hits == 1 and stop.stop_issued and not delegated
    assert stop.transport_sink['url'] == url
    assert stop.transport_sink['body_hex'] == body.hex()
    assert not list(tmp_path.iterdir())


@pytest.mark.parametrize('failure', [False, ValueError('rejected input')])
def test_failed_context_authorization_cannot_emit_a_ready_packet(tmp_path, monkeypatch, failure):
    from apps.live_control_server.services.plan_jev_writer import PlanJevWriter
    from evals.buddy_benchmark.context_capture import ContextCapture
    def reject(writer, prepared):
        if isinstance(failure, Exception):
            raise failure
        return failure
    monkeypatch.setattr(PlanJevWriter, 'authorize', reject)
    stop = ContextCapture(tmp_path)
    with stop.install():
        if failure is False:
            assert PlanJevWriter.authorize(SimpleNamespace(shared=True), object()) is False
        else:
            with pytest.raises(ValueError, match='rejected input'):
                PlanJevWriter.authorize(SimpleNamespace(shared=True), object())
    assert not stop.stop_issued and not list(tmp_path.iterdir())


def test_context_artifact_failure_cannot_be_reported_as_a_success(tmp_path, monkeypatch):
    from datetime import datetime, timezone
    from apps.live_control_server.services.plan_jev_writer import PlanJevWriter
    from evals.buddy_benchmark import context_capture as cc
    prepared = SimpleNamespace(provider='openai', model='test', api_mode='responses',
        method='POST', url='https://api.openai.com/v1/responses', body=b'{}',
        body_size=2, body_sha256=sha256(b'{}').hexdigest())
    turn = SimpleNamespace(world_id='world', conversation_id=uuid4(), turn_id=uuid4(), attempt=1,
        accepted_at=datetime.now(timezone.utc), graph_context_receipt=SimpleNamespace(
            context_receipt_sha256='a'*64, work_context=SimpleNamespace(surface_id='plan')))
    event = SimpleNamespace(event_id=uuid4(), provider_attempt_id=uuid4(), frame_sha256='b'*64)
    writer = SimpleNamespace(shared=True, prepared=prepared, authorization=event, adapter=SimpleNamespace(turn=turn))
    monkeypatch.setattr(PlanJevWriter, 'authorize', lambda *a: True)
    def fail_write(*a):
        raise OSError('capture storage unavailable')
    monkeypatch.setattr(cc, 'immutable_save', fail_write)
    stop = cc.ContextCapture(tmp_path)
    with stop.install(), pytest.raises(cc.ContextReadyStop):
        PlanJevWriter.authorize(writer, prepared)
    assert stop.authorization_calls == 1 and stop.stop_issued and not list(tmp_path.iterdir())
    turn.model_dump = lambda **kwargs: {}
    with pytest.raises(OSError, match='storage unavailable'):
        stop.finalize(turn)
    assert not list(tmp_path.iterdir())


def _native_order_schema():
    return {'type': 'object', 'properties': {
        'kind': {'type': 'string', 'const': 'native_assertion_claim'},
        'text': {'type': 'string'},
        'assertion_handles': {'type': 'array', 'items': {'type': 'string', 'enum': ['assertion0']}, 'minItems': 1}},
        'required': ['kind', 'text', 'assertion_handles'], 'additionalProperties': False}


def test_citation_first_changes_only_property_order():
    from copy import deepcopy
    original = _native_order_schema()
    before = deepcopy(original)
    changed = w.citation_first_schema(original)
    assert changed == before and original == before
    assert list(original['properties']) == ['kind', 'text', 'assertion_handles']
    assert list(changed['properties']) == ['kind', 'assertion_handles', 'text']
    assert changed['required'] == before['required']
    with pytest.raises(ValueError, match='native claim'):
        w.citation_first_schema({'type': 'object', 'properties': {}})


@pytest.mark.parametrize('lose_order', [False, True])
def test_context_tasting_checks_actual_wire_before_http(tmp_path, monkeypatch, lose_order):
    import httpx
    from application_state.agent_conversation import native_evidence_view, types
    frame = {'user_question': 'A generic question'}
    monkeypatch.setattr(native_evidence_view, 'semantic_frame_in_request', lambda *a, **k: frame)
    packet = {'tools': [], 'instructions': 'Frozen voice', 'input': [{'role': 'user', 'content': 'Frozen evidence'}],
        'text': {'format': {'schema': _native_order_schema(), 'name': 'answer'}}, 'reasoning': {'effort': 'low'}}
    raw = json.dumps(packet).encode()
    source = put(tmp_path/'source.json', {'body_hex': raw.hex(), 'body_sha256': sha256(raw).hexdigest(), 'body_size': len(raw)})
    ready = put(tmp_path/'ready.json', {'frame_sha256': types.canonical_sha256(frame)})
    manifest = tmp_path/'manifest.json'
    put(manifest, {'schema': 'dmb_context_tasting_v1', 'source_request': source, 'context_ready': ready,
        'models': ['test/model'], 'schema_order': 'citation_first'})
    if lose_order:
        monkeypatch.setattr(w, 'citation_first_schema', lambda schema: schema)
    seen = []
    def reply(request):
        body = json.loads(request.content)
        seen.append(body)
        output = {'kind': 'native_assertion_claim', 'assertion_handles': ['assertion0'], 'text': 'Supported.'}
        return httpx.Response(200, json={'id': 'offline', 'object': 'chat.completion', 'created': 1,
            'model': body['model'], 'choices': [{'index': 0, 'message': {'role': 'assistant',
            'content': json.dumps(output)}, 'finish_reason': 'stop'}],
            'usage': {'prompt_tokens': 10, 'completion_tokens': 5, 'total_tokens': 15}})
    target = tmp_path/'out'
    w.context_tasting(manifest, target, transport=httpx.MockTransport(reply))
    if lose_order:
        assert not seen
        assert (target/'A/failure.json').exists()
        assert not (target/'A/provider-wire-1.json').exists()
    else:
        assert len(seen) == 1
        proof = json.loads((target/'A/provider-wire-1.json').read_text())
        assert proof['citation_first_verified']
        assert proof['body_sha256'] == sha256(bytes.fromhex(proof['body_hex'])).hexdigest()
        assert proof['claim_property_orders'][0]['fields'] == ['kind', 'assertion_handles', 'text']
        assert seen[0]['messages'] == [{'role': 'system', 'content': 'Frozen voice'},
            {'role': 'user', 'content': 'Frozen evidence'}]
        assert (target/'A/result.json').exists()


def test_trace_report_counts_overlapping_spans_once(tmp_path, monkeypatch):
    from evals.buddy_benchmark import trace_report

    case = tmp_path / "example"
    case.mkdir()
    for name in ("context-ready", "context-request", "context-stop"):
        immutable_save(case, name, {})
    immutable_save(case, "detailed-host-trace", {
        "trace_id": "trace", "start_monotonic_ns": 1_000_000, "end_monotonic_ns": 31_000_000,
        "truncated": False, "intervals": [
            {"name": name, "start_monotonic_ns": start * 1_000_000,
             "end_monotonic_ns": end * 1_000_000}
            for name, start, end in (("runtime_dispatch", 1, 31),
                                     ("read", 1, 11), ("bind <evidence>", 6, 21), ("dispatch_point", 16, 16))
        ],
    })
    monkeypatch.setattr(trace_report, "validate_context_packet", lambda *args: {
        "turn": SimpleNamespace(world_id="world", user_text="Question"),
        "request_to_ready_ms": 30,
    })
    monkeypatch.setattr(trace_report, "summarize_host_trace", lambda *args: None)
    report = trace_report.build(tmp_path, "example", world="world", question="Question")
    assert report["allocated_ms"] == {
        "read": 5, "bind <evidence> / read": 5, "bind <evidence>": 10, "Unattributed": 10,
    }
    assert report["observed_duration_percent"] == pytest.approx(200 / 3)
    operations = {row["name"]: row for row in report["operations"]}
    assert operations["read"] == {"name": "read", "calls": 1, "markers": 0, "inclusive_ms": 10,
                                  "max_call_ms": 10, "exclusive_ms": 5, "wrapper_excluded": False}
    assert operations["dispatch_point"]["calls"] == 0
    assert operations["dispatch_point"]["markers"] == 1
    assert operations["runtime_dispatch"]["wrapper_excluded"] is True
    assert operations["runtime_dispatch"]["exclusive_ms"] == 0
    assert report["start_boundary"] == "request_start"
    assert report["end_boundary"] == "writer_ready"
    rendered = trace_report.render(report)
    assert "&lt;evidence&gt;" in rendered
    assert "Question" not in rendered
    with pytest.raises(ValueError, match="differs from the manifest case"):
        trace_report.build(tmp_path, "example", world="elsewhere", question="Question")


def test_trace_report_binds_browser_clock_to_durable_turn(tmp_path, monkeypatch):
    from apps.live_control_server.services.agent_turn_service import _turn_idempotency_key
    from evals.buddy_benchmark import trace_report

    case = tmp_path / "example"
    case.mkdir()
    request = {"owner_scope": {"world_id": "world"}, "message": "Question", "turn_id": "browser-turn"}
    for name in ("context-ready", "context-request", "context-stop"):
        immutable_save(case, name, {})
    immutable_save(case, "request", request)
    immutable_save(case, "detailed-host-trace", {"trace_id": "trace", "truncated": False,
        "start_monotonic_ns": 3_000_000, "end_monotonic_ns": 5_000_000, "intervals": []})
    turn = SimpleNamespace(world_id="world", user_text="Question",
                           idempotency_key=_turn_idempotency_key("world", "other-turn"))
    monkeypatch.setattr(trace_report, "validate_context_packet", lambda *args: {
        "turn": turn, "request_to_ready_ms": 2,
    })
    monkeypatch.setattr(trace_report, "summarize_host_trace", lambda *args: None)
    immutable_save(tmp_path, "browser-timing", {"request": request, "before": [[0, 0]], "after": [[0, 0]],
        "browserMarks": {"click": 1, "request": 2, "preflight": [{"start": 0, "end": 2, "phase": "invalid"}]}})
    with pytest.raises(ValueError, match="different durable case request"):
        trace_report.build(tmp_path, "example", world="world", question="Question")
    turn.idempotency_key = _turn_idempotency_key("world", "browser-turn")
    with pytest.raises(ValueError, match="outside Send preparation"):
        trace_report.build(tmp_path, "example", world="world", question="Question")


def test_context_capture_selects_browser_case_only_at_writer_sink(monkeypatch):
    calls = []
    monkeypatch.setattr(w, "capture", lambda *args, **kwargs: calls.append((args, kwargs)))
    argv = ["capture-context", "--manifest", "pinned.json", "--output", "isolated", "--case", "D05"]
    with pytest.raises(SystemExit):
        w.main(argv)
    assert not calls
    w.main(argv + ["--writer-transport"])
    assert calls == [(("pinned.json", "isolated"), {
        "context_only": True, "writer_transport": True, "detailed_trace": False, "browser_case": "D05",
    })]


def test_browser_inputs_rejects_bundle_drift_before_replay(tmp_path):
    from evals.buddy_benchmark.browser_capture import browser_inputs

    bundle = tmp_path / "bundle"
    bundle.mkdir()
    index = bundle / "index.html"
    index.write_text("Pinned UI")
    inventory = tmp_path / "bundle.json"
    inventory.write_text(json.dumps({"index.html": sha256(index.read_bytes()).hexdigest()}))
    tape = tmp_path / "wire.json"
    tape.write_text(json.dumps([{"method": "POST", "response_status": 200,
                                "request_hex": "7b7d", "response_hex": "7b7d"}]))
    def pin(path):
        return {"path": path.name, "sha256": sha256(path.read_bytes()).hexdigest()}
    manifest = {"browser_capture": {"bundle": bundle.name, "bundle_inventory": pin(inventory),
                                    "jev_wire": pin(tape)}}
    assert browser_inputs(manifest, tmp_path)[0] == bundle
    index.write_text("Changed UI")
    with pytest.raises(ValueError, match="bundle differs"):
        browser_inputs(manifest, tmp_path)


def test_unsent_draft_browser_requires_provider_free_build_fixture(tmp_path):
    from evals.buddy_benchmark.browser_capture import browser_inputs

    bundle = tmp_path / "bundle"
    bundle.mkdir()
    index = bundle / "index.html"
    index.write_text("Pinned UI")
    inventory = tmp_path / "bundle.json"
    inventory.write_text(json.dumps({"index.html": sha256(index.read_bytes()).hexdigest()}))
    manifest = {"browser_capture": {"bundle": bundle.name, "unsent_draft": True,
        "bundle_inventory": {"path": inventory.name, "sha256": sha256(inventory.read_bytes()).hexdigest()}}}
    assert browser_inputs(manifest, tmp_path, build_fixture=True)[1] == []
    with pytest.raises(ValueError, match="Unsent draft requires a Build browser fixture"):
        browser_inputs(manifest, tmp_path, live_plan=True)

@pytest.mark.parametrize("browser, clone_app, context_only, sequence_stopped, mixed", [
    (False, False, True, False, False), (True, False, True, False, False),
    (True, True, True, False, False), (False, True, False, False, False),
    (False, True, False, True, False), (False, True, False, False, True),
])
@pytest.mark.parametrize("changed, missing_capture", [(False, False), (True, False), (False, True)])
def test_cohort_inventory_brackets_members(tmp_path, monkeypatch, changed, missing_capture,
                                          browser, clone_app, context_only, sequence_stopped, mixed):
    from concurrent.futures import Future
    from evals.buddy_benchmark.workflow import BuildSequenceStopped
    from evals.buddy_benchmark import cohort_capture as cohort

    before = {"dungeonmind.fixture": []}
    pin = put(tmp_path / "native.json", before)
    native = dict(host="127.0.0.1", port=53421, database="native", oid="10",
                  system_identifier="42", inventory=pin)
    members = []
    for number in [1, 2]:
        app = dict(native, database="app", oid="1") if clone_app else dict(
            native, database=f"app{number}", oid=str(number))
        members.append(put(tmp_path / f"member{number}.json", {
            "schema": "dmb_ordinary_benchmark_v1",
            "cases": [{"id": f"case{number}", "question": f"Question {number}?"}] + (
                [{"id": "case1-followup", "question": "Continue?"}]
                if sequence_stopped and number == 1 and not missing_capture else []),
            "isolation": {"native": native, "app": app},
            **({"browser_capture": {}} if browser or (mixed and number == 2) else {}),
        }))
    if mixed:
        members[1]["driver"] = "live_build"
    protected = "00000000-0000-4000-8000-000000000001"
    manifest = put(tmp_path / "cohort.json", {
        "protected_work_objects": [protected],
        "schema": "dmb_context_capture_cohort_v1", "members": members,
    })
    monkeypatch.setenv(cohort.APP_DSN, "postgresql://127.0.0.1:53421/app")
    monkeypatch.setenv(cohort.CORE_DSN, "postgresql://127.0.0.1:53421/native")
    monkeypatch.setattr(cohort, "_endpoint", lambda *_: None)
    monkeypatch.setattr(cohort, "require_read_only_core", lambda *_: None)

    events = []
    def fixture_revisions(dsn, object_ids):
        assert dsn.endswith("/benchmark_run_owned")
        assert object_ids == [protected]
        return {protected: "changed" if changed and "case1" in events else "initial"}
    monkeypatch.setattr(cohort, "protected_work_revisions", fixture_revisions)
    from contextlib import contextmanager
    from application_state import cli
    from evals.buddy_benchmark import disposable_database

    owned_app = {**app, "database": "benchmark_run_owned", "oid": "25"}

    @contextmanager
    def own(admin_dsn, template):
        assert admin_dsn.endswith("/postgres")
        assert template == app
        events.append("clone")
        try:
            yield owned_app
        finally:
            events.append("drop")

    def upgrade():
        assert clone_app
        assert cohort.os.environ[cohort.APP_DSN].endswith("/benchmark_run_owned")
        events.append("upgrade")

    monkeypatch.setattr(disposable_database, "disposable_benchmark_database", own)
    monkeypatch.setattr(cli, "upgrade_to_head", upgrade)

    def inventory(*_, **__):
        events.append("scan")
        return {} if changed and events.count("scan") == 2 else before

    interrupted_member = None

    class InterruptedFuture(Future):
        def exception(self, timeout=None):
            raise KeyboardInterrupt

    class Executor:
        def __init__(self, **options):
            assert options["max_workers"] == (1 if clone_app else 2)
            assert options["max_tasks_per_child"] == 1

        def __enter__(self):
            return self

        def __exit__(self, *_):
            if clone_app:
                events.append("workers closed")
            return False

        def submit(self, member, manifest, output, app_dsn, manifest_sha256, **options):
            assert options.pop("context_only") is context_only
            if clone_app:
                assert options.pop("shared_app") == owned_app
                assert app_dsn.endswith("/benchmark_run_owned")
            if mixed and output.name == "case2":
                assert options == {"browser_case": "case2", "detailed_trace": False, "driver": "live_build"}
            else:
                assert options == ({"browser_case": output.name, "detailed_trace": True} if browser else {})
            assert member is cohort._capture_member
            assert sha256(manifest.read_bytes()).hexdigest() == manifest_sha256
            events.append(output.name)
            row = {"case_id": output.name}
            if not (missing_capture and output.name == ("case2" if context_only else "case1")):
                row["context"] = {"status": "captured"}
                row["capture_status"] = "complete"
                row["delivery"] = {"status": "fail" if output.name == "case2" else "pass"}
                if mixed and output.name == "case2":
                    del row["capture_status"]
                    row["capture_boundary"] = "image_preview"
            else:
                row["capture_status"] = "incomplete"
            f = InterruptedFuture() if output.name == interrupted_member else Future()
            if sequence_stopped and output.name == "case1" and not missing_capture:
                row["delivery"]["status"] = "fail"
                immutable_save(output, "report", {"cases": [
                    row, {"case_id": "case1-followup", "capture_status": "not_started"},
                ]})
                f.set_exception(BuildSequenceStopped("Retained failure"))
            else:
                immutable_save(output, "report", {"cases": [row]})
                f.set_result(None)
            return f

    monkeypatch.setattr(cohort, "row_inventory", inventory)
    monkeypatch.setattr(cohort, "ProcessPoolExecutor", Executor)
    out = tmp_path / "result"
    if changed:
        with pytest.raises(ValueError, match="changed during cohort"):
            cohort.capture_cohort(manifest["path"], out, workers=1 if clone_app else 2, browser=browser,
                                  detailed_trace=browser, clone_app=clone_app, context_only=context_only)
    elif missing_capture:
        with pytest.raises(RuntimeError, match="cohort members failed"):
            cohort.capture_cohort(manifest["path"], out, workers=1 if clone_app else 2, browser=browser,
                                  detailed_trace=browser, clone_app=clone_app, context_only=context_only)
        outcomes = json.loads((out / "members.json").read_text())
        if context_only:
            assert outcomes["case2"] == {"status": "failed", "case_statuses": {"case2": "missing"}}
        else:
            assert outcomes["case1"] == {"status": "failed", "case_statuses": {"case1": "incomplete"}}
            assert outcomes["case2"] == {"status": "not_started"}
    else:
        cohort.capture_cohort(manifest["path"], out, workers=1 if clone_app else 2, browser=browser,
                                  detailed_trace=browser, clone_app=clone_app, context_only=context_only)
    if clone_app:
        expected_cases = ["case1"] if (missing_capture or changed) and not context_only else ["case1", "case2"]
        if changed and not context_only:
            outcomes = json.loads((out / "members.json").read_text())
            assert outcomes["case1"]["status"] == "fixture_changed"
            assert outcomes["case2"]["status"] == "not_started"
        assert events == ["scan", "clone", "upgrade", *expected_cases, "workers closed", "drop", "scan"]
        assert json.loads((out / "owned-app.json").read_text())["database"] == owned_app
    else:
        assert events == ["scan", "case1", "case2", "scan"]

    if mixed and not changed and not missing_capture:
        for interrupted_member, started in (("case1", ["case1"]), ("case2", ["case1", "case2"])):
            events.clear()
            interrupted_out = tmp_path / f"interrupted-{interrupted_member}"
            with pytest.raises(KeyboardInterrupt):
                cohort.capture_cohort(manifest["path"], interrupted_out, workers=1, clone_app=True,
                                      context_only=False)
            summary = json.loads((interrupted_out / "members.json").read_text())
            assert summary[interrupted_member] == {"status": "interrupted"}
            if interrupted_member == "case1":
                assert summary["case2"] == {"status": "not_started"}
            else:
                assert summary["case1"]["status"] == "completed"
            assert events == ["scan", "clone", "upgrade", *started, "workers closed", "drop", "scan"]


def test_cohort_core_rejects_a_writable_login(monkeypatch):
    from evals.buddy_benchmark import cohort_capture as cohort

    class Connection:
        def __enter__(self):
            return self

        def __exit__(self, *_):
            return False

        def execute(self, _):
            return SimpleNamespace(fetchone=lambda: (True, False))

    monkeypatch.setattr(cohort.psycopg, "connect", lambda _: Connection())
    with pytest.raises(ValueError, match="dedicated non-writing login"):
        cohort.require_read_only_core("unused")


@pytest.mark.parametrize(("driver", "options", "has_keys"), [
    ("live_build", {"build_fixture": True, "live_build": True}, True),
    ("live_plan", {"live_plan": True}, True),
    ("build_fixture", {"build_fixture": True}, False),
    ("browser_control", {}, False),
])
def test_response_member_uses_pinned_driver(tmp_path, monkeypatch, driver, options, has_keys):
    from evals.buddy_benchmark import cohort_capture as cohort
    path = tmp_path / "manifest.json"
    pin = put(path, {"schema": "dmb_ordinary_benchmark_v1", "cases": [{"id": "mounted", "question": "Try it"}]})
    for key in ("TYPESAFE_JEV_API_KEY", "OPENAI_API_KEY"):
        monkeypatch.setenv(key, "fixture")
    for key in (cohort.APP_DSN, "DMB_MANAGED_WORLD_DATA_ROOT", "DUNGEONMIND_LIVE_SESSION_DIR",
                "DUNGEONMIND_WORLD_GRAPH_ROOT"):
        monkeypatch.setenv(key, "outside-worker")
    seen = []

    def capture(*args, **kwargs):
        assert bool(cohort.os.environ.get("TYPESAFE_JEV_API_KEY")) is has_keys
        assert bool(cohort.os.environ.get("OPENAI_API_KEY")) is has_keys
        seen.append(kwargs)

    monkeypatch.setattr(w, "capture", capture)
    cohort._capture_member(path, tmp_path / "run" / "mounted", "owned-dsn", pin["sha256"],
                           browser_case="mounted", context_only=False, driver=driver)
    assert seen == [dict(context_only=False, cohort_manifest_sha256=pin["sha256"],
                         browser_case="mounted", writer_transport=False, detailed_trace=False,
                         cohort_app=None, **options)]


@pytest.mark.parametrize(("outcome", "overrides", "delivery"), [
    ("captured", {}, "pass"), ("observed", {}, "pass"), ("incomplete", {}, "unknown"),
    ("observed", {"draft_restored": False}, "fail"),
    ("observed", {"conversation_unchanged": False}, "fail"),
    ("observed", {"committed_page_unchanged": False}, "fail"),
    ("observed", {"browser_turn_posts": 1}, "fail"),
    ("observed", {"server_turn_posts": 1}, "fail"),
])
def test_response_cohort_build_fixture_report(tmp_path, outcome, overrides, delivery):
    observation = dict(status=outcome, provider_calls=0, draft_restored=True, conversation_unchanged=True,
                       committed_page_unchanged=True, browser_turn_posts=0, server_turn_posts=0)
    put(tmp_path / "fixture-result.json", {**observation, **overrides})
    row = w.report_case({"id": "mounted", "capture_boundary": "build_fixture", "capture_dir": str(tmp_path)}, tmp_path)
    assert row["delivery"] == {"status": delivery}
    assert row["owner_observation"]["provider_calls"] == 0


def test_cohort_member_verifies_exact_manifest_bytes_before_startup(tmp_path):
    path = tmp_path / "member.json"
    expected = put(path, {"schema": "dmb_ordinary_benchmark_v1", "cases": []})
    path.write_text("{}")
    with pytest.raises(ValueError, match="Evidence pin mismatch"):
        w.capture(path, tmp_path / "out", context_only=True,
                  cohort_manifest_sha256=expected["sha256"])
    assert not (tmp_path / "out").exists()


@pytest.mark.parametrize("failure", [None, "migration", "capture"])
def test_capture_owns_disposable_app_scope(tmp_path, monkeypatch, failure):
    from contextlib import contextmanager

    from evals.buddy_benchmark import disposable_database

    env = "DUNGEONBUDDY_APPLICATION_STATE_DATABASE_URL"
    source = "postgresql://127.0.0.1:12345/eval_template"
    template = dict(host="127.0.0.1", port=12345, database="eval_template",
                    oid="1", system_identifier="2")
    native = {**template, "database": "eval_core", "oid": "3"}
    clone = {**template, "database": "benchmark_run_fixture", "oid": "4"}
    manifest = {"cases": [], "isolation": {"app": template, "native": native}}
    events = []
    monkeypatch.setenv(env, source)
    monkeypatch.setattr(w, "load_manifest", lambda *_, **__: (manifest, tmp_path))

    @contextmanager
    def owned(admin_dsn, expected):
        assert admin_dsn == "postgresql://127.0.0.1:12345/postgres"
        assert expected == template
        events.append("created")
        try:
            yield clone
        finally:
            assert w.os.environ[env] == source
            events.append("dropped")

    def capture(pinned, *_args, **_options):
        assert pinned["isolation"] == {"app": clone, "native": native}
        assert w.os.environ[env].endswith("/benchmark_run_fixture")
        if failure == "capture":
            raise RuntimeError("capture fixture failed")

    from application_state import cli

    def upgrade():
        assert w.os.environ[env].endswith("/benchmark_run_fixture")
        events.append("migrated")
        if failure == "migration":
            raise RuntimeError("migration fixture failed")

    monkeypatch.setattr(disposable_database, "disposable_benchmark_database", owned)
    monkeypatch.setattr(cli, "upgrade_to_head", upgrade)
    monkeypatch.setattr(w, "_capture", capture)
    if failure:
        with pytest.raises(RuntimeError, match=f"{failure} fixture failed"):
            w.capture("unused", tmp_path, context_only=True, clone_app=True)
    else:
        w.capture("unused", tmp_path, context_only=True, clone_app=True)
    assert events == ["created", "migrated", "dropped"]
    assert w.os.environ[env] == source


def test_browser_scratch_uses_explicit_directory_on_evidence_filesystem(tmp_path, monkeypatch):
    from evals.buddy_benchmark.browser_capture import browser_scratch_directory

    output = tmp_path / "nested" / "output"
    output.mkdir(parents=True)
    scratch = tmp_path / "chrome"
    scratch.mkdir()
    monkeypatch.delenv("DMB_BENCHMARK_BROWSER_TMPDIR", raising=False)
    assert browser_scratch_directory(output) == output.parent
    monkeypatch.setenv("DMB_BENCHMARK_BROWSER_TMPDIR", str(scratch))
    assert browser_scratch_directory(output) == scratch
    monkeypatch.setenv("DMB_BENCHMARK_BROWSER_TMPDIR", "relative")
    with pytest.raises(ValueError, match="existing absolute directory"):
        browser_scratch_directory(output)


def test_full_response_capture_cli_passes_clone_request(monkeypatch):
    calls = []
    monkeypatch.setattr(w, "capture", lambda *args, **kwargs: calls.append((args, kwargs)))
    w.main(["capture", "--manifest", "pinned.json", "--output", "isolated", "--clone-app"])
    assert calls == [(("pinned.json", "isolated"), {"clone_app": True})]


# Interrupted clone recovery and teardown safety.
"""Recovery must never create or accidentally drop a different database."""
import errno
import fcntl
import hashlib
import json
import os

import pytest
from evals.buddy_benchmark import disposable_database as owner


@pytest.fixture
def clone_recovery_fixture(tmp_path, monkeypatch):
    template = {"host": "127.0.0.1", "port": 5432, "database": "app_template", "oid": "10", "system_identifier": "20"}
    clone = {**template, "database": "benchmark_run_" + "a" * 32, "oid": "11"}
    receipt = tmp_path / "owner.json"
    lock = tmp_path / "owner.lock"
    lock.touch()
    state = {"owner": "benchmark", "pid": 999999, "database": clone,
             "stage": "awaiting_review", "cleanup_complete": False,
             "runs": [{"workers_closed": True, "process_group": 999998}]}
    def save():
        raw = json.dumps(state).encode()
        receipt.write_bytes(raw)
        return {"ledger": str(receipt), "ledger_sha256": hashlib.sha256(raw).hexdigest(),
                "lock": str(lock), "lock_device": lock.stat().st_dev, "lock_inode": lock.stat().st_ino,
                "owner": "benchmark", "clone": dict(clone), "current_port": template["port"]}
    control = {"ids": {template["database"]: ("10", "20"), clone["database"]: ("11", "20")},
               "sessions": 0, "statements": []}
    class Cursor:
        def __init__(self, result): self.result = result
        def fetchone(self): return self.result
    class Connection:
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def execute(self, statement, params=None):
            control["statements"].append(str(statement))
            if "FROM pg_database WHERE datname" in str(statement):
                return Cursor(control["ids"].get(params[0]))
            if "pg_stat_activity" in str(statement): return Cursor((control["sessions"],))
            if "DROP DATABASE" in str(statement): control["ids"].pop(clone["database"], None)
            return Cursor(None)
    monkeypatch.setattr(owner.psycopg, "connect", lambda *a, **k: Connection())
    def absent(*args): raise ProcessLookupError(errno.ESRCH, "absent")
    monkeypatch.setattr(owner.os, "kill", absent)
    monkeypatch.setattr(owner.os, "killpg", absent)
    return template, clone, state, save, control, receipt, lock


def invoke_clone_recovery(template, recovery):
    return owner.disposable_benchmark_database("host=127.0.0.1 port=5432 dbname=postgres", template, recovery=recovery)


def test_recovery_claims_and_drops_only_pinned_existing_clone(clone_recovery_fixture):
    template, clone, state, save, control, receipt, lock = clone_recovery_fixture
    with invoke_clone_recovery(template, save()) as actual:
        assert actual == clone
        assert json.loads(receipt.read_text())["stage"] == "recovery_claimed"
        assert not any("CREATE DATABASE" in s for s in control["statements"])
        current = json.loads(receipt.read_text())
        current.update(pid=os.getpid(), stage="accept")
        receipt.write_text(json.dumps(current))
    assert clone["database"] not in control["ids"]
    assert template["database"] in control["ids"]
    assert sum("DROP DATABASE" in s for s in control["statements"]) == 1


@pytest.mark.parametrize("fault", ["bad_digest", "wrong_owner", "worker_open", "owner_live", "worker_live", "identity_changed", "sessions", "locked"])
def test_recovery_refuses_without_teardown(clone_recovery_fixture, monkeypatch, fault):
    template, clone, state, save, control, receipt, lock = clone_recovery_fixture
    if fault == "worker_open": state["runs"][0]["workers_closed"] = False
    pin = save()
    if fault == "bad_digest": pin["ledger_sha256"] = "0" * 64
    if fault == "wrong_owner": pin["owner"] = "someone else"
    if fault == "owner_live": monkeypatch.setattr(owner.os, "kill", lambda *a: None)
    if fault == "worker_live": monkeypatch.setattr(owner.os, "killpg", lambda *a: None)
    if fault == "identity_changed": control["ids"][clone["database"]] = ("12", "20")
    if fault == "sessions": control["sessions"] = 1
    held = open(lock, "r+") if fault == "locked" else None
    if held: fcntl.flock(held, fcntl.LOCK_EX | fcntl.LOCK_NB)
    try:
        with pytest.raises((ValueError, RuntimeError, BlockingIOError)):
            with invoke_clone_recovery(template, pin): pytest.fail("unsafe adoption")
    finally:
        if held: held.close()
    assert not any("DROP DATABASE" in s or "CREATE DATABASE" in s for s in control["statements"])
    assert clone["database"] in control["ids"]


def test_changed_clone_is_not_dropped_on_exit(clone_recovery_fixture):
    template, clone, state, save, control, receipt, lock = clone_recovery_fixture
    with pytest.raises(RuntimeError, match="identity changed"):
        with invoke_clone_recovery(template, save()):
            current = json.loads(receipt.read_text())
            current.update(pid=os.getpid(), stage="accept")
            receipt.write_text(json.dumps(current))
            control["ids"][clone["database"]] = ("12", "20")
    assert not any("DROP DATABASE" in s for s in control["statements"])


def test_exception_and_missing_acceptance_leave_clone(clone_recovery_fixture):
    template, clone, state, save, control, receipt, lock = clone_recovery_fixture
    with pytest.raises(KeyboardInterrupt):
        with invoke_clone_recovery(template, save()):
            raise KeyboardInterrupt()
    assert clone["database"] in control["ids"]
    assert not any("DROP DATABASE" in s for s in control["statements"])
    with pytest.raises(RuntimeError, match="acceptance or abandonment"):
        with invoke_clone_recovery(template, save()):
            pass
    assert clone["database"] in control["ids"]


def test_recovery_refuses_template_as_clone(clone_recovery_fixture):
    template, clone, state, save, control, receipt, lock = clone_recovery_fixture
    pin = save()
    pin["clone"] = {**template, "database": "benchmark_run_" + "b" * 32}
    bad_template = dict(template, database=pin["clone"]["database"])
    with pytest.raises(ValueError, match="recovery identity"):
        with invoke_clone_recovery(bad_template, pin): pass
    assert not control["statements"]


def test_recovery_refuses_replaced_lock(clone_recovery_fixture):
    template, clone, state, save, control, receipt, lock = clone_recovery_fixture
    pin = save()
    with pytest.raises(ValueError, match="lock identity"):
        with invoke_clone_recovery(template, pin):
            current = json.loads(receipt.read_text())
            current.update(pid=os.getpid(), stage="accept")
            receipt.write_text(json.dumps(current))
            lock.unlink()
            lock.touch()
    assert not any("DROP DATABASE" in s for s in control["statements"])


@pytest.mark.parametrize('fault', ['worker', 'sessions', 'missing_workers'])
def test_current_owner_must_close_workers_and_connections_before_drop(clone_recovery_fixture, monkeypatch, fault):
    template, clone, state, save, control, receipt, lock = clone_recovery_fixture
    with pytest.raises((ValueError, RuntimeError)):
        with invoke_clone_recovery(template, save()):
            current = json.loads(receipt.read_text())
            current.update(pid=os.getpid(), stage='accept')
            if fault == 'worker': monkeypatch.setattr(owner.os, 'killpg', lambda *args: None)
            if fault == 'sessions': control['sessions'] = 1
            if fault == 'missing_workers': current['runs'][0]['workers_closed'] = False
            receipt.write_text(json.dumps(current))
    assert clone['database'] in control['ids']
    assert not any('DROP DATABASE' in s for s in control['statements'])


def test_duplicate_receipt_fields_and_symlinks_are_refused(clone_recovery_fixture, tmp_path):
    template, clone, state, save, control, receipt, lock = clone_recovery_fixture
    pin = save()
    raw = receipt.read_text().replace('"owner": "benchmark"', '"owner": "benchmark", "owner": "benchmark"')
    receipt.write_text(raw)
    pin['ledger_sha256'] = hashlib.sha256(raw.encode()).hexdigest()
    with pytest.raises(ValueError, match='Duplicate'):
        with invoke_clone_recovery(template, pin): pass
    pin = save()
    link = tmp_path / 'receipt-link'
    link.symlink_to(receipt)
    pin['ledger'] = str(link)
    with pytest.raises(OSError):
        with invoke_clone_recovery(template, pin): pass
    assert not any('DROP DATABASE' in s for s in control['statements'])


def test_recovery_allows_explicit_new_port_but_keeps_old_receipt_binding(clone_recovery_fixture):
    template, clone, state, save, control, receipt, lock = clone_recovery_fixture
    pin = save()
    pin['current_port'] = 15432
    moved_template = {**template, 'port': 15432}
    with owner.disposable_benchmark_database('host=127.0.0.1 port=15432 dbname=postgres', moved_template, recovery=pin) as resumed:
        assert resumed == {**clone, 'port': 15432}
        current = json.loads(receipt.read_text())
        current.update(pid=os.getpid(), stage='accept', database=resumed)
        receipt.write_text(json.dumps(current))
    assert clone['database'] not in control['ids']


def test_recovery_rejects_unpinned_new_port(clone_recovery_fixture):
    template, clone, state, save, control, receipt, lock = clone_recovery_fixture
    pin = save()
    pin['current_port'] = 15432
    with pytest.raises(ValueError, match='recovery identity'):
        with invoke_clone_recovery(template, pin): pass
    assert not control['statements']


def test_protected_work_revisions_reads_named_columns(monkeypatch):
    from contextlib import nullcontext
    from types import SimpleNamespace
    from evals.buddy_benchmark import cohort_capture

    def execute(query, parameters):
        assert "current_revision_id" in query
        assert parameters == (["page-id"],)
        return SimpleNamespace(fetchall=lambda: [
            {"work_object_id": "page-id", "current_revision_id": "revision-id"},
        ])

    connection = SimpleNamespace(execute=execute)
    monkeypatch.setattr(cohort_capture, "readonly", lambda _: nullcontext(connection))
    assert cohort_capture.protected_work_revisions("fixture", ["page-id"]) == {
        "page-id": "revision-id",
    }


def test_saved_citation_reopen_retains_exact_and_failed_reads():
    import httpx

    first, second, third = (str(uuid4()) for _ in range(3))
    root = "/api/live/agent/worlds/fixture/conversation/turns/" + str(uuid4())

    def respond(request):
        if request.url.path == f"{root}/saved-sections/0/{first}":
            return httpx.Response(200, json={"content": "Before. Exact passage. After."})
        if request.url.path == f"{root}/saved-sections/0/{third}":
            raise httpx.ReadTimeout("fixture")
        assert request.url.path == f"{root}/saved-sections/0/{second}"
        return httpx.Response(404, json={"detail": "Unavailable"})

    with httpx.Client(base_url="http://test", transport=httpx.MockTransport(respond)) as client:
        report = w.reopen_saved_citations(client, root, {
            "answer_segments": [{"text": "“Exact passage.”"}],
            "saved_source_citations": [{"segment_index": 0, "section_event_ids": [first, second, third]}],
        })
    assert [r["http_status"] for r in report["citations"]] == [200, 404, None]
    assert [r["claim_exact_substring_of_reopened_text"] for r in report["citations"]] == [True, None, None]
    assert report["citations"][2]["transport_error"] == "ReadTimeout"


def test_native_citation_reopen_verifies_exact_binding_and_records_failures(tmp_path):
    import httpx

    turn_id = str(uuid4())
    root = "/api/live/agent/worlds/fixture/conversation/turns"
    content = "A paragraph with an accented character, é.\n"
    citation = {"excerpt_sha256": sha256(content.encode()).hexdigest(), "source_artifact_id": "pinned"}
    opened = {
        "schema": "dmb_agent_native_body_excerpt_read_v2", "world_id": "fixture",
        "turn_id": turn_id, "citation": citation, "content": content, "display_label": None,
    }

    def respond(request):
        index = int(request.url.path.rsplit("/", 1)[1])
        assert request.url.path == f"{root}/{turn_id}/native-body-excerpts/{index}"
        if index == 3:
            return httpx.Response(404, json={"detail": "Unavailable"})
        if index == 4:
            raise httpx.ReadTimeout("fixture")
        body = dict(opened, citation_index=index)
        if index == 1:
            body["content"] = content.strip()
        elif index == 2:
            body["citation"] = dict(citation, source_artifact_id="different")
        elif index == 5:
            body.pop("display_label")
        return httpx.Response(200, json=body)

    with httpx.Client(base_url="http://test", transport=httpx.MockTransport(respond)) as client:
        w.retain_citation_readbacks(client, tmp_path, root.removesuffix("/turns"), "fixture", turn_id,
            {"plan_context": {"completion": {"native_body_citations": [citation] * 6}}})
    result = json.loads((tmp_path / "native-citation-reopen.json").read_text())
    rows = result["citations"]
    assert [r["http_status"] for r in rows] == [200, 200, 200, 404, None, 200]
    assert [r["binding_matches"] for r in rows] == [True, True, False, None, None, False]
    assert [r["exact_reopen"] for r in rows] == [True, False, False, False, False, False]
    assert rows[0]["observed_excerpt_sha256"] == citation["excerpt_sha256"]
    assert rows[4]["transport_error"] == "ReadTimeout"


def test_cohort_restore_rejects_different_request_page_before_database(tmp_path, monkeypatch):
    from evals.buddy_benchmark import cohort_capture, cohort_fixture

    restored = "77940b05-c350-428a-88a3-2fc433ad6df0"
    member = put(tmp_path / "member.json", {
        "schema": "dmb_ordinary_benchmark_v1",
        "world": "test",
        "conversation_mode": "build_sequence",
        "build_history": {},
        "cases": [{"id": "STANDALONE-PAGE-3", "question": "Draft the requested page."}],
        "request_template": {"primary_work": {
            "kind": "build", "object_id": "another-page",
            "expected_revision": 25, "expected_content_sha256": "0" * 64,
        }},
    })
    put(tmp_path / "cohort.json", {
        "schema": "dmb_context_capture_cohort_v1",
        "protected_work_objects": [restored],
        "members": [{**member, "build_fixture_restore": {"seed": {
            "page_revision": 24, "page_sha256": "0" * 64, "working_copy": None,
            "active_conversation_id": None, "pointer_revision": 0,
        }}}],
    })
    monkeypatch.setenv(cohort_capture.APP_DSN, "postgresql://127.0.0.1/app")
    monkeypatch.setenv(cohort_capture.CORE_DSN, "postgresql://127.0.0.1/core")
    monkeypatch.setattr(cohort_fixture, "load_build_fixture", lambda *args, **kwargs: (
        {}, {"object": {"work_object_id": restored, "object_revision": 25},
             "revision": {"content_sha256": "0" * 64}},
    ))
    with pytest.raises(ValueError, match="Build fixture page must match the first ordinary request"):
        cohort_capture.capture_cohort(
            tmp_path / "cohort.json", tmp_path / "output",
            workers=1, clone_app=True, context_only=False,
        )
    assert not (tmp_path / "output").exists()


def test_first_requested_work_requires_matching_provider_receipt():
    from evals.buddy_benchmark.workflow import first_requested_work

    def response(sequence, provider, action):
        return {"kind": "context_snapshot", "sequence": sequence, "snapshot_kind": "provider_response",
                "materials": [{"item_id": f"unvalidated-controller-decision:{provider}:context",
                    "text": json.dumps({"answers": {"requested_work": {"kind": "choice", "selected": action}}})}]}

    receipt = {"kind": "provider_call", "sequence": 1, "provider": "typesafe",
               "outcome": "response_received", "provider_attempt_id": "choice-attempt"}
    unmatched = {"attempt": 1, "observations": [receipt, response(2, "wrong-attempt", "discuss")]}
    assert first_requested_work([unmatched]) == {"status": "unknown"}
    ordered = {**unmatched, "observations": [response(4, "choice-attempt", "discuss"), receipt,
                                           response(3, "choice-attempt", "clarify_request")]}
    assert first_requested_work([ordered]) == {
        "status": "observed", "requested_work": "clarify_request", "attempt": 1,
        "trace_sequence": 3, "provider_attempt_id": "choice-attempt",
    }
