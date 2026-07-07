import { useEffect, type ReactNode } from "react";

import type { GraphProjectionAdjacencyCandidate } from "../../api/types";
import {
  GraphReviewNodeGameCard,
  type GraphReviewSelectedObjectAction,
} from "./GraphReviewNodeGameCard";
import { GraphReviewRelationshipCard } from "./GraphReviewRelationshipCard";
import {
  type GraphReviewRelationshipPredicate,
} from "./graphReviewLocalAuthoringState";
import {
  findSelectedAdjacency,
  type GraphReviewSelectedNode,
  type GraphReviewSelectedNodeViewModel,
  type GraphReviewSelectedRelationship,
} from "./graphReviewSelectionUtils";

export function GraphReviewProjectedInteractionSurface({
  open,
  selectedNode,
  selectedRelationship,
  authorMode,
  relationshipDraftSource,
  relationshipDraftSourceLabel,
  relationshipPredicate,
  resolver,
  onClose,
  onSelectRelationship,
  onSelectEvidenceDelta,
  onStageNodeAssertion,
  onUseAsRelationshipSource,
  onRelationshipPredicateChange,
  onStageRelationship,
}: {
  open: boolean;
  selectedNode: GraphReviewSelectedNodeViewModel | null;
  selectedRelationship: GraphReviewSelectedRelationship | null;
  authorMode: "review" | "author_draft";
  relationshipDraftSource: GraphReviewSelectedNode | null;
  relationshipDraftSourceLabel?: string | null;
  relationshipPredicate: GraphReviewRelationshipPredicate;
  resolver?: ReactNode;
  onClose: () => void;
  onSelectRelationship: (
    relationship: GraphProjectionAdjacencyCandidate,
  ) => void;
  onSelectEvidenceDelta: (deltaId: string | null) => void;
  onStageNodeAssertion: () => void;
  onUseAsRelationshipSource: () => void;
  onRelationshipPredicateChange: (
    predicate: GraphReviewRelationshipPredicate,
  ) => void;
  onStageRelationship: () => void;
}) {
  useEffect(() => {
    if (!open) return;
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [open, onClose]);

  if (!open || !selectedNode) return null;

  const relationship = findSelectedAdjacency(
    selectedNode.node,
    selectedRelationship,
  );
  const sameObjectAsSource =
    Boolean(relationshipDraftSource) &&
    relationshipDraftSource?.laneRole === selectedNode.laneRole &&
    relationshipDraftSource?.nodeId === selectedNode.node.node_id;
  const canStageRelationship =
    Boolean(relationshipDraftSource) && !sameObjectAsSource;

  const cardActions: GraphReviewSelectedObjectAction[] =
    authorMode === "author_draft"
      ? [
          {
            id: "stage-memory-assertion",
            label: "Stage memory assertion",
            onClick: onStageNodeAssertion,
          },
          {
            id: "use-as-relationship-source",
            label: "Use as relationship source",
            onClick: onUseAsRelationshipSource,
          },
        ]
      : [];

  const relationshipStaging =
    authorMode === "author_draft"
      ? {
          predicate: relationshipPredicate,
          onPredicateChange: onRelationshipPredicateChange,
          canStageRelationship,
          onStageRelationship,
          relationshipDraftSourceLabel: relationshipDraftSourceLabel ?? null,
          sameObjectAsSource,
        }
      : undefined;

  return (
    <div className="graph-review-projected-interaction-backdrop">
      <section
        className="graph-review-projected-interaction-surface"
        role="dialog"
        aria-modal="false"
        aria-label={`Selected object: ${selectedNode.node.label}`}
      >
        <header className="graph-review-projected-interaction-header">
          <p className="plan-surface-kicker">Selected object</p>
          <button
            type="button"
            aria-label="Close selected object"
            onClick={onClose}
          >
            Close
          </button>
        </header>

        <GraphReviewNodeGameCard
          viewModel={selectedNode}
          selectedEdgeId={relationship?.edge_id ?? null}
          onSelectRelationship={onSelectRelationship}
          onSelectEvidenceDelta={onSelectEvidenceDelta}
          actions={cardActions}
          draftActionsNote={
            authorMode === "author_draft"
              ? "Draft actions are local until you prepare and commit them."
              : undefined
          }
          relationshipStaging={relationshipStaging}
        />
        {relationship ? (
          <GraphReviewRelationshipCard
            sourceNode={selectedNode.node}
            relationship={relationship}
          />
        ) : null}

        <section className="graph-review-projected-resolver-section">
          <h4>Find existing object</h4>
          <p>
            DungeonBuddy can check whether this selected object may already
            exist in the reviewed graph. Suggestions are read-only. In Author
            Draft, you can stage a link intent for later prepare/commit review.
            No link or merge is written here.
          </p>
          {resolver ?? null}
        </section>
      </section>
    </div>
  );
}
