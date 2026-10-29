"""Native statement support commitments; no classic Graph or APP source aliases."""

from __future__ import annotations

from hashlib import sha256
import json
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator
from graph_memory.ingestion.selection_context import NativeStatementSelectionV1


def canonical(value):
    if isinstance(value, BaseModel):
        value = value.model_dump(mode="json", by_alias=True)
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )


def digest(value):
    return sha256(canonical(value).encode()).hexdigest()


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, populate_by_name=True)


class NativeAuthorityRefV1(Strict):
    authority_id: str = Field(min_length=1)
    revision: str = Field(min_length=1)
    descriptor_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")


class NativeStatementSupportV1(Strict):
    statement_id: str = Field(pattern=r"^ent:.+")
    payload: dict
    semantic_digest: str = Field(pattern=r"^[a-f0-9]{64}$")
    assertion_ids: list[str]
    publication_receipt: dict
    result_mappings: list[dict]
    ancestry: list[dict]
    source_artifact_id: str = Field(min_length=1)
    source_revision_id: str = Field(min_length=1)
    source_body_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    clause_start_byte: int = Field(ge=0, strict=True)
    clause_end_byte: int = Field(gt=0, strict=True)
    clause_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    clause_text: str = Field(min_length=1)

    @model_validator(mode="after")
    def exact_support(self):
        p = self.payload
        required = {
            "schema",
            "clause",
            "quote",
            "meaning",
            "mode",
            "reporter",
            "referents",
            "uncertainty",
            "qualifications",
            "episode",
            "source_order",
            "embedded_content_factive",
            "assertion_target",
            "visibility",
            "proof",
        }
        if (
            set(p) != required
            or p["schema"] != "dmb_source_statement_v1"
            or p["embedded_content_factive"] is not False
            or p["assertion_target"] != "source_statement"
            or p["mode"] not in {"narrator", "reported", "uncertain"}
            or (p["mode"] == "reported" and not p["reporter"])
            or not p["referents"]
            or not p["qualifications"]
            or digest({k: v for k, v in p.items() if k != "proof"})
            != self.semantic_digest
        ):
            raise ValueError("Complete nonfactive qualified payload required")
        clause = p["clause"]
        if (
            self.clause_end_byte - self.clause_start_byte
            != len(self.clause_text.encode())
            or sha256(self.clause_text.encode()).hexdigest() != self.clause_sha256
            or p["quote"] != self.clause_text
            or (
                clause["source_sha256"],
                clause["start_byte"],
                clause["end_byte"],
                clause["clause_sha256"],
            )
            != (
                self.source_body_sha256,
                self.clause_start_byte,
                self.clause_end_byte,
                self.clause_sha256,
            )
        ):
            raise ValueError("Exact source clause commitment differs")
        expected_publication = "dmb-statement:v1:" + digest(clause)
        receipt = self.publication_receipt
        child = receipt.get("published_revision_id")
        if (
            receipt.get("publication_id") != expected_publication
            or not child
            or not self.ancestry
            or self.ancestry[-1]["revision_id"] != child
            or self.ancestry[-1]["parent_revision_id"]
            != receipt.get("expected_parent_revision_id")
        ):
            raise ValueError("Original publication correspondence is required")
        seen = set()
        for i, header in enumerate(self.ancestry):
            if header["revision_id"] in seen or (
                i
                and self.ancestry[i - 1]["parent_revision_id"] != header["revision_id"]
            ):
                raise ValueError("Native ancestry differs or cycles")
            seen.add(header["revision_id"])
        mappings = self.result_mappings
        expected_ops = {
            "statement",
            "qualified-payload",
            *(f"about:{i}" for i in range(len(p["referents"]))),
        }
        if p["reporter"]:
            expected_ops.add("reporter")
        if (
            len(mappings) != len(expected_ops)
            or {b["client_op_id"] for b in mappings} != expected_ops
            or [b["durable_id"] for b in mappings if b["result_kind"] == "entity"]
            != [self.statement_id]
            or sorted(
                b["durable_id"] for b in mappings if b["result_kind"] == "assertion"
            )
            != self.assertion_ids
        ):
            raise ValueError("Original statement mappings differ")
        return self


