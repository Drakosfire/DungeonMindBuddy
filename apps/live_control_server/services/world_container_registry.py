"""Managed World metadata and product access policy over the APP catalog."""
from __future__ import annotations

import re
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from application_state.errors import ApplicationStateError
from application_state.world_catalog import service as catalog
from application_state.world_catalog.service import StoredWorld, normalize_world_name_for_compare
from application_state.world_catalog.types import (
    REGISTRY_SCHEMA as REGISTRY_SCHEMA, RECORD_SCHEMA as RECORD_SCHEMA,
    PUBLIC_REGISTRY_SCHEMA, PUBLIC_RECORD_SCHEMA,
    WorldPermission, WorldAccessGrant,
    NativeGraphBindingRecord as NativeGraphBindingRecord,
    NativeGraphProvisioningRecord as NativeGraphProvisioningRecord,
    WorldContainerRecord, WorldContainerRegistryDocument as WorldContainerRegistryDocument,
    _PERMISSION_ORDER, _DELEGABLE_WORLD_PERMISSIONS, _validate_subject,
)

_SAFE_WORLD_ID_RE = re.compile(r"^[a-z][a-z0-9_-]{0,62}$")


class WorldContainerRegistryError(ValueError):
    status_code: int = 404

    def __init__(self, message: str, *, status_code: int = 404) -> None:
        super().__init__(message)
        self.status_code = status_code


class WorldAccessDenied(ValueError):
    """Generic denial that does not reveal whether a World ID exists."""

    status_code = 404


class NativeGraphBindingPublicStatus(BaseModel):
    """Only the operational state of a binding is exposed to the local UI."""

    model_config = ConfigDict(extra="forbid")

    status: Literal["unbound", "active", "inactive", "provisioning"]
    binding_version: int = Field(ge=0)


class WorldContainerPublicRecord(BaseModel):
    """Stable HTTP view; owner/grants and native authority data stay private."""

    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["dmb_world_container_record_v1"] = PUBLIC_RECORD_SCHEMA
    world_id: str
    name: str
    source_root_relpath: str
    created_at: str
    native_graph_binding: NativeGraphBindingPublicStatus = Field(
        default_factory=lambda: NativeGraphBindingPublicStatus(
            status="unbound",
            binding_version=0,
        )
    )

    @classmethod
    def from_record(cls, record: WorldContainerRecord) -> "WorldContainerPublicRecord":
        binding = record.native_graph_binding
        return cls(
            world_id=record.world_id,
            name=record.name,
            source_root_relpath=record.source_root_relpath,
            created_at=record.created_at,
            native_graph_binding=(
                NativeGraphBindingPublicStatus(
                    status=binding.status,
                    binding_version=binding.binding_version,
                )
                if binding is not None
                else NativeGraphBindingPublicStatus(
                    status="unbound",
                    binding_version=0,
                )
            ),
        )


class WorldContainersListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["dmb_world_container_registry_v1"] = PUBLIC_REGISTRY_SCHEMA
    records: list[WorldContainerPublicRecord] = Field(default_factory=list)


class CreateWorldContainerRequest(BaseModel):
    """Human-facing create input. Clients must not supply world_id or paths."""

    model_config = ConfigDict(extra="forbid")

    name: str


def _validate_world_id(world_id: str) -> str:
    cleaned = world_id.strip()
    if not cleaned or not _SAFE_WORLD_ID_RE.fullmatch(cleaned):
        raise WorldContainerRegistryError("world_id must match ^[a-z][a-z0-9_-]{0,62}$", status_code=422)
    return cleaned


def _catalog_error(exc: ApplicationStateError) -> WorldContainerRegistryError:
    message = str(exc) if exc.status_code < 500 else (
        "World storage is unavailable." if exc.status_code == 503 else "Stored World metadata is invalid."
    )
    return WorldContainerRegistryError(message, status_code=exc.status_code)


