"""One native execution component, with closed surface-owned work commitments.

APP admits the exact shared request/work envelope. Producing SDK proof, completion
and consumer cutover remain mandatory activation gates. These structural models
and binding checks do not grant reads, reserve writes or accept grounded answers.
"""
from __future__ import annotations

from typing import Annotated, Literal
from uuid import UUID

from pydantic import ConfigDict, Discriminator, Tag, Field, ValidationInfo, field_validator, model_validator

from application_state.build_proposal.types import BuildWriteCapability
from . import types as t
from .build_intentional_response import Capabilities, known_semantics
from .build_related_pages import PagePointer
from .build_saved_statblock import BuildSavedStatblockReadV1, validate_read as validate_saved_statblock_read
from .native_context import (
    SurfaceNativeContextReceiptV1, NativeBuildQueryPendingV1, BuildWorkContextV1, PlanWorkContextV1,
    PlayWorkContextV1, NativeProviderInputV1, NativeReviewedActionInputV1, NativePlanRequestAdmissionV1, work_world_id,
)
from .native_statement_input import Strict
from .native_corpus import prior_conversation_work
from .plan_authoring import PlanAuthoringComposedSnapshotV1, PlanAuthoringOpeningCapture
from .plan_composed_targeting import ComposedColumn, ComposedPlanNominationV1, ComposedPlanPlacementCatalogV1
from .plan_placement import PlanPlacementCatalog

from .native_retrieval import (
    NativePlanAuthorScopeAuthorizedV1, NativePlanOpeningAuthorizedV1, NativeReadBatchConcludedV1,
    NativeRetrievalAuthorizedV1, NativeRetrievalSelectedV1, NativeRetrievalSelectedV2,
)
from .native_plan_opening import (
    NativePlanAuthorScopeObservedV1, NativePlanOpeningScopeBindingV1, bind_opening_author_scope,
    resolve_composed_opening,
)
from .authored_graph_references import BuildAuthoredReferenceAuthorizedV2, BuildAuthoredReferenceReadV2, BuildAuthoredReferenceReadV3
from .native_plan_assertions import NativeGraphQueryV4, NativePlanAssertionReadObservedV2

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

    @field_validator("capabilities", mode="before")
    @classmethod
    def reconstruct_capabilities(cls, value, info: ValidationInfo):
        # Reconstruct through the existing validating owner. Only JSON arrays
        # become tuples; Python callers must supply the strict tuple form.
        if isinstance(value, dict):
            data = dict(value)
            if info.mode == "json":
                for name in ("operations", "reviews"):
                    if isinstance(data.get(name), list):
                        data[name] = tuple(data[name])
            try:
                return Capabilities(**data)
            except (TypeError, ValueError) as exc:
                raise ValueError(str(exc)) from exc
        return value

    @model_validator(mode="after")
    def captured_work(self):
        if not known_semantics(self.requested_work_menu_sha256, self.response_resolver_sha256):
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
    intent: Annotated[t.SubmittedTurnIntentV4 | t.SubmittedTurnIntentV3 | t.SubmittedTurnIntentV2, Field(discriminator="schema_")]
    authoring_capture: PlanAuthoringOpeningCapture | None
    placement_catalog: PlanPlacementCatalog | None

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
            if type(capture) is PlanAuthoringComposedSnapshotV1 and type(self) is not NativePlanActionV3:
                raise ValueError("Composed capture requires contextual Plan admission")
            if capture.world_id != self.intent.world_id or capture.document_id != self.intent.primary_work.object_id:
                raise ValueError("Plan authoring capture belongs to different work")
            catalog.require_original(capture)
        return self


class NativePlayActionV1(Strict):
    surface_id: Literal["play"] = "play"
    intent: t.PlayGraphIntentV1


class NativePlanActionV2(NativePlanActionV1):
    """Current Plan freezes the same saved-page capability used by Build."""
    action_version: Literal['plan_saved_authored_pages_v2'] = 'plan_saved_authored_pages_v2'
    related_page_catalog: tuple[PagePointer, ...]

    @field_validator("related_page_catalog", mode="before")
    @classmethod
    def catalog_tuple(cls, value):
        return tuple(value) if isinstance(value, list) else value

    @model_validator(mode="after")
    def saved_pages(self):
        rows = self.related_page_catalog
        if (len({p.document_id for p in rows}) != len(rows)
                or any(p.world_id != self.intent.world_id
                    or str(p.document_id) == str(self.intent.primary_work.object_id) for p in rows)):
            raise ValueError("Related Plan pages differ from the actual work World")
        return self


class NativePlanActionV3(NativePlanActionV2):
    """Current Plan resolves a complete semantic target set before writing."""
    action_version: Literal['plan_contextual_targets_v3'] = 'plan_contextual_targets_v3'
    # Frozen Content metadata at plan_basis, never an inferred editor heading.
    # None supports source-only fixtures; it cannot bind a document-title ref.
    document_title: str | None = None

    @model_validator(mode="after")
    def contextual_catalog(self):
        from .plan_placement import PlanPlacementCatalogV2
        if type(self.placement_catalog) is ComposedPlanPlacementCatalogV1:
            if type(self.authoring_capture) is not PlanAuthoringComposedSnapshotV1:
                raise ValueError("Composed Plan requires its exact frozen snapshot")
            return self
        if type(self.placement_catalog) is not PlanPlacementCatalogV2 or self.authoring_capture is None:
            raise ValueError("Contextual Plan requires its frozen paragraph catalog and capture")
        if self.authoring_capture.target_kind not in {'insert_at_caret', 'replace_selection'}:
            raise ValueError("Contextual Plan does not broaden Plan Card authoring")
        return self


