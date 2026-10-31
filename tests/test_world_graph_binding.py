"""Owner-boundary tests for managed-World to native Graph binding."""

from __future__ import annotations

from tests.application_state.world_catalog_fixtures import legacy_world_catalog_path, store_world, world_snapshot

from pathlib import Path
from types import SimpleNamespace
from typing import Any

from fastapi import HTTPException
import pytest
from starlette.requests import Request

from apps.live_control_server.services.world_container_registry import (
    authorize_world_access,
    create_world_container as _create_provisioned_world,
    grant_world_access,
    list_world_containers,
)
from apps.live_control_server.services.world_graph_binding import (
    BindNativeGraphRequest,
    DeactivateNativeGraphBindingRequest,
    WorldGraphBindingError,
    bind_native_graph,
    deactivate_native_graph_binding,
)


def _existing_unbound_world(
    root: Path, *, name: str, owner_subject: str | None = None
):
    """Explicit retained unbound fixture for the existing-Graph binding contract."""
    created = _create_provisioned_world(
        root, name=name, owner_subject=owner_subject
    )
    return store_world(created.model_copy(update={"native_graph_binding": None}))


LOCAL_TOKEN = "binding-test-local-operator-token-long-enough"
NATIVE_ID = "test-native-world"


class _Authority:
    def __init__(
        self,
        world_id: str = NATIVE_ID,
        revision_id: str = "rev:head-1",
        *,
        stored_world_id: str | None = None,
        stored_revision_id: str | None = None,
        revision_exists: bool = True,
    ) -> None:
        self.binding = SimpleNamespace(
            world_id=world_id,
            dungeonmind_head_revision_id=revision_id,
        )
        self.get_revision_calls: list[tuple[str, str]] = []
        if revision_exists:
            self.revision = SimpleNamespace(
                world_id=stored_world_id if stored_world_id is not None else world_id,
                revision_id=(
                    stored_revision_id if stored_revision_id is not None else revision_id
                ),
            )
        else:
            self.revision = None
        self.bundle = SimpleNamespace(world_graph=self)

    def get_revision(self, world_id: str, revision_id: str) -> Any:
        self.get_revision_calls.append((world_id, revision_id))
        if self.revision is None:
            return None
        return SimpleNamespace(revision=self.revision, graph_payload={})


def _valid_request(path: str, *, token: str = LOCAL_TOKEN, host: str = "127.0.0.1") -> Request:
    scope = {
        "type": "http",
        "http_version": "1.1",
        "method": "PUT",
        "scheme": "http",
        "path": path,
        "raw_path": path.encode("ascii"),
        "query_string": b"",
        "headers": [(b"authorization", f"Bearer {token}".encode("utf-8"))],
        "client": (host, 50000),
        "server": ("127.0.0.1", 8000),
    }
    return Request(scope)


def _enable_local_auth(monkeypatch: pytest.MonkeyPatch) -> None:
    from apps.live_control_server.services.agent_graph_auth import (
        AUTH_ENVIRONMENT_ENV,
        AUTH_MODE_ENV,
        LOCAL_OPERATOR_TOKEN_ENV,
    )

    monkeypatch.setenv(AUTH_MODE_ENV, "local_operator")
    monkeypatch.setenv(AUTH_ENVIRONMENT_ENV, "local")
    monkeypatch.setenv(LOCAL_OPERATOR_TOKEN_ENV, LOCAL_TOKEN)


@pytest.fixture
def root(tmp_path: Path) -> Path:
    return tmp_path


