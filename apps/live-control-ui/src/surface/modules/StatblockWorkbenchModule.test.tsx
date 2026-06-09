import { render, screen, waitFor, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import * as liveApi from "../../api/liveApi";
import type { StatblockWorkbenchSampleResponse } from "../../api/types";
import { StatblockWorkbenchModule } from "./StatblockWorkbenchModule";

const sampleResponse: StatblockWorkbenchSampleResponse = {
  schema_version: "dmb_statblock_workbench_sample_v1",
  mode: "sample_mock",
  command_status: "ok",
  diagnostics: ["sample endpoint uses MockStatBlockGeneratorProvider only"],
  available_actions: [
    {
      action_id: "store_draft",
      label: "Store draft",
      enabled: true,
      disabled_reason: null,
    },
    {
      action_id: "add_to_combat",
      label: "Add to combat",
      enabled: false,
      disabled_reason: "Disabled in PR3: future lifecycle PR will make this action durable.",
    },
  ],
  artifact: {
    artifact_id: "statblock-draft-test",
    draft_id: "mock-generated-draft",
    title: "Geomantic Drake Juvenile",
    markdown: "## Geomantic Drake Juvenile\nClaw. Bite. Shifting stone.",
    structured_statblock: { name: "Geomantic Drake Juvenile" },
    combat_defaults: {
      name: "Geomantic Drake Juvenile",
      armor_class: 15,
      hit_points: 68,
      initiative_bonus: 2,
      passive_perception: 13,
      speed_summary: "30 ft., burrow 10 ft.",
      senses_summary: "darkvision 60 ft.",
      primary_actions: ["Bite", "Stone Skitter"],
      suggested_tactics: ["Open from cover"],
      legendary_actions: null,
    },
    warnings: [
      {
        code: "needs_dm_review",
        message: "Review damage numbers before table use.",
        severity: "warning",
        path: "statblock.actions[0]",
      },
    ],
    provenance: { generator: "mock-statblock-generator", mode: "generate_from_prompt" },
    review_status: "needs_dm_review",
    lifecycle_state: "live_draft",
    storage_status: "not_stored",
    corpus_status: "not_promoted",
    source_refs: [{ label: "Geomantic drake seed", path: "corpus/example.md" }],
    breadcrumbs: [
      { label: "campaign:c2", source: "sample_fixture", metadata: {} },
      { label: "surface:statblock_workbench", source: "live_control", metadata: {} },
    ],
    created_by: "agent",
    created_at: "2026-06-09T00:00:00Z",
    updated_at: "2026-06-09T00:00:00Z",
  },
};

describe("StatblockWorkbenchModule", () => {
  it("renders the read-only sample artifact lifecycle surface", async () => {
    vi.spyOn(liveApi, "getStatblockWorkbenchSample").mockResolvedValue(sampleResponse);

    render(<StatblockWorkbenchModule />);

    expect(screen.getByText(/Loading read-only sample artifact/i)).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getByText("Sample / mock / read-only")).toBeInTheDocument();
    });

    expect(screen.getByText(/Lifecycle preview for/i)).toBeInTheDocument();
    expect(screen.getAllByText("Geomantic Drake Juvenile").length).toBeGreaterThan(0);
    expect(screen.getByText(/Claw\. Bite\. Shifting stone\./)).toBeInTheDocument();
    expect(screen.getByText("Armor Class")).toBeInTheDocument();
    expect(screen.getByText("Bite, Stone Skitter")).toBeInTheDocument();
    expect(screen.getAllByText("needs_dm_review").length).toBeGreaterThan(0);
    expect(screen.getByText("not_stored")).toBeInTheDocument();
    expect(screen.getByText("not_promoted")).toBeInTheDocument();
    expect(screen.getByText("campaign:c2")).toBeInTheDocument();
    expect(screen.getByText(/Review damage numbers/)).toBeInTheDocument();
    expect(screen.getByText("Provenance")).toBeInTheDocument();
    expect(screen.getByText("Source refs")).toBeInTheDocument();

    const storeButton = screen.getByRole("button", { name: "Store draft" });
    const combatButton = screen.getByRole("button", { name: "Add to combat" });
    expect(storeButton).toBeDisabled();
    expect(combatButton).toBeDisabled();
    expect(within(storeButton.closest(".statblock-action-card") as HTMLElement).getByText(/read-only sample mode/)).toBeInTheDocument();
  });
});
