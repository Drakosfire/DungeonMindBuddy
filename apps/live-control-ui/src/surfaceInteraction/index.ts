/**
 * Public surface of the neutral surface-interaction contract (SIH-01).
 *
 * Exports only the neutral contract, helpers, validator, issue types, and
 * result types. No Plan, Build, Ingest, chrome, provider, canvas, or
 * graph-reference symbols are re-exported here (handoff §6.9).
 */

export type {
  SurfaceInteractionAgentContextContribution,
  SurfaceInteractionAvailability,
  SurfaceInteractionCanvasContribution,
  SurfaceInteractionCommandTarget,
  SurfaceInteractionEditCommandContribution,
  SurfaceInteractionIdentity,
  SurfaceInteractionInstancePart,
  SurfaceInteractionPlacement,
  SurfaceInteractionPointer,
  SurfaceInteractionProjectionBinding,
  SurfaceInteractionProjectionDescriptor,
  SurfaceInteractionProjectionKind,
  SurfaceInteractionProjectionSize,
  SurfaceInteractionPublication,
  SurfaceInteractionToolActivation,
  SurfaceInteractionToolContribution,
  SurfaceInteractionValidationIssue,
  SurfaceInteractionValidationIssueCode,
  SurfaceInteractionValidationResult,
  SurfaceInteractionWorkObjectIdentity,
} from "./types";

export {
  createSurfaceInteractionIdentity,
  encodeSurfaceInteractionInstanceKey,
  sameSurfaceInteractionIdentity,
} from "./surfaceIdentity";

export { validateSurfaceInteractionPublication } from "./publication";