@pytest.mark.parametrize("corpus_present", [True, False])
def test_initial_bind_reads_exact_head_revision_then_persists_v3(root: Path, corpus_present: bool) -> None:
    managed = _existing_unbound_world(root, name="Binding Target")
    if corpus_present:
        (root / managed.source_root_relpath).mkdir(parents=True)
    authority = _Authority()
    before = managed.model_dump()

    active = bind_native_graph(
        root,
        managed.world_id,
        native_world_id=NATIVE_ID,
        expected_binding_version=0,
        authority_validator=lambda world_id: authority,
    )

    binding = active.native_graph_binding
    assert binding is not None
    assert binding.status == "active"
    assert binding.binding_version == 1
    assert binding.native_world_id == NATIVE_ID
    assert binding.validated_head_revision_id == "rev:head-1"
    assert authority.get_revision_calls == [(NATIVE_ID, "rev:head-1")]
    assert active.world_id == before["world_id"]
    assert active.name == before["name"]
    assert active.source_root_relpath == before["source_root_relpath"]

    assert world_snapshot()[0].record.schema_version == "dmb_world_container_record_v3"
    assert list_world_containers(root)[0].native_graph_binding == binding


def test_bind_preserves_exact_opaque_head_revision_id(root: Path) -> None:
    managed = _existing_unbound_world(root, name="Opaque Head")
    authority = _Authority(NATIVE_ID, " rev:opaque-head ")

    active = bind_native_graph(
        root,
        managed.world_id,
        native_world_id=NATIVE_ID,
        expected_binding_version=0,
        authority_validator=lambda _world_id: authority,
    )

    assert authority.get_revision_calls == [(NATIVE_ID, " rev:opaque-head ")]
    assert active.native_graph_binding is not None
    assert active.native_graph_binding.validated_head_revision_id == " rev:opaque-head "


def test_graph_binding_mutations_preserve_owner_and_access_grants(root: Path) -> None:
    world = _existing_unbound_world(
        root,
        name="Synthetic Bound World",
        owner_subject="subject:owner",
    )
    grant_world_access(
        root,
        world.world_id,
        actor_subject="subject:owner",
        subject="subject:reader",
        permissions=["read"],
    )
    authority = _Authority(world_id="world:synthetic-graph")

    active = bind_native_graph(
        root,
        world.world_id,
        native_world_id="world:synthetic-graph",
        expected_binding_version=0,
        authority_validator=lambda _world_id: authority,
    )
    assert active.owner_subject == "subject:owner"
    assert active.access_grants[0].subject == "subject:reader"
    assert authorize_world_access(
        root, world.world_id, subject="subject:reader", permission="read"
    ).world_id == world.world_id

    deactivated = deactivate_native_graph_binding(
        root, world.world_id, expected_binding_version=1
    )
    assert deactivated.owner_subject == "subject:owner"
    assert deactivated.access_grants[0].subject == "subject:reader"


@pytest.mark.parametrize(
    ("world_id", "revision_id", "stored_world_id", "stored_revision_id", "exists"),
    [
        ("other-world", "rev:head-1", None, None, True),
        (" test-native-world ", "rev:head-1", None, None, True),
        (NATIVE_ID, "rev:head-1", "wrong-world", "rev:head-1", True),
        (NATIVE_ID, "rev:head-1", NATIVE_ID, "rev:wrong", True),
        (NATIVE_ID, "rev:missing", None, None, False),
        (NATIVE_ID, "", None, None, True),
    ],
)
def test_invalid_authority_or_head_revision_never_persists_active(
    root: Path,
    world_id: str,
    revision_id: str,
    stored_world_id: str | None,
    stored_revision_id: str | None,
    exists: bool,
) -> None:
    managed = _existing_unbound_world(root, name="No Active Binding")
    authority = _Authority(
        world_id,
        revision_id,
        stored_world_id=stored_world_id,
        stored_revision_id=stored_revision_id,
        revision_exists=exists,
    )
    original = world_snapshot()

    with pytest.raises(WorldGraphBindingError):
        bind_native_graph(
            root,
            managed.world_id,
            native_world_id=NATIVE_ID,
            expected_binding_version=0,
            authority_validator=lambda _world_id: authority,
        )

    assert world_snapshot() == original
    assert list_world_containers(root)[0].native_graph_binding is None


