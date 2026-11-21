import {useState} from 'react';
import {CombatRosterTable} from './CombatRosterTable';
import {stepCombatTurn} from './combatTurn';
import type {CombatEncounterDraft, CombatEntity} from './combatTypes';

function participant(id: string, name: string, team: CombatEntity['team'], order: number, init: number, ac: number, hp: number): CombatEntity {
  return {
    id, name, team, order, init, ac, hp, max_hp: hp, temp_hp: 0, defeated: false,
    notes: '', conditions: [], tags: [], source: 'manual', provenance: [],
    statblock_path: null, statblock_artifact_id: null, statblock_title: null, corpus_fingerprint: null,
  };
}

const sample: CombatEncounterDraft = {
  schema: 'dmb_combat_encounter_draft_v1',
  title: 'Crossing at dusk',
  round: 1,
  queue_model: 'circular_barrel_v1',
  active_turn_entity_id: 'mira',
  round_start_entity_id: 'mira',
  entities: [
    {...participant('mira', 'Mira Vale', 'pc', 1, 19, 17, 32), conditions: ['Concentrating'], notes: 'Keeps watch near the cart.'},
    {...participant('brute', 'Harbor Brute', 'enemy', 2, 17, 15, 68), notes: 'Blocks the bridge and guards the gate.'},
    participant('keeper', 'Keeper', 'ally', 3, 10, 13, 19),
  ],
  groups: [],
  provenance: [],
};

export function CombatSamplePreview({disabled, onClose, onKeep}: {
  disabled: boolean;
  onClose: () => void;
  onKeep: (draft: CombatEncounterDraft) => Promise<void>;
}) {
  const [draft, setDraft] = useState(sample);
  return <section className="combat-start-roster" aria-label="Sample encounter">
    <div className="combat-start-card">
      <h3>{draft.title}</h3>
      <p>D&amp;D 5e sample · Unsaved</p>
      <button type="button" disabled={disabled} onClick={onClose}>Close sample</button>
      <button type="button" disabled={disabled} onClick={() => void onKeep(draft)}>Create encounter from sample</button>
      <p>Round {draft.round} · {draft.entities.find(entity => entity.id === draft.active_turn_entity_id)?.name}</p>
      <button type="button" disabled={disabled} onClick={() => setDraft(current => stepCombatTurn(current, 'previous'))}>Back</button>
      <button type="button" disabled={disabled} onClick={() => setDraft(current => stepCombatTurn(current, 'next'))}>Next turn</button>
    </div>
    <CombatRosterTable draft={draft} disabled onToggleGroup={() => undefined} renderRow={(entity, hidden) =>
      <tr key={entity.id} hidden={hidden}>
        <td>{entity.init}</td>
        <th scope="row">{entity.name}{draft.active_turn_entity_id === entity.id && ' · Now'}</th>
        <td>{entity.ac}</td><td>{entity.hp} / {entity.max_hp}</td><td>—</td>
        <td>{entity.conditions.join(' · ') || '—'}</td><td>{entity.notes || '—'}</td><td>—</td>
      </tr>
    }/>
  </section>;
}
