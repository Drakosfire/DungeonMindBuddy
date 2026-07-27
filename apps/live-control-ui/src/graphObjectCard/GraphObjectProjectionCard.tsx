import type { ReactNode } from "react";

import type { GraphProjectionNodeView } from "../api/types";
import { GraphObjectCard } from "./GraphObjectCard";
import type {
  GraphObjectCardMode,
  GraphObjectCardViewModel,
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
  onSelectRelationshipTarget?: (targetId: string) => void;
  loading?: boolean;
  disabled?: boolean;
  selectedRelationshipId?: string | null;
  showRelationshipProvenance?: boolean;
  className?: string;
  "aria-label"?: string;
}

export function GraphObjectProjectionCard({
  nodeView,
  model,
  mode = "plan",
  actions,
  onSelectRelationshipTarget,
  loading = false,
  disabled = false,
  selectedRelationshipId = null,
  showRelationshipProvenance = true,
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

  const onSelectRelationship = onSelectRelationshipTarget
    ? (relationship: GraphObjectRelationshipViewModel) => {
        // Pass through empty-string targetIds so Plan's existing label/ambiguity
        // resolver remains reachable. Recap/Build treat empty as unresolved.
        if (relationship.targetId == null) return;
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
        onSelectRelationship={onSelectRelationship}
        selectedRelationshipId={selectedRelationshipId}
        relationshipsDisabled={disabled}
        actionsSlot={actions ?? undefined}
      />
    </div>
  );
}
