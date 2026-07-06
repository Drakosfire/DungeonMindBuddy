import type { PlanContextDescriptor, SurfaceConfig } from "../types";
import {
  PLAN_SURFACE_SPIKE_THEME_ID,
  PLAN_SURFACE_THEME_TOKENS,
} from "./planSurfaceConfig";

export function createIngestSurfaceConfig(
  context: PlanContextDescriptor,
): SurfaceConfig {
  return {
    id: "ingest",
    label: "Ingest",
    context,
    tools: [
      {
        id: "graph-review-diagnostics",
        label: "Diagnostics",
        size: "wide",
      },
      {
        id: "graph-review-author-draft",
        label: "Author Draft",
        size: "wide",
      },
    ],
    canvas: {
      documentId: "ingest-surface",
    },
    theme: {
      themeId: PLAN_SURFACE_SPIKE_THEME_ID,
      tokens: PLAN_SURFACE_THEME_TOKENS,
    },
  };
}
