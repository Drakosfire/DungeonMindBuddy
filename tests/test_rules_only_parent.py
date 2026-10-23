
from tests.application_state.session_encounter_helpers import session_request, historical_world_run
"""Actual ordinary Plan/Play admission, Rules broker and APP; synthetic provider IO."""
from dataclasses import replace
from hashlib import sha256
import json
from uuid import uuid4

import pytest

from application_state.agent_conversation import AgentConversationService
from application_state.agent_conversation.rules_authority_policy import rules_tool_definition
from application_state.agent_conversation.rules_authority_reads import MixedCompletedTurnV1
from application_state.content.service import create_world_plan, commit_plan, read_current_world_plan_revision
from application_state.play.service import create_world_play_run, replace_world_play_run_progress
from application_state.play.edition_service import read_context_snapshot
from apps.live_control_server.models.agent_turn import AgentTurnRequest
from apps.live_control_server.routes import agent
from apps.live_control_server.services.agent_runtime import AgentRuntimeResult
from apps.live_control_server.services.agent_turn_service import execute_agent_turn
from apps.live_control_server.services.hermes_agent_runtime import map_invocation_to_hermes_request
from apps.live_control_server.services.hermes_session_store import HermesSessionPointerStore
from apps.live_control_server.services.native_rules_capture import NativeProviderReply
from apps.live_control_server.services.world_container_registry import create_world_container
from tests.test_agent_turn_route import FakeRuntime, _payload, _native_lookup_roundtrip
from tests.application_state.play_runtime_helpers import V2_SOURCE_MARKDOWN


class RulesOnlyProvider(FakeRuntime):
    def __init__(self, mode, *, failure=None):
        super().__init__()
        self.mode, self.failure = mode, failure

    def run_with_provider_authorization(self, invocation, authorize, *, request_budget,
            on_graph_operation, on_provider_lifecycle, on_native_provider_reply,
            native_rules_capture_required):
        self.invocations.append(invocation)
        mapped = map_invocation_to_hermes_request(invocation)
        self.mapped = mapped
        from apps.live_control_server.services.hermes_graph_agent_contract import (
            serialize_hermes_graph_agent_turn_request, deserialize_hermes_graph_agent_turn_request)
        assert mapped.input_kind == "server_assembled_saved_work"
        wire = serialize_hermes_graph_agent_turn_request(replace(mapped, request_budget=request_budget,
            provider_authorization_required=True, parent_graph_broker_required=True,
            native_rules_capture_required=True))
        assert deserialize_hermes_graph_agent_turn_request(wire).question == mapped.question
        assert mapped.capability_policy.mode == "rules"
        assert mapped.capability_policy.graph_scope is None
        assert mapped.capability_policy.enabled_tool_names == ("lookup_rules",)
        assert native_rules_capture_required
        body = {"model": request_budget["model"], "input": [{"role":"user", "content":mapped.question}],
            "tools": [{"type":"function", **rules_tool_definition()["function"]}],
            "max_output_tokens": request_budget["outputReserveTokens"]}
        def view_for(body):
            raw = json.dumps(body, sort_keys=True, separators=(",", ":"))
            return {"provider":request_budget["provider"], "model":request_budget["model"],
                "apiMode":request_budget["apiMode"], "baseUrl":None, "payloadJson":raw,
                "payloadSha256":sha256(raw.encode()).hexdigest(), "payloadUtf8Bytes":len(raw.encode())}
        view = view_for(body)
        if self.failure in {"foreign_model", "foreign_tool", "changed_bytes", "body_model", "tool_schema", "output_limit"}:
            if self.failure == "foreign_model":
                view["model"] = "unadmitted-model"
            elif self.failure in {"body_model", "tool_schema", "output_limit"}:
                if self.failure == "body_model":
                    body["model"] = "unadmitted-model"
                elif self.failure == "tool_schema":
                    body["tools"][0]["parameters"] = {"type":"object"}
                else:
                    body["max_output_tokens"] = request_budget["outputReserveTokens"] + 1
                view = view_for(body)
            elif self.failure == "changed_bytes":
                view["payloadSha256"] = "0" * 64
            else:
                body["tools"].append({"type":"function", "name":"read_graph_source"})
                view = view_for(body)
            assert authorize(view) is False
            return AgentRuntimeResult(status="error",error_code="provider_authorization_refused")
        assert authorize(view), str(authorize.__self__.failure)
        assert on_provider_lifecycle({"transition":"sdk_entered"})
        text = "An ordinary answer without a Rules lookup."
        if self.mode != "unused":
            question = "Can I willingly end my move in a prone ally space?" if self.mode == "supported" else "How fast can the party travel?"
            view, packets = _native_lookup_roundtrip(body, view, authorize, on_graph_operation,
                on_provider_lifecycle, on_native_provider_reply, question=question)
            capsules = packets[0]["support_capsules"]
            segment = ({"kind":"rules_claim", "text":capsules[0]["excerpt_text"],
                "support_ids":[capsules[0]["support_id"]]} if capsules else
                {"kind":"rules_context", "text":"The admitted source does not supply this rule.", "category":"gap"})
            text = json.dumps({"schema":"dmb_rules_mixed_answer_v1", "base_output":None,
                "rules_segments":[segment], "ordered_refs":[{"domain":"rules","segment_index":0}]})
        if self.failure == "forged_base":
            candidate = json.loads(text)
            candidate["base_output"] = {"answer_segments":[{"kind":"plan_claim", "text":"Unverified Plan fact."}]}
            candidate["ordered_refs"].insert(0,{"domain":"base","segment_index":None})
            text = json.dumps(candidate)
        elif self.failure == "plaintext_after_lookup":
            text = "An unsupported plain answer after lookup."
        elif self.failure in {"unknown_outcome", "missing_capture"}:
            transition = "outcome_unknown" if self.failure == "unknown_outcome" else "response_received"
            accepted = on_provider_lifecycle({"transition":transition})
            assert accepted is True
            return AgentRuntimeResult(status="error", error_code="provider_lifecycle_unavailable")
        assert on_provider_lifecycle({"transition":"response_received"})
        assert on_native_provider_reply(NativeProviderReply(
            authorization_id="host:1", api_request_id=str(uuid4()), provider=view["provider"],
            model=view["model"], api_mode=view["apiMode"], request_sha256=view["payloadSha256"],
            finish_reason="stop", status="answered", text=text, text_sha256=sha256(text.encode()).hexdigest(),
            text_utf8_bytes=len(text.encode()), tool_calls=()))
        return AgentRuntimeResult(status="ok", final_text=text, runtime_session_id="runtime-1")


