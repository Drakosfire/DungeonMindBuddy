import { describe, expect, it } from "vitest";

import {
  buildPlanWorldGraphProjectionRequest,
  getPlanWorldGraphContext,
} from "./planGraphContextRequest";

const sessionDescriptor = {
  surfaceId: "plan" as const,
  campaignId: "longmont-c2",
  campaignLabel: "Longmont C2",
  prepSession: 23,
  memorySession: null as number | null,
  liveSession: 22,
  sourceStatusLabel: "World graph",
  sourceStatusKind: "unknown" as const,
  planningDocument: {
    documentId: "longmont-c2-session-23-prep",
    title: "C2 Session 23 Prep",
    targetRelpath: "corpus/example.md",
    storageKey: "storage-key",
    status: "local_draft" as const,
  },
};

describe("planGraphContextRequest", () => {
  it("defaults World Graph focus to none when memory session is unset", () => {
    const context = getPlanWorldGraphContext(sessionDescriptor);

    expect(context).toEqual({
      worldId: "eldyrwild",
      campaignId: "longmont-c2",
      focus: { kind: "none", sessionId: null },
    });
    expect(buildPlanWorldGraphProjectionRequest(context!)).toEqual({
      schema: "dmb_world_graph_projection_request_v1",
      worldId: "eldyrwild",
      campaignId: "longmont-c2",
      focus: { kind: "none", sessionId: null },
      admissibility: "gm",
    });
  });

  it("maps an explicit memory session to a session focus lens", () => {
    const context = getPlanWorldGraphContext({ ...sessionDescriptor, memorySession: 24 });

    expect(context).toEqual({
      worldId: "eldyrwild",
      campaignId: "longmont-c2",
      focus: { kind: "session", sessionId: "session-24" },
    });
  });

  it("rejects unsupported campaigns", () => {
    expect(getPlanWorldGraphContext({ ...sessionDescriptor, campaignId: "unknown-campaign" })).toBeNull();
  });
});
