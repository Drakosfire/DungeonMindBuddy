"""Closed references to author-reviewed actions; APP owns their resolution."""
from hashlib import sha256
import json
from typing import Literal
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field


class ReviewedStepReference(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    conversation_id: UUID
    source_turn_id: UUID
    command_id: UUID


class ReviewedStepBinding(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    reference: ReviewedStepReference
    step_id: UUID
    kind: Literal["discuss", "prepare_insertion"]
    source_answer_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    dispatch_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")

    @property
    def operation(self):
        return "answer_from_sources" if self.kind == "discuss" else "propose_build_insertion"


def digest(value):
    return sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
