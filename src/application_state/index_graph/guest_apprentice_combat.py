"""Seed the released Apprentice encounter in each isolated guest World."""
from __future__ import annotations

import os
from datetime import UTC, datetime
from uuid import uuid4

from application_state.combat_encounters import repository
from application_state.combat_encounters.rulesets import load_ruleset, ruleset_digest
from application_state.combat_encounters.types import CombatEncounterDraft, CombatEncounterRecord, CombatEntity

_MARKER = 'guest_apprentice_combat_v1'
_PLAN_MARKER = 'guest_apprentice_plan_v1'


def seed_guest_apprentice_combat(conn, *, session_id: str, world_id: str) -> None:
    if os.getenv('DMB_HOSTED_GUEST_PLAY_ENABLED') != '1':
        return
    bindings = dict(conn.execute(
        'SELECT key, value FROM application_state.index_graph_bindings '
        'WHERE session_id = %s::uuid AND key IN (%s, %s)',
        (session_id, _MARKER, _PLAN_MARKER),
    ).fetchall())
    if _MARKER in bindings or _PLAN_MARKER not in bindings:
        return
    count = conn.execute('SELECT count(*) FROM combat.encounter WHERE world_id = %s', (world_id,)).fetchone()[0]
    if count >= 16:
        return
    rules = load_ruleset('dnd5e.manual-tracking')
    entities = [CombatEntity(id='delphinius', name='Delphinius', order=1, team='enemy',
        notes='Hidden in the north control room (DC 13). If detected, fights unless the party attempts dialogue. DC 20 Charisma or effective roleplay can persuade him to surrender. The east and west walls move inward five feet each round.')] + [
        CombatEntity(id=f'skeleton-{i}', name=f'Skeleton {i}', order=i + 1, team='enemy',
                     notes='Drops from the ceiling if the confrontation turns to combat.') for i in range(1, 7)]
    now = datetime.now(UTC)
    record = CombatEncounterRecord(encounter_id=uuid4(), world_id=world_id, campaign_id=None,
        session=None, revision=1, ruleset=rules, ruleset_digest=ruleset_digest(rules),
        draft=CombatEncounterDraft(title='Funhouse: The Closing Walls', entities=entities),
        created_at=now, updated_at=now)
    repository.insert_encounter(conn, record)
    conn.execute('INSERT INTO application_state.index_graph_bindings(session_id, key, value) '
                 'VALUES (%s::uuid, %s, %s)', (session_id, _MARKER, str(record.encounter_id)))
