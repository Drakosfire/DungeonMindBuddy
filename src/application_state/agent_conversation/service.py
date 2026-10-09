"""Transactional Application State service for World-scoped conversations."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from uuid import UUID, uuid4

from pydantic import ValidationError

from application_state.agent_conversation import repository as repo
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
    PlanWorldGraphExecutionV1,
    PlanWorldGraphExecutionV2,
    ProviderAttemptAuthorizedEventV1,
    ProviderAttemptAuthorizedEventV2,
    ProviderOutcomeEventV1,
    ReopenCommand,
    SourceReadAuthorizationEventV2,
    SubmittedTurnIntentV1,
    SubmittedTurnIntentV2,
    Turn,
    TurnClaimReceipt,
    TurnFailure,
    TurnResult,
    TurnSubmission,
    ValidatedGraphOperationEventV1,
    ValidatedSourceReadEventV2,
    WorldPointer,
    request_fingerprint,
    submitted_turn_intent_fingerprint_v1,
    submitted_turn_intent_fingerprint_v2,
    turn_idempotency_fingerprint,
    validate_completion_against_receipt,
    validate_execution_completion,
)
from application_state.cli import assert_at_head
from application_state.config import load_runtime_dsn
from application_state.errors import (
    ApplicationStateConflictError,
    ApplicationStateIntegrityError,
    ApplicationStateNotFoundError,
    ApplicationStateValidationError,
)
from application_state.unit_of_work import unit_of_work

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

    def accept_turn(self, submission: TurnSubmission) -> Turn:
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
            world_id, submission.user_text, submission.provenance
        )
        submitted_intent_fingerprint = (
            None if submitted_intent is None else submitted_turn_intent_fingerprint_v1(submitted_intent)
        )
        submitted_intent_fingerprint_v2 = (
            None
            if submitted_intent_v2 is None
            else submitted_turn_intent_fingerprint_v2(submitted_intent_v2)
        )

        def matching_receipt(existing) -> Turn:
            (
                turn,
                _old_request_fingerprint,
                _old_idempotency_fingerprint,
                old_submitted_intent_fingerprint,
                old_submitted_intent_fingerprint_v2,
            ) = existing
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
                or turn.graph_context_receipt != submission.graph_context_receipt
                or (
                    (turn.graph_context_execution is None)
                    != (submission.graph_context_execution is None)
                )
                or (
                    turn.graph_context_execution is not None
                    and submission.graph_context_execution is not None
                    and (
                        turn.graph_context_execution.context_receipt_sha256
                        != submission.graph_context_execution.context_receipt_sha256
                        or turn.graph_context_execution.policy
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
        submitted_intent: SubmittedTurnIntentV1 | SubmittedTurnIntentV2,
    ) -> Turn | None:
        """Find an exact World receipt before resolving mutable current context.

        A legacy receipt has no lossless submitted-intent identity and therefore
        fails closed. A missing receipt remains a normal new-turn path.
        """
        world_id = _world_id(world_id)
        if submitted_intent.world_id != world_id:
            raise ApplicationStateValidationError(
                "submitted intent World does not match verified World"
            )
        if isinstance(submitted_intent, SubmittedTurnIntentV2):
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

    def list_turns(
        self,
        world_id: str,
        conversation_id: UUID,
        *,
        limit: int = 50,
        before_sequence: int | None = None,
    ) -> list[Turn]:
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
        with unit_of_work(dsn) as conn:
            turn = repo.lock_turn(conn, world_id, turn_id)
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
                if turn.status == "running" and (turn.claim_expires_at is None or turn.claim_expires_at <= now):
                    execution = turn.graph_context_execution
                    auths = [e for e in execution.events if isinstance(e, ProviderAttemptAuthorizedEventV1)]
                    latest = auths[-1]
                    outcomes = [e for e in execution.events if isinstance(e, ProviderOutcomeEventV1) and e.provider_attempt_id == latest.provider_attempt_id]
                    outcome_unknown = False
                    if not outcomes or outcomes[-1].outcome not in {"response_received", "known_not_sent", "outcome_unknown"}:
                        outcome_unknown = True
                        unknown = ProviderOutcomeEventV1(
                            event_id=uuid4(), sequence=len(execution.events),
                            kind="provider_outcome", provider_attempt_id=latest.provider_attempt_id,
                            outcome="outcome_unknown",
                        )
                        execution_type = (
                            PlanWorldGraphExecutionV2
                            if isinstance(execution, PlanWorldGraphExecutionV2)
                            else PlanWorldGraphExecutionV1
                        )
                        execution = execution_type.model_validate(
                            execution.model_dump(mode="json", by_alias=True)
                            | {"events": [*[e.model_dump(mode="json", by_alias=True) for e in execution.events], unknown.model_dump(mode="json", by_alias=True)]}
                        )
                    interrupted = repo.interrupt_expired_graph_execution(
                        conn, world_id=world_id, turn_id=turn_id,
                        expected_revision=expected_revision, execution=execution,
                        failure_code=("provider_outcome_unknown" if outcome_unknown else "provider_authorized_nonreclaimable"),
                    )
                    if interrupted is None:
                        raise ApplicationStateConflictError("expired Graph provider claim could not be fenced")
                    interrupted_after_dispatch = True
                else:
                    raise ApplicationStateConflictError(
                        "Graph execution with a prior provider authorization cannot be reclaimed"
                    )
            if not interrupted_after_dispatch:
                if turn.status not in {"accepted", "failed", "interrupted", "running"}:
                    raise ApplicationStateConflictError(
                        "turn is not eligible for a runtime claim"
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
                "expired Graph provider claim was recorded as potentially sent and cannot be reclaimed"
            )

    def _append_graph_execution_event(
        self,
        world_id: str,
        conversation_id: UUID,
        turn_id: UUID,
        *,
        expected_revision: int,
        expected_attempt: int,
        event: GraphExecutionEventV1 | GraphExecutionEventV2,
        duplicate_key: str,
    ) -> tuple[Turn, bool]:
        world_id = _world_id(world_id)
        dsn = _ready_dsn()
        with unit_of_work(dsn) as conn:
            turn = repo.lock_turn(conn, world_id, turn_id)
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
            for prior in execution.events:
                if getattr(prior, duplicate_key, None) == getattr(event, duplicate_key, None):
                    if (
                        isinstance(prior, ValidatedGraphOperationEventV1)
                        and isinstance(event, ValidatedGraphOperationEventV1)
                    ):
                        if prior.request_arguments_sha256 == event.request_arguments_sha256:
                            return turn, False
                        raise ApplicationStateConflictError("Graph operation ID was reused with changed arguments")
                    if prior == event:
                        return turn, False
                    raise ApplicationStateConflictError("Graph execution event ID was reused with changed content")
            if event.sequence != len(execution.events):
                raise ApplicationStateConflictError("Graph execution event sequence is stale")
            if isinstance(event, ProviderAttemptAuthorizedEventV1):
                receipt = turn.graph_context_receipt
                assert receipt is not None
                graph_events = [e for e in execution.events if isinstance(e, ValidatedGraphOperationEventV1)]
                included_graph_events = set(event.included_graph_event_ids)
                included_operations = [e for e in graph_events if e.event_id in included_graph_events]
                available_assertions = set(receipt.assembled_input.dispatched_assertion_ids) | {x for e in included_operations for x in e.assertion_ids}
                available_relationships = set(receipt.assembled_input.dispatched_relationship_ids) | {x for e in included_operations for x in e.relationship_ids}
                available_evidence = set(receipt.assembled_input.dispatched_evidence_ref_ids) | {x for e in included_operations for x in e.evidence_ref_ids}
                if not set(event.included_assertion_ids).issubset(available_assertions) or not set(event.included_relationship_ids).issubset(available_relationships) or not set(event.included_evidence_ref_ids).issubset(available_evidence):
                    raise ApplicationStateValidationError("provider envelope includes IDs absent from admitted Graph evidence")
                if event.input_tokens + event.output_token_reserve > receipt.assembled_input.context_window_limit:
                    raise ApplicationStateValidationError("provider envelope exceeds the frozen context window")
                operation_event_ids = {e.event_id for e in graph_events}
                if not set(event.included_graph_event_ids).issubset(operation_event_ids):
                    raise ApplicationStateValidationError("provider envelope references an unknown Graph operation event")
                previous_attempts = [e for e in execution.events if isinstance(e, ProviderAttemptAuthorizedEventV1)]
                if not previous_attempts:
                    assembled = receipt.assembled_input
                    if (
                        event.envelope_sha256 != assembled.assembled_input_sha256
                        or event.input_tokens != assembled.provider_envelope_input_tokens
                        or event.output_token_reserve != assembled.output_token_reserve
                        or event.input_estimator != assembled.tokenizer_name
                    ):
                        raise ApplicationStateValidationError("first provider authorization must match the frozen receipt envelope and accounting")
            if isinstance(event, ValidatedGraphOperationEventV1):
                receipt = turn.graph_context_receipt
                assert receipt is not None
                if event.graph_revision != receipt.graph_authority.graph_revision:
                    raise ApplicationStateValidationError("Graph operation event must use the frozen Graph revision")
            events = [*execution.events, event]
            try:
                execution_type = (
                    PlanWorldGraphExecutionV2
                    if isinstance(execution, PlanWorldGraphExecutionV2)
                    else PlanWorldGraphExecutionV1
                )
                updated_execution = execution_type.model_validate(
                    execution.model_dump(mode="json", by_alias=True) | {"events": [e.model_dump(mode="json", by_alias=True) for e in events]}
                )
            except ValueError as exc:
                raise ApplicationStateValidationError(str(exc)) from exc
            updated = repo.update_graph_execution(
                conn, world_id=world_id, turn_id=turn_id,
                expected_revision=expected_revision, execution=updated_execution,
            )
        if updated is None:
            raise ApplicationStateConflictError("Graph execution append lost its claim fence")
        return updated, True

    def append_validated_graph_operation(
        self, world_id: str, conversation_id: UUID, turn_id: UUID, *,
        expected_revision: int, expected_attempt: int,
        operation_event: ValidatedGraphOperationEventV1,
    ) -> tuple[Turn, bool]:
        return self._append_graph_execution_event(
            world_id, conversation_id, turn_id, expected_revision=expected_revision,
            expected_attempt=expected_attempt, event=operation_event, duplicate_key="operation_id",
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

    def record_provider_outcome(
        self, world_id: str, conversation_id: UUID, turn_id: UUID, *,
        expected_revision: int, expected_attempt: int,
        outcome: ProviderOutcomeEventV1,
    ) -> tuple[Turn, bool]:
        return self._append_graph_execution_event(
            world_id, conversation_id, turn_id, expected_revision=expected_revision,
            expected_attempt=expected_attempt, event=outcome, duplicate_key="event_id",
        )

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
    ) -> tuple[Turn, bool]:
        """Persist the server-validated source read result without source text."""
        return self._append_graph_execution_event(
            world_id, conversation_id, turn_id, expected_revision=expected_revision,
            expected_attempt=expected_attempt, event=receipt,
            duplicate_key="event_id",
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
        world_id = _world_id(result.world_id)
        dsn = _ready_dsn()
        with unit_of_work(dsn) as conn:
            turn = repo.lock_turn(conn, world_id, result.turn_id)
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
            if turn.revision != result.expected_revision or turn.status != "running":
                raise ApplicationStateConflictError("turn revision or lifecycle state changed")
            execution = turn.graph_context_execution
            if execution is not None:
                if result.completion is None or result.producing_provider_attempt_id is None or result.claim_graph_event_ids is None:
                    raise ApplicationStateValidationError("execution completion requires a producing attempt and claim evidence binding")
                payload = result.completion.model_dump(mode="json", by_alias=True)
                digest = hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")).hexdigest()
                binding = CompletionBindingEventV1(
                    event_id=uuid4(), sequence=len(execution.events), kind="completion_binding",
                    provider_attempt_id=result.producing_provider_attempt_id,
                    completion_sha256=digest,
                    claim_graph_event_ids=result.claim_graph_event_ids,
                )
                try:
                    execution_type = (
                        PlanWorldGraphExecutionV2
                        if isinstance(execution, PlanWorldGraphExecutionV2)
                        else PlanWorldGraphExecutionV1
                    )
                    execution = execution_type.model_validate(
                        execution.model_dump(mode="json", by_alias=True)
                        | {"events": [*[e.model_dump(mode="json", by_alias=True) for e in execution.events], binding.model_dump(mode="json", by_alias=True)]}
                    )
                    validate_execution_completion(
                        result.completion, turn.graph_context_receipt, execution,
                        result.producing_provider_attempt_id, result.claim_graph_event_ids,
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
            updated = repo.complete_claimed_turn(
                conn,
                world_id=world_id,
                turn_id=turn.turn_id,
                expected_revision=result.expected_revision,
                assistant_text=result.assistant_text,
                completion=result.completion,
                graph_context_execution=execution,
            )
        if updated is None:
            raise ApplicationStateConflictError(
                "turn claim expired or was fenced before completion"
            )
        return updated

    def fail_turn(self, failure: TurnFailure, *, interrupted: bool = False) -> Turn:
        world_id = _world_id(failure.world_id)
        status = "interrupted" if interrupted else "failed"
        dsn = _ready_dsn()
        with unit_of_work(dsn) as conn:
            turn = repo.lock_turn(conn, world_id, failure.turn_id)
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
            updated = repo.fail_claimed_turn(
                conn,
                world_id=world_id,
                turn_id=turn.turn_id,
                expected_revision=failure.expected_revision,
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
