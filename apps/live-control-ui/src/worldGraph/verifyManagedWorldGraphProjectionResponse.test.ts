import { describe, expect, it } from "vitest";

import type {
  ManagedWorldGraphProjectionResponse,
  WorldGraphProjection,
  WorldGraphProjectionRequest,
} from "../api/types";
import { verifyManagedWorldGraphProjectionResponse } from "./verifyManagedWorldGraphProjectionResponse";

const request: WorldGraphProjectionRequest = {
  schema: "dmb_world_graph_projection_request_v1",
  worldId: "elderwyld",
  campaignId: "",
  scopeMode: "world",
  focus: { kind: "none", sessionId: null },
  admissibility: "gm",
};

function projection(worldId = "eldyrwild"): WorldGraphProjection {
  return {
    schema: "dmb_world_graph_projection_v1",
    snapshot: {
      worldId,
      campaignId: "",
      revisionId: "rev:head",
      headRevisionId: "rev:head",
      isHead: true,
      focus: { kind: "none", sessionId: null },
      admissibility: "gm",
      scopeMode: "world",
    },
    summary: {
      nodeCount: 1,
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

function envelope(
  overrides: Partial<ManagedWorldGraphProjectionResponse> = {},
): ManagedWorldGraphProjectionResponse {
  return {
    schema: "dmb_managed_world_graph_projection_v1",
    managedWorldId: "elderwyld",
    nativeWorldId: "eldyrwild",
    bindingVersion: 1,
    projection: projection(),
    ...overrides,
  };
}

describe("verifyManagedWorldGraphProjectionResponse", () => {
  it("checks the managed owner and native snapshot while preserving the snapshot", () => {
    const response = envelope();
    expect(verifyManagedWorldGraphProjectionResponse({
      managedWorldId: "elderwyld",
      request,
      response,
      revisionKind: "head",
    })).toBeNull();
    expect(response.projection.snapshot.worldId).toBe("eldyrwild");
  });

  it("rejects a response for another managed World", () => {
    expect(verifyManagedWorldGraphProjectionResponse({
      managedWorldId: "elderwyld",
      request,
      response: envelope({ managedWorldId: "other-world" }),
      revisionKind: "head",
    })).toMatch(/Projection owner other-world does not match selected World elderwyld/);
  });

  it("rejects a snapshot that differs from the envelope native identity", () => {
    expect(verifyManagedWorldGraphProjectionResponse({
      managedWorldId: "elderwyld",
      request,
      response: envelope({ projection: projection("other-native-world") }),
      revisionKind: "head",
    })).toMatch(/Native projection world other-native-world does not match envelope world eldyrwild/);
  });

  it("rejects missing binding provenance and retains normal projection checks", () => {
    expect(verifyManagedWorldGraphProjectionResponse({
      managedWorldId: "elderwyld",
      request,
      response: envelope({ bindingVersion: 0 }),
      revisionKind: "head",
    })).toMatch(/missing valid native binding provenance/);
    expect(verifyManagedWorldGraphProjectionResponse({
      managedWorldId: "elderwyld",
      request,
      response: envelope({ projection: projection("eldyrwild") }),
      revisionKind: "pinned",
      pinnedRevisionId: "rev:wrong",
    })).toMatch(/Pinned revision rev:wrong does not match loaded revision rev:head/);
  });
});
