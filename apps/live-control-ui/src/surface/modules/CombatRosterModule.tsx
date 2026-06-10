import { useEffect, useMemo, useState } from "react";

import {
  advanceCombatTurn,
  applyCombatHpDelta,
  getCurrentCombat,
  patchCombatEntity,
  setCombatActiveTurn,
  sortCombatInitiative,
} from "../../api/liveApi";
import type { CombatEncounterState, CombatEntity, CombatTeam } from "../../api/types";

function valueText(value: unknown): string {
  if (value === null || value === undefined || value === "") return "—";
  return String(value);
}

function asInput(value: unknown): string {
  if (value === null || value === undefined) return "";
  return String(value);
}

function nextActor(encounter: CombatEncounterState | null): CombatEntity | null {
  if (!encounter || encounter.entities.length === 0) return null;
  const activeIndex = encounter.entities.findIndex(
    (entity) => entity.id === encounter.active_turn_entity_id,
  );
  if (activeIndex < 0) return encounter.entities[0] ?? null;
  return encounter.entities[(activeIndex + 1) % encounter.entities.length] ?? null;
}

function activeActor(encounter: CombatEncounterState | null): CombatEntity | null {
  if (!encounter) return null;
  return (
    encounter.entities.find((entity) => entity.id === encounter.active_turn_entity_id) ?? null
  );
}

function RosterRow({
  entity,
  active,
  onRefresh,
}: {
  entity: CombatEntity;
  active: boolean;
  onRefresh: (encounter: CombatEncounterState) => void;
}) {
  const [damage, setDamage] = useState("1");
  const [heal, setHeal] = useState("1");
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function mutate(label: string, run: () => Promise<{ encounter: CombatEncounterState }>) {
    setBusy(label);
    setError(null);
    try {
      const response = await run();
      onRefresh(response.encounter);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : String(caught));
    } finally {
      setBusy(null);
    }
  }

  function numberOrNull(value: string): number | null {
    if (value.trim() === "") return null;
    const parsed = Number.parseInt(value, 10);
    return Number.isFinite(parsed) ? parsed : null;
  }

  const damageAmount = Number.parseInt(damage, 10);
  const healAmount = Number.parseInt(heal, 10);
  const canApplyDamage = busy === null && Number.isFinite(damageAmount) && damageAmount > 0;
  const canApplyHeal = busy === null && Number.isFinite(healAmount) && healAmount > 0;

  return (
    <tr className={active ? "combat-roster-active-row" : undefined}>
      <td>
        <button
          type="button"
          onClick={() => mutate("active", () => setCombatActiveTurn({ entity_id: entity.id }))}
          disabled={busy !== null}
        >
          {active ? "▶" : "Set"}
        </button>
      </td>
      <td>
        <strong>{entity.name}</strong>
        <div className="module-muted">
          {entity.statblock_title ?? entity.statblock_artifact_id ?? entity.source}
        </div>
      </td>
      <td>
        <select
          aria-label={`Team for ${entity.name}`}
          value={entity.team}
          onChange={(event) =>
            mutate("team", () =>
              patchCombatEntity(entity.id, { team: event.target.value as CombatTeam }),
            )
          }
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
          key={`${entity.id}-init-${entity.init ?? ""}`}
          defaultValue={asInput(entity.init)}
          onBlur={(event) =>
            mutate("init", () =>
              patchCombatEntity(entity.id, { init: numberOrNull(event.target.value) }),
            )
          }
        />
      </td>
      <td>{valueText(entity.ac)}</td>
      <td>
        <input
          aria-label={`HP for ${entity.name}`}
          className="combat-roster-short-input"
          key={`${entity.id}-hp-${entity.hp ?? ""}`}
          defaultValue={asInput(entity.hp)}
          onBlur={(event) =>
            mutate("hp", () =>
              patchCombatEntity(entity.id, {
                hp: numberOrNull(event.target.value) ?? event.target.value,
              }),
            )
          }
        />{" "}
        / {valueText(entity.max_hp)}
      </td>
      <td>
        <input
          aria-label={`Temp HP for ${entity.name}`}
          className="combat-roster-short-input"
          key={`${entity.id}-temp-${entity.temp_hp ?? ""}`}
          defaultValue={asInput(entity.temp_hp)}
          onBlur={(event) =>
            mutate("temp", () =>
              patchCombatEntity(entity.id, { temp_hp: numberOrNull(event.target.value) ?? 0 }),
            )
          }
        />
      </td>
      <td>
        <div className="combat-roster-delta-controls">
          <input
            aria-label={`Damage for ${entity.name}`}
            type="number"
            min="0"
            value={damage}
            onChange={(event) => setDamage(event.target.value)}
          />
          <button
            type="button"
            disabled={!canApplyDamage}
            onClick={() =>
              mutate("damage", () =>
                applyCombatHpDelta(entity.id, {
                  action: "damage",
                  amount: damageAmount,
                }),
              )
            }
          >
            Damage
          </button>
          <input
            aria-label={`Healing for ${entity.name}`}
            type="number"
            min="0"
            value={heal}
            onChange={(event) => setHeal(event.target.value)}
          />
          <button
            type="button"
            disabled={!canApplyHeal}
            onClick={() =>
              mutate("heal", () =>
                applyCombatHpDelta(entity.id, {
                  action: "heal",
                  amount: healAmount,
                }),
              )
            }
          >
            Heal
          </button>
        </div>
      </td>
      <td>
        <input
          aria-label={`Conditions for ${entity.name}`}
          key={`${entity.id}-conditions-${entity.conditions.join(",")}`}
          defaultValue={entity.conditions.join(", ")}
          onBlur={(event) =>
            mutate("conditions", () =>
              patchCombatEntity(entity.id, {
                conditions: event.target.value
                  .split(",")
                  .map((item) => item.trim())
                  .filter(Boolean),
              }),
            )
          }
        />
      </td>
      <td>
        <textarea
          aria-label={`Notes for ${entity.name}`}
          key={`${entity.id}-notes-${entity.notes}`}
          defaultValue={entity.notes}
          onBlur={(event) =>
            mutate("notes", () => patchCombatEntity(entity.id, { notes: event.target.value }))
          }
        />
      </td>
      <td>
        <label>
          <input
            type="checkbox"
            checked={entity.defeated}
            onChange={(event) =>
              mutate("defeated", () =>
                patchCombatEntity(entity.id, { defeated: event.target.checked }),
              )
            }
          />{" "}
          Defeated
        </label>
        {error ? <div className="module-error">{error}</div> : null}
      </td>
    </tr>
  );
}

