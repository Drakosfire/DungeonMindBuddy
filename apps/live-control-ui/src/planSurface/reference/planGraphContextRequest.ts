import type { AgentWorldGraphQueryContextRequest, WorldGraphProjectionFocus, WorldGraphProjectionRequest } from "../../api/types";
import type { PlanSessionDescriptor } from "../types";
import {
  deriveApiLens,
  isReviewCampaignId,
  resolvePlanGraphLens,
  resolvePlanGraphScopeMode,
  type PlanGraphLens,
  type PlanGraphScopeMode,
} from "../sessionCampaignContext";

export interface PlanWorldGraphContext {
  worldId: string;
  campaignId: string;
  scopeMode: PlanGraphScopeMode;
  focus:
    | { kind: "none"; sessionId: null }
    | { kind: "session"; sessionId: string; focusCampaignId: string };
}

export const WORLD_GRAPH_REVISION_COMMITTED_EVENT = "dmb:world-graph-revision-committed";

export interface WorldGraphRevisionCommittedDetail {
  revisionId: string;
  worldId: string;
  campaignId: string;
  affectedNodeIds?: string[];
}

import { getWorldIdForCampaign } from "../../worldGraph/worldGraphSurfaceContext";

export {
  buildBuildWorldGraphProjectionRequest,
  buildWorldGraphRecapProjectionRequest,
  getWorldIdForCampaign,
  admitBuildDocumentScope,
} from "../../worldGraph/worldGraphSurfaceContext";

function buildProjectionFocus(context: PlanWorldGraphContext): WorldGraphProjectionFocus {
  if (context.focus.kind === "none") {
    return { kind: "none", sessionId: null };
  }
  return {
    kind: "session",
    sessionId: context.focus.sessionId,
    campaignId: context.focus.focusCampaignId,
  };
}

export function getPlanWorldGraphContext(
  sessionDescriptor: PlanSessionDescriptor | null | undefined,
  options?: { scopeMode?: PlanGraphScopeMode; lens?: PlanGraphLens | null },
): PlanWorldGraphContext | null {
  if (!sessionDescriptor) return null;

  let lens: PlanGraphLens;
  if (options != null && "lens" in options && options.lens != null) {
    lens = options.lens;
  } else if (options != null && "lens" in options && options.lens == null) {
    return null;
  } else {
    lens = resolvePlanGraphLens(
      sessionDescriptor.campaignId,
      typeof window !== "undefined" ? window.location.search : "",
    );
    if (
      lens.focus == null
      && sessionDescriptor.memorySession != null
      && isReviewCampaignId(sessionDescriptor.campaignId)
      && lens.selectedCampaignIds.includes(sessionDescriptor.campaignId)
    ) {
      lens = {
        ...lens,
        focus: {
          campaignId: sessionDescriptor.campaignId,
          sessionNumber: sessionDescriptor.memorySession,
        },
      };
    }
  }

  const derived = deriveApiLens(lens, sessionDescriptor.campaignId);
  if (!derived) return null;

  const worldId = getWorldIdForCampaign(derived.campaignId);
  if (!worldId) return null;

  const scopeMode = options?.scopeMode ?? derived.scopeMode ?? resolvePlanGraphScopeMode();

  const focus =
    derived.focus == null
      ? ({ kind: "none", sessionId: null } as const)
      : ({
          kind: "session",
          sessionId: `session-${derived.focus.sessionNumber}`,
          focusCampaignId: derived.focus.campaignId,
        } as const);

  return {
    worldId,
    campaignId: derived.campaignId,
    scopeMode,
    focus,
  };
}

export function buildPlanWorldGraphProjectionRequest(
  context: PlanWorldGraphContext,
): WorldGraphProjectionRequest {
  return {
    schema: "dmb_world_graph_projection_request_v1",
    worldId: context.worldId,
    campaignId: context.campaignId,
    scopeMode: context.scopeMode,
    focus: buildProjectionFocus(context),
    admissibility: "gm",
  };
}

export function buildPlanAgentWorldGraphQueryContextRequest(
  context: PlanWorldGraphContext,
  options?: { revisionPin?: string | null },
): AgentWorldGraphQueryContextRequest {
  return {
    schema: "dmb_agent_world_graph_query_context_request_v1",
    world_id: context.worldId,
    campaign_id: context.campaignId,
    scope_mode: context.scopeMode,
    focus: {
      kind: context.focus.kind,
      session_id: context.focus.sessionId,
      campaign_id: context.focus.kind === "session" ? context.focus.focusCampaignId : null,
    },
    admissibility: "gm",
    revision_pin: options?.revisionPin ?? null,
  };
}