NATIVE_PLAN_ACTION_TYPES = (NativePlanActionV1, NativePlanActionV2, NativePlanActionV3)


def _action_kind(value):
    if isinstance(value, dict):
        surface = value.get('surface_id')
        if surface == 'plan' and value.get('action_version') == 'plan_contextual_targets_v3':
            return 'plan_contextual_targets'
        return 'plan_saved_pages' if surface == 'plan' and value.get('action_version') == 'plan_saved_authored_pages_v2' else surface
    if type(value) is NativePlanActionV3:
        return 'plan_contextual_targets'
    return 'plan_saved_pages' if type(value) is NativePlanActionV2 else getattr(value, 'surface_id', None)


NativeAction = Annotated[
    Annotated[NativeBuildActionV1, Tag('build')]
    | Annotated[NativePlanActionV1, Tag('plan')]
    | Annotated[NativePlanActionV2, Tag('plan_saved_pages')]
    | Annotated[NativePlanActionV3, Tag('plan_contextual_targets')]
    | Annotated[NativePlayActionV1, Tag('play')],
    Discriminator(_action_kind),
]


class NativeWriterEstimatedBudgetV1(Strict):
    """Current native writer reuses its trusted controller's offline counter."""
    schema_: Literal['dmb_native_writer_estimated_budget_v1'] = Field(alias='schema')
    provider: Literal['openai']
    model: Literal['gpt-6-luna', 'gpt-6.1-sol']
    api_mode: Literal['responses']
    estimator: Literal['o200k_double_plus_4096_adaptive_context_v4']
    tokenizer_version: str = Field(min_length=1, max_length=128)
    context_limit_tokens: Literal[128000] | None = 128000
    output_reserve_tokens: Literal[0, 4096] = 4096

    def identity(self):
        return self.provider, self.model, self.api_mode

    @model_validator(mode='after')
    def complete_allowance(self):
        if (self.context_limit_tokens,self.output_reserve_tokens) not in {(128000,4096),(None,0)}:
            raise ValueError('Native writer requires its complete historical or provider-owned allowance')
        return self


class SurfaceNativeExecutionPolicyV1(Strict):
    policy_version: Literal["surface_native_execution_v1"] = "surface_native_execution_v1"
    action: NativeAction
    source_authority_sha256: Digest
    native_query_sha256: Digest
    provider_roles: t.GraphControllerWriterRolesV1
    provider_input_accounting: t.GraphExecutionAccountingV1
    max_provider_attempts: int | None = Field(ge=1, strict=True)
    max_total_provider_input_tokens: int | None = Field(ge=1, strict=True)
    max_total_provider_output_tokens: int | None = Field(ge=1, strict=True)
    controller_continuation_accounting: t.BuildControllerContinuationAccountingV4 | t.BuildControllerContinuationAccountingV3 | None
    writer_context_budget: t.BuildWriterContextBudgetV1 | NativeWriterEstimatedBudgetV1 | None

    @model_validator(mode="after")
    def exact_roles(self):
        roles, action = self.provider_roles, self.action
        if not isinstance(roles,t.GraphControllerWriterRolesV1):
            raise ValueError('Native surfaces require their actual controller/writer roles')
        if isinstance(action,NativePlayActionV1):
            if roles.controller.identity() != ('typesafe','jev-1.14.0','decision'):
                raise ValueError('Play requires its exact native retrieval controller')
            if any(value is not None for value in (self.max_provider_attempts,
                    self.max_total_provider_input_tokens,self.max_total_provider_output_tokens)):
                raise ValueError('Native Play uses provider-owned request allowances')
        if isinstance(action, NativeBuildActionV1):
            if (roles.controller.identity() != ("typesafe", "jev-1.14.0", "typesafe_decision")
                    or self.controller_continuation_accounting is None or self.writer_context_budget is None
                    or roles.writer.identity() != self.writer_context_budget.identity()):
                raise ValueError("Native Build role/accounting differs from its actual owner contracts")
            if isinstance(self.writer_context_budget, NativeWriterEstimatedBudgetV1):
                counter = self.controller_continuation_accounting
                if (self.writer_context_budget.estimator != counter.policy
                        or self.writer_context_budget.tokenizer_version != counter.tokenizer_version):
                    raise ValueError('Native writer accounting differs from its prepared controller counter')
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


class NativeBuildWriterAuthorizedV2(NativeWriterAuthorizedV1):
    """The existing writer owner commits all Build work, including unused reads."""
    kind: Literal["native_build_writer_authorized_v2"] = "native_build_writer_authorized_v2"
    work_frame_sha256: Digest


NATIVE_WRITER_TYPES = (NativeWriterAuthorizedV1, NativeBuildWriterAuthorizedV2)
NATIVE_WRITER_KINDS = frozenset({'native_writer_authorized_v1', 'native_build_writer_authorized_v2'})


