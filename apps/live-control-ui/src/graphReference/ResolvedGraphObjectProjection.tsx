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
import { useCompleteWorldObject, usesCompleteWorldObjectPayload } from "./fullWorldObjectProjection";
import { CompleteObjectPartialWarning } from "./CompleteObjectPartialWarning";
import { CompleteWorldObjectAdvancedDetails } from "./CompleteWorldObjectAdvancedDetails";
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

function withPinnedSourceExcerpts(
  model: GraphObjectCardViewModel,
  bindings: unknown[] | undefined,
): GraphObjectCardViewModel {
  if (!bindings?.length || !model.evidence?.length) return model;
  const byEvidence = new Map<string, {
    artifactId: string; spanId: string; domain: string; excerpt: string;
  }>();
  for (const candidate of bindings) {
    if (!candidate || typeof candidate !== "object") continue;
    const row = candidate as Record<string, unknown>;
    if (row.provenance_status !== "excerpt_ready" || typeof row.content_sha256 !== "string"
      || !/^[a-f0-9]{64}$/i.test(row.content_sha256) || typeof row.evidence_ref_id !== "string"
      || typeof row.source_artifact_id !== "string" || typeof row.source_span_ref_id !== "string"
      || typeof row.source_domain !== "string" || typeof row.excerpt !== "string" || !row.excerpt.trim()) continue;
    byEvidence.set(row.evidence_ref_id, {
      artifactId: row.source_artifact_id,
      spanId: row.source_span_ref_id,
      domain: row.source_domain,
      excerpt: row.excerpt,
    });
  }
  return {
    ...model,
    evidence: model.evidence.map((evidence) => {
      const binding = byEvidence.get(evidence.id);
      if (!binding || binding.artifactId !== evidence.sourceArtifactId
        || binding.spanId !== evidence.sourceSpanRefId || binding.domain !== evidence.sourceDomain) return evidence;
      return { ...evidence, excerpt: binding.excerpt };
    }),
  };
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
    scopeMode: scope?.scopeMode,
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
  const cardModel =
    usesCompleteWorldObjectPayload(complete.status) && completeModel
      ? completeModel
      : glanceModel;
  const readableCardModel = onReadSourceEvidence && complete.result
    ? withPinnedSourceExcerpts(cardModel, complete.result.sourceBindings)
    : cardModel;

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
      <CompleteObjectPartialWarning result={complete.result} />
      <GraphObjectProjectionCard
        model={readableCardModel}
        mode={mode}
        aria-label={ariaLabel ?? `${readableCardModel.label} graph object`}
        showRelationshipProvenance={showRelationshipProvenance}
        onSelectRelationship={onSelectRelationship}
        selectedRelationshipId={selectedRelationshipId}
        disabled={relationshipsDisabled}
        onReadSourceEvidence={onReadSourceEvidence}
        resolvingEvidenceId={resolvingEvidenceId}
        evidenceErrors={evidenceErrors}
        advancedSlot={complete.result ? (
          <CompleteWorldObjectAdvancedDetails
            result={complete.result}
            originSurface={originSurface}
          />
        ) : undefined}
      />
    </div>
  );
}
