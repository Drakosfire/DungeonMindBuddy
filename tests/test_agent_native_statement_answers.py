"""Native context through actual Core/WK and the ordinary APP/provider boundary."""

import pytest
from tests.test_source_statements import lane as lane
from tests.test_source_statements import commit, GM
from apps.live_control_server.services.native_statement_answer_context import (
    build_frame,
    header,
)
from graph_memory.ingestion.selection_context import NativeStatementSelectionV1


def selection_for(lane):
    h = header(
        lane.repo.get_revision(
            lane.world.world_id,
            lane.repo.get_head(lane.world.world_id).head_revision_id,
        )
    )
    return NativeStatementSelectionV1(
        managed_world_id=lane.selection.managed_world_id,
        campaign_id="c1",
        revision_id=h["revision_id"],
        subject_id=lane.ids["B"],
        domain_ref=h["domain_ref"],
        profile_ref=h["profile_ref"],
    )


def test_native_frame_contains_actual_source_and_original_publication(lane):
    packet, publication = commit(lane)
    frame = build_frame(selection_for(lane), GM)
    assert frame.status == "complete"
    (support,) = frame.supports
    assert support.payload == packet.envelope["payload"]
    assert support.publication_receipt == publication["result"]["receipt"]
    assert support.source_revision_id != frame.revision_id
    assert support.clause_text == support.payload["quote"]
    assert support.ancestry[0]["revision_id"] == frame.revision_id


class Wire:
    def __init__(self, *, on_enter=None, failure=False, alter_output=None):
        import httpx

        outer = self

        class Transport(httpx.AsyncBaseTransport):
            async def handle_async_request(self, request):
                import json

                outer.requests.append(json.loads(request.content))
                if on_enter:
                    on_enter()
                if failure:
                    raise httpx.ReadTimeout(
                        "synthetic native outcome unknown", request=request
                    )
                frame = json.loads(outer.requests[-1]["input"][0]["content"])[
                    "native_statement_context"
                ]
                identity = frame["supports"][0]["statement_id"]
                raw = json.dumps(
                    {
                        "segments": [
                            {
                                "kind": "source_report",
                                "text": "A reports that B fled, but the account remains uncertain.",
                                "statement_ids": [identity],
                            }
                        ]
                    }
                )
                if alter_output:
                    raw = json.dumps(alter_output(json.loads(raw)))
                return httpx.Response(
                    200,
                    request=request,
                    json={
                        "id": "resp_native_test",
                        "object": "response",
                        "created_at": 1,
                        "status": "completed",
                        "model": "gpt-6-luna",
                        "service_tier": "fast",
                        "output": [
                            {
                                "type": "message",
                                "id": "msg_native_test",
                                "role": "assistant",
                                "status": "completed",
                                "content": [
                                    {
                                        "type": "output_text",
                                        "text": raw,
                                        "annotations": [],
                                    }
                                ],
                            }
                        ],
                        "usage": {
                            "input_tokens": 100,
                            "output_tokens": 80,
                            "total_tokens": 180,
                        },
                    },
                )

            async def aclose(self):
                pass

        self.requests = []
        self.transport = Transport()


def native_client(lane, monkeypatch, tmp_path, wire):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from apps.live_control_server.routes import agent

    monkeypatch.setenv("DMB_AGENT_GRAPH_AUTH_MODE", "local_operator")
    monkeypatch.setenv("DMB_AGENT_GRAPH_AUTH_ENVIRONMENT", "local")
    monkeypatch.setenv(
        "DMB_AGENT_GRAPH_LOCAL_OPERATOR_TOKEN", "synthetic-native-test-token-1234567890"
    )
    monkeypatch.setenv("OPENAI_API_KEY", "synthetic-no-network")
    monkeypatch.setattr(agent, "repo_root", lambda: tmp_path)
    monkeypatch.setattr(agent, "session_dir", lambda: tmp_path / "sessions")
    monkeypatch.setattr(
        agent,
        "_owner_resolver",
        lambda request: {
            "kind": "world",
            "id": lane.selection.managed_world_id,
            "name": "Synthetic World",
        },
    )
    monkeypatch.setattr(agent, "_verified_world_id", lambda world: world)
    monkeypatch.setattr(agent, "_work_resolver", lambda request, owner: None)
    monkeypatch.setattr(
        agent,
        "_graph_resolver",
        lambda *args: pytest.fail("Native context must not consult classic Graph"),
    )
    app = FastAPI()
    app.state.native_statement_writer_transport = wire.transport
    app.include_router(agent.router, prefix="/api/live")
    return TestClient(
        app,
        client=("127.0.0.1", 42000),
        headers={"Authorization": "Bearer synthetic-native-test-token-1234567890"},
    )