class NativePlanRequestedWorkSelectedV3(t.PlanRequestedWorkSelectedV2):
    """Explicit saved-origin review, with the same retained placement proof."""
    kind: Literal['plan_requested_work_selected_v3'] = 'plan_requested_work_selected_v3'
    requested_work: Literal['discuss', 'clarify', 'write_current_page', 'different_destination', 'review_connected_page']


class NativePlanOpeningSelectedV1(NativePlanRequestedWorkSelectedV3, NativeRetrievalSelectedV2):
    """Atomic actual work and conditionally applicable first-batch votes."""
    kind: Literal['native_plan_opening_selected_v1'] = 'native_plan_opening_selected_v1'
    operation: Literal['select_candidates', 'discover_more', 'finish_retrieval'] | None
    post_read_plan: Literal['review_after_reads', 'finish_if_selected_reads_succeed'] | None

    @model_validator(mode='after')
    def applicable_read_plan(self):
        active = self.requested_work in {'discuss', 'clarify'}
        if active != (self.operation is not None and self.post_read_plan is not None):
            raise ValueError('Opening read plan differs from its actual work branch')
        if not active and (self.operation is not None or self.post_read_plan is not None or self.selected_handles):
            raise ValueError('Inactive opening work cannot authorize a read plan')
        if self.requested_work != 'discuss' and any(h.startswith('saved-authored-page:') for h in self.selected_handles):
            raise ValueError('Opening saved-page votes require actual discussion permission')
        return self


class NativePlanOpeningSelectedV2(NativePlanOpeningSelectedV1):
    """The actual intent and complete candidate set precede target authority."""
    kind: Literal['native_plan_opening_selected_v2'] = 'native_plan_opening_selected_v2'
    requested_intent: Literal['discuss', 'clarify', 'write_current_page', 'different_destination', 'review_connected_page']
    compatible_placement_selectors: tuple[str, ...]
    target_resolution: Literal['not_applicable', 'missing', 'unique', 'ambiguous']
    requested_placement_relation: Literal['captured', 'before_paragraph', 'after_paragraph',
        'before_heading', 'after_heading', 'after_section', 'end_page', 'unresolved']
    compatible_anchor_selectors: tuple[str, ...]
    direct_anchor_selectors: tuple[str, ...]
    compatible_passage_selectors: tuple[str, ...]
    compatible_section_selectors: tuple[str, ...]
    compatible_ancestor_selectors: tuple[str, ...]
    requested_paragraph_scope: Literal['unscoped', 'named', 'unresolved', 'not_applicable']
    requested_scope_qualifier: Literal['none', 'named', 'unresolved']
    author_scope_binding: NativePlanOpeningScopeBindingV1 | None = Field(
        default=None, exclude_if=lambda value: value is None)
    scope_document_title: str | None = Field(default=None, exclude_if=lambda value: value is None)
    source_placement_relation: str | None = Field(default=None, exclude_if=lambda value: value is None)
    scope_description_matches: dict[int, tuple[str, ...]] | None = Field(
        default=None, exclude_if=lambda value: value is None)
    excluded_scope_description_matches: dict[int, tuple[str, ...]] | None = Field(
        default=None, exclude_if=lambda value: value is None)
    locator_passage_selectors: tuple[str, ...] | None = Field(
        default=None, exclude_if=lambda value: value is None)
    literal_paragraph_excerpt: str | None = Field(
        default=None, min_length=1, exclude_if=lambda value: value is None)
    scope_refused: Literal[True] | None = Field(default=None, exclude_if=lambda value: value is None)

    @field_validator('compatible_placement_selectors', 'compatible_anchor_selectors',
        'direct_anchor_selectors', 'compatible_passage_selectors', 'compatible_section_selectors',
        'compatible_ancestor_selectors', 'locator_passage_selectors', mode='before')
    @classmethod
    def selectors_tuple(cls, value):
        return tuple(value) if isinstance(value, list) else value

    @model_validator(mode='after')
    def applicable_read_plan(self):
        # A question is not an evidence answer; V1's clarification reads remain
        # historical. Current question mode uses captured request/page context.
        active = self.requested_work == 'discuss'
        if active != (self.operation is not None and self.post_read_plan is not None):
            raise ValueError('Contextual opening read plan differs from its work')
        if not active and (self.operation is not None or self.post_read_plan is not None or self.selected_handles):
            raise ValueError('Inactive contextual work cannot authorize reads')
        return self

    @model_validator(mode='after')
    def exact_resolution(self):
        from .plan_authoring import PlanAuthoringCaptureV1
        from .plan_placement import decode_plan_placement_catalog
        from .plan_contextual_targets import resolve_author_scope_targets, resolve_component_targets
        if self.original_capture is None or self.placement_catalog is None:
            raise ValueError('Contextual selection requires its original captured catalog')
        capture = PlanAuthoringCaptureV1.model_validate(self.original_capture)
        catalog = decode_plan_placement_catalog(self.placement_catalog)
        if self.author_scope_binding is not None:
            fields = resolve_author_scope_targets(capture, catalog, self.requested_intent,
                self.source_placement_relation, self.author_scope_binding.observation,
                self.direct_anchor_selectors, self.compatible_passage_selectors,
                document_title=self.scope_document_title, description_matches=self.scope_description_matches,
                excluded_description_matches=self.excluded_scope_description_matches,
                locator_passages=self.locator_passage_selectors, literal_excerpt=self.literal_paragraph_excerpt,
                scope_refused=self.scope_refused is True, page_edit_intent=self.author_scope_binding.page_edit_intent)
        else:
            if any(value is not None for value in (self.source_placement_relation, self.scope_document_title,
                    self.scope_description_matches, self.excluded_scope_description_matches,
                    self.locator_passage_selectors, self.literal_paragraph_excerpt, self.scope_refused)):
                raise ValueError('Source relation, title and description matches require retained author scope')
            fields = resolve_component_targets(capture, catalog, self.requested_intent,
                self.requested_placement_relation, self.requested_paragraph_scope,
                self.direct_anchor_selectors, self.compatible_passage_selectors, self.compatible_section_selectors,
                self.requested_scope_qualifier, self.compatible_ancestor_selectors)
        if any(getattr(self, key) != value for key, value in fields.items()):
            raise ValueError('Contextual selection differs from its complete target resolution')
        return self


