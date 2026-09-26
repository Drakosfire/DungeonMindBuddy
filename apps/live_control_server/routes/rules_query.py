"""Read-only rules evidence packet route."""

from __future__ import annotations

import os
from pathlib import Path

from fastapi import APIRouter, Depends

from apps.live_control_server.integrations.dungeonmind.rules_query import DungeonMindRulesSearch
from apps.live_control_server.models.rules_query import RulesQueryPacket, RulesQueryRequest
from apps.live_control_server.services.rules_query import (
    RulesSearchPort, RulesSpaceBinding, load_binding, query_rules,
)


router = APIRouter(prefix="/api/live/rules", tags=["rules-query"])
DEFAULT_BINDING = Path(__file__).resolve().parents[1] / "integrations/dungeonmind/rules_occupancy_srd_v1.json"


def configured_binding() -> RulesSpaceBinding | None:
    path = Path(os.environ.get("DUNGEONMIND_RULES_BINDING_PATH", str(DEFAULT_BINDING)))
    try:
        return load_binding(path)
    except (OSError, ValueError, KeyError):
        return None


def rules_source() -> RulesSearchPort:
    return DungeonMindRulesSearch(os.environ.get("DUNGEONMIND_RULES_DATABASE_URL"))


@router.post("/query", response_model=RulesQueryPacket)
def post_rules_query(
    request: RulesQueryRequest,
    binding: RulesSpaceBinding | None = Depends(configured_binding),
    source: RulesSearchPort = Depends(rules_source),
) -> RulesQueryPacket:
    return query_rules(request, binding=binding, source=source)
