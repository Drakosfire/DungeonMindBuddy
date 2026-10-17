"""Durable, owner-bound Harness image preparations; no provider calls."""

from datetime import datetime, timezone
from uuid import UUID
from psycopg.types.json import Jsonb

from application_state import media
from application_state.agent_conversation.service import _lock_pointer, _ready_dsn
from application_state.build_proposal.service import _require_origin_claim
from application_state.build_proposal.types import (
    BuildImagePreparation,
    BuildProposalReservation,
)
from application_state.errors import (
    ApplicationStateConflictError,
    ApplicationStateNotFoundError,
)
from application_state.unit_of_work import unit_of_work


class BuildImageService:
    def prepare(
        self, reservation: BuildProposalReservation, owner: str, prompt: str, alt: str, *, writer_proof=None
    ) -> BuildImagePreparation:
        world = reservation.basis.world_id
        with unit_of_work(_ready_dsn()) as conn:
            pointer = _lock_pointer(conn, world)
            _require_origin_claim(conn, reservation)
            if (
                pointer.active_conversation_id != reservation.conversation_id
                or pointer.revision != reservation.expected_pointer_revision
            ):
                raise ApplicationStateConflictError("The World conversation changed")
            row = conn.execute(
                "SELECT payload FROM agent.build_proposal WHERE world_id=%s AND action_id=%s FOR UPDATE",
                (world, reservation.idempotency_key),
            ).fetchone()
            if row:
                previous = BuildImagePreparation.model_validate(row[0])
                if (
                    previous.reservation.model_dump(
                        exclude={"origin": {"broker_operation_id"}}
                    )
                    != reservation.model_dump(
                        exclude={"origin": {"broker_operation_id"}}
                    )
                    or previous.owner_id != owner
                    or previous.prompt != prompt
                    or previous.alt != alt
                    or previous.writer_proof != writer_proof
                ):
                    raise ApplicationStateConflictError(
                        "Image preparation key has a different request"
                    )
                return previous
            sequence = conn.execute(
                "SELECT next_turn_sequence FROM agent.conversation WHERE world_id=%s AND conversation_id=%s",
                (world, reservation.conversation_id),
            ).fetchone()
            if not sequence:
                raise ApplicationStateNotFoundError("World conversation unavailable")
            now = datetime.now(timezone.utc)
            result = BuildImagePreparation(
                action_id=reservation.idempotency_key,
                reservation=reservation,
                request_fingerprint=reservation.fingerprint,
                owner_id=owner,
                revision=1,
                after_turn_sequence=sequence[0] - 1,
                created_at=now,
                updated_at=now,
                prompt=prompt,
                alt=alt,
                writer_proof=writer_proof,
            )
            conn.execute(
                "INSERT INTO agent.build_proposal(action_id,world_id,conversation_id,idempotency_key,revision,payload) VALUES(%s,%s,%s,%s,1,%s)",
                (
                    result.action_id,
                    world,
                    reservation.conversation_id,
                    reservation.idempotency_key,
                    Jsonb(result.model_dump(mode="json")),
                ),
            )
            return result

    def get(self, action_id: UUID, owner: str) -> BuildImagePreparation:
        with unit_of_work(_ready_dsn()) as conn:
            row = conn.execute(
                "SELECT payload FROM agent.build_proposal WHERE action_id=%s AND payload->>'schema_version'='dmb_build_image_preparation_v2' AND payload->>'owner_id'=%s",
                (action_id, owner),
            ).fetchone()
        if row is None:
            raise ApplicationStateNotFoundError("Image preparation unavailable")
        return BuildImagePreparation.model_validate(row[0])

    def list(
        self, world: str, conversation_id: UUID, owner: str
    ) -> list[BuildImagePreparation]:
        with unit_of_work(_ready_dsn()) as conn:
            rows = conn.execute(
                "SELECT payload FROM agent.build_proposal WHERE world_id=%s AND conversation_id=%s AND payload->>'schema_version'='dmb_build_image_preparation_v2' AND payload->>'owner_id'=%s ORDER BY payload->>'created_at',action_id",
                (world, conversation_id, owner),
            ).fetchall()
        return [BuildImagePreparation.model_validate(row[0]) for row in rows]

    def associate(
        self, action_id: UUID, asset_id: UUID, owner: str, expected_revision: int
    ) -> BuildImagePreparation:
        asset = media.get_asset(asset_id, owner)
        if asset["state"] != "ready":
            raise ApplicationStateConflictError("Save the image before inserting it")
        basis = self.get(action_id, owner)
        with unit_of_work(_ready_dsn()) as conn:
            pointer = _lock_pointer(conn, basis.reservation.basis.world_id)
            row = conn.execute(
                "SELECT payload FROM agent.build_proposal WHERE action_id=%s AND payload->>'schema_version'='dmb_build_image_preparation_v2' AND payload->>'owner_id'=%s FOR UPDATE",
                (action_id, owner),
            ).fetchone()
            if row is None:
                raise ApplicationStateNotFoundError("Image preparation unavailable")
            previous = BuildImagePreparation.model_validate(row[0])
            if (
                pointer.active_conversation_id != previous.reservation.conversation_id
                or pointer.revision != previous.reservation.expected_pointer_revision
            ):
                raise ApplicationStateConflictError(
                    "The conversation changed; reopen the current page"
                )
            if previous.asset_id == asset_id:
                return previous
            if previous.revision != expected_revision:
                raise ApplicationStateConflictError("Image selection changed")
            result = BuildImagePreparation.model_validate(
                {
                    **previous.model_dump(mode="python"),
                    "asset_id": asset_id,
                    "revision": previous.revision + 1,
                    "updated_at": datetime.now(timezone.utc),
                }
            )
            conn.execute(
                "UPDATE agent.build_proposal SET revision=%s,payload=%s WHERE action_id=%s",
                (result.revision, Jsonb(result.model_dump(mode="json")), action_id),
            )
            return result
