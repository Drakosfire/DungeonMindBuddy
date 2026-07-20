import type { PlanViewProjection } from "../../api/types";
import type { PlanContextDescriptor, SurfaceConfig } from "../types";
import {
  PLAN_SURFACE_SPIKE_THEME_ID,
  PLAN_SURFACE_THEME_TOKENS,
  planLocationOverridesFromSearch,
} from "./planSurfaceConfig";

/** Ingest does not own a workspace plan document — context is plan-view + URL only. */
export function buildIngestContextFromPlanView(
  planView: PlanViewProjection,
  locationSearch: string | null | undefined = typeof window !== "undefined"
    ? window.location.search
    : null,
): PlanContextDescriptor {
  const overrides = planLocationOverridesFromSearch(locationSearch);
  const liveSession = planView.session;
  return {
    campaignId: planView.campaign_id,
    liveSession,
    ingestSession: overrides.memorySession ?? liveSession,
    headerLabel: "Memory Ingest",
  };
}

export function createIngestSurfaceConfig(
  context: PlanContextDescriptor,
): SurfaceConfig {
  return {
    id: "ingest",
    label: "Ingest",
    context,
    tools: [
      {
        id: "ingest-recap",
        label: "Ingest Recap",
        size: "wide",
      },
      {
        id: "graph-review-diagnostics",
        label: "Diagnostics",
        size: "wide",
      },
    ],
    canvas: {
      documentId: null,
    },
    theme: {
      themeId: PLAN_SURFACE_SPIKE_THEME_ID,
      tokens: PLAN_SURFACE_THEME_TOKENS,
    },
  };
}
