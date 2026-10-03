from __future__ import annotations

from pathlib import Path

from pydantic import ValidationError
import pytest

from apps.live_control_server.services import (
    managed_world_graph_projection as managed_projection,
)
from apps.live_control_server.services.world_container_registry import (
    NativeGraphBindingRecord,
    WorldContainerRecord,
    WorldContainerRegistryError,
    create_world_container,
)
from apps.live_control_server.services.world_graph_projection import (
    WorldGraphProjectionServiceError,
)
from graph_memory.projection.world_projection import (
    WorldGraphProjection,
    WorldGraphProjectionRequest,
)


def _request(
    **overrides: object,
) -> managed_projection.ManagedWorldGraphProjectionRequest:
    payload: dict[str, object] = {
        "schema": "dmb_managed_world_graph_projection_request_v1",
        "managedWorldId": "the-glass-orchard",
    }
    payload.update(overrides)
    return managed_projection.ManagedWorldGraphProjectionRequest.model_validate(payload)


def _record_with_binding(
    record: WorldContainerRecord,
    *,
    native_world_id: str = "eldyrwild",
    binding_version: int = 1,
    status: str = "active",
) -> WorldContainerRecord:
    binding = NativeGraphBindingRecord(
        native_world_id=native_world_id,
        binding_version=binding_version,
        status=status,
        validated_at="2026-10-02T00:00:00Z",
        validated_head_revision_id="rev:binding-head",
    )
    return record.model_copy(update={"native_graph_binding": binding})


def _native_projection(world_id: str = "eldyrwild") -> WorldGraphProjection:
    return WorldGraphProjection.model_validate(
        {
            "schema": "dmb_world_graph_projection_v1",
            "snapshot": {
                "worldId": world_id,
                "campaignId": "",
                "revisionId": "rev:read",
                "headRevisionId": "rev:head",
                "isHead": True,
                "focus": {"kind": "none"},
                "admissibility": "gm",
                "scopeMode": "world",
            },
            "summary": {
                "nodeCount": 0,
                "relationshipCount": 0,
                "attributeCount": 0,
                "evidenceCount": 0,
                "sourceArtifactCount": 0,
            },
            "trustBoundary": {"canTrust": [], "cannotTrust": []},
        }
    )


def test_active_binding_reads_native_world_and_returns_unchanged_projection(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    managed = create_world_container(tmp_path, name="The Glass Orchard")
    bound = _record_with_binding(managed)
    monkeypatch.setattr(
        managed_projection,
        "get_world_container",
        lambda _root, _world_id: bound,
    )
    native_projection = _native_projection()
    seen_requests: list[WorldGraphProjectionRequest] = []

    def read_native(request: WorldGraphProjectionRequest) -> WorldGraphProjection:
        seen_requests.append(request)
        return native_projection

    monkeypatch.setattr(managed_projection, "project_world_graph", read_native)

    result = managed_projection.project_managed_world_graph(
        _request(revisionPin="rev:requested", queryText="keeper"), root=tmp_path
    )

    assert len(seen_requests) == 1
    native_request = seen_requests[0]
    assert native_request.world_id == "eldyrwild"
    assert native_request.campaign_id == ""
    assert native_request.scope_mode == "world"
    assert native_request.admissibility == "gm"
    assert native_request.revision_pin == "rev:requested"
    assert native_request.query_text == "keeper"
    assert result.managed_world_id == managed.world_id
    assert result.native_world_id == "eldyrwild"
    assert result.binding_version == 1
    assert result.projection is native_projection
    assert result.projection.snapshot.world_id == "eldyrwild"
    assert result.projection.snapshot.revision_id == "rev:read"


@pytest.mark.parametrize(
    "state", ["missing-record", "unbound", "inactive", "unverified"]
)
def test_unresolvable_or_unverified_binding_fails_before_native_read(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    state: str,
) -> None:
    managed = create_world_container(tmp_path, name="The Glass Orchard")
    record = managed
    if state == "inactive":
        record = _record_with_binding(managed, status="inactive")
    elif state == "unverified":
        record = managed.model_copy(update={"source_root_relpath": "corpus/other-root"})

    def resolve(_root: Path, _world_id: str) -> WorldContainerRecord:
        if state == "missing-record":
            raise WorldContainerRegistryError("not found", status_code=404)
        return record

    monkeypatch.setattr(managed_projection, "get_world_container", resolve)
    reader_calls: list[WorldGraphProjectionRequest] = []
    monkeypatch.setattr(
        managed_projection,
        "project_world_graph",
        lambda request: reader_calls.append(request) or _native_projection(),
    )

    with pytest.raises(WorldGraphProjectionServiceError) as exc_info:
        managed_projection.project_managed_world_graph(_request(), root=tmp_path)

    assert reader_calls == []
    expected_codes = {
        "missing-record": "managed_world_not_found",
        "unbound": "native_graph_binding_missing",
        "inactive": "native_graph_binding_inactive",
        "unverified": "managed_world_unverified",
    }
    assert exc_info.value.code == expected_codes[state]


def test_binding_change_during_projection_discards_native_result(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    managed = create_world_container(tmp_path, name="The Glass Orchard")
    initial = _record_with_binding(
        managed, native_world_id="eldyrwild", binding_version=1
    )
    changed = _record_with_binding(
        managed, native_world_id="new-native-world", binding_version=2
    )
    records = iter([initial, changed])
    monkeypatch.setattr(
        managed_projection,
        "get_world_container",
        lambda _root, _world_id: next(records),
    )
    monkeypatch.setattr(
        managed_projection,
        "project_world_graph",
        lambda _request: _native_projection("eldyrwild"),
    )

    with pytest.raises(WorldGraphProjectionServiceError) as exc_info:
        managed_projection.project_managed_world_graph(_request(), root=tmp_path)

    assert exc_info.value.code == "native_graph_binding_changed"
    assert exc_info.value.status_code == 409


def test_client_cannot_select_native_identity_or_authority_fields() -> None:
    with pytest.raises(ValidationError):
        _request(nativeWorldId="client-selected")
    with pytest.raises(ValidationError):
        _request(bindingVersion=7)
    with pytest.raises(ValidationError):
        _request(admissibility="gm")
