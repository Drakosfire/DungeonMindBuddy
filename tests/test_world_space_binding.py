"""World → MIND KnowledgeSpace binding state and retry invariants."""

from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from apps.live_control_server.routes.world_containers import (
    ProvisionWorldSpaceRequest,
    get_world_containers,
    post_world_space_binding,
)
from apps.live_control_server.services.registry_file_lock import registry_mutation_lock
from apps.live_control_server.services.world_container_registry import (
    create_world_container,
    get_world_container,
    list_world_containers,
    world_containers_path,
)
from apps.live_control_server.services.world_space_binding import (
    WorldSpaceBindingError,
    provision_world_space,
)


def _receipt(allocation_id: str, space_id: str) -> dict[str, Any]:
    return {
        "schema_version": "dm_knowledge_space_provisioning_receipt_v1",
        "allocation_id": allocation_id,
        "request_sha256": "a" * 64,
        "space_id": space_id,
        "publication_receipt": {
            "schema_version": "dm_knowledge_publication_receipt_v1",
            "space_id": space_id,
            "publication_id": "space-genesis",
            "command_sha256": "b" * 64,
            "expected_parent_revision_id": None,
            "published_revision_id": f"rev:{space_id}",
            "graph_payload_sha256": "c" * 64,
            "status": "published",
        },
        "status": "provisioned",
    }


