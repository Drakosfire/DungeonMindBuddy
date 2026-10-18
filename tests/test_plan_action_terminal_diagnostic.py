"""Runtime producer, Action attribution, strict vocabulary and private read tests."""
from types import SimpleNamespace
import pytest
from application_state.plan_action_dialogue.types import ActionTerminalFailureV1
from apps.live_control_server.services.plan_action_terminal_diagnostic import retain_terminal_diagnostic
from apps.live_control_server.services.hermes_graph_agent_contract import validate_terminal_failure_record
from tests.application_state.test_plan_action_prompt_capture import frozen


@pytest.fixture
def application_state_dsn(monkeypatch):
    from tests.application_state import test_plan_action_consultation as cases
    yield from cases.application_state_dsn.__wrapped__(monkeypatch)


FAILURE = dict(phase="provider_lifecycle", reason="provider_transport_ambiguous",
    transition="outcome_unknown", acknowledged=True, transportExceptionClass="ReadTimeout")


@pytest.mark.parametrize("change", [{}, {"acknowledged": 1}, {"secret": "PRIVATE"},
    {"reason": "invented"}, {"transition": "known_not_sent"}, {"responseStatus": "failed"},
    {"transportExceptionClass": "SecretException"}, {"incompleteReason": "length"},
    {"reason": "lifecycle_ack_denied", "transportExceptionClass": None},
    {"reason": "provider_response_incomplete", "transportExceptionClass": None, "responseStatus": "incomplete", "incompleteReason": "length"}])
def test_app_and_actual_runtime_sanitizer_agree(change):
    value = {**FAILURE, **change}
    expected = validate_terminal_failure_record(value)
    try:
        actual = ActionTerminalFailureV1.model_validate(value).model_dump(exclude_none=True)
    except ValueError:
        actual = None
    assert actual == expected


def adapter(store, action, witness=None, generation=1):
    return SimpleNamespace(store=store, stop=lambda: action, turn=action, fence=None,
        failure=None, terminal_callback=witness, authorization_generation=generation)


@pytest.mark.parametrize("diagnostic,expected", [
    ({"reason": "provider_transport_ambiguous", "transition": "outcome_unknown", "acknowledged": True,
      "transport_exception_class": "ReadTimeout"}, "captured"),
    ({"reason": "PRIVATE_BAD_REASON", "transition": "outcome_unknown", "acknowledged": True}, "invalid_reported_by_host"),
    (None, "missing_or_not_retained"),
])
def test_actual_hosted_normalizer_then_runtime_mapper_then_fenced_app(application_state_dsn, tmp_path, diagnostic, expected):
    from apps.live_control_server.services.hermes_graph_agent import (
        HermesGraphAgentTurnRequest, run_hermes_graph_agent_turn,
    )
    from graph_memory.hermes_graph_plugin import default_conversation_only_capability_policy
    from apps.live_control_server.services.hermes_agent_runtime import map_hermes_result_to_runtime_result
    class FailedAgent:
        def __init__(self, **kwargs):
            self.session_id = kwargs.get("session_id")
        def run_conversation(self, *args, **kwargs):
            return dict(messages=[], failure_reason="request_budget_veto",
                failure_code="provider_lifecycle_unavailable", failure_diagnostic=diagnostic)
    raw = run_hermes_graph_agent_turn(HermesGraphAgentTurnRequest(
        question="Synthetic retention witness", world_id=None, campaign_id=None, scope_mode=None,
        root=tmp_path, capability_policy=default_conversation_only_capability_policy(),
        request_budget={"schema": "dmb_hermes_request_budget_policy_v1", "provider": "openai-api",
            "model": "synthetic-model", "apiMode": "chat_completions",
            "estimator": "utf8_json_bytes_plus_64_per_node_v1", "contextLimitTokens": 32768,
            "outputReserveTokens": 1024}), agent_factory=FailedAgent)
    assert raw.status == "error"
    result = map_hermes_result_to_runtime_result(raw)
    store, action, _, _ = frozen()
    saved = retain_terminal_diagnostic(adapter(store, action), result)
    report = saved.consultation.terminal_diagnostic
    assert report.attribution == "action_only"
    assert (report.availability if report.availability == "captured" else report.unavailable_reason) == expected
    assert "PRIVATE_BAD_REASON" not in report.model_dump_json()
    assert store.read_prompt_action(world_id=action.basis.world_id, action_id=action.action_id).consultation == saved.consultation


@pytest.mark.parametrize("witness", [None, {"generation": 1, "transition": "response_received", "parent_acknowledged": True},
    {"generation": 0, "transition": "outcome_unknown", "parent_acknowledged": True}])
def test_no_failure_callback_or_superseded_generation_never_blames_previous_call(application_state_dsn, witness):
    from apps.live_control_server.services.agent_runtime import AgentRuntimeResult
    store, action, _, _ = frozen()
    result = AgentRuntimeResult(status="error", final_text=None, error_code="request_budget_veto",
        runtime_metadata={"terminal_failure": FAILURE})
    saved = retain_terminal_diagnostic(adapter(store, action, witness), result)
    report = saved.consultation.terminal_diagnostic
    assert report.attribution == "action_only" and report.provider_attempt_id is None


