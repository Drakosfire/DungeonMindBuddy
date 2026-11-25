"""Build-only observations before source verification; never evidence authority.

These host records grant no content access, verified revision, completeness, or
citation capability. Runtime registration belongs to the matching new receipt.
"""
from __future__ import annotations

from typing import Literal

from pydantic import Field, model_validator

from .native_statement_input import Strict


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
        if (type(event) is t.BuildDraftContextCapturedV1
                and event.record.snapshot.saved_basis() != work.source_basis.model_dump(mode="json", by_alias=True)):
            raise ValueError("Pending working draft differs from its frozen source basis")
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
