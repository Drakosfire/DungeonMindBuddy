"""One native execution component, with closed surface-owned work commitments.

APP admits the exact shared request/work envelope. Producing SDK proof, completion
and consumer cutover remain mandatory activation gates. These structural models
and binding checks do not grant reads, reserve writes or accept grounded answers.
"""
from __future__ import annotations

from typing import Annotated, Literal
from uuid import UUID

from pydantic import ConfigDict, Field, model_validator

from application_state.build_proposal.types import BuildWriteCapability
from . import types as t
from .build_intentional_response import Capabilities, MENU_DIGEST, RESOLVER_DIGEST
from .build_related_pages import PagePointer
from .native_context import (
    SurfaceNativeContextReceiptV1, BuildWorkContextV1, PlanWorkContextV1,
    PlayWorkContextV1, NativeProviderInputV1, NativeReviewedActionInputV1, work_world_id,
)
from .native_statement_input import Strict
from .plan_authoring import PlanAuthoringCaptureV1
from .plan_placement import PlanPlacementCatalogV1

Digest = Annotated[str, Field(pattern=r"^[a-f0-9]{64}$", strict=True)]


class NativeBuildActionV1(Strict):
    model_config = ConfigDict(extra="forbid", frozen=True, populate_by_name=True, strict=True)
    surface_id: Literal["build"] = "build"
    intent: Annotated[t.BuildGraphIntentV2 | t.BuildGraphIntentV1, Field(discriminator="schema_")]
    write_capability: BuildWriteCapability | None
    capabilities: Capabilities
    related_page_catalog: tuple[PagePointer, ...] | None
    saved_source_char_count: int = Field(ge=0, strict=True)
    requested_work_menu_sha256: Digest
    response_resolver_sha256: Digest

    @model_validator(mode="after")
    def captured_work(self):
        if (self.requested_work_menu_sha256 != MENU_DIGEST
                or self.response_resolver_sha256 != RESOLVER_DIGEST):
            raise ValueError("Unknown frozen Build semantic menu or resolver")
        cap = self.write_capability
        # Match the existing owner hash recipe, including its default field names.
        expected = None if cap is None else t.canonical_sha256(cap.model_dump(mode="json"))
        if self.intent.build_write_capability_sha256 != expected:
            raise ValueError("Captured editor capability differs from the submitted commitment")
        if ("propose_build_insertion" in self.capabilities.operations) != (cap is not None):
            raise ValueError("Offered writing differs from the captured editor capability")
        if "prepare_build_image" in self.capabilities.operations and cap is None:
            raise ValueError("Offered image preparation requires the captured editor capability")
        if cap is not None:
            from .build_world_context import validate_work_intent
            validate_work_intent(cap.basis, self.intent)
        catalog = self.related_page_catalog
        if catalog is not None and (len({row.document_id for row in catalog}) != len(catalog)
                or any(row.world_id != self.intent.world_id
                    or str(row.document_id) == str(self.intent.primary_work.object_id) for row in catalog)):
            raise ValueError("Related page catalog differs from the actual work World")
        return self


class NativePlanActionV1(Strict):
    surface_id: Literal["plan"] = "plan"
    intent: t.SubmittedTurnIntentV2
    authoring_capture: PlanAuthoringCaptureV1 | None
    placement_catalog: PlanPlacementCatalogV1 | None

    @model_validator(mode="after")
    def captured_work(self):
        if not isinstance(self.intent.plan_context_policy, t.PlanContextPolicyV2):
            raise ValueError("Shared native Plan work requires its current explicit policy")
        capture, catalog = self.authoring_capture, self.placement_catalog
        if ((None if capture is None else capture.sha256) != self.intent.plan_authoring_capture_sha256
                or (None if catalog is None else catalog.sha256) != self.intent.plan_placement_catalog_sha256
                or (capture is None) != (catalog is None)):
            raise ValueError("Plan capture/catalog differs from the submitted commitments")
        if capture is not None:
            if capture.world_id != self.intent.world_id or capture.document_id != self.intent.primary_work.object_id:
                raise ValueError("Plan authoring capture belongs to different work")
            catalog.require_original(capture)
        return self


