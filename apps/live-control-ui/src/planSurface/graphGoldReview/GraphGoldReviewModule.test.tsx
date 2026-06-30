import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import * as liveApi from "../../api/liveApi";
import type { PlanContextDescriptor } from "../types";
import { GraphGoldReviewModule } from "./GraphGoldReviewModule";

const context: PlanContextDescriptor = {
  campaignId: "longmont-c2",
  liveSession: 24,
  prepSession: 25,
  ingestSession: 23,
  headerLabel: "Plan",
};

describe("GraphGoldReviewModule", () => {
  afterEach(() => {
    vi.restoreAllMocks();
    window.history.replaceState({}, "", "/");
  });

  it("loads sessions and opens deep-linked session compare", async () => {
    window.history.replaceState({}, "", "/plan?tool=graph-gold-review&session=session-23");
    vi.spyOn(liveApi, "getGoldReviewSessions").mockResolvedValue({
      schema_version: "dmb_graph_gold_review_sessions_v1",
      version: "0.1",
      sessions: [
        {
          session_id: "session-22",
          session_number: 22,
          campaign_id: "longmont-c2",
          gold_fixture_id: "gold-22",
          gold_manifest_path: "m22",
          gold_graph_path: "g22",
          gold_counts: { nodes: 1 },
          available_runs: [],
        },
        {
          session_id: "session-23",
          session_number: 23,
          campaign_id: "longmont-c2",
          gold_fixture_id: "gold-23",
          gold_manifest_path: "m23",
          gold_graph_path: "g23",
          gold_counts: { nodes: 2 },
          available_runs: [
            {
              manifest_path: "out/session-23/graph_ingest_run_manifest.json",
              run_dir: "out/session-23",
              campaign_id: "longmont-c2",
              session_id: "session-23",
              status: "preview_union_store_ready",
              node_count: 2,
              edge_count: 1,
              evidence_ref_count: 1,
              next_actions: [],
            },
          ],
        },
      ],
    });
    const compareSpy = vi.spyOn(liveApi, "getGoldReviewCompare").mockResolvedValue({
      schema_version: "dmb_graph_gold_review_compare_v1",
      version: "0.1",
      session_id: "session-23",
      campaign_id: "longmont-c2",
      gold_fixture_id: "gold-23",
      gold_manifest_path: "m23",
      gold_graph_path: "g23",
      live_run: null,
      comparison: {
        scores: {
          node_recall: 0,
          edge_recall: 0,
          beat_recall: 0,
          proposed_write_recall: 0,
        },
        coverage: {
          missing_gold_nodes: [{ id: "node:lysandro", label: "Lysandro" }],
          gold_nodes_total: 1,
          candidate_nodes_total: 0,
          matched_nodes: [],
        },
        soft_misses: [],
      },
      object_index: { gold: {}, live: {} },
      match_pairs: {},
    });
    vi.spyOn(liveApi, "getGoldReviewVocabularyAblation").mockResolvedValue({
      schema_version: "dmb_vocabulary_ablation_dogfood_v1",
      version: "0.1",
      generated_at: "2026-06-30T03:49:35Z",
      scope: "c2s23-mireward",
      session_id: "session-23",
      campaign_id: "longmont-c2",
      model_id: "gpt-5.4-mini",
      report_path: "Docs/Reports/GRAPH-MEMORY-VOCABULARY-ABLATION-DOGFOOD-C2S23-MIREWARD.md",
      packet_id: "packet:vocab:4f671bfb39e9",
      source_span_count: 13,
      source_files: [],
      recommendation:
        "Do not promote edge_and_node_packet from this run: present-set recognition tied baseline, while the heuristic winner contaminated absent-set names. If continuing packet-assisted dogfood, use edge_packet as the clean comparison and keep baseline as the safety control.",
      comparison: {
        best_variant: "node_packet",
        summary: {
          known_name_pickup_best_variant: "node_packet",
          predicate_hint_best_variant: "edge_packet",
          combat_encounter_best_variant: "baseline",
          safest_collision_variant: "node_packet",
        },
        warnings: [],
      },
      variant_setup: [
        {
          variant_name: "baseline",
          enable_node_packet: false,
          enable_edge_packet: false,
          node_count: 62,
          edge_count: 37,
          score: -19,
          known_name_pickup_rate: 0.333,
          recognition_rate: 0.571,
          present_recognized: ["Edge", "Mireward Reach", "North gate", "Orik Tane"],
          contamination_count: 0,
          contamination_rate: 0,
          absent_contaminated: [],
          combat_encounter_match_count: 0,
          predicate_hint_match_count: 0,
          unsafe_cross_class_blocked_count: 1,
        },
        {
          variant_name: "node_packet",
          enable_node_packet: true,
          enable_edge_packet: false,
          node_count: 52,
          edge_count: 35,
          score: 0,
          known_name_pickup_rate: 0.583,
          recognition_rate: 0.571,
          present_recognized: ["Edge", "Mireward Reach", "North gate", "Orik Tane"],
          contamination_count: 3,
          contamination_rate: 0.6,
          absent_contaminated: ["Mireward Council", "Shepherds", "Under-Hymn Brood"],
          combat_encounter_match_count: 0,
          predicate_hint_match_count: 3,
          unsafe_cross_class_blocked_count: 0,
        },
      ],
      partition: {
        present_set: [
          "Mireward Reach",
          "Lysandra",
          "Lysandro",
          "Orik Tane",
          "Edge",
          "North gate",
          "First meat wave",
        ],
        absent_set: ["Maelthor", "The Shepherd", "Shepherds", "Under-Hymn Brood", "Mireward Council"],
      },
    });
    vi.spyOn(liveApi, "getGoldReviewEvidence").mockResolvedValue({
      schema_version: "dmb_graph_gold_review_evidence_v1",
      version: "0.1",
      session_id: "session-23",
      campaign_id: "longmont-c2",
      object_kind: "nodes",
      object_id: "node:lysandro",
      matched: false,
      gold: {
        object_id: "node:lysandro",
        object_kind: "nodes",
        label: "Lysandro",
        payload: {},
        evidence: [
          {
            source_anchor_id: "anchor:s23-mayor-orik-tane-inn-debate",
            preview_snippet: "Lysandro argued with the mayor",
            paragraph_text: "Lysandro argued with the mayor",
            line_start: 12,
            line_end: 12,
          },
        ],
      },
      live: {
        object_id: "node:lysandro-live",
        object_kind: "nodes",
        label: "Lysandro (live)",
        payload: {},
        evidence: [
          {
            preview_snippet: "father Lysandro arrived",
            paragraph_text: "father Lysandro arrived",
          },
        ],
      },
    });

    render(<GraphGoldReviewModule context={context} />);

    await waitFor(() => {
      expect(compareSpy).toHaveBeenCalledWith({
        campaignId: "longmont-c2",
        sessionId: "session-23",
        manifestPath: "out/session-23/graph_ingest_run_manifest.json",
      });
    });

    expect(screen.getByRole("tab", { name: "Session 23" })).toHaveAttribute("aria-selected", "true");
    expect(await screen.findByText("C2S23 Mireward dogfood")).toBeInTheDocument();
    expect(screen.getByText(/Do not promote edge_and_node_packet/)).toBeInTheDocument();
    expect(screen.getAllByText("57.1%").length).toBeGreaterThan(0);
    expect(screen.getByText("60% (3)")).toBeInTheDocument();
    expect(screen.getByText(/Under-Hymn Brood/)).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: /Lysandro/i }));
    expect(await screen.findByText("Gold expected")).toBeInTheDocument();
    expect(screen.getByText("Lysandro argued with the mayor")).toBeInTheDocument();
    expect(screen.getByText("father Lysandro arrived")).toBeInTheDocument();
  });
});
