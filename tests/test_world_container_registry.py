"""Live World metadata has one DB owner; files cannot create authority."""
from pathlib import Path

import pytest
from pydantic import ValidationError

from application_state.errors import ApplicationStateUnavailableError
from application_state.world_catalog.service import normalize_world_name_for_compare
from apps.live_control_server.services import world_container_registry as registry
from apps.live_control_server.services.world_container_registry import (
    REGISTRY_SCHEMA, WorldContainerRegistryError, create_world_container,
    get_world_container, list_world_containers,
)
from apps.live_control_server.services.workspace_document_registry import (
    WorkspaceDocumentRegistryError, create_workspace_document,
)
from tests.application_state.world_catalog_fixtures import (
    legacy_world_catalog_path, store_world, world_snapshot,
)

pytestmark = pytest.mark.usefixtures("application_state_dsn")


@pytest.fixture
def root(tmp_path):
    return tmp_path


def test_create_world_persists_exact_identity_without_source_folder(root):
    created = create_world_container(root, name="The Glass Orchard")
    assert created.world_id == "the-glass-orchard"
    assert created.name == "The Glass Orchard"
    assert created.source_root_relpath == "corpus/the-glass-orchard-markdown"
    assert created.schema_version == "dmb_world_container_record_v3"
    assert list_world_containers(root) == [created]
    assert get_world_container(root, created.world_id) == created
    assert not legacy_world_catalog_path(root).exists()
    assert not (root / created.source_root_relpath).exists()


def test_reload_from_another_checkout_uses_the_same_database(root):
    created = create_world_container(root / "checkout-a", name="One-Shot Vale")
    assert list_world_containers(root / "checkout-b") == [created]
    assert get_world_container(root / "does-not-exist", created.world_id) == created


def test_empty_and_whitespace_names_fail_closed(root):
    for bad in ("", "   ", "\n\t"):
        with pytest.raises(WorldContainerRegistryError) as error:
            create_world_container(root, name=bad)
        assert error.value.status_code == 422
    assert list_world_containers(root) == []


def test_same_normalized_name_is_idempotent(root):
    first = create_world_container(root, name="The Glass Orchard")
    second = create_world_container(root, name="  the   glass   orchard  ")
    assert second == first
    assert len(list_world_containers(root)) == 1
    assert normalize_world_name_for_compare(first.name) == normalize_world_name_for_compare("THE GLASS ORCHARD")


def test_different_name_slug_collision_fails_409(root):
    first = create_world_container(root, name="Glass Orchard")
    with pytest.raises(WorldContainerRegistryError) as error:
        create_world_container(root, name="Glass-Orchard")
    assert error.value.status_code == 409
    assert list_world_containers(root) == [first]


def test_existing_directory_is_preserved_without_becoming_a_source_or_identity(root):
    directory = root / "corpus/stolen-path-markdown"
    directory.mkdir(parents=True)
    notes = directory / "notes.md"
    notes.write_text("original source\n")
    assert list_world_containers(root) == []
    created = create_world_container(root, name="Stolen Path")
    assert created.world_id == "stolen-path"
    assert notes.read_text() == "original source\n"
    assert not (root / "out/workspace").exists()


@pytest.mark.parametrize("content", ["not json", '{"schema_version":"dmb_world_container_registry_v1","records":[]}', '{"records":[{"world_id":"shadow"}]}'])
def test_missing_malformed_and_old_world_files_never_select_metadata(root, content):
    created = create_world_container(root, name="Actual World")
    path = legacy_world_catalog_path(root)
    path.parent.mkdir(parents=True)
    path.write_text(content)
    original = path.read_bytes()
    assert list_world_containers(root) == [created]
    with pytest.raises(WorldContainerRegistryError) as error:
        get_world_container(root, "shadow")
    assert error.value.status_code == 404
    moved = path.with_name("retained-copy.json")
    path.rename(moved)
    assert get_world_container(root, created.world_id) == created
    assert moved.read_bytes() == original


def test_database_failure_cannot_fall_back_to_a_file_or_expose_details(root, monkeypatch):
    path = legacy_world_catalog_path(root)
    path.parent.mkdir(parents=True)
    path.write_text('{"records":[]}')
    def unavailable():
        raise ApplicationStateUnavailableError("private database details")
    monkeypatch.setattr(registry.catalog, "list_worlds", unavailable)
    with pytest.raises(WorldContainerRegistryError) as error:
        list_world_containers(root)
    assert error.value.status_code == 503
    assert "private" not in str(error.value)
    assert path.read_text() == '{"records":[]}'


def test_client_cannot_supply_world_id_or_path_via_create_api_shape():
    for field in ("world_id", "source_root_relpath"):
        with pytest.raises(ValidationError):
            registry.CreateWorldContainerRequest.model_validate({"name": "X", field: "client-chosen"})


def _page(root, world_id):
    return create_workspace_document(root, title="First Source", campaign_id=world_id,
        kind="worldbuilding_source", world_id=world_id, source_domain="worldbuilding",
        document_class="lore", authority_state="draft", visibility_state="internal")


