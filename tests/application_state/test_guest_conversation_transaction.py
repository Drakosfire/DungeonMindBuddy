from contextlib import contextmanager
from datetime import datetime, timezone
from uuid import uuid4

import pytest

from application_state.agent_conversation import service as conversation
from application_state.errors import ApplicationStateConflictError
from apps.live_control_server.services.guest_build_access import _check_guest_session
from apps.live_control_server.services.guest_build_access import matches_guest_conversation_route
from types import SimpleNamespace
from fastapi import HTTPException


def test_guest_conversation_route_matching_is_narrow():
    path = f"/api/live/agent/worlds/guest-{uuid4().hex}/conversation"
    assert matches_guest_conversation_route("GET", path)
    assert matches_guest_conversation_route("POST", path + "/new")
    assert not matches_guest_conversation_route("POST", path)
    assert not matches_guest_conversation_route("GET", path + "/new")
    assert not matches_guest_conversation_route("GET", path + "/turns/1/context-trace")
    assert not matches_guest_conversation_route("GET", "/api/live/agent/worlds/private/conversation")


def test_transaction_authorization_precedes_access_and_denial_rolls_back(monkeypatch):
    events = []
    connection = object()

    @contextmanager
    def transaction(_dsn):
        events.append("begin")
        try:
            yield connection
        except Exception:
            events.append("rollback")
            raise
        else:
            events.append("commit")

    def reject(conn, *, read_only):
        assert conn is connection and not read_only
        events.append("authorize")
        raise ValueError("expired session")

    monkeypatch.setattr(conversation, "unit_of_work", transaction)
    service = conversation.AgentConversationService(authorize_transaction=reject)
    with pytest.raises(ValueError, match="expired session"):
        with service._transaction():
            events.append("write")
    assert events == ["begin", "authorize", "rollback"]


def test_read_only_transaction_is_configured_before_authorization(monkeypatch):
    events = []

    class Connection:
        def execute(self, sql):
            events.append(sql)

    @contextmanager
    def transaction(_dsn):
        yield Connection()

    monkeypatch.setattr(conversation, "unit_of_work", transaction)
    service = conversation.AgentConversationService(
        authorize_transaction=lambda conn, *, read_only: events.append((conn, read_only))
    )
    with service._transaction(read_only=True) as connection:
        events.append("read")
    assert events == ["SET TRANSACTION READ ONLY", (connection, True), "read"]


def test_expired_session_rejects_trace_before_storage_access(monkeypatch):
    @contextmanager
    def transaction(_dsn):
        yield object()

    def reject(_conn, *, read_only):
        assert not read_only
        raise ValueError("expired session")

    monkeypatch.setattr(conversation, "unit_of_work", transaction)
    monkeypatch.setattr(conversation, "_ready_dsn", lambda: "synthetic")
    service = conversation.AgentConversationService(authorize_transaction=reject)
    with pytest.raises(ValueError, match="expired session"):
        service.start_context_trace(
            world_id="guest-test", conversation_id=uuid4(), turn_id=uuid4(),
            expected_revision=1, attempt=1, trace_id=uuid4(),
            started_at=datetime.now(timezone.utc),
        )


@pytest.mark.parametrize("lock", [True, False])
def test_guest_session_transaction_rejects_expiry_and_wrong_world(lock):
    session = uuid4()
    world = f"guest-{session.hex}"
    request = SimpleNamespace(state=SimpleNamespace(guest_build_session=str(session), guest_build_world=world))
    queries = []

    class Connection:
        def execute(self, sql, params):
            queries.append((sql, params))
            return SimpleNamespace(fetchone=lambda: None)

    with pytest.raises(ApplicationStateConflictError):
        _check_guest_session(request, Connection(), world, lock=lock)
    assert queries[0][0].endswith(" FOR UPDATE") is lock
    queries.clear()
    with pytest.raises(ApplicationStateConflictError):
        _check_guest_session(request, Connection(), "guest-other", lock=lock)
    assert not queries


