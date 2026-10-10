"""Resolve a managed World binding before serving its native Graph projection."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

from apps.live_control_server import config
from apps.live_control_server.services.world_container_registry import (
    WorldContainerRecord,
    WorldContainerRegistryError,
    get_world_container,
    world_source_root_relpath,
)
from apps.live_control_server.services.world_graph_projection import (
    WorldGraphProjectionServiceError,
    project_world_graph,
)
from graph_memory.projection.world_projection import (
    WorldGraphProjection,
    WorldGraphProjectionRequest,
)


class ManagedWorldGraphProjectionRequest(BaseModel):
    """Request a current World-scope read by managed owner identity only."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        extra="forbid",
        populate_by_name=True,
        strict=True,
    )

    schema_: Literal["dmb_managed_world_graph_projection_request_v1"] = Field(
        alias="schema"
    )
    managed_world_id: str = Field(min_length=1, max_length=63)
    revision_pin: str | None = None
    query_text: str | None = None


class ManagedWorldGraphProjectionResponse(BaseModel):
    """Buddy binding provenance around an unchanged native projection."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        extra="forbid",
        populate_by_name=True,
    )

    schema_: Literal["dmb_managed_world_graph_projection_v1"] = Field(alias="schema")
    managed_world_id: str
    native_world_id: str
    binding_version: int = Field(gt=0)
    projection: WorldGraphProjection


@dataclass(frozen=True)
class VerifiedManagedWorldBinding:
    """Private source-root proof and active native publication/read identity."""

    managed_world_id: str
    native_world_id: str
    binding_version: int
    source_root_relpath: str


def _verified_managed_record(root: Path, managed_world_id: str) -> WorldContainerRecord:
    try:
        record = get_world_container(root, managed_world_id)
    except WorldContainerRegistryError as exc:
        code = (
            "managed_world_not_found"
            if exc.status_code == 404
            else "managed_world_unavailable"
        )
        raise WorldGraphProjectionServiceError(
            "Managed World could not be resolved.",
            code=code,
            status_code=exc.status_code,
        ) from None

    expected_source_root = world_source_root_relpath(record.world_id)
    if (
        record.source_root_relpath != expected_source_root
        or not (root / expected_source_root).is_dir()
    ):
        raise WorldGraphProjectionServiceError(
            "Managed World is not verified by its source root.",
            code="managed_world_unverified",
            status_code=409,
        )
    return record


def _active_binding(record: WorldContainerRecord) -> tuple[str, int]:
    binding = record.native_graph_binding
    if binding is None:
        raise WorldGraphProjectionServiceError(
            "Managed World has no native Graph binding.",
            code="native_graph_binding_missing",
            status_code=409,
        )
    if binding.status != "active":
        raise WorldGraphProjectionServiceError(
            "Managed World native Graph binding is inactive.",
            code="native_graph_binding_inactive",
            status_code=409,
        )

    native_world_id = binding.native_world_id.strip()
    if not native_world_id or binding.binding_version <= 0:
        raise WorldGraphProjectionServiceError(
            "Managed World native Graph binding is invalid.",
            code="native_graph_binding_invalid",
            status_code=409,
        )
    return native_world_id, binding.binding_version


def resolve_managed_world_binding(
    managed_world_id: str, *, root: Path | None = None
) -> VerifiedManagedWorldBinding:
    """Resolve the existing verified managed World and active native binding."""

    try:
        registry_root = root if root is not None else config.managed_world_data_root()
    except config.ManagedWorldDataRootError as exc:
        raise WorldGraphProjectionServiceError(
            "Managed World storage is unavailable.",
            code="managed_world_unavailable", status_code=503,
        ) from exc
    record = _verified_managed_record(registry_root, managed_world_id)
    native_world_id, binding_version = _active_binding(record)
    return VerifiedManagedWorldBinding(
        managed_world_id=record.world_id,
        native_world_id=native_world_id,
        binding_version=binding_version,
        source_root_relpath=record.source_root_relpath,
    )


def project_managed_world_graph(
    request: ManagedWorldGraphProjectionRequest,
    *,
    root: Path | None = None,
    expected_binding: VerifiedManagedWorldBinding | None = None,
) -> ManagedWorldGraphProjectionResponse:
    """Read through a stable active Buddy binding, failing closed on change."""

    initial = resolve_managed_world_binding(request.managed_world_id, root=root)
    if expected_binding is not None and initial != expected_binding:
        raise WorldGraphProjectionServiceError(
            "Managed World native Graph binding changed before projection.",
            code="native_graph_binding_changed", status_code=409,
        )

    native_request = WorldGraphProjectionRequest.model_validate(
        {
            "schema": "dmb_world_graph_projection_request_v1",
            "worldId": initial.native_world_id,
            "campaignId": "",
            "focus": {"kind": "none", "sessionId": None},
            "admissibility": "gm",
            "revisionPin": request.revision_pin,
            "queryText": request.query_text,
            "scopeMode": "world",
        }
    )
    projection = project_world_graph(native_request)

    current = resolve_managed_world_binding(request.managed_world_id, root=root)
    if current != initial:
        raise WorldGraphProjectionServiceError(
            "Managed World native Graph binding changed during projection; retry the read.",
            code="native_graph_binding_changed",
            status_code=409,
        )

    return ManagedWorldGraphProjectionResponse(
        schema_="dmb_managed_world_graph_projection_v1",
        managed_world_id=initial.managed_world_id,
        native_world_id=initial.native_world_id,
        binding_version=initial.binding_version,
        projection=projection,
    )


__all__ = [
    "ManagedWorldGraphProjectionRequest",
    "ManagedWorldGraphProjectionResponse",
    "VerifiedManagedWorldBinding",
    "project_managed_world_graph",
    "resolve_managed_world_binding",
]
