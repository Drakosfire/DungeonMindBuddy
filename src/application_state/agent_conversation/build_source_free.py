"""Build-only observations before source verification; never evidence authority.

These host records grant no content access, verified revision, completeness, or
citation capability. Runtime registration belongs to the matching new receipt.
"""
from __future__ import annotations

from typing import Literal

from pydantic import Field, model_validator

from .native_statement_input import Strict


class BuildSourceBindingObservedV1(Strict):
    managed_world_id: str = Field(min_length=1, strict=True)
    native_world_id: str = Field(min_length=1, strict=True)
    binding_version: int = Field(gt=0, strict=True)
    provisioning_id: str | None = Field(default=None, min_length=1, strict=True)


class BuildSourceObservationV1(Strict):
    """Requested identity and observed pointer, with no source-read assertion."""

    schema_: Literal["dmb_build_source_observation_v1"] = Field(
        default="dmb_build_source_observation_v1", alias="schema")
    managed_world_id: str = Field(min_length=1, strict=True)
    binding: BuildSourceBindingObservedV1 | None
    requested_revision_id: str | None = Field(min_length=1, strict=True)
    observed_head_revision_id: str | None = Field(min_length=1, strict=True)

    @model_validator(mode="after")
    def observed_scope(self):
        if self.binding is None:
            if self.observed_head_revision_id is not None:
                raise ValueError("A head observation requires its observed World binding")
        elif self.binding.managed_world_id != self.managed_world_id:
            raise ValueError("Observed source binding belongs to another managed World")
        return self

    @property
    def requested_or_observed_revision(self) -> str | None:
        """An identity to verify later, never proof that a revision exists."""
        return self.requested_revision_id or self.observed_head_revision_id



def validate_pending_source_settlement(receipt, settlement):
    """Join stored identities, without granting access or admitting an event.

    Current principal/request/pointer and one-way prefix checks remain with the
    transactional APP owner. This function never prepares or reopens a source.
    """
    from .native_context import BuildPendingContextReceiptV1
    from .native_execution import NativeBuildSourceSettledV1

    if type(receipt) is not BuildPendingContextReceiptV1 or type(settlement) is not NativeBuildSourceSettledV1:
        raise ValueError("Source settlement requires the distinct pending Build codec")
    # Do not trust model_copy/model_construct values to have run validators.
    BuildPendingContextReceiptV1.model_validate_json(receipt.model_dump_json(by_alias=True))
    NativeBuildSourceSettledV1.model_validate_json(settlement.model_dump_json(by_alias=True))
    if settlement.pending_context_receipt_sha256 != receipt.context_receipt_sha256:
        raise ValueError("Source settlement differs from its pending receipt")
    observed, source = receipt.source_observation, settlement.source_authority
    binding = observed.binding
    revision = observed.requested_or_observed_revision
    if binding is None or revision is None:
        raise ValueError("Unobserved source scope cannot be replaced during settlement")
    if any(getattr(source, key) != getattr(binding, key) for key in (
            "managed_world_id", "native_world_id", "binding_version", "provisioning_id")):
        raise ValueError("Source settlement differs from the observed binding")
    if source.revision_id != revision:
        raise ValueError("Source settlement differs from the requested or observed revision")
