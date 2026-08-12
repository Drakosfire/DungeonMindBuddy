import type { ReactNode } from "react";

import type { GraphProjectionNodeView } from "../api/types";
import { GraphObjectCard } from "./GraphObjectCard";
import type {
  GraphObjectCardMode,
  GraphObjectCardViewModel,
  GraphObjectEvidenceViewModel,
  GraphObjectRelationshipViewModel,
} from "./types";
import { buildGraphObjectCardFromNodeView } from "./buildGraphObjectCardFromNodeView";

export function resolveExactProjectedNode(
  nodeViews: Record<string, GraphProjectionNodeView>,
  nodeId: string,
): GraphProjectionNodeView | null {
  return nodeViews[nodeId] ?? null;
}

export interface GraphObjectProjectionCardProps {
  nodeView?: GraphProjectionNodeView;
  /** Plan may supply a pre-built card model (includes surface actions). */
  model?: GraphObjectCardViewModel;
  mode?: GraphObjectCardMode;
  actions?: ReactNode;
  /**
   * Preferred for Plan: receives the exact clicked relationship row so label-only
   * edges (shared empty targetId) still resolve to the clicked edge.
   */
  onSelectRelationship?: (relationship: GraphObjectRelationshipViewModel) => void;
  /** Exact-id navigation for Recap/Build when only the durable target id is needed. */
  onSelectRelationshipTarget?: (targetId: string) => void;
  loading?: boolean;
  disabled?: boolean;
  selectedRelationshipId?: string | null;
  showRelationshipProvenance?: boolean;
  onReadSourceEvidence?: (evidence: GraphObjectEvidenceViewModel) => void;
  resolvingEvidenceId?: string | null;
  evidenceErrors?: Record<string, string>;
  className?: string;
  "aria-label"?: string;
}

export function GraphObjectProjectionCard({
  nodeView,
  model,
  mode = "plan",
  actions,
  onSelectRelationship,
  onSelectRelationshipTarget,
  loading = false,
  disabled = false,
  selectedRelationshipId = null,
  showRelationshipProvenance = true,
  onReadSourceEvidence,
  resolvingEvidenceId = null,
  evidenceErrors = {},
  className,
  "aria-label": ariaLabel,
}: GraphObjectProjectionCardProps) {
  if (loading) {
    return <p className="plan-projection-empty">Loading graph object…</p>;
  }

  const baseModel =
    model ?? (nodeView ? buildGraphObjectCardFromNodeView(nodeView) : null);
  if (!baseModel) {
    return (
      <p className="graph-preview-error" role="status">
        Graph object is unavailable for this exact node id.
      </p>
    );
  }

  const cardModel: GraphObjectCardViewModel = {
    ...baseModel,
    actions: baseModel.actions?.length ? baseModel.actions : [],
  };

  const handleSelectRelationship =
    onSelectRelationship || onSelectRelationshipTarget
      ? (relationship: GraphObjectRelationshipViewModel) => {
          if (onSelectRelationship) {
            onSelectRelationship(relationship);
            return;
          }
          // Exact-id path: pass through empty-string targetIds so callers that still
          // interpret "" can run; Recap/Build treat empty as unresolved.
          if (relationship.targetId == null || !onSelectRelationshipTarget) return;
          onSelectRelationshipTarget(relationship.targetId);
        }
      : undefined;

  return (
    <div className={className ?? "graph-object-projection-card"} data-testid="graph-object-projection-card">
      <GraphObjectCard
        mode={mode}
        model={cardModel}
        aria-label={ariaLabel ?? `${cardModel.label} graph object`}
        showRelationshipProvenance={showRelationshipProvenance}
        onSelectRelationship={handleSelectRelationship}
        selectedRelationshipId={selectedRelationshipId}
        relationshipsDisabled={disabled}
        onReadSourceEvidence={onReadSourceEvidence}
        resolvingEvidenceId={resolvingEvidenceId}
        evidenceErrors={evidenceErrors}
        actionsSlot={actions ?? undefined}
      />
    </div>
  );
}
