import { describe, expect, it } from "vitest";

import type { PlanViewProjection } from "../../api/types";
import {
  buildIngestContextFromPlanView,
  createIngestSurfaceConfig,
} from "./ingestSurfaceConfig";

const planView = {
  campaign_id: "longmont-c2",
  session: 24,
} as PlanViewProjection;

describe("buildIngestContextFromPlanView", () => {
  it("builds context from plan view without a planning document", () => {
    const context = buildIngestContextFromPlanView(planView, "");
    expect(context).toEqual({
      campaignId: "longmont-c2",
      liveSession: 24,
      ingestSession: 24,
      headerLabel: "Memory Ingest",
    });
  });

  it("honors ?session= for ingestSession", () => {
    const context = buildIngestContextFromPlanView(planView, "?session=21");
    expect(context.ingestSession).toBe(21);
    expect(context.liveSession).toBe(24);
  });
});

describe("createIngestSurfaceConfig", () => {
  it("keeps ingest tool ids", () => {
    const config = createIngestSurfaceConfig(
      buildIngestContextFromPlanView(planView, ""),
    );
    expect(config.id).toBe("ingest");
    expect(config.tools.map((tool) => tool.id)).toEqual([
      "ingest-recap",
      "graph-review-diagnostics",
    ]);
  });

  it("attaches a session descriptor for shared World Graph reference resolution", () => {
    const config = createIngestSurfaceConfig(
      buildIngestContextFromPlanView(planView, "?session=7"),
    );
    expect(config.sessionDescriptor?.campaignId).toBe("longmont-c2");
    expect(config.sessionDescriptor?.memorySession).toBe(7);
    expect(config.sessionDescriptor?.planningDocument.title).toBe("Memory Ingest");
  });
});
