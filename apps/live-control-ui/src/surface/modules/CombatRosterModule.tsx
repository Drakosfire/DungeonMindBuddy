import {stepCombatTurn} from "../../combat/combatTurn";
import {CombatSamplePreview} from "../../combat/CombatSamplePreview";
import {combatEncounterHref} from "../../combat/combatEncounterLocation";
import type {SavedConversationVariantTarget} from '../../statblocks/savedStatblockLocation';
import {useTourNavigationGuard} from '../../guidedTour/Navigation';
import {useTourEncounter,type TourEncounterScope} from '../../guidedTour/EncounterScope';
import type {TourDispatchScope} from '../../guidedTour/GuidedTour';
import {useTourRun} from '../../guidedTour/RunScope';
import {useGuidedTour} from '../../guidedTour/GuidedTour';
import {CombatTourObservation,type AcknowledgedCombatSave} from '../../guidedTour/CombatObservations';
import { useEffect, useId, useLayoutEffect, useMemo, useRef, useState } from "react";

import {
  createWorldCombatEncounter,
  createManualCombatEncounter,
  getAnyWorldCombatEncounter,
  listAnyWorldCombatEncounters,
  saveWorldCombatEncounter,
} from "../../combat/combatApi";
import {ManualCombatEditor} from "../../combat/ManualCombatEditor";
import {ManualCombatProfileForm} from "../../combat/ManualCombatProfileForm";
import {isManualCombatRecord,type AnyCombatRecord,type ManualCombatRecord} from "../../combat/ManualCombatTypes";
import type { CombatEncounterDraft, CombatEncounterRecord, CombatEntity } from "../../combat/combatTypes";
import { CombatMechanicsAdoption } from '../../combat/CombatMechanicsAdoption';
import { CombatEncounterAssembly } from "../../combat/CombatEncounterAssembly";
import {CombatRosterWorkspace, type CombatProjectionControl} from '../../combat/CombatRosterWorkspace';
import "../../combat/combatRoster.css";
import {CombatRecoverySession, combatDraftEqual, combatSelectionKey, type CombatRecovery} from "../../combat/combatRecovery";
import { useSelectedWorld } from "../../selectedWorld/SelectedWorldContext";

const DND5E_RULESET_ID = "dnd5e.manual-tracking";

function asInput(value: unknown): string {
  if (value === null || value === undefined) return "";
  return String(value);
}

function numericValue(value: number | string | null): number | null {
  if (typeof value === "number" && Number.isFinite(value)) return value;
  if (typeof value !== "string" || value.trim() === "") return null;
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
}

function manualStatValue(value: string): number | string | null {
  if (value.trim() === "") return null;
  const numeric = Number(value);
  return Number.isSafeInteger(numeric) ? numeric : value;
}

function activeActor(draft: CombatEncounterDraft | null): CombatEntity | null {
  if (!draft) return null;
  return draft.entities.find(
    (entity) => entity.id === draft.active_turn_entity_id && !entity.defeated,
  ) ?? null;
}

function nextActor(draft: CombatEncounterDraft | null): CombatEntity | null {
  if (!draft) return null;
  const living = draft.entities.filter((entity) => !entity.defeated);
  if (living.length === 0) return null;
  const activeIndex = living.findIndex((entity) => entity.id === draft.active_turn_entity_id);
  return living[(activeIndex + 1 + living.length) % living.length] ?? living[0] ?? null;
}