class NativePlayActionV1(Strict):
    surface_id: Literal["play"] = "play"
    intent: t.PlayGraphIntentV1


NativeAction = Annotated[
    NativeBuildActionV1 | NativePlanActionV1 | NativePlayActionV1,
    Field(discriminator="surface_id"),
]


class SurfaceNativeExecutionPolicyV1(Strict):
    policy_version: Literal["surface_native_execution_v1"] = "surface_native_execution_v1"
    action: NativeAction
    source_authority_sha256: Digest
    native_query_sha256: Digest
    provider_roles: t.GraphControllerWriterRolesV1 | t.GraphProviderRoleTargetV1
    provider_input_accounting: t.GraphExecutionAccountingV1
    max_provider_attempts: int | None = Field(ge=1, strict=True)
    max_total_provider_input_tokens: int | None = Field(ge=1, strict=True)
    max_total_provider_output_tokens: int | None = Field(ge=1, strict=True)
    controller_continuation_accounting: t.BuildControllerContinuationAccountingV3 | None
    writer_context_budget: t.BuildWriterContextBudgetV1 | None

    @model_validator(mode="after")
    def exact_roles(self):
        roles, action = self.provider_roles, self.action
        if isinstance(action, NativePlayActionV1):
            if not isinstance(roles, t.GraphProviderRoleTargetV1):
                raise ValueError("Play requires its actual single-provider policy, not manufactured roles")
            if any(limit is None for limit in (self.max_provider_attempts,
                    self.max_total_provider_input_tokens, self.max_total_provider_output_tokens)):
                raise ValueError("Play retains its finite accepted provider allowance")
        elif not isinstance(roles, t.GraphControllerWriterRolesV1):
            raise ValueError("Build and Plan require their actual controller/writer roles")
        if isinstance(action, NativeBuildActionV1):
            if (roles.controller.identity() != ("typesafe", "jev-1.14.0", "typesafe_decision")
                    or self.controller_continuation_accounting is None or self.writer_context_budget is None
                    or roles.writer.identity() != self.writer_context_budget.identity()):
                raise ValueError("Native Build role/accounting differs from its actual owner contracts")
        elif self.controller_continuation_accounting is not None or self.writer_context_budget is not None:
            raise ValueError("Build role accounting cannot authorize another action family")
        if isinstance(action, NativePlanActionV1) and roles.controller.identity() != ("typesafe", "jev-1.14.0", "decision"):
            raise ValueError("Plan requires its exact decision controller")
        return self


class NativeWriterAuthorizedV1(t.ProviderAttemptAuthorizedEventV3):
    """One native producing frame and exact read set for every new surface.

    When recorded, its response_sha256 commits the selected assistant text UTF8,
    not the enclosing SDK HTTP response object.
    """
    kind: Literal["native_writer_authorized_v1"] = "native_writer_authorized_v1"
    frame_sha256: Digest
    native_read_event_ids: tuple[UUID, ...]

    @model_validator(mode="after")
    def exact_read_ids(self):
        if self.native_read_event_ids != tuple(sorted(set(self.native_read_event_ids), key=str)):
            raise ValueError("Native writer read IDs must be sorted and unique")
        return self


