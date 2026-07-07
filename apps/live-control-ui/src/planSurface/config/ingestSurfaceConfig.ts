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
        id: "ingest-recap",
        label: "Ingest Recap",
        size: "wide",
      },
      {
        id: "graph-review-diagnostics",
        label: "Diagnostics",
        size: "wide",
      },
      {
        id: "graph-review-author-draft",
        label: "Author Draft",
        size: "fullscreen",
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