def test_deactivation_and_reactivation_are_versioned_and_deactivation_is_local(
    root: Path,
) -> None:
    managed = _existing_unbound_world(root, name="Deactivate World")
    authority = _Authority()
    active = bind_native_graph(
        root,
        managed.world_id,
        native_world_id=NATIVE_ID,
        expected_binding_version=0,
        authority_validator=lambda _world_id: authority,
    )
    assert active.native_graph_binding is not None
    active_version = active.native_graph_binding.binding_version
    original_head = active.native_graph_binding.validated_head_revision_id
    original_calls = list(authority.get_revision_calls)

    inactive = deactivate_native_graph_binding(
        root,
        managed.world_id,
        expected_binding_version=active_version,
    )

    assert inactive.native_graph_binding is not None
    assert inactive.native_graph_binding.status == "inactive"
    assert inactive.native_graph_binding.binding_version == active_version + 1
    assert inactive.native_graph_binding.native_world_id == NATIVE_ID
    assert inactive.native_graph_binding.validated_head_revision_id == original_head
    assert authority.get_revision_calls == original_calls

    reactivated = bind_native_graph(
        root,
        managed.world_id,
        native_world_id=NATIVE_ID,
        expected_binding_version=inactive.native_graph_binding.binding_version,
        authority_validator=lambda _world_id: authority,
    )
    assert reactivated.native_graph_binding is not None
    assert reactivated.native_graph_binding.status == "active"
    assert reactivated.native_graph_binding.binding_version == active_version + 2
    assert len(authority.get_revision_calls) == len(original_calls) + 1


def test_rebinding_requires_inactive_and_exact_expected_version(root: Path) -> None:
    managed = _existing_unbound_world(root, name="Rebind World")
    first = _Authority(NATIVE_ID, "rev:first")
    bind_native_graph(
        root,
        managed.world_id,
        native_world_id=NATIVE_ID,
        expected_binding_version=0,
        authority_validator=lambda _world_id: first,
    )
    never_called: list[str] = []

    with pytest.raises(WorldGraphBindingError) as active_error:
        bind_native_graph(
            root,
            managed.world_id,
            native_world_id="other-native-world",
            expected_binding_version=1,
            authority_validator=lambda world_id: never_called.append(world_id),
        )
    assert active_error.value.status_code == 409
    assert never_called == []

    with pytest.raises(WorldGraphBindingError) as stale_error:
        deactivate_native_graph_binding(
            root,
            managed.world_id,
            expected_binding_version=0,
        )
    assert stale_error.value.status_code == 409

    deactivated = deactivate_native_graph_binding(
        root,
        managed.world_id,
        expected_binding_version=1,
    )
    assert deactivated.native_graph_binding is not None
    rebound = bind_native_graph(
        root,
        managed.world_id,
        native_world_id="other-native-world",
        expected_binding_version=2,
        authority_validator=lambda world_id: _Authority(world_id, "rev:second"),
    )
    assert rebound.native_graph_binding is not None
    assert rebound.native_graph_binding.native_world_id == "other-native-world"
    assert rebound.native_graph_binding.binding_version == 3


def test_duplicate_active_native_graph_claim_is_rejected_inside_mutation(root: Path) -> None:
    first = _existing_unbound_world(root, name="First World")
    second = _existing_unbound_world(root, name="Second World")
    bind_native_graph(
        root,
        first.world_id,
        native_world_id=NATIVE_ID,
        expected_binding_version=0,
        authority_validator=lambda _world_id: _Authority(),
    )
    before = world_snapshot()

    with pytest.raises(WorldGraphBindingError) as exc_info:
        bind_native_graph(
            root,
            second.world_id,
            native_world_id=NATIVE_ID,
            expected_binding_version=0,
            authority_validator=lambda _world_id: _Authority(),
        )

    assert exc_info.value.status_code == 409
    assert world_snapshot() == before
    assert list_world_containers(root)[1].native_graph_binding is None


@pytest.mark.parametrize("restore_original", [False, True])
def test_same_world_change_during_native_validation_rejects_stale_binding(root, restore_original):
    managed = _existing_unbound_world(root, name="Exact World CAS")
    authority = _Authority()
    def concurrent_change(_):
        store_world(managed.model_copy(update={"name": "Concurrent metadata edit"}))
        if restore_original:
            store_world(managed)
        return authority
    with pytest.raises(WorldGraphBindingError) as error:
        bind_native_graph(root, managed.world_id, native_world_id=NATIVE_ID,
            expected_binding_version=0, authority_validator=concurrent_change)
    assert error.value.status_code == 409
    assert list_world_containers(root)[0].native_graph_binding is None


