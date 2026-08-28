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
  /** Durable workspace document id when admitted. */
  documentId?: string | null;
  /** Local blank draft id for instance key when no durable document is admitted. */
  localDraftId?: string | null;
  campaignId: string;
  liveSession: number;
  memorySession: number | null;
}): ProjectionSurfaceIdentity {
  const instanceDocumentKey = input.documentId ?? input.localDraftId ?? "__no_document__";
  return {
    surfaceId: "plan",
    instanceKey: encodeInstanceParts([
      "plan",
      instanceDocumentKey,
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
 * A publication enables projections only when:
 * - identity.surfaceId agrees with config.id;
 * - tools are present;
 * - required render context exists.
 *
 * Tools without context, empty tools, or contradictory identity/config modes
 * all yield disabled. An invalid publication may still supersede the previous
 * surface identity so stale content cannot remain.
 */
export function isProjectionSurfaceEnabled(publication: ProjectionSurfacePublication): boolean {
  const { identity, config } = publication;
  if (identity.surfaceId !== config.id) return false;
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
