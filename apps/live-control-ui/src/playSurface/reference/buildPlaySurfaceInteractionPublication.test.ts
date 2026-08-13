import { describe, expect, it } from "vitest";

import { GRAPH_REFERENCE_RESOLUTION_BINDING_ID } from "../../graphReference/projectionBindings";
import { GRAPH_REFERENCE_PROJECTION_ID } from "../../surfaceInteraction/projection/projectionCatalog";
import { validateSurfaceInteractionPublication } from "../../surfaceInteraction/publication";
import { buildPlaySurfaceInteractionPublication } from "./buildPlaySurfaceInteractionPublication";

describe("buildPlaySurfaceInteractionPublication", () => {
  it("declares exactly one graph-reference content projection", () => {
    const publication = buildPlaySurfaceInteractionPublication("beats");
    const result = validateSurfaceInteractionPublication(publication);
    expect(result.valid).toBe(true);
    expect(publication.surfaceId).toBe("play");
    expect(publication.identity.surfaceId).toBe("play");
    const graphRefs = publication.projections.filter(
      (entry) => entry.id === GRAPH_REFERENCE_PROJECTION_ID && entry.kind === "content",
    );
    expect(graphRefs).toHaveLength(1);
    expect(graphRefs[0]?.bindingIds).toEqual([GRAPH_REFERENCE_RESOLUTION_BINDING_ID]);
  });
});
