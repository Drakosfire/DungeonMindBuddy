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
