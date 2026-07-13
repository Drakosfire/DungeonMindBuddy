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
