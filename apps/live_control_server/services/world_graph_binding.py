"""Compare-and-swap binding from a managed World to an existing MIND Graph."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from apps.live_control_server.services.registry_file_lock import registry_mutation_lock
from apps.live_control_server.services.world_container_registry import (
    NativeGraphBindingRecord,
    WorldContainerRecord,
    WorldContainerRegistryDocument,
    _load_unlocked,
    _save_cas,
    _validate_world_id,
    world_containers_path,
    world_source_root_relpath,
)


class WorldGraphBindingError(ValueError):
    """Fail-closed binding failure suitable for an HTTP response."""

    def __init__(self, message: str, *, status_code: int = 409) -> None:
        super().__init__(message)
        self.status_code = status_code


class BindNativeGraphRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    native_world_id: str = Field(min_length=1, max_length=255)
    expected_binding_version: int = Field(ge=0, strict=True)

    @field_validator("native_world_id")
    @classmethod
    def _trim_native_id(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned or any(ord(character) < 32 for character in cleaned):
            raise ValueError("native_world_id must be non-empty printable text")
        return cleaned


class DeactivateNativeGraphBindingRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    expected_binding_version: int = Field(ge=0, strict=True)


NativeGraphAuthorityValidator = Callable[[str], Any]


def _managed_record(
    document: WorldContainerRegistryDocument,
    root: Path,
    world_id: str,
) -> WorldContainerRecord:
    record = next((row for row in document.records if row.world_id == world_id), None)
    if record is None:
        raise WorldGraphBindingError("Managed World was not found.", status_code=404)
    if (
        record.source_root_relpath != world_source_root_relpath(record.world_id)
        or not (root / record.source_root_relpath).is_dir()
    ):
        raise WorldGraphBindingError(
            "Managed World is not verified by its source root.", status_code=409
        )
    return record


def _load_binding_snapshot(
    root: Path,
    world_id: str,
) -> tuple[WorldContainerRecord, str]:
    path = world_containers_path(root)
    with registry_mutation_lock(path):
        document, token = _load_unlocked(root)
        record = _managed_record(document, root, world_id)
        return record, token


def _binding_version(record: WorldContainerRecord) -> int:
    binding = record.native_graph_binding
    return binding.binding_version if binding is not None else 0


def _require_expected_version(record: WorldContainerRecord, expected: int) -> None:
    if _binding_version(record) != expected:
        raise WorldGraphBindingError(
            "Native Graph binding version changed; reload the managed World.",
            status_code=409,
        )


def _validate_with_mind(native_world_id: str) -> Any:
    """Open read-only MIND services through the existing authority adapter."""
    try:
        from apps.live_control_server.integrations.dungeonmind.world_graph_reads import (
            direct_services_from_config,
        )

        return direct_services_from_config(native_world_id)
    except Exception as exc:
        status_code = getattr(exc, "status_code", 503)
        if not isinstance(status_code, int) or not 400 <= status_code <= 599:
            status_code = 503
        raise WorldGraphBindingError(
            "Native Graph authority could not be verified.",
            status_code=status_code,
        ) from exc


def _validated_head_and_revision(
    services: Any,
    requested_world_id: str,
) -> str:
    authority = getattr(services, "binding", None)
    actual_world_id = getattr(authority, "world_id", None)
    head_revision_id = getattr(authority, "dungeonmind_head_revision_id", None)
    if (
        not isinstance(actual_world_id, str)
        or actual_world_id != requested_world_id
        or not isinstance(head_revision_id, str)
        or not head_revision_id.strip()
    ):
        raise WorldGraphBindingError(
            "Native Graph authority returned a mismatched identity or no current head.",
            status_code=502,
        )

    graph_repository = getattr(getattr(services, "bundle", None), "world_graph", None)
    get_revision = getattr(graph_repository, "get_revision", None)
    if not callable(get_revision):
        raise WorldGraphBindingError(
            "Native Graph repository cannot verify the current head revision.",
            status_code=503,
        )
    try:
        stored = get_revision(requested_world_id, head_revision_id)
    except Exception as exc:
        raise WorldGraphBindingError(
            "Native Graph head revision could not be read.",
            status_code=503,
        ) from exc
    if stored is None:
        raise WorldGraphBindingError(
            "Native Graph head revision is unavailable.",
            status_code=502,
        )
    revision = getattr(stored, "revision", None)
    stored_world_id = getattr(revision, "world_id", None)
    stored_revision_id = getattr(revision, "revision_id", None)
    if stored_world_id != requested_world_id or stored_revision_id != head_revision_id:
        raise WorldGraphBindingError(
            "Native Graph head revision returned a mismatched identity.",
            status_code=502,
        )
    return head_revision_id


def _check_native_graph_claim_is_unique(
    document: WorldContainerRegistryDocument,
    *,
    managed_world_id: str,
    native_world_id: str,
) -> None:
    if any(
        record.world_id != managed_world_id
        and record.native_graph_binding is not None
        and record.native_graph_binding.status == "active"
        and record.native_graph_binding.native_world_id == native_world_id
        for record in document.records
    ):
        raise WorldGraphBindingError(
            "That native Graph is already actively bound to another managed World.",
            status_code=409,
        )


def bind_native_graph(
    root: Path,
    managed_world_id: str,
    *,
    native_world_id: str,
    expected_binding_version: int,
    authority_validator: NativeGraphAuthorityValidator | None = None,
) -> WorldContainerRecord:
    """Validate MIND unlocked, then persist an exact-token/version CAS."""
    cleaned_managed_id = _validate_world_id(managed_world_id)
    cleaned_native_id = BindNativeGraphRequest(
        native_world_id=native_world_id,
        expected_binding_version=expected_binding_version,
    ).native_world_id
    if isinstance(expected_binding_version, bool) or expected_binding_version < 0:
        raise WorldGraphBindingError("Expected binding version must be non-negative.", status_code=422)

    initial, expected_token = _load_binding_snapshot(root, cleaned_managed_id)
    _require_expected_version(initial, expected_binding_version)
    if initial.native_graph_binding is not None and initial.native_graph_binding.status == "active":
        if initial.native_graph_binding.native_world_id == cleaned_native_id:
            return initial
        raise WorldGraphBindingError(
            "Deactivate the current native Graph binding before rebinding.",
            status_code=409,
        )

    # MIND calls and database work must never hold the Buddy registry lock.
    validator = authority_validator or _validate_with_mind
    services = validator(cleaned_native_id)
    validated_head_revision_id = _validated_head_and_revision(services, cleaned_native_id)

    path = world_containers_path(root)
    with registry_mutation_lock(path):
        document, current_token = _load_unlocked(root)
        if current_token != expected_token:
            raise WorldGraphBindingError(
                "Managed World registry changed during native Graph validation.",
                status_code=409,
            )
        current = _managed_record(document, root, cleaned_managed_id)
        _require_expected_version(current, expected_binding_version)
        if current.native_graph_binding is not None and current.native_graph_binding.status == "active":
            raise WorldGraphBindingError(
                "Managed World binding changed during native Graph validation.",
                status_code=409,
            )
        _check_native_graph_claim_is_unique(
            document,
            managed_world_id=cleaned_managed_id,
            native_world_id=cleaned_native_id,
        )

        binding = NativeGraphBindingRecord(
            native_world_id=cleaned_native_id,
            status="active",
            binding_version=expected_binding_version + 1,
            validated_at=_utc_now_iso(),
            validated_head_revision_id=validated_head_revision_id,
        )
        updated = current.model_copy(
            update={"native_graph_binding": binding, "schema_version": "dmb_world_container_record_v2"}
        )
        updated_records = [
            updated if record.world_id == cleaned_managed_id else record
            for record in document.records
        ]
        next_document = WorldContainerRegistryDocument(
            schema_version="dmb_world_container_registry_v2",
            records=updated_records,
        )
        _save_cas(root, next_document, expected_token=expected_token)
        return updated


def deactivate_native_graph_binding(
    root: Path,
    managed_world_id: str,
    *,
    expected_binding_version: int,
) -> WorldContainerRecord:
    """Deactivate locally under the registry lock; MIND availability is irrelevant."""
    cleaned_managed_id = _validate_world_id(managed_world_id)
    if isinstance(expected_binding_version, bool) or expected_binding_version < 0:
        raise WorldGraphBindingError("Expected binding version must be non-negative.", status_code=422)

    path = world_containers_path(root)
    with registry_mutation_lock(path):
        document, token = _load_unlocked(root)
        current = _managed_record(document, root, cleaned_managed_id)
        _require_expected_version(current, expected_binding_version)
        binding = current.native_graph_binding
        if binding is None:
            raise WorldGraphBindingError(
                "Managed World has no native Graph binding to deactivate.",
                status_code=409,
            )
        if binding.status == "inactive":
            return current

        inactive_binding = binding.model_copy(
            update={"status": "inactive", "binding_version": binding.binding_version + 1}
        )
        updated = current.model_copy(update={"native_graph_binding": inactive_binding})
        next_document = WorldContainerRegistryDocument(
            schema_version="dmb_world_container_registry_v2",
            records=[
                updated if record.world_id == cleaned_managed_id else record
                for record in document.records
            ],
        )
        _save_cas(root, next_document, expected_token=token)
        return updated


def _utc_now_iso() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


__all__ = [
    "BindNativeGraphRequest",
    "DeactivateNativeGraphBindingRequest",
    "WorldGraphBindingError",
    "bind_native_graph",
    "deactivate_native_graph_binding",
]
