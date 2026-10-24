"""Real mocked decision+writer SDKs, actual APP preparation/completion and recovery."""

import json
from hashlib import sha256
from uuid import uuid5
import httpx
import psycopg
import pytest
from psycopg.types.json import Jsonb
from application_state.agent_conversation import AgentConversationService
from application_state.agent_conversation import types as ledger
from application_state.build_proposal.images import BuildImageService
from application_state.errors import (
    ApplicationStateIntegrityError,
    ApplicationStateNotFoundError,
)
from apps.live_control_server.services import build_image_writer as image_writer
from apps.live_control_server.services.build_jev_harness import BuildJevHarness
from apps.live_control_server.services.build_jev_accounting import (
    ExperimentalAccounting,
)
from tests.test_agent_build_jev_ordinary_harness import (
    DecisionWire,
    ordinary_case,
    build_case as _build_case,
)
from tests.test_agent_build_governed_graph import execute


@pytest.fixture
def build_case(tmp_path, monkeypatch, application_state_dsn):
    return _build_case.__wrapped__(tmp_path, monkeypatch, application_state_dsn)


class ImageWire(httpx.AsyncBaseTransport):
    def __init__(self, *, timeout=False, after=None, purpose="map"):
        self.calls = []
        self.timeout = timeout
        self.after = after
        output = {
            "prompt": "An overhead fantasy map of the peaceful fort town beside its swamp, with the marketplace as proposed layout.",
            "alt": "Proposed map of the fort town",
        }
        if purpose is not None:
            output["purpose"] = purpose
        self.text = json.dumps(output)

    async def handle_async_request(self, request):
        self.calls.append(request)
        if self.timeout:
            raise httpx.ReadTimeout("synthetic uncertain send", request=request)
        if self.after:
            self.after()
        return httpx.Response(
            200,
            request=request,
            json={
                "id": "image-direction",
                "object": "response",
                "created_at": 1,
                "status": "completed",
                "model": "gpt-6-luna",
                "output": [
                    {
                        "type": "message",
                        "id": "msg",
                        "role": "assistant",
                        "status": "completed",
                        "content": [
                            {
                                "type": "output_text",
                                "text": self.text,
                                "annotations": [],
                            }
                        ],
                    }
                ],
                "usage": {
                    "input_tokens": 100,
                    "output_tokens": 35,
                    "total_tokens": 135,
                },
            },
        )


def setup(build_case, monkeypatch, *, world_context=False, **wire_options):
    case, reads = ordinary_case(build_case, monkeypatch, authoring=True)
    source, request, bootstrap = case
    request = request.model_copy(
        update={
            "message": "Open the image wizard with a map prompt based on this town and our conversation."
        }
    )
    monkeypatch.setattr(image_writer, "_model", lambda: "gpt-6-luna")
    decision = DecisionWire(operation="prepare_build_image")
    wire = ImageWire(**wire_options)
    runtime = BuildJevHarness(
        world_context=world_context,
        named_citations=world_context,
        decision_transport=decision,
        writer_transport=wire,
        accounting=ExperimentalAccounting(
            "synthetic-owner-test", lambda text: len(text) // 4
        ),
    )
    return (source, request, bootstrap), reads, runtime, decision, wire


