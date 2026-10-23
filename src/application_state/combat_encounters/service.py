"""Transactional service for durable Combat encounters."""

from __future__ import annotations

import re
from datetime import UTC, datetime
from uuid import UUID, uuid4

from application_state.cli import assert_at_head
from application_state.combat_encounters import repository as repo
from application_state.combat_encounters.rulesets import load_ruleset, ruleset_digest
from application_state.combat_encounters.types import (
    CombatEncounterDraft,
    CombatEncounterRecord,
    CombatWorldIdentity,
    CreateCombatEncounterRequest,
    SaveCombatEncounterRequest,
    SavedCombatMechanicsSnapshot,
)
from application_state.config import load_runtime_dsn
from application_state.errors import (
    ApplicationStateConflictError,
    ApplicationStateNotFoundError,
    ApplicationStateValidationError,
)
from application_state.unit_of_work import unit_of_work

_WORLD_ID = re.compile(r"^[a-z][a-z0-9_-]{0,62}$")


def _world_id(value: str) -> str:
    if not isinstance(value, str) or not _WORLD_ID.fullmatch(value):
        raise ApplicationStateValidationError("world_id must be a canonical managed World id")
    return value


def _encounter_id(value: UUID | str) -> UUID:
    try:
        parsed = value if isinstance(value, UUID) else UUID(str(value))
    except (TypeError, ValueError, AttributeError) as exc:
        raise ApplicationStateValidationError("encounter_id must be a UUID") from exc
    if str(value) != str(parsed):
        raise ApplicationStateValidationError("encounter_id must be a canonical UUID")
    return parsed


def _now() -> datetime:
    return datetime.now(UTC)


def create_encounter(
    *, world_id: str, request: CreateCombatEncounterRequest
) -> CombatEncounterRecord:
    canonical_world_id = _world_id(world_id)
    try:
        ruleset = load_ruleset(request.ruleset_id)
    except ValueError as exc:
        raise ApplicationStateValidationError(str(exc)) from exc
    now = _now()
    record = CombatEncounterRecord(
        encounter_id=uuid4(),
        world_id=canonical_world_id,
        campaign_id=request.campaign_id,
        session=request.session,
        revision=1,
        ruleset=ruleset,
        ruleset_digest=ruleset_digest(ruleset),
        draft=CombatEncounterDraft(title=request.title),
        created_at=now,
        updated_at=now,
    )
    dsn = load_runtime_dsn()
    assert_at_head(dsn=dsn)
    with unit_of_work(dsn) as conn:
        return repo.insert_encounter(conn, record)


def get_encounter(*, world_id: str, encounter_id: UUID | str, scope=None) -> CombatEncounterRecord:
    canonical_world_id = _world_id(world_id)
    canonical_encounter_id = _encounter_id(encounter_id)
    dsn = load_runtime_dsn()
    assert_at_head(dsn=dsn)
    with unit_of_work(dsn) as conn:
        from application_state.combat_encounters.access import guard
        guard(conn, world_id=canonical_world_id, encounter_id=canonical_encounter_id, scope=scope)
        record = repo.get_encounter(
            conn, encounter_id=canonical_encounter_id, world_id=canonical_world_id
        )
        if record is None:
            raise ApplicationStateNotFoundError(
                f"Combat encounter not found in World {canonical_world_id}"
            )
        _require_integrity(record)
        return record


def list_encounters(*, world_id: str) -> list[CombatEncounterRecord]:
    canonical_world_id = _world_id(world_id)
    dsn = load_runtime_dsn()
    assert_at_head(dsn=dsn)
    with unit_of_work(dsn) as conn:
        records = repo.list_encounters(conn, world_id=canonical_world_id)
        for record in records:
            _require_integrity(record)
        return records


