import type { SurfaceInteractionIdentity, SurfaceInteractionWorkObjectIdentity } from "../surfaceInteraction/types";
import { buildSurfaceInteractionIdentity } from "../surfaceInteraction/surfaceIdentity";
import {
  PLAN_LOCAL_DRAFT_WORK_KIND,
  createOpaqueLocalDraftId,
  formatPlanLocalDraftId,
} from "./planBlankAuthoringState";

let localDraftSequence = 0;

export function createWorldPlanLocalDraftId(worldId: string): string {
  return formatPlanLocalDraftId(`${worldId}:${createOpaqueLocalDraftId()}:${++localDraftSequence}`);
}

export function worldPlanWorkObject(input: {
  worldId: string;
  documentId: string | null;
  localDraftId: string | null;
}): SurfaceInteractionWorkObjectIdentity {
  if (input.documentId) return { kind: "document", id: input.documentId };
  if (!input.localDraftId || !input.localDraftId.startsWith(`local-plan:${input.worldId}:`)) {
    throw new Error("World Plan local draft identity is unavailable or belongs to another World.");
  }
  return { kind: PLAN_LOCAL_DRAFT_WORK_KIND, id: input.localDraftId };
}

export function buildWorldPlanSurfaceIdentity(input: {
  worldId: string;
  documentId: string | null;
  localDraftId: string | null;
}): SurfaceInteractionIdentity {
  const workObject = worldPlanWorkObject(input);
  return buildSurfaceInteractionIdentity({
    surfaceId: "plan",
    instanceParts: ["world-plan", input.worldId, workObject.kind, workObject.id],
  });
}
