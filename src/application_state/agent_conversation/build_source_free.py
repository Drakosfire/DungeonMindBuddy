"""Build-only observations before source verification; never evidence authority.

These host records grant no content access, verified revision, completeness, or
citation capability. Runtime registration belongs to the matching new receipt.
"""
from __future__ import annotations

from typing import Literal
from uuid import UUID

from pydantic import Field, model_validator

from .native_statement_input import Strict
from .build_related_pages import PagePointer


class BuildConversationObservationV1(Strict):
    """Captured existing App pointer; never an independent mutable owner."""
    conversation_id: UUID
    pointer_revision: int = Field(ge=0, strict=True)


def capture_pending_conversation(pointer, *, world_id, conversation_id):
    """Snapshot a record supplied by the existing App World-state owner.

    The transactional caller must lock/recheck authoritative state; constructing
    this observation alone grants neither conversation access nor source IO.
    """
    from .types import WorldPointer
    if type(pointer) is not WorldPointer:
        raise ValueError("Pending conversation requires its actual World pointer record")
    pointer = WorldPointer.model_validate_json(pointer.model_dump_json())
    if pointer.world_id != world_id or pointer.active_conversation_id != conversation_id:
        raise ValueError("Pending request differs from the active World conversation")
    return BuildConversationObservationV1(conversation_id=conversation_id, pointer_revision=pointer.revision)


def validate_pending_conversation_pointer(receipt, pointer):
    """Compare the captured pointer without refreshing or replacing it."""
    captured = receipt.conversation_observation
    actual = capture_pending_conversation(pointer,
        world_id=receipt.source_observation.managed_world_id,
        conversation_id=captured.conversation_id)
    if actual != captured:
        raise ValueError("Pending conversation pointer changed after capture")


class BuildAppPageCatalogObservedV1(Strict):
    """App navigation metadata captured after lookup; never read-page evidence."""
    kind: Literal["build_app_page_catalog_observed_v1"] = "build_app_page_catalog_observed_v1"
    event_id: UUID
    sequence: int = Field(ge=0, strict=True)
    pending_context_receipt_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    admitted_from_revision: int = Field(ge=1, strict=True)
    work_event_id: UUID
    # Use the existing exact App pointer owner; no Core binding or invented source grant.
    pages: tuple[PagePointer, ...]

    @model_validator(mode="after")
    def unique_ordered_pages(self):
        identifiers = [page.document_id for page in self.pages]
        if identifiers != sorted(set(identifiers), key=str):
            raise ValueError("Pending App page catalog must be sorted and distinct")
        return self


class BuildSourceBindingObservedV1(Strict):
    managed_world_id: str = Field(min_length=1, strict=True)
    native_world_id: str = Field(min_length=1, strict=True)
    binding_version: int = Field(gt=0, strict=True)
    provisioning_id: str | None = Field(default=None, min_length=1, strict=True)


class BuildSourceObservationV1(Strict):
    """Requested identity and observed pointer, with no source-read assertion."""

    schema_: Literal["dmb_build_source_observation_v1"] = Field(
        default="dmb_build_source_observation_v1", alias="schema")
    managed_world_id: str = Field(min_length=1, strict=True)
    binding: BuildSourceBindingObservedV1 | None
    requested_revision_id: str | None = Field(min_length=1, strict=True)
    observed_head_revision_id: str | None = Field(min_length=1, strict=True)

    @model_validator(mode="after")
    def observed_scope(self):
        if self.binding is None:
            if self.observed_head_revision_id is not None:
                raise ValueError("A head observation requires its observed World binding")
        elif self.binding.managed_world_id != self.managed_world_id:
            raise ValueError("Observed source binding belongs to another managed World")
        return self

    @property
    def requested_or_observed_revision(self) -> str | None:
        """An identity to verify later, never proof that a revision exists."""
        return self.requested_revision_id or self.observed_head_revision_id



def validate_pending_source_settlement(receipt, settlement):
    """Join stored identities, without granting access or admitting an event.

    Current principal/request/pointer and one-way prefix checks remain with the
    transactional APP owner. This function never prepares or reopens a source.
    """
    from .native_context import BuildPendingContextReceiptV1
    from .native_execution import NativeBuildSourceSettledV1

    if type(receipt) is not BuildPendingContextReceiptV1 or type(settlement) is not NativeBuildSourceSettledV1:
        raise ValueError("Source settlement requires the distinct pending Build codec")
    # Do not trust model_copy/model_construct values to have run validators.
    BuildPendingContextReceiptV1.model_validate_json(receipt.model_dump_json(by_alias=True))
    NativeBuildSourceSettledV1.model_validate_json(settlement.model_dump_json(by_alias=True))
    if settlement.pending_context_receipt_sha256 != receipt.context_receipt_sha256:
        raise ValueError("Source settlement differs from its pending receipt")
    observed, source = receipt.source_observation, settlement.source_authority
    binding = observed.binding
    revision = observed.requested_or_observed_revision
    if binding is None or revision is None:
        raise ValueError("Unobserved source scope cannot be replaced during settlement")
    if any(getattr(source, key) != getattr(binding, key) for key in (
            "managed_world_id", "native_world_id", "binding_version", "provisioning_id")):
        raise ValueError("Source settlement differs from the observed binding")
    if source.revision_id != revision:
        raise ValueError("Source settlement differs from the requested or observed revision")


