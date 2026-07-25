"""Narrow DungeonBuddy routes for DungeonMind statblock v1 integration readiness."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from apps.live_control_server.integrations.dungeonmind_statblocks.readiness import (
    evaluate_statblock_integration_readiness,
)

router = APIRouter(prefix="/api/live/statblocks/v1", tags=["statblock-integration"])


@router.get("/readiness")
def get_statblock_integration_readiness() -> dict[str, Any]:
    readiness = evaluate_statblock_integration_readiness()
    return readiness.model_dump(mode="json", by_alias=True)