# Current owner event codecs are reused. Classic Graph operations/scopes and
# source-anchor receipts deliberately have no branch in this native event union.
SurfaceNativeEvent = Annotated[
    t.ProviderAttemptAuthorizedEventV3 | t.ProviderAttemptAuthorizedEventV5
    | t.PlanJevProviderAuthorizedV1 | t.PlanRequestedWorkAuthorizedV2
    | NativeWriterAuthorizedV1 | t.ProviderOutcomeEventV1 | t.CompletionBindingEventV1
    | t.PlanJevRetrievalSelectionV1 | t.PlanRequestedWorkSelectedV2
    | t.NativeBodySearchAuthorizedV1 | t.NativeBodySearchObservedV1
    | t.NativeBodyReadAuthorizedV1 | t.NativeBodyReadObservedV1
    | t.NativePlanStatementReadAuthorizedV1 | t.NativePlanStatementReadObservedV1
    | t.NativePlanAssertionReadAuthorizedV1 | t.NativePlanAssertionReadObservedV1
    | t.BuildDraftContextCapturedV1 | t.BuildDraftProviderInclusionV1
    | t.BuildSectionReadAuthorizationV1 | t.ValidatedBuildSectionReadV1
    | t.BuildSectionProviderInclusionV1
    | t.BuildRequestedWorkResolutionV1 | t.BuildReviewedActionSelectionV2 | t.BuildReviewedActionSelectionV1
    | t.BuildWriterEvidenceSelectionV1 | t.BuildPlanOutputContractV2
    | t.RelatedPagesSelection | t.RelatedPageRead | t.RelatedPageInclusion
    | t.BuildAuthoredReferencesCapturedV1 | t.BuildAuthoredReferenceAuthorizedV1
    | t.BuildAuthoredReferenceReadV1 | t.BuildAuthoredProviderInclusionV1,
    Field(discriminator="kind"),
]


_BUILD_WORK_EVENTS = (
    t.BuildDraftContextCapturedV1, t.BuildDraftProviderInclusionV1,
    t.BuildSectionReadAuthorizationV1, t.ValidatedBuildSectionReadV1,
    t.BuildSectionProviderInclusionV1,
    t.BuildRequestedWorkResolutionV1, t.BuildReviewedActionSelectionV1,
    t.BuildWriterEvidenceSelectionV1, t.BuildPlanOutputContractV2,
    t.RelatedPagesSelection, t.RelatedPageRead, t.RelatedPageInclusion,
    t.BuildAuthoredReferencesCapturedV1, t.BuildAuthoredReferenceAuthorizedV1,
    t.BuildAuthoredReferenceReadV1, t.BuildAuthoredProviderInclusionV1,
)
_PLAN_WORK_EVENTS = (t.PlanRequestedWorkAuthorizedV2, t.PlanRequestedWorkSelectedV2)


