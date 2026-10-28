"""File-backed managed World identity, ownership, and access registry."""

from __future__ import annotations

import re
import unicodedata
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from apps.live_control_server.services.registry_file_lock import (
    registry_mutation_lock,
    registry_token,
)
from src.live_play.live_store import load_json, write_json

DEFAULT_REGISTRY_REL = "out/registries/world_containers.json"
LEGACY_REGISTRY_SCHEMA = "dmb_world_container_registry_v1"
LEGACY_RECORD_SCHEMA = "dmb_world_container_record_v1"
V2_REGISTRY_SCHEMA = "dmb_world_container_registry_v2"
V2_RECORD_SCHEMA = "dmb_world_container_record_v2"
REGISTRY_SCHEMA = "dmb_world_container_registry_v3"
RECORD_SCHEMA = "dmb_world_container_record_v3"
PUBLIC_REGISTRY_SCHEMA = LEGACY_REGISTRY_SCHEMA
PUBLIC_RECORD_SCHEMA = LEGACY_RECORD_SCHEMA

# Must stay aligned with workspace_document_registry._SAFE_WORLD_ID_RE.
_SAFE_WORLD_ID_RE = re.compile(r"^[a-z][a-z0-9_-]{0,62}$")
_NON_SLUG_RE = re.compile(r"[^a-z0-9]+")


class WorldContainerRegistryError(ValueError):
    status_code: int = 404

    def __init__(self, message: str, *, status_code: int = 404) -> None:
        super().__init__(message)
        self.status_code = status_code


class WorldAccessDenied(ValueError):
    """Generic denial that does not reveal whether a World ID exists."""

    status_code = 404


class WorldPermission(StrEnum):
    """Independent capabilities for a World and its subordinate resources."""

    READ = "read"
    WRITE = "write"
    MANAGE = "manage"
    SHARE = "share"


_PERMISSION_ORDER = {
    WorldPermission.READ: 0,
    WorldPermission.WRITE: 1,
    WorldPermission.MANAGE: 2,
    WorldPermission.SHARE: 3,
}
_DELEGABLE_WORLD_PERMISSIONS = frozenset(
    {WorldPermission.READ, WorldPermission.WRITE}
)


def _validate_subject(subject: str | None) -> str | None:
    if subject is None:
        return None
    if (
        not isinstance(subject, str)
        or not subject
        or subject != subject.strip()
        or any(ord(character) < 0x21 for character in subject)
    ):
        raise ValueError("World access subjects must be exact, non-empty identifiers")
    return subject


class WorldAccessGrant(BaseModel):
    """An explicit action grant; provenance bounds delegated sharing."""

    model_config = ConfigDict(extra="forbid")

    subject: str
    permissions: tuple[WorldPermission, ...]
    granted_by_subject: str

    @field_validator("subject", "granted_by_subject")
    @classmethod
    def _preserve_exact_subject(cls, value: str) -> str:
        return _validate_subject(value) or ""

    @field_validator("permissions")
    @classmethod
    def _require_unique_nonempty_permissions(
        cls, value: tuple[WorldPermission, ...]
    ) -> tuple[WorldPermission, ...]:
        if not value or len(value) != len(set(value)):
            raise ValueError("World access grants need unique, explicit permissions")
        return tuple(sorted(value, key=_PERMISSION_ORDER.__getitem__))