def test_v1_registry_records_load_as_explicitly_unbound(tmp_path: Path) -> None:
    path = world_containers_path(tmp_path)
    path.parent.mkdir(parents=True)
    path.write_text(
        json.dumps(
            {
                "schema_version": "dmb_world_container_registry_v1",
                "records": [
                    {
                        "schema_version": "dmb_world_container_record_v1",
                        "world_id": "old-world",
                        "name": "Old World",
                        "source_root_relpath": "corpus/old-world-markdown",
                        "created_at": "2026-01-01T00:00:00Z",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    (tmp_path / "corpus/old-world-markdown").mkdir(parents=True)

    record = list_world_containers(tmp_path)[0]
    assert record.space_binding_status == "unbound"
    assert record.space_binding_version is None
    assert record.space_id is None


def test_pending_is_persisted_before_unlocked_mind_call_and_receipt_is_exact(
    tmp_path: Path,
) -> None:
    world = create_world_container(tmp_path, name="Genesis Vale")
    other_thread_acquired_lock = threading.Event()
    allocation_ids: list[str] = []

    def provisioner(*, allocation_id: str, database_url: str | None) -> dict[str, Any]:
        del database_url
        allocation_ids.append(allocation_id)
        pending = get_world_container(tmp_path, world.world_id)
        assert pending.space_binding_status == "pending"
        assert pending.space_allocation_id == allocation_id

        def acquire() -> None:
            with registry_mutation_lock(world_containers_path(tmp_path)):
                other_thread_acquired_lock.set()

        contender = threading.Thread(target=acquire)
        contender.start()
        assert other_thread_acquired_lock.wait(timeout=1)
        contender.join(timeout=1)
        return _receipt(allocation_id, "space:dm:minted-opaque-id")

    active = provision_world_space(tmp_path, world.world_id, provisioner=provisioner)
    assert active.space_binding_status == "active"
    assert active.space_binding_version == 1
    assert active.space_id == "space:dm:minted-opaque-id"
    assert active.space_id != active.world_id
    assert active.space_allocation_id == allocation_ids[0]
    assert active.space_provisioning_receipt == _receipt(
        allocation_ids[0], "space:dm:minted-opaque-id"
    )


def test_uncertain_response_retries_with_same_allocation_id(tmp_path: Path) -> None:
    world = create_world_container(tmp_path, name="Retry Vale")
    attempted: list[str] = []

    def lost(*, allocation_id: str, database_url: str | None) -> None:
        del database_url
        attempted.append(allocation_id)
        raise TimeoutError("response lost after MIND committed")

    with pytest.raises(WorldSpaceBindingError) as exc_info:
        provision_world_space(tmp_path, world.world_id, provisioner=lost)
    assert exc_info.value.status_code == 503
    pending = get_world_container(tmp_path, world.world_id)
    assert pending.space_binding_status == "pending"

    active = provision_world_space(
        tmp_path,
        world.world_id,
        provisioner=lambda *, allocation_id, database_url: _receipt(
            attempted.append(allocation_id) or allocation_id,
            "space:dm:retry-result",
        ),
    )
    assert len(attempted) == 2
    assert attempted[0] == attempted[1] == active.space_allocation_id
    assert active.space_id == "space:dm:retry-result"


def test_concurrent_retry_has_one_stable_allocation_and_one_binding(tmp_path: Path) -> None:
    world = create_world_container(tmp_path, name="Concurrent Vale")
    barrier = threading.Barrier(2)
    observed: list[str] = []
    results: list[Any] = []
    failures: list[BaseException] = []

    def provisioner(*, allocation_id: str, database_url: str | None) -> dict[str, Any]:
        del database_url
        observed.append(allocation_id)
        barrier.wait(timeout=2)
        return _receipt(allocation_id, "space:dm:concurrent")

    def run() -> None:
        try:
            results.append(
                provision_world_space(tmp_path, world.world_id, provisioner=provisioner)
            )
        except BaseException as exc:  # surfaced below, preserve thread failure
            failures.append(exc)

    threads = [threading.Thread(target=run) for _ in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=5)
    assert not failures
    assert len(results) == 2
    assert observed[0] == observed[1]
    assert all(row.space_binding_status == "active" for row in results)
    assert len(list_world_containers(tmp_path)) == 1


def test_conflicting_remote_receipt_leaves_pending_and_fails_closed(tmp_path: Path) -> None:
    world = create_world_container(tmp_path, name="Conflict Vale")
    with pytest.raises(WorldSpaceBindingError) as exc_info:
        provision_world_space(
            tmp_path,
            world.world_id,
            provisioner=lambda *, allocation_id, database_url: _receipt(
                "different-allocation", "space:dm:conflicting"
            ),
        )
    assert exc_info.value.status_code == 502
    record = get_world_container(tmp_path, world.world_id)
    assert record.space_binding_status == "pending"
    assert record.space_id is None


def test_one_to_one_space_identity_and_no_ordinary_rebind(tmp_path: Path) -> None:
    first = create_world_container(tmp_path, name="First Vale")
    second = create_world_container(tmp_path, name="Second Vale")
    calls: list[str] = []

    def same_space(*, allocation_id: str, database_url: str | None) -> dict[str, Any]:
        del database_url
        calls.append(allocation_id)
        return _receipt(allocation_id, "space:dm:shared")

    bound = provision_world_space(tmp_path, first.world_id, provisioner=same_space)
    with pytest.raises(WorldSpaceBindingError):
        provision_world_space(tmp_path, second.world_id, provisioner=same_space)
    again = provision_world_space(
        tmp_path,
        first.world_id,
        provisioner=lambda **kwargs: pytest.fail("active binding must not call MIND"),
    )
    assert again.space_id == bound.space_id
    assert len(calls) == 2
    assert get_world_container(tmp_path, second.world_id).space_binding_status == "pending"


def test_binding_transition_rejects_changed_pending_token(tmp_path: Path) -> None:
    world = create_world_container(tmp_path, name="Changed Vale")

    def mutate_pending(*, allocation_id: str, database_url: str | None) -> dict[str, Any]:
        del database_url
        with registry_mutation_lock(world_containers_path(tmp_path)):
            path = world_containers_path(tmp_path)
            data = json.loads(path.read_text(encoding="utf-8"))
            data["records"][0]["space_allocation_id"] = "operator-replaced-key"
            path.write_text(json.dumps(data), encoding="utf-8")
        return _receipt(allocation_id, "space:dm:changed")

    with pytest.raises(WorldSpaceBindingError, match="changed while"):
        provision_world_space(tmp_path, world.world_id, provisioner=mutate_pending)
    assert get_world_container(tmp_path, world.world_id).space_id is None


def test_api_redacts_mind_ids_receipt_and_rejects_caller_identity(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "apps.live_control_server.routes.world_containers.repo_root", lambda: tmp_path
    )
    world = create_world_container(tmp_path, name="HTTP Vale")
    monkeypatch.setattr(
        "apps.live_control_server.routes.world_containers.provision_world_space",
        lambda *_args, **_kwargs: provision_world_space(
            tmp_path,
            world.world_id,
            provisioner=lambda *, allocation_id, database_url: _receipt(
                allocation_id, "space:dm:hidden"
            ),
        ),
    )
    with pytest.raises(ValidationError):
        ProvisionWorldSpaceRequest.model_validate({"space_id": "caller-choice"})
    public_record = post_world_space_binding(world.world_id, ProvisionWorldSpaceRequest())
    assert public_record["space_binding_status"] == "active"
    assert public_record["space_binding_version"] == 1
    assert not {"space_id", "space_allocation_id", "space_provisioning_receipt"} & set(
        public_record
    )
    listed = get_world_containers()["records"][0]
    assert listed == public_record


def test_ordinary_rebind_is_not_permitted(tmp_path: Path) -> None:
    world = create_world_container(tmp_path, name="Bound Once")
    first = provision_world_space(
        tmp_path,
        world.world_id,
        provisioner=lambda *, allocation_id, database_url: _receipt(
            allocation_id, "space:dm:original"
        ),
    )
    reloaded = get_world_container(tmp_path, world.world_id)
    assert reloaded.space_id == first.space_id
    again = provision_world_space(
        tmp_path,
        world.world_id,
        provisioner=lambda **kwargs: pytest.fail("active binding must not be rebound"),
    )
    assert again.space_id == first.space_id