class SurfaceNativeExecutionV1(Strict):
    schema_: Literal["dmb_surface_native_execution_v1"] = Field(default="dmb_surface_native_execution_v1", alias="schema")
    context_receipt_sha256: Digest
    execution_policy_sha256: Digest
    policy: SurfaceNativeExecutionPolicyV1
    events: list[SurfaceNativeEvent] = Field(max_length=2048)

    @model_validator(mode="after")
    def actual_records(self):
        # Recheck mutable owner models before trusting their frozen commitment.
        SurfaceNativeExecutionPolicyV1.model_validate_json(self.policy.model_dump_json(by_alias=True))
        expected = t.canonical_sha256(dict(schema=self.schema_,
            context_receipt_sha256=self.context_receipt_sha256,
            policy=self.policy.model_dump(mode="json", by_alias=True)))
        if self.execution_policy_sha256 != expected:
            raise ValueError("Native execution policy differs from its frozen commitment")
        t.validate_provider_execution(self)
        roles = self.policy.provider_roles
        for event in self.events:
            if isinstance(event,t.ProviderOutcomeEventV1) and event.outcome=='response_received':
                producer=next(e for e in self.events[:event.sequence]
                    if isinstance(e,t.ProviderAttemptAuthorizedEventV1) and e.provider_attempt_id==event.provider_attempt_id)
                if type(producer) is NativeWriterAuthorizedV1 and (not event.request_id or not event.response_sha256):
                    raise ValueError('Shared native writer response requires its exact selected output acknowledgement')
            if isinstance(event, _BUILD_WORK_EVENTS) and not isinstance(self.policy.action, NativeBuildActionV1):
                raise ValueError("Build work event cannot acquire another action family")
            if isinstance(event, _PLAN_WORK_EVENTS) and not isinstance(self.policy.action, NativePlanActionV1):
                raise ValueError("Plan work event cannot acquire another action family")
            if isinstance(event, t.ProviderAttemptAuthorizedEventV1):
                identity = event.provider, event.model, event.api_mode
                if type(event) is NativeWriterAuthorizedV1:
                    writer_role = roles.writer if isinstance(roles, t.GraphControllerWriterRolesV1) else roles
                    if identity != writer_role.identity():
                        raise ValueError("Shared native inclusion belongs only to its exact writer role")
                    reads = tuple(sorted((prior.event_id for prior in self.events[:event.sequence]
                        if isinstance(prior, (t.NativePlanStatementReadObservedV1,
                            t.NativePlanAssertionReadObservedV1, t.NativeBodyReadObservedV1))), key=str))
                    if event.native_read_event_ids != reads:
                        raise ValueError("Native writer changed its exact settled read inclusion set")
                    if isinstance(self.policy.action,NativeBuildActionV1) and any(isinstance(prior,
                            (t.BuildSectionReadAuthorizationV1,t.ValidatedBuildSectionReadV1,t.BuildWriterEvidenceSelectionV1))
                            for prior in self.events[:event.sequence]):
                        from .build_primary_context import validate_writer_reads
                        validate_writer_reads(self,event)
                if isinstance(roles, t.GraphControllerWriterRolesV1):
                    if identity == roles.writer.identity() and type(event) is not NativeWriterAuthorizedV1:
                        raise ValueError("Native writer requires its exact shared selected-read inclusion codec")
                    if (isinstance(self.policy.action, NativePlanActionV1)
                            and identity == roles.controller.identity()
                            and not isinstance(event, t.PlanJevProviderAuthorizedV1)):
                        raise ValueError("Plan controller requires its actual producing decision codec")
                if (event.included_assertion_ids or event.included_relationship_ids
                        or event.included_evidence_ref_ids or event.included_graph_event_ids
                        or event.included_source_read_event_ids
                        or getattr(event, "included_source_reuse_event_ids", ())):
                    raise ValueError("Native provider cannot acquire absent classic Graph evidence")
                if isinstance(roles, t.GraphProviderRoleTargetV1) and (event.provider, event.model, event.api_mode) != roles.identity():
                    raise ValueError("Provider differs from its frozen single-provider identity")
        if isinstance(self.policy.action,NativeBuildActionV1):
            from .build_intentional_response import validate_native_action_events
            validate_native_action_events(self)
            from .plan_objective import validate_events as validate_plan_output_events
            validate_plan_output_events(self)
            from .build_draft_context import validate_execution_records, validate_provider_inclusions
            from .build_primary_context import validate_reads, validate_selection_origin
            validate_execution_records(self)
            validate_provider_inclusions(self)
            validate_reads(self,max_chars=self.policy.action.saved_source_char_count)
            from .build_related_pages import validate_events as validate_related_events
            validate_related_events(self)
            t.validate_build_section_inclusions(self)
            for event in self.events:
                if isinstance(event,t.BuildWriterEvidenceSelectionV1):
                    validate_selection_origin(self,event)
                    if event.source_event_ids:
                        raise ValueError('Native World evidence cannot acquire a second classic source inclusion set')
        if isinstance(roles, t.GraphControllerWriterRolesV1):
            reviewed = [event for event in self.events if isinstance(event, t.BuildReviewedActionSelectionV1)]
            if reviewed:
                if (not isinstance(self.policy.action, NativeBuildActionV1) or len(reviewed) != 1
                        or reviewed[0].intent != self.policy.action.intent):
                    raise ValueError("Reviewed action differs from the actual native action commitment")
                # The submission/selection/reservation owners must additionally
                # validate this stored reviewed step before granting any write.
            t.validate_controller_writer_execution(self, reviewed_action=reviewed[0] if reviewed else None)
            if isinstance(self.policy.action, NativePlanActionV1):
                from .plan_jev_decision import validate_decision_phases
                validate_decision_phases(self)
            from .native_corpus import validate_native_body_events
            validate_native_body_events(self)
        elif any(isinstance(event, t.NATIVE_BODY_EVENTS) for event in self.events):
            raise ValueError("Single-provider native body acquisition awaits its actual SDK selection proof")
        if len(self.model_dump_json(by_alias=True).encode()) > 1_048_576:
            raise ValueError("Native execution exceeds the existing ledger storage bound")
        return self


