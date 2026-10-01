"""File-backed managed world-container registry (source-root ownership only)."""

from __future__ import annotations

import re
import unicodedata
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from apps.live_control_server.services.registry_file_lock import (
    registry_mutation_lock,
    registry_token,
)
from src.live_play.live_store import load_json, write_json

DEFAULT_REGISTRY_REL = "out/registries/world_containers.json"
REGISTRY_SCHEMA = "dmb_world_container_registry_v1"
RECORD_SCHEMA = "dmb_world_container_record_v1"
SPACE_BINDING_VERSION = 1

# Must stay aligned with workspace_document_registry._SAFE_WORLD_ID_RE.
_SAFE_WORLD_ID_RE = re.compile(r"^[a-z][a-z0-9_-]{0,62}$")
_NON_SLUG_RE = re.compile(r"[^a-z0-9]+")


class WorldContainerRegistryError(ValueError):
    status_code: int = 404

    def __init__(self, message: str, *, status_code: int = 404) -> None:
        super().__init__(message)
        self.status_code = status_code


class WorldContainerRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["dmb_world_container_record_v1"] = RECORD_SCHEMA
    world_id: str
    name: str
    source_root_relpath: str
    created_at: str
    # The binding fields have defaults so v1 records written before this slice
    # continue to load as explicitly unbound.
    space_binding_status: Literal["unbound", "pending", "active"] = "unbound"
    space_binding_version: int | None = None
    space_allocation_id: str | None = None
    space_id: str | None = None
    space_provisioning_receipt: dict[str, Any] | None = None

    @model_validator(mode="after")
    def _binding_state_is_coherent(self) -> "WorldContainerRecord":
        if self.space_binding_status == "unbound":
            if any(
                value is not None
                for value in (
                    self.space_binding_version,
                    self.space_allocation_id,
                    self.space_id,
                    self.space_provisioning_receipt,
                )
            ):
                raise ValueError("unbound World cannot contain KnowledgeSpace identity")
        elif self.space_binding_status == "pending":
            if (
                not self.space_allocation_id
                or self.space_binding_version is not None
                or self.space_id is not None
                or self.space_provisioning_receipt is not None
            ):
                raise ValueError("pending World binding is malformed")
        elif (
            not self.space_allocation_id
            or not self.space_id
            or self.space_binding_version != SPACE_BINDING_VERSION
            or self.space_provisioning_receipt is None
            or self.space_provisioning_receipt.get("allocation_id")
            != self.space_allocation_id
            or self.space_provisioning_receipt.get("space_id") != self.space_id
        ):
            raise ValueError("active World binding is malformed")
        return self

    @classmethod
    def from_storage(cls, payload: dict[str, Any]) -> "WorldContainerRecord":
        return cls.model_validate(payload)


class WorldContainerPublicRecord(BaseModel):
    """Redacted HTTP view; MIND identities and receipts stay server-side."""

    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["dmb_world_container_record_v1"] = RECORD_SCHEMA
    world_id: str
    name: str
    source_root_relpath: str
    created_at: str
    space_binding_status: Literal["unbound", "pending", "active"]
    space_binding_version: int | None = None

    @classmethod
    def from_record(cls, record: WorldContainerRecord) -> "WorldContainerPublicRecord":
        return cls(
            world_id=record.world_id,
            name=record.name,
            source_root_relpath=record.source_root_relpath,
            created_at=record.created_at,
            space_binding_status=record.space_binding_status,
            space_binding_version=record.space_binding_version,
        )


class WorldContainerRegistryDocument(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["dmb_world_container_registry_v1"] = REGISTRY_SCHEMA
    records: list[WorldContainerRecord] = Field(default_factory=list)

    @model_validator(mode="after")
    def _binding_identities_are_unique(self) -> "WorldContainerRegistryDocument":
        bound_space_ids = [
            record.space_id
            for record in self.records
            if record.space_binding_status == "active"
        ]
        allocation_ids = [
            record.space_allocation_id
            for record in self.records
            if record.space_allocation_id is not None
        ]
        if len(bound_space_ids) != len(set(bound_space_ids)):
            raise ValueError("KnowledgeSpace may be bound to only one World")
        if len(allocation_ids) != len(set(allocation_ids)):
            raise ValueError("allocation identity may be bound to only one World")
        return self


class WorldContainersListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["dmb_world_container_registry_v1"] = REGISTRY_SCHEMA
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
        raw = load_json(path)
        if not isinstance(raw, dict):
            raise ValueError("registry document must be an object")
        records = raw.get("records")
        if not isinstance(records, list):
            raise ValueError("registry records must be a list")
        # Validate each record independently so legacy v1 JSON receives the
        # unbound defaults without relaxing top-level or record validation.
        document = WorldContainerRegistryDocument(
            schema_version=raw.get("schema_version"),
            records=[WorldContainerRecord.from_storage(row) for row in records],
        )
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


def replace_world_container_record(
    root: Path,
    updated: WorldContainerRecord,
    *,
    expected_token: str,
) -> None:
    """Persist one already-locked record transition using the registry CAS."""
    document, _token = _load_unlocked(root)
    records = list(document.records)
    for index, record in enumerate(records):
        if record.world_id == updated.world_id:
            records[index] = updated
            break
    else:
        raise WorldContainerRegistryError(
            f"world container not found: {updated.world_id}", status_code=404
        )
    _save_cas(
        root,
        document.model_copy(update={"records": records}),
        expected_token=expected_token,
    )