export function CombatRosterModule() {
  const [encounter, setEncounter] = useState<CombatEncounterState | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let alive = true;
    getCurrentCombat()
      .then((response) => {
        if (alive) setEncounter(response);
      })
      .catch((caught) => {
        if (alive) setError(caught instanceof Error ? caught.message : String(caught));
      })
      .finally(() => {
        if (alive) setLoading(false);
      });
    return () => {
      alive = false;
    };
  }, []);

  const active = useMemo(() => activeActor(encounter), [encounter]);
  const next = useMemo(() => nextActor(encounter), [encounter]);

  async function mutate(label: string, run: () => Promise<{ encounter: CombatEncounterState }>) {
    setBusy(label);
    setError(null);
    try {
      const response = await run();
      setEncounter(response.encounter);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : String(caught));
    } finally {
      setBusy(null);
    }
  }

  return (
    <div className="module-panel combat-roster" data-module-id="combat_roster">
      <h2 className="module-title">Combat Roster</h2>
      {loading ? <p className="module-muted">Loading current combat…</p> : null}
      {error ? <p className="module-error">Combat roster error: {error}</p> : null}
      {encounter ? (
        <>
          <section className="combat-roster-turn-rail" aria-label="Combat turn controls">
            <div>
              <span className="eyebrow">Round</span>
              <strong>{encounter.round}</strong>
            </div>
            <div>
              <span className="eyebrow">Active</span>
              <strong>{active?.name ?? "No active actor"}</strong>
            </div>
            <div>
              <span className="eyebrow">Next</span>
              <strong>{next?.name ?? "—"}</strong>
            </div>
            <button
              type="button"
              disabled={busy !== null}
              onClick={() => mutate("sort", () => sortCombatInitiative())}
            >
              Sort initiative
            </button>
            <button
              type="button"
              disabled={busy !== null}
              onClick={() => mutate("previous", () => advanceCombatTurn({ direction: "previous" }))}
            >
              Previous turn
            </button>
            <button
              type="button"
              disabled={busy !== null}
              onClick={() => mutate("next", () => advanceCombatTurn({ direction: "next" }))}
            >
              Next turn
            </button>
          </section>
          {encounter.entities.length === 0 ? (
            <p className="module-muted">
              No combatants yet. Add generated statblocks from Statblock View.
            </p>
          ) : (
            <div className="combat-roster-table-wrap">
              <table className="combat-roster-table">
                <thead>
                  <tr>
                    <th>Turn</th>
                    <th>Name</th>
                    <th>Team</th>
                    <th>Init</th>
                    <th>AC</th>
                    <th>HP</th>
                    <th>Temp</th>
                    <th>Delta</th>
                    <th>Conditions</th>
                    <th>Notes</th>
                    <th>Status</th>
                  </tr>
                </thead>
                <tbody>
                  {encounter.entities.map((entity) => (
                    <RosterRow
                      key={entity.id}
                      entity={entity}
                      active={entity.id === encounter.active_turn_entity_id}
                      onRefresh={setEncounter}
                    />
                  ))}
                </tbody>
              </table>
            </div>
          )}
          <p className="module-muted">
            Persists only to combat/current_combat.json · Updated {encounter.updated_at}
          </p>
        </>
      ) : null}
    </div>
  );
}
