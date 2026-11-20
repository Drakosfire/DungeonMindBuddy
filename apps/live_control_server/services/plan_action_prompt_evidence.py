"""Exact prepared requests owned by durable Plan actions, separate from Ask traces."""
from __future__ import annotations

from hashlib import sha256
from uuid import UUID

from application_state.plan_action_dialogue.service import PlanActionDialogueService
from application_state.plan_action_dialogue.types import ActionPromptReferenceV1
from apps.live_control_server.services.agent_prompt_evidence import (
    PromptEvidenceError, read_prompt, store_prompt,
)


def capture_prompt(*, store, action, view, authorization):
    consultation = action.consultation
    if (consultation is None or consultation.execution is None
            or not consultation.execution.events
            or consultation.execution.events[-1] != authorization
            or authorization.envelope_sha256 != view["payloadSha256"]
            or sha256(view["payloadJson"].encode("utf-8")).hexdigest() != authorization.envelope_sha256
            or len(view["payloadJson"].encode("utf-8")) != view["payloadUtf8Bytes"]):
        raise PromptEvidenceError("action_prompt_authorization_mismatch")
    evidence_id = store_prompt(view["payloadJson"], digest=view["payloadSha256"], size=view["payloadUtf8Bytes"])
    reference = ActionPromptReferenceV1(
        world_id=action.basis.world_id, action_id=action.action_id,
        dispatch_fence=action.fence, authorization_event_id=authorization.event_id,
        provider_attempt_id=authorization.provider_attempt_id, evidence_id=evidence_id,
        provider=authorization.provider, model=authorization.model,
        api_mode=authorization.api_mode, serializer_version=authorization.serializer_version,
        payload_sha256=view["payloadSha256"], payload_utf8_bytes=view["payloadUtf8Bytes"],
    )
    updated, _ = store.append_prompt_reference(
        action_id=action.action_id, token=action.dispatch_token, fence=action.fence, reference=reference,
    )
    if reference not in getattr(updated.consultation, "prompt_references", []):
        raise PromptEvidenceError("action_prompt_capture_not_acknowledged")
    return updated


def _references(world_id: str, action_id: UUID):
    action = PlanActionDialogueService().read_prompt_action(world_id=world_id, action_id=action_id)
    return getattr(action.consultation, "prompt_references", [])


def _metadata(reference):
    # Blob IDs and dispatch fences remain private; the actual attempt selects reads.
    return reference.model_dump(mode="json", exclude={"evidence_id", "dispatch_fence"})


def prompt_index(world_id: str, action_id: UUID):
    return {"schema": "dmb_plan_action_prompt_index_v1", "world_id": world_id,
            "action_id": str(action_id), "references": [_metadata(ref) for ref in _references(world_id, action_id)]}


def prompt_body(world_id: str, action_id: UUID, provider_attempt_id: UUID):
    matches = [ref for ref in _references(world_id, action_id) if ref.provider_attempt_id == provider_attempt_id]
    if len(matches) != 1:
        raise PromptEvidenceError("action_prompt_not_captured")
    reference = matches[0]
    return {"schema": "dmb_plan_action_prompt_evidence_v1", "world_id": world_id,
            "action_id": str(action_id), "reference": _metadata(reference), "payload_json": read_prompt(reference)}