def test_unrelated_world_change_during_native_validation_does_not_invalidate_binding(
    root: Path,
) -> None:
    managed = _existing_unbound_world(root, name="CAS World")
    authority = _Authority()

    def validate_with_concurrent_registry_change(_world_id: str) -> Any:
        _existing_unbound_world(root, name="Concurrent World")
        return authority

    active = bind_native_graph(root, managed.world_id, native_world_id=NATIVE_ID,
        expected_binding_version=0, authority_validator=validate_with_concurrent_registry_change)
    assert active.native_graph_binding.status == "active"
    assert len(list_world_containers(root)) == 2


def test_retained_unbound_world_binds_without_files_or_migration(root):
    managed = _existing_unbound_world(root, name="Retained World")
    active = bind_native_graph(root, managed.world_id, native_world_id=NATIVE_ID,
        expected_binding_version=0, authority_validator=lambda _: _Authority())
    assert active.world_id == managed.world_id
    assert active.native_graph_binding.status == "active"
    assert not legacy_world_catalog_path(root).exists()


def _call_binding_route_without_auth(
    monkeypatch: pytest.MonkeyPatch,
    *,
    request: Request,
    operation: str,
) -> None:
    from apps.live_control_server.routes import world_containers

    monkeypatch.setattr(
        world_containers,
        "repo_root",
        lambda: pytest.fail("auth denial must happen before repo_root"),
    )
    monkeypatch.setattr(
        "apps.live_control_server.services.world_graph_binding._validate_with_mind",
        lambda _world_id: pytest.fail("auth denial must happen before MIND access"),
    )
    if operation == "bind":
        world_containers.put_native_graph_binding(
            managed_world_id="managed-world",
            body=BindNativeGraphRequest(
                native_world_id=NATIVE_ID,
                expected_binding_version=0,
            ),
            request=request,
        )
    else:
        world_containers.post_deactivate_native_graph_binding(
            managed_world_id="managed-world",
            body=DeactivateNativeGraphBindingRequest(expected_binding_version=1),
            request=request,
        )


@pytest.mark.parametrize(
    ("configured", "token", "host", "expected_status"),
    [
        (False, "", "127.0.0.1", 503),
        (True, "wrong-token", "127.0.0.1", 401),
        (True, LOCAL_TOKEN, "192.0.2.5", 403),
    ],
)
@pytest.mark.parametrize("operation", ["bind", "deactivate"])
def test_binding_route_denial_precedes_registry_and_mind(
    monkeypatch: pytest.MonkeyPatch,
    configured: bool,
    token: str,
    host: str,
    expected_status: int,
    operation: str,
) -> None:
    from apps.live_control_server.services.agent_graph_auth import (
        AUTH_ENVIRONMENT_ENV,
        AUTH_MODE_ENV,
        LOCAL_OPERATOR_TOKEN_ENV,
    )

    for key in (AUTH_ENVIRONMENT_ENV, AUTH_MODE_ENV, LOCAL_OPERATOR_TOKEN_ENV):
        monkeypatch.delenv(key, raising=False)
    if configured:
        _enable_local_auth(monkeypatch)
    suffix = "/native-graph-binding"
    if operation == "deactivate":
        suffix += "/deactivate"
    method = "POST" if operation == "deactivate" else "PUT"
    request = _valid_request(
        f"/api/live/world-containers/managed-world{suffix}",
        token=token,
        host=host,
    )
    request.scope["method"] = method

    with pytest.raises(HTTPException) as exc_info:
        _call_binding_route_without_auth(
            monkeypatch,
            request=request,
            operation=operation,
        )

    assert exc_info.value.status_code == expected_status