def case(tmp_path, monkeypatch, surface, *, note="Preserve my saved note.", historical_session=False):
    managed = create_world_container(tmp_path, name="Rules-only World")
    world = managed.world_id
    plan = create_world_plan(title="Keep this Plan", world_id=world)
    obj, revision = commit_plan(str(plan.work_object_id), V2_SOURCE_MARKDOWN, expected_world_id=world)
    primary = {"kind":"plan", "object_id":str(obj.work_object_id), "expected_revision":obj.object_revision,
        "expected_revision_n":revision.revision_n, "expected_content_sha256":revision.content_sha256}
    if surface == "play":
        if historical_session:
            run = historical_world_run(world_id=world,run_id=str(uuid4()),playable_artifact_id=obj.work_object_id,expected_playable_revision=revision.revision_n,expected_playable_content_sha256=revision.content_sha256)
        else:
            run = create_world_play_run(world_id=world, run_id=str(uuid4()), request=session_request(world_id=world, playable_artifact_id=obj.work_object_id, expected_playable_revision=revision.revision_n, expected_playable_content_sha256=revision.content_sha256)).aggregate
        replace_world_play_run_progress(world_id=world, run_id=run.run.run_id, expected_run_revision=run.run.run_revision,
            progress={"current_beat_id":"beat:arrival", "current_scene_id":"scene:gate", "resolved_beat_ids":[],
                "selections":{}, "notes_by_element_id":{"scene:gate":note}})
        current, content = read_context_snapshot(world_id=world, run_id=str(run.run.run_id))
        primary = {"kind":"run", "object_id":str(current.run_id), "expected_revision":current.run_revision,
            "play_content_basis":{"edition_revision":content.edition_revision,
                "edition_revision_id":content.edition_revision_id, "content_sha256":content.content_sha256}}
        retained = (current, content)
        def read_retained():
            return read_context_snapshot(world_id=world,run_id=str(current.run_id))
    else:
        def read_retained():
            return read_current_world_plan_revision(str(obj.work_object_id), expected_world_id=world,
                expected_revision=obj.object_revision, expected_revision_n=revision.revision_n,
                expected_content_sha256=revision.content_sha256)
        retained = read_retained()
    monkeypatch.setattr(agent, "repo_root", lambda: tmp_path)
    request = AgentTurnRequest.model_validate({**_payload(), "turn_id":str(uuid4()),
        "surface":{"surface_id":surface, "instance_id":surface+"-rules-only"},
        "owner_scope":{"kind":"world", "world_id":world}, "primary_work":primary,
        "client_work_state":"saved_clean", "message":"Please check the relevant rule.",
        **({"play_target":{"beat_id":"beat:arrival","scene_id":"scene:gate","marker_grammar_version":"v2"}} if surface == "play" else {})})
    owner = {"kind":"world", "id":world, "name":"Rules-only World"}
    service = AgentConversationService()
    pointers = HermesSessionPointerStore(tmp_path / "pointers")
    def execute(runtime, *, replay=False):
        def forbidden(*args, **kwargs):
            pytest.fail("Rules-only/replay acquired Graph or mutable work")
        return execute_agent_turn(request, root=tmp_path, pointer_store=pointers,
            owner_resolver=lambda _:owner, work_resolver=forbidden if replay else agent._work_resolver,
            graph_resolver=forbidden, plan_graph_resolver=forbidden,
            runtime=runtime, conversation_service=service)
    return request, service, execute, retained, read_retained


