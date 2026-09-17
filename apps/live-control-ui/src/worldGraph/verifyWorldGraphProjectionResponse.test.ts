import { describe, expect, it } from "vitest";

import type { WorldGraphProjection, WorldGraphProjectionRequest } from "../api/types";
import { verifyWorldGraphProjectionResponse } from "./verifyWorldGraphProjectionResponse";

function request(
  overrides: Partial<WorldGraphProjectionRequest> = {},
): WorldGraphProjectionRequest {
  return {
    schema: "dmb_world_graph_projection_request_v1",
    worldId: "eldyrwild",
    campaignId: "longmont-c2",
    scopeMode: "campaign",
    focus: { kind: "none", sessionId: null },
    admissibility: "gm",
    ...overrides,
  };
}

function projection(
  snapshotOverrides: Partial<WorldGraphProjection["snapshot"]> = {},
): WorldGraphProjection {
  return {
    schema: "dmb_world_graph_projection_v1",
    snapshot: {
      worldId: "eldyrwild",
      campaignId: "longmont-c2",
      revisionId: "rev-head",
      headRevisionId: "rev-head",
      isHead: true,
      focus: { kind: "none", sessionId: null },
      admissibility: "gm",
      scopeMode: "campaign",
      ...snapshotOverrides,
    },
    summary: {
      nodeCount: 0,
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
  };
}

describe("verifyWorldGraphProjectionResponse", () => {
  it("accepts a world-union snapshot that omits campaign identity", () => {
    expect(
      verifyWorldGraphProjectionResponse({
        request: request({ scopeMode: "world" }),
        response: projection({ campaignId: "", scopeMode: "world" }),
        revisionKind: "head",
      }),
    ).toBeNull();
  });

  it("still fails campaign-scoped identity mismatches", () => {
    expect(
      verifyWorldGraphProjectionResponse({
        request: request({ campaignId: "longmont-c2" }),
        response: projection({ campaignId: "longmont-c1" }),
        revisionKind: "head",
      }),
    ).toMatch(/does not match requested campaign longmont-c2/);
  });

  it("fails when a world-union snapshot claims a different standing campaign", () => {
    expect(
      verifyWorldGraphProjectionResponse({
        request: request({ scopeMode: "world", campaignId: "longmont-c2" }),
        response: projection({ campaignId: "longmont-c1", scopeMode: "world" }),
        revisionKind: "head",
      }),
    ).toMatch(/does not match requested campaign longmont-c2/);
  });
});
