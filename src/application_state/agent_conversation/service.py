"""Transactional Application State service for World-scoped conversations."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from uuid import UUID, uuid4

from application_state.agent_conversation import repository as repo
from application_state.agent_conversation.types import (
    ArchiveCommand,
    Conversation,
    ConversationCommand,
    ConversationCommandReceipt,
    CompletedPlanAskPair,
    Draft,
    DraftSave,
    DraftSubmit,
    DraftSubmitReceipt,
    LegacyImport,
    LegacyImportReceipt,
    PlanAskContextBasis,
    ReopenCommand,
    SubmittedTurnIntentV1,
    Turn,
    TurnClaimReceipt,
    TurnFailure,
    TurnResult,
    TurnSubmission,
    WorldPointer,
    request_fingerprint,
    submitted_turn_intent_fingerprint_v1,
    turn_idempotency_fingerprint,
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

    def new_conversation(self, command: ConversationCommand) -> ConversationCommandReceipt:
        world_id = _world_id(command.world_id)
        dsn = _ready_dsn()
        now = _now()
        with unit_of_work(dsn) as conn:
            pointer = _lock_pointer(conn, world_id)
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

        def matching_receipt(existing) -> Turn:
            (
                turn,
                _old_request_fingerprint,
                _old_idempotency_fingerprint,
                old_submitted_intent_fingerprint,
            ) = existing
            if old_submitted_intent_fingerprint is None:
                raise ApplicationStateConflictError(
                    "legacy-receipt-unverifiable: the stored turn has no submitted-intent fingerprint"
                )
            if submitted_intent_fingerprint is None:
                raise ApplicationStateConflictError(
                    "turn idempotency key requires its submitted-intent fingerprint"
                )
            if old_submitted_intent_fingerprint != submitted_intent_fingerprint:
                raise ApplicationStateConflictError(
                    "turn idempotency key was already used with different submitted intent"
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
            if submitted_intent_fingerprint is None:
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
                submission=submission,
                sequence=sequence,
                now=now,
            )

    def reconcile_turn(
        self,
        world_id: str,
        idempotency_key: UUID,
        submitted_intent: SubmittedTurnIntentV1,
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
        digest = submitted_turn_intent_fingerprint_v1(submitted_intent)
        dsn = _ready_dsn()
        with unit_of_work(dsn) as conn:
            existing = repo.get_turn_by_world_key(conn, world_id, idempotency_key)
        if existing is None:
            return None
        turn, _request_hash, _idempotency_hash, stored_digest = existing
        if stored_digest is None:
            raise ApplicationStateConflictError(
                "legacy-receipt-unverifiable: the stored turn has no submitted-intent fingerprint"
            )
        if stored_digest != digest:
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
                if (
                    turn.assistant_text == result.assistant_text
                    and turn.revision == result.expected_revision + 1
                ):
                    return turn
                raise ApplicationStateConflictError(
                    "completed turn has a different recorded result or a different claim fence"
                )
            if turn.revision != result.expected_revision or turn.status != "running":
                raise ApplicationStateConflictError("turn revision or lifecycle state changed")
            updated = repo.complete_claimed_turn(
                conn,
                world_id=world_id,
                turn_id=turn.turn_id,
                expected_revision=result.expected_revision,
                assistant_text=result.assistant_text,
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
                ) = existing
                if old_submitted_intent_fingerprint is not None:
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
