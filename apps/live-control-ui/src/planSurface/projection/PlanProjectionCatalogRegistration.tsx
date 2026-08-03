import { useEffect, useMemo } from "react";

import { GRAPH_REFERENCE_PROJECTION_ID } from "../../surfaceInteraction/projection/projectionCatalog";
import type { ProjectionKind, ProjectionSize } from "../../surfaceInteraction/projection/types";
import type { SurfaceInteractionProjectionDescriptor } from "../../surfaceInteraction/types";
import { PartyRegistryModule } from "../../modules/PartyRegistryModule";
import { StatblockWorkbenchModule } from "../../surface/modules/StatblockWorkbenchModule";
import { GraphPreviewModule } from "../graphPreview/GraphPreviewModule";
import { GraphGoldReviewModule } from "../graphGoldReview/GraphGoldReviewModule";
import { ManualReviewModule } from "../manualReview/ManualReviewModule";
import { RecapGraphModule } from "../graphPreview/RecapGraphModule";
import { PlanReferenceObjectCard } from "../reference/PlanReferenceObjectCard";
import {
  GRAPH_REFERENCE_BINDING_ID,
  GRAPH_REFERENCE_RESOLUTION_BINDING_ID,
  PLAN_CONTEXT_BINDING_ID,
  PLAN_SURFACE_CONFIG_BINDING_ID,
  readGraphReferenceBinding,
  readGraphReferenceProjectionStateBinding,
  readGraphReferenceResolutionBinding,
  readPlanContextBinding,
  readPlanSurfaceConfigBinding,
} from "./projectionBindings";
import { useProjection } from "./projectionContext";

export interface PlanProjectionDefinition {
  projectionId: string;
  kind: ProjectionKind;
  preferredSize: ProjectionSize;
  requiredBindingIds: readonly string[];
}

export const PLAN_PROJECTION_DEFINITIONS: readonly PlanProjectionDefinition[] = [
  {
    projectionId: "recap",
    kind: "tool",
    preferredSize: "wide",
    requiredBindingIds: [PLAN_CONTEXT_BINDING_ID],
  },
  {
    projectionId: "party-registry",
    kind: "tool",
    preferredSize: "wide",
    requiredBindingIds: [PLAN_CONTEXT_BINDING_ID],
  },
  {
    projectionId: "statblock",
    kind: "tool",
    preferredSize: "wide",
    requiredBindingIds: [],
  },
  {
    projectionId: "graph-preview",
    kind: "tool",
    preferredSize: "wide",
    requiredBindingIds: [PLAN_CONTEXT_BINDING_ID],
  },
  {
    projectionId: "graph-gold-review",
    kind: "tool",
    preferredSize: "wide",
    requiredBindingIds: [PLAN_CONTEXT_BINDING_ID],
  },
  {
    projectionId: "manual-review",
    kind: "tool",
    preferredSize: "wide",
    requiredBindingIds: [],
  },
  {
    projectionId: GRAPH_REFERENCE_PROJECTION_ID,
    kind: "content",
    preferredSize: "wide",
    requiredBindingIds: [
      PLAN_SURFACE_CONFIG_BINDING_ID,
      GRAPH_REFERENCE_RESOLUTION_BINDING_ID,
    ],
  },
] as const;

function renderPlanProjection(
  projectionId: string,
  bindings: Readonly<Record<string, unknown>>,
  glanceOnly: boolean,
) {
  switch (projectionId) {
    case "recap":
      return <RecapGraphModule context={readPlanContextBinding(bindings)} />;
    case "party-registry":
      return <PartyRegistryModule context={readPlanContextBinding(bindings)} />;
    case "statblock":
      return <StatblockWorkbenchModule />;
    case "graph-preview":
      return <GraphPreviewModule context={readPlanContextBinding(bindings)} />;
    case "graph-gold-review":
      return <GraphGoldReviewModule context={readPlanContextBinding(bindings)} />;
    case "manual-review":
      return <ManualReviewModule />;
    case GRAPH_REFERENCE_PROJECTION_ID: {
      const config = readPlanSurfaceConfigBinding(bindings);
      const resolution = readGraphReferenceResolutionBinding(bindings);
      const projectionState = readGraphReferenceProjectionStateBinding(bindings);
      const graphReferenceBinding = readGraphReferenceBinding(bindings);
      return (
        <PlanReferenceObjectCard
          resolution={resolution}
          sessionDescriptor={config.sessionDescriptor}
          projectionState={projectionState ?? null}
          graphReferenceBinding={graphReferenceBinding ?? null}
          glanceOnly={glanceOnly}
        />
      );
    }
    default:
      return null;
  }
}

export interface PlanProjectionCatalogRegistrationProps {
  surfaceId: string;
  toolDescriptors: readonly SurfaceInteractionProjectionDescriptor[];
}

export function PlanProjectionCatalogRegistration({
  surfaceId,
  toolDescriptors,
}: PlanProjectionCatalogRegistrationProps) {
  const { registerProjectionCatalog } = useProjection();

  const liveDefinitionIds = useMemo(() => {
    const toolIds = new Set(toolDescriptors.map((descriptor) => descriptor.id));
    return new Set([
      ...PLAN_PROJECTION_DEFINITIONS.filter(
        (definition) => definition.kind === "tool" && toolIds.has(definition.projectionId),
      ).map((definition) => definition.projectionId),
      GRAPH_REFERENCE_PROJECTION_ID,
    ]);
  }, [toolDescriptors]);

  useEffect(() => {
    if (surfaceId !== "plan") {
      return undefined;
    }
    const cleanups: Array<() => void> = [];
    for (const definition of PLAN_PROJECTION_DEFINITIONS) {
      if (!liveDefinitionIds.has(definition.projectionId)) {
        continue;
      }
      const descriptor = toolDescriptors.find((entry) => entry.id === definition.projectionId);
      const preferredSize = definition.kind === "content"
        ? definition.preferredSize
        : descriptor?.preferredSize ?? definition.preferredSize;
      cleanups.push(
        registerProjectionCatalog({
          projectionId: definition.projectionId,
          surfaceId,
          kind: definition.kind,
          preferredSize,
          requiredBindingIds: definition.requiredBindingIds,
          render: ({ active, bindings }) =>
            renderPlanProjection(
              definition.projectionId,
              bindings,
              active.glanceOnly === true,
            ),
        }),
      );
    }
    return () => {
      for (const cleanup of cleanups) {
        cleanup();
      }
    };
  }, [liveDefinitionIds, registerProjectionCatalog, surfaceId, toolDescriptors]);

  return null;
}

export { GRAPH_REFERENCE_BINDING_ID };