def effective_pending_source(receipt, execution):
    """Resolve a structurally joined pending source; never prepare or grant it.

    None means no source authority/query exists. A non-None result remains subject
    to actual locked-row settlement admission and existing read/access owners.
    """
    receipt, execution = _pending_components(receipt, execution)
    return _join_pending_source(receipt, execution)


def validate_pending_execution_binding(receipt, execution):
    """Return the freshly decoded execution after joining its actual receipt."""
    receipt, execution = _pending_components(receipt, execution)
    _join_pending_source(receipt, execution)
    return execution


def _pending_components(receipt, execution):
    """Reconstruct only at a boundary that does not already own fresh models."""
    from .native_context import BuildPendingContextReceiptV1
    from .native_execution import BuildPendingExecutionV1
    if type(receipt) is not BuildPendingContextReceiptV1 or type(execution) is not BuildPendingExecutionV1:
        raise ValueError("Pending source requires its concrete Build receipt and execution")
    return (BuildPendingContextReceiptV1.model_validate_json(receipt.model_dump_json(by_alias=True)),
            BuildPendingExecutionV1.model_validate_json(execution.model_dump_json(by_alias=True)))


def _join_pending_source(receipt, execution):
    """Join components already freshly decoded by their owning boundary."""
    from . import types as t
    from .native_context import work_world_id
    from .native_execution import BuildPendingExecutionV1, NativeBuildSourceSettledV1
    from .native_context import BuildPendingContextReceiptV1
    from .build_world_context import validate_work_intent
    if type(receipt) is not BuildPendingContextReceiptV1 or type(execution) is not BuildPendingExecutionV1:
        raise ValueError("Pending source requires its concrete Build receipt and execution")
    policy, work = execution.policy, receipt.work_context
    if (execution.context_receipt_sha256 != receipt.context_receipt_sha256
            or policy.source_observation_sha256 != t.canonical_sha256(receipt.source_observation)
            or policy.action.intent.world_id != work_world_id(work)):
        raise ValueError("Pending action, work and observation commitments differ")
    validate_work_intent(work.source_basis, policy.action.intent)
    for index, event in enumerate(execution.events):
        if isinstance(event, t.ProviderAttemptAuthorizedEventV1):
            t.validate_provider_envelope_accounting(receipt.assembled_input,
                execution.model_copy(update={'events': execution.events[:index]}), event)
    if receipt.source_observation.requested_revision_id != policy.action.intent.graph_request.revision_pin:
        raise ValueError("Pending observation differs from the explicitly requested revision")
    for event in execution.events:
        if type(event) is t.BuildDraftContextCapturedV1:
            if event.record.snapshot.saved_basis() != work.source_basis.model_dump(mode="json", by_alias=True):
                raise ValueError("Pending working draft differs from its frozen source basis")
            captured = receipt.conversation_observation
            if (event.record.conversation_id != captured.conversation_id
                    or event.record.expected_pointer_revision != captured.pointer_revision):
                raise ValueError("Pending draft differs from its captured conversation pointer")
    for event in execution.events:
        if type(event) is BuildAppPageCatalogObservedV1:
            if event.pending_context_receipt_sha256 != receipt.context_receipt_sha256:
                raise ValueError("Pending App catalog differs from its captured receipt")
            basis = work.source_basis
            if any(page.world_id != policy.action.intent.world_id
                   or (str(page.document_id) == str(basis.document_id)
                       and (page.registry_revision != basis.registry_revision
                            or page.visibility != basis.visibility))
                   for page in event.pages):
                raise ValueError("Pending App catalog contains a foreign World or mismatched current page")
        if type(event) is t.RelatedPageRead and str(event.page.document_id) == str(work.source_basis.document_id):
            basis = work.source_basis
            if (event.page.world_id != basis.world_id or event.page.registry_revision != basis.registry_revision
                    or event.page.visibility != basis.visibility or event.page.content_sha256 != basis.content_sha256):
                raise ValueError("Pending saved current page differs from its frozen source basis")
    settlements = [event for event in execution.events if type(event) is NativeBuildSourceSettledV1]
    if not settlements:
        return None
    settlement, = settlements
    validate_pending_source_settlement(receipt, settlement)
    return settlement.source_authority, settlement.native_query


def validate_pending_work_records(execution):
    """Bind captured editor context before the new first decision, without IO."""
    from . import types as t
    from .build_draft_context import (BuildDraftContextRecordV1, BuildDraftSnapshotV1,
                                     captured_context_sha256)
    action = execution.policy.action
    rows = [event for event in execution.events if type(event) is t.BuildDraftContextCapturedV1]
    if len(rows) > 1:
        raise ValueError("Pending work captures one immutable draft")
    for event in rows:
        record = BuildDraftContextRecordV1.model_validate_json(event.record.model_dump_json(by_alias=True))
        if (event.sequence != 0
                or captured_context_sha256(record) != action.intent.build_draft_context_sha256
                or record.submitted_intent_fingerprint != t.submitted_turn_intent_fingerprint_v2(action.intent)):
            raise ValueError("Pending draft differs from its submitted first-decision context")
        if action.write_capability is not None:
            capability = action.write_capability
            editor = BuildDraftSnapshotV1(**{key: capability.draft_markdown if key == 'draft_markdown'
                else getattr(capability.basis, key) for key in BuildDraftSnapshotV1.model_fields if key != 'schema_'})
            if record.snapshot != editor:
                raise ValueError("Pending editor differs from its captured write capability")
    if action.intent.build_draft_context_sha256 is not None and not rows and any(
            isinstance(event, t.ProviderAttemptAuthorizedEventV1) for event in execution.events):
        raise ValueError("Pending decision requires its submitted draft capture first")


