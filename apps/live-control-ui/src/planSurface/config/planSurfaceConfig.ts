import type { PlanViewProjection } from "../../api/types";
import type { SurfaceConfig } from "../types";

export const PLAN_SURFACE_SPIKE_THEME_ID = "mireward-runbook";

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

export function buildPlanContextFromPlanView(planView: PlanViewProjection): SurfaceConfig["context"] {
  const liveSession = planView.session;
  const prepSession = liveSession + 1;
  const ingestSession = Math.max(1, liveSession - 1);
  const campaignLabel = planView.campaign_id.replace(/^longmont-c/i, "Longmont C");
  return {
    campaignId: planView.campaign_id,
    liveSession,
    prepSession,
    ingestSession,
    headerLabel: `Plan · ${campaignLabel} · preparing Session ${prepSession} · ingesting Session ${ingestSession}`,
  };
}

export function createPlanSurfaceConfig(planView: PlanViewProjection): SurfaceConfig {
  return {
    id: "plan",
    label: "Plan",
    context: buildPlanContextFromPlanView(planView),
    tools: [
      { id: "ingest-recap", label: "Ingest Recap", size: "wide" },
      { id: "recap", label: "Recap", size: "wide" },
      { id: "graph-preview", label: "Graph Preview", size: "wide" },
      { id: "graph-gold-review", label: "Graph Gold Review", size: "wide" },
      { id: "party-registry", label: "Party Registry", size: "wide" },
      { id: "statblock", label: "Statblock", size: "wide" },
    ],
    canvas: {
      documentId: "north-gate-session-runbook",
    },
    theme: {
      themeId: PLAN_SURFACE_SPIKE_THEME_ID,
      tokens: PLAN_SURFACE_THEME_TOKENS,
    },
  };
}
