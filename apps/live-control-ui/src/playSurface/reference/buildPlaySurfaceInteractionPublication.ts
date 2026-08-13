import { GRAPH_REFERENCE_RESOLUTION_BINDING_ID } from "../../graphReference/projectionBindings";
import type { GraphReferenceResolution } from "../../graphReference/types";
import { GRAPH_REFERENCE_PROJECTION_ID } from "../../surfaceInteraction/projection/projectionCatalog";
import { buildSurfaceInteractionIdentity } from "../../surfaceInteraction/surfaceIdentity";
import type { SurfaceInteractionPublication } from "../../surfaceInteraction/types";
import { validateSurfaceInteractionPublication } from "../../surfaceInteraction/publication";

const PLAY_SURFACE_ID = "play" as const;
const PLAY_SURFACE_LABEL = "Play" as const;

const EMPTY_GRAPH_REFERENCE_RESOLUTION: GraphReferenceResolution = {
  kind: "unresolved",
  locator: "",
  reference: null,
  projectionState: null,
  message: "No object selected.",
};

export function buildPlaySurfaceInteractionPublication(panelId: string): SurfaceInteractionPublication {
  return {
    surfaceId: PLAY_SURFACE_ID,
    label: PLAY_SURFACE_LABEL,
    identity: buildSurfaceInteractionIdentity({
      surfaceId: PLAY_SURFACE_ID,
      instanceParts: [PLAY_SURFACE_ID, panelId],
    }),
    canvas: null,
    agentContext: null,
    tools: [],
    editCommands: [],
    projections: [
      {
        id: GRAPH_REFERENCE_PROJECTION_ID,
        kind: "content",
        preferredSize: "wide",
        bindingIds: [GRAPH_REFERENCE_RESOLUTION_BINDING_ID],
      },
    ],
    projectionBindings: [
      {
        id: GRAPH_REFERENCE_RESOLUTION_BINDING_ID,
        value: EMPTY_GRAPH_REFERENCE_RESOLUTION,
      },
    ],
  };
}

export function assertValidPlaySurfaceInteractionPublication(
  publication: SurfaceInteractionPublication,
): void {
  const result = validateSurfaceInteractionPublication(publication);
  if (!result.valid) {
    throw new Error(
      `Play surface interaction publication failed validation: ${result.issues
        .map((issue) => issue.code)
        .join(", ")}`,
    );
  }
}

assertValidPlaySurfaceInteractionPublication(buildPlaySurfaceInteractionPublication("beats"));