def validate_context_binding(context, execution):
    """Join components through real work and native record owners; grants no IO."""
    if type(context) is not SurfaceNativeContextReceiptV1 or type(execution) is not SurfaceNativeExecutionV1:
        raise ValueError("Native execution requires its concrete shared context")
    context = SurfaceNativeContextReceiptV1.model_validate_json(context.model_dump_json(by_alias=True))
    execution = SurfaceNativeExecutionV1.model_validate_json(execution.model_dump_json(by_alias=True))
    action, work = execution.policy.action, context.work_context
    if (action.surface_id != work.surface_id or action.intent.world_id != work_world_id(work)
            or execution.context_receipt_sha256 != context.context_receipt_sha256
            or execution.policy.source_authority_sha256 != t.canonical_sha256(context.source_authority)
            or execution.policy.native_query_sha256 != t.canonical_sha256(context.native_query)):
        raise ValueError("Native action, work and authority commitments differ")
    if isinstance(work, BuildWorkContextV1):
        from .build_world_context import validate_work_intent
        validate_work_intent(work.source_basis, action.intent)
        for event in execution.events:
            if isinstance(event,t.BuildDraftContextCapturedV1) and event.record.snapshot.saved_basis() != work.source_basis.model_dump(mode='json',by_alias=True):
                raise ValueError('Working draft differs from its frozen Build source basis')
            if isinstance(event,(t.BuildSectionReadAuthorizationV1,t.ValidatedBuildSectionReadV1)) and event.source_basis != work.source_basis:
                raise ValueError('Saved section differs from its frozen Build source authority')

    elif isinstance(work, PlanWorkContextV1):
        from .plan_source_context import validate_work_intent
        validate_work_intent(work, action.intent)
    elif isinstance(work, PlayWorkContextV1):
        from .play_graph_context import validate_work_intent
        validate_work_intent(work.play_basis, action.intent)
    assembled = context.assembled_input
    if isinstance(assembled, NativeReviewedActionInputV1):
        from .reviewed_action import admission_manifest, digest
        if (not isinstance(action, NativeBuildActionV1) or action.intent.reviewed_step is None
                or assembled.submitted_intent_sha256 != t.canonical_sha256(action.intent)
                or assembled.assembled_input_sha256 != digest(admission_manifest(action.intent))):
            raise ValueError("Native reviewed admission differs from the actual author intent")
    elif isinstance(assembled, NativeProviderInputV1):
        if isinstance(action, NativeBuildActionV1) and action.intent.reviewed_step is not None:
            raise ValueError("Native reviewed action requires its model-free admission")
        for index, event in enumerate(execution.events):
            if isinstance(event, t.ProviderAttemptAuthorizedEventV1):
                t.validate_provider_envelope_accounting(assembled,
                    execution.model_copy(update={"events": execution.events[:index]}), event)
    query = context.native_query
    if isinstance(query, t.NativePlanQueryV2):
        request = action.intent.graph_request
        if query.question != action.intent.message or query.authority.scope_mode != "world":
            raise ValueError("Native query differs from the unchanged submitted World question")
        if request.revision_pin is not None and request.revision_pin != query.authority.revision_id:
            raise ValueError("Native query cannot replace an explicitly requested revision")
    from .native_plan_statements import validate_selected_record_events
    validate_selected_record_events(query, execution)


