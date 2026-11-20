from __future__ import annotations

import uuid
from contextlib import closing
from typing import Any

import pytest
from fastapi import FastAPI
from psycopg.rows import dict_row
from starlette.testclient import TestClient

from application_state.engine import connect
from application_state.index_graph import sessions
from application_state.index_graph.sessions import local_profile
from application_state.index_graph.sessions import lookup_session
from apps.live_control_server.routes import index_graph
from apps.live_control_server.services import index_graph as index_graph_service
from apps.live_control_server.native_graph_demo import NativeGraphDemoService
from dungeonmind.infrastructure.memory.vnext_sources import (
    InMemoryNativeSourceEvidenceRepository,
)
from dungeonmind.domain.errors import (
    PersistenceIntegrityError,
    PersistenceUnavailableError,
)


UI_ORIGIN = "http://127.0.0.1:5202"
API_HOST = "127.0.0.1:8000"
HEADERS = {"Origin": UI_ORIGIN, "Sec-Fetch-Site": "same-site"}


@pytest.fixture
def local_client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("DMB_DEPLOYMENT_ENVIRONMENT", "local")
    monkeypatch.setenv("DMB_AUTH_MODE", "local_operator")
    monkeypatch.setenv("DMB_AGENT_GRAPH_LOCAL_UI_ORIGIN", UI_ORIGIN)
    monkeypatch.setenv("DMB_AGENT_GRAPH_LOCAL_API_HOST", API_HOST)
    app = FastAPI()
    app.include_router(index_graph.router)
    return TestClient(
        app,
        base_url=f"http://{API_HOST}",
        client=("127.0.0.1", 43210),
        headers=HEADERS,
    )


def _operation(graph: dict[str, Any], operation_id: str, name: str) -> dict[str, str]:
    return {
        "operation_id": operation_id,
        "expected_revision_id": graph["revision_id"],
        "kind": "create_object",
        "name": name,
        "object_kind": "person",
    }


def _session_count(dsn: str) -> int:
    with closing(connect(dsn)) as connection:
        return connection.execute(
            "SELECT count(*) FROM application_state.index_graph_sessions"
        ).fetchone()[0]


