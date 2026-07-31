import type { ReactNode } from "react";

import { IngestionModule } from "../../modules/IngestionModule";
import { PartyRegistryModule } from "../../modules/PartyRegistryModule";
import { StatblockWorkbenchModule } from "../../surface/modules/StatblockWorkbenchModule";
import { GraphPreviewModule } from "../graphPreview/GraphPreviewModule";
import { GraphGoldReviewModule } from "../graphGoldReview/GraphGoldReviewModule";
import { GraphReviewDiagnosticsToolPanel } from "../graphReviewWorkbench/GraphReviewDiagnosticsToolPanel";
import { ManualReviewModule } from "../manualReview/ManualReviewModule";
import { RecapGraphModule } from "../graphPreview/RecapGraphModule";
import type { PlanContextDescriptor, SurfaceConfig } from "../types";
import type {
  GraphReferenceProjectionBinding,
  GraphReferenceProjectionState,
  GraphReferenceResolution,
} from "../../graphReference/types";
import { PlanReferenceObjectCard } from "../reference/PlanReferenceObjectCard";
import type {
  GraphReviewDiagnosticsProjectionPayload,
} from "./projectionBindings";
import { GRAPH_REVIEW_DIAGNOSTICS_TOOL_ID } from "./projectionBindings";

export interface ToolProjectionProps {
  context: PlanContextDescriptor;
}

export interface ContentProjectionProps {
  resolution: GraphReferenceResolution;
  projectionState?: GraphReferenceProjectionState | null;
}

export interface RenderToolProjectionDeps {
  graphReviewDiagnosticsPayload?: GraphReviewDiagnosticsProjectionPayload | null;
}

export interface RenderContentProjectionDeps {
  graphReferenceBinding?: GraphReferenceProjectionBinding | null;
  glanceOnly?: boolean;
}

export function renderToolProjection(
  toolId: string,
  context: PlanContextDescriptor,
  deps: RenderToolProjectionDeps = {},
): ReactNode {
  if (toolId === "ingest-recap") {
    return (
      <IngestionModule
        campaignId={context.campaignId}
        session={context.ingestSession}
      />
    );
  }
  if (toolId === "statblock") {
    return <StatblockWorkbenchModule />;
  }
  if (toolId === "recap") {
    return <RecapGraphModule context={context} />;
  }
  if (toolId === "graph-preview") {
    return <GraphPreviewModule context={context} />;
  }
  if (toolId === "graph-gold-review") {
    return <GraphGoldReviewModule context={context} />;
  }
  if (toolId === GRAPH_REVIEW_DIAGNOSTICS_TOOL_ID) {
    return (
      <GraphReviewDiagnosticsToolPanel
        payload={deps.graphReviewDiagnosticsPayload ?? null}
      />
    );
  }
  if (toolId === "manual-review") {
    return <ManualReviewModule />;
  }
  if (toolId === "party-registry") {
    return <PartyRegistryModule context={context} />;
  }
  return <p className="plan-projection-empty">Unknown tool: {toolId}</p>;
}

export function renderContentProjection(
  resolution: GraphReferenceResolution,
  config: SurfaceConfig,
  projectionState?: GraphReferenceProjectionState | null,
  deps: RenderContentProjectionDeps = {},
): ReactNode {
  return (
    <PlanReferenceObjectCard
      resolution={resolution}
      sessionDescriptor={config.sessionDescriptor}
      projectionState={projectionState}
      graphReferenceBinding={deps.graphReferenceBinding}
      glanceOnly={deps.glanceOnly}
    />
  );
}