class NativeStatementFrameV1(Strict):
    schema_: Literal["dmb_native_statement_frame_v1"] = Field(
        default="dmb_native_statement_frame_v1", alias="schema"
    )
    authority: Literal["native_vnext"] = "native_vnext"
    managed_world_id: str
    native_world_id: str
    binding_version: int = Field(ge=1, strict=True)
    campaign_id: str
    role: Literal["gm", "player"]
    revision_id: str
    domain_ref: NativeAuthorityRefV1
    profile_ref: NativeAuthorityRefV1
    subject_id: str = Field(pattern=r"^ent:.+")
    status: Literal["complete", "partial", "no_visible_statements"]
    gap_codes: list[str]
    supports: list[NativeStatementSupportV1]
    universal_absence_claimed: Literal[False] = False

    @model_validator(mode="after")
    def one_authority(self):
        ids = [s.statement_id for s in self.supports]
        if len(ids) != len(set(ids)) or (
            self.status == "complete" and (self.gap_codes or not ids)
        ):
            raise ValueError("Native completeness differs from support inventory")
        if self.status == "no_visible_statements" and (ids or self.gap_codes):
            raise ValueError("No visible statements cannot carry support/gaps")
        if self.status == "partial" and not self.gap_codes:
            raise ValueError("Partial context must identify its gaps")
        for s in self.supports:
            if (
                (s.payload["clause"]["world"], s.payload["clause"]["campaign"])
                != (self.native_world_id, self.campaign_id)
                or self.subject_id not in s.payload["referents"]
                or s.ancestry[0]["revision_id"] != self.revision_id
                or s.publication_receipt.get("space_id") != self.native_world_id
            ):
                raise ValueError(
                    "Qualified support differs from native request authority"
                )
            for h in s.ancestry:
                if (
                    h["space_id"] != self.native_world_id
                    or h["domain_ref"] != self.domain_ref.model_dump()
                    or h["profile_ref"] != self.profile_ref.model_dump()
                ):
                    raise ValueError("Native support ancestry changed authority")
        return self


class NativeStatementContextReceiptV1(Strict):
    schema_: Literal["dmb_native_statement_context_receipt_v1"] = Field(
        default="dmb_native_statement_context_receipt_v1", alias="schema"
    )
    selection: NativeStatementSelectionV1
    frame: NativeStatementFrameV1
    user_text: str
    provenance_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    context_receipt_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")

    @model_validator(mode="after")
    def commitment(self):
        s, f = self.selection, self.frame
        if (
            (s.managed_world_id, s.campaign_id, s.revision_id, s.subject_id)
            != (f.managed_world_id, f.campaign_id, f.revision_id, f.subject_id)
            or s.domain_ref != f.domain_ref.model_dump()
            or s.profile_ref != f.profile_ref.model_dump()
            or digest(
                self.model_dump(
                    mode="json", by_alias=True, exclude={"context_receipt_sha256"}
                )
            )
            != self.context_receipt_sha256
        ):
            raise ValueError("Native receipt selection or commitment differs")
        return self


class NativeStatementWriterPolicyV1(Strict):
    policy_version: Literal["native_statement_writer_v1"] = "native_statement_writer_v1"
    provider: Literal["openai"] = "openai"
    model: str = Field(min_length=1)
    api_mode: Literal["responses"] = "responses"
    output_token_reserve: int = Field(gt=0, strict=True)
    context_limit_tokens: int = Field(gt=0, strict=True)
    requires_native_output_proof: Literal[True] = True


class NativeStatementInputEventV1(Strict):
    kind: Literal["native_statement_input_v1"] = "native_statement_input_v1"
    event_id: UUID
    sequence: int = Field(ge=0, strict=True)
    provider_attempt_id: UUID
    envelope_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    prepared_request_json: str

    @model_validator(mode="after")
    def exact_request(self):
        if (
            sha256(self.prepared_request_json.encode()).hexdigest()
            != self.envelope_sha256
        ):
            raise ValueError("Native producing request bytes differ")
        return self


def validate_request(receipt, policy, raw):
    from .native_statement_answer import OUTPUT_SCHEMA, INSTRUCTIONS
    from .source_writer_output import strict_json

    body = strict_json(raw)
    expected = {
        "model": policy.model,
        "input": [
            {
                "role": "user",
                "content": canonical(
                    {
                        "question": receipt.user_text,
                        "native_statement_context": receipt.frame.model_dump(
                            mode="json", by_alias=True
                        ),
                    }
                ),
            }
        ],
        "instructions": INSTRUCTIONS,
        "max_output_tokens": policy.output_token_reserve,
        "text": {
            "format": {
                "type": "json_schema",
                "name": "native_statement_answer",
                "strict": True,
                "schema": OUTPUT_SCHEMA,
            }
        },
        "tools": [],
        "stream": False,
        "reasoning": {"effort": "none"},
        "service_tier": "fast",
    }
    if body != expected:
        raise ValueError(
            "Actual native writer request changed evidence, instructions or capability"
        )
    if (
        native_input_tokens(raw, body) + policy.output_token_reserve
        > policy.context_limit_tokens
    ):
        raise ValueError("Native writer exceeds its frozen provider context allowance")
    return body


def native_input_tokens(raw, body=None):
    if body is None:
        from .source_writer_output import strict_json

        body = strict_json(raw)

    def nodes(value):
        if isinstance(value, dict):
            return 1 + sum(1 + nodes(v) for v in value.values())
        if isinstance(value, list):
            return 1 + sum(nodes(v) for v in value)
        return 1

    return len(raw.encode()) + 64 * (1 + nodes(body))
