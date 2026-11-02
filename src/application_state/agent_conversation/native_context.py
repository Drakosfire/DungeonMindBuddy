"""Native evidence context shared by real Build, Plan and Play work.

This is a stored commitment, not an admission decision. Core remains the source
and Graph authority. The owning surface must resolve its work before capture;
APP must join this context to the actual submitted intent, provenance, execution
and producing provider proof before it authorizes a read or accepts an answer.
No surface aliases or classic Graph authority are manufactured here.
"""
from __future__ import annotations

from typing import Annotated, Literal

from pydantic import Field, model_validator

from .native_corpus import NativeCorpusAuthorityV1
from .native_plan_assertions import NativePlanQueryV2
from .native_plan_statements import NativePlanQueryUnavailableV1
from .native_statement_input import Strict
from .rules_authority_types import canonical_sha256
from .types import (
    BuildSourceContextBasisV1, NativeCorpusUnavailableV1, PlanAskContextBasis,
    PlanContextPolicyV2, PlanPlayableTargetReceiptV1, PlanWorldGraphHistoryPinV1,
    PlayRunTurnContextReceiptV2,
)

Digest = Annotated[str, Field(pattern=r"^[a-f0-9]{64}$", strict=True)]


class BuildWorkContextV1(Strict):
    surface_id: Literal["build"] = "build"
    source_basis: BuildSourceContextBasisV1


class PlanWorkContextV1(Strict):
    surface_id: Literal["plan"] = "plan"
    plan_basis: PlanAskContextBasis
    plan_context_policy: PlanContextPolicyV2
    playable_target: PlanPlayableTargetReceiptV1 | None


class PlayWorkContextV1(Strict):
    surface_id: Literal["play"] = "play"
    play_basis: PlayRunTurnContextReceiptV2


SurfaceWorkContext = Annotated[
    BuildWorkContextV1 | PlanWorkContextV1 | PlayWorkContextV1,
    Field(discriminator="surface_id"),
]


def work_world_id(work: SurfaceWorkContext) -> str:
    if isinstance(work, BuildWorkContextV1):
        return work.source_basis.world_id
    if isinstance(work, PlanWorkContextV1):
        return work.plan_basis.world_id
    if isinstance(work, PlayWorkContextV1):
        return work.play_basis.world_id
    raise ValueError("Native context requires a concrete supported work basis")


class NativeProviderInputV1(Strict):
    """Actual first provider envelope accounting, not a synthetic Graph packet."""
    assembler_version: Literal["surface_native_initial_v1"] = "surface_native_initial_v1"
    provider_model_name: str = Field(min_length=1)
    provider_model_version: str = Field(min_length=1)
    tokenizer_name: str = Field(min_length=1)
    tokenizer_version: str = Field(min_length=1)
    provider_envelope_input_tokens: int = Field(ge=0, strict=True)
    output_token_reserve: int = Field(ge=0, strict=True)
    context_window_limit: int = Field(gt=0, strict=True)
    included_history: tuple[PlanWorldGraphHistoryPinV1, ...]
    assembled_input_sha256: Digest

    @model_validator(mode="after")
    def actual_allowance(self):
        if self.provider_envelope_input_tokens + self.output_token_reserve > self.context_window_limit:
            raise ValueError("Actual native provider input exceeds its context allowance")
        if len({pin.turn_id for pin in self.included_history}) != len(self.included_history):
            raise ValueError("Native initial context contains duplicate history turns")
        return self


class NativeReviewedActionInputV1(Strict):
    """Model-free author admission; its owning review still must be verified."""
    assembler_version: Literal["reviewed_author_admission_v1"] = "reviewed_author_admission_v1"
    submitted_intent_sha256: Digest
    assembled_input_sha256: Digest


NativeInitialInput = Annotated[
    NativeProviderInputV1 | NativeReviewedActionInputV1,
    Field(discriminator="assembler_version"),
]


class SurfaceNativeContextReceiptV1(Strict):
    schema_: Literal["dmb_surface_native_context_receipt_v1"] = Field(
        default="dmb_surface_native_context_receipt_v1", alias="schema")
    receipt_serializer_version: Literal["canonical-json-utf8-v1"] = "canonical-json-utf8-v1"
    context_receipt_sha256: Digest
    provenance_sha256: Digest
    work_context: SurfaceWorkContext
    source_authority: NativeCorpusAuthorityV1 | NativeCorpusUnavailableV1
    native_query: NativePlanQueryV2 | NativePlanQueryUnavailableV1
    assembled_input: NativeInitialInput

    @model_validator(mode="after")
    def coherent_native_context(self):
        world = work_world_id(self.work_context)
        if isinstance(self.assembled_input, NativeReviewedActionInputV1) and not isinstance(self.work_context, BuildWorkContextV1):
            raise ValueError("Model-free reviewed action admission requires actual Build work")
        query = self.native_query
        authority = query.authority if isinstance(query, NativePlanQueryV2) else query
        if self.source_authority.managed_world_id != world or authority.managed_world_id != world:
            raise ValueError("Native capabilities differ from their actual work World")
        if isinstance(self.source_authority, NativeCorpusAuthorityV1) and isinstance(query, NativePlanQueryV2):
            if any(getattr(self.source_authority, key) != getattr(authority, key) for key in (
                    "native_world_id", "binding_version", "revision_id", "domain_ref",
                    "profile_ref", "acquisition_epoch")):
                raise ValueError("Native source and query commitments differ")
        value = self.model_dump(mode="json", by_alias=True, exclude={"context_receipt_sha256"})
        if canonical_sha256(value) != self.context_receipt_sha256:
            raise ValueError("Native context digest differs from its contents")
        return self


def validate_work_context(context, provenance, *, play_context_receipt=None):
    """Join frozen records through their work owners; this grants no read access.

    Admission must additionally resolve the actual work and submitted intent.
    Read authorization must additionally require the actual running Turn, frozen
    execution policy and acknowledged producing SDK decision.
    """
    from . import types as t
    if type(context) is not SurfaceNativeContextReceiptV1 or type(provenance) is not t.TurnProvenance:
        raise ValueError("Native work binding requires its concrete context and provenance")
    # Revalidate nested mutable work models and the complete root commitment.
    context = SurfaceNativeContextReceiptV1.model_validate_json(context.model_dump_json(by_alias=True))
    provenance = t.TurnProvenance.model_validate_json(provenance.model_dump_json(by_alias=True))
    work = context.work_context
    if (canonical_sha256(provenance) != context.provenance_sha256
        or provenance.world_id != work_world_id(work)
        or provenance.surface_resolution != "resolved"
        or provenance.surface_id != work.surface_id or not provenance.surface_instance_id
        or provenance.selected_object.resolution != "absent"):
        raise ValueError("Native context differs from its actual work provenance")
    if isinstance(work, PlayWorkContextV1):
        if type(play_context_receipt) is not t.PlayRunTurnContextReceiptV2 or play_context_receipt != work.play_basis:
            raise ValueError("Native Play context differs from the exact retained Run snapshot")
        t.validate_play_context_receipt(work.play_basis, provenance.world_id, provenance)
    elif play_context_receipt is not None:
        raise ValueError("Non-Play native work cannot acquire a Run context")
    elif isinstance(work, PlanWorkContextV1):
        from .plan_source_context import validate_source_provenance
        validate_source_provenance(work, provenance)
    elif isinstance(work, BuildWorkContextV1):
        from .build_world_context import validate_work_provenance
        validate_work_provenance(work.source_basis, provenance)
    else:
        raise ValueError("Unknown native surface work owner")
    return context
