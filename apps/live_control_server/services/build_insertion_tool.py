"""Parent-owned Harness action. Model arguments never select a document or write it."""
from __future__ import annotations

import asyncio
from hashlib import sha256
import json
from uuid import UUID

from application_state.build_proposal.service import BuildProposalService
from application_state.build_proposal.types import BuildProposalOrigin
from application_state.errors import ApplicationStateNotFoundError
from apps.live_control_server.models.build_document_proposal import BuildDocumentProposalRequest, BuildWriteCapability
from . import build_document_proposal

TOOL_NAME = "propose_build_insertion"


def arguments_digest(arguments: dict) -> str:
    return sha256(json.dumps(arguments, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()


def validate_included_results(body, permitted):
    calls = {item["call_id"]: item for item in body.get("input", [])
        if isinstance(item, dict) and item.get("type") == "function_call"}
    for item in body.get("input", []):
        if not isinstance(item, dict) or item.get("type") != "function_call_output":
            continue
        call = calls.get(item.get("call_id"), {})
        if call.get("name") != TOOL_NAME:
            continue
        arguments = json.loads(call["arguments"])
        if (arguments_digest(arguments), item["output"]) not in permitted:
            raise ValueError("Unproved Build tool result in provider input")


class BuildInsertionTool:
    def __init__(self, capability: BuildWriteCapability, client_turn_id: str, current_turn):
        self.capability = capability
        self.client_turn_id = UUID(client_turn_id)
        self.current_turn = current_turn

    def dispatch(self, message):
        capability = self.capability
        args = message.get("arguments")
        operation_id = message.get("operationId")
        try:
            if (message.get("toolName") != TOOL_NAME or not isinstance(args, dict)
                    or set(args) != {"instruction"} or not isinstance(args["instruction"], str)
                    or not args["instruction"].strip()
                    or not isinstance(operation_id, str) or not 0 < len(operation_id) <= 256):
                raise ValueError("build_insertion_arguments_invalid")
            turn = self.current_turn()
            if (turn is None or turn.status != "running" or turn.world_id != capability.basis.world_id
                    or turn.conversation_id != capability.conversation_id
                    or turn.provenance.surface_id != "build"
                    or turn.provenance.primary_work.kind != "build"
                    or turn.provenance.primary_work.object_id != capability.basis.document_id
                    or turn.provenance.primary_work.revision != str(capability.basis.registry_revision)
                    or turn.provenance.primary_work.content_sha256 != capability.basis.content_sha256):
                raise ValueError("build_insertion_turn_changed")
            origin = BuildProposalOrigin(client_turn_id=self.client_turn_id, durable_turn_id=turn.turn_id, turn_attempt=turn.attempt,
                broker_operation_id=operation_id, arguments_sha256=arguments_digest(args))
            store = BuildProposalService()
            try:
                existing = store.get(capability.basis.world_id, capability.idempotency_key)
            except ApplicationStateNotFoundError:
                existing = None
            if existing is not None:
                saved = existing.reservation
                if (saved.basis != capability.basis or saved.conversation_id != capability.conversation_id
                        or saved.expected_pointer_revision != capability.expected_pointer_revision
                        or saved.origin is None or saved.origin.client_turn_id != self.client_turn_id
                        or saved.origin.durable_turn_id != turn.turn_id
                        or saved.origin.turn_attempt != turn.attempt
                        or saved.origin.arguments_sha256 != origin.arguments_sha256
                        or saved.instruction != args["instruction"]):
                    raise ValueError("build_insertion_request_changed")
                return self._reply(existing)
            request = BuildDocumentProposalRequest(**capability.model_dump(exclude={"instruction", "origin"}),
                instruction=args["instruction"], origin=origin)
            # The existing generator owns its separate provider authorization and
            # lifecycle. It never executes inside the worker or inherits its call.
            try:
                record = asyncio.run(build_document_proposal.compose(request))
            except Exception:
                try:
                    record = store.get(capability.basis.world_id, capability.idempotency_key)
                except ApplicationStateNotFoundError:
                    raise ValueError("build_insertion_not_prepared") from None
            return self._reply(record)
        except (ValueError, TypeError):
            return {"resultJson": json.dumps({"schema": "dmb_build_insertion_tool_result_v1",
                "status": "unavailable", "action_id": str(capability.idempotency_key),
                "message": "The page proposal could not be prepared for this captured target. Nothing was inserted. Ask again from the current editable page."}),
                "retrievalSession": None}

    @staticmethod
    def _reply(record):
        return {"resultJson": json.dumps({"schema": "dmb_build_insertion_tool_result_v1",
            "status": "awaiting_approval" if record.state == "proposed" else record.state,
            "action_id": str(record.action_id), "summary": record.proposal.summary if record.proposal else None,
            "message": "A preview is ready below this conversation. The user must approve Insert into page, then Save. Nothing has been inserted."
                if record.proposal else "The request has not produced a preview. Do not repeat this tool or regenerate automatically."}),
            "retrievalSession": None}