function RosterRow({
  entity,
  active,
  next,
  hidden,
  disabled,
  onChange,
  onSetActive,
  onRemove,
  projection,
  onMove,
  canMoveEarlier,
  canMoveLater,
}: {
  entity: CombatEntity;
  active: boolean;
  next: boolean;
  hidden: boolean;
  disabled: boolean;
  onChange: (entity: CombatEntity) => void;
  onSetActive: () => void;
  onRemove: () => void;
  projection: CombatProjectionControl;
  onMove: (direction: 'earlier' | 'later') => void;
  canMoveEarlier: boolean;
  canMoveLater: boolean;
}) {
  const [damage, setDamage] = useState("1");
  const [heal, setHeal] = useState("1");
  const [error, setError] = useState<string | null>(null);
  const [conditionsInput, setConditionsInput] = useState<string | null>(null);
  const editor = useRef<HTMLDialogElement>(null);
  const editTrigger = useRef<HTMLButtonElement>(null);

  function numberOrNull(value: string): number | null {
    if (value.trim() === "") return null;
    const parsed = Number(value);
    return Number.isFinite(parsed) ? Math.trunc(parsed) : null;
  }

  function update(patch: Partial<CombatEntity>) {
    setError(null);
    onChange({ ...entity, ...patch });
  }

  function applyDelta(action: "damage" | "heal", amount: number) {
    const hp = numericValue(entity.hp);
    const maximum = numericValue(entity.max_hp);
    const maxHp = maximum !== null && Number.isSafeInteger(maximum) ? maximum : null;
    if (hp === null) {
      setError("Enter numeric HP before applying damage or healing.");
      return;
    }
    if (action === "damage") {
      const absorbed = Math.min(entity.temp_hp, amount);
      const remaining = amount - absorbed;
      update({ temp_hp: entity.temp_hp - absorbed, hp: Math.max(0, hp - remaining) });
      return;
    }
    update({ hp: maxHp === null ? hp + amount : Math.max(hp, Math.min(maxHp, hp + amount)) });
  }

  const damageAmount = Number.parseInt(damage, 10);
  const healAmount = Number.parseInt(heal, 10);

  const hp = numericValue(entity.hp);
  const maximum = numericValue(entity.max_hp);
  const meterValue = hp !== null && maximum !== null && Number.isSafeInteger(maximum) && maximum > 0 && hp >= 0
    ? Math.min(hp, maximum) : null;
  const notePreview = entity.notes.length > 180
    ? entity.notes.trimStart().slice(0, 145).replace(/\s+\S*$/, "").trimEnd() : null;
  const healthLabel = entity.hp === null ? "Unrecorded"
    : entity.max_hp === null ? String(entity.hp) : `${entity.hp} / ${entity.max_hp}`;

  return (
    <tr role="row" hidden={hidden} className={active ? "combat-roster-active-row" : entity.defeated ? "combat-roster-defeated-row" : undefined}>
      <td role="cell" className="combat-roster-init" data-column="Initiative">{entity.init ?? "—"}</td>
      <th role="rowheader" scope="row" className="combat-roster-participant">
        <strong>{entity.name}</strong>
        <span className="combat-roster-team-label">{entity.team === "pc" ? "PC" : entity.team}</span>
        {active ? <span className="combat-roster-now">Now</span> : next && <span className="combat-roster-next">Next</span>}
        {entity.defeated && <span className="combat-roster-out">Defeated</span>}
      </th>
      <td role="cell" className="combat-roster-defense" data-column="AC">{entity.ac ?? "—"}</td>
      <td role="cell" className="combat-roster-health" data-column="HP">
        <div className="combat-roster-health-label">
          <span>{healthLabel}</span>
          {entity.temp_hp > 0 && <span className="combat-roster-temp-label">+{entity.temp_hp} temp</span>}
        </div>
        {meterValue !== null && maximum !== null && <meter className="combat-roster-hp-meter" min={0} max={maximum} value={meterValue} aria-label={`Recorded HP for ${entity.name}`}/>}
      </td>
      <td role="cell" className="combat-roster-quick-adjust" data-column="Adjust HP">
        <button type="button" aria-label={`Deal 1 damage to ${entity.name}`} disabled={disabled || hp === null} onClick={() => applyDelta("damage", 1)}>−</button>
        <button type="button" aria-label={`Heal ${entity.name} by 1`} disabled={disabled || hp === null} onClick={() => applyDelta("heal", 1)}>+</button>
      </td>
      <td role="cell" className="combat-roster-condition-list" data-empty={entity.conditions.length === 0 || undefined} data-column="Conditions">
        {entity.conditions.length === 0 ? "—" : entity.conditions.map((condition, index) =>
          <span key={`${index}:${condition}`} className="combat-roster-condition">{condition}</span>)}
      </td>
      <td role="cell" className="combat-roster-note-preview" data-empty={!entity.notes || undefined} data-column="Notes">
        {notePreview ? <details className="combat-roster-long-note">
          <summary aria-label={`Full note for ${entity.name}`}><span>{notePreview}…</span></summary>
          <p>{entity.notes}</p>
        </details> : entity.notes || "—"}
      </td>
      <td role="cell" className="combat-roster-row-actions">
        {entity.deleted_mechanics && <span>Statblock deleted</span>}
        {projection.available && <button type="button" aria-label={entity.mechanics_snapshot ? `Keep statblock open for ${entity.name}` : `Open corpus sheet for ${entity.name}`}
          aria-pressed={projection.selected} aria-controls={projection.selected ? projection.regionId : undefined}
          onClick={event => projection.open(event.currentTarget)}>Sheet</button>}
        <button ref={editTrigger} type="button" aria-label={`Edit ${entity.name}`} aria-haspopup="dialog" disabled={disabled} onClick={() => editor.current?.showModal()}>Edit</button>
        <dialog ref={editor} className="combat-mechanics-dialog combat-roster-actor-editor" aria-label={`Edit ${entity.name}`}
          onClose={() => {
            setConditionsInput(null);
            requestAnimationFrame(() => editTrigger.current?.focus({preventScroll: true}));
          }}
          onKeyDown={event => { if (event.key === "Escape") event.stopPropagation(); }}>
          <header>
            <strong>{entity.name}</strong>
            <button type="button" onClick={() => editor.current?.close()}>Done</button>
          </header>
          {(entity.world_identity || entity.statblock_title || entity.statblock_artifact_id) &&
            <p className="module-muted">{entity.world_identity ? `World: ${entity.world_identity.label} · Manual stats` : entity.statblock_title ?? entity.statblock_artifact_id}</p>}
          <fieldset disabled={disabled} className="combat-roster-edit-fields">
            <legend>Tracked values</legend>
            <label>Initiative<input aria-label={`Initiative for ${entity.name}`} value={asInput(entity.init)}
              onChange={event => update({init: numberOrNull(event.target.value)})}/></label>
            <label>AC<input aria-label={`AC for ${entity.name}`} value={asInput(entity.ac)} maxLength={64}
              onChange={event => update({ac: manualStatValue(event.target.value)})}/></label>
            <label>HP<input aria-label={`HP for ${entity.name}`} value={asInput(entity.hp)}
              onChange={event => {
                const value = event.target.value;
                update({hp: numberOrNull(value) ?? (value.trim() ? value : null)});
              }}/></label>
            <label>Max HP<input aria-label={`Maximum HP for ${entity.name}`} value={asInput(entity.max_hp)} maxLength={64}
              title="Whole numbers cap healing. Text values are tracked manually."
              onChange={event => update({max_hp: manualStatValue(event.target.value)})}/></label>
            <label>Temp HP<input aria-label={`Temp HP for ${entity.name}`} value={asInput(entity.temp_hp)}
              onChange={event => update({temp_hp: Math.max(0, numberOrNull(event.target.value) ?? 0)})}/></label>
            <label>Team<select aria-label={`Team for ${entity.name}`} value={entity.team}
              onChange={event => update({team: event.target.value as CombatEntity["team"]})}>
              <option value="pc">PC</option><option value="ally">Ally</option>
              <option value="enemy">Enemy</option><option value="neutral">Neutral</option>
            </select></label>
            <div className="combat-roster-edit-deltas">
              <input aria-label={`Damage for ${entity.name}`} type="number" min="0" value={damage} onChange={event => setDamage(event.target.value)}/>
              <button type="button" disabled={!Number.isFinite(damageAmount) || damageAmount <= 0} onClick={() => applyDelta("damage", damageAmount)}>Damage</button>
              <input aria-label={`Healing for ${entity.name}`} type="number" min="0" value={heal} onChange={event => setHeal(event.target.value)}/>
              <button type="button" disabled={!Number.isFinite(healAmount) || healAmount <= 0} onClick={() => applyDelta("heal", healAmount)}>Heal</button>
            </div>
            <label className="combat-roster-edit-text">Conditions<textarea rows={2} aria-label={`Conditions for ${entity.name}`}
              value={conditionsInput ?? entity.conditions.join(", ")}
              onBlur={() => setConditionsInput(null)}
              onChange={event => {
                const value = event.target.value;
                setConditionsInput(value);
                update({conditions: value.split(",").map(item => item.trim()).filter(Boolean)});
              }}/></label>
            <label className="combat-roster-edit-text">Notes<textarea rows={3}
              aria-label={`Notes for ${entity.name}`} value={entity.notes} onChange={event => update({notes: event.target.value})}/></label>
            <div className="combat-roster-edit-options">
              <button type="button" aria-label={`Set ${entity.name} as current actor`} onClick={onSetActive} disabled={entity.defeated}>Set current</button>
              <button type="button" aria-label={`Move ${entity.name} earlier`} disabled={!canMoveEarlier} onClick={() => {editor.current?.close(); onMove("earlier");}}>↑</button>
              <button type="button" aria-label={`Move ${entity.name} later`} disabled={!canMoveLater} onClick={() => {editor.current?.close(); onMove("later");}}>↓</button>
              <label><input type="checkbox" checked={entity.defeated} onChange={event => {editor.current?.close(); update({defeated: event.target.checked});}}/> Defeated</label>
              <button type="button" aria-label={`Remove ${entity.name} from encounter draft`}
                title="Remove from the draft. Revert restores the saved roster before Save."
                onClick={() => {editor.current?.close(); onRemove();}}>Remove</button>
            </div>
          </fieldset>
          {error && <p className="module-error" role="alert">{error}</p>}
        </dialog>
      </td>
    </tr>
  );
}

