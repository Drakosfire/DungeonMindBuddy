import { resolveGuardedEditInvoke } from "../../agentInteraction/surfaceInteractionLease";
import type {
  SurfaceInteractionCommandTarget,
  SurfaceInteractionPublication,
  SurfaceInteractionWorkObjectIdentity,
} from "../types";

export type EditHostActivationResult =
  | { status: "invoked" }
  | {
      status: "ignored";
      reason: "stale" | "missing" | "disabled" | "target_mismatch" | "no_canvas";
    };

function sameTarget(
  left: SurfaceInteractionCommandTarget | SurfaceInteractionWorkObjectIdentity | null | undefined,
  right: SurfaceInteractionCommandTarget | SurfaceInteractionWorkObjectIdentity | null | undefined,
): boolean {
  if (!left || !right) return false;
  return left.kind === right.kind && left.id === right.id;
}

/**
 * Click-time Edit activation against the *current* effective publication.
 * Never trusts a captured contribution object — re-resolves by exact id.
 *
 * Requires exact {kind,id} equality among expectedTarget, command.target,
 * and publication.canvas.workObject before invoking through the lease gate.
 */
export function activateEditContribution(args: {
  publication: SurfaceInteractionPublication | null;
  commandId: string;
  expectedTarget: SurfaceInteractionCommandTarget | null;
}): EditHostActivationResult {
  const { publication, commandId, expectedTarget } = args;
  if (!publication) {
    return { status: "ignored", reason: "stale" };
  }
  const command = publication.editCommands.find((entry) => entry.id === commandId);
  if (!command) {
    return { status: "ignored", reason: "missing" };
  }
  if (command.availability.status !== "enabled") {
    return { status: "ignored", reason: "disabled" };
  }
  const canvasTarget = publication.canvas?.workObject ?? null;
  if (!canvasTarget) {
    return { status: "ignored", reason: "no_canvas" };
  }
  if (
    !sameTarget(expectedTarget, canvasTarget)
    || !sameTarget(command.target, canvasTarget)
    || !sameTarget(expectedTarget, command.target)
  ) {
    return { status: "ignored", reason: "target_mismatch" };
  }
  const invoke = resolveGuardedEditInvoke(publication, commandId);
  if (!invoke) {
    return { status: "ignored", reason: "disabled" };
  }
  void invoke();
  return { status: "invoked" };
}
