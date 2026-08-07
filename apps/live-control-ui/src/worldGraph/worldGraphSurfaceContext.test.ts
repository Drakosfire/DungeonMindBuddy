import { describe, expect, it } from "vitest";

import { session23WorldGraphRecapFixture } from "../planSurface/graphPreview/worldGraphRecapFixture";
import {
  admitBuildDocumentScope,
  admitBuildObjectInsert,
  admitBuildWorldGraphBrowse,
  buildBuildWorldGraphProjectionRequest,
  buildGraphReviewCommittedProjectionRequest,
  buildWorldGraphRecapProjectionRequest,
  classifyBuildDocumentScope,
  getCampaignIdsForWorld,
  getWorldIdForCampaign,
} from "./worldGraphSurfaceContext";

describe("worldGraphSurfaceContext", () => {
  it("maps longmont campaigns to eldyrwild", () => {
    expect(getWorldIdForCampaign("longmont-c1")).toBe("eldyrwild");
    expect(getWorldIdForCampaign("longmont-c2")).toBe("eldyrwild");
    expect(getWorldIdForCampaign("unknown")).toBeNull();
  });

  it("getCampaignIdsForWorld returns mapped campaigns in sorted order", () => {
    expect(getCampaignIdsForWorld("eldyrwild")).toEqual(["longmont-c1", "longmont-c2"]);
    expect(getCampaignIdsForWorld("unknown-world")).toEqual([]);
  });

  it("classifyBuildDocumentScope distinguishes campaign, world, and unknown scopes", () => {
    expect(classifyBuildDocumentScope("longmont-c1")).toEqual({
      kind: "campaign",
      campaignId: "longmont-c1",
      worldId: "eldyrwild",
    });
    expect(classifyBuildDocumentScope("eldyrwild")).toEqual({
      kind: "world",
      worldId: "eldyrwild",
    });
    expect(classifyBuildDocumentScope("unknown-scope")).toEqual({ kind: "unknown" });
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

  it("buildGraphReviewCommittedProjectionRequest uses receipt.worldId and revisionPin", () => {
    expect(
      buildGraphReviewCommittedProjectionRequest({
        campaignId: "longmont-c2",
        sessionId: "session-25",
        receipt: {
          worldId: "eldyrwild",
          committedRevisionId: "rev:committed",
        },
      }),
    ).toEqual({
      schema: "dmb_world_graph_projection_request_v1",
      worldId: "eldyrwild",
      campaignId: "longmont-c2",
      scopeMode: "campaign",
      focus: {
        kind: "session",
        sessionId: "session-25",
        campaignId: "longmont-c2",
      },
      admissibility: "gm",
      revisionPin: "rev:committed",
    });
  });

  it("buildGraphReviewCommittedProjectionRequest fails closed on unknown or mismatched world mapping", () => {
    expect(
      buildGraphReviewCommittedProjectionRequest({
        campaignId: "unknown-campaign",
        sessionId: null,
        receipt: { worldId: "eldyrwild", committedRevisionId: "rev:committed" },
      }),
    ).toBeNull();
    expect(
      buildGraphReviewCommittedProjectionRequest({
        campaignId: "longmont-c2",
        sessionId: null,
        receipt: { worldId: "other-world", committedRevisionId: "rev:committed" },
      }),
    ).toBeNull();
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

  it("admitBuildWorldGraphBrowse admits same-world cross-campaign browse", () => {
    expect(
      admitBuildWorldGraphBrowse({
        documentCampaignId: "longmont-c1",
        projectionWorldId: "eldyrwild",
      }),
    ).toEqual({ ok: true, documentWorldId: "eldyrwild" });
    expect(
      admitBuildWorldGraphBrowse({
        documentCampaignId: "unknown-scope",
        projectionWorldId: "eldyrwild",
      }).ok,
    ).toBe(false);
  });

  it("admitBuildObjectInsert is object tenancy, not projection-anchor campaignId", () => {
    // C1 document: C1 + universal admitted; C2 denied
    expect(
      admitBuildObjectInsert({
        documentCampaignId: "longmont-c1",
        objectCampaignScope: "longmont-c1",
      }),
    ).toEqual({ ok: true });
    expect(
      admitBuildObjectInsert({
        documentCampaignId: "longmont-c1",
        objectCampaignScope: null,
      }),
    ).toEqual({ ok: true });
    expect(
      admitBuildObjectInsert({
        documentCampaignId: "longmont-c1",
        objectCampaignScope: "longmont-c2",
      }),
    ).toEqual({ ok: false, reason: "C2 object · C1 document" });

    // C2 document: inverse
    expect(
      admitBuildObjectInsert({
        documentCampaignId: "longmont-c2",
        objectCampaignScope: "longmont-c2",
      }),
    ).toEqual({ ok: true });
    expect(
      admitBuildObjectInsert({
        documentCampaignId: "longmont-c2",
        objectCampaignScope: null,
      }),
    ).toEqual({ ok: true });
    expect(
      admitBuildObjectInsert({
        documentCampaignId: "longmont-c2",
        objectCampaignScope: "longmont-c1",
      }),
    ).toEqual({ ok: false, reason: "C1 object · C2 document" });

    // World-scoped document admits all same-world objects
    expect(
      admitBuildObjectInsert({
        documentCampaignId: "eldyrwild",
        objectCampaignScope: "longmont-c1",
      }),
    ).toEqual({ ok: true });
    expect(
      admitBuildObjectInsert({
        documentCampaignId: "eldyrwild",
        objectCampaignScope: "longmont-c2",
      }),
    ).toEqual({ ok: true });
    expect(
      admitBuildObjectInsert({
        documentCampaignId: "eldyrwild",
        objectCampaignScope: null,
      }),
    ).toEqual({ ok: true });

    // Blank tenancy is malformed — fail closed (do not treat as universal).
    expect(
      admitBuildObjectInsert({
        documentCampaignId: "longmont-c1",
        objectCampaignScope: "",
      }),
    ).toEqual({
      ok: false,
      reason: "Object campaign scope is blank; world-universal requires null.",
    });
    expect(
      admitBuildObjectInsert({
        documentCampaignId: "longmont-c1",
        objectCampaignScope: "   ",
      }),
    ).toEqual({
      ok: false,
      reason: "Object campaign scope is blank; world-universal requires null.",
    });
  });
});
