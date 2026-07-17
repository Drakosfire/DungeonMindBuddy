import { describe, expect, it } from "vitest";

import { fixturePlanSessionDescriptor } from "../config/planSessionDescriptor";
import {
  buildPlanWorldGraphProjectionRequest,
  getPlanWorldGraphContext,
} from "./planGraphContextRequest";

const sessionDescriptor = fixturePlanSessionDescriptor({ memorySession: null });

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
});
