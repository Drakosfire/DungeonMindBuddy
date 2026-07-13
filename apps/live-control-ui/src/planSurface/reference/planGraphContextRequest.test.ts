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
  memorySession: 21,
  liveSession: 22,
  sourceStatusLabel: "Session 21",
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
  it("maps the Longmont C2 memory session to the Eldyrwild World Graph request", () => {
    const context = getPlanWorldGraphContext(sessionDescriptor);

    expect(context).toEqual({
      worldId: "eldyrwild",
      campaignId: "longmont-c2",
      focus: { kind: "session", sessionId: "session-21" },
    });
    expect(buildPlanWorldGraphProjectionRequest(context!)).toEqual({
      schema: "dmb_world_graph_projection_request_v1",
      worldId: "eldyrwild",
      campaignId: "longmont-c2",
      focus: { kind: "session", sessionId: "session-21" },
      admissibility: "gm",
    });
  });

  it("rejects unsupported campaigns", () => {
    expect(getPlanWorldGraphContext({ ...sessionDescriptor, campaignId: "unknown-campaign" })).toBeNull();
  });
});
