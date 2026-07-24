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
      errors: [],
    });
    expect(assertExactRunHandoff(handoff!)).toEqual([]);
  });

  it("returns null when no exact run is present", () => {
    expect(parseGraphReviewRunHandoff("?campaign=longmont-c2")).toBeNull();
  });

  it("rejects latest-run style identifiers", () => {
    const handoff = parseGraphReviewRunHandoff("?extractionRunId=latest");
    expect(assertExactRunHandoff(handoff!)).toContain(
      'extractionRunId must be an exact identifier, not "latest"',
    );
  });

  it("rejects duplicated identity parameters", () => {
    const handoff = parseGraphReviewRunHandoff(
      "?extractionRunId=run-1&extractionRunId=run-2",
    );
    expect(assertExactRunHandoff(handoff!)).toContain(
      "extractionRunId must appear at most once",
    );
    expect(handoff!.extractionRunId).toBe("");
  });

  it("rejects an empty identity parameter rather than treating it as absent", () => {
    const handoff = parseGraphReviewRunHandoff(
      "?extractionRunId=run-1&sourceArtifactId=",
    );
    expect(assertExactRunHandoff(handoff!)).toContain(
      "sourceArtifactId is present but empty",
    );
  });

  it("rejects malformed and non-positive revisions", () => {
    for (const raw of ["3.5", "-2", "0", "three"]) {
      const handoff = parseGraphReviewRunHandoff(
        `?extractionRunId=run-1&documentId=doc-1&revision=${raw}`,
      );
      expect(assertExactRunHandoff(handoff!)).toContain(
        "revision must be a positive integer",
      );
      expect(handoff!.revision).toBeNull();
    }
  });

  it("rejects a partial workspace lineage claim", () => {
    const handoff = parseGraphReviewRunHandoff("?extractionRunId=run-1&documentId=doc-1");
    expect(assertExactRunHandoff(handoff!)).toContain(
      "documentId and revision must be supplied together",
    );
  });

  it("accepts a recap handoff that claims no workspace lineage", () => {
    const handoff = parseGraphReviewRunHandoff("?extractionRunId=recap-run-1");
    expect(assertExactRunHandoff(handoff!)).toEqual([]);
    expect(handoff!.documentId).toBeNull();
    expect(handoff!.revision).toBeNull();
  });

  it("reports a malformed handoff even when only a foreign param is exact", () => {
    const handoff = parseGraphReviewRunHandoff("?revision=2");
    expect(assertExactRunHandoff(handoff!)).toContain("extractionRunId is required");
  });
});
