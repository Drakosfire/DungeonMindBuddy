import { describe, expect, it } from "vitest";

import { mockPlanView } from "../../test/fixtures";
import {
  createPlanSurfaceConfig,
  planLocationOverridesFromSearch,
} from "./planSurfaceConfig";
import { FIXTURE_DOC_ID, fixturePlanDocumentDescriptor } from "./planSessionDescriptor";

describe("planSurfaceConfig", () => {
  const planningDocument = fixturePlanDocumentDescriptor();

  it("builds plan context without prepSession identity", () => {
    const config = createPlanSurfaceConfig(mockPlanView, planningDocument);
    expect(config.context.liveSession).toBe(22);
    expect(config.context.ingestSession).toBe(22);
    expect(config.context.headerLabel).toContain("C2 Session 23 Prep");
  });

  it("parses memory session overrides from search", () => {
    expect(planLocationOverridesFromSearch("?session=24")).toEqual({
      memorySession: 24,
    });
    expect(planLocationOverridesFromSearch("")).toEqual({
      memorySession: null,
    });
    expect(planLocationOverridesFromSearch("?documentId=abc")).toEqual({
      memorySession: null,
    });
  });

  it("wires canvas documentId from the registry-backed planning document", () => {
    const config = createPlanSurfaceConfig(mockPlanView, planningDocument);
    expect(config.canvas.documentId).toBe(FIXTURE_DOC_ID);
    expect(config.sessionDescriptor.planningDocument.documentId).toBe(FIXTURE_DOC_ID);
  });

  it("honors memory session override in session descriptor", () => {
    const config = createPlanSurfaceConfig(
      mockPlanView,
      planningDocument,
      "?campaign=longmont-c2&session=24&dogfood=1",
    );
    expect(config.sessionDescriptor.memorySession).toBe(24);
    expect(config.canvas.documentId).toBe(FIXTURE_DOC_ID);
  });

  it("preserves explicit null canvas documentId override", () => {
    const config = createPlanSurfaceConfig(mockPlanView, planningDocument, "", {
      documentId: null,
    });
    expect(config.canvas.documentId).toBeNull();
    expect(config.sessionDescriptor.planningDocument.documentId).toBe(FIXTURE_DOC_ID);
  });
});
