import hashlib
import json
import pytest
from application_state.agent_conversation.types import (
    SubmittedTurnIntentV1,
    submitted_turn_intent_fingerprint_v1,
)
from apps.live_control_server.services.agent_turn_service import (
    _plan_message,
    AgentTurnServiceError,
)
from apps.live_control_server.services.agent_plan_context import selected_scene_markdown
from application_state.agent_conversation.types import PlanPlayableTargetReceiptV1
from apps.live_control_server.models.agent_turn import AgentTurnContentBasis

DOC = "<!-- dmb-playable-element:v1 kind=scene id=scene:first -->\n## First\nHello\n### Detail\nInside\n<!-- dmb-playable-element:v1 kind=scene id=scene:second -->\n## Second\nSecret second\n"


def test_scene_extraction_preserves_nested_text_and_excludes_next_marker():
    text = selected_scene_markdown(DOC, "scene:first")
    assert (
        "Inside" in text and "Secret second" not in text and "scene:second" not in text
    )


def test_scene_extraction_ignores_fenced_headings():
    text = selected_scene_markdown(
        DOC.replace("Hello", "```\n## fake\n```\nHello"), "scene:first"
    )
    assert "Hello" in text and "Inside" in text


def test_message_only_does_not_include_plan():
    assert _plan_message("Test", "x" * 48000, context_mode="message_only") == "Test"


def test_whole_plan_preview_reports_full_message_and_send_guard_rejects():
    text = _plan_message("Test", "x" * 48000, enforce_budget=False)
    assert len(text) > 8000 and "x" * 48000 in text
    with pytest.raises(AgentTurnServiceError, match="too large"):
        _plan_message("Test", "x" * 48000)


def test_selected_scene_requires_target():
    with pytest.raises(AgentTurnServiceError):
        _plan_message("Test", DOC, context_mode="selected_scene")


@pytest.mark.parametrize(
    "target",
    [
        None,
        {"schema": "dmb_plan_playable_target_v1", "kind": "scene", "id": "scene:first"},
    ],
)
def test_default_mode_preserves_previous_canonical_fingerprint(target):
    payload = {
        "world_id": "elderwyld",
        "client_thread_id": "client",
        "message": "Test",
        "surface_id": "plan",
        "surface_instance_id": "plan",
        "client_work_state": "saved_clean",
        "primary_work": {
            "kind": "plan",
            "object_id": "doc",
            "expected_revision": 5,
            "expected_revision_n": 5,
            "expected_content_sha256": "a" * 64,
        },
        "playable_target": target,
        "graph_request": {"mode": "none"},
        "graph_selection": None,
    }
    intent = SubmittedTurnIntentV1.model_validate(payload)
    canonical = intent.model_dump(
        mode="json", by_alias=True, exclude={"client_thread_id"}
    )
    canonical.pop("plan_context_mode")
    if target is None:
        canonical.pop("playable_target")
    expected = hashlib.sha256(
        json.dumps(
            canonical, sort_keys=True, separators=(",", ":"), ensure_ascii=False
        ).encode()
    ).hexdigest()
    assert submitted_turn_intent_fingerprint_v1(intent) == expected
    assert (
        submitted_turn_intent_fingerprint_v1(
            intent.model_copy(update={"plan_context_mode": "message_only"})
        )
        != expected
    )


def test_selected_scene_message_is_pinned_and_bounded():
    basis = AgentTurnContentBasis(
        world_id="elderwyld",
        document_id="doc",
        object_revision=5,
        work_revision_id="00000000-0000-0000-0000-000000000001",
        revision_n=5,
        content_sha256="a" * 64,
        committed_status="committed",
        has_divergent_working_copy=False,
    )
    target = PlanPlayableTargetReceiptV1(
        schema="dmb_plan_playable_target_receipt_v1",
        kind="scene",
        id="scene:first",
        marker_grammar_version="v1",
    )
    message = _plan_message(
        "Test",
        DOC,
        playable_target=target,
        content_basis=basis,
        context_mode="selected_scene",
    )
    assert "Inside" in message and "Secret second" not in message
    assert (
        json.loads(message.split("\n", 1)[1])["focus_metadata"]["work_revision"][
            "revision_n"
        ]
        == 5
    )


