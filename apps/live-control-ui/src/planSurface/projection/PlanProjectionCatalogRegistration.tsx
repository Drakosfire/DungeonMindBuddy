import { useEffect, useMemo } from "react";
import type { ReactNode } from "react";

import {
  GRAPH_REFERENCE_PROJECTION_ID,
  type ProjectionCatalogRenderRequest,
} from "../../surfaceInteraction/projection/projectionCatalog";
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
  /** Explicit renderer for this catalog ID — not selected via a shared switch. */
  render: (request: ProjectionCatalogRenderRequest) => ReactNode;
}

export const PLAN_PROJECTION_DEFINITIONS: readonly PlanProjectionDefinition[] = [
  {
    projectionId: "recap",
    kind: "tool",
    preferredSize: "wide",
    requiredBindingIds: [PLAN_CONTEXT_BINDING_ID],
    render: ({ bindings }) => <RecapGraphModule context={readPlanContextBinding(bindings)} />,
  },
  {
    projectionId: "party-registry",
    kind: "tool",
    preferredSize: "wide",
    requiredBindingIds: [PLAN_CONTEXT_BINDING_ID],
    render: ({ bindings }) => <PartyRegistryModule context={readPlanContextBinding(bindings)} />,
  },
  {
    projectionId: "statblock",
    kind: "tool",
    preferredSize: "wide",
    requiredBindingIds: [],
    render: () => <StatblockWorkbenchModule />,
  },
  {
    projectionId: "graph-preview",
    kind: "tool",
    preferredSize: "wide",
    requiredBindingIds: [PLAN_CONTEXT_BINDING_ID],
    render: ({ bindings }) => <GraphPreviewModule context={readPlanContextBinding(bindings)} />,
  },
  {
    projectionId: "graph-gold-review",
    kind: "tool",
    preferredSize: "wide",
    requiredBindingIds: [PLAN_CONTEXT_BINDING_ID],
    render: ({ bindings }) => <GraphGoldReviewModule context={readPlanContextBinding(bindings)} />,
  },
  {
    projectionId: "manual-review",
    kind: "tool",
    preferredSize: "wide",
    requiredBindingIds: [],
    render: () => <ManualReviewModule />,
  },
  {
    projectionId: GRAPH_REFERENCE_PROJECTION_ID,
    kind: "content",
    preferredSize: "wide",
    requiredBindingIds: [
      PLAN_SURFACE_CONFIG_BINDING_ID,
      GRAPH_REFERENCE_RESOLUTION_BINDING_ID,
    ],
    render: ({ active, bindings }) => {
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
          glanceOnly={active.glanceOnly === true}
        />
      );
    },
  },
];

export interface PlanProjectionCatalogRegistrationProps {
  surfaceId: string;
  toolDescriptors: readonly SurfaceInteractionProjectionDescriptor[];
}

export function PlanProjectionCatalogRegistration({
  surfaceId,
  toolDescriptors,
}: PlanProjectionCatalogRegistrationProps) {
  const { registerProjectionCatalog } = useProjection();

  // Membership only — preferredSize changes are synced atomically by the provider
  // on same-identity publication updates so open renderers do not remount.
  const publishedToolIdsKey = toolDescriptors.map((descriptor) => descriptor.id).join("\0");

  const liveDefinitions = useMemo(() => {
    const toolIds = new Set(publishedToolIdsKey.split("\0").filter(Boolean));
    return PLAN_PROJECTION_DEFINITIONS.filter(
      (definition) =>
        definition.kind === "content" || toolIds.has(definition.projectionId),
    );
  }, [publishedToolIdsKey]);

  useEffect(() => {
    if (surfaceId !== "plan") {
      return undefined;
    }
    const cleanups: Array<() => void> = [];
    for (const definition of liveDefinitions) {
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
          render: definition.render,
        }),
      );
    }
    return () => {
      for (const cleanup of cleanups) {
        cleanup();
      }
    };
    // toolDescriptors preferredSize is intentionally omitted: provider syncs size.
    // eslint-disable-next-line react-hooks/exhaustive-deps -- membership-stable registration
  }, [liveDefinitions, registerProjectionCatalog, surfaceId, publishedToolIdsKey]);

  return null;
}

export { GRAPH_REFERENCE_BINDING_ID };
