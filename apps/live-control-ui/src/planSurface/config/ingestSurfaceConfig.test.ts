import { describe, expect, it } from "vitest";

import type { PlanContextDescriptor } from "../types";
import { createIngestSurfaceConfig } from "./ingestSurfaceConfig";

const context: PlanContextDescriptor = {
  campaignId: "longmont-c2",
  liveSession: 24,
  prepSession: 25,
  ingestSession: 23,
  headerLabel: "Ingest",
};

describe("ingestSurfaceConfig", () => {
  it("creates ingest surface config with recap ingest first in the toolbox", () => {
    const config = createIngestSurfaceConfig(context);

    expect(config.id).toBe("ingest");
    expect(config.tools.map((tool) => tool.id)).toEqual([
      "ingest-recap",
      "graph-review-diagnostics",
      "graph-review-author-draft",
    ]);
    expect(config.tools.map((tool) => tool.label)).toEqual([
      "Ingest Recap",
      "Diagnostics",
      "Author Draft",
    ]);
    expect(config.canvas.documentId).toBe("ingest-surface");
  });
});
