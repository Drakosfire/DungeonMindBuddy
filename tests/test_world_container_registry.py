"""Managed world-container registry: identity, root lifecycle, fail-closed collisions."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from apps.live_control_server.services.world_container_registry import (
    REGISTRY_SCHEMA,
    WorldContainerRegistryError,
    create_world_container,
    derive_world_id_from_name,
    get_world_container,
    list_world_containers,
    normalize_world_name_for_compare,
    world_containers_path,
    world_source_root_relpath,
)
from apps.live_control_server.services.workspace_document_registry import (
    create_workspace_document,
)


@pytest.fixture
def root(tmp_path: Path) -> Path:
    return tmp_path


def test_create_world_persists_exact_identity_and_root(root: Path) -> None:
    created = create_world_container(root, name="The Glass Orchard")

    assert created.world_id == "the-glass-orchard"
    assert created.name == "The Glass Orchard"
    assert created.source_root_relpath == "corpus/the-glass-orchard-markdown"
    assert (root / created.source_root_relpath).is_dir()
    assert created.schema_version == "dmb_world_container_record_v1"

    listed = list_world_containers(root)
    assert len(listed) == 1
    assert listed[0].model_dump() == created.model_dump()
    assert get_world_container(root, created.world_id).model_dump() == created.model_dump()
    assert world_containers_path(root).is_file()


def test_reload_returns_same_managed_world(root: Path) -> None:
    created = create_world_container(root, name="One-Shot Vale")
    # Fresh load path (no in-memory cache).
    reloaded = list_world_containers(root)
    assert len(reloaded) == 1
    assert reloaded[0].world_id == created.world_id
    assert reloaded[0].name == "One-Shot Vale"
    assert reloaded[0].source_root_relpath == world_source_root_relpath(created.world_id)


def test_empty_and_whitespace_names_fail_closed(root: Path) -> None:
    for bad in ("", "   ", "\n\t"):
        with pytest.raises(WorldContainerRegistryError) as exc_info:
            create_world_container(root, name=bad)
        assert exc_info.value.status_code == 422
    assert list_world_containers(root) == []
    assert not any((root / "corpus").rglob("*")) if (root / "corpus").exists() else True


def test_same_normalized_name_is_idempotent(root: Path) -> None:
    first = create_world_container(root, name="The Glass Orchard")
    second = create_world_container(root, name="  the   glass   orchard  ")
    assert second.world_id == first.world_id
    assert second.name == first.name
    assert len(list_world_containers(root)) == 1
    assert normalize_world_name_for_compare("  the   glass   orchard  ") == (
        normalize_world_name_for_compare("The Glass Orchard")
    )


def test_derived_id_collision_with_different_name_fails_409(root: Path) -> None:
    create_world_container(root, name="Glass Orchard")
    # Same derived slug, different normalized display name.
    with patch(
        "apps.live_control_server.services.world_container_registry.derive_world_id_from_name",
        side_effect=lambda name: "glass-orchard",
    ):
        with pytest.raises(WorldContainerRegistryError) as exc_info:
            create_world_container(root, name="Different Label")
    assert exc_info.value.status_code == 409
    assert "already exists" in str(exc_info.value).lower()
    assert len(list_world_containers(root)) == 1


def test_unmanaged_existing_root_is_not_adopted(root: Path) -> None:
    world_id = derive_world_id_from_name("Stolen Path")
    unmanaged = root / world_source_root_relpath(world_id)
    unmanaged.mkdir(parents=True)
    (unmanaged / "notes.md").write_text("preexisting\n", encoding="utf-8")

    with pytest.raises(WorldContainerRegistryError) as exc_info:
        create_world_container(root, name="Stolen Path")
    assert exc_info.value.status_code == 409
    assert list_world_containers(root) == []
    assert (unmanaged / "notes.md").read_text(encoding="utf-8") == "preexisting\n"


def test_mkdir_failure_does_not_commit_registry_record(root: Path) -> None:
    world_id = derive_world_id_from_name("Broken Disk")
    target = root / world_source_root_relpath(world_id)
    real_mkdir = Path.mkdir

    def mkdir_fail(self: Path, *args: object, **kwargs: object) -> None:
        if self == target:
            raise OSError("disk full")
        return real_mkdir(self, *args, **kwargs)

    with patch.object(Path, "mkdir", mkdir_fail):
        with pytest.raises(WorldContainerRegistryError) as exc_info:
            create_world_container(root, name="Broken Disk")
    assert exc_info.value.status_code == 500
    assert list_world_containers(root) == []
    assert not world_containers_path(root).is_file()
    assert not target.exists()


def test_registry_persist_failure_removes_only_newly_created_empty_root(root: Path) -> None:
    world_id = derive_world_id_from_name("Persist Fail")
    target = root / world_source_root_relpath(world_id)

    with patch(
        "apps.live_control_server.services.world_container_registry.write_json",
        side_effect=OSError("persist failed"),
    ):
        with pytest.raises(WorldContainerRegistryError) as exc_info:
            create_world_container(root, name="Persist Fail")
    assert exc_info.value.status_code == 500
    assert list_world_containers(root) == []
    assert not target.exists()


def test_client_cannot_supply_world_id_or_path_via_create_api_shape() -> None:
    from pydantic import ValidationError

    from apps.live_control_server.services.world_container_registry import (
        CreateWorldContainerRequest,
    )

    with pytest.raises(ValidationError):
        CreateWorldContainerRequest.model_validate(
            {"name": "X", "world_id": "client-chosen"}
        )
    with pytest.raises(ValidationError):
        CreateWorldContainerRequest.model_validate(
            {"name": "X", "source_root_relpath": "corpus/x-markdown"}
        )


def test_managed_root_enables_workspace_source_without_weakening_missing_root(
    root: Path,
) -> None:
    world = create_world_container(root, name="Composable World")
    created = create_workspace_document(
        root,
        title="First Source",
        campaign_id=world.world_id,
        kind="worldbuilding_source",
        world_id=world.world_id,
        source_domain="worldbuilding",
        document_class="lore",
        authority_state="draft",
        visibility_state="internal",
    )
    assert created.world_id == world.world_id
    assert created.campaign_id == world.world_id
    assert created.target_relpath == (
        f"{world.source_root_relpath}/_dungeonbuddy/sources/{created.document_id}/source.md"
    )

    with pytest.raises(Exception) as exc_info:
        create_workspace_document(
            root,
            title="Missing",
            campaign_id="no-such-world",
            kind="worldbuilding_source",
            world_id="no-such-world",
            source_domain="worldbuilding",
            document_class="lore",
            authority_state="draft",
            visibility_state="internal",
        )
    assert "world source root is missing" in str(exc_info.value)


def test_registry_schema_constant() -> None:
    assert REGISTRY_SCHEMA == "dmb_world_container_registry_v1"
