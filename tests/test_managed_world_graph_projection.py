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
    managed = create_world_container(name="The Glass Orchard")
    bound = _record_with_binding(managed)
    monkeypatch.setattr(
        managed_projection,
        "get_world_container",
        lambda _world_id: bound,
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


def test_shared_binding_resolver_does_not_read_native_graph(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    managed = create_world_container(name="The Glass Orchard")
    bound = _record_with_binding(managed)
    monkeypatch.setattr(
        managed_projection, "get_world_container", lambda _world_id: bound
    )
    monkeypatch.setattr(
        managed_projection, "project_world_graph",
        lambda _request: pytest.fail("binding resolution read the native Graph"),
    )
    binding = managed_projection.resolve_managed_world_binding(
        managed.world_id, root=tmp_path
    )
    assert binding.managed_world_id == managed.world_id
    assert binding.native_world_id == "eldyrwild"
    assert binding.binding_version == 1
    assert binding.source_root_relpath == f"corpus/{managed.world_id}-markdown"


@pytest.mark.parametrize(
    "state", ["missing-record", "unbound", "inactive", "wrong-world"]
)
def test_unresolvable_or_unverified_binding_fails_before_native_read(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    state: str,
) -> None:
    managed = create_world_container(name="The Glass Orchard")
    record = managed
    if state == "unbound":
        record = managed.model_copy(update={"native_graph_binding": None})
    elif state == "inactive":
        record = _record_with_binding(managed, status="inactive")
    elif state == "wrong-world":
        record = _record_with_binding(managed).model_copy(update={"world_id": "other-world"})

    def resolve(_world_id: str) -> WorldContainerRecord:
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
        "wrong-world": "managed_world_identity_mismatch",
    }
    assert exc_info.value.code == expected_codes[state]


def test_binding_change_during_projection_discards_native_result(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    managed = create_world_container(name="The Glass Orchard")
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
        lambda _world_id: next(records),
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

pytestmark = pytest.mark.usefixtures("application_state_dsn")


@pytest.mark.parametrize("revision_pin", [None, "historical"])
def test_native_projection_support_uses_exact_revision(monkeypatch, revision_pin):
    from types import SimpleNamespace

    from dungeonmind.application.vnext import EntityReadService

    from apps.live_control_server.integrations.dungeonmind import native_registry_source

    binding = SimpleNamespace(native_world_id="elderwyld")
    repository = SimpleNamespace(
        get_head=lambda space: SimpleNamespace(head_revision_id="current")
    )
    context = object()
    support = object()

    def read_context(repo, space, revision, campaign, *, scope_mode, parsed_cache):
        assert parsed_cache is not None
        assert repo is repository
        assert (space, revision, campaign, scope_mode) == (
            "elderwyld", revision_pin or "current", None, "world"
        )
        return context, None, None, None

    def list_support(self, read_context):
        assert read_context is context
        return support

    monkeypatch.setattr(native_registry_source, "read_repository", lambda: repository)
    monkeypatch.setattr(native_registry_source, "read_context", read_context)
    monkeypatch.setattr(EntityReadService, "list_entities_with_support", list_support)
    assert managed_projection._read_native_projection_support(binding, revision_pin) == (
        "current", context, None, support
    )


def test_source_views_do_not_copy_producer_session_to_unmatched_revision(monkeypatch):
    from types import SimpleNamespace as Record

    from apps.live_control_server.integrations.dungeonmind import vnext_world_projection as adapter

    artifact = Record(
        source_artifact_id="artifact", source_classification="buddy:recap",
        domain_metadata=[], uri=None,
    )
    source_reader = Record(get_provenance_snapshot=lambda **_: Record(
        get_artifact=lambda _: artifact,
    ))
    support = Record(evidence=[
        Record(evidence_ref_id=key, source_artifact_id="artifact", locator=None,
               source_span_ref_id=None)
        for key in ("matched", "older")
    ])
    selected = Record(source_artifact=artifact, evidence_ref_ids=("matched",))

    def select(access, *, evidence_ref_ids):
        assert evidence_ref_ids == ["matched", "older"]
        return Record(sources=(selected,))

    monkeypatch.setattr(adapter, "list_admitted_native_text_sources", select)
    monkeypatch.setattr(adapter, "source_display_metadata", lambda items, world: [
        {"origin_matches_current_metadata": True, "campaign_id": "campaign",
         "session_id": "session-9"}
    ])
    evidence, artifacts = adapter.project_source_views(
        Record(source_reader=source_reader), support, access=object(), managed_world_id="world"
    )
    assert artifacts[0].session_id == "session-9"
    assert [(row.campaign_id, row.session_id) for row in evidence] == [
        ("campaign", "session-9"), (None, None)
    ]


@pytest.mark.parametrize("message, status", [
    ("native source context revision is missing", 404),
    ("native source context domain pin mismatch", None),
])
def test_native_projection_distinguishes_missing_pin_from_integrity_failure(
    monkeypatch, message, status
):
    from types import SimpleNamespace

    from dungeonmind.application.vnext.errors import KnowledgeReadContextIntegrityError

    from apps.live_control_server.integrations.dungeonmind import native_registry_source

    repository = SimpleNamespace(
        get_head=lambda space: SimpleNamespace(head_revision_id="current")
    )
    failure = KnowledgeReadContextIntegrityError(message)

    def read_context(*args, **kwargs):
        raise failure

    monkeypatch.setattr(native_registry_source, "read_repository", lambda: repository)
    monkeypatch.setattr(native_registry_source, "read_context", read_context)
    binding = SimpleNamespace(native_world_id="elderwyld")
    if status is None:
        with pytest.raises(KnowledgeReadContextIntegrityError) as caught:
            managed_projection._read_native_projection_support(binding, "missing")
        assert caught.value is failure
    else:
        with pytest.raises(managed_projection.WorldGraphProjectionServiceError) as caught:
            managed_projection._read_native_projection_support(binding, "missing")
        assert caught.value.status_code == status
        assert caught.value.code == "native_graph_revision_unavailable"
