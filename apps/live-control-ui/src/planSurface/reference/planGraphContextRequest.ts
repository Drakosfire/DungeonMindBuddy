import type { WorldGraphProjectionRequest } from "../../api/types";
import type { PlanSessionDescriptor } from "../types";

export interface PlanWorldGraphContext {
  worldId: string;
  campaignId: string;
  focus:
    | { kind: "none"; sessionId: null }
    | { kind: "session"; sessionId: string };
}

const WORLD_ID_BY_CAMPAIGN: Record<string, string> = {
  "longmont-c2": "eldyrwild",
};

export function getPlanWorldGraphContext(
  sessionDescriptor: PlanSessionDescriptor | null | undefined,
): PlanWorldGraphContext | null {
  if (!sessionDescriptor) return null;

  const worldId = WORLD_ID_BY_CAMPAIGN[sessionDescriptor.campaignId];
  if (!worldId) return null;

  return {
    worldId,
    campaignId: sessionDescriptor.campaignId,
    focus: {
      kind: "session",
      sessionId: `session-${sessionDescriptor.memorySession}`,
    },
  };
}

export function buildPlanWorldGraphProjectionRequest(
  context: PlanWorldGraphContext,
): WorldGraphProjectionRequest {
  return {
    schema: "dmb_world_graph_projection_request_v1",
    worldId: context.worldId,
    campaignId: context.campaignId,
    focus: context.focus,
    admissibility: "gm",
  };
}
