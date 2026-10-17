"""Explicit creative Build Compose; targets are host/editor-owned, never model output."""
from hashlib import sha256

from pydantic import Field, model_validator

from application_state.build_proposal.types import BuildProposalReservation


class BuildWriteCapability(BuildProposalReservation):
    """Browser-captured target; no model chooses insertion authority."""
    instruction: str = ""
    draft_markdown: str = Field(max_length=80_000)

    @model_validator(mode="after")
    def validate_capability(self):
        encoded = self.draft_markdown.encode("utf-8", errors="strict")
        if self.instruction or self.origin is not None:
            raise ValueError("The model instruction and tool origin are parent-owned")
        if len(encoded) > 64 * 1024 or sha256(encoded).hexdigest() != self.basis.draft_sha256:
            raise ValueError("Captured draft differs from its digest")
        return self


class BuildDocumentProposalRequest(BuildProposalReservation):
    draft_markdown: str = Field(max_length=80_000)

    @model_validator(mode="after")
    def validate_draft(self):
        encoded = self.draft_markdown.encode("utf-8", errors="strict")
        if len(encoded) > 64 * 1024 or sha256(encoded).hexdigest() != self.basis.draft_sha256:
            raise ValueError("Build draft exceeds context allowance or differs from its captured digest")
        return self

    def reservation_only(self) -> BuildProposalReservation:
        return BuildProposalReservation.model_validate(self.model_dump(exclude={"draft_markdown"}))
