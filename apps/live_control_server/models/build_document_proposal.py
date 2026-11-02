"""Explicit creative Build Compose; targets are host/editor-owned, never model output."""
from hashlib import sha256

from pydantic import model_validator

from application_state.build_proposal.types import (
    BuildProposalReservation, BuildWriteCapability as BuildWriteCapability,
)


class BuildDocumentProposalRequest(BuildProposalReservation):
    draft_markdown: str

    @model_validator(mode="after")
    def validate_draft(self):
        encoded = self.draft_markdown.encode("utf-8", errors="strict")
        if sha256(encoded).hexdigest() != self.basis.draft_sha256:
            raise ValueError("Build draft differs from its captured digest")
        return self

    def reservation_only(self) -> BuildProposalReservation:
        return BuildProposalReservation.model_validate(self.model_dump(exclude={"draft_markdown"}))