def preview_request():
    from apps.live_control_server.models.agent_turn import AgentTurnRequest

    return AgentTurnRequest.model_validate(
        {
            "schema": "dmb_agent_turn_request_v1",
            "client_thread_id": "client",
            "turn_id": "turn",
            "surface": {"surface_id": "plan", "instance_id": "plan"},
            "owner_scope": {"kind": "world", "world_id": "elderwyld"},
            "primary_work": {
                "kind": "plan",
                "object_id": "doc",
                "expected_revision": 5,
                "expected_revision_n": 5,
                "expected_content_sha256": "a" * 64,
            },
            "client_work_state": "saved_clean",
            "graph_request": {"mode": "none"},
            "graph_selection": None,
            "message": "Test",
            "plan_context_mode": "message_only",
        }
    )


def test_preview_auth_runs_first_and_never_executes_provider(monkeypatch):
    from fastapi import HTTPException
    from apps.live_control_server.routes import agent

    calls = []

    def deny(request):
        calls.append("auth")
        raise HTTPException(401)

    monkeypatch.setattr(agent, "enforce_native_graph_gm", deny)
    monkeypatch.setattr(
        agent, "execute_agent_turn", lambda *a, **k: pytest.fail("provider called")
    )
    monkeypatch.setattr(agent, "_owner_resolver", lambda *a: calls.append("owner"))
    with pytest.raises(HTTPException) as error:
        agent.preview_plan_context(preview_request(), None)
    assert error.value.status_code == 401 and calls == ["auth"]


def test_preview_matches_send_message_without_claiming_turn(monkeypatch):
    from types import SimpleNamespace
    from apps.live_control_server.routes import agent

    basis = AgentTurnContentBasis(
        world_id="elderwyld",
        document_id="doc",
        object_revision=5,
        work_revision_id="revision",
        revision_n=5,
        content_sha256="a" * 64,
        committed_status="committed",
        has_divergent_working_copy=False,
    )
    monkeypatch.setattr(agent, "enforce_native_graph_gm", lambda r: None)
    monkeypatch.setattr(
        agent, "_owner_resolver", lambda b: {"kind": "world", "id": "elderwyld"}
    )
    monkeypatch.setattr(
        agent,
        "_work_resolver",
        lambda b, o: SimpleNamespace(plan_markdown=DOC, content_basis=basis),
    )
    monkeypatch.setattr(
        agent, "execute_agent_turn", lambda *a, **k: pytest.fail("turn claimed")
    )
    result = agent.preview_plan_context(preview_request(), None)
    assert result["message"] == _plan_message(
        "Test", DOC, content_basis=basis, context_mode="message_only"
    )
    assert result["characters"] == 4


@pytest.mark.parametrize("mode", ["message_only", "selected_scene"])
def test_preview_matches_provider_bound_plan_message(tmp_path, mode):
    from tests.test_agent_turn_service import (
        _pinned_plan_request,
        _pinned_plan_work,
        FakeRuntime,
    )
    from application_state.agent_conversation.types import SubmittedPlanPlayableTargetV1
    from apps.live_control_server.services.agent_turn_service import execute_agent_turn
    from apps.live_control_server.services.hermes_session_store import (
        HermesSessionPointerStore,
    )

    markdown = DOC.replace("scene:first", "scene:arrival")
    request = _pinned_plan_request().model_copy(
        update={
            "plan_context_mode": mode,
            "message": "Test",
            "playable_target": SubmittedPlanPlayableTargetV1(
                schema="dmb_plan_playable_target_v1", kind="scene", id="scene:arrival"
            ),
        }
    )
    work = _pinned_plan_work(markdown)
    target = PlanPlayableTargetReceiptV1(
        schema="dmb_plan_playable_target_receipt_v1",
        kind="scene",
        id="scene:arrival",
        marker_grammar_version="v1",
    )
    preview = _plan_message(
        "Test",
        markdown,
        playable_target=target,
        content_basis=work.content_basis,
        context_mode=mode,
        enforce_budget=False,
    )
    runtime = FakeRuntime()
    execute_agent_turn(
        request,
        root=tmp_path,
        pointer_store=HermesSessionPointerStore(tmp_path / "pointers"),
        owner_resolver=lambda r: {"kind": "world", "id": "world:one", "name": "Test"},
        work_resolver=lambda r, o: work,
        graph_resolver=lambda *a: pytest.fail("Graph requested"),
        runtime=runtime,
    )
    assert len(runtime.invocations) == 1 and runtime.invocations[0].message == preview