def request_for(lane):
    world = lane.selection.managed_world_id
    return {
        "schema": "dmb_agent_turn_request_v1",
        "client_thread_id": "native-test-thread",
        "turn_id": "native-test-turn",
        "surface": {"surface_id": "plan", "instance_id": "native-question"},
        "owner_scope": {"kind": "world", "world_id": world},
        "primary_work": None,
        "client_work_state": "none",
        "graph_request": {"mode": "none"},
        "graph_selection": None,
        "native_statement_selection": selection_for(lane).model_dump(
            mode="json", by_alias=True
        ),
        "message": "What did the report say happened to B?",
    }


def test_ordinary_post_persists_and_reopens_exact_native_clause(
    lane, application_state_dsn, monkeypatch, tmp_path
):
    from application_state.agent_conversation import AgentConversationService
    from tests.test_source_statements import advance

    commit(lane)
    wire = Wire()
    client = native_client(lane, monkeypatch, tmp_path, wire)
    world = lane.selection.managed_world_id
    request = request_for(lane)
    response = client.post("/api/live/agent/turn", json=request)
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["answer"]["graph_grounded"] is False
    assert data["answer"]["text"].startswith("Source reports:")
    assert len(wire.requests) == 1
    service = AgentConversationService()
    (turn,) = service.list_turns(
        world, service.get_active_conversation(world).conversation_id
    )
    assert turn.status == "completed"
    assert turn.completion.schema_ == "dmb_native_statement_completion_v1"
    advance(lane)
    opened = client.get(
        f"/api/live/agent/worlds/{world}/conversation/turns/{turn.turn_id}/native-source-clauses/0"
    )
    assert opened.status_code == 200, opened.text
    assert (
        opened.json()["content"]
        == turn.graph_context_receipt.frame.supports[0].clause_text
    )
    from apps.live_control_server.services import native_statement_answer_runtime

    monkeypatch.setattr(
        native_statement_answer_runtime,
        "build_frame",
        lambda *args: pytest.fail("Completed replay must not reload current context"),
    )
    replay = client.post("/api/live/agent/turn", json=request)
    assert replay.status_code == 200, replay.text
    assert replay.json()["answer"]["text"] == data["answer"]["text"]
    assert len(wire.requests) == 1
    history = client.get(
        f"/api/live/agent/worlds/{world}/conversation?include_turn_correlation=true"
    )
    assert history.status_code == 200, history.text
    assert (
        history.json()["turns"][0]["native_statement_context"]["completion"]
        == data["native_statement_context"]["completion"]
    )