@pytest.mark.parametrize("surface", ["plan", "play"])
@pytest.mark.parametrize("mode", ["supported", "missing", "unavailable", "unused"])
def test_real_rules_only_parent_atomic_completion_reopen_and_zero_read_replay(
        application_state_dsn, tmp_path, monkeypatch, surface, mode):
    from apps.live_control_server.services import rules_lookup
    request, service, execute, retained, read_retained = case(tmp_path,monkeypatch,surface)
    counts = {"queries":0}
    original = rules_lookup.query_rules
    def query(*args, **kwargs):
        counts["queries"] += 1
        if mode == "unavailable":
            raise rules_lookup.RulesCorpusUnavailable("source unavailable")
        if mode == "unused":
            pytest.fail("unused Rules capability read the corpus")
        return original(*args, **kwargs)
    monkeypatch.setattr(rules_lookup, "query_rules", query)
    if mode == "unused":
        monkeypatch.setattr(rules_lookup,"admitted_bundle",lambda *_:pytest.fail("unused Rules source read"))
    runtime = RulesOnlyProvider(mode)
    response = execute(runtime)
    assert response.answer.status == "ok"
    turns = service.list_turns(request.owner_scope.world_id,
        service.get_world_pointer(request.owner_scope.world_id).active_conversation_id)
    completed = turns[-1]
    assert read_retained() == retained
    if surface == "plan":
        assert response.primary_work.content_basis is not None
        assert response.primary_work.content_basis.content_sha256 == request.primary_work.expected_content_sha256
    if surface == "play":
        context = response.play_source_context
        assert context.basis.beat_id == request.play_target.beat_id
        assert context.basis.scene_id == request.play_target.scene_id
        assert context.basis.run_revision == request.primary_work.expected_revision
        assert context.delivery_replay is False
        assert "scene_note" not in context.basis.model_dump()
        assert "Preserve my saved note." not in context.model_dump_json()
    if mode == "unused":
        assert completed.graph_context_receipt is None and completed.graph_context_execution is None
        assert completed.assistant_text == "An ordinary answer without a Rules lookup."
    else:
        assert isinstance(completed, MixedCompletedTurnV1)
        assert completed.base_projection.kind == "absent"
        assert completed.accepted_binding.base_disposition == "absent"
        assert completed.accepted_binding.graph_used is False
        assert response.rules_context.base_context is None and response.rules_context.unclaimed_context is None
        assert bool(completed.accepted_binding.support_table) == (mode == "supported")
    assert counts["queries"] == (0 if mode == "unused" else 2 if mode == "unavailable" else 1)
    def forbidden(*args, **kwargs):
        pytest.fail("completed replay read Rules corpus")
    monkeypatch.setattr(rules_lookup,"query_rules",forbidden)
    monkeypatch.setattr(rules_lookup,"admitted_bundle",forbidden)
    replay = execute(runtime, replay=True)
    assert replay.answer.text == response.answer.text
    if surface == "play":
        assert replay.play_source_context.basis == response.play_source_context.basis
        assert replay.play_source_context.delivery_replay is True
    assert len(runtime.invocations) == 1
    from starlette.requests import Request
    monkeypatch.setattr(agent,"enforce_native_graph_gm",lambda _:None)
    monkeypatch.setattr(agent,"_verified_world_id",lambda world:world)
    monkeypatch.setattr(agent,"_conversation_service",lambda _:service)
    historical = agent.get_world_conversation_history(request.owner_scope.world_id,
        Request({"type":"http","method":"GET","path":"/","headers":[],"query_string":b""}),
        limit=10,before_sequence=None,include_turn_correlation=True)
    row = historical.turns[-1]
    assert row.assistant_text == response.answer.text
    if surface == "play":
        assert row.play_source_context.basis == response.play_source_context.basis
        assert row.play_source_context.delivery_replay is True
        assert "Preserve my saved note." not in row.model_dump_json()
        assert historical.schema_ == "dmb_agent_conversation_history_v4"


