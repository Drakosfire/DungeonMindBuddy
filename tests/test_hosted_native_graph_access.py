"""Hosted owner-only boundary contracts with offline synthetic persistence.

The middleware, DmsPrincipalResolver, owner checks, managed binding resolution,
explorer routes and native Core/WorldKeeper operations are real. Only DMS HTTP
transport, APP catalog reads/journal storage, and Core repository storage are
synthetic. These tests do not prove PostgreSQL, real DMS cookies, or deployment.
"""

from __future__ import annotations

import asyncio
import copy
import json
from types import SimpleNamespace
from uuid import uuid4

import httpx
import pytest
from fastapi import FastAPI

from application_state.errors import ApplicationStateUnavailableError
from application_state.world_catalog import service as catalog
from application_state.world_catalog.service import StoredWorld
from application_state.world_catalog.types import (
    NativeGraphBindingRecord,
    WorldAccessGrant,
    WorldContainerRecord,
    WorldPermission,
)
from apps.live_control_server.routes.native_graph_explorer import (
    router as explorer_router,
)
from apps.live_control_server.routes.world_containers import router as worlds_router
from apps.live_control_server.routes.native_graph_inspection import (
    router as inspection_router,
)
from apps.live_control_server.services import (
    native_graph_inspection as inspection_service,
)
from apps.live_control_server.services import hosted_native_graph_access as access
from apps.live_control_server.services import native_graph_explorer as explorer_service
from apps.live_control_server.services.dms_principal import (
    DMS_CURRENT_USER_PATH,
    DMS_SESSION_COOKIE_NAME,
    DmsPrincipalResolver,
)
from apps.live_control_server.services.hosted_auth import (
    AUTH_MODE_ENV,
    DEPLOYMENT_ENVIRONMENT_ENV,
    HOSTED_WORLD_ACCESS_ENV,
    TRUSTED_FRONTEND_ORIGINS_ENV,
    install_hosted_request_boundary,
)
from tests.test_native_graph_explorer import InMemoryExplorerStore, _snapshot
from tests.test_native_recap_preparation import TOKEN, lane as recap_lane  # noqa: F401


FRONTEND_ORIGIN = "https://buddy.dungeonmind.net"
DMS_ORIGIN = "https://synthetic-dms.example.test"
OWNER = "synthetic-owner-alpha"
HOSTED_OWNER = f"hosted_dms:{OWNER}"
OTHER_OWNER = "synthetic-owner-beta"
OUTSIDER = "synthetic-outsider"
EXPLORER = "/api/live/native-graph-explorer"
COLLECTION = "/api/live/world-containers"
INSPECTION = "/api/live/native-graph-inspection/read"
OPERATIONS = ("graph", "prepare", "confirm", "operations/read")
# recap_lane substitutes binding for its own test scope; restore the actual
# function here so the real catalog-to-native binding validator is exercised.
_REAL_NATIVE_BINDING = explorer_service.native.binding


class _OfflineClient:
    """One request-scoped real DMS resolver backed only by MockTransport."""

    def __init__(self, application):
        self.application = application
        self.dms_requests = []
        self.peer = "127.0.0.1"
        self.subjects = {
            "owner-session": OWNER,
            "other-session": OTHER_OWNER,
            "outsider-session": OUTSIDER,
            "all-session": "synthetic-grantee-all",
            **{
                f"{permission}-session": f"synthetic-grantee-{permission}"
                for permission in WorldPermission
            },
        }

    def request(
        self,
        method,
        path,
        *,
        session="owner-session",
        origin=FRONTEND_ORIGIN,
        headers=None,
        **kwargs,
    ):
        outgoing = dict(headers or {})
        if session is not None:
            outgoing["Cookie"] = f"{DMS_SESSION_COOKIE_NAME}={session}"
        if origin is not None:
            outgoing["Origin"] = origin
        return asyncio.run(self._request(method, path, headers=outgoing, **kwargs))

    async def _request(self, method, path, **kwargs):
        def introspect(request):
            self.dms_requests.append(request)
            cookie = request.headers.get("cookie", "")
            session = cookie.removeprefix(f"{DMS_SESSION_COOKIE_NAME}=")
            if session == "unavailable-session":
                return httpx.Response(503, json={"sub": OWNER})
            if session == "timeout-session":
                raise httpx.ReadTimeout("Synthetic DMS timeout", request=request)
            if session == "redirect-session":
                return httpx.Response(302, headers={"location": "https://foreign.test"})
            if session == "malformed-session":
                return httpx.Response(200, json={"sub": 7, "role": "gm"})
            subject = self.subjects.get(session)
            return (
                httpx.Response(200, json={"sub": subject})
                if subject
                else httpx.Response(401)
            )

        async with httpx.AsyncClient(transport=httpx.MockTransport(introspect)) as dms:
            self.application.state.dms_principal_resolver = DmsPrincipalResolver(
                api_origin=DMS_ORIGIN,
                http_client=dms,
            )
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(
                    app=self.application,
                    client=(self.peer, 50000),
                ),
                base_url="http://testserver",
            ) as client:
                return await client.request(method, path, **kwargs)

    def post(self, operation, **kwargs):
        return self.request("POST", f"{EXPLORER}/{operation}", **kwargs)


def _record(world_id, owner, native_world_id, *, name=None, grants=()):
    return WorldContainerRecord(
        world_id=world_id,
        name=name or f"Private {world_id}",
        source_root_relpath=f"corpus/{world_id}-markdown",
        created_at="2026-11-10T00:00:00Z",
        owner_subject=owner,
        access_grants=list(grants),
        native_graph_binding=NativeGraphBindingRecord(
            native_world_id=native_world_id,
            binding_version=3,
            status="active",
            validated_at="2026-11-10T00:00:00Z",
            validated_head_revision_id=f"private-head-{world_id}",
        ),
    )