def validate_pending_turn_fields(receipt, execution, provenance, intent_fingerprint, completion, assistant_text):
    """Stored pending input, execution, final native completion and text closure."""
    receipt, execution = _pending_components(receipt, execution)
    _join_pending_turn_fields(receipt, execution, provenance, intent_fingerprint, completion, assistant_text)


def _join_pending_turn_fields(receipt, execution, provenance, intent_fingerprint, completion, assistant_text):
    from . import types as t
    from .native_context import _join_work_context
    _join_pending_source(receipt, execution)
    _join_work_context(receipt, provenance)
    if t.submitted_turn_intent_fingerprint_v2(execution.policy.action.intent) != intent_fingerprint:
        raise ValueError("Pending stored request fingerprint differs from admission")
    if completion is None:
        if assistant_text is not None or any(type(event) is t.CompletionBindingEventV1 for event in execution.events):
            raise ValueError("Pending prefix has no registered terminal output owner")
    else:
        from .native_completion import SurfaceNativeCompletionV1, validate_retained_completion
        if type(completion) is SurfaceNativeCompletionV1:
            validate_retained_completion(completion, receipt, execution, completion.producing_provider_attempt_id, {})
        elif type(completion) is t.BuildAuthoringCompletionV1:
            from .build_authoring import validate_native_authoring_binding
            validate_native_authoring_binding(completion, receipt, execution, completion.provider_attempt_id, {})
        else:
            raise ValueError('Pending terminal requires its exact native completion')
        bindings = [event for event in execution.events if type(event) is t.CompletionBindingEventV1]
        if (len(bindings) != 1 or bindings[0].completion_sha256 != t.canonical_sha256(completion)
                or assistant_text != '\n'.join(segment.text for segment in completion.answer_segments)):
            raise ValueError('Pending terminal differs from its final completion binding or text')


def validate_pending_submission(submission):
    from .native_context import _join_work_context
    receipt, execution = _pending_components(submission.graph_context_receipt, submission.graph_context_execution)
    _join_pending_source(receipt, execution)
    _join_work_context(receipt, submission.provenance, play_context_receipt=submission.play_context_receipt)
    intent = execution.policy.action.intent
    if (submission.submitted_intent_v1 is not None or submission.submitted_intent_v2 != intent
            or execution.events or submission.world_id != intent.world_id
            or submission.conversation_id != receipt.conversation_observation.conversation_id
            or submission.user_text != intent.message
            or submission.provenance.surface_instance_id != intent.surface_instance_id):
        raise ValueError("Pending admission requires its unchanged Build request and empty execution")


def _join_pending_turn(turn):
    receipt, execution = turn.graph_context_receipt, turn.graph_context_execution
    from .native_execution import _join_turn_lifecycle
    _join_turn_lifecycle(turn)
    _join_pending_turn_fields(receipt, execution, turn.provenance,
        turn.submitted_intent_fingerprint_v2, turn.completion, turn.assistant_text)
    validate_pending_request_identity(receipt, execution, turn)


def validate_pending_request_identity(receipt, execution, turn):
    """Exact request join for ordinary and unclaimed mixed completed readers."""
    from . import types as t
    from .native_context import BuildPendingContextReceiptV1, validate_work_context
    from .native_execution import BuildPendingExecutionV1
    from .build_draft_context import validate_record_identity
    from .build_intentional_response import validate_turn_arguments
    from .retained_conversation import validate_binding
    if (type(receipt), type(execution)) != (BuildPendingContextReceiptV1, BuildPendingExecutionV1):
        raise ValueError('Pending request identity requires its exact receipt/execution pair')
    validate_work_context(receipt, turn.provenance, play_context_receipt=turn.play_context_receipt)
    if t.submitted_turn_intent_fingerprint_v2(execution.policy.action.intent) != turn.submitted_intent_fingerprint_v2:
        raise ValueError('Pending request identity differs from its admitted intent')
    for event in execution.events:
        if type(event) is t.BuildPriorBodyEvidenceAdmittedV3:
            validate_binding(event, world_id=turn.world_id, conversation_id=turn.conversation_id,
                turn_id=turn.turn_id, attempt=turn.attempt)
            if (event.conversation_sequence != turn.sequence
                    or event.pointer_revision != receipt.conversation_observation.pointer_revision):
                raise ValueError('Pending retained context differs from its captured turn or pointer')
    intent = execution.policy.action.intent
    if (turn.submitted_intent_fingerprint_v1 is not None
            or turn.world_id != intent.world_id or turn.user_text != intent.message
            or turn.conversation_id != receipt.conversation_observation.conversation_id
            or turn.provenance.surface_instance_id != intent.surface_instance_id
            or turn.play_context_receipt is not None
            ):
        raise ValueError("Stored pending Turn differs from its admitted request or lifecycle")
    validate_turn_arguments(execution, user_text=turn.user_text, turn_id=turn.turn_id, attempt=turn.attempt)
    for event in execution.events:
        if type(event) is t.BuildDraftContextCapturedV1:
            validate_record_identity(event.record, world_id=turn.world_id,
                conversation_id=turn.conversation_id, turn_id=turn.turn_id,
                attempt=turn.attempt, submitted_intent_fingerprint=turn.submitted_intent_fingerprint_v2,
                saved_basis=receipt.work_context.source_basis)


