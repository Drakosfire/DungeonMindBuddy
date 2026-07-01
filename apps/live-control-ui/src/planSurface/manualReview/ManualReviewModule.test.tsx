import { render, screen, waitFor, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import * as liveApi from "../../api/liveApi";
import type { ManualReviewBedDetail, ManualReviewBedsResponse } from "../../api/types";
import { ManualReviewModule } from "./ManualReviewModule";

const bedsResponse: ManualReviewBedsResponse = {
  schema_version: "dmb_graph_manual_review_beds_v1",
  version: "0.1",
  generated_at: "2026-06-30T20:19:17Z",
  model_id: "gpt-5.4-mini",
  beds: [
    {
      bed_id: "c1s1-stonebridge",
      campaign_id: "longmont-c1",
      session_id: "session-1",
      source_label: "evals/graph_memory_layer/examples/session_1_recap_ingest/expected_normalized_recap.md",
      variant_names: ["baseline", "edge_and_node_packet"],
    },
    {
      bed_id: "mirathorn-city",
      campaign_id: "elderwyld",
      session_id: "mirathorn-city",
      source_label: "The City of Mirathorn.md",
      variant_names: ["baseline", "edge_and_node_packet"],
    },
  ],
};

function bedDetail(): ManualReviewBedDetail {
  return {
    schema_version: "dmb_graph_manual_review_bed_v1",
    version: "0.1",
    bed_id: "c1s1-stonebridge",
    campaign_id: "longmont-c1",
    session_id: "session-1",
    source_label: "expected_normalized_recap.md",
    generated_at: "2026-06-30T20:19:17Z",
    model_id: "gpt-5.4-mini",
    node_prompt_contexts: {
      actor_pass: "Known actors: Grishna [character]",
      location_pass: "",
      collective_pass: "",
      object_pass: "",
      thread_pass: "",
    },
    edge_prompt_context: "Known predicates: contains, located_in",
    variant_names: ["baseline", "edge_and_node_packet"],
    variants: {
      baseline: {
        variant_name: "baseline",
        node_count: 1,
        edge_count: 1,
        cost_usd: 0.01,
        nodes: [
          {
            node_id: "npc_grishna",
            label: "Grishna",
            node_type: "character",
            pass_name: "actor_pass",
            description: "Half-orc proprietor of The River's Edge Pub.",
            confidence: "medium",
            importance: "high",
            corpus_ref: null,
            evidence_span_ids: ["spref:c1s1-recap:002"],
            anchor_quotes: ["it's tavern The River's Edge Pub run by Grishna the Half-orc"],
          },
        ],
        edges: [
          {
            edge_id: "edge_1",
            from_node_id: "loc_stone_bridge",
            to_node_id: "loc_stone_bridge_bridge",
            from_label: "Stone Bridge",
            to_label: "Stone Bridge over the river",
            relationship_type: "contains",
            predicate_family: "location_hierarchy",
            confidence: "medium",
            evidence_span_ids: ["spref:c1s1-recap:002"],
            anchor_quotes: ["It has the Stone Bridge over the river"],
          },
        ],
        node_kinds: { character: 1 },
        edge_predicates: { contains: 1 },
        gold_comparison: { missing_gold_node_labels: ["Bonogo"], extra_candidate_node_labels: [] },
        party_context: {},
      },
      edge_and_node_packet: {
        variant_name: "edge_and_node_packet",
        node_count: 1,
        edge_count: 0,
        cost_usd: 0.02,
        nodes: [
          {
            node_id: "npc_grishna",
            label: "Grishna",
            node_type: "character",
            pass_name: "actor_pass",
            description: "Half-orc proprietor.",
            confidence: "high",
            importance: "high",
            corpus_ref: null,
            evidence_span_ids: ["spref:c1s1-recap:002"],
            anchor_quotes: [],
          },
        ],
        edges: [],
        node_kinds: { character: 1 },
        edge_predicates: {},
        gold_comparison: { missing_gold_node_labels: [], extra_candidate_node_labels: [] },
        party_context: {},
      },
    },
  };
}

describe("ManualReviewModule", () => {
  it("loads beds, defaults to the first bed, and shows actor-pass pills for both variants", async () => {
    vi.spyOn(liveApi, "getManualReviewBeds").mockResolvedValue(bedsResponse);
    vi.spyOn(liveApi, "getManualReviewBed").mockResolvedValue(bedDetail());

    render(<ManualReviewModule />);

    expect(await screen.findByText("Baseline vs vocabulary-assisted graph review")).toBeInTheDocument();
    await waitFor(() => {
      expect(liveApi.getManualReviewBed).toHaveBeenCalledWith("c1s1-stonebridge");
    });

    expect(await screen.findByText(/Known actors: Grishna/)).toBeInTheDocument();

    const columns = screen.getAllByText("Grishna");
    expect(columns).toHaveLength(2);

    expect(await screen.findByText("Half-orc proprietor of The River's Edge Pub.")).toBeInTheDocument();
    expect(screen.getAllByText(/confidence: medium/).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/importance: high/).length).toBeGreaterThan(0);
    expect(
      screen.getByText(/it's tavern The River's Edge Pub run by Grishna the Half-orc/),
    ).toBeInTheDocument();
  });

  it("switches to the edge pass and shows edge pills with resolved labels", async () => {
    vi.spyOn(liveApi, "getManualReviewBeds").mockResolvedValue(bedsResponse);
    vi.spyOn(liveApi, "getManualReviewBed").mockResolvedValue(bedDetail());

    render(<ManualReviewModule />);

    const edgeTab = await screen.findByRole("tab", { name: "Edge" });
    edgeTab.click();

    expect(await screen.findByText(/Known predicates: contains, located_in/)).toBeInTheDocument();
    const baselineColumn = (await screen.findByText("Baseline (no vocabulary)")).closest(
      ".manual-review-column",
    ) as HTMLElement;
    expect(within(baselineColumn).getByText(/contains/)).toBeInTheDocument();
    expect(within(baselineColumn).getByText(/It has the Stone Bridge over the river/)).toBeInTheDocument();
  });

  it("shows an error state when the beds request fails", async () => {
    vi.spyOn(liveApi, "getManualReviewBeds").mockRejectedValue(new Error("no artifact"));

    render(<ManualReviewModule />);

    expect(await screen.findByText("no artifact")).toBeInTheDocument();
  });
});
