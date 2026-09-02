import { describe, expect, it } from "vitest";

import { LiveApiError } from "../api/liveApi";
import type { WorldGraphProjection, WorldGraphProjectionRequest } from "../api/types";
import {
  WORLD_GRAPH_LENS_INFORMATION_KIND,
  WORLD_GRAPH_LENS_PROVIDER_ID,
  mapWorldGraphLensObservation,
  worldGraphLensInformationDescriptor,
} from "./worldGraphLensSurfaceInformation";

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
  overrides: Partial<WorldGraphProjection> = {},
  snapshotOverrides: Partial<WorldGraphProjection["snapshot"]> = {},
): WorldGraphProjection {
  return {
    schema: "dmb_world_graph_projection_v1",
    snapshot: {
      worldId: "eldyrwild",
      campaignId: "longmont-c2",
      revisionId: "rev:abc",
      headRevisionId: "rev:abc",
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
    ...overrides,
  };
}

const glowkindleNode = {
  nodeId: "npc:glowkindle",
  label: "Glowkindle",
  kind: "npc",
  role: "merchant",
  aliases: ["Glow"],
  sourceDomains: ["recap"],
  evidenceBadges: [],
  adjacency: [],
  suggestedExpansions: [],
  anchoredToFocusSession: true,
  summary: "A friendly merchant.",
  campaignScope: "longmont-c2",
  evidenceRefIds: [],
  sourceArtifactIds: [],
};

describe("worldGraphLensInformationDescriptor", () => {
  it("names dungeonmind authority, exact world subject, and request scope without revision", () => {
    const descriptor = worldGraphLensInformationDescriptor(request());
    expect(descriptor.authority).toBe("dungeonmind");
    expect(descriptor.providerId).toBe(WORLD_GRAPH_LENS_PROVIDER_ID);
    expect(descriptor.informationKind).toBe(WORLD_GRAPH_LENS_INFORMATION_KIND);
    expect(descriptor.subject).toEqual({ kind: "world", id: "eldyrwild" });
    expect(descriptor.scope).toEqual([
      { kind: "campaign", id: "longmont-c2" },
      { kind: "scope_mode", id: "campaign" },
      { kind: "admissibility", id: "gm" },
    ]);
    expect(descriptor.channelId.startsWith("world-graph-lens:")).toBe(true);
    expect(JSON.stringify(descriptor)).not.toContain("rev:abc");
  });

  it("preserves exact session focus campaign and session identity", () => {
    const descriptor = worldGraphLensInformationDescriptor(
      request({
        focus: {
          kind: "session",
          sessionId: "session-23",
          campaignId: "longmont-c1",
        },
      }),
    );
    expect(descriptor.scope).toEqual(
      expect.arrayContaining([
        { kind: "focus_campaign", id: "longmont-c1" },
        { kind: "focus_session", id: "session-23" },
      ]),
    );
  });
});

describe("mapWorldGraphLensObservation", () => {
  it("maps a verified non-empty projection to READY with an exact revision", () => {
    const response = projection({ nodes: [glowkindleNode] });
    const state = mapWorldGraphLensObservation({ request: request(), response });
    expect(state.status).toBe("ready");
    if (state.status !== "ready") return;
    expect(state.value).toBe(response);
    expect(state.revision).toEqual({ kind: "exact", value: "rev:abc" });
    expect(state.provenance).toEqual([{ kind: "world_graph_revision", id: "rev:abc" }]);
    expect(state.inspectionTargets).toEqual([
      { kind: "world", id: "eldyrwild" },
      { kind: "campaign", id: "longmont-c2" },
      { kind: "world_graph_revision", id: "rev:abc" },
    ]);
  });

  it("maps a verified zero-node projection to EMPTY at the exact revision", () => {
    const state = mapWorldGraphLensObservation({ request: request(), response: projection() });
    expect(state.status).toBe("empty");
    if (state.status !== "empty") return;
    expect(state.revision).toEqual({ kind: "exact", value: "rev:abc" });
    expect("value" in state).toBe(false);
  });

  it("maps transport and unavailable failures to UNAVAILABLE", () => {
    const unavailable = mapWorldGraphLensObservation({
      request: request(),
      error: new LiveApiError("World Graph unavailable", 404, { code: "world_graph_unavailable" }),
    });
    expect(unavailable.status).toBe("unavailable");
    if (unavailable.status === "unavailable") {
      expect(unavailable.reason).toMatch(/world_graph_unavailable/);
    }

    const transport = mapWorldGraphLensObservation({
      request: request(),
      error: new Error("connection refused"),
    });
    expect(transport.status).toBe("unavailable");
    if (transport.status === "unavailable") {
      expect(transport.reason).toMatch(/connection refused/);
    }
  });

  it("maps verification mismatch to INTEGRITY_ERROR, not EMPTY or UNAVAILABLE", () => {
    const state = mapWorldGraphLensObservation({
      request: request(),
      response: projection({}, { campaignId: "longmont-c1" }),
    });
    expect(state.status).toBe("integrity_error");
    if (state.status !== "integrity_error") return;
    expect(state.reason).toMatch(/campaign/);
    expect("value" in state).toBe(false);
  });

  it("maps a verified projection with a blank revision to INTEGRITY_ERROR", () => {
    const state = mapWorldGraphLensObservation({
      request: request(),
      response: projection({ nodes: [glowkindleNode] }, { revisionId: "  ", headRevisionId: "  " }),
    });
    expect(state.status).toBe("integrity_error");
    if (state.status === "integrity_error") {
      expect(state.reason).toMatch(/exact DungeonMind revision/);
    }
  });

  it("never emits unrevisioned or stale", () => {
    const ready = mapWorldGraphLensObservation({
      request: request(),
      response: projection({ nodes: [glowkindleNode] }),
    });
    const empty = mapWorldGraphLensObservation({ request: request(), response: projection() });
    const unavailable = mapWorldGraphLensObservation({
      request: request(),
      error: new Error("down"),
    });
    const integrity = mapWorldGraphLensObservation({
      request: request(),
      response: projection({}, { campaignId: "wrong" }),
    });
    for (const state of [ready, empty, unavailable, integrity]) {
      expect(state.status).not.toBe("stale");
      if ("revision" in state) {
        expect(state.revision.kind).toBe("exact");
      }
    }
  });
});
