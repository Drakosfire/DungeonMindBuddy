"""Transaction boundary for Plan action idempotency, fencing, and projections."""

from __future__ import annotations

from uuid import UUID, uuid4

from application_state.agent_conversation.types import (
    CompletionBindingEventV1,
    GraphExecutionEventV2,
    GraphExecutionPolicyV2,
    PlanWorldGraphExecutionV2,
    ProviderAttemptAuthorizedEventV1,
    WorldPointer,
    graph_execution_policy_digest_v2,
)
from application_state.errors import ApplicationStateConflictError, ApplicationStateValidationError
from application_state.plan_action_dialogue.graph_consultation import consultation_result_digest

from application_state.cli import assert_at_head
from application_state.config import load_runtime_dsn
from application_state.plan_action_dialogue import repository as repo
from application_state.plan_action_dialogue.types import (
    CompletedPlanActionContext,
    PlanActionBasis,
    PlanActionConsultation,
    PlanActionConversationProjectionPage,
    PlanActionConsultationReceipt,
    PlanActionConsultationResult,
    PlanActionContextUnavailableResult,
    PlanActionProjection,
    PlanActionProjectionPage,
    PlanActionRecord,
    PlanActionReservation,
)
from application_state.unit_of_work import unit_of_work


class PlanActionDialogueService:
    """Stateless action store; managed World/Content verification belongs to its caller."""

    def _dsn(self) -> str:
        dsn = load_runtime_dsn()
        assert_at_head(dsn=dsn)
        return dsn

    def reserve(self, request: PlanActionReservation) -> tuple[PlanActionRecord, bool]:
        with unit_of_work(self._dsn()) as conn:
            return repo.reserve(conn, request)

    def finish(
        self,
        *,
        action_id: UUID,
        token: UUID,
        fence: int,
        status: str,
        summary: str | None = None,
        failure_code: str | None = None,
    ) -> PlanActionRecord:
        with unit_of_work(self._dsn()) as conn:
            return repo.finish(
                conn, action_id=action_id, token=token, fence=fence,
                status=status, summary=summary, failure_code=failure_code,
            )

    def get_by_key(self, world_id: str, key: UUID) -> PlanActionRecord | None:
        with unit_of_work(self._dsn()) as conn:
            return repo.get_by_key(conn, world_id, key)

    def freeze_consultation(
        self, *, action_id: UUID, token: UUID, fence: int,
        receipt: PlanActionConsultationReceipt, policy: GraphExecutionPolicyV2 | None = None,
    ) -> tuple[PlanActionRecord, bool]:
        """Freeze server-resolved action/Graph input before any provider authorization."""
        receipt = PlanActionConsultationReceipt.model_validate(
            receipt.model_dump(mode="json", by_alias=True)
        )
        if receipt.authority_status == "unavailable" and policy is not None:
            raise ApplicationStateValidationError("unavailable authority cannot authorize execution")
        if receipt.authority_status == "resolved" and policy is None:
            raise ApplicationStateValidationError("resolved consultation requires a frozen policy")
        execution = None if policy is None else PlanWorldGraphExecutionV2.model_validate({
            "context_receipt_sha256": receipt.consultation_receipt_sha256,
            "execution_policy_sha256": graph_execution_policy_digest_v2(
                receipt.consultation_receipt_sha256, policy
            ),
            "policy": policy.model_dump(mode="json", by_alias=True), "events": [],
        })
        consultation = PlanActionConsultation(receipt=receipt, execution=execution)
        with unit_of_work(self._dsn()) as conn:
            current = repo.lock_dispatch(conn, action_id, token, fence)
            if receipt.action_id != action_id:
                raise ApplicationStateValidationError("consultation action ID differs from reservation")
            repo.expect_world_pointer(conn, WorldPointer(
                world_id=receipt.basis.world_id,
                active_conversation_id=receipt.origin_conversation_id,
                revision=receipt.origin_pointer_revision,
            ))
            if current.consultation is not None:
                if (current.consultation.receipt == receipt
                        and (current.consultation.execution.policy if current.consultation.execution else None)
                        == (execution.policy if execution else None)):
                    return current, False
                raise ApplicationStateConflictError("action consultation is already frozen with different inputs")
            repo.validate_predecessor(conn, consultation)
            return repo.write_consultation(conn, current, consultation), True

    def append_consultation_event(
        self, *, action_id: UUID, token: UUID, fence: int, event: GraphExecutionEventV2,
    ) -> tuple[PlanActionRecord, bool]:
        """A fresh provider-authorization append is the only one-shot dispatch permission."""
        if isinstance(event, CompletionBindingEventV1):
            raise ApplicationStateValidationError("terminal binding belongs to finish_consultation")
        with unit_of_work(self._dsn()) as conn:
            current = repo.lock_dispatch(conn, action_id, token, fence)
            if current.consultation is None or current.consultation.execution is None:
                raise ApplicationStateValidationError("action consultation must be frozen before event append")
            consultation = current.consultation
            for prior in consultation.execution.events:
                if prior.event_id == event.event_id:
                    if prior == event:
                        return current, False
                    raise ApplicationStateConflictError("action event ID was reused with different content")
            if isinstance(event, ProviderAttemptAuthorizedEventV1):
                receipt = consultation.receipt
                repo.expect_world_pointer(conn, WorldPointer(
                    world_id=receipt.basis.world_id,
                    active_conversation_id=receipt.origin_conversation_id,
                    revision=receipt.origin_pointer_revision,
                ))
            if event.sequence != len(consultation.execution.events):
                raise ApplicationStateConflictError("action consultation event sequence is stale")
            payload = consultation.model_dump(mode="json", by_alias=True)
            payload["execution"]["events"].append(event.model_dump(mode="json", by_alias=True))
            updated = PlanActionConsultation.model_validate(payload)
            return repo.write_consultation(conn, current, updated), True

    def finish_consultation(
        self, *, action_id: UUID, token: UUID, fence: int,
        result: PlanActionConsultationResult,
    ) -> PlanActionRecord:
        """Atomically commit typed result and its terminal evidence binding."""
        with unit_of_work(self._dsn()) as conn:
            current = repo.lock_dispatch(conn, action_id, token, fence)
            if current.consultation is None:
                raise ApplicationStateValidationError("action has no frozen consultation")
            payload = current.consultation.model_dump(mode="json", by_alias=True)
            payload["result"] = result.model_dump(mode="json", by_alias=True)
            if isinstance(result, PlanActionContextUnavailableResult):
                status, summary, failure_code = "failed", None, result.failure_code
            else:
                if current.consultation.execution is None:
                    raise ApplicationStateValidationError("unavailable authority cannot complete a proposal or clarification")
                binding = CompletionBindingEventV1(
                    event_id=uuid4(), sequence=len(payload["execution"]["events"]),
                    kind="completion_binding",
                    provider_attempt_id=result.producing_provider_attempt_id,
                    completion_sha256=consultation_result_digest(result),
                    claim_graph_event_ids=result.claim_graph_event_ids,
                )
                payload["execution"]["events"].append(binding.model_dump(mode="json", by_alias=True))
                status, summary, failure_code = "completed", result.message, None
            updated = PlanActionConsultation.model_validate(payload)
            return repo.write_consultation(
                conn, current, updated, status=status, summary=summary, failure_code=failure_code,
            )

    def list_status(self, basis: PlanActionBasis) -> PlanActionProjectionPage:
        with unit_of_work(self._dsn()) as conn:
            records = repo.list_basis(conn, basis)
        return PlanActionProjectionPage(
            basis=basis,
            actions=[
                self._projection(item)
                for item in records
            ],
        )

    @staticmethod
    def _projection(item: PlanActionRecord) -> PlanActionProjection:
        return PlanActionProjection(
            action_id=item.action_id,
            action_type=item.action_type,
            status=item.status,
            basis=item.basis,
            instruction=item.instruction,
            assistant_summary=item.assistant_summary if item.status == "completed" else None,
            action_sequence=item.action_sequence,
            accepted_at=item.accepted_at,
            completed_at=item.completed_at,
            playable_target_receipt=item.playable_target_receipt,
            consultation=item.consultation,
        )

    def list_conversation_status(
        self, world_id: str, conversation_id: UUID, *, limit: int = 50,
        before_action_sequence: int | None = None,
    ) -> PlanActionConversationProjectionPage:
        """Read one viewed World conversation across Plan saves and documents."""
        if not world_id.strip():
            raise ApplicationStateValidationError("World ID is required")
        with unit_of_work(self._dsn()) as conn:
            conn.execute("SET TRANSACTION READ ONLY")
            records, next_cursor = repo.list_conversation(
                conn, world_id, conversation_id, limit=limit,
                before_action_sequence=before_action_sequence,
            )
        return PlanActionConversationProjectionPage(
            world_id=world_id, conversation_id=conversation_id,
            actions=[self._projection(item) for item in records],
            next_before_action_sequence=next_cursor,
        )

    def completed_context(
        self, basis: PlanActionBasis, *, limit: int = 6
    ) -> list[CompletedPlanActionContext]:
        with unit_of_work(self._dsn()) as conn:
            records = repo.completed_context(conn, basis, limit=limit)
        return [
            CompletedPlanActionContext(
                action_id=item.action_id,
                action_type=item.action_type,
                basis=item.basis,
                instruction=item.instruction,
                assistant_summary=item.assistant_summary,
                action_sequence=item.action_sequence,
                accepted_at=item.accepted_at,
                consultation=item.consultation,
            )
            for item in records
        ]
