import type { AgentInteractionSurfaceContext } from "./agentInteractionTypes";

/** Stable product labels for Agent Interaction chrome. */
export const AGENT_SURFACE_LABELS: Record<string, string> = {
  index: "Index",
  plan: "Plan",
  ingest: "Ingest",
  build: "Build",
  surface: "Live Control",
  play: "Play",
};

export function agentSurfaceLabel(surfaceId: string | null | undefined): string | null {
  if (!surfaceId) return null;
  return AGENT_SURFACE_LABELS[surfaceId] ?? surfaceId;
}

export function surfaceContextSubtitle(
  context: AgentInteractionSurfaceContext | null,
): string | null {
  if (!context) return null;
  const ambient = context.ambientSummary?.trim() || context.label?.trim() || null;
  const surface = agentSurfaceLabel(context.surfaceId);
  if (surface && ambient && !ambient.toLowerCase().startsWith(surface.toLowerCase())) {
    return `${surface} · ${ambient}`;
  }
  return ambient ?? surface;
}
