import type {
  GraphReferenceProjectionBinding,
  GraphReferenceProjectionState,
  GraphReferenceResolution,
  OpenGraphReferenceArgs,
} from "../../graphReference/types";
import type { ActiveProjection } from "../../surfaceInteraction/projection/types";
import type {
  GraphReviewDiagnosticsProjectionPayload,
  RegisterableToolProjectionId,
  ToolProjectionPayloadMap,
} from "./projectionBindings";
import type { ValidatedProjectionSurface } from "../../agentInteraction/projectionSurfacePublication";
import type {
  ProjectionCatalogRegistration,
  ProjectionCatalogResolution,
} from "../../surfaceInteraction/projection/projectionCatalog";
import type { ActiveProjection } from "../../surfaceInteraction/projection/types";
import {
  useAgentInteraction,
  useOptionalAgentInteraction,
} from "../../agentInteraction/AgentInteractionProvider";

export interface ProjectionContextValue {
  projectionSurface: ValidatedProjectionSurface | null;
  active: ActiveProjection | null;
  activeGraphReference: GraphReferenceResolution | null;
  graphReferenceProjectionState: GraphReferenceProjectionState | null;
  graphReferenceBinding: GraphReferenceProjectionBinding | null;
  graphReviewDiagnosticsPayload: GraphReviewDiagnosticsProjectionPayload | null;
  openTool: (toolId: string) => void;
  openGraphReference: (args: OpenGraphReferenceArgs) => void;
  expandContent: () => void;
  close: () => void;
  registerGraphReferenceBinding: (binding: GraphReferenceProjectionBinding) => () => void;
  registerToolProjectionPayload: <K extends RegisterableToolProjectionId>(
    toolId: K,
    payload: ToolProjectionPayloadMap[K],
  ) => () => void;
  registerProjectionCatalog: (registration: ProjectionCatalogRegistration) => () => void;
  resolveProjectionCatalog: (args: {
    projectionId: string;
    active: ActiveProjection;
    bindings: Readonly<Record<string, unknown>>;
  }) => ProjectionCatalogResolution;
}

function mapAgentInteractionToProjection(host: ReturnType<typeof useAgentInteraction>): ProjectionContextValue {
  return {
    projectionSurface: host.projectionSurface,
    active: host.active,
    activeGraphReference: host.activeGraphReference,
    graphReferenceProjectionState: host.graphReferenceProjectionState,
    graphReferenceBinding: host.graphReferenceBinding,
    graphReviewDiagnosticsPayload: host.graphReviewDiagnosticsPayload,
    openTool: host.openTool,
    openGraphReference: host.openGraphReference,
    expandContent: host.expandContent,
    close: host.close,
    registerGraphReferenceBinding: host.registerGraphReferenceBinding,
    registerToolProjectionPayload: host.registerToolProjectionPayload,
    registerProjectionCatalog: host.registerProjectionCatalog,
    resolveProjectionCatalog: host.resolveProjectionCatalog,
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
