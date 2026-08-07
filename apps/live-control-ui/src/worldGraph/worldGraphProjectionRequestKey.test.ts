import { describe, expect, it } from "vitest";

import type { WorldGraphProjectionRequest } from "../api/types";
import {
  worldGraphProjectionRequestKey,
  worldGraphProjectionRequestsMatch,
} from "./worldGraphProjectionRequestKey";

const baseRequest: WorldGraphProjectionRequest = {
  schema: "dmb_world_graph_projection_request_v1",
  worldId: "eldyrwild",
  campaignId: "longmont-c2",
  scopeMode: "world",
  focus: { kind: "none", sessionId: null },
  admissibility: "gm",
  revisionPin: null,
};

describe("worldGraphProjectionRequestKey", () => {
  it("includes queryText in the exact identity", () => {
    const withoutQuery = worldGraphProjectionRequestKey(baseRequest);
    const withQuery = worldGraphProjectionRequestKey({
      ...baseRequest,
      queryText: "glowkindle",
    });
    expect(withoutQuery).not.toEqual(withQuery);
    expect(withQuery).toContain("glowkindle");
  });

  it("treats omitted and null queryText as equivalent", () => {
    expect(
      worldGraphProjectionRequestsMatch(baseRequest, {
        ...baseRequest,
        queryText: null,
      }),
    ).toBe(true);
  });
});
