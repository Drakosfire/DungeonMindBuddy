import { useEffect, useMemo } from "react";

import { IngestionModule } from "../../modules/IngestionModule";
import type { SurfaceInteractionProjectionContribution } from "../../surfaceInteraction/types";
import type { ProjectionKind, ProjectionSize } from "../../surfaceInteraction/projection/types";
import { GraphReviewDiagnosticsToolPanel } from "../graphReviewWorkbench/GraphReviewDiagnosticsToolPanel";
import {
  GRAPH_REVIEW_DIAGNOSTICS_BINDING_ID,
  GRAPH_REVIEW_DIAGNOSTICS_TOOL_ID,
  readGraphReviewDiagnosticsBinding,
  readPlanContextBinding,
  PLAN_CONTEXT_BINDING_ID,
} from "./projectionBindings";
import { useProjection } from "./projectionContext";

export interface IngestProjectionDefinition {
  projectionId: string;
  kind: ProjectionKind;
  preferredSize: ProjectionSize;
  requiredBindingIds: readonly string[];
}

export const INGEST_PROJECTION_DEFINITIONS: readonly IngestProjectionDefinition[] = [
  {
    projectionId: "ingest-recap",
    kind: "tool",
    preferredSize: "wide",
    requiredBindingIds: [PLAN_CONTEXT_BINDING_ID],
  },
  {
    projectionId: GRAPH_REVIEW_DIAGNOSTICS_TOOL_ID,
    kind: "tool",
    preferredSize: "wide",
    requiredBindingIds: [GRAPH_REVIEW_DIAGNOSTICS_BINDING_ID],
  },
] as const;

function renderIngestProjection(
  projectionId: string,
  bindings: Readonly<Record<string, unknown>>,
) {
  switch (projectionId) {
    case "ingest-recap": {
      const context = readPlanContextBinding(bindings);
      return (
        <IngestionModule
          campaignId={context.campaignId}
          session={context.ingestSession}
        />
      );
    }
    case GRAPH_REVIEW_DIAGNOSTICS_TOOL_ID:
      return (
        <GraphReviewDiagnosticsToolPanel
          payload={readGraphReviewDiagnosticsBinding(bindings)}
        />
      );
    default:
      return null;
  }
}

export interface IngestProjectionCatalogRegistrationProps {
  surfaceId: string;
  toolDescriptors: readonly SurfaceInteractionProjectionContribution[];
}

export function IngestProjectionCatalogRegistration({
  surfaceId,
  toolDescriptors,
}: IngestProjectionCatalogRegistrationProps) {
  const { registerProjectionCatalog } = useProjection();

  const liveDefinitionIds = useMemo(() => {
    const toolIds = new Set(toolDescriptors.map((descriptor) => descriptor.id));
    return new Set(
      INGEST_PROJECTION_DEFINITIONS.filter((definition) => toolIds.has(definition.projectionId))
        .map((definition) => definition.projectionId),
    );
  }, [toolDescriptors]);

  useEffect(() => {
    if (surfaceId !== "ingest") {
      return undefined;
    }
    const cleanups: Array<() => void> = [];
    for (const definition of INGEST_PROJECTION_DEFINITIONS) {
      if (!liveDefinitionIds.has(definition.projectionId)) {
        continue;
      }
      const descriptor = toolDescriptors.find((entry) => entry.id === definition.projectionId);
      const preferredSize = descriptor?.preferredSize ?? definition.preferredSize;
      cleanups.push(
        registerProjectionCatalog({
          projectionId: definition.projectionId,
          surfaceId,
          kind: definition.kind,
          preferredSize,
          requiredBindingIds: definition.requiredBindingIds,
          render: ({ bindings }) => renderIngestProjection(definition.projectionId, bindings),
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