def test_retention_storage_failure_preserves_original_action(application_state_dsn):
    from apps.live_control_server.services.agent_runtime import AgentRuntimeResult
    store, action, _, _ = frozen()
    def refuse(**kwargs):
        raise RuntimeError("PRIVATE_STORAGE_ERROR")
    fake = SimpleNamespace(append_terminal_diagnostic=refuse)
    result = AgentRuntimeResult(status="error", final_text=None, runtime_metadata={"terminal_failure": FAILURE})
    assert retain_terminal_diagnostic(adapter(fake, action), result) is action
    assert not hasattr(store.read_prompt_action(world_id=action.basis.world_id, action_id=action.action_id).consultation, "terminal_diagnostic")


def test_mounted_diagnostic_read_requires_auth_owner_and_exact_selector(application_state_dsn, monkeypatch):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from apps.live_control_server.routes import live
    from tests.application_state.test_plan_action_terminal_diagnostic import diagnostic, retain
    store, action, _, _ = frozen()
    action, _ = retain(store, action, diagnostic(action))
    monkeypatch.setenv("DMB_AGENT_GRAPH_AUTH_MODE", "local_operator")
    monkeypatch.setenv("DMB_AGENT_GRAPH_AUTH_ENVIRONMENT", "local")
    monkeypatch.setenv("DMB_AGENT_GRAPH_LOCAL_OPERATOR_TOKEN", "x" * 40)
    monkeypatch.setattr(live, "get_world_container", lambda root, world: SimpleNamespace(world_id=world))
    monkeypatch.setattr(live, "managed_world_data_root", lambda root: root)
    app = FastAPI(); app.include_router(live.router)
    client = TestClient(app, client=("127.0.0.1", 12345))
    path = f"/api/live/world-plan-edit/actions/{action.action_id}/terminal-diagnostic"
    assert client.get(path, params={"world_id": action.basis.world_id}).status_code == 401
    headers = {"Authorization": "Bearer " + "x" * 40}
    response = client.get(path, params={"world_id": action.basis.world_id}, headers=headers)
    assert response.status_code == 200
    assert response.json()["diagnostic"]["unavailable_reason"] == "missing_or_not_retained"
    assert "dispatch_fence" not in response.text
    assert response.headers["cache-control"] == "no-store" and response.headers["pragma"] == "no-cache"
    for query, status in (("world_id=other-world", 404), ("world_id=synthetic-world&world_id=synthetic-world", 422),
                          ("world_id=synthetic-world&blob=forged", 422)):
        assert client.get(path + "?" + query, headers=headers).status_code == status
    old = frozen()[1]
    response = client.get(f"/api/live/world-plan-edit/actions/{old.action_id}/terminal-diagnostic?world_id=synthetic-world", headers=headers)
    assert response.status_code == 200 and response.json()["diagnostic"] is None


def test_action_authorization_generation_clears_prior_callback_even_on_refusal(monkeypatch):
    from apps.live_control_server.services.plan_action_consultation import ActionPolicyExecutionAdapter
    from apps.live_control_server.services.agent_turn_service import _PolicyExecutionAdapter
    action = ActionPolicyExecutionAdapter.__new__(ActionPolicyExecutionAdapter)
    action.authorization_generation = 1
    action.terminal_callback = {"generation": 1, "transition": "outcome_unknown"}
    def refuse(self, view):
        assert self.authorization_generation == 2 and self.terminal_callback is None
        raise ValueError("synthetic denied authorization")
    monkeypatch.setattr(_PolicyExecutionAdapter, "authorize", refuse)
    with pytest.raises(ValueError):
        action.authorize({})
    assert action.authorization_generation == 2 and action.terminal_callback is None


@pytest.mark.parametrize("refuse_callback", [False, True])
def test_actual_action_callback_records_only_current_attempt(application_state_dsn, refuse_callback):
    from apps.live_control_server.services.plan_action_consultation import ActionPolicyExecutionAdapter, _ActionFence
    from apps.live_control_server.services.agent_runtime import AgentRuntimeResult
    from tests.application_state.test_plan_action_prompt_capture import append
    from application_state.errors import ApplicationStateValidationError
    store, action, _, events = frozen()
    for event in events[:8]:
        action = append(store, action, event)
    original = store.append_consultation_event
    if refuse_callback:
        def refuse(**kwargs):
            raise ApplicationStateValidationError("synthetic lifecycle refusal")
        store.append_consultation_event = refuse
    actual = ActionPolicyExecutionAdapter.__new__(ActionPolicyExecutionAdapter)
    actual.store = store
    actual.fence = _ActionFence(store, action)
    actual.turn = action
    actual.last_provider_attempt_id = events[6].provider_attempt_id
    actual.producing_provider_attempt_id = None
    actual.authorization_generation = 2
    actual.terminal_callback = None
    actual.failure = None
    actual.context_capture = None
    actual.budget = {}
    assert actual.record_lifecycle({"transition": "outcome_unknown"}) is (not refuse_callback)
    store.append_consultation_event = original
    failure = {**FAILURE, "acknowledged": not refuse_callback}
    saved = retain_terminal_diagnostic(actual, AgentRuntimeResult(status="error", final_text=None,
        runtime_metadata={"terminal_failure": failure}))
    report = saved.consultation.terminal_diagnostic
    assert report.attribution == "provider_attempt"
    assert report.provider_attempt_id == events[6].provider_attempt_id
    assert report.authorization_event_id == events[6].event_id
    assert report.parent_acknowledged is (not refuse_callback)
    assert report.latest_durable_outcome == ("sdk_entered" if refuse_callback else "outcome_unknown")
    assert (report.matching_transition_event_id is None) == refuse_callback