@pytest.fixture
def hosted(monkeypatch, request):
    lane = request.getfixturevalue("recap_lane")
    records = {
        "managed": _record(
            "managed",
            OWNER,
            lane.bound["native_world_id"],
            name="Shared display name",
            grants=[
                WorldAccessGrant(
                    subject=f"synthetic-grantee-{permission}",
                    permissions=(permission,),
                    granted_by_subject=OWNER,
                )
                for permission in WorldPermission
            ]
            + [
                WorldAccessGrant(
                    subject="synthetic-grantee-all",
                    permissions=tuple(WorldPermission),
                    granted_by_subject=OWNER,
                )
            ],
        ),
        "foreign": _record(
            "foreign", OTHER_OWNER, "native-foreign", name="Shared display name"
        ),
        "unowned": _record("unowned", None, "native-unowned"),
        "not-allowlisted": _record("not-allowlisted", OWNER, "native-hidden"),
    }
    catalog_reads = []

    def get_world(world_id):
        catalog_reads.append(world_id)
        record = records.get(world_id)
        return StoredWorld(copy.deepcopy(record), 1) if record else None

    def list_worlds():
        catalog_reads.append("*")
        return [StoredWorld(copy.deepcopy(record), 1) for record in records.values()]

    monkeypatch.setattr(catalog, "get_world", get_world)
    monkeypatch.setattr(catalog, "list_worlds", list_worlds)
    monkeypatch.setattr(explorer_service.native, "binding", _REAL_NATIVE_BINDING)
    monkeypatch.setattr(explorer_service.native, "repository", lambda: lane.repo)
    monkeypatch.setattr(explorer_service.native, "read_repository", lambda: lane.repo)
    monkeypatch.setattr(
        explorer_service, "NativeGraphExplorerStore", InMemoryExplorerStore
    )
    InMemoryExplorerStore.rows.clear()
    InMemoryExplorerStore.locks.clear()
    monkeypatch.setenv(DEPLOYMENT_ENVIRONMENT_ENV, "production")
    monkeypatch.setenv(AUTH_MODE_ENV, "hosted_dms")
    monkeypatch.setenv(TRUSTED_FRONTEND_ORIGINS_ENV, FRONTEND_ORIGIN)
    subjects = [OWNER, OTHER_OWNER, OUTSIDER, "synthetic-grantee-all"] + [
        f"synthetic-grantee-{p}" for p in WorldPermission
    ]
    allowlist = {world_id: subjects for world_id in ("managed", "foreign", "unowned")}
    monkeypatch.setenv(HOSTED_WORLD_ACCESS_ENV, json.dumps(allowlist))

    app = FastAPI()
    app.include_router(explorer_router)
    app.include_router(worlds_router)
    app.include_router(inspection_router)
    install_hosted_request_boundary(
        app,
        world_scope_resolvers={
            **{
                (
                    "POST",
                    f"{EXPLORER}/{operation}",
                ): access.resolve_hosted_explorer_world
                for operation in OPERATIONS
            },
            ("POST", INSPECTION): access.resolve_hosted_explorer_world,
        },
        collection_authorizers={("GET", COLLECTION): access.hosted_owner_collection},
    )
    unrelated_calls = []

    @app.api_route("/api/live/graph-authoring/confirm", methods=["POST"])
    @app.api_route("/api/provider", methods=["POST"])
    def unrelated():
        unrelated_calls.append(True)
        return {"secret": "must never be reached"}

    client = _OfflineClient(app)
    return SimpleNamespace(**locals())


def _payload(x, operation, world_id="managed"):
    if operation == "graph":
        return {"managed_world_id": world_id}
    body = {"managed_world_id": world_id, "operation_id": str(uuid4())}
    if operation == "prepare":
        body.update(
            native_world_id=x.lane.bound["native_world_id"],
            binding_version=3,
            expected_revision_id=x.lane.repo.get_head(
                x.lane.bound["native_world_id"]
            ).head_revision_id,
            kind="create_object",
            name="Synthetic hosted person",
            object_kind="person",
        )
    return body


def _prepare(x):
    body = _payload(x, "prepare")
    response = x.client.post("prepare", json=body)
    assert response.status_code == 200, response.text
    assert response.json()["status"] == "prepared"
    return {key: body[key] for key in ("managed_world_id", "operation_id")}


def _assert_unchanged(x, before, journal):
    assert _snapshot(x.lane.repo) == before
    assert InMemoryExplorerStore.rows == journal


def test_owner_collection_returns_only_allowlisted_owned_sanitized_records(hosted):
    x = hosted
    before = _snapshot(x.lane.repo)
    response = x.client.request("GET", COLLECTION)
    assert response.status_code == 200, response.text
    result = response.json()
    assert [record["world_id"] for record in result["records"]] == ["managed"]
    record = result["records"][0]
    assert record["name"] == "Shared display name"
    assert set(record) == {
        "schema_version",
        "world_id",
        "name",
        "source_root_relpath",
        "created_at",
        "native_graph_binding",
    }
    assert record["native_graph_binding"] == {"status": "active", "binding_version": 3}
    for secret in (
        OWNER,
        OTHER_OWNER,
        OUTSIDER,
        "private-head",
        "native-foreign",
        "unowned",
        "not-allowlisted",
    ):
        assert secret not in response.text
    _assert_unchanged(x, before, {})


def test_alternate_owner_collection_does_not_confuse_equal_world_names(hosted):
    response = hosted.client.request("GET", COLLECTION, session="other-session")
    assert response.status_code == 200, response.text
    assert [r["world_id"] for r in response.json()["records"]] == ["foreign"]
    assert OWNER not in response.text and "managed-markdown" not in response.text


@pytest.mark.parametrize(
    "session",
    ["outsider-session", "all-session"] + [f"{p}-session" for p in WorldPermission],
)
def test_nonowners_including_each_action_grantee_get_empty_collection(hosted, session):
    response = hosted.client.request("GET", COLLECTION, session=session)
    assert response.status_code == 200, response.text
    assert response.json()["records"] == []


def test_introspected_owner_reads_actual_native_graph_without_writes(hosted):
    x = hosted
    before = _snapshot(x.lane.repo)
    response = x.client.post("graph", json=_payload(x, "graph"))
    assert response.status_code == 200, response.text
    result = response.json()
    assert result["managed_world_id"] == "managed"
    assert result["native_world_id"] == x.lane.bound["native_world_id"]
    assert result["binding_version"] == 3
    assert (
        result["graph"]["revision_id"]
        == x.lane.repo.get_head(result["native_world_id"]).head_revision_id
    )
    assert result["graph"]["nodes"] == []
    assert result["graph"]["capabilities"] == {
        "create": False,
        "connect": False,
        "rename": False,
        "delete": False,
        "object_kinds": [],
    }
    assert x.app.dependency_overrides == {}
    assert x.catalog_reads and len(x.client.dms_requests) == 1
    outbound = x.client.dms_requests[0]
    assert str(outbound.url) == f"{DMS_ORIGIN}{DMS_CURRENT_USER_PATH}"
    assert outbound.headers["cookie"] == f"{DMS_SESSION_COOKIE_NAME}=owner-session"
    _assert_unchanged(x, before, {})


