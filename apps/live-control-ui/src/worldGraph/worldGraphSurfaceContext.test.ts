import { describe, expect, it } from "vitest";

import { session23WorldGraphRecapFixture } from "../planSurface/graphPreview/worldGraphRecapFixture";
import {
  admitBuildDocumentScope,
  buildBuildWorldGraphProjectionRequest,
  buildWorldGraphRecapProjectionRequest,
  getWorldIdForCampaign,
} from "./worldGraphSurfaceContext";

describe("worldGraphSurfaceContext", () => {
  it("maps longmont campaigns to eldyrwild", () => {
    expect(getWorldIdForCampaign("longmont-c1")).toBe("eldyrwild");
    expect(getWorldIdForCampaign("longmont-c2")).toBe("eldyrwild");
    expect(getWorldIdForCampaign("unknown")).toBeNull();
  });

  it("buildWorldGraphRecapProjectionRequest uses session focus without revision pin", () => {
    expect(
      buildWorldGraphRecapProjectionRequest({
        campaignId: "longmont-c2",
        sessionId: "session-23",
      }),
    ).toEqual({
      schema: "dmb_world_graph_projection_request_v1",
      worldId: "eldyrwild",
      campaignId: "longmont-c2",
      scopeMode: "campaign",
      focus: { kind: "session", sessionId: "session-23", campaignId: "longmont-c2" },
      admissibility: "gm",
    });
  });

  it("buildBuildWorldGraphProjectionRequest pins revision when provided", () => {
    expect(
      buildBuildWorldGraphProjectionRequest({
        campaignId: "longmont-c2",
        revisionPin: session23WorldGraphRecapFixture.snapshot.revisionId,
      }),
    ).toEqual({
      schema: "dmb_world_graph_projection_request_v1",
      worldId: "eldyrwild",
      campaignId: "longmont-c2",
      scopeMode: "campaign",
      focus: { kind: "none", sessionId: null },
      admissibility: "gm",
      revisionPin: session23WorldGraphRecapFixture.snapshot.revisionId,
    });
  });

  it("admitBuildDocumentScope accepts campaign-scoped and world-scoped documents", () => {
    expect(
      admitBuildDocumentScope({
        documentCampaignId: "longmont-c2",
        incomingCampaignId: "longmont-c2",
      }),
    ).toEqual({ ok: true });
    expect(
      admitBuildDocumentScope({
        documentCampaignId: "eldyrwild",
        incomingCampaignId: "longmont-c2",
      }),
    ).toEqual({ ok: true });
    expect(
      admitBuildDocumentScope({
        documentCampaignId: "longmont-c1",
        incomingCampaignId: "longmont-c2",
      }).ok,
    ).toBe(false);
  });
});
