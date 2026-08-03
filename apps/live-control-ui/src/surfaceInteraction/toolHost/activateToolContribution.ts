import { resolveGuardedToolInvoke } from "../../agentInteraction/surfaceInteractionLease";
import type { SurfaceInteractionPublication } from "../types";

export type ToolHostActivationResult =
  | { status: "invoked"; mode: "command" }
  | { status: "opened"; mode: "projection"; projectionId: string }
  | { status: "ignored"; reason: "missing" | "disabled" | "stale" | "unsupported" };

/**
 * Click-time Tool activation against the *current* effective publication.
 * Never trusts a captured contribution object — re-resolves by exact id.
 */
export function activateToolContribution(args: {
  publication: SurfaceInteractionPublication | null;
  toolId: string;
  openProjectionTool: (projectionId: string) => boolean;
}): ToolHostActivationResult {
  const { publication, toolId, openProjectionTool } = args;
  if (!publication) {
    return { status: "ignored", reason: "stale" };
  }
  const tool = publication.tools.find((entry) => entry.id === toolId);
  if (!tool) {
    return { status: "ignored", reason: "missing" };
  }
  if (tool.availability.status !== "enabled") {
    return { status: "ignored", reason: "disabled" };
  }
  if (tool.activation.kind === "command") {
    const invoke = resolveGuardedToolInvoke(publication, toolId);
    if (!invoke) {
      return { status: "ignored", reason: "disabled" };
    }
    void invoke();
    return { status: "invoked", mode: "command" };
  }
  if (tool.activation.kind === "projection") {
    const opened = openProjectionTool(tool.activation.projectionId);
    if (!opened) {
      return { status: "ignored", reason: "unsupported" };
    }
    return { status: "opened", mode: "projection", projectionId: tool.activation.projectionId };
  }
  return { status: "ignored", reason: "unsupported" };
}