class NativePlanOpeningSelectedV3(NativePlanOpeningSelectedV1):
    """Retain the independent author interpretation and actual slot nomination."""
    kind: Literal['native_plan_opening_selected_v3'] = 'native_plan_opening_selected_v3'
    author_scope_binding: NativePlanOpeningScopeBindingV1
    author_operation: Literal['discuss', 'write_current_page'] | None
    scope_document_title: str
    composed_nomination: ComposedPlanNominationV1
    target_resolution: Literal['not_applicable', 'missing', 'unique', 'ambiguous', 'unresolved']
    column_scope_version: Literal['v1'] | None = Field(default=None, exclude_if=lambda value: value is None)
    author_column: ComposedColumn | None = Field(
        default=None, exclude_if=lambda value: value is None)

    @model_validator(mode='after')
    def applicable_read_plan(self):
        active = self.requested_work == 'discuss'
        if active != (self.operation is not None and self.post_read_plan is not None):
            raise ValueError('Composed Plan opening read plan differs from its work')
        if not active and (self.operation is not None or self.post_read_plan is not None or self.selected_handles):
            raise ValueError('Inactive composed work cannot authorize reads')
        return self

    @model_validator(mode='after')
    def exact_composed_resolution(self):
        from .plan_authoring import parse_opening_capture
        from .plan_placement import decode_plan_placement_catalog
        capture = parse_opening_capture(self.original_capture)
        catalog = decode_plan_placement_catalog(self.placement_catalog)
        if type(capture) is not PlanAuthoringComposedSnapshotV1 or type(catalog) is not ComposedPlanPlacementCatalogV1:
            raise ValueError('Composed opening requires its exact snapshot and catalog')
        if self.author_column is not None and self.column_scope_version != 'v1':
            raise ValueError('Composed column scope requires its retained interpretation version')
        expected = resolve_composed_opening(capture, catalog, self.author_scope_binding,
            self.composed_nomination, self.author_operation, author_column=self.author_column)
        if any(getattr(self, key) != value for key, value in expected.items()):
            raise ValueError('Composed opening differs from its complete target resolution')
        return self


NATIVE_PLAN_OPENING_SELECTION_TYPES = (
    NativePlanOpeningSelectedV1, NativePlanOpeningSelectedV2, NativePlanOpeningSelectedV3,
)
NATIVE_PLAN_WORK_SELECTION_TYPES = (NativePlanRequestedWorkSelectedV3, *NATIVE_PLAN_OPENING_SELECTION_TYPES)


def native_read_event_ids(events):
    """One inclusion inventory for the current native writer."""
    return tuple(sorted((event.event_id for event in events if isinstance(event, (
        t.NativePlanStatementReadObservedV1, t.NativePlanAssertionReadObservedV1,
        t.NativeBodyReadObservedV1, t.NativeAuthoredSourceReadV1, BuildAuthoredReferenceReadV2,
        t.BuildPriorBodyEvidenceAdmittedV1))), key=str))


class NativeBuildQuerySettledV1(Strict):
    kind: Literal["native_build_query_settled_v1"] = "native_build_query_settled_v1"
    event_id: UUID
    sequence: int = Field(ge=0, strict=True)
    controller_attempt_id: UUID
    query: NativeGraphQueryV4


