import type { WorldGraphProjectionFocus, WorldGraphProjectionRequest } from "../api/types";
import { getWorldIdForCampaign } from "../worldGraph/worldGraphSurfaceContext";
import {
  deriveApiLens,
  resolvePlanGraphScopeMode,
  type PlanGraphLens,
  type PlanGraphScopeMode,
} from "./sessionCampaignContext";

export interface PlanWorldGraphContext {
  worldId: string;
  campaignId: string;
  scopeMode: PlanGraphScopeMode;
  focus:
    | { kind: "none"; sessionId: null }
    | { kind: "session"; sessionId: string; focusCampaignId: string };
}

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

/** Pure: PlanGraphLens + defaultCampaignId → PlanWorldGraphContext (no session descriptor). */
export function getWorldGraphContextFromLens(
  lens: PlanGraphLens,
  defaultCampaignId: string,
  options?: { scopeMode?: PlanGraphScopeMode },
): PlanWorldGraphContext | null {
  const derived = deriveApiLens(lens, defaultCampaignId);
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

export function buildWorldGraphLensProjectionRequest(
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
