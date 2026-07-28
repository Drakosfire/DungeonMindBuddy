import type { SurfaceConfig, SurfaceMode } from "../planSurface/types";

export interface ProjectionSurfaceIdentity {
  surfaceId: string;
  /** Opaque exact instance key — structured tuple encoding, never labels. */
  instanceKey: string;
}

export interface ProjectionSurfacePublication {
  identity: ProjectionSurfaceIdentity;
  config: SurfaceConfig;
}

export interface ValidatedProjectionSurface {
  publication: ProjectionSurfacePublication;
  /** True only when tools are present and required render context exists. */
  projectionsEnabled: boolean;
}

function encodeInstanceParts(parts: ReadonlyArray<string | number | null | undefined>): string {
  // JSON preserves tuple boundaries and distinguishes null from empty strings,
  // so uncontrolled surface-owned values cannot collide in the lease key.
  return JSON.stringify(parts);
}

export function buildPlanSurfaceIdentity(input: {
  documentId: string;
  campaignId: string;
  liveSession: number;
  memorySession: number | null;
}): ProjectionSurfaceIdentity {
  return {
    surfaceId: "plan",
    instanceKey: encodeInstanceParts([
      "plan",
      input.documentId,
      input.campaignId,
      input.liveSession,
      input.memorySession,
    ]),
  };
}

export function buildIngestSurfaceIdentity(input: {
  campaignId: string;
  liveSession: number;
  ingestSession: number;
}): ProjectionSurfaceIdentity {
  return {
    surfaceId: "ingest",
    instanceKey: encodeInstanceParts([
      "ingest",
      input.campaignId,
      input.liveSession,
      input.ingestSession,
    ]),
  };
}

export function buildBuildSurfaceIdentity(input: {
  documentId: string | null;
}): ProjectionSurfaceIdentity {
  return {
    surfaceId: "build",
    instanceKey: encodeInstanceParts(["build", input.documentId ?? "__new_source__"]),
  };
}

export function sameProjectionSurfaceIdentity(
  left: ProjectionSurfaceIdentity | null | undefined,
  right: ProjectionSurfaceIdentity | null | undefined,
): boolean {
  if (!left || !right) return false;
  return left.surfaceId === right.surfaceId && left.instanceKey === right.instanceKey;
}

/**
 * A publication with tools but no render context is invalid for opening
 * projections, yet still supersedes the previous surface identity.
 * Build empty-tools publications are valid and intentionally inactive.
 */
export function isProjectionSurfaceEnabled(publication: ProjectionSurfacePublication): boolean {
  const { config } = publication;
  if (config.tools.length === 0) return false;
  return config.context !== null && config.context !== undefined;
}

export function validateProjectionSurfacePublication(
  publication: ProjectionSurfacePublication,
): ValidatedProjectionSurface {
  return {
    publication,
    projectionsEnabled: isProjectionSurfaceEnabled(publication),
  };
}

export function createBuildSurfacePublication(input: {
  documentId: string | null;
  label?: string;
}): ProjectionSurfacePublication {
  return {
    identity: buildBuildSurfaceIdentity({ documentId: input.documentId }),
    config: {
      id: "build" satisfies SurfaceMode,
      label: input.label ?? "Build",
      context: null,
      tools: [],
      canvas: { documentId: input.documentId },
      theme: {},
    },
  };
}