def effective_native_query(context, execution):
    """Return the query admitted by this prefix, or the typed pending commitment."""
    query = context.native_query
    settlements = [e for e in execution.events if type(e) is NativeBuildQuerySettledV1]
    if type(query) is not NativeBuildQueryPendingV1:
        if settlements:
            raise ValueError("A settled-on-admission query cannot acquire a second catalog")
        return query

    action = execution.policy.action
    if (type(action) is not NativeBuildActionV1 or action.intent.reviewed_step is not None
            or getattr(action.intent, "authored_references", None) is not None
            or query.question != action.intent.message
            or action.intent.graph_request.revision_pin not in (None, query.authority.revision_id)):
        raise ValueError("Pending Graph query differs from the admitted Build request")
    if len(settlements) > 1:
        raise ValueError("Build can settle its pending Graph query only once")
    settlement = settlements[0] if settlements else None
    conversation_work = prior_conversation_work(execution.events)
    if settlement is None and conversation_work is not None:
        from .native_retrieval import NativeRetrievalAuthorizedV1, NativeRetrievalSelectedV1, NativeRetrievalSelectedV2

        if any(isinstance(event, (*t.NATIVE_BODY_EVENTS, NativeRetrievalAuthorizedV1,
                                 NativeRetrievalSelectedV1, NativeRetrievalSelectedV2, t.RelatedPageRead))
               for event in execution.events):
            raise ValueError("Conversation draft without Graph settlement cannot acquire new evidence")
        events = execution.events[:conversation_work.sequence]
    else:
        events = execution.events if settlement is None else execution.events[:settlement.sequence]
    authorization = None
    responded = False
    for event in events:
        if type(event) is t.BuildDraftContextCapturedV1 and authorization is None:
            continue
        if (type(event) is t.ProviderAttemptAuthorizedEventV5 and authorization is None
                and event.context_phase == "select"
                and (event.provider, event.model, event.api_mode) == execution.policy.provider_roles.controller.identity()):
            authorization = event
            continue
        if (type(event) is t.ProviderOutcomeEventV1 and authorization is not None
                and event.provider_attempt_id == authorization.provider_attempt_id):
            responded = event.outcome == "response_received"
            continue
        raise ValueError("Graph-dependent Build work requires its settled query")
    if settlement is None:
        return query
    if (authorization is None or not responded
            or settlement.controller_attempt_id != authorization.provider_attempt_id
            or settlement.query.authority != query.authority
            or settlement.query.question != query.question
            or settlement.query.authored_targets):
        raise ValueError("Settled Graph query differs from its opening Build authorization")
    return settlement.query


# Current owner event codecs are reused. Classic Graph operations/scopes and
# source-anchor receipts deliberately have no branch in this native event union.
SurfaceNativeEvent = Annotated[
    t.ProviderAttemptAuthorizedEventV3 | t.ProviderAttemptAuthorizedEventV5
    | t.PlanJevProviderAuthorizedV1 | NativeRetrievalAuthorizedV1 | NativePlanOpeningAuthorizedV1
    | NativePlanAuthorScopeAuthorizedV1 | NativePlanAuthorScopeObservedV1 | t.PlanRequestedWorkAuthorizedV2
    | NativeWriterAuthorizedV1 | NativeBuildWriterAuthorizedV2 | t.ProviderOutcomeEventV1 | t.CompletionBindingEventV1
    | t.PlanJevRetrievalSelectionV1 | NativeRetrievalSelectedV1 | NativeRetrievalSelectedV2 | NativeReadBatchConcludedV1 | t.PlanRequestedWorkSelectedV2 | NativePlanRequestedWorkSelectedV3 | NativePlanOpeningSelectedV1 | NativePlanOpeningSelectedV2 | NativePlanOpeningSelectedV3
    | t.NativeBodySearchAuthorizedV1 | t.NativeInitialSourceSearchAuthorizedV1 | t.NativePlanRequestSearchAuthorizedV1 | t.NativeBodySearchObservedV1
    | t.NativeBodyReadAuthorizedV1 | t.NativeBodyReadObservedV1 | t.NativeAuthoredSourceReadV1
    | t.NativeDirectSourceAuthorizedV1 | t.NativeDirectSourceObservedV1
    | t.NativePlanStatementReadAuthorizedV1 | t.NativePlanStatementReadObservedV1
    | t.NativePlanAssertionReadAuthorizedV1 | t.NativePlanAssertionReadObservedV1
    | t.BuildDraftContextCapturedV1 | NativeBuildQuerySettledV1 | t.BuildPriorBodyEvidenceAdmittedV1
    | t.BuildSectionReadAuthorizationV1 | t.ValidatedBuildSectionReadV1
    | t.BuildRequestedWorkResolutionV1 | t.BuildReviewedActionSelectionV2 | t.BuildReviewedActionSelectionV1
    | t.BuildWriterEvidenceSelectionV1 | t.BuildWriterEvidenceSelectionV2 | t.BuildPlanOutputContractV2
    | t.RelatedPagesSelection | t.RelatedPageRead | BuildSavedStatblockReadV1
    | t.BuildAuthoredReferencesCapturedV1 | BuildAuthoredReferenceAuthorizedV2
    | BuildAuthoredReferenceReadV2 | BuildAuthoredReferenceReadV3 | NativePlanAssertionReadObservedV2,
    Field(discriminator="kind"),
]


_BUILD_WORK_EVENTS = (
    t.BuildDraftContextCapturedV1, NativeBuildQuerySettledV1, t.BuildPriorBodyEvidenceAdmittedV1,
    t.BuildSectionReadAuthorizationV1, t.ValidatedBuildSectionReadV1,
    t.BuildRequestedWorkResolutionV1, t.BuildReviewedActionSelectionV1,
    t.BuildWriterEvidenceSelectionV1, t.BuildPlanOutputContractV2,
    t.RelatedPagesSelection, BuildSavedStatblockReadV1,
)
_PLAN_WORK_EVENTS = (t.PlanRequestedWorkAuthorizedV2, t.PlanRequestedWorkSelectedV2)


NATIVE_EXECUTION_EVENT_LIMIT = 2048