def test_owner_prepare_confirm_recovery_use_native_receipt_and_subject_scope(hosted):
    x = hosted
    body = _prepare(x)
    assert (HOSTED_OWNER, "managed", body["operation_id"]) in InMemoryExplorerStore.rows
    committed = x.client.post("confirm", json=body)
    assert committed.status_code == 200, committed.text
    first = committed.json()
    assert first["status"] == "committed"
    assert first["created_node_id"].startswith("ent:")
    assert first["created_node_id"] in {
        node["id"] for node in first["graph"]["graph"]["nodes"]
    }
    after = _snapshot(x.lane.repo)
    recovered = x.client.post("operations/read", json=body)
    replayed = x.client.post("confirm", json=body)
    for response in (recovered, replayed):
        assert response.status_code == 200, response.text
        assert response.json()["created_node_id"] == first["created_node_id"]
        assert response.json()["status"] == "committed"
    assert _snapshot(x.lane.repo) == after



def _interrupted_owner_prepare(x, monkeypatch):
    request = _payload(x, "prepare")
    original = InMemoryExplorerStore.mark_prepared

    def interrupted(*args, **kwargs):
        raise RuntimeError("synthetic interruption before the review journal write")

    monkeypatch.setattr(InMemoryExplorerStore, "mark_prepared", interrupted)
    response = x.client.post("prepare", json=request)
    assert response.status_code == 200, response.text
    assert response.json()["status"] == "unknown"
    monkeypatch.setattr(InMemoryExplorerStore, "mark_prepared", original)
    return request, {key: request[key] for key in ("managed_world_id", "operation_id")}


def test_owner_interrupted_prepare_recovers_exact_draft_without_duplicate_admission(
    hosted, monkeypatch
):
    x = hosted
    request, lookup = _interrupted_owner_prepare(x, monkeypatch)
    after_admission = _snapshot(x.lane.repo)
    result = x.client.post("operations/read", json=lookup)
    assert result.status_code == 200, result.text
    assert result.json()["status"] == "unknown"
    assert result.json()["recovery_action"] == "retry_prepare"
    assert _snapshot(x.lane.repo) == after_admission
    changed = x.client.post("prepare", json={**request, "name": "Different request"})
    assert changed.status_code == 409
    assert changed.json()["detail"]["code"] == "operation_id_conflict"
    recovered = x.client.post("prepare", json=request)
    assert recovered.status_code == 200, recovered.text
    assert recovered.json()["status"] == "prepared"
    assert recovered.json()["operation_id"] == request["operation_id"]
    assert _snapshot(x.lane.repo) == after_admission
    committed = x.client.post("confirm", json=lookup)
    assert committed.status_code == 200, committed.text
    assert committed.json()["status"] == "committed"
    assert sum(node["name"] == request["name"] for node in committed.json()["graph"]["graph"]["nodes"]) == 1


@pytest.mark.parametrize("session", ["other-session", "all-session"])
def test_nonowner_cannot_discover_or_retry_an_interrupted_owner_prepare(
    hosted, monkeypatch, session
):
    x = hosted
    request, lookup = _interrupted_owner_prepare(x, monkeypatch)
    before, journal = _snapshot(x.lane.repo), copy.deepcopy(InMemoryExplorerStore.rows)
    for operation, body in (("operations/read", lookup), ("prepare", request)):
        response = x.client.post(operation, session=session, json=body)
        assert response.status_code == 403, response.text
        assert "recovery_action" not in response.json()
        _assert_unchanged(x, before, journal)


@pytest.mark.parametrize("revoke", ["owner", "binding"])
def test_interrupted_prepare_retry_advice_is_withheld_after_midread_revocation(
    hosted, monkeypatch, revoke
):
    x = hosted
    _, lookup = _interrupted_owner_prepare(x, monkeypatch)
    before, journal = _snapshot(x.lane.repo), copy.deepcopy(InMemoryExplorerStore.rows)
    original = InMemoryExplorerStore.get_operation
    record = x.records["managed"]

    def get_operation_and_revoke(store, operation_id):
        result = original(store, operation_id)
        change = {"owner_subject": OTHER_OWNER} if revoke == "owner" else {
            "native_graph_binding": record.native_graph_binding.model_copy(
                update={"native_world_id": "native-foreign", "binding_version": 4}
            )
        }
        x.records["managed"] = record.model_copy(update=change)
        return result

    monkeypatch.setattr(InMemoryExplorerStore, "get_operation", get_operation_and_revoke)
    response = x.client.post("operations/read", json=lookup)
    assert response.status_code == (403 if revoke == "owner" else 409), response.text
    assert "recovery_action" not in response.json() and "status" not in response.json()
    _assert_unchanged(x, before, journal)

def test_hosted_subject_cannot_recover_local_operator_journal(hosted, monkeypatch):
    x = hosted
    monkeypatch.setenv(DEPLOYMENT_ENVIRONMENT_ENV, "local")
    monkeypatch.setenv(AUTH_MODE_ENV, "local_operator")
    local_body = _payload(x, "prepare")
    local = x.client.post(
        "prepare",
        session=None,
        headers={"Authorization": f"Bearer {TOKEN}"},
        json=local_body,
    )
    assert local.status_code == 200, local.text
    assert local.json()["status"] == "prepared"
    local_key = ("local_operator", "managed", local_body["operation_id"])
    local_row = copy.deepcopy(InMemoryExplorerStore.rows[local_key])

    # An opaque DMS subject may equal a local identity string, but the two
    # authentication domains must never share operations or native receipt IDs.
    x.client.subjects["owner-session"] = "local_operator"
    x.records["managed"] = x.records["managed"].model_copy(
        update={"owner_subject": "local_operator"}
    )
    monkeypatch.setenv(DEPLOYMENT_ENVIRONMENT_ENV, "production")
    monkeypatch.setenv(AUTH_MODE_ENV, "hosted_dms")
    monkeypatch.setenv(
        HOSTED_WORLD_ACCESS_ENV, json.dumps({"managed": ["local_operator"]})
    )
    lookup = {key: local_body[key] for key in ("managed_world_id", "operation_id")}
    before = _snapshot(x.lane.repo)
    for operation in ("operations/read", "confirm"):
        response = x.client.post(operation, json=lookup)
        assert response.status_code == (
            200 if operation == "operations/read" else 404
        ), response.text
        if operation == "operations/read":
            assert response.json()["status"] == "not_found"
        else:
            assert response.json()["detail"]["code"] == "operation_not_found"
        assert "review" not in response.json() and "graph" not in response.json()
    assert _snapshot(x.lane.repo) == before

    hosted_body = _payload(x, "prepare")
    hosted_body["operation_id"] = local_body["operation_id"]
    prepared = x.client.post("prepare", json=hosted_body)
    assert prepared.status_code == 200, prepared.text
    assert prepared.json()["status"] == "prepared"
    hosted_row = InMemoryExplorerStore.rows[
        ("hosted_dms:local_operator", "managed", local_body["operation_id"])
    ]
    assert hosted_row["source_admission_id"] != local_row["source_admission_id"]
    assert InMemoryExplorerStore.rows[local_key] == local_row