def test_successful_bind_route_returns_redacted_status_and_deactivation_skips_mind(
    root: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from apps.live_control_server.routes import world_containers

    _enable_local_auth(monkeypatch)
    managed = _existing_unbound_world(root, name="Route World")
    monkeypatch.setattr(world_containers, "repo_root", lambda: root)
    authority = _Authority()
    monkeypatch.setattr(
        "apps.live_control_server.services.world_graph_binding._validate_with_mind",
        lambda _world_id: authority,
    )
    put_result = world_containers.put_native_graph_binding(
        managed_world_id=managed.world_id,
        body=BindNativeGraphRequest(
            native_world_id=NATIVE_ID,
            expected_binding_version=0,
        ),
        request=_valid_request(
            f"/api/live/world-containers/{managed.world_id}/native-graph-binding"
        ),
    )

    public_binding = put_result["native_graph_binding"]
    assert public_binding == {"status": "active", "binding_version": 1}
    body_text = repr(put_result)
    assert NATIVE_ID not in body_text
    assert "rev:head-1" not in body_text
    assert "validated_head_revision_id" not in body_text
    assert "MIND receipt" not in body_text

    monkeypatch.setattr(
        "apps.live_control_server.services.world_graph_binding._validate_with_mind",
        lambda _world_id: pytest.fail("list/deactivation must not contact MIND"),
    )
    list_result = world_containers.get_world_containers()
    assert list_result["records"][0]["native_graph_binding"] == {
        "status": "active",
        "binding_version": 1,
    }
    list_text = repr(list_result)
    assert NATIVE_ID not in list_text
    assert "rev:head-1" not in list_text
    assert "validated_head_revision_id" not in list_text

    deactivate_result = world_containers.post_deactivate_native_graph_binding(
        managed_world_id=managed.world_id,
        body=DeactivateNativeGraphBindingRequest(expected_binding_version=1),
        request=_valid_request(
            f"/api/live/world-containers/{managed.world_id}/native-graph-binding/deactivate"
        ),
    )
    assert deactivate_result["native_graph_binding"] == {
        "status": "inactive",
        "binding_version": 2,
    }


def test_existing_graph_binding_cannot_steal_a_reserved_native_identity(root: Path) -> None:
    reserved = _create_provisioned_world(root, name="Reserved owner")
    other = _existing_unbound_world(root, name="Existing other")
    native_id = reserved.native_graph_binding.native_world_id
    before = world_snapshot()
    with pytest.raises(WorldGraphBindingError):
        bind_native_graph(root, other.world_id, native_world_id=native_id, expected_binding_version=0,
                          authority_validator=lambda _: _Authority(world_id=native_id))
    assert world_snapshot() == before

pytestmark = pytest.mark.usefixtures("application_state_dsn")


def test_corrupt_database_metadata_fails_before_native_validation_without_private_details(root, application_state_dsn, monkeypatch):
    import psycopg
    from apps.live_control_server.routes import world_containers
    world = _existing_unbound_world(root, name="Private metadata", owner_subject="subject:owner")
    grant_world_access(root, world.world_id, actor_subject="subject:owner", subject="subject:reader", permissions=["read"])
    with psycopg.connect(application_state_dsn) as conn:
        conn.execute("UPDATE workspace.managed_world SET owner_subject=NULL WHERE world_id=%s", (world.world_id,))
    _enable_local_auth(monkeypatch)
    monkeypatch.setattr(world_containers, "repo_root", lambda: root)
    monkeypatch.setattr("apps.live_control_server.services.world_graph_binding._validate_with_mind", lambda _: pytest.fail("corrupt metadata reached native validation"))
    with pytest.raises(HTTPException) as error:
        world_containers.put_native_graph_binding(world.world_id, BindNativeGraphRequest(native_world_id="private-native-marker", expected_binding_version=0), _valid_request("/api/live/world-containers/"+world.world_id+"/native-graph-binding"))
    assert error.value.status_code == 500
    assert error.value.detail == "Stored World metadata is invalid."
    assert "subject:" not in error.value.detail
    assert "private-native" not in error.value.detail