class NativeGraphBindingRecord(BaseModel):
    """Private Buddy-owned relationship to one verified native MIND Graph."""

    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["dmb_managed_world_native_graph_binding_v1"] = (
        "dmb_managed_world_native_graph_binding_v1"
    )
    provider: Literal["dungeonmind_v2"] = "dungeonmind_v2"
    native_world_id: str = Field(min_length=1, max_length=255)
    status: Literal["active", "inactive"]
    binding_version: int = Field(gt=0)
    validated_at: str = Field(min_length=1)
    validated_head_revision_id: str = Field(min_length=1)

    provisioning_id: str | None = Field(default=None, pattern=r"^provision:[0-9a-f]{32}$")
    initialization_revision_id: str | None = None

    @model_validator(mode="after")
    def _reviewed_provisioning_proof_is_complete(self):
        if (self.provisioning_id is None) != (self.initialization_revision_id is None):
            raise ValueError("reviewed native binding requires operation and genesis revision")
        if self.initialization_revision_id is not None and not self.initialization_revision_id.strip():
            raise ValueError("reviewed genesis revision must be nonblank")
        return self

    @field_validator("native_world_id")
    @classmethod
    def _trim_native_world_id(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned or any(ord(character) < 32 for character in cleaned):
            raise ValueError("native Graph identity values must be non-empty printable text")
        return cleaned

    @field_validator("validated_head_revision_id")
    @classmethod
    def _preserve_exact_head_revision_id(cls, value: str) -> str:
        if not value.strip() or any(ord(character) < 32 for character in value):
            raise ValueError("native Graph identity values must be non-empty printable text")
        return value


class NativeGraphProvisioningRecord(BaseModel):
    """Reserved native/source-space identity; no Graph or head exists by implication."""

    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["dmb_managed_world_native_graph_provisioning_v1"] = (
        "dmb_managed_world_native_graph_provisioning_v1"
    )
    provider: Literal["dungeonmind_v2"] = "dungeonmind_v2"
    native_world_id: str = Field(pattern=r"^world:[0-9a-f]{32}$")
    provisioning_id: str = Field(pattern=r"^provision:[0-9a-f]{32}$")
    status: Literal["provisioning"] = "provisioning"
    binding_version: Literal[1] = 1


class WorldContainerRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal[
        "dmb_world_container_record_v1",
        "dmb_world_container_record_v2",
        "dmb_world_container_record_v3",
    ] = RECORD_SCHEMA
    world_id: str
    name: str
    source_root_relpath: str
    created_at: str
    native_graph_binding: NativeGraphBindingRecord | NativeGraphProvisioningRecord | None = None
    owner_subject: str | None = None
    access_grants: list[WorldAccessGrant] = Field(default_factory=list)

    @field_validator("owner_subject")
    @classmethod
    def _preserve_exact_owner_subject(cls, value: str | None) -> str | None:
        return _validate_subject(value)

    @model_validator(mode="after")
    def _access_metadata_is_coherent(self) -> "WorldContainerRecord":
        if self.schema_version == LEGACY_RECORD_SCHEMA and self.native_graph_binding is not None:
            raise ValueError("legacy WorldContainerRecord cannot contain native Graph binding")
        grant_subjects = [grant.subject for grant in self.access_grants]
        if len(grant_subjects) != len(set(grant_subjects)):
            raise ValueError("a World may contain only one grant per subject")
        if self.owner_subject is None and self.access_grants:
            raise ValueError("an unowned World cannot contain access grants")
        if self.owner_subject is not None and self.owner_subject in grant_subjects:
            raise ValueError("the World owner is not stored as a share grant")
        return self


class WorldContainerRegistryDocument(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal[
        "dmb_world_container_registry_v1",
        "dmb_world_container_registry_v2",
        "dmb_world_container_registry_v3",
    ] = REGISTRY_SCHEMA
    records: list[WorldContainerRecord] = Field(default_factory=list)

    @model_validator(mode="after")
    def _claimed_native_graph_ids_are_unique(self) -> "WorldContainerRegistryDocument":
        claimed_native_ids = [
            record.native_graph_binding.native_world_id
            for record in self.records
            if record.native_graph_binding is not None
            and record.native_graph_binding.status in {"active", "provisioning"}
        ]
        if len(claimed_native_ids) != len(set(claimed_native_ids)):
            raise ValueError("a native identity may be reserved or active for only one managed World")
        operations = [
            record.native_graph_binding.provisioning_id
            for record in self.records
            if record.native_graph_binding is not None
            and record.native_graph_binding.provisioning_id is not None
        ]
        if len(operations) != len(set(operations)):
            raise ValueError("a provisioning operation belongs to only one managed World")
        return self


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


def _utc_now_iso() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def world_containers_path(root: Path) -> Path:
    return root / DEFAULT_REGISTRY_REL


def normalize_world_name_for_compare(name: str) -> str:
    """Trim + collapse whitespace + casefold for duplicate comparison only."""
    return " ".join(name.strip().split()).casefold()


def display_world_name(name: str) -> str:
    cleaned = " ".join(name.strip().split())
    if not cleaned:
        raise WorldContainerRegistryError("That world name is required.", status_code=422)
    return cleaned


def derive_world_id_from_name(name: str) -> str:
    """Server-owned safe world_id derived from the human name."""
    display = display_world_name(name)
    folded = unicodedata.normalize("NFKD", display).encode("ascii", "ignore").decode("ascii")
    slug = _NON_SLUG_RE.sub("-", folded.casefold()).strip("-")
    if not slug or not slug[0].isalpha():
        slug = f"world-{slug}".strip("-") if slug else "world"
        if not slug[0].isalpha():
            slug = f"w-{slug}"
    slug = slug[:63].strip("-")
    if not slug or not _SAFE_WORLD_ID_RE.fullmatch(slug):
        raise WorldContainerRegistryError(
            "Could not create the world.",
            status_code=422,
        )
    return slug


def world_source_root_relpath(world_id: str) -> str:
    return f"corpus/{world_id}-markdown"


def _validate_world_id(world_id: str) -> str:
    cleaned = world_id.strip()
    if not cleaned or not _SAFE_WORLD_ID_RE.fullmatch(cleaned):
        raise WorldContainerRegistryError(
            "world_id must match ^[a-z][a-z0-9_-]{0,62}$",
            status_code=422,
        )
    return cleaned


def _load_unlocked(root: Path) -> tuple[WorldContainerRegistryDocument, str]:
    path = world_containers_path(root)
    token = registry_token(path)
    if not path.is_file():
        return WorldContainerRegistryDocument(), token
    try:
        document = WorldContainerRegistryDocument.model_validate(load_json(path))
        if document.schema_version in {LEGACY_REGISTRY_SCHEMA, V2_REGISTRY_SCHEMA}:
            if document.schema_version == LEGACY_REGISTRY_SCHEMA and any(
                record.native_graph_binding is not None for record in document.records
            ):
                raise ValueError("v1 registry cannot contain native Graph bindings")
            expected_record_schema = (
                LEGACY_RECORD_SCHEMA
                if document.schema_version == LEGACY_REGISTRY_SCHEMA
                else V2_RECORD_SCHEMA
            )
            if any(record.schema_version != expected_record_schema for record in document.records):
                raise ValueError("registry contains a record with a mismatched schema")
            # Legacy records remain unowned. Reads normalize only in memory;
            # the original bytes are preserved until an authorized mutation.
            records = [
                record.model_copy(
                    update={
                        "schema_version": RECORD_SCHEMA,
                        "owner_subject": None,
                        "access_grants": [],
                    }
                )
                for record in document.records
            ]
            document = WorldContainerRegistryDocument(
                schema_version=REGISTRY_SCHEMA,
                records=records,
            )
        elif document.schema_version == REGISTRY_SCHEMA and any(
            record.schema_version != RECORD_SCHEMA for record in document.records
        ):
            raise ValueError("v3 registry contains a non-v3 WorldContainerRecord")
    except (TypeError, ValueError) as exc:
        raise WorldContainerRegistryError(
            "malformed world container registry",
            status_code=500,
        ) from exc
    return document, token


def _save_cas(
    root: Path,
    document: WorldContainerRegistryDocument,
    *,
    expected_token: str,
) -> Path:
    path = world_containers_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    current = registry_token(path)
    if current != expected_token:
        raise WorldContainerRegistryError(
            "world container registry changed concurrently",
            status_code=409,
        )
    try:
        write_json(path, document.model_dump(mode="json"))
    except (OSError, TypeError, ValueError) as exc:
        raise WorldContainerRegistryError(
            f"failed to persist world container registry: {exc}",
            status_code=500,
        ) from exc
    return path


def list_world_containers(root: Path) -> list[WorldContainerRecord]:
    records = list(_load_unlocked(root)[0].records)
    records.sort(key=lambda row: (row.name.casefold(), row.world_id))
    return records


def get_world_container(root: Path, world_id: str) -> WorldContainerRecord:
    cleaned = _validate_world_id(world_id)
    document, _token = _load_unlocked(root)
    record = next((r for r in document.records if r.world_id == cleaned), None)
    if record is None:
        raise WorldContainerRegistryError(
            f"world container not found: {cleaned}",
            status_code=404,
        )
    return record


def find_world_container_by_normalized_name(
    root: Path, name: str
) -> WorldContainerRecord | None:
    needle = normalize_world_name_for_compare(name)
    if not needle:
        return None
    for record in list_world_containers(root):
        if normalize_world_name_for_compare(record.name) == needle:
            return record
    return None


def _best_effort_remove_empty_root(path: Path) -> None:
    try:
        if path.is_dir() and not any(path.iterdir()):
            path.rmdir()
    except OSError:
        return


def _world_id_for_owner(
    records: list[WorldContainerRecord], *, base_world_id: str, owner_subject: str | None,
    compare_name: str,
) -> str:
    """Resolve a free identity without conflating equal names owned by others."""
    for existing in records:
        same_name = normalize_world_name_for_compare(existing.name) == compare_name
        same_owner = existing.owner_subject == owner_subject
        if same_name and same_owner:
            return existing.world_id
    occupied = {record.world_id for record in records}
    if base_world_id not in occupied:
        return base_world_id
    base_record = next(record for record in records if record.world_id == base_world_id)
    if normalize_world_name_for_compare(base_record.name) != compare_name:
        raise WorldContainerRegistryError("That world already exists.", status_code=409)
    if owner_subject is None:
        raise WorldContainerRegistryError("That world already exists.", status_code=409)
    # A creator with the same display name gets an independent World. The
    # suffix is an identity disambiguator, never a claim that the Worlds match.
    for _attempt in range(8):
        suffix = uuid4().hex[:8]
        candidate = f"{base_world_id[:54].rstrip('-')}-{suffix}"
        if candidate not in occupied:
            return candidate
    raise WorldContainerRegistryError("Could not create the world.", status_code=500)


def create_world_container(
    root: Path, *, name: str, owner_subject: str | None = None
) -> WorldContainerRecord:
    """Create or reconcile one managed world container + source root.

    Idempotent per owner and normalized name (or per unowned local-mode
    record). Fails closed on identity/path collisions and never silently
    adopts unmanaged directories.
    """
    display = display_world_name(name)
    owner_subject = _validate_subject(owner_subject)
    base_world_id = derive_world_id_from_name(display)
    compare_name = normalize_world_name_for_compare(display)

    path = world_containers_path(root)
    created_root = False
    with registry_mutation_lock(path):
        document, token = _load_unlocked(root)

        world_id = _world_id_for_owner(
            document.records,
            base_world_id=base_world_id,
            owner_subject=owner_subject,
            compare_name=compare_name,
        )
        existing = next((record for record in document.records if record.world_id == world_id), None)
        if existing is not None:
            # Reconcile only the exact creator identity (or legacy local mode);
            # a matching display name never adopts an unowned or other user's World.
            if existing.owner_subject != owner_subject:
                raise WorldContainerRegistryError("That world already exists.", status_code=409)
            existing_root = root / existing.source_root_relpath
            if not existing_root.is_dir():
                raise WorldContainerRegistryError(
                    "Could not create the world.",
                    status_code=500,
                )
            return existing

        source_root_rel = world_source_root_relpath(world_id)
        source_root = root / source_root_rel

        if source_root.exists():
            raise WorldContainerRegistryError(
                "That world already exists.",
                status_code=409,
            )

        try:
            source_root.mkdir(parents=True, exist_ok=False)
            created_root = True
        except FileExistsError as exc:
            raise WorldContainerRegistryError(
                "That world already exists.",
                status_code=409,
            ) from exc
        except OSError as exc:
            raise WorldContainerRegistryError(
                "Could not create the world.",
                status_code=500,
            ) from exc

        record = WorldContainerRecord(
            world_id=world_id,
            name=display,
            source_root_relpath=source_root_rel,
            created_at=_utc_now_iso(),
            native_graph_binding=NativeGraphProvisioningRecord(
                native_world_id=f"world:{uuid4().hex}",
                provisioning_id=f"provision:{uuid4().hex}",
            ),
            owner_subject=owner_subject,
        )
        document.records.append(record)
        try:
            _save_cas(root, document, expected_token=token)
        except WorldContainerRegistryError:
            if created_root:
                _best_effort_remove_empty_root(source_root)
            raise
        except Exception:
            if created_root:
                _best_effort_remove_empty_root(source_root)
            raise

        return record


def _world_record_or_deny(
    document: WorldContainerRegistryDocument, world_id: str
) -> WorldContainerRecord:
    try:
        cleaned = _validate_world_id(world_id)
    except (TypeError, AttributeError, WorldContainerRegistryError) as exc:
        raise WorldAccessDenied("World access denied") from exc
    record = next((row for row in document.records if row.world_id == cleaned), None)
    if record is None:
        raise WorldAccessDenied("World access denied")
    return record


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
    root: Path,
    world_id: str,
    *,
    subject: str | None,
    permission: WorldPermission | str,
    resource_world_id: str | None = None,
) -> WorldContainerRecord:
    """Load and check access, collapsing missing and unauthorized Worlds."""
    try:
        document, _token = _load_unlocked(root)
        record = _world_record_or_deny(document, world_id)
    except WorldContainerRegistryError as exc:
        raise WorldAccessDenied("World access denied") from exc
    return require_world_permission(
        record,
        subject=subject,
        permission=permission,
        resource_world_id=resource_world_id,
    )


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


def _persist_access_record(
    root: Path,
    document: WorldContainerRegistryDocument,
    record: WorldContainerRecord,
    *,
    expected_token: str,
) -> WorldContainerRecord:
    record = record.model_copy(
        update={
            "access_grants": sorted(record.access_grants, key=lambda grant: grant.subject)
        }
    )
    updated_records = [
        record if row.world_id == record.world_id else row for row in document.records
    ]
    next_document = WorldContainerRegistryDocument(
        schema_version=REGISTRY_SCHEMA,
        records=updated_records,
    )
    _save_cas(root, next_document, expected_token=expected_token)
    return record


def grant_world_access(
    root: Path,
    world_id: str,
    *,
    actor_subject: str | None,
    subject: str,
    permissions: tuple[WorldPermission | str, ...] | list[WorldPermission | str],
) -> WorldContainerRecord:
    """Create or replace an explicit grant under the registry CAS lock.

    Owners may grant any independent actions. A delegated sharer may issue
    only read/write they hold, and may update only grants they created.
    """
    try:
        actor = _validate_subject(actor_subject)
        target = _validate_subject(subject)
    except ValueError as exc:
        raise WorldAccessDenied("World access denied") from exc
    if actor is None or target is None:
        raise WorldAccessDenied("World access denied")
    requested = _requested_permissions(permissions)
    path = world_containers_path(root)
    with registry_mutation_lock(path):
        document, token = _load_unlocked(root)
        record = _world_record_or_deny(document, world_id)
        try:
            require_world_permission(
                record, subject=actor, permission=WorldPermission.SHARE
            )
        except WorldAccessDenied:
            raise
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
        return _persist_access_record(root, document, updated, expected_token=token)


def revoke_world_access(
    root: Path,
    world_id: str,
    *,
    actor_subject: str | None,
    subject: str,
) -> WorldContainerRecord:
    """Revoke a grant by its owner or its grantor, cascading delegated rights."""
    try:
        actor = _validate_subject(actor_subject)
        target = _validate_subject(subject)
    except ValueError as exc:
        raise WorldAccessDenied("World access denied") from exc
    if actor is None or target is None:
        raise WorldAccessDenied("World access denied")
    path = world_containers_path(root)
    with registry_mutation_lock(path):
        document, token = _load_unlocked(root)
        record = _world_record_or_deny(document, world_id)
        require_world_permission(record, subject=actor, permission=WorldPermission.SHARE)
        is_owner = actor == record.owner_subject
        existing = next((grant for grant in record.access_grants if grant.subject == target), None)
        if existing is None:
            return record
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
        return _persist_access_record(root, document, updated, expected_token=token)