def pending_source_work(execution):
    """Select acknowledged work only after App evidence requires further sources."""
    from . import types as t
    from .build_pending_app_coverage import BuildAppCoverageDecidedV1
    work = _pending_evidence_work(execution)
    if any(type(event) is t.RelatedPageRead for event in execution.events):
        decisions = [event for event in execution.events if type(event) is BuildAppCoverageDecidedV1]
        if len(decisions) != 1 or decisions[0].verdict != 'native_sources_required':
            raise ValueError('Native preparation requires acknowledged further-source coverage work')
    return work


def pending_work_requests_evidence(work, policy):
    """Keep an unavailable executor barred while allowing an explicit factual lookup."""
    if (work.resolution.get('source_scope') not in {'source_lookup', 'uncertain'}
            or work.requested_work in {'review_blank_lore_page', 'clarify_request', 'clarify_creation'}):
        return False
    barrier = work.resolution.get('barrier')
    if barrier is None:
        return True
    from .build_intentional_response import UNAVAILABLE, validate_resolution_metadata
    if (barrier != 'requested_executor_not_offered' or work.requested_work not in UNAVAILABLE
            or work.resolution.get('source_scope') != 'source_lookup'):
        return False
    validate_resolution_metadata(work, policy)
    return True


def _pending_evidence_work(execution):
    """Pre-coverage work shape only; never permission for source preparation."""
    from . import types as t
    from .native_execution import BuildPendingExecutionV1, NativeBuildSourceSettledV1
    if type(execution) is not BuildPendingExecutionV1:
        raise ValueError("Pending settlement requires its concrete execution")
    rows = [event for event in execution.events if type(event) is t.BuildRequestedWorkResolutionV1]
    if len(rows) != 1 or any(type(event) is NativeBuildSourceSettledV1 for event in execution.events):
        raise ValueError("Pending source work must be unique and not already settled")
    from .native_execution import BuildAppPageSelectionAuthorizedV1
    page_controllers = [event for event in execution.events if type(event) is BuildAppPageSelectionAuthorizedV1]
    if page_controllers:
        latest = page_controllers[-1]
        choices = [event for event in execution.events if type(event) is t.RelatedPagesSelection]
        outcomes = [event.outcome for event in execution.events if type(event) is t.ProviderOutcomeEventV1
                    and event.provider_attempt_id == latest.provider_attempt_id]
        read_pages = {event.page.document_id for event in execution.events if type(event) is t.RelatedPageRead}
        if (outcomes[-1:] != ['response_received'] or len(choices) != 1
                or set(choices[0].document_ids) != read_pages):
            raise ValueError('Pending App page acquisition must resolve before native source preparation')
    work, = rows
    if any(isinstance(event, t.BuildPriorBodyEvidenceAdmittedV1) for event in execution.events):
        raise ValueError('Pending retained conversation cannot acquire another source scope')
    if not pending_work_requests_evidence(work, execution.policy):
        raise ValueError("Pending source work does not request evidence acquisition")
    return work


def effective_pending_app_catalog(receipt, execution):
    """Return exact observed App pointers, not evidence or an access grant.

    None means discovery did not occur; an empty tuple means it ran and found
    no eligible pages. Neither supports claims about World/source completeness.
    """
    receipt, execution = _pending_components(receipt, execution)
    _join_pending_source(receipt, execution)
    rows = [event for event in execution.events if type(event) is BuildAppPageCatalogObservedV1]
    return rows[0].pages if rows else None


def pending_app_page_selection_input(receipt, execution, initial_request_json, *, current_variant=False):
    """Build the later decision from exact prior model input and App aliases.

    The first request is supplied by its existing trace owner, not reconstructed
    from today's history. No pointer, page UUID, revision or execution metadata
    is copied into the model request. Titles remain untrusted navigation data.
    """
    receipt, execution = _pending_components(receipt, execution)
    _join_pending_source(receipt, execution)
    catalogs = [event for event in execution.events if type(event) is BuildAppPageCatalogObservedV1]
    pages = catalogs[0].pages if catalogs else None
    return _compile_pending_app_page_selection_input(receipt, execution, initial_request_json, pages, current_variant=current_variant)


