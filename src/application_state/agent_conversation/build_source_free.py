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
            if any(page.world_id != policy.action.intent.world_id
                   or str(page.document_id) == str(work.source_basis.document_id)
                   for page in event.pages):
                raise ValueError("Pending App catalog contains a foreign World or current page")
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
    """Stored pending prefix closure, before its terminal owner is integrated."""
    receipt, execution = _pending_components(receipt, execution)
    _join_pending_turn_fields(receipt, execution, provenance, intent_fingerprint, completion, assistant_text)


def _join_pending_turn_fields(receipt, execution, provenance, intent_fingerprint, completion, assistant_text):
    from . import types as t
    from .native_context import _join_work_context
    _join_pending_source(receipt, execution)
    _join_work_context(receipt, provenance)
    if t.submitted_turn_intent_fingerprint_v2(execution.policy.action.intent) != intent_fingerprint:
        raise ValueError("Pending stored request fingerprint differs from admission")
    if completion is not None or assistant_text is not None:
        raise ValueError("Pending prefix has no registered terminal output owner")


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
    from . import types as t
    from .build_draft_context import validate_record_identity
    from .build_intentional_response import validate_turn_arguments
    receipt, execution = turn.graph_context_receipt, turn.graph_context_execution
    _join_pending_turn_fields(receipt, execution, turn.provenance,
        turn.submitted_intent_fingerprint_v2, turn.completion, turn.assistant_text)
    intent = execution.policy.action.intent
    if (turn.submitted_intent_fingerprint_v1 is not None
            or turn.world_id != intent.world_id or turn.user_text != intent.message
            or turn.conversation_id != receipt.conversation_observation.conversation_id
            or turn.provenance.surface_instance_id != intent.surface_instance_id
            or turn.play_context_receipt is not None or turn.status == 'completed'
            or turn.status in {'accepted', 'running'} and turn.completed_at is not None):
        raise ValueError("Stored pending Turn differs from its admitted request or lifecycle")
    validate_turn_arguments(execution, user_text=turn.user_text, turn_id=turn.turn_id, attempt=turn.attempt)
    for event in execution.events:
        if type(event) is t.BuildDraftContextCapturedV1:
            validate_record_identity(event.record, world_id=turn.world_id,
                conversation_id=turn.conversation_id, turn_id=turn.turn_id,
                attempt=turn.attempt, submitted_intent_fingerprint=turn.submitted_intent_fingerprint_v2,
                saved_basis=receipt.work_context.source_basis)


def pending_source_work(execution):
    """Select the one acknowledged evidence-seeking work; grants no IO itself."""
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
    if (work.resolution.get('barrier') is not None
            or work.resolution.get('source_scope') not in {'source_lookup', 'uncertain'}
            or work.requested_work in {'review_blank_lore_page', 'clarify_request', 'clarify_creation'}):
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


def pending_app_page_selection_input(receipt, execution, initial_request_json):
    """Build the later decision from exact prior model input and App aliases.

    The first request is supplied by its existing trace owner, not reconstructed
    from today's history. No pointer, page UUID, revision or execution metadata
    is copied into the model request. Titles remain untrusted navigation data.
    """
    receipt, execution = _pending_components(receipt, execution)
    _join_pending_source(receipt, execution)
    catalogs = [event for event in execution.events if type(event) is BuildAppPageCatalogObservedV1]
    pages = catalogs[0].pages if catalogs else None
    return _compile_pending_app_page_selection_input(receipt, execution, initial_request_json, pages)


def _compile_pending_app_page_selection_input(receipt, execution, initial_request_json, pages):
    from copy import deepcopy
    from hashlib import sha256
    from .source_writer_output import strict_json
    if not pages:
        raise ValueError('An absent or empty App catalog does not need a page-selection call')
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
        history.append({'user': row['user'], 'assistant': row['assistant'],
            **({'proposed_work': semantic_collaboration(row['proposed_work'])}
               if 'proposed_work' in row else {})})
    role = 'untrusted_saved_page_title_for_navigation_not_evidence'
    state = {'user_question': initial['state']['user_question'],
        'history': deepcopy(history),
        'current_page': {'title': interaction['current_page_title'], 'role': role},
        'saved_pages': [{'choice': f'page{i + 1}', 'title': page.title, 'role': role}
                        for i, page in enumerate(pages)]}
    from .build_related_pages import question_text
    questions = {f'page{i + 1}': {'type': 'choice', 'instructions': question_text(page, semantic=True),
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
    if strict_json(prepared_request_json) != expected:
        raise ValueError('Prepared App page selection changed its frozen dialogue, catalog or choices')
    validate_prepared(authorization, execution, prepared_request_json, host_phase='navigate')
    return expected
