from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from src.ingestion.entity_extractor import ExtractedEntity


class EventRecord(BaseModel):
    event_name: str | None = None
    event_class: Literal[
        "conversation",
        "travel",
        "combat",
        "discovery",
        "transfer",
        "ritual",
        "betrayal",
        "disaster",
        "investigation",
        "social_conflict",
    ]
    participants: list[str] = Field(default_factory=list)
    referenced_slugs: list[str] = Field(default_factory=list)
    location: str | None = None
    outcomes: list[str] = Field(default_factory=list)
    time_scope: Literal["scene", "session", "historical_reference"]
    certainty: Literal["observed", "inferred", "uncertain"]


class ClaimRecord(BaseModel):
    subject: str
    predicate: str
    object: str
    claim_type: Literal["fact", "suspicion", "rumor", "intent", "memory"]
    speaker_or_source: str
    certainty: Literal["high", "medium", "low"]


class RecapExtractionResult(BaseModel):
    entities: list[ExtractedEntity] = Field(default_factory=list)
    event_records: list[EventRecord] = Field(default_factory=list)
    claims: list[ClaimRecord] = Field(default_factory=list)