def test_guest_graph_principal_is_typed_and_bound_to_session(monkeypatch):
    from apps.live_control_server.services import guest_build_access, hosted_native_graph_access as access
    from apps.live_control_server.services.agent_graph_auth import NativeGraphPrincipal

    monkeypatch.setattr(access.hosted_auth, "deployment_environment", lambda: access.hosted_auth.PRODUCTION_ENVIRONMENT)
    monkeypatch.setattr(access.hosted_auth, "auth_mode", lambda: access.hosted_auth.HOSTED_MODE)
    checked = []
    monkeypatch.setattr(guest_build_access, "require_guest_build_world", lambda request, world: checked.append(world))
    request = SimpleNamespace(state=SimpleNamespace(guest_build_session="session"))
    principal = access.HostedGuestGraphPrincipal(
        subject="hosted_guest", role="gm", auth_method="hosted_guest", managed_world_id="world",
        session_id="session", request=request,
    )
    access.require_explorer_access(principal, "world")
    assert checked == ["world"]
    with pytest.raises(HTTPException):
        access.require_explorer_access(principal, "other")
    with pytest.raises(HTTPException):
        access.require_explorer_access(NativeGraphPrincipal(subject="hosted_guest", role="gm", auth_method="hosted_guest"), "world")
    request.state.guest_build_session = "different"
    with pytest.raises(HTTPException):
        access.require_explorer_access(principal, "world")


def test_guest_graph_response_rejects_binding_change(monkeypatch):
    from apps.live_control_server.services import native_graph_explorer as explorer
    from apps.live_control_server.services.agent_graph_auth import NativeGraphPrincipal

    principal = NativeGraphPrincipal(subject="guest", role="gm", auth_method="hosted_guest")
    bindings = iter([
        {"managed_world_id": "world", "native_world_id": "first", "binding_version": 1},
        {"managed_world_id": "world", "native_world_id": "second", "binding_version": 2},
    ])
    monkeypatch.setattr(explorer, "_require_access", lambda *_: None)
    monkeypatch.setattr(explorer, "_resolve_binding", lambda _: next(bindings))
    with pytest.raises(explorer.NativeGraphExplorerError) as error:
        with explorer.hosted_response_binding(principal, "world"):
            pass
    assert error.value.code == "binding_changed"


def test_guest_turn_capacity_rejects_oversized_and_exhausted(monkeypatch):
    from apps.live_control_server.services import guest_build_access as guest

    monkeypatch.setattr(guest, "_lock_guest_session", lambda *_: None)
    monkeypatch.setattr(guest, "MAX_GUEST_TURN_BYTES", 4)
    monkeypatch.setattr(guest, "MAX_GUEST_TURNS", 1)

    class Connection:
        def execute(self, _sql, _params):
            return SimpleNamespace(fetchone=lambda: (1,))

    with pytest.raises(ApplicationStateConflictError):
        guest.guest_turn_capacity(None, Connection(), "world", SimpleNamespace(world_id="world", user_text="ééé"))
    with pytest.raises(ApplicationStateConflictError):
        guest.guest_turn_capacity(None, Connection(), "world", SimpleNamespace(world_id="world", user_text="ok"))


def test_guest_plan_selection_refuses_write_before_reservation():
    from apps.live_control_server.services.agent_turn_service import AgentTurnServiceError
    from apps.live_control_server.services.hosted_native_graph_access import HostedGuestGraphPrincipal
    from apps.live_control_server.services.plan_jev_harness import _require_guest_discussion_selection

    principal = HostedGuestGraphPrincipal(subject="hosted_guest", role="gm", auth_method="hosted_guest",
        managed_world_id="world", session_id="session", request=SimpleNamespace())
    adapter = SimpleNamespace(native_principal=principal)
    _require_guest_discussion_selection(adapter, "discuss")
    _require_guest_discussion_selection(adapter, "clarify")
    with pytest.raises(AgentTurnServiceError) as error:
        _require_guest_discussion_selection(adapter, "write_current_page")
    assert error.value.code == "guest_turn_capability_unavailable"


@pytest.mark.parametrize('operation', ['retained_build_read', 'retained_build_writer'])
def test_retained_build_paths_authorize_before_world_locks(application_state_dsn, monkeypatch, operation):
    from application_state.agent_conversation.native_execution import NativeBuildWriterAuthorizedV2

    def denied(_conn, *, read_only):
        assert not read_only
        raise ApplicationStateConflictError('guest session revoked')

    def unexpected(*_args, **_kwargs):
        pytest.fail('World/turn access ran before guest authorization')

    monkeypatch.setattr(conversation.repo, 'lock_world_state', unexpected)
    service = conversation.AgentConversationService(authorize_transaction=denied)
    world, conversation_id, turn_id = 'guest-test', uuid4(), uuid4()
    with pytest.raises(ApplicationStateConflictError, match='guest session revoked'):
        if operation == 'retained_build_read':
            service.admit_build_prior_body_evidence(world, conversation_id, turn_id,
                expected_revision=1, expected_attempt=1, event_id=uuid4())
        else:
            service.authorize_native_writer(world, conversation_id, turn_id,
                expected_revision=1, expected_attempt=1, expected_rules_revision=1,
                authorization=NativeBuildWriterAuthorizedV2.model_construct(),
                prepared_request_json='{}', work_proof={})
