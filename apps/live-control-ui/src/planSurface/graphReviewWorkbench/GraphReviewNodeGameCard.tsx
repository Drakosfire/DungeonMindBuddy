import { useState } from "react";
import type { GraphProjectionAdjacencyCandidate } from "../../api/types";
import { GraphReviewRelationshipChips } from "./GraphReviewRelationshipChips";
import {
  gameSummaryForNode,
  type GraphReviewSelectedNodeViewModel,
} from "./graphReviewSelectionUtils";

function statusCopy(viewModel: GraphReviewSelectedNodeViewModel): string {
  if (viewModel.status === "matched") return "Matched with the other lane.";
  if (viewModel.status === "gold_only")
    return "Present only in the gold fixture.";
  if (viewModel.status === "live_only")
    return "Present only in the selected live run.";
  if (viewModel.status === "comparator_uncertain")
    return "Comparator uncertain; inspect evidence if needed.";
  if (viewModel.status.startsWith("changed_"))
    return "Matched object with changed projected details.";
  return "No comparison status is available yet.";
}

export function GraphReviewNodeGameCard({
  viewModel,
  selectedEdgeId,
  onSelectRelationship,
  onSelectEvidenceDelta,
  showUsefulSurfaces = true,
}: {
  viewModel: GraphReviewSelectedNodeViewModel;
  selectedEdgeId: string | null;
  onSelectRelationship: (
    relationship: GraphProjectionAdjacencyCandidate,
  ) => void;
  onSelectEvidenceDelta?: (deltaId: string | null) => void;
  showUsefulSurfaces?: boolean;
}) {
  const [debugOpen, setDebugOpen] = useState(false);
  const node = viewModel.node;
  return (
    <article
      className="graph-review-node-game-card"
      aria-label={`${node.label} game card`}
    >
      <p className="plan-surface-kicker">
        {viewModel.laneRole === "gold"
          ? "Gold Fixture · read-only"
          : "Live Run · read-only"}
      </p>
      <h4>{node.label}</h4>
      <p className="graph-review-game-kind">
        {[node.kind, node.role].filter(Boolean).join(" / ") || "Graph object"}
      </p>
      <p>{gameSummaryForNode(node)}</p>

      <section>
        <h5>Review status</h5>
        <p>{statusCopy(viewModel)}</p>
        {viewModel.counterpart ? (
          <p>
            <strong>Counterpart:</strong> {viewModel.counterpart.label} (
            {viewModel.counterpart.laneRole})
          </p>
        ) : null}
      </section>

      <section>
        <h5>Connected objects / relationships</h5>
        <GraphReviewRelationshipChips
          sourceLabel={node.label}
          relationships={node.adjacency}
          selectedEdgeId={selectedEdgeId}
          onSelect={onSelectRelationship}
        />
      </section>

      {showUsefulSurfaces ? (
        <section>
          <h5>Useful surfaces</h5>
          <div className="graph-review-card-actions">
            <button
              type="button"
              onClick={() => onSelectEvidenceDelta?.(viewModel.deltaId ?? null)}
              disabled={!viewModel.deltaId}
            >
              Open evidence/debug
            </button>
          </div>
        </section>
      ) : null}

      <details
        className="graph-review-debug-panel"
        open={debugOpen}
        onToggle={(event) => setDebugOpen(event.currentTarget.open)}
      >
        <summary>Evidence / Debug</summary>
        <p>
          {node.evidence_badges.length} evidence badge
          {node.evidence_badges.length === 1 ? "" : "s"};{" "}
          {node.source_domains.length
            ? node.source_domains.join(", ")
            : "no source domains"}
          .
        </p>
      </details>
    </article>
  );
}
