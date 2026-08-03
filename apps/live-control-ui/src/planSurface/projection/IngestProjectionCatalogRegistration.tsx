import { useEffect, useMemo, useRef } from "react";
import type { ReactNode } from "react";

import { IngestionModule } from "../../modules/IngestionModule";
import type { SurfaceInteractionProjectionDescriptor } from "../../surfaceInteraction/types";
import type { ProjectionCatalogRenderRequest } from "../../surfaceInteraction/projection/projectionCatalog";
import type { ProjectionKind, ProjectionSize } from "../../surfaceInteraction/projection/types";
import { GraphReviewDiagnosticsToolPanel } from "../graphReviewWorkbench/GraphReviewDiagnosticsToolPanel";
import {
  GRAPH_REVIEW_DIAGNOSTICS_BINDING_ID,
  GRAPH_REVIEW_DIAGNOSTICS_TOOL_ID,
  readGraphReviewDiagnosticsBinding,
  readPlanContextBinding,
  PLAN_CONTEXT_BINDING_ID,
  stabilizeStringSetMembership,
} from "./projectionBindings";
import { useProjection } from "./projectionContext";

export interface IngestProjectionDefinition {
  projectionId: string;
  kind: ProjectionKind;
  preferredSize: ProjectionSize;
  requiredBindingIds: readonly string[];
  /** Explicit renderer for this catalog ID — not selected via a shared switch. */
  render: (request: ProjectionCatalogRenderRequest) => ReactNode;
}

export const INGEST_PROJECTION_DEFINITIONS: readonly IngestProjectionDefinition[] = [
  {
    projectionId: "ingest-recap",
    kind: "tool",
    preferredSize: "wide",
    requiredBindingIds: [PLAN_CONTEXT_BINDING_ID],
    render: ({ bindings }) => {
      const context = readPlanContextBinding(bindings);
      return (
        <IngestionModule
          campaignId={context.campaignId}
          session={context.ingestSession}
        />
      );
    },
  },
  {
    projectionId: GRAPH_REVIEW_DIAGNOSTICS_TOOL_ID,
    kind: "tool",
    preferredSize: "wide",
    requiredBindingIds: [GRAPH_REVIEW_DIAGNOSTICS_BINDING_ID],
    render: ({ bindings }) => (
      <GraphReviewDiagnosticsToolPanel
        payload={readGraphReviewDiagnosticsBinding(bindings)}
      />
    ),
  },
];

export interface IngestProjectionCatalogRegistrationProps {
  surfaceId: string;
  toolDescriptors: readonly SurfaceInteractionProjectionDescriptor[];
}

export function IngestProjectionCatalogRegistration({
  surfaceId,
  toolDescriptors,
}: IngestProjectionCatalogRegistrationProps) {
  const { registerProjectionCatalog } = useProjection();

  // Compare full IDs via Set equality; never delimiter-compose membership keys.
  const publishedToolIdsRef = useRef<ReadonlySet<string>>(new Set());
  publishedToolIdsRef.current = stabilizeStringSetMembership(
    publishedToolIdsRef.current,
    toolDescriptors.map((descriptor) => descriptor.id),
  );
  const publishedToolIds = publishedToolIdsRef.current;

  const liveDefinitions = useMemo(() => {
    return INGEST_PROJECTION_DEFINITIONS.filter((definition) =>
      publishedToolIds.has(definition.projectionId),
    );
  }, [publishedToolIds]);

  useEffect(() => {
    if (surfaceId !== "ingest") {
      return undefined;
    }
    const cleanups: Array<() => void> = [];
    for (const definition of liveDefinitions) {
      const descriptor = toolDescriptors.find((entry) => entry.id === definition.projectionId);
      const preferredSize = descriptor?.preferredSize ?? definition.preferredSize;
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
    // eslint-disable-next-line react-hooks/exhaustive-deps -- membership-stable registration
  }, [liveDefinitions, registerProjectionCatalog, surfaceId, publishedToolIds]);

  return null;
}
