import type { PlanSessionDescriptor } from "../types";

/**
 * What Plan currently asks the Union Supergraph projection API for.
 * This is the *requested* graph context, not a claim that a matching store exists.
 */
export type PlanGraphProjectionMode = "latest-ingest";

export interface PlanGraphContextRequest {
  campaignId: string;
  prepSession: number;
  memorySession: number;
  liveSession: number;
  /** Session id passed to getUnionSupergraphProjection today. */
  requestedSessionId: string;
  projectionMode: PlanGraphProjectionMode;
}

export function buildPlanGraphContextRequest(
  sessionDescriptor: PlanSessionDescriptor,
): PlanGraphContextRequest {
  return {
    campaignId: sessionDescriptor.campaignId,
    prepSession: sessionDescriptor.prepSession,
    memorySession: sessionDescriptor.memorySession,
    liveSession: sessionDescriptor.liveSession,
    requestedSessionId: `session-${sessionDescriptor.memorySession}`,
    projectionMode: "latest-ingest",
  };
}

export const PLAN_GRAPH_PROJECTION_UNAVAILABLE_COPY =
  "No Plan graph projection is available for the current Plan graph context.";
