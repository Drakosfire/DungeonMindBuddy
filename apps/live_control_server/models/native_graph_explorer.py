"""Closed request shapes for the managed native graph explorer."""

from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


ManagedWorldId = Annotated[
    str, Field(min_length=1, max_length=63, pattern=r"^[a-z][a-z0-9_-]{0,62}$")
]
NativeWorldId = Annotated[str, Field(min_length=1, max_length=256, pattern=r"^\S+$")]
RevisionId = Annotated[str, Field(min_length=1, max_length=256, pattern=r"^\S+$")]
OperationId = Annotated[
    str,
    Field(
        min_length=36,
        max_length=36,
        pattern=r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    ),
]


class Closed(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class NativeGraphExplorerGraphRequest(Closed):
    managed_world_id: ManagedWorldId


class NativeGraphExplorerCreateRequest(Closed):
    managed_world_id: ManagedWorldId
    native_world_id: NativeWorldId
    binding_version: int = Field(ge=1, strict=True)
    expected_revision_id: RevisionId
    operation_id: OperationId
    kind: Literal["create_object"]
    name: Annotated[str, Field(min_length=1, max_length=256)]
    object_kind: Literal["person", "location"]


class NativeGraphExplorerConnectRequest(Closed):
    managed_world_id: ManagedWorldId
    native_world_id: NativeWorldId
    binding_version: int = Field(ge=1, strict=True)
    expected_revision_id: RevisionId
    operation_id: OperationId
    kind: Literal["connect"]
    source_id: NativeWorldId
    target_id: NativeWorldId
    predicate: Annotated[str, Field(min_length=1, max_length=256)]


NativeGraphExplorerPrepareRequest = Annotated[
    NativeGraphExplorerCreateRequest | NativeGraphExplorerConnectRequest,
    Field(discriminator="kind"),
]


class NativeGraphExplorerOperationRequest(Closed):
    managed_world_id: ManagedWorldId
    operation_id: OperationId


def canonical_operation_id(value: str) -> str:
    try:
        parsed = str(UUID(value))
    except (ValueError, TypeError, AttributeError) as exc:
        raise ValueError("operation_id must be a canonical UUID") from exc
    if parsed != value:
        raise ValueError("operation_id must be a lowercase canonical UUID")
    return parsed
