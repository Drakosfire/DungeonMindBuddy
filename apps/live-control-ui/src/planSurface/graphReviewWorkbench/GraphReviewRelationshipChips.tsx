import type { GraphProjectionAdjacencyCandidate } from "../../api/types";
import { formatGraphReviewRelationshipStatement } from "./graphReviewSelectionUtils";

export function GraphReviewRelationshipChips({
  sourceLabel,
  relationships,
  selectedEdgeId,
  onSelect,
}: {
  sourceLabel: string;
  relationships: GraphProjectionAdjacencyCandidate[];
  selectedEdgeId: string | null;
  onSelect: (relationship: GraphProjectionAdjacencyCandidate) => void;
}) {
  if (!relationships.length) {
    return <p className="graph-review-muted">No projected relationships available for this object yet.</p>;
  }
  return (
    <div className="graph-review-relationship-chips" aria-label="Connected relationships">
      {relationships.map((relationship) => (
        <button
          key={`${relationship.edge_id}-${relationship.node_id}`}
          type="button"
          aria-pressed={selectedEdgeId === relationship.edge_id}
          onClick={() => onSelect(relationship)}
        >
          {formatGraphReviewRelationshipStatement(sourceLabel, relationship)}
        </button>
      ))}
    </div>
  );
}
