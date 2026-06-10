import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import * as liveApi from "../../api/liveApi";
import type { AddGeneratedStatblockCombatResponse, CombatEncounterState, GeneratedStatblockDetailResponse, GeneratedStatblockListResponse } from "../../api/types";
import { StatblockViewModule } from "./StatblockViewModule";

const emptyEncounter: CombatEncounterState = {
  schema: "dmb_combat_encounter_state_v1",
  campaign_id: "longmont-c2",
  session: 22,
  encounter_id: "current-combat",
  title: "Current Combat",
  round: 1,
  active_turn_entity_id: null,
  round_start_entity_id: null,
  queue_model: "circular_barrel_v1",
  entities: [],
  groups: [],
  provenance: [],
  updated_at: "2026-06-09T00:00:00Z",
};

function addResponseFor(name = "Geomantic Drake Juvenile"): AddGeneratedStatblockCombatResponse {
  const entity = {
    id: "geomantic-drake-abc123",
    name,
    team: "enemy" as const,
    order: 1,
    init: null,
    ac: 15,
    hp: 76,
    max_hp: 76,
    temp_hp: null,
    defeated: false,
    notes: "Added from generated Statblock View.",
    conditions: [],
    tags: ["generated_statblock", "corpus_backed", "statblock_view"],
    statblock_path: "corpus/eldyrwild-markdown/example.md",
    statblock_artifact_id: "statblock-one",
    statblock_title: name,
    corpus_fingerprint: "abc123",
    source: "corpus" as const,
    provenance: [],
  };
  return {
    schema_version: "dmb_add_generated_statblock_to_combat_v1",
    added_entities: [entity],
    encounter: { ...emptyEncounter, entities: [entity] },
    diagnostics: [],
  };
}

const listResponse: GeneratedStatblockListResponse = {
  schema_version: "dmb_generated_statblock_list_v1",
  diagnostics: [],
  statblocks: [
    {
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
    },
  ],
};

