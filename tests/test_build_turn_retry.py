"""Real APP/host/SDK retry admission with disposable state and synthetic transports."""

from dataclasses import replace
from uuid import uuid4
import pytest
from application_state.agent_conversation import AgentConversationService
from application_state.agent_conversation import retry
from application_state.agent_conversation.build_draft_context import (
    BuildDraftSnapshotV1,
    BuildDraftContextRequestV1,
)
from apps.live_control_server.models.agent_turn import AgentTurnRequest
from apps.live_control_server.services import build_document_proposal as proposals
from apps.live_control_server.services.agent_turn_service import AgentTurnServiceError
from apps.live_control_server.services.build_jev_harness import BuildJevHarness
from tests.test_agent_build_jev_ordinary_harness import (
    build_case as _build_case,
    ordinary_case,
    DecisionWire,
    WriterWire,
)
from tests.test_agent_build_governed_graph import execute
from tests.test_build_jev_estimated_continuations import counter


@pytest.fixture
def failed_case(tmp_path, monkeypatch, application_state_dsn):
    case = _build_case.__wrapped__(tmp_path, monkeypatch, application_state_dsn)
    (source, request, bootstrap), _ = ordinary_case(case, monkeypatch, authoring=True)
    cap = request.build_write_capability
    cap = cap.model_copy(
        update={"basis": cap.basis.model_copy(update={"editor_sha256": "b" * 64})}
    )
    snap = BuildDraftSnapshotV1(
        **{
            k: getattr(cap.basis, k)
            for k in (
                "world_id",
                "document_id",
                "registry_revision",
                "content_sha256",
                "visibility",
                "draft_sha256",
                "editor_sha256",
                "draft_generation",
            )
        },
        draft_markdown=cap.draft_markdown,
    )
    draft = BuildDraftContextRequestV1(
        snapshot=snap,
        conversation_id=cap.conversation_id,
        expected_pointer_revision=cap.expected_pointer_revision,
    )
    request = AgentTurnRequest.model_validate(
        {
            **request.model_dump(mode="json", by_alias=True),
            "build_write_capability": cap.model_dump(mode="json"),
            "build_draft_context": draft.model_dump(mode="json", by_alias=True),
        }
    )
    bootstrap = replace(bootstrap, completed_discovery_query=request.message)
    submissions = []
    accept = AgentConversationService.accept_turn

    def retain(self, submission):
        submissions.append(submission)
        return accept(self, submission)

    monkeypatch.setattr(AgentConversationService, "accept_turn", retain)
    original = proposals._result

    def fail(raw):
        original(raw)
        raise proposals.BuildComposeError("controlled_retry_test")

    monkeypatch.setattr(proposals, "_result", fail)
    decisions, writer = DecisionWire(operation="propose_build_insertion"), WriterWire()

    def harness():
        return BuildJevHarness(
            world_context=True,
            named_citations=True,
            decision_transport=decisions,
            writer_transport=writer,
            accounting=counter(),
        )

    with pytest.raises(AgentTurnServiceError) as caught:
        execute((source, request, bootstrap), tmp_path, harness())
    service = AgentConversationService()
    parent = service.list_turns("elderwyld", cap.conversation_id)[0]
    assert parent.status == "interrupted" and len(writer.calls) == 1, repr(
        caught.value.__cause__
    )
    assert retry.read_context(
        parent.world_id, parent.conversation_id, [parent.turn_id]
    )["turns"][0]["context"]["eligible"]
    monkeypatch.setattr(proposals, "_result", original)
    return source, request, bootstrap, parent, submissions[0], harness, writer


def test_real_host_retry_has_one_edge_and_exact_delivery_replay(failed_case, tmp_path):
    source, request, bootstrap, parent, _, harness, writer = failed_case
    request = AgentTurnRequest.model_validate(
        {
            **request.model_dump(mode="json", by_alias=True),
            "turn_id": str(uuid4()),
            "build_write_capability": {
                **request.build_write_capability.model_dump(mode="json"),
                "idempotency_key": str(uuid4()),
            },
            "retry_of": {"turn_id": str(parent.turn_id), "revision": parent.revision},
        }
    )
    response = execute((source, request, bootstrap), tmp_path, harness())
    service = AgentConversationService()
    turns = service.list_turns(parent.world_id, parent.conversation_id)
    assert [t.status for t in turns] == ["interrupted", "completed"]
    contexts = retry.read_context(
        parent.world_id, parent.conversation_id, [t.turn_id for t in turns]
    )["turns"]
    assert contexts[0]["context"]["successor_id"] == str(turns[1].turn_id)
    assert (
        contexts[1]["context"]["root_id"] == str(parent.turn_id)
        and contexts[1]["context"]["ordinal"] == 1
    )
    assert not any(x["context"]["eligible"] for x in contexts)
    replay = execute((source, request, bootstrap), tmp_path, harness())
    assert (
        replay.knowledge_context.completion == response.knowledge_context.completion
        and len(writer.calls) == 2
    )
    assert len(service.list_turns(parent.world_id, parent.conversation_id)) == 2


def test_ineligible_predecessor_reaches_no_provider(failed_case, tmp_path):
    source, request, bootstrap, parent, _, harness, writer = failed_case
    request = AgentTurnRequest.model_validate(
        {
            **request.model_dump(mode="json", by_alias=True),
            "turn_id": str(uuid4()),
            "build_write_capability": {
                **request.build_write_capability.model_dump(mode="json"),
                "idempotency_key": str(uuid4()),
            },
            "retry_of": {
                "turn_id": str(parent.turn_id),
                "revision": parent.revision + 1,
            },
        }
    )
    controller_calls = len(harness().decision_transport.calls)
    with pytest.raises(AgentTurnServiceError) as failure:
        execute((source, request, bootstrap), tmp_path, harness())
    assert failure.value.code == "build_retry_unavailable"
    assert failure.value.provider_dispatched is False
    assert len(harness().decision_transport.calls) == controller_calls
    assert len(writer.calls) == 1