@pytest.mark.parametrize(
    "mutation",
    [
        "world",
        "revision",
        "campaign",
        "fullref",
        "classic_id",
        "classic_scope",
        "ingest",
        "build",
    ],
)
def test_native_request_scope_refuses_before_provider(
    lane, application_state_dsn, monkeypatch, tmp_path, mutation
):
    commit(lane)
    wire = Wire()
    client = native_client(lane, monkeypatch, tmp_path, wire)
    request = request_for(lane)
    selection = request["native_statement_selection"]
    if mutation == "world":
        selection["managedWorldId"] = "other-world"
    if mutation == "revision":
        selection["revisionId"] = "rev:unavailable"
    if mutation == "campaign":
        selection["campaignId"] = "other-campaign"
    if mutation == "fullref":
        selection["domainRef"]["descriptor_sha256"] = "0" * 64
    if mutation == "classic_id":
        selection["subjectId"] = "item:meat-sample"
    if mutation == "classic_scope":
        request["graph_request"] = {
            "mode": "world",
            "world_id": lane.selection.managed_world_id,
            "revision_pin": None,
            "focus": {"kind": "none", "session_id": None},
        }
    if mutation == "ingest":
        request["surface"]["surface_id"] = "ingest"
    if mutation == "build":
        request["surface"]["surface_id"] = "build"
    response = client.post("/api/live/agent/turn", json=request)
    assert response.status_code in {403, 409, 422}, response.text
    assert not wire.requests


def test_native_unknown_outcome_is_retained_without_redispatch(
    lane, application_state_dsn, monkeypatch, tmp_path
):
    from application_state.agent_conversation import AgentConversationService

    commit(lane)
    wire = Wire(failure=True)
    client = native_client(lane, monkeypatch, tmp_path, wire)
    request = request_for(lane)
    response = client.post("/api/live/agent/turn", json=request)
    assert response.status_code == 502, response.text
    service = AgentConversationService()
    world = lane.selection.managed_world_id
    (turn,) = service.list_turns(
        world, service.get_active_conversation(world).conversation_id
    )
    assert turn.status == "interrupted"
    assert turn.graph_context_execution.events[-1].outcome == "outcome_unknown"
    assert len(wire.requests) == 1
    # Missing/changed current source must not prompt a new call or replace this attempt.
    monkeypatch.setattr(
        lane.repo,
        "get_head",
        lambda *a: pytest.fail("Unknown outcome cannot consult current head"),
    )
    response = client.post("/api/live/agent/turn", json=request)
    assert response.status_code == 409, response.text
    assert len(wire.requests) == 1


def test_completion_policy_rejects_plain_result_even_without_completion(
    lane, application_state_dsn, monkeypatch, tmp_path
):
    from application_state.agent_conversation import AgentConversationService
    from application_state.agent_conversation.types import TurnResult
    from application_state.errors import ApplicationStateValidationError

    commit(lane)
    service = AgentConversationService()
    world = lane.selection.managed_world_id
    rejected = []

    def attack():
        (turn,) = service.list_turns(
            world, service.get_active_conversation(world).conversation_id
        )
        assert turn.status == "running"
        with pytest.raises(
            ApplicationStateValidationError, match="Frozen native policy"
        ):
            service.complete_turn(
                TurnResult(
                    world_id=world,
                    conversation_id=turn.conversation_id,
                    turn_id=turn.turn_id,
                    expected_revision=turn.revision,
                    assistant_text="Unsupported World fact",
                )
            )
        rejected.append(True)

    wire = Wire(on_enter=attack)
    client = native_client(lane, monkeypatch, tmp_path, wire)
    response = client.post("/api/live/agent/turn", json=request_for(lane))
    assert response.status_code == 200, response.text
    assert rejected == [True]


def test_unincluded_or_world_fact_output_cannot_complete(
    lane, application_state_dsn, monkeypatch, tmp_path
):
    from application_state.agent_conversation import AgentConversationService

    commit(lane)
    wire = Wire(
        alter_output=lambda output: {
            "segments": [
                {
                    "kind": "source_report",
                    "text": "Unsupported",
                    "statement_ids": ["ent:unincluded"],
                }
            ]
        }
    )
    client = native_client(lane, monkeypatch, tmp_path, wire)
    response = client.post("/api/live/agent/turn", json=request_for(lane))
    assert response.status_code == 502, response.text
    service = AgentConversationService()
    world = lane.selection.managed_world_id
    (turn,) = service.list_turns(
        world, service.get_active_conversation(world).conversation_id
    )
    assert turn.status == "interrupted" and turn.completion is None
    assert (
        turn.graph_context_execution.events[-1].kind
        == "native_statement_output_captured_v1"
    )
    assert len(wire.requests) == 1


