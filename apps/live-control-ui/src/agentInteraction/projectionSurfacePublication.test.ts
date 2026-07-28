import { describe, expect, it } from "vitest";

import {
  buildBuildSurfaceIdentity,
  buildIngestSurfaceIdentity,
  buildPlanSurfaceIdentity,
  createBuildSurfacePublication,
  isProjectionSurfaceEnabled,
  sameProjectionSurfaceIdentity,
  validateProjectionSurfacePublication,
} from "./projectionSurfacePublication";

describe("projectionSurfacePublication", () => {
  it("builds exact Plan identity from document/campaign/session fields", () => {
    const identity = buildPlanSurfaceIdentity({
      documentId: "doc-1",
      campaignId: "longmont-c2",
      liveSession: 22,
      memorySession: 21,
    });
    expect(identity.surfaceId).toBe("plan");
    expect(identity.instanceKey).toContain("doc-1");
    expect(identity.instanceKey).toContain("longmont-c2");
    expect(sameProjectionSurfaceIdentity(
      identity,
      buildPlanSurfaceIdentity({
        documentId: "doc-1",
        campaignId: "longmont-c2",
        liveSession: 22,
        memorySession: 21,
      }),
    )).toBe(true);
    expect(sameProjectionSurfaceIdentity(
      identity,
      buildPlanSurfaceIdentity({
        documentId: "doc-2",
        campaignId: "longmont-c2",
        liveSession: 22,
        memorySession: 21,
      }),
    )).toBe(false);
  });

  it("does not treat labels as identity", () => {
    const left = buildIngestSurfaceIdentity({
      campaignId: "longmont-c2",
      liveSession: 22,
      ingestSession: 21,
    });
    const right = buildIngestSurfaceIdentity({
      campaignId: "longmont-c2",
      liveSession: 22,
      ingestSession: 21,
    });
    expect(sameProjectionSurfaceIdentity(left, right)).toBe(true);
    expect(left.instanceKey.includes("Ingest")).toBe(false);
  });

  it("keeps tuple boundaries distinct when identity fields contain delimiters", () => {
    const left = buildBuildSurfaceIdentity({ documentId: "doc\u001f-a" });
    const right = buildBuildSurfaceIdentity({ documentId: "doc-a" });

    expect(sameProjectionSurfaceIdentity(left, right)).toBe(false);
  });

  it("uses an explicit new-source identity for Build without a document", () => {
    const publication = createBuildSurfacePublication({ documentId: null });
    expect(publication.identity).toEqual(buildBuildSurfaceIdentity({ documentId: null }));
    expect(publication.config.context).toBeNull();
    expect(publication.config.tools).toEqual([]);
    expect(isProjectionSurfaceEnabled(publication)).toBe(false);
    expect(validateProjectionSurfacePublication(publication).projectionsEnabled).toBe(false);
  });

  it("disables projections when tools exist without render context", () => {
    const publication = {
      identity: buildBuildSurfaceIdentity({ documentId: "doc-1" }),
      config: {
        id: "build" as const,
        label: "Broken",
        context: null,
        tools: [{ id: "recap", label: "Recap", size: "wide" as const }],
        canvas: { documentId: "doc-1" },
        theme: {},
      },
    };
    expect(isProjectionSurfaceEnabled(publication)).toBe(false);
  });

  it("disables projections when identity.surfaceId and config.id contradict", () => {
    const publication = {
      identity: { surfaceId: "plan", instanceKey: '["plan","doc-1"]' },
      config: {
        id: "ingest" as const,
        label: "Mismatched",
        context: {
          campaignId: "longmont-c2",
          liveSession: 22,
          ingestSession: 21,
          headerLabel: "Ingest",
        },
        tools: [{ id: "ingest-recap", label: "Recap", size: "wide" as const }],
        canvas: { documentId: null },
        theme: {},
      },
    };
    expect(isProjectionSurfaceEnabled(publication)).toBe(false);
    expect(validateProjectionSurfacePublication(publication).projectionsEnabled).toBe(false);
  });
});
