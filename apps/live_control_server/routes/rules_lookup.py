"""Authenticated passive rules lookup; no source paths or remote fetches."""
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from apps.live_control_server.services.agent_graph_auth import enforce_native_graph_gm
from apps.live_control_server.services import hosted_auth
from apps.live_control_server.services import rules_lookup as service

def require_rules_access(request: Request, world_id: str | None = None):
    from apps.live_control_server.services.hosted_native_graph_access import require_conversation_access

    require_conversation_access(request, world_id or "", authorize_local=enforce_native_graph_gm)


router = APIRouter(prefix="/api/live/rules", tags=["rules"], dependencies=[Depends(require_rules_access)])
DigestQuery = Annotated[str, Query(pattern=r"^[a-f0-9]{64}$")]

def _read(request: Request, response: Response, call):
    response.headers["Cache-Control"] = "no-store"
    try:
        result = call()
    except service.RulesCorpusUnavailable:
        raise HTTPException(503, detail={"code": "rules_corpus_unavailable", "message": "This rules source is unavailable."}, headers={"Cache-Control": "no-store"})

    if hosted_auth.deployment_environment() not in hosted_auth.LOCAL_ENVIRONMENTS:
        require_rules_access(request, request.query_params.get("world_id"))
    return result

@router.get("/catalog")
def get_catalog(request: Request, response: Response):
    return _read(request, response, service.catalog)

@router.get("/query")
def get_query(request: Request, response: Response, corpus: DigestQuery, question: Annotated[str, Query(min_length=1, max_length=800)], limit: Annotated[int, Query(ge=1, le=8)] = 4):
    if not question.strip():
        raise HTTPException(422, detail="Enter a rules question.", headers={"Cache-Control": "no-store"})
    return _read(request, response, lambda: service.query_rules(corpus, question, limit))

@router.get("/passages/{citation_id}")
def get_passage(request: Request, response: Response, citation_id: str, corpus: DigestQuery):
    import re
    if not re.fullmatch(r"[a-f0-9]{64}", citation_id):
        raise HTTPException(422, detail="Invalid rules citation.", headers={"Cache-Control": "no-store"})
    result = _read(request, response, lambda: service.inspect_passage(corpus, citation_id))
    if result is None:
        raise HTTPException(404, detail="This exact rules passage is unavailable.", headers={"Cache-Control": "no-store"})
    return result
