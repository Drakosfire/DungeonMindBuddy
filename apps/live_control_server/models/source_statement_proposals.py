"""Explicit admitted-source operation and full human-reviewed selection."""
from uuid import UUID
from pydantic import Field
from apps.live_control_server.models.source_statements import Strict, StatementSelection


class ProposalRequest(Strict):
    operation_id: UUID = Field(strict=False)
    managed_world_id: str = Field(min_length=1)
    campaign_id: str = Field(min_length=1)
    read_revision_id: str = Field(min_length=1)
    source_admission_id: str = Field(min_length=1)
    evidence_ref_id: str = Field(min_length=1)
    source_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


class ProposalReview(Strict):
    decision_id: UUID = Field(strict=False)
    expected_revision: int = Field(ge=1)
    proposal_id: str = Field(min_length=1)
    selection: StatementSelection