def _stored_world(world_id: str) -> StoredWorld:
    cleaned = _validate_world_id(world_id)
    try:
        stored = catalog.get_world(cleaned)
    except ApplicationStateError as exc:
        raise _catalog_error(exc) from exc
    if stored is None:
        raise WorldContainerRegistryError(f"world container not found: {cleaned}", status_code=404)
    return stored


def list_world_containers(root: Path) -> list[WorldContainerRecord]:
    del root  # Artifact paths cannot select a different metadata catalog.
    try:
        records = [stored.record for stored in catalog.list_worlds()]
    except ApplicationStateError as exc:
        raise _catalog_error(exc) from exc
    return sorted(records, key=lambda record: (record.name.casefold(), record.world_id))


def get_world_container(root: Path, world_id: str) -> WorldContainerRecord:
    del root
    return _stored_world(world_id).record


def find_world_container_by_normalized_name(root: Path, name: str) -> WorldContainerRecord | None:
    needle = normalize_world_name_for_compare(name)
    if not needle:
        return None
    for record in list_world_containers(root):
        if normalize_world_name_for_compare(record.name) == needle:
            return record
    return None


def create_world_container(root: Path, *, name: str, owner_subject: str | None = None) -> WorldContainerRecord:
    """Create/reconcile exact metadata and reservation; never adopt a directory."""
    del root
    try:
        return catalog.create_world(name=name, owner_subject=owner_subject).record
    except ApplicationStateError as exc:
        raise _catalog_error(exc) from exc


def require_world_permission(
    record: WorldContainerRecord,
    *,
    subject: str | None,
    permission: WorldPermission | str,
    resource_world_id: str | None = None,
) -> WorldContainerRecord:
    """Enforce one independent action permission against an authoritative World.

    ``resource_world_id`` must come from server-side resource resolution. A
    caller-supplied selector is not an authority source.
    """
    try:
        exact_subject = _validate_subject(subject)
        requested_permission = WorldPermission(permission)
    except (TypeError, ValueError) as exc:
        raise WorldAccessDenied("World access denied") from exc
    if exact_subject is None:
        raise WorldAccessDenied("World access denied")
    if resource_world_id is not None and resource_world_id != record.world_id:
        raise WorldAccessDenied("World access denied")
    if record.owner_subject == exact_subject:
        return record
    grant = next(
        (item for item in record.access_grants if item.subject == exact_subject),
        None,
    )
    if grant is None or requested_permission not in grant.permissions:
        raise WorldAccessDenied("World access denied")
    return record


def authorize_world_access(
    root: Path, world_id: str, *, subject: str | None,
    permission: WorldPermission | str, resource_world_id: str | None = None,
) -> WorldContainerRecord:
    try:
        record = get_world_container(root, world_id)
    except (TypeError, AttributeError, WorldContainerRegistryError) as exc:
        raise WorldAccessDenied("World access denied") from exc
    return require_world_permission(record, subject=subject, permission=permission,
                                    resource_world_id=resource_world_id)


def _requested_permissions(
    permissions: tuple[WorldPermission | str, ...] | list[WorldPermission | str],
) -> tuple[WorldPermission, ...]:
    try:
        normalized = tuple(WorldPermission(permission) for permission in permissions)
    except (TypeError, ValueError) as exc:
        raise WorldAccessDenied("World access denied") from exc
    if not normalized or len(normalized) != len(set(normalized)):
        raise WorldAccessDenied("World access denied")
    return tuple(sorted(normalized, key=_PERMISSION_ORDER.__getitem__))


