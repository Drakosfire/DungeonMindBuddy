import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import * as liveApi from "../../api/liveApi";
import * as combatApi from "../../combat/combatApi";
import type { AddGeneratedStatblockResponse, CombatEncounterRecord } from "../../combat/combatTypes";
import * as selectedWorld from "../../selectedWorld/SelectedWorldContext";
import type { GeneratedStatblockDetailResponse, GeneratedStatblockListResponse } from "../../api/types";
import { StatblockViewModule } from "./StatblockViewModule";

function encounter(overrides: Partial<CombatEncounterRecord> = {}): CombatEncounterRecord {
  return {
    encounter_id: "3f620410-21cb-4d18-88d4-5ea5e60b0b14",
    world_id: "elderwyld",
    campaign_id: "longmont-c2",
    session: 29,
    revision: 1,
    ruleset: {
      schema: "dmb_combat_ruleset_v1",
      config_id: "generic.manual-tracking",
      system_id: "generic",
      edition_id: "manual",
      revision: "1",
      mode: "manual_tracking",
      fields: [],
      manual_defaults: {},
    },
    ruleset_digest: "a".repeat(64),
    draft: {
      schema: "dmb_combat_encounter_draft_v1",
      title: "Mireward Gate",
      round: 1,
      active_turn_entity_id: null,
      round_start_entity_id: null,
      queue_model: "circular_barrel_v1",
      entities: [],
      groups: [],
      provenance: [],
    },
    created_at: "2026-10-17T12:00:00Z",
    updated_at: "2026-10-17T12:00:00Z",
    ...overrides,
  };
}

const listResponse: GeneratedStatblockListResponse = {
  schema_version: "dmb_generated_statblock_list_v1",
  diagnostics: [],
  statblocks: [{
    artifact_id: "statblock-one",
    draft_id: "draft-one",
    title: "Geomantic Drake Juvenile",
    campaign_id: "longmont-c2",
    session: 22,
    review_status: "needs_dm_review",
    lifecycle_state: "corpus_promoted",
    storage_status: "stored_draft",
    corpus_status: "promotion_confirmed",
    retrieval_status: "retrieval_verified",
    corpus_relpath: "Longmont Campaign/Campaign 2/Statblocks/generated/geomantic_drake.md",
    corpus_display_path: "corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/Statblocks/generated/geomantic_drake.md",
    corpus_written_at: "2026-06-09T00:00:00Z",
    retrieval_verified_at: "2026-06-09T00:01:00Z",
    armor_class: 15,
    hit_points: 76,
    challenge_rating: "3",
    creature_type: "dragon",
    primary_actions: ["Bite", "Geomantic Breath"],
    warning_count: 1,
  }],
};

function detailFor(artifactId = "statblock-one", title = "Geomantic Drake Juvenile"): GeneratedStatblockDetailResponse {
  return {
    schema_version: "dmb_generated_statblock_detail_v1",
    artifact_id: artifactId,
    draft_id: `${artifactId}-draft`,
    title,
    corpus_relpath: `Longmont Campaign/Campaign 2/Statblocks/generated/${artifactId}.md`,
    corpus_display_path: `corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/Statblocks/generated/${artifactId}.md`,
    corpus_markdown: `# ${title}\n\nArmor Class 15\nHit Points 76\nGeomantic Breath.`,
    corpus_markdown_bytes: 72,
    corpus_file_fingerprint: "abc123",
    combat_defaults: {
      name: title,
      armor_class: 15,
      hit_points: 76,
      initiative_bonus: 2,
      speed_summary: "30 ft., burrow 10 ft.",
      senses_summary: "darkvision 60 ft.",
      primary_actions: ["Bite", "Geomantic Breath"],
    },
    warnings: [{ code: "needs_dm_review", message: "Review damage numbers.", severity: "warning" }],
    provenance: { generator: "mock" },
    breadcrumbs: [{ label: "surface:statblock_view", source: "test", metadata: {} }],
    source_refs: [{ label: "source" }],
    retrieval: {
      status: "retrieval_verified",
      verified_at: "2026-06-09T00:01:00Z",
      evidence_path: "corpus/eldyrwild-markdown/example.md",
    },
    available_actions: [{ action_id: "add_to_combat", label: "Add to current combat", enabled: true, disabled_reason: null }],
    diagnostics: [],
    stored_record: {
      schema_version: "dmb_statblock_draft_record_v1",
      artifact_id: artifactId,
      title,
      campaign_id: "longmont-c2",
      session: 22,
      stored_at: "2026-06-09T00:00:00Z",
      updated_at: "2026-06-09T00:00:00Z",
      storage_path: `statblock_drafts/${artifactId}.json`,
      corpus_relpath: `Longmont Campaign/Campaign 2/Statblocks/generated/${artifactId}.md`,
      corpus_display_path: "corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/Statblocks/generated/example.md",
      corpus_written_at: "2026-06-09T00:00:00Z",
      retrieval_status: "retrieval_verified",
      artifact: {
        artifact_id: artifactId,
        draft_id: `${artifactId}-draft`,
        title,
        markdown: `## ${title}`,
        structured_statblock: {},
        combat_defaults: { armor_class: 15, hit_points: 76 },
        warnings: [],
        provenance: {},
        review_status: "needs_dm_review",
        lifecycle_state: "corpus_promoted",
        storage_status: "stored_draft",
        corpus_status: "promotion_confirmed",
        source_refs: [],
        breadcrumbs: [],
        created_by: "agent",
        created_at: "2026-06-09T00:00:00Z",
        updated_at: "2026-06-09T00:00:00Z",
      },
    },
  };
}

