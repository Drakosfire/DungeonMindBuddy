"""Synthetic World ownership, sharing, and fail-closed action checks."""

from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from apps.live_control_server.services.world_container_registry import (
    WorldAccessDenied,
    WorldContainerRegistryError,
    WorldPermission,
    authorize_world_access,
    create_world_container,
    grant_world_access,
    revoke_world_access,
    world_containers_path,
)


@pytest.fixture
def root(tmp_path: Path) -> Path:
    return tmp_path


def test_owner_has_normal_world_use_and_new_world_is_private(root: Path) -> None:
    world = create_world_container(root, name="Owner Test", owner_subject="subject:owner")

    assert world.owner_subject == "subject:owner"
    assert world.access_grants == []
    for permission in WorldPermission:
        assert authorize_world_access(
            root, world.world_id, subject="subject:owner", permission=permission
        ) == world
    for subject in (None, "subject:other"):
        with pytest.raises(WorldAccessDenied) as denied:
            authorize_world_access(
                root, world.world_id, subject=subject, permission=WorldPermission.READ
            )
        assert denied.value.status_code == 404
        assert str(denied.value) == "World access denied"
    with pytest.raises(WorldAccessDenied) as missing:
        authorize_world_access(
            root, "missing-world", subject="subject:other", permission="read"
        )
    assert str(missing.value) == "World access denied"


def test_same_display_name_does_not_merge_creators_or_legacy_unowned_worlds(
    root: Path,
) -> None:
    legacy = create_world_container(root, name="Test Realm")
    first = create_world_container(root, name="Test Realm", owner_subject="subject:one")
    second = create_world_container(root, name="Test Realm", owner_subject="subject:two")
    first_retry = create_world_container(
        root, name="  TEST REALM  ", owner_subject="subject:one"
    )

    assert len({legacy.world_id, first.world_id, second.world_id}) == 3
    assert first.world_id == first_retry.world_id
    assert first.owner_subject == "subject:one"
    assert second.owner_subject == "subject:two"
    assert legacy.owner_subject is None
    assert len({row.source_root_relpath for row in (legacy, first, second)}) == 3
    with pytest.raises(WorldAccessDenied):
        authorize_world_access(
            root, legacy.world_id, subject="subject:one", permission="read"
        )


def test_read_only_grant_cannot_write_manage_or_share(root: Path) -> None:
    world = create_world_container(root, name="Read Only", owner_subject="subject:owner")
    grant_world_access(
        root,
        world.world_id,
        actor_subject="subject:owner",
        subject="subject:reader",
        permissions=["read"],
    )

    assert authorize_world_access(
        root, world.world_id, subject="subject:reader", permission="read"
    ).world_id == world.world_id
    for action in ("write", "manage", "share"):
        with pytest.raises(WorldAccessDenied):
            authorize_world_access(
                root, world.world_id, subject="subject:reader", permission=action
            )


def test_write_and_manage_grants_do_not_imply_other_actions(root: Path) -> None:
    world = create_world_container(root, name="Independent Actions", owner_subject="subject:owner")
    grant_world_access(
        root,
        world.world_id,
        actor_subject="subject:owner",
        subject="subject:writer",
        permissions=["write"],
    )
    grant_world_access(
        root,
        world.world_id,
        actor_subject="subject:owner",
        subject="subject:manager",
        permissions=["manage"],
    )

    assert authorize_world_access(
        root, world.world_id, subject="subject:writer", permission="write"
    ).world_id == world.world_id
    assert authorize_world_access(
        root, world.world_id, subject="subject:manager", permission="manage"
    ).world_id == world.world_id
    for subject, actions in (
        ("subject:writer", ("read", "manage", "share")),
        ("subject:manager", ("read", "write", "share")),
    ):
        for action in actions:
            with pytest.raises(WorldAccessDenied):
                authorize_world_access(
                    root, world.world_id, subject=subject, permission=action
                )


def test_permissions_are_explicit_and_unknown_values_deny(root: Path) -> None:
    world = create_world_container(root, name="Explicit Actions", owner_subject="subject:owner")
    with pytest.raises(WorldAccessDenied):
        authorize_world_access(
            root, world.world_id, subject="subject:owner", permission="admin"
        )
    with pytest.raises(WorldAccessDenied):
        grant_world_access(
            root,
            world.world_id,
            actor_subject="subject:owner",
            subject="subject:guest",
            permissions=["read", "admin"],
        )
    with pytest.raises(WorldAccessDenied):
        authorize_world_access(
            root, world.world_id, subject="subject:guest", permission="read"
        )


