"""Transactional Application State service for World-scoped conversations."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from uuid import UUID, uuid4
from typing import TYPE_CHECKING

from pydantic import ValidationError

from application_state.agent_conversation import repository as repo
from application_state.agent_conversation.context_trace import (
    ContextTraceObservation,
    TraceSourcePassage,
    TraceHistoricalSourceReferenceV1,
    TurnContextTraceV1,
)
from application_state.agent_conversation.context_trace_store import (
    TurnContextTraceStore,
    append_source_passages_locked,
    close_context_trace_locked,
)
from application_state.agent_conversation.types import (
    ArchiveCommand,
    CompletedPlanAskPair,
    CompletionBindingEventV1,
    Conversation,
    ConversationCommand,
    ConversationCommandReceipt,
    CommandResolutionRequestV1,
    CommandResolutionRecordV1,
    OccupiedCommandProofV1,
    _fingerprint,
    Draft,
    DraftSave,
    DraftSubmit,
    DraftSubmitReceipt,
    GraphExecutionEventV1,
    GraphExecutionEventV2,
    LegacyImport,
    LegacyImportReceipt,
    PlanAskContextBasis,
    PlanWorldGraphExecutionV3,
    PlayRunTurnContextReceiptV2,
    SourceScopeExtensionEventV3,
    ValidatedGraphOperationEventV3,
    GraphExecutionEventV3,
    BuildGraphContextReceiptV1,
    BuildSectionReadAuthorizationV1,
    ValidatedBuildSectionReadV1,
    BuildSectionProviderInclusionV1,
    BuildSectionAnswerBindingV1,
    project_build_section_answer_bindings,
    validate_selected_source_binding,
    ProviderAttemptAuthorizedEventV1,
    ProviderAttemptAuthorizedEventV2,
    ProviderAttemptAuthorizedEventV3,
    ProviderOutcomeEventV1,
    RelatedRecapContextAuthorizationEventV2,
    RelatedRecapContextProviderInclusionEventV2,
    ReopenCommand,
    SourceReadAuthorizationEventV2,
    SubmittedTurnIntentV1,
    SubmittedTurnIntentV2,
    BuildGraphIntentV1,
    PlayGraphIntentV1, PlayWorldGraphExecutionV1, PlaySourceProviderInclusionV1,
    Turn,
    TurnClaimReceipt,
    TurnFailure,
    TurnResult,
    TurnSubmission,
    ValidatedGraphOperationEventV1,
    ValidatedRelatedRecapContextEventV2,
    ValidatedSourceReadEventV2,
    WorldPointer,
    request_fingerprint,
    submitted_turn_intent_fingerprint_v1,
    submitted_turn_intent_fingerprint_v2,
    turn_idempotency_fingerprint,
    validate_completion_against_receipt,
    validate_execution_completion,
    validate_related_recap_context_scope,
    _ask_graph_validation_inputs,
    validate_graph_provider_envelope,
)
from .rules_authority_reads import MixedCompletedTurnV1, TurnReadModel
from .rules_authority_completion import (
    MixedTurnResultV1, BuildRulesMixedTurnResultV1, NativeRulesMixedTurnResultV1,
    RulesCitedSourceTurnResultV1,
)
from .rules_authority_passages import RulesHistoricalPassageRequestV1, RulesHistoricalPassageV1
from application_state.cli import assert_at_head
from application_state.config import load_runtime_dsn
from application_state.errors import (
    ApplicationStateConflictError,
    ApplicationStateIntegrityError,
    ApplicationStateNotFoundError,
    ApplicationStateValidationError,
)
from application_state.unit_of_work import unit_of_work

if TYPE_CHECKING:
    from .rules_authority_types import RulesScopeV1
    from .rules_authority_events import (
        RulesToolAuthorizedV1, RulesProviderAuthorizedV1,
        RulesProviderIncludedV1, RulesProviderOutcomeV1,
    )
    from .rules_authority_store import RulesLedgerRecordV1
    from .rules_authority_runtime import RulesLocalReader, RulesLookupDeliveryV1

DEFAULT_TURN_CLAIM_LEASE_SECONDS = 60
MAX_TURN_CLAIM_LEASE_SECONDS = 300


def _now() -> datetime:
    return datetime.now(UTC)


def _world_id(world_id: str) -> str:
    if not world_id or not world_id.strip():
        raise ApplicationStateValidationError("verified world_id is required")
    if world_id != world_id.strip():
        raise ApplicationStateValidationError("world_id must not contain surrounding whitespace")
    return world_id


def _validate_turn_claim_lease(lease_seconds: int) -> None:
    if (
        isinstance(lease_seconds, bool)
        or not isinstance(lease_seconds, int)
        or not 1 <= lease_seconds <= MAX_TURN_CLAIM_LEASE_SECONDS
    ):
        raise ApplicationStateValidationError(
            f"turn claim lease must be between 1 and {MAX_TURN_CLAIM_LEASE_SECONDS} seconds"
        )


def _validate_source_passage_observations(
    execution,
    event: ValidatedSourceReadEventV2,
    passages: list[TraceSourcePassage] | None,
    *,
    trace_active: bool,
    trace_capture_status: str | None,
) -> list[TraceSourcePassage]:
    supplied = passages or []
    if not trace_active:
        if supplied:
            raise ApplicationStateValidationError("source passage capture requires an active turn trace")
        return []
    authorization = next(
        (
            item for item in execution.events
            if isinstance(item, SourceReadAuthorizationEventV2)
            and item.read_call_id == event.read_call_id
        ),
        None,
    )
    if authorization is None:
        raise ApplicationStateIntegrityError("validated source read has no persisted authorization")
    receipt_by_id = {item.source_read_id: item for item in event.receipts}
    expected_ids = {
        item.source_read_id for item in event.receipts
        if item.content_sha256 is not None and item.returned_chars > 0
    }
    if {item.source_read_id for item in supplied} != expected_ids:
        if not supplied and expected_ids and trace_capture_status == "incomplete":
            # The caller must suppress these bytes from model context; the trace
            # records its safe incompleteness code and the ledger keeps the read
            # receipt without making uncaptured text look inspectable.
            return []
        raise ApplicationStateValidationError(
            "active context trace requires the exact text for every content-bearing source receipt"
        )
    if len(supplied) != len(expected_ids):
        raise ApplicationStateValidationError("source passage observations must be unique")
    supplied_by_id = {item.source_read_id: item for item in supplied}
    for passage in supplied:
        receipt = receipt_by_id[passage.source_read_id]
        if (
            passage.source_read_event_id != event.event_id
            or passage.read_call_id != event.read_call_id
            or passage.world_id != authorization.world_id
            or passage.graph_revision != authorization.graph_revision
            or passage.anchor_id != receipt.anchor_id
            or passage.evidence_ref_id != receipt.evidence_ref_id
            or passage.source_artifact_id != receipt.source_artifact_id
            or passage.source_revision_id != receipt.source_revision_id
            or passage.line_start != receipt.line_start
            or passage.line_end != receipt.line_end
            or passage.outcome != receipt.outcome
            or passage.returned_chars != receipt.returned_chars
            or passage.content_sha256 != receipt.content_sha256
        ):
            raise ApplicationStateValidationError(
                "captured passage differs from its validated source-read receipt"
            )
    return [supplied_by_id[item.source_read_id] for item in event.receipts if item.source_read_id in supplied_by_id]


def _fingerprint_payload(payload: object) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _receipt_replay(
    conn,
    command: ConversationCommand,
    *,
    command_kind: str,
) -> ConversationCommandReceipt | None:
    found = repo.get_command_receipt(conn, command.world_id, command.command_id)
    if found is None:
        return None
    receipt, fingerprint = found
    if receipt.command_kind != command_kind or fingerprint != request_fingerprint(command):
        raise ApplicationStateConflictError(
            "conversation command ID was already used with a different binding"
        )
    return receipt


def _lock_pointer(conn, world_id: str) -> WorldPointer:
    repo.ensure_world_state(conn, world_id, _now())
    return repo.lock_world_state(conn, world_id)


def _expect_pointer(command: ConversationCommand, pointer: WorldPointer) -> None:
    if (
        pointer.revision != command.expected_pointer_revision
        or pointer.active_conversation_id != command.expected_active_conversation_id
    ):
        raise ApplicationStateConflictError(
            "World active conversation changed; refresh before retrying"
        )


def _archive_active(conn, pointer: WorldPointer, now: datetime) -> None:
    if pointer.active_conversation_id is None:
        return
    active = repo.lock_conversation(conn, pointer.world_id, pointer.active_conversation_id)
    if active is None or active.status != "active":
        raise ApplicationStateIntegrityError("World active pointer does not reference an active conversation")
    archived = repo.update_conversation_state(
        conn,
        world_id=pointer.world_id,
        conversation_id=active.conversation_id,
        expected_revision=active.revision,
        status="archived",
        next_turn_sequence=active.next_turn_sequence,
        now=now,
        archived_at=now,
    )
    if archived is None:
        raise ApplicationStateConflictError("active conversation changed while archiving")


def _ready_dsn() -> str:
    dsn = load_runtime_dsn()
    assert_at_head(dsn=dsn)
    return dsn


def _ordinary_mutation_turn(turn: TurnReadModel | None, conversation_id: UUID) -> Turn | None:
    if isinstance(turn, MixedCompletedTurnV1):
        if turn.envelope.conversation_id != conversation_id:
            raise ApplicationStateNotFoundError("turn not found in verified World conversation")
        raise ApplicationStateConflictError("completed mixed Rules answer cannot accept an ordinary mutation")
    return turn


def _validated_base_execution_locked(
    conn, turn: Turn, result: TurnResult, *, prepared_recovery: bool = False,
    mixed_output_context=None, native_output_verified=False,
):
    """Validate the unchanged base-domain completion without committing a Turn."""
    from .types import (
        BuildAuthoringCompletionV1,
        BuildImagePreparationCompletionV1,
        BuildActionControllerWriterPolicyV1,
        BuildCitedSourceActionControllerWriterPolicyV1,
    )

    from .types import PlayWorldGraphCompletionV1
    from .native_rules_output import NativeRulesNormalizedOutputV1
    if (isinstance(result.completion, PlayWorldGraphCompletionV1)
            and not native_output_verified
            and not isinstance(mixed_output_context, NativeRulesNormalizedOutputV1)):
        raise ApplicationStateValidationError("Native Play requires its actual producing-output proof owner before completion")
    execution = turn.graph_context_execution
    if isinstance(result, RulesCitedSourceTurnResultV1) and (
            mixed_output_context is None or not isinstance(getattr(execution, "policy", None),
                BuildCitedSourceActionControllerWriterPolicyV1)):
        raise ApplicationStateValidationError("Mixed base output proof requires atomic mixed acceptance and current Build source policy")
    if prepared_recovery and not isinstance(
        getattr(execution, "policy", None), BuildActionControllerWriterPolicyV1
    ):
        raise ApplicationStateValidationError(
            "Recovery requires the controller-selected Build action policy"
        )
    if execution is not None:
        if (
            result.completion is None
            or result.producing_provider_attempt_id is None
            or result.claim_graph_event_ids is None
        ):
            raise ApplicationStateValidationError(
                "execution completion requires a producing attempt and claim evidence binding"
            )
        if isinstance(
            execution.policy, BuildCitedSourceActionControllerWriterPolicyV1
        ) and (isinstance(result, RulesCitedSourceTurnResultV1) or not isinstance(
            result.completion,
            (BuildAuthoringCompletionV1, BuildImagePreparationCompletionV1),
        )):
            from .source_writer_output import validate_completion_proof

            try:
                if isinstance(result, RulesCitedSourceTurnResultV1):
                    from .rules_authority_output import validate_build_base_completion
                    rules_execution, output_proof, answer = mixed_output_context
                    validate_build_base_completion(result, turn, rules_execution=rules_execution,
                        output_proof=output_proof, answer=answer)
                else:
                    captured = conn.execute(
                        "SELECT payload FROM agent.turn_context_trace WHERE turn_id=%s AND attempt=%s",
                        (turn.turn_id, turn.attempt),
                    ).fetchone()
                    validate_completion_proof(result, turn, captured[0] if captured else {})
            except (ValueError, KeyError, TypeError, AttributeError) as exc:
                raise ApplicationStateValidationError(str(exc)) from exc
        payload = result.completion.model_dump(mode="json", by_alias=True)
        digest = hashlib.sha256(
            json.dumps(
                payload,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
                allow_nan=False,
            ).encode("utf-8")
        ).hexdigest()
        try:
            execution = project_build_section_answer_bindings(
                execution,
                result.completion,
                result.producing_provider_attempt_id,
                result.build_section_bindings,
            )
        except ValueError as exc:
            raise ApplicationStateValidationError(str(exc)) from exc
        binding = CompletionBindingEventV1(
            event_id=uuid4(),
            sequence=len(execution.events),
            kind="completion_binding",
            provider_attempt_id=result.producing_provider_attempt_id,
            completion_sha256=digest,
            claim_graph_event_ids=result.claim_graph_event_ids,
        )
        try:
            execution_type = type(execution)
            execution = execution_type.model_validate(
                execution.model_dump(mode="json", by_alias=True)
                | {
                    "events": [
                        *[
                            e.model_dump(mode="json", by_alias=True)
                            for e in execution.events
                        ],
                        binding.model_dump(mode="json", by_alias=True),
                    ]
                }
            )
            validate_execution_completion(
                result.completion,
                turn.graph_context_receipt,
                execution,
                result.producing_provider_attempt_id,
                result.claim_graph_event_ids,
            )
        except ValueError as exc:
            raise ApplicationStateValidationError(str(exc)) from exc
    if turn.graph_context_receipt is None:
        if result.completion is not None:
            raise ApplicationStateValidationError(
                "Graph completion requires a frozen context receipt"
            )
    else:
        if result.completion is None:
            raise ApplicationStateValidationError(
                "Graph receipt turn requires a completion envelope"
            )
        if execution is None:
            try:
                validate_completion_against_receipt(
                    result.completion, turn.graph_context_receipt
                )
            except ValueError as exc:
                raise ApplicationStateValidationError(str(exc)) from exc
    from .build_authoring import validate_stored_proposal

    validate_stored_proposal(conn, turn, result.completion)
    return execution


class AgentConversationService:
    """Stateless storage boundary. World verification belongs to the caller."""

    def get_world_pointer(self, world_id: str) -> WorldPointer:
        world_id = _world_id(world_id)
        dsn = _ready_dsn()
        with unit_of_work(dsn) as conn:
            found = repo.get_world_state(conn, world_id)
        return found or WorldPointer(
            world_id=world_id, active_conversation_id=None, revision=0
        )

    def get_active_conversation(self, world_id: str) -> Conversation | None:
        world_id = _world_id(world_id)
        dsn = _ready_dsn()
        with unit_of_work(dsn) as conn:
            pointer = repo.get_world_state(conn, world_id)
            active = repo.get_active_conversation(conn, world_id)
        if pointer is None or pointer.active_conversation_id is None:
            if active is not None:
                raise ApplicationStateIntegrityError("active conversation exists without a World pointer")
            return None
        if active is None or active.conversation_id != pointer.active_conversation_id:
            raise ApplicationStateIntegrityError("World active pointer has no matching conversation")
        return active

    def get_conversation(self, world_id: str, conversation_id: UUID) -> Conversation:
        world_id = _world_id(world_id)
        dsn = _ready_dsn()
        with unit_of_work(dsn) as conn:
            result = repo.get_conversation(conn, world_id, conversation_id)
        if result is None:
            raise ApplicationStateNotFoundError("conversation not found in verified World")
        return result

    def list_conversations(
        self,
        world_id: str,
        *,
        status: str | None = None,
        limit: int = 100,
    ) -> list[Conversation]:
        world_id = _world_id(world_id)
        if status not in {None, "active", "archived"}:
            raise ApplicationStateValidationError("invalid conversation status filter")
        if not 1 <= limit <= 500:
            raise ApplicationStateValidationError("conversation page limit must be between 1 and 500")
        dsn = _ready_dsn()
        with unit_of_work(dsn) as conn:
            return repo.list_conversations(conn, world_id, status=status, limit=limit)

    def get_new_conversation_receipt(self, command: ConversationCommand) -> ConversationCommandReceipt | None:
        """Read an exact original command receipt without creating World state."""
        _world_id(command.world_id)
        with unit_of_work(_ready_dsn()) as conn:
            conn.execute("SET TRANSACTION READ ONLY")
            receipt = _receipt_replay(conn, command, command_kind="new")
        if receipt is not None and (
            receipt.world_id != command.world_id or receipt.command_id != command.command_id
            or receipt.active_conversation_id != receipt.conversation_id
            or receipt.conversation_id == command.expected_active_conversation_id
            or receipt.pointer_revision <= command.expected_pointer_revision
        ):
            raise ApplicationStateIntegrityError("stored new conversation receipt is invalid")
        return receipt

    def get_command_resolution(self, request: CommandResolutionRequestV1) -> CommandResolutionRecordV1 | None:
        _world_id(request.original_command.world_id)
        with unit_of_work(_ready_dsn()) as conn:
            conn.execute("SET TRANSACTION READ ONLY")
            record = repo.get_command_resolution(conn, request.original_command.world_id, request.resolution_operation_id)
        if record is not None and record.resolution_request_fingerprint != request.fingerprint():
            raise ApplicationStateConflictError("resolution operation ID has a different binding")
        return record

    def resolve_new_conversation(self, request: CommandResolutionRequestV1, *, actor: str) -> CommandResolutionRecordV1:
        command = request.original_command
        _world_id(command.world_id)
        if not actor.strip():
            raise ApplicationStateValidationError("resolution actor is required")
        with unit_of_work(_ready_dsn()) as conn:
            pointer = _lock_pointer(conn, command.world_id)
            previous = repo.get_command_resolution(conn, command.world_id, request.resolution_operation_id)
            if previous is not None:
                if previous.resolution_request_fingerprint != request.fingerprint():
                    raise ApplicationStateConflictError("resolution operation ID has a different binding")
                return previous
            found = repo.get_command_receipt(conn, command.world_id, command.command_id)
            retired = repo.get_command_retirement(conn, command.world_id, command.command_id)
            if found is not None and retired is not None:
                raise ApplicationStateIntegrityError("successful and retired command coexist")
            if retired is not None:
                if retired.original_request_fingerprint != request_fingerprint(command):
                    raise ApplicationStateConflictError("retired command has a different binding")
                raise ApplicationStateConflictError("use_original_resolution_record")
            confirmed = occupied = None
            if found is not None:
                receipt, fingerprint = found
                if receipt.command_kind == "new" and fingerprint == request_fingerprint(command):
                    outcome = "confirmed"
                    confirmed = receipt
                else:
                    outcome = "submitted_binding_blocked"
                    occupied = OccupiedCommandProofV1(world_id=command.world_id, command_id=command.command_id,
                        command_kind=receipt.command_kind, request_fingerprint=fingerprint,
                        receipt_sha256=_fingerprint({"receipt": receipt.model_dump(mode="json"), "request_fingerprint": fingerprint}))
            else:
                if pointer.revision != request.expected_current_pointer_revision or pointer.active_conversation_id != request.expected_current_active_conversation_id:
                    raise ApplicationStateConflictError("World active conversation changed; refresh before resolving")
                outcome = "retired"
            try:
                record = CommandResolutionRecordV1.create(request=request,
                    original_request_fingerprint=request_fingerprint(command), resolution_request_fingerprint=request.fingerprint(),
                    observed_pointer=pointer, outcome=outcome, actor=actor, recorded_at=_now().isoformat(),
                    confirmed_receipt=confirmed, occupied_receipt=occupied,
                    retirement_operation_id=request.resolution_operation_id if outcome == "retired" else None)
            except ValidationError as exc:
                raise ApplicationStateIntegrityError("command resolution evidence is invalid") from exc
            return repo.insert_command_resolution(conn, record)

    def new_conversation(self, command: ConversationCommand) -> ConversationCommandReceipt:
        world_id = _world_id(command.world_id)
        dsn = _ready_dsn()
        now = _now()
        with unit_of_work(dsn) as conn:
            pointer = _lock_pointer(conn, world_id)
            retirement = repo.get_command_retirement(conn, world_id, command.command_id)
            if retirement is not None:
                if repo.get_command_receipt(conn, world_id, command.command_id) is not None:
                    raise ApplicationStateIntegrityError("successful and retired command coexist")
                if retirement.original_request_fingerprint != request_fingerprint(command):
                    raise ApplicationStateConflictError("retired command has a different binding")
                raise ApplicationStateConflictError("new_conversation_request_retired")
            replay = _receipt_replay(conn, command, command_kind="new")
            if replay is not None:
                return replay
            _expect_pointer(command, pointer)
            _archive_active(conn, pointer, now)
            conversation_id = uuid4()
            repo.insert_conversation(
                conn,
                conversation_id=conversation_id,
                world_id=world_id,
                status="active",
                revision=1,
                next_turn_sequence=1,
                now=now,
                archived_at=None,
            )
            new_pointer = repo.update_world_state(
                conn,
                world_id=world_id,
                active_conversation_id=conversation_id,
                pointer_revision=pointer.revision + 1,
                now=now,
            )
            return repo.insert_command_receipt(
                conn,
                world_id=world_id,
                command_id=command.command_id,
                command_kind="new",
                request_fingerprint=request_fingerprint(command),
                expected_pointer_revision=command.expected_pointer_revision,
                expected_active_conversation_id=command.expected_active_conversation_id,
                conversation_id=conversation_id,
                result_active_conversation_id=new_pointer.active_conversation_id,
                result_pointer_revision=new_pointer.revision,
                recorded_at=now,
            )

    def archive_conversation(self, command: ArchiveCommand) -> ConversationCommandReceipt:
        world_id = _world_id(command.world_id)
        dsn = _ready_dsn()
        now = _now()
        with unit_of_work(dsn) as conn:
            pointer = _lock_pointer(conn, world_id)
            if repo.get_command_retirement(conn, world_id, command.command_id) is not None:
                raise ApplicationStateConflictError("command ID is retired")
            replay = _receipt_replay(conn, command, command_kind="archive")
            if replay is not None:
                return replay
            _expect_pointer(command, pointer)
            if pointer.active_conversation_id != command.conversation_id:
                raise ApplicationStateConflictError("only the active conversation can be archived")
            _archive_active(conn, pointer, now)
            new_pointer = repo.update_world_state(
                conn,
                world_id=world_id,
                active_conversation_id=None,
                pointer_revision=pointer.revision + 1,
                now=now,
            )
            return repo.insert_command_receipt(
                conn,
                world_id=world_id,
                command_id=command.command_id,
                command_kind="archive",
                request_fingerprint=request_fingerprint(command),
                expected_pointer_revision=command.expected_pointer_revision,
                expected_active_conversation_id=command.expected_active_conversation_id,
                conversation_id=command.conversation_id,
                result_active_conversation_id=None,
                result_pointer_revision=new_pointer.revision,
                recorded_at=now,
            )

    def reopen_conversation(self, command: ReopenCommand) -> ConversationCommandReceipt:
        world_id = _world_id(command.world_id)
        dsn = _ready_dsn()
        now = _now()
        with unit_of_work(dsn) as conn:
            pointer = _lock_pointer(conn, world_id)
            if repo.get_command_retirement(conn, world_id, command.command_id) is not None:
                raise ApplicationStateConflictError("command ID is retired")
            replay = _receipt_replay(conn, command, command_kind="reopen")
            if replay is not None:
                return replay
            _expect_pointer(command, pointer)
            target = repo.lock_conversation(conn, world_id, command.conversation_id)
            if target is None:
                raise ApplicationStateNotFoundError("conversation not found in verified World")
            if target.status != "archived":
                raise ApplicationStateConflictError("only an archived conversation can be reopened")
            _archive_active(conn, pointer, now)
            reopened = repo.update_conversation_state(
                conn,
                world_id=world_id,
                conversation_id=target.conversation_id,
                expected_revision=target.revision,
                status="active",
                next_turn_sequence=target.next_turn_sequence,
                now=now,
                archived_at=None,
            )
            if reopened is None:
                raise ApplicationStateConflictError("archived conversation changed while reopening")
            new_pointer = repo.update_world_state(
                conn,
                world_id=world_id,
                active_conversation_id=target.conversation_id,
                pointer_revision=pointer.revision + 1,
                now=now,
            )
            return repo.insert_command_receipt(
                conn,
                world_id=world_id,
                command_id=command.command_id,
                command_kind="reopen",
                request_fingerprint=request_fingerprint(command),
                expected_pointer_revision=command.expected_pointer_revision,
                expected_active_conversation_id=command.expected_active_conversation_id,
                conversation_id=command.conversation_id,
                result_active_conversation_id=new_pointer.active_conversation_id,
                result_pointer_revision=new_pointer.revision,
                recorded_at=now,
            )

    def accept_turn(self, submission: TurnSubmission) -> TurnReadModel:
        world_id = _world_id(submission.world_id)
        if submission.provenance.world_id != world_id:
            raise ApplicationStateValidationError("turn provenance must match verified World")
        submitted_intent = submission.submitted_intent_v1
        submitted_intent_v2 = submission.submitted_intent_v2
        if submitted_intent is not None and (
            submitted_intent.world_id != world_id
            or submitted_intent.message != submission.user_text
        ):
            raise ApplicationStateValidationError(
                "submitted intent World/message must match the turn"
            )
        dsn = _ready_dsn()
        now = _now()
        fingerprint = request_fingerprint(submission)
        stable_fingerprint = turn_idempotency_fingerprint(
            world_id, submission.user_text, submission.provenance,
            submission.play_context_receipt,
        )
        submitted_intent_fingerprint = (
            None if submitted_intent is None else submitted_turn_intent_fingerprint_v1(submitted_intent)
        )
        submitted_intent_fingerprint_v2 = (
            None
            if submitted_intent_v2 is None
            else submitted_turn_intent_fingerprint_v2(submitted_intent_v2)
        )

        def matching_receipt(existing) -> TurnReadModel:
            (
                turn,
                _old_request_fingerprint,
                _old_idempotency_fingerprint,
                old_submitted_intent_fingerprint,
                old_submitted_intent_fingerprint_v2,
            ) = existing
            if isinstance(turn, MixedCompletedTurnV1):
                turn_meta = turn.envelope
                projection = turn.base_projection
                if projection.kind == "approved":
                    graph_receipt = projection.turn.graph_context_receipt
                    graph_execution = projection.turn.graph_context_execution
                elif projection.kind == "unclaimed":
                    graph_receipt = projection.graph_context_receipt
                    graph_execution = projection.graph_context_execution
                else:
                    graph_receipt = None
                    graph_execution = None
            else:
                turn_meta = turn
                graph_receipt = turn.graph_context_receipt
                graph_execution = turn.graph_context_execution
            if (
                turn_meta.play_context_receipt is not None
                and turn_meta.play_context_receipt != submission.play_context_receipt
            ):
                raise ApplicationStateConflictError(
                    "turn idempotency key was already used with a different Play context receipt"
                )
            if (
                old_submitted_intent_fingerprint is None
                and old_submitted_intent_fingerprint_v2 is None
            ):
                raise ApplicationStateConflictError(
                    "legacy-receipt-unverifiable: the stored turn has no submitted-intent fingerprint"
                )
            if submitted_intent_fingerprint is None and submitted_intent_fingerprint_v2 is None:
                raise ApplicationStateConflictError(
                    "turn idempotency key requires its submitted-intent fingerprint"
                )
            if submitted_intent_fingerprint is not None and (
                old_submitted_intent_fingerprint != submitted_intent_fingerprint
                or old_submitted_intent_fingerprint_v2 is not None
            ):
                raise ApplicationStateConflictError(
                    "turn idempotency key was already used with different submitted intent"
                )
            if submitted_intent_fingerprint_v2 is not None and (
                old_submitted_intent_fingerprint_v2 != submitted_intent_fingerprint_v2
                or old_submitted_intent_fingerprint is not None
                or graph_receipt != submission.graph_context_receipt
                or (
                    (graph_execution is None)
                    != (submission.graph_context_execution is None)
                )
                or (
                    graph_execution is not None
                    and submission.graph_context_execution is not None
                    and (
                        graph_execution.context_receipt_sha256
                        != submission.graph_context_execution.context_receipt_sha256
                        or graph_execution.policy
                        != submission.graph_context_execution.policy
                    )
                )
            ):
                raise ApplicationStateConflictError(
                    "turn idempotency key was already used with different submitted intent or Graph receipt"
                )
            return turn

        with unit_of_work(dsn) as conn:
            # Read the receipt before touching mutable pointer/CAS state. The
            # second read under the World pointer lock closes a concurrent
            # first-delivery race before any conversation revision advances.
            existing = repo.get_turn_by_world_key(
                conn, world_id, submission.idempotency_key
            )
            if existing is not None:
                return matching_receipt(existing)
            if submitted_intent_fingerprint is None and submitted_intent_fingerprint_v2 is None:
                raise ApplicationStateValidationError(
                    "submitted intent v1 is required for ordinary turn acceptance"
                )
            play_receipt = submission.play_context_receipt
            if isinstance(play_receipt, PlayRunTurnContextReceiptV2):
                # Acquire the Run lock before the conversation/pointer locks,
                # matching Trash's lock order. Existing receipts above remain
                # replayable after Trash; only new admissions are refused.
                if isinstance(submitted_intent_v2, PlayGraphIntentV1) or (
                        submitted_intent is not None and submitted_intent.schema_ == "dmb_play_rules_intent_v1"):
                    from .play_graph_persistence import lock_and_validate_native_play_basis
                    lock_and_validate_native_play_basis(conn, play_receipt)
                else:
                    run = conn.execute(
                        "SELECT world_id,lifecycle_status FROM play.run WHERE run_id=%s FOR UPDATE",
                        (play_receipt.run_id,),
                    ).fetchone()
                    if run is None or run[0] != world_id:
                        raise ApplicationStateNotFoundError("Play session is unavailable in this World")
                    if run[1] != "active":
                        raise ApplicationStateConflictError("Play session is in Trash")
            pointer = _lock_pointer(conn, world_id)
            existing = repo.get_turn_by_world_key(
                conn, world_id, submission.idempotency_key
            )
            if existing is not None:
                return matching_receipt(existing)
            if pointer.active_conversation_id != submission.conversation_id:
                raise ApplicationStateConflictError("conversation is no longer active in this World")
            conversation = repo.lock_conversation(conn, world_id, submission.conversation_id)
            if conversation is None:
                raise ApplicationStateNotFoundError("conversation not found in verified World")
            if conversation.status != "active":
                raise ApplicationStateConflictError("conversation is archived")
            advanced = repo.advance_conversation_for_turn(
                conn,
                world_id=world_id,
                conversation_id=conversation.conversation_id,
                expected_revision=submission.expected_conversation_revision,
                now=now,
            )
            if advanced is None:
                raise ApplicationStateConflictError("conversation revision mismatch")
            _, sequence = advanced
            return repo.insert_turn(
                conn,
                turn_id=uuid4(),
                request_fingerprint=fingerprint,
                idempotency_fingerprint=stable_fingerprint,
                submitted_intent_fingerprint_v1=submitted_intent_fingerprint,
                submitted_intent_fingerprint_v2=submitted_intent_fingerprint_v2,
                submission=submission,
                sequence=sequence,
                now=now,
            )

    def reconcile_turn(
        self,
        world_id: str,
        idempotency_key: UUID,
        submitted_intent: SubmittedTurnIntentV1 | SubmittedTurnIntentV2 | BuildGraphIntentV1 | PlayGraphIntentV1,
    ) -> TurnReadModel | None:
        """Find an exact World receipt before resolving mutable current context.

        A legacy receipt has no lossless submitted-intent identity and therefore
        fails closed. A missing receipt remains a normal new-turn path.
        """
        world_id = _world_id(world_id)
        if submitted_intent.world_id != world_id:
            raise ApplicationStateValidationError(
                "submitted intent World does not match verified World"
            )
        if isinstance(submitted_intent, (SubmittedTurnIntentV2, BuildGraphIntentV1, PlayGraphIntentV1)):
            digest_v1 = None
            digest_v2 = submitted_turn_intent_fingerprint_v2(submitted_intent)
        else:
            digest_v1 = submitted_turn_intent_fingerprint_v1(submitted_intent)
            digest_v2 = None
        dsn = _ready_dsn()
        with unit_of_work(dsn) as conn:
            existing = repo.get_turn_by_world_key(conn, world_id, idempotency_key)
        if existing is None:
            return None
        turn, _request_hash, _idempotency_hash, stored_digest, stored_digest_v2 = existing
        if stored_digest is None and stored_digest_v2 is None:
            raise ApplicationStateConflictError(
                "legacy-receipt-unverifiable: the stored turn has no submitted-intent fingerprint"
            )
        if (
            (digest_v1 is not None and stored_digest != digest_v1)
            or (digest_v2 is not None and stored_digest_v2 != digest_v2)
            or (digest_v1 is not None and stored_digest_v2 is not None)
            or (digest_v2 is not None and stored_digest is not None)
        ):
            raise ApplicationStateConflictError(
                "turn idempotency key was already used with different submitted intent"
            )
        return turn

    def inspect_turn(self, *, world_id: str, turn_id: UUID) -> TurnReadModel:
        """Load one historical turn in its verified World; no pointer/head lookup."""
        world_id = _world_id(world_id)
        with unit_of_work(_ready_dsn()) as conn:
            turn = repo.get_turn(conn, world_id, turn_id)
            if turn is None:
                raise ApplicationStateNotFoundError("turn not found in verified World")
            return turn

    def begin_rules_execution(self, scope: RulesScopeV1, *, expected_turn_revision: int) -> RulesLedgerRecordV1:
        """Internal parent port; caller already admitted current operator/World."""
        from .rules_authority_store import open_execution_locked
        with unit_of_work(_ready_dsn()) as conn:
            record = open_execution_locked(conn, scope, expected_turn_revision=expected_turn_revision)
        return record

    def authorize_rules_lookup(self, scope: RulesScopeV1, *, expected_turn_revision: int,
                               expected_ledger_revision: int, event: RulesToolAuthorizedV1) -> RulesLedgerRecordV1:
        """Commit exact call authority before the parent starts a local read."""
        from .rules_authority_events import RulesToolAuthorizedV1
        from .rules_authority_store import append_lookup_event_locked
        if not isinstance(event, RulesToolAuthorizedV1):
            raise ApplicationStateValidationError("Rules lookup requires a tool authorization")
        with unit_of_work(_ready_dsn()) as conn:
            record, _ = append_lookup_event_locked(conn, scope,
                expected_turn_revision=expected_turn_revision,
                expected_ledger_revision=expected_ledger_revision, event=event)
        return record

    def execute_rules_lookup(self, scope: RulesScopeV1, *, expected_turn_revision: int,
                             call_id: str, local_reader: RulesLocalReader) -> RulesLookupDeliveryV1:
        """Serialize/reload/read/seal; return source bytes only after commit.

        local_reader is an internal bounded local-source adapter, never model or
        HTTP input. It must not dispatch inference/network work under this lock.
        """
        from .rules_authority_runtime import execute_local_lookup_locked
        with unit_of_work(_ready_dsn()) as conn:
            delivery = execute_local_lookup_locked(conn, scope,
                expected_turn_revision=expected_turn_revision, call_id=call_id,
                local_reader=local_reader)
        return delivery

    def append_rules_provider_event(self, scope: RulesScopeV1, *, expected_turn_revision: int,
                                    expected_ledger_revision: int,
                                    event: RulesProviderAuthorizedV1 | RulesProviderIncludedV1 | RulesProviderOutcomeV1,
                                    prepared_request_json: str | None = None) -> RulesLedgerRecordV1:
        """Internal exact-input/lifecycle append; no dispatch permission on failure."""
        from .rules_authority_store import append_provider_event_locked
        with unit_of_work(_ready_dsn()) as conn:
            record, _ = append_provider_event_locked(conn, scope,
                expected_turn_revision=expected_turn_revision,
                expected_ledger_revision=expected_ledger_revision, event=event,
                prepared_request_json=prepared_request_json)
        return record

    def inspect_rules_passage(
        self, request: RulesHistoricalPassageRequestV1
    ) -> RulesHistoricalPassageV1:
        """Caller verifies current World/operator admission; inspect one cited capsule."""
        from .rules_authority_passages import read_historical_rules_passage

        if _world_id(request.world_id) != request.world_id:
            raise ApplicationStateValidationError(
                "Rules passage World must be canonical"
            )
        with unit_of_work(_ready_dsn()) as conn:
            return read_historical_rules_passage(conn, request)

    def list_turns(
        self,
        world_id: str,
        conversation_id: UUID,
        *,
        limit: int = 50,
        before_sequence: int | None = None,
    ) -> list[TurnReadModel]:
        world_id = _world_id(world_id)
        if not 1 <= limit <= 100:
            raise ApplicationStateValidationError("turn page limit must be between 1 and 100")
        if before_sequence is not None and before_sequence < 1:
            raise ApplicationStateValidationError("before_sequence must be positive")
        dsn = _ready_dsn()
        with unit_of_work(dsn) as conn:
            if repo.get_conversation(conn, world_id, conversation_id) is None:
                raise ApplicationStateNotFoundError("conversation not found in verified World")
            return repo.list_turns(
                conn,
                world_id,
                conversation_id,
                limit=limit,
                before_sequence=before_sequence,
            )

    def list_completed_plan_ask_context(
        self,
        verified_world_id: str,
        basis: PlanAskContextBasis,
        *,
        limit: int = 6,
    ) -> list[CompletedPlanAskPair]:
        """Read the newest eligible completed Ask pairs for an exact Plan basis."""

        world_id = _world_id(verified_world_id)
        if world_id != basis.world_id:
            raise ApplicationStateValidationError(
                "Plan Ask basis World must match the verified World"
            )
        if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 6:
            raise ApplicationStateValidationError(
                "Plan Ask context limit must be between 1 and 6"
            )
        dsn = _ready_dsn()
        with unit_of_work(dsn) as conn:
            return repo.list_completed_plan_ask_context(
                conn, world_id, basis, limit=limit
            )

    def begin_turn(self, world_id: str, conversation_id: UUID, turn_id: UUID, *, expected_revision: int) -> Turn:
        receipt = self.claim_turn(
            world_id,
            conversation_id,
            turn_id,
            expected_revision=expected_revision,
        )
        if receipt.disposition != "claimed":
            raise ApplicationStateConflictError(
                "turn claim is already pending or the turn is complete"
            )
        return receipt.turn

    def claim_turn(
        self,
        world_id: str,
        conversation_id: UUID,
        turn_id: UUID,
        *,
        expected_revision: int,
        lease_seconds: int = DEFAULT_TURN_CLAIM_LEASE_SECONDS,
    ) -> TurnClaimReceipt:
        world_id = _world_id(world_id)
        _validate_turn_claim_lease(lease_seconds)
        dsn = _ready_dsn()
        interrupted_after_dispatch = False
        interrupted_domain = "Graph"
        with unit_of_work(dsn) as conn:
            turn = repo.lock_turn(conn, world_id, turn_id)
            if isinstance(turn, MixedCompletedTurnV1):
                if turn.envelope.conversation_id != conversation_id:
                    raise ApplicationStateNotFoundError(
                        "turn not found in verified World conversation"
                    )
                return TurnClaimReceipt(disposition="completed", turn=turn)
            if turn is None or turn.conversation_id != conversation_id:
                raise ApplicationStateNotFoundError(
                    "turn not found in verified World conversation"
                )
            if turn.status == "completed":
                return TurnClaimReceipt(disposition="completed", turn=turn)
            now = repo.database_clock(conn)
            if (
                turn.status == "running"
                and turn.claim_expires_at is not None
                and turn.claim_expires_at > now
            ):
                return TurnClaimReceipt(disposition="pending", turn=turn)
            if turn.revision != expected_revision:
                raise ApplicationStateConflictError(
                    "turn claim fence changed before it could be acquired"
                )
            if turn.graph_context_execution is not None and any(
                isinstance(event, ProviderAttemptAuthorizedEventV1)
                for event in turn.graph_context_execution.events
            ):
                if turn.status == "running" and (
                    turn.claim_expires_at is None or turn.claim_expires_at <= now
                ):
                    execution = turn.graph_context_execution
                    auths = [
                        e
                        for e in execution.events
                        if isinstance(e, ProviderAttemptAuthorizedEventV1)
                    ]
                    latest = auths[-1]
                    outcomes = [
                        e
                        for e in execution.events
                        if isinstance(e, ProviderOutcomeEventV1)
                        and e.provider_attempt_id == latest.provider_attempt_id
                    ]
                    outcome_unknown = False
                    if not outcomes or outcomes[-1].outcome not in {
                        "response_received",
                        "known_not_sent",
                        "outcome_unknown",
                    }:
                        outcome_unknown = True
                        unknown = ProviderOutcomeEventV1(
                            event_id=uuid4(),
                            sequence=len(execution.events),
                            kind="provider_outcome",
                            provider_attempt_id=latest.provider_attempt_id,
                            outcome="outcome_unknown",
                        )
                        execution_type = type(execution)
                        execution = execution_type.model_validate(
                            execution.model_dump(mode="json", by_alias=True)
                            | {
                                "events": [
                                    *[
                                        e.model_dump(mode="json", by_alias=True)
                                        for e in execution.events
                                    ],
                                    unknown.model_dump(mode="json", by_alias=True),
                                ]
                            }
                        )
                    interrupted = repo.interrupt_expired_graph_execution(
                        conn,
                        world_id=world_id,
                        turn_id=turn_id,
                        expected_revision=expected_revision,
                        expected_attempt=turn.attempt,
                        execution=execution,
                        failure_code=(
                            "provider_outcome_unknown"
                            if outcome_unknown
                            else "provider_authorized_nonreclaimable"
                        ),
                    )
                    if interrupted is None:
                        raise ApplicationStateConflictError(
                            "expired Graph provider claim could not be fenced"
                        )
                    from .rules_authority_store import fail_execution_locked

                    fail_execution_locked(conn, turn)
                    interrupted_after_dispatch = True
                else:
                    raise ApplicationStateConflictError(
                        "Graph execution with a prior provider authorization cannot be reclaimed"
                    )
            if not interrupted_after_dispatch:
                from .rules_authority_store import (
                    load_turn_rules_locked,
                    fail_execution_locked,
                )
                from .rules_authority_events import (
                    RulesProviderAuthorizedV1,
                    RulesProviderOutcomeV1,
                )

                rules = load_turn_rules_locked(conn, turn)
                dispatches = (
                    [
                        event
                        for event in rules.execution.events
                        if isinstance(event, RulesProviderAuthorizedV1)
                    ]
                    if rules is not None
                    else []
                )
                if dispatches:
                    if turn.status != "running":
                        raise ApplicationStateConflictError(
                            "Rules execution with a prior provider authorization cannot be reclaimed"
                        )
                    latest = dispatches[-1]
                    outcomes = [
                        event
                        for event in rules.execution.events
                        if isinstance(event, RulesProviderOutcomeV1)
                        and event.provider_attempt_id == latest.provider_attempt_id
                    ]
                    unknown = not outcomes or outcomes[-1].status == "unknown"
                    fail_execution_locked(conn, turn)
                    interrupted = repo.interrupt_expired_rules_claim(
                        conn,
                        world_id=world_id,
                        turn_id=turn_id,
                        expected_revision=expected_revision,
                        expected_attempt=turn.attempt,
                        failure_code="rules_provider_outcome_unknown"
                        if unknown
                        else "rules_provider_authorized_nonreclaimable",
                    )
                    if interrupted is None:
                        raise ApplicationStateConflictError(
                            "expired Rules provider claim could not be fenced"
                        )
                    interrupted_after_dispatch = True
                    interrupted_domain = "Rules"
                elif rules is not None and rules.execution.state == "active":
                    # A new product attempt must never inherit old source cache or
                    # pending output authority, even when nothing was dispatched.
                    fail_execution_locked(conn, turn)
            if not interrupted_after_dispatch:
                if turn.status not in {"accepted", "failed", "interrupted", "running"}:
                    raise ApplicationStateConflictError(
                        "turn is not eligible for a runtime claim"
                    )
                if turn.status == "running" and (
                    turn.claim_expires_at is None or turn.claim_expires_at <= now
                ):
                    close_context_trace_locked(
                        conn,
                        world_id=world_id,
                        turn_id=turn_id,
                        attempt=turn.attempt,
                        status="interrupted",
                        closed_at=now,
                    )
                claimed = repo.claim_turn(
                    conn,
                    world_id=world_id,
                    turn_id=turn_id,
                    expected_revision=expected_revision,
                    lease_seconds=lease_seconds,
                )
                if claimed is None:
                    raise ApplicationStateConflictError(
                        "turn claim expired or changed while it was being acquired"
                    )
                return TurnClaimReceipt(disposition="claimed", turn=claimed)
        if interrupted_after_dispatch:
            raise ApplicationStateConflictError(
                f"expired {interrupted_domain} provider claim was recorded as potentially sent and cannot be reclaimed"
            )

    def _append_graph_execution_event(
        self,
        world_id: str,
        conversation_id: UUID,
        turn_id: UUID,
        *,
        expected_revision: int,
        expected_attempt: int,
        event: GraphExecutionEventV1 | GraphExecutionEventV2 | GraphExecutionEventV3,
        duplicate_key: str,
        source_passages: list[TraceSourcePassage] | None = None,
        build_source_markdown: str | None = None,
        writer_selection_proof: dict | None = None,
        native_play_prepared_request_json: str | None = None,
    ) -> tuple[Turn, bool]:
        world_id = _world_id(world_id)
        dsn = _ready_dsn()
        with unit_of_work(dsn) as conn:
            turn = repo.lock_turn(conn, world_id, turn_id)
            turn = _ordinary_mutation_turn(turn, conversation_id)
            if turn is None or turn.conversation_id != conversation_id:
                raise ApplicationStateNotFoundError("turn not found in verified World conversation")
            execution = turn.graph_context_execution
            if execution is None:
                raise ApplicationStateValidationError("turn has no Graph execution policy")
            if turn.status != "running" or turn.revision != expected_revision or turn.attempt != expected_attempt:
                raise ApplicationStateConflictError("Graph execution append is fenced by a stale claim")
            now = repo.database_clock(conn)
            if turn.claim_expires_at is None or turn.claim_expires_at <= now:
                raise ApplicationStateConflictError("Graph execution claim has expired")
            if isinstance(event, (BuildSectionReadAuthorizationV1, ValidatedBuildSectionReadV1)):
                receipt = turn.graph_context_receipt
                if (not isinstance(receipt, BuildGraphContextReceiptV1)
                        or event.source_basis != receipt.source_basis):
                    raise ApplicationStateValidationError("Saved section differs from frozen Build source")
                if isinstance(event, ValidatedBuildSectionReadV1):
                    from application_state.agent_conversation.build_section import exact_saved_section
                    try:
                        exact = exact_saved_section(build_source_markdown, receipt.source_basis.content_sha256,
                            event.line_start, event.line_end)
                    except (TypeError, ValueError, UnicodeError) as exc:
                        raise ApplicationStateValidationError("Immutable Build passage proof is unavailable or invalid") from exc
                    if event.text != exact:
                        raise ApplicationStateValidationError("Saved passage is not the exact immutable source slice")
            if isinstance(event, PlaySourceProviderInclusionV1):
                raise ApplicationStateValidationError("Native Play source inclusion requires its actual prepared-input proof owner")
            if native_play_prepared_request_json is not None:
                from .types import PlayWorldGraphContextReceiptV1
                from .play_graph_input import MAX_REQUEST_BYTES
                if (not isinstance(execution, PlayWorldGraphExecutionV1)
                        or not isinstance(turn.graph_context_receipt, PlayWorldGraphContextReceiptV1)
                        or not isinstance(event, ProviderAttemptAuthorizedEventV3)
                        or not isinstance(native_play_prepared_request_json, str)
                        or len(native_play_prepared_request_json.encode("utf-8")) > MAX_REQUEST_BYTES
                        or hashlib.sha256(native_play_prepared_request_json.encode("utf-8")).hexdigest() != event.envelope_sha256):
                    raise ApplicationStateValidationError("Native Play input snapshot differs from its owning provider")
            trace_row = conn.execute(
                "SELECT payload->>'capture_status' FROM agent.turn_context_trace "
                "WHERE turn_id=%s AND attempt=%s",
                (turn_id, expected_attempt),
            ).fetchone()
            trace_active = trace_row is not None
            trace_capture_status = trace_row[0] if trace_row is not None else None
            for prior in execution.events:
                # Inclusion and outcome events share the authorization attempt ID.
                # Only an earlier authorization can be its duplicate.
                if duplicate_key == "provider_attempt_id" and not isinstance(prior, ProviderAttemptAuthorizedEventV1):
                    continue
                if (isinstance(event, BuildSectionReadAuthorizationV1)
                        and duplicate_key == "read_id" and not isinstance(prior, BuildSectionReadAuthorizationV1)):
                    continue
                if getattr(prior, duplicate_key, None) == getattr(event, duplicate_key, None):
                    if (
                        isinstance(prior, ValidatedGraphOperationEventV1)
                        and isinstance(event, ValidatedGraphOperationEventV1)
                    ):
                        if isinstance(execution, (PlanWorldGraphExecutionV3, PlayWorldGraphExecutionV1)):
                            if prior == event:
                                return turn, False
                            raise ApplicationStateConflictError("Graph origin was reused with changed content")
                        if prior.request_arguments_sha256 == event.request_arguments_sha256:
                            return turn, False
                        raise ApplicationStateConflictError("Graph operation ID was reused with changed arguments")
                    if isinstance(prior, ValidatedSourceReadEventV2) and isinstance(event, ValidatedSourceReadEventV2):
                        if prior != event:
                            raise ApplicationStateConflictError("source-read event ID was reused with changed content")
                        source_observations = _validate_source_passage_observations(
                            execution, prior, source_passages, trace_active=trace_active,
                            trace_capture_status=trace_capture_status,
                        )
                        if trace_active and source_observations:
                            persisted = append_source_passages_locked(
                                conn, world_id=world_id, turn_id=turn_id, attempt=expected_attempt,
                                event_id=prior.event_id, passages=source_observations,
                            )
                            if persisted is None:
                                raise ApplicationStateIntegrityError("active context trace disappeared during source read")
                        elif source_observations:
                            raise ApplicationStateValidationError("source passage trace is not active")
                        return turn, False
                    if prior == event:
                        return turn, False
                    raise ApplicationStateConflictError("Graph execution event ID was reused with changed content")
            if isinstance(execution, PlanWorldGraphExecutionV3):
                from .rules_authority_store import load_turn_rules_locked
                from .rules_authority_events import RulesPlanPacketProviderAuthorizedV1
                rules = load_turn_rules_locked(conn, turn)
                writer = next((item for item in rules.execution.events
                    if isinstance(item, RulesPlanPacketProviderAuthorizedV1)), None) if rules else None
                if writer is not None and not (
                    isinstance(event, ProviderOutcomeEventV1)
                    and event.provider_attempt_id == writer.provider_attempt_id
                ):
                    raise ApplicationStateValidationError(
                        "Plan packet final writer forbids later Graph reads or providers"
                    )
            native_inclusion = None
            if native_play_prepared_request_json is not None:
                from .types import PlayWorldGraphContextReceiptV1
                from .play_graph_input import prove_play_source_input
                from .play_graph_source_owner import resolve_native_play_source_owner
                if (not isinstance(execution, PlayWorldGraphExecutionV1)
                        or not isinstance(turn.graph_context_receipt, PlayWorldGraphContextReceiptV1)
                        or not isinstance(event, ProviderAttemptAuthorizedEventV3)):
                    raise ApplicationStateValidationError("Native Play input proof requires its own provider/receipt/ledger")
                try:
                    native_inclusion = prove_play_source_input(turn.graph_context_receipt, execution, event,
                        prepared_request_json=native_play_prepared_request_json,
                        submission_id=turn.idempotency_key, original_message=turn.user_text, event_id=uuid4(),
                        owner_resolver=lambda frame: resolve_native_play_source_owner(conn, turn, frame))
                except ValueError as exc:
                    raise ApplicationStateValidationError(str(exc)) from exc
            if event.sequence != len(execution.events) + (1 if native_inclusion is not None else 0):
                raise ApplicationStateConflictError("Graph execution event sequence is stale")
            if isinstance(event, ProviderAttemptAuthorizedEventV1):
                receipt = turn.graph_context_receipt
                assert receipt is not None
                try:
                    validate_graph_provider_envelope(
                        _ask_graph_validation_inputs(receipt), execution, event
                    )
                except ValueError as exc:
                    raise ApplicationStateValidationError(str(exc)) from exc
            if trace_active and isinstance(event, ProviderAttemptAuthorizedEventV3):
                payload = conn.execute(
                    "SELECT payload FROM agent.turn_context_trace WHERE turn_id=%s AND attempt=%s",
                    (turn_id, expected_attempt),
                ).fetchone()[0]
                captured = {(item.get("source_read_event_id"), item.get("source_read_id"), item.get("content_sha256"))
                            for item in payload["observations"] if item.get("kind") == "source_passage"}
                for read_event in execution.events:
                    if isinstance(read_event, ValidatedSourceReadEventV2) and read_event.event_id in event.included_source_read_event_ids:
                        if any(read.returned_chars and (str(read_event.event_id), read.source_read_id, read.content_sha256) not in captured for read in read_event.receipts):
                            raise ApplicationStateValidationError("provider inclusion requires captured source passages")
            if isinstance(event, ValidatedGraphOperationEventV1):
                receipt = turn.graph_context_receipt
                assert receipt is not None
                if event.graph_revision != receipt.graph_authority.graph_revision:
                    raise ApplicationStateValidationError("Graph operation event must use the frozen Graph revision")
            source_observations: list[TraceSourcePassage] = []
            if isinstance(event, ValidatedSourceReadEventV2):
                source_observations = _validate_source_passage_observations(
                    execution, event, source_passages, trace_active=trace_active,
                    trace_capture_status=trace_capture_status,
                )
            elif source_passages:
                raise ApplicationStateValidationError("passage observations require a validated source-read event")
            from .types import BuildWriterEvidenceSelectionV1
            if isinstance(event, BuildWriterEvidenceSelectionV1):
                from .writer_evidence_selection import validate_selection_proof
                captured = conn.execute(
                    "SELECT payload FROM agent.turn_context_trace WHERE turn_id=%s AND attempt=%s",
                    (turn.turn_id, turn.attempt),
                ).fetchone()
                try:
                    validate_selection_proof(turn, event, captured[0] if captured else {}, writer_selection_proof)
                except (ValueError, KeyError, TypeError, AttributeError) as exc:
                    raise ApplicationStateValidationError(str(exc)) from exc
            events = [*execution.events, *([native_inclusion] if native_inclusion is not None else []), event]
            try:
                execution_type = type(execution)
                updated_execution = execution_type.model_validate(
                    execution.model_dump(mode="json", by_alias=True) | {"events": [e.model_dump(mode="json", by_alias=True) for e in events]}
                )
                if turn.graph_context_receipt is not None:
                    validate_related_recap_context_scope(
                        turn.graph_context_receipt, updated_execution
                    )
                    validate_selected_source_binding(turn.graph_context_receipt, updated_execution)
            except ValueError as exc:
                raise ApplicationStateValidationError(str(exc)) from exc
            updated = repo.update_graph_execution(
                conn, world_id=world_id, turn_id=turn_id,
                expected_revision=expected_revision, execution=updated_execution,
            )
            if (
                updated is not None and isinstance(event, ValidatedSourceReadEventV2)
                and trace_active and source_observations
            ):
                persisted = append_source_passages_locked(
                    conn, world_id=world_id, turn_id=turn_id, attempt=expected_attempt,
                    event_id=event.event_id, passages=source_observations,
                )
                if persisted is None:
                    raise ApplicationStateIntegrityError("active context trace disappeared during source read")
        if updated is None:
            raise ApplicationStateConflictError("Graph execution append lost its claim fence")
        return updated, True

    def append_validated_graph_operation(
        self, world_id: str, conversation_id: UUID, turn_id: UUID, *,
        expected_revision: int, expected_attempt: int,
        operation_event: ValidatedGraphOperationEventV1 | ValidatedGraphOperationEventV3,
    ) -> tuple[Turn, bool]:
        return self._append_graph_execution_event(
            world_id, conversation_id, turn_id, expected_revision=expected_revision,
            expected_attempt=expected_attempt, event=operation_event, duplicate_key="operation_id",
        )

    def extend_source_scope(
        self, world_id: str, conversation_id: UUID, turn_id: UUID, *,
        expected_revision: int, expected_attempt: int,
        extension: SourceScopeExtensionEventV3,
    ) -> tuple[Turn, bool]:
        """Admit only exact earlier parent-validated origin pins under the live claim."""
        return self._append_graph_execution_event(
            world_id, conversation_id, turn_id, expected_revision=expected_revision,
            expected_attempt=expected_attempt, event=extension, duplicate_key="event_id",
        )

    def authorize_provider_attempt(
        self, world_id: str, conversation_id: UUID, turn_id: UUID, *,
        expected_revision: int, expected_attempt: int,
        provider_attempt_event: ProviderAttemptAuthorizedEventV1,
    ) -> tuple[Turn, bool]:
        """A True result is a fresh durable one-shot dispatch authorization."""
        return self._append_graph_execution_event(
            world_id, conversation_id, turn_id, expected_revision=expected_revision,
            expected_attempt=expected_attempt, event=provider_attempt_event,
            duplicate_key="provider_attempt_id",
        )

    def record_build_jev_action_selection(self, world_id, conversation_id, turn_id, *,
            expected_revision, expected_attempt, selection):
        from .types import BuildJevActionSelectionV1
        if not isinstance(selection, BuildJevActionSelectionV1):
            raise ApplicationStateValidationError("A typed Build selection is required")
        return self._append_graph_execution_event(world_id, conversation_id, turn_id,
            expected_revision=expected_revision, expected_attempt=expected_attempt,
            event=selection, duplicate_key="event_id")

    def record_build_writer_evidence_selection(self, world_id, conversation_id, turn_id, *,
            expected_revision, expected_attempt, selection, producer_proof=None):
        from .types import BuildWriterEvidenceSelectionV1
        if not isinstance(selection, BuildWriterEvidenceSelectionV1):
            raise ApplicationStateValidationError("A typed writer evidence selection is required")
        return self._append_graph_execution_event(world_id, conversation_id, turn_id,
            expected_revision=expected_revision, expected_attempt=expected_attempt,
            event=selection, duplicate_key="event_id", writer_selection_proof=producer_proof)

    def record_provider_outcome(
        self, world_id: str, conversation_id: UUID, turn_id: UUID, *,
        expected_revision: int, expected_attempt: int,
        outcome: ProviderOutcomeEventV1,
    ) -> tuple[Turn, bool]:
        return self._append_graph_execution_event(
            world_id, conversation_id, turn_id, expected_revision=expected_revision,
            expected_attempt=expected_attempt, event=outcome, duplicate_key="event_id",
        )

    def record_build_section_inclusion(
        self, world_id: str, conversation_id: UUID, turn_id: UUID, *,
        expected_revision: int, expected_attempt: int, inclusion: BuildSectionProviderInclusionV1,
    ) -> tuple[Turn, bool]:
        return self._append_graph_execution_event(world_id, conversation_id, turn_id,
            expected_revision=expected_revision, expected_attempt=expected_attempt,
            event=inclusion, duplicate_key="event_id")

    def authorize_build_section_read(
        self, world_id: str, conversation_id: UUID, turn_id: UUID, *,
        expected_revision: int, expected_attempt: int,
        authorization: BuildSectionReadAuthorizationV1,
    ) -> tuple[Turn, bool]:
        return self._append_graph_execution_event(world_id, conversation_id, turn_id,
            expected_revision=expected_revision, expected_attempt=expected_attempt,
            event=authorization, duplicate_key="read_id")

    def record_validated_build_section(
        self, world_id: str, conversation_id: UUID, turn_id: UUID, *,
        expected_revision: int, expected_attempt: int,
        receipt: ValidatedBuildSectionReadV1, source_markdown: str,
    ) -> tuple[Turn, bool]:
        return self._append_graph_execution_event(world_id, conversation_id, turn_id,
            expected_revision=expected_revision, expected_attempt=expected_attempt,
            event=receipt, duplicate_key="event_id", build_source_markdown=source_markdown)

    def authorize_source_read(
        self, world_id: str, conversation_id: UUID, turn_id: UUID, *,
        expected_revision: int, expected_attempt: int,
        authorization: SourceReadAuthorizationEventV2,
    ) -> tuple[Turn, bool]:
        """Persist the one-shot source-read authorization before the external read."""
        return self._append_graph_execution_event(
            world_id, conversation_id, turn_id, expected_revision=expected_revision,
            expected_attempt=expected_attempt, event=authorization,
            duplicate_key="read_call_id",
        )

    def record_validated_source_read(
        self, world_id: str, conversation_id: UUID, turn_id: UUID, *,
        expected_revision: int, expected_attempt: int,
        receipt: ValidatedSourceReadEventV2,
        source_passages: list[TraceSourcePassage] | None = None,
    ) -> tuple[Turn, bool]:
        """Persist the validated receipt and optional exact trace passages atomically."""
        return self._append_graph_execution_event(
            world_id, conversation_id, turn_id, expected_revision=expected_revision,
            expected_attempt=expected_attempt, event=receipt,
            duplicate_key="event_id", source_passages=source_passages,
        )

    def start_context_trace(
        self, *, world_id: str, conversation_id: UUID, turn_id: UUID,
        expected_revision: int, attempt: int, trace_id: UUID, started_at: datetime,
    ) -> TurnContextTraceV1:
        """Start optional trace capture under the active turn claim."""
        return TurnContextTraceStore().begin(
            world_id=_world_id(world_id), conversation_id=conversation_id,
            turn_id=turn_id, expected_revision=expected_revision, attempt=attempt,
            trace_id=trace_id, started_at=started_at,
        )

    def append_context_trace(
        self, *, world_id: str, conversation_id: UUID, turn_id: UUID,
        expected_revision: int, attempt: int, trace_id: UUID,
        observation: ContextTraceObservation,
    ) -> TurnContextTraceV1:
        return TurnContextTraceStore().append(
            world_id=_world_id(world_id), conversation_id=conversation_id,
            turn_id=turn_id, expected_revision=expected_revision, attempt=attempt,
            trace_id=trace_id, observation=observation,
        )

    def mark_context_trace_incomplete(
        self, *, world_id: str, conversation_id: UUID, turn_id: UUID,
        expected_revision: int, attempt: int, trace_id: UUID, failure_code: str,
    ) -> TurnContextTraceV1:
        return TurnContextTraceStore().mark_incomplete(
            world_id=_world_id(world_id), conversation_id=conversation_id,
            turn_id=turn_id, expected_revision=expected_revision, attempt=attempt,
            trace_id=trace_id, failure_code=failure_code,
        )

    def read_historical_source_passage(self, reference: TraceHistoricalSourceReferenceV1) -> TraceSourcePassage:
        return TurnContextTraceStore().read_historical_passage(reference)

    def list_context_trace_attempts(
        self, *, world_id: str, turn_id: UUID,
    ) -> list[TurnContextTraceV1]:
        return TurnContextTraceStore().list_attempts(
            world_id=_world_id(world_id), turn_id=turn_id,
        )

    def authorize_related_recap_context(
        self, world_id: str, conversation_id: UUID, turn_id: UUID, *,
        expected_revision: int, expected_attempt: int,
        authorization: RelatedRecapContextAuthorizationEventV2,
    ) -> tuple[Turn, bool]:
        """Persist the parent-authorized context scope before the Buddy read."""
        return self._append_graph_execution_event(
            world_id, conversation_id, turn_id, expected_revision=expected_revision,
            expected_attempt=expected_attempt, event=authorization,
            duplicate_key="read_call_id",
        )

    def record_validated_related_recap_context(
        self, world_id: str, conversation_id: UUID, turn_id: UUID, *,
        expected_revision: int, expected_attempt: int,
        result: ValidatedRelatedRecapContextEventV2,
    ) -> tuple[Turn, bool]:
        """Persist context-read metadata without passage text or continuation tokens."""
        return self._append_graph_execution_event(
            world_id, conversation_id, turn_id, expected_revision=expected_revision,
            expected_attempt=expected_attempt, event=result, duplicate_key="event_id",
        )

    def record_related_recap_context_inclusion(
        self, world_id: str, conversation_id: UUID, turn_id: UUID, *,
        expected_revision: int, expected_attempt: int,
        inclusion: RelatedRecapContextProviderInclusionEventV2,
    ) -> tuple[Turn, bool]:
        """Persist context inclusion before its matching provider authorization."""
        return self._append_graph_execution_event(
            world_id, conversation_id, turn_id, expected_revision=expected_revision,
            expected_attempt=expected_attempt, event=inclusion, duplicate_key="event_id",
        )

    def authorize_provider_attempt_v2(
        self, world_id: str, conversation_id: UUID, turn_id: UUID, *,
        expected_revision: int, expected_attempt: int,
        provider_attempt_event: ProviderAttemptAuthorizedEventV2,
    ) -> tuple[Turn, bool]:
        """Authorize a V2 provider envelope that may include validated source reads."""
        return self._append_graph_execution_event(
            world_id, conversation_id, turn_id, expected_revision=expected_revision,
            expected_attempt=expected_attempt, event=provider_attempt_event,
            duplicate_key="provider_attempt_id",
        )

    def authorize_native_play_provider(
        self, world_id: str, conversation_id: UUID, turn_id: UUID, *,
        expected_revision: int, expected_attempt: int,
        provider_attempt_event: ProviderAttemptAuthorizedEventV3,
        prepared_request_json: str,
    ) -> tuple[Turn, bool]:
        """Atomically commit exact Play source inclusion + provider authorization.

        A fresh=False replay is not another SDK send permission. The caller also
        owns the general actual-envelope validation and Rules-domain fence.
        """
        if not isinstance(prepared_request_json, str):
            raise ApplicationStateValidationError("Native Play requires its actual prepared input snapshot")
        return self._append_graph_execution_event(
            world_id, conversation_id, turn_id, expected_revision=expected_revision,
            expected_attempt=expected_attempt, event=provider_attempt_event,
            duplicate_key="provider_attempt_id", native_play_prepared_request_json=prepared_request_json,
        )

    def renew_turn_claim(
        self,
        world_id: str,
        conversation_id: UUID,
        turn_id: UUID,
        *,
        expected_revision: int,
        lease_seconds: int = DEFAULT_TURN_CLAIM_LEASE_SECONDS,
    ) -> Turn:
        world_id = _world_id(world_id)
        _validate_turn_claim_lease(lease_seconds)
        dsn = _ready_dsn()
        with unit_of_work(dsn) as conn:
            turn = repo.lock_turn(conn, world_id, turn_id)
            turn = _ordinary_mutation_turn(turn, conversation_id)
            if turn is None or turn.conversation_id != conversation_id:
                raise ApplicationStateNotFoundError(
                    "turn not found in verified World conversation"
                )
            renewed = repo.renew_turn_claim(
                conn,
                world_id=world_id,
                turn_id=turn_id,
                expected_revision=expected_revision,
                lease_seconds=lease_seconds,
            )
        if renewed is None:
            raise ApplicationStateConflictError(
                "turn claim is expired or fenced by a newer attempt"
            )
        return renewed

    def complete_turn(self, result: TurnResult) -> Turn:
        return self._complete_turn(result, prepared_recovery=False)

    def complete_native_base_turn(self, result: TurnResult, *, output_proof,
                                  expected_rules_revision: int) -> Turn:
        """Accept a captured native answer and close its unused Rules scope atomically."""
        return self._complete_turn(result, prepared_recovery=False,
            native_output_proof=output_proof, expected_rules_revision=expected_rules_revision)

    def recover_prepared_build_turn(self, result: TurnResult) -> Turn:
        """Recover an immutable acknowledged proposal, never a provider claim."""
        return self._complete_turn(result, prepared_recovery=True)

    def _complete_turn(self, result: TurnResult, *, prepared_recovery: bool,
                       native_output_proof=None, expected_rules_revision=None) -> Turn:
        from .types import BuildAuthoringCompletionV1, BuildImagePreparationCompletionV1
        if prepared_recovery and not isinstance(result.completion, (BuildAuthoringCompletionV1, BuildImagePreparationCompletionV1)):
            raise ApplicationStateValidationError("Recovery requires a typed prepared Build proposal")
        world_id = _world_id(result.world_id)
        dsn = _ready_dsn()
        with unit_of_work(dsn) as conn:
            turn = repo.lock_turn(conn, world_id, result.turn_id)
            turn = _ordinary_mutation_turn(turn, result.conversation_id)
            if turn is None or turn.conversation_id != result.conversation_id:
                raise ApplicationStateNotFoundError("turn not found in verified World conversation")
            if turn.status == "completed":
                stored_binding = None
                if turn.graph_context_execution is not None:
                    stored_binding = next(
                        (
                            event
                            for event in turn.graph_context_execution.events
                            if isinstance(event, CompletionBindingEventV1)
                        ),
                        None,
                    )
                if (
                    turn.assistant_text == result.assistant_text
                    and turn.completion == result.completion
                    and [item for event in (turn.graph_context_execution.events if turn.graph_context_execution else [])
                        if isinstance(event, BuildSectionAnswerBindingV1) for item in event.bindings] == result.build_section_bindings
                    and turn.revision == result.expected_revision + 1
                    and (
                        turn.graph_context_execution is None
                        or (
                            stored_binding is not None
                            and stored_binding.provider_attempt_id == result.producing_provider_attempt_id
                            and stored_binding.claim_graph_event_ids == result.claim_graph_event_ids
                        )
                    )
                ):
                    return turn
                raise ApplicationStateConflictError(
                    "completed turn has a different recorded result or a different claim fence"
                )
            allowed_status = {"running", "interrupted"} if prepared_recovery else {"running"}
            if turn.revision != result.expected_revision or turn.status not in allowed_status:
                raise ApplicationStateConflictError("turn revision or lifecycle state changed")
            native_output_verified = False
            if native_output_proof is not None:
                from .native_rules_output import NativeRulesOutputProofV1, normalize_unused_native_output
                from .rules_authority_store import load_turn_rules_locked
                current = load_turn_rules_locked(conn, turn)
                if (current is None or current.revision != expected_rules_revision
                        or not isinstance(native_output_proof, NativeRulesOutputProofV1)):
                    raise ApplicationStateConflictError("Native completion differs from its Rules ledger")
                try:
                    completion, bindings, text = normalize_unused_native_output(
                        turn, current.execution, native_output_proof)
                    if (completion != result.completion or bindings != result.claim_graph_event_ids
                            or text != result.assistant_text or result.producing_provider_attempt_id
                                != (native_output_proof.producing_provider_attempt_id
                                    if completion is not None else None)):
                        raise ValueError("Native result differs from its actual captured output")
                except (ValueError, KeyError, TypeError, AttributeError, UnicodeError) as exc:
                    raise ApplicationStateValidationError(str(exc)) from exc
                native_output_verified = True
            execution = _validated_base_execution_locked(conn, turn, result,
                prepared_recovery=prepared_recovery, native_output_verified=native_output_verified)
            from .rules_authority_store import close_unused_locked
            close_unused_locked(conn, turn)
            completion_update = repo.complete_prepared_build_turn if prepared_recovery else repo.complete_claimed_turn
            updated = completion_update(
                conn,
                world_id=world_id,
                turn_id=turn.turn_id,
                expected_revision=result.expected_revision,
                expected_attempt=turn.attempt,
                assistant_text=result.assistant_text,
                completion=result.completion,
                graph_context_execution=execution,
            )
            if updated is None:
                raise ApplicationStateConflictError(
                    "turn claim expired or was fenced before completion"
                )
        return updated

    def complete_mixed_turn(self, result: MixedTurnResultV1) -> MixedCompletedTurnV1:
        """Accept both domains in one transaction; replay before live-claim gates."""
        from .rules_authority_completion import prepare_rules_acceptance
        from .rules_authority_store import (
            load_turn_rules_locked,
            persist_accepted_locked,
        )
        from .rules_authority_types import RulesScopeV1, canonical_sha256

        from .rules_authority_policy import capability_for_policy_sha256
        from .rules_authority_output import (
            MAX_REQUEST_BYTES,
            parse_answer,
            verify_build_output,
        )
        from .rules_authority_types import RulesSupportRefV1

        scope = result.scope
        world_id = _world_id(scope.world_id)
        if (capability_for_policy_sha256(scope.capability_policy_sha256) is not None
                and not isinstance(result, (BuildRulesMixedTurnResultV1, NativeRulesMixedTurnResultV1))):
            raise ApplicationStateValidationError("Current runtime Rules completion requires actual outer output proof")
        with unit_of_work(_ready_dsn()) as conn:
            turn = repo.lock_turn(conn, world_id, scope.turn_id)
            if isinstance(turn, MixedCompletedTurnV1):
                if turn.envelope.conversation_id != scope.conversation_id:
                    raise ApplicationStateNotFoundError(
                        "turn not found in verified World conversation"
                    )
                # Read only frozen scope metadata, never source bodies on replay.
                frozen = conn.execute(
                    """SELECT revision,CASE WHEN octet_length((payload->'scope')::text)<=4096
                    THEN payload->'scope' ELSE NULL END FROM agent.turn_rules_execution
                    WHERE turn_id=%s AND product_attempt=%s""",
                    (scope.turn_id, scope.product_attempt),
                ).fetchone()
                try:
                    exact_scope = (
                        RulesScopeV1.model_validate_json(json.dumps(frozen[1]))
                        if frozen and frozen[1] is not None
                        else None
                    )
                except ValueError as exc:
                    raise ApplicationStateIntegrityError(
                        "accepted Rules scope is malformed"
                    ) from exc
                if exact_scope is None:
                    raise ApplicationStateIntegrityError(
                        "accepted Rules scope is missing or oversized"
                    )
                binding = turn.accepted_binding
                if (
                    exact_scope.world_id,
                    exact_scope.conversation_id,
                    exact_scope.turn_id,
                    exact_scope.product_attempt,
                    exact_scope.execution_id,
                    exact_scope.corpus_sha256,
                    exact_scope.ruleset_id,
                ) != (
                    binding.world_id,
                    binding.conversation_id,
                    binding.turn_id,
                    binding.product_attempt,
                    binding.execution_id,
                    binding.corpus_sha256,
                    binding.ruleset_id,
                ):
                    raise ApplicationStateIntegrityError(
                        "accepted Rules scope differs from its sealed binding"
                    )
                base = turn.base_projection
                base_matches = (
                    result.base_result is None
                    if base.kind != "approved"
                    else result.base_result is not None
                    and base.turn.completion == result.base_result.completion
                    and base.turn.assistant_text == result.base_result.assistant_text
                    and [
                        item
                        for event in (
                            base.turn.graph_context_execution.events
                            if base.turn.graph_context_execution
                            else []
                        )
                        if isinstance(event, BuildSectionAnswerBindingV1)
                        for item in event.bindings
                    ]
                    == result.base_result.build_section_bindings
                )
                if (
                    base.kind == "approved"
                    and base.turn.graph_context_execution is not None
                ):
                    graph_binding = next(
                        item
                        for item in base.turn.graph_context_execution.events
                        if isinstance(item, CompletionBindingEventV1)
                    )
                    base_matches = (
                        base_matches
                        and graph_binding.claim_graph_event_ids
                        == result.base_result.claim_graph_event_ids
                    )
                if isinstance(result, BuildRulesMixedTurnResultV1):
                    try:
                        proof = result.output_proof
                        base_segments = (tuple(item.text for item in result.base_result.completion.answer_segments)
                            if result.base_result is not None else ())
                        derived = parse_answer(proof.raw_output_json).composition(
                            supplied_refs=tuple(RulesSupportRefV1(support_id=item.support_id,
                                support_sha256=item.support_sha256) for item in binding.support_table),
                            base_segments=base_segments, base_disposition=result.composition.base_disposition)
                        if (hashlib.sha256(proof.prepared_request_json.encode()).hexdigest() != binding.request_envelope_sha256
                                or derived != result.composition):
                            raise ValueError("Replayed output differs from accepted producing request/composition")
                    except (ValueError, KeyError, TypeError, AttributeError) as exc:
                        raise ApplicationStateValidationError(str(exc)) from exc
                elif isinstance(result, NativeRulesMixedTurnResultV1):
                    try:
                        proof = result.output_proof
                        base_segments = (tuple(item.text for item in result.base_result.completion.answer_segments)
                            if result.base_result is not None else ())
                        supplied = tuple(RulesSupportRefV1(
                            support_id=item.support_id,
                            support_sha256=item.support_sha256,
                        ) for item in binding.support_table)
                        from .rules_authority_output import parse_answer
                        request_bytes = proof.prepared_request_json.encode("utf-8")
                        output_bytes = proof.raw_output_json.encode("utf-8")
                        sealed = conn.execute(
                            """SELECT e.value->>'authorization_id',e.value->>'api_request_id',
                            e.value->>'request_envelope_sha256',e.value->>'output_sha256',
                            (e.value->>'output_utf8_bytes')::integer
                            FROM agent.turn_rules_execution r
                            CROSS JOIN LATERAL jsonb_array_elements(r.payload->'events') AS e(value)
                            WHERE r.turn_id=%s AND r.product_attempt=%s
                            AND e.value->>'kind'='native_provider_outcome'
                            AND e.value->>'provider_attempt_id'=%s
                            AND octet_length(e.value::text)<=2048""",
                            (scope.turn_id, scope.product_attempt,
                             str(result.producing_provider_attempt_id)),
                        ).fetchall()
                        if len(sealed) != 1:
                            raise ValueError("Replayed native output has no unique compact provider witness")
                        derived = parse_answer(proof.raw_output_json).composition(
                            supplied_refs=supplied,
                            base_segments=base_segments,
                            base_disposition=result.composition.base_disposition,
                        )
                        if (hashlib.sha256(request_bytes).hexdigest()
                                != binding.request_envelope_sha256
                                or len(request_bytes) > MAX_REQUEST_BYTES
                                or len(output_bytes) != proof.raw_output_utf8_bytes
                                or hashlib.sha256(output_bytes).hexdigest()
                                != proof.raw_output_sha256
                                or (proof.authorization_id, proof.api_request_id,
                                    proof.request_envelope_sha256, proof.raw_output_sha256,
                                    proof.raw_output_utf8_bytes) != sealed[0]
                                or derived != result.composition):
                            raise ValueError("Replayed native output differs from the accepted producing request/composition")
                    except (ValueError, KeyError, TypeError, AttributeError, UnicodeError) as exc:
                        raise ApplicationStateValidationError(str(exc)) from exc
                if (
                    exact_scope == scope
                    and frozen[0] == result.expected_rules_revision + 1
                    and turn.envelope.revision == result.expected_turn_revision + 1
                    and turn.envelope.attempt == scope.product_attempt
                    and turn.assistant_text == result.assistant_text
                    and binding.composition_sha256
                    == canonical_sha256(result.composition)
                    and binding.producing_provider_attempt_id
                    == result.producing_provider_attempt_id
                    and base_matches
                ):
                    return turn
                raise ApplicationStateConflictError(
                    "completed mixed turn has a different result or acceptance fence"
                )
            if turn is None or turn.conversation_id != scope.conversation_id:
                raise ApplicationStateNotFoundError(
                    "turn not found in verified World conversation"
                )
            now = repo.database_clock(conn)
            if (
                turn.status != "running"
                or turn.revision != result.expected_turn_revision
                or turn.attempt != scope.product_attempt
                or turn.claim_expires_at is None
                or turn.claim_expires_at <= now
            ):
                raise ApplicationStateConflictError(
                    "mixed completion is fenced by a stale or expired claim"
                )
            current = load_turn_rules_locked(conn, turn)
            if (
                current is None
                or current.execution.scope != scope
                or current.revision != result.expected_rules_revision
            ):
                raise ApplicationStateConflictError(
                    "mixed completion differs from its frozen Rules execution"
                )
            output_context = None
            if isinstance(result, BuildRulesMixedTurnResultV1):
                captured = conn.execute(
                    "SELECT payload FROM agent.turn_context_trace WHERE turn_id=%s AND attempt=%s",
                    (turn.turn_id, turn.attempt),
                ).fetchone()
                try:
                    proof = result.output_proof
                    answer = verify_build_output(current.execution,
                        producing_provider_attempt_id=result.producing_provider_attempt_id,
                        prepared_request_json=proof.prepared_request_json, raw_output_json=proof.raw_output_json,
                        trace=captured[0] if captured else {})
                    output_context = (current.execution, proof, answer)
                except (ValueError, KeyError, TypeError, AttributeError) as exc:
                    raise ApplicationStateValidationError(str(exc)) from exc
            elif isinstance(result, NativeRulesMixedTurnResultV1):
                try:
                    from .native_rules_output import normalize_native_mixed_output

                    proof = result.output_proof
                    from .native_rules_output import sealed_native_producer
                    capture, graph_support = sealed_native_producer(turn, current.execution, proof)
                    normalized = normalize_native_mixed_output(
                        turn, turn.graph_context_execution, current.execution,
                        proof, capture, graph_support=graph_support,
                    )
                    if (normalized.composition != result.composition
                            or normalized.assistant_text != result.assistant_text):
                        raise ValueError("Native mixed result differs from its actual outer output normalization")
                    if normalized.base_completion is None:
                        if result.base_result is not None:
                            raise ValueError("Native unclaimed output cannot attach a base completion")
                    elif (result.base_result is None
                            or result.base_result.completion != normalized.base_completion
                            or result.base_result.assistant_text != "\n".join(
                                item.text for item in normalized.base_completion.answer_segments)
                            or result.base_result.producing_provider_attempt_id
                                != result.producing_provider_attempt_id
                            or result.base_result.claim_graph_event_ids
                                != normalized.claim_graph_event_ids):
                        raise ValueError("Native base result differs from its owning Plan/Play normalization")
                    output_context = normalized
                except (ValueError, KeyError, TypeError, AttributeError, UnicodeError) as exc:
                    raise ApplicationStateValidationError(str(exc)) from exc
            disposition = result.composition.base_disposition
            base_result = result.base_result
            execution = turn.graph_context_execution
            completion = None
            segments = ()
            graph_used = False
            if disposition == "approved":
                execution = _validated_base_execution_locked(conn, turn, base_result, mixed_output_context=output_context)
                completion = base_result.completion
                segments = tuple(item.text for item in completion.answer_segments)
                graph_used = "world_graph" in completion.answer_basis
            elif disposition == "absent":
                if turn.graph_context_receipt is not None or execution is not None:
                    raise ApplicationStateValidationError(
                        "absent base cannot retain Graph authority"
                    )
            elif turn.graph_context_receipt is None or execution is None:
                raise ApplicationStateValidationError(
                    "unclaimed base requires genuine Graph receipt and execution"
                )
            try:
                if isinstance(result, NativeRulesMixedTurnResultV1):
                    if (output_context is None
                            or output_context.composition != result.composition
                            or output_context.assistant_text != result.assistant_text):
                        raise ValueError("Native mixed result differs from its actual outer output normalization")
                elif output_context is not None:
                    derived = output_context[2].composition(supplied_refs=next(
                        e.support_refs for e in current.execution.events
                        if e.kind == "build_provider_included" and e.provider_attempt_id == result.producing_provider_attempt_id),
                        base_segments=segments, base_disposition=disposition)
                    if derived != result.composition or derived.render(segments) != result.assistant_text:
                        raise ValueError("Mixed result differs from its actual outer output normalization")
                accepted, binding = prepare_rules_acceptance(
                    current.execution,
                    result.composition,
                    producing_provider_attempt_id=result.producing_provider_attempt_id,
                    accepted_turn_revision=turn.revision + 1,
                    event_id=uuid4(),
                    base_segments=segments,
                    graph_used=graph_used,
                )
            except ValueError as exc:
                raise ApplicationStateValidationError(
                    "Rules completion lacks exact producing evidence or composition"
                ) from exc
            if execution is not None:
                from .rules_authority_reads import (
                    validate_graph_producer_join,
                    validate_unclaimed_receipt_owner,
                )

                try:
                    validate_graph_producer_join(execution, binding)
                    if disposition == "unclaimed":
                        validate_unclaimed_receipt_owner(
                            turn, turn.graph_context_receipt
                        )
                except ValueError as exc:
                    raise ApplicationStateValidationError(
                        "Rules/base producing request or provenance differs"
                    ) from exc
            persist_accepted_locked(conn, current, accepted, binding)
            updated = repo.complete_mixed_claimed_turn(
                conn,
                world_id=world_id,
                turn_id=turn.turn_id,
                expected_revision=turn.revision,
                expected_attempt=turn.attempt,
                assistant_text=result.assistant_text,
                completion=completion,
                graph_context_execution=execution,
            )
            if updated is None:
                raise ApplicationStateConflictError(
                    "mixed completion lost its turn claim fence"
                )
            return updated

    def fail_turn(self, failure: TurnFailure, *, interrupted: bool = False) -> Turn:
        world_id = _world_id(failure.world_id)
        status = "interrupted" if interrupted else "failed"
        dsn = _ready_dsn()
        with unit_of_work(dsn) as conn:
            turn = repo.lock_turn(conn, world_id, failure.turn_id)
            turn = _ordinary_mutation_turn(turn, failure.conversation_id)
            if turn is None or turn.conversation_id != failure.conversation_id:
                raise ApplicationStateNotFoundError("turn not found in verified World conversation")
            if turn.status == status:
                if (
                    turn.failure_code == failure.failure_code
                    and turn.revision == failure.expected_revision + 1
                ):
                    return turn
                raise ApplicationStateConflictError(
                    "turn failure is fenced by a different claim or failure"
                )
            if turn.revision != failure.expected_revision or turn.status != "running":
                raise ApplicationStateConflictError("turn revision or lifecycle state changed")
            from .rules_authority_store import fail_execution_locked
            fail_execution_locked(conn, turn)
            updated = repo.fail_claimed_turn(
                conn,
                world_id=world_id,
                turn_id=turn.turn_id,
                expected_revision=failure.expected_revision,
                expected_attempt=turn.attempt,
                status=status,
                failure_code=failure.failure_code,
            )
            if updated is None:
                raise ApplicationStateConflictError(
                    "turn claim expired or was fenced before failure was recorded"
                )
        return updated

    def get_draft(self, world_id: str, conversation_id: UUID, draft_id: UUID) -> Draft:
        world_id = _world_id(world_id)
        dsn = _ready_dsn()
        with unit_of_work(dsn) as conn:
            found = repo.get_draft(conn, world_id, conversation_id, draft_id)
        if found is None:
            raise ApplicationStateNotFoundError("composer draft not found in verified World conversation")
        return found[0]

    def save_draft(self, save: DraftSave) -> Draft:
        world_id = _world_id(save.world_id)
        if save.provenance.world_id != world_id:
            raise ApplicationStateValidationError("draft provenance must match verified World")
        dsn = _ready_dsn()
        now = _now()
        fingerprint = request_fingerprint(save)
        with unit_of_work(dsn) as conn:
            pointer = _lock_pointer(conn, world_id)
            conversation = repo.lock_conversation(conn, world_id, save.conversation_id)
            if conversation is None:
                raise ApplicationStateNotFoundError("conversation not found in verified World")
            current = repo.lock_draft(conn, world_id, save.conversation_id, save.draft_id)
            if current is not None:
                draft, old_fingerprint = current
                if draft.revision == save.expected_revision + 1 and old_fingerprint == fingerprint:
                    return draft
                if draft.revision != save.expected_revision:
                    raise ApplicationStateConflictError("composer draft revision mismatch")
                if draft.retired_at is not None:
                    raise ApplicationStateConflictError("submitted composer draft is retired")
                if draft.provenance != save.provenance and not save.explicitly_revalidated_source:
                    raise ApplicationStateConflictError(
                        "composer source changed; explicitly revalidate before rebinding this draft"
                    )
            elif save.expected_revision != 0:
                raise ApplicationStateConflictError("composer draft does not exist at expected revision")
            if pointer.active_conversation_id != save.conversation_id or conversation.status != "active":
                raise ApplicationStateConflictError("composer draft conversation is no longer active")
            saved = repo.save_draft(
                conn,
                save=save,
                save_fingerprint=fingerprint,
                revision=save.expected_revision + 1,
                now=now,
                create=current is None,
            )
        return saved

    def submit_draft(self, submit: DraftSubmit) -> DraftSubmitReceipt:
        world_id = _world_id(submit.world_id)
        if submit.provenance.world_id != world_id:
            raise ApplicationStateValidationError("submission provenance must match verified World")
        dsn = _ready_dsn()
        now = _now()
        with unit_of_work(dsn) as conn:
            pointer = _lock_pointer(conn, world_id)
            conversation = repo.lock_conversation(conn, world_id, submit.conversation_id)
            if conversation is None:
                raise ApplicationStateNotFoundError("conversation not found in verified World")
            current = repo.lock_draft(conn, world_id, submit.conversation_id, submit.draft_id)
            if current is None:
                raise ApplicationStateNotFoundError("composer draft not found in verified World conversation")
            draft, _ = current
            if draft.provenance != submit.provenance:
                raise ApplicationStateConflictError("submission source binding differs from saved draft")
            fingerprint = _fingerprint_payload(
                {
                    "world_id": world_id,
                    "conversation_id": str(submit.conversation_id),
                    "draft_id": str(submit.draft_id),
                    "draft_revision": submit.expected_draft_revision,
                    "idempotency_key": str(submit.idempotency_key),
                    "expected_conversation_revision": submit.expected_conversation_revision,
                    "body": draft.body,
                    "provenance": submit.provenance.model_dump(mode="json"),
                }
            )
            existing = repo.get_turn_by_world_key(
                conn, world_id, submit.idempotency_key
            )
            if existing is not None:
                (
                    turn,
                    old_fingerprint,
                    _old_idempotency_fingerprint,
                    old_submitted_intent_fingerprint,
                    old_submitted_intent_fingerprint_v2,
                ) = existing
                if (
                    old_submitted_intent_fingerprint is not None
                    or old_submitted_intent_fingerprint_v2 is not None
                ):
                    raise ApplicationStateConflictError(
                        "turn idempotency key was already used by an Agent turn"
                    )
                if old_fingerprint != fingerprint:
                    raise ApplicationStateConflictError(
                        "turn idempotency key was already used with different draft submission"
                    )
                if draft.retired_at is None:
                    raise ApplicationStateIntegrityError("committed draft turn has an unretired draft")
                return DraftSubmitReceipt(
                    turn=turn,
                    draft_id=draft.draft_id,
                    retired_draft_revision=draft.revision,
                    retired_at=draft.retired_at,
                )
            if draft.revision != submit.expected_draft_revision or draft.retired_at is not None:
                raise ApplicationStateConflictError("composer draft changed or was already submitted")
            if pointer.active_conversation_id != submit.conversation_id or conversation.status != "active":
                raise ApplicationStateConflictError("composer draft conversation is no longer active")
            if conversation.revision != submit.expected_conversation_revision:
                raise ApplicationStateConflictError("conversation revision mismatch")
            submission = TurnSubmission(
                world_id=world_id,
                conversation_id=submit.conversation_id,
                idempotency_key=submit.idempotency_key,
                expected_conversation_revision=submit.expected_conversation_revision,
                user_text=draft.body,
                provenance=submit.provenance,
            )
            advanced = repo.advance_conversation_for_turn(
                conn,
                world_id=world_id,
                conversation_id=submit.conversation_id,
                expected_revision=submit.expected_conversation_revision,
                now=now,
            )
            if advanced is None:
                raise ApplicationStateConflictError("conversation revision mismatch")
            _, sequence = advanced
            turn = repo.insert_turn(
                conn,
                turn_id=uuid4(),
                request_fingerprint=fingerprint,
                idempotency_fingerprint=turn_idempotency_fingerprint(
                    world_id, draft.body, submit.provenance
                ),
                submission=submission,
                sequence=sequence,
                now=now,
            )
            retired = repo.retire_draft(
                conn,
                world_id=world_id,
                conversation_id=submit.conversation_id,
                draft_id=submit.draft_id,
                expected_revision=submit.expected_draft_revision,
                retired_at=now,
            )
            if retired is None:
                raise ApplicationStateConflictError("composer draft revision changed during submission")
            return DraftSubmitReceipt(
                turn=turn,
                draft_id=retired.draft_id,
                retired_draft_revision=retired.revision,
                retired_at=retired.retired_at,
            )

    def import_legacy_conversation(self, request: LegacyImport) -> LegacyImportReceipt:
        world_id = _world_id(request.world_id)
        if any(turn.world_id != world_id or turn.provenance.world_id != world_id for turn in request.turns):
            raise ApplicationStateValidationError("every imported turn must match the verified World")
        dsn = _ready_dsn()
        now = _now()
        fingerprint = request_fingerprint(request)
        with unit_of_work(dsn) as conn:
            pointer = _lock_pointer(conn, world_id)
            existing = repo.get_import_receipt(conn, world_id, request.source_import_key)
            if existing is not None:
                receipt, old_fingerprint = existing
                if old_fingerprint != fingerprint:
                    raise ApplicationStateConflictError("legacy import key was already used with different data")
                return receipt
            _expect_pointer(request, pointer)
            if request.activate:
                _archive_active(conn, pointer, now)
            conversation_id = uuid4()
            repo.insert_conversation(
                conn,
                conversation_id=conversation_id,
                world_id=world_id,
                status="active" if request.activate else "archived",
                revision=1,
                next_turn_sequence=len(request.turns) + 1,
                now=now,
                archived_at=None if request.activate else now,
            )
            if request.activate:
                pointer = repo.update_world_state(
                    conn,
                    world_id=world_id,
                    active_conversation_id=conversation_id,
                    pointer_revision=pointer.revision + 1,
                    now=now,
                )
            for index, legacy_turn in enumerate(request.turns, start=1):
                turn_id = uuid4()
                turn_fingerprint = _fingerprint_payload(
                    {
                        "source_thread_id": request.source_thread_id,
                        "source_turn_id": legacy_turn.source_turn_id,
                        "user_text": legacy_turn.user_text,
                        "assistant_text": legacy_turn.assistant_text,
                        "provenance": legacy_turn.provenance.model_dump(mode="json"),
                    }
                )
                repo.insert_legacy_turn(
                    conn,
                    turn_id=turn_id,
                    conversation_id=conversation_id,
                    world_id=world_id,
                    idempotency_key=uuid4(),
                    sequence=index,
                    request_fingerprint=turn_fingerprint,
                    legacy_turn=legacy_turn,
                    now=now,
                )
            return repo.insert_import_receipt(
                conn,
                world_id=world_id,
                source_import_key=request.source_import_key,
                source_thread_id=request.source_thread_id,
                request_fingerprint=fingerprint,
                conversation_id=conversation_id,
                active_conversation_id=pointer.active_conversation_id,
                pointer_revision=pointer.revision,
                imported_turn_count=len(request.turns),
                recorded_at=now,
            )
