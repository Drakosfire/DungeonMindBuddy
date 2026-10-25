"""Writer and APP must not offer a continuation without its admitted capability."""

import json
import pytest
from tests.test_typed_collaboration import packet, answer
from application_state.agent_conversation.build_draft_answer import (
    normalize,
    output_schema,
)


def scoped_packet():
    value = packet()
    value["collaboration_action_scope"] = {
        "policy": "admitted_collaboration_actions_v1",
        "allowed_step_kinds": ["discuss"],
    }
    return value


def test_finite_schema_excludes_unavailable_insertion():
    schema = output_schema(scoped_packet())
    assert schema["$defs"]["ProposedStep"]["properties"]["kind"]["enum"] == ["discuss"]


def test_unavailable_insertion_is_rejected_without_silent_step_repair():
    raw = answer(
        {
            "kind": "plan",
            "steps": [{"text": "Prepare the insertion.", "kind": "prepare_insertion"}],
        }
    )
    with pytest.raises(ValueError, match="admitted"):
        normalize(json.dumps(raw), scoped_packet())


@pytest.fixture
def build_case(tmp_path, monkeypatch, application_state_dsn):
    from tests.test_agent_build_jev_ordinary_harness import build_case as original

    return original.__wrapped__(tmp_path, monkeypatch, application_state_dsn)


