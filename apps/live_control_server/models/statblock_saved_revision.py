"""Explicit manual Save intent; no inherited acceptance or encounter mutation."""
from uuid import UUID
from pydantic import BaseModel,ConfigDict,Field
from apps.live_control_server.integrations.dungeonmind_statblocks.generated import StatblockDefinitionV1Input
from apps.live_control_server.integrations.dungeonmind_statblocks.mechanics_locator import MechanicsLocatorV1


class SaveMechanicsRevisionRequest(BaseModel):
    model_config=ConfigDict(extra='forbid')
    operation_id: UUID
    world_id: str=Field(pattern=r'^[a-z][a-z0-9_-]{0,62}$')
    base: MechanicsLocatorV1
    definition: StatblockDefinitionV1Input
    change_summary: str=Field(min_length=1)
