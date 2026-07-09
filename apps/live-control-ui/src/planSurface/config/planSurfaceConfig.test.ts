import { describe, expect, it } from "vitest";

import { mockPlanView } from "../../test/fixtures";
import { buildPlanContextFromPlanView, createPlanSurfaceConfig } from "./planSurfaceConfig";

describe("planSurfaceConfig", () => {
  it("builds plan context from plan view projection", () => {
    const context = buildPlanContextFromPlanView(mockPlanView);
    expect(context.campaignId).toBe("longmont-c2");
    expect(context.liveSession).toBe(22);
    expect(context.prepSession).toBe(23);
    expect(context.ingestSession).toBe(21);
    expect(context.headerLabel).toContain("Plan · Longmont C2");
    expect(context.headerLabel).toContain("preparing Session 23");
  });

  it("creates plan surface config with one session-prep board", () => {
    const config = createPlanSurfaceConfig(mockPlanView);
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
    expect(config.sessionDescriptor.planningDocument.targetRelpath).toContain("Session Prep/Session 23 Prep.md");
  });
});
