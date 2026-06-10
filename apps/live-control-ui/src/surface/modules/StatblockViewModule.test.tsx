import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import * as liveApi from "../../api/liveApi";
import type { GeneratedStatblockDetailResponse, GeneratedStatblockListResponse } from "../../api/types";
import { StatblockViewModule } from "./StatblockViewModule";

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

  it("shows empty state", async () => {
    vi.spyOn(liveApi, "listGeneratedStatblocks").mockResolvedValue({
      schema_version: "dmb_generated_statblock_list_v1",
      statblocks: [],
      diagnostics: [],
    });

    render(<StatblockViewModule />);

    expect(await screen.findByText("No corpus-backed generated statblocks yet.")).toBeInTheDocument();
  });

  it("loads list and auto-selects first detail", async () => {
    vi.spyOn(liveApi, "listGeneratedStatblocks").mockResolvedValue(listResponse);
    vi.spyOn(liveApi, "getGeneratedStatblock").mockResolvedValue(detailFor("statblock-one", "Geomantic Drake Juvenile"));

    render(<StatblockViewModule />);

    expect(await screen.findByText("Geomantic Drake Juvenile")).toBeInTheDocument();
    expect(await screen.findByText(/Armor Class 15/)).toBeInTheDocument();
    expect(screen.getByText(/AC 15 · HP 76 · CR 3/)).toBeInTheDocument();
    expect(screen.getAllByText(/Retrieval verified/).length).toBeGreaterThan(0);
    expect(screen.getByText(/generated\/statblock-one\.md/)).toBeInTheDocument();
    const addButton = screen.getByRole("button", { name: "Add to current combat" });
    expect(addButton).toBeDisabled();
    expect(addButton).toHaveAttribute("title", "Statblock View is read-only in PR111.");
  });

  it("selects a different statblock and updates detail", async () => {
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
    vi.spyOn(liveApi, "listGeneratedStatblocks").mockResolvedValue(listResponse);
    vi.spyOn(liveApi, "getGeneratedStatblock").mockRejectedValue(new Error("detail failed safely"));

    render(<StatblockViewModule />);

    expect(await screen.findByText("Geomantic Drake Juvenile")).toBeInTheDocument();
    expect(await screen.findByText(/Unable to load selected statblock: detail failed safely/)).toBeInTheDocument();
  });

  it("shows loading error when list fetch fails", async () => {
    vi.spyOn(liveApi, "listGeneratedStatblocks").mockRejectedValue(new Error("list failed safely"));

    render(<StatblockViewModule />);

    await waitFor(() => expect(screen.getByText(/Unable to load generated statblocks: list failed safely/)).toBeInTheDocument());
  });
});