def pending_semantic_context(receipt, execution, initial_request_json):
    """Original captured conversation semantics; no current history lookup."""
    from copy import deepcopy
    from hashlib import sha256
    from .source_writer_output import strict_json
    if (not isinstance(initial_request_json, str)
            or sha256(initial_request_json.encode()).hexdigest() != receipt.assembled_input.assembled_input_sha256):
        raise ValueError('App page selection requires its actual frozen initial request')
    initial = strict_json(initial_request_json)
    if (set(initial) != {'model', 'state', 'questions'}
            or initial['model'] != execution.policy.provider_roles.controller.model
            or not isinstance(initial['state'], dict)
            or set(initial['state']) != {'user_question', 'interaction'}
            or initial['state']['user_question'] != execution.policy.action.intent.message):
        raise ValueError('App page selection requires its semantic opening request')
    interaction = initial['state']['interaction']
    if (not isinstance(interaction, dict) or not isinstance(interaction.get('history'), list)
            or not isinstance(interaction.get('current_page_title'), str)):
        raise ValueError('App page selection requires captured dialogue and page navigation')
    from .build_intentional_response import semantic_collaboration
    history = []
    for row in interaction['history']:
        if (not isinstance(row, dict) or set(row) - {'user', 'assistant', 'proposed_work'}
                or not isinstance(row.get('user'), str) or not isinstance(row.get('assistant'), str)):
            raise ValueError('App page selection requires semantic dialogue rows')
        proposed = None
        if 'proposed_work' in row:
            card = row['proposed_work']
            # The opening already projected this card; it is not an original
            # full lore proposal and cannot be decoded as one a second time.
            if isinstance(card, dict) and card.get('kind') == 'lore_page':
                if set(card) != {'kind', 'title'} or not isinstance(card['title'], str) or not card['title']:
                    raise ValueError('App page selection requires the captured semantic lore proposal')
                proposed = deepcopy(card)
            else:
                proposed = semantic_collaboration(card)
        history.append({'user': row['user'], 'assistant': row['assistant'],
            **({'proposed_work': proposed} if 'proposed_work' in row else {})})
    return {'user_question': initial['state']['user_question'], 'history': deepcopy(history),
        'current_page': {'title': interaction['current_page_title'],
            'role': 'untrusted_saved_page_title_for_navigation_not_evidence'}}


def _compile_pending_app_page_selection_input(receipt, execution, initial_request_json, pages, *, current_variant=False):
    if not pages:
        raise ValueError('An absent or empty App catalog does not need a page-selection call')
    state = pending_semantic_context(receipt, execution, initial_request_json)
    current_id = str(receipt.work_context.source_basis.document_id)
    current_offer = current_variant and any(str(page.document_id) == current_id for page in pages)
    state['saved_pages'] = [{'choice': f'page{i + 1}', 'title': page.title,
        'role': ('untrusted_current_saved_page_title_for_navigation_not_evidence'
                 if current_offer and str(page.document_id) == current_id
                 else 'untrusted_saved_page_title_for_navigation_not_evidence')} for i, page in enumerate(pages)]
    from .build_related_pages import question_text
    questions = {f'page{i + 1}': {'type': 'choice', 'instructions': question_text(page, semantic=True,
                    current_offer=current_offer, is_current=str(page.document_id) == current_id),
                                 'criteria': {'read': None, 'skip': None}}
                 for i, page in enumerate(pages)}
    return {'model': execution.policy.provider_roles.controller.model, 'state': state, 'questions': questions}


def validate_pending_app_page_selection_request(receipt, execution, authorization,
                                                prepared_request_json, initial_request_json):
    """Verify the actual later dispatch bytes; not permission to dispatch them."""
    from .native_execution import BuildAppPageSelectionAuthorizedV1
    from .source_writer_output import strict_json
    from .build_decision_context import validate_prepared
    if type(authorization) is not BuildAppPageSelectionAuthorizedV1:
        raise ValueError('App page selection requires its distinct phase authorization')
    receipt, execution = _pending_components(receipt, execution)
    catalogs = [event for event in execution.events if type(event) is BuildAppPageCatalogObservedV1]
    if len(catalogs) != 1 or authorization.catalog_event_id != catalogs[0].event_id:
        raise ValueError('App page selection authorization differs from its captured catalog')
    _join_pending_source(receipt, execution)
    expected = _compile_pending_app_page_selection_input(receipt, execution, initial_request_json, catalogs[0].pages)
    current_expected = _compile_pending_app_page_selection_input(receipt, execution, initial_request_json,
        catalogs[0].pages, current_variant=True)
    actual = strict_json(prepared_request_json)
    if actual not in (expected, current_expected):
        raise ValueError('Prepared App page selection changed its frozen dialogue, catalog or choices')
    validate_prepared(authorization, execution, prepared_request_json, host_phase='navigate')
    return actual


