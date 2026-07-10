import { describe, expect, it } from "vitest";

import { createPlanCanvasStorageKey } from "../config/planSessionDescriptor";
import type { PlanSessionDescriptor } from "../types";
import {
  buildPlanGraphContextRequest,
  PLAN_GRAPH_PROJECTION_UNAVAILABLE_COPY,
} from "./planGraphContextRequest";

const sessionDescriptor: PlanSessionDescriptor = {
  surfaceId: "plan",
  campaignId: "longmont-c2",
  campaignLabel: "Longmont C2",
  prepSession: 23,
  memorySession: 21,
  liveSession: 22,
  sourceStatusLabel: "Session 21",
  sourceStatusKind: "unknown",
  planningDocument: {
    documentId: "longmont-c2-session-23-prep",
    title: "Longmont C2 Session 23 Prep",
    targetRelpath: "corpus/example/Session 23 Prep.md",
    storageKey: createPlanCanvasStorageKey({
      campaignId: "longmont-c2",
      prepSession: 23,
      documentId: "longmont-c2-session-23-prep",
    }),
    status: "local_draft",
  },
};

describe("buildPlanGraphContextRequest", () => {
  it("mirrors the current latest-ingest memorySession lookup", () => {
    expect(buildPlanGraphContextRequest(sessionDescriptor)).toEqual({
      campaignId: "longmont-c2",
      prepSession: 23,
      memorySession: 21,
      liveSession: 22,
      requestedSessionId: "session-21",
      projectionMode: "latest-ingest",
    });
  });

  it("keeps unavailable copy free of memory-session framing", () => {
    expect(PLAN_GRAPH_PROJECTION_UNAVAILABLE_COPY).toMatch(/Plan graph context/i);
    expect(PLAN_GRAPH_PROJECTION_UNAVAILABLE_COPY).not.toMatch(/memory session/i);
  });
});