def test_two_guests_get_separate_native_graphs_and_operation_namespaces(
    application_state_dsn: str,
    local_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository = InMemoryNativeSourceEvidenceRepository()
    monkeypatch.setattr(index_graph_service, "repository", lambda: repository)
    first = local_client
    second = TestClient(
        first.app,
        base_url=f"http://{API_HOST}",
        client=("127.0.0.1", 43211),
        headers=HEADERS,
    )

    first_session = first.post("/api/live/index-graph/session")
    second_session = second.post("/api/live/index-graph/session")
    assert first_session.status_code == second_session.status_code == 200
    first_cookie = first_session.headers["set-cookie"].lower()
    _origin, _host, cookie_name = local_profile()
    assert first_cookie.startswith(cookie_name.lower() + "=")
    assert "httponly" in first_cookie
    assert "samesite=strict" in first_cookie
    assert "path=/api/live/index-graph" in first_cookie
    assert not any(
        attribute.strip().startswith("secure")
        for attribute in first_cookie.split(";")[1:]
    )
    first_csrf = first_session.json()["csrf_token"]
    second_csrf = second_session.json()["csrf_token"]
    assert first_csrf != second_csrf
    assert "cannot be reattached automatically" in first_session.json()["notice"]

    first_graph = first.get("/api/live/index-graph/graph").json()
    second_graph = second.get("/api/live/index-graph/graph").json()
    assert first_graph["world_id"] != second_graph["world_id"]
    assert first_graph["storage"] == second_graph["storage"] == "postgres"

    operation_id = str(uuid.uuid4())
    first_prepare = first.post(
        "/api/live/index-graph/prepare",
        headers={"X-DMB-Index-Graph-CSRF": first_csrf},
        json=_operation(first_graph, operation_id, "Lira"),
    )
    second_prepare = second.post(
        "/api/live/index-graph/prepare",
        headers={"X-DMB-Index-Graph-CSRF": second_csrf},
        json=_operation(second_graph, operation_id, "Zed"),
    )
    assert first_prepare.status_code == second_prepare.status_code == 200
    assert (
        first_prepare.json()["status"] == second_prepare.json()["status"] == "prepared"
    )

    first_confirm = first.post(
        "/api/live/index-graph/confirm",
        headers={"X-DMB-Index-Graph-CSRF": first_csrf},
        json={"operation_id": operation_id},
    )
    second_confirm = second.post(
        "/api/live/index-graph/confirm",
        headers={"X-DMB-Index-Graph-CSRF": second_csrf},
        json={"operation_id": operation_id},
    )
    assert (
        first_confirm.json()["status"] == second_confirm.json()["status"] == "committed"
    )
    first_after = first.get("/api/live/index-graph/graph").json()
    second_after = second.get("/api/live/index-graph/graph").json()
    assert any(node["name"] == "Lira" for node in first_after["nodes"])
    assert not any(node["name"] == "Zed" for node in first_after["nodes"])
    assert any(node["name"] == "Zed" for node in second_after["nodes"])
    assert not any(node["name"] == "Lira" for node in second_after["nodes"])

    resumed = first.post("/api/live/index-graph/session")
    assert resumed.status_code == 200
    assert resumed.json()["csrf_token"] == first_csrf
    assert (
        first.get("/api/live/index-graph/graph").json()["world_id"]
        == first_graph["world_id"]
    )

    with closing(connect(application_state_dsn)) as connection:
        connection.row_factory = dict_row
        sessions_rows = connection.execute(
            "SELECT session_id, credential_hash, allocation_id FROM application_state.index_graph_sessions "
            "ORDER BY created_at"
        ).fetchall()
        assert len(sessions_rows) == 2
        assert len({row["allocation_id"] for row in sessions_rows}) == 2
        assert len({bytes(row["credential_hash"]) for row in sessions_rows}) == 2
        assert all(len(bytes(row["credential_hash"])) == 32 for row in sessions_rows)
        operation_rows = connection.execute(
            "SELECT session_id, operation_id FROM application_state.index_graph_operations "
            "WHERE operation_id = %s",
            (operation_id,),
        ).fetchall()
        assert len(operation_rows) == 2
        assert len({str(row["session_id"]) for row in operation_rows}) == 2


def test_unknown_cookie_forged_selectors_and_csrf_fail_closed(
    application_state_dsn: str,
    local_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository = InMemoryNativeSourceEvidenceRepository()
    monkeypatch.setattr(index_graph_service, "repository", lambda: repository)
    client = local_client
    bootstrap = client.post("/api/live/index-graph/session")
    csrf = bootstrap.json()["csrf_token"]
    graph = client.get("/api/live/index-graph/graph").json()
    before_head = repository.get_head(graph["world_id"]).head_revision_id

    forged_world = client.get("/api/live/index-graph/graph?world_id=some-other-world")
    assert forged_world.status_code == 400
    bad_csrf = client.post(
        "/api/live/index-graph/prepare",
        headers={"X-DMB-Index-Graph-CSRF": "incorrect"},
        json=_operation(graph, str(uuid.uuid4()), "Nope"),
    )
    assert bad_csrf.status_code == 403
    forged_body = client.post(
        "/api/live/index-graph/prepare",
        headers={"X-DMB-Index-Graph-CSRF": csrf},
        json={**_operation(graph, str(uuid.uuid4()), "Nope"), "space_id": "chosen"},
    )
    assert forged_body.status_code == 400
    assert repository.get_head(graph["world_id"]).head_revision_id == before_head

    _origin, _host, cookie_name = local_profile()
    unknown = TestClient(
        client.app,
        base_url=f"http://{API_HOST}",
        client=("127.0.0.1", 43212),
        headers={**HEADERS, "Cookie": f"{cookie_name}=unknown-session-token"},
    )
    count_before = _session_count(application_state_dsn)
    forged_session = unknown.post(
        "/api/live/index-graph/session", json={"world_id": "forged-world"}
    )
    assert forged_session.status_code == 400
    unknown_resume = unknown.post("/api/live/index-graph/session")
    assert unknown_resume.status_code == 401
    assert unknown_resume.json()["code"] == "session_unknown"
    assert _session_count(application_state_dsn) == count_before


def test_local_host_origin_proxy_and_session_limits_are_enforced(
    application_state_dsn: str,
    local_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        index_graph_service,
        "repository",
        lambda: InMemoryNativeSourceEvidenceRepository(),
    )
    client = local_client
    created = client.post("/api/live/index-graph/session")
    assert created.status_code == 200

    assert (
        client.get(
            "/api/live/index-graph/graph",
            headers={"Origin": "https://evil.example", "Sec-Fetch-Site": "cross-site"},
        ).status_code
        == 403
    )
    assert (
        client.get(
            "/api/live/index-graph/graph",
            headers={"Origin": UI_ORIGIN},
        ).status_code
        == 200
    )
    assert (
        client.get(
            "/api/live/index-graph/graph", headers={"Host": "localhost:8000"}
        ).status_code
        == 403
    )
    assert (
        client.get(
            "/api/live/index-graph/graph", headers={"X-Forwarded-Host": API_HOST}
        ).status_code
        == 403
    )
    no_origin = TestClient(
        client.app,
        base_url=f"http://{API_HOST}",
        client=("127.0.0.1", 43213),
        headers={"Sec-Fetch-Site": "same-site"},
    )
    assert no_origin.post("/api/live/index-graph/session").status_code == 403
    assert no_origin.get("/api/live/index-graph/graph").status_code == 403
    no_csrf = client.post(
        "/api/live/index-graph/prepare",
        json={"operation_id": str(uuid.uuid4())},
    )
    assert no_csrf.status_code == 403

    monkeypatch.setattr(sessions, "MAX_ACTIVE_SESSIONS", 1)
    other = TestClient(
        client.app,
        base_url=f"http://{API_HOST}",
        client=("127.0.0.1", 43214),
        headers=HEADERS,
    )
    exhausted = other.post("/api/live/index-graph/session")
    assert exhausted.status_code == 429
    assert exhausted.json()["code"] == "session_limit_reached"
    assert _session_count(application_state_dsn) == 1


def test_hosted_mode_is_denied_before_guest_allocation(
    application_state_dsn: str,
    local_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DMB_DEPLOYMENT_ENVIRONMENT", "production")
    monkeypatch.setenv("DMB_AUTH_MODE", "hosted_dms")
    monkeypatch.setattr(
        index_graph_service,
        "repository",
        lambda: pytest.fail("Hosted graph request reached native allocation."),
    )
    denied = local_client.post("/api/live/index-graph/session")
    assert denied.status_code == 404
    assert denied.json()["code"] == "index_graph_unavailable"
    assert _session_count(application_state_dsn) == 0


def test_prepare_body_limit_and_duplicate_json_keys_are_rejected(
    application_state_dsn: str,
    local_client: TestClient,
) -> None:
    client = local_client
    session = client.post("/api/live/index-graph/session")
    csrf = session.json()["csrf_token"]
    too_large = client.post(
        "/api/live/index-graph/prepare",
        headers={"X-DMB-Index-Graph-CSRF": csrf},
        content=b"{" + b" " * (16 * 1024) + b"}",
    )
    assert too_large.status_code == 413
    duplicate = client.post(
        "/api/live/index-graph/prepare",
        headers={"X-DMB-Index-Graph-CSRF": csrf, "Content-Type": "application/json"},
        content=b'{"operation_id":"a","operation_id":"b"}',
    )
    assert duplicate.status_code == 400


@pytest.mark.parametrize(
    ("native_failure", "expected_code"),
    [
        (PersistenceUnavailableError, "native_authority_unavailable"),
        (PersistenceIntegrityError, "native_authority_integrity_failure"),
    ],
)
def test_native_readback_failure_after_checkpoint_recovers_same_operation(
    application_state_dsn: str,
    local_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    native_failure: type[Exception],
    expected_code: str,
) -> None:
    sentinel = "native-secret-detail-sentinel"

    class FaultingRepository(InMemoryNativeSourceEvidenceRepository):
        fail_next_head = False

        def get_head(self, space_id: str):
            if self.fail_next_head:
                self.fail_next_head = False
                raise native_failure(sentinel)
            return super().get_head(space_id)

    repository = FaultingRepository()

    class FaultingService(NativeGraphDemoService):
        def _admit_operation_source(self, request, *, expected_parent_revision_id):
            receipt = super()._admit_operation_source(
                request, expected_parent_revision_id=expected_parent_revision_id
            )
            repository.fail_next_head = True
            return receipt

    monkeypatch.setattr(index_graph_service, "repository", lambda: repository)
    monkeypatch.setattr(index_graph_service, "NativeGraphDemoService", FaultingService)
    client = local_client
    session_response = client.post("/api/live/index-graph/session")
    csrf = session_response.json()["csrf_token"]
    graph = client.get("/api/live/index-graph/graph").json()
    operation_id = str(uuid.uuid4())
    request = _operation(graph, operation_id, "Nima")

    interrupted = client.post(
        "/api/live/index-graph/prepare",
        headers={"X-DMB-Index-Graph-CSRF": csrf},
        json=request,
    )
    assert interrupted.status_code == 503
    assert interrupted.json()["code"] == expected_code
    assert "same operation ID" in interrupted.json()["error"]
    assert sentinel not in str(interrupted.json())
    assert (
        repository.get_native_source_admission_receipt(
            graph["world_id"],
            "native-graph-demo:operation-source:" + operation_id.replace("-", ""),
        )
        is not None
    )

    _origin, _host, cookie_name = local_profile()
    credential = client.cookies.get(cookie_name)
    assert isinstance(credential, str) and credential
    session = lookup_session(credential)
    with index_graph_service.open_index_graph_service(session) as service:
        with service._store.atomic():
            reservation = service._store.get_reservation(operation_id)
    assert reservation is not None
    assert reservation["request"] == request

    recovered = client.get(f"/api/live/index-graph/operations/{operation_id}")
    assert recovered.status_code == 200
    assert recovered.json()["status"] == "prepared"
    committed = client.post(
        "/api/live/index-graph/confirm",
        headers={"X-DMB-Index-Graph-CSRF": csrf},
        json={"operation_id": operation_id},
    )
    assert committed.status_code == 200
    assert committed.json()["status"] == "committed"
    assert any(node["name"] == "Nima" for node in committed.json()["graph"]["nodes"])


@pytest.mark.parametrize(
    ("native_failure", "expected_code"),
    [
        (PersistenceUnavailableError, "native_authority_unavailable"),
        (PersistenceIntegrityError, "native_authority_integrity_failure"),
    ],
)
def test_native_persistence_error_during_prepare_retains_reservation_for_recovery(
    application_state_dsn: str,
    local_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    native_failure: type[Exception],
    expected_code: str,
) -> None:
    sentinel = "native-persistence-detail-sentinel"
    fail_next_prepare = {"enabled": False}

    class FaultingRuntime:
        def prepare_change(self, _intent: Any) -> Any:
            raise native_failure(sentinel)

    class FaultingService(NativeGraphDemoService):
        def _runtime(self, *, prepared_id: str):
            if fail_next_prepare["enabled"]:
                fail_next_prepare["enabled"] = False
                return FaultingRuntime()
            return super()._runtime(prepared_id=prepared_id)

    repository = InMemoryNativeSourceEvidenceRepository()
    monkeypatch.setattr(index_graph_service, "repository", lambda: repository)
    monkeypatch.setattr(index_graph_service, "NativeGraphDemoService", FaultingService)
    client = local_client
    session_response = client.post("/api/live/index-graph/session")
    csrf = session_response.json()["csrf_token"]
    graph = client.get("/api/live/index-graph/graph").json()
    operation_id = str(uuid.uuid4())
    request = _operation(graph, operation_id, "Integrity Recovery")
    fail_next_prepare["enabled"] = True

    interrupted = client.post(
        "/api/live/index-graph/prepare",
        headers={"X-DMB-Index-Graph-CSRF": csrf},
        json=request,
    )
    assert interrupted.status_code == 503
    assert interrupted.json()["code"] == expected_code
    assert "same operation ID" in interrupted.json()["error"]
    assert sentinel not in str(interrupted.json())
    assert (
        repository.get_native_source_admission_receipt(
            graph["world_id"],
            "native-graph-demo:operation-source:" + operation_id.replace("-", ""),
        )
        is not None
    )

    _origin, _host, cookie_name = local_profile()
    credential = client.cookies.get(cookie_name)
    assert isinstance(credential, str) and credential
    session = lookup_session(credential)
    with index_graph_service.open_index_graph_service(session) as service:
        with service._store.atomic():
            reservation = service._store.get_reservation(operation_id)
            rejected_or_prepared = service._store.get_operation(operation_id)
    assert reservation is not None
    assert reservation["request"] == request
    assert rejected_or_prepared is None

    recovered = client.get(f"/api/live/index-graph/operations/{operation_id}")
    assert recovered.status_code == 200
    assert recovered.json()["status"] == "prepared"
    committed = client.post(
        "/api/live/index-graph/confirm",
        headers={"X-DMB-Index-Graph-CSRF": csrf},
        json={"operation_id": operation_id},
    )
    assert committed.status_code == 200
    assert committed.json()["status"] == "committed"
    assert any(
        node["name"] == "Integrity Recovery"
        for node in committed.json()["graph"]["nodes"]
    )


def test_main_registers_index_graph_without_hosted_world_exemption(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DMB_DEPLOYMENT_ENVIRONMENT", "local")
    monkeypatch.setenv("DMB_AUTH_MODE", "local_operator")
    from apps.live_control_server.main import create_app

    app = create_app()
    route_paths = {route.path for route in app.routes}
    assert "/api/live/index-graph/session" in route_paths
    assert "/api/live/index-graph/graph" in route_paths
