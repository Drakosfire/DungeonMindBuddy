import { resolveGuardedToolInvoke } from "../../agentInteraction/surfaceInteractionLease";
import type { SurfaceInteractionPublication } from "../types";

export type ToolHostActivationResult =
  | { status: "invoked"; mode: "command" }
  | { status: "opened"; mode: "projection"; projectionId: string }
  | { status: "ignored"; reason: "missing" | "disabled" | "stale" | "unsupported" };

function isThenable<T>(value: T | Promise<T>): value is Promise<T> {
  return typeof value === "object" && value !== null && "then" in value;
}

/**
 * Click-time Tool activation against the *current* effective publication.
 * Never trusts a captured contribution object — re-resolves by exact id.
 *
 * Projection opens pass the **Tool contribution id** to `openProjectionTool`.
 * The host resolves `activation.projectionId` internally.
 */
export function activateToolContribution(args: {
  publication: SurfaceInteractionPublication | null;
  toolId: string;
  openProjectionTool: (toolId: string) => boolean | Promise<boolean>;
}): ToolHostActivationResult | Promise<ToolHostActivationResult> {
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
    const projectionId = tool.activation.projectionId;
    const opened = openProjectionTool(toolId);
    if (isThenable(opened)) {
      return opened.then((ok) =>
        ok
          ? { status: "opened", mode: "projection", projectionId }
          : { status: "ignored", reason: "unsupported" },
      );
    }
    if (!opened) {
      return { status: "ignored", reason: "unsupported" };
    }
    return { status: "opened", mode: "projection", projectionId };
  }
  return { status: "ignored", reason: "unsupported" };
}