def validate_pending_app_page_selection_result(receipt, execution, selection, proof, trace):
    """Bind actual captured SDK votes to exact host page pointers; no reads."""
    from hashlib import sha256
    from generationengine.types import DecisionResult
    from .native_execution import BuildAppPageSelectionAuthorizedV1
    from .build_related_pages import RelatedPagesSelection, should_read_page
    from .jev_retrieval_contract import validated_choice_answers
    from .source_writer_output import strict_json
    receipt, execution = _pending_components(receipt, execution)
    if type(selection) is not RelatedPagesSelection:
        raise ValueError('Pending App choices require their actual selection record')
    selection = RelatedPagesSelection.model_validate_json(selection.model_dump_json())
    if (not isinstance(proof, dict)
            or set(proof) != {'request_json', 'response_json', 'initial_request_json'}):
        raise ValueError('Pending App choices require their exact producing request and response')
    authorizations = [event for event in execution.events if type(event) is BuildAppPageSelectionAuthorizedV1]
    authorization = authorizations[-1] if authorizations else None
    outcomes = [event.outcome for event in execution.events
                if getattr(event, 'provider_attempt_id', None) == selection.controller_attempt_id
                and getattr(event, 'kind', None) == 'provider_outcome']
    if (authorization is None or selection.controller_attempt_id != authorization.provider_attempt_id
            or selection.controller_envelope_sha256 != authorization.envelope_sha256
            or outcomes[-1:] != ['response_received'] or selection.sequence != len(execution.events)):
        raise ValueError('Pending App choices lack their latest acknowledged controller')
    request = validate_pending_app_page_selection_request(receipt, execution, authorization,
        proof['request_json'], proof['initial_request_json'])
    response_raw = proof['response_json']
    if not isinstance(response_raw, str) or sha256(response_raw.encode()).hexdigest() != selection.controller_response_sha256:
        raise ValueError('Pending App choices differ from their producing response')
    response = DecisionResult.model_validate(strict_json(response_raw))
    validated_choice_answers(response, set(request['questions']), expected_model=authorization.model)
    item_id = f'unvalidated-controller-decision:{authorization.provider_attempt_id}:{receipt.context_receipt_sha256}'
    captured = [material for observation in (trace or {}).get('observations', [])
                if observation.get('kind') == 'context_snapshot'
                for material in observation.get('materials', []) if material.get('item_id') == item_id]
    if len(captured) != 1 or captured[0].get('text') != response_raw:
        raise ValueError('Pending App choices require their exact captured controller response')
    catalog, = [event for event in execution.events if type(event) is BuildAppPageCatalogObservedV1]
    current_id = str(receipt.work_context.source_basis.document_id)
    current_expected = _compile_pending_app_page_selection_input(receipt, execution,
        proof['initial_request_json'], catalog.pages, current_variant=True)
    current_offer = (request == current_expected
                     and any(str(page.document_id) == current_id for page in catalog.pages))
    selected = sorted([page.document_id for index, page in enumerate(catalog.pages)
        if should_read_page(page, request['questions'][f'page{index + 1}'],
                            response.answers[f'page{index + 1}'], semantic=True,
                            current_offer=current_offer, is_current=str(page.document_id) == current_id)], key=str)
    if selected != selection.document_ids:
        raise ValueError('Pending App choices differ from the actual read/skip votes')
    return tuple(selected)


def pending_conversation_route_can_admit(receipt, execution):
    """A pending Build may reuse its conversation, never new acquisition."""
    from . import types as t
    from .native_execution import NativeBuildSourceSettledV1
    receipt, execution = _pending_components(receipt, execution)
    _join_pending_source(receipt, execution)
    return not any(type(event) in (NativeBuildSourceSettledV1, BuildAppPageCatalogObservedV1,
        t.RelatedPagesSelection, t.RelatedPageRead) for event in execution.events)


def pending_retained_work(execution):
    """Select retained-only pending work, without granting reads or admission.

    Keep legacy conversation-work interpretation unchanged. A chat draft is an
    existing requested operation; its anchored form uses the same full retained
    closure as discussion, with current access and pointer checks at admission.
    """
    from . import types as t
    from .native_execution import BuildPendingExecutionV1
    from .native_corpus import prior_conversation_work
    from .build_intentional_response import validate_resolution_metadata
    if type(execution) is not BuildPendingExecutionV1:
        return None
    work = prior_conversation_work(execution.events, allow_discussion=True)
    if work is None:
        rows = [event for event in execution.events if type(event) is t.BuildRequestedWorkResolutionV1]
        if len(rows) != 1:
            return None
        work = rows[0]
        if (work.requested_work != 'draft_in_conversation'
                or work.resolution.get('source_scope') != 'anchored'
                or work.resolution.get('barrier') is not None):
            return None
    validate_resolution_metadata(work, execution.policy)
    return work


def validate_pending_retained_admission(execution, event):
    """Structural closure; only the locked capture owner can create this event."""
    from . import types as t
    from .native_execution import NativeBuildSourceSettledV1
    if type(event) is not t.BuildPriorBodyEvidenceAdmittedV3:
        raise ValueError('Pending retained context requires its full current closure codec')
    prefix = execution.events[:event.sequence]
    work = pending_retained_work(execution.model_copy(update={'events': prefix}))
    if (work is None or work.event_id != event.work_event_id
            or event.world_id != execution.policy.action.intent.world_id
            or event.presentation_policy not in {'retained_conversation_semantic_v3', 'retained_conversation_semantic_v4'}
            or any(isinstance(prior, t.BuildPriorBodyEvidenceAdmittedV1)
                or type(prior) in (NativeBuildSourceSettledV1, BuildAppPageCatalogObservedV1,
                    t.RelatedPagesSelection, t.RelatedPageRead) for prior in prefix)):
        raise ValueError('Pending retained context requires unique source-free conversation work')


