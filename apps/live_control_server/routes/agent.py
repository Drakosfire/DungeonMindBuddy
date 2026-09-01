from __future__ import annotations

from typing import Any

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from apps.live_control_server.config import repo_root, session_dir
from apps.live_control_server.services.agent_query import (
    AgentQueryRequest,
    AgentQueryRequestError,
    process_agent_query,
)
from apps.live_control_server.services.agent_world_graph_query_context import (
    AgentWorldGraphQueryContextError,
)
from apps.live_control_server.services.hermes_graph_query import HermesGraphQueryRequestError

router = APIRouter(prefix="/api/agent", tags=["agent"])


@router.post("/query", response_model=None)
def post_agent_query(body: AgentQueryRequest) -> Any:
    try:
        return process_agent_query(
            body.text,
            base=session_dir(),
            root=repo_root(),
            agent_thread_id=body.agent_thread_id,
            hermes_session_pointer=body.hermes_session_pointer,
            trace_requested=body.trace_requested,
            world_graph_context=body.world_graph_context,
            conversation_history=body.conversation_history,
            surface_context=body.surface_context,
            session_base=session_dir(),
        )
    except AgentQueryRequestError as exc:
        return JSONResponse(status_code=exc.status_code, content=exc.response_body())
    except HermesGraphQueryRequestError as exc:
        return JSONResponse(status_code=exc.status_code, content=exc.response_body())
    except AgentWorldGraphQueryContextError as exc:
        return JSONResponse(status_code=exc.status_code, content=exc.response_body())
    except ValidationError as exc:
        return JSONResponse(
            status_code=422,
            content={
                "schema": "dmb_world_graph_projection_error_v1",
                "code": "invalid_request",
                "message": str(exc),
                "statusCode": 422,
                "diagnostics": [
                    {
                        "code": "invalid_request",
                        "message": str(exc),
                        "severity": "error",
                    }
                ],
            },
        )