function detailFor(artifactId: string, title: string): GeneratedStatblockDetailResponse {
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
    available_actions: [
      {
        action_id: "add_to_combat",
        label: "Add to current combat",
        enabled: true,
        disabled_reason: null,
      },
    ],
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
      corpus_display_path: `corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/Statblocks/generated/${artifactId}.md`,
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

describe("StatblockViewModule", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  function mockCurrentCombat() {
    vi.spyOn(liveApi, "getCurrentCombat").mockResolvedValue(emptyEncounter);
  }

  it("shows empty state", async () => {
    mockCurrentCombat();
    vi.spyOn(liveApi, "listGeneratedStatblocks").mockResolvedValue({
      schema_version: "dmb_generated_statblock_list_v1",
      statblocks: [],
      diagnostics: [],
    });

    render(<StatblockViewModule />);

    expect(await screen.findByText("No corpus-backed generated statblocks yet.")).toBeInTheDocument();
  });

  it("loads list and auto-selects first detail", async () => {
    mockCurrentCombat();
    vi.spyOn(liveApi, "listGeneratedStatblocks").mockResolvedValue(listResponse);
    vi.spyOn(liveApi, "getGeneratedStatblock").mockResolvedValue(detailFor("statblock-one", "Geomantic Drake Juvenile"));

    render(<StatblockViewModule />);

    expect(await screen.findByText("Geomantic Drake Juvenile")).toBeInTheDocument();
    expect(await screen.findByText(/Armor Class 15/)).toBeInTheDocument();
    expect(screen.getByText(/AC 15 · HP 76 · CR 3/)).toBeInTheDocument();
    expect(screen.getAllByText(/Retrieval verified/).length).toBeGreaterThan(0);
    expect(screen.getByText(/generated\/statblock-one\.md/)).toBeInTheDocument();
    const addButton = screen.getByRole("button", { name: "Add to current combat" });
    expect(addButton).toBeEnabled();
    expect(screen.getByRole("region", { name: "Add to current combat" })).toBeInTheDocument();
    expect(screen.getByText(/No combatants in current combat/)).toBeInTheDocument();
  });

  it("selects a different statblock and updates detail", async () => {
    mockCurrentCombat();
    vi.spyOn(liveApi, "listGeneratedStatblocks").mockResolvedValue({
      ...listResponse,
      statblocks: [
        listResponse.statblocks[0],
        { ...listResponse.statblocks[0], artifact_id: "statblock-two", title: "Crystal Mite Swarm", armor_class: 12 },
      ],
    });
    vi.spyOn(liveApi, "getGeneratedStatblock")
      .mockResolvedValueOnce(detailFor("statblock-one", "Geomantic Drake Juvenile"))
      .mockResolvedValueOnce(detailFor("statblock-two", "Crystal Mite Swarm"));

    render(<StatblockViewModule />);

    expect(await screen.findByText(/Armor Class 15/)).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: /Crystal Mite Swarm/ }));
    expect(await screen.findByText(/# Crystal Mite Swarm/)).toBeInTheDocument();
    expect(liveApi.getGeneratedStatblock).toHaveBeenLastCalledWith("statblock-two");
  });

  it("keeps list visible when detail load fails", async () => {
    mockCurrentCombat();
    vi.spyOn(liveApi, "listGeneratedStatblocks").mockResolvedValue(listResponse);
    vi.spyOn(liveApi, "getGeneratedStatblock").mockRejectedValue(new Error("detail failed safely"));

    render(<StatblockViewModule />);

    expect(await screen.findByText("Geomantic Drake Juvenile")).toBeInTheDocument();
    expect(await screen.findByText(/Unable to load selected statblock: detail failed safely/)).toBeInTheDocument();
  });

  it("shows loading error when list fetch fails", async () => {
    mockCurrentCombat();
    vi.spyOn(liveApi, "listGeneratedStatblocks").mockRejectedValue(new Error("list failed safely"));

    render(<StatblockViewModule />);

    await waitFor(() => expect(screen.getByText(/Unable to load generated statblocks: list failed safely/)).toBeInTheDocument());
  });

  it("submits default add-to-combat request and shows current combat readback", async () => {
    mockCurrentCombat();
    vi.spyOn(liveApi, "listGeneratedStatblocks").mockResolvedValue(listResponse);
    vi.spyOn(liveApi, "getGeneratedStatblock").mockResolvedValue(detailFor("statblock-one", "Geomantic Drake Juvenile"));
    const addSpy = vi.spyOn(liveApi, "addGeneratedStatblockToCombat").mockResolvedValue(addResponseFor());

    render(<StatblockViewModule />);

    await userEvent.click(await screen.findByRole("button", { name: "Add to current combat" }));

    expect(addSpy).toHaveBeenCalledWith("statblock-one", { team: "enemy", count: 1 });
    expect(await screen.findByText("Added Geomantic Drake Juvenile to current combat.")).toBeInTheDocument();
    expect(screen.getByText(/Round 1 · 1 combatant/)).toBeInTheDocument();
  });

  it("sends changed add-to-combat options", async () => {
    mockCurrentCombat();
    vi.spyOn(liveApi, "listGeneratedStatblocks").mockResolvedValue(listResponse);
    vi.spyOn(liveApi, "getGeneratedStatblock").mockResolvedValue(detailFor("statblock-one", "Geomantic Drake Juvenile"));
    const addSpy = vi.spyOn(liveApi, "addGeneratedStatblockToCombat").mockResolvedValue(addResponseFor("South Gate Drake"));

    render(<StatblockViewModule />);

    await screen.findByLabelText("Team");
    await userEvent.selectOptions(screen.getByLabelText("Team"), "ally");
    await userEvent.clear(screen.getByLabelText("Count"));
    await userEvent.type(screen.getByLabelText("Count"), "2");
    await userEvent.type(screen.getByLabelText("Initiative"), "17");
    await userEvent.type(screen.getByLabelText("Name override"), "South Gate Drake");
    await userEvent.type(screen.getByLabelText("Notes"), "Arrives from south gate.");
    await userEvent.click(screen.getByRole("button", { name: "Add to current combat" }));

    expect(addSpy).toHaveBeenCalledWith("statblock-one", {
      team: "ally",
      count: 2,
      initiative: 17,
      name_override: "South Gate Drake",
      notes: "Arrives from south gate.",
    });
  });

  it("keeps detail visible and reports safe add-to-combat failures", async () => {
    mockCurrentCombat();
    vi.spyOn(liveApi, "listGeneratedStatblocks").mockResolvedValue(listResponse);
    vi.spyOn(liveApi, "getGeneratedStatblock").mockResolvedValue(detailFor("statblock-one", "Geomantic Drake Juvenile"));
    vi.spyOn(liveApi, "addGeneratedStatblockToCombat").mockRejectedValue(new Error("add failed safely"));

    render(<StatblockViewModule />);

    await userEvent.click(await screen.findByRole("button", { name: "Add to current combat" }));

    expect(await screen.findByText(/Unable to add to combat: add failed safely/)).toBeInTheDocument();
    expect(screen.getByText(/# Geomantic Drake Juvenile/)).toBeInTheDocument();
  });

  it("does not offer add-to-combat when no detail is selected", async () => {
    mockCurrentCombat();
    vi.spyOn(liveApi, "listGeneratedStatblocks").mockResolvedValue({
      schema_version: "dmb_generated_statblock_list_v1",
      statblocks: [],
      diagnostics: [],
    });

    render(<StatblockViewModule />);

    expect(await screen.findByText("No corpus-backed generated statblocks yet.")).toBeInTheDocument();
    expect(screen.queryByRole("region", { name: "Add to current combat" })).not.toBeInTheDocument();
  });

});
