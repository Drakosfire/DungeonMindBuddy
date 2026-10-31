"""Corpus storage layout cannot authorize or disqualify a managed World."""
from __future__ import annotations

from tests.application_state.world_catalog_fixtures import store_world

from pathlib import Path

import pytest

from apps.live_control_server.services import first_world_graph as first_world
from apps.live_control_server.services import managed_world_graph_projection as projection
from apps.live_control_server.services.world_container_registry import (
    create_world_container,
)
from apps.live_control_server.services.world_graph_projection import WorldGraphProjectionServiceError
from graph_memory.worldbuilding_write_plan import WorldbuildingWritePlanError
from tests.test_managed_world_graph_projection import _native_projection, _record_with_binding, _request


def _without_corpus(root: Path, *, active: bool = False, relocated_hint: bool = False):
    record = create_world_container(root, name="The Glass Orchard")
    if active:
        record = _record_with_binding(record)
    if relocated_hint:
        record = record.model_copy(update={"source_root_relpath": "older-layout/retained-markdown"})
    return store_world(record)


@pytest.mark.parametrize("relocated_hint", [False, True])
def test_registered_identity_and_native_projection_do_not_consult_corpus_layout(
    tmp_path, monkeypatch, relocated_hint,
):
    record = _without_corpus(tmp_path, active=True, relocated_hint=relocated_hint)
    native_result = _native_projection()
    seen = []
    monkeypatch.setattr(projection, "project_world_graph", lambda request: seen.append(request) or native_result)
    with monkeypatch.context() as guard:
        guard.setattr(Path, "is_dir", lambda *_a: pytest.fail("World admission inspected a directory"))
        assert first_world.admit_managed_world(tmp_path, record.world_id) == record
        binding = projection.resolve_managed_world_binding(record.world_id, root=tmp_path)
        source = projection.resolve_managed_source_identity(record.world_id, root=tmp_path)
        result = projection.project_managed_world_graph(_request(), root=tmp_path)
    assert binding.native_world_id == source.native_world_id == "eldyrwild"
    assert result.projection is native_result
    assert len(seen) == 1 and seen[0].world_id == "eldyrwild"
    assert not (tmp_path / record.source_root_relpath).exists()


def test_reserved_world_admission_keeps_provisioning_and_graph_authority_distinct(tmp_path, monkeypatch):
    monkeypatch.delenv("DMB_MANAGED_WORLD_DATA_ROOT", raising=False)
    record = _without_corpus(tmp_path, relocated_hint=True)
    binding = record.native_graph_binding
    source = projection.resolve_managed_source_identity(record.world_id, root=tmp_path)
    target = first_world.first_world_native_target(tmp_path, record.world_id)
    assert source.native_world_id == target.native_world_id == binding.native_world_id
    assert source.provisioning_id == target.provisioning_id == binding.provisioning_id
    with pytest.raises(WorldGraphProjectionServiceError) as error:
        projection.resolve_managed_world_binding(record.world_id, root=tmp_path)
    assert error.value.code == "native_graph_provisioning_pending"


def test_a_directory_without_a_registered_world_grants_no_admission(tmp_path):
    (tmp_path / "corpus/unregistered-markdown").mkdir(parents=True)
    with pytest.raises(WorldbuildingWritePlanError) as error:
        first_world.admit_managed_world(tmp_path, "unregistered")
    assert error.value.code == "world_unmanaged"
    with pytest.raises(WorldGraphProjectionServiceError) as projection_error:
        projection.resolve_managed_source_identity("unregistered", root=tmp_path)
    assert projection_error.value.code == "managed_world_not_found"


def test_first_publication_cannot_use_an_unbound_record_without_reservation(tmp_path, monkeypatch):
    monkeypatch.delenv("DMB_MANAGED_WORLD_DATA_ROOT", raising=False)
    record = _without_corpus(tmp_path)
    store_world(record.model_copy(update={"native_graph_binding": None}))
    with pytest.raises(WorldbuildingWritePlanError) as error:
        first_world.first_world_native_target(tmp_path, record.world_id)
    assert error.value.code == "native_graph_provisioning_required"

pytestmark = pytest.mark.usefixtures("application_state_dsn")