def test_delegated_sharing_is_bounded_and_revocation_cascades(root: Path) -> None:
    world = create_world_container(root, name="Sharing Boundaries", owner_subject="subject:owner")
    grant_world_access(
        root,
        world.world_id,
        actor_subject="subject:owner",
        subject="subject:sharer",
        permissions=["read", "write", "share"],
    )
    grant_world_access(
        root,
        world.world_id,
        actor_subject="subject:owner",
        subject="subject:direct-reader",
        permissions=["read"],
    )
    grant_world_access(
        root,
        world.world_id,
        actor_subject="subject:owner",
        subject="subject:read-sharer",
        permissions=["read", "share"],
    )
    grant_world_access(
        root,
        world.world_id,
        actor_subject="subject:sharer",
        subject="subject:delegate",
        permissions=["read", "write"],
    )
    assert authorize_world_access(
        root, world.world_id, subject="subject:delegate", permission="write"
    ).world_id == world.world_id

    with pytest.raises(WorldAccessDenied):
        grant_world_access(
            root,
            world.world_id,
            actor_subject="subject:sharer",
            subject="subject:escalated",
            permissions=["manage"],
        )
    with pytest.raises(WorldAccessDenied):
        grant_world_access(
            root,
            world.world_id,
            actor_subject="subject:read-sharer",
            subject="subject:unearned-write",
            permissions=["write"],
        )
    with pytest.raises(WorldAccessDenied):
        grant_world_access(
            root,
            world.world_id,
            actor_subject="subject:sharer",
            subject="subject:escalated-share",
            permissions=["share"],
        )

    with pytest.raises(WorldAccessDenied):
        revoke_world_access(
            root,
            world.world_id,
            actor_subject="subject:sharer",
            subject="subject:direct-reader",
        )
    revoke_world_access(
        root,
        world.world_id,
        actor_subject="subject:sharer",
        subject="subject:delegate",
    )
    with pytest.raises(WorldAccessDenied):
        authorize_world_access(
            root, world.world_id, subject="subject:delegate", permission="read"
        )

    grant_world_access(
        root,
        world.world_id,
        actor_subject="subject:owner",
        subject="subject:delegate",
        permissions=["read", "share"],
    )
    grant_world_access(
        root,
        world.world_id,
        actor_subject="subject:delegate",
        subject="subject:leaf",
        permissions=["read"],
    )
    revoke_world_access(
        root,
        world.world_id,
        actor_subject="subject:owner",
        subject="subject:delegate",
    )
    for subject in ("subject:delegate", "subject:leaf"):
        with pytest.raises(WorldAccessDenied):
            authorize_world_access(root, world.world_id, subject=subject, permission="read")
    assert authorize_world_access(
        root, world.world_id, subject="subject:sharer", permission="read"
    ).world_id == world.world_id
    assert authorize_world_access(
        root, world.world_id, subject="subject:direct-reader", permission="read"
    ).world_id == world.world_id


def test_non_owner_can_only_revoke_grants_they_created(root: Path) -> None:
    world = create_world_container(root, name="Grant Provenance", owner_subject="subject:owner")
    grant_world_access(
        root,
        world.world_id,
        actor_subject="subject:owner",
        subject="subject:sharer",
        permissions=["read", "share"],
    )
    grant_world_access(
        root,
        world.world_id,
        actor_subject="subject:owner",
        subject="subject:direct",
        permissions=["read"],
    )
    grant_world_access(
        root,
        world.world_id,
        actor_subject="subject:sharer",
        subject="subject:reader",
        permissions=["read"],
    )

    revoke_world_access(
        root, world.world_id, actor_subject="subject:sharer", subject="subject:reader"
    )
    with pytest.raises(WorldAccessDenied):
        authorize_world_access(root, world.world_id, subject="subject:reader", permission="read")
    with pytest.raises(WorldAccessDenied):
        revoke_world_access(
            root, world.world_id, actor_subject="subject:sharer", subject="subject:direct"
        )


def test_resource_world_mismatch_denies_even_when_subject_owns_requested_world(
    root: Path,
) -> None:
    owned = create_world_container(root, name="Owned Resource", owner_subject="subject:owner")
    other = create_world_container(root, name="Other Resource", owner_subject="subject:someone")

    with pytest.raises(WorldAccessDenied):
        authorize_world_access(
            root,
            owned.world_id,
            subject="subject:owner",
            permission="read",
            resource_world_id=other.world_id,
        )


def test_owner_grants_serialize_as_v3_and_concurrent_updates_do_not_overwrite(
    root: Path,
) -> None:
    world = create_world_container(root, name="Concurrent Grants", owner_subject="subject:owner")
    subjects = [f"subject:reader-{index}" for index in range(8)]

    def add_grant(subject: str) -> None:
        grant_world_access(
            root,
            world.world_id,
            actor_subject="subject:owner",
            subject=subject,
            permissions=["read"],
        )

    with ThreadPoolExecutor(max_workers=4) as executor:
        list(executor.map(add_grant, subjects))

    stored = json.loads(world_containers_path(root).read_text(encoding="utf-8"))
    [stored_world] = stored["records"]
    assert stored["schema_version"] == "dmb_world_container_registry_v3"
    assert stored_world["schema_version"] == "dmb_world_container_record_v3"
    assert {grant["subject"] for grant in stored_world["access_grants"]} == set(subjects)
    assert [grant["subject"] for grant in stored_world["access_grants"]] == sorted(subjects)
    assert all(grant["permissions"] == ["read"] for grant in stored_world["access_grants"])
    for subject in subjects:
        assert authorize_world_access(
            root, world.world_id, subject=subject, permission="read"
        ).world_id == world.world_id


def test_stale_registry_cas_cannot_overwrite_serialized_access_state(root: Path) -> None:
    from apps.live_control_server.services.registry_file_lock import registry_token
    from apps.live_control_server.services.world_container_registry import (
        _load_unlocked,
        _save_cas,
    )

    world = create_world_container(root, name="CAS Grant State", owner_subject="subject:owner")
    document, stale_token = _load_unlocked(root)
    grant_world_access(
        root,
        world.world_id,
        actor_subject="subject:owner",
        subject="subject:reader",
        permissions=["read"],
    )
    before = world_containers_path(root).read_bytes()

    with pytest.raises(WorldContainerRegistryError) as error:
        _save_cas(root, document, expected_token=stale_token)
    assert error.value.status_code == 409
    assert world_containers_path(root).read_bytes() == before
    assert registry_token(world_containers_path(root)) != stale_token
    assert authorize_world_access(
        root, world.world_id, subject="subject:reader", permission="read"
    ).world_id == world.world_id
