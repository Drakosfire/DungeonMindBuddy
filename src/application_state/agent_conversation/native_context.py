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
from .build_source_free import BuildSourceObservationV1, BuildConversationObservationV1
from .native_plan_assertions import NativePlanQueryV2, NativeGraphQueryV3, NativeGraphQueryV4
from .native_plan_statements import NativePlanQueryAuthorityV1, NativePlanQueryUnavailableV1
from .native_statement_input import Strict
from .rules_authority_types import canonical_sha256
from .types import (
    BuildSourceContextBasisV1, NativeCorpusUnavailableV1, PlanAskContextBasis,
    PlanContextPolicyV2, PlanPlayableTargetReceiptV1, PlanWorldGraphHistoryPinV1,
    PlayRunTurnContextReceiptV2, PlaySourceManifestV1,
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
    play_sources: PlaySourceManifestV1
    play_source_frame_sha256: Digest


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
    context_window_limit: int | None = Field(gt=0, strict=True)
    included_history: tuple[PlanWorldGraphHistoryPinV1, ...]
    assembled_input_sha256: Digest

    @model_validator(mode="after")
    def actual_allowance(self):
        if self.context_window_limit is not None and self.provider_envelope_input_tokens + self.output_token_reserve > self.context_window_limit:
            raise ValueError("Actual native provider input exceeds its context allowance")
        if len({pin.turn_id for pin in self.included_history}) != len(self.included_history):
            raise ValueError("Native initial context contains duplicate history turns")
        return self


class NativeBuildProviderInputV2(NativeProviderInputV1):
    """Fresh Build routing presentation; all control metadata stays host-side."""
    assembler_version: Literal["native_build_semantic_initial_v2"] = "native_build_semantic_initial_v2"


class NativeBuildPendingProviderInputV3(NativeProviderInputV1):
    """Initial Build input before any native revision/catalog verification."""
    assembler_version: Literal["native_build_pending_initial_v3"] = "native_build_pending_initial_v3"


class NativeReviewedActionInputV1(Strict):
    """Model-free author admission; its owning review still must be verified."""
    assembler_version: Literal["reviewed_author_admission_v1"] = "reviewed_author_admission_v1"
    submitted_intent_sha256: Digest
    assembled_input_sha256: Digest


class NativePlanRequestAdmissionV1(Strict):
    """Actual request admission before any provider input has been prepared.

    The manifest is request authority, never a substitute SDK envelope or a
    measured token count. Every later provider keeps its real dispatch proof.
    """
    assembler_version: Literal['native_plan_request_admission_v1'] = 'native_plan_request_admission_v1'
    manifest_sha256: Digest
    submitted_intent_sha256: Digest
    dialogue_sha256: Digest
    tokenizer_name: str = Field(min_length=1)
    tokenizer_version: str = Field(min_length=1)
    context_window_limit: int | None = Field(gt=0, strict=True)
    output_token_reserve: int = Field(ge=0, strict=True)

    @model_validator(mode='after')
    def coherent_request_allowance(self):
        if self.context_window_limit is not None and self.output_token_reserve > self.context_window_limit:
            raise ValueError('Plan request reserve exceeds its configured context allowance')
        return self


NativeInitialInput = Annotated[
    NativeProviderInputV1 | NativeBuildProviderInputV2 | NativeReviewedActionInputV1 | NativePlanRequestAdmissionV1,
    Field(discriminator="assembler_version"),
]


class NativePlanGraphQueryPendingV1(Strict):
    """Plan-only frozen Graph authority; no query or evidence has been acquired."""
    schema_: Literal["dmb_native_plan_graph_query_pending_v1"] = Field(
        default="dmb_native_plan_graph_query_pending_v1", alias="schema")
    authority: NativePlanQueryAuthorityV1
    question: str = Field(min_length=1)


class NativeBuildQueryPendingV1(Strict):
    """Pinned Graph inputs for a fresh Build decision before catalog assembly."""
    schema_: Literal["dmb_native_build_query_pending_v1"] = Field(
        default="dmb_native_build_query_pending_v1", alias="schema")
    authority: NativePlanQueryAuthorityV1
    question: str = Field(min_length=1)


class NativeBuildSelectedSourceQueryPendingV1(Strict):
    """A deferred Graph query bound to an exact, source-only author selection.

    This is a commitment to the input, not permission to read it or a claim that
    the Graph or selected source is available. The execution owner must join the
    digest to the submitted selection before any evidence can be used.
    """
    schema_: Literal['dmb_native_build_selected_source_query_pending_v1'] = Field(
        default='dmb_native_build_selected_source_query_pending_v1', alias='schema')
    authority: NativePlanQueryAuthorityV1
    question: str = Field(min_length=1)
    selected_references_sha256: Digest


class SurfaceNativeContextReceiptV1(Strict):
    schema_: Literal["dmb_surface_native_context_receipt_v1"] = Field(
        default="dmb_surface_native_context_receipt_v1", alias="schema")
    receipt_serializer_version: Literal["canonical-json-utf8-v1"] = "canonical-json-utf8-v1"
    context_receipt_sha256: Digest
    provenance_sha256: Digest
    work_context: SurfaceWorkContext
    source_authority: NativeCorpusAuthorityV1 | NativeCorpusUnavailableV1
    native_query: NativeGraphQueryV4 | NativeGraphQueryV3 | NativePlanQueryV2 | NativePlanQueryUnavailableV1 | NativeBuildQueryPendingV1 | NativeBuildSelectedSourceQueryPendingV1 | NativePlanGraphQueryPendingV1
    assembled_input: NativeInitialInput

    @model_validator(mode="after")
    def coherent_native_context(self):
        world = work_world_id(self.work_context)
        if isinstance(self.assembled_input, NativeReviewedActionInputV1) and not isinstance(self.work_context, BuildWorkContextV1):
            raise ValueError("Model-free reviewed action admission requires actual Build work")
        if isinstance(self.assembled_input, NativeBuildProviderInputV2) and not isinstance(self.work_context, BuildWorkContextV1):
            raise ValueError("Semantic Build input requires actual Build work")
        if isinstance(self.assembled_input, NativePlanRequestAdmissionV1) and not isinstance(self.work_context, PlanWorkContextV1):
            raise ValueError('Plan request admission requires actual Plan work')
        query = self.native_query
        if isinstance(query, (NativeBuildQueryPendingV1, NativeBuildSelectedSourceQueryPendingV1)) and (
            type(self.work_context) is not BuildWorkContextV1
            or type(self.assembled_input) is not NativeBuildProviderInputV2
            or type(self.source_authority) is not NativeCorpusAuthorityV1
            or query.authority.scope_mode != "world"
            or query.authority.campaign_id is not None
            or query.authority.session_id is not None
        ):
            raise ValueError("Pending Graph query requires pinned ordinary Build authority")
        if isinstance(query, NativePlanGraphQueryPendingV1) and (
            type(self.work_context) is not PlanWorkContextV1
            or type(self.assembled_input) is not NativePlanRequestAdmissionV1
            or type(self.source_authority) is not NativeCorpusAuthorityV1
            or query.authority.scope_mode != 'world'
            or query.authority.campaign_id is not None
            or query.authority.session_id is not None
        ):
            raise ValueError('Pending Plan Graph query requires pinned request-owned Plan authority')
        has_query_pin = isinstance(query, (NativePlanQueryV2, NativeBuildQueryPendingV1, NativeBuildSelectedSourceQueryPendingV1, NativePlanGraphQueryPendingV1))
        authority = query.authority if has_query_pin else query
        if self.source_authority.managed_world_id != world or authority.managed_world_id != world:
            raise ValueError("Native capabilities differ from their actual work World")
        if isinstance(self.source_authority, NativeCorpusAuthorityV1) and has_query_pin:
            if any(getattr(self.source_authority, key) != getattr(authority, key) for key in (
                    "native_world_id", "binding_version", "revision_id", "domain_ref",
                    "profile_ref", "acquisition_epoch")):
                raise ValueError("Native source and query commitments differ")
        value = self.model_dump(mode="json", by_alias=True, exclude={"context_receipt_sha256"})
        if canonical_sha256(value) != self.context_receipt_sha256:
            raise ValueError("Native context digest differs from its contents")
        return self


class BuildPendingContextReceiptV1(Strict):
    """Build observation commitment, deliberately not a native source receipt.

    No source authority, native query, domain/profile or evidence can be supplied
    under this discriminator. A separate settlement must verify actual sources.
    """
    schema_: Literal["dmb_build_pending_context_receipt_v1"] = Field(
        default="dmb_build_pending_context_receipt_v1", alias="schema")
    receipt_serializer_version: Literal["canonical-json-utf8-v1"] = "canonical-json-utf8-v1"
    context_receipt_sha256: Digest
    provenance_sha256: Digest
    work_context: BuildWorkContextV1
    source_observation: BuildSourceObservationV1
    conversation_observation: BuildConversationObservationV1
    assembled_input: NativeBuildPendingProviderInputV3

    @model_validator(mode="after")
    def coherent_pending_build(self):
        if work_world_id(self.work_context) != self.source_observation.managed_world_id:
            raise ValueError("Pending Build observation differs from its actual work World")
        value = self.model_dump(mode="json", by_alias=True,
                                exclude={"context_receipt_sha256"})
        if canonical_sha256(value) != self.context_receipt_sha256:
            raise ValueError("Pending Build context digest differs from its contents")
        return self


def validate_work_context(context, provenance, *, play_context_receipt=None):
    """Join frozen records through their work owners; this grants no read access.

    Admission must additionally resolve the actual work and submitted intent.
    Read authorization must additionally require the actual running Turn, frozen
    execution policy and acknowledged producing SDK decision.
    """
    from . import types as t
    if type(context) is BuildPendingContextReceiptV1 and type(provenance) is t.TurnProvenance:
        context = BuildPendingContextReceiptV1.model_validate_json(context.model_dump_json(by_alias=True))
        provenance = t.TurnProvenance.model_validate_json(provenance.model_dump_json(by_alias=True))
        return _join_work_context(context, provenance, play_context_receipt=play_context_receipt)
    if type(context) is not SurfaceNativeContextReceiptV1 or type(provenance) is not t.TurnProvenance:
        raise ValueError("Native work binding requires its concrete context and provenance")
    # Revalidate nested mutable work models and the complete root commitment.
    context = SurfaceNativeContextReceiptV1.model_validate(context.model_dump(mode="python", by_alias=True))
    provenance = t.TurnProvenance.model_validate(provenance.model_dump(mode="python", by_alias=True))
    return _join_work_context(context, provenance, play_context_receipt=play_context_receipt)


def _join_work_context(context, provenance, *, play_context_receipt=None):
    """Join components freshly validated by the calling construction owner."""
    from . import types as t
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


def is_semantic_build_input(receipt):
    """Dispatch only the exact fresh Build input codec; never infer from text."""
    return (type(receipt) is SurfaceNativeContextReceiptV1
        and type(receipt.assembled_input) is NativeBuildProviderInputV2
        or type(receipt) is BuildPendingContextReceiptV1
        and type(receipt.assembled_input) is NativeBuildPendingProviderInputV3)