@pytest.mark.parametrize("operation", OPERATIONS)
@pytest.mark.parametrize(
    "session",
    ["other-session", "outsider-session", "all-session"]
    + [f"{p}-session" for p in WorldPermission],
)
def test_allowlist_or_action_grants_never_make_a_nonowner_native_gm(
    hosted, operation, session
):
    x = hosted
    before = _snapshot(x.lane.repo)
    response = x.client.post(operation, session=session, json=_payload(x, operation))
    assert response.status_code == 403, response.text
    assert "Synthetic hosted person" not in response.text
    _assert_unchanged(x, before, {})


@pytest.mark.parametrize("operation", OPERATIONS)
@pytest.mark.parametrize(
    "world_id", ["foreign", "unowned", "not-allowlisted", "does-not-exist"]
)
def test_owned_id_cannot_select_foreign_unowned_hidden_or_missing_world(
    hosted, operation, world_id
):
    x = hosted
    before = _snapshot(x.lane.repo)
    response = x.client.post(operation, json=_payload(x, operation, world_id))
    assert response.status_code == 403, response.text
    assert "private-head" not in response.text
    _assert_unchanged(x, before, {})


@pytest.mark.parametrize("operation", ["confirm", "operations/read"])
def test_guessed_operation_does_not_cross_principal_or_world(hosted, operation):
    x = hosted
    prepared = _prepare(x)
    before, journal = _snapshot(x.lane.repo), copy.deepcopy(InMemoryExplorerStore.rows)
    # Another real owner can enter their own World, but cannot recover alpha's journal.
    response = x.client.post(
        operation,
        session="other-session",
        json={**prepared, "managed_world_id": "foreign"},
    )
    if operation == "confirm":
        assert response.status_code == 404, response.text
    else:
        assert response.status_code == 200, response.text
        assert response.json() == {
            "schema": "dmb_native_graph_explorer_v1",
            "operation_id": prepared["operation_id"],
            "managed_world_id": "foreign",
            "native_world_id": "native-foreign",
            "binding_version": 3,
            "status": "not_found",
        }
    assert "Synthetic hosted person" not in response.text
    assert "review" not in response.json()
    _assert_unchanged(x, before, journal)


@pytest.mark.parametrize("operation", OPERATIONS)
@pytest.mark.parametrize("origin", [None, "https://foreign.example.test", "null"])
def test_all_hosted_explorer_posts_require_trusted_origin(hosted, operation, origin):
    x = hosted
    before = _snapshot(x.lane.repo)
    response = x.client.post(operation, origin=origin, json=_payload(x, operation))
    assert response.status_code == 403, response.text
    assert x.catalog_reads == []
    _assert_unchanged(x, before, {})


@pytest.mark.parametrize(
    ("session", "status"),
    [
        (None, 401),
        ("expired-session", 401),
        ("unavailable-session", 503),
        ("timeout-session", 503),
        ("redirect-session", 503),
        ("malformed-session", 503),
    ],
)
@pytest.mark.parametrize("collection", [False, True])
def test_expired_or_failed_dms_never_reaches_app_or_native_authority(
    hosted, session, status, collection
):
    x = hosted
    before = _snapshot(x.lane.repo)
    if collection:
        response = x.client.request("GET", COLLECTION, session=session)
    else:
        response = x.client.post("graph", session=session, json=_payload(x, "graph"))
    assert response.status_code == status, response.text
    assert x.catalog_reads == []
    assert len(x.client.dms_requests) == (0 if session is None else 1)
    _assert_unchanged(x, before, {})


@pytest.mark.parametrize("session", [None, "outsider-session"])
def test_caller_identity_role_and_local_bearer_cannot_replace_dms_owner(
    hosted, session
):
    x = hosted
    before = _snapshot(x.lane.repo)
    response = x.client.post(
        "graph",
        session=session,
        json=_payload(x, "graph"),
        headers={
            "X-User-ID": OWNER,
            "X-Subject": OWNER,
            "X-Role": "gm",
            "X-Forwarded-User": OWNER,
            "Authorization": f"Bearer {TOKEN}",
        },
    )
    assert response.status_code == (401 if session is None else 403), response.text
    for outbound in x.client.dms_requests:
        assert "authorization" not in outbound.headers
        assert "x-user-id" not in outbound.headers
        assert "x-role" not in outbound.headers
    _assert_unchanged(x, before, {})


@pytest.mark.parametrize(
    "body",
    [
        {},
        {"managedWorldId": "managed"},
        {"managed_world_id": ["managed"]},
        {"managed_world_id": " managed"},
        {"managed_world_id": "managed", "role": "gm"},
        {"managed_world_id": "managed", "world_id": "foreign"},
        {"managed_world_id": "managed", "nested": {"worldId": "foreign"}},
    ],
)
def test_hostile_graph_payload_is_denied_before_catalog_or_graph(hosted, body):
    x = hosted
    before = _snapshot(x.lane.repo)
    response = x.client.post("graph", json=body)
    assert response.status_code == 403, response.text
    assert x.catalog_reads == []
    _assert_unchanged(x, before, {})


