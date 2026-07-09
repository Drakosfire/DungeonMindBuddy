import type { ReactNode } from "react";

import { IngestionModule } from "../../modules/IngestionModule";
import { PartyRegistryModule } from "../../modules/PartyRegistryModule";
import { StatblockWorkbenchModule } from "../../surface/modules/StatblockWorkbenchModule";
import { GraphPreviewModule } from "../graphPreview/GraphPreviewModule";
import { GraphGoldReviewModule } from "../graphGoldReview/GraphGoldReviewModule";
import { GraphReviewAuthorDraftToolPanel } from "../graphReviewWorkbench/GraphReviewAuthorDraftToolPanel";
import { GraphReviewDiagnosticsToolPanel } from "../graphReviewWorkbench/GraphReviewDiagnosticsToolPanel";
import { ManualReviewModule } from "../manualReview/ManualReviewModule";
import { RecapGraphModule } from "../graphPreview/RecapGraphModule";
import type { PlanContextDescriptor } from "../types";
import type { ReferenceResolution } from "../reference/referenceResolver";
import { SelectedObjectCard } from "../selectedObject/SelectedObjectCard";

export interface ToolProjectionProps {
  context: PlanContextDescriptor;
}

export interface ContentProjectionProps {
  resolution: ReferenceResolution;
}

export function renderToolProjection(toolId: string, context: PlanContextDescriptor): ReactNode {
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
  if (toolId === "graph-review-diagnostics") {
    return <GraphReviewDiagnosticsToolPanel />;
  }
  if (toolId === "graph-review-author-draft") {
    return <GraphReviewAuthorDraftToolPanel />;
  }
  if (toolId === "manual-review") {
    return <ManualReviewModule />;
  }
  if (toolId === "party-registry") {
    return <PartyRegistryModule context={context} />;
  }
  return <p className="plan-projection-empty">Unknown tool: {toolId}</p>;
}

export function renderContentProjection(resolution: ReferenceResolution): ReactNode {
  return <SelectedObjectCard resolution={resolution} />;
}
