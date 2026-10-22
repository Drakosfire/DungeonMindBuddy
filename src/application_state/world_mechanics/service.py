"""Append-only APP association history; external verification precedes writes."""
from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from psycopg.types.json import Jsonb

from application_state.cli import assert_at_head
from application_state.config import load_runtime_dsn
from application_state.errors import ApplicationStateConflictError, ApplicationStateIntegrityError
from application_state.unit_of_work import unit_of_work
from application_state.world_mechanics.types import (
    AcceptedMechanicsProof, AssociateWorldMechanicsRequest,
    AssociateWorldMechanicsResponse, WorldMechanicsAssociation,
)


def _dsn():
    value = load_runtime_dsn()
    assert_at_head(dsn=value)
    return value


def _load(row):
    if row is None:
        return None
    try:
        record = WorldMechanicsAssociation.model_validate(row[0])
    except ValueError as exc:
        raise ApplicationStateIntegrityError("Stored mechanics association is invalid") from exc
    return record


def _replay(conn, world_id, request):
    record = _load(conn.execute(
        "SELECT payload FROM world_mechanics.association WHERE world_id=%s AND request_id=%s",
        (world_id, request.request_id),
    ).fetchone())
    if record is not None and record.request != request:
        raise ApplicationStateConflictError("Association request ID already belongs to a different request")
    return record


def replay(request: AssociateWorldMechanicsRequest) -> WorldMechanicsAssociation | None:
    with unit_of_work(_dsn()) as conn:
        return _replay(conn, request.target.managed_world_id, request)


def list_current(*, world_id: str) -> list[WorldMechanicsAssociation]:
    with unit_of_work(_dsn()) as conn:
        rows = conn.execute(
            "SELECT DISTINCT ON (node_id) payload FROM world_mechanics.association "
            "WHERE world_id=%s ORDER BY node_id,version DESC", (world_id,),
        ).fetchall()
        return [_load(row) for row in rows]


def append_verified(*, request: AssociateWorldMechanicsRequest, proof: AcceptedMechanicsProof,
                    actor: str) -> AssociateWorldMechanicsResponse:
    world = request.target.managed_world_id
    with unit_of_work(_dsn()) as conn:
        # Separate locks serialize key reuse and slot CAS, including absent slots.
        for key in (f"world-mechanics-key:{world}:{request.request_id}",
                    f"world-mechanics-slot:{world}:{request.target.node_id}"):
            conn.execute("SELECT pg_advisory_xact_lock(hashtextextended(%s,0))", (key,))
        existing = _replay(conn, world, request)
        if existing is not None:
            return AssociateWorldMechanicsResponse(association=existing, replayed=True)
        previous = _load(conn.execute(
            "SELECT payload FROM world_mechanics.association WHERE world_id=%s AND node_id=%s "
            "ORDER BY version DESC LIMIT 1", (world, request.target.node_id),
        ).fetchone())
        if (previous.version if previous else 0) != request.expected_version:
            raise ApplicationStateConflictError("Creature mechanics association changed; refresh and confirm again")
        record = WorldMechanicsAssociation(
            association_id=uuid4(), request=request, request_digest=request.digest,
            version=request.expected_version + 1,
            previous_association_id=previous.association_id if previous else None,
            proof=proof, actor=actor, created_at=datetime.now(UTC),
        )
        conn.execute(
            "INSERT INTO world_mechanics.association "
            "(association_id,world_id,node_id,version,request_id,previous_association_id,payload) "
            "VALUES(%s,%s,%s,%s,%s,%s,%s)",
            (record.association_id,world,request.target.node_id,record.version,request.request_id,
             record.previous_association_id,Jsonb(record.model_dump(mode="json"))),
        )
        return AssociateWorldMechanicsResponse(association=record, replayed=False)