@pytest.mark.parametrize(
    "raw",
    [
        '{"managed_world_id":"managed","managed_world_id":"foreign"}',
        '{"managed_world_id":"managed","managed_world_id":"managed"}',
        '{"managed_world_id":"managed"',
        "[]",
        "null",
    ],
)
def test_malformed_or_duplicate_json_never_reaches_catalog(hosted, raw):
    response = hosted.client.post(
        "graph", content=raw, headers={"Content-Type": "application/json"}
    )
    assert response.status_code == 403, response.text
    assert hosted.catalog_reads == []


@pytest.mark.parametrize("operation", OPERATIONS)
@pytest.mark.parametrize(
    "query",
    [
        "world_id=foreign",
        "managed_world_id=managed&managed_world_id=foreign",
        "managed_world_id=managed&managed_world_id=managed",
        "worldId=managed",
        "native_world_id=native-foreign",
        "unexpected=ignored",
    ],
)
def test_query_selector_cannot_override_typed_body_scope(hosted, operation, query):
    x = hosted
    before = _snapshot(x.lane.repo)
    response = x.client.request(
        "POST", f"{EXPLORER}/{operation}?{query}", json=_payload(x, operation)
    )
    assert response.status_code == 403, response.text
    _assert_unchanged(x, before, {})


@pytest.mark.parametrize(
    "query",
    ["world_id=foreign", "managed_world_id=managed", "worldId=managed&worldId=foreign"],
)
def test_collection_cannot_be_used_as_a_world_selector_bypass(hosted, query):
    response = hosted.client.request("GET", f"{COLLECTION}?{query}")
    assert response.status_code == 403, response.text


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("POST", COLLECTION),
        ("PUT", f"{COLLECTION}/managed/native-graph-binding"),
        ("POST", f"{COLLECTION}/managed/native-graph-binding/deactivate"),
        ("GET", f"{COLLECTION}/"),
        ("HEAD", COLLECTION),
        ("GET", f"{EXPLORER}/graph"),
        ("POST", f"{EXPLORER}/graph/"),
        ("POST", "/api/live/native-graph-inspection/catalog"),
        ("POST", "/api/live/native-graph-inspection/source"),
        ("POST", "/api/live/graph-authoring/confirm"),
        ("POST", "/api/provider"),
    ],
)
def test_exact_route_registration_does_not_open_other_capabilities(
    hosted, method, path
):
    x = hosted
    before = _snapshot(x.lane.repo)
    response = x.client.request(method, path, json={"managed_world_id": "managed"})
    assert response.status_code == 403, response.text
    assert x.unrelated_calls == [] and x.catalog_reads == []
    _assert_unchanged(x, before, {})


@pytest.mark.parametrize("collection", [False, True])
def test_catalog_failure_is_closed_and_does_not_reveal_internal_error(
    hosted, monkeypatch, collection
):
    def unavailable(*_):
        raise ApplicationStateUnavailableError("synthetic-private-catalog-coordinate")

    monkeypatch.setattr(catalog, "get_world", unavailable)
    monkeypatch.setattr(catalog, "list_worlds", unavailable)
    response = (
        hosted.client.request("GET", COLLECTION)
        if collection
        else hosted.client.post("graph", json=_payload(hosted, "graph"))
    )
    assert response.status_code in {403, 503}, response.text
    assert "synthetic-private-catalog-coordinate" not in response.text


@pytest.mark.parametrize("operation", ["confirm", "operations/read"])
@pytest.mark.parametrize("revoke", ["owner", "allowlist"])
def test_revocation_after_prepare_denies_confirm_and_recovery_without_effects(
    hosted, monkeypatch, operation, revoke
):
    x = hosted
    body = _prepare(x)
    before, journal = _snapshot(x.lane.repo), copy.deepcopy(InMemoryExplorerStore.rows)
    if revoke == "owner":
        x.records["managed"] = x.records["managed"].model_copy(
            update={"owner_subject": OTHER_OWNER}
        )
    else:
        monkeypatch.setenv(
            HOSTED_WORLD_ACCESS_ENV, json.dumps({"managed": [OTHER_OWNER]})
        )
    response = x.client.post(operation, json=body)
    assert response.status_code == 403, response.text
    assert "review" not in response.json()
    _assert_unchanged(x, before, journal)


def test_owner_transfer_cannot_recover_previous_owners_operation(hosted):
    x = hosted
    body = _prepare(x)
    x.records["managed"] = x.records["managed"].model_copy(
        update={"owner_subject": OTHER_OWNER}
    )
    before, journal = _snapshot(x.lane.repo), copy.deepcopy(InMemoryExplorerStore.rows)
    response = x.client.post("operations/read", json=body, session="other-session")
    assert response.status_code == 200, response.text
    assert response.json() == {
        "schema": "dmb_native_graph_explorer_v1",
        "operation_id": body["operation_id"],
        "managed_world_id": "managed",
        "native_world_id": x.lane.bound["native_world_id"],
        "binding_version": 3,
        "status": "not_found",
    }
    assert "Synthetic hosted person" not in response.text
    _assert_unchanged(x, before, journal)


def test_local_native_bearer_behavior_remains_available_only_on_loopback(
    hosted, monkeypatch
):
    x = hosted
    monkeypatch.setenv(DEPLOYMENT_ENVIRONMENT_ENV, "local")
    monkeypatch.setenv(AUTH_MODE_ENV, "local_operator")
    response = x.client.post(
        "graph",
        session=None,
        origin=None,
        headers={"Authorization": f"Bearer {TOKEN}"},
        json=_payload(x, "graph"),
    )
    assert response.status_code == 200, response.text
    assert x.client.dms_requests == []
    denied = x.client.post(
        "graph", session=None, origin=None, json=_payload(x, "graph")
    )
    assert denied.status_code == 401


@pytest.mark.parametrize(
    "proxy_header",
    [
        "Forwarded",
        "X-Forwarded-For",
        "X-Forwarded-Host",
        "X-Forwarded-Proto",
        "X-Real-IP",
    ],
)
def test_local_bearer_is_not_usable_through_forwarding_proxy(
    hosted, monkeypatch, proxy_header
):
    x = hosted
    monkeypatch.setenv(DEPLOYMENT_ENVIRONMENT_ENV, "local")
    monkeypatch.setenv(AUTH_MODE_ENV, "local_operator")
    response = x.client.post(
        "graph",
        session=None,
        headers={"Authorization": f"Bearer {TOKEN}", proxy_header: "127.0.0.1"},
        json=_payload(x, "graph"),
    )
    assert response.status_code == 403, response.text
    assert x.catalog_reads == [] and x.client.dms_requests == []