class SurfaceNativeExecutionV1(Strict):
    schema_: Literal["dmb_surface_native_execution_v1"] = Field(default="dmb_surface_native_execution_v1", alias="schema")
    context_receipt_sha256: Digest
    execution_policy_sha256: Digest
    policy: SurfaceNativeExecutionPolicyV1
    events: list[SurfaceNativeEvent] = Field(max_length=NATIVE_EXECUTION_EVENT_LIMIT)

    @model_validator(mode="after")
    def actual_records(self):
        # Recheck mutable owner models before trusting their frozen commitment.
        SurfaceNativeExecutionPolicyV1.model_validate(self.policy.model_dump(mode="python", by_alias=True))
        expected = t.canonical_sha256(dict(schema=self.schema_,
            context_receipt_sha256=self.context_receipt_sha256,
            policy=self.policy.model_dump(mode="json", by_alias=True)))
        if self.execution_policy_sha256 != expected:
            raise ValueError("Native execution policy differs from its frozen commitment")
        t.validate_provider_execution(self)
        roles = self.policy.provider_roles
        action = self.policy.action
        contextual_selection = None
        if type(action) is NativePlanActionV3:
            contextual_selection = (NativePlanOpeningSelectedV3
                if type(action.placement_catalog) is ComposedPlanPlacementCatalogV1
                else NativePlanOpeningSelectedV2)
        for event in self.events:
            if isinstance(event, t.PlanRequestedWorkSelectedV1):
                if (contextual_selection is not None and type(event) is not contextual_selection
                    or contextual_selection is None and type(event) in (NativePlanOpeningSelectedV2, NativePlanOpeningSelectedV3)):
                    raise ValueError('Plan work selection differs from its action contract version')
            if type(event) in (NativePlanOpeningSelectedV2, NativePlanOpeningSelectedV3) and event.author_scope_binding is not None:
                binding = event.author_scope_binding
                if binding != bind_opening_author_scope(
                        self.model_copy(update={'events': self.events[:event.sequence]}),
                        binding.observation_event_id, binding.observation):
                    raise ValueError('Selected page edit intent differs from its actual author observations')
                expected_title = action.document_title
                if type(event) is NativePlanOpeningSelectedV3:
                    expected_title = expected_title or ''
                    if event.author_operation != getattr(action.intent, "plan_requested_operation", None):
                        raise ValueError('Composed opening changed the submitted author operation')
                if event.scope_document_title != expected_title:
                    raise ValueError('Bound opening selection title differs from the frozen Content title')
            if isinstance(event,t.ProviderOutcomeEventV1) and event.outcome=='response_received':
                producer=next(e for e in self.events[:event.sequence]
                    if isinstance(e,t.ProviderAttemptAuthorizedEventV1) and e.provider_attempt_id==event.provider_attempt_id)
                if type(producer) in NATIVE_WRITER_TYPES and (not event.request_id or not event.response_sha256):
                    raise ValueError('Shared native writer response requires its exact selected output acknowledgement')
            if isinstance(event, _BUILD_WORK_EVENTS) and not isinstance(self.policy.action, NativeBuildActionV1):
                raise ValueError("Build work event cannot acquire another action family")
            if isinstance(event, t.BuildPriorBodyEvidenceAdmittedV1):
                prefix = self.events[:event.sequence]
                work = prior_conversation_work(prefix)
                references = [support.reference for support in event.supports]
                if (work is None or work.event_id != event.work_event_id
                        or len(set((r.turn_id, r.citation_index) for r in references)) != len(references)
                        or any(isinstance(prior, t.BuildPriorBodyEvidenceAdmittedV1)
                               or type(prior) in NATIVE_WRITER_TYPES for prior in prefix)):
                    raise ValueError("Prior body evidence requires the unique producing Build work decision")
            if isinstance(event, BuildSavedStatblockReadV1):
                validate_saved_statblock_read(event, self)
            if isinstance(event, t.RelatedPageRead) and type(self.policy.action) not in (NativeBuildActionV1, NativePlanActionV2, NativePlanActionV3):
                raise ValueError("Saved-page read lacks its actual surface capability")
            if isinstance(event, _PLAN_WORK_EVENTS) and not isinstance(self.policy.action, NativePlanActionV1):
                raise ValueError("Plan work event cannot acquire another action family")
            if isinstance(event, t.ProviderAttemptAuthorizedEventV1):
                identity = event.provider, event.model, event.api_mode
                if type(event) in NATIVE_WRITER_TYPES:
                    if type(event) is NativeBuildWriterAuthorizedV2 and not isinstance(self.policy.action, NativeBuildActionV1):
                        raise ValueError('Build work authorization cannot authorize another surface')
                    writer_role = roles.writer
                    if identity != writer_role.identity():
                        raise ValueError("Shared native inclusion belongs only to its exact writer role")
                    reads = native_read_event_ids(self.events[:event.sequence])
                    if event.native_read_event_ids != reads:
                        raise ValueError("Native writer changed its exact settled read inclusion set")
                if type(event) is NativeRetrievalAuthorizedV1:
                    if not isinstance(roles,t.GraphControllerWriterRolesV1) or identity!=roles.controller.identity():
                        raise ValueError("Native retrieval belongs only to its actual controller role")
                    if (isinstance(self.policy.action,NativeBuildActionV1)) != (event.build_context is not None):
                        raise ValueError("Native dispatch context differs from its concrete surface")
                if isinstance(roles, t.GraphControllerWriterRolesV1):
                    if identity == roles.writer.identity() and type(event) not in NATIVE_WRITER_TYPES:
                        raise ValueError("Native writer requires its exact shared selected-read inclusion codec")
                    if (isinstance(self.policy.action, (NativePlanActionV1,NativePlayActionV1))
                            and identity == roles.controller.identity()
                            and not isinstance(event, t.PlanJevProviderAuthorizedV1)):
                        raise ValueError("Native decision controller requires its actual producing codec")
                if (event.included_assertion_ids or event.included_relationship_ids
                        or event.included_evidence_ref_ids or event.included_graph_event_ids
                        or event.included_source_read_event_ids
                        or getattr(event, "included_source_reuse_event_ids", ())):
                    raise ValueError("Native provider cannot acquire absent classic Graph evidence")
        from .authored_graph_references import validate_native_execution
        validate_native_execution(self)
        if isinstance(self.policy.action,NativeBuildActionV1):
            from .build_intentional_response import validate_native_action_events
            validate_native_action_events(self)
            from .plan_objective import validate_events as validate_plan_output_events
            validate_plan_output_events(self)
            from .build_draft_context import validate_execution_records
            from .build_primary_context import validate_reads, validate_selection_origin
            validate_execution_records(self)
            validate_reads(self,max_chars=self.policy.action.saved_source_char_count)
            from .build_related_pages import validate_events as validate_related_events
            validate_related_events(self)
            for event in self.events:
                if isinstance(event,t.BuildWriterEvidenceSelectionV1):
                    validate_selection_origin(self,event)
                    if event.source_event_ids:
                        raise ValueError('Native World evidence cannot acquire a second classic source inclusion set')
        elif type(self.policy.action) in (NativePlanActionV2, NativePlanActionV3):
            from .build_related_pages import validate_events as validate_related_events
            validate_related_events(self)
        if isinstance(roles, t.GraphControllerWriterRolesV1):
            reviewed = [event for event in self.events if isinstance(event, t.BuildReviewedActionSelectionV1)]
            if reviewed:
                if (not isinstance(self.policy.action, NativeBuildActionV1) or len(reviewed) != 1
                        or reviewed[0].intent != self.policy.action.intent):
                    raise ValueError("Reviewed action differs from the actual native action commitment")
                # The submission/selection/reservation owners must additionally
                # validate this stored reviewed step before granting any write.
            t.validate_controller_writer_execution(self, reviewed_action=reviewed[0] if reviewed else None)
            from .native_retrieval import validate_decision_phases
            validate_decision_phases(self)
            from .native_corpus import validate_native_body_events
            validate_native_body_events(self)
        elif any(isinstance(event, t.NATIVE_BODY_EVENTS) for event in self.events):
            raise ValueError("Single-provider native body acquisition awaits its actual SDK selection proof")
        # This is retained acquisition history, not a provider request. Its event
        # bound and owner checks apply here; actual SDK envelope budgets apply at
        # dispatch. APP's shared native JSONB contract has no aggregate byte cap.
        return self


