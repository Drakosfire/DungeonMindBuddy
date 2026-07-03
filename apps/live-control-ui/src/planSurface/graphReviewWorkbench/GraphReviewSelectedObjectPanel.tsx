import { GraphReviewNodeGameCard } from "./GraphReviewNodeGameCard";
import { GraphReviewRelationshipCard } from "./GraphReviewRelationshipCard";
import { findSelectedAdjacency, type GraphReviewSelectedNodeViewModel, type GraphReviewSelectedRelationship } from "./graphReviewSelectionUtils";
import type { GraphProjectionAdjacencyCandidate } from "../../api/types";

export function GraphReviewSelectedObjectPanel({
  selectedNode,
  selectedRelationship,
  onSelectRelationship,
  onSelectEvidenceDelta,
}: {
  selectedNode: GraphReviewSelectedNodeViewModel | null;
  selectedRelationship: GraphReviewSelectedRelationship | null;
  onSelectRelationship: (relationship: GraphProjectionAdjacencyCandidate) => void;
  onSelectEvidenceDelta: (deltaId: string | null) => void;
}) {
  if (!selectedNode) {
    return (
      <aside className="graph-review-selected-object-panel" aria-label="Selected graph object">
        <p>Select a graph pill to inspect how this object is used in the campaign.</p>
      </aside>
    );
  }
  const relationship = findSelectedAdjacency(selectedNode.node, selectedRelationship);
  return (
    <aside className="graph-review-selected-object-panel" aria-label="Selected graph object">
      <GraphReviewNodeGameCard
        viewModel={selectedNode}
        selectedEdgeId={relationship?.edge_id ?? null}
        onSelectRelationship={onSelectRelationship}
        onSelectEvidenceDelta={onSelectEvidenceDelta}
      />
      {relationship ? <GraphReviewRelationshipCard sourceNode={selectedNode.node} relationship={relationship} /> : null}
    </aside>
  );
}