def test_local_bearer_cannot_cross_nonloopback_peer(hosted, monkeypatch):
    x = hosted
    monkeypatch.setenv(DEPLOYMENT_ENVIRONMENT_ENV, "local")
    monkeypatch.setenv(AUTH_MODE_ENV, "local_operator")
    x.client.peer = "203.0.113.42"
    response = x.client.post(
        "graph",
        session=None,
        headers={"Authorization": f"Bearer {TOKEN}"},
        json=_payload(x, "graph"),
    )
    assert response.status_code == 403, response.text
    assert x.catalog_reads == [] and x.client.dms_requests == []


def test_collection_revalidates_ownership_after_middleware_admission(
    hosted, monkeypatch
):
    x = hosted
    original = catalog.list_worlds
    calls = []

    def transfer_after_snapshot():
        result = original()
        calls.append(True)
        if len(calls) == 1:
            x.records["managed"] = x.records["managed"].model_copy(
                update={"owner_subject": OTHER_OWNER}
            )
        return result

    monkeypatch.setattr(catalog, "list_worlds", transfer_after_snapshot)
    response = x.client.request("GET", COLLECTION)
    assert response.status_code == 200, response.text
    assert response.json()["records"] == []
    assert len(calls) >= 2


def test_graph_result_is_withheld_when_owner_changes_during_native_read(
    hosted, monkeypatch
):
    x = hosted
    before = _snapshot(x.lane.repo)

    def read_repository_and_revoke():
        x.records["managed"] = x.records["managed"].model_copy(
            update={"owner_subject": OTHER_OWNER}
        )
        return x.lane.repo

    monkeypatch.setattr(
        explorer_service.native, "read_repository", read_repository_and_revoke
    )
    response = x.client.post("graph", json=_payload(x, "graph"))
    assert response.status_code == 403, response.text
    assert "graph" not in response.json()
    _assert_unchanged(x, before, {})


@pytest.mark.parametrize("operation", ["prepare", "confirm"])
def test_revocation_at_journal_checkpoint_prevents_next_native_publication(
    hosted, monkeypatch, operation
):
    x = hosted
    body = _payload(x, "prepare") if operation == "prepare" else _prepare(x)
    before = _snapshot(x.lane.repo)
    checkpoints = []

    def revoke_at_checkpoint(_store):
        checkpoints.append(True)
        x.records["managed"] = x.records["managed"].model_copy(
            update={"owner_subject": OTHER_OWNER}
        )

    monkeypatch.setattr(InMemoryExplorerStore, "checkpoint", revoke_at_checkpoint)
    response = x.client.post(operation, json=body)
    assert checkpoints
    assert response.status_code == 403, response.text
    assert "review" not in response.json() and "graph" not in response.json()
    assert _snapshot(x.lane.repo) == before
    # A retained uncertainty marker is allowed; it cannot imply publication.
    assert (
        InMemoryExplorerStore.rows[(HOSTED_OWNER, "managed", body["operation_id"])][
            "status"
        ]
        == "unknown"
    )


@pytest.mark.parametrize("operation", ["prepare", "confirm", "operations/read"])
def test_operation_payloads_cannot_smuggle_extra_authority_fields(hosted, operation):
    x = hosted
    body = _payload(x, operation)
    body["principal_subject"] = OWNER
    response = x.client.post(operation, json=body)
    assert response.status_code == 403, response.text
    assert x.catalog_reads == [] and InMemoryExplorerStore.rows == {}


@pytest.mark.parametrize("field", ["native_world_id", "binding_version"])
def test_owner_cannot_supply_a_foreign_native_binding_for_prepare(hosted, field):
    x = hosted
    body = _payload(x, "prepare")
    body[field] = "native-foreign" if field == "native_world_id" else 4
    before = _snapshot(x.lane.repo)
    response = x.client.post("prepare", json=body)
    assert response.status_code == 409, response.text
    _assert_unchanged(x, before, {})


def test_collection_rejects_body_even_when_selector_matches_owner(hosted):
    response = hosted.client.request(
        "GET", COLLECTION, json={"managed_world_id": "managed"}
    )
    assert response.status_code == 403, response.text
    assert hosted.catalog_reads == []


@pytest.mark.parametrize(
    ("operation", "committed"),
    [
        ("confirm", False),
        ("confirm", True),
        ("operations/read", True),
    ],
)
def test_revocation_during_runtime_setup_prevents_commit_or_recovery_dispatch(
    hosted, monkeypatch, operation, committed
):
    x = hosted
    body = _prepare(x)
    if committed:
        response = x.client.post("confirm", json=body)
        assert response.status_code == 200 and response.json()["status"] == "committed"
    before = _snapshot(x.lane.repo)
    original = explorer_service.transport.runtime
    setups, dispatches = [], []

    def runtime_and_revoke(*args, **kwargs):
        runtime = original(*args, **kwargs)
        setups.append(True)
        x.records["managed"] = x.records["managed"].model_copy(
            update={"owner_subject": OTHER_OWNER}
        )

        def dispatch(*dispatch_args, **dispatch_kwargs):
            dispatches.append(True)
            return runtime.commit_prepared_change(*dispatch_args, **dispatch_kwargs)

        return SimpleNamespace(commit_prepared_change=dispatch)

    monkeypatch.setattr(explorer_service.transport, "runtime", runtime_and_revoke)
    response = x.client.post(operation, json=body)
    assert setups
    assert response.status_code == 403, response.text
    assert "graph" not in response.json() and "review" not in response.json()
    assert dispatches == []
    assert _snapshot(x.lane.repo) == before


