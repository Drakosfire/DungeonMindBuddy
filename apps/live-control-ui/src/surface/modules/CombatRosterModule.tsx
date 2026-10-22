import { useEffect, useLayoutEffect, useMemo, useRef, useState } from "react";

import {
  createWorldCombatEncounter,
  getWorldCombatEncounter,
  listWorldCombatEncounters,
  saveWorldCombatEncounter,
} from "../../combat/combatApi";
import type { CombatEncounterDraft, CombatEncounterRecord, CombatEntity } from "../../combat/combatTypes";
import { CombatMechanicsInspection } from "../../combat/CombatMechanicsInspection";
import { CombatEncounterAssembly } from "../../combat/CombatEncounterAssembly";
import { useSelectedWorld } from "../../selectedWorld/SelectedWorldContext";

function valueText(value: unknown): string {
  if (value === null || value === undefined || value === "") return "—";
  return String(value);
}

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
  disabled,
  onChange,
  onSetActive,
}: {
  entity: CombatEntity;
  active: boolean;
  disabled: boolean;
  onChange: (entity: CombatEntity) => void;
  onSetActive: () => void;
}) {
  const [damage, setDamage] = useState("1");
  const [heal, setHeal] = useState("1");
  const [error, setError] = useState<string | null>(null);

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
    const maxHp = numericValue(entity.max_hp);
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
    update({ hp: maxHp === null ? hp + amount : Math.min(maxHp, hp + amount) });
  }

  const damageAmount = Number.parseInt(damage, 10);
  const healAmount = Number.parseInt(heal, 10);

  return (
    <tr className={active ? "combat-roster-active-row" : undefined}>
      <td>
        <button type="button" onClick={onSetActive} disabled={disabled || entity.defeated}>
          {active ? "▶" : "Set"}
        </button>
      </td>
      <td>
        <strong>{entity.name}</strong>
        <div className="module-muted">
          {entity.world_identity ? `World: ${entity.world_identity.label} · Manual stats` : entity.statblock_title ?? entity.statblock_artifact_id ?? entity.source}
        </div>
        {entity.mechanics_snapshot && <CombatMechanicsInspection snapshot={entity.mechanics_snapshot} />}
      </td>
      <td>
        <select
          aria-label={`Team for ${entity.name}`}
          value={entity.team}
          disabled={disabled}
          onChange={(event) => update({ team: event.target.value as CombatEntity["team"] })}
        >
          <option value="pc">PC</option>
          <option value="ally">Ally</option>
          <option value="enemy">Enemy</option>
          <option value="neutral">Neutral</option>
        </select>
      </td>
      <td>
        <input
          aria-label={`Initiative for ${entity.name}`}
          className="combat-roster-short-input"
          value={asInput(entity.init)}
          disabled={disabled}
          onChange={(event) => update({ init: numberOrNull(event.target.value) })}
        />
      </td>
      <td>{valueText(entity.ac)}</td>
      <td>
        <input
          aria-label={`HP for ${entity.name}`}
          className="combat-roster-short-input"
          value={asInput(entity.hp)}
          disabled={disabled}
          onChange={(event) => {
            const parsed = numberOrNull(event.target.value);
            update({ hp: parsed === null && event.target.value.trim() !== "" ? event.target.value : parsed });
          }}
        />{" "}/ {valueText(entity.max_hp)}
      </td>
      <td>
        <input
          aria-label={`Temp HP for ${entity.name}`}
          className="combat-roster-short-input"
          value={asInput(entity.temp_hp)}
          disabled={disabled}
          onChange={(event) => update({ temp_hp: Math.max(0, numberOrNull(event.target.value) ?? 0) })}
        />
      </td>
      <td>
        <div className="combat-roster-delta-controls">
          <input
            aria-label={`Damage for ${entity.name}`}
            type="number"
            min="0"
            value={damage}
            disabled={disabled}
            onChange={(event) => setDamage(event.target.value)}
          />
          <button
            type="button"
            disabled={disabled || !Number.isFinite(damageAmount) || damageAmount <= 0}
            onClick={() => applyDelta("damage", damageAmount)}
          >
            Damage
          </button>
          <input
            aria-label={`Healing for ${entity.name}`}
            type="number"
            min="0"
            value={heal}
            disabled={disabled}
            onChange={(event) => setHeal(event.target.value)}
          />
          <button
            type="button"
            disabled={disabled || !Number.isFinite(healAmount) || healAmount <= 0}
            onClick={() => applyDelta("heal", healAmount)}
          >
            Heal
          </button>
        </div>
      </td>
      <td>
        <input
          aria-label={`Conditions for ${entity.name}`}
          value={entity.conditions.join(", ")}
          disabled={disabled}
          onChange={(event) => update({
            conditions: event.target.value.split(",").map((item) => item.trim()).filter(Boolean),
          })}
        />
      </td>
      <td>
        <textarea
          aria-label={`Notes for ${entity.name}`}
          value={entity.notes}
          disabled={disabled}
          onChange={(event) => update({ notes: event.target.value })}
        />
      </td>
      <td>
        <label>
          <input
            type="checkbox"
            checked={entity.defeated}
            disabled={disabled}
            onChange={(event) => update({ defeated: event.target.checked })}
          />{" "}
          Defeated
        </label>
        {error ? <div className="module-error">{error}</div> : null}
      </td>
    </tr>
  );
}

