"""Read selectors, never client-supplied Graph authority or publication grants."""

from typing import Annotated, Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator

Text = Annotated[str, Field(min_length=1, pattern=r"\S")]


class Closed(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class InspectionScope(Closed):
    managed_world_id: Text
    scope_mode: Literal["world", "campaign"] = "world"
    campaign_id: Text | None = None

    @model_validator(mode="after")
    def explicit_scope(self):
        if (self.scope_mode == "campaign") != (self.campaign_id is not None):
            raise ValueError(
                "campaign scope requires its exact campaign; World scope has none"
            )
        return self


class InspectionPin(InspectionScope):
    native_world_id: Text
    binding_version: int = Field(gt=0)
    revision_id: Text


class EntitySelection(Closed):
    kind: Literal["entity"]
    entity_id: Text


class SourceSelection(Closed):
    kind: Literal["source"]
    assertion_id: Text
    evidence_ref_id: Text


class ChronologySelection(Closed):
    kind: Literal["chronology"]


class NeighborhoodSelection(Closed):
    kind: Literal["neighborhood"]
    seed_node_ids: list[Text] = Field(min_length=1, max_length=8)
    max_depth: Literal[1, 2] = 1
    max_nodes: int = Field(default=8, ge=1, le=12)
    max_relationships: int = Field(default=16, ge=1, le=24)


class InspectionRead(Closed):
    scope: InspectionPin
    selection: Annotated[EntitySelection | SourceSelection | ChronologySelection | NeighborhoodSelection, Field(discriminator="kind")]
