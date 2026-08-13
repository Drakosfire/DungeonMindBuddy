import type {
  GraphObjectCardMode,
  GraphObjectCardViewModel,
  GraphObjectEvidenceViewModel,
  GraphObjectRelationshipViewModel,
} from "../graphObjectCard";
import { GraphObjectProjectionCard } from "../graphObjectCard/GraphObjectProjectionCard";
import { ThreatSheetProjection } from "../statblocks/projection/ThreatSheetProjection";
import { shouldRenderThreatCampaignSheet } from "../statblocks/projection/threatSheetViewModel";
import type { PlanSessionDescriptor } from "../planSurface/types";
import {
  PlayObjectSheetProjection,
  shouldRenderPlayObjectSheet,
} from "./PlayObjectSheetProjection";
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
 * Of Conks play-bridged nodes → Play Object Sheet; everything else → GraphObjectProjectionCard.
 */
export function ResolvedGraphObjectProjection({
  resolution,
  glanceOnly = false,
  graphReferenceBinding = null,
  projectionState = null,
  sessionDescriptor,
  model,
  mode = "plan",
  onSelectRelationship,
  selectedRelationshipId = null,
  relationshipsDisabled = false,
  showRelationshipProvenance = true,
  onReadSourceEvidence,
  resolvingEvidenceId = null,
  evidenceErrors = {},
  "aria-label": ariaLabel,
}: ResolvedGraphObjectProjectionProps) {
  if (shouldRenderThreatCampaignSheet(resolution)) {
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

  const cardModel = model ?? resolution.graphObject;

  if (shouldRenderPlayObjectSheet(resolution)) {
    return (
      <PlayObjectSheetProjection
        resolution={resolution}
        model={cardModel}
        glanceOnly={glanceOnly}
        onSelectRelationship={onSelectRelationship}
        selectedRelationshipId={selectedRelationshipId}
        relationshipsDisabled={relationshipsDisabled}
        onReadSourceEvidence={onReadSourceEvidence}
        resolvingEvidenceId={resolvingEvidenceId}
        evidenceErrors={evidenceErrors}
      />
    );
  }

  return (
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
  );
}
