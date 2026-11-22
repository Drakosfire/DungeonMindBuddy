"""Exact saved Build image editor capture retained by native turn admission."""

from uuid import UUID

from pydantic import ConfigDict, Field, model_validator

from application_state.build_proposal.types import BuildProposalBasis, StrictModel
from application_state.content.page_presentation import Identifier
from application_state.content.types import sha256_utf8


class BuildImageMoveCapture(StrictModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    basis: BuildProposalBasis
    conversation_id: UUID
    expected_pointer_revision: int = Field(strict=True, ge=1)
    editor_json: str = Field(min_length=1, max_length=1_000_000)
    author_selected_block_id: Identifier | None = None

    @model_validator(mode="after")
    def exact_editor(self):
        if (
            self.basis.visibility != "internal"
            or self.basis.content_sha256 != self.basis.draft_sha256
            or sha256_utf8(self.editor_json) != self.basis.editor_sha256
        ):
            raise ValueError("Image movement requires the exact saved internal Page capture")
        return self