def test_owner_change_after_dispatch_hides_committed_result_and_denies_retry(
    hosted, monkeypatch
):
    x = hosted
    body = _prepare(x)
    original = explorer_service.transport.runtime
    dispatched = []

    def runtime_revoking_after_commit(*args, **kwargs):
        runtime = original(*args, **kwargs)

        def dispatch(*dispatch_args, **dispatch_kwargs):
            result = runtime.commit_prepared_change(*dispatch_args, **dispatch_kwargs)
            dispatched.append(result)
            x.records["managed"] = x.records["managed"].model_copy(
                update={"owner_subject": OTHER_OWNER}
            )
            return result

        return SimpleNamespace(commit_prepared_change=dispatch)

    monkeypatch.setattr(
        explorer_service.transport, "runtime", runtime_revoking_after_commit
    )
    response = x.client.post("confirm", json=body)
    assert response.status_code == 403, response.text
    assert len(dispatched) == 1
    assert "graph" not in response.json() and "created_node_id" not in response.json()
    # The documented race permits a publication dispatched while still owned to
    # finish. It does not permit its data to be returned after owner revocation.
    assert (
        x.lane.repo.get_head(x.lane.bound["native_world_id"]).head_revision_id
        == dispatched[0].child_revision_id
    )
    after = _snapshot(x.lane.repo)
    for operation in ("confirm", "operations/read"):
        denied = x.client.post(operation, json=body)
        assert denied.status_code == 403, denied.text
    assert len(dispatched) == 1
    assert _snapshot(x.lane.repo) == after


@pytest.mark.parametrize("collection", [False, True])
def test_successful_hosted_graph_and_selector_responses_are_not_cacheable(
    hosted, collection
):
    response = (
        hosted.client.request("GET", COLLECTION)
        if collection
        else hosted.client.post("graph", json=_payload(hosted, "graph"))
    )
    assert response.status_code == 200, response.text
    assert response.headers["cache-control"] == "no-store"


@pytest.mark.parametrize(
    "change",
    [
        {"status": "inactive"},
        {"native_world_id": "native-foreign"},
        {"binding_version": 4},
    ],
)
@pytest.mark.parametrize("hook", ["native_read", "journal_read"])
def test_prepared_status_is_withheld_when_binding_changes_during_request(
    hosted, monkeypatch, change, hook
):
    x = hosted
    body = _prepare(x)
    before, journal = _snapshot(x.lane.repo), copy.deepcopy(InMemoryExplorerStore.rows)
    record = x.records["managed"]

    def change_binding():
        x.records["managed"] = record.model_copy(
            update={
                "native_graph_binding": record.native_graph_binding.model_copy(
                    update=change
                ),
            }
        )

    if hook == "native_read":

        def read_repository():
            change_binding()
            return x.lane.repo

        monkeypatch.setattr(explorer_service.native, "read_repository", read_repository)
    else:
        original = InMemoryExplorerStore.get_operation

        def get_operation(store, operation_id):
            result = original(store, operation_id)
            change_binding()
            return result

        monkeypatch.setattr(InMemoryExplorerStore, "get_operation", get_operation)

    response = x.client.post("operations/read", json=body)
    assert response.status_code == 409, response.text
    assert "review" not in response.json() and "graph" not in response.json()
    _assert_unchanged(x, before, journal)


@pytest.mark.parametrize("state", ["not_found", "rejected"])
def test_early_operation_status_rechecks_binding_before_disclosure(
    hosted, monkeypatch, state
):
    x = hosted
    if state == "not_found":
        body = _payload(x, "operations/read")
    else:
        body = _prepare(x)
        InMemoryExplorerStore(HOSTED_OWNER, "managed").mark_rejected(
            body["operation_id"],
            code="synthetic_rejection",
            error="Private rejection explanation",
            updated_at="2026-11-10T00:00:00Z",
        )
    before, journal = _snapshot(x.lane.repo), copy.deepcopy(InMemoryExplorerStore.rows)
    original = InMemoryExplorerStore.get_operation
    record = x.records["managed"]

    def get_operation_and_rebind(store, operation_id):
        result = original(store, operation_id)
        x.records["managed"] = record.model_copy(
            update={
                "native_graph_binding": record.native_graph_binding.model_copy(
                    update={"native_world_id": "native-foreign", "binding_version": 4}
                ),
            }
        )
        return result

    monkeypatch.setattr(
        InMemoryExplorerStore, "get_operation", get_operation_and_rebind
    )
    response = x.client.post("operations/read", json=body)
    assert response.status_code == 409, response.text
    assert "status" not in response.json() and "Private rejection" not in response.text
    _assert_unchanged(x, before, journal)


def test_allowlisted_world_without_app_catalog_record_is_not_authorized(
    hosted, monkeypatch
):
    x = hosted
    monkeypatch.setenv(HOSTED_WORLD_ACCESS_ENV, json.dumps({"missing-world": [OWNER]}))
    response = x.client.post("graph", json={"managed_world_id": "missing-world"})
    assert response.status_code == 403, response.text
    assert x.catalog_reads == ["missing-world"]
    assert InMemoryExplorerStore.rows == {}


def test_catalog_identity_must_match_the_exact_requested_world(hosted, monkeypatch):
    x = hosted
    original = catalog.get_world

    def confused_catalog(world_id):
        stored = original(world_id)
        if stored is not None:
            return StoredWorld(
                stored.record.model_copy(update={"world_id": "foreign"}),
                stored.revision,
            )
        return None

    monkeypatch.setattr(catalog, "get_world", confused_catalog)
    response = x.client.post("graph", json=_payload(x, "graph"))
    assert response.status_code == 403, response.text
    assert InMemoryExplorerStore.rows == {}


def _inspection_payload(x, entity_id="ent:guessed"):
    return {
        "scope": {
            "managed_world_id": "managed",
            "native_world_id": x.lane.bound["native_world_id"],
            "binding_version": 3,
            "revision_id": x.lane.repo.get_head(
                x.lane.bound["native_world_id"]
            ).head_revision_id,
            "scope_mode": "world",
            "campaign_id": None,
        },
        "selection": {"kind": "entity", "entity_id": entity_id},
    }


def _create_entity(x):
    response = x.client.post("confirm", json=_prepare(x))
    assert response.status_code == 200, response.text
    assert response.json()["status"] == "committed"
    return response.json()["created_node_id"]


def test_owner_inspects_actual_loaded_entity_without_source_body_prefetch(
    hosted, monkeypatch
):
    x = hosted
    entity_id = _create_entity(x)
    body = _inspection_payload(x, entity_id)
    before, journal = _snapshot(x.lane.repo), copy.deepcopy(InMemoryExplorerStore.rows)

    def forbidden_source_open(*_, **__):
        pytest.fail("Entity inspection must not prefetch source body")

    monkeypatch.setattr(
        inspection_service, "open_admitted_native_text", forbidden_source_open
    )
    response = x.client.request("POST", INSPECTION, json=body)
    assert response.status_code == 200, response.text
    assert response.json()["schema"] == "dmb_native_graph_entity_v1"
    assert response.json()["scope"] == body["scope"]
    assert entity_id in response.text and "Synthetic hosted person" in response.text
    assert "source" not in response.json()
    assert response.headers["cache-control"] == "no-store"
    _assert_unchanged(x, before, journal)