@pytest.mark.parametrize("world_context", [False, True])
@pytest.mark.parametrize("long_instruction", [False, True])
@pytest.mark.parametrize("purpose", ["map", "illustration"])
def test_image_operation_prepares_one_writer_and_reopens_without_generation(
    build_case, monkeypatch, tmp_path, purpose, long_instruction, world_context
):
    case, reads, runtime, decisions, wire = setup(
        build_case, monkeypatch, purpose=purpose, world_context=world_context
    )
    if long_instruction:
        source, request, bootstrap = case
        case = (source, request.model_copy(update={"message": request.message * 70}), bootstrap)
        assert len(case[1].message) > 4000
    response = execute(case, tmp_path, runtime, operator_subject="local_operator")
    completion = response.knowledge_context.completion
    assert isinstance(completion, ledger.BuildImagePreparationCompletionV1)
    assert response.answer.text == ledger.BUILD_IMAGE_READY_TEXT
    assert len(decisions.calls) == len(wire.calls) == 1 and reads == {
        "graph": 0,
        "source": 0,
    }
    image = BuildImageService().get(completion.action_id, "local_operator")
    assert image.prompt == json.loads(wire.text)["prompt"] and image.asset_id is None
    assert image.purpose == purpose
    assert image.reservation.instruction == case[1].message
    assert image.writer_proof.raw_response == wire.text
    assert (
        image.writer_proof.authorization.payload_sha256
        == sha256(wire.calls[0].content).hexdigest()
    )
    packet = json.loads(json.loads(wire.calls[0].content)["input"])
    assert packet["draft_markdown"] == case[1].build_write_capability.draft_markdown
    assert json.loads(wire.calls[0].content)["tools"] == []
    assert json.loads(wire.calls[0].content)["text"]["format"]["type"] == "json_schema"
    service = AgentConversationService()
    turn = service.list_turns("elderwyld", image.reservation.conversation_id)[0]
    assert turn.completion == completion
    traces = service.list_context_trace_attempts(world_id="elderwyld", turn_id=turn.turn_id)
    observed = [item for trace in traces for item in trace.observations
                if item.kind == "provider_call" and item.duration_ms is not None]
    assert len(observed) == 2
    assert {item.provider_attempt_id for item in observed} == {
        event.provider_attempt_id for event in turn.graph_context_execution.events
        if event.kind == "provider_attempt_authorized_v3"
    }
    assert all(item.provider_attempt_id is not None for item in observed)
    assert [(item.input_tokens, item.output_tokens) for item in observed] == [(23, 4), (100, 35)]
    assert all(call["runtime_api_request_id"].startswith("generationengine:") for call in runtime.calls)
    replay = execute(case, tmp_path, runtime, operator_subject="local_operator")
    assert replay.knowledge_context.delivery_replay is True
    assert len(decisions.calls) == len(wire.calls) == 1
    with pytest.raises(ApplicationStateNotFoundError):
        BuildImageService().get(image.action_id, "foreign")


@pytest.mark.parametrize("field", ["prompt", "alt", "purpose", "raw_response", "request_json"])
def test_reopen_rejects_forged_preparation(
    build_case, monkeypatch, tmp_path, application_state_dsn, field
):
    case, _, runtime, _, _ = setup(build_case, monkeypatch)
    response = execute(case, tmp_path, runtime, operator_subject="local_operator")
    action = response.knowledge_context.completion.action_id
    with psycopg.connect(application_state_dsn) as conn:
        payload = conn.execute(
            "SELECT payload FROM agent.build_proposal WHERE action_id=%s", (action,)
        ).fetchone()[0]
        if field == "purpose":
            payload[field] = "illustration"
        elif field in {"prompt", "alt"}:
            payload[field] += " forged"
        else:
            payload["writer_proof"][field] += " forged"
        conn.execute(
            "UPDATE agent.build_proposal SET payload=%s WHERE action_id=%s",
            (Jsonb(payload), action),
        )
    with pytest.raises(ApplicationStateIntegrityError):
        AgentConversationService().list_turns(
            "elderwyld", case[1].build_write_capability.conversation_id
        )