@pytest.mark.parametrize("surface", ["plan", "play"])
@pytest.mark.parametrize("failure", ["foreign_model", "foreign_tool", "changed_bytes", "body_model", "tool_schema", "output_limit", "forged_base",
    "plaintext_after_lookup", "unknown_outcome", "missing_capture"])
def test_rules_only_rejects_foreign_authority_unproved_output_and_unsafe_redispatch(
        application_state_dsn, tmp_path, monkeypatch, surface, failure):
    from apps.live_control_server.services import rules_lookup
    from apps.live_control_server.services.agent_turn_service import AgentTurnServiceError

    request, service, execute, retained, read_retained = case(tmp_path,monkeypatch,surface)
    original = rules_lookup.query_rules
    reads = []
    def query(*args, **kwargs):
        reads.append(args)
        return original(*args, **kwargs)
    monkeypatch.setattr(rules_lookup,"query_rules",query)
    runtime = RulesOnlyProvider("supported",failure=failure)
    if failure in {"forged_base", "plaintext_after_lookup"}:
        with pytest.raises(AgentTurnServiceError,match="could not be verified"):
            execute(runtime)
    else:
        response = execute(runtime)
        assert response.answer.status == "error"
    current = service.get_world_pointer(request.owner_scope.world_id)
    turn = service.list_turns(request.owner_scope.world_id,current.active_conversation_id)[-1]
    assert not isinstance(turn,MixedCompletedTurnV1) and turn.status in {"failed","interrupted"}
    assert turn.assistant_text is None and turn.completion is None
    assert read_retained() == retained
    assert len(reads) == (0 if failure in {"foreign_model","foreign_tool","changed_bytes","body_model","tool_schema","output_limit"} else 1)
    if reads:
        with pytest.raises(AgentTurnServiceError):
            execute(runtime)
        assert len(runtime.invocations) == 1


@pytest.mark.parametrize("change", ["missing", "note", "edition", "target", "stale_run"])
def test_rules_only_play_forged_or_changed_source_refuses_before_provider(
        application_state_dsn,tmp_path,monkeypatch,change):
    from apps.live_control_server.services.agent_turn_service import AgentTurnServiceError

    request,service,execute,_,_ = case(tmp_path,monkeypatch,"play")
    original = agent._work_resolver
    def changed(body,owner):
        work = original(body,owner)
        receipt = work.play_context_receipt
        if change == "missing":
            receipt = None
        elif change == "note":
            text = "A forged saved note."
            receipt = receipt.model_copy(update={"scene_note":text,"scene_note_sha256":sha256(text.encode()).hexdigest()})
        elif change == "edition":
            receipt = receipt.model_copy(update={"edition_revision":1,"edition_revision_id":uuid4(),"content_sha256":"b"*64})
        elif change == "target":
            receipt = receipt.model_copy(update={"scene_id":"scene:other","scene_note":None,"scene_note_sha256":None})
        else:
            replace_world_play_run_progress(world_id=request.owner_scope.world_id,run_id=request.primary_work.object_id,
                expected_run_revision=request.primary_work.expected_revision,progress={"current_beat_id":"beat:arrival",
                "current_scene_id":"scene:gate","resolved_beat_ids":[],"selections":{},"notes_by_element_id":{"scene:gate":"A new saved note."}})
        return replace(work,play_context_receipt=receipt)
    monkeypatch.setattr(agent,"_work_resolver",changed)
    runtime = RulesOnlyProvider("supported")
    with pytest.raises((AgentTurnServiceError,ValueError)):
        execute(runtime)
    assert runtime.invocations == []
    pointer = service.get_world_pointer(request.owner_scope.world_id)
    if pointer.active_conversation_id:
        assert service.list_turns(request.owner_scope.world_id,pointer.active_conversation_id) == []


def test_large_saved_play_source_crosses_actual_ipc_without_truncation(application_state_dsn, tmp_path, monkeypatch):
    note = "Retain this exact saved scene detail. " * 400
    _, _, execute, retained, read_retained = case(tmp_path, monkeypatch, 'play', note=note)
    runtime = RulesOnlyProvider('unused')
    response = execute(runtime)
    assert response.answer.status == 'ok'
    assert len(runtime.mapped.question) > 8000 and note in runtime.mapped.question
    assert note not in (runtime.mapped.surface_context_block or "")
    assert read_retained() == retained