@pytest.mark.parametrize(
    "with_editor,step_kind,should_complete",
    [
        (False, "discuss", True),
        (False, "prepare_insertion", False),
        (True, "prepare_insertion", True),
    ],
)
def test_actual_host_and_app_enforce_frozen_plan_actions(
    build_case, monkeypatch, tmp_path, with_editor, step_kind, should_complete
):
    from dataclasses import replace
    from hashlib import sha256
    import httpx
    from application_state.agent_conversation import AgentConversationService
    from application_state.agent_conversation.build_draft_context import (
        BuildDraftSnapshotV1,
        BuildDraftContextRequestV1,
    )
    from application_state.agent_conversation.source_writer_output import reconstruct
    from apps.live_control_server.models.agent_turn import AgentTurnRequest
    from apps.live_control_server.services.build_jev_harness import BuildJevHarness
    from apps.live_control_server.services.agent_turn_service import (
        AgentTurnServiceError,
    )
    from tests.test_agent_build_jev_ordinary_harness import ordinary_case, DecisionWire
    from tests.test_agent_build_governed_graph import execute
    from tests.test_build_jev_estimated_continuations import counter
    from apps.live_control_server.services import build_related_pages
    from application_state.agent_conversation.collaboration_scope import KEY

    (source, request, bootstrap), _ = ordinary_case(
        build_case, monkeypatch, authoring=True
    )
    cap = request.build_write_capability
    text = "The workshop owner remains an author choice."
    snap = BuildDraftSnapshotV1(
        **{
            k: getattr(cap.basis, k)
            for k in (
                "world_id",
                "document_id",
                "registry_revision",
                "content_sha256",
                "visibility",
                "draft_generation",
            )
        },
        draft_markdown=text,
        draft_sha256=sha256(text.encode()).hexdigest(),
        editor_sha256="b" * 64,
    )
    cap = cap.model_copy(
        update={
            "draft_markdown": text,
            "basis": cap.basis.model_copy(
                update={
                    "draft_sha256": snap.draft_sha256,
                    "editor_sha256": snap.editor_sha256,
                }
            ),
        }
    )
    draft = BuildDraftContextRequestV1(
        snapshot=snap,
        conversation_id=cap.conversation_id,
        expected_pointer_revision=cap.expected_pointer_revision,
    )
    payload = {
        **request.model_dump(mode="json", by_alias=True),
        "message": "Propose a plan for developing this workshop, without executing it.",
        "build_draft_context": draft.model_dump(mode="json"),
        "build_write_capability": cap.model_dump(mode="json") if with_editor else None,
    }
    request = AgentTurnRequest.model_validate(payload)
    bootstrap = replace(bootstrap, completed_discovery_query=request.message)
    monkeypatch.setattr(build_related_pages, "discover", lambda _: [])

    class PlanWriter(httpx.AsyncBaseTransport):
        def __init__(self):
            self.calls = []

        async def handle_async_request(self, req):
            self.calls.append(req)
            raw = answer(
                {
                    "kind": "plan",
                    "steps": [{"text": "Develop the workshop.", "kind": step_kind}],
                }
            )
            return httpx.Response(
                200,
                request=req,
                json={
                    "id": "resp_scope",
                    "object": "response",
                    "created_at": 1,
                    "status": "completed",
                    "model": "gpt-6-luna",
                    "output": [
                        {
                            "id": "msg_scope",
                            "type": "message",
                            "status": "completed",
                            "role": "assistant",
                            "content": [
                                {
                                    "type": "output_text",
                                    "text": json.dumps(raw),
                                    "annotations": [],
                                }
                            ],
                        }
                    ],
                    "usage": {
                        "input_tokens": 100,
                        "output_tokens": 100,
                        "total_tokens": 200,
                    },
                },
            )

    wire = PlanWriter()
    harness = BuildJevHarness(
        world_context=True,
        named_citations=True,
        related_pages=True,
        accounting=counter(),
        decision_transport=DecisionWire(operation="answer_from_sources"),
        writer_transport=wire,
    )
    if not should_complete:
        with pytest.raises(AgentTurnServiceError):
            execute((source, request, bootstrap), tmp_path, harness)
    else:
        response = execute((source, request, bootstrap), tmp_path, harness)
        assert (
            response.knowledge_context.completion.collaboration.steps[0].kind
            == step_kind
        )
    assert len(wire.calls) == 1
    body = json.loads(wire.calls[0].content)
    packet = json.loads(body["input"])
    expected = ["discuss", "prepare_insertion"] if with_editor else ["discuss"]
    assert packet[KEY]["allowed_step_kinds"] == expected
    assert (
        body["text"]["format"]["schema"]["$defs"]["ProposedStep"]["properties"]["kind"][
            "enum"
        ]
        == expected
    )
    turn = AgentConversationService().list_turns("elderwyld", cap.conversation_id)[0]
    assert (turn.status == "completed") is should_complete
    if should_complete:
        # Existing completion/history remain readable after the transient proof.
        assert (
            type(turn)
            .model_validate_json(turn.model_dump_json(by_alias=True))
            .completion
            == turn.completion
        )
    if not with_editor and should_complete:
        auth = next(
            e
            for e in turn.graph_context_execution.events
            if getattr(e, "provider", None) == "openai"
            and getattr(e, "kind", "") == "provider_attempt_authorized_v3"
        )
        bad = answer(
            {
                "kind": "plan",
                "steps": [{"text": "Prepare writing.", "kind": "prepare_insertion"}],
            }
        )
        # APP recomputes capability even if a worker omits the new input metadata.
        old_packet = dict(packet)
        old_packet.pop(KEY)
        with pytest.raises(ValueError, match="admitted"):
            reconstruct(json.dumps(bad), old_packet, turn, auth)
        forged = dict(packet)
        forged[KEY] = {
            "policy": "admitted_collaboration_actions_v1",
            "allowed_step_kinds": ["discuss", "prepare_insertion"],
        }
        with pytest.raises(ValueError, match="admitted"):
            reconstruct(json.dumps(bad), forged, turn, auth)
    from apps.live_control_server.services.workspace_document_registry import (
        get_workspace_document_snapshot,
    )

    assert (
        get_workspace_document_snapshot(tmp_path, source.record.document_id).markdown
        == source.markdown
    )


def test_historical_producer_schema_is_not_rewritten():
    schema = output_schema(packet())
    assert schema["$defs"]["ProposedStep"]["properties"]["kind"]["enum"] == [
        "discuss",
        "prepare_insertion",
    ]


@pytest.mark.parametrize(
    "scope",
    [
        {"policy": "unknown", "allowed_step_kinds": ["discuss"]},
        {
            "policy": "admitted_collaboration_actions_v1",
            "allowed_step_kinds": ["prepare_insertion"],
        },
        {
            "policy": "admitted_collaboration_actions_v1",
            "allowed_step_kinds": ["discuss", "discuss"],
        },
        {
            "policy": "admitted_collaboration_actions_v1",
            "allowed_step_kinds": ["discuss"],
            "extra": "authority",
        },
    ],
)
def test_invalid_scope_cannot_broaden_schema(scope):
    value = packet()
    value["collaboration_action_scope"] = scope
    with pytest.raises(ValueError):
        output_schema(value)
