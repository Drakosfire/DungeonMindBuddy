import { describe, expect, it } from "vitest";

import { buildGraphNavbarStatus } from "./buildGraphNavbarStatus";

describe("buildGraphNavbarStatus", () => {
  it("reports loading as a single line", () => {
    expect(
      buildGraphNavbarStatus({
        projectionState: "loading",
        projection: null,
      }),
    ).toMatchObject({
      id: "build-navbar-graph-status",
      label: "Graph · Loading…",
      tone: "loading",
    });
  });

  it("reports ready node count and short revision", () => {
    expect(
      buildGraphNavbarStatus({
        projectionState: "ready",
        projection: {
          schema: "dmb_world_graph_projection_v1",
          snapshot: {
            worldId: "eldyrwild",
            campaignId: "longmont-c2",
            revisionId: "wg-rev-abcdefghijk",
            headRevisionId: "wg-rev-abcdefghijk",
            isHead: true,
            focus: { kind: "none", sessionId: null },
            admissibility: "gm",
            scopeMode: "campaign",
          },
          summary: {
            nodeCount: 12,
            relationshipCount: 0,
            attributeCount: 0,
            evidenceCount: 0,
            sourceArtifactCount: 0,
            projectionTruncated: false,
          },
          nodes: [],
          relationships: [],
          attributes: [],
          evidence: [],
          sourceArtifacts: [],
          diagnostics: [],
        },
      }),
    ).toMatchObject({
      label: "Graph · 12 nodes · wg-rev-abc…",
      tone: "ready",
    });
  });

  it("reports error and unavailable tones", () => {
    expect(
      buildGraphNavbarStatus({
        projectionState: "error",
        projection: null,
        projectionError: "boom",
      }).label,
    ).toBe("Graph · boom");
    expect(
      buildGraphNavbarStatus({
        projectionState: "unavailable",
        projection: null,
      }).tone,
    ).toBe("unavailable");
  });
});
