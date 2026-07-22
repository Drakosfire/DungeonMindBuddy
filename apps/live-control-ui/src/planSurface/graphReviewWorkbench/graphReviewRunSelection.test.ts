import { describe, expect, it } from "vitest";

import {
  assertExactRunHandoff,
  parseGraphReviewRunHandoff,
} from "./graphReviewRunSelection";

describe("graphReviewRunSelection", () => {
  it("parses exact handoff identifiers and never invents latest", () => {
    const handoff = parseGraphReviewRunHandoff(
      "?extractionRunId=run-1&sourceArtifactId=artifact:wb:1&documentId=doc-1&revision=3",
    );
    expect(handoff).toEqual({
      extractionRunId: "run-1",
      sourceArtifactId: "artifact:wb:1",
      documentId: "doc-1",
      revision: 3,
    });
    expect(assertExactRunHandoff(handoff!)).toEqual([]);
  });

  it("returns null when no exact run is present", () => {
    expect(parseGraphReviewRunHandoff("?campaign=longmont-c2")).toBeNull();
  });

  it("rejects latest-run style identifiers", () => {
    const handoff = parseGraphReviewRunHandoff("?extractionRunId=latest");
    expect(assertExactRunHandoff(handoff!)).toContain("latest-run handoff is forbidden");
  });
});
