import { readFileSync } from "node:fs";
import { resolve } from "node:path";

import { beforeAll, beforeEach, describe, expect, it } from "vitest";

type CombatEntity = {
  id: string;
  name?: string;
  team?: string;
  hp?: unknown;
  maxHp?: unknown;
  ac?: unknown;
  statblockPath?: string;
};

type CombatState = { entities: CombatEntity[] };

type CombatPrepApi = {
  freshCombatState: () => CombatState;
  normalizeCombatState: (raw: unknown) => CombatState;
  combatEntityDefeated: (entity: {
    hp?: unknown;
    defeated?: boolean;
  }) => boolean;
  mergePersistedCombatFields: (current: CombatState, legacy: CombatState) => CombatState;
  loadPersistedCombatState: () => { raw: CombatState | null; source: string };
  saveCombatState: (state: CombatState) => void;
  addCombatantFromPool: (state: CombatState, templateId: string) => CombatEntity | null;
};

function prepApi(): CombatPrepApi {
  return (window as typeof window & { MirewardPrep: CombatPrepApi }).MirewardPrep;
}

describe("Combat Tracker roster replace", () => {
  const STORAGE_PREFIX = "mireward-prep.";
  const CURRENT_KEY = `${STORAGE_PREFIX}combat.board.v2`;
  const LEGACY_KEY = `${STORAGE_PREFIX}combat.mirewardWallBreach`;

  beforeAll(() => {
    const prepPath = resolve(
      process.cwd(),
      "../../evals/c2_live_prep/mireward-prep/assets/prep.js",
    );
    window.eval(readFileSync(prepPath, "utf8"));
  });

  beforeEach(() => {
    localStorage.removeItem(CURRENT_KEY);
    localStorage.removeItem(LEGACY_KEY);
    localStorage.removeItem(`${STORAGE_PREFIX}combat.northReachGate`);
  });

  it("starts Reset / fresh combat with no entities", () => {
    expect(prepApi().freshCombatState().entities).toEqual([]);
    expect(prepApi().normalizeCombatState(null).entities).toEqual([]);
  });

  it("does not graft catalog defaults onto an imported roster", () => {
    const imported = prepApi().normalizeCombatState({
      entities: [{ id: "baergrom", name: "Baergrom", team: "pc", order: 0 }],
    });
    expect(imported.entities.map((entity) => entity.id)).toEqual(["baergrom"]);
    expect(
      imported.entities.some((entity) =>
        /meatwing|tripod|sewer-meat|corrupted-meat/i.test(entity.id),
      ),
    ).toBe(false);
  });

  it("keeps an empty imported board empty instead of restoring the old catalog", () => {
    const cleared = prepApi().normalizeCombatState({ entities: [] });
    expect(cleared.entities).toEqual([]);
  });

  it("does not treat blank HP as dead", () => {
    expect(prepApi().combatEntityDefeated({ hp: "", defeated: false })).toBe(false);
    expect(prepApi().combatEntityDefeated({ hp: "   ", defeated: false })).toBe(false);
    expect(prepApi().combatEntityDefeated({ hp: "35", defeated: false })).toBe(false);
    expect(prepApi().combatEntityDefeated({ hp: 8, defeated: false })).toBe(false);
  });

  it("treats explicit 0 HP or the defeated flag as dead", () => {
    expect(prepApi().combatEntityDefeated({ hp: "0", defeated: false })).toBe(true);
    expect(prepApi().combatEntityDefeated({ hp: 0, defeated: false })).toBe(true);
    expect(prepApi().combatEntityDefeated({ hp: "45", defeated: true })).toBe(true);
  });

  it("keeps tracked HP on the current board when saving", () => {
    prepApi().saveCombatState({
      entities: [{ id: "baergrom", name: "Baergrom", team: "pc", hp: "41", maxHp: "44" }],
    });
    const stored = JSON.parse(localStorage.getItem(CURRENT_KEY) ?? "null");
    expect(stored.entities[0].hp).toBe("41");
    expect(stored.entities[0].maxHp).toBe("44");
  });

  it("restores blank current HP from the previous live board", () => {
    const restored = prepApi().mergePersistedCombatFields(
      { entities: [{ id: "baergrom", name: "Baergrom", hp: "", maxHp: "" }] },
      { entities: [{ id: "baergrom", name: "Baergrom", hp: "41", maxHp: "44" }] },
    );
    expect(restored.entities[0]?.hp).toBe("41");
    expect(restored.entities[0]?.maxHp).toBe("44");
  });

  it("does not overwrite HP that is already tracked on the current board", () => {
    const kept = prepApi().mergePersistedCombatFields(
      { entities: [{ id: "baergrom", hp: "10" }] },
      { entities: [{ id: "baergrom", hp: "41" }] },
    );
    expect(kept.entities[0]?.hp).toBe("10");
  });

  it("migrates the stranded live board when the current key is empty", () => {
    localStorage.setItem(
      LEGACY_KEY,
      JSON.stringify({
        entities: [{ id: "caelynn", name: "Caelynn", hp: "35", maxHp: "37" }],
      }),
    );
    const loaded = prepApi().loadPersistedCombatState();
    expect(loaded.source).toBe("migrated");
    expect(loaded.raw?.entities[0]?.hp).toBe("35");
  });

  it("fills HP from the stranded live board onto the current snapshot", () => {
    localStorage.setItem(
      CURRENT_KEY,
      JSON.stringify({
        entities: [{ id: "caelynn", name: "Caelynn", hp: "", maxHp: "" }],
      }),
    );
    localStorage.setItem(
      LEGACY_KEY,
      JSON.stringify({
        entities: [{ id: "caelynn", name: "Caelynn", hp: "35", maxHp: "37" }],
      }),
    );
    const loaded = prepApi().loadPersistedCombatState();
    expect(loaded.source).toBe("local");
    expect(loaded.raw?.entities[0]?.hp).toBe("35");
    expect(loaded.raw?.entities[0]?.maxHp).toBe("37");
  });

  it("relabels Mireward Latchlings as Under-Hymn Brood without wiping HP", () => {
    const normalized = prepApi().normalizeCombatState({
      entities: [
        {
          id: "mireward-latchling-b",
          name: "Mireward Latchling B",
          team: "enemy",
          hp: "32",
          maxHp: "52",
          statblockPath: "mireward_latchling_group",
        },
      ],
    });
    expect(normalized.entities[0]?.name).toBe("Under-Hymn Brood B");
    expect(normalized.entities[0]?.hp).toBe("32");
    expect(normalized.entities[0]?.statblockPath).toContain("under_hymn_brood.md");
  });

  it("adds lettered Under-Hymn Brood copies from the creature pool", () => {
    const state: CombatState = {
      entities: [
        {
          id: "mireward-latchling-a",
          name: "Under-Hymn Brood A",
          hp: "40",
        },
      ],
    };
    const added = prepApi().addCombatantFromPool(state, "under-hymn-brood");
    expect(added?.name).toBe("Under-Hymn Brood B");
    expect(added?.hp).toBe("110");
    expect(added?.ac).toBe("14");
    expect(added?.statblockPath).toContain("under_hymn_brood.md");
    expect(state.entities.map((entity) => entity.name)).toEqual([
      "Under-Hymn Brood A",
      "Under-Hymn Brood B",
    ]);
  });

  it("adds lettered Mireward Latchlings from the creature pool with the published sheet", () => {
    const state: CombatState = { entities: [] };
    const added = prepApi().addCombatantFromPool(state, "mireward-latchling");
    expect(added?.name).toBe("Mireward Latchling A");
    expect(added?.hp).toBe("45");
    expect(added?.ac).toBe("14");
    expect(added?.statblockPath).toContain("mireward_latchling.md");
    const normalized = prepApi().normalizeCombatState(state);
    expect(normalized.entities[0]?.name).toBe("Mireward Latchling A");
    expect(normalized.entities[0]?.statblockPath).toContain("mireward_latchling.md");
  });

  it("adds the party, Lysandra, Lysandro, and Thrin as unique named people", () => {
    const state: CombatState = { entities: [] };
    expect(prepApi().addCombatantFromPool(state, "party")?.name).toBe("Stafl");
    expect(state.entities.map((entity) => entity.name)).toEqual([
      "Baergrom",
      "Bonogo",
      "Caelynn",
      "Ephanna",
      "Karsemine",
      "Stafl",
    ]);
    expect(state.entities.every((entity) => entity.team === "pc")).toBe(true);
    expect(prepApi().addCombatantFromPool(state, "party")).toBeNull();

    const lysandra = prepApi().addCombatantFromPool(state, "lysandra");
    expect(lysandra?.name).toBe("Lysandra");
    expect(lysandra?.team).toBe("ally");
    expect(lysandra?.hp).toBe("52");
    expect(lysandra?.statblockPath).toContain("captain_lysandra_ironveil_statblock_cr4.md");
    expect(prepApi().addCombatantFromPool(state, "lysandra")).toBeNull();

    const lysandro = prepApi().addCombatantFromPool(state, "lysandro");
    expect(lysandro?.name).toBe("Lysandro");
    expect(lysandro?.statblockPath).toContain("lysandro_ironveil_character_dossier.md");

    const thrin = prepApi().addCombatantFromPool(state, "thrinn");
    expect(thrin?.name).toBe("Thrin");
    expect(thrin?.hp).toBe("20");
    expect(thrin?.maxHp).toBe("44");
    expect(thrin?.statblockPath).toContain("thrin_branchborn_character_dossier.md");
  });
});
