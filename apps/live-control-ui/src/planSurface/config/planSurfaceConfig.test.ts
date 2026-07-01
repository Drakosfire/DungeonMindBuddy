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
  });

  it("creates plan surface config with tools and spike theme", () => {
    const config = createPlanSurfaceConfig(mockPlanView);
    expect(config.id).toBe("plan");
    expect(config.tools.map((tool) => tool.id)).toEqual([
      "ingest-recap",
      "recap",
      "graph-preview",
      "graph-gold-review",
      "manual-review",
      "party-registry",
      "statblock",
    ]);
    expect(config.theme.themeId).toBe("mireward-runbook");
    expect(config.theme.tokens?.["--accent"]).toBe("#7aa2f7");
  });
});
