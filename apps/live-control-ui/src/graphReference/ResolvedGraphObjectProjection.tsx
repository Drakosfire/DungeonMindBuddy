import type {
  GraphObjectCardMode,
  GraphObjectCardViewModel,
  GraphObjectEvidenceViewModel,
  GraphObjectRelationshipViewModel,
} from "../graphObjectCard";
import { buildGraphObjectCardFromNodeView } from "../graphObjectCard";
import { GraphObjectProjectionCard } from "../graphObjectCard/GraphObjectProjectionCard";
import { ThreatSheetProjection } from "../statblocks/projection/ThreatSheetProjection";
import { shouldRenderThreatCampaignSheet } from "../statblocks/projection/threatSheetViewModel";
import type { PlanSessionDescriptor } from "../planSurface/types";
import type { WorldGraphObjectProjectionRequest } from "../api/types";
import { useCompleteWorldObject } from "./fullWorldObjectProjection";
import type {
  GraphReferenceProjectionBinding,
  GraphReferenceProjectionState,
  GraphReferenceResolution,
} from "./types";

export interface ResolvedGraphObjectProjectionProps {
  resolution: Extract<GraphReferenceResolution, { kind: "resolved_graph" }>;
  glanceOnly?: boolean;
  graphReferenceBinding?: GraphReferenceProjectionBinding | null;
  projectionState?: GraphReferenceProjectionState | null;
  sessionDescriptor?: PlanSessionDescriptor;
  /** When omitted, uses resolution.graphObject. Plan supplies actions-enriched models. */
  model?: GraphObjectCardViewModel;
  mode?: GraphObjectCardMode;
  originSurface?: NonNullable<WorldGraphObjectProjectionRequest["originSurface"]>;
  onSelectRelationship?: (relationship: GraphObjectRelationshipViewModel) => void;
  selectedRelationshipId?: string | null;
  relationshipsDisabled?: boolean;
  showRelationshipProvenance?: boolean;
  onReadSourceEvidence?: (evidence: GraphObjectEvidenceViewModel) => void;
  resolvingEvidenceId?: string | null;
  evidenceErrors?: Record<string, string>;
  "aria-label"?: string;
}

/**
 * Surface-agnostic resolved-graph content: authored Threats → campaign Threat sheet;
 * everything else → GraphObjectProjectionCard backed by the complete World-object read.
 */
export function ResolvedGraphObjectProjection({
  resolution,
  glanceOnly = false,
  graphReferenceBinding = null,
  projectionState = null,
  sessionDescriptor,
  model,
  mode = "plan",
  originSurface = "plan",
  onSelectRelationship,
  selectedRelationshipId = null,
  relationshipsDisabled = false,
  showRelationshipProvenance = true,
  onReadSourceEvidence,
  resolvingEvidenceId = null,
  evidenceErrors = {},
  "aria-label": ariaLabel,
}: ResolvedGraphObjectProjectionProps) {
  const isThreatSheet = shouldRenderThreatCampaignSheet(resolution);
  const scope = resolution.graphScope;
  const complete = useCompleteWorldObject({
    enabled: !glanceOnly && !isThreatSheet && Boolean(scope?.worldId && scope.revisionId),
    worldId: scope?.worldId,
    campaignId: scope?.campaignId ?? "",
    nodeId: resolution.graphNodeId,
    revisionPin: scope?.revisionId ?? null,
    originSurface,
  });

  if (isThreatSheet) {
    return (
      <ThreatSheetProjection
        resolution={resolution}
        sessionDescriptor={sessionDescriptor}
        projectionState={projectionState}
        graphReferenceBinding={graphReferenceBinding}
        glanceOnly={glanceOnly}
      />
    );
  }

  const glanceModel = model ?? resolution.graphObject;
  const completeModel = complete.nodeView
    ? {
        ...buildGraphObjectCardFromNodeView(complete.nodeView),
        actions: glanceModel.actions,
      }
    : null;
  const cardModel = complete.status === "ready" && completeModel ? completeModel : glanceModel;

  return (
    <div data-complete-object-status={complete.status}>
      {complete.status === "loading" ? (
        <p className="module-muted">Loading complete World object…</p>
      ) : null}
      {complete.status === "error" || complete.status === "missing" ? (
        <p className="module-muted" data-testid="complete-object-load-error">
          {complete.error}
        </p>
      ) : null}
      <GraphObjectProjectionCard
        model={cardModel}
        mode={mode}
        aria-label={ariaLabel ?? `${cardModel.label} graph object`}
        showRelationshipProvenance={showRelationshipProvenance}
        onSelectRelationship={onSelectRelationship}
        selectedRelationshipId={selectedRelationshipId}
        disabled={relationshipsDisabled}
        onReadSourceEvidence={onReadSourceEvidence}
        resolvingEvidenceId={resolvingEvidenceId}
        evidenceErrors={evidenceErrors}
      />
    </div>
  );
}
