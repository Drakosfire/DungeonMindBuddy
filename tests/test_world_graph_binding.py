"""Owner-boundary tests for managed-World to native Graph binding."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from fastapi import HTTPException
import pytest
from starlette.requests import Request

from apps.live_control_server.services.world_container_registry import (
    REGISTRY_SCHEMA,
    create_world_container,
    list_world_containers,
    world_containers_path,
)
from apps.live_control_server.services.world_graph_binding import (
    BindNativeGraphRequest,
    DeactivateNativeGraphBindingRequest,
    WorldGraphBindingError,
    bind_native_graph,
    deactivate_native_graph_binding,
)


LOCAL_TOKEN = "binding-test-local-operator-token-long-enough"
NATIVE_ID = "eldyrwild"


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


def test_initial_bind_reads_exact_head_revision_then_persists_v2(root: Path) -> None:
    managed = create_world_container(root, name="Binding Target")
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

    payload = __import__("json").loads(world_containers_path(root).read_text(encoding="utf-8"))
    assert payload["schema_version"] == REGISTRY_SCHEMA
    assert payload["records"][0]["schema_version"] == "dmb_world_container_record_v2"
    assert list_world_containers(root)[0].native_graph_binding == binding


def test_bind_preserves_exact_opaque_head_revision_id(root: Path) -> None:
    managed = create_world_container(root, name="Opaque Head")
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


@pytest.mark.parametrize(
    ("world_id", "revision_id", "stored_world_id", "stored_revision_id", "exists"),
    [
        ("other-world", "rev:head-1", None, None, True),
        (" eldyrwild ", "rev:head-1", None, None, True),
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
    managed = create_world_container(root, name="No Active Binding")
    authority = _Authority(
        world_id,
        revision_id,
        stored_world_id=stored_world_id,
        stored_revision_id=stored_revision_id,
        revision_exists=exists,
    )
    registry_path = world_containers_path(root)
    original = registry_path.read_bytes()

    with pytest.raises(WorldGraphBindingError):
        bind_native_graph(
            root,
            managed.world_id,
            native_world_id=NATIVE_ID,
            expected_binding_version=0,
            authority_validator=lambda _world_id: authority,
        )

    assert registry_path.read_bytes() == original
    assert list_world_containers(root)[0].native_graph_binding is None


def test_deactivation_and_reactivation_are_versioned_and_deactivation_is_local(
    root: Path,
) -> None:
    managed = create_world_container(root, name="Deactivate World")
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
    managed = create_world_container(root, name="Rebind World")
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
    first = create_world_container(root, name="First World")
    second = create_world_container(root, name="Second World")
    bind_native_graph(
        root,
        first.world_id,
        native_world_id=NATIVE_ID,
        expected_binding_version=0,
        authority_validator=lambda _world_id: _Authority(),
    )
    path = world_containers_path(root)
    before = path.read_bytes()

    with pytest.raises(WorldGraphBindingError) as exc_info:
        bind_native_graph(
            root,
            second.world_id,
            native_world_id=NATIVE_ID,
            expected_binding_version=0,
            authority_validator=lambda _world_id: _Authority(),
        )

    assert exc_info.value.status_code == 409
    assert path.read_bytes() == before
    assert list_world_containers(root)[1].native_graph_binding is None


def test_registry_token_change_during_mind_validation_fails_compare_and_swap(
    root: Path,
) -> None:
    managed = create_world_container(root, name="CAS World")
    authority = _Authority()

    def validate_with_concurrent_registry_change(_world_id: str) -> Any:
        create_world_container(root, name="Concurrent World")
        return authority

    with pytest.raises(WorldGraphBindingError) as exc_info:
        bind_native_graph(
            root,
            managed.world_id,
            native_world_id=NATIVE_ID,
            expected_binding_version=0,
            authority_validator=validate_with_concurrent_registry_change,
        )

    assert exc_info.value.status_code == 409
    assert len(list_world_containers(root)) == 2
    assert list_world_containers(root)[0].native_graph_binding is None


def test_legacy_v1_world_is_migrated_only_by_successful_locked_bind(root: Path) -> None:
    from apps.live_control_server.services.world_container_registry import (
        WorldContainerRecord,
    )
    from src.live_play.live_store import write_json

    legacy = WorldContainerRecord.model_validate(
        {
            "schema_version": "dmb_world_container_record_v1",
            "world_id": "legacy-world",
            "name": "Legacy World",
            "source_root_relpath": "corpus/legacy-world-markdown",
            "created_at": "2026-01-01T00:00:00Z",
        }
    )
    (root / legacy.source_root_relpath).mkdir(parents=True)
    path = world_containers_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    write_json(
        path,
        {
            "schema_version": "dmb_world_container_registry_v1",
            "records": [legacy.model_dump(mode="json")],
        },
    )

    active = bind_native_graph(
        root,
        legacy.world_id,
        native_world_id=NATIVE_ID,
        expected_binding_version=0,
        authority_validator=lambda _world_id: _Authority(),
    )

    payload = __import__("json").loads(path.read_text(encoding="utf-8"))
    assert payload["schema_version"] == REGISTRY_SCHEMA
    assert payload["records"][0]["schema_version"] == "dmb_world_container_record_v2"
    assert payload["records"][0]["world_id"] == legacy.world_id
    assert payload["records"][0]["name"] == legacy.name
    assert payload["records"][0]["source_root_relpath"] == legacy.source_root_relpath
    assert active.native_graph_binding is not None
    assert active.native_graph_binding.binding_version == 1


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
    managed = create_world_container(root, name="Route World")
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


@pytest.mark.parametrize("malformation", ["oversized_native_id", "missing_timestamp"])
def test_malformed_registry_bind_error_does_not_echo_private_graph_identity(
    root: Path,
    monkeypatch: pytest.MonkeyPatch,
    malformation: str,
) -> None:
    from apps.live_control_server.routes import world_containers

    _enable_local_auth(monkeypatch)
    monkeypatch.setattr(world_containers, "repo_root", lambda: root)
    monkeypatch.setattr(
        "apps.live_control_server.services.world_graph_binding._validate_with_mind",
        lambda _world_id: pytest.fail("malformed registry must fail before MIND access"),
    )
    native_id = "native-leak-marker-" + "x" * 300
    if malformation == "missing_timestamp":
        native_id = "private-native-id"
    path = world_containers_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    binding = {
        "schema_version": "dmb_managed_world_native_graph_binding_v1",
        "provider": "dungeonmind_v2",
        "native_world_id": native_id,
        "status": "active",
        "binding_version": 1,
        "validated_at": "2026-01-01T00:00:00Z",
        "validated_head_revision_id": "private-head-marker",
    }
    if malformation == "missing_timestamp":
        binding.pop("validated_at")
    path.write_text(
        json.dumps(
            {
                "schema_version": "dmb_world_container_registry_v2",
                "records": [
                    {
                        "schema_version": "dmb_world_container_record_v2",
                        "world_id": "managed-world",
                        "name": "Managed World",
                        "source_root_relpath": "corpus/managed-world-markdown",
                        "created_at": "2026-01-01T00:00:00Z",
                        "native_graph_binding": binding,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(HTTPException) as exc_info:
        world_containers.put_native_graph_binding(
            managed_world_id="managed-world",
            body=BindNativeGraphRequest(
                native_world_id=NATIVE_ID,
                expected_binding_version=1,
            ),
            request=_valid_request(
                "/api/live/world-containers/managed-world/native-graph-binding"
            ),
        )

    assert exc_info.value.status_code == 500
    assert exc_info.value.detail == "malformed world container registry"
    assert "native-leak-marker" not in str(exc_info.value.detail)
    assert "private-head-marker" not in str(exc_info.value.detail)
    assert "private-native-id" not in str(exc_info.value.detail)
