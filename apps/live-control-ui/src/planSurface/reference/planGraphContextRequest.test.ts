import { describe, expect, it } from "vitest";
import { existsSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { fixturePlanSessionDescriptor } from "../config/planSessionDescriptor";
import {
  buildPlanAgentWorldGraphQueryContextRequest,
  buildPlanWorldGraphProjectionRequest,
  getPlanWorldGraphContext,
} from "./planGraphContextRequest";

const sessionDescriptor = fixturePlanSessionDescriptor({ memorySession: null });

describe("planGraphContextRequest", () => {
  it("defaults to both-campaign world union when lens is default", () => {
    const context = getPlanWorldGraphContext(sessionDescriptor, {
      lens: {
        selectedCampaignIds: ["longmont-c1", "longmont-c2"],
        focus: null,
      },
    });

    expect(context).toEqual({
      worldId: "eldyrwild",
      campaignId: "longmont-c2",
      scopeMode: "world",
      focus: { kind: "none", sessionId: null },
    });
    expect(buildPlanWorldGraphProjectionRequest(context!)).toEqual({
      schema: "dmb_world_graph_projection_request_v1",
      worldId: "eldyrwild",
      campaignId: "longmont-c2",
      scopeMode: "world",
      focus: { kind: "none", sessionId: null },
      admissibility: "gm",
    });
    expect(buildPlanAgentWorldGraphQueryContextRequest(context!)).toEqual({
      schema: "dmb_agent_world_graph_query_context_request_v1",
      world_id: "eldyrwild",
      campaign_id: "longmont-c2",
      scope_mode: "world",
      focus: { kind: "none", session_id: null, campaign_id: null },
      admissibility: "gm",
      revision_pin: null,
    });
  });

  it("maps C1-only lens to campaign scope with qualified session focus", () => {
    const context = getPlanWorldGraphContext(
      fixturePlanSessionDescriptor({
        campaignId: "longmont-c1",
        memorySession: 3,
      }),
      {
        lens: {
          selectedCampaignIds: ["longmont-c1"],
          focus: { campaignId: "longmont-c1", sessionNumber: 3 },
        },
      },
    );

    expect(context).toEqual({
      worldId: "eldyrwild",
      campaignId: "longmont-c1",
      scopeMode: "campaign",
      focus: {
        kind: "session",
        sessionId: "session-3",
        focusCampaignId: "longmont-c1",
      },
    });
    expect(buildPlanWorldGraphProjectionRequest(context!)).toEqual({
      schema: "dmb_world_graph_projection_request_v1",
      worldId: "eldyrwild",
      campaignId: "longmont-c1",
      scopeMode: "campaign",
      focus: {
        kind: "session",
        sessionId: "session-3",
        campaignId: "longmont-c1",
      },
      admissibility: "gm",
    });
    expect(buildPlanAgentWorldGraphQueryContextRequest(context!)).toEqual({
      schema: "dmb_agent_world_graph_query_context_request_v1",
      world_id: "eldyrwild",
      campaign_id: "longmont-c1",
      scope_mode: "campaign",
      focus: {
        kind: "session",
        session_id: "session-3",
        campaign_id: "longmont-c1",
      },
      admissibility: "gm",
      revision_pin: null,
    });
  });

  it("returns null when no campaigns are selected", () => {
    expect(
      getPlanWorldGraphContext(sessionDescriptor, {
        lens: { selectedCampaignIds: [], focus: null },
      }),
    ).toBeNull();
  });

  it("honors an explicit campaign scope mode override on a world lens", () => {
    const context = getPlanWorldGraphContext(sessionDescriptor, {
      scopeMode: "campaign",
      lens: {
        selectedCampaignIds: ["longmont-c1", "longmont-c2"],
        focus: null,
      },
    });

    expect(context?.scopeMode).toBe("campaign");
    expect(buildPlanWorldGraphProjectionRequest(context!).scopeMode).toBe("campaign");
  });

  it("PR380B: longmont-c1/c2 map to eldyrwild for future neutral surface context re-export", () => {
    const c1 = getPlanWorldGraphContext(
      fixturePlanSessionDescriptor({ campaignId: "longmont-c1", memorySession: 1 }),
      {
        lens: { selectedCampaignIds: ["longmont-c1"], focus: null },
      },
    );
    const c2 = getPlanWorldGraphContext(sessionDescriptor, {
      lens: { selectedCampaignIds: ["longmont-c2"], focus: null },
    });
    expect(c1?.worldId).toBe("eldyrwild");
    expect(c2?.worldId).toBe("eldyrwild");
  });

  it("re-exports neutral worldGraphSurfaceContext helpers", async () => {
    const planContext = await import("./planGraphContextRequest");
    expect(planContext.buildWorldGraphRecapProjectionRequest).toBeTypeOf("function");
    expect(planContext.getWorldIdForCampaign("longmont-c2")).toBe("eldyrwild");
  });
});
