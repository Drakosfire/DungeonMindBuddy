"""Identifier-only purge receipts sharing the saved revision write lock."""

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from application_state.errors import ApplicationStateConflictError
from application_state.unit_of_work import unit_of_work

from .service import _dsn


@dataclass(frozen=True)
class PurgeTarget:
    statblock_id: str
    world_id: str
    draft_id: UUID
    draft_version: int
    expected_revision_id: str

    def key(self) -> tuple:
        return (
            self.statblock_id, self.world_id, self.draft_id, self.draft_version,
            self.expected_revision_id,
        )


def find_receipt(*, world_id: str, draft_id: UUID) -> tuple[PurgeTarget, bool] | None:
    """Read the exact retry target after the draft has left the store."""
    with unit_of_work(_dsn()) as conn:
        row = conn.execute(
            """SELECT statblock_id, world_id, draft_id, draft_version, expected_revision_id, complete
               FROM mechanics_revision.purge WHERE world_id=%s AND draft_id=%s""",
            (world_id, draft_id),
        ).fetchone()
    if row is None:
        return None
    statblock_id, bound_world, bound_draft, draft_version, revision_id, complete = row
    return PurgeTarget(statblock_id, bound_world, bound_draft, draft_version, revision_id), complete


def assert_draft_writable(*, draft_id: UUID, statblock_id: str | None) -> None:
    """Use the durable receipt to exclude draft updates and new claims of its mechanics."""
    with unit_of_work(_dsn()) as conn:
        blocked = conn.execute(
            """SELECT 1 FROM mechanics_revision.purge
               WHERE draft_id=%s OR statblock_id=%s LIMIT 1""",
            (draft_id, statblock_id),
        ).fetchone()
    if blocked:
        raise ApplicationStateConflictError("This statblock is being deleted or has been deleted")


def _lock(conn, statblock_id: str) -> None:
    conn.execute(
        "SELECT pg_advisory_xact_lock(hashtextextended(%s,0))",
        (f"mechanics-revision:{statblock_id}",),
    )


def _receipt(conn, target: PurgeTarget):
    rows = conn.execute(
        """SELECT statblock_id, world_id, draft_id, draft_version, expected_revision_id, complete
           FROM mechanics_revision.purge WHERE statblock_id=%s OR draft_id=%s""",
        (target.statblock_id, target.draft_id),
    ).fetchall()
    if not rows:
        return None
    if len(rows) != 1 or tuple(rows[0][:-1]) != target.key():
        raise ApplicationStateConflictError("Deletion already belongs to a different saved statblock")
    return rows[0][-1]


def claim(target: PurgeTarget, *, authorize) -> bool:
    """Return whether this exact deletion has already completed.

    The caller pins the draft before claiming and holds its filesystem lock
    through the claim. Authorization runs before acquiring APP locks.
    """
    authorize()
    with unit_of_work(_dsn()) as conn:
        _lock(conn, target.statblock_id)
        complete = _receipt(conn, target)
        if complete is not None:
            return complete
        unresolved = conn.execute(
            """SELECT 1 FROM mechanics_revision.operation
               WHERE statblock_id=%s AND state IN ('prepared','outcome_unknown') LIMIT 1""",
            (target.statblock_id,),
        ).fetchone()
        if unresolved:
            raise ApplicationStateConflictError("Resolve the pending mechanics save before deleting")
        # Preflight supplied a validated lineage. Recheck its unextended tip
        # under the same lock that admits revision writes.
        newer_revision = conn.execute(
            """SELECT 1 FROM mechanics_revision.operation
               WHERE statblock_id=%s AND state='committed'
                 AND payload #>> '{base,revision_id}' = %s LIMIT 1""",
            (target.statblock_id, target.expected_revision_id),
        ).fetchone()
        if newer_revision:
            raise ApplicationStateConflictError("Saved mechanics changed before deletion")
        conn.execute(
            """INSERT INTO mechanics_revision.purge
               (statblock_id, world_id, draft_id, draft_version, expected_revision_id)
               VALUES (%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING""",
            target.key(),
        )
        return _receipt(conn, target) is True


def require_available_statblocks(conn, statblock_ids: Iterable[str], *, wait: bool = True) -> None:
    """Fence snapshot admission against a concurrently claimed deletion."""
    for statblock_id in sorted(set(statblock_ids)):
        if wait:
            _lock(conn, statblock_id)
        elif not conn.execute(
            "SELECT pg_try_advisory_xact_lock_shared(hashtextextended(%s,0))",
            (f"mechanics-revision:{statblock_id}",),
        ).fetchone()[0]:
            raise ApplicationStateConflictError("Statblock mechanics are changing. Retry opening the encounter.")
        if conn.execute(
            "SELECT 1 FROM mechanics_revision.purge WHERE statblock_id=%s",
            (statblock_id,),
        ).fetchone():
            raise ApplicationStateConflictError("This statblock is being deleted or has been deleted")


def redact_combat_draft(draft, statblock_id: str):
    """Preserve every tracker value while replacing the exact source payload."""
    from application_state.combat_encounters.types import DeletedCombatMechanics

    entities = []
    for actor in draft.entities:
        snapshot = actor.mechanics_snapshot
        if snapshot is not None and snapshot.locator.statblock_id == statblock_id:
            actor = actor.model_copy(update={
                "mechanics_snapshot": None,
                "deleted_mechanics": DeletedCombatMechanics(
                    statblock_id=statblock_id, revision_id=snapshot.locator.revision_id,
                ),
            })
        entities.append(actor)
    return draft.model_copy(update={"entities": entities})


def remove_current_combat_copies(target: PurgeTarget) -> None:
    """Replace live encounter copies with identifier-only references under the App receipt."""
    from application_state.combat_encounters import repository
    from application_state.combat_encounters.scene_templates import redact_saved_versions
    from application_state.errors import ApplicationStateIntegrityError

    with unit_of_work(_dsn()) as conn:
        _lock(conn, target.statblock_id)
        if _receipt(conn, target) is None:
            raise ApplicationStateConflictError("Deletion has not been claimed")
        encounters = repository.lock_encounters_with_statblock(
            conn, world_id=target.world_id, statblock_id=target.statblock_id,
        )
        for encounter in encounters:
            draft = redact_combat_draft(encounter.draft, target.statblock_id)
            saved = repository.cas_replace_draft(
                conn, world_id=encounter.world_id, encounter_id=encounter.encounter_id,
                expected_revision=encounter.revision, draft=draft.model_dump(mode="json", by_alias=True),
                updated_at=datetime.now(UTC),
            )
            if saved is None:
                raise ApplicationStateIntegrityError("Locked encounter changed during statblock deletion")
        redact_saved_versions(conn, world_id=target.world_id, statblock_id=target.statblock_id)


def settle_after_cleanup(target: PurgeTarget, *, authorize) -> None:
    """Drop local revision request copies after downstream cleanup is verified."""
    authorize()
    with unit_of_work(_dsn()) as conn:
        _lock(conn, target.statblock_id)
        if _receipt(conn, target) is None:
            raise ApplicationStateConflictError("Deletion has not been claimed")
        completed = conn.execute(
            "SELECT mechanics_revision.complete_statblock_purge(%s,%s,%s,%s,%s)",
            target.key(),
        ).fetchone()[0]
        if not completed:
            raise ApplicationStateConflictError("Deletion receipt changed")
