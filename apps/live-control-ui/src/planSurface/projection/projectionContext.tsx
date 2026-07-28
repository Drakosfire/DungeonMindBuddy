import type { RunbookReferenceAttrs } from "../../tiptap/references/runbookReferences";
import type { PlanGraphProjectionState, PlanReferenceResolution } from "../reference/graphAwareReferenceResolver";
import type { ActiveProjection, ProjectionSize } from "../types";
import type {
  GraphReviewDiagnosticsProjectionPayload,
  PlanReferenceProjectionBinding,
  RegisterableToolProjectionId,
  ToolProjectionPayloadMap,
} from "./projectionBindings";
import type { ValidatedProjectionSurface } from "../../agentInteraction/projectionSurfacePublication";
import {
  useAgentInteraction,
  useOptionalAgentInteraction,
} from "../../agentInteraction/AgentInteractionProvider";

export interface ProjectionContextValue {
  projectionSurface: ValidatedProjectionSurface | null;
  active: ActiveProjection | null;
  activePlanReference: PlanReferenceResolution | null;
  planProjectionState: PlanGraphProjectionState | null;
  planReferenceBinding: PlanReferenceProjectionBinding | null;
  graphReviewDiagnosticsPayload: GraphReviewDiagnosticsProjectionPayload | null;
  openTool: (toolId: string) => void;
  openContentFromChip: (
    ref: RunbookReferenceAttrs,
    resolution: PlanReferenceResolution,
    glanceOnly?: boolean,
    projectionState?: PlanGraphProjectionState | null,
  ) => void;
  openPlanReferenceResolution: (
    resolution: PlanReferenceResolution,
    projectionState?: PlanGraphProjectionState | null,
  ) => void;
  expandContent: () => void;
  close: () => void;
  registerPlanReferenceBinding: (binding: PlanReferenceProjectionBinding) => () => void;
  registerToolProjectionPayload: <K extends RegisterableToolProjectionId>(
    toolId: K,
    payload: ToolProjectionPayloadMap[K],
  ) => () => void;
}

function mapAgentInteractionToProjection(host: ReturnType<typeof useAgentInteraction>): ProjectionContextValue {
  return {
    projectionSurface: host.projectionSurface,
    active: host.active,
    activePlanReference: host.activePlanReference,
    planProjectionState: host.planProjectionState,
    planReferenceBinding: host.planReferenceBinding,
    graphReviewDiagnosticsPayload: host.graphReviewDiagnosticsPayload,
    openTool: host.openTool,
    openContentFromChip: host.openContentFromChip,
    openPlanReferenceResolution: host.openPlanReferenceResolution,
    expandContent: host.expandContent,
    close: host.close,
    registerPlanReferenceBinding: host.registerPlanReferenceBinding,
    registerToolProjectionPayload: host.registerToolProjectionPayload,
  };
}

export function useProjection(): ProjectionContextValue {
  const host = useAgentInteraction();
  return mapAgentInteractionToProjection(host);
}

export function useOptionalProjection(): ProjectionContextValue | null {
  const host = useOptionalAgentInteraction();
  if (!host) return null;
  return mapAgentInteractionToProjection(host);
}

export function projectionContainerClass(size: ProjectionSize | undefined): string {
  if (size === "fullscreen") return "plan-projection-container plan-projection-fullscreen";
  if (size === "wide") return "plan-projection-container plan-projection-wide";
  return "plan-projection-container plan-projection-compact";
}
