"""Exact Buddy World metadata, grants and native binding descriptors."""
from __future__ import annotations

from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

LEGACY_REGISTRY_SCHEMA = "dmb_world_container_registry_v1"
LEGACY_RECORD_SCHEMA = "dmb_world_container_record_v1"
V2_REGISTRY_SCHEMA = "dmb_world_container_registry_v2"
V2_RECORD_SCHEMA = "dmb_world_container_record_v2"
REGISTRY_SCHEMA = "dmb_world_container_registry_v3"
RECORD_SCHEMA = "dmb_world_container_record_v3"
PUBLIC_REGISTRY_SCHEMA = LEGACY_REGISTRY_SCHEMA
PUBLIC_RECORD_SCHEMA = LEGACY_RECORD_SCHEMA

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


