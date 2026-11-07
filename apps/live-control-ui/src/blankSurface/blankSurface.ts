import { buildSurfaceInteractionIdentity } from "../surfaceInteraction/surfaceIdentity";
import type { SurfaceInteractionPublication } from "../surfaceInteraction/types";

/** An inert, nonauthoring Surface. Domain capabilities remain with their owners. */
export interface BlankSurfaceDescriptor {
  surfaceId: string;
  label: string;
  ambientSummary: string;
}

export const LANDING_SURFACE: BlankSurfaceDescriptor = {
  surfaceId: "index",
  label: "Buddy Surface",
  ambientSummary: "Blank Surface · no active work. Open a surface from navigation to create or resume work.",
};

export function blankSurfacePublication(descriptor: BlankSurfaceDescriptor): SurfaceInteractionPublication {
  return {
    surfaceId: descriptor.surfaceId,
    label: descriptor.label,
    identity: buildSurfaceInteractionIdentity({
      surfaceId: descriptor.surfaceId,
      instanceParts: [descriptor.surfaceId],
    }),
    canvas: null,
    agentContext: {
      label: descriptor.label,
      campaignId: null,
      documentId: null,
      sessionNumber: null,
      ambientSummary: descriptor.ambientSummary,
      pointers: [],
    },
    tools: [],
    editCommands: [],
    projections: [],
    projectionBindings: [],
  };
}
