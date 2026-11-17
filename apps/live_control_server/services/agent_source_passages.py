"""Open a completed answer's exact historical source through native authority."""

from __future__ import annotations

from hashlib import sha256
from uuid import UUID

from application_state.agent_conversation import AgentConversationService
from application_state.agent_conversation.rules_authority_reads import MixedCompletedTurnV1
from application_state.agent_conversation.types import (
    BuildGraphCompletionV2,
    BuildIntentionalResponseCompletionV1,
    BuildGraphContextReceiptV1,
    SurfaceSourceCompletionV1,
    SurfaceEvidenceCompletionV1,
    PlanWorldGraphContextReceiptV1, PlanSourceContextReceiptV1,
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
    if isinstance(turn, MixedCompletedTurnV1):
        # inspect_turn validated the accepted composition, base owner and completion seal.
        if turn.base_projection.kind != "approved":
            raise SourcePassageOpenError("source_passage_completion_unavailable", 404)
        turn = turn.base_projection.turn
    if turn.world_id != world_id or turn.turn_id != turn_id:
        raise SourcePassageOpenError("source_passage_binding_invalid")
    if turn.status != "completed" or not (
        (
            isinstance(
                turn.completion,
                (BuildGraphCompletionV2, BuildIntentionalResponseCompletionV1),
            )
            and isinstance(turn.graph_context_receipt, BuildGraphContextReceiptV1)
        )
        or (
            isinstance(
                turn.completion, (SurfaceSourceCompletionV1, SurfaceEvidenceCompletionV1)
            )
            and isinstance(
                turn.graph_context_receipt,
                (PlanWorldGraphContextReceiptV1, PlanSourceContextReceiptV1, PlayWorldGraphContextReceiptV1),
            )
        )
    ):
        raise SourcePassageOpenError("source_passage_completion_unavailable", 404)
    if citation_index >= len(turn.completion.source_citations):
        raise SourcePassageOpenError("source_passage_not_found", 404)
    citation = turn.completion.source_citations[citation_index]
    receipt = citation.receipt
    from application_state.agent_conversation.plan_source_context import require_graph
    root = turn.graph_context_receipt
    graph = require_graph(root) if isinstance(root, PlanSourceContextReceiptV1) else root
    authority = graph.graph_authority
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


def _completed_evidence_turn(*, world_id: str, turn_id: UUID, service: AgentConversationService):
    turn = service.inspect_turn(world_id=world_id, turn_id=turn_id)
    if isinstance(turn, MixedCompletedTurnV1):
        if turn.base_projection.kind != "approved":
            raise SourcePassageOpenError("source_passage_completion_unavailable", 404)
        turn = turn.base_projection.turn
    if turn.world_id != world_id or turn.turn_id != turn_id or turn.status != "completed":
        raise SourcePassageOpenError("source_passage_binding_invalid")
    return turn


def open_saved_turn_graph_evidence(*, world_id: str, turn_id: UUID, claim_id: str,
        anchor_id: str, service: AgentConversationService):
    from apps.live_control_server.services.agent_turn_service import _evidence_anchor_open_targets

    turn = _completed_evidence_turn(world_id=world_id, turn_id=turn_id, service=service)
    matches = [
        item for item in _evidence_anchor_open_targets(turn)
        if item.claim_id == claim_id and item.anchor_id == anchor_id and item.managed_world_id == world_id
    ]
    if len(matches) != 1:
        raise SourcePassageOpenError("source_passage_not_found", 404)
    return _open_pinned_evidence_anchor(matches[0])


def open_saved_plan_action_graph_evidence(*, world_id: str, action_id: UUID, claim_id: str, anchor_id: str):
    from application_state.plan_action_dialogue.service import PlanActionDialogueService
    from apps.live_control_server.models.agent_turn import AgentEvidenceAnchorOpenTargetV1
    from apps.live_control_server.services.plan_action_consultation import project_plan_action_source_targets

    action = PlanActionDialogueService().read_prompt_action(world_id=world_id, action_id=action_id)
    matches = [
        item for item in project_plan_action_source_targets(action)
        if item["claim_id"] == claim_id and item["anchor_id"] == anchor_id
        and item["managed_world_id"] == world_id
    ]
    if len(matches) != 1:
        raise SourcePassageOpenError("source_passage_not_found", 404)
    return _open_pinned_evidence_anchor(AgentEvidenceAnchorOpenTargetV1.model_validate(matches[0]))


def _open_pinned_evidence_anchor(target):
    from apps.live_control_server.services.managed_world_graph_projection import resolve_managed_world_binding

    world_id = target.managed_world_id
    try:
        binding = resolve_managed_world_binding(world_id)
        if (binding.native_world_id, binding.binding_version) != (target.native_world_id, target.binding_version):
            raise SourcePassageOpenError("source_passage_binding_invalid")
        opened = direct.read_source_anchor_direct_v2(
            direct.direct_services_from_config(target.native_world_id),
            WorldGraphSourceAnchorReadRequest.model_validate({
                "schema": "dmb_world_graph_source_anchor_read_request_v1",
                "worldId": target.native_world_id, "campaignId": "", "scopeMode": "world",
                "focus": {"kind": "none", "sessionId": None, "campaignId": None},
                "admissibility": "gm", "revisionPin": target.graph_revision, "anchorId": target.anchor_id,
            }),
            repo_root=artifact_data_root(),
        )
        if resolve_managed_world_binding(world_id) != binding:
            raise SourcePassageOpenError("source_passage_binding_invalid")
    except SourcePassageOpenError:
        raise
    except Exception as exc:
        raise SourcePassageOpenError("source_passage_unavailable") from exc
    result = opened.result
    if (
        opened.graph_revision != target.graph_revision
        or opened.source_revision_id != target.source_revision_id
        or opened.source_artifact_id != target.source_artifact_id
        or opened.evidence_ref_id != target.evidence_ref_id
        or result.anchor_id != target.anchor_id
        or result.source_artifact_id != target.source_artifact_id
        or result.evidence_ref_id != target.evidence_ref_id
        or result.snapshot is None
        or result.snapshot.world_id != target.native_world_id
        or result.snapshot.revision_id != target.graph_revision
    ):
        raise SourcePassageOpenError("source_passage_binding_invalid")
    return result


def open_saved_turn_related_recap(*, world_id: str, turn_id: UUID, claim_id: str,
        anchor_id: str, continuation: str | None, service: AgentConversationService):
    from apps.live_control_server.services.agent_turn_service import project_plan_turn_context
    from apps.live_control_server.services.managed_world_graph_projection import resolve_managed_world_binding
    from graph_memory.retrieval.models import RecapContextReadRequestV2

    turn = _completed_evidence_turn(world_id=world_id, turn_id=turn_id, service=service)
    context = project_plan_turn_context(turn, delivery_replay=False)
    matches = [
        item for item in getattr(context, "source_open_targets", ())
        if item.kind == "related_recap_context" and item.claim_id == claim_id
        and item.context_anchor_id == anchor_id and item.managed_world_id == world_id
    ]
    if len(matches) != 1:
        raise SourcePassageOpenError("source_passage_not_found", 404)
    target = matches[0]
    try:
        binding = resolve_managed_world_binding(world_id)
        if (binding.native_world_id, binding.binding_version) != (target.native_world_id, target.binding_version):
            raise SourcePassageOpenError("source_passage_binding_invalid")
        result = direct.read_recap_context_direct_v2(
            direct.direct_services_from_config(target.native_world_id),
            RecapContextReadRequestV2.model_validate({
                "schema": "dmb_recap_context_read_request_v2",
                "worldId": target.native_world_id, "campaignId": "", "scopeMode": "world",
                "focus": {"kind": "none", "sessionId": None, "campaignId": None},
                "admissibility": "gm", "revisionPin": target.graph_revision,
                "contextAnchorId": target.context_anchor_id, "maxChars": 12000,
                "continuation": continuation,
            }),
            repo_root=artifact_data_root(),
        )
        if resolve_managed_world_binding(world_id) != binding:
            raise SourcePassageOpenError("source_passage_binding_invalid")
    except SourcePassageOpenError:
        raise
    except Exception as exc:
        raise SourcePassageOpenError("source_passage_unavailable") from exc
    descriptor = result.context
    if (
        descriptor is None or descriptor.source_artifact_id != target.source_artifact_id
        or descriptor.source_revision_id != target.source_revision_id
        or descriptor.content_sha256 != target.content_sha256
        or descriptor.context_anchor_id != target.context_anchor_id
        or result.snapshot is None or result.snapshot.world_id != target.native_world_id
        or result.snapshot.revision_id != target.graph_revision
    ):
        raise SourcePassageOpenError("source_passage_binding_invalid")
    return result