def pending_source_free_terminal(execution):
    """Exact acknowledged non-evidence work; never a substitute for a lookup."""
    from . import types as t
    from .native_execution import (BuildPendingExecutionV1, NativeBuildSourceSettledV1,
        BuildAppPageCatalogObservedV1, native_read_event_ids)
    from .build_intentional_response import UNAVAILABLE, validate_resolution_metadata
    if type(execution) is not BuildPendingExecutionV1:
        return None
    work = [row for row in execution.events if type(row) is t.BuildRequestedWorkResolutionV1]
    if len(work) != 1:
        return None
    work = work[0]
    if work.requested_work not in {
            'clarify_request', 'clarify_creation', 'review_blank_lore_page', 'write_current_page',
            *UNAVAILABLE}:
        return None
    validate_resolution_metadata(work, execution.policy)
    if (work.requested_work in UNAVAILABLE
            and (work.resolution.get('barrier') != 'requested_executor_not_offered'
                 or work.resolution.get('source_scope') not in ('anchored', 'uncertain'))):
        return None
    if (work.requested_work == 'write_current_page'
            and (work.resolution.get('source_scope') != 'anchored'
                 or work.resolution.get('barrier') not in (None, 'current_page_target_absent'))):
        return None
    controllers = [row for row in execution.events[:work.sequence]
        if isinstance(row, t.ProviderAttemptAuthorizedEventV3)]
    outcomes = [row.outcome for row in execution.events[:work.sequence]
        if type(row) is t.ProviderOutcomeEventV1 and row.provider_attempt_id == work.controller_attempt_id]
    if (not controllers or controllers[-1].provider_attempt_id != work.controller_attempt_id
            or controllers[-1].envelope_sha256 != work.controller_envelope_sha256
            or outcomes[-1:] != ['response_received']
            or native_read_event_ids(execution.events)
            or any(type(row) in (NativeBuildSourceSettledV1, BuildAppPageCatalogObservedV1,
                    t.RelatedPagesSelection, t.RelatedPageRead)
                or isinstance(row, t.BuildPriorBodyEvidenceAdmittedV1) for row in execution.events)):
        return None
    return {'status': 'ready', 'reason': 'pending_source_free_' + work.requested_work}


def pending_native_terminal(execution):
    """Classify a stored native finish; never grant IO or writer dispatch."""
    from .native_execution import BuildPendingExecutionV1, NativeBuildSourceSettledV1
    from .native_retrieval import NativeRetrievalSelectedV1
    if type(execution) is not BuildPendingExecutionV1:
        return None
    if not any(type(e) is NativeBuildSourceSettledV1 for e in execution.events):
        return None
    choices = [e for e in execution.events if type(e) is NativeRetrievalSelectedV1]
    if not choices or choices[-1].operation != 'finish_retrieval':
        return None
    return dict(status='ready', reason='native_retrieval_finished')


def validate_pending_writer_selection_authorization(execution, event):
    from . import types as t
    from .writer_evidence_selection import native_body_catalog
    prefix = execution.model_copy(update={'events': execution.events[:event.sequence]})
    if (type(event) is not t.ProviderAttemptAuthorizedEventV5
            or event.context_phase != 'writer_selection' or pending_native_terminal(prefix) is None
            or (event.provider, event.model, event.api_mode) != execution.policy.provider_roles.controller.identity()
            or not native_body_catalog(prefix)
            or any(type(e) is t.ProviderAttemptAuthorizedEventV5 and e.context_phase == 'writer_selection'
                   or isinstance(e, t.BuildWriterEvidenceSelectionV1) for e in prefix.events)):
        raise ValueError('Pending writer selection requires its nonempty finished native catalog')


def validate_pending_writer_selection(execution, event):
    from . import types as t
    from .writer_evidence_selection import NATIVE_POLICY, native_body_catalog, digest, close_selection
    from .build_primary_context import validate_selection_origin
    if event.mode == 'empty_catalog':
        return validate_pending_empty_writer_selection(execution, event)
    prefix = execution.model_copy(update={'events': execution.events[:event.sequence]})
    catalog = native_body_catalog(prefix)
    controllers = [e for e in prefix.events if isinstance(e, t.ProviderAttemptAuthorizedEventV1)]
    latest = controllers[-1] if controllers else None
    if (type(event) is not t.BuildWriterEvidenceSelectionV2 or event.policy != NATIVE_POLICY
            or pending_native_terminal(prefix) != event.terminal_disposition or not catalog
            or event.catalog_sha256 != digest(catalog) or type(latest) is not t.ProviderAttemptAuthorizedEventV5
            or latest.context_phase != 'writer_selection'):
        raise ValueError('Pending native selection differs from its finished exact catalog')
    validate_selection_origin(execution, event)
    for field, expected in close_selection(catalog, event.judgments).items():
        if [str(v) for v in getattr(event, field)] != expected:
            raise ValueError('Pending native selection changed its whole-event evidence closure')