def _prune_delegated_grants(record: WorldContainerRecord) -> WorldContainerRecord:
    """Cascade revocations when a non-owner loses share or delegated actions."""
    grants = list(record.access_grants)
    owner = record.owner_subject
    changed = True
    while changed:
        changed = False
        by_subject = {grant.subject: grant for grant in grants}
        next_grants: list[WorldAccessGrant] = []
        for grant in grants:
            if grant.granted_by_subject == owner:
                next_grants.append(grant)
                continue
            grantor = by_subject.get(grant.granted_by_subject)
            if grantor is None or WorldPermission.SHARE not in grantor.permissions:
                changed = True
                continue
            allowable = set(grantor.permissions) & _DELEGABLE_WORLD_PERMISSIONS
            permissions = tuple(
                permission for permission in grant.permissions if permission in allowable
            )
            if not permissions:
                changed = True
                continue
            if permissions != grant.permissions:
                grant = grant.model_copy(update={"permissions": permissions})
                changed = True
            next_grants.append(grant)
        grants = next_grants
    if grants == record.access_grants:
        return record
    return record.model_copy(update={"access_grants": grants})


def grant_world_access(
    root: Path, world_id: str, *, actor_subject: str | None, subject: str,
    permissions: tuple[WorldPermission | str, ...] | list[WorldPermission | str],
) -> WorldContainerRecord:
    """Apply the one product grant policy to the latest locked World grants."""
    del root
    try:
        actor = _validate_subject(actor_subject)
        target = _validate_subject(subject)
        cleaned = _validate_world_id(world_id)
    except (ValueError, TypeError, AttributeError) as exc:
        raise WorldAccessDenied("World access denied") from exc
    if actor is None or target is None:
        raise WorldAccessDenied("World access denied")
    requested = _requested_permissions(permissions)
    def transform(record):
        require_world_permission(record, subject=actor, permission=WorldPermission.SHARE)
        if target == actor or target == record.owner_subject:
            raise WorldAccessDenied("World access denied")
        is_owner = actor == record.owner_subject
        existing = next((grant for grant in record.access_grants if grant.subject == target), None)
        if existing is not None and not is_owner and existing.granted_by_subject != actor:
            raise WorldAccessDenied("World access denied")
        if not is_owner:
            actor_grant = next(
                (grant for grant in record.access_grants if grant.subject == actor), None
            )
            allowed = (
                set(actor_grant.permissions) & _DELEGABLE_WORLD_PERMISSIONS
                if actor_grant is not None
                else set()
            )
            if not set(requested) <= allowed:
                raise WorldAccessDenied("World access denied")
        new_grant = WorldAccessGrant(
            subject=target,
            permissions=requested,
            granted_by_subject=actor,
        )
        grants = [grant for grant in record.access_grants if grant.subject != target]
        grants.append(new_grant)
        updated = record.model_copy(update={"access_grants": grants})
        updated = _prune_delegated_grants(updated)
        return updated.access_grants
    try:
        return catalog.update_world_grants(cleaned, transform).record
    except ApplicationStateError as exc:
        if exc.status_code == 404:
            raise WorldAccessDenied("World access denied") from exc
        raise _catalog_error(exc) from exc


def revoke_world_access(
    root: Path, world_id: str, *, actor_subject: str | None, subject: str,
) -> WorldContainerRecord:
    """Revoke and cascade using the same serialized access-policy boundary."""
    del root
    try:
        actor = _validate_subject(actor_subject)
        target = _validate_subject(subject)
        cleaned = _validate_world_id(world_id)
    except (ValueError, TypeError, AttributeError) as exc:
        raise WorldAccessDenied("World access denied") from exc
    if actor is None or target is None:
        raise WorldAccessDenied("World access denied")
    def transform(record):
        require_world_permission(record, subject=actor, permission=WorldPermission.SHARE)
        is_owner = actor == record.owner_subject
        existing = next((grant for grant in record.access_grants if grant.subject == target), None)
        if existing is None:
            return record.access_grants
        if not is_owner and existing.granted_by_subject != actor:
            raise WorldAccessDenied("World access denied")
        updated = record.model_copy(
            update={
                "access_grants": [
                    grant for grant in record.access_grants if grant.subject != target
                ]
            }
        )
        updated = _prune_delegated_grants(updated)
        return updated.access_grants
    try:
        return catalog.update_world_grants(cleaned, transform).record
    except ApplicationStateError as exc:
        if exc.status_code == 404:
            raise WorldAccessDenied("World access denied") from exc
        raise _catalog_error(exc) from exc
