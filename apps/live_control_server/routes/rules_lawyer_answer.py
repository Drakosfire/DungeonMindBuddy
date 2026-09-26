"""Rules Lawyer answer composed from one server-owned exact evidence packet."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from apps.live_control_server.models.rules_lawyer_answer import RulesAnswerResponse
from apps.live_control_server.models.rules_query import RulesQueryRequest
from apps.live_control_server.routes.rules_query import configured_binding, rules_source
from apps.live_control_server.services.rules_lawyer_answer import synthesize_rules_answer
from apps.live_control_server.services.rules_query import RulesSearchPort, RulesSpaceBinding, query_rules


router = APIRouter(prefix="/api/live/rules", tags=["rules-answer"])


@router.post("/answer", response_model=RulesAnswerResponse)
async def post_rules_answer(
    request: RulesQueryRequest,
    binding: RulesSpaceBinding | None = Depends(configured_binding),
    source: RulesSearchPort = Depends(rules_source),
) -> RulesAnswerResponse:
    packet = query_rules(request, binding=binding, source=source)
    return await synthesize_rules_answer(question=request.question, packet=packet)
