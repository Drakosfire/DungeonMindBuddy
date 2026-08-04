import { describe, expect, it } from "vitest";

import type { GraphReferenceProjectionBinding, GraphReferenceResolution } from "./types";
import {
  GRAPH_REFERENCE_BINDING_ID,
  GRAPH_REFERENCE_PROJECTION_STATE_BINDING_ID,
  GRAPH_REFERENCE_RESOLUTION_BINDING_ID,
  readGraphReferenceBinding,
  readGraphReferenceProjectionStateBinding,
  readGraphReferenceResolutionBinding,
} from "./projectionBindings";

const sampleResolution: GraphReferenceResolution = {
  kind: "unresolved",
  locator: "dmb-node:missing",
  reference: null,
  projectionState: "unavailable",
  message: "Not found.",
};

const sampleBinding: GraphReferenceProjectionBinding = {
  resolverState: "ready",
  resolveRelationship: async () => sampleResolution,
  openResolvedReference: () => undefined,
  openTool: () => undefined,
};

describe("graphReference projectionBindings", () => {
  it("exports stable neutral binding IDs", () => {
    expect(GRAPH_REFERENCE_RESOLUTION_BINDING_ID).toBe("graph-reference-resolution");
    expect(GRAPH_REFERENCE_PROJECTION_STATE_BINDING_ID).toBe("graph-reference-projection-state");
    expect(GRAPH_REFERENCE_BINDING_ID).toBe("graph-reference-binding");
  });

  it("reads required graph reference resolution binding", () => {
    const bindings = {
      [GRAPH_REFERENCE_RESOLUTION_BINDING_ID]: sampleResolution,
    };
    expect(readGraphReferenceResolutionBinding(bindings)).toBe(sampleResolution);
  });

  it("throws when required graph reference resolution binding is missing", () => {
    expect(() => readGraphReferenceResolutionBinding({})).toThrow(
      "Missing required projection binding: graph-reference-resolution",
    );
  });

  it("throws when required graph reference resolution binding is null", () => {
    expect(() =>
      readGraphReferenceResolutionBinding({
        [GRAPH_REFERENCE_RESOLUTION_BINDING_ID]: null,
      }),
    ).toThrow("Required projection binding is null: graph-reference-resolution");
  });

  it("returns undefined when optional projection state binding is absent", () => {
    expect(readGraphReferenceProjectionStateBinding({})).toBeUndefined();
  });

  it("reads optional projection state binding including null", () => {
    const bindings = {
      [GRAPH_REFERENCE_PROJECTION_STATE_BINDING_ID]: null,
    };
    expect(readGraphReferenceProjectionStateBinding(bindings)).toBeNull();

    const readyBindings = {
      [GRAPH_REFERENCE_PROJECTION_STATE_BINDING_ID]: "ready" as const,
    };
    expect(readGraphReferenceProjectionStateBinding(readyBindings)).toBe("ready");
  });

  it("returns undefined when optional graph reference binding is absent", () => {
    expect(readGraphReferenceBinding({})).toBeUndefined();
  });

  it("reads optional graph reference binding including null", () => {
    const bindings = {
      [GRAPH_REFERENCE_BINDING_ID]: null,
    };
    expect(readGraphReferenceBinding(bindings)).toBeNull();

    const presentBindings = {
      [GRAPH_REFERENCE_BINDING_ID]: sampleBinding,
    };
    expect(readGraphReferenceBinding(presentBindings)).toBe(sampleBinding);
  });
});
