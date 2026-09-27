import { buildBuildSurfaceIdentity } from "./projectionSurfacePublication";
import { BUILD_FIND_EXISTING_TOOL_ID, BUILD_REFERENCE_SEARCH_PROJECTION_ID } from "../buildSurface/reference/buildReferenceIds";
import { activateToolContribution, type ToolHostActivationResult } from "../surfaceInteraction/toolHost/activateToolContribution";
import { sameSurfaceInteractionIdentity } from "../surfaceInteraction/surfaceIdentity";
import type {
  SurfaceInteractionAvailability,
  SurfaceInteractionPublication,
  SurfaceInteractionWorkObjectIdentity,
} from "../surfaceInteraction/types";

const BUILD_SURFACE_ID = "build" as const;

type SemanticActionEffect = Readonly<{
  kind: "open-projection";
  projectionId: typeof BUILD_REFERENCE_SEARCH_PROJECTION_ID;
}>;

/** A callback-free view of one currently published Build action. */
export interface SemanticActionProjection {
  readonly id: typeof BUILD_FIND_EXISTING_TOOL_ID;
  readonly label: string;
  readonly availability: SurfaceInteractionAvailability;
  readonly surfaceIdentity: Readonly<{ surfaceId: string; instanceKey: string }>;
  readonly target: Readonly<SurfaceInteractionWorkObjectIdentity>;
  readonly effect: SemanticActionEffect;
}

const publicationForDescriptor = new WeakMap<
  SemanticActionProjection,
  SurfaceInteractionPublication
>();

function snapshotAvailability(
  availability: SurfaceInteractionAvailability,
): SurfaceInteractionAvailability {
  if (availability.status === "enabled") {
    return Object.freeze({ status: "enabled" });
  }
  return Object.freeze({ status: "disabled", disabledReason: availability.disabledReason });
}

function projectCurrentAction(
  publication: SurfaceInteractionPublication | null,
): SemanticActionProjection | null {
  if (!publication || publication.surfaceId !== BUILD_SURFACE_ID) return null;
  const workObject = publication.canvas?.workObject;
  if (!workObject || workObject.kind !== "document" || !workObject.id.trim()) return null;

  const exactBuildIdentity = buildBuildSurfaceIdentity({ documentId: workObject.id });
  if (!sameSurfaceInteractionIdentity(publication.identity, exactBuildIdentity)) return null;

  const action = publication.tools.find((tool) => tool.id === BUILD_FIND_EXISTING_TOOL_ID);
  if (
    !action
    || action.activation.kind !== "projection"
    || action.activation.projectionId !== BUILD_REFERENCE_SEARCH_PROJECTION_ID
  ) {
    return null;
  }

  return Object.freeze({
    id: BUILD_FIND_EXISTING_TOOL_ID,
    label: action.label,
    availability: snapshotAvailability(action.availability),
    surfaceIdentity: Object.freeze({
      surfaceId: publication.identity.surfaceId,
      instanceKey: publication.identity.instanceKey,
    }),
    target: Object.freeze({ kind: workObject.kind, id: workObject.id }),
    effect: Object.freeze({
      kind: "open-projection",
      projectionId: BUILD_REFERENCE_SEARCH_PROJECTION_ID,
    }),
  });
}

function sameProjection(
  left: SemanticActionProjection,
  right: SemanticActionProjection,
): boolean {
  return left.id === right.id
    && left.label === right.label
    && left.availability.status === right.availability.status
    && (left.availability.status !== "disabled"
      || (right.availability.status === "disabled"
        && left.availability.disabledReason === right.availability.disabledReason))
    && sameSurfaceInteractionIdentity(left.surfaceIdentity, right.surfaceIdentity)
    && left.target.kind === right.target.kind
    && left.target.id === right.target.id
    && left.effect.kind === right.effect.kind
    && left.effect.projectionId === right.effect.projectionId;
}

/**
 * Return the safe semantic view for the one supported action. The runtime-only
 * WeakMap binds it to this exact effective publication without exposing a lease
 * token, callback, or projection binding in the descriptor.
 */
export function describeBuildSemanticAction(
  publication: SurfaceInteractionPublication | null,
): SemanticActionProjection | null {
  const descriptor = projectCurrentAction(publication);
  if (!descriptor || !publication) return null;
  publicationForDescriptor.set(descriptor, publication);
  return descriptor;
}

/**
 * Deterministic Agent-side selection through the same guarded ToolHost helper.
 * Descriptors from a superseded publication, document, or lease fail closed.
 */
export function activateBuildSemanticAction(
  descriptor: SemanticActionProjection,
  currentPublication: SurfaceInteractionPublication | null,
  openProjectionTool: (toolId: string) => boolean | Promise<boolean>,
): ToolHostActivationResult | Promise<ToolHostActivationResult> {
  const originatingPublication = publicationForDescriptor.get(descriptor);
  if (!originatingPublication || originatingPublication !== currentPublication) {
    return { status: "ignored", reason: "stale" };
  }

  const currentDescriptor = projectCurrentAction(currentPublication);
  if (!currentDescriptor || !sameProjection(descriptor, currentDescriptor)) {
    return { status: "ignored", reason: "stale" };
  }

  return activateToolContribution({
    publication: currentPublication,
    toolId: descriptor.id,
    openProjectionTool,
  });
}