@pytest.mark.parametrize("hidden_reporter", [False, True])
def test_multiple_publication_children_reach_one_writer_without_episode_loss(
    lane, application_state_dsn, monkeypatch, tmp_path, hidden_reporter
):
    import hashlib
    from tests.test_source_statements import BODY, service as statements
    from apps.live_control_server.models.source_statements import ConfirmStatement

    first_packet, first = commit(lane)
    start = len(BODY.splitlines(keepends=True)[0].encode())
    end = len(BODY.encode())
    second_selection = lane.selection.model_copy(
        update={
            "expected_parent_revision_id": first["result"]["receipt"][
                "published_revision_id"
            ],
            "start_byte": start,
            "end_byte": end,
            "clause_sha256": hashlib.sha256(BODY.encode()[start:end]).hexdigest(),
            "meaning": "Another source-local episode is recorded",
            "mode": "narrator",
            "reporter": None,
            "uncertainty": [],
            "qualifications": {"source_local": "separate episode"},
            "episode": "episode-2",
        }
    )
    prepared = statements.prepare(second_selection, GM)
    second = statements.confirm(
        ConfirmStatement(**{k: prepared[k] for k in ("envelope", "prepared", "token")}),
        GM,
    )

    if hidden_reporter:
        from dataclasses import replace
        from tests.test_source_statements import mapping

        original = statements.EntityReadService.get_complete_entity
        first_id = first["result"]["bundle"]["statement_id"]

        def scoped_read(self, context, entity_id):
            value = original(self, context, entity_id)
            if entity_id == first_id:
                value = replace(
                    value,
                    assertions=tuple(
                        a
                        for a in value.assertions
                        if a.predicate != mapping.REPORTED_BY
                    ),
                )
            return value

        monkeypatch.setattr(
            statements.EntityReadService, "get_complete_entity", scoped_read
        )

    def combined(output):
        # A fixture writer exercises cross-source synthesis; this is transport
        # proof, not a model-quality or Q13 score claim.
        frame = build_frame(selection_for(lane), GM)
        return {
            "segments": [
                {
                    "kind": "source_report",
                    "text": "One account reports B fled with uncertainty; another episode is separately recorded, without an established causal connection.",
                    "statement_ids": [s.statement_id for s in frame.supports],
                }
            ]
        }

    wire = Wire(alter_output=combined)
    client = native_client(lane, monkeypatch, tmp_path, wire)
    response = client.post("/api/live/agent/turn", json=request_for(lane))
    assert response.status_code == 200, response.text
    frame = response.json()["native_statement_context"]["receipt"]["frame"]
    if hidden_reporter:
        assert len(frame["supports"]) == 1
        assert frame["status"] == "partial"
        assert frame["gap_codes"] == ["statement_bundle_unavailable"]
        assert frame["universal_absence_claimed"] is False
        completion = response.json()["native_statement_context"]["completion"]
        assert completion["answer_context_status"] == "source_attributed_partial"
        assert len(completion["native_clause_citations"]) == 1
        assert frame["supports"][0]["payload"]["episode"] == "episode-2"
        assert len(wire.requests) == 1
        return
    assert len(frame["supports"]) == 2
    assert {s["payload"]["episode"] for s in frame["supports"]} == {
        "episode-1",
        "episode-2",
    }
    assert {
        s["publication_receipt"]["published_revision_id"] for s in frame["supports"]
    } == {
        first["result"]["receipt"]["published_revision_id"],
        second["result"]["receipt"]["published_revision_id"],
    }
    assert frame["revision_id"] == second["result"]["receipt"]["published_revision_id"]
    assert any(len(s["ancestry"]) == 2 for s in frame["supports"])
    citations = response.json()["native_statement_context"]["completion"][
        "native_clause_citations"
    ]
    assert len(citations) == 2
    assert first_packet.envelope["payload"]["reporter"] is not None