def test_registered_world_allows_page_without_a_corpus_folder(root):
    world = create_world_container(root, name="Composable World")
    created = _page(root, world.world_id)
    assert created.world_id == world.world_id
    assert created.target_relpath == f"{world.source_root_relpath}/_dungeonbuddy/sources/{created.document_id}/source.md"
    assert not (root / world.source_root_relpath).exists()


def test_unregistered_directory_cannot_authorize_a_page(root):
    (root / "corpus/no-such-world-markdown").mkdir(parents=True)
    with pytest.raises(WorkspaceDocumentRegistryError) as error:
        _page(root, "no-such-world")
    assert error.value.status_code == 404


def test_registered_page_storage_cannot_escape_through_a_symlink(root, tmp_path):
    world = create_world_container(root, name="Escaped World")
    outside = tmp_path.parent / (tmp_path.name + "-outside")
    outside.mkdir()
    target = root / world.source_root_relpath
    target.parent.mkdir(parents=True)
    target.symlink_to(outside, target_is_directory=True)
    with pytest.raises(WorkspaceDocumentRegistryError, match="escapes"):
        _page(root, world.world_id)
    assert list(outside.iterdir()) == []


def test_registry_schema_constant():
    assert REGISTRY_SCHEMA == "dmb_world_container_registry_v3"


def test_fresh_world_reservation_is_durable_private_and_unique(root: Path) -> None:
    from apps.live_control_server.services.world_container_registry import (
        NativeGraphProvisioningRecord, WorldContainerPublicRecord,
    )
    first = create_world_container(root, name="First fresh World")
    reserved = first.native_graph_binding
    assert isinstance(reserved, NativeGraphProvisioningRecord)
    assert reserved.native_world_id != first.world_id
    assert "validated_head_revision_id" not in reserved.model_dump()
    assert get_world_container(root, first.world_id).native_graph_binding == reserved
    assert create_world_container(root, name="first fresh world") == first
    other = create_world_container(root, name="Second fresh World")
    assert other.native_graph_binding.native_world_id != reserved.native_world_id
    assert other.native_graph_binding.provisioning_id != reserved.provisioning_id
    public = WorldContainerPublicRecord.from_record(first).model_dump_json()
    assert reserved.native_world_id not in public
    assert reserved.provisioning_id not in public
    assert '"status":"provisioning"' in public


def test_reservation_grants_source_identity_without_graph_read_or_binding_authority(root: Path) -> None:
    from apps.live_control_server.services.managed_world_graph_projection import (
        resolve_managed_source_identity, resolve_managed_world_binding,
        WorldGraphProjectionServiceError,
    )
    from apps.live_control_server.services.world_graph_binding import (
        bind_native_graph, deactivate_native_graph_binding, WorldGraphBindingError,
    )
    from apps.live_control_server.services.first_world_graph import first_world_native_target

    world = create_world_container(root, name="Reserved sources")
    reserved = world.native_graph_binding
    source = resolve_managed_source_identity(world.world_id, root=root)
    assert source.native_world_id == reserved.native_world_id
    with pytest.raises(WorldGraphProjectionServiceError) as error:
        resolve_managed_world_binding(world.world_id, root=root)
    assert error.value.code == "native_graph_provisioning_pending"
    with pytest.raises(WorldGraphBindingError):
        bind_native_graph(root, world.world_id, native_world_id="other", expected_binding_version=1,
                          authority_validator=lambda _: pytest.fail("must reject before native read"))
    with pytest.raises(WorldGraphBindingError):
        deactivate_native_graph_binding(root, world.world_id, expected_binding_version=1)
    target = first_world_native_target(root, world.world_id)
    assert target.native_world_id == reserved.native_world_id
    assert target.provisioning_id == reserved.provisioning_id
    assert get_world_container(root, world.world_id) == world


def test_reservation_cannot_be_duplicated_in_registry(root: Path) -> None:
    from apps.live_control_server.services.world_container_registry import WorldContainerRegistryDocument
    from pydantic import ValidationError
    first = create_world_container(root, name="Reserved first")
    second = create_world_container(root, name="Reserved second")
    with pytest.raises(ValidationError):
        WorldContainerRegistryDocument(records=[first, second.model_copy(update={
            "native_graph_binding": first.native_graph_binding,
        })])


def test_reconcile_existing_unbound_world_does_not_allocate_or_rewrite(root):
    world = create_world_container(root, name="Retained unbound")
    retained = store_world(world.model_copy(update={"native_graph_binding": None}))
    before = world_snapshot()
    assert create_world_container(root, name="retained unbound") == retained
    assert world_snapshot() == before


def test_concurrent_fresh_world_create_reuses_one_reservation(root: Path) -> None:
    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor(max_workers=4) as executor:
        records = list(executor.map(lambda _: create_world_container(root, name="Concurrent World"), range(8)))
    assert all(record == records[0] for record in records)
    assert len(list_world_containers(root)) == 1
