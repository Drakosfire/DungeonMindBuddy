import { describe, expect, it } from "vitest";

import { agentSurfaceLabel, surfaceContextSubtitle } from "./surfaceContextDisplay";

describe("surfaceContextDisplay", () => {
  it("maps known surface ids to product labels", () => {
    expect(agentSurfaceLabel("plan")).toBe("Plan");
    expect(agentSurfaceLabel("ingest")).toBe("Ingest");
    expect(agentSurfaceLabel("build")).toBe("Build");
    expect(agentSurfaceLabel("index")).toBe("Index");
    expect(agentSurfaceLabel(null)).toBeNull();
  });

  it("prefixes ambient summary with the surface label", () => {
    expect(
      surfaceContextSubtitle({
        surfaceId: "ingest",
        label: "Memory Ingest",
        campaignId: "longmont-c2",
        documentId: null,
        sessionNumber: 22,
        ambientSummary: "Graph Review · longmont-c2 · session 22",
        sourceEnvelope: null,
        updatedAt: "2026-07-29T00:00:00Z",
      }),
    ).toBe("Ingest · Graph Review · longmont-c2 · session 22");
  });
});
