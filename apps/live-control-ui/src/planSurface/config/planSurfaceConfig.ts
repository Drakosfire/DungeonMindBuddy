import type { PlanViewProjection } from "../../api/types";
import type { PlanDocumentDescriptor, PlanSurfaceConfig } from "../types";
import { requestedSessionNumberFromLocation } from "../sessionCampaignContext";
import {
  buildPlanContextFromPlanView,
  createPlanSessionDescriptor,
  type PlanSessionLocationOverrides,
} from "./planSessionDescriptor";

export const PLAN_SURFACE_SPIKE_THEME_ID = "mireward-runbook";
export const PLAN_SURFACE_NOTEBOOK_THEME_ID = "notebook";

export const PLAN_SURFACE_THEME_TOKENS: Record<string, string> = {
  "--fg": "var(--text, #e8eaef)",
  "--fg-mute": "var(--text-muted, #9aa3b5)",
  "--border": "#2a3142",
  "--bg-card": "var(--panel, #171b24)",
  "--bg-input": "#12141a",
  "--accent": "#7aa2f7",
  "--radius": "10px",
  "--mono": "ui-monospace, SFMono-Regular, Menlo, Consolas, monospace",
};

export const PLAN_SURFACE_NOTEBOOK_THEME_TOKENS: Record<string, string> = {
  "--fg": "#243041",
  "--fg-mute": "#5b6b7c",
  "--border": "#d4c4a8",
  "--bg-card": "#fbf7ee",
  "--bg-input": "#fffdf8",
  "--accent": "#2563a8",
  "--radius": "6px",
  "--mono": "ui-monospace, SFMono-Regular, Menlo, Consolas, monospace",
  "--text": "#243041",
};

export { buildPlanContextFromPlanView } from "./planSessionDescriptor";

export function planLocationOverridesFromSearch(
  search: string | null | undefined = typeof window !== "undefined" ? window.location.search : null,
): PlanSessionLocationOverrides {
  return {
    memorySession: requestedSessionNumberFromLocation(search),
  };
}

export function createPlanSurfaceConfig(
  planView: PlanViewProjection,
  planningDocument: PlanDocumentDescriptor,
  locationSearch: string | null | undefined = typeof window !== "undefined"
    ? window.location.search
    : null,
): PlanSurfaceConfig {
  const overrides = planLocationOverridesFromSearch(locationSearch);
  const sessionDescriptor = createPlanSessionDescriptor(planView, planningDocument, overrides);
  return {
    id: "plan",
    label: "Plan",
    context: buildPlanContextFromPlanView(planView, planningDocument, overrides),
    sessionDescriptor,
    tools: [
      { id: "recap", label: "Recap", size: "wide" },
      { id: "party-registry", label: "Party Registry", size: "wide" },
      { id: "statblock", label: "Statblock", size: "wide" },
    ],
    canvas: {
      documentId: planningDocument.documentId,
    },
    theme: {
      themeId: PLAN_SURFACE_NOTEBOOK_THEME_ID,
      tokens: PLAN_SURFACE_NOTEBOOK_THEME_TOKENS,
    },
  };
}
