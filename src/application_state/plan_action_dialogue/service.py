"""Transaction boundary for Plan action idempotency, fencing, and projections."""

from __future__ import annotations

from uuid import UUID

from application_state.cli import assert_at_head
from application_state.config import load_runtime_dsn
from application_state.plan_action_dialogue import repository as repo
from application_state.plan_action_dialogue.types import (
    CompletedPlanActionContext,
    PlanActionBasis,
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

    def get_by_key(self, key: UUID) -> PlanActionRecord | None:
        with unit_of_work(self._dsn()) as conn:
            return repo.get_by_key(conn, key)

    def list_status(self, basis: PlanActionBasis) -> PlanActionProjectionPage:
        with unit_of_work(self._dsn()) as conn:
            records = repo.list_basis(conn, basis)
        return PlanActionProjectionPage(
            basis=basis,
            actions=[
                PlanActionProjection(
                    action_id=item.action_id,
                    action_type=item.action_type,
                    status=item.status,
                    basis=item.basis,
                    instruction=item.instruction,
                    assistant_summary=item.assistant_summary if item.status == "completed" else None,
                    action_sequence=item.action_sequence,
                    accepted_at=item.accepted_at,
                    completed_at=item.completed_at,
                )
                for item in records
            ],
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
            )
            for item in records
        ]