def validate_context_binding(context, execution) -> SurfaceNativeExecutionV1:
    """Validate both mutable components and return the reconstructed execution."""
    _, validated = _revalidate_context_binding(context, execution)
    return validated


def _revalidate_context_binding(context, execution):
    """Return the freshly decoded pair after checking its context binding."""
    if type(context) is not SurfaceNativeContextReceiptV1 or type(execution) is not SurfaceNativeExecutionV1:
        raise ValueError("Native execution requires its concrete shared context")
    context = SurfaceNativeContextReceiptV1.model_validate(context.model_dump(mode="python", by_alias=True))
    execution = SurfaceNativeExecutionV1.model_validate(execution.model_dump(mode="python", by_alias=True))
    return context, _join_context_binding(context, execution)


def _validate_owned_context_binding(context, execution):
    """Run the complete predicate owners on APP's exclusively owned prefix.

    This pure function grants no IO authority. A session caller must prove
    current storage equality and strictly decode any new events. Retained
    completion checking uses an exact slice of its already validated parent.
    Both callers preserve nonescaping ownership of the typed components.
    Initial admission, recovery and the actual writer frontier use the full codec.
    """
    if type(context) is not SurfaceNativeContextReceiptV1 or type(execution) is not SurfaceNativeExecutionV1:
        raise ValueError('Owned native binding requires its concrete complete components')
    if len(execution.events) > NATIVE_EXECUTION_EVENT_LIMIT:
        raise ValueError('Native execution exceeds its event bound')
    execution.actual_records()
    return _join_context_binding(context, execution)


