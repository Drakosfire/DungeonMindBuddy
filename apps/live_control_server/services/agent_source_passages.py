"""Open a completed answer's exact historical source through native authority."""

from __future__ import annotations

from hashlib import sha256
from uuid import UUID

from application_state.agent_conversation import AgentConversationService
from application_state.agent_conversation.types import (
    BuildGraphCompletionV2,
    BuildGraphContextReceiptV1,
    SurfaceSourceCompletionV1,
    SurfaceEvidenceCompletionV1,
    PlanWorldGraphContextReceiptV1,
    PlayWorldGraphContextReceiptV1,
)
from apps.live_control_server.config import artifact_data_root
from apps.live_control_server.integrations.dungeonmind import (
    world_graph_reads as direct,
)
from apps.live_control_server.models.agent_turn import (
    AgentSourcePassageOpenTargetV1,
    AgentSourcePassageReadResponseV1,
)
from graph_memory.retrieval.models import WorldGraphSourceAnchorReadRequest


class SourcePassageOpenError(ValueError):
    def __init__(self, code: str, status_code: int = 409):
        super().__init__(code)
        self.code, self.status_code = code, status_code


def open_source_passage(
    *,
    world_id: str,
    turn_id: UUID,
    citation_index: int,
    service: AgentConversationService | None = None,
) -> AgentSourcePassageReadResponseV1:
    if (
        isinstance(citation_index, bool)
        or not isinstance(citation_index, int)
        or not 0 <= citation_index <= 16383
    ):
        raise SourcePassageOpenError("source_passage_selector_invalid", 422)
    # inspect_turn performs full typed reconstruction and completion validation.
    turn = (service or AgentConversationService()).inspect_turn(
        world_id=world_id, turn_id=turn_id
    )
    if (
        turn.status != "completed"
        or not (isinstance(turn.completion, BuildGraphCompletionV2)
            and isinstance(turn.graph_context_receipt, BuildGraphContextReceiptV1)
            or isinstance(turn.completion, (SurfaceSourceCompletionV1, SurfaceEvidenceCompletionV1))
            and isinstance(turn.graph_context_receipt, (PlanWorldGraphContextReceiptV1, PlayWorldGraphContextReceiptV1)))
    ):
        raise SourcePassageOpenError("source_passage_completion_unavailable", 404)
    if citation_index >= len(turn.completion.source_citations):
        raise SourcePassageOpenError("source_passage_not_found", 404)
    citation = turn.completion.source_citations[citation_index]
    receipt = citation.receipt
    authority = turn.graph_context_receipt.graph_authority
    request = WorldGraphSourceAnchorReadRequest.model_validate(
        {
            "schema": "dmb_world_graph_source_anchor_read_request_v1",
            "worldId": authority.native_world_id,
            "campaignId": "",
            "scopeMode": "world",
            "focus": {"kind": "none", "sessionId": None, "campaignId": None},
            "admissibility": "gm",
            "revisionPin": authority.graph_revision,
            "anchorId": receipt.anchor_id,
            "maxChars": receipt.returned_chars,
        }
    )
    try:
        opened = direct.read_source_anchor_direct_v2(
            direct.direct_services_from_config(authority.native_world_id),
            request,
            repo_root=artifact_data_root(),
        )
    except Exception as exc:
        # Never fall back to current source, current Graph, or captured trace text.
        raise SourcePassageOpenError("source_passage_unavailable") from exc
    result, snapshot = opened.result, opened.result.snapshot
    if (
        snapshot is None
        or snapshot.world_id != authority.native_world_id
        or snapshot.revision_id != authority.graph_revision
        or snapshot.scope_mode != "world"
        or snapshot.campaign_id != ""
        or snapshot.admissibility != "gm"
        or snapshot.focus.kind != "none"
        or snapshot.focus.session_id is not None
        or snapshot.focus.campaign_id is not None
        or opened.graph_revision != authority.graph_revision
        or opened.source_revision_id != receipt.source_revision_id
        or opened.source_artifact_id != receipt.source_artifact_id
        or opened.evidence_ref_id != receipt.evidence_ref_id
        or result.anchor_id != receipt.anchor_id
        or result.evidence_ref_id != receipt.evidence_ref_id
        or result.source_artifact_id != receipt.source_artifact_id
        or result.outcome != "enough"
        or result.truncated
        or not isinstance(result.content, str)
        or not result.content
        or len(result.content) != receipt.returned_chars
        # Native content_sha256 identifies the full source revision, not the excerpt.
        or result.content_sha256 != opened.source_revision_sha256
        or not opened.source_revision_sha256
        or sha256(result.content.encode()).hexdigest() != receipt.content_sha256
        or result.line_start != receipt.line_start
        or result.line_end != receipt.line_end
    ):
        raise SourcePassageOpenError("source_passage_binding_invalid")
    return AgentSourcePassageReadResponseV1(
        target=AgentSourcePassageOpenTargetV1(
            world_id=world_id, turn_id=turn_id, citation_index=citation_index
        ),
        citation=citation,
        content=result.content,
    )