def validate_submission(submission):
    """Join new native admission to the actual request, before any APP mutation."""
    receipt, execution = submission.graph_context_receipt, submission.graph_context_execution
    validate_context_binding(receipt, execution)
    from .native_context import validate_work_context
    validate_work_context(receipt, submission.provenance,
        play_context_receipt=submission.play_context_receipt)
    intent = execution.policy.action.intent
    if (submission.submitted_intent_v1 is not None
            or submission.submitted_intent_v2 != intent or execution.events
            or intent.world_id != submission.world_id or intent.message != submission.user_text
            or intent.surface_instance_id != submission.provenance.surface_instance_id):
        raise ValueError("Shared native admission requires its exact request and empty execution")
    binding = getattr(intent, 'reviewed_step', None)
    if binding is not None and binding.reference.conversation_id != submission.conversation_id:
        raise ValueError("Reviewed native action belongs to a different conversation")
    capture = getattr(execution.policy.action, 'authoring_capture', None)
    if capture is not None and capture.conversation_id != submission.conversation_id:
        raise ValueError("Native Plan capture belongs to a different conversation")


def validate_turn_fields(receipt, execution, provenance, intent_fingerprint, completion, assistant_text):
    """Read structural commitments without treating them as producer acceptance."""
    validate_context_binding(receipt, execution)
    if (t.canonical_sha256(provenance) != receipt.provenance_sha256
            or t.submitted_turn_intent_fingerprint_v2(execution.policy.action.intent) != intent_fingerprint):
        raise ValueError("Stored shared native request or provenance differs from admission")
    bindings=[event for event in execution.events if isinstance(event,t.CompletionBindingEventV1)]
    if completion is None:
        if assistant_text is not None or bindings:
            raise ValueError('Shared native text requires its typed completion and binding')
        return
    if (len(bindings)!=1 or assistant_text!='\n'.join(s.text for s in completion.answer_segments)):
        raise ValueError('Shared native completion requires exact retained text and binding')
    from .native_completion import validate_retained_completion
    validate_retained_completion(completion,receipt,execution,bindings[0].provider_attempt_id,bindings[0].claim_graph_event_ids)


def validate_turn_identity(turn):
    """Bind stored work to real Turn identity; no manufactured submission/Turn."""
    validate_request_identity(turn.graph_context_receipt,turn.graph_context_execution,turn)
    if ((turn.status=='completed' and (turn.completion is None or turn.completed_at is None))
            or (turn.status!='completed' and turn.completion is not None)
            or (turn.status in {'accepted','running'} and turn.completed_at is not None)):
        raise ValueError('Stored shared native lifecycle differs from admission')


def validate_request_identity(receipt, execution, envelope):
    """One request/work join for ordinary and unclaimed completed read owners."""
    if type(receipt) is not SurfaceNativeContextReceiptV1 or type(execution) is not SurfaceNativeExecutionV1:
        raise ValueError('Stored shared native Turn requires its concrete context and execution')
    from .native_context import validate_work_context
    validate_work_context(receipt,envelope.provenance,play_context_receipt=envelope.play_context_receipt)
    action=execution.policy.action
    intent=action.intent
    if (envelope.submitted_intent_fingerprint_v1 is not None
            or t.submitted_turn_intent_fingerprint_v2(intent)!=envelope.submitted_intent_fingerprint_v2
            or envelope.world_id!=intent.world_id or envelope.user_text!=intent.message
            or envelope.provenance.surface_instance_id!=intent.surface_instance_id):
        raise ValueError('Stored shared native request differs from admission')
    binding=getattr(intent,'reviewed_step',None)
    if binding is not None and binding.reference.conversation_id!=envelope.conversation_id:
        raise ValueError('Reviewed native action belongs to a different conversation')
    capture=getattr(action,'authoring_capture',None)
    if capture is not None and capture.conversation_id!=envelope.conversation_id:
        raise ValueError('Native Plan capture belongs to a different conversation')