def test_completion_failure_recovers_owned_preparation_without_another_writer(
    build_case, monkeypatch, tmp_path
):
    case, _, runtime, decisions, wire = setup(build_case, monkeypatch)
    original = AgentConversationService.complete_turn
    monkeypatch.setattr(
        AgentConversationService,
        "complete_turn",
        lambda *a, **k: (_ for _ in ()).throw(
            ValueError("synthetic completion outage")
        ),
    )
    with pytest.raises(Exception):
        execute(case, tmp_path, runtime, operator_subject="local_operator")
    action = uuid5(case[1].build_write_capability.idempotency_key, "image")
    assert BuildImageService().get(action, "local_operator").writer_proof
    monkeypatch.setattr(AgentConversationService, "complete_turn", original)
    response = execute(case, tmp_path, runtime, operator_subject="local_operator")
    assert response.knowledge_context.completion.action_id == action
    assert len(decisions.calls) == len(wire.calls) == 1


def test_unknown_writer_does_not_replay_or_create_preparation(
    build_case, monkeypatch, tmp_path
):
    case, _, runtime, decisions, wire = setup(build_case, monkeypatch, timeout=True)
    with pytest.raises(Exception):
        execute(case, tmp_path, runtime, operator_subject="local_operator")
    with pytest.raises(Exception):
        execute(case, tmp_path, runtime, operator_subject="local_operator")
    assert len(wire.calls) == 1
    with pytest.raises(ApplicationStateNotFoundError):
        BuildImageService().get(
            uuid5(case[1].build_write_capability.idempotency_key, "image"),
            "local_operator",
        )


def test_no_editor_capability_does_not_offer_image(build_case, monkeypatch):
    case, _, runtime, _, _ = setup(build_case, monkeypatch)
    request = case[1].model_copy(update={"build_write_capability": None})
    assert (
        "prepare_build_image"
        not in runtime.configured_budget(request)["buildJevActions"][
            "allowed_surface_operations"
        ]
    )


def test_legacy_direction_and_completion_reopen_with_unchanged_digest(
    build_case, monkeypatch, tmp_path, application_state_dsn
):
    from application_state.build_proposal import types as image_types
    from application_state.agent_conversation.build_authoring import result_digest, _image_digest

    # Produce the old schema through the same real Harness/DB boundary, then
    # restore the new implementation before reopening the historical completion.
    with monkeypatch.context() as legacy:
        legacy.setattr(image_writer, "POLICY", "captured_build_image_prompt_alt_v1")
        legacy.setattr(image_writer, "ImageDirectionV2", image_types.ImageDirection)
        legacy.setattr(image_types, "ImageDirectionV2", image_types.ImageDirection)
        case, _, runtime, _, wire = setup(build_case, legacy, purpose=None)
        response = execute(case, tmp_path, runtime, operator_subject="local_operator")
    completion = response.knowledge_context.completion
    record = BuildImageService().get(completion.action_id, "local_operator")
    expected = _image_digest({"prompt": record.prompt, "alt": record.alt,
                              "writer_proof": record.writer_proof.model_dump(mode="json")})
    assert result_digest(record) == completion.preparation_result_sha256 == expected
    with psycopg.connect(application_state_dsn) as conn:
        payload = conn.execute("SELECT payload FROM agent.build_proposal WHERE action_id=%s", (record.action_id,)).fetchone()[0]
        payload.pop("purpose", None)
        conn.execute("UPDATE agent.build_proposal SET payload=%s WHERE action_id=%s", (Jsonb(payload), record.action_id))
    assert BuildImageService().get(record.action_id, "local_operator").purpose is None
    reopened = AgentConversationService().list_turns("elderwyld", record.reservation.conversation_id)[0]
    assert reopened.completion == completion and len(wire.calls) == 1


@pytest.mark.parametrize("purpose", [None, "unsupported"])
def test_new_writer_rejects_missing_or_unknown_purpose(build_case, monkeypatch, tmp_path, purpose):
    case, _, runtime, _, wire = setup(build_case, monkeypatch, purpose=purpose)
    with pytest.raises(Exception):
        execute(case, tmp_path, runtime, operator_subject="local_operator")
    assert len(wire.calls) == 1
    with pytest.raises(ApplicationStateNotFoundError):
        BuildImageService().get(uuid5(case[1].build_write_capability.idempotency_key, "image"), "local_operator")
