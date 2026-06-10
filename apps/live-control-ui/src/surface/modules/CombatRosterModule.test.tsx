import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import * as liveApi from "../../api/liveApi";
import type { CombatEncounterState } from "../../api/types";
import { CombatRosterModule } from "./CombatRosterModule";

const entity = {
  id: "drake-1",
  name: "Geomantic Drake",
  team: "enemy" as const,
  order: 1,
  init: 14,
  ac: 15,
  hp: 76,
  max_hp: 76,
  temp_hp: 0,
  defeated: false,
  notes: "",
  conditions: [],
  tags: [],
  statblock_path: "corpus/example.md",
  statblock_artifact_id: "drake-artifact",
  statblock_title: "Geomantic Drake",
  corpus_fingerprint: "abc",
  source: "corpus" as const,
  provenance: [],
};

function encounter(overrides: Partial<CombatEncounterState> = {}): CombatEncounterState {
  return {
    schema: "dmb_combat_encounter_state_v1",
    campaign_id: "longmont-c2",
    session: 22,
    encounter_id: "current-combat",
    title: "Current Combat",
    round: 1,
    active_turn_entity_id: "drake-1",
    round_start_entity_id: "drake-1",
    queue_model: "circular_barrel_v1",
    entities: [entity],
    groups: [],
    provenance: [],
    updated_at: "2026-06-10T00:00:00Z",
    ...overrides,
  };
}

describe("CombatRosterModule", () => {
  afterEach(() => vi.restoreAllMocks());

  it("renders active and next actors from current combat", async () => {
    vi.spyOn(liveApi, "getCurrentCombat").mockResolvedValue(encounter());

    render(<CombatRosterModule />);

    expect(await screen.findByRole("heading", { name: /combat roster/i })).toBeInTheDocument();
    expect(screen.getAllByText("Geomantic Drake").length).toBeGreaterThan(0);
    expect(screen.getByText("Round")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /next turn/i })).toBeInTheDocument();
  });

  it("applies damage through roster controls", async () => {
    const damaged = encounter({ entities: [{ ...entity, hp: 66 }] });
    vi.spyOn(liveApi, "getCurrentCombat").mockResolvedValue(encounter());
    const deltaSpy = vi.spyOn(liveApi, "applyCombatHpDelta").mockResolvedValue({
      schema_version: "dmb_combat_mutation_v1",
      encounter: damaged,
      diagnostics: [],
    });

    render(<CombatRosterModule />);
    await screen.findByRole("heading", { name: /combat roster/i });
    await userEvent.clear(screen.getByLabelText("Damage for Geomantic Drake"));
    await userEvent.type(screen.getByLabelText("Damage for Geomantic Drake"), "10");
    await userEvent.click(screen.getByRole("button", { name: "Damage" }));

    await waitFor(() => expect(deltaSpy).toHaveBeenCalledWith("drake-1", { action: "damage", amount: 10 }));
    expect(screen.getByLabelText("HP for Geomantic Drake")).toHaveValue("66");
  });
});