function cloneDraft(draft: CombatEncounterDraft): CombatEncounterDraft {
  return JSON.parse(JSON.stringify(draft)) as CombatEncounterDraft;
}

export interface PreparedCombatOwnerReading {record:AnyCombatRecord|null;blocked:boolean;error:string|null;acknowledged:{dispatchScope:TourDispatchScope|null;scope:TourEncounterScope;before:CombatEncounterRecord;saved:CombatEncounterRecord}|null}
export type CombatHostScope = {worldId:string;encounterId:string;label:string;initialRecord?:AnyCombatRecord;onPreparedState?:(reading:PreparedCombatOwnerReading|null)=>void;runScope?:import("../../combat/runEncountersApi").RunEncounterScope};
export function CombatRosterModule({scope,variant,encounterListHref}:{scope?:CombatHostScope;variant?:SavedConversationVariantTarget;encounterListHref?:string} = {}) {
  const panelRef = useRef<HTMLDivElement>(null);
  const turnRailRef = useRef<HTMLElement>(null);
  const tourRun=useTourRun(),tour=useGuidedTour(),tourEncounter=useTourEncounter();
  const [preparedAcknowledged,setPreparedAcknowledged]=useState<PreparedCombatOwnerReading["acknowledged"]>(null);
  const [tourAcknowledged,setTourAcknowledged]=useState<AcknowledgedCombatSave|null>(null);
  const selectedWorld = useSelectedWorld();
  const worldId = selectedWorld.kind === "managed" && (!scope || scope.worldId === selectedWorld.worldId) ? selectedWorld.worldId : null;
  const worldRequestGeneration = useRef(0);
  const recoverySession = useRef(new CombatRecoverySession());
  const draftRef = useRef<CombatEncounterDraft | null>(null);
  const recordRef = useRef<CombatEncounterRecord | null>(null);
  const pendingSave = useRef<CombatRecovery['pending']>(null);
  const [availableRecovery, setAvailableRecovery] = useState<CombatRecovery | null>(null);
  const [recoveryMessage, setRecoveryMessage] = useState<string | null>(null);
  const [encounters, setEncounters] = useState<AnyCombatRecord[]>([]);
  const [loadedWorldId, setLoadedWorldId] = useState<string | null>(null);
  const [selectedEncounterId, setSelectedEncounterId] = useState("");
  const [record, setRecord] = useState<CombatEncounterRecord | null>(null);
  const [manualRecord,setManualRecord]=useState<ManualCombatRecord|null>(null);
  const [manualBlocked,setManualBlocked]=useState(false);
  const [draft, setDraft] = useState<CombatEncounterDraft | null>(null);
  const [sampleWorld, setSampleWorld] = useState<string | null>(null);
  const sampleTarget = useRef<CombatEncounterRecord | null>(null);
  const [setupSystem, setSetupSystem] = useState<"dnd5e" | "custom">("dnd5e");
  const [newTitle, setNewTitle] = useState("New encounter");
  const [loading, setLoading] = useState(false);
  const [busy, setBusy] = useState<string | null>(null);
  const [adoptionBlocked,setAdoptionBlocked]=useState(false);
  const operationsBlocked=busy!==null||adoptionBlocked||manualBlocked;
  const replacingDraft = adoptionBlocked || busy === "create" || busy === "open" || busy === "reload" || availableRecovery !== null;
  const [error, setError] = useState<string | null>(null);

  useLayoutEffect(() => {
    worldRequestGeneration.current += 1;
    return () => {
      worldRequestGeneration.current += 1;
      recoverySession.current.close();
    };
  }, [worldId, scope?.encounterId]);

  useEffect(() => {
    let alive = true;
    const generation = worldRequestGeneration.current;
    setManualRecord(null);setManualBlocked(false);
    setSampleWorld(null);
    sampleTarget.current = null;
    setRecord(null); recordRef.current = null;
    setDraft(null); draftRef.current = null; pendingSave.current = null;
    setAvailableRecovery(null); setRecoveryMessage(null);
    setEncounters([]);
    setLoadedWorldId(null);
    setSelectedEncounterId("");
    setBusy(null);
    setError(null);
    if (!worldId) {
      setLoading(false);
      return () => { alive = false; };
    }
    setLoading(true);
    if (scope) {
      const opening=scope.initialRecord ? Promise.resolve(scope.initialRecord) : getAnyWorldCombatEncounter(worldId, scope.encounterId,...(scope.runScope?[scope.runScope] as const:[] as const));
      void opening.then(async opened => {
        if (!alive || generation !== worldRequestGeneration.current) return;
        await adoptRecord(opened,worldId,scope.encounterId,generation);
        if (alive && generation === worldRequestGeneration.current) setLoadedWorldId(worldId);
      }).catch(caught => {if(alive && generation===worldRequestGeneration.current)setError(String(caught));})
        .finally(()=>{if(alive && generation===worldRequestGeneration.current)setLoading(false);});
      return ()=>{alive=false;};
    }
    void listAnyWorldCombatEncounters(worldId)
      .then((items) => {
        if (alive && generation === worldRequestGeneration.current) {
          setEncounters(items);
          setLoadedWorldId(worldId);
          const selected = localStorage.getItem(combatSelectionKey(worldId));
          if (items.some(item => item.world_id === worldId && item.encounter_id === selected)) setSelectedEncounterId(selected!);
        }
      })
      .catch((caught) => {
        if (alive && generation === worldRequestGeneration.current) {
          setError(caught instanceof Error ? caught.message : String(caught));
          setLoadedWorldId(worldId);
        }
      })
      .finally(() => {
        if (alive && generation === worldRequestGeneration.current) setLoading(false);
      });
    return () => { alive = false; };
  }, [worldId, scope?.encounterId]);

  const visibleRecord = record?.world_id === worldId ? record : null;
  const visibleDraft = visibleRecord ? draft : null;
  const livingOrder = visibleDraft?.entities.filter(entity => !entity.defeated).map(entity => entity.id) ?? [];
  useLayoutEffect(() => {
    const rail = turnRailRef.current, panel = panelRef.current;
    if (!rail || !panel) return;
    const measure = () => panel.style.setProperty('--combat-turn-rail-height', `${rail.getBoundingClientRect().height}px`);
    measure();
    const observer = typeof ResizeObserver === 'undefined' ? null : new ResizeObserver(measure);
    observer?.observe(rail);
    return () => {observer?.disconnect(); panel.style.removeProperty('--combat-turn-rail-height');};
  }, [visibleRecord?.encounter_id, worldId]);
  const visibleEncounters = encounters.filter((item) => item.world_id === worldId);
  const worldListLoading = worldId !== null && (loading || loadedWorldId !== worldId);
  const dirty = Boolean(visibleRecord && visibleDraft && JSON.stringify(visibleRecord.draft) !== JSON.stringify(visibleDraft));
  const active = useMemo(() => activeActor(visibleDraft), [visibleDraft]);
  const next = useMemo(() => nextActor(visibleDraft), [visibleDraft]);

  function updateDraft(update: (current: CombatEncounterDraft) => CombatEncounterDraft): boolean {
    const current = draftRef.current, base = recordRef.current;
    if (!current || !base) return false;
    try {
      if (adoptionBlocked) throw new Error('Resolve the pending mechanics adoption before editing.');
      if (availableRecovery) throw new Error('Recover or discard the retained Combat draft before editing.');
      if (pendingSave.current && busy !== 'save') throw new Error('The previous Save outcome is unknown. Retry the same Save or explicitly reload; local edits are retained.');
      const nextDraft = update(current);
      recoverySession.current.write(base, nextDraft, pendingSave.current);
      draftRef.current = nextDraft; setDraft(nextDraft); return true;
    } catch (caught) {setError(String(caught)); return false;}
  }

  async function adoptRecord(opened: AnyCombatRecord, requestedWorld: string, requestedId: string | null, generation: number) {
    if (opened.world_id !== requestedWorld || (requestedId && opened.encounter_id !== requestedId)) throw new Error('Combat response belongs to a different encounter.');
    setRecord(null); recordRef.current = null; setDraft(null); draftRef.current = null;
    if(isManualCombatRecord(opened)) {
      recoverySession.current.close();setAvailableRecovery(null);setRecoveryMessage(null);
      setManualRecord(opened);setManualBlocked(true);return;
    }
    setManualRecord(null);setManualBlocked(false);
    const recovery = await recoverySession.current.open(opened, () => generation === worldRequestGeneration.current,!scope);
    if (generation !== worldRequestGeneration.current) return;
    recordRef.current = opened; draftRef.current = cloneDraft(opened.draft); pendingSave.current = null;
    setRecord(opened); setDraft(draftRef.current); setAvailableRecovery(recovery.recovery);
    setRecoveryMessage(recovery.committedMatch ? (recovery.recovery ? 'The submitted Save is committed. Later local edits remain available to recover.' : 'Committed encounter matches the retained Save. No request was reposted.') : null);
  }

  function recoverDraft() {
    if (!availableRecovery) return;
    recordRef.current = availableRecovery.base; draftRef.current = cloneDraft(availableRecovery.draft);
    pendingSave.current = availableRecovery.pending;
    setRecord(availableRecovery.base); setDraft(draftRef.current); setAvailableRecovery(null);
    setRecoveryMessage('Recovered local edits are unsaved. Save uses their original base revision.');
  }

  function discardRecovery() {
    try {recoverySession.current.clear(); setAvailableRecovery(null); setRecoveryMessage(null);}
    catch (caught) {setError(String(caught));}
  }

  function revertDraft() {
    if (!visibleRecord) return;
    try {
      recoverySession.current.clear(); pendingSave.current = null;
      draftRef.current = cloneDraft(visibleRecord.draft); setDraft(draftRef.current);
    } catch (caught) {setError(String(caught));}
  }

  function updateEntity(entityId: string, replacement: CombatEntity) {
    updateDraft((current) => {
      const entities = current.entities.map((entity) => entity.id === entityId ? replacement : entity);
      const index = entities.findIndex(entity => entity.id === entityId);
      const successor = [...entities.slice(index + 1), ...entities.slice(0, index)]
        .find(entity => !entity.defeated)?.id ?? null;
      return {...current, entities,
        active_turn_entity_id: replacement.defeated && current.active_turn_entity_id === entityId
          ? successor : current.active_turn_entity_id,
      };
    });
  }

  async function createEncounter(sample?: CombatEncounterDraft) {
    if (!worldId) return;
    const requestedWorldId = worldId;
    const generation = worldRequestGeneration.current;
    setBusy("create");
    setError(null);
    try {
      const retainedTarget = sample ? sampleTarget.current : null;
      const created = retainedTarget ?? await createWorldCombatEncounter(requestedWorldId, {
        title: sample?.title ?? (newTitle.trim() || "New encounter"),
        ruleset_id: DND5E_RULESET_ID,
      });
      if (generation !== worldRequestGeneration.current) return;
      if (sample) sampleTarget.current = created;
      setEncounters((current) => [created, ...current.filter((item) => item.encounter_id !== created.encounter_id)]);
      setSelectedEncounterId(created.encounter_id);
      if (!retainedTarget || recordRef.current?.encounter_id !== created.encounter_id) {
        await adoptRecord(created, requestedWorldId, null, generation);
      }
      if (sample && generation === worldRequestGeneration.current && recordRef.current?.encounter_id === created.encounter_id) {
        if (updateDraft(() => sample)) closeSample();
      }
    } catch (caught) {
      if (generation === worldRequestGeneration.current) setError(caught instanceof Error ? caught.message : String(caught));
    } finally {
      if (generation === worldRequestGeneration.current) setBusy(null);
    }
  }

  function closeSample() {
    sampleTarget.current = null;
    setSampleWorld(null);
  }

  async function openEncounter() {
    if (!worldId || !selectedEncounterId || dirty) return;
    const requestedWorldId = worldId;
    const requestedEncounterId = selectedEncounterId;
    const generation = worldRequestGeneration.current;
    setBusy("open");
    setError(null);
    try {
      const opened = await getAnyWorldCombatEncounter(requestedWorldId, requestedEncounterId,...(scope?.runScope?[scope.runScope] as const:[] as const));
      if (generation !== worldRequestGeneration.current) return;
      await adoptRecord(opened, requestedWorldId, requestedEncounterId, generation);
    } catch (caught) {
      if (generation === worldRequestGeneration.current) setError(caught instanceof Error ? caught.message : String(caught));
    } finally {
      if (generation === worldRequestGeneration.current) setBusy(null);
    }
  }

  async function saveEncounter() {
    if (!worldId || !visibleRecord || !visibleDraft || (!dirty && !pendingSave.current)) return;
    const requestedWorldId = worldId;
    const submittedRecord = visibleRecord;
    const submittedDraft = cloneDraft(pendingSave.current?.draft ?? visibleDraft);
    const generation = worldRequestGeneration.current,tourAtDispatch=tour?.tracking?tourRun:null,tourDispatch=tour?.captureScope()??null,tourEncounterAtDispatch=tour?.tracking?tourEncounter:null;
    setBusy("save");
    setError(null);
    try {
      const submitted = {expected_revision: submittedRecord.revision, draft: submittedDraft};
      recoverySession.current.write(submittedRecord, draftRef.current ?? submittedDraft, submitted);
      pendingSave.current = submitted;
      const saved = await saveWorldCombatEncounter(requestedWorldId, submittedRecord.encounter_id, submittedRecord.revision, submittedDraft,...(scope?.runScope?[scope.runScope] as const:[] as const));
      if (generation !== worldRequestGeneration.current) return;
      if (saved.world_id !== requestedWorldId || saved.encounter_id !== submittedRecord.encounter_id
          || saved.revision !== submittedRecord.revision + 1 || !combatDraftEqual(saved.draft, submittedDraft)) {
        throw new Error('Save acknowledgement did not match the submitted encounter; recovery is retained.');
      }
      const laterDraft = draftRef.current ?? submittedDraft;
      const nextDraft = combatDraftEqual(laterDraft, submittedDraft) ? cloneDraft(saved.draft) : laterDraft;
      if (combatDraftEqual(nextDraft, saved.draft)) recoverySession.current.clear();
      else recoverySession.current.write(saved, nextDraft);
      pendingSave.current = null; recordRef.current = saved; draftRef.current = nextDraft;
      setRecord(saved); setDraft(nextDraft); setRecoveryMessage(null);
      if(tourEncounterAtDispatch&&!scope?.runScope)setPreparedAcknowledged({dispatchScope:tourDispatch,scope:tourEncounterAtDispatch,before:submittedRecord,saved});
      if(tourAtDispatch&&scope?.runScope)setTourAcknowledged({dispatchScope:tourDispatch,scope:tourAtDispatch,sceneId:scope.runScope.sceneId,before:submittedRecord,saved});
      setEncounters((current) => [saved, ...current.filter((item) => item.encounter_id !== saved.encounter_id)]);
    } catch (caught) {
      if (generation === worldRequestGeneration.current) setError(caught instanceof Error ? caught.message : String(caught));
    } finally {
      if (generation === worldRequestGeneration.current) setBusy(null);
    }
  }

  async function reloadEncounter() {
    if (!worldId || !visibleRecord) return;
    const requestedWorldId = worldId;
    const requestedEncounterId = visibleRecord.encounter_id;
    const generation = worldRequestGeneration.current;
    setBusy("reload");
    setError(null);
    try {
      const opened = await getAnyWorldCombatEncounter(requestedWorldId, requestedEncounterId,...(scope?.runScope?[scope.runScope] as const:[] as const));
      if (generation !== worldRequestGeneration.current) return;
      // Explicit reload discards only this owned local recovery after a verified read.
      if (opened.world_id !== requestedWorldId || opened.encounter_id !== requestedEncounterId) throw new Error('Combat response belongs to a different encounter.');
      if (isManualCombatRecord(opened)) throw new Error('Encounter version changed; reopen it before editing.');
      recoverySession.current.clear(); pendingSave.current = null; setAvailableRecovery(null);
      recordRef.current = opened; draftRef.current = cloneDraft(opened.draft);
      setRecord(opened); setDraft(draftRef.current); setRecoveryMessage(null);
    } catch (caught) {
      if (generation === worldRequestGeneration.current) setError(caught instanceof Error ? caught.message : String(caught));
    } finally {
      if (generation === worldRequestGeneration.current) setBusy(null);
    }
  }

  function removeEntity(entityId: string) {
    updateDraft((current) => {
      const index = current.entities.findIndex((entity) => entity.id === entityId);
      if (index < 0) return current;
      const successor = [...current.entities.slice(index + 1), ...current.entities.slice(0, index)]
        .find((entity) => !entity.defeated)?.id ?? null;
      return {
        ...current,
        entities: current.entities.filter((entity) => entity.id !== entityId)
          .map((entity, order) => ({ ...entity, order: order + 1 })),
        groups: current.groups.flatMap((group) => {
          const member_ids = group.member_ids.filter((id) => id !== entityId);
          return member_ids.length ? [{ ...group, member_ids }] : [];
        }),
        active_turn_entity_id: current.active_turn_entity_id === entityId ? successor : current.active_turn_entity_id,
        round_start_entity_id: current.round_start_entity_id === entityId ? null : current.round_start_entity_id,
      };
    });
  }

  function moveEntity(entityId: string, direction: 'earlier' | 'later') {
    updateDraft(current => {
      const participating = current.entities.filter(entity => !entity.defeated);
      const index = participating.findIndex(entity => entity.id === entityId);
      const neighbor = participating[index + (direction === 'earlier' ? -1 : 1)];
      if (index < 0 || !neighbor) return current;
      const entities = [...current.entities];
      const from = entities.findIndex(entity => entity.id === entityId);
      const to = entities.findIndex(entity => entity.id === neighbor.id);
      [entities[from], entities[to]] = [entities[to], entities[from]];
      return {...current, entities: entities.map((entity, order) => ({...entity, order: order + 1}))};
    });
  }

  function setActive(entityId: string) {
    updateDraft((current) => current.entities.some((entity) => entity.id === entityId && !entity.defeated)
      ? { ...current, active_turn_entity_id: entityId, round_start_entity_id: current.round_start_entity_id ?? entityId }
      : current);
  }

  function advance(direction: "next" | "previous") {
    updateDraft(current => stepCombatTurn(current, direction));
  }

  function sortInitiative() {
    updateDraft((current) => ({
      ...current,
      entities: [...current.entities]
        .sort((left, right) => {
          const leftInit = numericValue(left.init);
          const rightInit = numericValue(right.init);
          if (leftInit === null && rightInit !== null) return 1;
          if (rightInit === null && leftInit !== null) return -1;
          return (rightInit ?? 0) - (leftInit ?? 0) || left.order - right.order;
        })
        .map((entity, index) => ({ ...entity, order: index + 1 })),
    }));
  }

  const preparedBlocked=busy!==null||dirty||availableRecovery!==null||!!pendingSave.current||adoptionBlocked||manualBlocked;
  useTourNavigationGuard(worldId?{worldId,reason:()=>preparedBlocked?'Save or recover the encounter work before leaving these controls.':null}:null);
  const preparedListener=scope?.onPreparedState;
  const preparedRecord=visibleRecord??(manualRecord?.world_id===worldId?manualRecord:null);
  useEffect(()=>{preparedListener?.({record:preparedRecord,blocked:preparedBlocked,error,acknowledged:preparedAcknowledged});},[preparedListener,preparedRecord,preparedBlocked,error,preparedAcknowledged]);
  useEffect(()=>()=>preparedListener?.(null),[preparedListener]);

  const worldMessage = scope && selectedWorld.kind === "managed" && scope.worldId !== selectedWorld.worldId
    ? "This encounter belongs to another World. Reopen its scene in that World."
    : selectedWorld.kind === "loading"
    ? "Verifying selected World…"
    : selectedWorld.kind === "error"
      ? selectedWorld.message
      : selectedWorld.kind === "legacy"
        ? "Choose a verified World before creating or opening a Combat encounter."
        : null;

  const showSample = Boolean(worldId && sampleWorld === worldId);
  const showSetup = !scope && !worldListLoading && (showSample || (!visibleRecord && !manualRecord && !error));
  const dndSetup = <>
    <label>
      <span className="eyebrow">New encounter</span>
      <input aria-label="New encounter title" value={newTitle} disabled={operationsBlocked} onChange={(event) => setNewTitle(event.target.value)} />
    </label>
    <button type="button" disabled={operationsBlocked || !newTitle.trim() || dirty} onClick={() => void createEncounter()}>
      Create
    </button>
  </>;
  const customSetup = <ManualCombatProfileForm inline={showSetup} disabled={operationsBlocked||dirty||availableRecovery!==null} onCreate={async(title,profile)=>{
    if (!worldId) return;
    const generation=worldRequestGeneration.current;
    setBusy('create');
    try {
      const created=await createManualCombatEncounter(worldId,title,profile);
      if(generation!==worldRequestGeneration.current)return;
      setEncounters(items=>[created,...items]);setSelectedEncounterId(created.encounter_id);
      await adoptRecord(created,worldId,created.encounter_id,generation);
    } finally {if(generation===worldRequestGeneration.current)setBusy(null);}
  }}/>;

  const disclosureGroup = useId();
  const running = !showSample && visibleRecord !== null && visibleDraft !== null;
  const encounterSetup = running && (
    <details className="combat-roster-setup" name={disclosureGroup} open={adoptionBlocked ? true : undefined}><summary>Setup</summary>
      <div className="combat-toolbar-panel">
        <header className="combat-encounter-heading">
          <label>
            <span className="eyebrow">Encounter title</span>
            <input aria-label="Encounter title" value={visibleDraft.title} disabled={replacingDraft} onChange={(event) => updateDraft((current) => ({ ...current, title: event.target.value }))} />
          </label>
          <span className="module-muted">
            {visibleRecord.ruleset.config_id === DND5E_RULESET_ID
              ? "D&D 5e" : `${visibleRecord.ruleset.system_id} · ${visibleRecord.ruleset.edition_id}`}
            {" · config rev "}{visibleRecord.ruleset.revision}{" · pinned "}{visibleRecord.ruleset_digest.slice(0, 12)}
          </span>
        </header>

        <CombatMechanicsAdoption key={`adoption:${worldId}:${visibleRecord.encounter_id}`}
          scope={scope?.runScope} record={visibleRecord} disabled={busy!==null||dirty||availableRecovery!==null||!!pendingSave.current}
          onLockChange={setAdoptionBlocked} onReconciled={current=>{
            const base=recordRef.current,local=draftRef.current;
            if(!base||!local||current.world_id!==worldId||current.encounter_id!==base.encounter_id)
              throw new Error('Combat view changed; adoption recovery is retained.');
            if(!combatDraftEqual(base.draft,local)||pendingSave.current||availableRecovery)
              throw new Error('Resolve the local Combat draft before reconciling adoption.');
            recoverySession.current.clear();recordRef.current=current;draftRef.current=cloneDraft(current.draft);
            setRecord(current);setDraft(draftRef.current);setAvailableRecovery(null);setRecoveryMessage(null);
            setEncounters(items=>[current,...items.filter(item=>item.encounter_id!==current.encounter_id)]);
          }}/>
      </div>
    </details>
  );
  const assembly = running && worldId && (
    <CombatEncounterAssembly key={`${worldId}:${worldRequestGeneration.current}:${visibleRecord.encounter_id}`}
      worldId={worldId} variant={variant} disclosureGroup={disclosureGroup} disabled={operationsBlocked || availableRecovery !== null} remainingSlots={100 - visibleDraft.entities.length}
      onAdd={(entities, group) => {
        const proposed = {...visibleDraft,
          entities: [...visibleDraft.entities, ...entities].map((entity, index) => ({...entity, order: index + 1})),
          groups: group ? [...visibleDraft.groups, group] : visibleDraft.groups,
        };
        // Mirror the owning APP draft limit over the complete UTF-8 payload.
        if (new TextEncoder().encode(JSON.stringify(proposed)).byteLength > 700 * 1024) {
          return 'These copies exceed the encounter’s 700 KiB storage capacity. Reduce copies before adding; your draft is unchanged.';
        }
        if (!updateDraft(() => proposed)) return 'Combat draft could not be retained. Your prior draft and assembly inputs are unchanged.';
      }} />
  );

  return (
    <div ref={panelRef} className="module-panel combat-roster" data-module-id="combat_roster">
      <CombatTourObservation record={visibleRecord} runScope={scope?.runScope??null} acknowledged={tourAcknowledged} blocked={busy!==null||dirty||availableRecovery!==null||!!pendingSave.current||adoptionBlocked} error={error}/>
      <h2 className={running ? "sr-only" : "module-title"} data-guided-control={running ? undefined : "combat"} data-guided-control-group={running ? undefined : "true"} tabIndex={running ? undefined : -1}>Combat</h2>
      {worldMessage ? <p className="module-muted">{worldMessage}</p> : null}
      {error ? <p className="module-error" role="alert">Combat: {error}</p> : null}
      {worldId ? (
        <>
          <section ref={visibleRecord && visibleDraft ? turnRailRef : undefined} className={`combat-roster-save-rail${visibleRecord && visibleDraft ? " combat-roster-active-toolbar" : ""}`} aria-label="Encounter selection and save" data-guided-control={running ? "combat" : undefined} data-guided-control-group={running ? "true" : undefined} tabIndex={running ? -1 : undefined}>
            {encounterListHref && <a href={encounterListHref}>All encounters</a>}
            {scope ? <span className="combat-toolbar-scope" title={scope.label}>{running ? visibleDraft.title : scope.label}</span> : <>
            <label>
              {!running && <span className="eyebrow">Encounter</span>}
              <select
                aria-label="Encounter"
                value={selectedEncounterId}
                onChange={(event) => setSelectedEncounterId(event.target.value)}
                disabled={showSample || operationsBlocked || availableRecovery !== null}
              >
                <option value="">Choose an encounter…</option>
                {visibleEncounters.map((item) => (
                  <option key={item.encounter_id} value={item.encounter_id}>
                    {item.draft.title} · rev {item.revision}
                  </option>
                ))}
              </select>
            </label>
            <button type="button" disabled={showSample || operationsBlocked || manualRecord?.encounter_id===selectedEncounterId || !visibleEncounters.some((item) => item.encounter_id === selectedEncounterId) || dirty} onClick={() => void openEncounter()}>
              Open
            </button>
            {preparedRecord && !preparedBlocked && !showSample && <a href={combatEncounterHref({
              worldId: preparedRecord.world_id, encounterId: preparedRecord.encounter_id,
            })}>Encounter link</a>}
            {!showSetup && !running && dndSetup}
            </>}
            {running && <>
              <span className="combat-toolbar-system">
                {visibleRecord.ruleset.config_id === DND5E_RULESET_ID
                  ? "D&D 5e" : `${visibleRecord.ruleset.system_id} · ${visibleRecord.ruleset.edition_id}`}
              </span>
              <div className="combat-roster-turn-rail" role="group" aria-label="Combat turn controls">
                <span className="combat-toolbar-turn">
                  <span>Round</span> {visibleDraft.round} · <strong>{active?.name ?? "No active actor"}</strong>
                  {next && <> <span aria-label="Next">→</span> {next.name}</>}
                </span>
                <button type="button" onClick={() => advance("previous")} disabled={operationsBlocked || visibleDraft.entities.length === 0}>Back</button>
                <button className="combat-toolbar-next" type="button" onClick={() => advance("next")} disabled={operationsBlocked || visibleDraft.entities.length === 0}>Next turn</button>
              </div>
              {assembly}
            </>}
            {!manualRecord && <>
              <button type="button" disabled={operationsBlocked || (!dirty && !pendingSave.current)} onClick={() => void saveEncounter()}>
                {busy === "save" ? "Saving…" : "Save"}
              </button>
              {running ? <>
                {encounterSetup}
                <details className="combat-toolbar-more" name={disclosureGroup}>
                  <summary>More</summary>
                  <div className="combat-toolbar-panel">
                    <button type="button" onClick={sortInitiative} disabled={operationsBlocked || visibleDraft.entities.length < 2}>Sort initiative</button>
                    <button type="button" disabled={busy !== null || (!dirty && !pendingSave.current)} onClick={revertDraft}>Revert</button>
                    {!scope && <>{dndSetup}{customSetup}</>}
                    <p className="module-muted">Durable encounter · {visibleRecord.encounter_id} · revision {visibleRecord.revision}</p>
                  </div>
                </details>
              </> : <button type="button" disabled={busy !== null || (!dirty && !pendingSave.current)} onClick={revertDraft}>Revert</button>}
              {pendingSave.current ? <span className="module-muted" role="status">{busy === 'save' ? 'Saving exact request…' : 'Save outcome unconfirmed · exact request retained'}</span> : dirty ? <span className="module-muted" role="status">Unsaved changes</span> : visibleRecord ? <span className="sr-only" role="status">Saved · rev {visibleRecord.revision}</span> : null}
            </>}
          </section>
          {!scope && (showSetup ? (
            <section className="combat-start-workspace" aria-label="Empty Combat workspace">
              {showSample ? <CombatSamplePreview
                disabled={operationsBlocked}
                onClose={closeSample}
                onKeep={createEncounter}
              /> : <div className="combat-start-roster">
                <div className="combat-start-columns" aria-hidden="true">
                  <span>Participant</span><span>Stats</span><span>Conditions</span><span>Notes</span>
                </div>
                <div className="combat-start-card">
                  <h3>Set the scene</h3>
                  <p>{visibleEncounters.length ? "Start an encounter or open one above." : "No encounters yet. Set up your first encounter."}</p>
                  <label>System
                    <select value={setupSystem} onChange={event => setSetupSystem(event.target.value === "custom" ? "custom" : "dnd5e")} disabled={operationsBlocked}>
                      <option value="dnd5e">D&amp;D 5e</option>
                      <option value="custom">Custom system</option>
                    </select>
                  </label>
                  {setupSystem === "custom" ? customSetup : <div className="combat-start-fields">
                    {dndSetup}
                    <button type="button" disabled={operationsBlocked} onClick={() => setSampleWorld(worldId)}>Load sample</button>
                  </div>}
                </div>
              </div>}
              <aside className="combat-start-source">
                <h3>Statblock</h3>
                <p>Open a participant’s sheet here or in a pop-up.</p>
              </aside>
            </section>
          ) : !running && customSetup)}
          {manualRecord?.world_id===worldId&&<ManualCombatEditor key={JSON.stringify([manualRecord.world_id,manualRecord.encounter_id,scope?.runScope])} record={manualRecord} externallyDisabled={busy==='open'||busy==='create'||busy==='reload'} scope={scope?.runScope} onBlocked={setManualBlocked} onSaved={saved=>{setManualRecord(saved);setEncounters(items=>items.map(item=>item.encounter_id===saved.encounter_id?saved:item));}}/>}
          {availableRecovery && <section aria-label="Combat draft recovery">
            <p>Local Combat draft available from revision {availableRecovery.base.revision}. Current committed revision: {visibleRecord?.revision}. Recover explicitly; newer server state is never overwritten automatically.</p>
            <button type="button" disabled={busy !== null} onClick={recoverDraft}>Recover local Combat draft</button>
            <button type="button" disabled={busy !== null} onClick={discardRecovery}>Discard local Combat draft</button>
          </section>}
          {recoveryMessage && <p role="status">{recoveryMessage}</p>}
          {worldListLoading ? <p className="module-muted">Loading World encounters…</p> : null}
          {!showSetup && !worldListLoading && !visibleRecord && !manualRecord && !error ? (
            <p className="module-muted">Choose an encounter and open it, or create a new one.</p>
          ) : null}
          {!showSample && visibleRecord && visibleDraft ? (
            <>
              {visibleDraft.entities.length === 0 ? (
                <p className="module-muted">Add combatants to assemble this encounter.</p>
              ) : (
                <CombatRosterWorkspace key={JSON.stringify([worldId, visibleRecord.encounter_id, scope?.runScope?.runId, scope?.runScope?.sceneId])}
                  draft={visibleDraft} disabled={replacingDraft}
                  corpusScope={scope?.runScope ? undefined : {worldId, encounterId: visibleRecord.encounter_id}}
                  onToggleGroup={key => updateDraft(current => ({...current,
                    groups: current.groups.map(group => group.group_key === key ? {...group, collapsed: !group.collapsed} : group),
                  }))}
                  renderRow={(entity, hidden, projection) => (
                        <RosterRow
                          key={entity.id}
                          entity={entity}
                          active={entity.id === visibleDraft.active_turn_entity_id}
                          next={entity.id === next?.id}
                          hidden={hidden}
                          projection={projection}
                          onMove={direction => moveEntity(entity.id, direction)}
                          canMoveEarlier={livingOrder.indexOf(entity.id) > 0}
                          canMoveLater={!entity.defeated && livingOrder.indexOf(entity.id) < livingOrder.length - 1}
                          disabled={replacingDraft}
                          onChange={(updated) => updateEntity(entity.id, updated)}
                          onSetActive={() => setActive(entity.id)}
                          onRemove={() => removeEntity(entity.id)}
                        />
                      )}/>
              )}
              {error?.includes("changed since it was opened") ? (
                <button type="button" disabled={operationsBlocked} onClick={() => void reloadEncounter()}>Reload latest revision</button>
              ) : null}
            </>
          ) : null}
        </>
      ) : null}
    </div>
  );
}