def save_encounter(
    *, world_id: str, encounter_id: UUID | str, request: SaveCombatEncounterRequest,
    verified_world_identities: dict[str, CombatWorldIdentity] | None = None,
    verified_mechanics_snapshots: dict | None = None,
    scope=None,
) -> CombatEncounterRecord:
    canonical_world_id = _world_id(world_id)
    canonical_encounter_id = _encounter_id(encounter_id)
    dsn = load_runtime_dsn()
    assert_at_head(dsn=dsn)
    with unit_of_work(dsn) as conn:
        from application_state.combat_encounters.access import guard
        guard(conn, world_id=canonical_world_id, encounter_id=canonical_encounter_id, scope=scope, for_mutation=True)
        before = repo.get_encounter(
            conn, encounter_id=canonical_encounter_id, world_id=canonical_world_id
        )
        if before is None:
            raise ApplicationStateNotFoundError(
                f"Combat encounter not found in World {canonical_world_id}"
            )
        _require_integrity(before)
        if before.revision != request.expected_revision:
            raise ApplicationStateConflictError("Combat encounter changed since it was opened; reload before saving")
        existing = {entity.id: entity for entity in before.draft.entities}
        new_snapshots = []
        for entity in request.draft.entities:
            prior = existing.get(entity.id)
            if entity.mechanics_snapshot is not None and prior is None:
                if isinstance(entity.mechanics_snapshot, SavedCombatMechanicsSnapshot):
                    raise ApplicationStateValidationError("Saved mechanics overrides require explicit adoption for an existing actor")
                if (verified_mechanics_snapshots or {}).get(entity.id) != entity.mechanics_snapshot:
                    raise ApplicationStateValidationError("New mechanics snapshot must be independently verified")
                from application_state.combat_encounters.types import AcceptedCombatMechanicsSnapshot
                if isinstance(entity.mechanics_snapshot, AcceptedCombatMechanicsSnapshot):
                    if entity.mechanics_snapshot.managed_world_id != canonical_world_id:
                        raise ApplicationStateValidationError("Accepted mechanics belong to a different World")
                    if entity.source != "manual" or entity.provenance or entity.statblock_artifact_id or entity.statblock_path or entity.statblock_title or entity.corpus_fingerprint or entity.tags:
                        raise ApplicationStateValidationError("Direct accepted mechanics cannot claim another source")
                else:
                    new_snapshots.append(entity.mechanics_snapshot)
            if prior is not None and entity.mechanics_snapshot != prior.mechanics_snapshot:
                raise ApplicationStateValidationError("Saved combatant mechanics snapshot cannot be changed")
            if prior is not None:
                if (entity.world_identity, entity.provenance, entity.statblock_artifact_id,
                    entity.statblock_path, entity.statblock_title, entity.corpus_fingerprint, entity.source) != (
                    prior.world_identity, prior.provenance, prior.statblock_artifact_id,
                    prior.statblock_path, prior.statblock_title, prior.corpus_fingerprint, prior.source):
                    raise ApplicationStateValidationError("Saved combatant source identity cannot be changed")
            elif entity.world_identity is not None:
                if (verified_world_identities or {}).get(entity.id) != entity.world_identity:
                    raise ApplicationStateValidationError("New World combatant identity must be verified")
                if entity.source != "manual" or entity.provenance or entity.statblock_artifact_id or entity.statblock_path or entity.statblock_title or entity.corpus_fingerprint or entity.tags:
                    raise ApplicationStateValidationError("World identity alone supplies no statblock mechanics")
        from application_state.world_mechanics.service import verify_current_slots
        verify_current_slots(conn, world_id=canonical_world_id, snapshots=new_snapshots)
        saved = repo.cas_replace_draft(
            conn,
            encounter_id=canonical_encounter_id,
            world_id=canonical_world_id,
            expected_revision=request.expected_revision,
            draft=request.draft.model_dump(mode="json", by_alias=True),
            updated_at=_now(),
        )
        if saved is None:
            raise ApplicationStateConflictError(
                "Combat encounter changed since it was opened; reload before saving"
            )
        _require_integrity(saved)
        return saved


def _require_integrity(record: CombatEncounterRecord) -> None:
    stored_digest = ruleset_digest(record.ruleset)
    if stored_digest != record.ruleset_digest:
        raise ApplicationStateValidationError("The encounter's stored ruleset digest is invalid")
    # Encounters own the complete immutable ruleset snapshot. Reads validate the
    # snapshot digest and never resolve a saved encounter through a mutable
    # "current" catalog entry.
