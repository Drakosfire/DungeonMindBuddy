import { describe, expect, it } from "vitest";

import type { RecapIngestStatus } from "../api/types";
import { mergeInspectResult } from "./ingestResultMerge";

function makeStatus(overrides: Partial<RecapIngestStatus> = {}): RecapIngestStatus {
  return {
    schema: "dmb_raw_recap_ingest_status_v1",
    campaign_id: "longmont-c2",
    session: 24,
    status: "ready_for_planning_activation",
    states: ["session_memory_materialized", "ready_for_planning_activation"],
    paths: {},
    authority: {
      staged_raw_notes: "pre_canonical_evidence",
      canonical_recap: "canon_play",
      normalized_recap: "canon_play_prepared",
      frontmatter_seed: "reviewable_route_allowlist",
      breadcrumbed_recap: "canon_play_routed",
      session_memory: "derived_memory",
    },
    warnings: [],
    errors: [],
    next_actions: [],
    ingest_report: {},
    entity_spelling_audit: [],
    ...overrides,
  };
}

describe("mergeInspectResult", () => {
  it("uses fresh disk inspection instead of stale saved recap claims", () => {
    const draft = makeStatus({
      status: "ready_for_planning_activation",
      states: [
        "recap_reused",
        "normalized_reused",
        "frontmatter_seed_found",
        "session_memory_materialized",
        "graph_candidate_ready",
      ],
      paths: {
        canonical_recap: "old/canonical.md",
        normalized_recap: "old/normalized.md",
      },
      warnings: ["stale draft warning"],
      next_actions: ["stale draft action"],
      entity_spelling_audit: [{ source: "old staged source" }],
      ingest_report: {
        corpus_impact: [{ artifact: "normalized_recap", status: "reused" }],
        graph_preview: {
          status: "candidate_validation_ready",
          candidate_node_count: 59,
          candidate_edge_count: 33,
        },
      },
    });
    const inspected = makeStatus({
      status: "initialized",
      states: ["ingest_status_inspected"],
      paths: {
        canonical_recap: "current/canonical.md",
        normalized_recap: "current/normalized.md",
      },
      next_actions: ["Prep for ingest."],
      ingest_report: {
        corpus_impact: [{ artifact: "normalized_recap", status: "missing" }],
      },
    });

    const merged = mergeInspectResult(draft, inspected);

    expect(merged.status).toBe("initialized");
    expect(merged.states).toEqual(["ingest_status_inspected", "graph_candidate_ready"]);
    expect(merged.paths).toEqual(inspected.paths);
    expect(merged.warnings).toEqual([]);
    expect(merged.next_actions).toEqual(["Prep for ingest."]);
    expect(merged.entity_spelling_audit).toEqual([]);
    expect(merged.ingest_report?.corpus_impact).toEqual([
      { artifact: "normalized_recap", status: "missing" },
    ]);
    expect(merged.ingest_report?.graph_preview).toEqual(draft.ingest_report?.graph_preview);
  });

  it("lets inspect graph_preview win over a stale draft ready claim", () => {
    const draft = makeStatus({
      states: [
        "session_memory_materialized",
        "ready_for_planning_activation",
        "preview_union_store_ready",
      ],
      ingest_report: {
        graph_preview: {
          status: "preview_union_store_ready",
          node_count: 99,
          edge_count: 50,
        },
      },
    });
    const inspected = makeStatus({
      states: ["session_memory_materialized", "ready_for_planning_activation", "graph_preview_missing"],
      ingest_report: {
        graph_preview: { status: "missing" },
      },
    });

    const merged = mergeInspectResult(draft, inspected);

    expect(merged.ingest_report?.graph_preview?.status).toBe("missing");
    expect(merged.states).not.toContain("preview_union_store_ready");
    expect(merged.states).toContain("graph_preview_missing");
    expect(merged.states).toContain("session_memory_materialized");
    expect(merged.states).not.toContain("graph_candidate_ready");
  });

  it("keeps inspect preview_union_store_ready when draft had missing", () => {
    const draft = makeStatus({
      states: ["session_memory_materialized", "graph_preview_missing"],
      ingest_report: { graph_preview: { status: "missing" } },
    });
    const inspected = makeStatus({
      states: ["session_memory_materialized", "preview_union_store_ready"],
      ingest_report: {
        graph_preview: {
          status: "preview_union_store_ready",
          node_count: 12,
          edge_count: 8,
        },
      },
    });

    const merged = mergeInspectResult(draft, inspected);

    expect(merged.ingest_report?.graph_preview?.status).toBe("preview_union_store_ready");
    expect(merged.ingest_report?.graph_preview?.node_count).toBe(12);
    expect(merged.states).toContain("preview_union_store_ready");
    expect(merged.states).not.toContain("graph_preview_missing");
  });
});
