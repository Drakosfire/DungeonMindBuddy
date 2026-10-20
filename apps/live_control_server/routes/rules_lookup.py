"""Authenticated passive rules lookup; no source paths or remote fetches."""
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, Query, Response
from apps.live_control_server.services.agent_graph_auth import native_graph_gm_dependency
from apps.live_control_server.services import rules_lookup as service

router = APIRouter(prefix="/api/live/rules", tags=["rules"], dependencies=[Depends(native_graph_gm_dependency)])
DigestQuery = Annotated[str, Query(pattern=r"^[a-f0-9]{64}$")]

def _read(response: Response, call):
    response.headers["Cache-Control"] = "no-store"
    try:
        return call()
    except service.RulesCorpusUnavailable:
        raise HTTPException(503, detail={"code": "rules_corpus_unavailable", "message": "This rules source is unavailable."}, headers={"Cache-Control": "no-store"})

@router.get("/catalog")
def get_catalog(response: Response):
    return _read(response, service.catalog)

@router.get("/query")
def get_query(response: Response, corpus: DigestQuery, question: Annotated[str, Query(min_length=1, max_length=800)], limit: Annotated[int, Query(ge=1, le=8)] = 4):
    if not question.strip():
        raise HTTPException(422, detail="Enter a rules question.", headers={"Cache-Control": "no-store"})
    return _read(response, lambda: service.query_rules(corpus, question, limit))

@router.get("/passages/{citation_id}")
def get_passage(response: Response, citation_id: str, corpus: DigestQuery):
    import re
    if not re.fullmatch(r"[a-f0-9]{64}", citation_id):
        raise HTTPException(422, detail="Invalid rules citation.", headers={"Cache-Control": "no-store"})
    result = _read(response, lambda: service.inspect_passage(corpus, citation_id))
    if result is None:
        raise HTTPException(404, detail="This exact rules passage is unavailable.", headers={"Cache-Control": "no-store"})
    return result
