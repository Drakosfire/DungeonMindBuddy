import { describe, expect, it } from "vitest";

import type { RecapIngestStatus } from "../api/types";
import { buildIngestReadiness } from "./ingestReadiness";

function makeStatus(overrides: Partial<RecapIngestStatus> = {}): RecapIngestStatus {
  return {
    schema: "dmb_raw_recap_ingest_status_v1",
    campaign_id: "longmont-c2",
    session: 24,
    status: "ready_for_planning_activation",
    states: [
      "recap_reused",
      "normalized_reused",
      "breadcrumb_found",
      "session_memory_materialized",
      "ready_for_planning_activation",
      "ingest_status_inspected",
    ],
    paths: {
      canonical_recap:
        "Longmont Campaign/Campaign 2/Session Recaps/Session 24 - Mireward Gate Battle.md",
      normalized_recap:
        "Longmont Campaign/Campaign 2/Session Recaps/_normalized/Session 24 - Mireward Gate Battle.md",
    },
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
    ingest_report: {
      graph_preview: { status: "missing" },
    },
    entity_spelling_audit: [],
    ...overrides,
  };
}

describe("buildIngestReadiness", () => {
  it("marks memory ready and graph not ready without claiming complete", () => {
    const readiness = buildIngestReadiness(makeStatus());

    expect(readiness.memory.state).toBe("ready");
    expect(readiness.graph.state).toBe("not_ready");
    expect(readiness.isComplete).toBe(false);
    expect(readiness.nextAction).toMatch(/category graph extraction/i);
    expect(readiness.nextAction).not.toMatch(/^Complete:/);
  });

  it("reports complete only when memory and preview graph are both ready", () => {
    const readiness = buildIngestReadiness(
      makeStatus({
        states: [
          "session_memory_materialized",
          "ready_for_planning_activation",
          "preview_union_store_ready",
        ],
        ingest_report: {
          graph_preview: { status: "preview_union_store_ready", node_count: 12, edge_count: 8 },
        },
      }),
    );

    expect(readiness.memory.state).toBe("ready");
    expect(readiness.graph.state).toBe("ready");
    expect(readiness.isComplete).toBe(true);
    expect(readiness.nextAction).toMatch(/^Complete:/);
  });

  it("surfaces blocked graph extraction in Attention and next action", () => {
    const readiness = buildIngestReadiness(
      makeStatus({
        ingest_report: {
          graph_preview: {
            status: "failed",
            extraction_mode: "llm_blocked",
            blocked_reason: "party roster required",
          },
        },
      }),
    );

    expect(readiness.graph.state).toBe("blocked");
    expect(readiness.attention.state).toBe("blocked");
    expect(readiness.attention.detail).toMatch(/party roster required/i);
    expect(readiness.nextAction).toMatch(/blocked/i);
    expect(readiness.isComplete).toBe(false);
  });

  it("asks for memory materialization before graph when breadcrumb exists", () => {
    const readiness = buildIngestReadiness(
      makeStatus({
        status: "recap_applied",
        states: ["recap_reused", "normalized_reused", "breadcrumb_found", "ingest_status_inspected"],
        ingest_report: { graph_preview: { status: "missing" } },
      }),
    );

    expect(readiness.memory.state).toBe("not_ready");
    expect(readiness.nextAction).toMatch(/Materialize Session Memory/i);
  });
});