function cloneDraft(draft: CombatEncounterDraft): CombatEncounterDraft {
  return JSON.parse(JSON.stringify(draft)) as CombatEncounterDraft;
}

export function CombatRosterModule() {
  const selectedWorld = useSelectedWorld();
  const worldId = selectedWorld.kind === "managed" ? selectedWorld.worldId : null;
  const worldRequestGeneration = useRef(0);
  const [encounters, setEncounters] = useState<CombatEncounterRecord[]>([]);
  const [loadedWorldId, setLoadedWorldId] = useState<string | null>(null);
  const [selectedEncounterId, setSelectedEncounterId] = useState("");
  const [record, setRecord] = useState<CombatEncounterRecord | null>(null);
  const [draft, setDraft] = useState<CombatEncounterDraft | null>(null);
  const [newTitle, setNewTitle] = useState("New encounter");
  const [loading, setLoading] = useState(false);
  const [busy, setBusy] = useState<string | null>(null);
  const replacingDraft = busy === "create" || busy === "open" || busy === "reload";
  const [error, setError] = useState<string | null>(null);

  useLayoutEffect(() => {
    worldRequestGeneration.current += 1;
    return () => {
      worldRequestGeneration.current += 1;
    };
  }, [worldId]);

  useEffect(() => {
    let alive = true;
    const generation = worldRequestGeneration.current;
    setRecord(null);
    setDraft(null);
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
    void listWorldCombatEncounters(worldId)
      .then((items) => {
        if (alive && generation === worldRequestGeneration.current) {
          setEncounters(items);
          setLoadedWorldId(worldId);
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
  }, [worldId]);

  const visibleRecord = record?.world_id === worldId ? record : null;
  const visibleDraft = visibleRecord ? draft : null;
  const visibleEncounters = encounters.filter((item) => item.world_id === worldId);
  const worldListLoading = worldId !== null && (loading || loadedWorldId !== worldId);
  const dirty = Boolean(visibleRecord && visibleDraft && JSON.stringify(visibleRecord.draft) !== JSON.stringify(visibleDraft));
  const active = useMemo(() => activeActor(visibleDraft), [visibleDraft]);
  const next = useMemo(() => nextActor(visibleDraft), [visibleDraft]);

  function updateDraft(update: (current: CombatEncounterDraft) => CombatEncounterDraft) {
    setDraft((current) => current ? update(current) : current);
  }

  function updateEntity(entityId: string, replacement: CombatEntity) {
    updateDraft((current) => ({
      ...current,
      entities: current.entities.map((entity) => entity.id === entityId ? replacement : entity),
    }));
  }

  async function createEncounter() {
    if (!worldId) return;
    const requestedWorldId = worldId;
    const generation = worldRequestGeneration.current;
    setBusy("create");
    setError(null);
    try {
      const created = await createWorldCombatEncounter(requestedWorldId, { title: newTitle.trim() || "New encounter" });
      if (generation !== worldRequestGeneration.current) return;
      setEncounters((current) => [created, ...current.filter((item) => item.encounter_id !== created.encounter_id)]);
      setSelectedEncounterId(created.encounter_id);
      setRecord(created);
      setDraft(cloneDraft(created.draft));
    } catch (caught) {
      if (generation === worldRequestGeneration.current) setError(caught instanceof Error ? caught.message : String(caught));
    } finally {
      if (generation === worldRequestGeneration.current) setBusy(null);
    }
  }

  async function openEncounter() {
    if (!worldId || !selectedEncounterId || dirty) return;
    const requestedWorldId = worldId;
    const requestedEncounterId = selectedEncounterId;
    const generation = worldRequestGeneration.current;
    setBusy("open");
    setError(null);
    try {
      const opened = await getWorldCombatEncounter(requestedWorldId, requestedEncounterId);
      if (generation !== worldRequestGeneration.current) return;
      setRecord(opened);
      setDraft(cloneDraft(opened.draft));
    } catch (caught) {
      if (generation === worldRequestGeneration.current) setError(caught instanceof Error ? caught.message : String(caught));
    } finally {
      if (generation === worldRequestGeneration.current) setBusy(null);
    }
  }

  async function saveEncounter() {
    if (!worldId || !visibleRecord || !visibleDraft || !dirty) return;
    const requestedWorldId = worldId;
    const submittedRecord = visibleRecord;
    const submittedDraft = cloneDraft(visibleDraft);
    const generation = worldRequestGeneration.current;
    setBusy("save");
    setError(null);
    try {
      const saved = await saveWorldCombatEncounter(requestedWorldId, submittedRecord.encounter_id, submittedRecord.revision, submittedDraft);
      if (generation !== worldRequestGeneration.current) return;
      setRecord(saved);
      setDraft((current) => current && JSON.stringify(current) !== JSON.stringify(submittedDraft)
        ? current
        : cloneDraft(saved.draft));
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
      const opened = await getWorldCombatEncounter(requestedWorldId, requestedEncounterId);
      if (generation !== worldRequestGeneration.current) return;
      setRecord(opened);
      setDraft(cloneDraft(opened.draft));
    } catch (caught) {
      if (generation === worldRequestGeneration.current) setError(caught instanceof Error ? caught.message : String(caught));
    } finally {
      if (generation === worldRequestGeneration.current) setBusy(null);
    }
  }

  function setActive(entityId: string) {
    updateDraft((current) => current.entities.some((entity) => entity.id === entityId && !entity.defeated)
      ? { ...current, active_turn_entity_id: entityId, round_start_entity_id: current.round_start_entity_id ?? entityId }
      : current);
  }

  function advance(direction: "next" | "previous") {
    updateDraft((current) => {
      const living = current.entities.filter((entity) => !entity.defeated);
      if (living.length === 0) return current;
      const activeIndex = living.findIndex((entity) => entity.id === current.active_turn_entity_id);
      if (activeIndex < 0) {
        return {
          ...current,
          active_turn_entity_id: living[0]?.id ?? null,
          round_start_entity_id: current.round_start_entity_id ?? living[0]?.id ?? null,
        };
      }
      const from = activeIndex;
      const nextIndex = (from + (direction === "next" ? 1 : living.length - 1)) % living.length;
      const wrapped = direction === "next" ? nextIndex <= from : nextIndex >= from;
      return {
        ...current,
        active_turn_entity_id: living[nextIndex]?.id ?? null,
        round: Math.max(1, current.round + (wrapped ? (direction === "next" ? 1 : -1) : 0)),
        round_start_entity_id: current.round_start_entity_id ?? living[0]?.id ?? null,
      };
    });
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

  const worldMessage = selectedWorld.kind === "loading"
    ? "Verifying selected World…"
    : selectedWorld.kind === "error"
      ? selectedWorld.message
      : selectedWorld.kind === "legacy"
        ? "Choose a verified World before creating or opening a Combat encounter."
        : null;

  return (
    <div className="module-panel combat-roster" data-module-id="combat_roster">
      <h2 className="module-title">Combat</h2>
      {worldMessage ? <p className="module-muted">{worldMessage}</p> : null}
      {error ? <p className="module-error" role="alert">Combat: {error}</p> : null}
      {worldId ? (
        <>
          <section className="combat-roster-save-rail" aria-label="Encounter selection and save">
            <label>
              <span className="eyebrow">Encounter</span>
              <select
                aria-label="Encounter"
                value={selectedEncounterId}
                onChange={(event) => setSelectedEncounterId(event.target.value)}
                disabled={busy !== null}
              >
                <option value="">Choose an encounter…</option>
                {visibleEncounters.map((item) => (
                  <option key={item.encounter_id} value={item.encounter_id}>
                    {item.draft.title} · rev {item.revision}
                  </option>
                ))}
              </select>
            </label>
            <button type="button" disabled={busy !== null || !visibleEncounters.some((item) => item.encounter_id === selectedEncounterId) || dirty} onClick={() => void openEncounter()}>
              Open
            </button>
            <label>
              <span className="eyebrow">New encounter</span>
              <input aria-label="New encounter title" value={newTitle} disabled={busy !== null} onChange={(event) => setNewTitle(event.target.value)} />
            </label>
            <button type="button" disabled={busy !== null || !newTitle.trim() || dirty} onClick={() => void createEncounter()}>
              Create
            </button>
            <button type="button" disabled={busy !== null || !dirty} onClick={() => void saveEncounter()}>
              {busy === "save" ? "Saving…" : "Save"}
            </button>
            <button type="button" disabled={busy !== null || !dirty} onClick={() => visibleRecord && setDraft(cloneDraft(visibleRecord.draft))}>
              Revert
            </button>
            {dirty ? <span className="module-muted">Unsaved changes</span> : visibleRecord ? <span className="module-muted">Saved · rev {visibleRecord.revision}</span> : null}
          </section>
          {worldListLoading ? <p className="module-muted">Loading World encounters…</p> : null}
          {!worldListLoading && visibleEncounters.length === 0 && !visibleRecord ? (
            <p className="module-muted">No encounters yet. Create a named encounter to begin; it won’t replace another fight.</p>
          ) : null}
          {!visibleRecord ? (
            <p className="module-muted">Choose an encounter and open it, or create a new one.</p>
          ) : null}
          {visibleRecord && visibleDraft ? (
            <>
              <section className="combat-roster-turn-rail" aria-label="Combat turn controls">
                <div><span className="eyebrow">Round</span><strong>{visibleDraft.round}</strong></div>
                <div><span className="eyebrow">Active</span><strong>{active?.name ?? "No active actor"}</strong></div>
                <div><span className="eyebrow">Next</span><strong>{next?.name ?? "—"}</strong></div>
                <button type="button" onClick={sortInitiative} disabled={busy !== null || visibleDraft.entities.length < 2}>Sort initiative</button>
                <button type="button" onClick={() => advance("previous")} disabled={busy !== null || visibleDraft.entities.length === 0}>Previous turn</button>
                <button type="button" onClick={() => advance("next")} disabled={busy !== null || visibleDraft.entities.length === 0}>Next turn</button>
              </section>
              <header className="combat-encounter-heading">
                <label>
                  <span className="eyebrow">Encounter title</span>
                  <input aria-label="Encounter title" value={visibleDraft.title} disabled={replacingDraft} onChange={(event) => updateDraft((current) => ({ ...current, title: event.target.value }))} />
                </label>
                <span className="module-muted">{visibleRecord.ruleset.system_id} · {visibleRecord.ruleset.edition_id} · config rev {visibleRecord.ruleset.revision} · pinned {visibleRecord.ruleset_digest.slice(0, 12)}</span>
              </header>
              <CombatEncounterAssembly key={`${worldId}:${worldRequestGeneration.current}:${visibleRecord.encounter_id}`}
                worldId={worldId} disabled={busy !== null} remainingSlots={100 - visibleDraft.entities.length}
                onAdd={(entities, group) => updateDraft(current => ({...current,
                  entities: [...current.entities, ...entities].map((entity, index) => ({...entity, order: index + 1})),
                  groups: group ? [...current.groups, group] : current.groups,
                }))} />
              {visibleDraft.entities.length === 0 ? (
                <p className="module-muted">Add combatants to assemble this encounter.</p>
              ) : (
                <div className="combat-roster-table-wrap">
                  <table className="combat-roster-table">
                    <thead><tr><th>Turn</th><th>Name</th><th>Team</th><th>Init</th><th>AC</th><th>HP</th><th>Temp</th><th>Delta</th><th>Conditions</th><th>Notes</th><th>Status</th></tr></thead>
                    <tbody>
                      {visibleDraft.entities.map((entity) => (
                        <RosterRow
                          key={entity.id}
                          entity={entity}
                          active={entity.id === visibleDraft.active_turn_entity_id}
                          disabled={replacingDraft}
                          onChange={(updated) => updateEntity(entity.id, updated)}
                          onSetActive={() => setActive(entity.id)}
                        />
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
              {error?.includes("changed since it was opened") ? (
                <button type="button" disabled={busy !== null} onClick={() => void reloadEncounter()}>Reload latest revision</button>
              ) : null}
              <p className="module-muted">Durable encounter · {visibleRecord.encounter_id} · revision {visibleRecord.revision}</p>
            </>
          ) : null}
        </>
      ) : null}
    </div>
  );
}
