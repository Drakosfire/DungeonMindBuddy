"""Exact current-submission source exposure in a real native Play request.

Pure proof only. The caller owns SDK capture, claim-fenced persistence and send.
No request/source body is retained by this module or represented as a receipt.
"""
from __future__ import annotations

import json
from hashlib import sha256
from typing import Annotated, Literal, Callable
from uuid import UUID

from pydantic import Field, model_validator

from . import types as t
from .rules_authority_types import ClosedRulesModel, canonical_bytes
from .source_writer_output import strict_json
from .play_graph_context import (
    prepare_play_source_provider_inclusion, validate_play_graph_provider_authorization,
)

MAX_REQUEST_BYTES = 1050000


class NativePlayInputV1(ClosedRulesModel):
    schema_: Literal["dmb_native_play_input_v1"] = Field(default="dmb_native_play_input_v1", alias="schema")
    submission_id: UUID
    message: Annotated[str, Field(min_length=1, max_length=32000)]
    source_frame: t.PlaySourceFrameV1

    @model_validator(mode="after")
    def bounded_input(self):
        if not self.message.strip() or len(canonical_bytes(self)) > 131072:
            raise ValueError("Native Play input is blank or exceeds its UTF8 budget")
        return self


def _user_texts(body, mode):
    if mode == "chat_completions" and "input" not in body:
        messages, block_type = body.get("messages"), "text"
    elif mode == "codex_responses" and "messages" not in body:
        messages, block_type = body.get("input"), "input_text"
    else:
        raise ValueError("Unknown or ambiguous native Play provider representation")
    if not isinstance(messages, list) or len(messages) > 4096:
        raise ValueError("Native Play provider messages exceed their bound")
    for message in messages:
        if not isinstance(message, dict):
            raise ValueError("Native Play provider message is malformed")
        if message.get("role") != "user":
            continue
        if mode == "codex_responses" and message.get("type", "message") != "message":
            continue
        content = message.get("content")
        if isinstance(content, str):
            yield content
        elif (isinstance(content, list) and len(content) == 1 and isinstance(content[0], dict)
                and set(content[0]) == {"type", "text"} and content[0]["type"] == block_type
                and isinstance(content[0]["text"], str)):
            yield content[0]["text"]


def prove_play_source_input(
    receipt: t.PlayWorldGraphContextReceiptV1,
    execution: t.PlayWorldGraphExecutionV1,
    authorization: t.ProviderAttemptAuthorizedEventV3,
    *, prepared_request_json: str, submission_id: UUID, original_message: str,
    event_id: UUID, owner_resolved_current_moment_text: str | None = None,
    owner_resolver: Callable[[t.PlaySourceFrameV1], str | None] | None = None,
) -> t.PlaySourceProviderInclusionV1:
    """Derive a witness only from the exact current producing request body.

    General SDK envelope/tool/budget validation remains with its existing owner.
    This adds explicit source-body proof; a precomputed manifest is insufficient.
    """
    if not isinstance(prepared_request_json, str) or len(prepared_request_json.encode("utf-8")) > MAX_REQUEST_BYTES:
        raise ValueError("Native Play prepared request exceeds its UTF8 bound")
    authorization = t.ProviderAttemptAuthorizedEventV3.model_validate_json(authorization.model_dump_json(by_alias=True))
    if sha256(prepared_request_json.encode("utf-8")).hexdigest() != authorization.envelope_sha256:
        raise ValueError("Native Play source request differs from its actual producer hash")
    body = strict_json(prepared_request_json)
    if not isinstance(body, dict) or body.get("model") != authorization.model:
        raise ValueError("Native Play source request differs from its producing model")
    carriers = []
    for text in _user_texts(body, authorization.api_mode):
        try:
            value = strict_json(text)
        except (ValueError, TypeError):
            continue
        if not isinstance(value, dict) or value.get("schema") != "dmb_native_play_input_v1":
            continue
        carrier = NativePlayInputV1.model_validate_json(json.dumps(value, ensure_ascii=False))
        if carrier.submission_id == submission_id:
            carriers.append(carrier)
    if len(carriers) != 1 or carriers[0].message != original_message:
        raise ValueError("Native Play request lacks one exact current-submission source carrier")
    frame = carriers[0].source_frame
    if frame.manifest != receipt.play_sources or t.canonical_sha256(frame) != receipt.play_source_frame_sha256:
        raise ValueError("Native Play source frame differs from its frozen receipt")
    if owner_resolver is not None:
        if owner_resolved_current_moment_text is not None:
            raise ValueError("Native Play source proof requires one independent owner resolver")
        owner_resolved_current_moment_text = owner_resolver(frame)
    included = prepare_play_source_provider_inclusion(receipt, execution, frame,
        event_id=event_id, provider_attempt_id=authorization.provider_attempt_id,
        envelope_sha256=authorization.envelope_sha256,
        owner_resolved_current_moment_text=owner_resolved_current_moment_text)
    wire = execution.model_dump(mode="json", by_alias=True)
    wire["events"].append(included.model_dump(mode="json", by_alias=True))
    pending = t.PlayWorldGraphExecutionV1.model_validate_json(json.dumps(wire))
    # The inclusion precedes the exact same authorization, never an arbitrary
    # earlier producer or an unaccounted source projection.
    validate_play_graph_provider_authorization(receipt, pending, authorization)
    return included
