"""Harness image direction. Only the parent chooses the page and authorizes storage."""

import json
from uuid import UUID, uuid5

from application_state.build_proposal.images import BuildImageService
from application_state.build_proposal.types import (
    BuildProposalOrigin,
    BuildProposalReservation,
)
from application_state.errors import ApplicationStateError
from .build_insertion_tool import arguments_digest
from .build_document_proposal import _source

TOOL_NAME = "prepare_build_image"


def validate_included_results(body, permitted):
    calls = {
        item["call_id"]: item
        for item in body.get("input", [])
        if isinstance(item, dict) and item.get("type") == "function_call"
    }
    for item in body.get("input", []):
        if not isinstance(item, dict) or item.get("type") != "function_call_output":
            continue
        call = calls.get(item.get("call_id"), {})
        if (
            call.get("name") == TOOL_NAME
            and (arguments_digest(json.loads(call["arguments"])), item["output"])
            not in permitted
        ):
            raise ValueError("Unproved image preparation in provider input")


class BuildImageTool:
    def __init__(self, capability, client_turn_id, current_turn, owner):
        self.capability = capability
        self.client_turn_id = UUID(client_turn_id)
        self.current_turn = current_turn
        self.owner = owner

    def dispatch(self, message):
        try:
            args = message.get("arguments")
            operation = message.get("operationId")
            if (
                message.get("toolName") != TOOL_NAME
                or not isinstance(args, dict)
                or set(args) != {"prompt", "alt", "purpose"}
                or not isinstance(args["prompt"], str)
                or not isinstance(args["alt"], str)
                or args["purpose"] not in ("map", "illustration")
                or not isinstance(operation, str)
                or not 0 < len(operation) <= 256
                or not self.owner
            ):
                raise ValueError("Invalid image preparation")
            turn = self.current_turn()
            if turn is None or turn.status != "running":
                raise ValueError("Current turn unavailable")
            _source(self.capability)
            reservation = BuildProposalReservation(
                **self.capability.model_dump(
                    exclude={
                        "instruction",
                        "origin",
                        "draft_markdown",
                        "idempotency_key",
                    }
                ),
                idempotency_key=uuid5(self.capability.idempotency_key, "image"),
                instruction=args["prompt"],
                origin=BuildProposalOrigin(
                    client_turn_id=self.client_turn_id,
                    durable_turn_id=turn.turn_id,
                    turn_attempt=turn.attempt,
                    broker_operation_id=operation,
                    arguments_sha256=arguments_digest(args),
                ),
            )
            record = BuildImageService().prepare(
                reservation, self.owner, args["prompt"], args["alt"], purpose=args["purpose"]
            )
            reply = {
                "schema": "dmb_build_image_tool_result_v1",
                "status": "prepared",
                "action_id": str(record.action_id),
                "message": "The image prompt is ready in this conversation. The user can open the Image Studio to review it, choose model/settings, Generate, Save and explicitly Insert. No image has been generated or inserted. Do not repeat this tool automatically.",
            }
        except (ValueError, TypeError, ApplicationStateError):
            reply = {
                "schema": "dmb_build_image_tool_result_v1",
                "status": "unavailable",
                "message": "The image direction could not be prepared for this page. Nothing was generated or inserted. Ask again from the current saved editable page.",
            }
        return {"resultJson": json.dumps(reply), "retrievalSession": None}
