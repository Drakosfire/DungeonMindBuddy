import type {CombatEncounterDraft, CombatEncounterRecord} from './combatTypes';

export const combatSelectionKey = (worldId: string) => `dmb.combat.selected:${worldId}`;
export const combatRecoveryKey = (worldId: string, id: string) => `dmb.combat.recovery:${worldId}:${id}`;
export interface CombatRecovery {
  schema: 'dmb_combat_recovery_v1';
  base: CombatEncounterRecord;
  draft: CombatEncounterDraft;
  pending: {expected_revision: number; draft: CombatEncounterDraft} | null;
}
function ordered(value: unknown): unknown {
  if (Array.isArray(value)) return value.map(ordered);
  if (value && typeof value === 'object') return Object.fromEntries(Object.entries(value).sort(([a],[b]) => a.localeCompare(b)).map(([key,item]) => [key,ordered(item)]));
  return value;
}
export const combatDraftEqual = (a: unknown, b: unknown) => JSON.stringify(ordered(a)) === JSON.stringify(ordered(b));
function validDraft(value: unknown): value is CombatEncounterDraft {
  if (!value || typeof value !== 'object') return false;
  const d = value as CombatEncounterDraft;
  return typeof d.title === 'string' && d.schema === 'dmb_combat_encounter_draft_v1'
    && Number.isInteger(d.round) && d.round > 0 && d.queue_model === 'circular_barrel_v1'
    && Array.isArray(d.entities) && Array.isArray(d.groups) && Array.isArray(d.provenance)
    && d.entities.every(e => e && typeof e.id === 'string' && typeof e.name === 'string'
      && Number.isInteger(e.order) && typeof e.notes === 'string' && typeof e.temp_hp === 'number'
      && typeof e.defeated === 'boolean' && Array.isArray(e.conditions) && Array.isArray(e.tags)
      && Array.isArray(e.provenance));
}
function parse(raw: string | null, current: CombatEncounterRecord): CombatRecovery | null {
  if (raw === null) return null;
  const saved = JSON.parse(raw) as CombatRecovery;
  if (!saved || saved.schema !== 'dmb_combat_recovery_v1' || !saved.base
      || saved.base.world_id !== current.world_id || saved.base.encounter_id !== current.encounter_id
      || !Number.isInteger(saved.base.revision) || saved.base.revision < 1
      || !validDraft(saved.base.draft) || !validDraft(saved.draft)
      || !saved.base.ruleset || !Array.isArray(saved.base.ruleset.fields)
      || (saved.pending !== null && (!saved.pending || saved.pending.expected_revision !== saved.base.revision
        || !validDraft(saved.pending.draft)))) {
    throw new Error('Stored Combat recovery is invalid or belongs to a different encounter. It has been preserved.');
  }
  return saved;
}

/** Same-origin recovery coordination only. APP expected-revision CAS owns commits. */
export class CombatRecoverySession {
  private release: (() => void) | null = null;
  private key: string | null = null;
  private expectedRaw: string | null = null;
  private generation = 0;
  close() { this.generation++; this.release?.(); this.release = null; this.key = null; }

  async open(record: CombatEncounterRecord, isCurrent: () => boolean): Promise<{recovery: CombatRecovery | null; committedMatch: boolean}> {
    this.close();
    const generation = this.generation;
    const key = combatRecoveryKey(record.world_id, record.encounter_id);
    if (!navigator.locks) throw new Error('This browser cannot safely retain Combat drafts across views.');
    await new Promise<void>((resolve, reject) => {
      void navigator.locks.request(key, {ifAvailable: true}, async lock => {
        if (!lock) {reject(new Error('This encounter is open in another view. Close that editor before opening it here.')); return;}
        if (generation !== this.generation || !isCurrent()) {reject(new Error('Combat view changed.')); return;}
        await new Promise<void>(finish => {
          this.release = finish; this.key = key; resolve();
        });
      }).catch(reject);
    });
    try {
      if (generation !== this.generation || !isCurrent()) throw new Error('Combat view changed.');
      this.expectedRaw = localStorage.getItem(key);
      const recovery = parse(this.expectedRaw, record);
      const committedMatch = !!recovery?.pending && record.revision === recovery.pending.expected_revision + 1
        && combatDraftEqual(record.draft, recovery.pending.draft);
      let remaining = recovery;
      if (committedMatch && recovery) {
        if (combatDraftEqual(recovery.draft, recovery.pending!.draft)) {this.clear(); remaining = null;}
        else { this.write(record, recovery.draft); remaining = {...recovery,base:record,pending:null}; }
      }
      localStorage.setItem(combatSelectionKey(record.world_id), record.encounter_id);
      return {recovery: remaining, committedMatch};
    } catch (error) { if (generation === this.generation) this.close(); throw error; }
  }

  private assertOwned(): string {
    if (!this.release || !this.key) throw new Error('Combat recovery ownership is unavailable. Reopen before editing.');
    if (localStorage.getItem(this.key) !== this.expectedRaw) throw new Error('Stored Combat draft changed. Reopen before editing; recovery is preserved.');
    return this.key;
  }
  write(base: CombatEncounterRecord, draft: CombatEncounterDraft, pending: CombatRecovery['pending'] = null) {
    const key = this.assertOwned();
    if (key !== combatRecoveryKey(base.world_id, base.encounter_id)) throw new Error('Combat recovery scope changed.');
    const raw = JSON.stringify({schema:'dmb_combat_recovery_v1', base, draft, pending} satisfies CombatRecovery);
    localStorage.setItem(key, raw);
    this.expectedRaw = raw;
    if (localStorage.getItem(key) !== raw) throw new Error('Combat draft storage could not be verified.');
  }
  clear() {
    const key = this.assertOwned();
    localStorage.removeItem(key); this.expectedRaw = null;
    if (localStorage.getItem(key) !== null) throw new Error('Combat recovery cleanup could not be verified.');
  }
}