function addedResponse(): AddGeneratedStatblockResponse {
  const added = {
    id: "geomantic-drake-abc123",
    name: "Geomantic Drake Juvenile",
    team: "enemy" as const,
    order: 1,
    init: null,
    ac: 15,
    hp: 76,
    max_hp: 76,
    temp_hp: 0,
    defeated: false,
    notes: "Added from generated Statblock View.",
    conditions: [],
    tags: ["generated_statblock", "corpus_backed", "statblock_view"],
    statblock_path: "corpus/eldyrwild-markdown/example.md",
    statblock_artifact_id: "statblock-one",
    statblock_title: "Geomantic Drake Juvenile",
    corpus_fingerprint: "abc123",
    source: "corpus" as const,
    provenance: [],
  };
  return {
    added_entities: [added],
    encounter: encounter({ draft: { ...encounter().draft, entities: [added] } }),
  };
}

function deferred<T>() {
  let resolve!: (value: T) => void;
  const promise = new Promise<T>((resolvePromise) => { resolve = resolvePromise; });
  return { promise, resolve };
}

describe("StatblockViewModule", () => {
  afterEach(() => vi.restoreAllMocks());

  function mount(encounters = [encounter()]) {
    let worldId = "elderwyld";
    vi.spyOn(selectedWorld, "useSelectedWorld").mockImplementation(() => ({
      kind: "managed", worldId, name: worldId === "elderwyld" ? "Elderwyld" : "Conks and Cons", documentId: null,
    }));
    vi.spyOn(combatApi, "listWorldCombatEncounters").mockResolvedValue(encounters);
    vi.spyOn(liveApi, "listGeneratedStatblocks").mockResolvedValue(listResponse);
    vi.spyOn(liveApi, "getGeneratedStatblock").mockResolvedValue(detailFor());
    const view = render(<StatblockViewModule />);
    return {
      ...view,
      setWorld(nextWorldId: string) {
        worldId = nextWorldId;
        view.rerender(<StatblockViewModule />);
      },
    };
  }

  it("requires an explicit target encounter before adding a statblock", async () => {
    mount();
    const addButton = await screen.findByRole("button", { name: "Add to encounter" });
    expect(addButton).toBeDisabled();
    expect(screen.getByText("Choose the encounter that should receive this statblock.")).toBeInTheDocument();

    await screen.findByRole("option", { name: "Mireward Gate · rev 1" });
    await userEvent.selectOptions(screen.getByRole("combobox", { name: "Encounter to receive statblock" }), encounter().encounter_id);
    expect(addButton).toBeEnabled();
    const addSpy = vi.spyOn(combatApi, "addGeneratedStatblockToEncounter").mockResolvedValue(addedResponse());
    await userEvent.click(addButton);

    expect(addSpy).toHaveBeenCalledWith("elderwyld", encounter().encounter_id, "statblock-one", { team: "enemy", count: 1 });
    expect(await screen.findByText("Added Geomantic Drake Juvenile to Mireward Gate.")).toBeInTheDocument();
    expect(screen.getByText(/Round 1 · 1 combatant · rev 1/)).toBeInTheDocument();
  });

  it("sends changed add-to-encounter options", async () => {
    mount();
    vi.spyOn(combatApi, "addGeneratedStatblockToEncounter").mockResolvedValue(addedResponse());
    await screen.findByRole("option", { name: "Mireward Gate · rev 1" });
    await userEvent.selectOptions(screen.getByRole("combobox", { name: "Encounter to receive statblock" }), encounter().encounter_id);
    await userEvent.selectOptions(screen.getByLabelText("Team"), "ally");
    await userEvent.clear(screen.getByLabelText("Count"));
    await userEvent.type(screen.getByLabelText("Count"), "2");
    await userEvent.type(screen.getByLabelText("Initiative"), "17");
    await userEvent.type(screen.getByLabelText("Name override"), "South Gate Drake");
    await userEvent.type(screen.getByLabelText("Notes"), "Arrives from south gate.");
    await userEvent.click(await screen.findByRole("button", { name: "Add to encounter" }));

    expect(combatApi.addGeneratedStatblockToEncounter).toHaveBeenCalledWith("elderwyld", encounter().encounter_id, "statblock-one", {
      team: "ally", count: 2, initiative: 17, name_override: "South Gate Drake", notes: "Arrives from south gate.",
    });
  });

  it("ignores an add response after its target World changes A→B→A", async () => {
    const pendingAdd = deferred<AddGeneratedStatblockResponse>();
    const currentEncounter = encounter();
    const otherWorldEncounter = encounter({
      world_id: "conks-and-cons",
      encounter_id: "d94ebf8a-7f0e-4ff2-a1b8-69916f6a79d1",
      draft: { ...encounter().draft, title: "Conks encounter" },
    });
    const view = mount();
    vi.spyOn(combatApi, "listWorldCombatEncounters").mockImplementation(async (worldId) =>
      worldId === "elderwyld" ? [currentEncounter] : [otherWorldEncounter]);
    const addSpy = vi.spyOn(combatApi, "addGeneratedStatblockToEncounter").mockReturnValue(pendingAdd.promise);

    await screen.findByRole("option", { name: "Mireward Gate · rev 1" });
    await userEvent.selectOptions(screen.getByRole("combobox", { name: "Encounter to receive statblock" }), currentEncounter.encounter_id);
    await userEvent.click(await screen.findByRole("button", { name: "Add to encounter" }));
    expect(addSpy).toHaveBeenCalledWith("elderwyld", currentEncounter.encounter_id, "statblock-one", { team: "enemy", count: 1 });

    view.setWorld("conks-and-cons");
    await screen.findByRole("option", { name: "Conks encounter · rev 1" });
    view.setWorld("elderwyld");
    await screen.findByRole("option", { name: "Mireward Gate · rev 1" });
    await userEvent.selectOptions(
      screen.getByRole("combobox", { name: "Encounter to receive statblock" }),
      currentEncounter.encounter_id,
    );

    pendingAdd.resolve(addedResponse());
    await waitFor(() => expect(screen.getByText(/Round 1 · 0 combatants · rev 1/)).toBeInTheDocument());
    expect(screen.queryByText("Added Geomantic Drake Juvenile to Mireward Gate.")).not.toBeInTheDocument();
  });

  it("shows safe errors and keeps the statblock visible", async () => {
    mount();
    vi.spyOn(combatApi, "addGeneratedStatblockToEncounter").mockRejectedValue(new Error("stale revision"));
    await screen.findByRole("option", { name: "Mireward Gate · rev 1" });
    await userEvent.selectOptions(screen.getByRole("combobox", { name: "Encounter to receive statblock" }), encounter().encounter_id);
    await userEvent.click(await screen.findByRole("button", { name: "Add to encounter" }));

    expect(await screen.findByText(/Unable to add to combat: stale revision/)).toBeInTheDocument();
    expect(screen.getByText(/# Geomantic Drake Juvenile/)).toBeInTheDocument();
  });

  it("loads generated statblocks and reports the empty state", async () => {
    vi.spyOn(selectedWorld, "useSelectedWorld").mockReturnValue({
      kind: "managed", worldId: "elderwyld", name: "Elderwyld", documentId: null,
    });
    vi.spyOn(combatApi, "listWorldCombatEncounters").mockResolvedValue([]);
    vi.spyOn(liveApi, "listGeneratedStatblocks").mockResolvedValue({ schema_version: "dmb_generated_statblock_list_v1", statblocks: [], diagnostics: [] });

    render(<StatblockViewModule />);

    expect(await screen.findByText("No corpus-backed generated statblocks yet.")).toBeInTheDocument();
  });
});
