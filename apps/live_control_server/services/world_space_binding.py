"""Durable, retry-safe World → MIND KnowledgeSpace binding."""

from __future__ import annotations

import re
from collections.abc import Callable
from pathlib import Path
from typing import Any
from uuid import uuid4

from apps.live_control_server.integrations.dungeonmind.world_space_provisioning import (
    provision_empty_world_space,
)
from apps.live_control_server.services.registry_file_lock import (
    registry_mutation_lock,
)
from apps.live_control_server.services.world_container_registry import (
    SPACE_BINDING_VERSION,
    WorldContainerRecord,
    WorldContainerRegistryDocument,
    _load_unlocked,
    _validate_world_id,
    replace_world_container_record,
    world_containers_path,
    world_source_root_relpath,
)

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


class WorldSpaceBindingError(ValueError):
    """Expected fail-closed binding failures suitable for route mapping."""

    def __init__(self, message: str, *, status_code: int = 409) -> None:
        super().__init__(message)
        self.status_code = status_code


Provisioner = Callable[..., Any]


def _receipt_payload(receipt: Any, *, allocation_id: str) -> tuple[dict[str, Any], str]:
    if not hasattr(receipt, "model_dump") and not isinstance(receipt, dict):
        raise WorldSpaceBindingError(
            "DungeonMind returned an invalid provisioning receipt", status_code=502
        )
    try:
        from dungeonmind.contracts.vnext.space_provisioning import (
            KnowledgeSpaceProvisioningReceipt,
        )

        validated = KnowledgeSpaceProvisioningReceipt.model_validate(receipt)
        payload = validated.model_dump(mode="json")
    except (ImportError, TypeError, ValueError) as exc:
        raise WorldSpaceBindingError(
            "DungeonMind returned an invalid provisioning receipt", status_code=502
        ) from exc
    if not isinstance(payload, dict):
        raise WorldSpaceBindingError(
            "DungeonMind returned an invalid provisioning receipt", status_code=502
        )
    publication = payload.get("publication_receipt")
    space_id = payload.get("space_id")
    if (
        payload.get("schema_version") != "dm_knowledge_space_provisioning_receipt_v1"
        or payload.get("status") != "provisioned"
        or payload.get("allocation_id") != allocation_id
        or not isinstance(space_id, str)
        or not space_id.strip()
        or not isinstance(payload.get("request_sha256"), str)
        or not _SHA256_RE.fullmatch(payload["request_sha256"])
        or not isinstance(publication, dict)
        or publication.get("space_id") != space_id
        or publication.get("publication_id") != "space-genesis"
        or publication.get("expected_parent_revision_id") is not None
        or publication.get("status") != "published"
        or not publication.get("published_revision_id")
    ):
        raise WorldSpaceBindingError(
            "DungeonMind provisioning receipt did not match the pending allocation",
            status_code=502,
        )
    return payload, space_id


def _load_managed_record(
    document: WorldContainerRegistryDocument, world_id: str, root: Path
) -> WorldContainerRecord:
    record = next((row for row in document.records if row.world_id == world_id), None)
    if record is None:
        raise WorldSpaceBindingError("world container not found", status_code=404)
    if (
        record.source_root_relpath != world_source_root_relpath(record.world_id)
        or not (root / record.source_root_relpath).is_dir()
    ):
        raise WorldSpaceBindingError(
            "world container is not a verified managed World", status_code=409
        )
    return record


def provision_world_space(
    root: Path,
    world_id: str,
    *,
    database_url: str | None = None,
    provisioner: Provisioner | None = None,
) -> WorldContainerRecord:
    """Bind one verified World to an empty MIND space, retrying by allocation key.

    The existing registry mutation lock is held only while persisting PENDING
    and while committing the final CAS. The external MIND call runs unlocked.
    """
    cleaned = _validate_world_id(world_id)
    path = world_containers_path(root)
    with registry_mutation_lock(path):
        document, token = _load_unlocked(root)
        record = _load_managed_record(document, cleaned, root)
        if record.space_binding_status == "active":
            return record
        if record.space_binding_status == "unbound":
            allocation_id = f"dmb-world-space-{uuid4().hex}"
            pending = record.model_copy(
                update={
                    "space_binding_status": "pending",
                    "space_allocation_id": allocation_id,
                }
            )
            replace_world_container_record(root, pending, expected_token=token)
        elif record.space_binding_status == "pending":
            allocation_id = record.space_allocation_id or ""
            if not allocation_id:
                raise WorldSpaceBindingError(
                    "pending World binding has no allocation identity", status_code=500
                )
        else:  # pragma: no cover - Literal validation prevents this
            raise WorldSpaceBindingError("unknown World binding state", status_code=500)

    call = provisioner or provision_empty_world_space
    try:
        receipt = call(allocation_id=allocation_id, database_url=database_url)
    except WorldSpaceBindingError:
        raise
    except Exception as exc:
        # Keep PENDING: the remote outcome may be uncertain. The next attempt
        # must retry MIND with the exact same allocation key.
        raise WorldSpaceBindingError(
            "DungeonMind space provisioning is unavailable; retry the same World",
            status_code=503,
        ) from exc
    payload, space_id = _receipt_payload(receipt, allocation_id=allocation_id)

    with registry_mutation_lock(path):
        current_document, token = _load_unlocked(root)
        current = _load_managed_record(current_document, cleaned, root)
        if current.space_binding_status == "active":
            if (
                current.space_allocation_id == allocation_id
                and current.space_id == space_id
                and current.space_provisioning_receipt == payload
            ):
                return current
            raise WorldSpaceBindingError(
                "World is already bound to a different KnowledgeSpace"
            )
        if (
            current.space_binding_status != "pending"
            or current.space_allocation_id != allocation_id
        ):
            raise WorldSpaceBindingError(
                "World binding changed while DungeonMind provisioning was in flight"
            )
        if any(
            other.world_id != cleaned
            and other.space_binding_status == "active"
            and other.space_id == space_id
            for other in current_document.records
        ):
            raise WorldSpaceBindingError(
                "KnowledgeSpace is already bound to another World"
            )
        active = current.model_copy(
            update={
                "space_binding_status": "active",
                "space_binding_version": SPACE_BINDING_VERSION,
                "space_id": space_id,
                "space_provisioning_receipt": payload,
            }
        )
        replace_world_container_record(root, active, expected_token=token)
        return active
