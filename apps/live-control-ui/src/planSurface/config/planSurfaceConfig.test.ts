import { describe, expect, it } from "vitest";

import { mockPlanView } from "../../test/fixtures";
import {
  buildPlanContextFromPlanView,
  createPlanSurfaceConfig,
  planLocationOverridesFromSearch,
} from "./planSurfaceConfig";

describe("planSurfaceConfig", () => {
  it("builds plan context from plan view without inventing a stale memory session", () => {
    const context = buildPlanContextFromPlanView(mockPlanView);
    expect(context.campaignId).toBe("longmont-c2");
    expect(context.liveSession).toBe(22);
    expect(context.prepSession).toBe(23);
    expect(context.ingestSession).toBe(22);
    expect(context.headerLabel).toContain("Plan · Longmont C2");
    expect(context.headerLabel).toContain("preparing Session 23");
  });

  it("parses bare and session-prefixed URL overrides", () => {
    expect(planLocationOverridesFromSearch("?session=24&prepSession=25")).toEqual({
      memorySession: 24,
      prepSession: 25,
    });
    expect(planLocationOverridesFromSearch("?session=session-23")).toEqual({
      memorySession: 23,
      prepSession: null,
    });
    expect(planLocationOverridesFromSearch("")).toEqual({
      memorySession: null,
      prepSession: null,
    });
  });

  it("creates plan surface config with world-union memory focus by default", () => {
    const config = createPlanSurfaceConfig(mockPlanView, "");
    expect(config.id).toBe("plan");
    expect(config.tools.map((tool) => tool.id)).toEqual([
      "recap",
      "party-registry",
      "statblock",
    ]);
    expect(config.theme.themeId).toBe("mireward-runbook");
    expect(config.theme.tokens?.["--accent"]).toBe("#7aa2f7");
    expect(config.canvas.documentId).toBe("longmont-c2-session-23-prep");
    expect(config.sessionDescriptor.planningDocument.title).toBe("C2 Session 23 Prep");
    expect(config.sessionDescriptor.memorySession).toBeNull();
    expect(config.sessionDescriptor.planningDocument.targetRelpath).toContain("Session Prep/Session 23 Prep.md");
  });

  it("applies URL session overrides to the surface config", () => {
    const config = createPlanSurfaceConfig(
      mockPlanView,
      "?campaign=longmont-c2&session=24&prepSession=25&dogfood=1",
    );
    expect(config.sessionDescriptor.memorySession).toBe(24);
    expect(config.sessionDescriptor.prepSession).toBe(25);
    expect(config.context.ingestSession).toBe(24);
    expect(config.canvas.documentId).toBe("longmont-c2-session-25-prep");
  });
});
