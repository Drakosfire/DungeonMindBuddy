import type { SurfaceConfig } from "../planSurface/types";
import {
  PLAN_SURFACE_SPIKE_THEME_ID,
  PLAN_SURFACE_THEME_TOKENS,
} from "../planSurface/config/planSurfaceConfig";
import type { WorkspaceDocumentRecord } from "../api/types";

export const BUILD_SURFACE_ID = "build" as const;
export const BUILD_SURFACE_LABEL = "Build";
export const BUILD_SURFACE_KICKER = "Worldbuilding source authoring";
export const BUILD_DEFAULT_CAMPAIGN_ID = "eldyrwild";
export const BUILD_DEFAULT_DOCUMENT_CLASS = "lore";
export const BUILD_THEME_ID = PLAN_SURFACE_SPIKE_THEME_ID;

export function createBuildSurfaceConfig(
  record: WorkspaceDocumentRecord,
): SurfaceConfig {
  return {
    id: BUILD_SURFACE_ID,
    label: BUILD_SURFACE_LABEL,
    context: {
      campaignId: record.campaign_id,
      liveSession: 0,
      ingestSession: 0,
      headerLabel: record.title,
    },
    tools: [],
    canvas: {
      documentId: record.document_id,
    },
    theme: {
      themeId: BUILD_THEME_ID,
      tokens: PLAN_SURFACE_THEME_TOKENS,
    },
  };
}