@pytest.mark.parametrize(
    "session",
    ["other-session", "outsider-session", "all-session"]
    + [f"{p}-session" for p in WorldPermission],
)
def test_entity_inspection_requires_owner_not_nonowner_action_grants(hosted, session):
    x = hosted
    before = _snapshot(x.lane.repo)
    response = x.client.request(
        "POST", INSPECTION, session=session, json=_inspection_payload(x)
    )
    assert response.status_code == 403, response.text
    _assert_unchanged(x, before, {})


@pytest.mark.parametrize("field", ["native_world_id", "binding_version", "revision_id"])
def test_entity_inspection_requires_exact_native_binding_and_revision_pin(
    hosted, field
):
    x = hosted
    entity_id = _create_entity(x)
    body = _inspection_payload(x, entity_id)
    body["scope"][field] = 4 if field == "binding_version" else "foreign:identity"
    before, journal = _snapshot(x.lane.repo), copy.deepcopy(InMemoryExplorerStore.rows)
    response = x.client.request("POST", INSPECTION, json=body)
    assert response.status_code == 409, response.text
    assert "entity" not in response.json()
    _assert_unchanged(x, before, journal)


def test_foreign_or_missing_entity_cannot_be_opened_from_owned_world_pin(hosted):
    x = hosted
    body = _inspection_payload(x, "ent:foreign-owner-entity")
    before = _snapshot(x.lane.repo)
    response = x.client.request("POST", INSPECTION, json=body)
    assert response.status_code == 409, response.text
    assert "entity" not in response.json()
    _assert_unchanged(x, before, {})


def test_hosted_entity_read_returns_pdf_reference_without_rendering(hosted, monkeypatch):
    from types import SimpleNamespace

    entity_id = "ent:pdf-backed"
    evidence_id = "pdf-region:fixture"
    request = _inspection_payload(hosted, entity_id)

    def pinned(scope, principal):
        return inspection_service.native.binding(scope.managed_world_id), None, None, scope

    class FixtureEntityReader:
        def list_entities(self, read):
            return SimpleNamespace(entities=[SimpleNamespace(entity_id=entity_id)])

        def get_complete_entity(self, read, selected_id):
            assert selected_id == entity_id
            return {"evidence": [{"evidence_ref_id": evidence_id, "evidence_role": "support"}]}

    def forbidden_render(*args, **kwargs):
        pytest.fail("Hosted entity inspection must not render PDF evidence")

    monkeypatch.setattr(inspection_service, "_pinned", pinned)
    monkeypatch.setattr(inspection_service, "EntityReadService", FixtureEntityReader)
    monkeypatch.setattr(inspection_service, "render_admitted_pdf_evidence", forbidden_render)

    response = hosted.client.request("POST", INSPECTION, json=request)
    assert response.status_code == 200, response.text
    assert response.json()["entity"]["evidence"][0]["evidence_ref_id"] == evidence_id



def test_source_selection_is_denied_before_any_source_or_catalog_read(
    hosted, monkeypatch
):
    x = hosted
    body = _inspection_payload(x)
    body["selection"] = {
        "kind": "source",
        "assertion_id": "assertion:guessed",
        "evidence_ref_id": "evidence:guessed",
    }

    def forbidden_source_open(*_, **__):
        pytest.fail("Hosted source body opening is not an authorized capability")

    monkeypatch.setattr(
        inspection_service, "open_admitted_native_text", forbidden_source_open
    )
    response = x.client.request("POST", INSPECTION, json=body)
    assert response.status_code == 403, response.text
    assert x.catalog_reads == []
    assert "source" not in response.json()


@pytest.mark.parametrize("mutation", ["campaign", "extra_authority", "query"])
def test_inspection_scope_is_closed_world_entity_only(hosted, mutation):
    x = hosted
    body = _inspection_payload(x)
    path = INSPECTION
    if mutation == "campaign":
        body["scope"].update(scope_mode="campaign", campaign_id="campaign:synthetic")
    elif mutation == "extra_authority":
        body["selection"]["owner_subject"] = OWNER
    else:
        path += "?managed_world_id=managed&managed_world_id=managed"
    response = x.client.request("POST", path, json=body)
    assert response.status_code == 403, response.text
    assert x.catalog_reads == []


@pytest.mark.parametrize(
    ("session", "origin", "status"),
    [
        (None, FRONTEND_ORIGIN, 401),
        ("expired-session", FRONTEND_ORIGIN, 401),
        ("unavailable-session", FRONTEND_ORIGIN, 503),
        ("owner-session", None, 403),
        ("owner-session", "https://foreign.test", 403),
    ],
)
def test_inspection_preserves_dms_and_origin_boundary(hosted, session, origin, status):
    x = hosted
    response = x.client.request(
        "POST", INSPECTION, session=session, origin=origin, json=_inspection_payload(x)
    )
    assert response.status_code == status, response.text
    assert x.catalog_reads == []


@pytest.mark.parametrize("revoke", ["owner", "binding"])
def test_entity_inspection_result_is_withheld_after_midread_revocation(
    hosted, monkeypatch, revoke
):
    x = hosted
    body = _inspection_payload(x, _create_entity(x))
    before, journal = _snapshot(x.lane.repo), copy.deepcopy(InMemoryExplorerStore.rows)
    record = x.records["managed"]

    def read_repository_and_revoke():
        update = (
            {"owner_subject": OTHER_OWNER}
            if revoke == "owner"
            else {
                "native_graph_binding": record.native_graph_binding.model_copy(
                    update={"binding_version": 4}
                )
            }
        )
        x.records["managed"] = record.model_copy(update=update)
        return x.lane.repo

    monkeypatch.setattr(
        explorer_service.native, "read_repository", read_repository_and_revoke
    )
    response = x.client.request("POST", INSPECTION, json=body)
    assert response.status_code == (403 if revoke == "owner" else 409), response.text
    assert "entity" not in response.json()
    _assert_unchanged(x, before, journal)
