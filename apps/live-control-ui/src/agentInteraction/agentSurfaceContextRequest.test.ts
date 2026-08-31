import { describe, expect, it } from "vitest";

import {
  buildAgentSurfaceContextRequest,
  buildPlanAgentSurfaceContextRequest,
  AGENT_SURFACE_CONTEXT_REQUEST_SCHEMA,
} from "./agentSurfaceContextRequest";
import type { SurfaceInteractionPublication } from "../surfaceInteraction/types";

function publication(
  overrides: Partial<SurfaceInteractionPublication> & {
    agentContext?: SurfaceInteractionPublication["agentContext"];
  } = {},
): SurfaceInteractionPublication {
  const {
    agentContext = {
      label: "C2 Session 27 Prep",
      campaignId: "longmont-c2",
      documentId: "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
      sessionNumber: 27,
      ambientSummary: "Plan prep for Longmont C2 — must never ship",
      pointers: [],
    },
    ...rest
  } = overrides;
  return {
    surfaceId: "plan",
    label: "Plan",
    identity: { surfaceId: "plan", instanceKey: "plan:aaaaaaaa" },
    canvas: null,
    agentContext,
    tools: [],
    editCommands: [],
    projections: [],
    projectionBindings: [],
    ...rest,
  };
}

describe("buildAgentSurfaceContextRequest", () => {
  it("copies identity-only fields and omits label/ambientSummary", () => {
    const request = buildAgentSurfaceContextRequest(publication());
    expect(request).toEqual({
      schema: AGENT_SURFACE_CONTEXT_REQUEST_SCHEMA,
      surface_id: "plan",
      campaign_id: "longmont-c2",
      document_id: "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
      session_number: 27,
      pointers: [],
    });
    expect(JSON.stringify(request)).not.toContain("must never ship");
    expect(JSON.stringify(request)).not.toContain("C2 Session 27 Prep");
  });

  it("returns null when publication or agentContext is absent", () => {
    expect(buildAgentSurfaceContextRequest(null)).toBeNull();
    expect(buildAgentSurfaceContextRequest(publication({ agentContext: null }))).toBeNull();
  });

  it("nulls local-plan document ids instead of synthesizing durable identity", () => {
    const request = buildAgentSurfaceContextRequest(
      publication({
        agentContext: {
          label: "Blank",
          campaignId: "longmont-c2",
          documentId: "local-plan:draft-1",
          sessionNumber: 22,
          ambientSummary: null,
          pointers: [],
        },
      }),
    );
    expect(request?.document_id).toBeNull();
    expect(request?.surface_id).toBe("plan");
  });

  it("preserves non-plan surface_id without rewriting to plan", () => {
    const request = buildAgentSurfaceContextRequest(
      publication({
        surfaceId: "play",
        identity: { surfaceId: "play", instanceKey: "play:1" },
      }),
    );
    expect(request?.surface_id).toBe("play");
  });

  it("copies bounded pointers without inventing values", () => {
    const request = buildAgentSurfaceContextRequest(
      publication({
        agentContext: {
          label: "x",
          campaignId: "longmont-c2",
          documentId: null,
          sessionNumber: 22,
          ambientSummary: null,
          pointers: [{ kind: "selection", value: "beat-1" }],
        },
      }),
    );
    expect(request?.pointers).toEqual([{ kind: "selection", value: "beat-1" }]);
  });
});

describe("buildPlanAgentSurfaceContextRequest", () => {
  it("returns Plan identity snapshots", () => {
    expect(buildPlanAgentSurfaceContextRequest(publication())?.surface_id).toBe("plan");
  });

  it("fails closed to absence for a foreign surface lease", () => {
    expect(
      buildPlanAgentSurfaceContextRequest(
        publication({
          surfaceId: "play",
          identity: { surfaceId: "play", instanceKey: "play:1" },
        }),
      ),
    ).toBeNull();
  });
});
