"""Admitted campaign→world overlay API."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from apps.live_control_server.services.admitted_campaign_worlds import (
    AdmittedCampaignWorldsDocument,
    load_admitted_campaign_worlds,
)

router = APIRouter(prefix="/api/live", tags=["admitted-campaign-worlds"])


@router.get(
    "/admitted-campaign-worlds",
    response_model=AdmittedCampaignWorldsDocument,
)
def get_admitted_campaign_worlds() -> dict[str, Any]:
    return load_admitted_campaign_worlds().model_dump(mode="json")
