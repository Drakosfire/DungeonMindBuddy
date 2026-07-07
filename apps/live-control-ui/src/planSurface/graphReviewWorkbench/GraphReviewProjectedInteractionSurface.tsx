import { useEffect } from "react";

import type { GraphProjectionAdjacencyCandidate } from "../../api/types";
import { GraphReviewNodeGameCard } from "./GraphReviewNodeGameCard";
import { GraphReviewRelationshipCard } from "./GraphReviewRelationshipCard";
import {
  findSelectedAdjacency,
  type GraphReviewSelectedNodeViewModel,
  type GraphReviewSelectedRelationship,
} from "./graphReviewSelectionUtils";

export function GraphReviewProjectedInteractionSurface({
  open,
  selectedNode,
  selectedRelationship,
  onClose,
  onSelectRelationship,
  onSelectEvidenceDelta,
}: {
  open: boolean;
  selectedNode: GraphReviewSelectedNodeViewModel | null;
  selectedRelationship: GraphReviewSelectedRelationship | null;
  onClose: () => void;
  onSelectRelationship: (
    relationship: GraphProjectionAdjacencyCandidate,
  ) => void;
  onSelectEvidenceDelta: (deltaId: string | null) => void;
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
          actions={[]}
        />
        {relationship ? (
          <GraphReviewRelationshipCard
            sourceNode={selectedNode.node}
            relationship={relationship}
          />
        ) : null}
      </section>
    </div>
  );
}
