"""File-backed managed world-container registry (source-root ownership only)."""

from __future__ import annotations

import re
import unicodedata
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from apps.live_control_server.services.registry_file_lock import (
    registry_mutation_lock,
    registry_token,
)
from src.live_play.live_store import load_json, write_json

DEFAULT_REGISTRY_REL = "out/registries/world_containers.json"
LEGACY_REGISTRY_SCHEMA = "dmb_world_container_registry_v1"
LEGACY_RECORD_SCHEMA = "dmb_world_container_record_v1"
REGISTRY_SCHEMA = "dmb_world_container_registry_v2"
RECORD_SCHEMA = "dmb_world_container_record_v2"
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


class WorldContainerRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["dmb_world_container_record_v1", "dmb_world_container_record_v2"] = RECORD_SCHEMA
    world_id: str
    name: str
    source_root_relpath: str
    created_at: str
    native_graph_binding: NativeGraphBindingRecord | None = None

    @model_validator(mode="after")
    def _legacy_record_cannot_claim_native_binding(self) -> "WorldContainerRecord":
        if self.schema_version == LEGACY_RECORD_SCHEMA and self.native_graph_binding is not None:
            raise ValueError("legacy WorldContainerRecord cannot contain native Graph binding")
        return self


class WorldContainerRegistryDocument(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["dmb_world_container_registry_v1", "dmb_world_container_registry_v2"] = REGISTRY_SCHEMA
    records: list[WorldContainerRecord] = Field(default_factory=list)

    @model_validator(mode="after")
    def _active_native_graph_ids_are_unique(self) -> "WorldContainerRegistryDocument":
        active_native_ids = [
            record.native_graph_binding.native_world_id
            for record in self.records
            if record.native_graph_binding is not None
            and record.native_graph_binding.status == "active"
        ]
        if len(active_native_ids) != len(set(active_native_ids)):
            raise ValueError("a native Graph may be actively bound to only one managed World")
        return self


class NativeGraphBindingPublicStatus(BaseModel):
    """Only the operational state of a binding is exposed to the local UI."""

    model_config = ConfigDict(extra="forbid")

    status: Literal["unbound", "active", "inactive"]
    binding_version: int = Field(ge=0)


class WorldContainerPublicRecord(BaseModel):
    """Stable HTTP view; native IDs, heads and authority receipts stay private."""

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
        if document.schema_version == LEGACY_REGISTRY_SCHEMA:
            if any(record.native_graph_binding is not None for record in document.records):
                raise ValueError("v1 registry cannot contain native Graph bindings")
            # Read-only compatibility: v1 remains on disk until an authorized
            # mutation saves the normalized v2 document through _save_cas.
            records = [
                record.model_copy(
                    update={
                        "schema_version": RECORD_SCHEMA,
                        "native_graph_binding": None,
                    }
                )
                for record in document.records
            ]
            document = WorldContainerRegistryDocument(
                schema_version=REGISTRY_SCHEMA,
                records=records,
            )
        elif any(record.schema_version != RECORD_SCHEMA for record in document.records):
            raise ValueError("v2 registry contains a non-v2 WorldContainerRecord")
    except (TypeError, ValueError) as exc:
        raise WorldContainerRegistryError(
            f"malformed world container registry: {exc}",
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


def create_world_container(root: Path, *, name: str) -> WorldContainerRecord:
    """Create or reconcile one managed world container + source root.

    Idempotent for the same normalized name. Fails closed on identity/path
    collisions and never silently adopts unmanaged directories.
    """
    display = display_world_name(name)
    world_id = derive_world_id_from_name(display)
    source_root_rel = world_source_root_relpath(world_id)
    source_root = root / source_root_rel
    compare_name = normalize_world_name_for_compare(display)

    path = world_containers_path(root)
    created_root = False
    with registry_mutation_lock(path):
        document, token = _load_unlocked(root)

        for existing in document.records:
            if normalize_world_name_for_compare(existing.name) == compare_name:
                # Reconcile: registry record is authority; require root present.
                existing_root = root / existing.source_root_relpath
                if not existing_root.is_dir():
                    raise WorldContainerRegistryError(
                        "Could not create the world.",
                        status_code=500,
                    )
                return existing
            if existing.world_id == world_id:
                raise WorldContainerRegistryError(
                    "That world already exists.",
                    status_code=409,
                )

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