def validate_pending_empty_writer_selection(execution, event):
    from .build_pending_app_coverage import pending_app_writer_terminal
    from . import types as t
    from .writer_evidence_selection import NATIVE_POLICY, close_selection, digest
    prefix = execution.events[:event.sequence]
    controllers = [prior for prior in prefix if isinstance(prior, t.ProviderAttemptAuthorizedEventV1)]
    latest = controllers[-1] if controllers else None
    outcomes = [prior.outcome for prior in prefix if type(prior) is t.ProviderOutcomeEventV1
                and latest is not None and prior.provider_attempt_id == latest.provider_attempt_id]
    if (event.mode != 'empty_catalog' or event.policy != NATIVE_POLICY or event.catalog_sha256 != digest({})
            or event.judgments or event.controller_response_sha256 is not None or latest is None
            or latest.provider_attempt_id != event.controller_attempt_id
            or latest.envelope_sha256 != event.controller_envelope_sha256 or outcomes[-1:] != ['response_received']
            or not (any(type(prior) is t.BuildPriorBodyEvidenceAdmittedV3 for prior in prefix)
                or pending_source_free_terminal(execution.model_copy(update={'events': prefix}))
                or pending_app_writer_terminal(execution.model_copy(update={'events': prefix}))
                or pending_native_terminal(execution.model_copy(update={'events': prefix})))
            or any(isinstance(prior, t.BuildWriterEvidenceSelectionV1) for prior in prefix)):
        raise ValueError('Pending empty writer selection requires acknowledged source-free work or retained context')
    terminal = (pending_source_free_terminal(execution.model_copy(update={'events': prefix}))
        or pending_app_writer_terminal(execution.model_copy(update={'events': prefix}))
        or pending_native_terminal(execution.model_copy(update={'events': prefix})))
    if terminal is not None and event.terminal_disposition != terminal:
        raise ValueError('Pending empty selection differs from its source-free work terminal')
    from .writer_evidence_selection import native_body_catalog
    if native_body_catalog(execution.model_copy(update={'events': prefix})):
        raise ValueError('Pending empty selection cannot omit an acquired native catalog')
    for field, expected in close_selection({}, {}).items():
        if list(getattr(event, field)) != expected:
            raise ValueError('Pending empty selection cannot manufacture acquired evidence')


def pending_turn_owner(turn):
    """Validate a current pending parent; this grants no selected source reads."""
    from . import types as t
    from .native_context import BuildPendingContextReceiptV1
    from .native_execution import BuildPendingExecutionV1
    if (type(turn) is not t.Turn or turn.status != 'running'
            or type(turn.graph_context_receipt) is not BuildPendingContextReceiptV1
            or type(turn.graph_context_execution) is not BuildPendingExecutionV1):
        raise ValueError('Pending runtime requires its actual running Build owner')
    current = t.Turn.model_validate_json(turn.model_dump_json(by_alias=True))
    return current.graph_context_receipt, current.graph_context_execution


def validate_pending_writer_authorization(execution, event):
    from .build_pending_app_coverage import pending_app_writer_terminal
    from . import types as t
    from .native_execution import NativeBuildWriterAuthorizedV2, native_read_event_ids
    prefix = execution.events[:event.sequence]
    selected = [row for row in prefix if type(row) is t.BuildWriterEvidenceSelectionV2]
    if (type(event) is not NativeBuildWriterAuthorizedV2 or len(selected) != 1
            or not (any(type(row) is t.BuildPriorBodyEvidenceAdmittedV3 for row in prefix)
                or pending_source_free_terminal(execution.model_copy(update={'events': prefix}))
                or pending_app_writer_terminal(execution.model_copy(update={'events': prefix}))
                or pending_native_terminal(execution.model_copy(update={'events': prefix})))
            or (event.provider, event.model, event.api_mode) != execution.policy.provider_roles.writer.identity()
            or event.native_read_event_ids != native_read_event_ids(prefix)
            or any(type(row) is NativeBuildWriterAuthorizedV2 for row in prefix)
            or event.included_assertion_ids or event.included_relationship_ids or event.included_evidence_ref_ids
            or event.included_graph_event_ids or event.included_source_read_event_ids
            or getattr(event, 'included_source_reuse_event_ids', ())
            or event.compact_plan_editor_prose or event.compact_plan_graph_qualifications
            or event.deduplicate_plan_recap_prose):
        raise ValueError('Pending writer requires exact source-free or retained work and read inclusion')


def validate_pending_completion_binding(execution, event):
    from . import types as t
    from .native_execution import NativeBuildWriterAuthorizedV2
    prefix = execution.events[:event.sequence]
    writers = [row for row in prefix if type(row) is NativeBuildWriterAuthorizedV2]
    responses = [row for row in prefix if type(row) is t.ProviderOutcomeEventV1
        and row.outcome == 'response_received' and row.provider_attempt_id == event.provider_attempt_id]
    if (type(event) is not t.CompletionBindingEventV1 or len(writers) != 1 or len(responses) != 1
            or event.provider_attempt_id != writers[0].provider_attempt_id or event.claim_graph_event_ids
            or responses[0].sequence != event.sequence - 1
            or not responses[0].request_id or not responses[0].response_sha256
            or event.sequence != len(execution.events) - 1
            or any(type(row) is t.CompletionBindingEventV1 for row in prefix)):
        raise ValueError('Pending completion requires its final exact acknowledged writer response')