def _join_context_binding(context, execution):
    """Join components freshly validated by the calling construction owner."""
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
            if isinstance(event, BuildSavedStatblockReadV1) and event.pdf_support is not None:
                from .authored_graph_references import native_references, object_selections
                from .native_corpus import NativeCorpusAuthorityV1

                pin = event.pdf_support.scope
                identity = (pin.managed_world_id, pin.native_world_id, pin.binding_version, pin.revision_id)
                authority = context.source_authority
                source_matches = isinstance(authority, NativeCorpusAuthorityV1) and identity == (
                    authority.managed_world_id, authority.native_world_id,
                    authority.binding_version, authority.revision_id,
                )
                if not source_matches and not any(
                    identity == (ref.managed_world_id, ref.native_world_id, ref.binding_version, ref.graph_revision)
                    for ref in object_selections(native_references(execution))
                ):
                    raise ValueError("Saved statblock PDF support differs from its admitted Graph pin")
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
    if type(action) is NativePlanActionV3 and type(assembled) is not NativePlanRequestAdmissionV1:
        raise ValueError('Contextual Plan requires current request-owned admission')
    if (not isinstance(assembled, NativePlanRequestAdmissionV1)
            and any(isinstance(e, t.NativePlanRequestSearchAuthorizedV1) for e in execution.events)):
        raise ValueError('Request-owned discovery requires its explicit Plan request-admission codec')
    if isinstance(assembled, NativeReviewedActionInputV1):
        from .reviewed_action import admission_manifest, digest
        if (not isinstance(action, NativeBuildActionV1) or action.intent.reviewed_step is None
                or assembled.submitted_intent_sha256 != t.canonical_sha256(action.intent)
                or assembled.assembled_input_sha256 != digest(admission_manifest(action.intent))):
            raise ValueError("Native reviewed admission differs from the actual author intent")
    elif isinstance(assembled, NativePlanRequestAdmissionV1):
        from .native_plan_opening import validate_request_admission
        validate_request_admission(context, execution)
        for index, event in enumerate(execution.events):
            if isinstance(event, t.ProviderAttemptAuthorizedEventV1):
                t.validate_provider_envelope_accounting(assembled,
                    execution.model_copy(update={'events': execution.events[:index]}), event)
    elif isinstance(assembled, NativeProviderInputV1):
        if isinstance(action, NativeBuildActionV1) and action.intent.reviewed_step is not None:
            raise ValueError("Native reviewed action requires its model-free admission")
        for index, event in enumerate(execution.events):
            if isinstance(event, t.ProviderAttemptAuthorizedEventV1):
                t.validate_provider_envelope_accounting(assembled,
                    execution.model_copy(update={"events": execution.events[:index]}), event)
    from .native_corpus import conversation_route_can_admit
    if (any(isinstance(event, t.BuildPriorBodyEvidenceAdmittedV1) for event in execution.events)
            and not conversation_route_can_admit(context, execution)):
        raise ValueError("Conversation body evidence requires a Graph query that was never settled")
    query = effective_native_query(context, execution)
    if isinstance(query, t.NativePlanQueryV2):
        request = action.intent.graph_request
        if query.question != action.intent.message or query.authority.scope_mode != "world":
            raise ValueError("Native query differs from the unchanged submitted World question")
        if request.revision_pin is not None and request.revision_pin != query.authority.revision_id:
            raise ValueError("Native query cannot replace an explicitly requested revision")
    from .native_plan_statements import validate_selected_record_events
    validate_selected_record_events(query, execution)
    from .authored_graph_references import validate_native_context
    validate_native_context(query, execution)
    from .native_batch_completion import selected_read_closure
    for event in execution.events:
        if type(event) is NativeReadBatchConcludedV1:
            expected = selected_read_closure(context, execution, event.selection_event_id,
                before_sequence=event.sequence)
            if expected is None or event.read_event_ids != expected:
                raise ValueError('Read-batch conclusion differs from its actual selected successful closure')
    return execution


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
    receipt, execution = _revalidate_context_binding(receipt, execution)
    if (t.canonical_sha256(provenance) != receipt.provenance_sha256
            or t.submitted_turn_intent_fingerprint_v2(execution.policy.action.intent) != intent_fingerprint):
        raise ValueError("Stored shared native request or provenance differs from admission")
    _join_turn_fields(receipt, execution, completion, assistant_text)


def _join_turn_fields(receipt, execution, completion, assistant_text):
    """Complete the structural join after the caller has checked the context binding."""
    bindings=[event for event in execution.events if isinstance(event,t.CompletionBindingEventV1)]
    if completion is None:
        if assistant_text is not None or bindings:
            raise ValueError('Shared native text requires its typed completion and binding')
        return
    if (len(bindings)!=1 or assistant_text!='\n'.join(s.text for s in completion.answer_segments)):
        raise ValueError('Shared native completion requires exact retained text and binding')
    from .native_completion import _join_retained_completion

    binding = bindings[0]
    _join_retained_completion(completion, receipt, execution, binding.provider_attempt_id, binding.claim_graph_event_ids)


def _join_turn_lifecycle(turn):
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
    _join_request_identity(receipt, execution, envelope)


def _join_request_identity(receipt, execution, envelope):
    action=execution.policy.action
    intent=action.intent
    if (envelope.submitted_intent_fingerprint_v1 is not None
            or t.submitted_turn_intent_fingerprint_v2(intent)!=envelope.submitted_intent_fingerprint_v2
            or envelope.world_id!=intent.world_id or envelope.user_text!=intent.message
            or envelope.provenance.surface_instance_id!=intent.surface_instance_id):
        raise ValueError('Stored shared native request differs from admission')
    from .authored_graph_references import validate_native_capture_identity
    validate_native_capture_identity(execution, turn_id=envelope.turn_id,
        conversation_id=envelope.conversation_id, attempt=envelope.attempt,
        fingerprint=envelope.submitted_intent_fingerprint_v2)
    binding=getattr(intent,'reviewed_step',None)
    if binding is not None and binding.reference.conversation_id!=envelope.conversation_id:
        raise ValueError('Reviewed native action belongs to a different conversation')
    capture=getattr(action,'authoring_capture',None)
    if capture is not None and capture.conversation_id!=envelope.conversation_id:
        raise ValueError('Native Plan capture belongs to a different conversation')
