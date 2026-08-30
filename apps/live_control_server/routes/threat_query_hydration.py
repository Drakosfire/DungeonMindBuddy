"""SBW10a: read-only exact Threat query + mechanics hydration API."""

from __future__ import annotations



from fastapi import APIRouter, HTTPException

from fastapi.responses import JSONResponse

from pydantic import ValidationError



from apps.live_control_server.config import world_graph_root

from apps.live_control_server.models.threat_query_hydration import (

    ThreatQueryHydrationRequestV1,

)

from apps.live_control_server.services.threat_query_hydration import (

    ThreatQueryHydrationError,

    query_threats_with_hydration,

)



router = APIRouter(prefix="/api/live/threats", tags=["threat-query-hydration"])





@router.post("/query-hydration")

def post_threat_query_hydration(body: ThreatQueryHydrationRequestV1) -> JSONResponse:

    root = world_graph_root()

    try:

        response = query_threats_with_hydration(body, root=root)

    except ThreatQueryHydrationError as exc:

        return JSONResponse(

            status_code=exc.status_code,

            content={

                "schema": "dmb_threat_query_hydration_error_v1",

                "resultLabel": exc.result_label,

                "message": str(exc),

                "diagnostics": exc.diagnostics,

            },

        )

    except ValidationError as exc:

        raise HTTPException(status_code=422, detail=exc.errors()) from exc



    return JSONResponse(

        status_code=200,

        content=response.model_dump(mode="json", by_alias=True),

    )
