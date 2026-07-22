import type { PlanViewProjection } from "../../api/types";
import { formatReviewCampaignLabel } from "../sessionCampaignContext";
import type { PlanContextDescriptor, PlanSessionDescriptor, SurfaceConfig } from "../types";
import {
  FIXTURE_DOC_ID,
  fixturePlanDocumentDescriptor,
} from "./planSessionDescriptor";
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

/**
 * Session descriptor for World Graph resolution + PlanReferenceObjectCard actions.
 * Ingest has no planning document; stub one so the shared reference host can render.
 */
export function buildIngestSessionDescriptor(
  context: PlanContextDescriptor,
): PlanSessionDescriptor {
  const memorySession = context.ingestSession;
  return {
    surfaceId: "plan",
    campaignId: context.campaignId,
    campaignLabel: formatReviewCampaignLabel(context.campaignId),
    memorySession,
    liveSession: context.liveSession,
    sourceStatusLabel:
      memorySession != null
        ? `Ingest · Session ${memorySession}`
        : "Ingest · world graph",
    sourceStatusKind: "unknown",
    planningDocument: fixturePlanDocumentDescriptor({
      documentId: FIXTURE_DOC_ID,
      title: "Memory Ingest",
      campaignId: context.campaignId,
      targetSession: memorySession,
      targetRelpath: null,
      description: "Ingest surface stub — not a workspace plan document.",
    }),
  };
}

export function createIngestSurfaceConfig(
  context: PlanContextDescriptor,
): SurfaceConfig {
  return {
    id: "ingest",
    label: "Ingest",
    context,
    sessionDescriptor: buildIngestSessionDescriptor(context),
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
