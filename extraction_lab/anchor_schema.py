from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

from src.contracts.entity_taxonomy import EntityClass


class EntityGoldAnchor(BaseModel):
    anchor_id: str
    intent: str
    expected_class: EntityClass
    expected_names: list[str] = Field(default_factory=list)
    source_text_marker: str | None = None
    source_file: str | None = None
    resolution_strategy: Literal["name_in_store"] = "name_in_store"
    min_fact_count: int | None = Field(default=None, ge=0)
    surface: str = "core_extraction"


class FactGoldAnchor(BaseModel):
    anchor_id: str
    intent: str
    subject_anchor: str
    expected_attribute: str
    match_keywords: list[str] = Field(default_factory=list, min_length=1)
    alternative_attributes: list[str] = Field(default_factory=list)
    source_text_marker: str | None = None
    source_file: str | None = None
    surface: str = "core_extraction"


def load_entity_anchors(path: Path) -> list[EntityGoldAnchor]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return [EntityGoldAnchor.model_validate(row) for row in payload]


def load_fact_anchors(path: Path) -> list[FactGoldAnchor]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return [FactGoldAnchor.model_validate(row) for row in payload]
